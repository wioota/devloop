"""Agent summary CLI command."""

import asyncio
from typing import Optional

import typer
from rich.console import Console

from dev_agents.core.context_store import context_store
from dev_agents.core.summary_generator import SummaryGenerator
from dev_agents.core.summary_formatter import SummaryFormatter

app = typer.Typer()
console = Console()


# Summary formatting is now handled by SummaryFormatter


@app.command()
def agent_summary(
    scope: str = typer.Argument(
        "recent", help="Summary scope: recent|today|session|all"
    ),
    agent: Optional[str] = typer.Option(None, "--agent", help="Filter by agent name"),
    severity: Optional[str] = typer.Option(
        None, "--severity", help="Filter by severity"
    ),
    category: Optional[str] = typer.Option(
        None, "--category", help="Filter by category"
    ),
):
    """Generate intelligent summary of dev-agent findings."""
    filters = {}
    if agent and agent is not None:
        filters["agent"] = str(agent)
    if severity and severity is not None:
        filters["severity"] = str(severity)
    if category and category is not None:
        filters["category"] = str(category)

    generator = SummaryGenerator(context_store)

    try:
        report = asyncio.run(generator.generate_summary(scope, filters))
        markdown_output = SummaryFormatter.format_markdown(report)
        console.print(markdown_output)
    except Exception as e:
        console.print(f"[red]Error generating summary: {e}[/red]")
        raise typer.Exit(1)
