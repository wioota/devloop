"""DevLoop MCP Server implementation.

This module provides the MCP (Model Context Protocol) server for DevLoop,
enabling real-time bidirectional communication with Claude Code and other
MCP-compatible clients.

The server uses stdio transport and reads from the existing ContextStore
for findings, invoking the DevLoop CLI for write operations.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from devloop import __version__
from devloop.core.context_store import ContextStore
from devloop.mcp.tools import apply_fix, dismiss_finding, get_findings

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

        # Initialize context store
        context_dir = self.devloop_dir / "context"
        self.context_store = ContextStore(
            context_dir=context_dir, enable_path_validation=False
        )

        # Register tool handlers
        self._register_tools()

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

    def _register_tools(self) -> None:
        """Register MCP tool handlers for findings management."""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available DevLoop tools."""
            return [
                Tool(
                    name="get_findings",
                    description=(
                        "Get code quality findings from DevLoop agents. "
                        "Supports filtering by file, severity, category, and tier."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file": {
                                "type": "string",
                                "description": "Filter findings by file path (exact match)",
                            },
                            "severity": {
                                "type": "string",
                                "enum": ["error", "warning", "info", "style"],
                                "description": "Filter by severity level",
                            },
                            "category": {
                                "type": "string",
                                "description": "Filter by category (e.g., security, style)",
                            },
                            "tier": {
                                "type": "string",
                                "enum": ["immediate", "relevant", "background", "auto_fixed"],
                                "description": "Filter by disclosure tier",
                            },
                            "limit": {
                                "type": "integer",
                                "default": 100,
                                "description": "Maximum number of findings to return",
                            },
                        },
                    },
                ),
                Tool(
                    name="dismiss_finding",
                    description=(
                        "Dismiss a finding by marking it as seen. "
                        "The finding remains but will be deprioritized."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "finding_id": {
                                "type": "string",
                                "description": "The ID of the finding to dismiss",
                            },
                            "reason": {
                                "type": "string",
                                "description": "Optional reason for dismissal",
                            },
                        },
                        "required": ["finding_id"],
                    },
                ),
                Tool(
                    name="apply_fix",
                    description=(
                        "Apply an auto-fix for a specific finding. "
                        "Only works for findings marked as auto-fixable."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "finding_id": {
                                "type": "string",
                                "description": "The ID of the finding to fix",
                            },
                        },
                        "required": ["finding_id"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(
            name: str, arguments: Dict[str, Any]
        ) -> List[TextContent]:
            """Handle tool invocation."""
            try:
                if name == "get_findings":
                    result = await get_findings(
                        self.context_store,
                        file=arguments.get("file"),
                        severity=arguments.get("severity"),
                        category=arguments.get("category"),
                        tier=arguments.get("tier"),
                        limit=arguments.get("limit", 100),
                    )
                    return [
                        TextContent(type="text", text=json.dumps(result, indent=2))
                    ]

                elif name == "dismiss_finding":
                    result = await dismiss_finding(
                        self.context_store,
                        finding_id=arguments["finding_id"],
                        reason=arguments.get("reason"),
                    )
                    return [
                        TextContent(type="text", text=json.dumps(result, indent=2))
                    ]

                elif name == "apply_fix":
                    result = await apply_fix(
                        self.context_store,
                        finding_id=arguments["finding_id"],
                    )
                    return [
                        TextContent(type="text", text=json.dumps(result, indent=2))
                    ]

                else:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"error": f"Unknown tool: {name}"}, indent=2
                            ),
                        )
                    ]

            except Exception as e:
                logger.error(f"Error handling tool {name}: {e}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": str(e), "tool": name}, indent=2
                        ),
                    )
                ]

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
