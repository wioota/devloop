"""Sandbox factory for automatic selection of best available implementation."""

from __future__ import annotations

import logging
from typing import Optional, cast

from devloop.security.bubblewrap_sandbox import BubblewrapSandbox
from devloop.security.no_sandbox import NoSandbox
from devloop.security.sandbox import (
    SandboxConfig,
    SandboxExecutor,
    SandboxNotAvailableError,
)

logger = logging.getLogger(__name__)

# Agent classification for sandbox selection
# Pure Python agents that can run in WASM (Capsule)
PURE_PYTHON_AGENTS = {
    "type_checker",  # mypy
    "formatter",  # black
    "security_scanner",  # bandit
    "performance_profiler",  # radon
}

# Agents that require native tools (need Bubblewrap/system sandbox)
TOOL_DEPENDENT_AGENTS = {
    "linter",  # ruff (native Rust binary)
    "git_commit_assistant",  # git (native)
    "ci_monitor",  # gh CLI (native)
    "snyk",  # snyk (native)
}


async def create_sandbox(
    config: SandboxConfig, agent_type: Optional[str] = None
) -> SandboxExecutor:
    """Create appropriate sandbox executor based on configuration and agent type.

    Selection strategy:
    1. If mode is explicitly set (not "auto"), try that mode only
    2. For pure-Python agents, prefer Capsule (WASM) if available
    3. For tool-dependent agents, prefer Bubblewrap if available
    4. Fallback chain: Capsule → Bubblewrap → seccomp → None

    Args:
        config: Sandbox configuration
        agent_type: Agent type identifier (e.g., "linter", "type_checker")

    Returns:
        SandboxExecutor instance

    Raises:
        SandboxNotAvailableError: If no suitable sandbox is available
    """
    # Explicit mode selection (not auto)
    if config.mode != "auto":
        return await _create_explicit_sandbox(config)

    # Auto mode: select based on agent type and availability
    return await _create_auto_sandbox(config, agent_type)


async def _create_explicit_sandbox(config: SandboxConfig) -> SandboxExecutor:
    """Create sandbox with explicitly configured mode.

    Args:
        config: Sandbox configuration with non-auto mode

    Returns:
        SandboxExecutor instance

    Raises:
        SandboxNotAvailableError: If requested sandbox is not available
    """
    if config.mode == "capsule":
        try:
            # Import only when needed (Capsule not available until Jan 2025)
            from devloop.security.capsule_sandbox import CapsuleSandbox  # type: ignore[import-untyped]

            sandbox = CapsuleSandbox(config)
            if await sandbox.is_available():
                logger.info("Using Capsule (WASM) sandbox")
                return cast(SandboxExecutor, sandbox)
            raise SandboxNotAvailableError(
                "Capsule sandbox requested but not available. "
                "Install capsule: pip install capsule-runtime"
            )
        except ImportError as e:
            raise SandboxNotAvailableError(
                f"Capsule sandbox not available: {e}. "
                "Install capsule: pip install capsule-runtime"
            )

    elif config.mode == "bubblewrap":
        sandbox = BubblewrapSandbox(config)
        if await sandbox.is_available():
            logger.info("Using Bubblewrap (Linux namespaces) sandbox")
            return sandbox
        raise SandboxNotAvailableError(
            "Bubblewrap sandbox requested but not available. "
            "Install bubblewrap: apt-get install bubblewrap"
        )

    elif config.mode == "seccomp":
        try:
            # Import only when needed
            from devloop.security.seccomp_sandbox import SeccompSandbox  # type: ignore[import-untyped]

            sandbox = SeccompSandbox(config)
            if await sandbox.is_available():
                logger.info("Using seccomp (syscall filtering) sandbox")
                return cast(SandboxExecutor, sandbox)
            raise SandboxNotAvailableError(
                "seccomp sandbox requested but not available on this system"
            )
        except ImportError as e:
            raise SandboxNotAvailableError(f"seccomp sandbox not available: {e}")

    elif config.mode == "none":
        logger.warning(
            "Using NO sandbox! This provides NO security isolation. "
            "Only use in development or trusted environments."
        )
        return NoSandbox(config)

    else:
        raise ValueError(f"Unknown sandbox mode: {config.mode}")


async def _create_auto_sandbox(
    config: SandboxConfig, agent_type: Optional[str]
) -> SandboxExecutor:
    """Automatically select best available sandbox.

    Args:
        config: Sandbox configuration
        agent_type: Agent type identifier

    Returns:
        SandboxExecutor instance (guaranteed to return something)
    """
    # Try Capsule first for pure-Python agents
    if agent_type in PURE_PYTHON_AGENTS:
        try:
            from devloop.security.capsule_sandbox import CapsuleSandbox

            capsule_sandbox = CapsuleSandbox(config)
            if await capsule_sandbox.is_available():
                logger.info(f"Using Capsule (WASM) sandbox for {agent_type}")
                return cast(SandboxExecutor, capsule_sandbox)
        except ImportError:
            pass  # Capsule not installed, try next option

    # Try Bubblewrap next (works for all agents)
    bwrap_sandbox = BubblewrapSandbox(config)
    if await bwrap_sandbox.is_available():
        logger.info(
            f"Using Bubblewrap (Linux namespaces) sandbox for {agent_type or 'agent'}"
        )
        return bwrap_sandbox

    # Try seccomp as fallback
    try:
        from devloop.security.seccomp_sandbox import SeccompSandbox

        seccomp_sandbox = SeccompSandbox(config)
        if await seccomp_sandbox.is_available():
            logger.info(
                f"Using seccomp (syscall filtering) sandbox for {agent_type or 'agent'}"
            )
            return cast(SandboxExecutor, seccomp_sandbox)
    except ImportError:
        pass

    # Last resort: no sandbox (but with whitelist enforcement)
    logger.warning(
        f"No sandbox available for {agent_type or 'agent'}! "
        "Using direct execution with whitelist only. "
        "Install bubblewrap for security: apt-get install bubblewrap"
    )
    return NoSandbox(config)


def is_pure_python_agent(agent_type: str) -> bool:
    """Check if agent can run in pure Python (WASM-compatible).

    Args:
        agent_type: Agent type identifier

    Returns:
        True if agent is pure Python
    """
    return agent_type in PURE_PYTHON_AGENTS


def is_tool_dependent_agent(agent_type: str) -> bool:
    """Check if agent requires native system tools.

    Args:
        agent_type: Agent type identifier

    Returns:
        True if agent needs native tools
    """
    return agent_type in TOOL_DEPENDENT_AGENTS
