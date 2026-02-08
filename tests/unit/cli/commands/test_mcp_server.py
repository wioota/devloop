"""Tests for MCP server CLI command."""

import json
import re
from unittest.mock import AsyncMock, Mock, patch

import pytest
from typer.testing import CliRunner

from devloop.cli.commands.mcp_server import (
    app,
    install_mcp_server,
    uninstall_mcp_server,
)


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


@pytest.fixture
def cli_runner():
    """Create a CliRunner for testing."""
    return CliRunner()


@pytest.fixture
def mock_settings_file(tmp_path):
    """Create a mock ~/.claude/settings.json file."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    settings_file = claude_dir / "settings.json"
    return settings_file


class TestMCPServerHelp:
    """Tests for mcp-server command help."""

    def test_help_shows_usage(self, cli_runner):
        """Test that help displays usage information."""
        result = cli_runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "mcp-server" in result.stdout.lower() or "MCP" in result.stdout

    def test_help_shows_options(self, cli_runner):
        """Test that help shows all options."""
        result = cli_runner.invoke(app, ["--help"])
        output = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "--check" in output
        assert "--install" in output
        assert "--uninstall" in output


class TestMCPServerCheck:
    """Tests for --check option."""

    def test_check_success_with_devloop_dir(self, cli_runner, tmp_path):
        """Test --check succeeds when .devloop exists."""
        devloop_dir = tmp_path / ".devloop"
        devloop_dir.mkdir(parents=True)

        with patch("devloop.mcp.server.MCPServer") as mock_server_class:
            mock_server = Mock()
            mock_server.project_root = tmp_path
            mock_server_class.return_value = mock_server

            result = cli_runner.invoke(app, ["--check"])

            assert result.exit_code == 0
            assert (
                "Server validated" in result.stdout
                or "validated" in result.stdout.lower()
            )

    def test_check_fails_without_devloop_dir(self, cli_runner, tmp_path):
        """Test --check fails when .devloop doesn't exist."""
        with patch(
            "devloop.mcp.server.MCPServer",
            side_effect=FileNotFoundError("Could not find .devloop directory"),
        ):
            result = cli_runner.invoke(app, ["--check"])

            assert result.exit_code != 0
            assert "error" in result.stdout.lower() or ".devloop" in result.stdout


class TestMCPServerInstall:
    """Tests for --install option."""

    def test_install_creates_settings_file(self, mock_settings_file):
        """Test install creates settings.json if it doesn't exist."""
        settings_file = mock_settings_file

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=settings_file,
        ):
            result = install_mcp_server()

            assert result is True
            assert settings_file.exists()

            settings = json.loads(settings_file.read_text())
            assert "mcpServers" in settings
            assert "devloop" in settings["mcpServers"]
            assert settings["mcpServers"]["devloop"]["command"] == "devloop"
            assert settings["mcpServers"]["devloop"]["args"] == ["mcp-server"]

    def test_install_updates_existing_settings(self, mock_settings_file):
        """Test install updates existing settings.json."""
        settings_file = mock_settings_file

        # Create existing settings with other servers
        existing_settings = {
            "mcpServers": {
                "other-server": {
                    "command": "other",
                    "args": ["arg1"],
                }
            },
            "someOtherSetting": True,
        }
        settings_file.write_text(json.dumps(existing_settings))

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=settings_file,
        ):
            result = install_mcp_server()

            assert result is True

            settings = json.loads(settings_file.read_text())
            # Should preserve other servers
            assert "other-server" in settings["mcpServers"]
            # Should add devloop
            assert "devloop" in settings["mcpServers"]
            # Should preserve other settings
            assert settings["someOtherSetting"] is True

    def test_install_already_installed(self, mock_settings_file):
        """Test install when devloop is already installed."""
        settings_file = mock_settings_file

        existing_settings = {
            "mcpServers": {
                "devloop": {
                    "command": "devloop",
                    "args": ["mcp-server"],
                }
            }
        }
        settings_file.write_text(json.dumps(existing_settings))

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=settings_file,
        ):
            result = install_mcp_server()

            # Should succeed but not change anything
            assert result is True

    def test_install_creates_claude_directory(self, tmp_path):
        """Test install creates .claude directory if needed."""
        settings_file = tmp_path / ".claude" / "settings.json"

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=settings_file,
        ):
            result = install_mcp_server()

            assert result is True
            assert settings_file.parent.exists()
            assert settings_file.exists()

    def test_install_cli(self, cli_runner, mock_settings_file):
        """Test --install via CLI."""
        settings_file = mock_settings_file

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=settings_file,
        ):
            result = cli_runner.invoke(app, ["--install"])

            assert result.exit_code == 0
            assert (
                "installed" in result.stdout.lower()
                or "success" in result.stdout.lower()
            )


