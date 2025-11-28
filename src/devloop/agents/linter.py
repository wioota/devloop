"""Linter agent - runs linters on file changes."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from devloop.core.agent import Agent, AgentResult
from devloop.core.context_store import Finding, Severity
from devloop.core.event import Event


class LinterConfig:
    """Configuration for LinterAgent."""

    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get("enabled", True)
        self.auto_fix = config.get("autoFix", False)
        self.file_patterns = config.get("filePatterns", ["**/*.py"])
        self.linters = config.get(
            "linters",
            {"python": "ruff", "javascript": "eslint", "typescript": "eslint"},
        )
        self.debounce = config.get("debounce", 500)  # ms


class LinterResult:
    """Result from running a linter."""

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


class LinterAgent(Agent):
    """Agent that runs linters on file changes."""

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
        self.config = LinterConfig(config or {})
        self._last_run: Dict[str, float] = {}  # path -> timestamp for debouncing

    async def handle(self, event: Event) -> AgentResult:
        """Handle file change event by running linter."""
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

        # Check if file should be linted
        if not self._should_lint(path):
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message=f"Skipped {path.name} (not in patterns)",
            )

        # Get appropriate linter for file type
        linter = self._get_linter_for_file(path)
        if not linter:
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message=f"No linter configured for {path.suffix}",
            )

        # Run linter
        result = await self._run_linter(linter, path)

        # Auto-fix if configured and issues found
        if self.config.auto_fix and result.has_issues:
            fix_result = await self._auto_fix(linter, path)
            if fix_result.success:
                # Re-run linter to get updated results
                result = await self._run_linter(linter, path)

        # Build result message
        if result.error:
            message = f"Linter error on {path.name}: {result.error}"
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
                "linter": linter,
                "issues": result.issues,
                "issue_count": result.issue_count,
            },
        )

        # Write findings to context store for Claude Code integration
        await self._write_findings_to_context(path, result, linter)

        return agent_result

    def _should_lint(self, path: Path) -> bool:
        """Check if file should be linted based on patterns."""
        # Skip if file doesn't exist
        if not path.exists():
            return False

        # Simple pattern matching (could be improved with fnmatch)
        suffix = path.suffix
        for pattern in self.config.file_patterns:
            if pattern.endswith(suffix):
                return True
            if "*" in pattern and suffix in pattern:
                return True

        return False

    def _get_linter_for_file(self, path: Path) -> Optional[str]:
        """Get the appropriate linter for a file."""
        suffix = path.suffix.lstrip(".")

        # Map file extensions to language
        extension_map = {
            "py": "python",
            "js": "javascript",
            "jsx": "javascript",
            "ts": "typescript",
            "tsx": "typescript",
        }

        language = extension_map.get(suffix)
        if language:
            return self.config.linters.get(language)

        return None

    async def _run_linter(self, linter: str, path: Path) -> LinterResult:
        """Run linter on a file."""
        try:
            # Build command based on linter
            if linter == "ruff":
                result = await self._run_ruff(path)
            elif linter == "eslint":
                result = await self._run_eslint(path)
            else:
                result = LinterResult(success=False, error=f"Unknown linter: {linter}")

            return result

        except Exception as e:
            self.logger.error(f"Error running {linter}: {e}")
            return LinterResult(success=False, error=str(e))

    async def _run_ruff(self, path: Path) -> LinterResult:
        """Run ruff on a Python file."""
        try:
            # Get updated environment with venv bin in PATH
            import os

            env = os.environ.copy()
            venv_bin = Path(__file__).parent.parent.parent.parent / ".venv" / "bin"
            if venv_bin.exists():
                env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"

            # Check if ruff is installed
            check = await asyncio.create_subprocess_exec(
                "ruff",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            await check.communicate()

            if check.returncode != 0:
                return LinterResult(success=False, error="ruff not installed")

            # Run ruff with JSON output
            proc = await asyncio.create_subprocess_exec(
                "ruff",
                "check",
                "--output-format",
                "json",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            stdout, stderr = await proc.communicate()

            # ruff returns non-zero if issues found, but that's expected
            if stdout:
                try:
                    issues = json.loads(stdout.decode())
                    return LinterResult(success=True, issues=issues)
                except json.JSONDecodeError:
                    # No issues found or invalid JSON
                    return LinterResult(success=True, issues=[])
            else:
                # No output = no issues
                return LinterResult(success=True, issues=[])

        except FileNotFoundError:
            return LinterResult(success=False, error="ruff command not found")

    async def _run_eslint(self, path: Path) -> LinterResult:
        """Run eslint on a JavaScript/TypeScript file."""
        try:
            # Check if eslint is installed
            check = await asyncio.create_subprocess_exec(
                "eslint",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await check.communicate()

            if check.returncode != 0:
                return LinterResult(success=False, error="eslint not installed")

            # Run eslint with JSON output
            proc = await asyncio.create_subprocess_exec(
                "eslint",
                "--format",
                "json",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()

            if stdout:
                try:
                    results = json.loads(stdout.decode())
                    # ESLint returns array of file results
                    if results and len(results) > 0:
                        issues = results[0].get("messages", [])
                        return LinterResult(success=True, issues=issues)
                except json.JSONDecodeError:
                    pass

            return LinterResult(success=True, issues=[])

        except FileNotFoundError:
            return LinterResult(success=False, error="eslint command not found")

    async def _auto_fix(self, linter: str, path: Path) -> LinterResult:
        """Attempt to auto-fix issues."""
        try:
            # Get updated environment with venv bin in PATH
            import os

            env = os.environ.copy()
            venv_bin = Path(__file__).parent.parent.parent.parent / ".venv" / "bin"
            if venv_bin.exists():
                env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"

            if linter == "ruff":
                proc = await asyncio.create_subprocess_exec(
                    "ruff",
                    "check",
                    "--fix",
                    str(path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
                await proc.communicate()
                return LinterResult(success=True)

            elif linter == "eslint":
                proc = await asyncio.create_subprocess_exec(
                    "eslint",
                    "--fix",
                    str(path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
                await proc.communicate()
                return LinterResult(success=True)

            return LinterResult(success=False, error="Auto-fix not supported")

        except Exception as e:
            return LinterResult(success=False, error=str(e))

    async def _write_findings_to_context(
        self, path: Path, result: LinterResult, linter: str
    ) -> None:
        """Write linter findings to context store."""
        if not result.success or not result.has_issues:
            return

        from devloop.core.context_store import context_store

        # Convert each linter issue to a Finding
        for idx, issue in enumerate(result.issues):
            # Extract issue details (format varies by linter)
            if linter == "ruff":
                location = issue.get("location", {})
                line = location.get("row") if isinstance(location, dict) else None
                column = location.get("column") if isinstance(location, dict) else None
                code = issue.get("code", "unknown")
                message_text = issue.get("message", "")
                fixable = issue.get("fix", None) is not None
                # Get severity from code prefix (E, W, F, etc.)
                severity = "error" if code.startswith(("E", "F")) else "warning"
            elif linter == "eslint":
                line = issue.get("line")
                column = issue.get("column")
                code = issue.get("ruleId", "unknown")
                message_text = issue.get("message", "")
                fixable = issue.get("fix", None) is not None
                # eslint severity: 1 = warning, 2 = error
                eslint_severity = issue.get("severity", 1)
                severity = "error" if eslint_severity == 2 else "warning"
            else:
                # Generic format
                line = None
                column = None
                code = "unknown"
                message_text = str(issue)
                fixable = False
                severity = "warning"

            # Create Finding
            finding = Finding(
                id=f"{self.name}-{path}-{line}-{code}",
                agent=self.name,
                timestamp=str(datetime.now()),
                file=str(path),
                line=line,
                column=column,
                severity=Severity(severity),
                message=message_text,
                category=code,
                suggestion=(
                    f"Run {linter} --fix {path}"
                    if fixable and self.config.auto_fix
                    else ""
                ),
                context={
                    "linter": linter,
                    "fixable": fixable,
                    "auto_fixable": fixable and self.config.auto_fix,
                },
            )

            try:
                await context_store.add_finding(finding)
            except Exception as e:
                self.logger.error(f"Failed to write finding to context: {e}")
