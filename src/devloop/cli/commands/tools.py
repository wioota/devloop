"""Tool dependency verification commands."""

from pathlib import Path

import typer

from devloop.core.tool_dependencies import ToolDependencyManager

app = typer.Typer(help="Verify external tool dependencies")


@app.command()
def check(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed version information"
    ),
    save: bool = typer.Option(
        False, "--save", "-s", help="Save report to .devloop/tools-report.json"
    ),
):
    """Check status of all external tools."""
    manager = ToolDependencyManager()

    if verbose:
        typer.echo("Checking external tool dependencies...\n")
        manager.show_compatibility_matrix()
    else:
        results = manager.check_all_tools()
        missing = [
            name
            for name, info in results.items()
            if info["critical"] and not info["available"]
        ]
        incompatible = [
            name
            for name, info in results.items()
            if info["available"] and not info["compatible"]
        ]

        if missing:
            typer.echo(f"❌ Missing critical tools: {', '.join(missing)}")
        if incompatible:
            typer.echo(f"⚠️  Incompatible versions: {', '.join(incompatible)}")
        if not missing and not incompatible:
            typer.echo("✅ All critical tools available and compatible")

    if save:
        report_path = Path(".devloop/tools-report.json")
        manager.save_compatibility_report(report_path)


@app.command()
def list():
    """List all tracked tool dependencies."""
    manager = ToolDependencyManager()

    typer.echo("\n📦 Python Tools (via dev dependencies):")
    for name, tool in sorted(manager.PYTHON_TOOLS.items()):
        typer.echo(f"  • {name:15} {tool.description}")
        if tool.min_version:
            typer.echo(f"    Min version: {tool.min_version}")

    typer.echo("\n🔧 External CLI Tools:")
    for name, tool in sorted(manager.EXTERNAL_TOOLS.items()):
        typer.echo(f"  • {name:15} {tool.description}")
        if tool.min_version:
            typer.echo(f"    Min version: {tool.min_version}")
        if tool.install_url:
            typer.echo(f"    Install: {tool.install_url}")

    typer.echo("\n⚙️  Optional Tools:")
    for name, tool in sorted(manager.OPTIONAL_TOOLS.items()):
        typer.echo(f"  • {name:15} {tool.description}")
        if tool.install_url:
            typer.echo(f"    Install: {tool.install_url}")

    typer.echo()


@app.command()
def verify_startup():
    """Run startup health check (used by daemon)."""
    manager = ToolDependencyManager()
    if manager.startup_check():
        typer.echo("✅ Startup check passed")
    else:
        typer.echo("⚠️  Some tools missing (non-blocking)")
        raise typer.Exit(code=1)
