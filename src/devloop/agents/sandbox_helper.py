"""Helper utilities for agents to use sandbox execution.

This module provides a simple API for agents to execute commands in a sandbox
without needing to understand the details of sandbox configuration and selection.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from devloop.security.factory import create_sandbox
from devloop.security.sandbox import (
    CommandNotAllowedError,
    SandboxConfig,
    SandboxExecutor,
    SandboxResult,
    SandboxTimeoutError,
)

logger = logging.getLogger(__name__)


class AgentSandboxHelper:
    """Helper class for agents to use sandbox execution.

    This provides a simple interface for agents to run commands in a sandbox
    without needing to manage sandbox lifecycle or configuration details.
    """

    def __init__(
        self,
        agent_name: str,
        agent_type: str,
        config: Optional[SandboxConfig] = None,
    ):
        """Initialize sandbox helper for an agent.

        Args:
            agent_name: Name of the agent (for logging)
            agent_type: Type of agent (for sandbox selection, e.g., "linter", "formatter")
            config: Optional sandbox configuration (uses defaults if not provided)
        """
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.config = config or SandboxConfig()
        self._sandbox: Optional[SandboxExecutor] = None
        self._sandbox_initialized = False

    async def _get_sandbox(self) -> SandboxExecutor:
        """Get or create sandbox executor.

        Returns:
            SandboxExecutor instance
        """
        if self._sandbox is None or not self._sandbox_initialized:
            self._sandbox = await create_sandbox(self.config, self.agent_type)
            self._sandbox_initialized = True
            logger.debug(
                f"Initialized sandbox for {self.agent_name} ({self.agent_type})"
            )
        return self._sandbox

    async def run_sandboxed(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> SandboxResult:
        """Run a command in the sandbox.

        This is the main method agents should use to execute commands safely.

        Args:
            cmd: Command and arguments to execute
            cwd: Working directory (defaults to current directory)
            env: Environment variables (will be filtered to allowed list)
            timeout: Optional timeout override (uses config default if not provided)

        Returns:
            SandboxResult with stdout, stderr, exit_code, and metrics

        Raises:
            CommandNotAllowedError: If command is not in whitelist
            SandboxTimeoutError: If execution exceeds timeout
            RuntimeError: If sandbox execution fails

        Example:
            >>> helper = AgentSandboxHelper("linter", "linter")
            >>> result = await helper.run_sandboxed(["ruff", "check", "file.py"])
            >>> if result.exit_code == 0:
            ...     print(result.stdout)
        """
        sandbox = await self._get_sandbox()

        # Use provided cwd or default to current directory
        if cwd is None:
            cwd = Path.cwd()

        # Merge environment with current environment if provided
        if env is not None:
            merged_env = os.environ.copy()
            merged_env.update(env)
            env = merged_env

        # Override timeout if provided
        if timeout is not None:
            original_timeout = self.config.timeout_seconds
            self.config.timeout_seconds = timeout
            try:
                result = await sandbox.execute(cmd, cwd, env)
            finally:
                self.config.timeout_seconds = original_timeout
        else:
            result = await sandbox.execute(cmd, cwd, env)

        logger.debug(
            f"{self.agent_name}: Executed {cmd[0]} in {result.duration_ms}ms "
            f"(exit={result.exit_code})"
        )

        return result

    async def check_tool_available(self, tool_name: str) -> bool:
        """Check if a tool is available and allowed in the sandbox.

        Args:
            tool_name: Name of the tool to check (e.g., "ruff", "black")

        Returns:
            True if tool is available and allowed, False otherwise

        Example:
            >>> helper = AgentSandboxHelper("linter", "linter")
            >>> if await helper.check_tool_available("ruff"):
            ...     result = await helper.run_sandboxed(["ruff", "check", "file.py"])
        """
        try:
            result = await self.run_sandboxed(
                [tool_name, "--version"],
                timeout=5,  # Quick check
            )
            return result.exit_code == 0
        except (CommandNotAllowedError, RuntimeError):
            return False
        except SandboxTimeoutError:
            # If it times out on --version, something is wrong
            return False

    async def run_sandboxed_with_venv(
        self,
        cmd: List[str],
        venv_path: Path,
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxResult:
        """Run a command with a Python virtual environment in PATH.

        This is a convenience method for agents that need to run Python tools
        installed in a virtual environment.

        Args:
            cmd: Command and arguments to execute
            venv_path: Path to virtual environment root
            cwd: Working directory
            env: Additional environment variables

        Returns:
            SandboxResult from execution

        Example:
            >>> helper = AgentSandboxHelper("linter", "linter")
            >>> venv = Path(__file__).parent.parent.parent.parent / ".venv"
            >>> result = await helper.run_sandboxed_with_venv(
            ...     ["ruff", "check", "file.py"],
            ...     venv_path=venv
            ... )
        """
        # Add venv bin to PATH
        venv_bin = venv_path / "bin"
        if not venv_bin.exists():
            raise ValueError(f"Virtual environment bin not found: {venv_bin}")

        # Prepare environment with venv in PATH
        env = env or {}
        env["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"

        return await self.run_sandboxed(cmd, cwd, env)


def create_agent_sandbox_helper(
    agent_name: str,
    agent_type: str,
    config: Optional[Dict] = None,
) -> AgentSandboxHelper:
    """Factory function to create a sandbox helper for an agent.

    This is the recommended way for agents to create their sandbox helper.

    Args:
        agent_name: Name of the agent
        agent_type: Type identifier (e.g., "linter", "formatter", "type_checker")
        config: Optional configuration dict (will be converted to SandboxConfig)

    Returns:
        AgentSandboxHelper instance ready to use

    Example:
        >>> # In an agent's __init__:
        >>> from devloop.agents.sandbox_helper import create_agent_sandbox_helper
        >>> self.sandbox = create_agent_sandbox_helper(
        ...     agent_name=self.name,
        ...     agent_type="linter"
        ... )
        >>>
        >>> # In the agent's handle method:
        >>> result = await self.sandbox.run_sandboxed(["ruff", "check", str(path)])
    """
    sandbox_config = None
    if config:
        # Convert config dict to SandboxConfig if provided
        sandbox_config = SandboxConfig(**config)

    return AgentSandboxHelper(
        agent_name=agent_name,
        agent_type=agent_type,
        config=sandbox_config,
    )
