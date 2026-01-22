"""Tests for CodeRabbit CLI installer module."""

import os
import subprocess
from unittest.mock import Mock, patch

import pytest

from devloop.cli.coderabbit_installer import (
    authenticate_coderabbit,
    check_coderabbit_api_key,
    check_coderabbit_available,
    install_coderabbit_cli,
    prompt_coderabbit_installation,
)


class TestCheckCodeRabbitAvailable:
    """Tests for check_coderabbit_available function."""

    def test_coderabbit_not_in_path(self):
        """Test when coderabbit is not found in PATH."""
        with patch("devloop.cli.coderabbit_installer.shutil.which", return_value=None):
            available, message = check_coderabbit_available()

            assert available is False
            assert "not found in PATH" in message

    def test_coderabbit_available_with_version(self):
        """Test when coderabbit is available and returns version."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "1.2.3\n"

        with patch(
            "devloop.cli.coderabbit_installer.shutil.which",
            return_value="/usr/bin/coderabbit",
        ):
            with patch(
                "devloop.cli.coderabbit_installer.subprocess.run",
                return_value=mock_result,
            ):
                available, version = check_coderabbit_available()

                assert available is True
                assert version == "1.2.3"

    def test_coderabbit_command_fails(self):
        """Test when coderabbit command returns non-zero."""
        mock_result = Mock()
        mock_result.returncode = 1

        with patch(
            "devloop.cli.coderabbit_installer.shutil.which",
            return_value="/usr/bin/coderabbit",
        ):
            with patch(
                "devloop.cli.coderabbit_installer.subprocess.run",
                return_value=mock_result,
            ):
                available, message = check_coderabbit_available()

                assert available is False
                assert "Failed to get CodeRabbit version" in message

    def test_coderabbit_command_exception(self):
        """Test when coderabbit command raises exception."""
        with patch(
            "devloop.cli.coderabbit_installer.shutil.which",
            return_value="/usr/bin/coderabbit",
        ):
            with patch(
                "devloop.cli.coderabbit_installer.subprocess.run",
                side_effect=subprocess.TimeoutExpired("coderabbit", 5),
            ):
                available, message = check_coderabbit_available()

                assert available is False
                assert "TimeoutExpired" in message or "timed out" in message.lower()


class TestCheckCodeRabbitApiKey:
    """Tests for check_coderabbit_api_key function."""

    def test_api_key_not_set(self):
        """Test when CODE_RABBIT_API_KEY is not set."""
        with patch.dict(os.environ, {}, clear=True):
            assert check_coderabbit_api_key() is False

    def test_api_key_empty_string(self):
        """Test when CODE_RABBIT_API_KEY is empty string."""
        with patch.dict(os.environ, {"CODE_RABBIT_API_KEY": ""}, clear=True):
            assert check_coderabbit_api_key() is False

    def test_api_key_whitespace_only(self):
        """Test when CODE_RABBIT_API_KEY is whitespace."""
        with patch.dict(os.environ, {"CODE_RABBIT_API_KEY": "   "}, clear=True):
            assert check_coderabbit_api_key() is False

    def test_api_key_set_with_value(self):
        """Test when CODE_RABBIT_API_KEY has a value."""
        with patch.dict(
            os.environ, {"CODE_RABBIT_API_KEY": "test-api-key-123"}, clear=True
        ):
            assert check_coderabbit_api_key() is True

    def test_api_key_with_surrounding_whitespace(self):
        """Test when CODE_RABBIT_API_KEY has whitespace around value."""
        with patch.dict(
            os.environ, {"CODE_RABBIT_API_KEY": "  test-key  "}, clear=True
        ):
            assert check_coderabbit_api_key() is True


class TestInstallCodeRabbitCli:
    """Tests for install_coderabbit_cli function."""

    def test_curl_not_available(self):
        """Test when curl is not in PATH."""
        with patch(
            "devloop.cli.coderabbit_installer.shutil.which",
            side_effect=lambda x: None if x == "curl" else "/bin/sh",
        ):
            with patch("devloop.cli.coderabbit_installer.console") as mock_console:
                result = install_coderabbit_cli()

                assert result is False
                assert any(
                    "curl not found" in str(call)
                    for call in mock_console.print.call_args_list
                )

    def test_sh_not_available(self):
        """Test when sh shell is not in PATH."""
        with patch(
            "devloop.cli.coderabbit_installer.shutil.which",
            side_effect=lambda x: "/usr/bin/curl" if x == "curl" else None,
        ):
            with patch("devloop.cli.coderabbit_installer.console") as mock_console:
                result = install_coderabbit_cli()

                assert result is False
                assert any(
                    "sh shell not found" in str(call)
                    for call in mock_console.print.call_args_list
                )

    def test_installation_success(self):
        """Test successful installation."""
        mock_result = Mock()
        mock_result.returncode = 0

        with patch(
            "devloop.cli.coderabbit_installer.shutil.which",
            return_value="/usr/bin/curl",
        ):
            with patch(
                "devloop.cli.coderabbit_installer.subprocess.run",
                return_value=mock_result,
            ):
                with patch("devloop.cli.coderabbit_installer.console"):
                    result = install_coderabbit_cli()

                    assert result is True

    def test_installation_failure(self):
        """Test failed installation."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Download failed"

        with patch(
            "devloop.cli.coderabbit_installer.shutil.which",
            return_value="/usr/bin/curl",
        ):
            with patch(
                "devloop.cli.coderabbit_installer.subprocess.run",
                return_value=mock_result,
            ):
                with patch("devloop.cli.coderabbit_installer.console"):
                    result = install_coderabbit_cli()

                    assert result is False

    def test_installation_timeout(self):
        """Test installation timeout."""
        with patch(
            "devloop.cli.coderabbit_installer.shutil.which",
            return_value="/usr/bin/curl",
        ):
            with patch(
                "devloop.cli.coderabbit_installer.subprocess.run",
                side_effect=subprocess.TimeoutExpired("sh", 180),
            ):
                with patch("devloop.cli.coderabbit_installer.console"):
                    result = install_coderabbit_cli()

                    assert result is False

    def test_installation_exception(self):
        """Test installation with unexpected exception."""
        with patch(
            "devloop.cli.coderabbit_installer.shutil.which",
            return_value="/usr/bin/curl",
        ):
            with patch(
                "devloop.cli.coderabbit_installer.subprocess.run",
                side_effect=Exception("Network error"),
            ):
                with patch("devloop.cli.coderabbit_installer.console"):
                    result = install_coderabbit_cli()

                    assert result is False


