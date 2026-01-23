"""Tests for tools CLI command."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from devloop.cli.commands.tools import check, list, verify_startup


class TestToolsCheck:
    """Tests for tools check command."""

    @pytest.fixture
    def mock_manager(self):
        """Create mock ToolDependencyManager."""
        mock_mgr = Mock()
        mock_mgr.check_all_tools.return_value = {
            "gh": {
                "available": True,
                "compatible": True,
                "critical": True,
                "version": "2.40.0",
            },
            "bd": {
                "available": True,
                "compatible": True,
                "critical": True,
                "version": "0.1.0",
            },
        }
        return mock_mgr

    def test_check_all_tools_available(self, mock_manager):
        """Test check when all tools are available and compatible."""
        with patch(
            "devloop.cli.commands.tools.ToolDependencyManager",
            return_value=mock_manager,
        ):
            with patch("devloop.cli.commands.tools.typer.echo") as mock_echo:
                check(verbose=False, save=False)

                # Should show success message
                mock_echo.assert_called_once()
                assert "✅" in str(mock_echo.call_args[0][0])
                assert "All critical tools available" in str(mock_echo.call_args[0][0])

    def test_check_missing_critical_tools(self, mock_manager):
        """Test check when critical tools are missing."""
        mock_manager.check_all_tools.return_value = {
            "gh": {
                "available": False,
                "compatible": False,
                "critical": True,
                "version": None,
            },
            "bd": {
                "available": True,
                "compatible": True,
                "critical": True,
                "version": "0.1.0",
            },
        }

        with patch(
            "devloop.cli.commands.tools.ToolDependencyManager",
            return_value=mock_manager,
        ):
            with patch("devloop.cli.commands.tools.typer.echo") as mock_echo:
                check(verbose=False, save=False)

                # Should show missing tools
                calls = [str(call) for call in mock_echo.call_args_list]
                assert any("❌" in call and "gh" in call for call in calls)

    def test_check_incompatible_versions(self, mock_manager):
        """Test check when tool versions are incompatible."""
        mock_manager.check_all_tools.return_value = {
            "gh": {
                "available": True,
                "compatible": False,
                "critical": True,
                "version": "1.0.0",
            },
            "bd": {
                "available": True,
                "compatible": True,
                "critical": True,
                "version": "0.1.0",
            },
        }

        with patch(
            "devloop.cli.commands.tools.ToolDependencyManager",
            return_value=mock_manager,
        ):
            with patch("devloop.cli.commands.tools.typer.echo") as mock_echo:
                check(verbose=False, save=False)

                # Should show incompatible versions
                calls = [str(call) for call in mock_echo.call_args_list]
                assert any("⚠️" in call and "gh" in call for call in calls)

    def test_check_verbose_mode(self, mock_manager):
        """Test check with verbose flag."""
        with patch(
            "devloop.cli.commands.tools.ToolDependencyManager",
            return_value=mock_manager,
        ):
            with patch("devloop.cli.commands.tools.typer.echo") as mock_echo:
                check(verbose=True, save=False)

                # Should show checking message
                calls = [str(call) for call in mock_echo.call_args_list]
                assert any(
                    "Checking external tool dependencies" in call for call in calls
                )

                # Should call show_compatibility_matrix
                mock_manager.show_compatibility_matrix.assert_called_once()

    def test_check_save_report(self, mock_manager):
        """Test check with save flag."""
        with patch(
            "devloop.cli.commands.tools.ToolDependencyManager",
            return_value=mock_manager,
        ):
            with patch("devloop.cli.commands.tools.typer.echo"):
                check(verbose=False, save=True)

                # Should save report
                mock_manager.save_compatibility_report.assert_called_once()
                saved_path = mock_manager.save_compatibility_report.call_args[0][0]
                assert str(saved_path) == ".devloop/tools-report.json"

    def test_check_verbose_and_save(self, mock_manager):
        """Test check with both verbose and save flags."""
        with patch(
            "devloop.cli.commands.tools.ToolDependencyManager",
            return_value=mock_manager,
        ):
            with patch("devloop.cli.commands.tools.typer.echo"):
                check(verbose=True, save=True)

                # Should call both methods
                mock_manager.show_compatibility_matrix.assert_called_once()
                mock_manager.save_compatibility_report.assert_called_once()

    def test_check_missing_and_incompatible(self, mock_manager):
        """Test check when some tools are missing and others incompatible."""
        mock_manager.check_all_tools.return_value = {
            "gh": {
                "available": False,
                "compatible": False,
                "critical": True,
                "version": None,
            },
            "bd": {
                "available": True,
                "compatible": False,
                "critical": True,
                "version": "0.0.1",
            },
            "ruff": {
                "available": True,
                "compatible": True,
                "critical": False,
                "version": "0.1.0",
            },
        }

        with patch(
            "devloop.cli.commands.tools.ToolDependencyManager",
            return_value=mock_manager,
        ):
            with patch("devloop.cli.commands.tools.typer.echo") as mock_echo:
                check(verbose=False, save=False)

                # Should show both missing and incompatible
                calls = [str(call) for call in mock_echo.call_args_list]
                assert any("❌" in call and "gh" in call for call in calls)
                assert any("⚠️" in call and "bd" in call for call in calls)


class TestToolsList:
    """Tests for tools list command."""

    @pytest.fixture
    def mock_manager(self):
        """Create mock ToolDependencyManager with tool definitions."""
        mock_mgr = Mock()
        mock_mgr.PYTHON_TOOLS = {
            "black": Mock(
                description="Code formatter",
                min_version="23.0.0",
            ),
            "ruff": Mock(
                description="Python linter",
                min_version="0.1.0",
            ),
        }
        mock_mgr.EXTERNAL_TOOLS = {
            "gh": Mock(
                description="GitHub CLI",
                min_version="2.0.0",
                install_url="https://cli.github.com",
            ),
            "bd": Mock(
                description="Beads task manager",
                min_version="0.1.0",
                install_url="https://github.com/wioota/devloop",
            ),
        }
        mock_mgr.OPTIONAL_TOOLS = {
            "snyk": Mock(
                description="Security scanner",
                min_version=None,
                install_url="https://snyk.io",
            ),
        }
        return mock_mgr

    def test_list_all_tools(self, mock_manager):
        """Test list command shows all tool categories."""
        with patch(
            "devloop.cli.commands.tools.ToolDependencyManager",
            return_value=mock_manager,
        ):
            with patch("devloop.cli.commands.tools.typer.echo") as mock_echo:
                list()

                calls = [str(call) for call in mock_echo.call_args_list]

                # Should show Python tools header
                assert any("📦 Python Tools" in call for call in calls)
                # Should show external tools header
                assert any("🔧 External CLI Tools" in call for call in calls)
                # Should show optional tools header
                assert any("⚙️  Optional Tools" in call for call in calls)

    def test_list_python_tools(self, mock_manager):
        """Test list shows Python tools with details."""
        with patch(
            "devloop.cli.commands.tools.ToolDependencyManager",
            return_value=mock_manager,
        ):
            with patch("devloop.cli.commands.tools.typer.echo") as mock_echo:
                list()

                calls = [str(call) for call in mock_echo.call_args_list]

                # Should show black and ruff
                assert any(
                    "black" in call and "Code formatter" in call for call in calls
                )
                assert any("ruff" in call and "Python linter" in call for call in calls)
                # Should show min versions
                assert any("Min version: 23.0.0" in call for call in calls)

    def test_list_external_tools(self, mock_manager):
        """Test list shows external tools with install URLs."""
        with patch(
            "devloop.cli.commands.tools.ToolDependencyManager",
            return_value=mock_manager,
        ):
            with patch("devloop.cli.commands.tools.typer.echo") as mock_echo:
                list()

                calls = [str(call) for call in mock_echo.call_args_list]

                # Should show gh and bd
                assert any("gh" in call and "GitHub CLI" in call for call in calls)
                assert any("bd" in call and "Beads" in call for call in calls)
                # Should show install URLs
                assert any("Install: https://cli.github.com" in call for call in calls)

    def test_list_optional_tools(self, mock_manager):
        """Test list shows optional tools."""
        with patch(
            "devloop.cli.commands.tools.ToolDependencyManager",
            return_value=mock_manager,
        ):
            with patch("devloop.cli.commands.tools.typer.echo") as mock_echo:
                list()

                calls = [str(call) for call in mock_echo.call_args_list]

                # Should show snyk
                assert any(
                    "snyk" in call and "Security scanner" in call for call in calls
                )
                assert any("Install: https://snyk.io" in call for call in calls)

    def test_list_empty_tools(self):
        """Test list with no tools defined."""
        mock_mgr = Mock()
        mock_mgr.PYTHON_TOOLS = {}
        mock_mgr.EXTERNAL_TOOLS = {}
        mock_mgr.OPTIONAL_TOOLS = {}

        with patch(
            "devloop.cli.commands.tools.ToolDependencyManager",
            return_value=mock_mgr,
        ):
            with patch("devloop.cli.commands.tools.typer.echo") as mock_echo:
                list()

                calls = [str(call) for call in mock_echo.call_args_list]

                # Should still show headers
                assert any("📦 Python Tools" in call for call in calls)
                assert any("🔧 External CLI Tools" in call for call in calls)
                assert any("⚙️  Optional Tools" in call for call in calls)


class TestToolsVerifyStartup:
    """Tests for tools verify_startup command."""

    @pytest.fixture
    def mock_manager(self):
        """Create mock ToolDependencyManager."""
        return Mock()

    def test_verify_startup_success(self, mock_manager):
        """Test verify_startup when all checks pass."""
        mock_manager.startup_check.return_value = True

        with patch(
            "devloop.cli.commands.tools.ToolDependencyManager",
            return_value=mock_manager,
        ):
            with patch("devloop.cli.commands.tools.typer.echo") as mock_echo:
                verify_startup()

                mock_echo.assert_called_once_with("✅ Startup check passed")
                mock_manager.startup_check.assert_called_once()

    def test_verify_startup_failure(self, mock_manager):
        """Test verify_startup when checks fail."""
        import typer as typer_module

        mock_manager.startup_check.return_value = False

        with patch(
            "devloop.cli.commands.tools.ToolDependencyManager",
            return_value=mock_manager,
        ):
            with patch("devloop.cli.commands.tools.typer.echo") as mock_echo:
                with pytest.raises(typer_module.Exit) as exc_info:
                    verify_startup()

                # Should print warning message
                calls = [str(call) for call in mock_echo.call_args_list]
                assert any("⚠️  Some tools missing" in call for call in calls)

                # Should exit with code 1
                assert exc_info.value.exit_code == 1
                mock_manager.startup_check.assert_called_once()

    def test_verify_startup_exception(self, mock_manager):
        """Test verify_startup when startup_check raises exception."""
        mock_manager.startup_check.side_effect = Exception("Connection error")

        with patch(
            "devloop.cli.commands.tools.ToolDependencyManager",
            return_value=mock_manager,
        ):
            with pytest.raises(Exception) as exc_info:
                verify_startup()

            assert "Connection error" in str(exc_info.value)
