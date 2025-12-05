"""Base sandbox abstraction for secure agent execution."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Literal, Optional

# Default tools allowed across all sandbox implementations
DEFAULT_ALLOWED_TOOLS = [
    # Python
    "python3",
    "python",
    # Version control
    "git",
    # Python linting/formatting
    "ruff",
    "black",
    "mypy",
    "bandit",
    "radon",
    # Testing
    "pytest",
    # JavaScript tools
    "eslint",
    "prettier",
    # Security
    "snyk",
    # GitHub CLI
    "gh",
]


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution.

    Attributes:
        mode: Sandbox implementation to use
        max_memory_mb: Maximum memory in megabytes
        max_cpu_percent: Maximum CPU usage percentage
        timeout_seconds: Execution timeout in seconds
        allowed_tools: Whitelist of executable names
        allowed_network_domains: Whitelist of network domains
        allowed_env_vars: Whitelist of environment variable names
    """

    mode: Literal["capsule", "bubblewrap", "seccomp", "none", "auto"] = "auto"
    max_memory_mb: int = 500
    max_cpu_percent: int = 25
    timeout_seconds: int = 30
    allowed_tools: List[str] = field(default_factory=lambda: DEFAULT_ALLOWED_TOOLS.copy())
    allowed_network_domains: List[str] = field(default_factory=list)
    allowed_env_vars: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate configuration."""
        if self.max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive")
        if self.max_cpu_percent <= 0 or self.max_cpu_percent > 100:
            raise ValueError("max_cpu_percent must be between 1 and 100")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass
class SandboxResult:
    """Result from sandbox execution.

    Attributes:
        stdout: Standard output from execution
        stderr: Standard error from execution
        exit_code: Process exit code
        duration_ms: Execution duration in milliseconds
        memory_peak_mb: Peak memory usage in megabytes
        cpu_usage_percent: CPU usage percentage
        fuel_consumed: WASM fuel consumed (Capsule-specific)
    """

    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    memory_peak_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    fuel_consumed: Optional[int] = None  # WASM-specific metric


class SandboxExecutor(ABC):
    """Abstract base class for sandbox implementations.

    Provides common interface for different sandboxing technologies:
    - Capsule (WASM-based, for pure Python)
    - Bubblewrap (Linux namespaces, for native tools)
    - seccomp-bpf (Syscall filtering, fallback)
    - None (No sandboxing, development only)
    """

    def __init__(self, config: SandboxConfig):
        """Initialize sandbox executor.

        Args:
            config: Sandbox configuration
        """
        self.config = config
        self._start_time: Optional[float] = None

    @abstractmethod
    async def execute(
        self, cmd: List[str], cwd: Path, env: Optional[Dict[str, str]] = None
    ) -> SandboxResult:
        """Execute command in sandbox.

        Args:
            cmd: Command and arguments to execute
            cwd: Working directory for execution
            env: Environment variables

        Returns:
            SandboxResult containing execution output and metrics

        Raises:
            ValueError: If command is not allowed
            TimeoutError: If execution exceeds timeout
            RuntimeError: If sandbox execution fails
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this sandbox implementation is available.

        Returns:
            True if sandbox can be used, False otherwise
        """
        pass

    @abstractmethod
    def validate_command(self, cmd: List[str]) -> bool:
        """Validate command against security policies.

        Args:
            cmd: Command and arguments to validate

        Returns:
            True if command is allowed, False otherwise
        """
        pass

    def _start_timer(self) -> None:
        """Start execution timer."""
        self._start_time = time.perf_counter()

    def _get_duration_ms(self) -> int:
        """Get execution duration in milliseconds.

        Returns:
            Duration in milliseconds

        Raises:
            RuntimeError: If timer was not started
        """
        if self._start_time is None:
            raise RuntimeError("Timer not started")
        return int((time.perf_counter() - self._start_time) * 1000)

    def _validate_whitelist(self, executable: str) -> bool:
        """Check if executable is in whitelist.

        Args:
            executable: Name of executable to check

        Returns:
            True if executable is allowed, False otherwise
        """
        return executable in self.config.allowed_tools

    def _filter_env_vars(self, env: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Filter environment variables to allowed list.

        Args:
            env: Environment variables to filter

        Returns:
            Filtered environment variables
        """
        if not env:
            return {}

        if not self.config.allowed_env_vars:
            # If no env vars allowed, return empty dict
            return {}

        return {k: v for k, v in env.items() if k in self.config.allowed_env_vars}


class SandboxError(Exception):
    """Base exception for sandbox errors."""

    pass


class SandboxNotAvailableError(SandboxError):
    """Raised when requested sandbox is not available."""

    pass


class CommandNotAllowedError(SandboxError):
    """Raised when command is blocked by security policy."""

    pass


class SandboxTimeoutError(SandboxError):
    """Raised when execution exceeds timeout."""

    pass


class ResourceLimitExceededError(SandboxError):
    """Raised when resource limits are exceeded."""

    pass
