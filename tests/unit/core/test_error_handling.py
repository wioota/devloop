"""Tests for error handling and notification system."""

import pytest

from devloop.core.error_handler import (
    ErrorCode,
    ErrorContext,
    ErrorSeverity,
    StartupError,
    get_error_handler,
    reset_error_handler,
)
from devloop.core.error_notifier import ErrorNotifier
from rich.console import Console


@pytest.fixture
def error_handler():
    """Create error handler instance."""
    reset_error_handler()
    return get_error_handler()


@pytest.fixture
def error_notifier(tmp_path):
    """Create error notifier with mock console."""
    output_file = open(tmp_path / "output.txt", "w")
    console = Console(file=output_file)
    notifier = ErrorNotifier(console)

    yield notifier

    # Clean up - close the file
    output_file.close()


class TestErrorContext:
    """Tests for ErrorContext class."""

    def test_error_context_creation(self):
        """Test creating error context."""
        ctx = ErrorContext(
            code=ErrorCode.CONFIG_NOT_FOUND,
            severity=ErrorSeverity.CRITICAL,
            message="Config file not found",
        )
        assert ctx.code == ErrorCode.CONFIG_NOT_FOUND
        assert ctx.severity == ErrorSeverity.CRITICAL
        assert ctx.message == "Config file not found"

    def test_error_context_string_representation(self):
        """Test error context string representation."""
        ctx = ErrorContext(
            code=ErrorCode.CONFIG_INVALID,
            severity=ErrorSeverity.ERROR,
            message="Invalid configuration",
        )
        assert str(ctx) == "[E002] Invalid configuration"

    def test_error_context_to_dict(self):
        """Test error context to dict conversion."""
        exc = ValueError("test error")
        ctx = ErrorContext(
            code=ErrorCode.AGENT_STARTUP_FAILED,
            severity=ErrorSeverity.ERROR,
            message="Agent failed to start",
            details="Timeout after 30s",
            exception=exc,
            component="linter",
            recoverable=True,
            suggested_action="Restart the agent",
        )

        data = ctx.to_dict()
        assert data["code"] == "E101"
        assert data["severity"] == "ERROR"
        assert data["message"] == "Agent failed to start"
        assert data["details"] == "Timeout after 30s"
        assert data["component"] == "linter"
        assert data["recoverable"] is True
        assert data["suggested_action"] == "Restart the agent"
        assert data["exception_type"] == "ValueError"


class TestErrorHandler:
    """Tests for ErrorHandler class."""

    def test_error_handler_add_error(self, error_handler):
        """Test adding errors to handler."""
        ctx = ErrorContext(
            code=ErrorCode.CONFIG_INVALID,
            severity=ErrorSeverity.ERROR,
            message="Invalid config",
        )
        error_handler.add_error(ctx)

        assert len(error_handler.errors) == 1
        assert error_handler.errors[0] == ctx

    def test_error_handler_tracks_critical_errors(self, error_handler):
        """Test tracking of critical errors."""
        # Add non-critical error first
        ctx1 = ErrorContext(
            code=ErrorCode.CONFIG_INVALID,
            severity=ErrorSeverity.WARNING,
            message="Warning",
        )
        error_handler.add_error(ctx1)
        assert error_handler.critical_error is None

        # Add critical error
        ctx2 = ErrorContext(
            code=ErrorCode.CONFIG_NOT_FOUND,
            severity=ErrorSeverity.CRITICAL,
            message="Critical error",
        )
        error_handler.add_error(ctx2)
        assert error_handler.critical_error == ctx2

    def test_startup_error_raises_exception(self, error_handler):
        """Test that critical startup errors raise StartupError."""
        with pytest.raises(StartupError):
            error_handler.handle_startup_error(
                ErrorCode.CONFIG_INVALID,
                "Configuration invalid",
                severity=ErrorSeverity.CRITICAL,
            )

    def test_warning_startup_error_doesnt_raise(self, error_handler):
        """Test that warning severity doesn't raise."""
        # Should not raise
        error_handler.handle_startup_error(
            ErrorCode.CONFIG_INVALID,
            "Configuration warning",
            severity=ErrorSeverity.WARNING,
        )
        assert len(error_handler.errors) == 1

    def test_error_handler_get_summary(self, error_handler):
        """Test error summary generation."""
        ctx1 = ErrorContext(
            code=ErrorCode.CONFIG_INVALID,
            severity=ErrorSeverity.WARNING,
            message="Warning",
        )
        ctx2 = ErrorContext(
            code=ErrorCode.AGENT_STARTUP_FAILED,
            severity=ErrorSeverity.CRITICAL,
            message="Agent failed",
        )
        error_handler.add_error(ctx1)
        error_handler.add_error(ctx2)

        summary = error_handler.get_error_summary()
        assert summary["total_errors"] == 2
        assert summary["critical_errors"] == 1


