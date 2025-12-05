"""Security tests for sandbox escape prevention.

These tests verify that sandboxes properly block malicious commands
and prevent various attack vectors.
"""

import pytest
from pathlib import Path
from devloop.security.sandbox import SandboxConfig, CommandNotAllowedError, SandboxTimeoutError
from devloop.security.bubblewrap_sandbox import BubblewrapSandbox
from devloop.security.no_sandbox import NoSandbox


@pytest.fixture
def sandbox_config():
    """Create test sandbox configuration."""
    return SandboxConfig(
        mode="bubblewrap",
        max_memory_mb=100,
        max_cpu_percent=25,
        timeout_seconds=5,
        allowed_tools=["python3", "echo", "cat"],
        allowed_env_vars=["TEST_VAR"],
    )


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "test.txt").write_text("Hello, world!")
    return workspace


class TestCommandWhitelisting:
    """Test that only whitelisted commands can execute."""

    @pytest.mark.asyncio
    async def test_whitelisted_command_allowed(self, sandbox_config, temp_workspace):
        """Whitelisted commands should execute successfully."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        result = await sandbox.execute(
            ["echo", "test"], cwd=temp_workspace
        )

        assert result.exit_code == 0
        assert "test" in result.stdout

    @pytest.mark.asyncio
    async def test_non_whitelisted_command_blocked(self, sandbox_config, temp_workspace):
        """Non-whitelisted commands should be blocked."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        with pytest.raises(CommandNotAllowedError):
            await sandbox.execute(
                ["rm", "-rf", "/"],  # Dangerous command not in whitelist
                cwd=temp_workspace
            )

    @pytest.mark.asyncio
    async def test_shell_command_blocked(self, sandbox_config, temp_workspace):
        """Shell commands should be blocked."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        with pytest.raises(CommandNotAllowedError):
            await sandbox.execute(
                ["bash", "-c", "cat /etc/passwd"],  # Shell not in whitelist
                cwd=temp_workspace
            )

    @pytest.mark.asyncio
    async def test_sh_command_blocked(self, sandbox_config, temp_workspace):
        """sh commands should be blocked."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        with pytest.raises(CommandNotAllowedError):
            await sandbox.execute(
                ["sh", "-c", "ls"],  # sh not in whitelist
                cwd=temp_workspace
            )


