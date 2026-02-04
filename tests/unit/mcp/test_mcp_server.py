"""Tests for DevLoop MCP Server."""

from pathlib import Path
from unittest.mock import patch

import pytest

from devloop.mcp.server import DevLoopMCPServer


class TestDevLoopMCPServerInit:
    """Tests for DevLoopMCPServer initialization."""

    def test_init_with_explicit_project_root(self, tmp_path: Path) -> None:
        """Server initializes with explicit project root."""
        # Create a devloop marker
        (tmp_path / ".devloop").mkdir()

        server = DevLoopMCPServer(project_root=tmp_path)

        assert server.project_root == tmp_path

    def test_init_finds_project_root_from_cwd(self, tmp_path: Path) -> None:
        """Server finds project root when not explicitly provided."""
        # Create project structure
        (tmp_path / ".beads").mkdir()
        subdir = tmp_path / "src" / "module"
        subdir.mkdir(parents=True)

        with patch.object(Path, "cwd", return_value=subdir):
            server = DevLoopMCPServer()

        assert server.project_root == tmp_path

    def test_init_fails_without_devloop_markers(self, tmp_path: Path) -> None:
        """Server raises ValueError when no DevLoop project found."""
        # Empty directory with no markers
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with patch.object(Path, "cwd", return_value=empty_dir):
            with pytest.raises(ValueError, match="Could not find DevLoop project root"):
                DevLoopMCPServer()


class TestFindProjectRoot:
    """Tests for _find_project_root helper."""

    def test_finds_devloop_directory(self, tmp_path: Path) -> None:
        """Finds project root with .devloop directory."""
        (tmp_path / ".devloop").mkdir()
        subdir = tmp_path / "deep" / "nested"
        subdir.mkdir(parents=True)

        result = DevLoopMCPServer._find_project_root(subdir)

        assert result == tmp_path

    def test_finds_beads_directory(self, tmp_path: Path) -> None:
        """Finds project root with .beads directory."""
        (tmp_path / ".beads").mkdir()

        result = DevLoopMCPServer._find_project_root(tmp_path)

        assert result == tmp_path

    def test_finds_devloop_toml(self, tmp_path: Path) -> None:
        """Finds project root with devloop.toml file."""
        (tmp_path / "devloop.toml").touch()
        subdir = tmp_path / "src"
        subdir.mkdir()

        result = DevLoopMCPServer._find_project_root(subdir)

        assert result == tmp_path

    def test_returns_none_when_no_markers(self, tmp_path: Path) -> None:
        """Returns None when no DevLoop markers found."""
        empty = tmp_path / "empty"
        empty.mkdir()

        result = DevLoopMCPServer._find_project_root(empty)

        assert result is None

    def test_uses_cwd_when_no_start_path(self, tmp_path: Path) -> None:
        """Uses current working directory when start_path not provided."""
        (tmp_path / ".devloop").mkdir()

        with patch.object(Path, "cwd", return_value=tmp_path):
            result = DevLoopMCPServer._find_project_root()

        assert result == tmp_path
