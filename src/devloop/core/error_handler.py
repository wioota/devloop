"""Error handling and notification system for DevLoop.

Provides:
- Error codes for different failure categories
- Error context and severity levels
- Error notification mechanisms
- Fail-fast detection for critical errors
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""

    INFO = 0  # Informational, not an error
    WARNING = 1  # Can continue but with degraded functionality
    ERROR = 2  # Operation failed but system can continue
    CRITICAL = 3  # Daemon cannot continue, must stop
    FATAL = 4  # Unrecoverable system state


class ErrorCode(Enum):
    """Error codes for different failure categories."""

    # Configuration errors
    CONFIG_NOT_FOUND = "E001"
    CONFIG_INVALID = "E002"
    CONFIG_MIGRATION_FAILED = "E003"
    CONFIG_PERMISSION_DENIED = "E004"

    # Agent errors
    AGENT_STARTUP_FAILED = "E101"
    AGENT_EXECUTION_ERROR = "E102"
    AGENT_RESOURCE_EXHAUSTED = "E103"
    AGENT_TIMEOUT = "E104"

    # System errors
    INSUFFICIENT_DISK_SPACE = "E201"
    PERMISSION_DENIED = "E202"
    PATH_NOT_FOUND = "E203"
    INVALID_PATH = "E204"

    # Storage errors
    DATABASE_ERROR = "E301"
    EVENT_STORE_FAILED = "E302"
    CONTEXT_STORE_FAILED = "E303"
    FILE_LOCK_TIMEOUT = "E304"

    # Collector errors
    FILESYSTEM_WATCH_FAILED = "E401"
    GIT_INTEGRATION_FAILED = "E402"
    SYSTEM_MONITOR_FAILED = "E403"

    # Sandbox/Security errors
    SANDBOX_INITIALIZATION_FAILED = "E501"
    SECURITY_VIOLATION = "E502"

    # Health/Recovery errors
    DAEMON_HEALTH_CHECK_FAILED = "E601"
    TRANSACTION_RECOVERY_FAILED = "E602"
    CHECKSUM_VERIFICATION_FAILED = "E603"

    # Integration errors
    AMP_INTEGRATION_FAILED = "E701"
    MARKETPLACE_UNAVAILABLE = "E702"

    # Unknown error
    UNKNOWN_ERROR = "E999"


@dataclass
class ErrorContext:
    """Context information for an error."""

    code: ErrorCode
    severity: ErrorSeverity
    message: str
    details: Optional[str] = None
    exception: Optional[Exception] = None
    component: str = "unknown"
    recoverable: bool = False
    suggested_action: Optional[str] = None

    def __str__(self) -> str:
        """Format error for display."""
        return f"[{self.code.value}] {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "code": self.code.value,
            "severity": self.severity.name,
            "message": self.message,
            "details": self.details,
            "component": self.component,
            "recoverable": self.recoverable,
            "suggested_action": self.suggested_action,
            "exception_type": (
                type(self.exception).__name__ if self.exception else None
            ),
        }


class ErrorHandler:
    """Central error handling and notification system."""

    def __init__(self):
        """Initialize error handler."""
        self.errors: list[ErrorContext] = []
        self.critical_error: Optional[ErrorContext] = None

    def add_error(self, error_ctx: ErrorContext) -> None:
        """Register an error.

        Args:
            error_ctx: Error context information
        """
        self.errors.append(error_ctx)

        # Track critical errors
        if error_ctx.severity in (ErrorSeverity.CRITICAL, ErrorSeverity.FATAL):
            if not self.critical_error:
                self.critical_error = error_ctx

        # Log the error
        log_level = {
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
            ErrorSeverity.FATAL: logging.CRITICAL,
        }[error_ctx.severity]

        logger.log(
            log_level,
            f"{error_ctx}: {error_ctx.details or error_ctx.exception or ''}",
            exc_info=error_ctx.exception if error_ctx.exception else False,
        )

    def handle_startup_error(
        self,
        code: ErrorCode,
        message: str,
        exception: Optional[Exception] = None,
        details: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.CRITICAL,
    ) -> None:
        """Handle a startup error with fail-fast behavior.

        Args:
            code: Error code
            message: Human-readable message
            exception: Original exception if applicable
            details: Additional details
            severity: Error severity (default: CRITICAL)
        """
        error_ctx = ErrorContext(
            code=code,
            severity=severity,
            message=message,
            details=details,
            exception=exception,
            component="startup",
            recoverable=False,
        )

        self.add_error(error_ctx)

        # For critical startup errors, fail fast
        if severity in (ErrorSeverity.CRITICAL, ErrorSeverity.FATAL):
            raise StartupError(error_ctx)

    def has_critical_error(self) -> bool:
        """Check if a critical error has occurred."""
        return self.critical_error is not None

    def get_critical_error(self) -> Optional[ErrorContext]:
        """Get the first critical error if any."""
        return self.critical_error

    def get_error_summary(self) -> dict[str, Any]:
        """Get summary of all errors."""
        return {
            "total_errors": len(self.errors),
            "critical_errors": sum(
                1
                for e in self.errors
                if e.severity in (ErrorSeverity.CRITICAL, ErrorSeverity.FATAL)
            ),
            "errors": [e.to_dict() for e in self.errors[-10:]],  # Last 10 errors
        }


class StartupError(Exception):
    """Exception raised when startup fails with critical error."""

    def __init__(self, error_ctx: ErrorContext):
        """Initialize with error context.

        Args:
            error_ctx: Error context information
        """
        self.error_ctx = error_ctx
        super().__init__(str(error_ctx))


class DaemonError(Exception):
    """Exception raised when daemon experiences critical error."""

    def __init__(self, error_ctx: ErrorContext):
        """Initialize with error context.

        Args:
            error_ctx: Error context information
        """
        self.error_ctx = error_ctx
        super().__init__(str(error_ctx))


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def reset_error_handler() -> None:
    """Reset global error handler (mainly for testing)."""
    global _error_handler
    _error_handler = None
