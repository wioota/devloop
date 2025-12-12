"""Transactional I/O operations with checksums and recovery.

Provides atomic file operations with data integrity verification:
- Atomic writes (write to temp, atomic rename)
- Checksum generation and verification (SHA-256)
- Crash recovery (cleanup orphaned temp files)
- Self-healing (checksum verification on startup)
"""

import hashlib
import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TransactionError(Exception):
    """Raised when a transaction operation fails."""

    pass


class ChecksumMismatchError(TransactionError):
    """Raised when checksum verification fails."""

    pass


def compute_checksum(data: bytes) -> str:
    """Compute SHA-256 checksum of data.

    Args:
        data: Raw bytes to checksum

    Returns:
        Hex-encoded SHA-256 checksum
    """
    return hashlib.sha256(data).hexdigest()


def compute_file_checksum(file_path: Path) -> str:
    """Compute SHA-256 checksum of a file.

    Args:
        file_path: Path to file

    Returns:
        Hex-encoded SHA-256 checksum

    Raises:
        TransactionError: If file cannot be read
    """
    try:
        with open(file_path, "rb") as f:
            return compute_checksum(f.read())
    except Exception as e:
        raise TransactionError(
            f"Failed to compute checksum for {file_path}: {e}"
        ) from e


class TransactionalFile:
    """Manages transactional file operations with checksums.

    Example:
        >>> tf = TransactionalFile(Path("data.json"))
        >>> tf.write_json({"key": "value"})
        >>> data = tf.read_json()
        >>> tf.verify_checksum()  # Raises if corrupted
    """

    def __init__(self, file_path: Path | str, create_checksum: bool = True):
        """Initialize transactional file manager.

        Args:
            file_path: Path to the file
            create_checksum: Whether to create/verify checksums
        """
        self.file_path = Path(file_path)
        self.create_checksum = create_checksum
        self.checksum_path = self.file_path.with_suffix(
            self.file_path.suffix + ".sha256"
        )
        self.temp_suffix = ".tmp"

    def write_atomic(self, data: bytes) -> None:
        """Write data atomically with optional checksum.

        Args:
            data: Bytes to write

        Raises:
            TransactionError: If write fails
        """
        try:
            # Ensure parent directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to temp file
            temp_file = self.file_path.with_suffix(
                self.file_path.suffix + self.temp_suffix
            )
            temp_file.write_bytes(data)

            # Compute checksum before rename
            if self.create_checksum:
                checksum = compute_checksum(data)
                self.checksum_path.write_text(checksum)

            # Atomic rename
            temp_file.replace(self.file_path)

            logger.debug(f"Wrote {len(data)} bytes to {self.file_path}")

        except Exception as e:
            # Clean up temp file on failure
            temp_file = self.file_path.with_suffix(
                self.file_path.suffix + self.temp_suffix
            )
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

            raise TransactionError(f"Failed to write {self.file_path}: {e}") from e

    def write_text(self, content: str, encoding: str = "utf-8") -> None:
        """Write text atomically.

        Args:
            content: Text to write
            encoding: Text encoding

        Raises:
            TransactionError: If write fails
        """
        self.write_atomic(content.encode(encoding))

    def write_json(
        self, data: Any, indent: int = 2, ensure_ascii: bool = False
    ) -> None:
        """Write JSON data atomically.

        Args:
            data: JSON-serializable data
            indent: JSON indentation
            ensure_ascii: Whether to escape non-ASCII characters

        Raises:
            TransactionError: If write fails
        """
        try:
            json_str = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)
            self.write_text(json_str)
        except (TypeError, ValueError) as e:
            raise TransactionError(
                f"Failed to serialize JSON for {self.file_path}: {e}"
            ) from e

    def read_bytes(self) -> bytes:
        """Read file as bytes.

        Returns:
            File contents as bytes

        Raises:
            TransactionError: If read fails
        """
        try:
            return self.file_path.read_bytes()
        except Exception as e:
            raise TransactionError(f"Failed to read {self.file_path}: {e}") from e

    def read_text(self, encoding: str = "utf-8") -> str:
        """Read file as text.

        Args:
            encoding: Text encoding

        Returns:
            File contents as string

        Raises:
            TransactionError: If read fails
        """
        return self.read_bytes().decode(encoding)

    def read_json(self) -> Any:
        """Read file as JSON.

        Returns:
            Deserialized JSON data

        Raises:
            TransactionError: If read or parse fails
        """
        try:
            return json.loads(self.read_text())
        except (json.JSONDecodeError, ValueError) as e:
            raise TransactionError(
                f"Failed to parse JSON from {self.file_path}: {e}"
            ) from e

    def verify_checksum(self) -> bool:
        """Verify file checksum matches stored checksum.

        Returns:
            True if checksum matches or no checksum exists

        Raises:
            ChecksumMismatchError: If checksum doesn't match
        """
        if not self.create_checksum:
            return True

        if not self.file_path.exists():
            return True  # No file yet

        if not self.checksum_path.exists():
            logger.warning(
                f"No checksum file for {self.file_path}, skipping verification"
            )
            return True

        try:
            expected_checksum = self.checksum_path.read_text().strip()
            actual_checksum = compute_file_checksum(self.file_path)

            if expected_checksum != actual_checksum:
                raise ChecksumMismatchError(
                    f"Checksum mismatch for {self.file_path}: "
                    f"expected {expected_checksum}, got {actual_checksum}"
                )

            logger.debug(f"Checksum verified for {self.file_path}")
            return True

        except ChecksumMismatchError:
            raise
        except Exception as e:
            logger.error(f"Checksum verification failed for {self.file_path}: {e}")
            return False

    def exists(self) -> bool:
        """Check if file exists."""
        return self.file_path.exists()

    def delete(self) -> None:
        """Delete file and its checksum.

        Raises:
            TransactionError: If deletion fails
        """
        try:
            if self.file_path.exists():
                self.file_path.unlink()

            if self.checksum_path.exists():
                self.checksum_path.unlink()

            logger.debug(f"Deleted {self.file_path}")

        except Exception as e:
            raise TransactionError(f"Failed to delete {self.file_path}: {e}") from e


