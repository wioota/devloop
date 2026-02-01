"""Agent insights CLI command.

Displays detected patterns from the self-improvement agent with filtering
and formatting options.
"""

from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from devloop.core.pattern_detector import DetectedPattern, get_pattern_detector

app = typer.Typer(help="View agent insights and detected patterns")
console = Console()


def _format_threads(threads: list[str], max_display: int = 3) -> str:
    """Format thread list for display."""
    if not threads:
        return "-"
    if len(threads) <= max_display:
        return ", ".join(threads)
    return f"{', '.join(threads[:max_display])} (+{len(threads) - max_display} more)"


def _format_evidence(evidence: dict) -> str:
    """Format evidence dictionary for display."""
    if not evidence:
        return "-"
    parts = []
    for key, value in evidence.items():
        if key in ("examples", "affected_threads"):
            continue  # Skip these, shown separately
        if isinstance(value, list):
            parts.append(f"{key}: {len(value)}")
        else:
            parts.append(f"{key}: {value}")
    return ", ".join(parts) if parts else "-"


def _severity_style(severity: str) -> str:
    """Get rich style for severity level."""
    styles = {
        "error": "red bold",
        "warning": "yellow",
        "medium": "yellow",
        "info": "blue",
    }
    return styles.get(severity.lower(), "white")


def _print_table(patterns: list[DetectedPattern]) -> None:
    """Print patterns as a rich table."""
    table = Table(title="Detected Patterns")
    table.add_column("Pattern", style="cyan", no_wrap=True)
    table.add_column("Severity", no_wrap=True)
    table.add_column("Confidence", justify="right")
    table.add_column("Message")
    table.add_column("Threads")

    for pattern in patterns:
        severity_styled = f"[{_severity_style(pattern.severity)}]{pattern.severity}[/]"
        confidence_str = f"{pattern.confidence:.0%}"
        threads_str = _format_threads(pattern.affected_threads)

        table.add_row(
            pattern.pattern_name,
            severity_styled,
            confidence_str,
            pattern.message,
            threads_str,
        )

    console.print(table)


def _print_detailed(patterns: list[DetectedPattern]) -> None:
    """Print patterns with full details."""
    for i, pattern in enumerate(patterns):
        if i > 0:
            console.print()

        severity_styled = f"[{_severity_style(pattern.severity)}]{pattern.severity}[/]"
        console.print(f"[bold cyan]{pattern.pattern_name}[/] ({severity_styled})")
        console.print(f"  Message: {pattern.message}")
        console.print(f"  Confidence: {pattern.confidence:.0%}")

        if pattern.affected_threads:
            console.print(f"  Threads: {_format_threads(pattern.affected_threads, 5)}")

        if pattern.evidence:
            console.print(f"  Evidence: {_format_evidence(pattern.evidence)}")

        if pattern.recommendation:
            console.print(f"  [green]Recommendation:[/] {pattern.recommendation}")


def _print_json(patterns: list[DetectedPattern]) -> None:
    """Print patterns as JSON."""
    data = [pattern.to_dict() for pattern in patterns]
    console.print(json.dumps(data, indent=2, default=str))


@app.command("list")
def list_patterns(
    severity: Optional[str] = typer.Option(
        None, "--severity", "-s", help="Filter by severity (info, warning, error)"
    ),
    pattern: Optional[str] = typer.Option(
        None, "--pattern", "-p", help="Filter by pattern name"
    ),
    thread: Optional[str] = typer.Option(
        None, "--thread", "-t", help="Filter by thread ID"
    ),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum patterns to show"),
    min_confidence: float = typer.Option(
        0.0, "--min-confidence", help="Minimum confidence (0.0 to 1.0)"
    ),
    output_format: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, detailed, json"
    ),
) -> None:
    """List detected patterns from agent activity."""
    try:
        detector = get_pattern_detector()

        # Get patterns based on filters
        if thread:
            patterns = detector.get_patterns_for_thread(thread)
        elif pattern:
            patterns = detector.get_patterns_by_type(pattern)
        else:
            patterns = detector.get_recent_patterns(limit=limit, severity=severity)

        # Apply additional filters
        if min_confidence > 0:
            patterns = [p for p in patterns if p.confidence >= min_confidence]

        if severity and not thread and not pattern:
            # Already filtered by get_recent_patterns
            pass
        elif severity:
            patterns = [p for p in patterns if p.severity.lower() == severity.lower()]

        # Limit results
        patterns = patterns[:limit]

        if not patterns:
            console.print("[yellow]No patterns detected yet.[/]")
            console.print("Run 'devloop insights detect' to analyze activity.")
            return

        # Output based on format
        if output_format == "json":
            _print_json(patterns)
        elif output_format == "detailed":
            _print_detailed(patterns)
        else:
            _print_table(patterns)

        console.print(f"\n[dim]Showing {len(patterns)} pattern(s)[/]")

    except Exception as e:
        console.print(f"[red]Error listing patterns: {e}[/]")
        raise typer.Exit(1)