class TestFilesystemIsolation:
    """Test filesystem access restrictions."""

    @pytest.mark.asyncio
    async def test_workspace_access_allowed(self, sandbox_config, temp_workspace):
        """Sandbox should allow access to workspace directory."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        result = await sandbox.execute(
            ["cat", "test.txt"], cwd=temp_workspace
        )

        assert result.exit_code == 0
        assert "Hello, world!" in result.stdout

    @pytest.mark.asyncio
    async def test_system_files_isolated(self, sandbox_config, temp_workspace):
        """Sandbox should prevent access to system files outside workspace."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Try to read /etc/passwd (should fail due to isolation)
        result = await sandbox.execute(
            ["cat", "/etc/passwd"], cwd=temp_workspace
        )

        # Should either fail to find file or get permission denied
        assert result.exit_code != 0

    @pytest.mark.asyncio
    async def test_tmp_directory_isolated(self, sandbox_config, temp_workspace):
        """Each sandbox execution should have isolated /tmp."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Write to /tmp in first execution
        result1 = await sandbox.execute(
            ["python3", "-c", "open('/tmp/test', 'w').write('data1')"],
            cwd=temp_workspace
        )
        assert result1.exit_code == 0

        # Try to read from /tmp in second execution (should fail - isolated)
        result2 = await sandbox.execute(
            ["python3", "-c", "print(open('/tmp/test').read())"],
            cwd=temp_workspace
        )

        # File should not exist in new sandbox instance
        assert result2.exit_code != 0


class TestTimeoutEnforcement:
    """Test execution timeout enforcement."""

    @pytest.mark.asyncio
    async def test_timeout_enforced(self, sandbox_config, temp_workspace):
        """Commands that exceed timeout should be killed."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        with pytest.raises(SandboxTimeoutError):
            # Sleep longer than timeout
            await sandbox.execute(
                ["python3", "-c", "import time; time.sleep(10)"],
                cwd=temp_workspace
            )

    @pytest.mark.asyncio
    async def test_timeout_allows_short_execution(self, sandbox_config, temp_workspace):
        """Commands that finish within timeout should succeed."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        result = await sandbox.execute(
            ["python3", "-c", "import time; time.sleep(0.1); print('done')"],
            cwd=temp_workspace
        )

        assert result.exit_code == 0
        assert "done" in result.stdout


class TestEnvironmentVariableFiltering:
    """Test environment variable filtering."""

    @pytest.mark.asyncio
    async def test_allowed_env_vars_passed(self, sandbox_config, temp_workspace):
        """Allowed environment variables should be passed through."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        result = await sandbox.execute(
            ["python3", "-c", "import os; print(os.getenv('TEST_VAR'))"],
            cwd=temp_workspace,
            env={"TEST_VAR": "secret_value"}
        )

        assert result.exit_code == 0
        assert "secret_value" in result.stdout

    @pytest.mark.asyncio
    async def test_non_allowed_env_vars_filtered(self, sandbox_config, temp_workspace):
        """Non-allowed environment variables should be filtered out."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        result = await sandbox.execute(
            ["python3", "-c", "import os; print(os.getenv('FORBIDDEN_VAR', 'not_set'))"],
            cwd=temp_workspace,
            env={"FORBIDDEN_VAR": "should_not_appear"}
        )

        assert result.exit_code == 0
        assert "not_set" in result.stdout
        assert "should_not_appear" not in result.stdout


class TestNetworkIsolation:
    """Test network isolation."""

    @pytest.mark.asyncio
    async def test_network_access_blocked(self, sandbox_config, temp_workspace):
        """Network access should be blocked by default."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Try to make network connection
        result = await sandbox.execute(
            [
                "python3", "-c",
                "import socket; sock = socket.socket(); sock.connect(('8.8.8.8', 53))"
            ],
            cwd=temp_workspace
        )

        # Should fail due to network isolation
        assert result.exit_code != 0


class TestMaliciousScenarios:
    """Test protection against malicious scenarios."""

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, sandbox_config, temp_workspace):
        """Path traversal attempts should be blocked."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Try to read file outside workspace using path traversal
        result = await sandbox.execute(
            ["cat", "../../../../etc/passwd"],
            cwd=temp_workspace
        )

        # Should fail (file not found in isolated environment)
        assert result.exit_code != 0

    @pytest.mark.asyncio
    async def test_fork_bomb_prevented(self, sandbox_config, temp_workspace):
        """Fork bomb attempts should be prevented."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Try to create many processes
        with pytest.raises(SandboxTimeoutError):
            await sandbox.execute(
                [
                    "python3", "-c",
                    "import os; [os.fork() for _ in range(1000)]"
                ],
                cwd=temp_workspace
            )

    @pytest.mark.asyncio
    async def test_memory_bomb_handled(self, sandbox_config, temp_workspace):
        """Memory exhaustion attempts should timeout."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        with pytest.raises(SandboxTimeoutError):
            await sandbox.execute(
                [
                    "python3", "-c",
                    "data = []; [data.append(' ' * 10**6) for _ in range(10000)]"
                ],
                cwd=temp_workspace
            )


class TestNoSandboxFallback:
    """Test no-sandbox mode still enforces basic security."""

    @pytest.mark.asyncio
    async def test_whitelist_still_enforced(self, sandbox_config, temp_workspace):
        """Even with no sandbox, whitelist should be enforced."""
        sandbox = NoSandbox(sandbox_config)

        with pytest.raises(ValueError, match="not allowed"):
            await sandbox.execute(
                ["rm", "-rf", "/"],
                cwd=temp_workspace
            )

    @pytest.mark.asyncio
    async def test_timeout_still_enforced(self, sandbox_config, temp_workspace):
        """Even with no sandbox, timeout should be enforced."""
        sandbox = NoSandbox(sandbox_config)

        with pytest.raises(SandboxTimeoutError):
            await sandbox.execute(
                ["python3", "-c", "import time; time.sleep(10)"],
                cwd=temp_workspace
            )
