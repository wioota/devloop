"""Metrics commands for value analysis, dashboards, and ROI reporting."""

from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from devloop.core.telemetry import get_telemetry_logger
from devloop.metrics.dora import DORAMetricsAnalyzer

app = typer.Typer(help="View and analyze DevLoop metrics, value, and ROI")
console = Console()


def _parse_period(period: str) -> tuple[datetime, datetime]:
    """Parse period string into start and end datetime.

    Args:
        period: Period string like '24h', '7d', '30d', 'week', 'month', etc.

    Returns:
        Tuple of (start_datetime, end_datetime) in UTC
    """
    now = datetime.now(UTC)

    period_lower = period.lower().strip()

    # Parse duration-based periods
    if period_lower.endswith("h"):
        hours = int(period_lower[:-1])
        start = now - timedelta(hours=hours)
    elif period_lower.endswith("d"):
        days = int(period_lower[:-1])
        start = now - timedelta(days=days)
    elif period_lower.endswith("w"):
        weeks = int(period_lower[:-1])
        start = now - timedelta(weeks=weeks)
    elif period_lower.endswith("m"):
        months = int(period_lower[:-1])
        # Approximate: 30 days per month
        start = now - timedelta(days=months * 30)
    elif period_lower == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period_lower == "week":
        start = now - timedelta(days=7)
    elif period_lower == "month":
        start = now - timedelta(days=30)
    elif period_lower == "all":
        # Very old date (essentially "all time")
        start = now - timedelta(days=3650)  # 10 years
    else:
        # Default: last 24 hours
        start = now - timedelta(hours=24)

    return start, now


def _filter_events_by_period(
    events: list[dict], start: datetime, end: datetime
) -> list[dict]:
    """Filter events to those within the time period.

    Args:
        events: List of events with timestamp field
        start: Start datetime
        end: End datetime

    Returns:
        Filtered list of events
    """
    # Ensure start and end are timezone-aware
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)

    filtered = []
    for event in events:
        timestamp_str = event.get("timestamp", "")
        try:
            # Parse ISO format timestamp
            # Handle both 'Z' and '+00:00' formats
            if timestamp_str.endswith("Z"):
                timestamp_str = timestamp_str[:-1] + "+00:00"

            event_time = datetime.fromisoformat(timestamp_str)

            # Ensure event time is timezone-aware for comparison
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=UTC)

            if start <= event_time <= end:
                filtered.append(event)
        except (ValueError, AttributeError, TypeError):
            # Skip events with invalid timestamps
            continue

    return filtered


def _calculate_time_saved(events: list[dict]) -> dict[str, any]:
    """Calculate time saved from value events.

    Args:
        events: List of filtered events

    Returns:
        Dictionary with time metrics
    """
    total_ms = 0
    count = 0

    for event in events:
        if event.get("event_type") == "value_event":
            duration = event.get("duration_ms")
            if duration:
                total_ms += duration
                count += 1

    total_seconds = total_ms / 1000
    total_minutes = total_seconds / 60
    total_hours = total_minutes / 60

    return {
        "total_ms": total_ms,
        "total_seconds": total_seconds,
        "total_minutes": total_minutes,
        "total_hours": total_hours,
        "count": count,
    }


def _calculate_ci_metrics(events: list[dict]) -> dict[str, any]:
    """Calculate CI-related metrics.

    Args:
        events: List of filtered events

    Returns:
        Dictionary with CI metrics
    """
    ci_roundtrips_prevented = 0
    pre_commit_passed = 0
    pre_commit_failed = 0
    pre_push_passed = 0
    pre_push_failed = 0

    for event in events:
        event_type = event.get("event_type")

        if event_type == "ci_roundtrip_prevented":
            ci_roundtrips_prevented += 1
        elif event_type == "pre_commit_check":
            if event.get("success"):
                pre_commit_passed += 1
            else:
                pre_commit_failed += 1
        elif event_type == "pre_push_check":
            if event.get("success"):
                pre_push_passed += 1
            else:
                pre_push_failed += 1

    total_commits = pre_commit_passed + pre_commit_failed
    total_pushes = pre_push_passed + pre_push_failed

    return {
        "ci_roundtrips_prevented": ci_roundtrips_prevented,
        "pre_commit_passed": pre_commit_passed,
        "pre_commit_failed": pre_commit_failed,
        "pre_commit_total": total_commits,
        "pre_commit_pass_rate": (
            (pre_commit_passed / total_commits * 100) if total_commits > 0 else 0
        ),
        "pre_push_passed": pre_push_passed,
        "pre_push_failed": pre_push_failed,
        "pre_push_total": total_pushes,
        "pre_push_pass_rate": (
            (pre_push_passed / total_pushes * 100) if total_pushes > 0 else 0
        ),
    }


