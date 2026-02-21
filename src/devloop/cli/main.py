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
from .commands import insights as insights_cmd
from .commands import marketplace as marketplace_cmd
from .commands import mcp_server as mcp_server_cmd
from .commands import metrics as metrics_cmd
from .commands import release as release_cmd
from .commands import summary as summary_cmd
from .commands import telemetry as telemetry_cmd
from .commands import tools as tools_cmd

_typer_app = typer.Typer(
    help="DevLoop - Development workflow automation", add_completion=False
)
console = Console()

_typer_app.add_typer(summary_cmd.app, name="summary")
_typer_app.add_typer(custom_agents_cmd.app, name="custom")
_typer_app.add_typer(feedback_cmd.app, name="feedback")
_typer_app.add_typer(insights_cmd.app, name="insights")
_typer_app.add_typer(marketplace_cmd.app, name="agent")
_typer_app.add_typer(mcp_server_cmd.app, name="mcp-server")
_typer_app.add_typer(metrics_cmd.app, name="metrics")
_typer_app.add_typer(release_cmd.app, name="release")
_typer_app.add_typer(telemetry_cmd.app, name="telemetry")
_typer_app.add_typer(tools_cmd.app, name="tools")

# Wrap Typer app to handle Click-based audit command
# Note: We can't use add_typer with Click groups due to Typer version compatibility
_original_app = _typer_app


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


def _fork_to_background() -> None:
    """Fork the process to run in background. Exits parent process."""
    import os
    import sys

    try:
        pid = os.fork()
        if pid > 0:
            console.print(
                f"[green]✓[/green] DevLoop started in background (PID: {pid})"
            )
            console.print("[dim]Run 'devloop stop' to stop the daemon[/dim]")
            sys.exit(0)
    except OSError as e:
        console.print(f"[red]✗[/red] Failed to start daemon: {e}")
        sys.exit(1)


def _setup_daemon_environment(project_dir: Path, verbose: bool) -> None:
    """Setup daemon environment (detach from terminal, setup logging)."""
    import os

    os.chdir("/")
    os.setsid()
    os.umask(0)
    setup_logging_with_rotation(verbose, project_dir)


def _run_daemon_loop(project_dir: Path, config_path: Path | None) -> None:
    """Run the daemon main loop with PID file management."""
    import os

    pid_file = project_dir / ".devloop" / "devloop.pid"
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    print(f"DevLoop v2 daemon started (PID: {os.getpid()})")
    print(f"Watching: {project_dir}")

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
        if pid_file.exists():
            pid_file.unlink()


def run_daemon(path: Path, config_path: Path | None, verbose: bool):
    """Run devloop in daemon/background mode."""
    _fork_to_background()
    project_dir = path.resolve()
    _setup_daemon_environment(project_dir, verbose)
    _run_daemon_loop(project_dir, config_path)


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


def _load_watch_config(path: Path, config_path: Path | None) -> ConfigWrapper:
    """Load and validate watch configuration.

    Args:
        path: Project directory path
        config_path: Optional explicit config file path

    Returns:
        ConfigWrapper instance with loaded configuration

    Raises:
        SystemExit: On configuration errors (handled by error_handler)
    """
    error_handler = get_error_handler()

    try:
        if config_path:
            config_manager = Config(str(Path(config_path).resolve()))
        else:
            config_path_str = str((path / ".devloop" / "agents.json").resolve())
            if not Path(config_path_str).exists():
                error_handler.handle_startup_error(
                    ErrorCode.CONFIG_NOT_FOUND,
                    f"Configuration file not found: {config_path_str}",
                    severity=ErrorSeverity.CRITICAL,
                    details="Run 'devloop init' to create a default configuration.",
                )
            config_manager = Config(config_path_str)

        config_dict = config_manager.load()
        return ConfigWrapper(config_dict)
    except ValueError as e:
        error_handler.handle_startup_error(
            ErrorCode.CONFIG_INVALID,
            "Configuration validation failed",
            exception=e,
            severity=ErrorSeverity.CRITICAL,
        )
        raise  # Unreachable but satisfies type checker
    except Exception as e:
        error_handler.handle_startup_error(
            ErrorCode.CONFIG_INVALID,
            f"Failed to load configuration: {e}",
            exception=e,
            severity=ErrorSeverity.CRITICAL,
        )
        raise  # Unreachable but satisfies type checker


