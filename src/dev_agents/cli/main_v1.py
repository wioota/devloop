"""CLI entry point - prototype version."""

import asyncio
import logging
import signal
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler

from dev_agents.agents import EchoAgent, FileLoggerAgent
from dev_agents.collectors import FileSystemCollector
from dev_agents.core import EventBus

app = typer.Typer(
    help="Claude Agents - Development workflow automation (PROTOTYPE)",
    add_completion=False,
)
console = Console()


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@app.command()
def watch(
    path: Path = typer.Argument(Path.cwd(), help="Path to watch for changes"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
):
    """
    Watch a directory for file changes and run agents.

    This is a prototype that demonstrates the core architecture:
    - FileSystem collector watches for file changes
    - Events are emitted to the EventBus
    - Agents subscribe to events and process them

    Press Ctrl+C to stop.
    """
    setup_logging(verbose)

    console.print("[bold green]Claude Agents Prototype[/bold green]")
    console.print(f"Watching: [cyan]{path.absolute()}[/cyan]\n")

    # Run the async main loop
    try:
        asyncio.run(watch_async(path))
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")


async def watch_async(path: Path):
    """Async watch implementation."""
    # Create event bus
    event_bus = EventBus()

    # Create filesystem collector
    fs_collector = FileSystemCollector(event_bus=event_bus, watch_paths=[str(path)])

    # Create agents
    echo_agent = EchoAgent(
        name="echo",
        triggers=["file:*"],  # Listen to all file events
        event_bus=event_bus,
    )

    logger_agent = FileLoggerAgent(
        name="file-logger",
        triggers=["file:modified", "file:created"],
        event_bus=event_bus,
    )

    # Start everything
    await fs_collector.start()
    await echo_agent.start()
    await logger_agent.start()

    console.print("[green]✓[/green] Agents started:")
    console.print("  • [cyan]echo[/cyan] - logs all file events")
    console.print(
        "  • [cyan]file-logger[/cyan] - writes changes to .claude/file-changes.log"
    )
    console.print("\n[dim]Waiting for file changes... (Ctrl+C to stop)[/dim]\n")

    # Wait for shutdown signal
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Keep running until shutdown
    await shutdown_event.wait()

    # Stop everything
    await echo_agent.stop()
    await logger_agent.stop()
    await fs_collector.stop()


@app.command()
def events(
    count: int = typer.Option(10, "--count", "-n", help="Number of events to show")
):
    """Show recent events (from last watch session)."""
    console.print("[yellow]Event history not yet implemented in prototype[/yellow]")
    console.print("Events are logged to .claude/file-changes.log")


@app.command()
def init(path: Path = typer.Argument(Path.cwd(), help="Project directory")):
    """Initialize dev-agents in a project."""
    claude_dir = path / ".claude"

    if claude_dir.exists():
        console.print(f"[yellow]Directory already exists: {claude_dir}[/yellow]")
        return

    claude_dir.mkdir(exist_ok=True)
    console.print(f"[green]✓[/green] Created: {claude_dir}")
    console.print(f"\nRun [cyan]dev-agents watch {path}[/cyan] to start watching!")


@app.command()
def version():
    """Show version information."""
    from dev_agents import __version__

    console.print(f"Claude Agents v{__version__} (PROTOTYPE)")


if __name__ == "__main__":
    app()
