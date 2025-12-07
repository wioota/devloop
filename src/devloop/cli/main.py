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

from .commands import custom_agents as custom_agents_cmd
from .commands import feedback as feedback_cmd
from .commands import summary as summary_cmd
from devloop.agents import (
    AgentHealthMonitorAgent,
    FormatterAgent,
    GitCommitAssistantAgent,
    LinterAgent,
    PerformanceProfilerAgent,
    SecurityScannerAgent,
    TestRunnerAgent,
    TypeCheckerAgent,
)
from devloop.collectors import FileSystemCollector
from devloop.core import (
    AgentManager,
    Config,
    ConfigWrapper,
    EventBus,
    context_store,
    event_store,
)
from devloop.core.amp_integration import check_agent_findings, show_agent_status

app = typer.Typer(
    help="DevLoop - Development workflow automation", add_completion=False
)
console = Console()

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
    context_dir = Path.cwd() / ".devloop/context"
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
            "[yellow]No context index found. Start agents with 'devloop watch .' first.[/yellow]"
        )


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


def setup_logging_with_rotation(verbose: bool = False, project_dir: Path | None = None):
    """Setup logging configuration with file rotation for daemon mode."""
    from logging.handlers import RotatingFileHandler

    if project_dir is None:
        project_dir = Path.cwd()

    level = logging.DEBUG if verbose else logging.INFO
    log_file = project_dir / ".devloop" / "devloop.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Create rotating file handler
    # maxBytes: 10MB per file
    # backupCount: keep 3 rotated files (total ~40MB max)
    rotating_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=3,
    )

    # Format: timestamp | level | logger | message
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    rotating_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(rotating_handler)


def run_daemon(path: Path, config_path: Path | None, verbose: bool):
    """Run devloop in daemon/background mode."""
    import os
    import sys

    # Fork to background
    try:
        pid = os.fork()
        if pid > 0:
            # Parent process - exit
            console.print(
                f"[green]✓[/green] DevLoop started in background (PID: {pid})"
            )
            console.print("[dim]Run 'devloop stop' to stop the daemon[/dim]")
            sys.exit(0)
    except OSError as e:
        console.print(f"[red]✗[/red] Failed to start daemon: {e}")
        sys.exit(1)

    # Child process continues
    # Convert path to absolute before changing directory
    project_dir = path.resolve()

    os.chdir("/")
    os.setsid()
    os.umask(0)

    # Setup logging with rotation BEFORE redirecting file descriptors
    setup_logging_with_rotation(verbose, project_dir)

    # Don't redirect stdout/stderr - let logging handlers manage it
    # This prevents unbounded log file growth

    # Write PID file
    pid_file = project_dir / ".devloop" / "devloop.pid"
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    print(f"DevLoop v2 daemon started (PID: {os.getpid()})")
    print(f"Watching: {project_dir}")

    # Run the async main loop (will run indefinitely)
    # Ensure config_path is also absolute if specified
    abs_config_path = (
        config_path.resolve()
        if config_path
        else project_dir / ".devloop" / "agents.json"
    )
    try:
        asyncio.run(watch_async(project_dir, abs_config_path))
    except Exception as e:
        import traceback

        print(f"Daemon error: {e}")
        traceback.print_exc()
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
        console.print("[bold green]DevLoop v2[/bold green]")
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


async def _cleanup_old_data(context_store, event_store, interval_hours: int = 1):
    """Periodically clean up old findings and events to prevent disk fill-up.

    Args:
        context_store: Context store instance
        event_store: Event store instance
        interval_hours: How often to run cleanup (default: 1 hour)
    """
    cleanup_interval = interval_hours * 60 * 60  # Convert to seconds
    context_retention_hours = 7 * 24  # Keep 7 days of findings
    event_retention_days = 30  # Keep 30 days of events

    while True:
        try:
            await asyncio.sleep(cleanup_interval)

            # Clean up old context findings
            findings_removed = await context_store.cleanup_old_findings(
                hours_to_keep=context_retention_hours
            )

            # Clean up old events
            events_removed = await event_store.cleanup_old_events(
                days_to_keep=event_retention_days
            )

            console.print(
                f"[dim]Cleanup: removed {findings_removed} old findings, {events_removed} old events[/dim]"
            )

        except asyncio.CancelledError:
            break
        except Exception as e:
            console.print(f"[yellow]Cleanup error: {e}[/yellow]")


