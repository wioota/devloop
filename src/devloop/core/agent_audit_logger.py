"""Audit logging for agent actions and file modifications.

Provides immutable audit trail of agent actions, file modifications, and fixes
applied by agents for security, compliance, and incident investigation.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import difflib


class ActionType(str, Enum):
    """Types of agent actions that can be audited."""

    FILE_MODIFIED = "file_modified"
    FILE_CREATED = "file_created"
    FILE_DELETED = "file_deleted"
    COMMAND_EXECUTED = "command_executed"
    FIX_APPLIED = "fix_applied"
    FINDING_REPORTED = "finding_reported"
    CONFIG_CHANGED = "config_changed"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class FileModification:
    """Details of a file modification.

    Attributes:
        path: Absolute path to file
        action: Type of modification (created, modified, deleted)
        size_bytes_before: File size before modification (or None if created)
        size_bytes_after: File size after modification (or None if deleted)
        line_count_before: Number of lines before (or None if created)
        line_count_after: Number of lines after (or None if deleted)
        diff_lines: List of unified diff lines (limited to first/last N for large changes)
        hash_before: SHA256 hash before (for integrity verification)
        hash_after: SHA256 hash after (for integrity verification)
    """

    path: str
    action: str  # created, modified, deleted
    size_bytes_before: Optional[int] = None
    size_bytes_after: Optional[int] = None
    line_count_before: Optional[int] = None
    line_count_after: Optional[int] = None
    diff_lines: Optional[List[str]] = None
    hash_before: Optional[str] = None
    hash_after: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AgentAuditEntry:
    """Single audit log entry for agent action.

    Attributes:
        timestamp: ISO 8601 timestamp with timezone
        agent_name: Name of the agent that performed action
        action_type: Type of action (from ActionType enum)
        message: Human-readable description of action
        success: Whether action completed successfully
        duration_ms: Duration of action in milliseconds
        file_modifications: List of file modifications (if applicable)
        command: Command executed (if applicable)
        exit_code: Exit code of command (if applicable)
        error: Error message (if action failed)
        findings_count: Number of findings reported (if applicable)
        context: Additional context data
    """

    timestamp: str
    agent_name: str
    action_type: str
    message: str
    success: bool
    duration_ms: int
    file_modifications: Optional[List[Dict[str, Any]]] = None
    command: Optional[str] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None
    findings_count: Optional[int] = None
    context: Optional[Dict[str, Any]] = None

    def to_json(self) -> str:
        """Convert to JSON string for logging.

        Returns:
            JSON string representation
        """
        return json.dumps(asdict(self), ensure_ascii=False)


class AgentAuditLogger:
    """Audit logger for agent actions and file modifications.

    Maintains immutable append-only log of all agent operations for:
    - Security audits
    - Incident investigation
    - Compliance tracking
    - File change tracking with diffs
    - Fix validation

    Implements 30-day retention policy to prevent unbounded log growth.
    """

    def __init__(self, log_path: Optional[Path] = None, retention_days: int = 30):
        """Initialize agent audit logger.

        Args:
            log_path: Path to audit log file (defaults to .devloop/agent-audit.log)
            retention_days: Number of days to keep audit logs (default: 30)
        """
        if log_path is None:
            log_path = Path(".devloop/agent-audit.log")

        self.log_path = log_path
        self.retention_days = retention_days
        self.logger = logging.getLogger("agent.audit")

        # Ensure log directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_action(
        self,
        agent_name: str,
        action_type: ActionType | str,
        message: str,
        success: bool,
        duration_ms: int,
        file_modifications: Optional[List[FileModification]] = None,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        error: Optional[str] = None,
        findings_count: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an agent action to audit log.

        Args:
            agent_name: Name of the agent
            action_type: Type of action (ActionType enum value or string)
            message: Human-readable description
            success: Whether action succeeded
            duration_ms: Duration in milliseconds
            file_modifications: List of FileModification objects
            command: Command executed (if applicable)
            exit_code: Exit code (if applicable)
            error: Error message (if applicable)
            findings_count: Number of findings (if applicable)
            context: Additional context data
        """
        # Convert ActionType enum to string if needed
        action_str = (
            action_type.value
            if isinstance(action_type, ActionType)
            else str(action_type)
        )

        # Create audit entry
        entry = AgentAuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_name=agent_name,
            action_type=action_str,
            message=message,
            success=success,
            duration_ms=duration_ms,
            file_modifications=[m.to_dict() for m in (file_modifications or [])],
            command=command,
            exit_code=exit_code,
            error=error,
            findings_count=findings_count,
            context=context,
        )

        # Write to audit log (append-only)
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(entry.to_json() + "\n")

            # Periodically clean up old logs
            self._cleanup_old_logs()
        except Exception as e:
            self.logger.error(f"Failed to write agent audit log: {e}")

    def log_file_modified(
        self,
        agent_name: str,
        file_path: Path,
        before_content: Optional[str] = None,
        after_content: Optional[str] = None,
        message: str = "File modified",
        success: bool = True,
        duration_ms: int = 0,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a file modification with optional diff.

        Args:
            agent_name: Name of the agent
            file_path: Path to modified file
            before_content: Content before modification
            after_content: Content after modification
            message: Description of change
            success: Whether modification succeeded
            duration_ms: Duration of modification
            context: Additional context
        """
        # Calculate file metrics and diff
        mod = self._create_file_modification(file_path, before_content, after_content)

        self.log_action(
            agent_name=agent_name,
            action_type=ActionType.FILE_MODIFIED,
            message=message,
            success=success,
            duration_ms=duration_ms,
            file_modifications=[mod],
            context=context,
        )

    def log_fix_applied(
        self,
        agent_name: str,
        file_path: Path,
        before_content: Optional[str] = None,
        after_content: Optional[str] = None,
        fix_type: str = "unknown",
        severity: str = "info",
        success: bool = True,
        duration_ms: int = 0,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a fix applied to a file.

        Args:
            agent_name: Name of the agent
            file_path: Path to file being fixed
            before_content: Original content
            after_content: Fixed content
            fix_type: Type of fix (e.g., 'formatting', 'type-error', 'security-issue')
            severity: Severity of the issue fixed (critical, high, medium, low, info)
            success: Whether fix was applied successfully
            duration_ms: Time taken to apply fix
            context: Additional context
        """
        mod = self._create_file_modification(file_path, before_content, after_content)

        context = context or {}
        context["fix_type"] = fix_type
        context["severity"] = severity

        self.log_action(
            agent_name=agent_name,
            action_type=ActionType.FIX_APPLIED,
            message=f"Applied {fix_type} fix to {file_path.name}",
            success=success,
            duration_ms=duration_ms,
            file_modifications=[mod],
            context=context,
        )

    def log_command_execution(
        self,
        agent_name: str,
        command: str,
        exit_code: int,
        success: bool,
        duration_ms: int,
        message: str = "Command executed",
        error: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a command execution.

        Args:
            agent_name: Name of the agent
            command: Command that was executed
            exit_code: Exit code of the command
            success: Whether command succeeded
            duration_ms: Duration in milliseconds
            message: Description
            error: Error message (if failed)
            context: Additional context
        """
        self.log_action(
            agent_name=agent_name,
            action_type=ActionType.COMMAND_EXECUTED,
            message=message,
            success=success,
            duration_ms=duration_ms,
            command=command,
            exit_code=exit_code,
            error=error,
            context=context,
        )

    def log_finding_reported(
        self,
        agent_name: str,
        finding_type: str,
        severity: str,
        message: str,
        file_path: Optional[Path] = None,
        line_number: Optional[int] = None,
        fixable: bool = False,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a finding reported by an agent.

        Args:
            agent_name: Name of the agent
            finding_type: Type of finding (e.g., 'lint-error', 'type-error')
            severity: Severity level
            message: Finding message
            file_path: File containing the finding
            line_number: Line number (if applicable)
            fixable: Whether the finding is auto-fixable
            context: Additional context
        """
        context = context or {}
        context["finding_type"] = finding_type
        context["severity"] = severity
        context["fixable"] = fixable
        if line_number is not None:
            context["line_number"] = line_number

        self.log_action(
            agent_name=agent_name,
            action_type=ActionType.FINDING_REPORTED,
            message=message,
            success=True,
            duration_ms=0,
            context=context,
        )

    def log_error(
        self,
        agent_name: str,
        error: str,
        message: str = "Agent error",
        duration_ms: int = 0,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an agent error.

        Args:
            agent_name: Name of the agent
            error: Error message
            message: Description
            duration_ms: Duration before error
            context: Additional context
        """
        self.log_action(
            agent_name=agent_name,
            action_type=ActionType.ERROR_OCCURRED,
            message=message,
            success=False,
            duration_ms=duration_ms,
            error=error,
            context=context,
        )

    def query_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Query recent audit entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of audit entries (newest first)
        """
        if not self.log_path.exists():
            return []

        entries = []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        entries.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        self.logger.warning(
                            f"Invalid JSON in agent audit log: {line[:100]}"
                        )
        except Exception as e:
            self.logger.error(f"Failed to read agent audit log: {e}")

        return list(reversed(entries))

    def query_by_agent(self, agent_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Query audit entries for a specific agent.

        Args:
            agent_name: Name of the agent to filter by
            limit: Maximum number of entries to return

        Returns:
            List of audit entries (newest first)
        """
        entries = self.query_recent(limit * 2)
        return [e for e in entries if e.get("agent_name") == agent_name][:limit]

    def query_by_action_type(
        self, action_type: ActionType | str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query audit entries by action type.

        Args:
            action_type: Type of action to filter by
            limit: Maximum number of entries to return

        Returns:
            List of audit entries (newest first)
        """
        type_str = (
            action_type.value
            if isinstance(action_type, ActionType)
            else str(action_type)
        )
        entries = self.query_recent(limit * 2)
        return [e for e in entries if e.get("action_type") == type_str][:limit]

    def query_file_modifications(
        self, file_path: Path, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query modifications to a specific file.

        Args:
            file_path: Path to file to query
            limit: Maximum number of entries to return

        Returns:
            List of audit entries that modified the file
        """
        file_str = str(file_path.resolve())
        entries = self.query_recent(limit * 2)

        results = []
        for entry in entries:
            mods = entry.get("file_modifications", [])
            for mod in mods:
                if str(mod.get("path")) == file_str:
                    results.append(entry)
                    break

        return results[:limit]

    def query_failed_actions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Query failed agent actions.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of failed action entries
        """
        entries = self.query_recent(limit * 2)
        return [e for e in entries if not e.get("success", True)][:limit]

    def query_fixes_applied(
        self, agent_name: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query fixes applied by agents.

        Args:
            agent_name: Optional filter by specific agent
            limit: Maximum number of entries to return

        Returns:
            List of fix entries
        """
        entries = self.query_recent(limit * 2)
        fixes = [
            e for e in entries if e.get("action_type") == ActionType.FIX_APPLIED.value
        ]

        if agent_name:
            fixes = [e for e in fixes if e.get("agent_name") == agent_name]

        return fixes[:limit]

    def _cleanup_old_logs(self) -> None:
        """Remove audit log entries older than retention period.

        Runs periodically to prevent unbounded log file growth.
        Only cleans when file hasn't been modified for 5+ minutes to amortize cost.
        """
        if not self.log_path.exists():
            return

        # Check if cleanup is needed (skip if file was modified recently)
        try:
            mtime = self.log_path.stat().st_mtime
            current_time = time.time()

            # Only run cleanup if file hasn't been modified in the last 5 minutes
            # This prevents running cleanup on every write
            if current_time - mtime < 300:
                return
        except Exception:
            return

        self._cleanup_old_logs_sync()

    def _cleanup_old_logs_sync(self) -> None:
        """Synchronous cleanup of old audit log entries.

        Separated for testability.
        """
        # Calculate cutoff timestamp
        cutoff_time = time.time() - (self.retention_days * 24 * 3600)

        try:
            # Read all entries
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Filter recent entries
            recent_lines = []
            for line in lines:
                try:
                    data = json.loads(line.strip())
                    # Parse ISO 8601 timestamp
                    timestamp_str = data.get("timestamp", "")
                    if timestamp_str:
                        dt = datetime.fromisoformat(timestamp_str)
                        timestamp = dt.timestamp()
                        if timestamp >= cutoff_time:
                            recent_lines.append(line)
                except (json.JSONDecodeError, ValueError, KeyError):
                    # Keep malformed lines (for safety)
                    recent_lines.append(line)

            # Write back recent entries only
            with open(self.log_path, "w", encoding="utf-8") as f:
                f.writelines(recent_lines)

            removed_count = len(lines) - len(recent_lines)
            if removed_count > 0:
                self.logger.debug(
                    f"Cleaned up {removed_count} old audit log entries "
                    f"(kept last {self.retention_days} days)"
                )
        except Exception as e:
            self.logger.error(f"Failed to cleanup old audit logs: {e}")

    @staticmethod
    def _create_file_modification(
        file_path: Path,
        before_content: Optional[str] = None,
        after_content: Optional[str] = None,
    ) -> FileModification:
        """Create a FileModification object with metrics and diff.

        Args:
            file_path: Path to file
            before_content: Content before modification
            after_content: Content after modification

        Returns:
            FileModification object with calculated metrics
        """
        import hashlib

        # Determine action type
        if before_content is None and after_content is not None:
            action = "created"
        elif before_content is not None and after_content is None:
            action = "deleted"
        else:
            action = "modified"

        # Calculate metrics before
        size_before = len(before_content.encode()) if before_content else None
        lines_before = len(before_content.splitlines()) if before_content else None
        hash_before = (
            hashlib.sha256(before_content.encode()).hexdigest()
            if before_content
            else None
        )

        # Calculate metrics after
        size_after = len(after_content.encode()) if after_content else None
        lines_after = len(after_content.splitlines()) if after_content else None
        hash_after = (
            hashlib.sha256(after_content.encode()).hexdigest()
            if after_content
            else None
        )

        # Generate diff
        diff_lines = None
        if before_content is not None and after_content is not None:
            before_lines = before_content.splitlines(keepends=True)
            after_lines = after_content.splitlines(keepends=True)
            diff = list(
                difflib.unified_diff(
                    before_lines,
                    after_lines,
                    fromfile=str(file_path),
                    tofile=str(file_path),
                    lineterm="",
                )
            )

            # Limit diff to first/last 50 lines for very large changes
            if len(diff) > 100:
                diff_lines = diff[:25] + ["... (truncated) ..."] + diff[-25:]
            else:
                diff_lines = diff

        return FileModification(
            path=str(file_path.resolve()),
            action=action,
            size_bytes_before=size_before,
            size_bytes_after=size_after,
            line_count_before=lines_before,
            line_count_after=lines_after,
            diff_lines=diff_lines,
            hash_before=hash_before,
            hash_after=hash_after,
        )


# Global singleton instance
_agent_audit_logger: Optional[AgentAuditLogger] = None


def get_agent_audit_logger() -> AgentAuditLogger:
    """Get global agent audit logger instance.

    Returns:
        Singleton agent audit logger
    """
    global _agent_audit_logger
    if _agent_audit_logger is None:
        _agent_audit_logger = AgentAuditLogger()
    return _agent_audit_logger
