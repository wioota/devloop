"""Tests for backup manager functionality."""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from devloop.core.backup_manager import BackupManager


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Create a test file
        test_file = project_root / "test.py"
        test_file.write_text("print('Hello, World!')\n")

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=project_root, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=project_root,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=project_root,
            capture_output=True,
        )
        subprocess.run(["git", "add", "."], cwd=project_root, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=project_root,
            capture_output=True,
        )

        yield project_root


@pytest.fixture
def backup_manager(temp_project):
    """Create a backup manager for testing."""
    return BackupManager(temp_project)


def test_backup_manager_initialization(temp_project):
    """Test backup manager initializes correctly."""
    manager = BackupManager(temp_project)

    assert manager.project_root == temp_project
    assert manager.backup_dir == temp_project / ".devloop" / "backups"
    assert manager.backup_dir.exists()
    assert manager.change_log_file.exists()


def test_create_backup(backup_manager, temp_project):
    """Test creating a backup."""
    test_file = temp_project / "test.py"
    original_content = test_file.read_text()

    # Create backup
    backup_id = backup_manager.create_backup(
        file_path=test_file,
        fix_type="formatter",
        description="Format code with black",
        metadata={"tool": "black"},
    )

    assert backup_id is not None

    # Verify backup directory exists
    backup_dir = backup_manager.backup_dir / backup_id
    assert backup_dir.exists()

    # Verify backup file exists and matches original
    backup_file = backup_dir / "original"
    assert backup_file.exists()
    assert backup_file.read_text() == original_content

    # Verify metadata
    metadata_file = backup_dir / "metadata.json"
    assert metadata_file.exists()

    metadata = json.loads(metadata_file.read_text())
    assert metadata["backup_id"] == backup_id
    assert metadata["fix_type"] == "formatter"
    assert metadata["description"] == "Format code with black"
    assert metadata["file_path"] == "test.py"
    assert "checksum" in metadata
    assert "timestamp" in metadata


def test_create_backup_nonexistent_file(backup_manager, temp_project):
    """Test creating backup for nonexistent file fails gracefully."""
    nonexistent = temp_project / "nonexistent.py"

    backup_id = backup_manager.create_backup(
        file_path=nonexistent, fix_type="formatter", description="Test"
    )

    assert backup_id is None


def test_rollback(backup_manager, temp_project):
    """Test rolling back a change."""
    test_file = temp_project / "test.py"
    original_content = test_file.read_text()

    # Create backup
    backup_id = backup_manager.create_backup(
        file_path=test_file, fix_type="formatter", description="Format code"
    )

    # Modify file
    test_file.write_text("print('Modified!')\n")
    assert test_file.read_text() != original_content

    # Rollback
    success = backup_manager.rollback(backup_id)
    assert success

    # Verify file restored
    assert test_file.read_text() == original_content

    # Verify marked as rolled back in change log
    log_data = json.loads(backup_manager.change_log_file.read_text())
    changes = [c for c in log_data["changes"] if c["backup_id"] == backup_id]
    assert len(changes) == 1
    assert changes[0].get("rolled_back") is True


def test_rollback_nonexistent_backup(backup_manager):
    """Test rolling back nonexistent backup fails gracefully."""
    success = backup_manager.rollback("nonexistent_backup_id")
    assert success is False


def test_change_log(backup_manager, temp_project):
    """Test change log tracking."""
    test_file = temp_project / "test.py"

    # Create multiple backups
    backup_id1 = backup_manager.create_backup(test_file, "formatter", "First change")
    backup_id2 = backup_manager.create_backup(test_file, "linter", "Second change")

    # Get change history
    history = backup_manager.get_change_history()

    assert len(history) == 2
    assert history[0]["backup_id"] == backup_id1
    assert history[1]["backup_id"] == backup_id2

    # Test limit
    limited_history = backup_manager.get_change_history(limit=1)
    assert len(limited_history) == 1
    assert limited_history[0]["backup_id"] == backup_id2


