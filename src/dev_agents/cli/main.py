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

from dev_agents.agents import (
    AgentHealthMonitorAgent,
    FormatterAgent,
    GitCommitAssistantAgent,
    LinterAgent,
    PerformanceProfilerAgent,
    SecurityScannerAgent,
    TestRunnerAgent,
    TypeCheckerAgent,
)
from dev_agents.collectors import FileSystemCollector
from dev_agents.core import (
    AgentManager,
    Config,
    ConfigWrapper,
    EventBus,
    context_store,
    event_store,
)
from dev_agents.core.amp_integration import check_agent_findings, show_agent_status

app = typer.Typer(
    help="Dev Agents - Development workflow automation", add_completion=False
)
console = Console()

# Import and add command submodules
from .commands import summary as summary_cmd
from .commands import custom_agents as custom_agents_cmd
from .commands import feedback as feedback_cmd

app.add_typer(summary_cmd.app, name="summary")
app.add_typer(custom_agents_cmd.app, name="custom")
app.add_typer(feedback_cmd.app, name="feedback")


@app.command()
def amp_status():
    """Show current agent status for Amp."""
    import asyncio

    result = asyncio.run(show_agent_status())
    console.print_json(data=result)


@app.command()
def amp_findings():
    """Show agent findings for Amp."""
    import asyncio

    result = asyncio.run(check_agent_findings())
    console.print_json(data=result)


@app.command()
def amp_context():
    """Show context store index for Amp."""
    from pathlib import Path

    # Try to read the context index
    context_dir = Path(".claude/context")
    index_file = context_dir / "index.json"

    if index_file.exists():
        try:
            import json

            with open(index_file) as f:
                data = json.load(f)
            console.print_json(data=data)
        except Exception as e:
            console.print(f"[red]Error reading context: {e}[/red]")
    else:
        console.print(
            "[yellow]No context index found. Start agents with 'dev-agents watch .' first.[/yellow]"
        )


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


def run_daemon(path: Path, config_path: Path | None, verbose: bool):
    """Run dev-agents in daemon/background mode."""
    import os
    import sys

    # Fork to background
    try:
        pid = os.fork()
        if pid > 0:
            # Parent process - exit
            console.print(
                f"[green]✓[/green] Dev Agents started in background (PID: {pid})"
            )
            console.print("[dim]Run 'dev-agents stop' to stop the daemon[/dim]")
            sys.exit(0)
    except OSError as e:
        console.print(f"[red]✗[/red] Failed to start daemon: {e}")
        sys.exit(1)

    # Child process continues
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # Redirect stdout/stderr to log file
    log_file = path / ".claude" / "dev-agents.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with open(log_file, "a") as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
        os.dup2(f.fileno(), sys.stderr.fileno())

    # Setup logging for daemon
    setup_logging(verbose)

    # Write PID file
    pid_file = path / ".claude" / "dev-agents.pid"
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    print(f"Dev Agents v2 daemon started (PID: {os.getpid()})")
    print(f"Watching: {path.absolute()}")

    # Run the async main loop (will run indefinitely)
    try:
        asyncio.run(watch_async(path, config_path))
    except Exception as e:
        print(f"Daemon error: {e}")
    finally:
        # Clean up PID file
        if pid_file.exists():
            pid_file.unlink()


