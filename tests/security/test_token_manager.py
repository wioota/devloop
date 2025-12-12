"""Tests for secure token management."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from devloop.security.token_manager import (
    TokenInfo,
    TokenManager,
    TokenType,
    get_github_token,
    get_pypi_token,
    get_token_manager,
    sanitize_command,
    sanitize_log,
)


@pytest.fixture
def token_manager():
    """Create TokenManager instance for testing."""
    return TokenManager(warn_on_insecure=False)


@pytest.fixture
def token_manager_with_warnings():
    """Create TokenManager instance with warnings enabled."""
    return TokenManager(warn_on_insecure=True)


class TestTokenInfo:
    """Test TokenInfo dataclass."""

    def test_token_info_creation(self):
        """Test creating TokenInfo instance."""
        token = TokenInfo(
            token_type=TokenType.GITHUB,
            value="ghp_test123456789012345678901234567890",
        )

        assert token.token_type == TokenType.GITHUB
        assert token.value == "ghp_test123456789012345678901234567890"
        assert token.scopes == []
        assert token.read_only is False

    def test_token_not_expired(self):
        """Test token that hasn't expired."""
        future = datetime.now(UTC) + timedelta(days=30)
        token = TokenInfo(
            token_type=TokenType.GITHUB,
            value="test_token",
            expires_at=future,
        )

        assert not token.is_expired()

    def test_token_expired(self):
        """Test expired token."""
        past = datetime.now(UTC) - timedelta(days=1)
        token = TokenInfo(
            token_type=TokenType.GITHUB,
            value="test_token",
            expires_at=past,
        )

        assert token.is_expired()

    def test_token_no_expiry(self):
        """Test token with no expiry."""
        token = TokenInfo(
            token_type=TokenType.GITHUB,
            value="test_token",
        )

        assert not token.is_expired()
        assert not token.expires_soon()

    def test_token_expires_soon(self):
        """Test token expiring soon."""
        soon = datetime.now(UTC) + timedelta(days=3)
        token = TokenInfo(
            token_type=TokenType.GITHUB,
            value="test_token",
            expires_at=soon,
        )

        assert token.expires_soon(days=7)
        assert not token.expires_soon(days=1)

    def test_token_sanitized(self):
        """Test token sanitization."""
        token = TokenInfo(
            token_type=TokenType.GITHUB,
            value="ghp_1234567890abcdefghij",
        )

        # Default: show last 4 characters
        # Token is 24 chars long, so 20 stars + last 4 chars
        assert token.sanitized() == "*" * 20 + "ghij"

        # Custom: show last 8 characters
        # Token is 24 chars long, so 16 stars + last 8 chars
        assert token.sanitized(show_chars=8) == "*" * 16 + "cdefghij"

    def test_token_sanitized_short(self):
        """Test sanitizing short token."""
        token = TokenInfo(
            token_type=TokenType.GENERIC,
            value="abc",
        )

        # Token shorter than show_chars should be fully masked
        assert token.sanitized(show_chars=4) == "***"