# Agent registry: maps agent names to (class, default_triggers, uses_name_param)
_AGENT_REGISTRY: dict[str, tuple[type, list[str], bool]] = {
    "linter": (LinterAgent, ["file:modified"], True),
    "formatter": (FormatterAgent, ["file:modified"], True),
    "test-runner": (TestRunnerAgent, ["file:modified"], True),
    "agent-health-monitor": (AgentHealthMonitorAgent, ["agent:*:completed"], True),
    "type-checker": (TypeCheckerAgent, [], False),
    "security-scanner": (SecurityScannerAgent, [], False),
    "git-commit-assistant": (GitCommitAssistantAgent, [], False),
    "performance-profiler": (PerformanceProfilerAgent, [], False),
    "snyk": (SnykAgent, ["file:modified", "file:created"], True),
    "code-rabbit": (CodeRabbitAgent, ["file:modified", "file:created"], True),
}


def _register_agents(
    config: ConfigWrapper, event_bus: EventBus, agent_manager: AgentManager
) -> None:
    """Register all enabled agents based on configuration.

    Uses a data-driven approach to reduce code duplication and complexity.

    Args:
        config: Configuration wrapper with agent settings
        event_bus: Event bus for agent communication
        agent_manager: Agent manager to register agents with
    """
    for agent_name, (
        agent_class,
        default_triggers,
        uses_name_param,
    ) in _AGENT_REGISTRY.items():
        if not config.is_agent_enabled(agent_name):
            continue

        agent_config = config.get_agent_config(agent_name) or {}
        triggers = agent_config.get("triggers", default_triggers)
        inner_config = agent_config.get("config", {})

        if uses_name_param:
            agent = agent_class(
                name=agent_name,
                triggers=triggers,
                event_bus=event_bus,
                config=inner_config,
            )
        else:
            agent = agent_class(config=inner_config, event_bus=event_bus)

        agent_manager.register(agent)


async def _initialize_stores(path: Path) -> None:
    """Initialize context and event stores.

    Args:
        path: Project directory path
    """
    context_store.context_dir = path / ".devloop" / "context"
    await context_store.initialize()

    event_store.db_path = path / ".devloop" / "events.db"
    await event_store.initialize()

    console.print(f"[dim]Context store: {context_store.context_dir}[/dim]")
    console.print(f"[dim]Event store: {event_store.db_path}[/dim]")


async def _replay_events(event_bus: EventBus, agent_manager: AgentManager) -> None:
    """Replay missed events and report gaps.

    Args:
        event_bus: Event bus for event replay
        agent_manager: Agent manager with registered agents
    """
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


async def _wait_for_shutdown() -> None:
    """Wait for shutdown signal (SIGINT or SIGTERM)."""
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    await shutdown_event.wait()


async def watch_async(path: Path, config_path: Path | None) -> None:
    """Async watch implementation.

    Watches the project directory for file changes and triggers agents accordingly.

    Args:
        path: Project directory to watch
        config_path: Optional path to configuration file
    """
    # Load configuration
    config = _load_watch_config(path, config_path)

    # Create event bus
    event_bus = EventBus()

    # Initialize transaction system (recovery and self-healing)
    initialize_transaction_system(path / ".devloop")

    # Initialize stores
    await _initialize_stores(path)

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

    # Register all enabled agents
    _register_agents(config, event_bus, agent_manager)

    # Start everything
    await fs_collector.start()
    await agent_manager.start_all()

    console.print("[green]✓[/green] Started agents:")
    for agent_name in agent_manager.list_agents():
        console.print(f"  • [cyan]{agent_name}[/cyan]")

    # Replay missed events
    await _replay_events(event_bus, agent_manager)

    console.print("\n[dim]Waiting for file changes... (Ctrl+C to stop)[/dim]\n")

    # Wait for shutdown signal
    await _wait_for_shutdown()

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


def _setup_devloop_directory(path: Path) -> Path:
    """Create and configure .devloop directory."""
    claude_dir = path / ".devloop"

    if claude_dir.exists():
        console.print(f"[yellow]Directory already exists: {claude_dir}[/yellow]")
        claude_dir.chmod(0o755)
    else:
        claude_dir.mkdir(parents=True, exist_ok=True)
        claude_dir.chmod(0o755)
        console.print(f"[green]✓[/green] Created: {claude_dir}")

    return claude_dir


