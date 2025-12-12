"""Bubblewrap-based sandbox using Linux namespaces."""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from devloop.security.audit_logger import get_audit_logger
from devloop.security.cgroups_helper import CgroupsManager
from devloop.security.path_validator import PathValidationError
from devloop.security.sandbox import (
    CommandNotAllowedError,
    SandboxConfig,
    SandboxExecutor,
    SandboxResult,
    SandboxTimeoutError,
)

logger = logging.getLogger(__name__)


class BubblewrapSandbox(SandboxExecutor):
    """Linux namespace-based sandbox using Bubblewrap.

    Provides strong isolation through:
    - Filesystem isolation (read-only system, isolated /tmp)
    - Network isolation (--unshare-net)
    - Process isolation (--unshare-pid)
    - IPC isolation (--unshare-ipc)
    - Resource enforcement via cgroups v2 (if available)

    Requires: bwrap binary installed on system
    """

    def __init__(self, config: SandboxConfig):
        """Initialize Bubblewrap sandbox.

        Args:
            config: Sandbox configuration
        """
        super().__init__(config)
        self._cgroups_manager: Optional[CgroupsManager] = None
        self._cgroups_available: Optional[bool] = None

    async def _init_cgroups(self) -> bool:
        """Initialize cgroups if available.

        Returns:
            True if cgroups is available and initialized
        """
        if self._cgroups_available is not None:
            return self._cgroups_available

        try:
            self._cgroups_manager = CgroupsManager(cgroup_name="devloop-bwrap")
            self._cgroups_available = await self._cgroups_manager.is_available()

            if self._cgroups_available:
                logger.debug("cgroups v2 available for resource enforcement")
            else:
                logger.info("cgroups v2 not available, resource limits not enforced")

        except Exception as e:
            logger.warning(f"Failed to initialize cgroups: {e}")
            self._cgroups_available = False

        return self._cgroups_available

    async def is_available(self) -> bool:
        """Check if bwrap is installed.

        Returns:
            True if bwrap binary is found in PATH
        """
        return shutil.which("bwrap") is not None

    def validate_command(self, cmd: List[str]) -> bool:
        """Validate command against whitelist and security policies.

        Args:
            cmd: Command and arguments to validate

        Returns:
            True if command passes all security checks

        Security checks:
        1. Executable must be in whitelist
        2. Executable must exist in PATH
        3. Executable must be in trusted system directories
        """
        if not cmd:
            return False

        executable = cmd[0]

        # Check whitelist first
        if not self._validate_whitelist(executable):
            return False

        # Verify executable exists in PATH
        exe_path = shutil.which(executable)
        if not exe_path:
            return False

        # Resolve symlinks to get real path
        try:
            real_path = Path(exe_path).resolve()
        except (OSError, RuntimeError):
            return False

        # Verify it's in a trusted system directory
        # This prevents executing arbitrary binaries from user directories
        allowed_prefixes = ["/usr/bin", "/usr/local/bin", "/bin", "/opt", "/usr/lib"]
        str_path = str(real_path)

        if not any(str_path.startswith(prefix) for prefix in allowed_prefixes):
            return False

        return True

    async def execute(
        self, cmd: List[str], cwd: Path, env: Optional[Dict[str, str]] = None
    ) -> SandboxResult:
        """Execute command in Bubblewrap sandbox.

        Args:
            cmd: Command and arguments to execute
            cwd: Working directory for execution
            env: Environment variables (filtered to allowed list)

        Returns:
            SandboxResult with execution output and metrics

        Raises:
            CommandNotAllowedError: If command fails security validation
            SandboxTimeoutError: If execution exceeds timeout
            RuntimeError: If sandbox execution fails
            PathValidationError: If cwd path is invalid or malicious
        """
        audit_logger = get_audit_logger()

        # Validate working directory for security
        try:
            cwd = Path(cwd).resolve()  # Resolve symlinks
            if not cwd.exists():
                raise PathValidationError(f"Working directory does not exist: {cwd}")
            if not cwd.is_dir():
                raise PathValidationError(
                    f"Working directory is not a directory: {cwd}"
                )
            # Check for any symlink components in the path
            for parent in cwd.parents:
                if parent.is_symlink():
                    raise PathValidationError(
                        f"Working directory contains symlink component: {parent}"
                    )
        except (OSError, RuntimeError) as e:
            raise PathValidationError(
                f"Failed to validate working directory: {e}"
            ) from e

        if not self.validate_command(cmd):
            # Log blocked command attempt
            audit_logger.log_blocked_command(
                sandbox_mode="bubblewrap",
                cmd=cmd,
                cwd=cwd,
                reason=f"Command not in whitelist: {self.config.allowed_tools}",
            )
            raise CommandNotAllowedError(
                f"Command not allowed: {cmd[0]}. "
                f"Must be in whitelist: {self.config.allowed_tools}"
            )

        # Initialize cgroups if available
        cgroups_enabled = await self._init_cgroups()

        # Set up cgroups if available
        if cgroups_enabled and self._cgroups_manager:
            try:
                self._cgroups_manager.set_memory_limit(self.config.max_memory_mb)
                self._cgroups_manager.set_cpu_limit(self.config.max_cpu_percent)
                logger.debug(
                    f"cgroups limits set: {self.config.max_memory_mb}MB RAM, "
                    f"{self.config.max_cpu_percent}% CPU"
                )
            except RuntimeError as e:
                logger.warning(f"Failed to set cgroups limits: {e}")
                cgroups_enabled = False

        # Build bwrap command with strict isolation
        bwrap_cmd = self._build_bwrap_command(cmd, cwd, env)

        # Execute with timeout
        self._start_timer()

        try:
            process = await asyncio.create_subprocess_exec(
                *bwrap_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Add process to cgroup if enabled
            if cgroups_enabled and self._cgroups_manager and process.pid:
                try:
                    self._cgroups_manager.add_process(process.pid)
                    logger.debug(f"Added process {process.pid} to cgroup")
                except RuntimeError as e:
                    logger.warning(f"Failed to add process to cgroup: {e}")
                    cgroups_enabled = False

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.config.timeout_seconds
            )

        except asyncio.TimeoutError:
            # Kill process if it exceeds timeout
            try:
                process.kill()
                await process.wait()
            except ProcessLookupError:
                pass  # Process already dead

            duration_ms = self._get_duration_ms()

            # Log timeout
            audit_logger.log_timeout(
                sandbox_mode="bubblewrap",
                cmd=cmd,
                cwd=cwd,
                duration_ms=duration_ms,
            )

            # Cleanup cgroups
            if cgroups_enabled and self._cgroups_manager:
                self._cgroups_manager.cleanup()

            raise SandboxTimeoutError(
                f"Command exceeded {self.config.timeout_seconds}s timeout: {cmd}"
            )

        duration_ms = self._get_duration_ms()

        # Get resource usage from cgroups if available
        memory_peak_mb = 0.0
        cpu_usage_percent = 0.0

        if cgroups_enabled and self._cgroups_manager:
            try:
                resources = self._cgroups_manager.get_resource_usage()
                memory_peak_mb = resources.memory_peak_mb
                cpu_usage_percent = resources.cpu_usage_percent
                logger.debug(
                    f"cgroups metrics: {memory_peak_mb:.2f}MB RAM, "
                    f"{cpu_usage_percent:.1f}% CPU"
                )
            except Exception as e:
                logger.warning(f"Failed to get cgroups metrics: {e}")

        # Cleanup cgroups
        if cgroups_enabled and self._cgroups_manager:
            self._cgroups_manager.cleanup()

        result = SandboxResult(
            stdout=stdout.decode("utf-8", errors="replace") if stdout else "",
            stderr=stderr.decode("utf-8", errors="replace") if stderr else "",
            exit_code=process.returncode or 0,
            duration_ms=duration_ms,
            memory_peak_mb=memory_peak_mb,
            cpu_usage_percent=cpu_usage_percent,
        )

        # Log successful execution
        audit_logger.log_execution(
            sandbox_mode="bubblewrap",
            cmd=cmd,
            cwd=cwd,
            result=result,
        )

        return result

    def _build_bwrap_command(
        self, cmd: List[str], cwd: Path, env: Optional[Dict[str, str]]
    ) -> List[str]:
        """Build bwrap command with isolation parameters.

        Args:
            cmd: Command to wrap
            cwd: Working directory
            env: Environment variables

        Returns:
            Complete bwrap command list
        """
        bwrap_cmd = [
            "bwrap",
            # Filesystem isolation - read-only system directories
            "--ro-bind",
            "/usr",
            "/usr",
            "--ro-bind",
            "/bin",
            "/bin",
            "--ro-bind",
            "/lib",
            "/lib",
        ]

        # Add /lib64 if it exists (not present on all systems)
        if Path("/lib64").exists():
            bwrap_cmd.extend(["--ro-bind", "/lib64", "/lib64"])

        # Handle working directory binding
        # If cwd is in /tmp, we need to bind /tmp first, then the specific directory
        cwd_str = str(cwd.resolve())
        if cwd_str.startswith("/tmp/"):
            # Bind entire /tmp for test directories
            bwrap_cmd.extend(["--bind", "/tmp", "/tmp"])
        else:
            # Isolated tmpfs for non-/tmp working directories
            bwrap_cmd.extend(["--tmpfs", "/tmp"])
            # Project directory gets read-write access
            bwrap_cmd.extend(["--bind", cwd_str, cwd_str])

        # Essential directories
        bwrap_cmd.extend(
            [
                "--dev",
                "/dev",  # Device files
                "--proc",
                "/proc",  # Process info
            ]
        )

        # Isolation flags
        isolation_flags = [
            "--unshare-pid",  # Isolated process namespace
            "--unshare-ipc",  # Isolated IPC namespace
            "--unshare-uts",  # Isolated hostname namespace
            "--die-with-parent",  # Prevent orphaned processes
        ]

        # Network isolation: Only use --unshare-net if no domains are allowed
        # TODO(Phase 3): Implement selective network access using network namespaces
        # Currently: all-or-nothing (full isolation or full access)
        if not self.config.allowed_network_domains:
            isolation_flags.insert(0, "--unshare-net")  # No network access
            logger.debug("Network completely isolated (no allowed domains)")
        else:
            logger.warning(
                f"Network allowlist configured ({len(self.config.allowed_network_domains)} domains) "
                "but selective filtering not yet implemented. Network access UNRESTRICTED. "
                "See https://github.com/yourusername/devloop/issues/XXX for status."
            )

        bwrap_cmd.extend(isolation_flags)

        # Working directory
        bwrap_cmd.extend(["--chdir", str(cwd)])

        # Environment variables (filtered to allowed list)
        filtered_env = self._filter_env_vars(env)
        for key, value in filtered_env.items():
            bwrap_cmd.extend(["--setenv", key, value])

        # Add the actual command to execute
        bwrap_cmd.extend(cmd)

        return bwrap_cmd
