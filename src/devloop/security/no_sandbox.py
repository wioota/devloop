"""No-op sandbox for development and testing.

WARNING: This provides NO security isolation and should only be used
for development or in trusted environments.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, List, Optional

from devloop.security.sandbox import (
    SandboxExecutor,
    SandboxResult,
    SandboxTimeoutError,
)
from devloop.security.audit_logger import get_audit_logger


class NoSandbox(SandboxExecutor):
    """No-op sandbox that executes commands directly.

    WARNING: Provides NO security isolation!

    Use only for:
    - Development and testing
    - Trusted environments
    - When sandbox dependencies are unavailable

    This implementation:
    - Still validates whitelists (basic security)
    - Still enforces timeouts
    - Does NOT provide filesystem/network/process isolation
    """

    async def is_available(self) -> bool:
        """Always available.

        Returns:
            True
        """
        return True

    def validate_command(self, cmd: List[str]) -> bool:
        """Validate command against whitelist only.

        Args:
            cmd: Command and arguments to validate

        Returns:
            True if command is in whitelist
        """
        if not cmd:
            return False

        executable = cmd[0]
        return self._validate_whitelist(executable)

    async def execute(
        self, cmd: List[str], cwd: Path, env: Optional[Dict[str, str]] = None
    ) -> SandboxResult:
        """Execute command directly without sandboxing.

        Args:
            cmd: Command and arguments to execute
            cwd: Working directory for execution
            env: Environment variables

        Returns:
            SandboxResult with execution output

        Raises:
            SandboxTimeoutError: If execution exceeds timeout
        """
        audit_logger = get_audit_logger()

        # Still validate whitelist for basic security
        if not self.validate_command(cmd):
            # Log blocked command
            audit_logger.log_blocked_command(
                sandbox_mode="none",
                cmd=cmd,
                cwd=cwd,
                reason=f"Command not in whitelist: {self.config.allowed_tools}",
            )
            raise ValueError(
                f"Command not allowed: {cmd[0]}. "
                f"Must be in whitelist: {self.config.allowed_tools}"
            )

        self._start_timer()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,  # Don't filter env vars in no-sandbox mode
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.config.timeout_seconds
            )

        except asyncio.TimeoutError:
            try:
                process.kill()
                await process.wait()
            except ProcessLookupError:
                pass

            duration_ms = self._get_duration_ms()

            # Log timeout
            audit_logger.log_timeout(
                sandbox_mode="none",
                cmd=cmd,
                cwd=cwd,
                duration_ms=duration_ms,
            )

            raise SandboxTimeoutError(
                f"Command exceeded {self.config.timeout_seconds}s timeout: {cmd}"
            )

        duration_ms = self._get_duration_ms()

        result = SandboxResult(
            stdout=stdout.decode("utf-8", errors="replace") if stdout else "",
            stderr=stderr.decode("utf-8", errors="replace") if stderr else "",
            exit_code=process.returncode or 0,
            duration_ms=duration_ms,
        )

        # Log execution
        audit_logger.log_execution(
            sandbox_mode="none",
            cmd=cmd,
            cwd=cwd,
            result=result,
        )

        return result
