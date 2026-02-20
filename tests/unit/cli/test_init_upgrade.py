"""Tests for devloop init upgrade behavior.

Verifies that `devloop init` correctly handles upgrades:
- Creates manifest on fresh install
- Refreshes managed files on version upgrade
- Removes stale files no longer in template set
- Preserves user-created files
- Is idempotent when re-run at same version
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from devloop.cli.main import (
    _create_claude_hooks,
    _needs_upgrade,
    _read_init_manifest,
    _setup_claude_commands,
    _write_init_manifest,
)


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project directory structure."""
    devloop_dir = tmp_path / ".devloop"
    devloop_dir.mkdir()
    return tmp_path


@pytest.fixture
def claude_dir(project_dir: Path) -> Path:
    return project_dir / ".devloop"


class TestManifestHelpers:
    """Test _read_init_manifest, _write_init_manifest, _needs_upgrade."""

    def test_read_missing_manifest_returns_empty(self, claude_dir: Path) -> None:
        assert _read_init_manifest(claude_dir) == {}

    def test_write_and_read_manifest(self, claude_dir: Path) -> None:
        _write_init_manifest(claude_dir, "1.0.0", ["a.txt", "b.txt"])
        manifest = _read_init_manifest(claude_dir)
        assert manifest["version"] == "1.0.0"
        assert manifest["managed_files"] == ["a.txt", "b.txt"]

    def test_manifest_deduplicates_and_sorts(self, claude_dir: Path) -> None:
        _write_init_manifest(claude_dir, "1.0.0", ["b.txt", "a.txt", "b.txt"])
        manifest = _read_init_manifest(claude_dir)
        assert manifest["managed_files"] == ["a.txt", "b.txt"]

    def test_read_corrupt_manifest_returns_empty(self, claude_dir: Path) -> None:
        manifest_path = claude_dir / ".init-manifest.json"
        manifest_path.write_text("not valid json{{{")
        assert _read_init_manifest(claude_dir) == {}

    def test_needs_upgrade_no_manifest(self, claude_dir: Path) -> None:
        """Fresh install (no manifest) should need upgrade."""
        assert _needs_upgrade(claude_dir) is True

    def test_needs_upgrade_different_version(self, claude_dir: Path) -> None:
        _write_init_manifest(claude_dir, "0.8.0", [])
        with patch("devloop.cli.main._get_installed_version", return_value="0.9.0"):
            assert _needs_upgrade(claude_dir) is True

    def test_needs_upgrade_same_version(self, claude_dir: Path) -> None:
        _write_init_manifest(claude_dir, "0.9.0", [])
        with patch("devloop.cli.main._get_installed_version", return_value="0.9.0"):
            assert _needs_upgrade(claude_dir) is False


class TestUpgradeRefresh:
    """Test that managed files are refreshed on upgrade."""

    def test_hooks_overwritten_on_upgrade(self, project_dir: Path) -> None:
        hooks_dir = project_dir / ".agents" / "hooks"
        hooks_dir.mkdir(parents=True)

        # First install
        created = _create_claude_hooks(hooks_dir)
        assert len(created) > 0

        # Tamper with a hook
        first_hook = hooks_dir / created[0]
        first_hook.write_text("#!/bin/bash\n# user modified")

        # Upgrade should overwrite
        created_again = _create_claude_hooks(hooks_dir, upgrade=True)
        assert created[0] in created_again
        content = first_hook.read_text()
        assert "user modified" not in content

        # Backup should exist
        backup = first_hook.with_suffix(".bak")
        assert backup.exists()
        assert "user modified" in backup.read_text()

    def test_hooks_skipped_without_upgrade(self, project_dir: Path) -> None:
        hooks_dir = project_dir / ".agents" / "hooks"
        hooks_dir.mkdir(parents=True)

        # First install
        created = _create_claude_hooks(hooks_dir)
        assert len(created) > 0

        # Re-run without upgrade: nothing new
        created_again = _create_claude_hooks(hooks_dir)
        assert created_again == []

    def test_commands_overwritten_on_upgrade(self, project_dir: Path) -> None:
        # First install using real templates
        managed = _setup_claude_commands(project_dir)
        if not managed:
            pytest.skip("No template commands found")

        # Tamper with a command
        first_managed = project_dir / managed[0]
        first_managed.write_text("# user modified")

        # Upgrade should overwrite
        managed_again = _setup_claude_commands(project_dir, upgrade=True)
        assert len(managed_again) > 0
        content = first_managed.read_text()
        assert "user modified" not in content

        # Backup should exist
        backup = first_managed.with_suffix(first_managed.suffix + ".bak")
        assert backup.exists()


