"""DevLoop doctor - diagnostic command for validating installation health."""

import json
import os
import subprocess
from pathlib import Path
from typing import List, Tuple

import typer
from rich.console import Console

app = typer.Typer(
    help="Diagnose DevLoop installation health", invoke_without_command=True
)
console = Console()


def _check_devloop_init(project_dir: Path) -> Tuple[bool, str]:
    """Check if devloop is initialized."""
    devloop_dir = project_dir / ".devloop"
    if not devloop_dir.exists():
        return False, "Not initialized. Run 'devloop init'"
    config_file = devloop_dir / "agents.json"
    if not config_file.exists():
        return False, ".devloop exists but agents.json missing"
    return True, "Initialized"


def _check_config_valid(project_dir: Path) -> Tuple[bool, str]:
    """Validate config schema."""
    config_file = project_dir / ".devloop" / "agents.json"
    if not config_file.exists():
        return False, "agents.json not found"
    try:
        with open(config_file) as f:
            config = json.load(f)

        from devloop.core.config_schema import validate_config

        errors = validate_config(config, fail_fast=False)
        if errors:
            return False, f"{len(errors)} validation error(s)"
        return True, f"Valid (v{config.get('version', '?')})"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def _check_daemon(project_dir: Path) -> Tuple[bool, str]:
    """Check if daemon is running and healthy."""
    pid_file = project_dir / ".devloop" / "devloop.pid"
    if not pid_file.exists():
        return False, "Not running"
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)

        # Check heartbeat freshness
        heartbeat_file = project_dir / ".devloop" / "daemon.heartbeat"
        if heartbeat_file.exists():
            import time

            age = time.time() - heartbeat_file.stat().st_mtime
            if age > 120:
                return False, f"PID {pid} alive but heartbeat stale ({int(age)}s ago)"
            return True, f"Running (PID {pid}, heartbeat {int(age)}s ago)"
        return True, f"Running (PID {pid}, no heartbeat file)"
    except (ValueError, ProcessLookupError):
        return False, "PID file exists but process is dead"
    except PermissionError:
        return True, "Running (PID, permission denied on signal check)"


def _check_hook_scripts(project_dir: Path) -> List[Tuple[bool, str, str]]:
    """Check hook scripts exist and are executable."""
    hooks_dir = project_dir / ".agents" / "hooks"
    expected_hooks = [
        "claude-session-start",
        "claude-stop",
        "claude-file-protection",
        "check-devloop-context",
        "claude-post-tool-use",
    ]

    results = []
    for hook_name in expected_hooks:
        hook_path = hooks_dir / hook_name
        if not hook_path.exists():
            results.append((False, hook_name, "Missing"))
        elif not os.access(hook_path, os.X_OK):
            results.append((False, hook_name, "Not executable"))
        else:
            results.append((True, hook_name, "OK"))
    return results


def _check_settings_json(project_dir: Path) -> Tuple[bool, str]:
    """Check .claude/settings.json has hooks registered."""
    settings_file = project_dir / ".claude" / "settings.json"
    if not settings_file.exists():
        return False, "Missing .claude/settings.json"
    try:
        with open(settings_file) as f:
            settings = json.load(f)
        hooks = settings.get("hooks", {})
        expected_events = ["SessionStart", "Stop", "PreToolUse", "PostToolUse"]
        missing = [e for e in expected_events if e not in hooks]
        if missing:
            return False, f"Missing hook events: {', '.join(missing)}"
        return True, f"All {len(expected_events)} hook events registered"
    except json.JSONDecodeError:
        return False, "Invalid JSON in settings.json"


def _check_hook_execution(project_dir: Path) -> List[Tuple[bool, str, str]]:
    """Test-run each hook script to verify they execute without errors."""
    hooks_dir = project_dir / ".agents" / "hooks"
    results = []

    test_hooks = [
        ("claude-session-start", ""),
        ("check-devloop-context", '{"tool_name":"Edit","tool_input":{}}'),
    ]

    for hook_name, stdin_data in test_hooks:
        hook_path = hooks_dir / hook_name
        if not hook_path.exists():
            results.append((False, hook_name, "Missing"))
            continue
        try:
            proc = subprocess.run(
                [str(hook_path)],
                cwd=str(project_dir),
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=5,
                env={**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir)},
            )
            if proc.returncode == 0:
                results.append((True, hook_name, "Executes OK"))
            else:
                stderr_snippet = proc.stderr.strip()[:80] if proc.stderr else ""
                results.append(
                    (False, hook_name, f"Exit code {proc.returncode}: {stderr_snippet}")
                )
        except subprocess.TimeoutExpired:
            results.append((False, hook_name, "Timed out (>5s)"))
        except Exception as e:
            results.append((False, hook_name, f"Error: {e}"))

    return results