def _read_init_manifest(claude_dir: Path) -> dict:
    """Read .devloop/.init-manifest.json, returning defaults if missing or invalid."""
    import json

    manifest_path = claude_dir / ".init-manifest.json"
    if not manifest_path.exists():
        return {"version": None, "managed": []}
    try:
        return json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"version": None, "managed": []}


def _write_init_manifest(claude_dir: Path, managed_files: list[str]) -> None:
    """Write init manifest with current version and managed file list."""
    import json

    from devloop import __version__

    manifest_path = claude_dir / ".init-manifest.json"
    manifest_path.write_text(
        json.dumps({"version": __version__, "managed": managed_files}, indent=2) + "\n"
    )


def _needs_upgrade(claude_dir: Path) -> bool:
    """Return True if manifest is missing, has no version, or version differs."""
    from devloop import __version__

    manifest = _read_init_manifest(claude_dir)
    return manifest.get("version") != __version__


def _setup_config(claude_dir: Path, skip_config: bool, non_interactive: bool) -> None:
    """Create default configuration."""
    if skip_config:
        return

    config_file = claude_dir / "agents.json"
    if config_file.exists():
        console.print(f"[yellow]Configuration already exists: {config_file}[/yellow]")
        return

    optional_agents = {}

    # Interactive prompts for optional agents
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
            from devloop.cli.coderabbit_installer import (
                prompt_coderabbit_installation,
            )

            prompt_coderabbit_installation(non_interactive=False)

        # CI Monitor prompt
        if typer.confirm(
            "Enable [yellow]CI Monitor[/yellow] agent to track CI/CD pipeline status?",
            default=False,
        ):
            optional_agents["ci-monitor"] = True
            console.print("  [green]✓[/green] CI Monitor agent enabled")

        # Pyodide WASM Sandbox
        from devloop.cli.pyodide_installer import prompt_pyodide_installation

        prompt_pyodide_installation(non_interactive=False)

    config = Config()
    config._config = config._get_default_config(optional_agents=optional_agents)
    config.save(config_file)
    console.print(f"\n[green]✓[/green] Created: {config_file}")


def _normalize_section_title(title: str) -> str:
    """Normalize a section title for comparison (lowercase, strip emoji/punctuation)."""
    import re

    title = title.lower().strip()
    # Strip leading emoji sequences and special chars like ⛔️, 🔧, etc.
    title = re.sub(r"^[\U0001f300-\U0001faff\u2600-\u27bf\ufe0f\s️]+", "", title)
    # Strip leading punctuation and whitespace
    title = re.sub(r"^[\W_]+", "", title)
    return title


def _merge_agents_md(existing_content: str, template_content: str) -> str:
    """Merge template sections into existing AGENTS.md without duplicating.

    Appends only sections from the template that don't already exist in the
    existing content (matched by normalized heading).  Existing content is
    preserved verbatim at the top so project-specific customizations are kept.
    """
    import re

    heading_re = re.compile(r"^(##)\s+(.+)$", re.MULTILINE)

    def _split_sections(text: str) -> list[tuple[str, str, str]]:
        """Split markdown into (raw_heading, normalized_title, body) tuples.

        The first tuple may have an empty heading (preamble before any heading).
        """
        parts: list[tuple[str, str, str]] = []
        matches = list(heading_re.finditer(text))
        if not matches:
            return [("", "", text)]

        # Preamble before first heading
        if matches[0].start() > 0:
            parts.append(("", "", text[: matches[0].start()]))

        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            raw_heading = m.group(0)
            title = m.group(2)
            body = text[m.end() : end]
            parts.append((raw_heading, _normalize_section_title(title), body))

        return parts

    existing_sections = _split_sections(existing_content)
    template_sections = _split_sections(template_content)

    existing_titles = {norm for _, norm, _ in existing_sections if norm}

    new_sections = [
        (heading, body)
        for heading, norm, body in template_sections
        if norm and norm not in existing_titles
    ]

    if not new_sections:
        return existing_content

    merged = existing_content.rstrip("\n")
    merged += "\n\n"
    for heading, body in new_sections:
        merged += heading + body

    return merged


