"""Tests for Snyk CLI installer module."""

import os
import subprocess
from unittest.mock import Mock, patch


from devloop.cli.snyk_installer import (
    authenticate_snyk,
    check_snyk_available,
    check_snyk_token,
    install_snyk_cli,
    prompt_snyk_installation,
)


class TestCheckSnykAvailable:
    """Tests for check_snyk_available function."""

    def test_snyk_not_in_path(self):
        """Test when snyk is not found in PATH."""
        with patch("devloop.cli.snyk_installer.shutil.which", return_value=None):
            available, message = check_snyk_available()

            assert available is False
            assert "not found in PATH" in message

    def test_snyk_available_with_version(self):
        """Test when snyk is available and returns version."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "1.1050.0\n"

        with patch(
            "devloop.cli.snyk_installer.shutil.which", return_value="/usr/bin/snyk"
        ):
            with patch(
                "devloop.cli.snyk_installer.subprocess.run", return_value=mock_result
            ):
                available, version = check_snyk_available()

                assert available is True
                assert version == "1.1050.0"

    def test_snyk_command_fails(self):
        """Test when snyk command returns non-zero."""
        mock_result = Mock()
        mock_result.returncode = 1

        with patch(
            "devloop.cli.snyk_installer.shutil.which", return_value="/usr/bin/snyk"
        ):
            with patch(
                "devloop.cli.snyk_installer.subprocess.run", return_value=mock_result
            ):
                available, message = check_snyk_available()

                assert available is False
                assert "Failed to get Snyk version" in message

    def test_snyk_command_exception(self):
        """Test when snyk command raises exception."""
        with patch(
            "devloop.cli.snyk_installer.shutil.which", return_value="/usr/bin/snyk"
        ):
            with patch(
                "devloop.cli.snyk_installer.subprocess.run",
                side_effect=subprocess.TimeoutExpired("snyk", 5),
            ):
                available, message = check_snyk_available()

                assert available is False
                assert "TimeoutExpired" in message or "timed out" in message.lower()


class TestCheckSnykToken:
    """Tests for check_snyk_token function."""

    def test_token_not_set(self):
        """Test when SNYK_TOKEN is not set."""
        with patch.dict(os.environ, {}, clear=True):
            assert check_snyk_token() is False

    def test_token_empty_string(self):
        """Test when SNYK_TOKEN is empty string."""
        with patch.dict(os.environ, {"SNYK_TOKEN": ""}, clear=True):
            assert check_snyk_token() is False

    def test_token_whitespace_only(self):
        """Test when SNYK_TOKEN is whitespace."""
        with patch.dict(os.environ, {"SNYK_TOKEN": "   "}, clear=True):
            assert check_snyk_token() is False

    def test_token_set_with_value(self):
        """Test when SNYK_TOKEN has a value."""
        with patch.dict(os.environ, {"SNYK_TOKEN": "test-token-123"}, clear=True):
            assert check_snyk_token() is True

    def test_token_with_surrounding_whitespace(self):
        """Test when SNYK_TOKEN has whitespace around value."""
        with patch.dict(os.environ, {"SNYK_TOKEN": "  test-token  "}, clear=True):
            assert check_snyk_token() is True


class TestInstallSnykCli:
    """Tests for install_snyk_cli function."""

    def test_npm_not_available(self):
        """Test when npm is not in PATH."""
        with patch("devloop.cli.snyk_installer.shutil.which", return_value=None):
            with patch("devloop.cli.snyk_installer.console") as mock_console:
                result = install_snyk_cli()

                assert result is False
                assert any(
                    "npm not found" in str(call)
                    for call in mock_console.print.call_args_list
                )

    def test_npm_install_success(self):
        """Test successful npm install."""
        mock_result = Mock()
        mock_result.returncode = 0

        with patch(
            "devloop.cli.snyk_installer.shutil.which", return_value="/usr/bin/npm"
        ):
            with patch(
                "devloop.cli.snyk_installer.subprocess.run", return_value=mock_result
            ):
                with patch("devloop.cli.snyk_installer.console"):
                    result = install_snyk_cli()

                    assert result is True

    def test_npm_install_failure(self):
        """Test failed npm install."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Permission denied"

        with patch(
            "devloop.cli.snyk_installer.shutil.which", return_value="/usr/bin/npm"
        ):
            with patch(
                "devloop.cli.snyk_installer.subprocess.run", return_value=mock_result
            ):
                with patch("devloop.cli.snyk_installer.console"):
                    result = install_snyk_cli()

                    assert result is False

    def test_npm_install_timeout(self):
        """Test npm install timeout."""
        with patch(
            "devloop.cli.snyk_installer.shutil.which", return_value="/usr/bin/npm"
        ):
            with patch(
                "devloop.cli.snyk_installer.subprocess.run",
                side_effect=subprocess.TimeoutExpired("npm", 180),
            ):
                with patch("devloop.cli.snyk_installer.console"):
                    result = install_snyk_cli()

                    assert result is False

    def test_npm_install_exception(self):
        """Test npm install with unexpected exception."""
        with patch(
            "devloop.cli.snyk_installer.shutil.which", return_value="/usr/bin/npm"
        ):
            with patch(
                "devloop.cli.snyk_installer.subprocess.run",
                side_effect=Exception("Network error"),
            ):
                with patch("devloop.cli.snyk_installer.console"):
                    result = install_snyk_cli()

                    assert result is False