class TestMCPServerUninstall:
    """Tests for --uninstall option."""

    def test_uninstall_removes_devloop(self, mock_settings_file):
        """Test uninstall removes devloop from settings."""
        settings_file = mock_settings_file

        existing_settings = {
            "mcpServers": {
                "devloop": {
                    "command": "devloop",
                    "args": ["mcp-server"],
                },
                "other-server": {
                    "command": "other",
                    "args": ["arg1"],
                },
            }
        }
        settings_file.write_text(json.dumps(existing_settings))

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=settings_file,
        ):
            result = uninstall_mcp_server()

            assert result is True

            settings = json.loads(settings_file.read_text())
            assert "devloop" not in settings["mcpServers"]
            # Should preserve other servers
            assert "other-server" in settings["mcpServers"]

    def test_uninstall_not_installed(self, mock_settings_file):
        """Test uninstall when devloop is not installed."""
        settings_file = mock_settings_file

        existing_settings = {
            "mcpServers": {
                "other-server": {
                    "command": "other",
                    "args": ["arg1"],
                }
            }
        }
        settings_file.write_text(json.dumps(existing_settings))

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=settings_file,
        ):
            result = uninstall_mcp_server()

            # Should succeed even if not installed
            assert result is True

    def test_uninstall_no_settings_file(self, tmp_path):
        """Test uninstall when settings file doesn't exist."""
        settings_file = tmp_path / ".claude" / "settings.json"

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=settings_file,
        ):
            result = uninstall_mcp_server()

            # Should succeed even if file doesn't exist
            assert result is True

    def test_uninstall_cli(self, cli_runner, mock_settings_file):
        """Test --uninstall via CLI."""
        settings_file = mock_settings_file

        existing_settings = {
            "mcpServers": {
                "devloop": {
                    "command": "devloop",
                    "args": ["mcp-server"],
                }
            }
        }
        settings_file.write_text(json.dumps(existing_settings))

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=settings_file,
        ):
            result = cli_runner.invoke(app, ["--uninstall"])

            assert result.exit_code == 0
            assert (
                "uninstalled" in result.stdout.lower()
                or "removed" in result.stdout.lower()
            )


class TestMCPServerRun:
    """Tests for running the MCP server (default behavior)."""

    def test_run_starts_server(self, cli_runner, tmp_path):
        """Test default invocation starts the server."""
        devloop_dir = tmp_path / ".devloop"
        devloop_dir.mkdir(parents=True)

        with patch("devloop.mcp.server.MCPServer") as mock_server_class:
            mock_server = Mock()
            mock_server.run = AsyncMock()
            mock_server_class.return_value = mock_server

            with patch("devloop.cli.commands.mcp_server.asyncio.run") as mock_run:
                cli_runner.invoke(app, [])

                # Should call asyncio.run with server.run()
                mock_run.assert_called_once()

    def test_run_fails_without_devloop(self, cli_runner, tmp_path):
        """Test server fails to start without .devloop directory."""
        with patch(
            "devloop.mcp.server.MCPServer",
            side_effect=FileNotFoundError("Could not find .devloop directory"),
        ):
            result = cli_runner.invoke(app, [])

            assert result.exit_code != 0


class TestMCPServerMutualExclusion:
    """Tests for option mutual exclusion."""

    def test_check_and_install_mutually_exclusive(self, cli_runner):
        """Test that --check and --install cannot be used together."""
        result = cli_runner.invoke(app, ["--check", "--install"])

        assert (
            result.exit_code != 0
            or "only one" in result.stdout.lower()
            or "mutually exclusive" in result.stdout.lower()
        )

    def test_check_and_uninstall_mutually_exclusive(self, cli_runner):
        """Test that --check and --uninstall cannot be used together."""
        result = cli_runner.invoke(app, ["--check", "--uninstall"])

        assert (
            result.exit_code != 0
            or "only one" in result.stdout.lower()
            or "mutually exclusive" in result.stdout.lower()
        )

    def test_install_and_uninstall_mutually_exclusive(self, cli_runner):
        """Test that --install and --uninstall cannot be used together."""
        result = cli_runner.invoke(app, ["--install", "--uninstall"])

        assert (
            result.exit_code != 0
            or "only one" in result.stdout.lower()
            or "mutually exclusive" in result.stdout.lower()
        )


class TestGetClaudeSettingsPath:
    """Tests for get_claude_settings_path function."""

    def test_returns_home_claude_settings(self):
        """Test that function returns ~/.claude/settings.json."""
        from devloop.cli.commands.mcp_server import get_claude_settings_path

        result = get_claude_settings_path()

        assert result.name == "settings.json"
        assert result.parent.name == ".claude"