def _calculate_agent_metrics(events: list[dict]) -> dict[str, dict]:
    """Calculate per-agent metrics.

    Args:
        events: List of filtered events

    Returns:
        Dictionary of agent name -> metrics
    """
    agent_stats: dict[str, dict] = {}

    for event in events:
        agent = event.get("agent")
        if not agent:
            continue

        if agent not in agent_stats:
            agent_stats[agent] = {
                "executions": 0,
                "findings": 0,
                "total_duration_ms": 0,
                "success_count": 0,
                "failure_count": 0,
                "severity_counts": {},
            }

        stats = agent_stats[agent]
        stats["executions"] += 1

        # Count findings
        findings = event.get("findings", 0)
        if findings:
            stats["findings"] += findings

        # Track duration
        duration = event.get("duration_ms")
        if duration:
            stats["total_duration_ms"] += duration

        # Track success/failure
        success = event.get("success")
        if success is True:
            stats["success_count"] += 1
        elif success is False:
            stats["failure_count"] += 1

        # Track severity levels
        severities = event.get("severity_levels", [])
        for severity in severities:
            stats["severity_counts"][severity] = (
                stats["severity_counts"].get(severity, 0) + 1
            )

    # Calculate derived metrics
    for agent, stats in agent_stats.items():
        total = stats["success_count"] + stats["failure_count"]
        stats["success_rate"] = (
            (stats["success_count"] / total * 100) if total > 0 else 0
        )
        stats["avg_duration_ms"] = (
            stats["total_duration_ms"] / stats["executions"]
            if stats["executions"] > 0
            else 0
        )

    return agent_stats


@app.command()
def value(
    period: str = typer.Option(
        "24h",
        "--period",
        "-p",
        help="Period to analyze (24h, 7d, 30d, today, week, month, all)",
    ),
    log_file: Optional[Path] = typer.Option(
        None,
        "--log-file",
        help="Path to events.jsonl file (defaults to .devloop/events.jsonl)",
    ),
):
    """Show value metrics - time saved, CI roundtrips prevented, issues caught."""
    if log_file:
        telemetry = get_telemetry_logger(log_file)
    else:
        telemetry = get_telemetry_logger()

    # Get all events and filter by period
    all_events = telemetry._get_events_streaming()
    start, end = _parse_period(period)
    events = _filter_events_by_period(all_events, start, end)

    if not events:
        console.print(f"[yellow]No events in period '{period}'[/yellow]")
        return

    # Calculate metrics
    time_saved = _calculate_time_saved(events)
    ci_metrics = _calculate_ci_metrics(events)
    agent_metrics = _calculate_agent_metrics(events)

    # Build dashboard
    dashboard_lines = []
    dashboard_lines.append(
        f"[bold cyan]DevLoop Value Dashboard ({period})[/bold cyan]\n"
    )

    # Time saved section
    dashboard_lines.append("[bold green]⏱️  Time Saved[/bold green]")
    dashboard_lines.append(f"  {time_saved['total_hours']:.1f} hours")
    dashboard_lines.append(f"  {time_saved['total_minutes']:.0f} minutes")
    dashboard_lines.append(f"  {time_saved['count']} value events\n")

    # CI metrics section
    dashboard_lines.append("[bold green]🔄 CI Improvements[/bold green]")
    dashboard_lines.append(
        f"  CI Roundtrips Prevented: {ci_metrics['ci_roundtrips_prevented']}"
    )
    dashboard_lines.append(
        f"  Pre-Commit Success Rate: {ci_metrics['pre_commit_pass_rate']:.1f}% "
        f"({ci_metrics['pre_commit_passed']}/{ci_metrics['pre_commit_total']})"
    )
    dashboard_lines.append(
        f"  Pre-Push Success Rate: {ci_metrics['pre_push_pass_rate']:.1f}% "
        f"({ci_metrics['pre_push_passed']}/{ci_metrics['pre_push_total']})"
    )
    dashboard_lines.append("")

    # Issues caught section
    total_findings = sum(stats["findings"] for stats in agent_metrics.values())
    dashboard_lines.append("[bold green]🐛 Issues Caught[/bold green]")
    dashboard_lines.append(f"  Total: {total_findings}")

    # Most valuable agents
    if agent_metrics:
        sorted_agents = sorted(
            agent_metrics.items(),
            key=lambda x: x[1]["findings"],
            reverse=True,
        )
        dashboard_lines.append("\n[bold green]⭐ Most Valuable Agents[/bold green]")
        for agent, stats in sorted_agents[:5]:
            console.print(f"  {agent}: {stats['findings']} findings")

    # Print dashboard
    dashboard_text = "\n".join(dashboard_lines)
    console.print(Panel(dashboard_text, border_style="cyan", padding=(1, 2)))


