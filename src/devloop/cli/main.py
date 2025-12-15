"""CLI entry point - v2 with real agents."""

import asyncio
import logging
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from devloop.agents import (
    AgentHealthMonitorAgent,
    CodeRabbitAgent,
    FormatterAgent,
    GitCommitAssistantAgent,
    LinterAgent,
    PerformanceProfilerAgent,
    SecurityScannerAgent,
    SnykAgent,
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
    get_action_logger,
)
from devloop.core.amp_integration import check_agent_findings, show_agent_status
from devloop.core.daemon_health import DaemonHealthCheck, check_daemon_health
from devloop.core.error_handler import ErrorCode, ErrorSeverity, get_error_handler
from devloop.core.error_notifier import ErrorNotifier
from devloop.core.event_replayer import EventReplayer
from devloop.core.transactional_io import initialize_transaction_system

from .commands import audit as audit_cmd
from .commands import custom_agents as custom_agents_cmd
from .commands import feedback as feedback_cmd
from .commands import marketplace as marketplace_cmd
from .commands import metrics as metrics_cmd
from .commands import release as release_cmd
from .commands import summary as summary_cmd
from .commands import telemetry as telemetry_cmd
from .commands import tools as tools_cmd

app = typer.Typer(
    help="DevLoop - Development workflow automation", add_completion=False
)
console = Console()

app.add_typer(summary_cmd.app, name="summary")
app.add_typer(custom_agents_cmd.app, name="custom")
app.add_typer(feedback_cmd.app, name="feedback")
app.add_typer(marketplace_cmd.app, name="agent")
app.add_typer(metrics_cmd.app, name="metrics")
app.add_typer(release_cmd.app, name="release")
app.add_typer(telemetry_cmd.app, name="telemetry")
app.add_typer(tools_cmd.app, name="tools")

# Wrap Typer app to handle Click-based audit command
# Note: We can't use add_typer with Click groups due to Typer version compatibility
_original_app = app


class _WrappedApp:
    """Wrapper app that intercepts Click commands before Typer processes them.

    Also logs all CLI commands with optional Amp thread context for self-improvement agent.
    """

    def __init__(self, typer_app):
        self.typer_app = typer_app
        self.action_logger = get_action_logger()

    def __call__(self, *args, **kwargs):
        """Handle command invocation with action logging."""
        start_time = time.time()
        exit_code = None
        error_message = None

        try:
            if len(sys.argv) > 1 and sys.argv[1] == "audit":
                # Delegate to Click for audit command
                audit_cmd.audit(sys.argv[2:], standalone_mode=False)
                exit_code = 0
                return

            # Run the Typer app normally
            return self.typer_app(*args, **kwargs)
        except SystemExit as e:
            exit_code = (
                e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
            )
            raise
        except Exception as e:
            exit_code = 1
            error_message = str(e)
            raise
        finally:
            # Log the command execution (even if it failed)
            try:
                duration_ms = int((time.time() - start_time) * 1000)
                command = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "devloop"

                self.action_logger.log_cli_command(
                    command=command,
                    exit_code=exit_code,
                    duration_ms=duration_ms,
                    error_message=error_message,
                )
            except Exception as log_error:
                # Don't let logging errors break the CLI
                logging.getLogger(__name__).debug(
                    f"Failed to log CLI action: {log_error}"
                )

    def __getattr__(self, name):
        """Delegate attribute access to the wrapped Typer app."""
        return getattr(self.typer_app, name)


app = _WrappedApp(_original_app)


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


@app.command()
def health():
    """Show operational health status of agents."""
    from pathlib import Path

    from devloop.core.operational_health import OperationalHealthAnalyzer

    devloop_dir = Path.cwd() / ".devloop"

    if not devloop_dir.exists():
        console.print(
            "[yellow]No .devloop directory found. Start agents with 'devloop watch .' first.[/yellow]"
        )
        return

    analyzer = OperationalHealthAnalyzer(devloop_dir)
    report = analyzer.generate_health_report()
    console.print(report)


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
    except Exception as e:
        # Display critical startup errors with help
        error_handler = get_error_handler()
        error_notifier = ErrorNotifier(console)

        if error_handler.has_critical_error():
            critical_error = error_handler.get_critical_error()
            if critical_error:
                error_notifier.notify_startup_error(critical_error)
                error_notifier.show_recovery_help(critical_error)
        else:
            # Unknown startup error
            console.print(f"[red]✗ Startup failed: {e}[/red]")

        sys.exit(1)