@app.command()
def watch(
    path: Path = typer.Argument(Path.cwd(), help="Path to watch for changes"),
    config_path: Optional[Path] = typer.Option(
        None, "--config", help="Path to configuration file"
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose logging"),
    foreground: bool = typer.Option(
        False, "--foreground", help="Run in foreground (blocking mode) for debugging"
    ),
):
    """
    Watch a directory for file changes and run agents.

    Agents will automatically lint, format, and test your code as you work.

    Runs in background by default for coding agent integration.
    Use --foreground for debugging/interactive mode.
    """
    if foreground:
        # Run in foreground for debugging
        setup_logging(verbose)
        console.print("[bold green]Dev Agents v2[/bold green]")
        console.print(f"Watching: [cyan]{path.absolute()}[/cyan] (foreground mode)\\n")
    else:
        # Run in background (default)
        run_daemon(path, config_path, verbose)
        return

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

    # Initialize context store
    context_store.context_dir = path / ".claude" / "context"
    await context_store.initialize()

    # Initialize event store
    event_store.db_path = path / ".claude" / "events.db"
    await event_store.initialize()
    console.print(f"[dim]Context store: {context_store.context_dir}[/dim]")
    console.print(f"[dim]Event store: {event_store.db_path}[/dim]")

    # Create agent manager
    agent_manager = AgentManager(event_bus)

    # Create filesystem collector
    fs_config = {"watch_paths": [str(path)]}
    fs_collector = FileSystemCollector(event_bus=event_bus, config=fs_config)

    # Create and register agents based on configuration
    if config.is_agent_enabled("linter"):
        linter_config = config.get_agent_config("linter") or {}
        linter = LinterAgent(
            name="linter",
            triggers=linter_config.get("triggers", ["file:modified"]),
            event_bus=event_bus,
            config=linter_config.get("config", {}),
        )
        agent_manager.register(linter)

    if config.is_agent_enabled("formatter"):
        formatter_config = config.get_agent_config("formatter") or {}
        formatter = FormatterAgent(
            name="formatter",
            triggers=formatter_config.get("triggers", ["file:modified"]),
            event_bus=event_bus,
            config=formatter_config.get("config", {}),
        )
        agent_manager.register(formatter)

    if config.is_agent_enabled("test-runner"):
        test_config = config.get_agent_config("test-runner") or {}
        test_runner = TestRunnerAgent(
            name="test-runner",
            triggers=test_config.get("triggers", ["file:modified"]),
            event_bus=event_bus,
            config=test_config.get("config", {}),
        )
        agent_manager.register(test_runner)

    if config.is_agent_enabled("agent-health-monitor"):
        monitor_config = config.get_agent_config("agent-health-monitor") or {}
        health_monitor = AgentHealthMonitorAgent(
            name="agent-health-monitor",
            triggers=monitor_config.get("triggers", ["agent:*:completed"]),
            event_bus=event_bus,
            config=monitor_config.get("config", {}),
        )
        agent_manager.register(health_monitor)

    if config.is_agent_enabled("type-checker"):
        type_config = config.get_agent_config("type-checker") or {}
        type_checker = TypeCheckerAgent(
            config=type_config.get("config", {}), event_bus=event_bus
        )
        agent_manager.register(type_checker)

    if config.is_agent_enabled("security-scanner"):
        security_config = config.get_agent_config("security-scanner") or {}
        security_scanner = SecurityScannerAgent(
            config=security_config.get("config", {}), event_bus=event_bus
        )
        agent_manager.register(security_scanner)

    if config.is_agent_enabled("git-commit-assistant"):
        commit_config = config.get_agent_config("git-commit-assistant") or {}
        commit_assistant = GitCommitAssistantAgent(
            config=commit_config.get("config", {}), event_bus=event_bus
        )
        agent_manager.register(commit_assistant)

    if config.is_agent_enabled("performance-profiler"):
        perf_config = config.get_agent_config("performance-profiler") or {}
        performance_profiler = PerformanceProfilerAgent(
            config=perf_config.get("config", {}), event_bus=event_bus
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
    path: Path = typer.Argument(Path.cwd(), help="Project directory"),
    skip_config: bool = typer.Option(False, "--skip-config", help="Skip creating configuration file"),
):
    """Initialize dev-agents in a project."""
    claude_dir = path / ".claude"

    if claude_dir.exists():
        console.print(f"[yellow]Directory already exists: {claude_dir}[/yellow]")
    else:
        claude_dir.mkdir(exist_ok=True)
        console.print(f"[green]✓[/green] Created: {claude_dir}")
    # Create default configuration
    if not skip_config:
        config_file = claude_dir / "agents.json"
        if config_file.exists():
            console.print(
                f"[yellow]Configuration already exists: {config_file}[/yellow]"
            )
        else:
            config = Config.default_config()
            config.save(config_file)
            console.print(f"[green]✓[/green] Created: {config_file}")

    console.print("\n[green]✓[/green] Initialized!")
    console.print("\nNext steps:")
    console.print(f"  1. Review/edit: [cyan]{claude_dir / 'agents.json'}[/cyan]")
    console.print(f"  2. Run: [cyan]dev-agents watch {path}[/cyan]")


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
def stop(path: Path = typer.Argument(Path.cwd(), help="Project directory")):
    """Stop the background dev-agents daemon."""
    import os
    import signal

    pid_file = path / ".claude" / "dev-agents.pid"

    if not pid_file.exists():
        console.print(f"[yellow]No daemon running in {path}[/yellow]")
        return

    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())

        # Check if process is still running
        os.kill(pid, 0)  # Signal 0 just checks if process exists

        # Send SIGTERM to gracefully stop
        os.kill(pid, signal.SIGTERM)
        console.print(f"[green]✓[/green] Stopped dev-agents daemon (PID: {pid})")

        # Clean up files
        pid_file.unlink()
        log_file = path / ".claude" / "dev-agents.log"
        if log_file.exists():
            console.print(f"[dim]Logs available at: {log_file}[/dim]")

    except (ValueError, OSError) as e:
        console.print(f"[red]✗[/red] Failed to stop daemon: {e}")
        if pid_file.exists():
            pid_file.unlink()


@app.command()
def version():
    """Show version information."""
    from dev_agents import __version__

    console.print(f"Dev Agents v{__version__}")


if __name__ == "__main__":
    app()
