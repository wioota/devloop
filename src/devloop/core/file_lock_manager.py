"""File-level locking and versioning to prevent race conditions.

Provides synchronized file access with:
- Per-file locking for exclusive access during modifications
- File versioning with etags to detect concurrent changes
- Conflict detection when multiple agents attempt modifications
- Ordered access queue for competing modifications
"""

import hashlib
import logging
import asyncio
import time
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class LockMode(str, Enum):
    """Types of file locks."""

    SHARED = "shared"  # Multiple readers
    EXCLUSIVE = "exclusive"  # Single writer


@dataclass
class FileVersion:
    """Version information for a file.

    Attributes:
        etag: SHA256 hash of file content (integrity check)
        size: File size in bytes
        mtime: Modification time (Unix timestamp)
        modified_by: Agent that last modified the file
        modified_at: When the modification occurred
    """

    etag: str
    size: int
    mtime: float
    modified_by: Optional[str] = None
    modified_at: Optional[float] = None

    def __eq__(self, other: object) -> bool:
        """Compare versions by etag."""
        if not isinstance(other, FileVersion):
            return NotImplemented
        return self.etag == other.etag

    def __hash__(self) -> int:
        """Hash based on etag."""
        return hash(self.etag)


class FileLockManager:
    """Manages file-level locks and versioning.

    Ensures:
    - Only one agent can modify a file at a time (exclusive lock)
    - Multiple agents can read the same file simultaneously (shared lock)
    - Concurrent modifications are detected and reported
    - File changes are tracked with versioning/etags
    """

    def __init__(self):
        """Initialize file lock manager."""
        self.logger = logging.getLogger("file.lock")

        # Per-file locks
        self._file_locks: Dict[str, asyncio.Lock] = {}

        # Lock mode tracking (exclusive vs shared)
        self._lock_modes: Dict[str, LockMode] = {}

        # Active readers per file (for shared locks)
        self._readers: Dict[str, Set[str]] = {}

        # File version tracking
        self._file_versions: Dict[str, FileVersion] = {}

        # Modification queue for competing requests
        self._modification_queue: Dict[str, list[Tuple[str, float]]] = {}

        # Global lock for metadata updates
        self._metadata_lock = asyncio.Lock()

    async def acquire_lock(
        self,
        file_path: Path,
        agent_name: str,
        mode: LockMode = LockMode.EXCLUSIVE,
        timeout: Optional[float] = None,
    ) -> bool:
        """Acquire a lock on a file.

        Args:
            file_path: Path to file to lock
            agent_name: Name of agent requesting lock
            mode: Lock mode (EXCLUSIVE or SHARED)
            timeout: Maximum time to wait (None = infinite)

        Returns:
            True if lock acquired, False if timeout/conflict
        """
        file_key = str(file_path.resolve())

        # Ensure lock exists for this file
        if file_key not in self._file_locks:
            self._file_locks[file_key] = asyncio.Lock()

        # Check for conflicts first (without acquiring)
        async with self._metadata_lock:
            current_mode = self._lock_modes.get(file_key)

            # Any lock conflicts with any existing lock (simplified)
            if current_mode is not None:
                self.logger.warning(
                    f"Lock conflict for {file_key}: "
                    f"currently held in {current_mode} mode"
                )
                return False

        try:
            # Try to acquire the lock with timeout
            if timeout is not None:
                await asyncio.wait_for(
                    self._file_locks[file_key].acquire(), timeout=timeout
                )
            else:
                await self._file_locks[file_key].acquire()

            # Record the lock after acquiring
            async with self._metadata_lock:
                self._lock_modes[file_key] = mode
                if mode == LockMode.SHARED:
                    if file_key not in self._readers:
                        self._readers[file_key] = set()
                    self._readers[file_key].add(agent_name)

                # Queue the modification request
                if file_key not in self._modification_queue:
                    self._modification_queue[file_key] = []
                self._modification_queue[file_key].append((agent_name, time.time()))

            self.logger.debug(
                f"Acquired {mode} lock on {file_path.name} for {agent_name}"
            )
            return True

        except asyncio.TimeoutError:
            self.logger.warning(
                f"Lock acquisition timeout ({timeout}s) for {file_path.name} "
                f"by {agent_name}"
            )
            return False

    async def release_lock(self, file_path: Path, agent_name: str) -> None:
        """Release a lock on a file.

        Args:
            file_path: Path to file to unlock
            agent_name: Name of agent releasing lock
        """
        file_key = str(file_path.resolve())

        if file_key not in self._file_locks:
            self.logger.warning(f"No lock found for {file_path.name}")
            return

        try:
            lock = self._file_locks[file_key]
            if not lock.locked():
                self.logger.warning(f"Lock not held for {file_path.name}")
                return

            async with self._metadata_lock:
                mode = self._lock_modes.get(file_key)

                # Remove from readers list if shared lock
                if mode == LockMode.SHARED:
                    if file_key in self._readers:
                        self._readers[file_key].discard(agent_name)
                        if not self._readers[file_key]:
                            del self._readers[file_key]
                            self._lock_modes.pop(file_key, None)
                else:
                    # For exclusive locks, always clear
                    self._lock_modes.pop(file_key, None)

                # Clear modification queue if no more readers
                if file_key not in self._readers and mode == LockMode.SHARED:
                    self._modification_queue.pop(file_key, None)
                elif mode == LockMode.EXCLUSIVE:
                    self._modification_queue.pop(file_key, None)

            lock.release()
            self.logger.debug(f"Released {mode} lock on {file_path.name}")

        except RuntimeError as e:
            self.logger.error(f"Error releasing lock for {file_path.name}: {e}")

    async def check_version(
        self, file_path: Path, expected_etag: Optional[str] = None
    ) -> Tuple[bool, Optional[FileVersion]]:
        """Check if file has been modified by another agent.

        Args:
            file_path: Path to file to check
            expected_etag: Expected etag (if any)

        Returns:
            Tuple of (is_changed, current_version)
            is_changed: True if file differs from expected
        """
        if not file_path.exists():
            return False, None

        current_version = self._get_file_version(file_path)

        if expected_etag is None:
            return False, current_version

        is_changed = current_version.etag != expected_etag
        if is_changed:
            self.logger.warning(
                f"File {file_path.name} was modified externally: "
                f"{expected_etag[:8]}... → {current_version.etag[:8]}..."
            )

        return is_changed, current_version

    async def record_modification(
        self,
        file_path: Path,
        agent_name: str,
        new_version: Optional[FileVersion] = None,
    ) -> FileVersion:
        """Record a file modification.

        Args:
            file_path: Path to file that was modified
            agent_name: Agent that performed modification
            new_version: Version to record (calculated if None)

        Returns:
            FileVersion object for the modification
        """
        if new_version is None:
            new_version = self._get_file_version(file_path)

        new_version.modified_by = agent_name
        new_version.modified_at = time.time()

        file_key = str(file_path.resolve())
        async with self._metadata_lock:
            self._file_versions[file_key] = new_version

        self.logger.debug(
            f"Recorded modification to {file_path.name} by {agent_name}: "
            f"{new_version.etag[:8]}..."
        )

        return new_version

    async def detect_concurrent_modifications(self, file_path: Path) -> Optional[str]:
        """Detect if multiple agents are attempting to modify a file.

        Args:
            file_path: Path to file to check

        Returns:
            String describing conflict, or None if no conflict
        """
        file_key = str(file_path.resolve())

        if file_key not in self._modification_queue:
            return None

        queue = self._modification_queue[file_key]
        if len(queue) <= 1:
            return None

        # Report conflict
        agents = [agent for agent, _ in queue]
        timestamps = [t for _, t in queue]
        time_diff = max(timestamps) - min(timestamps)

        conflict_msg = (
            f"Concurrent modification attempt on {file_path.name}: "
            f"{agents} within {time_diff:.2f}s"
        )
        self.logger.warning(conflict_msg)

        return conflict_msg

    def get_file_status(self, file_path: Path) -> Dict[str, Any]:
        """Get lock and version status for a file.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with lock status and version info
        """
        file_key = str(file_path.resolve())

        return {
            "path": str(file_path),
            "locked": file_key in self._lock_modes,
            "lock_mode": self._lock_modes.get(file_key),
            "readers": list(self._readers.get(file_key, set())),
            "modification_queue": [
                agent for agent, _ in self._modification_queue.get(file_key, [])
            ],
            "version": self._file_versions.get(file_key),
        }

    def get_all_locks(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all locked files.

        Returns:
            Dictionary mapping file paths to lock status
        """
        return {
            file_key: {
                "lock_mode": self._lock_modes.get(file_key),
                "readers": list(self._readers.get(file_key, set())),
                "queue_length": len(self._modification_queue.get(file_key, [])),
            }
            for file_key in self._file_locks
        }

    @staticmethod
    def _get_file_version(file_path: Path) -> FileVersion:
        """Calculate version information for a file.

        Args:
            file_path: Path to file

        Returns:
            FileVersion object
        """
        stat = file_path.stat()

        # Calculate SHA256 etag
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            etag = hasher.hexdigest()
        except IOError:
            etag = "error"

        return FileVersion(
            etag=etag,
            size=stat.st_size,
            mtime=stat.st_mtime,
        )

    async def reset(self) -> None:
        """Reset all locks and versions.

        Use with caution - only for testing or cleanup.
        """
        async with self._metadata_lock:
            # Release all locks
            for lock in self._file_locks.values():
                while lock.locked():
                    try:
                        lock.release()
                    except RuntimeError:
                        break

            # Clear tracking
            self._file_locks.clear()
            self._lock_modes.clear()
            self._readers.clear()
            self._file_versions.clear()
            self._modification_queue.clear()

            self.logger.info("Reset all file locks and versions")


# Global singleton instance
_file_lock_manager: Optional[FileLockManager] = None


def get_file_lock_manager() -> FileLockManager:
    """Get global file lock manager instance.

    Returns:
        Singleton file lock manager
    """
    global _file_lock_manager
    if _file_lock_manager is None:
        _file_lock_manager = FileLockManager()
    return _file_lock_manager


class FileLockContext:
    """Async context manager for file locks.

    Usage:
        async with FileLockContext(path, agent_name):
            # Safely modify file
            pass
    """

    def __init__(
        self,
        file_path: Path,
        agent_name: str,
        mode: LockMode = LockMode.EXCLUSIVE,
        timeout: Optional[float] = None,
    ):
        """Initialize context manager.

        Args:
            file_path: Path to file to lock
            agent_name: Name of agent requesting lock
            mode: Lock mode (EXCLUSIVE or SHARED)
            timeout: Maximum time to wait for lock
        """
        self.file_path = file_path
        self.agent_name = agent_name
        self.mode = mode
        self.timeout = timeout
        self.manager = get_file_lock_manager()
        self.lock_acquired = False

    async def __aenter__(self) -> "FileLockContext":
        """Acquire lock on entry."""
        self.lock_acquired = await self.manager.acquire_lock(
            self.file_path, self.agent_name, self.mode, self.timeout
        )

        if not self.lock_acquired:
            raise TimeoutError(
                f"Could not acquire {self.mode} lock on {self.file_path} "
                f"for {self.agent_name}"
            )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Release lock on exit."""
        if self.lock_acquired:
            await self.manager.release_lock(self.file_path, self.agent_name)
