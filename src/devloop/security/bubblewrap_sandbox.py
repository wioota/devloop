"""Bubblewrap-based sandbox using Linux namespaces."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from devloop.security.sandbox import (
    CommandNotAllowedError,
    SandboxConfig,
    SandboxExecutor,
    SandboxResult,
    SandboxTimeoutError,
)


class BubblewrapSandbox(SandboxExecutor):
    """Linux namespace-based sandbox using Bubblewrap.

    Provides strong isolation through:
    - Filesystem isolation (read-only system, isolated /tmp)
    - Network isolation (--unshare-net)
    - Process isolation (--unshare-pid)
    - IPC isolation (--unshare-ipc)

    Requires: bwrap binary installed on system
    """

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

        # Check whitelist
        if not self._validate_whitelist(executable):
            return False

        # Verify executable exists
        exe_path = shutil.which(executable)
        if not exe_path:
            return False

        # Verify it's in a trusted system directory
        # This prevents executing arbitrary binaries from user directories
        allowed_paths = ["/usr/bin", "/usr/local/bin", "/bin", "/opt"]
        if not any(exe_path.startswith(p) for p in allowed_paths):
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
        """
        if not self.validate_command(cmd):
            raise CommandNotAllowedError(
                f"Command not allowed: {cmd[0]}. "
                f"Must be in whitelist: {self.config.allowed_tools}"
            )

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

            raise SandboxTimeoutError(
                f"Command exceeded {self.config.timeout_seconds}s timeout: {cmd}"
            )

        duration_ms = self._get_duration_ms()

        return SandboxResult(
            stdout=stdout.decode("utf-8", errors="replace") if stdout else "",
            stderr=stderr.decode("utf-8", errors="replace") if stderr else "",
            exit_code=process.returncode or 0,
            duration_ms=duration_ms,
            memory_peak_mb=0.0,  # TODO: Get from cgroups
            cpu_usage_percent=0.0,  # TODO: Get from cgroups
        )

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

        # Project directory gets read-write access
        # This allows agents to read source files and write reports
        bwrap_cmd.extend(["--bind", str(cwd), str(cwd)])

        # Essential directories
        bwrap_cmd.extend(
            [
                "--dev",
                "/dev",  # Device files
                "--proc",
                "/proc",  # Process info
                "--tmpfs",
                "/tmp",  # Isolated temporary directory
            ]
        )

        # Isolation flags
        bwrap_cmd.extend(
            [
                "--unshare-net",  # No network access
                "--unshare-pid",  # Isolated process namespace
                "--unshare-ipc",  # Isolated IPC namespace
                "--unshare-uts",  # Isolated hostname namespace
                "--die-with-parent",  # Prevent orphaned processes
            ]
        )

        # Working directory
        bwrap_cmd.extend(["--chdir", str(cwd)])

        # Environment variables (filtered to allowed list)
        filtered_env = self._filter_env_vars(env)
        for key, value in filtered_env.items():
            bwrap_cmd.extend(["--setenv", key, value])

        # Add the actual command to execute
        bwrap_cmd.extend(cmd)

        return bwrap_cmd
