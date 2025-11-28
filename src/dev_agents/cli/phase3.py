"""Phase 3: Learning & Optimization Commands."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..core.custom_agent import (
    AgentBuilder,
    CustomAgentStore,
    CustomAgentType,
    get_agent_template,
)
from ..core.learning import LearningSystem
from ..core.performance import PerformanceMonitor
from ..core.feedback import FeedbackStore, FeedbackAPI

app = typer.Typer(help="Phase 3: Learning & Optimization")
console = Console()


# Custom Agent Management Commands


@app.command()
def custom_list(
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """List all custom agents."""

    async def _run():
        if project_dir is None:
            project_dir = Path.cwd()

        storage_path = project_dir / ".claude" / "custom_agents"
        store = CustomAgentStore(storage_path)

        agents = await store.get_all_agents()

        if not agents:
            console.print("[yellow]No custom agents found[/yellow]")
            return

        table = Table(title="Custom Agents")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Type", style="blue")
        table.add_column("Enabled", style="yellow")
        table.add_column("Triggers", style="magenta")

        for agent in agents:
            trigger_str = ", ".join(agent.triggers) if agent.triggers else "—"
            table.add_row(
                agent.id[:8] + "...",
                agent.name,
                agent.agent_type.value,
                "✓" if agent.enabled else "✗",
                trigger_str,
            )

        console.print(table)

    asyncio.run(_run())


@app.command()
def custom_create(
    name: str = typer.Argument(..., help="Name of the custom agent"),
    agent_type: str = typer.Argument(
        ...,
        help="Type: pattern_matcher, file_processor, output_analyzer, composite",
    ),
    description: Optional[str] = typer.Option(None, help="Description"),
    triggers: Optional[str] = typer.Option(
        None, help="Comma-separated list of event triggers"
    ),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """Create a new custom agent."""

    async def _run():
        if project_dir is None:
            project_dir = Path.cwd()

        # Validate agent type
        try:
            agent_type_enum = CustomAgentType(agent_type)
        except ValueError:
            console.print(
                f"[red]Invalid agent type: {agent_type}[/red]"
            )
            console.print(
                "Valid types: pattern_matcher, file_processor, output_analyzer, composite"
            )
            return

        # Parse triggers
        trigger_list = []
        if triggers:
            trigger_list = [t.strip() for t in triggers.split(",")]

        # Build agent
        builder = AgentBuilder(name, agent_type_enum)
        if description:
            builder.with_description(description)
        if trigger_list:
            builder.with_triggers(*trigger_list)

        config = builder.build()

        # Save agent
        storage_path = project_dir / ".claude" / "custom_agents"
        store = CustomAgentStore(storage_path)
        await store.save_agent(config)

        console.print(f"[green]✓[/green] Custom agent created: {name}")
        console.print(f"[dim]ID: {config.id}[/dim]")

    asyncio.run(_run())


@app.command()
def custom_show(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """Show details of a custom agent."""

    async def _run():
        if project_dir is None:
            project_dir = Path.cwd()

        storage_path = project_dir / ".claude" / "custom_agents"
        store = CustomAgentStore(storage_path)

        agent = await store.get_agent(agent_id)

        if not agent:
            console.print(f"[red]Agent not found: {agent_id}[/red]")
            return

        console.print(f"\n[bold]{agent.name}[/bold]")
        console.print(f"[dim]ID: {agent.id}[/dim]")
        console.print(f"[dim]Type: {agent.agent_type.value}[/dim]")
        console.print(f"[dim]Enabled: {'Yes' if agent.enabled else 'No'}[/dim]")
        console.print(f"[dim]Description: {agent.description}[/dim]")

        if agent.triggers:
            console.print(f"[dim]Triggers: {', '.join(agent.triggers)}[/dim]")

        if agent.config:
            console.print("[dim]Configuration:[/dim]")
            for key, value in agent.config.items():
                console.print(f"  {key}: {value}")

    asyncio.run(_run())


@app.command()
def custom_delete(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """Delete a custom agent."""

    async def _run():
        if project_dir is None:
            project_dir = Path.cwd()

        storage_path = project_dir / ".claude" / "custom_agents"
        store = CustomAgentStore(storage_path)

        if not force:
            agent = await store.get_agent(agent_id)
            if not agent:
                console.print(f"[red]Agent not found: {agent_id}[/red]")
                return
            console.print(f"Delete custom agent: {agent.name}?")
            if not typer.confirm("Continue?"):
                return

        deleted = await store.delete_agent(agent_id)

        if deleted:
            console.print("[green]✓[/green] Custom agent deleted")
        else:
            console.print(f"[red]Agent not found: {agent_id}[/red]")

    asyncio.run(_run())


# Learning System Commands


@app.command()
def learning_insights(
    agent: Optional[str] = typer.Option(None, help="Filter by agent name"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """Show learning insights for agents."""

    async def _run():
        if project_dir is None:
            project_dir = Path.cwd()

        storage_path = project_dir / ".claude" / "learning"
        learning = LearningSystem(storage_path)

        if agent:
            # Show specific agent insights
            insights = await learning.get_insights_for_agent(agent)

            if not insights:
                console.print(f"[yellow]No insights found for {agent}[/yellow]")
                return

            console.print(f"\n[bold]Insights for {agent}[/bold]")
            for insight_type, data in insights.items():
                console.print(f"\n[cyan]{insight_type}[/cyan]")
                console.print(f"  Count: {data['count']}")
                console.print(f"  Last observed: {data['last_observed']}")

        else:
            # Show summary
            console.print(
                "[yellow]Use --agent to specify which agent insights to view[/yellow]"
            )

    asyncio.run(_run())


@app.command()
def learning_recommendations(
    agent: str = typer.Argument(..., help="Agent name"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """Show recommendations for an agent based on learning."""

    async def _run():
        if project_dir is None:
            project_dir = Path.cwd()

        storage_path = project_dir / ".claude" / "learning"
        learning = LearningSystem(storage_path)

        recommendations = await learning.get_recommendations(agent)

        if not recommendations:
            console.print(f"[yellow]No recommendations available for {agent}[/yellow]")
            return

        table = Table(title=f"Recommendations for {agent}")
        table.add_column("Pattern", style="cyan")
        table.add_column("Action", style="green")
        table.add_column("Confidence", style="yellow")
        table.add_column("Frequency", style="blue")

        for rec in recommendations:
            confidence_pct = f"{rec['confidence'] * 100:.0f}%"
            table.add_row(
                rec["pattern"],
                rec["action"][:30],
                confidence_pct,
                str(rec["frequency"]),
            )

        console.print(table)

    asyncio.run(_run())


@app.command()
def learning_patterns(
    agent: str = typer.Argument(..., help="Agent name"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """Show learned behavior patterns for an agent."""

    async def _run():
        if project_dir is None:
            project_dir = Path.cwd()

        storage_path = project_dir / ".claude" / "learning"
        learning = LearningSystem(storage_path)

        patterns = await learning.get_patterns_for_agent(agent)

        if not patterns:
            console.print(f"[yellow]No patterns learned for {agent}[/yellow]")
            return

        for pattern in patterns:
            console.print(f"\n[bold]{pattern.pattern_name}[/bold]")
            console.print(f"[dim]{pattern.description}[/dim]")
            console.print(f"Confidence: {pattern.confidence:.1%}")
            console.print(f"Frequency: {pattern.frequency}")
            console.print(f"Recommended: {pattern.recommended_action}")

    asyncio.run(_run())


# Performance & Feedback Commands


@app.command()
def perf_summary(
    agent: Optional[str] = typer.Option(None, help="Filter by agent"),
    hours: int = typer.Option(24, help="Time range in hours"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """Show performance summary."""

    async def _run():
        if project_dir is None:
            project_dir = Path.cwd()

        storage_path = project_dir / ".claude" / "performance"
        monitor = PerformanceMonitor(storage_path)

        if agent:
            summary = await monitor.get_performance_summary(agent, hours)
            console.print(f"\n[bold]Performance Summary: {agent}[/bold]")
            console.print(f"Time range: {hours} hours")
            console.print(f"Total operations: {summary['total_operations']}")
            console.print(f"Success rate: {summary['success_rate']}%")
            console.print(f"Average duration: {summary['average_duration']}s")
            console.print(f"Average CPU: {summary['average_cpu_usage']}%")
            console.print(f"Average memory: {summary['average_memory_usage_mb']}MB")
        else:
            health = await monitor.get_system_health()
            console.print("\n[bold]System Health[/bold]")
            console.print(f"[dim]CPU: {health['process']['cpu_percent']}%[/dim]")
            console.print(
                f"[dim]Memory: {health['process']['memory_mb']:.1f}MB[/dim]"
            )

    asyncio.run(_run())


@app.command()
def feedback_submit(
    agent: str = typer.Argument(..., help="Agent name"),
    feedback_type: str = typer.Argument(
        ..., help="thumbs_up, thumbs_down, rating, comment"
    ),
    value: str = typer.Argument(..., help="Feedback value"),
    comment: Optional[str] = typer.Option(None, help="Optional comment"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """Submit feedback for an agent."""

    async def _run():
        if project_dir is None:
            project_dir = Path.cwd()

        from ..core.feedback import FeedbackType

        storage_path = project_dir / ".claude" / "feedback"
        feedback_store = FeedbackStore(storage_path)
        feedback_api = FeedbackAPI(feedback_store)

        # Parse feedback type
        try:
            fb_type = FeedbackType(feedback_type)
        except ValueError:
            console.print(f"[red]Invalid feedback type: {feedback_type}[/red]")
            return

        # Parse value
        if fb_type in (FeedbackType.THUMBS_UP, FeedbackType.THUMBS_DOWN):
            parsed_value = value.lower() in ("true", "1", "yes")
        elif fb_type == FeedbackType.RATING:
            try:
                parsed_value = int(value)
                if not (1 <= parsed_value <= 5):
                    raise ValueError()
            except ValueError:
                console.print("[red]Rating must be 1-5[/red]")
                return
        else:
            parsed_value = value

        feedback_id = await feedback_api.submit_feedback(
            agent_name=agent,
            event_type="manual",
            feedback_type=fb_type,
            value=parsed_value,
            comment=comment,
        )

        console.print(f"[green]✓[/green] Feedback submitted (ID: {feedback_id})")

    asyncio.run(_run())


@app.command()
def feedback_list(
    agent: str = typer.Argument(..., help="Agent name"),
    limit: int = typer.Option(10, help="Number of recent items"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """List feedback for an agent."""

    async def _run():
        if project_dir is None:
            project_dir = Path.cwd()

        storage_path = project_dir / ".claude" / "feedback"
        feedback_store = FeedbackStore(storage_path)

        feedback_items = await feedback_store.get_feedback_for_agent(agent, limit)

        if not feedback_items:
            console.print(f"[yellow]No feedback found for {agent}[/yellow]")
            return

        table = Table(title=f"Feedback for {agent}")
        table.add_column("Type", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Comment", style="yellow")

        for item in feedback_items:
            table.add_row(
                item.feedback_type.value,
                str(item.value),
                item.comment or "—",
            )

        console.print(table)

    asyncio.run(_run())


if __name__ == "__main__":
    app()