async def watch_async(path: Path, config_path: Path | None):
    """Async watch implementation."""
    # Load configuration
    if config_path:
        # Ensure it's a Path object and convert to string
        config_manager = Config(str(Path(config_path).resolve()))
    else:
        # Default to project .devloop/agents.json
        config_manager = Config(str((path / ".devloop" / "agents.json").resolve()))
    config_dict = config_manager.load()
    config = ConfigWrapper(config_dict)

    # Create event bus
    event_bus = EventBus()

    # Initialize context store
    context_store.context_dir = path / ".devloop" / "context"
    await context_store.initialize()

    # Initialize event store
    event_store.db_path = path / ".devloop" / "events.db"
    await event_store.initialize()
    console.print(f"[dim]Context store: {context_store.context_dir}[/dim]")
    console.print(f"[dim]Event store: {event_store.db_path}[/dim]")

    # Get global config for resource limits
    global_config = config.get_global_config()

    # Create agent manager with project directory and resource limits
    agent_manager = AgentManager(
        event_bus, project_dir=path, resource_limits=global_config.resource_limits
    )

    # Create filesystem collector
    fs_config = {"watch_paths": [str(path)]}
    fs_collector = FileSystemCollector(event_bus=event_bus, config=fs_config)

    # Start cleanup task (run every hour to remove old findings/events)
    cleanup_task = asyncio.create_task(_cleanup_old_data(context_store, event_store))

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
    cleanup_task.cancel()
    await agent_manager.stop_all()
    await fs_collector.stop()

    # Wait for cleanup task to finish
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


@app.command()
def init(
    path: Path = typer.Argument(Path.cwd(), help="Project directory"),
    skip_config: bool = typer.Option(
        False, "--skip-config", help="Skip creating configuration file"
    ),
    non_interactive: bool = typer.Option(
        False, "--non-interactive", help="Skip interactive prompts for optional agents"
    ),
):
    """Initialize devloop in a project."""
    claude_dir = path / ".devloop"

    if claude_dir.exists():
        console.print(f"[yellow]Directory already exists: {claude_dir}[/yellow]")
    else:
        claude_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] Created: {claude_dir}")

    # Create default configuration
    if not skip_config:
        config_file = claude_dir / "agents.json"
        if config_file.exists():
            console.print(
                f"[yellow]Configuration already exists: {config_file}[/yellow]"
            )
        else:
            optional_agents = {}

            # Interactive prompts for optional agents (unless non-interactive mode)
            if not non_interactive:
                console.print("\n[cyan]Optional Agents Setup[/cyan]")
                console.print("The following optional agents can be enabled:\n")

                # Snyk prompt
                if typer.confirm(
                    "Enable [yellow]Snyk[/yellow] agent for security vulnerability scanning?",
                    default=False,
                ):
                    optional_agents["snyk"] = True
                    console.print(
                        "  [green]✓[/green] Snyk agent enabled (requires SNYK_TOKEN env var)"
                    )

                # Code Rabbit prompt
                if typer.confirm(
                    "Enable [yellow]Code Rabbit[/yellow] agent for code analysis insights?",
                    default=False,
                ):
                    optional_agents["code-rabbit"] = True
                    console.print(
                        "  [green]✓[/green] Code Rabbit agent enabled (requires CODE_RABBIT_API_KEY env var)"
                    )

                # CI Monitor prompt
                if typer.confirm(
                    "Enable [yellow]CI Monitor[/yellow] agent to track CI/CD pipeline status?",
                    default=False,
                ):
                    optional_agents["ci-monitor"] = True
                    console.print("  [green]✓[/green] CI Monitor agent enabled")

                # Pyodide WASM Sandbox prompt and installation
                from devloop.cli.pyodide_installer import prompt_pyodide_installation

                prompt_pyodide_installation(non_interactive=False)

            config = Config()
            config._config = config._get_default_config(optional_agents=optional_agents)
            config.save(config_file)
            console.print(f"\n[green]✓[/green] Created: {config_file}")

    # Check for and manage AGENTS.md with Beads integration
    agents_md = path / "AGENTS.md"
    beads_template = claude_dir / "beads_template.md"

    if beads_template.exists():
        beads_content = beads_template.read_text()

        if agents_md.exists():
            # Check if AGENTS.md already has Beads section
            content = agents_md.read_text()
            if "Task Management with Beads" not in content:
                # Inject Beads section after first heading
                lines = content.split("\n")
                insert_pos = 0
                for i, line in enumerate(lines):
                    if line.startswith("# ") and i > 0:
                        insert_pos = i + 1
                        break

                # Insert Beads section
                new_content = (
                    "\n".join(lines[:insert_pos])
                    + "\n\n"
                    + beads_content
                    + "\n\n"
                    + "\n".join(lines[insert_pos:])
                )
                agents_md.write_text(new_content)
                console.print(
                    f"[green]✓[/green] Injected Beads section into {agents_md}"
                )
        else:
            # Create AGENTS.md from template
            template_header = """# Development Workflow

This project uses background agents and Beads for task management.

"""
            agents_md.write_text(template_header + beads_content)
            console.print(f"[green]✓[/green] Created: {agents_md}")

    # Handle Claude.md symlink for Claude code tools
    claude_md = path / "CLAUDE.md"
    if claude_md.exists():
        if claude_md.is_symlink():
            target = claude_md.resolve()
            if target.name == "AGENTS.md":
                console.print("\n[green]✓[/green] Claude symlink already set up")
            else:
                console.print(
                    "\n[yellow]Warning:[/yellow] CLAUDE.md exists but doesn't point to AGENTS.md"
                )
        else:
            console.print("\n[yellow]Note:[/yellow] CLAUDE.md exists as a regular file")
            console.print("  [cyan]Consider replacing it with a symlink:[/cyan]")
            console.print("    rm CLAUDE.md && ln -s AGENTS.md CLAUDE.md")
    else:
        # Create symlink for Claude
        try:
            claude_md.symlink_to("AGENTS.md")
            console.print(f"[green]✓[/green] Created: {claude_md} -> AGENTS.md")
        except Exception as e:
            console.print(
                f"[yellow]Warning:[/yellow] Could not create CLAUDE.md symlink: {e}"
            )

    # Set up Claude Code slash commands
    claude_commands_dir = path / ".claude" / "commands"
    template_commands_dir = Path(__file__).parent / "templates" / "claude_commands"

    if template_commands_dir.exists():
        claude_commands_dir.mkdir(parents=True, exist_ok=True)

        # Copy command templates
        import shutil

        commands_copied = []
        for template_file in template_commands_dir.glob("*.md"):
            dest_file = claude_commands_dir / template_file.name
            if not dest_file.exists():
                shutil.copy2(template_file, dest_file)
                commands_copied.append(template_file.stem)

        if commands_copied:
            console.print("\n[green]✓[/green] Created Claude Code slash commands:")
            for cmd in commands_copied:
                console.print(f"  • /{cmd}")

    # Install git hooks if this is a git repository
    git_dir = path / ".git"
    if git_dir.exists() and git_dir.is_dir():
        hooks_template_dir = Path(__file__).parent / "templates" / "git_hooks"
        hooks_dest_dir = git_dir / "hooks"

        if hooks_template_dir.exists():
            hooks_installed = []
            for template_file in hooks_template_dir.iterdir():
                if template_file.is_file():
                    dest_file = hooks_dest_dir / template_file.name

                    # Backup existing hook if present
                    if dest_file.exists():
                        backup_file = hooks_dest_dir / f"{template_file.name}.backup"
                        shutil.copy2(dest_file, backup_file)

                    # Install new hook
                    shutil.copy2(template_file, dest_file)
                    dest_file.chmod(0o755)  # Make executable
                    hooks_installed.append(template_file.name)

            if hooks_installed:
                console.print("\n[green]✓[/green] Installed git hooks:")
                for hook in hooks_installed:
                    console.print(f"  • {hook}")

    console.print("\n[green]✓[/green] Initialized!")
    console.print("\nNext steps:")
    console.print(f"  1. Review/edit: [cyan]{claude_dir / 'agents.json'}[/cyan]")
    console.print(f"  2. Run: [cyan]devloop watch {path}[/cyan]")


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
    """Stop the background devloop daemon."""
    import os
    import signal

    pid_file = path / ".devloop" / "devloop.pid"

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
        console.print(f"[green]✓[/green] Stopped devloop daemon (PID: {pid})")

        # Clean up files
        pid_file.unlink()
        log_file = path / ".devloop" / "devloop.log"
        if log_file.exists():
            console.print(f"[dim]Logs available at: {log_file}[/dim]")

    except (ValueError, OSError) as e:
        console.print(f"[red]✗[/red] Failed to stop daemon: {e}")
        if pid_file.exists():
            pid_file.unlink()