def _check_missing_devloop_sections(content: str) -> list[tuple[str, str]]:
    """Check for missing DevLoop sections in AGENTS.md.

    Returns a list of (check_string, display_name) tuples for each missing section.
    """
    missing_sections: list[tuple[str, str]] = []

    # Each entry: (check_string, alt_check_strings, display_name)
    # The check_string is the canonical key used in _parse_template_sections.
    # alt_check_strings are additional strings that indicate the section is present
    # (e.g. from older template versions or hand-written AGENTS.md files).
    checks: list[tuple[str, list[str], str]] = [
        (
            "NO MARKDOWN FILES FOR PLANNING",
            ["NO MARKDOWN FILES"],
            "No markdown files rule",
        ),
        (
            "Task Management with Beads",
            ["BEADS FOR ALL TASK MANAGEMENT"],
            "Beads task management",
        ),
        (
            "Development Discipline",
            ["COMMIT & PUSH AFTER EVERY TASK"],
            "Development discipline",
        ),
        (
            "Pre-Flight Development Checklist",
            ["PRE-FLIGHT CHECKLIST"],
            "Pre-flight checklist",
        ),
        (
            "Documentation Practices",
            ["DOCUMENTATION PRACTICES"],
            "Documentation practices",
        ),
        ("Release Process", ["ESSENTIAL COMMANDS"], "Release process"),
    ]

    for check_str, alt_strs, display_name in checks:
        if check_str not in content and not any(s in content for s in alt_strs):
            missing_sections.append((check_str, display_name))

    # Special case for token security (multiple variants)
    if (
        "Secrets Management & Token Security" not in content
        and "Secrets Management" not in content
        and "TOKEN SECURITY" not in content
    ):
        missing_sections.append(
            ("Secrets Management & Token Security", "Token security")
        )

    # Special case for CI verification (multiple variants)
    if (
        "CI Verification" not in content
        and "Pre-Push Hook" not in content
        and "CI VERIFICATION" not in content
    ):
        missing_sections.append(("CI Verification", "CI verification (pre-push hook)"))

    return missing_sections


def _setup_agents_md(path: Path, claude_dir: Path) -> None:
    """Setup AGENTS.md file."""
    import shutil

    agents_md = path / "AGENTS.md"
    devloop_template = (
        Path(__file__).parent / "templates" / "devloop_agents_template.md"
    )
    beads_template = claude_dir / "beads_template.md"

    if agents_md.exists():
        content = agents_md.read_text()
        missing_sections = _check_missing_devloop_sections(content)

        if missing_sections:
            template_content = devloop_template.read_text()
            merged = _merge_agents_md(content, template_content)
            agents_md.write_text(merged)
            console.print(
                "[green]✓[/green] Merged missing DevLoop sections into AGENTS.md"
            )
    else:
        # Create new AGENTS.md from template
        if devloop_template.exists():
            shutil.copy(devloop_template, agents_md)
            console.print(
                f"[green]✓[/green] Created: {agents_md} (from DevLoop template)"
            )
        elif beads_template.exists():
            beads_content = beads_template.read_text()
            template_header = """# Development Workflow

This project uses background agents and Beads for task management.

"""
            agents_md.write_text(template_header + beads_content)
            console.print(f"[green]✓[/green] Created: {agents_md} (legacy template)")


def _setup_claude_md(path: Path) -> None:
    """Setup CLAUDE.md symlink."""
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
        try:
            claude_md.symlink_to("AGENTS.md")
            console.print(f"[green]✓[/green] Created: {claude_md} -> AGENTS.md")
        except Exception as e:
            console.print(
                f"[yellow]Warning:[/yellow] Could not create CLAUDE.md symlink: {e}"
            )


def _setup_claude_commands(path: Path) -> tuple[list[str], int]:
    """Setup Claude Code slash commands.

    Returns:
        Tuple of (managed_paths, updated_count) where managed_paths are
        relative paths like ".claude/commands/verify-work.md" and
        updated_count is the number of existing files that were overwritten.
    """
    import shutil

    claude_commands_dir = path / ".claude" / "commands"
    template_commands_dir = Path(__file__).parent / "templates" / "claude_commands"

    if not template_commands_dir.exists():
        return [], 0

    claude_commands_dir.mkdir(parents=True, exist_ok=True)

    managed_paths: list[str] = []
    updated_count = 0
    for template_file in template_commands_dir.glob("*.md"):
        dest_file = claude_commands_dir / template_file.name
        if dest_file.exists():
            # Back up the existing file before overwriting
            backup_file = dest_file.with_suffix(".md.backup")
            shutil.copy2(dest_file, backup_file)
            updated_count += 1
        shutil.copy2(template_file, dest_file)
        managed_paths.append(f".claude/commands/{template_file.name}")

    new_count = len(managed_paths) - updated_count
    if managed_paths:
        if updated_count:
            console.print(f"\n[green]✓[/green] Updated {updated_count} command(s)")
        if new_count:
            console.print(f"\n[green]✓[/green] Created {new_count} command(s)")

    return managed_paths, updated_count


