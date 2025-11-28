"""CLI commands for custom agent management."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from dev_agents.core.custom_agent import (
    AgentBuilder,
    CustomAgentStore,
    CustomAgentType,
    get_agent_template,
)

app = typer.Typer(help="Manage custom agents")
console = Console()


@app.command()
def list_agents(
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """List all custom agents."""

    async def _run():
        if project_dir is None:
            project_dir = Path.cwd()

        storage_path = project_dir / ".dev-agents" / "custom_agents"
        store = CustomAgentStore(storage_path)

        agents = await store.get_all_agents()

        if not agents:
            console.print("[yellow]No custom agents found[/yellow]")
            return

        table = Table(title="Custom Agents")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Type", style="blue")
        table.add_column("Status", style="yellow")

        for agent_id, agent in agents.items():
            table.add_row(
                agent_id, agent.name, agent.agent_type, "Active"
            )

        console.print(table)

    asyncio.run(_run())


@app.command()
def create(
    name: str = typer.Argument(..., help="Agent name"),
    agent_type: str = typer.Option("detector", help="Agent type"),
    description: str = typer.Option("", help="Agent description"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """Create a new custom agent."""

    async def _run():
        if project_dir is None:
            project_dir = Path.cwd()

        # Get template
        template = get_agent_template(agent_type)
        if not template:
            console.print(f"[red]Unknown agent type: {agent_type}[/red]")
            raise typer.Exit(1)

        # Build custom agent
        builder = AgentBuilder()
        agent = builder.build(
            name=name,
            agent_type=agent_type,
            description=description or template.get("description", ""),
            config=template.get("config", {}),
        )

        # Store it
        storage_path = project_dir / ".dev-agents" / "custom_agents"
        store = CustomAgentStore(storage_path)
        await store.save_agent(agent)

        console.print(f"[green]✓[/green] Created custom agent: [cyan]{name}[/cyan]")
        console.print(f"  ID: {agent.id}")
        console.print(f"  Type: {agent_type}")

    asyncio.run(_run())


@app.command()
def delete(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    project_dir: Optional[Path] = typer.Option(None, help="Project directory"),
):
    """Delete a custom agent."""

    async def _run():
        if project_dir is None:
            project_dir = Path.cwd()

        storage_path = project_dir / ".dev-agents" / "custom_agents"
        store = CustomAgentStore(storage_path)

        await store.delete_agent(agent_id)
        console.print(f"[green]✓[/green] Deleted agent: [cyan]{agent_id}[/cyan]")

    asyncio.run(_run())


@app.command()
def templates():
    """Show available agent templates."""
    templates = {
        "detector": {
            "description": "Pattern detection agent",
            "triggers": ["file:modified"],
        },
        "analyzer": {
            "description": "Code analysis agent",
            "triggers": ["file:modified"],
        },
        "generator": {
            "description": "Code generation agent",
            "triggers": ["command:generate"],
        },
    }

    table = Table(title="Available Agent Templates")
    table.add_column("Type", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Default Triggers", style="yellow")

    for template_type, template_data in templates.items():
        triggers = ", ".join(template_data["triggers"])
        table.add_row(template_type, template_data["description"], triggers)

    console.print(table)
