"""Tests for pre_push_check module."""

import json
import subprocess
from unittest.mock import Mock, patch

import pytest

from devloop.cli.pre_push_check import get_current_branch, main


class TestGetCurrentBranch:
    """Tests for get_current_branch function."""

    def test_get_current_branch_success(self):
        """Test get_current_branch returns branch name."""
        mock_result = Mock()
        mock_result.stdout = "main\n"

        with patch(
            "devloop.cli.pre_push_check.subprocess.run", return_value=mock_result
        ):
            branch = get_current_branch()

            assert branch == "main"

    def test_get_current_branch_failure(self):
        """Test get_current_branch returns None on error."""
        with patch(
            "devloop.cli.pre_push_check.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "git"),
        ):
            branch = get_current_branch()

            assert branch is None


class TestMain:
    """Tests for main function."""

    def test_main_no_branch(self):
        """Test main returns 1 when can't get branch."""
        with patch("devloop.cli.pre_push_check.get_current_branch", return_value=None):
            with patch("devloop.cli.pre_push_check.print") as mock_print:
                result = main()

                assert result == 1
                mock_print.assert_called_once_with(
                    "ERROR: Could not determine current branch"
                )

    def test_main_no_provider(self):
        """Test main returns 0 when no CI provider."""
        with patch(
            "devloop.cli.pre_push_check.get_current_branch", return_value="main"
        ):
            mock_manager = Mock()
            mock_manager.auto_detect_ci_provider.return_value = None

            with patch(
                "devloop.cli.pre_push_check.get_provider_manager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.pre_push_check.print") as mock_print:
                    result = main()

                    assert result == 0
                    mock_print.assert_called_once_with(
                        "WARNING: No CI provider available"
                    )

    def test_main_provider_not_available(self):
        """Test main returns 0 when provider not available."""
        with patch(
            "devloop.cli.pre_push_check.get_current_branch", return_value="main"
        ):
            mock_provider = Mock()
            mock_provider.is_available.return_value = False
            mock_provider.get_provider_name.return_value = "GitHub Actions"

            mock_manager = Mock()
            mock_manager.auto_detect_ci_provider.return_value = mock_provider

            with patch(
                "devloop.cli.pre_push_check.get_provider_manager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.pre_push_check.print") as mock_print:
                    result = main()

                    assert result == 0
                    mock_print.assert_called_once_with(
                        "WARNING: CI provider 'GitHub Actions' not available"
                    )

    def test_main_no_runs(self):
        """Test main returns 0 when no CI runs found."""
        with patch(
            "devloop.cli.pre_push_check.get_current_branch", return_value="main"
        ):
            mock_provider = Mock()
            mock_provider.is_available.return_value = True
            mock_provider.list_runs.return_value = []

            mock_manager = Mock()
            mock_manager.auto_detect_ci_provider.return_value = mock_provider

            with patch(
                "devloop.cli.pre_push_check.get_provider_manager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.pre_push_check.print") as mock_print:
                    result = main()

                    assert result == 0
                    mock_print.assert_called_once_with("INFO: No CI runs found")

    def test_main_success(self):
        """Test main returns 0 and outputs JSON with run info."""
        with patch(
            "devloop.cli.pre_push_check.get_current_branch", return_value="main"
        ):
            mock_run = Mock()
            mock_run.status.value = "completed"
            mock_run.conclusion.value = "success"
            mock_run.url = "https://github.com/org/repo/actions/runs/123"

            mock_provider = Mock()
            mock_provider.is_available.return_value = True
            mock_provider.get_provider_name.return_value = "GitHub Actions"
            mock_provider.list_runs.return_value = [mock_run]

            mock_manager = Mock()
            mock_manager.auto_detect_ci_provider.return_value = mock_provider

            with patch(
                "devloop.cli.pre_push_check.get_provider_manager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.pre_push_check.print") as mock_print:
                    result = main()

                    assert result == 0

                    # Should print JSON output
                    output = json.loads(mock_print.call_args[0][0])
                    assert output["provider"] == "GitHub Actions"
                    assert output["branch"] == "main"
                    assert output["status"] == "completed"
                    assert output["conclusion"] == "success"
                    assert (
                        output["url"] == "https://github.com/org/repo/actions/runs/123"
                    )

    def test_main_success_no_conclusion(self):
        """Test main handles run with no conclusion."""
        with patch(
            "devloop.cli.pre_push_check.get_current_branch", return_value="develop"
        ):
            mock_run = Mock()
            mock_run.status.value = "in_progress"
            mock_run.conclusion = None
            mock_run.url = "https://github.com/org/repo/actions/runs/456"

            mock_provider = Mock()
            mock_provider.is_available.return_value = True
            mock_provider.get_provider_name.return_value = "GitHub Actions"
            mock_provider.list_runs.return_value = [mock_run]

            mock_manager = Mock()
            mock_manager.auto_detect_ci_provider.return_value = mock_provider

            with patch(
                "devloop.cli.pre_push_check.get_provider_manager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.pre_push_check.print") as mock_print:
                    result = main()

                    assert result == 0

                    # Should print JSON with None conclusion
                    output = json.loads(mock_print.call_args[0][0])
                    assert output["status"] == "in_progress"
                    assert output["conclusion"] is None
