"""Project context detection for devloop.

This module provides functionality to detect whether devloop is running
in its own source repository vs a user's project, enabling context-aware
test discovery and agent behavior.
"""

from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class ProjectContext:
    """Detects and manages project context.

    Determines if devloop is running in:
    - The devloop source repository (development mode)
    - A user's project where devloop is installed

    This enables context-aware behavior like test discovery.
    """

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize project context.

        Args:
            project_root: Root directory of the project. Defaults to current directory.
        """
        self.project_root = project_root or Path.cwd()
        self._cache: dict = {}

    def is_devloop_repository(self) -> bool:
        """Detect if we're IN the devloop source repository.

        Uses multiple detection methods:
        1. Check pyproject.toml for name="devloop"
        2. Check git remote URL contains "devloop"
        3. Check for .devloop-repository-marker file

        Returns:
            True if this is the devloop source repository
        """
        # Check cache
        if "is_devloop_repo" in self._cache:
            return self._cache["is_devloop_repo"]

        result = False

        # Check 1: pyproject.toml with name="devloop"
        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            try:
                # Use tomllib for Python 3.11+, fall back to tomli
                try:
                    import tomllib
                except ImportError:
                    import tomli as tomllib  # type: ignore

                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)
                    poetry_name = data.get("tool", {}).get("poetry", {}).get("name")
                    if poetry_name == "devloop":
                        logger.debug("Detected devloop repository via pyproject.toml")
                        result = True
            except Exception as e:
                logger.debug(f"Failed to read pyproject.toml: {e}")

        # Check 2: Git remote URL contains "devloop"
        if not result:
            git_config = self.project_root / ".git" / "config"
            if git_config.exists():
                try:
                    content = git_config.read_text()
                    if (
                        "github.com/wioota/devloop" in content
                        or "devloop.git" in content
                    ):
                        logger.debug("Detected devloop repository via git remote")
                        result = True
                except Exception as e:
                    logger.debug(f"Failed to read git config: {e}")

        # Check 3: Specific marker file
        if not result:
            marker = self.project_root / ".devloop-repository-marker"
            if marker.exists():
                logger.debug("Detected devloop repository via marker file")
                result = True

        # Cache result
        self._cache["is_devloop_repo"] = result
        return result

    def get_test_root(self) -> Path:
        """Get the root directory for tests in this project.

        Returns:
            Path to the test root directory
        """
        if self.is_devloop_repository():
            # In devloop: use tests/ directory
            test_root = self.project_root / "tests"
            logger.debug(f"Using devloop test root: {test_root}")
            return test_root
        else:
            # User project: common patterns
            for candidate in ["tests", "test", "spec", "__tests__"]:
                path = self.project_root / candidate
                if path.exists() and path.is_dir():
                    logger.debug(f"Using user project test root: {path}")
                    return path
            # Default: project root
            logger.debug(f"Using project root as test root: {self.project_root}")
            return self.project_root

    def get_exclude_patterns(self) -> List[str]:
        """Get patterns to exclude from test discovery.

        Returns:
            List of glob patterns to exclude
        """
        if self.is_devloop_repository():
            # In devloop: no exclusions (we want ALL tests)
            return []
        else:
            # User project: exclude devloop's tests from site-packages
            return [
                "**/site-packages/devloop/tests/**",
                "**/.venv/**/devloop/tests/**",
                "**/venv/**/devloop/tests/**",
                "**/.tox/**/devloop/tests/**",
                "**/env/**/devloop/tests/**",
            ]

    def get_project_type(self) -> str:
        """Detect project type based on files.

        Returns:
            Project type string: "python", "javascript", "rust", "go", or "unknown"
        """
        # Check cache
        if "project_type" in self._cache:
            return self._cache["project_type"]

        result = "unknown"

        if (self.project_root / "pyproject.toml").exists() or (
            self.project_root / "setup.py"
        ).exists():
            result = "python"
        elif (self.project_root / "package.json").exists():
            result = "javascript"
        elif (self.project_root / "Cargo.toml").exists():
            result = "rust"
        elif (self.project_root / "go.mod").exists():
            result = "go"

        # Cache result
        self._cache["project_type"] = result
        logger.debug(f"Detected project type: {result}")
        return result

    def clear_cache(self) -> None:
        """Clear the internal cache.

        Useful for testing or when project state changes.
        """
        self._cache.clear()
