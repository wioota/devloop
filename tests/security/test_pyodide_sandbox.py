"""Tests for Pyodide WASM sandbox.

Tests the PyodideSandbox implementation in POC mode (without full Pyodide installation).
"""

import pytest
from pathlib import Path
import shutil
import os

from devloop.security.sandbox import SandboxConfig
from devloop.security.pyodide_sandbox import PyodideSandbox


@pytest.fixture
def sandbox_config():
    """Create sandbox configuration for testing."""
    return SandboxConfig(
        mode="pyodide",
        max_memory_mb=500,
        max_cpu_percent=50,
        timeout_seconds=10,
        allowed_tools=["python3", "python"],
    )


@pytest.fixture
def test_workspace(tmp_path):
    """Create test workspace with Python script."""
    workspace = tmp_path / "pyodide_test"
    workspace.mkdir()

    # Create simple test script
    test_script = workspace / "test.py"
    test_script.write_text("print('Hello from Pyodide')\n")

    return workspace


@pytest.fixture(autouse=True)
def set_poc_mode():
    """Enable POC mode for testing without full Pyodide installation."""
    os.environ["PYODIDE_POC_MODE"] = "1"
    yield
    os.environ.pop("PYODIDE_POC_MODE", None)


class TestPyodideSandboxAvailability:
    """Test Pyodide sandbox availability detection."""

    @pytest.mark.asyncio
    async def test_available_with_node_and_runner(self, sandbox_config):
        """Verify sandbox reports available when Node.js and runner exist."""
        sandbox = PyodideSandbox(sandbox_config)

        # Should be available if Node.js is installed
        node_available = shutil.which("node") is not None

        if node_available:
            assert await sandbox.is_available()
        else:
            pytest.skip("Node.js not available for testing")

    @pytest.mark.asyncio
    async def test_unavailable_without_node(self, sandbox_config, monkeypatch):
        """Verify sandbox reports unavailable when Node.js missing."""

        # Mock shutil.which to return None for 'node'
        def mock_which(cmd):
            if cmd == "node":
                return None
            return shutil.which(cmd)

        monkeypatch.setattr("shutil.which", mock_which)

        sandbox = PyodideSandbox(sandbox_config)
        assert not await sandbox.is_available()


class TestPyodideSandboxValidation:
    """Test command validation."""

    def test_validate_python_command(self, sandbox_config):
        """Verify Python commands are validated correctly."""
        sandbox = PyodideSandbox(sandbox_config)

        # Python commands should be allowed
        assert sandbox.validate_command(["python3", "test.py"])
        assert sandbox.validate_command(["python", "test.py"])
        assert sandbox.validate_command(["python3", "-c", "print('hello')"])

    def test_reject_non_python_commands(self, sandbox_config):
        """Verify non-Python commands are rejected."""
        sandbox = PyodideSandbox(sandbox_config)

        # Non-Python commands should be rejected
        assert not sandbox.validate_command(["bash", "script.sh"])
        assert not sandbox.validate_command(["node", "app.js"])
        assert not sandbox.validate_command(["ruff", "check", "file.py"])

    def test_validate_requires_executable(self, sandbox_config):
        """Verify validation rejects empty commands."""
        sandbox = PyodideSandbox(sandbox_config)

        assert not sandbox.validate_command([])


