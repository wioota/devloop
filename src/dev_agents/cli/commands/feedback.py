"""CLI commands for agent feedback and performance monitoring."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from dev_agents.core.feedback import FeedbackAPI, FeedbackStore, FeedbackType
from dev_agents.core.performance import PerformanceMonitor

app = typer.Typer(help="Feedback and performance monitoring")
console = Console()


def get_feedback_api(project_dir: Path = None) -> FeedbackAPI:
    """Get feedback API instance for the project."""
    if project_dir is None:
        project_dir = Path.cwd()

    storage_path = project_dir / ".dev-agents" / "feedback"
    feedback_store = FeedbackStore(storage_path)
    return FeedbackAPI(feedback_store)


def get_performance_monitor(project_dir: Path = None) -> PerformanceMonitor:
    """Get performance monitor instance for the project."""
    if project_dir is None:
        project_dir = Path.cwd()

    storage_path = project_dir / ".dev-agents" / "performance"
    return PerformanceMonitor(storage_path)


@app.command()
def list_feedback(
    agent: Optional[str] = typer.Option(None, help="Filter by agent name"),
    limit: int = typer.Option(20, help="Maximum number of feedback items to show"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """List recent feedback for agents."""

    async def _run():
        feedback_api = get_feedback_api(project_dir)

        if agent:
            # Get feedback for specific agent
            feedback_items = await feedback_api.feedback_store.get_feedback_for_agent(
                agent
            )
        else:
            # Get all feedback
            feedback_items = await feedback_api.feedback_store.get_all_feedback()

        feedback_items = feedback_items[-limit:]  # Get last N items

        if not feedback_items:
            console.print("[yellow]No feedback found[/yellow]")
            return

        table = Table(title="Agent Feedback")
        table.add_column("Timestamp", style="cyan")
        table.add_column("Agent", style="green")
        table.add_column("Type", style="blue")
        table.add_column("Message", style="yellow")

        for item in feedback_items:
            table.add_row(
                item.timestamp.isoformat(),
                item.agent_name,
                item.feedback_type,
                item.message[:50] + "..." if len(item.message) > 50 else item.message,
            )

        console.print(table)

    asyncio.run(_run())


@app.command()
def submit_feedback(
    agent: str = typer.Option(..., help="Agent name"),
    feedback_type: str = typer.Option(
        "suggestion", help="Feedback type: suggestion|bug|improvement|other"
    ),
    message: str = typer.Argument(..., help="Feedback message"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """Submit feedback for an agent."""

    async def _run():
        feedback_api = get_feedback_api(project_dir)

        await feedback_api.submit_feedback(agent, feedback_type, message)
        console.print(f"[green]✓[/green] Feedback submitted for [cyan]{agent}[/cyan]")

    asyncio.run(_run())


@app.command()
def performance_status(
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """Show agent performance metrics."""

    async def _run():
        monitor = get_performance_monitor(project_dir)

        metrics = await monitor.get_performance_summary()

        table = Table(title="Agent Performance Metrics")
        table.add_column("Agent", style="cyan")
        table.add_column("Success Rate", style="green")
        table.add_column("Avg Duration (ms)", style="blue")
        table.add_column("Total Runs", style="yellow")

        for agent_name, data in metrics.items():
            success_rate = (
                f"{data.get('success_rate', 0):.1%}"
                if data.get("success_rate") is not None
                else "N/A"
            )
            avg_duration = (
                f"{data.get('avg_duration', 0):.2f}"
                if data.get("avg_duration") is not None
                else "N/A"
            )
            total_runs = data.get("total_runs", 0)

            table.add_row(agent_name, success_rate, avg_duration, str(total_runs))

        console.print(table)

    asyncio.run(_run())


@app.command()
def performance_detail(
    agent: str = typer.Option(..., help="Agent name"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """Show detailed performance metrics for an agent."""

    async def _run():
        monitor = get_performance_monitor(project_dir)

        metrics = await monitor.get_agent_metrics(agent)

        if not metrics:
            console.print(f"[yellow]No metrics found for agent: {agent}[/yellow]")
            return

        console.print(f"\n[bold]Performance Metrics for {agent}[/bold]")
        console.print(f"  Success Rate: {metrics.get('success_rate', 0):.1%}")
        console.print(f"  Average Duration: {metrics.get('avg_duration', 0):.2f}ms")
        console.print(f"  Total Runs: {metrics.get('total_runs', 0)}")
        console.print(f"  Last Run: {metrics.get('last_run', 'Never')}")

    asyncio.run(_run())
