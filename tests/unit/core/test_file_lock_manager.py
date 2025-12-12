"""Tests for file lock manager and race condition prevention."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from devloop.core.file_lock_manager import (
    FileLockManager,
    FileLockContext,
    FileVersion,
    LockMode,
)


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
        f.write("test content\n")
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink()


@pytest.fixture
def lock_manager():
    """Create a fresh lock manager for testing."""
    manager = FileLockManager()
    yield manager
    # Cleanup
    asyncio.run(manager.reset())


class TestFileVersion:
    """Tests for FileVersion dataclass."""

    def test_version_creation(self):
        """Test creating a FileVersion."""
        version = FileVersion(
            etag="abc123",
            size=1024,
            mtime=1234567890.0,
            modified_by="formatter",
        )

        assert version.etag == "abc123"
        assert version.size == 1024
        assert version.modified_by == "formatter"

    def test_version_equality(self):
        """Test version equality comparison."""
        v1 = FileVersion(etag="abc123", size=100, mtime=1.0)
        v2 = FileVersion(etag="abc123", size=200, mtime=2.0)
        v3 = FileVersion(etag="def456", size=100, mtime=1.0)

        assert v1 == v2  # Same etag
        assert v1 != v3  # Different etag

    def test_version_hash(self):
        """Test version hashing."""
        v1 = FileVersion(etag="abc123", size=100, mtime=1.0)
        v2 = FileVersion(etag="abc123", size=200, mtime=2.0)

        # Same etag means same hash
        assert hash(v1) == hash(v2)


class TestFileLockManager:
    """Tests for FileLockManager."""

    @pytest.mark.asyncio
    async def test_exclusive_lock_acquisition(self, lock_manager, temp_file):
        """Test acquiring an exclusive lock."""
        acquired = await lock_manager.acquire_lock(
            temp_file, "agent1", LockMode.EXCLUSIVE
        )
        assert acquired is True

        # Verify lock is recorded
        status = lock_manager.get_file_status(temp_file)
        assert status["locked"] is True
        assert status["lock_mode"] == LockMode.EXCLUSIVE

        await lock_manager.release_lock(temp_file, "agent1")

    @pytest.mark.asyncio
    async def test_exclusive_lock_conflict(self, lock_manager, temp_file):
        """Test exclusive lock conflict."""
        # Agent 1 acquires exclusive lock
        acquired1 = await lock_manager.acquire_lock(
            temp_file, "agent1", LockMode.EXCLUSIVE
        )
        assert acquired1 is True

        # Agent 2 tries to acquire exclusive lock (should fail)
        acquired2 = await lock_manager.acquire_lock(
            temp_file, "agent2", LockMode.EXCLUSIVE, timeout=0.1
        )
        assert acquired2 is False

        await lock_manager.release_lock(temp_file, "agent1")

    @pytest.mark.asyncio
    async def test_lock_release(self, lock_manager, temp_file):
        """Test lock release."""
        # Acquire lock
        await lock_manager.acquire_lock(temp_file, "agent1", LockMode.EXCLUSIVE)

        # Verify locked
        assert lock_manager.get_file_status(temp_file)["locked"] is True

        # Release lock
        await lock_manager.release_lock(temp_file, "agent1")

        # Verify unlocked
        status = lock_manager.get_file_status(temp_file)
        assert status["locked"] is False

    @pytest.mark.asyncio
    async def test_check_version_no_change(self, lock_manager, temp_file):
        """Test version check when file hasn't changed."""
        version1 = lock_manager._get_file_version(temp_file)

        is_changed, version2 = await lock_manager.check_version(
            temp_file, version1.etag
        )

        assert is_changed is False
        assert version2.etag == version1.etag

    @pytest.mark.asyncio
    async def test_check_version_changed(self, lock_manager, temp_file):
        """Test version check when file has been modified."""
        version1 = lock_manager._get_file_version(temp_file)

        # Modify the file
        with open(temp_file, "w") as f:
            f.write("modified content\n")

        is_changed, version2 = await lock_manager.check_version(
            temp_file, version1.etag
        )

        assert is_changed is True
        assert version2.etag != version1.etag

    @pytest.mark.asyncio
    async def test_record_modification(self, lock_manager, temp_file):
        """Test recording a modification."""
        # Modify the file
        with open(temp_file, "w") as f:
            f.write("new content\n")

        # Record modification
        version = await lock_manager.record_modification(temp_file, "formatter")

        assert version.modified_by == "formatter"
        assert version.modified_at is not None

        # Verify stored
        stored_version = lock_manager._file_versions[str(temp_file.resolve())]
        assert stored_version.modified_by == "formatter"

    @pytest.mark.asyncio
    async def test_file_version_calculation(self, lock_manager, temp_file):
        """Test file version calculation with etag."""
        version = lock_manager._get_file_version(temp_file)

        assert version.etag is not None
        assert len(version.etag) == 64  # SHA256 hex length
        assert version.size > 0
        assert version.mtime > 0

    @pytest.mark.asyncio
    async def test_reset(self, lock_manager, temp_file):
        """Test resetting all locks."""
        # Acquire locks
        await lock_manager.acquire_lock(temp_file, "agent1", LockMode.EXCLUSIVE)

        # Reset
        await lock_manager.reset()

        # Verify all cleared
        assert len(lock_manager._file_locks) == 0
        assert len(lock_manager._lock_modes) == 0
        assert len(lock_manager._readers) == 0


class TestFileLockContext:
    """Tests for FileLockContext async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_success(self, lock_manager, temp_file):
        """Test successful lock acquisition and release with context manager."""
        async with FileLockContext(temp_file, "agent1", LockMode.EXCLUSIVE) as ctx:
            assert ctx.lock_acquired is True

        # Lock should be released after context
        status = lock_manager.get_file_status(temp_file)
        assert not status.get("lock_mode")

    @pytest.mark.asyncio
    async def test_context_manager_exception_handling(self, lock_manager, temp_file):
        """Test that lock is released even on exception."""
        try:
            async with FileLockContext(temp_file, "agent1", LockMode.EXCLUSIVE):
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Lock should still be released
        status = lock_manager.get_file_status(temp_file)
        assert status["locked"] is False
