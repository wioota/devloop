#!/usr/bin/env python3
"""Security Scanner Agent - Detects security vulnerabilities in code."""

import asyncio
import json
import logging
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..core.agent import Agent, AgentResult
from ..core.context_store import (
    context_store,
    Finding,
    Severity,
    ScopeType,
)
from ..core.event import Event


@dataclass
class SecurityConfig:
    """Configuration for security scanning."""

    enabled_tools: List[str] = None  # ["bandit", "safety", "trivy"]
    severity_threshold: str = "medium"  # low, medium, high
    confidence_threshold: str = "medium"  # low, medium, high
    exclude_patterns: List[str] = None
    max_issues: int = 50

    def __post_init__(self):
        if self.enabled_tools is None:
            self.enabled_tools = ["bandit"]
        if self.exclude_patterns is None:
            self.exclude_patterns = ["test*", "*_test.py", "*/tests/*"]


class SecurityResult:
    """Security scan result."""

    def __init__(
        self, tool: str, issues: List[Dict[str, Any]], errors: List[str] = None
    ):
        self.tool = tool
        self.issues = issues
        self.errors = errors or []
        self.timestamp = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "issues_found": len(self.issues),
            "issues": self.issues,
            "errors": self.errors,
            "severity_breakdown": self._get_severity_breakdown(),
            "confidence_breakdown": self._get_confidence_breakdown(),
        }

    def _get_severity_breakdown(self) -> Dict[str, int]:
        breakdown = {"low": 0, "medium": 0, "high": 0, "unknown": 0}
        for issue in self.issues:
            severity = issue.get("severity", "unknown").lower()
            breakdown[severity] = breakdown.get(severity, 0) + 1
        return breakdown

    def _get_confidence_breakdown(self) -> Dict[str, int]:
        breakdown = {"low": 0, "medium": 0, "high": 0, "unknown": 0}
        for issue in self.issues:
            confidence = issue.get("confidence", "unknown").lower()
            breakdown[confidence] = breakdown.get(confidence, 0) + 1
        return breakdown


