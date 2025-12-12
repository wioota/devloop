"""Path validation and sanitization for security.

Prevents path traversal attacks, symlink exploits, and ensures all paths
are within allowed boundaries.
"""

import fnmatch
import logging
from pathlib import Path
from typing import List, Optional, Union

logger = logging.getLogger(__name__)


class PathValidationError(Exception):
    """Raised when path validation fails."""

    pass


class PathTraversalError(PathValidationError):
    """Raised when path traversal attack is detected."""

    pass


class SymlinkError(PathValidationError):
    """Raised when dangerous symlink is detected."""

    pass


class PathValidator:
    """Validates and sanitizes file paths for security.

    Features:
    - Resolves symlinks to prevent symlink attacks
    - Validates paths are within project directory
    - Prevents path traversal attacks (../, etc.)
    - Pattern matching with fnmatch/glob
    - Configurable allowed/blocked patterns

    Example:
        >>> validator = PathValidator(project_root="/home/user/project")
        >>> safe_path = validator.validate("/home/user/project/file.py")
        >>> validator.is_within_project(safe_path)  # True
    """

    def __init__(
        self,
        project_root: Union[Path, str],
        allow_symlinks: bool = False,
        blocked_patterns: Optional[List[str]] = None,
    ):
        """Initialize path validator.

        Args:
            project_root: Root directory of the project (all paths must be within this)
            allow_symlinks: Whether to allow symlinks (default: False for security)
            blocked_patterns: List of fnmatch patterns to block (e.g., ["*.exe", "*.sh"])
        """
        self.project_root = Path(project_root).resolve()

        if not self.project_root.exists():
            raise PathValidationError(
                f"Project root does not exist: {self.project_root}"
            )

        if not self.project_root.is_dir():
            raise PathValidationError(
                f"Project root is not a directory: {self.project_root}"
            )

        self.allow_symlinks = allow_symlinks
        self.blocked_patterns = blocked_patterns or []

        logger.debug(f"PathValidator initialized for {self.project_root}")

    def resolve_path(self, path: Union[Path, str]) -> Path:
        """Resolve path to eliminate symlinks and relative components.

        Args:
            path: Path to resolve

        Returns:
            Resolved absolute path

        Raises:
            SymlinkError: If symlinks are not allowed and path contains symlinks
            PathValidationError: If path cannot be resolved
        """
        try:
            path_obj = Path(path)

            # Check for symlinks before resolving if not allowed
            if not self.allow_symlinks and path_obj.is_symlink():
                raise SymlinkError(f"Symlinks not allowed: {path} is a symbolic link")

            # Resolve to absolute path (follows symlinks, resolves .., etc.)
            resolved = path_obj.resolve()

            # Double-check no symlink components in the resolved path
            if not self.allow_symlinks:
                # Check each parent for symlinks
                for parent in resolved.parents:
                    if parent.is_symlink():
                        raise SymlinkError(f"Path contains symlink component: {parent}")

            return resolved

        except (OSError, RuntimeError) as e:
            raise PathValidationError(f"Failed to resolve path {path}: {e}") from e

    def is_within_project(self, path: Union[Path, str]) -> bool:
        """Check if path is within project directory.

        Args:
            path: Path to check

        Returns:
            True if path is within project, False otherwise
        """
        try:
            resolved = self.resolve_path(path)

            # Check if resolved path is relative to project root
            try:
                resolved.relative_to(self.project_root)
                return True
            except ValueError:
                return False

        except PathValidationError:
            return False

    def validate(self, path: Union[Path, str]) -> Path:
        """Validate and sanitize a path.

        Performs:
        - Symlink resolution
        - Path traversal attack prevention
        - Project boundary validation
        - Pattern-based blocking

        Args:
            path: Path to validate

        Returns:
            Validated and resolved path

        Raises:
            PathTraversalError: If path attempts to escape project directory
            SymlinkError: If symlinks not allowed and path contains symlinks
            PathValidationError: If path is blocked by pattern or other validation fails
        """
        # Resolve path (handles symlinks, .., ., etc.)
        resolved = self.resolve_path(path)

        # Check if within project directory
        if not self.is_within_project(resolved):
            raise PathTraversalError(
                f"Path outside project directory: {path} "
                f"(resolved to {resolved}, project root: {self.project_root})"
            )

        # Check against blocked patterns
        for pattern in self.blocked_patterns:
            if fnmatch.fnmatch(resolved.name, pattern):
                raise PathValidationError(
                    f"Path matches blocked pattern '{pattern}': {resolved.name}"
                )

        logger.debug(f"Validated path: {path} -> {resolved}")
        return resolved

    def validate_multiple(self, paths: List[Union[Path, str]]) -> List[Path]:
        """Validate multiple paths.

        Args:
            paths: List of paths to validate

        Returns:
            List of validated paths

        Raises:
            PathValidationError: If any path fails validation
        """
        validated = []

        for path in paths:
            try:
                validated.append(self.validate(path))
            except PathValidationError as e:
                logger.error(f"Path validation failed for {path}: {e}")
                raise

        return validated

    def match_pattern(self, path: Union[Path, str], pattern: str) -> bool:
        """Match path against a glob/fnmatch pattern.

        Args:
            path: Path to match
            pattern: Glob pattern (e.g., "**/*.py", "*.txt")

        Returns:
            True if path matches pattern, False otherwise
        """
        try:
            resolved = self.resolve_path(path)

            # Try glob-style matching (supports **/*)
            if "**" in pattern:
                # Convert to relative path for glob matching
                try:
                    relative = resolved.relative_to(self.project_root)
                    return relative.match(pattern)
                except ValueError:
                    return False
            else:
                # Simple fnmatch for filename
                return fnmatch.fnmatch(resolved.name, pattern)

        except PathValidationError:
            return False

    def filter_paths(
        self,
        paths: List[Union[Path, str]],
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> List[Path]:
        """Filter paths by include/exclude patterns.

        Args:
            paths: List of paths to filter
            include_patterns: Patterns to include (if None, include all)
            exclude_patterns: Patterns to exclude

        Returns:
            Filtered list of validated paths
        """
        filtered = []

        for path in paths:
            try:
                resolved = self.validate(path)

                # Check exclude patterns
                if exclude_patterns:
                    excluded = any(
                        self.match_pattern(resolved, pattern)
                        for pattern in exclude_patterns
                    )
                    if excluded:
                        continue

                # Check include patterns
                if include_patterns:
                    included = any(
                        self.match_pattern(resolved, pattern)
                        for pattern in include_patterns
                    )
                    if not included:
                        continue

                filtered.append(resolved)

            except PathValidationError as e:
                logger.warning(f"Skipping invalid path {path}: {e}")
                continue

        return filtered


def safe_path_join(base: Union[Path, str], *parts: str) -> Path:
    """Safely join path components, preventing traversal.

    Args:
        base: Base directory
        *parts: Path components to join

    Returns:
        Joined path

    Raises:
        PathTraversalError: If result would escape base directory
    """
    base_path = Path(base).resolve()
    joined = base_path.joinpath(*parts).resolve()

    # Ensure result is still within base
    try:
        joined.relative_to(base_path)
    except ValueError as e:
        raise PathTraversalError(
            f"Path traversal detected: {parts} would escape {base}"
        ) from e

    return joined


def is_safe_path(path: Union[Path, str], allowed_root: Union[Path, str]) -> bool:
    """Check if path is safe (within allowed root, no traversal).

    Args:
        path: Path to check
        allowed_root: Root directory that path must be within

    Returns:
        True if path is safe, False otherwise
    """
    try:
        path_resolved = Path(path).resolve()
        root_resolved = Path(allowed_root).resolve()

        # Check if path is relative to allowed root
        path_resolved.relative_to(root_resolved)
        return True

    except (ValueError, OSError):
        return False


def validate_safe_patterns(patterns: List[str]) -> List[str]:
    """Validate that glob patterns don't contain dangerous constructs.

    Args:
        patterns: List of glob patterns

    Returns:
        Validated patterns

    Raises:
        PathValidationError: If pattern contains dangerous constructs
    """
    validated = []

    for pattern in patterns:
        # Check for suspicious patterns
        if ".." in pattern:
            raise PathValidationError(
                f"Pattern contains parent directory reference: {pattern}"
            )

        if pattern.startswith("/"):
            raise PathValidationError(f"Pattern must not be absolute path: {pattern}")

        # Pattern is safe
        validated.append(pattern)

    return validated
