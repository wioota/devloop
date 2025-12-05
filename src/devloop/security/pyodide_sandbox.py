"""Pyodide-based WASM sandbox for Python code execution.

Provides cross-platform sandboxed Python execution using Pyodide runtime
running in Node.js subprocess.
"""

from __future__ import annotations

import asyncio
import json
import logging
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
from devloop.security.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)


class PyodideSandbox(SandboxExecutor):
    """WASM-based sandbox using Pyodide runtime.

    Provides cross-platform Python code execution in isolated WASM environment
    running in Node.js subprocess.

    Requires:
    - Node.js 18+
    - Pyodide npm package (installed in project)
    """

    def __init__(self, config: SandboxConfig):
        """Initialize Pyodide sandbox.

        Args:
            config: Sandbox configuration
        """
        super().__init__(config)
        self._node_path: Optional[str] = None
        self._pyodide_runner: Optional[Path] = None
        self._runner_checked: bool = False

    async def is_available(self) -> bool:
        """Check if Node.js and Pyodide runner are available.

        Returns:
            True if Pyodide sandbox can be used
        """
        if self._runner_checked:
            return self._pyodide_runner is not None

        # Check for Node.js
        self._node_path = shutil.which("node")
        if not self._node_path:
            logger.debug("Node.js not found - Pyodide sandbox unavailable")
            self._runner_checked = True
            return False

        # Check for pyodide_runner.js in security directory
        security_dir = Path(__file__).parent
        runner_path = security_dir / "pyodide_runner.js"

        if not runner_path.exists():
            logger.debug(f"Pyodide runner not found at {runner_path}")
            self._runner_checked = True
            return False

        # Verify Node.js can load the runner (basic syntax check)
        try:
            process = await asyncio.create_subprocess_exec(
                self._node_path,
                "--check",
                str(runner_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(process.communicate(), timeout=5)

            if process.returncode != 0:
                logger.warning("Pyodide runner has syntax errors")
                self._runner_checked = True
                return False

        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"Failed to verify Pyodide runner: {e}")
            self._runner_checked = True
            return False

        self._pyodide_runner = runner_path
        self._runner_checked = True
        logger.debug("Pyodide sandbox available")
        return True

    def validate_command(self, cmd: List[str]) -> bool:
        """Validate command for Pyodide execution.

        Only Python execution commands are allowed in Pyodide sandbox.

        Args:
            cmd: Command and arguments to validate

        Returns:
            True if command is a valid Python execution
        """
        if not cmd:
            return False

        executable = cmd[0]

        # Only allow Python commands
        if executable not in ["python3", "python"]:
            logger.debug(f"Pyodide only supports Python commands, got: {executable}")
            return False

        # Check whitelist (should include python3/python)
        if not self._validate_whitelist(executable):
            return False

        # Note: We don't validate script existence here because we don't have cwd yet
        # Script existence will be validated during execution

        return True

    async def execute(
        self, cmd: List[str], cwd: Path, env: Optional[Dict[str, str]] = None
    ) -> SandboxResult:
        """Execute Python code in Pyodide WASM sandbox.

        Args:
            cmd: Python command and arguments to execute
            cwd: Working directory for execution
            env: Environment variables (limited support in WASM)

        Returns:
            SandboxResult with execution output and metrics

        Raises:
            CommandNotAllowedError: If command is not a Python execution
            SandboxTimeoutError: If execution exceeds timeout
            RuntimeError: If sandbox execution fails
        """
        audit_logger = get_audit_logger()

        if not self.validate_command(cmd):
            audit_logger.log_blocked_command(
                sandbox_mode="pyodide",
                cmd=cmd,
                cwd=cwd,
                reason="Only Python commands allowed in Pyodide sandbox",
            )
            raise CommandNotAllowedError(
                f"Pyodide sandbox only supports Python commands, got: {cmd[0]}"
            )

        if not await self.is_available():
            raise RuntimeError("Pyodide sandbox not available")

        # Prepare execution parameters
        exec_params = self._prepare_execution(cmd, cwd, env)

        # Execute in Node.js subprocess
        self._start_timer()

        try:
            process = await asyncio.create_subprocess_exec(
                self._node_path,
                str(self._pyodide_runner),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Send execution parameters via stdin
            stdin_data = json.dumps(exec_params).encode("utf-8")

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=stdin_data),
                timeout=self.config.timeout_seconds,
            )

        except asyncio.TimeoutError:
            # Kill process if it exceeds timeout
            try:
                process.kill()
                await process.wait()
            except ProcessLookupError:
                pass

            duration_ms = self._get_duration_ms()

            audit_logger.log_timeout(
                sandbox_mode="pyodide",
                cmd=cmd,
                cwd=cwd,
                duration_ms=duration_ms,
            )

            raise SandboxTimeoutError(
                f"Pyodide execution exceeded {self.config.timeout_seconds}s timeout"
            )

        duration_ms = self._get_duration_ms()

        # Parse result from stdout (JSON format)
        try:
            result_data = json.loads(stdout.decode("utf-8"))
            result = SandboxResult(
                stdout=result_data.get("stdout", ""),
                stderr=result_data.get("stderr", ""),
                exit_code=result_data.get("exitCode", process.returncode or 1),
                duration_ms=duration_ms,
                memory_peak_mb=result_data.get("memoryPeakMb", 0.0),
                cpu_usage_percent=0.0,  # WASM doesn't provide CPU metrics
            )

        except (json.JSONDecodeError, KeyError) as e:
            # If JSON parsing fails, treat as error
            logger.error(f"Failed to parse Pyodide result: {e}")
            result = SandboxResult(
                stdout="",
                stderr=f"Pyodide execution error: {stderr.decode('utf-8', errors='replace')}",
                exit_code=1,
                duration_ms=duration_ms,
                memory_peak_mb=0.0,
                cpu_usage_percent=0.0,
            )

        # Log execution
        audit_logger.log_execution(
            sandbox_mode="pyodide",
            cmd=cmd,
            cwd=cwd,
            result=result,
        )

        return result

    def _prepare_execution(
        self, cmd: List[str], cwd: Path, env: Optional[Dict[str, str]]
    ) -> Dict:
        """Prepare execution parameters for Pyodide runner.

        Args:
            cmd: Command to execute
            cwd: Working directory
            env: Environment variables

        Returns:
            Dictionary with execution parameters for JSON serialization
        """
        params = {
            "command": cmd,
            "cwd": str(cwd.resolve()),
            "timeout": self.config.timeout_seconds,
            "maxMemoryMb": self.config.max_memory_mb,
        }

        # Include filtered environment variables
        if env:
            filtered_env = self._filter_env_vars(env)
            if filtered_env:
                params["env"] = filtered_env

        return params
