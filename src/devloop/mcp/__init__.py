"""DevLoop MCP Server module.

Provides Model Context Protocol (MCP) server functionality for DevLoop,
enabling Claude Code and other MCP clients to access DevLoop findings
and context.
"""

from devloop.mcp.server import DevLoopMCPServer

__all__ = ["DevLoopMCPServer"]