@app.command()
def agents(
    period: str = typer.Option(
        "24h",
        "--period",
        "-p",
        help="Period to analyze (24h, 7d, 30d, today, week, month, all)",
    ),
    sort_by: str = typer.Option(
        "findings",
        "--sort",
        "-s",
        help="Sort by: findings, duration, success-rate, executions",
    ),
    log_file: Optional[Path] = typer.Option(
        None,
        "--log-file",
        help="Path to events.jsonl file (defaults to .devloop/events.jsonl)",
    ),
):
    """Show agent performance metrics - execution counts, success rates, findings."""
    if log_file:
        telemetry = get_telemetry_logger(log_file)
    else:
        telemetry = get_telemetry_logger()

    # Get all events and filter by period
    all_events = telemetry._get_events_streaming()
    start, end = _parse_period(period)
    events = _filter_events_by_period(all_events, start, end)

    if not events:
        console.print(f"[yellow]No events in period '{period}'[/yellow]")
        return

    # Calculate agent metrics
    agent_metrics = _calculate_agent_metrics(events)

    if not agent_metrics:
        console.print("[yellow]No agent executions in this period[/yellow]")
        return

    # Sort agents
    sort_key = {
        "findings": lambda x: x[1]["findings"],
        "duration": lambda x: x[1]["total_duration_ms"],
        "success-rate": lambda x: x[1]["success_rate"],
        "executions": lambda x: x[1]["executions"],
    }.get(sort_by, lambda x: x[1]["findings"])

    sorted_agents = sorted(agent_metrics.items(), key=sort_key, reverse=True)

    # Create table
    table = Table(title=f"Agent Performance ({period})")
    table.add_column("Agent", style="cyan")
    table.add_column("Executions", justify="right")
    table.add_column("Findings", justify="right")
    table.add_column("Success Rate", justify="right")
    table.add_column("Avg Duration", justify="right")

    for agent, stats in sorted_agents:
        success_rate_str = f"{stats['success_rate']:.1f}%"
        avg_duration_str = f"{stats['avg_duration_ms']:.0f}ms"

        table.add_row(
            agent,
            str(stats["executions"]),
            str(stats["findings"]),
            success_rate_str,
            avg_duration_str,
        )

    console.print(table)

    # Print summary
    console.print("\n[cyan]Summary:[/cyan]")
    console.print(f"Total agents: {len(agent_metrics)}")
    total_executions = sum(s["executions"] for s in agent_metrics.values())
    console.print(f"Total executions: {total_executions}")