async def _cleanup_old_data(context_store, event_store, interval_minutes: int = 15):
    """Periodically clean up old findings and events to prevent disk/memory fill-up.

    Args:
        context_store: Context store instance
        event_store: Event store instance
        interval_minutes: How often to run cleanup (default: 15 minutes)

    Note: This is aggressive cleanup to prevent memory bloat between finds.
    Most findings are auto-retained for 24 hours (IMMEDIATE/RELEVANT) or
    7 days (BACKGROUND) on disk. Memory is trimmed more aggressively per
    tier limits in ContextStore.add_finding().
    """
    cleanup_interval = interval_minutes * 60  # Convert to seconds
    context_retention_hours = 7 * 24  # Keep 7 days of findings on disk
    event_retention_days = 30  # Keep 30 days of events

    while True:
        try:
            await asyncio.sleep(cleanup_interval)

            # Clean up old context findings (removes from disk)
            findings_removed = await context_store.cleanup_old_findings(
                hours_to_keep=context_retention_hours
            )

            # Clean up old events (removes from database)
            events_removed = await event_store.cleanup_old_events(
                days_to_keep=event_retention_days
            )

            if findings_removed > 0 or events_removed > 0:
                console.print(
                    f"[dim]Cleanup: removed {findings_removed} old findings, {events_removed} old events[/dim]"
                )

        except asyncio.CancelledError:
            break
        except Exception as e:
            console.print(f"[yellow]Cleanup error: {e}[/yellow]")


