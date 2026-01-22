"""Tests for prerequisites validation module."""

from unittest.mock import patch

import pytest

from devloop.cli.prerequisites import (
    PrerequisiteChecker,
    validate_prerequisites,
)


class TestPrerequisiteChecker:
    """Tests for PrerequisiteChecker class."""

    def test_required_tools_defined(self):
        """Test that required tools are defined."""
        assert "gh" in PrerequisiteChecker.REQUIRED_TOOLS
        assert "bd" in PrerequisiteChecker.REQUIRED_TOOLS

    def test_optional_tools_defined(self):
        """Test that optional tools are defined."""
        assert "snyk" in PrerequisiteChecker.OPTIONAL_TOOLS
        assert "poetry" in PrerequisiteChecker.OPTIONAL_TOOLS

    def test_tool_info_structure(self):
        """Test that tool info has expected structure."""
        gh_info = PrerequisiteChecker.REQUIRED_TOOLS["gh"]
        assert "description" in gh_info
        assert "install_url" in gh_info
        assert "critical" in gh_info

    def test_check_tool_available_found(self):
        """Test check_tool_available when tool is found."""
        with patch("devloop.cli.prerequisites.shutil.which", return_value="/usr/bin/gh"):
            result = PrerequisiteChecker.check_tool_available("gh")
            assert result is True

    def test_check_tool_available_not_found(self):
        """Test check_tool_available when tool is not found."""
        with patch("devloop.cli.prerequisites.shutil.which", return_value=None):
            result = PrerequisiteChecker.check_tool_available("gh")
            assert result is False

    def test_check_prerequisites_all_available(self):
        """Test check_prerequisites when all tools are available."""
        with patch("devloop.cli.prerequisites.shutil.which", return_value="/usr/bin/tool"):
            results = PrerequisiteChecker.check_prerequisites()

            assert isinstance(results, dict)
            assert "gh" in results
            assert "bd" in results
            assert all(results.values())  # All True

    def test_check_prerequisites_some_missing(self):
        """Test check_prerequisites when some tools are missing."""
        def mock_which(tool):
            return "/usr/bin/gh" if tool == "gh" else None

        with patch("devloop.cli.prerequisites.shutil.which", side_effect=mock_which):
            results = PrerequisiteChecker.check_prerequisites()

            assert results["gh"] is True
            assert results["bd"] is False

    def test_check_prerequisites_all_missing(self):
        """Test check_prerequisites when all tools are missing."""
        with patch("devloop.cli.prerequisites.shutil.which", return_value=None):
            results = PrerequisiteChecker.check_prerequisites()

            assert isinstance(results, dict)
            assert all(not available for available in results.values())  # All False

    def test_check_optional_prerequisites_all_available(self):
        """Test check_optional_prerequisites when all tools are available."""
        with patch("devloop.cli.prerequisites.shutil.which", return_value="/usr/bin/tool"):
            results = PrerequisiteChecker.check_optional_prerequisites()

            assert isinstance(results, dict)
            assert "snyk" in results
            assert "poetry" in results
            assert all(results.values())  # All True

    def test_check_optional_prerequisites_some_missing(self):
        """Test check_optional_prerequisites when some tools are missing."""
        def mock_which(tool):
            return "/usr/bin/snyk" if tool == "snyk" else None

        with patch("devloop.cli.prerequisites.shutil.which", side_effect=mock_which):
            results = PrerequisiteChecker.check_optional_prerequisites()

            assert results["snyk"] is True
            assert results["poetry"] is False

    def test_validate_for_git_hooks_all_available(self):
        """Test validate_for_git_hooks when all tools are available."""
        with patch("devloop.cli.prerequisites.shutil.which", return_value="/usr/bin/tool"):
            all_available, missing = PrerequisiteChecker.validate_for_git_hooks(
                interactive=False
            )

            assert all_available is True
            assert missing == []

    def test_validate_for_git_hooks_some_missing_non_interactive(self):
        """Test validate_for_git_hooks with missing tools in non-interactive mode."""
        with patch("devloop.cli.prerequisites.shutil.which", return_value=None):
            all_available, missing = PrerequisiteChecker.validate_for_git_hooks(
                interactive=False
            )

            assert all_available is False
            assert "gh" in missing
            assert "bd" in missing

    def test_validate_for_git_hooks_some_missing_interactive(self):
        """Test validate_for_git_hooks with missing tools in interactive mode."""
        with patch("devloop.cli.prerequisites.shutil.which", return_value=None):
            with patch("devloop.cli.prerequisites.console"):
                all_available, missing = PrerequisiteChecker.validate_for_git_hooks(
                    interactive=True
                )

                assert all_available is False
                assert "gh" in missing
                assert "bd" in missing

    def test_show_missing_tools_warning(self):
        """Test _show_missing_tools_warning displays correctly."""
        with patch("devloop.cli.prerequisites.console") as mock_console:
            PrerequisiteChecker._show_missing_tools_warning(["gh", "bd"])

            # Should have called print multiple times
            assert mock_console.print.call_count > 0

            # Check that tool names appear in output
            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("gh" in call for call in calls)
            assert any("bd" in call for call in calls)

    def test_get_installation_instructions_gh(self):
        """Test get_installation_instructions for gh."""
        instructions = PrerequisiteChecker.get_installation_instructions("gh")

        assert "GitHub CLI" in instructions or "gh" in instructions
        assert "apt-get" in instructions or "brew" in instructions

    def test_get_installation_instructions_bd(self):
        """Test get_installation_instructions for bd."""
        instructions = PrerequisiteChecker.get_installation_instructions("bd")

        assert "Beads" in instructions or "bd" in instructions
        assert "pip install" in instructions or "beads" in instructions

    def test_get_installation_instructions_unknown_tool(self):
        """Test get_installation_instructions for unknown tool."""
        instructions = PrerequisiteChecker.get_installation_instructions("unknown-tool")

        assert "documentation" in instructions.lower()
        assert "unknown-tool" in instructions

    def test_get_installation_instructions_optional_tool(self):
        """Test get_installation_instructions for optional tool."""
        instructions = PrerequisiteChecker.get_installation_instructions("snyk")

        assert "snyk.io" in instructions or "Visit:" in instructions

    def test_show_installation_guide(self):
        """Test show_installation_guide displays correctly."""
        with patch("devloop.cli.prerequisites.console") as mock_console:
            PrerequisiteChecker.show_installation_guide(["gh"])

            # Should print installation guide
            assert mock_console.print.call_count > 0

            # Check that gh appears in output
            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("gh" in call for call in calls)

    def test_show_installation_guide_multiple_tools(self):
        """Test show_installation_guide with multiple tools."""
        with patch("devloop.cli.prerequisites.console") as mock_console:
            PrerequisiteChecker.show_installation_guide(["gh", "bd"])

            # Should print for both tools
            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("gh" in call for call in calls)
            assert any("bd" in call or "Beads" in call for call in calls)