class TestStaleFileRemoval:
    """Test that stale files from previous version are removed."""

    def test_stale_files_removed(self, project_dir: Path, claude_dir: Path) -> None:
        """Files in old manifest but not in new managed set get removed."""
        # Simulate old manifest with a file that no longer exists in templates
        stale_file = project_dir / ".agents" / "hooks" / "old-hook"
        stale_file.parent.mkdir(parents=True, exist_ok=True)
        stale_file.write_text("#!/bin/bash\necho old")
        stale_file.chmod(0o755)

        old_managed = [".agents/hooks/old-hook", ".agents/hooks/some-current-hook"]
        _write_init_manifest(claude_dir, "0.8.0", old_managed)

        old_manifest = _read_init_manifest(claude_dir)
        new_managed = [".agents/hooks/some-current-hook"]

        # Simulate stale removal logic from init()
        old_set = set(old_manifest.get("managed_files", []))
        new_set = set(new_managed)
        stale = old_set - new_set
        for stale_path in stale:
            full_path = project_dir / stale_path
            if full_path.exists():
                full_path.unlink()

        assert not stale_file.exists()

    def test_user_files_not_removed(self, project_dir: Path, claude_dir: Path) -> None:
        """Files NOT in the old manifest are preserved even if not in new set."""
        user_file = project_dir / ".agents" / "hooks" / "my-custom-hook"
        user_file.parent.mkdir(parents=True, exist_ok=True)
        user_file.write_text("#!/bin/bash\necho custom")

        # Old manifest doesn't mention user_file
        _write_init_manifest(claude_dir, "0.8.0", [".agents/hooks/managed-hook"])

        old_manifest = _read_init_manifest(claude_dir)
        new_managed = [".agents/hooks/managed-hook"]

        old_set = set(old_manifest.get("managed_files", []))
        new_set = set(new_managed)
        stale = old_set - new_set

        for stale_path in stale:
            full_path = project_dir / stale_path
            if full_path.exists():
                full_path.unlink()

        # User file should still exist
        assert user_file.exists()


class TestIdempotency:
    """Test that re-running init at the same version is idempotent."""

    def test_manifest_unchanged_on_rerun(self, claude_dir: Path) -> None:
        """Writing the same manifest twice produces identical content."""
        managed = ["a.txt", "b.txt"]
        _write_init_manifest(claude_dir, "1.0.0", managed)
        first_content = (claude_dir / ".init-manifest.json").read_text()

        _write_init_manifest(claude_dir, "1.0.0", managed)
        second_content = (claude_dir / ".init-manifest.json").read_text()

        assert first_content == second_content

    def test_hooks_not_rewritten_at_same_version(self, project_dir: Path) -> None:
        """Without upgrade=True, existing hooks are not touched."""
        hooks_dir = project_dir / ".agents" / "hooks"
        hooks_dir.mkdir(parents=True)

        _create_claude_hooks(hooks_dir)

        # Get modification times
        hook_files = list(hooks_dir.iterdir())
        assert len(hook_files) > 0
        mtimes = {f.name: f.stat().st_mtime for f in hook_files}

        # Small delay to ensure mtime would differ
        import time

        time.sleep(0.05)

        # Re-run without upgrade
        _create_claude_hooks(hooks_dir)

        # Mtimes should be unchanged
        for f in hooks_dir.iterdir():
            if f.name in mtimes:
                assert (
                    f.stat().st_mtime == mtimes[f.name]
                ), f"{f.name} was unexpectedly modified"