class TestTokenManager:
    """Test TokenManager class."""

    def test_get_token_from_env(self, token_manager, monkeypatch):
        """Test retrieving token from environment variable."""
        monkeypatch.setenv(
            "GITHUB_TOKEN", "ghp_test_token_123456789012345678901234567890"
        )

        token = token_manager.get_token(TokenType.GITHUB)

        assert token is not None
        assert token.token_type == TokenType.GITHUB
        assert token.value == "ghp_test_token_123456789012345678901234567890"

    def test_get_token_custom_env_var(self, token_manager, monkeypatch):
        """Test retrieving token from custom environment variable."""
        monkeypatch.setenv(
            "MY_CUSTOM_TOKEN", "ghp_custom_token_123456789012345678901234567890"
        )

        token = token_manager.get_token(
            TokenType.GITHUB,
            env_var="MY_CUSTOM_TOKEN",
        )

        assert token is not None
        assert token.value == "ghp_custom_token_123456789012345678901234567890"

    def test_get_token_fallback(self, token_manager):
        """Test using fallback token value."""
        token = token_manager.get_token(
            TokenType.GITHUB,
            fallback_value="ghp_fallback_token_12345678901234567890123456",
        )

        assert token is not None
        assert token.value == "ghp_fallback_token_12345678901234567890123456"

    @patch("devloop.security.token_manager.logger")
    def test_get_token_fallback_warning(self, mock_logger, token_manager_with_warnings):
        """Test warning when using fallback token."""
        token_manager_with_warnings.get_token(
            TokenType.GITHUB,
            fallback_value="ghp_fallback_123456789012345678901234567890",
        )

        # Should be called twice: once for hardcoded token, once for validation
        assert mock_logger.warning.call_count == 2
        # First call should be about hardcoded token
        assert "hardcoded" in mock_logger.warning.call_args_list[0][0][0].lower()

    def test_get_token_not_found(self, token_manager):
        """Test when token not found."""
        token = token_manager.get_token(TokenType.GITHUB)
        assert token is None

    def test_get_pypi_token_from_poetry_env(self, token_manager, monkeypatch):
        """Test retrieving PyPI token from Poetry environment variable."""
        monkeypatch.setenv("POETRY_PYPI_TOKEN_PYPI", "pypi-test-token-" + "a" * 70)

        token = token_manager.get_token(TokenType.PYPI)

        assert token is not None
        assert token.token_type == TokenType.PYPI

    def test_validate_token_github_valid(self, token_manager):
        """Test validating valid GitHub token."""
        valid_token = "ghp_" + "a" * 36

        is_valid, error = token_manager.validate_token(TokenType.GITHUB, valid_token)

        assert is_valid
        assert error is None

    def test_validate_token_github_invalid(self, token_manager):
        """Test validating invalid GitHub token."""
        invalid_token = "invalid_token"

        is_valid, error = token_manager.validate_token(TokenType.GITHUB, invalid_token)

        assert not is_valid
        assert error is not None

    def test_validate_token_too_short(self, token_manager):
        """Test validating token that's too short."""
        short_token = "short"

        is_valid, error = token_manager.validate_token(TokenType.GENERIC, short_token)

        assert not is_valid
        assert "too short" in error.lower()

    def test_validate_token_placeholder(self, token_manager):
        """Test validating placeholder token."""
        placeholder = "changeme"

        is_valid, error = token_manager.validate_token(TokenType.GENERIC, placeholder)

        assert not is_valid
        assert "placeholder" in error.lower()

    def test_sanitize_command_password_flag(self, token_manager):
        """Test sanitizing command with password flag."""
        command = ["poetry", "publish", "-p", "secret_token_12345678901234567890"]

        sanitized = token_manager.sanitize_command(command)

        assert sanitized == ["poetry", "publish", "-p", "****"]

    def test_sanitize_command_token_flag(self, token_manager):
        """Test sanitizing command with token flag."""
        command = [
            "gh",
            "auth",
            "login",
            "--token",
            "ghp_secret_123456789012345678901234567890",
        ]

        sanitized = token_manager.sanitize_command(command)

        assert sanitized == ["gh", "auth", "login", "--token", "****"]

    def test_sanitize_command_inline_token(self, token_manager):
        """Test sanitizing command with inline token."""
        command = [
            "curl",
            "--token=ghp_secret_123456789012345678901234567890",
            "api.github.com",
        ]

        sanitized = token_manager.sanitize_command(command)

        assert sanitized == ["curl", "--token=****", "api.github.com"]

    def test_sanitize_command_multiple_tokens(self, token_manager):
        """Test sanitizing command with multiple tokens."""
        command = ["cmd", "-p", "pass1", "--token", "token2", "arg"]

        sanitized = token_manager.sanitize_command(command)

        assert sanitized == ["cmd", "-p", "****", "--token", "****", "arg"]

    def test_sanitize_log_message_github(self, token_manager):
        """Test sanitizing log message with GitHub token."""
        message = (
            "Using token ghp_1234567890abcdefghijklmnopqrstuvwxyzABCD to authenticate"
        )

        sanitized = token_manager.sanitize_log_message(message)

        assert "ghp_" not in sanitized
        assert "gh****" in sanitized

    def test_sanitize_log_message_pypi(self, token_manager):
        """Test sanitizing log message with PyPI token."""
        message = "Publishing with pypi-" + "a" * 70

        sanitized = token_manager.sanitize_log_message(message)

        assert "pypi-****" in sanitized
        assert "a" * 70 not in sanitized

    def test_sanitize_log_message_bearer(self, token_manager):
        """Test sanitizing log message with Bearer token."""
        message = "Authorization: Bearer abc123def456ghi789jkl012mno345pqr678"

        sanitized = token_manager.sanitize_log_message(message)

        assert "Bearer ****" in sanitized
        assert "abc123" not in sanitized

    def test_sanitize_log_message_generic(self, token_manager):
        """Test sanitizing log message with generic token."""
        message = "token=my_secret_token_value_123456789"

        sanitized = token_manager.sanitize_log_message(message)

        assert "token=****" in sanitized
        assert "my_secret_token_value" not in sanitized

    @patch("devloop.security.token_manager.subprocess.run")
    @patch("devloop.security.token_manager.logger")
    def test_check_token_in_process_list_found(
        self, mock_logger, mock_run, token_manager_with_warnings
    ):
        """Test detecting token in process list."""
        mock_result = Mock()
        mock_result.stdout = (
            "python script.py --token secret_token_123456789012345678901234"
        )
        mock_run.return_value = mock_result

        found = token_manager_with_warnings.check_token_in_process_list(
            "secret_token_123456789012345678901234"
        )

        assert found
        mock_logger.warning.assert_called_once()
        assert "SECURITY" in mock_logger.warning.call_args[0][0]

    @patch("devloop.security.token_manager.subprocess.run")
    def test_check_token_in_process_list_not_found(self, mock_run, token_manager):
        """Test when token not in process list."""
        mock_result = Mock()
        mock_result.stdout = "python script.py --token ****"
        mock_run.return_value = mock_result

        found = token_manager.check_token_in_process_list("secret_token")

        assert not found

    def test_recommend_oauth2_github(self, token_manager):
        """Test OAuth2 recommendation for GitHub."""
        recommendation = token_manager.recommend_oauth2("github")

        assert "OAuth" in recommendation
        assert "github" in recommendation.lower()
        assert "https://" in recommendation

    def test_recommend_oauth2_gitlab(self, token_manager):
        """Test OAuth2 recommendation for GitLab."""
        recommendation = token_manager.recommend_oauth2("gitlab")

        assert "OAuth" in recommendation
        assert "gitlab" in recommendation.lower()

    def test_recommend_oauth2_pypi(self, token_manager):
        """Test scoped token recommendation for PyPI."""
        recommendation = token_manager.recommend_oauth2("pypi")

        assert "scoped" in recommendation.lower()
        assert "pypi" in recommendation.lower()

    def test_recommend_oauth2_unknown(self, token_manager):
        """Test recommendation for unknown service."""
        recommendation = token_manager.recommend_oauth2("unknown_service")

        assert "documentation" in recommendation.lower()


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_get_github_token(self, monkeypatch):
        """Test get_github_token convenience function."""
        monkeypatch.setenv(
            "GITHUB_TOKEN", "ghp_convenience_123456789012345678901234567890"
        )

        token = get_github_token()

        assert token is not None
        assert token.token_type == TokenType.GITHUB

    def test_get_pypi_token(self, monkeypatch):
        """Test get_pypi_token convenience function."""
        monkeypatch.setenv("PYPI_TOKEN", "pypi-convenience-" + "x" * 70)

        token = get_pypi_token()

        assert token is not None
        assert token.token_type == TokenType.PYPI

    def test_sanitize_command_function(self):
        """Test sanitize_command convenience function."""
        command = ["cmd", "-p", "secret"]

        sanitized = sanitize_command(command)

        assert sanitized == ["cmd", "-p", "****"]

    def test_sanitize_log_function(self):
        """Test sanitize_log convenience function."""
        message = "Token: ghp_123456789012345678901234567890abcdefgh"

        sanitized = sanitize_log(message)

        assert "ghp_" not in sanitized
        assert "****" in sanitized

    def test_get_token_manager_singleton(self):
        """Test that get_token_manager returns singleton."""
        manager1 = get_token_manager()
        manager2 = get_token_manager()

        assert manager1 is manager2


class TestTokenTypes:
    """Test TokenType enum."""

    def test_token_types_exist(self):
        """Test that all expected token types exist."""
        assert TokenType.GITHUB.value == "github"
        assert TokenType.GITLAB.value == "gitlab"
        assert TokenType.PYPI.value == "pypi"
        assert TokenType.NPM.value == "npm"
        assert TokenType.DOCKER.value == "docker"
        assert TokenType.GENERIC.value == "generic"