@app.command()
def compare(
    before: str = typer.Option(..., "--before", help="Start date (YYYY-MM-DD)"),
    after: str = typer.Option(..., "--after", help="End date (YYYY-MM-DD)"),
    log_file: Optional[Path] = typer.Option(
        None,
        "--log-file",
        help="Path to events.jsonl file (defaults to .devloop/events.jsonl)",
    ),
):
    """Compare metrics between two periods (before/after DevLoop adoption)."""
    if log_file:
        telemetry = get_telemetry_logger(log_file)
    else:
        telemetry = get_telemetry_logger()

    # Parse dates
    try:
        before_date = datetime.fromisoformat(before).replace(tzinfo=UTC)
        after_date = datetime.fromisoformat(after).replace(tzinfo=UTC)
    except ValueError:
        console.print("[red]Invalid date format. Use YYYY-MM-DD[/red]")
        raise typer.Exit(code=1)

    if before_date >= after_date:
        console.print("[red]Before date must be before after date[/red]")
        raise typer.Exit(code=1)

    # Get all events
    all_events = telemetry._get_events_streaming()

    # Split events into before and after
    before_end = before_date + timedelta(days=30)
    after_start = after_date
    after_end = after_date + timedelta(days=30)

    before_events = _filter_events_by_period(all_events, before_date, before_end)
    after_events = _filter_events_by_period(all_events, after_start, after_end)

    if not before_events or not after_events:
        console.print("[yellow]Insufficient data in one or both periods[/yellow]")
        return

    # Calculate metrics for both periods
    before_ci = _calculate_ci_metrics(before_events)
    after_ci = _calculate_ci_metrics(after_events)

    before_time = _calculate_time_saved(before_events)
    after_time = _calculate_time_saved(after_events)

    # Create comparison table
    table = Table(
        title=f"Metrics Comparison: {before_date.date()} vs {after_date.date()}"
    )
    table.add_column("Metric", style="cyan")
    table.add_column("Before", style="yellow")
    table.add_column("After", style="green")
    table.add_column("Change", style="white")

    # Pre-commit success rate
    before_rate = before_ci["pre_commit_pass_rate"]
    after_rate = after_ci["pre_commit_pass_rate"]
    change = after_rate - before_rate
    change_indicator = "↑" if change > 0 else "↓" if change < 0 else "→"
    table.add_row(
        "Pre-Commit Success Rate",
        f"{before_rate:.1f}%",
        f"{after_rate:.1f}%",
        f"{change_indicator} {change:+.1f}pp",
    )

    # CI roundtrips prevented
    before_roundtrips = before_ci["ci_roundtrips_prevented"]
    after_roundtrips = after_ci["ci_roundtrips_prevented"]
    change = after_roundtrips - before_roundtrips
    table.add_row(
        "CI Roundtrips Prevented",
        str(before_roundtrips),
        str(after_roundtrips),
        f"↑ +{change}" if change >= 0 else f"↓ {change}",
    )

    # Time saved
    before_hours = before_time["total_hours"]
    after_hours = after_time["total_hours"]
    change = after_hours - before_hours
    table.add_row(
        "Time Saved (hours)",
        f"{before_hours:.1f}",
        f"{after_hours:.1f}",
        f"↑ +{change:.1f}" if change >= 0 else f"↓ {change:.1f}",
    )

    console.print(table)