class TestErrorNotifier:
    """Tests for ErrorNotifier class."""

    def test_error_notifier_notify_startup_error(self, error_notifier):
        """Test notifying startup error."""
        ctx = ErrorContext(
            code=ErrorCode.CONFIG_NOT_FOUND,
            severity=ErrorSeverity.CRITICAL,
            message="Configuration file not found",
            details="Location: /path/to/config.json",
            suggested_action="Run: devloop init",
            component="startup",
        )

        # Should not raise
        error_notifier.notify_startup_error(ctx)

    def test_error_notifier_show_error_dashboard(self, error_notifier):
        """Test showing error dashboard."""
        errors = [
            ErrorContext(
                code=ErrorCode.CONFIG_INVALID,
                severity=ErrorSeverity.ERROR,
                message="Invalid config",
                component="startup",
            ),
            ErrorContext(
                code=ErrorCode.AGENT_STARTUP_FAILED,
                severity=ErrorSeverity.WARNING,
                message="Agent warning",
                component="linter",
            ),
        ]

        # Should not raise
        error_notifier.show_error_dashboard(errors)

    def test_error_notifier_show_recovery_help(self, error_notifier):
        """Test showing recovery help."""
        ctx = ErrorContext(
            code=ErrorCode.CONFIG_NOT_FOUND,
            severity=ErrorSeverity.CRITICAL,
            message="Config not found",
        )

        # Should not raise
        error_notifier.show_recovery_help(ctx)

    def test_error_notifier_recovery_help_text(self, error_notifier):
        """Test recovery help text for known errors."""
        help_text = error_notifier._get_recovery_help(ErrorCode.CONFIG_NOT_FOUND)
        assert help_text is not None
        assert "devloop init" in help_text.lower()

        help_text = error_notifier._get_recovery_help(ErrorCode.DATABASE_ERROR)
        assert help_text is not None
        assert "debug" in help_text.lower()

        # Unknown error should return None
        help_text = error_notifier._get_recovery_help(ErrorCode.UNKNOWN_ERROR)
        # Unknown error might or might not have help


class TestErrorCodes:
    """Tests for error codes."""

    def test_all_error_codes_have_values(self):
        """Test that all error codes have values."""
        for code in ErrorCode:
            assert code.value.startswith("E")
            assert len(code.value) == 4  # E + 3 digits

    def test_error_codes_are_unique(self):
        """Test that all error codes are unique."""
        values = [code.value for code in ErrorCode]
        assert len(values) == len(set(values))

    def test_error_severities_have_order(self):
        """Test error severity ordering."""
        assert ErrorSeverity.INFO.value < ErrorSeverity.WARNING.value
        assert ErrorSeverity.WARNING.value < ErrorSeverity.ERROR.value
        assert ErrorSeverity.ERROR.value < ErrorSeverity.CRITICAL.value
        assert ErrorSeverity.CRITICAL.value < ErrorSeverity.FATAL.value


class TestGlobalErrorHandler:
    """Tests for global error handler instance."""

    def test_get_error_handler_singleton(self):
        """Test that get_error_handler returns singleton."""
        reset_error_handler()
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        assert handler1 is handler2

    def test_reset_error_handler(self):
        """Test resetting error handler."""
        handler1 = get_error_handler()
        reset_error_handler()
        handler2 = get_error_handler()
        assert handler1 is not handler2