class TestValidatePrerequisites:
    """Tests for validate_prerequisites function."""

    def test_validate_prerequisites_all_available(self):
        """Test validate_prerequisites when all tools are available."""
        with patch("devloop.cli.prerequisites.shutil.which", return_value="/usr/bin/tool"):
            result = validate_prerequisites(interactive=False)

            assert result is True

    def test_validate_prerequisites_missing_tools(self):
        """Test validate_prerequisites when tools are missing."""
        with patch("devloop.cli.prerequisites.shutil.which", return_value=None):
            result = validate_prerequisites(interactive=False)

            assert result is False

    def test_validate_prerequisites_interactive_mode(self):
        """Test validate_prerequisites in interactive mode."""
        with patch("devloop.cli.prerequisites.shutil.which", return_value=None):
            with patch("devloop.cli.prerequisites.console"):
                result = validate_prerequisites(interactive=True)

                assert result is False

    def test_validate_prerequisites_partial_availability(self):
        """Test validate_prerequisites when some tools are available."""
        def mock_which(tool):
            return "/usr/bin/gh" if tool == "gh" else None

        with patch("devloop.cli.prerequisites.shutil.which", side_effect=mock_which):
            result = validate_prerequisites(interactive=False)

            # Should fail because not all required tools are available
            assert result is False