class TransactionRecovery:
    """Handles recovery from crashed transactions.

    Example:
        >>> recovery = TransactionRecovery(Path(".devloop"))
        >>> recovery.recover_all()  # Clean up orphaned temp files
    """

    def __init__(self, base_dir: Path | str):
        """Initialize transaction recovery.

        Args:
            base_dir: Base directory to scan for orphaned files
        """
        self.base_dir = Path(base_dir)

    def find_orphaned_temp_files(self) -> List[Path]:
        """Find orphaned temporary files (.tmp).

        Returns:
            List of paths to orphaned temp files
        """
        orphaned = []

        try:
            if not self.base_dir.exists():
                return []

            for temp_file in self.base_dir.rglob("*.tmp"):
                # Check if target file exists
                target_file = temp_file.with_suffix("")

                # If temp file exists but target doesn't, it's orphaned
                # This indicates a crashed write operation
                if not target_file.exists():
                    orphaned.append(temp_file)
                    logger.warning(f"Found orphaned temp file: {temp_file}")

        except Exception as e:
            logger.error(f"Error scanning for orphaned files: {e}")

        return orphaned

    def recover_all(self) -> int:
        """Recover from all crashed transactions.

        Returns:
            Number of orphaned files cleaned up
        """
        orphaned = self.find_orphaned_temp_files()

        if not orphaned:
            logger.debug("No orphaned temp files found")
            return 0

        cleaned = 0
        for temp_file in orphaned:
            try:
                temp_file.unlink()
                logger.info(f"Cleaned up orphaned temp file: {temp_file}")
                cleaned += 1
            except Exception as e:
                logger.error(f"Failed to clean up {temp_file}: {e}")

        return cleaned


