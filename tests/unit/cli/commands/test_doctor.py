"""Tests for devloop doctor command."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from devloop.cli.commands.doctor import (
    _check_config_valid,
    _check_context_store,
    _check_daemon,
    _check_devloop_init,
    _check_hook_scripts,
    _check_settings_json,
    _check_tool,
    app,
)


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def temp_project_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def initialized_project(temp_project_dir):
    """Create a fully initialized project directory."""
    devloop_dir = temp_project_dir / ".devloop"
    devloop_dir.mkdir()

    # Config
    config = {
        "version": "1.1.0",
        "enabled": True,
        "agents": {},
        "global": {"mode": "report-only"},
        "eventSystem": {},
    }
    (devloop_dir / "agents.json").write_text(json.dumps(config))

    # Context store
    context_dir = devloop_dir / "context"
    context_dir.mkdir()

    # Hook scripts
    hooks_dir = temp_project_dir / ".agents" / "hooks"
    hooks_dir.mkdir(parents=True)
    for hook_name in [
        "claude-session-start",
        "claude-stop",
        "claude-file-protection",
        "check-devloop-context",
        "claude-post-tool-use",
    ]:
        hook_file = hooks_dir / hook_name
        hook_file.write_text("#!/bin/bash\nexit 0\n")
        hook_file.chmod(0o755)

    # Settings.json
    claude_dir = temp_project_dir / ".claude"
    claude_dir.mkdir()
    settings = {
        "hooks": {
            "SessionStart": [],
            "Stop": [],
            "PreToolUse": [],
            "PostToolUse": [],
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings))

    return temp_project_dir


class TestCheckDevloopInit:
    def test_not_initialized(self, temp_project_dir):
        ok, msg = _check_devloop_init(temp_project_dir)
        assert not ok
        assert "Not initialized" in msg

    def test_initialized(self, initialized_project):
        ok, msg = _check_devloop_init(initialized_project)
        assert ok

    def test_missing_config(self, temp_project_dir):
        (temp_project_dir / ".devloop").mkdir()
        ok, msg = _check_devloop_init(temp_project_dir)
        assert not ok
        assert "agents.json missing" in msg


class TestCheckConfigValid:
    def test_valid_config(self, initialized_project):
        ok, msg = _check_config_valid(initialized_project)
        assert ok

    def test_missing_config(self, temp_project_dir):
        ok, msg = _check_config_valid(temp_project_dir)
        assert not ok

    def test_invalid_json(self, temp_project_dir):
        devloop_dir = temp_project_dir / ".devloop"
        devloop_dir.mkdir()
        (devloop_dir / "agents.json").write_text("{bad json")
        ok, msg = _check_config_valid(temp_project_dir)
        assert not ok
        assert "Invalid JSON" in msg


class TestCheckDaemon:
    def test_no_pid_file(self, initialized_project):
        ok, msg = _check_daemon(initialized_project)
        assert not ok
        assert "Not running" in msg

    def test_dead_process(self, initialized_project):
        pid_file = initialized_project / ".devloop" / "devloop.pid"
        pid_file.write_text("999999999")
        ok, msg = _check_daemon(initialized_project)
        assert not ok
        assert "dead" in msg


class TestCheckHookScripts:
    def test_all_present(self, initialized_project):
        results = _check_hook_scripts(initialized_project)
        assert all(ok for ok, _, _ in results)

    def test_missing_hook(self, initialized_project):
        hook = initialized_project / ".agents" / "hooks" / "claude-session-start"
        hook.unlink()
        results = _check_hook_scripts(initialized_project)
        missing = [name for ok, name, _ in results if not ok]
        assert "claude-session-start" in missing

    def test_not_executable(self, initialized_project):
        hook = initialized_project / ".agents" / "hooks" / "claude-stop"
        hook.chmod(0o644)
        results = _check_hook_scripts(initialized_project)
        failed = {name: msg for ok, name, msg in results if not ok}
        assert "claude-stop" in failed
        assert "Not executable" in failed["claude-stop"]


class TestCheckSettingsJson:
    def test_valid_settings(self, initialized_project):
        ok, msg = _check_settings_json(initialized_project)
        assert ok

    def test_missing_settings(self, temp_project_dir):
        ok, msg = _check_settings_json(temp_project_dir)
        assert not ok

    def test_missing_hook_events(self, initialized_project):
        settings_file = initialized_project / ".claude" / "settings.json"
        settings = {"hooks": {"SessionStart": []}}
        settings_file.write_text(json.dumps(settings))
        ok, msg = _check_settings_json(initialized_project)
        assert not ok
        assert "Missing hook events" in msg


class TestCheckTool:
    def test_available_tool(self):
        ok, msg = _check_tool("python3", ["python3", "--version"])
        assert ok
        assert "Python" in msg or "python" in msg.lower()

    def test_missing_tool(self):
        ok, msg = _check_tool("nonexistent", ["nonexistent-tool-xyz", "--version"])
        assert not ok
        assert "Not installed" in msg


class TestCheckContextStore:
    def test_present_and_writable(self, initialized_project):
        ok, msg = _check_context_store(initialized_project)
        assert ok

    def test_missing_dir(self, temp_project_dir):
        ok, msg = _check_context_store(temp_project_dir)
        assert not ok


class TestDoctorCommand:
    def test_healthy_project(self, cli_runner, initialized_project):
        result = cli_runner.invoke(app, [str(initialized_project)])
        assert "Doctor" in result.stdout or "doctor" in result.stdout.lower()

    def test_uninitialized_project(self, cli_runner, temp_project_dir):
        result = cli_runner.invoke(app, [str(temp_project_dir)])
        assert result.exit_code == 1

    def test_verbose_flag(self, cli_runner, initialized_project):
        result = cli_runner.invoke(app, ["--verbose", str(initialized_project)])
        # Verbose should show individual tool/hook details
        assert "python3" in result.stdout or "black" in result.stdout