def _setup_git_hooks(path: Path) -> None:
    """Setup git hooks."""
    import shutil

    git_dir = path / ".git"
    if not (git_dir.exists() and git_dir.is_dir()):
        return

    from devloop.cli.prerequisites import PrerequisiteChecker

    checker = PrerequisiteChecker()
    available, missing = checker.validate_for_git_hooks(interactive=True)

    hooks_template_dir = Path(__file__).parent / "templates" / "git_hooks"
    hooks_dest_dir = git_dir / "hooks"

    if not hooks_template_dir.exists():
        return

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


def _create_claude_hooks(agents_hooks_dir: Path) -> list:
    """Create Claude Code hook scripts."""
    hooks = {
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
        "check-devloop-context": """#!/bin/bash
#
# PreToolUse hook: Check for unreviewed DevLoop findings before file operations
#
# Fast (<100ms) hook that warns about agent findings before file ops.
# Includes debouncing (warns at most once per 30 seconds) to avoid spam.
#
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" || exit 0

# Debounce settings
DEBOUNCE_SECONDS=30
DEBOUNCE_FILE="/tmp/devloop-context-warned-${PPID:-$$}"

# Check if we've warned recently
if [[ -f "$DEBOUNCE_FILE" ]]; then
    LAST_WARN=$(cat "$DEBOUNCE_FILE" 2>/dev/null || echo "0")
    NOW=$(date +%s)
    ELAPSED=$((NOW - LAST_WARN))
    if [[ $ELAPSED -lt $DEBOUNCE_SECONDS ]]; then
        exit 0
    fi
fi

# Consume stdin
cat > /dev/null

# Fast check: Does context exist? Prefer .last_update marker (fastest)
CONTEXT_DIR="$PROJECT_DIR/.devloop/context"
MARKER_FILE="$CONTEXT_DIR/.last_update"
CONTEXT_INDEX="$CONTEXT_DIR/index.json"

if [[ -f "$MARKER_FILE" ]]; then
    CHECK_FILE="$MARKER_FILE"
elif [[ -f "$CONTEXT_INDEX" ]]; then
    CHECK_FILE="$CONTEXT_INDEX"
else
    exit 0
fi

# Fast check: Is context stale (>30 min)?
if [[ "$OSTYPE" == "darwin"* ]]; then
    LAST_UPDATED=$(stat -f %m "$CHECK_FILE" 2>/dev/null || echo "0")
else
    LAST_UPDATED=$(stat -c %Y "$CHECK_FILE" 2>/dev/null || echo "0")
fi
NOW=$(date +%s)
AGE_SECONDS=$((NOW - LAST_UPDATED))
if [[ $AGE_SECONDS -gt 1800 ]]; then
    exit 0
fi

# Quick grep for check_now count
CHECK_NOW_COUNT=$(grep -o '"check_now"[^}]*"count": [0-9]*' "$CONTEXT_INDEX" 2>/dev/null | grep -o '[0-9]*$' || echo "0")

if [[ "$CHECK_NOW_COUNT" -gt 0 ]]; then
    date +%s > "$DEBOUNCE_FILE"
    cat >&2 <<EOF
DevLoop: $CHECK_NOW_COUNT agent finding(s) need attention.
Run /agent-summary for details before continuing.
EOF
fi

exit 0
""",
        "claude-post-tool-use": """#!/bin/bash
#
# PostToolUse hook: Show relevant findings after file modifications
#
# Shows existing findings for the edited file after Edit/Write completes.
# Silent when no findings exist.
#
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" || exit 0

INPUT_FILE=$(mktemp)
cat > "$INPUT_FILE"
export INPUT_FILE PROJECT_DIR

python3 << 'PYTHON_EOF'
import json
import os
import sys
from pathlib import Path

def get_findings_for_file(file_path, context_dir):
    findings = []
    try:
        target_path = Path(file_path).resolve()
    except (OSError, ValueError):
        return []
    for tier in ["immediate", "relevant"]:
        tier_file = context_dir / f"{tier}.json"
        if not tier_file.exists():
            continue
        try:
            data = json.loads(tier_file.read_text())
            for finding in data.get("findings", []):
                finding_file = finding.get("file", "")
                if not finding_file:
                    continue
                try:
                    if Path(finding_file).resolve() == target_path:
                        findings.append(finding)
                except (OSError, ValueError):
                    continue
        except (json.JSONDecodeError, OSError):
            continue
    severity_order = {"error": 0, "warning": 1, "info": 2, "style": 3}
    return sorted(findings, key=lambda f: (severity_order.get(f.get("severity", "info"), 2), f.get("line") or 9999))

def format_output(findings, file_path):
    if not findings:
        return ""
    file_name = Path(file_path).name
    count = len(findings)
    lines = [f"\\u26a0\\ufe0f {count} issue{'s' if count != 1 else ''} in {file_name}:"]
    top = findings[0]
    line_num = top.get("line")
    message = top.get("message", "Unknown issue")
    agent = top.get("agent", "")
    location = f"Line {line_num}: " if line_num else ""
    source = f" [{agent}]" if agent else ""
    lines.append(f"  \\u2022 {location}{message}{source}")
    if count > 2:
        lines.append(f"  ... and {count - 1} more")
    elif count == 2:
        second = findings[1]
        line_num = second.get("line")
        message = second.get("message", "Unknown issue")
        agent = second.get("agent", "")
        location = f"Line {line_num}: " if line_num else ""
        source = f" [{agent}]" if agent else ""
        lines.append(f"  \\u2022 {location}{message}{source}")
    return "\\n".join(lines)

input_file = os.environ.get("INPUT_FILE", "")
project_dir = Path(os.environ.get("PROJECT_DIR", "."))
if not input_file:
    sys.exit(0)
try:
    with open(input_file) as f:
        input_data = f.read()
    if not input_data.strip():
        sys.exit(0)
    hook_input = json.loads(input_data)
except (json.JSONDecodeError, OSError):
    sys.exit(0)
tool_name = hook_input.get("tool_name", "")
if tool_name not in ["Edit", "Write"]:
    sys.exit(0)
tool_input = hook_input.get("tool_input", {})
if not isinstance(tool_input, dict):
    sys.exit(0)
file_path = tool_input.get("file_path") or tool_input.get("path", "")
if not file_path:
    sys.exit(0)
context_dir = project_dir / ".devloop" / "context"
if not context_dir.exists():
    sys.exit(0)
findings = get_findings_for_file(file_path, context_dir)
if findings:
    output = format_output(findings, file_path)
    if output:
        print(output)
PYTHON_EOF

rm -f "$INPUT_FILE"
exit 0
""",
    }

    managed_paths = []
    updated_count = 0
    for hook_name, hook_content in hooks.items():
        hook_file = agents_hooks_dir / hook_name
        if hook_file.exists():
            # Back up the existing file before overwriting
            backup_file = hook_file.with_suffix(".backup")
            backup_file.write_text(hook_file.read_text())
            updated_count += 1
        hook_file.write_text(hook_content)
        hook_file.chmod(0o755)
        managed_paths.append(f".agents/hooks/{hook_name}")

    return managed_paths, updated_count


