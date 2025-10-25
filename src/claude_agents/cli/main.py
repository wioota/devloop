"""CLI entry point - v2 with real agents."""
import asyncio
import logging
import signal
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from claude_agents.agents import AgentHealthMonitorAgent, FormatterAgent, GitCommitAssistantAgent, LinterAgent, PerformanceProfilerAgent, SecurityScannerAgent, TestRunnerAgent, TypeCheckerAgent
from claude_agents.collectors import FileSystemCollector
from claude_agents.core import AgentManager, Config, ConfigWrapper, EventBus

app = typer.Typer(
    help="Claude Agents - Development workflow automation",
    add_completion=False
)
console = Console()


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )


@app.command()
def watch(
    path: Path = typer.Argument(
        Path.cwd(),
        help="Path to watch for changes"
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        help="Path to configuration file"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Verbose logging"
    )
):
    """
    Watch a directory for file changes and run agents.

    Agents will automatically lint, format, and test your code as you work.

    Press Ctrl+C to stop.
    """
    setup_logging(verbose)

    console.print(f"[bold green]Claude Agents v2[/bold green]")
    console.print(f"Watching: [cyan]{path.absolute()}[/cyan]\n")

    # Run the async main loop
    try:
        asyncio.run(watch_async(path, config_path))
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")


async def watch_async(path: Path, config_path: Path | None):
    """Async watch implementation."""
    # Load configuration
    if config_path:
        config_manager = Config(str(config_path))
    else:
        config_manager = Config()
    config_dict = config_manager.load()
    config = ConfigWrapper(config_dict)

    # Create event bus
    event_bus = EventBus()

    # Create agent manager
    agent_manager = AgentManager(event_bus)

    # Create filesystem collector
    fs_collector = FileSystemCollector(
        event_bus=event_bus,
        watch_paths=[str(path)]
    )

    # Create and register agents based on configuration
    if config.is_agent_enabled("linter"):
        linter_config = config.get_agent_config("linter") or {}
        linter = LinterAgent(
            name="linter",
            triggers=linter_config.get("triggers", ["file:modified"]),
            event_bus=event_bus,
            config=linter_config.get("config", {})
        )
        agent_manager.register(linter)

    if config.is_agent_enabled("formatter"):
        formatter_config = config.get_agent_config("formatter") or {}
        formatter = FormatterAgent(
            name="formatter",
            triggers=formatter_config.get("triggers", ["file:modified"]),
            event_bus=event_bus,
            config=formatter_config.get("config", {})
        )
        agent_manager.register(formatter)

    if config.is_agent_enabled("test-runner"):
        test_config = config.get_agent_config("test-runner") or {}
        test_runner = TestRunnerAgent(
            name="test-runner",
            triggers=test_config.get("triggers", ["file:modified"]),
            event_bus=event_bus,
            config=test_config.get("config", {})
        )
        agent_manager.register(test_runner)

    if config.is_agent_enabled("agent-health-monitor"):
        monitor_config = config.get_agent_config("agent-health-monitor") or {}
        health_monitor = AgentHealthMonitorAgent(
            name="agent-health-monitor",
            triggers=monitor_config.get("triggers", ["agent:*:completed"]),
            event_bus=event_bus,
            config=monitor_config.get("config", {})
        )
        agent_manager.register(health_monitor)

    if config.is_agent_enabled("type-checker"):
        type_config = config.get_agent_config("type-checker") or {}
        type_checker = TypeCheckerAgent(
            config=type_config.get("config", {}),
            event_bus=event_bus
        )
        agent_manager.register(type_checker)

    if config.is_agent_enabled("security-scanner"):
        security_config = config.get_agent_config("security-scanner") or {}
        security_scanner = SecurityScannerAgent(
            config=security_config.get("config", {}),
            event_bus=event_bus
        )
        agent_manager.register(security_scanner)

    if config.is_agent_enabled("git-commit-assistant"):
        commit_config = config.get_agent_config("git-commit-assistant") or {}
        commit_assistant = GitCommitAssistantAgent(
            config=commit_config.get("config", {}),
            event_bus=event_bus
        )
        agent_manager.register(commit_assistant)

    if config.is_agent_enabled("performance-profiler"):
        perf_config = config.get_agent_config("performance-profiler") or {}
        performance_profiler = PerformanceProfilerAgent(
            config=perf_config.get("config", {}),
            event_bus=event_bus
        )
        agent_manager.register(performance_profiler)

    # Start everything
    await fs_collector.start()
    await agent_manager.start_all()

    console.print("[green]✓[/green] Started agents:")
    for agent_name in agent_manager.list_agents():
        console.print(f"  • [cyan]{agent_name}[/cyan]")

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
    await agent_manager.stop_all()
    await fs_collector.stop()


@app.command()
def init(
    path: Path = typer.Argument(
        Path.cwd(),
        help="Project directory"
    ),
    create_config: bool = typer.Option(
        True,
        help="Create default configuration file"
    )
):
    """Initialize claude-agents in a project."""
    claude_dir = path / ".claude"

    if claude_dir.exists():
        console.print(f"[yellow]Directory already exists: {claude_dir}[/yellow]")
    else:
        claude_dir.mkdir(exist_ok=True)
        console.print(f"[green]✓[/green] Created: {claude_dir}")
#
    # Create default configuration
    if create_config:
        config_file = claude_dir / "agents.json"
        if config_file.exists():
            console.print(f"[yellow]Configuration already exists: {config_file}[/yellow]")
        else:
            config = Config.default_config()
            config.save(config_file)
            console.print(f"[green]✓[/green] Created: {config_file}")
#
    console.print(f"\n[green]✓[/green] Initialized!")
    console.print(f"\nNext steps:")
    console.print(f"  1. Review/edit: [cyan]{claude_dir / 'agents.json'}[/cyan]")
    console.print(f"  2. Run: [cyan]claude-agents watch {path}[/cyan]")


@app.command()
def status():
    """Show configuration and agent status."""
    # Load configuration
    config_manager = Config()
    config_dict = config_manager.load()
    config = ConfigWrapper(config_dict)

    table = Table(title="Agent Configuration")

    table.add_column("Agent", style="cyan")
    table.add_column("Enabled", style="green")
    table.add_column("Triggers", style="yellow")

    for agent_name, agent_config in config.agents().items():
        enabled = "✓" if agent_config.get("enabled") else "✗"
        triggers = ", ".join(agent_config.get("triggers", []))
        table.add_row(agent_name, enabled, triggers)

    console.print(table)






@app.command()
def version():
    """Show version information."""
    from claude_agents import __version__
    console.print(f"Claude Agents v{__version__}")


if __name__ == "__main__":
    app()