class TestAuthenticateCodeRabbit:
    """Tests for authenticate_coderabbit function."""

    def test_no_api_key_set(self):
        """Test authentication when CODE_RABBIT_API_KEY not set."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("devloop.cli.coderabbit_installer.console"):
                result = authenticate_coderabbit()

                assert result is False

    def test_api_key_set(self):
        """Test when CODE_RABBIT_API_KEY is configured."""
        with patch.dict(os.environ, {"CODE_RABBIT_API_KEY": "test-key"}, clear=True):
            with patch("devloop.cli.coderabbit_installer.console"):
                result = authenticate_coderabbit()

                assert result is True

    def test_authentication_exception(self):
        """Test authentication with exception."""
        with patch.dict(os.environ, {"CODE_RABBIT_API_KEY": "test-key"}, clear=True):
            with patch(
                "devloop.cli.coderabbit_installer.os.environ.get",
                side_effect=Exception("Environment error"),
            ):
                with patch("devloop.cli.coderabbit_installer.console"):
                    result = authenticate_coderabbit()

                    assert result is False


class TestPromptCodeRabbitInstallation:
    """Tests for prompt_coderabbit_installation function."""

    def test_non_interactive_mode(self):
        """Test non-interactive mode returns True immediately."""
        result = prompt_coderabbit_installation(non_interactive=True)
        assert result is True

    def test_coderabbit_already_installed_with_api_key(self):
        """Test when coderabbit is already installed and API key is set."""
        with patch(
            "devloop.cli.coderabbit_installer.check_coderabbit_available",
            return_value=(True, "1.2.3"),
        ):
            with patch(
                "devloop.cli.coderabbit_installer.check_coderabbit_api_key",
                return_value=True,
            ):
                with patch(
                    "devloop.cli.coderabbit_installer.authenticate_coderabbit",
                    return_value=True,
                ):
                    with patch("devloop.cli.coderabbit_installer.console"):
                        result = prompt_coderabbit_installation(non_interactive=False)

                        assert result is True

    def test_coderabbit_already_installed_no_api_key(self):
        """Test when coderabbit is installed but no API key set."""
        with patch(
            "devloop.cli.coderabbit_installer.check_coderabbit_available",
            return_value=(True, "1.2.3"),
        ):
            with patch(
                "devloop.cli.coderabbit_installer.check_coderabbit_api_key",
                return_value=False,
            ):
                with patch("devloop.cli.coderabbit_installer.console"):
                    result = prompt_coderabbit_installation(non_interactive=False)

                    assert result is True

    def test_coderabbit_not_installed_user_accepts_install_success(self):
        """Test installation when user accepts and install succeeds."""
        with patch(
            "devloop.cli.coderabbit_installer.check_coderabbit_available",
            return_value=(False, "not found"),
        ):
            with patch(
                "devloop.cli.coderabbit_installer.check_coderabbit_api_key",
                return_value=False,
            ):
                with patch(
                    "devloop.cli.coderabbit_installer.typer.confirm", return_value=True
                ):
                    with patch(
                        "devloop.cli.coderabbit_installer.install_coderabbit_cli",
                        return_value=True,
                    ):
                        with patch("devloop.cli.coderabbit_installer.console"):
                            result = prompt_coderabbit_installation(
                                non_interactive=False
                            )

                            assert result is True

    def test_coderabbit_not_installed_user_accepts_install_failure(self):
        """Test installation when user accepts but install fails."""
        with patch(
            "devloop.cli.coderabbit_installer.check_coderabbit_available",
            return_value=(False, "not found"),
        ):
            with patch(
                "devloop.cli.coderabbit_installer.typer.confirm", return_value=True
            ):
                with patch(
                    "devloop.cli.coderabbit_installer.install_coderabbit_cli",
                    return_value=False,
                ):
                    with patch("devloop.cli.coderabbit_installer.console"):
                        result = prompt_coderabbit_installation(non_interactive=False)

                        assert result is False

    def test_coderabbit_not_installed_user_declines(self):
        """Test when user declines installation."""
        with patch(
            "devloop.cli.coderabbit_installer.check_coderabbit_available",
            return_value=(False, "not found"),
        ):
            with patch(
                "devloop.cli.coderabbit_installer.typer.confirm", return_value=False
            ):
                with patch("devloop.cli.coderabbit_installer.console"):
                    result = prompt_coderabbit_installation(non_interactive=False)

                    assert result is True  # Returns True even when declined

    def test_install_with_api_key_authenticates(self):
        """Test that authentication check happens after successful install when API key is set."""
        with patch(
            "devloop.cli.coderabbit_installer.check_coderabbit_available",
            return_value=(False, "not found"),
        ):
            with patch(
                "devloop.cli.coderabbit_installer.check_coderabbit_api_key",
                return_value=True,
            ):
                with patch(
                    "devloop.cli.coderabbit_installer.typer.confirm", return_value=True
                ):
                    with patch(
                        "devloop.cli.coderabbit_installer.install_coderabbit_cli",
                        return_value=True,
                    ):
                        with patch(
                            "devloop.cli.coderabbit_installer.authenticate_coderabbit"
                        ) as mock_auth:
                            with patch("devloop.cli.coderabbit_installer.console"):
                                result = prompt_coderabbit_installation(
                                    non_interactive=False
                                )

                                assert result is True
                                mock_auth.assert_called_once()
