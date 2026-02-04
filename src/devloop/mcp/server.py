"""DevLoop MCP Server implementation.

Provides an MCP server that exposes DevLoop findings and context
to MCP clients like Claude Code.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from mcp.server import FastMCP


class DevLoopMCPServer:
    """MCP Server for DevLoop integration.

    Exposes DevLoop findings and project context via the Model Context Protocol,
    allowing Claude Code and other MCP clients to access DevLoop data.
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize the DevLoop MCP server.

        Args:
            project_root: Path to the project root. If None, will attempt
                to find it by looking for devloop markers.

        Raises:
            ValueError: If project_root is not provided and cannot be found.
        """
        if project_root is None:
            project_root = self._find_project_root()

        if project_root is None:
            raise ValueError(
                "Could not find DevLoop project root. "
                "Please run from a DevLoop-enabled project or specify project_root."
            )

        self.project_root = project_root
        self._server: Optional["FastMCP"] = None

    def _create_server(self) -> "FastMCP":
        """Create and configure the MCP server instance.

        Lazy initialization to avoid import issues during test collection.
        """
        # Import here to avoid module-level import issues
        from mcp.server import FastMCP

        server = FastMCP(name="devloop")
        return server

    @staticmethod
    def _find_project_root(start_path: Optional[Path] = None) -> Optional[Path]:
        """Find the DevLoop project root by looking for markers.

        Searches upward from start_path (or cwd) for directories containing
        DevLoop markers like .devloop/, devloop.toml, or pyproject.toml with
        devloop configuration.

        Args:
            start_path: Path to start searching from. Defaults to cwd.

        Returns:
            Path to project root if found, None otherwise.
        """
        if start_path is None:
            start_path = Path.cwd()

        current = start_path.resolve()

        # DevLoop project markers
        markers = [
            ".devloop",
            "devloop.toml",
            ".beads",
        ]

        while current != current.parent:
            for marker in markers:
                if (current / marker).exists():
                    return current
            current = current.parent

        # Check root as well
        for marker in markers:
            if (current / marker).exists():
                return current

        return None

    async def run(self) -> None:
        """Run the MCP server using stdio transport.

        This method blocks and handles MCP protocol messages via stdin/stdout.
        """
        if self._server is None:
            self._server = self._create_server()
        await self._server.run_stdio_async()
