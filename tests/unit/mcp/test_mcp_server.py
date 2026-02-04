"""Tests for DevLoop MCP server."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from devloop import __version__
from devloop.mcp.server import DEVLOOP_DIR, MCPServer


class TestMCPServer:
    """Tests for MCPServer class."""

    def test_server_init_with_project_root(self, tmp_path: Path) -> None:
        """Test server initialization with explicit project root."""
        # Create .devloop directory
        devloop_dir = tmp_path / DEVLOOP_DIR
        devloop_dir.mkdir()

        server = MCPServer(project_root=tmp_path)

        assert server.project_root == tmp_path
        assert server.devloop_dir == devloop_dir
        assert server.server is not None
        assert server.server.name == "devloop"

    def test_server_init_finds_project_root(self, tmp_path: Path) -> None:
        """Test server initialization automatically finds project root."""
        # Create .devloop directory in tmp_path
        devloop_dir = tmp_path / DEVLOOP_DIR
        devloop_dir.mkdir()

        # Mock cwd to return tmp_path
        with patch.object(Path, "cwd", return_value=tmp_path):
            server = MCPServer()

        assert server.project_root == tmp_path
        assert server.devloop_dir == devloop_dir

    def test_server_init_finds_project_root_in_parent(self, tmp_path: Path) -> None:
        """Test server initialization finds project root in parent directory."""
        # Create .devloop directory in tmp_path (parent)
        devloop_dir = tmp_path / DEVLOOP_DIR
        devloop_dir.mkdir()

        # Create a child directory
        child_dir = tmp_path / "src" / "module"
        child_dir.mkdir(parents=True)

        # Mock cwd to return child directory
        with patch.object(Path, "cwd", return_value=child_dir):
            server = MCPServer()

        assert server.project_root == tmp_path
        assert server.devloop_dir == devloop_dir

    def test_server_init_fails_without_devloop(self, tmp_path: Path) -> None:
        """Test server initialization fails when .devloop not found."""
        # Mock cwd to return a directory without .devloop
        with patch.object(Path, "cwd", return_value=tmp_path):
            with pytest.raises(FileNotFoundError) as exc_info:
                MCPServer()

        assert ".devloop" in str(exc_info.value)
        assert "devloop init" in str(exc_info.value)

    def test_server_init_fails_with_invalid_project_root(self, tmp_path: Path) -> None:
        """Test server initialization fails when project_root has no .devloop."""
        # tmp_path exists but has no .devloop directory
        with pytest.raises(FileNotFoundError) as exc_info:
            MCPServer(project_root=tmp_path)

        assert ".devloop" in str(exc_info.value)

    def test_find_project_root_not_found(self, tmp_path: Path) -> None:
        """Test _find_project_root returns None when not found."""
        # Mock cwd to return a temp directory without .devloop
        with patch.object(Path, "cwd", return_value=tmp_path):
            server_cls = MCPServer
            result = server_cls._find_project_root(server_cls)

        assert result is None

    def test_find_project_root_at_root(self, tmp_path: Path) -> None:
        """Test _find_project_root finds .devloop at project root."""
        # Create .devloop at tmp_path
        devloop_dir = tmp_path / DEVLOOP_DIR
        devloop_dir.mkdir()

        with patch.object(Path, "cwd", return_value=tmp_path):
            server = MCPServer()

        assert server.project_root == tmp_path

    @pytest.mark.asyncio
    async def test_run_starts_and_stops(self, tmp_path: Path) -> None:
        """Test server run method starts stdio transport."""
        # Create .devloop directory
        devloop_dir = tmp_path / DEVLOOP_DIR
        devloop_dir.mkdir()

        server = MCPServer(project_root=tmp_path)

        # Mock stdio_server and server.run
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()

        with patch("devloop.mcp.server.stdio_server") as mock_stdio:
            # Make stdio_server an async context manager
            mock_stdio.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read_stream, mock_write_stream)
            )
            mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)

            # Mock the underlying server.run
            server.server.run = AsyncMock()

            await server.run()

            # Verify stdio_server was used as context manager
            mock_stdio.return_value.__aenter__.assert_called_once()
            mock_stdio.return_value.__aexit__.assert_called_once()

            # Verify server.run was called with streams
            server.server.run.assert_called_once()
            call_args = server.server.run.call_args
            assert call_args[0][0] == mock_read_stream
            assert call_args[0][1] == mock_write_stream


class TestMCPServerAttributes:
    """Tests for MCPServer attribute setup."""

    def test_server_name_and_version(self, tmp_path: Path) -> None:
        """Test MCP server has correct name and version."""
        devloop_dir = tmp_path / DEVLOOP_DIR
        devloop_dir.mkdir()

        server = MCPServer(project_root=tmp_path)

        assert server.server.name == "devloop"
        assert server.server.version == __version__

    def test_devloop_dir_constant(self) -> None:
        """Test DEVLOOP_DIR constant is correct."""
        assert DEVLOOP_DIR == ".devloop"