@app.command()
def version():
    """Show version information."""
    from devloop import __version__

    console.print(f"DevLoop v{__version__}")


@app.command()
def update_hooks(path: Path = typer.Argument(Path.cwd(), help="Project directory")):
    """Update git hooks from latest templates."""
    import shutil

    git_dir = path / ".git"

    if not git_dir.exists() or not git_dir.is_dir():
        console.print(
            f"[red]✗[/red] Not a git repository: {path}\n"
            "[yellow]Git hooks can only be installed in git repositories.[/yellow]"
        )
        return

    hooks_template_dir = Path(__file__).parent / "templates" / "git_hooks"
    hooks_dest_dir = git_dir / "hooks"

    if not hooks_template_dir.exists():
        console.print(f"[red]✗[/red] Hook templates not found at: {hooks_template_dir}")
        return

    hooks_dest_dir.mkdir(parents=True, exist_ok=True)
    hooks_updated = []

    for template_file in hooks_template_dir.iterdir():
        if template_file.is_file():
            dest_file = hooks_dest_dir / template_file.name

            # Backup existing hook if present
            if dest_file.exists():
                backup_file = hooks_dest_dir / f"{template_file.name}.backup"
                shutil.copy2(dest_file, backup_file)
                console.print(
                    f"[dim]  Backed up existing hook: {template_file.name} -> {template_file.name}.backup[/dim]"
                )

            # Install new hook
            shutil.copy2(template_file, dest_file)
            dest_file.chmod(0o755)  # Make executable
            hooks_updated.append(template_file.name)

    if hooks_updated:
        console.print("\n[green]✓[/green] Updated git hooks:")
        for hook in hooks_updated:
            console.print(f"  • {hook}")
    else:
        console.print("[yellow]No hooks found to update[/yellow]")


if __name__ == "__main__":
    app()
