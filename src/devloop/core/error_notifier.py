"""Error notification system for displaying errors to users.

Provides:
- Rich console error formatting
- Error dashboards and summaries
- Fail-fast error reporting
"""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from devloop.core.error_handler import ErrorCode, ErrorContext, ErrorSeverity


class ErrorNotifier:
    """Formats and displays errors to users."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize notifier.

        Args:
            console: Rich console instance (creates new if not provided)
        """
        self.console = console or Console()

    def notify_startup_error(self, error_ctx: ErrorContext) -> None:
        """Display a startup error with clear messaging.

        Args:
            error_ctx: Error context
        """
        severity_color = {
            ErrorSeverity.WARNING: "yellow",
            ErrorSeverity.ERROR: "red",
            ErrorSeverity.CRITICAL: "red",
            ErrorSeverity.FATAL: "red",
        }.get(error_ctx.severity, "red")

        # Format error title
        title = f"[{severity_color}]Startup Error ({error_ctx.code.value})[/{severity_color}]"

        # Build error content
        lines = [
            f"[bold]{error_ctx.message}[/bold]",
            "",
            f"Component: {error_ctx.component}",
        ]

        if error_ctx.details:
            lines.append(f"Details: {error_ctx.details}")

        if error_ctx.suggested_action:
            lines.append("")
            lines.append("[yellow]Suggested Action:[/yellow]")
            lines.append(f"  {error_ctx.suggested_action}")

        if error_ctx.exception and str(error_ctx.exception):
            lines.append("")
            lines.append(
                f"[dim]{type(error_ctx.exception).__name__}: {error_ctx.exception}[/dim]"
            )

        content = "\n".join(lines)

        # Display as panel
        panel = Panel(
            content,
            title=title,
            border_style=severity_color,
            padding=(1, 2),
        )
        self.console.print(panel)

    def notify_error(self, error_ctx: ErrorContext, verbose: bool = False) -> None:
        """Display an error.

        Args:
            error_ctx: Error context
            verbose: Show full details
        """
        severity_icon = {
            ErrorSeverity.INFO: "ℹ",
            ErrorSeverity.WARNING: "⚠",
            ErrorSeverity.ERROR: "✗",
            ErrorSeverity.CRITICAL: "✗✗",
            ErrorSeverity.FATAL: "✗✗✗",
        }.get(error_ctx.severity, "?")

        severity_color = {
            ErrorSeverity.INFO: "blue",
            ErrorSeverity.WARNING: "yellow",
            ErrorSeverity.ERROR: "red",
            ErrorSeverity.CRITICAL: "red",
            ErrorSeverity.FATAL: "red",
        }.get(error_ctx.severity, "red")

        # Format output
        msg = (
            f"[{severity_color}]{severity_icon}[/{severity_color}] {error_ctx.message}"
        )

        if verbose and error_ctx.details:
            msg += f"\n  {error_ctx.details}"

        self.console.print(msg)

    def show_error_dashboard(self, errors: list[ErrorContext]) -> None:
        """Display dashboard of all errors.

        Args:
            errors: List of error contexts
        """
        if not errors:
            self.console.print("[green]✓ No errors[/green]")
            return

        # Create summary table
        table = Table(title="Error Summary")
        table.add_column("Code", style="cyan")
        table.add_column("Severity", style="magenta")
        table.add_column("Message")
        table.add_column("Component", style="green")

        severity_colors = {
            ErrorSeverity.INFO: "blue",
            ErrorSeverity.WARNING: "yellow",
            ErrorSeverity.ERROR: "red",
            ErrorSeverity.CRITICAL: "red",
            ErrorSeverity.FATAL: "red",
        }

        for error in errors:
            severity_style = severity_colors.get(error.severity, "white")
            table.add_row(
                error.code.value,
                f"[{severity_style}]{error.severity.name}[/{severity_style}]",
                error.message,
                error.component,
            )

        self.console.print(table)

    def show_recovery_help(self, error_ctx: ErrorContext) -> None:
        """Show help for recovering from an error.

        Args:
            error_ctx: Error context
        """
        help_text = self._get_recovery_help(error_ctx.code)

        if help_text:
            panel = Panel(
                help_text,
                title="[yellow]Recovery Help[/yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
            self.console.print(panel)

    def _get_recovery_help(self, code: ErrorCode) -> Optional[str]:
        """Get recovery help text for error code.

        Args:
            code: Error code

        Returns:
            Help text or None
        """
        help_map = {
            ErrorCode.CONFIG_NOT_FOUND: (
                "The configuration file was not found.\n\n"
                "Run: [cyan]devloop init[/cyan] to create a default configuration."
            ),
            ErrorCode.CONFIG_INVALID: (
                "The configuration file is invalid.\n\n"
                "Check your .devloop/agents.json file for syntax errors.\n"
                "Run: [cyan]devloop validate-config[/cyan] to check for issues."
            ),
            ErrorCode.INSUFFICIENT_DISK_SPACE: (
                "Your disk is running out of space.\n\n"
                "Free up some disk space and try again."
            ),
            ErrorCode.PERMISSION_DENIED: (
                "Permission denied accessing a file or directory.\n\n"
                "Check file permissions and try running with appropriate privileges."
            ),
            ErrorCode.DATABASE_ERROR: (
                "Database operation failed.\n\n"
                "Try running: [cyan]devloop debug --repair-db[/cyan] to repair the database."
            ),
            ErrorCode.SANDBOX_INITIALIZATION_FAILED: (
                "Sandbox initialization failed.\n\n"
                "This usually means a required tool is not installed.\n"
                "Run: [cyan]devloop validate-setup[/cyan] to check your environment."
            ),
        }

        return help_map.get(code)
