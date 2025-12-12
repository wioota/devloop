"""Secure token management for external API authentication.

This module provides utilities for secure token storage, validation, and usage
to prevent common security issues like token exposure in logs, process lists,
and shell history.

Security Features:
- Token expiry validation
- Secure token retrieval from environment variables
- Token sanitization for logs and command lines
- Warnings for insecure token usage
- OAuth2 flow recommendations
- Token rotation helpers

Best Practices:
1. Store tokens in environment variables, not code or command history
2. Use read-only tokens when possible
3. Enable token expiry and rotation
4. Never log full tokens
5. Use OAuth2 for user-facing applications
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Types of API tokens."""

    GITHUB = "github"
    GITLAB = "gitlab"
    PYPI = "pypi"
    NPM = "npm"
    DOCKER = "docker"
    GENERIC = "generic"


@dataclass
class TokenInfo:
    """Information about an API token."""

    token_type: TokenType
    value: str
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    scopes: list[str] = field(default_factory=list)
    read_only: bool = False

    def is_expired(self) -> bool:
        """Check if token has expired.

        Returns:
            True if token is expired, False otherwise
        """
        if self.expires_at is None:
            return False

        return datetime.now(UTC) >= self.expires_at

    def expires_soon(self, days: int = 7) -> bool:
        """Check if token expires within specified days.

        Args:
            days: Number of days to check

        Returns:
            True if token expires within the specified days
        """
        if self.expires_at is None:
            return False

        threshold = datetime.now(UTC) + timedelta(days=days)
        return self.expires_at <= threshold

    def sanitized(self, show_chars: int = 4) -> str:
        """Get sanitized token for display.

        Args:
            show_chars: Number of characters to show at end

        Returns:
            Sanitized token string (e.g., "****abc123")
        """
        if len(self.value) <= show_chars:
            return "*" * len(self.value)

        return "*" * (len(self.value) - show_chars) + self.value[-show_chars:]