@app.command(name="dora")
def dora_metrics(
    period: int = typer.Option(
        30,
        "--period",
        "-p",
        help="Number of days to analyze",
    ),
    branch: str = typer.Option(
        "main",
        "--branch",
        "-b",
        help="Git branch to analyze",
    ),
    repo_path: Path = typer.Option(
        Path("."),
        "--repo",
        help="Path to git repository",
    ),
):
    """Analyze DORA metrics from git history.

    DORA (DevOps Research and Assessment) metrics:
    - Deployment Frequency: How often deployments occur
    - Lead Time for Changes: Time from commit to deployment
    - Change Failure Rate: % of deployments causing issues
    - Time to Restore: Recovery time from incidents
    """
    try:
        analyzer = DORAMetricsAnalyzer(repo_path=repo_path)
        metrics = analyzer.analyze(period_days=period, branch=branch)
    except Exception as e:
        console.print(f"[red]Error analyzing DORA metrics: {e}[/red]")
        raise typer.Exit(code=1)

    # Display results
    console.print(
        Panel(
            f"[bold cyan]DORA Metrics Analysis - {metrics.period}[/bold cyan]\n"
            f"[dim]Period: {metrics.date_range[0].date()} to {metrics.date_range[1].date()}[/dim]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # Deployment Frequency
    console.print("\n[bold green]📊 Deployment Frequency[/bold green]")
    freq_table = Table()
    freq_table.add_column("Metric", style="cyan")
    freq_table.add_column("Value", style="green")
    freq_table.add_row(
        "Deployments",
        str(metrics.deployment_frequency.deployments_count),
    )
    freq_table.add_row(
        "Frequency",
        f"{metrics.deployment_frequency.deployment_frequency:.2f} per day",
    )
    console.print(freq_table)

    # Lead Time for Changes
    if metrics.lead_time:
        console.print("\n[bold green]⏱️  Lead Time for Changes[/bold green]")
        lead_table = Table()
        lead_table.add_column("Metric", style="cyan")
        lead_table.add_column("Value", style="green")
        lead_table.add_row(
            "Average",
            f"{metrics.lead_time.avg_lead_time_hours:.1f} hours",
        )
        lead_table.add_row(
            "Median",
            f"{metrics.lead_time.median_lead_time_hours:.1f} hours",
        )
        lead_table.add_row(
            "Min",
            f"{metrics.lead_time.min_lead_time_hours:.1f} hours",
        )
        lead_table.add_row(
            "Max",
            f"{metrics.lead_time.max_lead_time_hours:.1f} hours",
        )
        lead_table.add_row(
            "Commits Analyzed",
            str(metrics.lead_time.commits_analyzed),
        )
        console.print(lead_table)

    # Change Failure Rate
    if metrics.change_failure_rate:
        console.print("\n[bold green]🔴 Change Failure Rate[/bold green]")
        cfr_table = Table()
        cfr_table.add_column("Metric", style="cyan")
        cfr_table.add_column("Value", style="green")
        cfr_table.add_row(
            "Failure Rate",
            f"{metrics.change_failure_rate.failure_rate_percent:.1f}%",
        )
        cfr_table.add_row(
            "Failed Deployments",
            str(metrics.change_failure_rate.failed_deployments),
        )
        cfr_table.add_row(
            "Total Deployments",
            str(metrics.change_failure_rate.total_deployments),
        )
        console.print(cfr_table)


@app.command()
def dora_compare(
    before_days: int = typer.Option(
        30,
        "--before-days",
        help="Days to go back for 'before' period",
    ),
    after_days: int = typer.Option(
        30,
        "--after-days",
        help="Days to go back for 'after' period (from before start)",
    ),
    branch: str = typer.Option(
        "main",
        "--branch",
        "-b",
        help="Git branch to analyze",
    ),
    repo_path: Path = typer.Option(
        Path("."),
        "--repo",
        help="Path to git repository",
    ),
):
    """Compare DORA metrics between two periods.

    Useful for measuring improvement from DevLoop adoption.
    """
    try:
        analyzer = DORAMetricsAnalyzer(repo_path=repo_path)

        # Calculate date ranges
        now = datetime.now(UTC)
        after_end = now
        after_start = after_end - timedelta(days=after_days)
        before_end = after_start
        before_start = before_end - timedelta(days=before_days)

        before_metrics, after_metrics = analyzer.compare_periods(
            before_start,
            before_end,
            after_start,
            after_end,
            branch=branch,
        )
    except Exception as e:
        console.print(f"[red]Error comparing DORA metrics: {e}[/red]")
        raise typer.Exit(code=1)

    # Display comparison
    console.print(
        Panel(
            "[bold cyan]DORA Metrics Comparison[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # Deployment Frequency Comparison
    console.print("\n[bold green]📊 Deployment Frequency[/bold green]")
    freq_table = Table()
    freq_table.add_column("Metric", style="cyan")
    freq_table.add_column("Before", style="yellow")
    freq_table.add_column("After", style="green")
    freq_table.add_column("Change", style="white")

    before_freq = before_metrics.deployment_frequency.deployment_frequency
    after_freq = after_metrics.deployment_frequency.deployment_frequency
    change = after_freq - before_freq
    change_pct = (change / before_freq * 100) if before_freq > 0 else 0

    freq_table.add_row(
        "Deployment Frequency",
        f"{before_freq:.2f}/day",
        f"{after_freq:.2f}/day",
        f"↑ +{change_pct:.0f}%" if change >= 0 else f"↓ {change_pct:.0f}%",
    )
    console.print(freq_table)

    # Lead Time Comparison
    if before_metrics.lead_time and after_metrics.lead_time:
        console.print("\n[bold green]⏱️  Lead Time for Changes[/bold green]")
        lead_table = Table()
        lead_table.add_column("Metric", style="cyan")
        lead_table.add_column("Before", style="yellow")
        lead_table.add_column("After", style="green")
        lead_table.add_column("Change", style="white")

        before_lead = before_metrics.lead_time.avg_lead_time_hours
        after_lead = after_metrics.lead_time.avg_lead_time_hours
        change = before_lead - after_lead  # Lower is better
        change_pct = (change / before_lead * 100) if before_lead > 0 else 0

        lead_table.add_row(
            "Average Lead Time",
            f"{before_lead:.1f}h",
            f"{after_lead:.1f}h",
            f"↓ -{change_pct:.0f}%" if change >= 0 else f"↑ +{change_pct:.0f}%",
        )
        console.print(lead_table)


@app.command()
def dashboard(
    period: str = typer.Option(
        "24h",
        "--period",
        "-p",
        help="Period to analyze (24h, 7d, 30d, today, week, month, all)",
    ),
    log_file: Optional[Path] = typer.Option(
        None,
        "--log-file",
        help="Path to events.jsonl file (defaults to .devloop/events.jsonl)",
    ),
    refresh: int = typer.Option(
        0,
        "--refresh",
        "-r",
        help="Auto-refresh interval in seconds (0 = no refresh)",
    ),
):
    """Interactive dashboard showing real-time DevLoop metrics."""
    import time

    if log_file:
        telemetry = get_telemetry_logger(log_file)
    else:
        telemetry = get_telemetry_logger()

    def show_dashboard():
        """Display the dashboard."""
        console.clear()

        # Get all events and filter by period
        all_events = telemetry._get_events_streaming()
        start, end = _parse_period(period)
        events = _filter_events_by_period(all_events, start, end)

        if not events:
            console.print(f"[yellow]No events in period '{period}'[/yellow]")
            return

        # Calculate metrics
        time_saved = _calculate_time_saved(events)
        ci_metrics = _calculate_ci_metrics(events)
        agent_metrics = _calculate_agent_metrics(events)

        # Header
        console.print(
            Panel(
                f"[bold cyan]DevLoop Metrics Dashboard - {period}[/bold cyan]\n"
                f"[dim]{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}[/dim]",
                border_style="cyan",
                padding=(0, 2),
            )
        )

        # Key metrics row
        metrics_table = Table(show_header=False, box=None, padding=(0, 2))
        metrics_table.add_row(
            "[bold green]⏱️  Time Saved[/bold green]\n"
            f"{time_saved['total_hours']:.1f}h",
            "[bold green]🔄 CI Roundtrips[/bold green]\n"
            f"{ci_metrics['ci_roundtrips_prevented']}",
            "[bold green]✓ Commit Success[/bold green]\n"
            f"{ci_metrics['pre_commit_pass_rate']:.0f}%",
            "[bold green]🐛 Issues Caught[/bold green]\n"
            f"{sum(s['findings'] for s in agent_metrics.values())}",
        )
        console.print(metrics_table)

        # Agent performance
        if agent_metrics:
            console.print("\n[bold cyan]Agent Performance[/bold cyan]")
            agent_table = Table()
            agent_table.add_column("Agent", style="cyan")
            agent_table.add_column("Runs", justify="right")
            agent_table.add_column("Success", justify="right")
            agent_table.add_column("Avg Time", justify="right")

            sorted_agents = sorted(
                agent_metrics.items(),
                key=lambda x: x[1]["findings"],
                reverse=True,
            )
            for agent, stats in sorted_agents[:10]:
                agent_table.add_row(
                    agent,
                    str(stats["executions"]),
                    f"{stats['success_rate']:.0f}%",
                    f"{stats['avg_duration_ms']:.0f}ms",
                )

            console.print(agent_table)

        # Footer
        if refresh > 0:
            console.print(
                f"\n[dim]Auto-refreshing every {refresh}s (Ctrl+C to stop)[/dim]"
            )

    # Show dashboard initially
    show_dashboard()

    # Auto-refresh if requested
    if refresh > 0:
        try:
            while True:
                time.sleep(refresh)
                show_dashboard()
        except KeyboardInterrupt:
            console.print("\n[yellow]Dashboard stopped[/yellow]")
