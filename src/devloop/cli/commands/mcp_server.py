"""MCP server CLI command.

This module provides the CLI entry point for the DevLoop MCP server,
enabling integration with Claude Code and other MCP-compatible clients.

Usage:
    devloop mcp-server              # Start server (stdio mode)
    devloop mcp-server --check      # Validate server can start
    devloop mcp-server --install    # Register in Claude Code settings
    devloop mcp-server --uninstall  # Remove from Claude Code settings
"""

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(name="mcp-server", help="DevLoop MCP server for Claude Code")
console = Console()


def get_claude_settings_path() -> Path:
    """Get the path to Claude Code settings file.

    Returns:
        Path to ~/.claude/settings.json
    """
    return Path.home() / ".claude" / "settings.json"


def install_mcp_server() -> bool:
    """Install DevLoop MCP server in Claude Code settings.

    Creates or updates ~/.claude/settings.json to register the devloop
    MCP server.

    Returns:
        True if installation succeeded, False otherwise.
    """
    settings_path = get_claude_settings_path()

    # Create .claude directory if needed
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing settings or create new
    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except json.JSONDecodeError:
            settings = {}

    # Ensure mcpServers key exists
    if "mcpServers" not in settings:
        settings["mcpServers"] = {}

    # Add devloop server configuration
    settings["mcpServers"]["devloop"] = {
        "command": "devloop",
        "args": ["mcp-server"],
    }

    # Write settings back
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")

    return True


def uninstall_mcp_server() -> bool:
    """Remove DevLoop MCP server from Claude Code settings.

    Updates ~/.claude/settings.json to remove the devloop MCP server.

    Returns:
        True if uninstallation succeeded, False otherwise.
    """
    settings_path = get_claude_settings_path()

    if not settings_path.exists():
        return True

    try:
        settings = json.loads(settings_path.read_text())
    except json.JSONDecodeError:
        return True

    # Remove devloop from mcpServers if present
    if "mcpServers" in settings and "devloop" in settings["mcpServers"]:
        del settings["mcpServers"]["devloop"]

        # Write settings back
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")

    return True


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    check: bool = typer.Option(
        False, "--check", help="Validate server can start correctly"
    ),
    install: bool = typer.Option(
        False, "--install", help="Register in Claude Code settings"
    ),
    uninstall: bool = typer.Option(
        False, "--uninstall", help="Remove from Claude Code settings"
    ),
) -> None:
    """DevLoop MCP server for Claude Code integration.

    By default, starts the MCP server in stdio mode for Claude Code communication.

    Use --install to register the server in Claude Code settings, and
    --uninstall to remove it.
    """
    # Import here to avoid circular imports and for lazy loading
    from devloop.mcp.server import MCPServer

    # Check for mutually exclusive options
    options_set = sum([check, install, uninstall])
    if options_set > 1:
        console.print(
            "[red]Error:[/red] Only one of --check, --install, or --uninstall can be specified"
        )
        raise typer.Exit(1)

    if check:
        # Validate server can start
        try:
            server = MCPServer()
            console.print("[green]Server validated successfully.[/green]")
            console.print(f"Project root: {server.project_root}")
        except FileNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error validating server:[/red] {e}")
            raise typer.Exit(1)

    elif install:
        # Install MCP server in Claude Code settings
        try:
            if install_mcp_server():
                settings_path = get_claude_settings_path()
                console.print(
                    "[green]DevLoop MCP server installed successfully.[/green]"
                )
                console.print(f"Settings updated: {settings_path}")
                console.print("\nRestart Claude Code to activate the MCP server.")
            else:
                console.print("[red]Failed to install MCP server.[/red]")
                raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error installing MCP server:[/red] {e}")
            raise typer.Exit(1)

    elif uninstall:
        # Remove MCP server from Claude Code settings
        try:
            if uninstall_mcp_server():
                console.print(
                    "[green]DevLoop MCP server uninstalled successfully.[/green]"
                )
            else:
                console.print("[red]Failed to uninstall MCP server.[/red]")
                raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error uninstalling MCP server:[/red] {e}")
            raise typer.Exit(1)

    else:
        # Start server in stdio mode (default behavior)
        try:
            server = MCPServer()
            asyncio.run(server.run())
        except FileNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            console.print(f"[red]Server error:[/red] {e}")
            raise typer.Exit(1)
