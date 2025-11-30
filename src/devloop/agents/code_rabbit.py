"""Code Rabbit agent - integrates Code Rabbit CLI for code analysis."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from devloop.core.agent import Agent, AgentResult
from devloop.core.context_store import Finding, Severity
from devloop.core.event import Event


class CodeRabbitConfig:
    """Configuration for CodeRabbitAgent."""

    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get("enabled", True)
        self.api_key = config.get("apiKey")
        self.min_severity = config.get("minSeverity", "warning")
        self.file_patterns = config.get("filePatterns", ["**/*.py", "**/*.js", "**/*.ts"])
        self.debounce = config.get("debounce", 500)  # ms


class CodeRabbitResult:
    """Result from running Code Rabbit analysis."""

    def __init__(
        self,
        success: bool,
        issues: List[Dict[str, Any]] | None = None,
        error: str | None = None,
    ):
        self.success = success
        self.issues = issues or []
        self.error = error

    @property
    def has_issues(self) -> bool:
        """Check if there are any issues."""
        return len(self.issues) > 0

    @property
    def issue_count(self) -> int:
        """Get number of issues."""
        return len(self.issues)


class CodeRabbitAgent(Agent):
    """Agent that runs Code Rabbit analysis on file changes."""

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
        self.config = CodeRabbitConfig(config or {})
        self._last_run: Dict[str, float] = {}  # path -> timestamp for debouncing

    async def handle(self, event: Event) -> AgentResult:
        """Handle file change event by running Code Rabbit analysis."""
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

        # Check if file should be analyzed
        if not self._should_analyze(path):
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message=f"Skipped {path.name} (not in patterns)",
            )

        # Run Code Rabbit analysis
        result = await self._run_code_rabbit(path)

        # Build result message
        if result.error:
            message = f"Code Rabbit error on {path.name}: {result.error}"
            success = False
        elif result.has_issues:
            message = f"Found {result.issue_count} issue(s) in {path.name}"
            success = True
        else:
            message = f"No issues in {path.name}"
            success = True

        agent_result = AgentResult(
            agent_name=self.name,
            success=success,
            duration=0,
            message=message,
            data={
                "file": str(path),
                "tool": "code-rabbit",
                "issues": result.issues,
                "issue_count": result.issue_count,
            },
        )

        # Write findings to context store for Claude Code integration
        await self._write_findings_to_context(path, result)

        return agent_result

    def _should_analyze(self, path: Path) -> bool:
        """Check if file should be analyzed based on patterns."""
        # Skip if file doesn't exist
        if not path.exists():
            return False

        # Simple pattern matching
        suffix = path.suffix
        for pattern in self.config.file_patterns:
            if pattern.endswith(suffix):
                return True
            if "*" in pattern and suffix in pattern:
                return True

        return False

    async def _run_code_rabbit(self, path: Path) -> CodeRabbitResult:
        """Run Code Rabbit analysis on a file."""
        try:
            # Check if code-rabbit CLI is installed
            check = await asyncio.create_subprocess_exec(
                "code-rabbit",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await check.communicate()

            if check.returncode != 0:
                return CodeRabbitResult(
                    success=False, error="code-rabbit CLI not installed"
                )

            # Run Code Rabbit with JSON output
            proc = await asyncio.create_subprocess_exec(
                "code-rabbit",
                "analyze",
                "--format",
                "json",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode != 0 and not stdout:
                return CodeRabbitResult(
                    success=False,
                    error=f"code-rabbit failed: {stderr.decode() if stderr else 'unknown error'}",
                )

            if stdout:
                try:
                    data = json.loads(stdout.decode())
                    issues = data.get("issues", []) if isinstance(data, dict) else data
                    return CodeRabbitResult(success=True, issues=issues)
                except json.JSONDecodeError as e:
                    return CodeRabbitResult(
                        success=False, error=f"Failed to parse Code Rabbit output: {e}"
                    )

            return CodeRabbitResult(success=True, issues=[])

        except FileNotFoundError:
            return CodeRabbitResult(
                success=False, error="code-rabbit command not found"
            )
        except Exception as e:
            self.logger.error(f"Error running Code Rabbit: {e}")
            return CodeRabbitResult(success=False, error=str(e))

    async def _write_findings_to_context(
        self, path: Path, result: CodeRabbitResult
    ) -> None:
        """Write Code Rabbit findings to context store."""
        if not result.success or not result.has_issues:
            return

        from devloop.core.context_store import context_store

        # Convert each issue to a Finding
        for idx, issue in enumerate(result.issues):
            # Extract issue details
            line = issue.get("line")
            column = issue.get("column")
            code = issue.get("code", "unknown")
            message_text = issue.get("message", "")
            severity_str = issue.get("severity", "warning").lower()

            # Map severity values
            severity_map = {
                "error": Severity.ERROR,
                "warning": Severity.WARNING,
                "info": Severity.INFO,
                "note": Severity.INFO,
            }
            severity = severity_map.get(severity_str, Severity.WARNING)

            # Create Finding
            finding = Finding(
                id=f"{self.name}-{path}-{line}-{code}",
                agent=self.name,
                timestamp=str(datetime.now()),
                file=str(path),
                line=line,
                column=column,
                severity=severity,
                message=message_text,
                category=code,
                suggestion=issue.get("suggestion", ""),
                context={
                    "tool": "code-rabbit",
                    "issue_type": issue.get("type", "unknown"),
                },
            )

            try:
                await context_store.add_finding(finding)
            except Exception as e:
                self.logger.error(f"Failed to write finding to context: {e}")
