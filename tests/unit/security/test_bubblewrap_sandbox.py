"""Tests for BubblewrapSandbox command validation and bwrap command building."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devloop.security.bubblewrap_sandbox import BubblewrapSandbox
from devloop.security.sandbox import SandboxConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config() -> SandboxConfig:
    return SandboxConfig(
        mode="bubblewrap",
        max_memory_mb=256,
        max_cpu_percent=25,
        timeout_seconds=10,
        allowed_tools=["python3", "ruff", "black"],
        allowed_network_domains=[],
        allowed_env_vars=["PATH", "HOME"],
    )


@pytest.fixture
def sandbox(config: SandboxConfig) -> BubblewrapSandbox:
    return BubblewrapSandbox(config)


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------


class TestIsAvailable:
    @pytest.mark.asyncio
    async def test_available_when_bwrap_found(self, sandbox: BubblewrapSandbox) -> None:
        with patch(
            "devloop.security.bubblewrap_sandbox.shutil.which",
            return_value="/usr/bin/bwrap",
        ):
            assert await sandbox.is_available() is True

    @pytest.mark.asyncio
    async def test_not_available_when_bwrap_missing(
        self, sandbox: BubblewrapSandbox
    ) -> None:
        with patch(
            "devloop.security.bubblewrap_sandbox.shutil.which", return_value=None
        ):
            assert await sandbox.is_available() is False


# ---------------------------------------------------------------------------
# validate_command
# ---------------------------------------------------------------------------


class TestValidateCommand:
    def test_empty_cmd_rejected(self, sandbox: BubblewrapSandbox) -> None:
        assert sandbox.validate_command([]) is False

    def test_command_not_in_whitelist_rejected(
        self, sandbox: BubblewrapSandbox
    ) -> None:
        with patch(
            "devloop.security.bubblewrap_sandbox.shutil.which",
            return_value="/usr/bin/rm",
        ):
            assert sandbox.validate_command(["rm", "-rf", "/"]) is False

    def test_whitelisted_command_not_in_path(self, sandbox: BubblewrapSandbox) -> None:
        with patch(
            "devloop.security.bubblewrap_sandbox.shutil.which", return_value=None
        ):
            assert sandbox.validate_command(["python3"]) is False

    def test_whitelisted_command_in_trusted_dir(
        self, sandbox: BubblewrapSandbox
    ) -> None:
        with patch(
            "devloop.security.bubblewrap_sandbox.shutil.which",
            return_value="/usr/bin/python3",
        ):
            with patch.object(Path, "resolve", return_value=Path("/usr/bin/python3")):
                assert sandbox.validate_command(["python3", "-c", "pass"]) is True

    def test_whitelisted_command_in_untrusted_dir(
        self, sandbox: BubblewrapSandbox
    ) -> None:
        with patch(
            "devloop.security.bubblewrap_sandbox.shutil.which",
            return_value="/home/user/.local/bin/python3",
        ):
            with patch.object(
                Path, "resolve", return_value=Path("/home/user/.local/bin/python3")
            ):
                assert sandbox.validate_command(["python3"]) is False

    def test_whitelisted_command_resolve_raises(
        self, sandbox: BubblewrapSandbox
    ) -> None:
        with patch(
            "devloop.security.bubblewrap_sandbox.shutil.which",
            return_value="/usr/bin/python3",
        ):
            with patch.object(Path, "resolve", side_effect=OSError("broken symlink")):
                assert sandbox.validate_command(["python3"]) is False

    def test_command_in_opt_directory_accepted(
        self, sandbox: BubblewrapSandbox
    ) -> None:
        with patch(
            "devloop.security.bubblewrap_sandbox.shutil.which",
            return_value="/opt/python/bin/python3",
        ):
            with patch.object(
                Path, "resolve", return_value=Path("/opt/python/bin/python3")
            ):
                assert sandbox.validate_command(["python3"]) is True


# ---------------------------------------------------------------------------
# _init_cgroups
# ---------------------------------------------------------------------------


class TestInitCgroups:
    @pytest.mark.asyncio
    async def test_cgroups_available(self, sandbox: BubblewrapSandbox) -> None:
        mock_mgr = MagicMock()
        mock_mgr.is_available = AsyncMock(return_value=True)

        with patch(
            "devloop.security.bubblewrap_sandbox.CgroupsManager",
            return_value=mock_mgr,
        ):
            result = await sandbox._init_cgroups()
            assert result is True
            assert sandbox._cgroups_available is True

    @pytest.mark.asyncio
    async def test_cgroups_not_available(self, sandbox: BubblewrapSandbox) -> None:
        mock_mgr = MagicMock()
        mock_mgr.is_available = AsyncMock(return_value=False)

        with patch(
            "devloop.security.bubblewrap_sandbox.CgroupsManager",
            return_value=mock_mgr,
        ):
            result = await sandbox._init_cgroups()
            assert result is False

    @pytest.mark.asyncio
    async def test_cgroups_init_error_handled(self, sandbox: BubblewrapSandbox) -> None:
        with patch(
            "devloop.security.bubblewrap_sandbox.CgroupsManager",
            side_effect=RuntimeError("cgroups broken"),
        ):
            result = await sandbox._init_cgroups()
            assert result is False
            assert sandbox._cgroups_available is False

    @pytest.mark.asyncio
    async def test_cgroups_cached_on_second_call(
        self, sandbox: BubblewrapSandbox
    ) -> None:
        sandbox._cgroups_available = True  # Pre-set cache
        result = await sandbox._init_cgroups()
        assert result is True  # Returns cached value without re-initializing


# ---------------------------------------------------------------------------
# _build_bwrap_command
# ---------------------------------------------------------------------------


class TestBuildBwrapCommand:
    def test_basic_command_structure(
        self, sandbox: BubblewrapSandbox, tmp_path: Path
    ) -> None:
        result = sandbox._build_bwrap_command(
            cmd=["python3", "test.py"], cwd=tmp_path, env=None
        )
        assert result[0] == "bwrap"
        assert "--ro-bind" in result
        assert "--unshare-pid" in result
        assert "--unshare-ipc" in result
        assert "--die-with-parent" in result
        # Command should be at the end
        assert result[-2] == "python3"
        assert result[-1] == "test.py"

    def test_network_isolated_by_default(
        self, sandbox: BubblewrapSandbox, tmp_path: Path
    ) -> None:
        result = sandbox._build_bwrap_command(cmd=["python3"], cwd=tmp_path, env=None)
        assert "--unshare-net" in result

    def test_network_not_isolated_with_domains(
        self, config: SandboxConfig, tmp_path: Path
    ) -> None:
        config.allowed_network_domains = ["pypi.org"]
        sandbox = BubblewrapSandbox(config)
        result = sandbox._build_bwrap_command(cmd=["python3"], cwd=tmp_path, env=None)
        assert "--unshare-net" not in result

    def test_chdir_set_to_cwd(self, sandbox: BubblewrapSandbox, tmp_path: Path) -> None:
        result = sandbox._build_bwrap_command(cmd=["python3"], cwd=tmp_path, env=None)
        chdir_idx = result.index("--chdir")
        assert result[chdir_idx + 1] == str(tmp_path)

    def test_env_vars_filtered(
        self, sandbox: BubblewrapSandbox, tmp_path: Path
    ) -> None:
        result = sandbox._build_bwrap_command(
            cmd=["python3"],
            cwd=tmp_path,
            env={"PATH": "/usr/bin", "HOME": "/home/u", "SECRET": "bad"},
        )
        # PATH and HOME are in allowed_env_vars, SECRET is not
        assert "--setenv" in result
        setenv_indices = [i for i, v in enumerate(result) if v == "--setenv"]
        env_keys = [result[i + 1] for i in setenv_indices]
        assert "PATH" in env_keys
        assert "HOME" in env_keys
        assert "SECRET" not in env_keys

    def test_tmp_cwd_binds_tmp(self, sandbox: BubblewrapSandbox) -> None:
        tmp_cwd = Path("/tmp/pytest-123/test_0")
        result = sandbox._build_bwrap_command(cmd=["python3"], cwd=tmp_cwd, env=None)
        # Should bind /tmp directly, not use --tmpfs /tmp
        bind_idx = [
            i for i, v in enumerate(result) if v == "--bind" and result[i + 1] == "/tmp"
        ]
        assert len(bind_idx) == 1

    def test_non_tmp_cwd_uses_tmpfs(self, sandbox: BubblewrapSandbox) -> None:
        project_cwd = Path("/home/user/project")
        result = sandbox._build_bwrap_command(
            cmd=["python3"], cwd=project_cwd, env=None
        )
        assert "--tmpfs" in result
        tmpfs_idx = result.index("--tmpfs")
        assert result[tmpfs_idx + 1] == "/tmp"

    def test_lib64_included_when_exists(
        self, sandbox: BubblewrapSandbox, tmp_path: Path
    ) -> None:
        with patch.object(Path, "exists", return_value=True):
            result = sandbox._build_bwrap_command(
                cmd=["python3"], cwd=tmp_path, env=None
            )
            # Should have --ro-bind /lib64 /lib64
            ro_bind_pairs = []
            for i, v in enumerate(result):
                if v == "--ro-bind" and i + 2 < len(result):
                    ro_bind_pairs.append((result[i + 1], result[i + 2]))
            lib64_binds = [p for p in ro_bind_pairs if p[0] == "/lib64"]
            assert len(lib64_binds) >= 1
