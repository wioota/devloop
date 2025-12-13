"""CLI command for starting the marketplace HTTP server."""

import logging
from pathlib import Path
from typing import List, Optional

import typer

logger = logging.getLogger(__name__)

app = typer.Typer(help="Marketplace registry HTTP server")


@app.command()
def start(
    registry_dir: Optional[Path] = typer.Option(
        None,
        "--registry-dir",
        "-r",
        help="Registry directory (default: ~/.devloop/registry)",
    ),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        "-h",
        help="Server host",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="Server port",
    ),
    remote_urls: Optional[List[str]] = typer.Option(
        None,
        "--remote",
        help="Remote registry URLs",
    ),
    cors_origins: Optional[List[str]] = typer.Option(
        None,
        "--cors-origin",
        help="CORS allowed origins",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Auto-reload on code changes",
    ),
) -> None:
    """Start the marketplace API server.

    Example:
        devloop marketplace server start --port 8000
        devloop marketplace server start --host 0.0.0.0 --port 5000
    """
    try:
        from devloop.marketplace import create_http_server
    except ImportError:
        typer.echo(
            "FastAPI is required for the marketplace server. "
            "Install with: pip install devloop[marketplace-api]",
            err=True,
        )
        raise typer.Exit(1)

    # Default registry directory
    if not registry_dir:
        registry_dir = Path.home() / ".devloop" / "registry"

    typer.echo("Starting marketplace API server...")
    typer.echo(f"  Registry: {registry_dir}")
    typer.echo(f"  Server: http://{host}:{port}")
    typer.echo(f"  API Docs: http://{host}:{port}/docs")
    typer.echo()

    try:
        server = create_http_server(
            registry_dir=registry_dir,
            remote_urls=remote_urls,
            host=host,
            port=port,
            cors_origins=cors_origins,
        )
        server.run(reload=reload)
    except ImportError as e:
        typer.echo(f"Error: {e}", err=True)
        typer.echo(
            "Install with: pip install devloop[marketplace-api]",
            err=True,
        )
        raise typer.Exit(1)
    except KeyboardInterrupt:
        typer.echo("Server stopped.")
        raise typer.Exit(0)


@app.command()
def status(
    registry_dir: Optional[Path] = typer.Option(
        None,
        "--registry-dir",
        "-r",
        help="Registry directory",
    ),
) -> None:
    """Show marketplace registry status.

    Example:
        devloop marketplace status
    """
    from devloop.marketplace import create_registry_client

    if not registry_dir:
        registry_dir = Path.home() / ".devloop" / "registry"

    if not registry_dir.exists():
        typer.echo("Registry not found.")
        raise typer.Exit(1)

    try:
        client = create_registry_client(registry_dir)
        stats = client.get_registry_stats()

        local = stats["local"]
        typer.echo("Marketplace Registry Status")
        typer.echo("=" * 50)
        typer.echo(f"Location: {registry_dir}")
        typer.echo()
        typer.echo("Statistics:")
        typer.echo(f"  Total Agents: {local['total_agents']}")
        typer.echo(f"  Active Agents: {local['active_agents']}")
        typer.echo(f"  Deprecated Agents: {local['deprecated_agents']}")
        typer.echo(f"  Trusted Agents: {local['trusted_agents']}")
        typer.echo(f"  Experimental Agents: {local['experimental_agents']}")
        typer.echo(f"  Total Downloads: {local['total_downloads']}")
        typer.echo(f"  Average Rating: {local['average_rating']}")
        typer.echo()

        if local["categories"]:
            typer.echo("Categories:")
            for category, count in sorted(
                local["categories"].items(),
                key=lambda x: -x[1],
            ):
                typer.echo(f"  {category}: {count} agents")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def register_marketplace_commands(main_app: typer.Typer) -> None:
    """Register marketplace commands with main CLI app."""
    main_app.add_typer(app, name="marketplace")
