"""CLI commands for Phase 3 features: feedback and performance analytics."""

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from ..core.feedback import FeedbackAPI, FeedbackStore, FeedbackType
from ..core.performance import PerformanceMonitor

app = typer.Typer(help="Phase 3: Learning & Optimization Commands")
console = Console()


def get_feedback_api(project_dir: Path = None) -> FeedbackAPI:
    """Get feedback API instance for the project."""
    if project_dir is None:
        project_dir = Path.cwd()

    storage_path = project_dir / ".claude" / "feedback"
    feedback_store = FeedbackStore(storage_path)
    return FeedbackAPI(feedback_store)


def get_performance_monitor(project_dir: Path = None) -> PerformanceMonitor:
    """Get performance monitor instance for the project."""
    if project_dir is None:
        project_dir = Path.cwd()

    storage_path = project_dir / ".claude" / "performance"
    return PerformanceMonitor(storage_path)


@app.command()
def feedback_list(
    agent: Optional[str] = typer.Option(None, help="Filter by agent name"),
    limit: int = typer.Option(20, help="Maximum number of feedback items to show"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory")
):
    """List recent feedback for agents."""
    async def _run():
        feedback_api = get_feedback_api(project_dir)

        if agent:
            # Get feedback for specific agent
            feedback_items = await feedback_api.feedback_store.get_feedback_for_agent(agent, limit)
            if not feedback_items:
                console.print(f"[yellow]No feedback found for agent '{agent}'[/yellow]")
                return

            table = Table(title=f"Feedback for {agent}")
            table.add_column("Type", style="cyan")
            table.add_column("Value", style="green")
            table.add_column("Comment", style="yellow")
            table.add_column("Time", style="blue")

            for item in feedback_items:
                table.add_row(
                    item.feedback_type.value,
                    str(item.value),
                    item.comment or "",
                    f"{item.timestamp:.1f}"
                )
        else:
            # Show summary for all agents
            # This would require scanning all feedback - for now show message
            console.print("[yellow]Use --agent to specify which agent feedback to view[/yellow]")
            return

        console.print(table)

    asyncio.run(_run())


@app.command()
def feedback_submit(
    agent: str = typer.Argument(..., help="Agent name"),
    feedback_type: str = typer.Argument(..., help="Type of feedback (thumbs_up, thumbs_down, rating, comment, dismiss)"),
    value: str = typer.Argument(..., help="Feedback value (boolean for thumbs, number for rating, text for comment)"),
    comment: Optional[str] = typer.Option(None, help="Optional comment"),
    event_type: str = typer.Option("manual", help="Event type that triggered feedback"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory")
):
    """Submit feedback for an agent."""
    async def _run():
        feedback_api = get_feedback_api(project_dir)

        # Parse feedback type
        try:
            fb_type = FeedbackType(feedback_type)
        except ValueError:
            console.print(f"[red]Invalid feedback type: {feedback_type}[/red]")
            console.print("Valid types: thumbs_up, thumbs_down, rating, comment, dismiss")
            return

        # Parse value based on type
        if fb_type in (FeedbackType.THUMBS_UP, FeedbackType.THUMBS_DOWN):
            if value.lower() in ('true', '1', 'yes'):
                parsed_value = True
            elif value.lower() in ('false', '0', 'no'):
                parsed_value = False
            else:
                console.print(f"[red]Thumbs feedback must be boolean (true/false)[/red]")
                return
        elif fb_type == FeedbackType.RATING:
            try:
                parsed_value = int(value)
                if not (1 <= parsed_value <= 5):
                    raise ValueError()
            except ValueError:
                console.print("[red]Rating must be an integer between 1 and 5[/red]")
                return
        elif fb_type == FeedbackType.COMMENT:
            parsed_value = value
        elif fb_type == FeedbackType.DISMISS:
            parsed_value = None
        else:
            parsed_value = value

        feedback_id = await feedback_api.submit_feedback(
            agent_name=agent,
            event_type=event_type,
            feedback_type=fb_type,
            value=parsed_value,
            comment=comment
        )

        console.print(f"[green]Feedback submitted![/green] ID: {feedback_id}")

    asyncio.run(_run())


@app.command()
def performance_status(
    agent: Optional[str] = typer.Option(None, help="Filter by agent name"),
    hours: int = typer.Option(24, help="Time range in hours"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory")
):
    """Show performance analytics."""
    async def _run():
        performance_monitor = get_performance_monitor(project_dir)

        if agent:
            # Show agent-specific performance
            summary = await performance_monitor.get_performance_summary(agent, hours)
            feedback_api = get_feedback_api(project_dir)
            insights = await feedback_api.get_agent_insights(agent)

            console.print(f"\n[bold]Performance Summary for {agent}[/bold]")
            console.print(f"Time range: Last {hours} hours")
            console.print(f"Total executions: {summary['total_operations']}")
            console.print(f"Success rate: {summary['success_rate']}%")
            console.print(f"Average duration: {summary['average_duration']}s")
            console.print(f"Average CPU usage: {summary['average_cpu_usage']}%")
            console.print(f"Average memory usage: {summary['average_memory_usage_mb']} MB")

            console.print(f"\n[bold]Feedback Insights[/bold]")
            console.print(f"Total feedback: {insights['performance']['feedback_count']}")
            console.print(f"Thumbs up rate: {insights['performance']['thumbs_up_rate']}%")
            console.print(f"Average rating: {insights['performance']['average_rating']}/5")

        else:
            # Show system health
            health = await performance_monitor.get_system_health()

            console.print(f"\n[bold]System Health[/bold]")
            console.print(f"Timestamp: {health['timestamp']}")

            console.print(f"\n[bold]Process Metrics[/bold]")
            console.print(f"CPU Usage: {health['process']['cpu_percent']}%")
            console.print(f"Memory Usage: {health['process']['memory_mb']:.1f} MB ({health['process']['memory_percent']}%)")

            console.print(f"\n[bold]System Metrics[/bold]")
            console.print(f"System CPU: {health['system']['cpu_percent']}%")
            console.print(f"System Memory: {health['system']['memory_used_gb']:.1f} GB / {health['system']['memory_total_gb']:.1f} GB ({health['system']['memory_percent']}%)")
            console.print(f"Disk Usage: {health['system']['disk_used_gb']:.1f} GB / {health['system']['disk_total_gb']:.1f} GB ({health['system']['disk_percent']}%)")

    asyncio.run(_run())


@app.command()
def performance_trends(
    hours: int = typer.Option(24, help="Time range in hours"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory")
):
    """Show performance trends over time."""
    async def _run():
        performance_monitor = get_performance_monitor(project_dir)
        trends = await performance_monitor.get_resource_trends(hours)

        if not trends:
            console.print(f"[yellow]No performance data found for the last {hours} hours[/yellow]")
            return

        table = Table(title=f"Performance Trends (Last {hours} hours)")
        table.add_column("Time", style="blue")
        table.add_column("Operations", style="cyan", justify="right")
        table.add_column("Avg CPU %", style="green", justify="right")
        table.add_column("Avg Memory MB", style="yellow", justify="right")

        for trend in trends:
            import datetime
            time_str = datetime.datetime.fromtimestamp(trend["timestamp"]).strftime("%H:%M")
            table.add_row(
                time_str,
                str(trend["operations"]),
                f"{trend['avg_cpu']:.1f}",
                f"{trend['avg_memory_mb']:.1f}"
            )

        console.print(table)

    asyncio.run(_run())


@app.command()
def agent_insights(
    project_dir: Optional[Path] = typer.Option(None, help="Project directory")
):
    """Show insights for all agents."""
    async def _run():
        feedback_api = get_feedback_api(project_dir)

        # We need to scan for all agents that have feedback
        # For now, let's check common agent names
        common_agents = ["linter", "formatter", "test-runner", "git-commit-assistant"]

        table = Table(title="Agent Insights")
        table.add_column("Agent", style="cyan")
        table.add_column("Executions", style="blue", justify="right")
        table.add_column("Success %", style="green", justify="right")
        table.add_column("Avg Duration", style="yellow", justify="right")
        table.add_column("Feedback", style="magenta", justify="right")
        table.add_column("Rating", style="red", justify="right")

        for agent_name in common_agents:
            try:
                insights = await feedback_api.get_agent_insights(agent_name)
                perf = insights["performance"]

                table.add_row(
                    agent_name,
                    str(perf["total_executions"]),
                    f"{perf['success_rate']}%",
                    f"{perf['average_duration']:.2f}s",
                    str(perf["feedback_count"]),
                    f"{perf['average_rating']:.1f}/5" if perf["average_rating"] > 0 else "-"
                )
            except Exception:
                # Agent might not exist or have no data
                continue

        if table.row_count == 0:
            console.print("[yellow]No agent performance data found[/yellow]")
            console.print("Run some agents first to collect performance data")
        else:
            console.print(table)

    asyncio.run(_run())