def _create_claude_settings_json(path: Path, upgrade: bool = False) -> str | None:
    """Create project-level .claude/settings.json with hook registrations.

    This registers hooks at the project level so they work automatically
    when Claude Code is used in this project.

    Args:
        path: Project root directory
        upgrade: When True, overwrite the entire hooks section with the new
            template.  When False, only add missing hook event types.

    Returns:
        ".claude/settings.json" if the file was created or updated, None if
        unchanged.  The string is a relative path suitable for the init manifest.
    """
    import json

    claude_dir = path / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings_file = claude_dir / "settings.json"

    # Hook configuration using relative paths from project root
    new_hooks = {
        "SessionStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": ".agents/hooks/claude-session-start",
                    }
                ],
            }
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": ".agents/hooks/claude-stop",
                    }
                ],
            }
        ],
        "PreToolUse": [
            {
                "matcher": "Write|Edit",
                "hooks": [
                    {
                        "type": "command",
                        "command": ".agents/hooks/claude-file-protection",
                    },
                    {
                        "type": "command",
                        "command": ".agents/hooks/check-devloop-context",
                    },
                ],
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Edit|Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": ".agents/hooks/claude-post-tool-use",
                    }
                ],
            }
        ],
    }

    # Load existing settings if present
    existing_settings = {}
    if settings_file.exists():
        try:
            with open(settings_file) as f:
                existing_settings = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    changed = False

    if upgrade:
        # On upgrade, replace the entire hooks section with the new template
        # but preserve all non-hooks settings (e.g. "permissions")
        if existing_settings.get("hooks") != new_hooks:
            existing_settings["hooks"] = new_hooks
            changed = True
    else:
        # Only add hook event types that don't already exist
        if "hooks" not in existing_settings:
            existing_settings["hooks"] = {}

        for hook_name, hook_config in new_hooks.items():
            if hook_name not in existing_settings["hooks"]:
                existing_settings["hooks"][hook_name] = hook_config
                changed = True

    if changed:
        with open(settings_file, "w") as f:
            json.dump(existing_settings, f, indent=2)
            f.write("\n")
        return ".claude/settings.json"

    return None


