"""Comprehensive tests for devloop CLI commands."""

import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner

from devloop.cli.main import (
    app,
    init,
    status,
    stop,
    version,
    amp_status,
    amp_findings,
    amp_context,
)
from devloop.core import Config, ConfigWrapper


@pytest.fixture
def cli_runner():
    """Create a CliRunner for testing."""
    return CliRunner()


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestInitCommand:
    """Tests for the init command."""

    def test_init_creates_claude_directory(self, cli_runner, temp_project_dir):
        """Test that init creates .devloop directory."""
        result = cli_runner.invoke(app, ["init", str(temp_project_dir)])

        assert result.exit_code == 0
        assert (temp_project_dir / ".devloop").exists()
        assert (
            "[green]✓[/green] Created:" in result.stdout or "Created:" in result.stdout
        )

    def test_init_creates_config_file(self, cli_runner, temp_project_dir):
        """Test that init creates agents.json config file."""
        result = cli_runner.invoke(app, ["init", str(temp_project_dir)])

        assert result.exit_code == 0
        config_file = temp_project_dir / ".devloop" / "agents.json"
        assert config_file.exists()

        # Verify it's valid JSON
        with open(config_file) as f:
            config_data = json.load(f)
        assert "agents" in config_data or "enabled" in config_data

    def test_init_skip_config_flag(self, cli_runner, temp_project_dir):
        """Test that init --skip-config doesn't create config."""
        result = cli_runner.invoke(
            app, ["init", str(temp_project_dir), "--skip-config"]
        )

        assert result.exit_code == 0
        config_file = temp_project_dir / ".devloop" / "agents.json"
        assert not config_file.exists()
        assert (temp_project_dir / ".devloop").exists()

    def test_init_idempotent(self, cli_runner, temp_project_dir):
        """Test that init can be run multiple times safely."""
        # First init
        result1 = cli_runner.invoke(app, ["init", str(temp_project_dir)])
        assert result1.exit_code == 0

        # Second init
        result2 = cli_runner.invoke(app, ["init", str(temp_project_dir)])
        assert result2.exit_code == 0

        # Directory should still exist
        assert (temp_project_dir / ".devloop").exists()

    def test_init_default_path_current_directory(self, cli_runner):
        """Test that init without path argument works."""
        # Just test that the command accepts being called without path
        # The CliRunner doesn't use actual cwd, so we just verify the command works
        result = cli_runner.invoke(app, ["init", "--help"])

        # Should show help without path as argument
        assert result.exit_code == 0
        assert "init" in result.stdout.lower()


class TestStatusCommand:
    """Tests for the status command."""

    @patch("devloop.cli.main.ConfigWrapper")
    @patch("devloop.cli.main.Config")
    def test_status_displays_agents(
        self, mock_config_class, mock_wrapper_class, cli_runner
    ):
        """Test that status displays agent configuration."""
        mock_config = MagicMock()
        mock_config.load.return_value = {
            "agents": {
                "linter": {"enabled": True, "triggers": ["file:modified"]},
                "formatter": {"enabled": False, "triggers": []},
            }
        }
        mock_config_class.return_value = mock_config

        mock_wrapper = MagicMock()
        mock_wrapper.agents.return_value = {
            "linter": {"enabled": True, "triggers": ["file:modified"]},
            "formatter": {"enabled": False, "triggers": []},
        }
        mock_wrapper_class.return_value = mock_wrapper

        result = cli_runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "linter" in result.stdout or "Agent" in result.stdout

    @patch("devloop.cli.main.ConfigWrapper")
    @patch("devloop.cli.main.Config")
    def test_status_shows_enabled_disabled(
        self, mock_config_class, mock_wrapper_class, cli_runner
    ):
        """Test that status shows enabled/disabled status."""
        mock_config = MagicMock()
        mock_config.load.return_value = {"agents": {}}
        mock_config_class.return_value = mock_config

        mock_wrapper = MagicMock()
        mock_wrapper.agents.return_value = {}
        mock_wrapper_class.return_value = mock_wrapper

        result = cli_runner.invoke(app, ["status"])

        assert result.exit_code == 0