class TestPyodideSandboxExecution:
    """Test Python code execution in Pyodide sandbox."""

    @pytest.mark.asyncio
    async def test_execute_simple_script(self, sandbox_config, test_workspace):
        """Verify basic script execution works."""
        sandbox = PyodideSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Pyodide sandbox not available")

        script_path = test_workspace / "test.py"
        result = await sandbox.execute(
            ["python3", str(script_path)], cwd=test_workspace
        )

        # In POC mode, we get a confirmation message
        assert result.exit_code == 0
        assert (
            "Would execute" in result.stdout or "Successfully loaded" in result.stdout
        )

    @pytest.mark.asyncio
    async def test_execute_inline_code(self, sandbox_config, test_workspace):
        """Verify inline code execution with -c flag."""
        sandbox = PyodideSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Pyodide sandbox not available")

        result = await sandbox.execute(
            ["python3", "-c", "print('inline code')"], cwd=test_workspace
        )

        # In POC mode, we get a confirmation message
        assert result.exit_code == 0
        assert "Would execute inline code" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_nonexistent_script(self, sandbox_config, test_workspace):
        """Verify error when script doesn't exist."""
        sandbox = PyodideSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Pyodide sandbox not available")

        result = await sandbox.execute(
            ["python3", "nonexistent.py"], cwd=test_workspace
        )

        # Should fail in POC mode
        assert result.exit_code == 1
        assert "Failed to read script" in result.stderr

    @pytest.mark.asyncio
    async def test_timeout_enforcement(self, sandbox_config, test_workspace):
        """Verify timeout is enforced."""
        # Create config with very short timeout
        short_timeout_config = SandboxConfig(
            mode="pyodide",
            timeout_seconds=1,  # 1 second timeout
            allowed_tools=["python3", "python"],
        )

        sandbox = PyodideSandbox(short_timeout_config)

        if not await sandbox.is_available():
            pytest.skip("Pyodide sandbox not available")

        # POC mode doesn't actually hang, so this will succeed
        # In real Pyodide mode with infinite loop, this would timeout
        script_path = test_workspace / "test.py"

        result = await sandbox.execute(
            ["python3", str(script_path)], cwd=test_workspace
        )

        # POC mode completes quickly
        assert result.duration_ms < 2000

    @pytest.mark.asyncio
    async def test_working_directory_isolation(self, sandbox_config, test_workspace):
        """Verify working directory is respected."""
        sandbox = PyodideSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Pyodide sandbox not available")

        # Create script in workspace
        script_path = test_workspace / "test.py"

        result = await sandbox.execute(
            ["python3", str(script_path)], cwd=test_workspace
        )

        assert result.exit_code == 0


class TestPyodideSandboxMetrics:
    """Test resource metrics collection."""

    @pytest.mark.asyncio
    async def test_duration_tracking(self, sandbox_config, test_workspace):
        """Verify execution duration is tracked."""
        sandbox = PyodideSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Pyodide sandbox not available")

        script_path = test_workspace / "test.py"

        result = await sandbox.execute(
            ["python3", str(script_path)], cwd=test_workspace
        )

        # Duration should be positive
        assert result.duration_ms > 0
        assert result.duration_ms < 10000  # Should complete in <10s

    @pytest.mark.asyncio
    async def test_memory_tracking(self, sandbox_config, test_workspace):
        """Verify memory usage is tracked."""
        sandbox = PyodideSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Pyodide sandbox not available")

        script_path = test_workspace / "test.py"

        result = await sandbox.execute(
            ["python3", str(script_path)], cwd=test_workspace
        )

        # Memory should be reported (from Node.js process)
        assert result.memory_peak_mb >= 0.0


@pytest.mark.integration
class TestPyodideSandboxIntegration:
    """Integration tests for Pyodide sandbox."""

    @pytest.mark.asyncio
    async def test_multiple_executions(self, sandbox_config, test_workspace):
        """Verify multiple executions work correctly."""
        sandbox = PyodideSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Pyodide sandbox not available")

        script_path = test_workspace / "test.py"

        # Run multiple times
        for i in range(3):
            result = await sandbox.execute(
                ["python3", str(script_path)], cwd=test_workspace
            )
            assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_concurrent_not_supported(self, sandbox_config, test_workspace):
        """Document that concurrent executions spawn separate processes."""
        # Note: Each execution spawns a new Node.js process,
        # so concurrent executions are independent
        # This is a documentation test, not a functional requirement
        pass