def _setup_mcp_server(path: Path) -> None:
    """Register MCP server with Claude Code if settings exist.

    This auto-registers the devloop MCP server in ~/.claude/settings.json
    so that Claude Code can use devloop's MCP tools.

    Args:
        path: Project root directory (unused, but kept for consistency)
    """
    from devloop.cli.commands.mcp_server import (
        get_claude_settings_path,
        install_mcp_server,
    )

    settings_path = get_claude_settings_path()

    # Only register if Claude Code settings directory exists
    if not settings_path.parent.exists():
        return

    try:
        install_mcp_server()
        console.print(
            "[green]✓[/green] MCP server registered for Claude Code integration"
        )
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not register MCP server: {e}")


def _setup_claude_hooks(
    path: Path, agents_hooks_dir: Path, non_interactive: bool, upgrade: bool = False
) -> list:
    """Setup Claude Code hooks.

    Args:
        path: Project root directory.
        agents_hooks_dir: Directory for agent hook scripts.
        non_interactive: Skip interactive prompts.
        upgrade: When True, overwrite hooks in settings.json with new template.

    Returns:
        List of relative managed paths (e.g. [".agents/hooks/claude-session-start", ...]).
    """
    managed_paths, updated_count = _create_claude_hooks(agents_hooks_dir)
    new_count = len(managed_paths) - updated_count

    if managed_paths:
        if updated_count:
            console.print(f"\n[green]✓[/green] Updated {updated_count} hook script(s)")
        if new_count:
            console.print(f"\n[green]✓[/green] Created {new_count} hook script(s)")

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

    # Create project-level .claude/settings.json with hook registrations
    settings_path = _create_claude_settings_json(path, upgrade=upgrade)
    if settings_path:
        managed_paths.append(settings_path)
        console.print(
            "[green]✓[/green] Created .claude/settings.json with hook registrations"
        )

    return managed_paths


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
    import shutil

    # Setup .devloop directory
    claude_dir = _setup_devloop_directory(path)

    # Read old manifest and check if upgrade is needed
    old_manifest = _read_init_manifest(claude_dir)
    upgrade = _needs_upgrade(claude_dir)

    # Create default configuration
    _setup_config(claude_dir, skip_config, non_interactive)

    # Setup AGENTS.md with DevLoop template
    _setup_agents_md(path, claude_dir)

    # Setup CLAUDE.md symlink
    _setup_claude_md(path)

    # Setup Claude Code slash commands — collect managed paths
    managed_files: list[str] = []
    cmd_paths, _cmd_updated = _setup_claude_commands(path)
    managed_files.extend(cmd_paths)

    # Setup git hooks (managed separately by update-hooks, not tracked in manifest)
    _setup_git_hooks(path)

    # Setup Claude Code hooks — collect managed paths
    agents_hooks_dir = path / ".agents" / "hooks"
    agents_hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_paths = _setup_claude_hooks(
        path, agents_hooks_dir, non_interactive, upgrade=upgrade
    )
    managed_files.extend(hook_paths)

    # Register MCP server with Claude Code
    _setup_mcp_server(path)

    # Clean up stale files from previous init
    stale = set(old_manifest.get("managed", [])) - set(managed_files)
    for stale_rel in sorted(stale):
        stale_path = path / stale_rel
        if stale_path.exists():
            backup_path = stale_path.with_suffix(".backup")
            shutil.copy2(stale_path, backup_path)
            stale_path.unlink()
            console.print(f"Removed stale: {stale_rel}")

    # Write new manifest
    _write_init_manifest(claude_dir, managed_files)

    # Print upgrade summary if applicable
    if upgrade and old_manifest.get("version"):
        from devloop import __version__

        console.print(f"\nUpdated from v{old_manifest['version']} → v{__version__}")

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


