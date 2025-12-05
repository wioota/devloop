"""Audit logging for sandbox execution.

Provides immutable audit trail of all sandboxed command execution for security
and compliance purposes.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from devloop.security.sandbox import SandboxResult


@dataclass
class AuditEntry:
    """Single audit log entry for sandbox execution.

    Attributes:
        timestamp: ISO 8601 timestamp with timezone
        sandbox_mode: Sandbox implementation used
        command: Command executed (first element only for security)
        args_count: Number of arguments (for size tracking)
        cwd: Working directory
        exit_code: Process exit code
        duration_ms: Execution duration in milliseconds
        memory_peak_mb: Peak memory usage
        cpu_usage_percent: CPU usage percentage
        blocked: Whether command was blocked by policy
        block_reason: Reason for blocking (if applicable)
        timeout: Whether execution timed out
        error: Error message (if applicable)
    """

    timestamp: str
    sandbox_mode: str
    command: str
    args_count: int
    cwd: str
    exit_code: int
    duration_ms: int
    memory_peak_mb: float
    cpu_usage_percent: float
    blocked: bool
    block_reason: Optional[str] = None
    timeout: bool = False
    error: Optional[str] = None

    def to_json(self) -> str:
        """Convert to JSON string for logging.

        Returns:
            JSON string representation
        """
        return json.dumps(asdict(self), ensure_ascii=False)


class SandboxAuditLogger:
    """Audit logger for sandbox execution.

    Maintains immutable append-only log of all sandbox operations for:
    - Security audits
    - Incident investigation
    - Compliance tracking
    - Performance analysis
    """

    def __init__(self, log_path: Optional[Path] = None):
        """Initialize audit logger.

        Args:
            log_path: Path to audit log file (defaults to .devloop/security-audit.log)
        """
        if log_path is None:
            log_path = Path(".devloop/security-audit.log")

        self.log_path = log_path
        self.logger = logging.getLogger("sandbox.audit")

        # Ensure log directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_execution(
        self,
        sandbox_mode: str,
        cmd: List[str],
        cwd: Path,
        result: SandboxResult,
        blocked: bool = False,
        block_reason: Optional[str] = None,
        timeout: bool = False,
        error: Optional[str] = None,
    ) -> None:
        """Log sandbox execution to audit log.

        Args:
            sandbox_mode: Sandbox implementation used
            cmd: Command that was executed
            cwd: Working directory
            result: Execution result
            blocked: Whether command was blocked
            block_reason: Reason for blocking
            timeout: Whether execution timed out
            error: Error message if execution failed
        """
        # Create audit entry
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            sandbox_mode=sandbox_mode,
            command=cmd[0] if cmd else "unknown",  # Only log executable name
            args_count=len(cmd) - 1 if len(cmd) > 1 else 0,
            cwd=str(cwd),
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            memory_peak_mb=result.memory_peak_mb,
            cpu_usage_percent=result.cpu_usage_percent,
            blocked=blocked,
            block_reason=block_reason,
            timeout=timeout,
            error=error,
        )

        # Write to audit log (append-only)
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(entry.to_json() + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write audit log: {e}")

    def log_blocked_command(
        self,
        sandbox_mode: str,
        cmd: List[str],
        cwd: Path,
        reason: str,
    ) -> None:
        """Log blocked command attempt.

        Args:
            sandbox_mode: Sandbox implementation
            cmd: Command that was blocked
            cwd: Working directory
            reason: Reason for blocking
        """
        # Create mock result for blocked command
        result = SandboxResult(
            stdout="",
            stderr="",
            exit_code=-1,
            duration_ms=0,
        )

        self.log_execution(
            sandbox_mode=sandbox_mode,
            cmd=cmd,
            cwd=cwd,
            result=result,
            blocked=True,
            block_reason=reason,
        )

    def log_timeout(
        self,
        sandbox_mode: str,
        cmd: List[str],
        cwd: Path,
        duration_ms: int,
    ) -> None:
        """Log command timeout.

        Args:
            sandbox_mode: Sandbox implementation
            cmd: Command that timed out
            cwd: Working directory
            duration_ms: Time before timeout
        """
        result = SandboxResult(
            stdout="",
            stderr="Execution timed out",
            exit_code=-1,
            duration_ms=duration_ms,
        )

        self.log_execution(
            sandbox_mode=sandbox_mode,
            cmd=cmd,
            cwd=cwd,
            result=result,
            timeout=True,
            error="Execution exceeded timeout",
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
                # Read all lines and take last N
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        entries.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        self.logger.warning(f"Invalid JSON in audit log: {line[:100]}")
        except Exception as e:
            self.logger.error(f"Failed to read audit log: {e}")

        # Return newest first
        return list(reversed(entries))

    def query_blocked(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Query recent blocked command attempts.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of blocked command entries
        """
        entries = self.query_recent(limit * 2)  # Get more to filter
        return [e for e in entries if e.get("blocked", False)][:limit]

    def query_errors(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Query recent execution errors.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of error entries
        """
        entries = self.query_recent(limit * 2)
        return [e for e in entries if e.get("error") or e.get("exit_code", 0) != 0][:limit]


# Global singleton instance
_audit_logger: Optional[SandboxAuditLogger] = None


def get_audit_logger() -> SandboxAuditLogger:
    """Get global audit logger instance.

    Returns:
        Singleton audit logger
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = SandboxAuditLogger()
    return _audit_logger
