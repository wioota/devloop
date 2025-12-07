"""Backup and rollback management for auto-fix operations."""

import hashlib
import json
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages backups and rollbacks for auto-fix operations.

    Features:
    - Pre-modification backups with metadata
    - Git-aware rollback using temporary branches
    - Atomic operations with checksums
    - Change history tracking
    - Selective and batch rollback
    """

    def __init__(self, project_root: Path, backup_dir: Optional[Path] = None):
        """Initialize backup manager.

        Args:
            project_root: Root directory of the project
            backup_dir: Optional custom backup directory (default: .devloop/backups)
        """
        self.project_root = Path(project_root).resolve()
        self.backup_dir = backup_dir or (self.project_root / ".devloop" / "backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Change log for tracking all modifications
        self.change_log_file = self.backup_dir / "change_log.json"
        self._ensure_change_log()

        # Git integration
        self._git_available = self._check_git_available()

    def _ensure_change_log(self):
        """Ensure change log file exists."""
        if not self.change_log_file.exists():
            self.change_log_file.write_text(json.dumps({"changes": []}, indent=2))

    def _check_git_available(self) -> bool:
        """Check if git is available and this is a git repository."""
        try:
            result: subprocess.CompletedProcess[str] = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Git not available: {e}")
            return False

    def _compute_checksum(self, file_path: Path) -> str:
        """Compute SHA256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def create_backup(
        self,
        file_path: Path,
        fix_type: str,
        description: str,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """Create a backup before modifying a file.

        Args:
            file_path: Path to file being modified
            fix_type: Type of fix (e.g., "formatter", "linter")
            description: Human-readable description of the fix
            metadata: Additional metadata about the fix

        Returns:
            Backup ID if successful, None otherwise
        """
        try:
            file_path = Path(file_path).resolve()

            # Ensure file exists
            if not file_path.exists():
                logger.error(f"Cannot backup non-existent file: {file_path}")
                return None

            # Generate backup ID
            timestamp = datetime.now().isoformat()
            backup_id = self._generate_backup_id(file_path, timestamp)

            # Create backup directory structure
            backup_entry_dir = self.backup_dir / backup_id
            backup_entry_dir.mkdir(parents=True, exist_ok=True)

            # Copy original file
            backup_file = backup_entry_dir / "original"
            shutil.copy2(file_path, backup_file)

            # Compute checksum
            checksum = self._compute_checksum(file_path)

            # Store metadata
            backup_metadata = {
                "backup_id": backup_id,
                "timestamp": timestamp,
                "file_path": str(file_path.relative_to(self.project_root)),
                "absolute_path": str(file_path),
                "fix_type": fix_type,
                "description": description,
                "checksum": checksum,
                "git_commit": self._get_current_git_commit() if self._git_available else None,
                "metadata": metadata or {}
            }

            metadata_file = backup_entry_dir / "metadata.json"
            metadata_file.write_text(json.dumps(backup_metadata, indent=2))

            # Add to change log
            self._add_to_change_log(backup_metadata)

            logger.info(f"Created backup {backup_id} for {file_path}")
            return backup_id

        except Exception as e:
            logger.error(f"Failed to create backup for {file_path}: {e}")
            return None

    def _generate_backup_id(self, file_path: Path, timestamp: str) -> str:
        """Generate unique backup ID."""
        # Use timestamp (including microseconds) + file path hash for uniqueness
        # MD5 used only for non-cryptographic ID generation, not security
        path_hash = hashlib.md5(str(file_path).encode(), usedforsecurity=False).hexdigest()[:8]
        dt = datetime.fromisoformat(timestamp)
        time_str = dt.strftime("%Y%m%d_%H%M%S_%f")  # Include microseconds
        return f"{time_str}_{path_hash}"

    def _get_current_git_commit(self) -> Optional[str]:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.debug(f"Failed to get git commit: {e}")
        return None

    def _add_to_change_log(self, backup_metadata: Dict):
        """Add backup entry to change log."""
        try:
            log_data = json.loads(self.change_log_file.read_text())
            log_data["changes"].append(backup_metadata)

            # Write atomically (write to temp, then rename)
            temp_file = self.change_log_file.with_suffix(".tmp")
            temp_file.write_text(json.dumps(log_data, indent=2))
            temp_file.replace(self.change_log_file)

        except Exception as e:
            logger.error(f"Failed to update change log: {e}")

    def rollback(
        self,
        backup_id: str,
        verify_checksum: bool = True
    ) -> bool:
        """Rollback a specific backup.

        Args:
            backup_id: ID of backup to restore
            verify_checksum: Whether to verify file hasn't changed since backup

        Returns:
            True if rollback successful
        """
        try:
            backup_entry_dir = self.backup_dir / backup_id

            if not backup_entry_dir.exists():
                logger.error(f"Backup {backup_id} not found")
                return False

            # Load metadata
            metadata_file = backup_entry_dir / "metadata.json"
            metadata = json.loads(metadata_file.read_text())

            file_path = Path(metadata["absolute_path"])
            backup_file = backup_entry_dir / "original"

            # Verify file hasn't been modified by something else
            if verify_checksum and file_path.exists():
                current_checksum = self._compute_checksum(file_path)
                # Note: We don't check against original checksum because the file
                # has been modified by the fix. Instead, we could store the
                # post-fix checksum, but for now we skip this check.
                # This is a TODO for enhanced safety.

            # Restore backup
            if backup_file.exists():
                shutil.copy2(backup_file, file_path)
                logger.info(f"Restored {file_path} from backup {backup_id}")

                # Mark as rolled back in change log
                self._mark_rolled_back(backup_id)
                return True
            else:
                logger.error(f"Backup file missing for {backup_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to rollback {backup_id}: {e}")
            return False

    def _mark_rolled_back(self, backup_id: str):
        """Mark a backup as rolled back in the change log."""
        try:
            log_data = json.loads(self.change_log_file.read_text())

            for change in log_data["changes"]:
                if change["backup_id"] == backup_id:
                    change["rolled_back"] = True
                    change["rollback_time"] = datetime.now().isoformat()
                    break

            temp_file = self.change_log_file.with_suffix(".tmp")
            temp_file.write_text(json.dumps(log_data, indent=2))
            temp_file.replace(self.change_log_file)

        except Exception as e:
            logger.error(f"Failed to mark rollback in log: {e}")

    def rollback_all(self, since: Optional[datetime] = None) -> List[str]:
        """Rollback all changes, optionally since a specific time.

        Args:
            since: Only rollback changes after this time

        Returns:
            List of successfully rolled back backup IDs
        """
        try:
            log_data = json.loads(self.change_log_file.read_text())
            changes = log_data["changes"]

            # Filter by time if specified
            if since:
                changes = [
                    c for c in changes
                    if datetime.fromisoformat(c["timestamp"]) >= since
                ]

            # Filter out already rolled back
            changes = [c for c in changes if not c.get("rolled_back", False)]

            rolled_back = []
            for change in reversed(changes):  # Rollback in reverse order
                if self.rollback(change["backup_id"], verify_checksum=False):
                    rolled_back.append(change["backup_id"])

            return rolled_back

        except Exception as e:
            logger.error(f"Failed to rollback all: {e}")
            return []

    def get_change_history(
        self,
        limit: Optional[int] = None,
        include_rolled_back: bool = False
    ) -> List[Dict]:
        """Get change history.

        Args:
            limit: Maximum number of changes to return
            include_rolled_back: Whether to include rolled back changes

        Returns:
            List of change metadata dictionaries
        """
        try:
            log_data = json.loads(self.change_log_file.read_text())
            changes = log_data["changes"]

            if not include_rolled_back:
                changes = [c for c in changes if not c.get("rolled_back", False)]

            if limit:
                changes = changes[-limit:]

            return changes

        except Exception as e:
            logger.error(f"Failed to get change history: {e}")
            return []

    def create_git_rollback_branch(self, branch_name: str = "devloop-fixes") -> bool:
        """Create a git branch for fixes (git-aware rollback).

        This allows easy rollback via git branch operations.

        Args:
            branch_name: Name of the branch to create

        Returns:
            True if branch created successfully
        """
        if not self._git_available:
            logger.warning("Git not available, cannot create rollback branch")
            return False

        try:
            # Check if branch already exists
            check_result = subprocess.run(
                ["git", "rev-parse", "--verify", branch_name],
                cwd=self.project_root,
                capture_output=True,
                timeout=5
            )

            if check_result.returncode == 0:
                logger.info(f"Branch {branch_name} already exists")
                return True

            # Create new branch from current HEAD
            create_result: subprocess.CompletedProcess[str] = subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5
            )

            if create_result.returncode == 0:
                logger.info(f"Created rollback branch: {branch_name}")
                return True
            else:
                logger.error(f"Failed to create branch: {create_result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to create git rollback branch: {e}")
            return False

    def cleanup_old_backups(self, days: int = 30) -> int:
        """Clean up backups older than specified days.

        Args:
            days: Remove backups older than this many days

        Returns:
            Number of backups removed
        """
        try:
            cutoff = datetime.now().timestamp() - (days * 86400)
            removed = 0

            for backup_dir in self.backup_dir.iterdir():
                if not backup_dir.is_dir():
                    continue

                metadata_file = backup_dir / "metadata.json"
                if metadata_file.exists():
                    metadata = json.loads(metadata_file.read_text())
                    timestamp = datetime.fromisoformat(metadata["timestamp"]).timestamp()

                    if timestamp < cutoff:
                        shutil.rmtree(backup_dir)
                        removed += 1
                        logger.debug(f"Removed old backup: {backup_dir.name}")

            if removed > 0:
                logger.info(f"Cleaned up {removed} old backups")

            return removed

        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return 0


# Global instance (will be initialized by AutoFix)
_backup_manager: Optional[BackupManager] = None


def get_backup_manager(project_root: Optional[Path] = None) -> BackupManager:
    """Get or create global backup manager instance."""
    global _backup_manager

    if _backup_manager is None:
        if project_root is None:
            project_root = Path.cwd()
        _backup_manager = BackupManager(project_root)

    return _backup_manager