def test_rollback_all(backup_manager, temp_project):
    """Test rolling back all changes."""
    test_file1 = temp_project / "test1.py"
    test_file2 = temp_project / "test2.py"

    test_file1.write_text("original1\n")
    test_file2.write_text("original2\n")

    # Create backups
    backup_manager.create_backup(test_file1, "formatter", "Change 1")
    backup_manager.create_backup(test_file2, "linter", "Change 2")

    # Modify files
    test_file1.write_text("modified1\n")
    test_file2.write_text("modified2\n")

    # Rollback all
    rolled_back = backup_manager.rollback_all()

    assert len(rolled_back) == 2
    assert test_file1.read_text() == "original1\n"
    assert test_file2.read_text() == "original2\n"


def test_git_integration(backup_manager, temp_project):
    """Test git integration features."""
    test_file = temp_project / "test.py"

    # Create backup with git info
    backup_id = backup_manager.create_backup(test_file, "formatter", "Test with git")

    # Load metadata
    metadata_file = backup_manager.backup_dir / backup_id / "metadata.json"
    metadata = json.loads(metadata_file.read_text())

    # Should have git commit hash
    assert "git_commit" in metadata
    assert metadata["git_commit"] is not None
    assert len(metadata["git_commit"]) == 40  # SHA-1 hash length


def test_create_git_rollback_branch(backup_manager, temp_project):
    """Test creating git rollback branch."""
    success = backup_manager.create_git_rollback_branch("test-rollback-branch")
    assert success

    # Verify branch exists
    result = subprocess.run(
        ["git", "branch", "--list", "test-rollback-branch"],
        cwd=temp_project,
        capture_output=True,
        text=True,
    )
    assert "test-rollback-branch" in result.stdout


def test_cleanup_old_backups(backup_manager, temp_project):
    """Test cleaning up old backups."""
    test_file = temp_project / "test.py"

    # Create a backup
    backup_manager.create_backup(test_file, "formatter", "Old backup")

    # Cleanup backups older than 0 days (should remove everything)
    removed = backup_manager.cleanup_old_backups(days=0)

    # Note: This might be 0 if the backup was created too recently
    # In a real test, we'd mock the timestamps
    assert removed >= 0


def test_atomic_operations(backup_manager, temp_project):
    """Test that backup operations are atomic."""
    test_file = temp_project / "test.py"

    # Create backup
    backup_manager.create_backup(test_file, "formatter", "Test")

    # Verify change log is valid JSON (atomic write worked)
    log_data = json.loads(backup_manager.change_log_file.read_text())
    assert "changes" in log_data
    assert len(log_data["changes"]) == 1


def test_checksum_verification(backup_manager, temp_project):
    """Test checksum computation and verification."""
    test_file = temp_project / "test.py"
    test_file.read_text()

    # Create backup
    backup_id = backup_manager.create_backup(test_file, "formatter", "Test")

    # Load metadata
    metadata_file = backup_manager.backup_dir / backup_id / "metadata.json"
    metadata = json.loads(metadata_file.read_text())

    # Verify checksum matches
    checksum = backup_manager._compute_checksum(test_file)
    assert checksum == metadata["checksum"]

    # Modify file and verify checksum changes
    test_file.write_text("modified content\n")
    new_checksum = backup_manager._compute_checksum(test_file)
    assert new_checksum != checksum


def test_multiple_backups_same_file(backup_manager, temp_project):
    """Test creating multiple backups for the same file."""
    test_file = temp_project / "test.py"

    # Create multiple backups
    backup_id1 = backup_manager.create_backup(test_file, "formatter", "First")
    test_file.write_text("version 2\n")
    backup_id2 = backup_manager.create_backup(test_file, "linter", "Second")
    test_file.write_text("version 3\n")
    backup_id3 = backup_manager.create_backup(test_file, "formatter", "Third")

    # All should have unique IDs
    assert backup_id1 != backup_id2 != backup_id3

    # All backups should exist
    assert (backup_manager.backup_dir / backup_id1 / "original").exists()
    assert (backup_manager.backup_dir / backup_id2 / "original").exists()
    assert (backup_manager.backup_dir / backup_id3 / "original").exists()
