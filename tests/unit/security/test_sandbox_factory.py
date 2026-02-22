"""Tests for sandbox factory selection logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devloop.security.factory import (
    PURE_PYTHON_AGENTS,
    TOOL_DEPENDENT_AGENTS,
    create_sandbox,
    is_pure_python_agent,
    is_tool_dependent_agent,
)
from devloop.security.no_sandbox import NoSandbox
from devloop.security.sandbox import SandboxConfig, SandboxNotAvailableError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestClassificationHelpers:
    """Tests for is_pure_python_agent / is_tool_dependent_agent."""

    @pytest.mark.parametrize("agent", list(PURE_PYTHON_AGENTS))
    def test_pure_python_agent_recognised(self, agent: str) -> None:
        assert is_pure_python_agent(agent) is True

    @pytest.mark.parametrize("agent", list(TOOL_DEPENDENT_AGENTS))
    def test_tool_dependent_agent_recognised(self, agent: str) -> None:
        assert is_tool_dependent_agent(agent) is True

    def test_unknown_agent_not_pure_python(self) -> None:
        assert is_pure_python_agent("unknown_agent") is False

    def test_unknown_agent_not_tool_dependent(self) -> None:
        assert is_tool_dependent_agent("unknown_agent") is False


# ---------------------------------------------------------------------------
# Explicit mode selection
# ---------------------------------------------------------------------------


class TestExplicitModeSelection:
    """Tests for _create_explicit_sandbox via create_sandbox."""

    @pytest.mark.asyncio
    async def test_explicit_none_returns_no_sandbox(self) -> None:
        config = SandboxConfig(mode="none")
        sandbox = await create_sandbox(config)
        assert isinstance(sandbox, NoSandbox)

    @pytest.mark.asyncio
    async def test_explicit_bubblewrap_available(self) -> None:
        config = SandboxConfig(mode="bubblewrap")
        mock_bwrap = MagicMock()
        mock_bwrap.is_available = AsyncMock(return_value=True)

        with patch(
            "devloop.security.factory.BubblewrapSandbox", return_value=mock_bwrap
        ):
            result = await create_sandbox(config)
            assert result is mock_bwrap

    @pytest.mark.asyncio
    async def test_explicit_bubblewrap_not_available_raises(self) -> None:
        config = SandboxConfig(mode="bubblewrap")
        mock_bwrap = MagicMock()
        mock_bwrap.is_available = AsyncMock(return_value=False)

        with patch(
            "devloop.security.factory.BubblewrapSandbox", return_value=mock_bwrap
        ):
            with pytest.raises(SandboxNotAvailableError, match="Bubblewrap"):
                await create_sandbox(config)

    @pytest.mark.asyncio
    async def test_explicit_capsule_import_error_raises(self) -> None:
        config = SandboxConfig(mode="capsule")

        # capsule_sandbox doesn't exist, so import will fail naturally
        with pytest.raises(SandboxNotAvailableError, match="[Cc]apsule"):
            await create_sandbox(config)

    @pytest.mark.asyncio
    async def test_explicit_seccomp_import_error_raises(self) -> None:
        config = SandboxConfig(mode="seccomp")

        # seccomp_sandbox doesn't exist either
        with pytest.raises(SandboxNotAvailableError, match="seccomp"):
            await create_sandbox(config)

    @pytest.mark.asyncio
    async def test_explicit_unknown_mode_raises_value_error(self) -> None:
        config = SandboxConfig.__new__(SandboxConfig)
        config.mode = "imaginary"
        config.max_memory_mb = 500
        config.max_cpu_percent = 25
        config.timeout_seconds = 30
        config.allowed_tools = []
        config.allowed_network_domains = []
        config.allowed_env_vars = []

        with pytest.raises(ValueError, match="Unknown sandbox mode"):
            await create_sandbox(config)


# ---------------------------------------------------------------------------
# Auto mode selection
# ---------------------------------------------------------------------------


class TestAutoModeSelection:
    """Tests for _create_auto_sandbox via create_sandbox(mode='auto')."""

    @pytest.mark.asyncio
    async def test_auto_falls_back_to_no_sandbox(self) -> None:
        """When no sandbox implementations are available, falls back to NoSandbox."""
        config = SandboxConfig(mode="auto")
        mock_bwrap = MagicMock()
        mock_bwrap.is_available = AsyncMock(return_value=False)

        with patch(
            "devloop.security.factory.BubblewrapSandbox", return_value=mock_bwrap
        ):
            result = await create_sandbox(config, agent_type="linter")
            assert isinstance(result, NoSandbox)

    @pytest.mark.asyncio
    async def test_auto_prefers_bubblewrap_when_available(self) -> None:
        config = SandboxConfig(mode="auto")
        mock_bwrap = MagicMock()
        mock_bwrap.is_available = AsyncMock(return_value=True)

        with patch(
            "devloop.security.factory.BubblewrapSandbox", return_value=mock_bwrap
        ):
            result = await create_sandbox(config, agent_type="linter")
            assert result is mock_bwrap

    @pytest.mark.asyncio
    async def test_auto_pure_python_agent_tries_capsule_first(self) -> None:
        """For pure Python agents, capsule is attempted before bubblewrap."""
        config = SandboxConfig(mode="auto")

        # Capsule import will fail, should fall through to bubblewrap
        mock_bwrap = MagicMock()
        mock_bwrap.is_available = AsyncMock(return_value=True)

        with patch(
            "devloop.security.factory.BubblewrapSandbox", return_value=mock_bwrap
        ):
            result = await create_sandbox(config, agent_type="type_checker")
            # Falls back to bubblewrap since capsule isn't installed
            assert result is mock_bwrap

    @pytest.mark.asyncio
    async def test_auto_no_agent_type_uses_bubblewrap(self) -> None:
        config = SandboxConfig(mode="auto")
        mock_bwrap = MagicMock()
        mock_bwrap.is_available = AsyncMock(return_value=True)

        with patch(
            "devloop.security.factory.BubblewrapSandbox", return_value=mock_bwrap
        ):
            result = await create_sandbox(config, agent_type=None)
            assert result is mock_bwrap

    @pytest.mark.asyncio
    async def test_auto_no_agent_type_fallback_to_no_sandbox(self) -> None:
        config = SandboxConfig(mode="auto")
        mock_bwrap = MagicMock()
        mock_bwrap.is_available = AsyncMock(return_value=False)

        with patch(
            "devloop.security.factory.BubblewrapSandbox", return_value=mock_bwrap
        ):
            result = await create_sandbox(config, agent_type=None)
            assert isinstance(result, NoSandbox)