class TokenManager:
    """Manages secure token storage and retrieval."""

    # Environment variable naming conventions
    ENV_VAR_PATTERNS = {
        TokenType.GITHUB: ["GITHUB_TOKEN", "GH_TOKEN"],
        TokenType.GITLAB: ["GITLAB_TOKEN", "GL_TOKEN"],
        TokenType.PYPI: ["PYPI_TOKEN", "POETRY_PYPI_TOKEN_PYPI"],
        TokenType.NPM: ["NPM_TOKEN"],
        TokenType.DOCKER: ["DOCKER_TOKEN", "DOCKER_PASSWORD"],
    }

    # Token format patterns (for validation)
    TOKEN_PATTERNS = {
        TokenType.GITHUB: r"^gh[pousr]_[A-Za-z0-9]{36,}$",
        TokenType.PYPI: r"^pypi-[A-Za-z0-9_-]{70,}$",
        TokenType.GITLAB: r"^(glpat-|glptt-)[A-Za-z0-9_-]{20,}$",
    }

    def __init__(self, warn_on_insecure: bool = True):
        """Initialize token manager.

        Args:
            warn_on_insecure: Whether to log warnings for insecure token usage
        """
        self.warn_on_insecure = warn_on_insecure
        self._warned_tokens: set[str] = set()

    def get_token(
        self,
        token_type: TokenType,
        env_var: Optional[str] = None,
        fallback_value: Optional[str] = None,
    ) -> Optional[TokenInfo]:
        """Securely retrieve token from environment.

        Args:
            token_type: Type of token to retrieve
            env_var: Specific environment variable name (optional)
            fallback_value: Fallback token value (NOT RECOMMENDED)

        Returns:
            TokenInfo if found, None otherwise
        """
        # Try specific env var first
        if env_var:
            value = os.environ.get(env_var)
            if value:
                return self._create_token_info(token_type, value)

        # Try standard env vars for this token type
        for std_var in self.ENV_VAR_PATTERNS.get(token_type, []):
            value = os.environ.get(std_var)
            if value:
                return self._create_token_info(token_type, value)

        # Use fallback if provided (with warning)
        if fallback_value:
            if self.warn_on_insecure and fallback_value not in self._warned_tokens:
                logger.warning(
                    f"Using hardcoded {token_type.value} token. "
                    f"Store in environment variable instead: {self.ENV_VAR_PATTERNS.get(token_type, ['TOKEN'])[0]}"
                )
                self._warned_tokens.add(fallback_value)

            return self._create_token_info(token_type, fallback_value)

        return None

    def validate_token(
        self,
        token_type: TokenType,
        value: str,
    ) -> tuple[bool, Optional[str]]:
        """Validate token format.

        Args:
            token_type: Type of token
            value: Token value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for obvious security issues first
        if value.lower() in ["token", "password", "secret", "changeme"]:
            return False, "Token appears to be a placeholder value"

        if len(value) < 20:
            return False, "Token too short (minimum 20 characters)"

        # Check if token matches expected pattern
        pattern = self.TOKEN_PATTERNS.get(token_type)
        if pattern and not re.match(pattern, value):
            return False, f"Token does not match expected {token_type.value} format"

        return True, None

    def sanitize_command(self, command: list[str]) -> list[str]:
        """Sanitize command line arguments to hide tokens.

        Args:
            command: Command and arguments

        Returns:
            Sanitized command with tokens replaced by placeholders
        """
        sanitized = []
        token_flags = ["-p", "--password", "--token", "-t", "--api-key"]

        i = 0
        while i < len(command):
            arg = command[i]

            # Check if this is a token flag
            if arg in token_flags and i + 1 < len(command):
                sanitized.append(arg)
                sanitized.append("****")  # Hide the token value
                i += 2  # Skip the token value
                continue

            # Check for inline token (e.g., --token=abc123)
            inline_found = False
            for flag in token_flags:
                if arg.startswith(f"{flag}="):
                    sanitized.append(f"{flag}=****")
                    inline_found = True
                    break

            if inline_found:
                i += 1
                continue

            sanitized.append(arg)
            i += 1

        return sanitized

    def sanitize_log_message(self, message: str) -> str:
        """Sanitize log message to remove potential tokens.

        Args:
            message: Log message to sanitize

        Returns:
            Sanitized message with tokens replaced
        """
        # Pattern for common token formats
        patterns = [
            (r"gh[pousr]_[A-Za-z0-9]{36,}", "gh****"),  # GitHub tokens
            (r"pypi-[A-Za-z0-9_-]{70,}", "pypi-****"),  # PyPI tokens
            (r"glpat-[A-Za-z0-9_-]{20,}", "glpat-****"),  # GitLab tokens
            (r"Bearer\s+[A-Za-z0-9._-]{20,}", "Bearer ****"),  # Bearer tokens
            (r"token[=:]\s*['\"]?[A-Za-z0-9._-]{20,}['\"]?", "token=****"),  # Generic
        ]

        sanitized = message
        for pattern, replacement in patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        return sanitized

    def check_token_in_process_list(
        self,
        token_value: str,
        warn: bool = True,
    ) -> bool:
        """Check if token is visible in process list.

        Args:
            token_value: Token value to check
            warn: Whether to log warning if found

        Returns:
            True if token found in process list
        """
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if token_value in result.stdout:
                if warn and token_value not in self._warned_tokens:
                    logger.warning(
                        "⚠️  SECURITY: Token visible in process list! "
                        "Avoid passing tokens as command-line arguments."
                    )
                    self._warned_tokens.add(token_value)
                return True

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return False

    def recommend_oauth2(self, service: str) -> str:
        """Get OAuth2 recommendations for a service.

        Args:
            service: Service name (github, gitlab, etc.)

        Returns:
            OAuth2 recommendation message
        """
        recommendations = {
            "github": (
                "For user-facing applications, consider using GitHub OAuth Apps:\n"
                "https://docs.github.com/en/apps/oauth-apps/building-oauth-apps\n"
                "Benefits: User-scoped access, automatic token refresh, revocable access"
            ),
            "gitlab": (
                "For user-facing applications, consider using GitLab OAuth2:\n"
                "https://docs.gitlab.com/ee/api/oauth2.html\n"
                "Benefits: User-scoped access, automatic token refresh, revocable access"
            ),
            "pypi": (
                "PyPI supports scoped tokens with fine-grained permissions:\n"
                "https://pypi.org/help/#apitoken\n"
                "Recommendation: Use project-scoped tokens with upload-only permissions"
            ),
        }

        return recommendations.get(
            service.lower(),
            f"Check {service} documentation for OAuth2 or scoped token support.",
        )

    def _create_token_info(
        self,
        token_type: TokenType,
        value: str,
    ) -> TokenInfo:
        """Create TokenInfo from raw token value.

        Args:
            token_type: Type of token
            value: Token value

        Returns:
            TokenInfo instance
        """
        # Validate token format
        is_valid, error = self.validate_token(token_type, value)
        if not is_valid and self.warn_on_insecure:
            logger.warning(f"Token validation warning: {error}")

        return TokenInfo(
            token_type=token_type,
            value=value,
            created_at=datetime.now(UTC),
        )


# Global instance
_token_manager: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    """Get or create global token manager instance.

    Returns:
        TokenManager instance
    """
    global _token_manager

    if _token_manager is None:
        _token_manager = TokenManager()

    return _token_manager


# Convenience functions
def get_github_token(env_var: Optional[str] = None) -> Optional[TokenInfo]:
    """Get GitHub token from environment.

    Args:
        env_var: Specific environment variable name

    Returns:
        TokenInfo if found, None otherwise
    """
    return get_token_manager().get_token(TokenType.GITHUB, env_var=env_var)


def get_pypi_token(env_var: Optional[str] = None) -> Optional[TokenInfo]:
    """Get PyPI token from environment.

    Args:
        env_var: Specific environment variable name

    Returns:
        TokenInfo if found, None otherwise
    """
    return get_token_manager().get_token(TokenType.PYPI, env_var=env_var)


def sanitize_command(command: list[str]) -> list[str]:
    """Sanitize command to hide tokens.

    Args:
        command: Command and arguments

    Returns:
        Sanitized command
    """
    return get_token_manager().sanitize_command(command)


def sanitize_log(message: str) -> str:
    """Sanitize log message to hide tokens.

    Args:
        message: Log message

    Returns:
        Sanitized message
    """
    return get_token_manager().sanitize_log_message(message)
