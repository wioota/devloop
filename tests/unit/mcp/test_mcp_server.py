"""Tests for DevLoop MCP server."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devloop import __version__
from devloop.mcp.server import DEVLOOP_DIR, MCPServer, main


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


class TestMCPServerMain:
    """Tests for the main() entry point."""

    def test_main_file_not_found_exits(self) -> None:
        """main() handles FileNotFoundError by exiting with code 1."""
        with patch(
            "devloop.mcp.server.MCPServer",
            side_effect=FileNotFoundError("no .devloop"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_keyboard_interrupt_handled(self) -> None:
        """main() handles KeyboardInterrupt gracefully."""
        mock_server = MagicMock()
        with patch("devloop.mcp.server.MCPServer", return_value=mock_server):
            with patch("asyncio.run", side_effect=KeyboardInterrupt()):
                # Should not raise
                main()

    def test_main_generic_exception_exits(self) -> None:
        """main() handles generic exceptions by exiting with code 1."""
        mock_server = MagicMock()
        with patch("devloop.mcp.server.MCPServer", return_value=mock_server):
            with patch("asyncio.run", side_effect=RuntimeError("boom")):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1


class TestMCPServerCallTool:
    """Tests for the call_tool handler dispatch."""

    @pytest.fixture
    def server(self, tmp_path: Path) -> MCPServer:
        devloop_dir = tmp_path / DEVLOOP_DIR
        devloop_dir.mkdir()
        return MCPServer(project_root=tmp_path)

    def _get_call_tool_handler(self, server: MCPServer):
        """Extract the registered call_tool handler from the MCP server."""
        from mcp.types import CallToolRequest

        return server.server.request_handlers.get(CallToolRequest)

    @pytest.mark.asyncio
    async def test_get_findings_dispatches(self, server: MCPServer) -> None:
        with patch("devloop.mcp.server.get_findings", new_callable=AsyncMock) as mock:
            mock.return_value = {"findings": [], "count": 0}

            # Access call_tool via the request handler
            from mcp.types import CallToolRequest, CallToolRequestParams

            handler = self._get_call_tool_handler(server)
            assert handler is not None

            request = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="get_findings",
                    arguments={"severity": "error", "limit": 10},
                ),
            )
            await handler(request)
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, server: MCPServer) -> None:
        from mcp.types import CallToolRequest, CallToolRequestParams

        handler = self._get_call_tool_handler(server)
        request = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(
                name="nonexistent_tool",
                arguments={},
            ),
        )
        server_result = await handler(request)
        # ServerResult wraps a CallToolResult
        content = server_result.root.content
        assert len(content) > 0
        data = json.loads(content[0].text)
        assert "error" in data
        assert "nonexistent_tool" in data["error"]

    @pytest.mark.asyncio
    async def test_tool_exception_returns_error(self, server: MCPServer) -> None:
        with patch(
            "devloop.mcp.server.get_findings",
            new_callable=AsyncMock,
            side_effect=RuntimeError("context store failed"),
        ):
            from mcp.types import CallToolRequest, CallToolRequestParams

            handler = self._get_call_tool_handler(server)
            request = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="get_findings",
                    arguments={},
                ),
            )
            server_result = await handler(request)
            content = server_result.root.content
            data = json.loads(content[0].text)
            assert "error" in data
            assert "context store failed" in data["error"]

    @pytest.mark.asyncio
    async def test_run_formatter_dispatches(self, server: MCPServer) -> None:
        with patch("devloop.mcp.server.run_formatter", new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "formatted": 5}

            from mcp.types import CallToolRequest, CallToolRequestParams

            handler = self._get_call_tool_handler(server)
            request = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="run_formatter",
                    arguments={"timeout": 30},
                ),
            )
            await handler(request)
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_status_dispatches(self, server: MCPServer) -> None:
        with patch("devloop.mcp.server.get_status", new_callable=AsyncMock) as mock:
            mock.return_value = {"running": False}

            from mcp.types import CallToolRequest, CallToolRequestParams

            handler = self._get_call_tool_handler(server)
            request = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="get_status",
                    arguments={},
                ),
            )
            await handler(request)
            mock.assert_called_once()