def _check_tool(name: str, cmd: List[str]) -> Tuple[bool, str]:
    """Check if a tool is available and get its version."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        version = result.stdout.strip().split("\n")[0][:60]
        return True, version
    except FileNotFoundError:
        return False, "Not installed"
    except subprocess.TimeoutExpired:
        return False, "Timed out"
    except Exception as e:
        return False, f"Error: {e}"


def _check_context_store(project_dir: Path) -> Tuple[bool, str]:
    """Check context store is present and writable."""
    context_dir = project_dir / ".devloop" / "context"
    if not context_dir.exists():
        return False, "Context directory missing"
    if not os.access(context_dir, os.W_OK):
        return False, "Context directory not writable"

    # Check for index
    index_file = context_dir / "index.json"
    if index_file.exists():
        try:
            with open(index_file) as f:
                data = json.load(f)
            return True, f"OK ({len(data.get('findings', {}))} finding categories)"
        except Exception:
            return True, "Writable (index unreadable)"
    return True, "Writable (no index yet)"


@app.callback(invoke_without_command=True)
def check(
    path: Path = typer.Argument(Path.cwd(), help="Project directory"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed check output"
    ),
    fix: bool = typer.Option(
        False, "--fix", help="Attempt to fix issues automatically"
    ),
):
    """Run comprehensive health checks on DevLoop installation.

    Validates: initialization, config, daemon, hooks, tools, and context store.
    """
    project_dir = path.resolve()

    console.print(f"\n[bold]🩺 DevLoop Doctor[/bold]  —  {project_dir}\n")

    all_passed = True
    issues: List[str] = []

    # 1. Initialization
    ok, msg = _check_devloop_init(project_dir)
    _print_check("Initialization", ok, msg)
    if not ok:
        all_passed = False
        issues.append("Run 'devloop init' to initialize")
        if fix:
            console.print(
                "  [cyan]→ Running 'devloop init --non-interactive'...[/cyan]"
            )
            subprocess.run(
                ["devloop", "init", str(project_dir), "--non-interactive"],
                capture_output=True,
            )

    # 2. Config validation
    ok, msg = _check_config_valid(project_dir)
    _print_check("Config schema", ok, msg)
    if not ok:
        all_passed = False
        issues.append("Fix agents.json configuration")

    # 3. Daemon status
    ok, msg = _check_daemon(project_dir)
    _print_check("Watch daemon", ok, msg)
    if not ok:
        all_passed = False
        issues.append("Start daemon with 'devloop watch .'")
        if fix:
            console.print("  [cyan]→ Starting daemon...[/cyan]")
            subprocess.run(
                ["devloop", "watch", str(project_dir)],
                capture_output=True,
            )

    # 4. Hook scripts
    console.print()
    hook_results = _check_hook_scripts(project_dir)
    hook_all_ok = all(ok for ok, _, _ in hook_results)
    _print_check(
        "Hook scripts",
        hook_all_ok,
        f"{sum(1 for ok, _, _ in hook_results if ok)}/{len(hook_results)} present & executable",
    )
    if verbose or not hook_all_ok:
        for ok, name, msg in hook_results:
            _print_subcheck(name, ok, msg)
            if not ok:
                all_passed = False

    # 5. Settings.json registration
    ok, msg = _check_settings_json(project_dir)
    _print_check("Hook registration", ok, msg)
    if not ok:
        all_passed = False
        issues.append("Re-run 'devloop init' to register hooks")

    # 6. Hook execution test
    exec_results = _check_hook_execution(project_dir)
    exec_all_ok = all(ok for ok, _, _ in exec_results)
    _print_check(
        "Hook execution",
        exec_all_ok,
        f"{sum(1 for ok, _, _ in exec_results if ok)}/{len(exec_results)} hooks execute cleanly",
    )
    if verbose or not exec_all_ok:
        for ok, name, msg in exec_results:
            _print_subcheck(name, ok, msg)
            if not ok:
                all_passed = False

    # 7. Required tools
    console.print()
    tools = [
        ("python3", ["python3", "--version"]),
        ("black", ["black", "--version"]),
        ("ruff", ["ruff", "--version"]),
        ("mypy", ["mypy", "--version"]),
        ("pytest", ["pytest", "--version"]),
        ("jq", ["jq", "--version"]),
    ]
    tool_results = [(name, *_check_tool(name, cmd)) for name, cmd in tools]
    tools_ok = all(ok for _, ok, _ in tool_results)
    _print_check(
        "Required tools",
        tools_ok,
        f"{sum(1 for _, ok, _ in tool_results if ok)}/{len(tool_results)} available",
    )
    if not tools_ok:
        all_passed = False
        missing_tools = [name for name, ok, _ in tool_results if not ok]
        issues.append(f"Install missing tools: {', '.join(missing_tools)}")
    if verbose or not tools_ok:
        for name, ok, msg in tool_results:
            _print_subcheck(name, ok, msg)

    # 8. Context store
    ok, msg = _check_context_store(project_dir)
    _print_check("Context store", ok, msg)
    if not ok:
        all_passed = False

    # Summary
    console.print()
    if all_passed:
        console.print("[bold green]✅ All checks passed[/bold green]")
    else:
        console.print(f"[bold red]❌ {len(issues)} issue(s) found[/bold red]")
        if issues:
            console.print("\n[bold]Suggested fixes:[/bold]")
            for i, issue in enumerate(issues, 1):
                console.print(f"  {i}. {issue}")
        if not fix:
            console.print("\n[dim]Run with --fix to attempt automatic fixes[/dim]")

    raise typer.Exit(code=0 if all_passed else 1)


def _print_check(name: str, ok: bool, msg: str) -> None:
    """Print a top-level check result."""
    emoji = "✅" if ok else "❌"
    style = "green" if ok else "red"
    console.print(f"  {emoji} [bold]{name}[/bold]: [{style}]{msg}[/{style}]")


def _print_subcheck(name: str, ok: bool, msg: str) -> None:
    """Print a sub-check result (indented)."""
    emoji = "✓" if ok else "✗"
    style = "green" if ok else "red"
    console.print(f"       [{style}]{emoji} {name}: {msg}[/{style}]")
