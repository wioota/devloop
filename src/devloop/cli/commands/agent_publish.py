"""CLI commands for publishing agents to the marketplace."""

from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(help="Agent publishing and maintenance")


@app.command()
def publish(
    agent_dir: Path = typer.Argument(
        ...,
        help="Directory containing the agent to publish",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force publish even if version exists",
    ),
    sign: bool = typer.Option(
        True,
        "--sign/--no-sign",
        help="Sign the agent before publishing",
    ),
    signer_id: Optional[str] = typer.Option(
        None,
        "--signer",
        "-s",
        help="Signer ID for agent signature",
    ),
    registry_dir: Optional[Path] = typer.Option(
        None,
        "--registry-dir",
        "-r",
        help="Registry directory (default: ~/.devloop/registry)",
    ),
) -> None:
    """Publish an agent to the marketplace.

    Example:
        devloop agent publish ./my-agent
        devloop agent publish ./my-agent --force
        devloop agent publish ./my-agent --sign --signer "John Doe"
    """
    from devloop.marketplace import (
        AgentPublisher,
        AgentSigner,
        create_registry_client,
    )

    # Validate agent directory
    if not agent_dir.exists():
        typer.echo(f"Error: Agent directory not found: {agent_dir}", err=True)
        raise typer.Exit(1)

    if not (agent_dir / "agent.json").exists():
        typer.echo(f"Error: No agent.json found in {agent_dir}", err=True)
        raise typer.Exit(1)

    # Default registry directory
    if not registry_dir:
        registry_dir = Path.home() / ".devloop" / "registry"

    try:
        # Create registry client and publisher
        client = create_registry_client(registry_dir)
        publisher = AgentPublisher(client)

        # Check publish readiness
        readiness = publisher.get_publish_readiness(agent_dir)

        typer.echo("Publish Readiness Check:")
        typer.echo("=" * 50)

        if readiness["errors"]:
            typer.secho("Errors (blocking):", fg=typer.colors.RED)
            for error in readiness["errors"]:
                typer.secho(f"  ✗ {error}", fg=typer.colors.RED)
            raise typer.Exit(1)

        if readiness["warnings"]:
            typer.secho("Warnings:", fg=typer.colors.YELLOW)
            for warning in readiness["warnings"]:
                typer.secho(f"  ⚠ {warning}", fg=typer.colors.YELLOW)

        if readiness["ready"]:
            typer.secho("✓ Agent is ready to publish", fg=typer.colors.GREEN)

        typer.echo()

        # Sign agent if requested
        if sign:
            typer.echo("Signing agent...")
            signer = AgentSigner(signer_id or "devloop-agent")
            success, signature = signer.sign_agent(agent_dir)

            if success and signature is not None:
                signer.save_signature(agent_dir, signature)
                typer.echo(f"✓ Agent signed by {signature.signer}")
                typer.echo(f"  Checksum: {signature.checksum[:16]}...")
            else:
                typer.echo("Warning: Failed to sign agent", err=True)

            typer.echo()

        # Publish agent
        typer.echo("Publishing agent...")
        success, message = publisher.publish_agent(agent_dir, force=force)

        if success:
            typer.secho(f"✓ {message}", fg=typer.colors.GREEN)
        else:
            typer.secho(f"✗ {message}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def check(
    agent_dir: Path = typer.Argument(
        ...,
        help="Directory containing the agent",
    ),
    registry_dir: Optional[Path] = typer.Option(
        None,
        "--registry-dir",
        "-r",
        help="Registry directory",
    ),
) -> None:
    """Check if agent is ready to publish.

    Example:
        devloop agent check ./my-agent
    """
    from devloop.marketplace import AgentPublisher, create_registry_client

    if not agent_dir.exists():
        typer.echo(f"Error: Agent directory not found: {agent_dir}", err=True)
        raise typer.Exit(1)

    if not (agent_dir / "agent.json").exists():
        typer.echo(f"Error: No agent.json found in {agent_dir}", err=True)
        raise typer.Exit(1)

    if not registry_dir:
        registry_dir = Path.home() / ".devloop" / "registry"

    try:
        client = create_registry_client(registry_dir)
        publisher = AgentPublisher(client)

        readiness = publisher.get_publish_readiness(agent_dir)

        typer.echo("Publish Readiness Report")
        typer.echo("=" * 50)

        # Show status
        status = "✓ READY" if readiness["ready"] else "✗ NOT READY"
        color = typer.colors.GREEN if readiness["ready"] else typer.colors.RED
        typer.secho(f"Status: {status}", fg=color)
        typer.echo()

        # Show checks
        if readiness["checks"]:
            typer.echo("Checks:")
            for check_name, result in readiness["checks"].items():
                symbol = "✓" if result else "✗"
                color = typer.colors.GREEN if result else typer.colors.RED
                typer.secho(f"  {symbol} {check_name}", fg=color)

        # Show errors
        if readiness["errors"]:
            typer.echo()
            typer.secho("Errors (blocking):", fg=typer.colors.RED)
            for error in readiness["errors"]:
                typer.echo(f"  • {error}")

        # Show warnings
        if readiness["warnings"]:
            typer.echo()
            typer.secho("Warnings:", fg=typer.colors.YELLOW)
            for warning in readiness["warnings"]:
                typer.echo(f"  • {warning}")

        # Show update info
        typer.echo()
        updates = publisher.check_updates(agent_dir)
        if updates.get("has_updates"):
            typer.secho(
                f"Update available: {updates['published_version']} → "
                f"{updates['local_version']}",
                fg=typer.colors.BLUE,
            )
        elif "local_version" in updates:
            typer.echo(f"Local version: {updates['local_version']}")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def version(
    agent_dir: Path = typer.Argument(
        ...,
        help="Directory containing the agent",
    ),
    bump_type: str = typer.Argument(
        "patch",
        help="Type of version bump: major, minor, or patch",
    ),
) -> None:
    """Bump agent version.

    Example:
        devloop agent version ./my-agent patch
        devloop agent version ./my-agent minor
        devloop agent version ./my-agent major
    """
    from devloop.marketplace import VersionManager
    import json

    if not agent_dir.exists():
        typer.echo(f"Error: Agent directory not found: {agent_dir}", err=True)
        raise typer.Exit(1)

    agent_json = agent_dir / "agent.json"
    if not agent_json.exists():
        typer.echo(f"Error: No agent.json found in {agent_dir}", err=True)
        raise typer.Exit(1)

    try:
        # Get current version
        with open(agent_json) as f:
            data = json.load(f)
        current = data.get("version", "0.0.0")

        # Bump version
        if bump_type not in ["major", "minor", "patch"]:
            typer.echo(
                "Error: bump_type must be major, minor, or patch",
                err=True,
            )
            raise typer.Exit(1)

        new_version = VersionManager.bump_version(current, bump_type)

        # Update file
        success = VersionManager.update_agent_json(agent_dir, new_version)

        if success:
            typer.secho(
                f"✓ Version bumped: {current} → {new_version}", fg=typer.colors.GREEN
            )
        else:
            typer.echo("Error: Failed to update version", err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def deprecate(
    agent_name: str = typer.Argument(
        ...,
        help="Name of the agent to deprecate",
    ),
    message: str = typer.Option(
        ...,
        "--message",
        "-m",
        help="Deprecation message",
    ),
    replacement: Optional[str] = typer.Option(
        None,
        "--replacement",
        "-r",
        help="Suggested replacement agent",
    ),
    registry_dir: Optional[Path] = typer.Option(
        None,
        "--registry-dir",
        help="Registry directory",
    ),
) -> None:
    """Deprecate an agent.

    Example:
        devloop agent deprecate old-agent --message "No longer maintained"
        devloop agent deprecate old-agent -m "Use new-agent instead" -r new-agent
    """
    from devloop.marketplace import DeprecationManager, create_registry_client

    if not registry_dir:
        registry_dir = Path.home() / ".devloop" / "registry"

    try:
        client = create_registry_client(registry_dir)
        manager = DeprecationManager(client)

        success, result_message = manager.deprecate_agent(
            agent_name,
            message,
            replacement=replacement,
        )

        if success:
            typer.secho(f"✓ {result_message}", fg=typer.colors.GREEN)
        else:
            typer.secho(f"✗ {result_message}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def register_agent_commands(main_app: typer.Typer) -> None:
    """Register agent commands with main CLI app."""
    main_app.add_typer(app, name="agent")
