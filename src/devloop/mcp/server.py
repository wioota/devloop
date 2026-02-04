"""DevLoop MCP Server implementation.

This module provides the MCP (Model Context Protocol) server for DevLoop,
enabling real-time bidirectional communication with Claude Code and other
MCP-compatible clients.

The server uses stdio transport and reads from the existing ContextStore
for findings, invoking the DevLoop CLI for write operations.
"""

import logging
from pathlib import Path
from typing import Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server

from devloop import __version__

logger = logging.getLogger(__name__)

# DevLoop directory name
DEVLOOP_DIR = ".devloop"


class MCPServer:
    """MCP Server for DevLoop integration with Claude Code.

    This server provides tools and resources for Claude Code to interact
    with DevLoop's context store, findings, and agent controls.

    Attributes:
        project_root: Path to the project root directory containing .devloop
        server: The underlying MCP Server instance
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize the MCP server.

        Args:
            project_root: Path to the project root. If not provided, will
                attempt to find the project root by looking for .devloop directory.

        Raises:
            FileNotFoundError: If .devloop directory cannot be found.
        """
        if project_root is None:
            project_root = self._find_project_root()

        if project_root is None:
            raise FileNotFoundError(
                "Could not find .devloop directory. "
                "Please run 'devloop init' to initialize the project."
            )

        self.project_root = project_root
        self.devloop_dir = project_root / DEVLOOP_DIR

        # Verify .devloop directory exists
        if not self.devloop_dir.exists():
            raise FileNotFoundError(
                f".devloop directory not found at {self.devloop_dir}. "
                "Please run 'devloop init' to initialize the project."
            )

        # Create MCP server instance
        self.server = Server(
            name="devloop",
            version=__version__,
        )

        logger.info(f"MCPServer initialized with project root: {self.project_root}")

    def _find_project_root(self) -> Optional[Path]:
        """Find the project root by searching for .devloop directory.

        Searches from the current working directory upward through parent
        directories until a .devloop directory is found.

        Returns:
            Path to the project root if found, None otherwise.
        """
        current = Path.cwd()

        # Search up from current directory
        while current != current.parent:
            if (current / DEVLOOP_DIR).exists():
                return current
            current = current.parent

        # Check root directory
        if (current / DEVLOOP_DIR).exists():
            return current

        return None

    async def run(self) -> None:
        """Run the MCP server using stdio transport.

        This method starts the server and handles communication via stdin/stdout.
        It runs until the client disconnects or an error occurs.
        """
        logger.info("Starting DevLoop MCP server...")

        async with stdio_server() as (read_stream, write_stream):
            init_options = self.server.create_initialization_options()
            await self.server.run(read_stream, write_stream, init_options)

        logger.info("DevLoop MCP server stopped.")


def main() -> None:
    """Main entry point for the MCP server."""
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        server = MCPServer()
        asyncio.run(server.run())
    except FileNotFoundError as e:
        logger.error(str(e))
        raise SystemExit(1)
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
