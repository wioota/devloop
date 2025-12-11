"""CLI action logging for self-improvement agent.

Logs all CLI commands executed, optionally capturing Amp thread context
for pattern detection and cross-thread analysis.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CLIAction:
    """Single CLI action log entry.

    Attributes:
        timestamp: ISO 8601 timestamp with timezone
        command: Full command line (list of args or joined string)
        exit_code: Exit code of command (None if not completed)
        thread_id: Optional Amp thread ID (format: T-{uuid})
        thread_url: Optional Amp thread URL
        duration_ms: Command duration in milliseconds (optional)
        user: Username or user identifier (optional)
        working_dir: Working directory when command was executed (optional)
        environment: Selected environment variables (optional)
        output_size_bytes: Size of stdout/stderr output
        error_message: Any error message if command failed
        notes: Additional context or notes
    """

    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    command: str = ""
    exit_code: Optional[int] = None
    thread_id: Optional[str] = None
    thread_url: Optional[str] = None
    duration_ms: Optional[int] = None
    user: Optional[str] = None
    working_dir: Optional[str] = None
    environment: Optional[dict[str, str]] = None
    output_size_bytes: int = 0
    error_message: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class ActionLogger:
    """Logs CLI commands with optional Amp thread context."""

    def __init__(self, log_file: Path):
        """Initialize action logger.

        Args:
            log_file: Path to .devloop/cli-actions.jsonl file
        """
        self.log_file = log_file
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Ensure log directory exists."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_action(self, action: CLIAction) -> None:
        """Log a CLI action to JSONL file.

        Args:
            action: CLIAction to log
        """
        try:
            with open(self.log_file, "a") as f:
                f.write(action.to_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to log CLI action: {e}")

    def log_cli_command(
        self,
        command: str | list[str],
        exit_code: Optional[int] = None,
        duration_ms: Optional[int] = None,
        output_size_bytes: int = 0,
        error_message: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Log a CLI command execution.

        Args:
            command: Command line as string or list of args
            exit_code: Exit code returned by command
            duration_ms: Command duration in milliseconds
            output_size_bytes: Size of command output
            error_message: Any error that occurred
            notes: Additional context or notes
        """
        # Normalize command to string
        if isinstance(command, list):
            command_str = " ".join(command)
        else:
            command_str = command

        # Capture thread context from environment
        thread_id = os.environ.get("AMP_THREAD_ID")
        thread_url = os.environ.get("AMP_THREAD_URL")

        # Capture optional context
        user = os.environ.get("USER")
        working_dir = os.getcwd()

        # Capture selected environment variables for context
        captured_env = {}
        env_vars_to_capture = [
            "AMP_THREAD_ID",
            "AMP_THREAD_URL",
            "CI",
            "GITHUB_ACTIONS",
            "GITLAB_CI",
            "JENKINS_URL",
        ]
        for var in env_vars_to_capture:
            if var in os.environ:
                captured_env[var] = os.environ[var]

        action = CLIAction(
            command=command_str,
            exit_code=exit_code,
            thread_id=thread_id,
            thread_url=thread_url,
            duration_ms=duration_ms,
            user=user,
            working_dir=working_dir,
            environment=captured_env if captured_env else None,
            output_size_bytes=output_size_bytes,
            error_message=error_message,
            notes=notes,
        )

        self.log_action(action)

    def read_recent(self, limit: int = 100) -> list[CLIAction]:
        """Read recent CLI actions from log file.

        Args:
            limit: Maximum number of recent actions to return

        Returns:
            List of CLIAction objects (most recent first)
        """
        if not self.log_file.exists():
            return []

        actions = []
        try:
            with open(self.log_file, "r") as f:
                lines = f.readlines()
                # Process in reverse to get most recent first
                for line in reversed(lines):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            actions.append(CLIAction(**data))
                            if len(actions) >= limit:
                                break
                        except json.JSONDecodeError:
                            logger.warning(f"Skipped malformed JSON line: {line}")
        except Exception as e:
            logger.error(f"Failed to read CLI actions: {e}")

        return actions

    def read_by_thread(self, thread_id: str) -> list[CLIAction]:
        """Read all actions for a specific Amp thread.

        Args:
            thread_id: Amp thread ID (format: T-{uuid})

        Returns:
            List of CLIAction objects for the thread
        """
        if not self.log_file.exists():
            return []

        actions = []
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if data.get("thread_id") == thread_id:
                                actions.append(CLIAction(**data))
                        except json.JSONDecodeError:
                            logger.warning(f"Skipped malformed JSON line: {line}")
        except Exception as e:
            logger.error(f"Failed to read actions for thread {thread_id}: {e}")

        return actions


# Global instance (initialized on first use)
_action_logger: Optional[ActionLogger] = None


def get_action_logger(devloop_dir: Optional[Path] = None) -> ActionLogger:
    """Get or create the global action logger instance.

    Args:
        devloop_dir: Path to .devloop directory (defaults to ~/.devloop)

    Returns:
        ActionLogger instance
    """
    global _action_logger

    if _action_logger is None:
        if devloop_dir is None:
            devloop_dir = Path.home() / ".devloop"

        log_file = devloop_dir / "cli-actions.jsonl"
        _action_logger = ActionLogger(log_file)

    return _action_logger


def log_cli_command(
    command: str | list[str],
    exit_code: Optional[int] = None,
    duration_ms: Optional[int] = None,
    output_size_bytes: int = 0,
    error_message: Optional[str] = None,
    notes: Optional[str] = None,
    devloop_dir: Optional[Path] = None,
) -> None:
    """Convenience function to log a CLI command.

    Args:
        command: Command line as string or list of args
        exit_code: Exit code returned by command
        duration_ms: Command duration in milliseconds
        output_size_bytes: Size of command output
        error_message: Any error that occurred
        notes: Additional context or notes
        devloop_dir: Path to .devloop directory
    """
    logger = get_action_logger(devloop_dir)
    logger.log_cli_command(
        command=command,
        exit_code=exit_code,
        duration_ms=duration_ms,
        output_size_bytes=output_size_bytes,
        error_message=error_message,
        notes=notes,
    )