@app.command("detect")
def detect_patterns(
    hours: int = typer.Option(24, "--hours", "-h", help="Time window in hours"),
    min_occurrences: int = typer.Option(
        2, "--min-occurrences", help="Minimum occurrences to trigger pattern"
    ),
    output_format: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, detailed, json"
    ),
    save: bool = typer.Option(True, "--save/--no-save", help="Save detected patterns"),
) -> None:
    """Detect patterns in recent activity."""
    try:
        detector = get_pattern_detector()

        console.print(
            f"[dim]Analyzing activity from last {hours} hours "
            f"(min {min_occurrences} occurrences)...[/]"
        )

        patterns = detector.detect_patterns(
            time_window_hours=hours,
            min_occurrences=min_occurrences,
            save_results=save,
        )

        if not patterns:
            console.print("[green]No patterns detected.[/]")
            return

        # Output based on format
        if output_format == "json":
            _print_json(patterns)
        elif output_format == "detailed":
            _print_detailed(patterns)
        else:
            _print_table(patterns)

        console.print(f"\n[dim]Detected {len(patterns)} pattern(s)[/]")
        if save:
            console.print("[dim]Patterns saved to ~/.devloop/patterns.jsonl[/]")

    except Exception as e:
        console.print(f"[red]Error detecting patterns: {e}[/]")
        raise typer.Exit(1)


@app.command("summary")
def pattern_summary(
    hours: int = typer.Option(24, "--hours", "-h", help="Time window in hours"),
) -> None:
    """Show summary of pattern activity."""
    try:
        detector = get_pattern_detector()
        patterns = detector.get_recent_patterns(limit=200)

        if not patterns:
            console.print("[yellow]No patterns recorded yet.[/]")
            return

        # Group by pattern name
        by_name: dict[str, list[DetectedPattern]] = {}
        for p in patterns:
            by_name.setdefault(p.pattern_name, []).append(p)

        # Group by severity
        by_severity: dict[str, int] = {}
        for p in patterns:
            by_severity[p.severity] = by_severity.get(p.severity, 0) + 1

        console.print("[bold]Pattern Summary[/]")
        console.print()

        # Severity breakdown
        console.print("[cyan]By Severity:[/]")
        for sev in ["error", "warning", "medium", "info"]:
            if sev in by_severity:
                style = _severity_style(sev)
                console.print(f"  [{style}]{sev}:[/] {by_severity[sev]}")

        console.print()

        # Pattern breakdown
        console.print("[cyan]By Pattern Type:[/]")
        for name, items in sorted(by_name.items(), key=lambda x: -len(x[1])):
            avg_confidence = sum(p.confidence for p in items) / len(items)
            console.print(f"  {name}: {len(items)} (avg conf: {avg_confidence:.0%})")

        console.print()
        console.print(f"[dim]Total: {len(patterns)} pattern(s) recorded[/]")

    except Exception as e:
        console.print(f"[red]Error generating summary: {e}[/]")
        raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """View agent insights and detected patterns.

    The insights command helps you understand patterns in your development
    workflow by analyzing CLI actions and agent activity.
    """
    if ctx.invoked_subcommand is None:
        # Default to list command with explicit defaults
        ctx.invoke(
            list_patterns,
            severity=None,
            pattern=None,
            thread=None,
            limit=50,
            min_confidence=0.0,
            output_format="table",
        )