class TestAuthenticateSnyk:
    """Tests for authenticate_snyk function."""

    def test_no_token_set(self):
        """Test authentication when SNYK_TOKEN not set."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("devloop.cli.snyk_installer.console"):
                result = authenticate_snyk()

                assert result is False

    def test_authentication_success(self):
        """Test successful authentication."""
        mock_result = Mock()
        mock_result.returncode = 0

        with patch.dict(os.environ, {"SNYK_TOKEN": "test-token"}, clear=True):
            with patch(
                "devloop.cli.snyk_installer.subprocess.run", return_value=mock_result
            ):
                with patch("devloop.cli.snyk_installer.console"):
                    result = authenticate_snyk()

                    assert result is True

    def test_authentication_failure(self):
        """Test failed authentication."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Invalid token"

        with patch.dict(os.environ, {"SNYK_TOKEN": "bad-token"}, clear=True):
            with patch(
                "devloop.cli.snyk_installer.subprocess.run", return_value=mock_result
            ):
                with patch("devloop.cli.snyk_installer.console"):
                    result = authenticate_snyk()

                    assert result is False

    def test_authentication_timeout(self):
        """Test authentication timeout."""
        with patch.dict(os.environ, {"SNYK_TOKEN": "test-token"}, clear=True):
            with patch(
                "devloop.cli.snyk_installer.subprocess.run",
                side_effect=subprocess.TimeoutExpired("snyk", 30),
            ):
                with patch("devloop.cli.snyk_installer.console"):
                    result = authenticate_snyk()

                    assert result is False

    def test_authentication_exception(self):
        """Test authentication with exception."""
        with patch.dict(os.environ, {"SNYK_TOKEN": "test-token"}, clear=True):
            with patch(
                "devloop.cli.snyk_installer.subprocess.run",
                side_effect=Exception("Connection error"),
            ):
                with patch("devloop.cli.snyk_installer.console"):
                    result = authenticate_snyk()

                    assert result is False


class TestPromptSnykInstallation:
    """Tests for prompt_snyk_installation function."""

    def test_non_interactive_mode(self):
        """Test non-interactive mode returns True immediately."""
        result = prompt_snyk_installation(non_interactive=True)
        assert result is True

    def test_snyk_already_installed_with_token(self):
        """Test when snyk is already installed and token is set."""
        with patch(
            "devloop.cli.snyk_installer.check_snyk_available",
            return_value=(True, "1.1050.0"),
        ):
            with patch(
                "devloop.cli.snyk_installer.check_snyk_token", return_value=True
            ):
                with patch(
                    "devloop.cli.snyk_installer.typer.confirm", return_value=True
                ):
                    with patch(
                        "devloop.cli.snyk_installer.authenticate_snyk",
                        return_value=True,
                    ):
                        with patch("devloop.cli.snyk_installer.console"):
                            result = prompt_snyk_installation(non_interactive=False)

                            assert result is True

    def test_snyk_already_installed_no_token(self):
        """Test when snyk is installed but no token set."""
        with patch(
            "devloop.cli.snyk_installer.check_snyk_available",
            return_value=(True, "1.1050.0"),
        ):
            with patch(
                "devloop.cli.snyk_installer.check_snyk_token", return_value=False
            ):
                with patch("devloop.cli.snyk_installer.console"):
                    result = prompt_snyk_installation(non_interactive=False)

                    assert result is True

    def test_snyk_not_installed_user_accepts_install_success(self):
        """Test installation when user accepts and install succeeds."""
        with patch(
            "devloop.cli.snyk_installer.check_snyk_available",
            return_value=(False, "not found"),
        ):
            with patch(
                "devloop.cli.snyk_installer.check_snyk_token", return_value=False
            ):
                with patch(
                    "devloop.cli.snyk_installer.typer.confirm", return_value=True
                ):
                    with patch(
                        "devloop.cli.snyk_installer.install_snyk_cli", return_value=True
                    ):
                        with patch("devloop.cli.snyk_installer.console"):
                            result = prompt_snyk_installation(non_interactive=False)

                            assert result is True

    def test_snyk_not_installed_user_accepts_install_failure(self):
        """Test installation when user accepts but install fails."""
        with patch(
            "devloop.cli.snyk_installer.check_snyk_available",
            return_value=(False, "not found"),
        ):
            with patch("devloop.cli.snyk_installer.typer.confirm", return_value=True):
                with patch(
                    "devloop.cli.snyk_installer.install_snyk_cli", return_value=False
                ):
                    with patch("devloop.cli.snyk_installer.console"):
                        result = prompt_snyk_installation(non_interactive=False)

                        assert result is False

    def test_snyk_not_installed_user_declines(self):
        """Test when user declines installation."""
        with patch(
            "devloop.cli.snyk_installer.check_snyk_available",
            return_value=(False, "not found"),
        ):
            with patch("devloop.cli.snyk_installer.typer.confirm", return_value=False):
                with patch("devloop.cli.snyk_installer.console"):
                    result = prompt_snyk_installation(non_interactive=False)

                    assert result is True  # Returns True even when declined

    def test_install_with_token_authenticates(self):
        """Test that authentication is attempted after successful install when token is set."""
        with patch(
            "devloop.cli.snyk_installer.check_snyk_available",
            return_value=(False, "not found"),
        ):
            with patch(
                "devloop.cli.snyk_installer.check_snyk_token", return_value=True
            ):
                with patch(
                    "devloop.cli.snyk_installer.typer.confirm", return_value=True
                ):
                    with patch(
                        "devloop.cli.snyk_installer.install_snyk_cli", return_value=True
                    ):
                        with patch(
                            "devloop.cli.snyk_installer.authenticate_snyk"
                        ) as mock_auth:
                            with patch("devloop.cli.snyk_installer.console"):
                                result = prompt_snyk_installation(non_interactive=False)

                                assert result is True
                                mock_auth.assert_called_once()