def _install_hook_from_template(
    template_file: Path, hooks_dest_dir: Path
) -> str | None:
    """Install a single hook from template. Returns hook name if installed."""
    import shutil

    if not template_file.is_file():
        return None

    dest_file = hooks_dest_dir / template_file.name

    if dest_file.exists():
        backup_file = hooks_dest_dir / f"{template_file.name}.backup"
        shutil.copy2(dest_file, backup_file)
        console.print(
            f"[dim]  Backed up existing hook: {template_file.name} -> {template_file.name}.backup[/dim]"
        )

    shutil.copy2(template_file, dest_file)
    dest_file.chmod(0o755)
    return template_file.name


@app.command()
def update_hooks(path: Path = typer.Argument(Path.cwd(), help="Project directory")):
    """Update git hooks from latest templates."""
    git_dir = path / ".git"

    if not git_dir.exists() or not git_dir.is_dir():
        console.print(
            f"[red]✗[/red] Not a git repository: {path}\n"
            "[yellow]Git hooks can only be installed in git repositories.[/yellow]"
        )
        return

    hooks_template_dir = Path(__file__).parent / "templates" / "git_hooks"
    if not hooks_template_dir.exists():
        console.print(f"[red]✗[/red] Hook templates not found at: {hooks_template_dir}")
        return

    hooks_dest_dir = git_dir / "hooks"
    hooks_dest_dir.mkdir(parents=True, exist_ok=True)

    hooks_updated = [
        name
        for template in hooks_template_dir.iterdir()
        if (name := _install_hook_from_template(template, hooks_dest_dir))
    ]

    if hooks_updated:
        console.print("\n[green]✓[/green] Updated git hooks:")
        for hook in hooks_updated:
            console.print(f"  • {hook}")
    else:
        console.print("[yellow]No hooks found to update[/yellow]")


def _display_verification_status(verification: dict) -> None:
    """Display verification pass/fail status and blocking issues."""
    if verification.get("verified"):
        console.print("[green]✅ All checks passed[/green]")
        return

    console.print("[red]❌ Verification failed[/red]")
    if verification.get("blocking_issues"):
        console.print("\n[bold red]Blocking Issues:[/bold red]")
        for issue in verification["blocking_issues"]:
            console.print(f"  • {issue}")


def _display_warnings(warnings: list, max_display: int = 5) -> None:
    """Display warnings with truncation."""
    if not warnings:
        return

    console.print("\n[bold yellow]Warnings:[/bold yellow]")
    for warning in warnings[:max_display]:
        console.print(f"  • {warning}")
    if len(warnings) > max_display:
        console.print(f"  ... and {len(warnings) - max_display} more")


def _display_extraction_results(extraction: dict) -> None:
    """Display findings extraction results."""
    issues_created = extraction.get("issues_created", 0)
    if issues_created > 0:
        console.print(f"\n[green]✅ Created {issues_created} Beads issue(s)[/green]")
        for issue_id in extraction.get("issue_ids", []):
            console.print(f"  • {issue_id}")
    else:
        console.print("\n[dim]No new Beads issues created[/dim]")


@app.command()
def verify_work():
    """Run code quality verification (Claude Code equivalent to Amp post-task hook)."""
    from devloop.core.claude_adapter import ClaudeCodeAdapter

    adapter = ClaudeCodeAdapter()
    result = adapter.verify_and_extract()

    console.print("\n[bold]Code Quality Verification[/bold]")
    console.print("=" * 50)

    verification = result.get("verification", {})
    _display_verification_status(verification)
    _display_warnings(verification.get("warnings", []))
    _display_extraction_results(result.get("extraction", {}))

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