class SelfHealing:
    """Self-healing mechanisms for data integrity.

    Example:
        >>> healer = SelfHealing(Path(".devloop"))
        >>> healer.verify_all_checksums()
        >>> healer.repair_corrupted_files()
    """

    def __init__(self, base_dir: Path | str):
        """Initialize self-healing system.

        Args:
            base_dir: Base directory containing files with checksums
        """
        self.base_dir = Path(base_dir)

    def find_files_with_checksums(self) -> List[Path]:
        """Find all files that have checksum files.

        Returns:
            List of paths to files with checksums
        """
        files_with_checksums = []

        try:
            if not self.base_dir.exists():
                return []

            for checksum_file in self.base_dir.rglob("*.sha256"):
                data_file = checksum_file.with_suffix("")

                if data_file.exists():
                    files_with_checksums.append(data_file)

        except Exception as e:
            logger.error(f"Error scanning for checksum files: {e}")

        return files_with_checksums

    def verify_all_checksums(self) -> Dict[str, bool]:
        """Verify checksums for all files.

        Returns:
            Dict mapping file path to verification result
        """
        results = {}

        for file_path in self.find_files_with_checksums():
            tf = TransactionalFile(file_path, create_checksum=True)
            try:
                tf.verify_checksum()
                results[str(file_path)] = True
                logger.debug(f"✓ Checksum verified: {file_path}")
            except ChecksumMismatchError as e:
                results[str(file_path)] = False
                logger.error(f"✗ Checksum mismatch: {e}")
            except Exception as e:
                results[str(file_path)] = False
                logger.error(f"✗ Verification failed for {file_path}: {e}")

        return results

    def repair_corrupted_files(self, backup_dir: Optional[Path] = None) -> int:
        """Attempt to repair corrupted files from backups.

        Args:
            backup_dir: Directory containing backup files

        Returns:
            Number of files repaired
        """
        if not backup_dir or not backup_dir.exists():
            logger.warning("No backup directory specified or it doesn't exist")
            return 0

        verification_results = self.verify_all_checksums()
        corrupted = [
            path for path, verified in verification_results.items() if not verified
        ]

        if not corrupted:
            logger.info("No corrupted files found")
            return 0

        repaired = 0
        for corrupted_file in corrupted:
            corrupted_path = Path(corrupted_file)
            backup_path = backup_dir / corrupted_path.name

            if not backup_path.exists():
                logger.error(f"No backup found for corrupted file: {corrupted_file}")
                continue

            try:
                # Copy backup to corrupted location
                shutil.copy2(backup_path, corrupted_path)

                # Verify the restored file
                tf = TransactionalFile(corrupted_path, create_checksum=True)
                tf.verify_checksum()

                logger.info(f"✓ Repaired corrupted file: {corrupted_file}")
                repaired += 1

            except Exception as e:
                logger.error(f"Failed to repair {corrupted_file}: {e}")

        return repaired


def initialize_transaction_system(base_dir: Path | str) -> None:
    """Initialize transaction system on startup.

    Performs:
    - Transaction recovery (cleanup orphaned files)
    - Checksum verification
    - Self-healing if needed

    Args:
        base_dir: Base directory for DevLoop files
    """
    base_path = Path(base_dir)

    logger.info("Initializing transaction system...")

    # Step 1: Recover from crashed transactions
    recovery = TransactionRecovery(base_path)
    orphaned_count = recovery.recover_all()

    if orphaned_count > 0:
        logger.info(f"Recovered {orphaned_count} orphaned temp files")

    # Step 2: Verify all checksums
    healer = SelfHealing(base_path)
    verification_results = healer.verify_all_checksums()

    total_files = len(verification_results)
    verified_files = sum(1 for v in verification_results.values() if v)
    corrupted_files = total_files - verified_files

    if corrupted_files > 0:
        logger.warning(
            f"Found {corrupted_files}/{total_files} corrupted files during startup"
        )
    else:
        logger.info(f"All {total_files} files verified successfully")

    logger.info("Transaction system initialized")
