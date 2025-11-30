"""Snyk agent - integrates Snyk CLI for vulnerability scanning."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from devloop.core.agent import Agent, AgentResult
from devloop.core.context_store import Finding, Severity
from devloop.core.event import Event


class SnykConfig:
    """Configuration for SnykAgent."""

    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get("enabled", True)
        self.api_token = config.get("apiToken")
        self.severity = config.get("severity", "high")
        self.file_patterns = config.get(
            "filePatterns",
            ["**/package.json", "**/requirements.txt", "**/Gemfile", "**/pom.xml"],
        )
        self.debounce = config.get("debounce", 500)  # ms


class SnykResult:
    """Result from running Snyk scan."""

    def __init__(
        self,
        success: bool,
        vulnerabilities: List[Dict[str, Any]] | None = None,
        error: str | None = None,
    ):
        self.success = success
        self.vulnerabilities = vulnerabilities or []
        self.error = error

    @property
    def has_vulnerabilities(self) -> bool:
        """Check if there are any vulnerabilities."""
        return len(self.vulnerabilities) > 0

    @property
    def vulnerability_count(self) -> int:
        """Get number of vulnerabilities."""
        return len(self.vulnerabilities)

    @property
    def critical_count(self) -> int:
        """Get count of critical vulnerabilities."""
        return sum(
            1
            for v in self.vulnerabilities
            if v.get("severity", "").lower() == "critical"
        )

    @property
    def high_count(self) -> int:
        """Get count of high severity vulnerabilities."""
        return sum(
            1
            for v in self.vulnerabilities
            if v.get("severity", "").lower() == "high"
        )


class SnykAgent(Agent):
    """Agent that runs Snyk security scanning on dependency files."""

    def __init__(
        self,
        name: str,
        triggers: List[str],
        event_bus,
        config: Dict[str, Any] | None = None,
        feedback_api=None,
        performance_monitor=None,
    ):
        super().__init__(
            name,
            triggers,
            event_bus,
            feedback_api=feedback_api,
            performance_monitor=performance_monitor,
        )
        self.config = SnykConfig(config or {})
        self._last_run: Dict[str, float] = {}  # path -> timestamp for debouncing

    async def handle(self, event: Event) -> AgentResult:
        """Handle file change event by running Snyk scan."""
        # Extract file path
        file_path = event.payload.get("path")
        if not file_path:
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message="No file path in event",
            )

        path = Path(file_path)

        # Check if file should be scanned
        if not self._should_scan(path):
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message=f"Skipped {path.name} (not a dependency file)",
            )

        # Run Snyk scan
        result = await self._run_snyk(path)

        # Build result message
        if result.error:
            message = f"Snyk error on {path.name}: {result.error}"
            success = False
        elif result.has_vulnerabilities:
            critical = result.critical_count
            high = result.high_count
            message = (
                f"Found {result.vulnerability_count} vulnerability(ies) in {path.name}"
            )
            if critical > 0:
                message += f" ({critical} critical, {high} high)"
            success = True
        else:
            message = f"No vulnerabilities in {path.name}"
            success = True

        agent_result = AgentResult(
            agent_name=self.name,
            success=success,
            duration=0,
            message=message,
            data={
                "file": str(path),
                "tool": "snyk",
                "vulnerabilities": result.vulnerabilities,
                "vulnerability_count": result.vulnerability_count,
                "critical_count": result.critical_count,
                "high_count": result.high_count,
            },
        )

        # Write findings to context store
        await self._write_findings_to_context(path, result)

        return agent_result

    def _should_scan(self, path: Path) -> bool:
        """Check if file should be scanned based on patterns."""
        # Skip if file doesn't exist
        if not path.exists():
            return False

        # Only scan dependency files
        file_name = path.name
        for pattern in self.config.file_patterns:
            # Simple pattern matching for common dependency files
            if pattern.startswith("**/"):
                pattern = pattern[3:]
            if file_name == pattern:
                return True

        return False

    async def _run_snyk(self, path: Path) -> SnykResult:
        """Run Snyk scan on a dependency file."""
        try:
            # Check if snyk CLI is installed
            check = await asyncio.create_subprocess_exec(
                "snyk",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await check.communicate()

            if check.returncode != 0:
                return SnykResult(
                    success=False, error="snyk CLI not installed or not authenticated"
                )

            # Run Snyk test with JSON output
            proc = await asyncio.create_subprocess_exec(
                "snyk",
                "test",
                str(path.parent),  # Scan from directory containing dependency file
                "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()

            # Snyk returns non-zero if vulnerabilities found, but that's expected
            if stdout:
                try:
                    data = json.loads(stdout.decode())

                    # Handle Snyk JSON response format
                    if isinstance(data, dict):
                        vulnerabilities = data.get("vulnerabilities", [])
                        error = data.get("error")
                        if error:
                            error_msg = error.get("message", "Unknown Snyk error")
                            return SnykResult(
                                success=False,
                                error=error_msg,
                            )
                        return SnykResult(success=True, vulnerabilities=vulnerabilities)
                    else:
                        # If it's a list, use it directly
                        return SnykResult(success=True, vulnerabilities=data)

                except json.JSONDecodeError as e:
                    return SnykResult(
                        success=False, error=f"Failed to parse Snyk output: {e}"
                    )

            return SnykResult(success=True, vulnerabilities=[])

        except FileNotFoundError:
            return SnykResult(success=False, error="snyk command not found")
        except Exception as e:
            self.logger.error(f"Error running Snyk: {e}")
            return SnykResult(success=False, error=str(e))

    async def _write_findings_to_context(self, path: Path, result: SnykResult) -> None:
        """Write Snyk findings to context store."""
        if not result.success or not result.has_vulnerabilities:
            return

        from devloop.core.context_store import context_store

        # Convert each vulnerability to a Finding
        for idx, vuln in enumerate(result.vulnerabilities):
            # Extract vulnerability details
            vuln_id = vuln.get("id", f"snyk-{idx}")
            title = vuln.get("title", "Unknown vulnerability")
            severity_str = vuln.get("severity", "medium").lower()
            cvss_score = vuln.get("cvssScore")
            package = vuln.get("package", "unknown")
            from_package = vuln.get("from", [])
            fix_available = vuln.get("fixAvailable", False)
            upgradePath = vuln.get("upgradePath", [])

            # Map severity values
            severity_map = {
                "critical": Severity.ERROR,
                "high": Severity.ERROR,
                "medium": Severity.WARNING,
                "low": Severity.INFO,
            }
            severity = severity_map.get(severity_str, Severity.WARNING)

            # Build suggestion
            suggestion = ""
            if fix_available and upgradePath:
                suggestion = f"Upgrade path available: {' -> '.join(upgradePath)}"
            elif fix_available:
                suggestion = "Fix available - run 'snyk fix' to apply"

            # Create Finding
            finding = Finding(
                id=f"{self.name}-{path.name}-{vuln_id}",
                agent=self.name,
                timestamp=str(datetime.now()),
                file=str(path),
                line=None,
                column=None,
                severity=severity,
                message=title,
                category=f"vulnerability-{severity_str}",
                suggestion=suggestion,
                context={
                    "tool": "snyk",
                    "vulnerability_id": vuln_id,
                    "package": package,
                    "cvss_score": cvss_score,
                    "fix_available": fix_available,
                    "from": from_package,
                },
            )

            try:
                await context_store.add_finding(finding)
            except Exception as e:
                self.logger.error(f"Failed to write finding to context: {e}")