async def watch_async(path: Path, config_path: Path | None):
    """Async watch implementation."""
    # Initialize error handler
    error_handler = get_error_handler()

    # Load configuration with fail-fast on errors
    try:
        if config_path:
            # Ensure it's a Path object and convert to string
            config_manager = Config(str(Path(config_path).resolve()))
        else:
            # Default to project .devloop/agents.json
            config_path_str = str((path / ".devloop" / "agents.json").resolve())
            if not Path(config_path_str).exists():
                error_handler.handle_startup_error(
                    ErrorCode.CONFIG_NOT_FOUND,
                    f"Configuration file not found: {config_path_str}",
                    severity=ErrorSeverity.CRITICAL,
                    details="Run 'devloop init' to create a default configuration.",
                    suggested_action="devloop init",
                )
            config_manager = Config(config_path_str)

        config_dict = config_manager.load()
        config = ConfigWrapper(config_dict)
    except ValueError as e:
        error_handler.handle_startup_error(
            ErrorCode.CONFIG_INVALID,
            "Configuration validation failed",
            exception=e,
            severity=ErrorSeverity.CRITICAL,
        )
    except Exception as e:
        error_handler.handle_startup_error(
            ErrorCode.CONFIG_INVALID,
            f"Failed to load configuration: {e}",
            exception=e,
            severity=ErrorSeverity.CRITICAL,
        )

    # Create event bus
    event_bus = EventBus()

    # Initialize transaction system (recovery and self-healing)
    initialize_transaction_system(path / ".devloop")

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

    # Start daemon health check (heartbeat every 30 seconds)
    health_check = DaemonHealthCheck(path, heartbeat_interval=30)
    await health_check.start()

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

    if config.is_agent_enabled("snyk"):
        snyk_config = config.get_agent_config("snyk") or {}
        snyk_agent = SnykAgent(
            name="snyk",
            triggers=snyk_config.get("triggers", ["file:modified", "file:created"]),
            event_bus=event_bus,
            config=snyk_config.get("config", {}),
        )
        agent_manager.register(snyk_agent)

    if config.is_agent_enabled("code-rabbit"):
        code_rabbit_config = config.get_agent_config("code-rabbit") or {}
        code_rabbit_agent = CodeRabbitAgent(
            name="code-rabbit",
            triggers=code_rabbit_config.get(
                "triggers", ["file:modified", "file:created"]
            ),
            event_bus=event_bus,
            config=code_rabbit_config.get("config", {}),
        )
        agent_manager.register(code_rabbit_agent)

    # Start everything
    await fs_collector.start()
    await agent_manager.start_all()

    console.print("[green]✓[/green] Started agents:")
    for agent_name in agent_manager.list_agents():
        console.print(f"  • [cyan]{agent_name}[/cyan]")

    # Replay missed events (event persistence and recovery)
    replayer = EventReplayer(event_bus, agent_manager)
    replay_stats = await replayer.replay_all_agents()

    if replay_stats["total_replayed"] > 0:
        console.print(
            f"\n[cyan]Event Replay[/cyan]: Replayed {replay_stats['total_replayed']} missed events"
        )
        for agent_name, count in replay_stats["agents"].items():
            if count > 0:
                console.print(f"  • {agent_name}: {count} events")

    if replay_stats["gaps"]:
        console.print(
            f"\n[yellow]⚠ Event Gaps Detected[/yellow]: {len(replay_stats['gaps'])} gaps in sequence"
        )
        console.print("[dim]Run 'devloop debug' for details[/dim]")

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
    await health_check.stop()
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
        # Ensure proper permissions even if directory exists
        claude_dir.chmod(0o755)
    else:
        claude_dir.mkdir(parents=True, exist_ok=True)
        # Set proper permissions (rwxr-xr-x) so agents can write
        claude_dir.chmod(0o755)
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
                    # Install and configure Snyk CLI if needed
                    from devloop.cli.snyk_installer import prompt_snyk_installation

                    prompt_snyk_installation(non_interactive=False)

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

    # Check for and manage AGENTS.md with DevLoop template
    agents_md = path / "AGENTS.md"
    devloop_template = (
        Path(__file__).parent / "templates" / "devloop_agents_template.md"
    )

    # Legacy beads template (for backward compatibility)
    beads_template = claude_dir / "beads_template.md"

    # Check if AGENTS.md needs DevLoop content
    needs_devloop_content = False
    if agents_md.exists():
        content = agents_md.read_text()
        # Check for critical DevLoop sections
        missing_sections = []
        if "Task Management with Beads" not in content:
            missing_sections.append("Beads task management")
        if "NO MARKDOWN FILES FOR PLANNING" not in content:
            missing_sections.append("No markdown files rule")
        if (
            "Secrets Management & Token Security" not in content
            and "Secrets Management" not in content
        ):
            missing_sections.append("Token security")
        if "Development Discipline" not in content:
            missing_sections.append("Development discipline")
        if "Pre-Flight Development Checklist" not in content:
            missing_sections.append("Pre-flight checklist")
        if "CI Verification" not in content and "Pre-Push Hook" not in content:
            missing_sections.append("CI verification (pre-push hook)")
        if "Documentation Practices" not in content:
            missing_sections.append("Documentation practices")
        if "Publishing & Security Considerations" not in content:
            missing_sections.append("Publishing & security considerations")
        if "Release Process" not in content:
            missing_sections.append("Release process")
        if "Configuration" not in content:
            missing_sections.append("Configuration (logging, agents)")
        if "Security & Privacy" not in content:
            missing_sections.append("Security & privacy")
        if "Success Metrics" not in content:
            missing_sections.append("Success metrics")
        if "Future Considerations" not in content:
            missing_sections.append("Future considerations")

        needs_devloop_content = len(missing_sections) > 0

        if needs_devloop_content:
            # Copy template to .devloop for reference
            devloop_template_copy = claude_dir / "devloop_agents_template.md"
            if devloop_template.exists():
                import shutil

                shutil.copy(devloop_template, devloop_template_copy)

                # Inject self-executing merge instruction directly into AGENTS.md
                instruction_section = f"""

---

## 🔧 DevLoop Setup Required

**⚠️ ACTION FOR AI ASSISTANT (Claude/Copilot):** This AGENTS.md is missing critical DevLoop sections.

### Missing Sections:
{chr(10).join(f'- {section}' for section in missing_sections)}

### Instructions:

Please complete this setup automatically:

1. **Read the template**: `.devloop/devloop_agents_template.md`
2. **Merge missing sections** into this AGENTS.md file
3. **Follow merge guidelines** (see below)
4. **Delete this entire section** (🔧 DevLoop Setup Required) after merging

### Merge Guidelines:

- ✅ **Do NOT duplicate** existing content - only add missing sections
- ✅ **Preserve** all existing project-specific content
- ✅ **Maintain** the existing document structure and headings
- ✅ **Merge intelligently** - if a section partially exists, enhance it
- ✅ **Respect** document flow - place sections in logical order

### Required Sections:

- ⚠️ Task Management with Beads (at the top, after title)
- ⛔️ NO MARKDOWN FILES FOR PLANNING (absolute rules)
- Development Discipline (commit/push requirements)
- Secrets Management & Token Security
- Absolute Rules for AI Agents

**Template location:** `.devloop/devloop_agents_template.md`

**Delete this section after successful merge.**

---

"""
                # Insert at the beginning of the file (after title if present)
                lines = content.split("\n")
                insert_pos = 0

                # Find first heading
                for i, line in enumerate(lines):
                    if line.startswith("# "):
                        insert_pos = i + 1
                        break

                # Insert the instruction
                new_content = (
                    "\n".join(lines[:insert_pos])
                    + instruction_section
                    + "\n".join(lines[insert_pos:])
                )
                agents_md.write_text(new_content)

                console.print(
                    "\n[green]✓[/green] Injected DevLoop setup instructions into AGENTS.md"
                )
                console.print(
                    f"[cyan]→[/cyan] Template copied to: {devloop_template_copy}"
                )
                console.print("\n[cyan]Next step:[/cyan]")
                console.print(
                    "  • Open this project in Claude Code/Amp - it will automatically merge the template!"
                )
    else:
        # Create new AGENTS.md from devloop template
        if devloop_template.exists():
            import shutil

            shutil.copy(devloop_template, agents_md)
            console.print(
                f"[green]✓[/green] Created: {agents_md} (from DevLoop template)"
            )
        elif beads_template.exists():
            # Fallback to legacy beads template
            beads_content = beads_template.read_text()
            template_header = """# Development Workflow

This project uses background agents and Beads for task management.

"""
            agents_md.write_text(template_header + beads_content)
            console.print(f"[green]✓[/green] Created: {agents_md} (legacy template)")

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
        # Check prerequisites before installing hooks
        from devloop.cli.prerequisites import PrerequisiteChecker

        checker = PrerequisiteChecker()
        available, missing = checker.validate_for_git_hooks(interactive=True)

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

            # Show installation guide if prerequisites missing
            if missing:
                checker.show_installation_guide(missing)

    # Set up Claude Code hooks
    agents_hooks_dir = path / ".agents" / "hooks"
    agents_hooks_dir.mkdir(parents=True, exist_ok=True)

    # Define Claude hook scripts
    claude_hooks = {
        "claude-session-start": """#!/bin/bash
#
# SessionStart hook: Pre-load DevLoop findings when Claude Code starts
#
set -e
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" || exit 0
if command -v devloop &>/dev/null; then
    devloop amp_context 2>/dev/null || exit 0
fi
exit 0
""",
        "claude-stop": """#!/bin/bash
#
# Stop hook: Collect DevLoop findings when Claude finishes
#
set -e
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" || exit 0
if ! command -v devloop &>/dev/null; then
    exit 0
fi
input_json=$(cat)
stop_hook_active=$(echo "$input_json" | jq -r '.stop_hook_active // false' 2>/dev/null || echo "false")
if [ "$stop_hook_active" = "true" ]; then
    exit 0
fi
devloop amp_findings 2>/dev/null || true
exit 0
""",
        "claude-file-protection": """#!/bin/bash
#
# PreToolUse hook: Block modifications to protected files
#
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" || exit 0
input_json=$(cat)
tool_name=$(echo "$input_json" | jq -r '.tool_name // ""' 2>/dev/null || echo "")
tool_input=$(echo "$input_json" | jq -r '.tool_input // {}' 2>/dev/null || echo "{}")
if [[ "$tool_name" != "Write" && "$tool_name" != "Edit" ]]; then
    exit 0
fi
file_path=$(echo "$tool_input" | jq -r '.path // ""' 2>/dev/null || echo "")
if [ -n "$file_path" ]; then
    file_path=$(realpath "$file_path" 2>/dev/null || echo "$file_path")
fi
protected_patterns=(".beads/" ".devloop/" ".git/" ".agents/hooks/" ".claude/" "AGENTS.md" "CODING_RULES.md" "AMP_ONBOARDING.md")
is_protected=0
for pattern in "${protected_patterns[@]}"; do
    if [[ "$file_path" == *"$pattern"* ]]; then
        is_protected=1
        break
    fi
done
if [ $is_protected -eq 1 ]; then
    cat >&2 <<EOF
🚫 Protected file: $file_path
This file is protected by DevLoop to prevent accidental modifications.
If you need to modify this file, use manual editing or ask the user.
EOF
    exit 2
fi
exit 0
""",
    }

    # Create hook scripts
    hooks_created = []
    for hook_name, hook_content in claude_hooks.items():
        hook_file = agents_hooks_dir / hook_name
        if not hook_file.exists():
            hook_file.write_text(hook_content)
            hook_file.chmod(0o755)
            hooks_created.append(hook_name)

    if hooks_created:
        console.print("\n[green]✓[/green] Created Claude Code hooks:")
        for hook in hooks_created:
            console.print(f"  • {hook}")

        # Offer to install hooks to Claude settings (skip in non-interactive mode)
        install_hooks = True
        if not non_interactive:
            install_hooks = typer.confirm(
                "\nInstall Claude Code hooks to ~/.claude/settings.json?", default=True
            )

        if install_hooks:
            install_hook_script = agents_hooks_dir / "install-claude-hooks"
            if install_hook_script.exists():
                try:
                    result = subprocess.run(
                        [str(install_hook_script), str(path)],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if result.returncode == 0:
                        console.print("[green]✓[/green] Claude Code hooks installed")
                    else:
                        console.print("[yellow]⚠[/yellow] Could not auto-install hooks")
                        console.print("To install manually, run:")
                        console.print(f"  {install_hook_script} {path}")
                except Exception as e:
                    console.print(f"[yellow]⚠[/yellow] Hook installation error: {e}")
                    console.print("To install manually, run:")
                    console.print(f"  {install_hook_script} {path}")
    else:
        console.print("\n[green]✓[/green] Claude Code hooks already exist")

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
def daemon_status(path: Path = typer.Argument(Path.cwd(), help="Project directory")):
    """Check daemon health and status."""
    health_result = check_daemon_health(path)

    status = health_result["status"]
    emoji = {"HEALTHY": "✅", "UNHEALTHY": "❌", "ERROR": "⚠️"}.get(status, "❓")

    console.print(f"\n{emoji} Daemon Status: [bold]{status}[/bold]")
    console.print(f"Message: {health_result['message']}")

    if health_result.get("pid"):
        console.print(f"PID: {health_result['pid']}")
    if health_result.get("uptime_seconds"):
        uptime = health_result["uptime_seconds"]
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        console.print(f"Uptime: {hours}h {minutes}m")

    if not health_result["healthy"]:
        console.print("\n[yellow]Daemon may need to be restarted[/yellow]")
        console.print("Run: [cyan]devloop stop && devloop watch .[/cyan]")


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


@app.command()
def verify_work():
    """Run code quality verification (Claude Code equivalent to Amp post-task hook)."""
    from devloop.core.claude_adapter import ClaudeCodeAdapter

    adapter = ClaudeCodeAdapter()
    result = adapter.verify_and_extract()

    console.print("\n[bold]Code Quality Verification[/bold]")
    console.print("=" * 50)

    # Verification status
    verification = result.get("verification", {})
    if verification.get("verified"):
        console.print("[green]✅ All checks passed[/green]")
    else:
        console.print("[red]❌ Verification failed[/red]")
        if verification.get("blocking_issues"):
            console.print("\n[bold red]Blocking Issues:[/bold red]")
            for issue in verification["blocking_issues"]:
                console.print(f"  • {issue}")

    # Warnings
    if verification.get("warnings"):
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warning in verification["warnings"][:5]:  # Show first 5
            console.print(f"  • {warning}")
        if len(verification["warnings"]) > 5:
            console.print(f"  ... and {len(verification['warnings']) - 5} more")

    # Findings extraction
    extraction = result.get("extraction", {})
    if extraction.get("issues_created") > 0:
        console.print(
            f"\n[green]✅ Created {extraction['issues_created']} Beads issue(s)[/green]"
        )
        if extraction.get("issue_ids"):
            for issue_id in extraction["issue_ids"]:
                console.print(f"  • {issue_id}")
    else:
        console.print("\n[dim]No new Beads issues created[/dim]")

    console.print("\n[dim]Use 'bd ready' to see ready work[/dim]")


@app.command()
def extract_findings_cmd():
    """Extract DevLoop findings and create Beads issues."""
    from devloop.core.claude_adapter import ClaudeCodeAdapter

    adapter = ClaudeCodeAdapter()
    result = adapter.extract_findings()

    console.print("\n[bold]Findings Extraction[/bold]")
    console.print("=" * 50)

    if result.get("extracted"):
        console.print(
            f"[green]✅ {result.get('issues_created', 0)} Beads issue(s) created[/green]"
        )
        if result.get("issue_ids"):
            for issue_id in result["issue_ids"]:
                console.print(f"  • {issue_id}")
    else:
        console.print(
            f"[yellow]⚠️  {result.get('message', 'Could not extract findings')}[/yellow]"
        )

    console.print("\n[dim]Use 'bd ready' to see ready work[/dim]")


if __name__ == "__main__":
    app()