class SecurityScannerAgent(Agent):
    """Agent for scanning code for security vulnerabilities."""

    def __init__(self, config: Dict[str, Any], event_bus):
        super().__init__(
            "security-scanner", ["file:modified", "file:created"], event_bus
        )
        self.config = SecurityConfig(**config)
        self.logger = logging.getLogger(f"agent.{self.name}")

    async def handle(self, event: Event) -> AgentResult:
        """Handle file change events by scanning for security issues."""
        try:
            file_path = event.payload.get("path")
            if not file_path:
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    duration=0.0,
                    message="No file path in event",
                )

            path = Path(file_path)
            if not path.exists():
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    duration=0.0,
                    message=f"File does not exist: {file_path}",
                )

            # Only scan Python files for now
            if path.suffix != ".py":
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    duration=0.0,
                    message=f"Skipped non-Python file: {file_path}",
                )

            # Check if file matches exclude patterns
            if self._should_exclude_file(str(path)):
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    duration=0.0,
                    message=f"Excluded file: {file_path}",
                )

            # Run security scan
            results = await self._run_security_scan(path)

            # Filter results based on thresholds
            filtered_issues = self._filter_issues(results.issues)

            agent_result = AgentResult(
                agent_name=self.name,
                success=True,
                duration=0.0,  # Would be calculated in real implementation
                message=f"Scanned {file_path} with {results.tool}",
                data={
                    "file": str(path),
                    "tool": results.tool,
                    "issues_found": len(filtered_issues),
                    "issues": filtered_issues,
                    "severity_breakdown": results._get_severity_breakdown(),
                    "confidence_breakdown": results._get_confidence_breakdown(),
                    "errors": results.errors,
                },
            )

            # Write to context store for Claude Code integration
            await self._write_findings_to_context(path, filtered_issues)

            return agent_result
        except Exception as e:
            self.logger.error(
                f"Error handling security scan for {event.payload.get('path', 'unknown')}: {e}",
                exc_info=True,
            )
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0.0,
                message=f"Security scan failed: {str(e)}",
                error=str(e),
            )

    async def _write_findings_to_context(
        self, path: Path, issues: List[Dict[str, Any]]
    ) -> None:
        """Write security issues to the context store."""
        # Map bandit severity to our Severity enum
        severity_map = {
            "high": Severity.ERROR,
            "medium": Severity.WARNING,
            "low": Severity.INFO,
        }

        for idx, issue in enumerate(issues):
            issue_severity = issue.get("severity", "medium").lower()
            severity = severity_map.get(issue_severity, Severity.WARNING)

            # Security issues are always blocking if high severity
            blocking = issue_severity == "high"

            finding = Finding(
                id=f"security_{path.name}_{issue.get('line_number', 0)}_{idx}",
                agent="security-scanner",
                timestamp=datetime.now(UTC).isoformat() + "Z",
                file=str(path),
                line=issue.get("line_number"),
                severity=severity,
                blocking=blocking,
                category=f"security_{issue.get('test_id', 'unknown')}",
                message=issue.get("text", "Security issue detected"),
                scope_type=ScopeType.CURRENT_FILE,
                caused_by_recent_change=True,
                is_new=True,
            )
            await context_store.add_finding(finding)

    def _should_exclude_file(self, file_path: str) -> bool:
        """Check if file should be excluded from scanning."""
        for pattern in self.config.exclude_patterns:
            if pattern.startswith("*") and pattern.endswith("*"):
                if pattern[1:-1] in file_path:
                    return True
            elif pattern.startswith("*"):
                if file_path.endswith(pattern[1:]):
                    return True
            elif pattern.endswith("*"):
                if file_path.startswith(pattern[:-1]):
                    return True
            elif pattern == file_path:
                return True
        return False

    async def _run_security_scan(self, file_path: Path) -> SecurityResult:
        """Run security scanning tools."""
        try:
            results = []

            # Try bandit first (most common Python security scanner)
            if "bandit" in self.config.enabled_tools:
                bandit_result = await self._run_bandit(file_path)
                if bandit_result:
                    results.append(bandit_result)

            # If no results from primary tools, return empty
            if results:
                return results[0]  # Return first successful result

            return SecurityResult("none", [], ["No security scanning tools available"])
        except Exception as e:
            self.logger.error(
                f"Error running security scan on {file_path}: {e}", exc_info=True
            )
            return SecurityResult("error", [], [f"Security scan error: {str(e)}"])

    async def _run_bandit(self, file_path: Path) -> Optional[SecurityResult]:
        """Run Bandit security scanner."""
        try:
            # Check if bandit is available
            import subprocess  # nosec B404 - Required for running security analysis tools

            result = subprocess.run(
            [sys.executable, "-c", "import bandit"], capture_output=True, text=True
            )  # nosec B603 - Running trusted system Python with safe arguments
            if result.returncode != 0:
                return SecurityResult(
                    "bandit", [], ["Bandit not installed - run: pip install bandit"]
                )

            cmd = [
                sys.executable,
                "-m",
                "bandit",
                "-f",
                "json",
                "-r",
                str(file_path),
                "--severity-level",
                self.config.severity_threshold,
                "--confidence-level",
                self.config.confidence_threshold,
                "-x",
                ",".join(self.config.exclude_patterns),
            ]

            # Run bandit in subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=file_path.parent,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                # Parse JSON output
                try:
                    data = json.loads(stdout.decode())
                    issues = []

                    # Extract issues from bandit output
                    for result in data.get("results", []):
                        filename = result.get("filename", "")
                        if str(file_path) in filename or filename.endswith(
                            str(file_path)
                        ):
                            for issue in result.get("issues", []):
                                issues.append(
                                    {
                                        "code": issue.get("code", ""),
                                        "filename": issue.get("filename", ""),
                                        "line_number": issue.get("line_number", 0),
                                        "line_range": issue.get("line_range", []),
                                        "test_id": issue.get("test_id", ""),
                                        "test_name": issue.get("test_name", ""),
                                        "severity": issue.get(
                                            "issue_severity", "unknown"
                                        ),
                                        "confidence": issue.get(
                                            "issue_confidence", "unknown"
                                        ),
                                        "text": issue.get("issue_text", ""),
                                        "cwe": issue.get("cwe", {}),
                                        "more_info": issue.get("more_info", ""),
                                    }
                                )

                    return SecurityResult("bandit", issues[: self.config.max_issues])

                except json.JSONDecodeError:
                    return SecurityResult(
                        "bandit",
                        [],
                        [f"Failed to parse bandit output: {stdout.decode()[:200]}"],
                    )

            else:
                error_msg = stderr.decode().strip()
                return SecurityResult("bandit", [], [f"Bandit failed: {error_msg}"])

        except Exception as e:
            return SecurityResult("bandit", [], [f"Bandit execution error: {str(e)}"])

    def _filter_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter issues based on configuration thresholds."""
        filtered = []

        severity_levels = {"low": 1, "medium": 2, "high": 3}
        confidence_levels = {"low": 1, "medium": 2, "high": 3}

        threshold_severity = severity_levels.get(self.config.severity_threshold, 1)
        threshold_confidence = confidence_levels.get(
            self.config.confidence_threshold, 1
        )

        for issue in issues:
            issue_severity = severity_levels.get(
                issue.get("severity", "unknown").lower(), 0
            )
            issue_confidence = confidence_levels.get(
                issue.get("confidence", "unknown").lower(), 0
            )

            if (
                issue_severity >= threshold_severity
                and issue_confidence >= threshold_confidence
            ):
                filtered.append(issue)

        return filtered[: self.config.max_issues]