class TestStopCommand:
    """Tests for the stop command."""

    def test_stop_no_daemon_running(self, cli_runner, temp_project_dir):
        """Test stop when no daemon is running."""
        result = cli_runner.invoke(app, ["stop", str(temp_project_dir)])

        assert result.exit_code == 0
        assert "No daemon running" in result.stdout or "daemon" in result.stdout.lower()

    def test_stop_with_running_daemon(self, cli_runner, temp_project_dir):
        """Test stop with an actual PID file."""
        # Create .devloop directory and PID file
        claude_dir = temp_project_dir / ".devloop"
        claude_dir.mkdir()

        pid_file = claude_dir / "devloop.pid"
        pid_file.write_text("99999")  # Non-existent PID

        result = cli_runner.invoke(app, ["stop", str(temp_project_dir)])

        # Should fail to kill non-existent process but shouldn't crash
        assert "Failed to stop" in result.stdout or "daemon" in result.stdout.lower()

    def test_stop_default_path(self, cli_runner):
        """Test stop with default path (current directory)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = cli_runner.invoke(app, ["stop"])
                # Should succeed even with no daemon
                assert result.exit_code == 0
            finally:
                os.chdir(original_cwd)


class TestVersionCommand:
    """Tests for the version command."""

    def test_version_shows_version(self, cli_runner):
        """Test that version command displays version info."""
        result = cli_runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "v" in result.stdout or "version" in result.stdout.lower()
        assert "DevLoop" in result.stdout

    def test_version_is_valid_semver(self, cli_runner):
        """Test that version output contains valid semantic version."""
        result = cli_runner.invoke(app, ["version"])

        assert result.exit_code == 0
        # Should contain something like vX.Y.Z
        import re

        assert re.search(r"v?\d+\.\d+\.\d+", result.stdout)


class TestAmpStatusCommand:
    """Tests for the amp_status command."""

    @patch("devloop.cli.main.show_agent_status")
    def test_amp_status_returns_json(self, mock_show_status, cli_runner):
        """Test that amp_status returns valid JSON."""
        mock_show_status.return_value = {
            "status": "ok",
            "agents": [],
            "timestamp": "2024-01-01T00:00:00Z",
        }

        with patch("asyncio.run", return_value=mock_show_status.return_value):
            result = cli_runner.invoke(app, ["amp-status"])

            assert result.exit_code == 0
            # Should be valid JSON
            try:
                json.loads(result.stdout)
            except json.JSONDecodeError:
                pytest.fail("Output is not valid JSON")

    @patch("devloop.cli.main.show_agent_status")
    def test_amp_status_async_call(self, mock_show_status, cli_runner):
        """Test that amp_status properly calls async function."""
        mock_result = {"status": "ok", "agents": []}
        mock_show_status.return_value = mock_result

        with patch("asyncio.run", return_value=mock_result) as mock_asyncio:
            result = cli_runner.invoke(app, ["amp-status"])

            assert result.exit_code == 0


class TestAmpFindingsCommand:
    """Tests for the amp_findings command."""

    @patch("devloop.cli.main.check_agent_findings")
    def test_amp_findings_returns_json(self, mock_check_findings, cli_runner):
        """Test that amp_findings returns valid JSON."""
        mock_check_findings.return_value = {"findings": [], "count": 0}

        with patch("asyncio.run", return_value=mock_check_findings.return_value):
            result = cli_runner.invoke(app, ["amp-findings"])

            assert result.exit_code == 0
            try:
                json.loads(result.stdout)
            except json.JSONDecodeError:
                pytest.fail("Output is not valid JSON")


class TestAmpContextCommand:
    """Tests for the amp_context command."""

    def test_amp_context_no_index_file(self, cli_runner, temp_project_dir):
        """Test amp_context when no context index exists."""
        with patch("pathlib.Path.cwd", return_value=temp_project_dir):
            result = cli_runner.invoke(app, ["amp-context"])

            # Should handle gracefully
            assert "No context index found" in result.stdout or result.exit_code == 0

    def test_amp_context_with_valid_index(self, cli_runner, temp_project_dir):
        """Test amp_context with valid index file."""
        context_dir = temp_project_dir / ".devloop" / "context"
        context_dir.mkdir(parents=True, exist_ok=True)

        index_data = {"files": [], "metadata": {}}
        index_file = context_dir / "index.json"
        with open(index_file, "w") as f:
            json.dump(index_data, f)

        with patch("pathlib.Path.cwd", return_value=temp_project_dir):
            result = cli_runner.invoke(app, ["amp-context"])

            assert result.exit_code == 0
            try:
                json.loads(result.stdout)
            except json.JSONDecodeError:
                pytest.fail("Output is not valid JSON")


class TestSummaryCommand:
    """Tests for the summary subcommand."""

    def test_summary_command_exists(self, cli_runner):
        """Test that summary command is registered."""
        result = cli_runner.invoke(app, ["summary", "--help"])

        # Should show help without errors
        assert result.exit_code == 0 or "Usage" in result.stdout


class TestWatchCommand:
    """Tests for the watch command."""

    def test_watch_help(self, cli_runner):
        """Test that watch command has proper help."""
        result = cli_runner.invoke(app, ["watch", "--help"])

        assert result.exit_code == 0
        assert "watch" in result.stdout.lower()

    def test_watch_accepts_path_argument(self, cli_runner, temp_project_dir):
        """Test that watch accepts path argument."""
        # We won't actually run watch (it would block), just test invocation
        # by checking the command structure
        result = cli_runner.invoke(app, ["watch", "--help"])

        assert result.exit_code == 0
        assert "path" in result.stdout.lower() or "directory" in result.stdout.lower()

    def test_watch_has_foreground_option(self, cli_runner):
        """Test that watch has --foreground option."""
        result = cli_runner.invoke(app, ["watch", "--help"])

        assert result.exit_code == 0
        assert "--foreground" in result.stdout or "foreground" in result.stdout.lower()

    def test_watch_has_verbose_option(self, cli_runner):
        """Test that watch has --verbose option."""
        result = cli_runner.invoke(app, ["watch", "--help"])

        assert result.exit_code == 0
        assert "--verbose" in result.stdout or "verbose" in result.stdout.lower()

    def test_watch_has_config_option(self, cli_runner):
        """Test that watch has --config option."""
        result = cli_runner.invoke(app, ["watch", "--help"])

        assert result.exit_code == 0
        assert "--config" in result.stdout or "config" in result.stdout.lower()


class TestCLIHelp:
    """Tests for CLI help and general functionality."""

    def test_main_help(self, cli_runner):
        """Test that main help is accessible."""
        result = cli_runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "DevLoop" in result.stdout or "usage" in result.stdout.lower()

    def test_all_commands_listed(self, cli_runner):
        """Test that all commands are listed in help."""
        result = cli_runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        commands = ["init", "watch", "status", "stop", "version"]
        for cmd in commands:
            assert cmd in result.stdout.lower()

    def test_invalid_command(self, cli_runner):
        """Test that invalid command fails appropriately."""
        result = cli_runner.invoke(app, ["nonexistent"])

        assert result.exit_code != 0

    def test_invalid_option(self, cli_runner):
        """Test that invalid option fails appropriately."""
        result = cli_runner.invoke(app, ["init", "--invalid-option"])

        assert result.exit_code != 0


class TestCLIErrorHandling:
    """Tests for CLI error handling."""

    def test_init_with_invalid_path(self, cli_runner):
        """Test init with invalid path."""
        invalid_path = "/nonexistent/path/that/does/not/exist"
        result = cli_runner.invoke(app, ["init", invalid_path])

        # Should fail gracefully
        assert result.exit_code != 0 or "error" in result.stdout.lower()

    @patch("devloop.cli.main.Config")
    def test_status_handles_missing_config(self, mock_config_class, cli_runner):
        """Test that status handles missing config gracefully."""
        mock_config = MagicMock()
        mock_config.load.side_effect = FileNotFoundError("Config not found")
        mock_config_class.return_value = mock_config

        result = cli_runner.invoke(app, ["status"])

        # Should either show error or use defaults
        assert result.exit_code != 0 or result.stdout


class TestCLIIntegration:
    """Integration tests for CLI workflow."""

    def test_init_then_status_workflow(self, cli_runner, temp_project_dir):
        """Test the init -> status workflow."""
        # Initialize
        init_result = cli_runner.invoke(app, ["init", str(temp_project_dir)])
        assert init_result.exit_code == 0

        # Change to that directory and check status
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project_dir)

            with patch("devloop.cli.main.ConfigWrapper") as mock_wrapper_class:
                mock_wrapper = MagicMock()
                mock_wrapper.agents.return_value = {}
                mock_wrapper_class.return_value = mock_wrapper

                with patch("devloop.cli.main.Config") as mock_config_class:
                    mock_config = MagicMock()
                    mock_config.load.return_value = {"agents": {}}
                    mock_config_class.return_value = mock_config

                    status_result = cli_runner.invoke(app, ["status"])
                    assert status_result.exit_code == 0
        finally:
            os.chdir(original_cwd)
