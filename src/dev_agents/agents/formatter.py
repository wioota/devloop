"""Formatter agent - auto-formats code on save."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dev_agents.core.agent import Agent, AgentResult
from dev_agents.core.context_store import Finding, Severity
from dev_agents.core.event import Event


class FormatterConfig:
    """Configuration for FormatterAgent."""

    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get("enabled", True)
        self.format_on_save = config.get("formatOnSave", True)
        self.report_only = config.get("reportOnly", False)
        self.file_patterns = config.get(
            "filePatterns", ["**/*.py", "**/*.js", "**/*.ts"]
        )
        self.formatters = config.get(
            "formatters",
            {
                "python": "black",
                "javascript": "prettier",
                "typescript": "prettier",
                "json": "prettier",
                "markdown": "prettier",
            },
        )


class FormatterAgent(Agent):
    """Agent that auto-formats code files."""

    def __init__(
        self,
        name: str,
        triggers: List[str],
        event_bus,
        config: Dict[str, Any] | None = None,
    ):
        super().__init__(name, triggers, event_bus)
        self.config = FormatterConfig(config or {})

        # Loop prevention mechanisms
        self._recent_formats: Dict[
            str, List[float]
        ] = {}  # file_path -> list of timestamps
        self._format_timeout = 30  # seconds
        self._loop_detection_window = 10  # seconds
        self._max_consecutive_formats = 3  # per file per window

    async def handle(self, event: Event) -> AgentResult:
        """Handle file change event by formatting the file."""
        # Skip if both format_on_save and report_only are disabled
        if not self.config.format_on_save and not self.config.report_only:
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message="Formatter disabled (not in format-on-save or report-only mode)",
            )

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

        # Loop prevention: Check for formatting loops
        if self._detect_formatting_loop(path):
            await self._write_finding_to_context(
                path=path,
                formatter="loop_detector",
                severity="warning",
                message=f"Prevented formatting loop for {path.name} (too many recent format operations)",
                blocking=True,
            )
            result = AgentResult(
                agent_name=self.name,
                success=False,
                duration=0,
                message=f"Prevented formatting loop for {path.name} (too many recent format operations)",
                error="FORMATTING_LOOP_DETECTED",
            )
            return result

        # Check if file should be formatted
        if not self._should_format(path):
            result = AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message=f"Skipped {path.name} (not in patterns)",
            )
            return result

        # Get appropriate formatter
        formatter = self._get_formatter_for_file(path)
        if not formatter:
            result = AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message=f"No formatter configured for {path.suffix}",
            )
            return result

        # Idempotency check: Only format if file actually needs formatting
        if self.config.format_on_save and not self.config.report_only:
            needs_formatting, check_error = await self._check_formatter(formatter, path)
            if check_error:
                await self._write_finding_to_context(
                    path=path,
                    formatter=formatter,
                    severity="error",
                    message=f"Failed to check if {path.name} needs formatting: {check_error}",
                    blocking=True,
                )
                result = AgentResult(
                    agent_name=self.name,
                    success=False,
                    duration=0,
                    message=f"Failed to check if {path.name} needs formatting: {check_error}",
                    error=check_error,
                )
                return result
            if not needs_formatting:
                result = AgentResult(
                    agent_name=self.name,
                    success=True,
                    duration=0,
                    message=f"{path.name} is already formatted",
                )
                return result

        # Run formatter
        if self.config.report_only:
            # Check mode: see if formatting is needed but don't modify
            needs_formatting, error = await self._check_formatter(formatter, path)
            if error:
                message = f"Check failed for {path.name}: {error}"
                success = False
                await self._write_finding_to_context(
                    path=path,
                    formatter=formatter,
                    severity="error",
                    message=message,
                    blocking=True,
                )
            elif needs_formatting:
                message = (
                    f"Would format {path.name} with {formatter} (report-only mode)"
                )
                success = True
                await self._write_finding_to_context(
                    path=path,
                    formatter=formatter,
                    severity="info",
                    message=f"{path.name} needs formatting with {formatter}",
                    auto_fixable=True,
                )
            else:
                message = f"No formatting needed for {path.name}"
                success = True

            result = AgentResult(
                agent_name=self.name,
                success=success,
                duration=0,
                message=message,
                data={
                    "file": str(path),
                    "formatter": formatter,
                    "needs_formatting": needs_formatting,
                    "report_only": True,
                },
                error=error,
            )
            return result
        else:
            # Format mode: actually modify the file
            success, error = await self._run_formatter(formatter, path)

            if success:
                # Record successful formatting operation for loop prevention
                self._record_formatting_operation(path)
                message = f"Formatted {path.name} with {formatter}"
            else:
                message = f"Failed to format {path.name}: {error}"
                await self._write_finding_to_context(
                    path=path,
                    formatter=formatter,
                    severity="error",
                    message=message,
                    blocking=True,
                )

            result = AgentResult(
                agent_name=self.name,
                success=success,
                duration=0,
                message=message,
                data={"file": str(path), "formatter": formatter, "formatted": success},
                error=error if not success else None,
            )
            return result

    def _should_format(self, path: Path) -> bool:
        """Check if file should be formatted based on patterns."""
        if not path.exists():
            return False

        suffix = path.suffix
        for pattern in self.config.file_patterns:
            if pattern.endswith(suffix):
                return True
            if "*" in pattern and suffix in pattern:
                return True

        return False

    def _get_formatter_for_file(self, path: Path) -> Optional[str]:
        """Get the appropriate formatter for a file."""
        suffix = path.suffix.lstrip(".")

        # Map file extensions to language
        extension_map = {
            "py": "python",
            "js": "javascript",
            "jsx": "javascript",
            "ts": "typescript",
            "tsx": "typescript",
            "json": "json",
            "md": "markdown",
        }

        language = extension_map.get(suffix)
        if language:
            return self.config.formatters.get(language)

        return None

    def _detect_formatting_loop(self, path: Path) -> bool:
        """Detect if we're in a formatting loop for this file."""
        import time

        file_key = str(path.resolve())
        now = time.time()

        # Clean up old entries (older than detection window)
        for k in list(self._recent_formats.keys()):
            self._recent_formats[k] = [
                ts
                for ts in self._recent_formats[k]
                if now - ts < self._loop_detection_window
            ]
            if not self._recent_formats[k]:
                del self._recent_formats[k]

        # Count recent formats for this file
        timestamps = self._recent_formats.get(file_key, [])
        recent_count = len(timestamps)

        if recent_count >= self._max_consecutive_formats + 1:
            self.logger.warning(
                f"Formatting loop detected for {path.name}: "
                f"{recent_count} formats in {self._loop_detection_window}s"
            )
            return True

        return False

    def _record_formatting_operation(self, path: Path) -> None:
        """Record that we just formatted this file."""
        import time

        file_key = str(path.resolve())
        if file_key not in self._recent_formats:
            self._recent_formats[file_key] = []
        self._recent_formats[file_key].append(time.time())

    async def _write_finding_to_context(
        self,
        path: Path,
        formatter: str,
        severity: str,
        message: str,
        blocking: bool = False,
        auto_fixable: bool = False,
    ) -> None:
        """Write a formatting finding to the context store."""
        from dev_agents.core.context_store import context_store

        finding = Finding(
            id=f"{self.name}-{path}-{formatter}",
            agent=self.name,
            timestamp=str(datetime.now()),
            file=str(path),
            severity=Severity(severity),
            message=message,
            suggestion=f"Run {formatter} on {path}" if auto_fixable else "",
            auto_fixable=auto_fixable,
            context={
                "formatter": formatter,
                "blocking": blocking,
            },
        )
        await context_store.add_finding(finding)

    async def _run_formatter(
        self, formatter: str, path: Path
    ) -> tuple[bool, Optional[str]]:
        """Run formatter on a file with timeout protection."""
        try:
            # Add timeout protection to prevent hanging formatters
            import asyncio

            if formatter == "black":
                result = await asyncio.wait_for(
                    self._run_black(path), timeout=self._format_timeout
                )
                return result
            elif formatter == "prettier":
                result = await asyncio.wait_for(
                    self._run_prettier(path), timeout=self._format_timeout
                )
                return result
            else:
                return False, f"Unknown formatter: {formatter}"

        except asyncio.TimeoutError:
            error_msg = f"Formatter {formatter} timed out after {self._format_timeout}s on {path.name}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            self.logger.error(f"Error running {formatter}: {e}")
            return False, str(e)

    async def _check_formatter(
        self, formatter: str, path: Path
    ) -> tuple[bool, Optional[str]]:
        """Check if file needs formatting without modifying it."""
        try:
            if formatter == "black":
                return await self._check_black(path)
            elif formatter == "prettier":
                return await self._check_prettier(path)
            else:
                return False, f"Unknown formatter: {formatter}"

        except Exception as e:
            self.logger.error(f"Error checking {formatter}: {e}")
            return False, str(e)

    async def _run_black(self, path: Path) -> tuple[bool, Optional[str]]:
        """Run black formatter on Python file."""
        try:
            # Get updated environment with venv bin in PATH
            import os

            env = os.environ.copy()
            venv_bin = Path(__file__).parent.parent.parent.parent / ".venv" / "bin"
            if venv_bin.exists():
                env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"

            # Check if black is installed
            check = await asyncio.create_subprocess_exec(
                "black",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            await check.communicate()

            if check.returncode != 0:
                return False, "black not installed"

            # Run black
            proc = await asyncio.create_subprocess_exec(
                "black",
                "--quiet",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                return True, None
            else:
                error = stderr.decode() if stderr else "Unknown error"
                return False, error

        except FileNotFoundError:
            return False, "black command not found"

    async def _run_prettier(self, path: Path) -> tuple[bool, Optional[str]]:
        """Run prettier formatter on JavaScript/TypeScript/JSON/Markdown file."""
        try:
            # Check if prettier is installed
            check = await asyncio.create_subprocess_exec(
                "prettier",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await check.communicate()

            if check.returncode != 0:
                return False, "prettier not installed"

            # Run prettier
            proc = await asyncio.create_subprocess_exec(
                "prettier",
                "--write",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                return True, None
            else:
                error = stderr.decode() if stderr else "Unknown error"
                return False, error

        except FileNotFoundError:
            return False, "prettier command not found"

    async def _check_black(self, path: Path) -> tuple[bool, Optional[str]]:
        """Check if black would format this file (without modifying it)."""
        try:
            # Get updated environment with venv bin in PATH
            import os

            env = os.environ.copy()
            venv_bin = Path(__file__).parent.parent.parent.parent / ".venv" / "bin"
            if venv_bin.exists():
                env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"

            # Run black in check mode
            proc = await asyncio.create_subprocess_exec(
                "black",
                "--check",
                "--quiet",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            stdout, stderr = await proc.communicate()

            # black --check returns 0 if file is formatted, 1 if would reformat
            if proc.returncode == 0:
                # File is already formatted
                return False, None
            elif proc.returncode == 1:
                # File would be reformatted
                return True, None
            else:
                # Error occurred
                error = stderr.decode() if stderr else "Unknown error"
                return False, error

        except FileNotFoundError:
            return False, "black command not found"

    async def _check_prettier(self, path: Path) -> tuple[bool, Optional[str]]:
        """Check if prettier would format this file (without modifying it)."""
        try:
            # Run prettier in check mode
            proc = await asyncio.create_subprocess_exec(
                "prettier",
                "--check",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()

            # prettier --check returns 0 if formatted, 1 if would reformat
            if proc.returncode == 0:
                # File is already formatted
                return False, None
            elif proc.returncode == 1:
                # File would be reformatted
                return True, None
            else:
                # Error occurred
                error = stderr.decode() if stderr else "Unknown error"
                return False, error

        except FileNotFoundError:
            return False, "prettier command not found"
