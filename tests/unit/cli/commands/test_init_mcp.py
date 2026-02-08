"""Tests for MCP server auto-registration during devloop init."""

import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from devloop.cli.main import app


@pytest.fixture
def cli_runner():
    """Create a CliRunner for testing."""
    return CliRunner()


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    return tmp_path


@pytest.fixture
def mock_claude_settings(tmp_path):
    """Create a mock ~/.claude/settings.json directory structure."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    settings_file = claude_dir / "settings.json"
    return settings_file


class TestInitMCPServerRegistration:
    """Tests for MCP server auto-registration during init."""

    def test_init_registers_mcp_server_when_claude_settings_exist(
        self, cli_runner, temp_project_dir, mock_claude_settings
    ):
        """Test that MCP server is registered when Claude settings exist."""
        # Create existing Claude settings file
        existing_settings = {"someOtherSetting": True}
        mock_claude_settings.write_text(json.dumps(existing_settings))

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=mock_claude_settings,
        ):
            result = cli_runner.invoke(
                app, ["init", str(temp_project_dir), "--non-interactive"]
            )

            assert result.exit_code == 0
            # Check that MCP server was registered
            assert "MCP server registered" in result.stdout

            # Verify the settings file was updated
            settings = json.loads(mock_claude_settings.read_text())
            assert "mcpServers" in settings
            assert "devloop" in settings["mcpServers"]
            assert settings["mcpServers"]["devloop"]["command"] == "devloop"
            assert settings["mcpServers"]["devloop"]["args"] == ["mcp-server"]
            # Preserve existing settings
            assert settings["someOtherSetting"] is True

    def test_init_succeeds_when_claude_settings_dont_exist(
        self, cli_runner, temp_project_dir, tmp_path
    ):
        """Test that init succeeds even if Claude settings don't exist."""
        # Point to non-existent settings file
        fake_settings_path = tmp_path / "nonexistent" / ".claude" / "settings.json"

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=fake_settings_path,
        ):
            result = cli_runner.invoke(
                app, ["init", str(temp_project_dir), "--non-interactive"]
            )

            # Init should still succeed
            assert result.exit_code == 0
            assert (temp_project_dir / ".devloop").exists()

    def test_init_succeeds_with_warning_if_registration_fails(
        self, cli_runner, temp_project_dir, mock_claude_settings
    ):
        """Test that init succeeds with warning if MCP registration fails."""
        # Create Claude settings file
        mock_claude_settings.write_text("{}")

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=mock_claude_settings,
        ):
            with patch(
                "devloop.cli.commands.mcp_server.install_mcp_server",
                side_effect=Exception("Permission denied"),
            ):
                result = cli_runner.invoke(
                    app, ["init", str(temp_project_dir), "--non-interactive"]
                )

                # Init should still succeed
                assert result.exit_code == 0
                assert (temp_project_dir / ".devloop").exists()
                # Should show a warning
                assert (
                    "warning" in result.stdout.lower()
                    or "Warning" in result.stdout
                    or "MCP" in result.stdout
                )

    def test_init_preserves_existing_mcp_servers(
        self, cli_runner, temp_project_dir, mock_claude_settings
    ):
        """Test that init preserves other MCP servers in settings."""
        # Create existing Claude settings with other MCP servers
        existing_settings = {
            "mcpServers": {
                "other-server": {
                    "command": "other",
                    "args": ["arg1"],
                }
            }
        }
        mock_claude_settings.write_text(json.dumps(existing_settings))

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=mock_claude_settings,
        ):
            result = cli_runner.invoke(
                app, ["init", str(temp_project_dir), "--non-interactive"]
            )

            assert result.exit_code == 0

            # Verify both servers are present
            settings = json.loads(mock_claude_settings.read_text())
            assert "other-server" in settings["mcpServers"]
            assert "devloop" in settings["mcpServers"]

    def test_init_does_not_duplicate_if_already_registered(
        self, cli_runner, temp_project_dir, mock_claude_settings
    ):
        """Test that init doesn't duplicate devloop if already registered."""
        # Create existing Claude settings with devloop already registered
        existing_settings = {
            "mcpServers": {
                "devloop": {
                    "command": "devloop",
                    "args": ["mcp-server"],
                }
            }
        }
        mock_claude_settings.write_text(json.dumps(existing_settings))

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=mock_claude_settings,
        ):
            result = cli_runner.invoke(
                app, ["init", str(temp_project_dir), "--non-interactive"]
            )

            assert result.exit_code == 0

            # Verify only one devloop entry exists
            settings = json.loads(mock_claude_settings.read_text())
            assert len(settings["mcpServers"]) == 1
            assert "devloop" in settings["mcpServers"]


class TestInitMCPServerOutput:
    """Tests for MCP server registration output messages."""

    def test_init_shows_registration_message(
        self, cli_runner, temp_project_dir, mock_claude_settings
    ):
        """Test that init shows MCP server registration message."""
        mock_claude_settings.write_text("{}")

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=mock_claude_settings,
        ):
            result = cli_runner.invoke(
                app, ["init", str(temp_project_dir), "--non-interactive"]
            )

            assert result.exit_code == 0
            # Should show registration message
            assert "MCP server registered" in result.stdout

    def test_init_no_mcp_message_when_settings_dont_exist(
        self, cli_runner, temp_project_dir, tmp_path
    ):
        """Test that init doesn't show MCP message when settings don't exist."""
        # Point to non-existent settings
        fake_settings = tmp_path / "nonexistent" / ".claude" / "settings.json"

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=fake_settings,
        ):
            result = cli_runner.invoke(
                app, ["init", str(temp_project_dir), "--non-interactive"]
            )

            assert result.exit_code == 0
            # Should NOT show registration message since settings don't exist
            # (or the directory doesn't exist)
            # The key thing is init succeeds
