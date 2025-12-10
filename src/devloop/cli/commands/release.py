"""Release management command."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from devloop.release import ReleaseConfig, ReleaseManager

app = typer.Typer(help="Release management commands", add_completion=False)
console = Console()


@app.command()
def publish(
    version: str = typer.Argument(..., help="Version to release (e.g., 1.2.3)"),
    branch: str = typer.Option(
        "main", "--branch", "-b", help="Target branch for release"
    ),
    ci_provider: Optional[str] = typer.Option(
        None, "--ci", help="CI provider (auto-detect if not specified)"
    ),
    registry_provider: Optional[str] = typer.Option(
        None, "--registry", help="Registry provider (auto-detect if not specified)"
    ),
    skip_checks: bool = typer.Option(
        False, "--skip-checks", help="Skip pre-release checks"
    ),
    skip_tag: bool = typer.Option(False, "--skip-tag", help="Skip creating git tag"),
    skip_publish: bool = typer.Option(
        False, "--skip-publish", help="Skip publishing to registry"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without doing it"
    ),
) -> int:
    """Publish a new release.

    Performs the full release workflow:
    1. Pre-release checks (git clean, branch, CI passes, registry credentials)
    2. Create git tag (v{version} by default)
    3. Publish to registry (PyPI, Artifactory, etc.)
    4. Push tag to remote

    Example:
        devloop release publish 1.2.3
        devloop release publish 2.0.0 --branch release --skip-tag
        devloop release publish 1.0.0 --ci github --registry pypi
    """
    console.print("[bold]DevLoop Release Manager[/bold]")
    console.print(f"Version: [cyan]{version}[/cyan]")
    console.print(f"Branch: [cyan]{branch}[/cyan]")
    console.print()

    if dry_run:
        console.print("[yellow]Dry-run mode[/yellow] - no changes will be made")
        console.print()

    # Create config
    config = ReleaseConfig(
        version=version,
        branch=branch,
        create_tag=not skip_tag,
        publish=not skip_publish,
        ci_provider=ci_provider,
        registry_provider=registry_provider,
    )

    # Create manager
    manager = ReleaseManager(config)

    # Run pre-release checks
    console.print("[bold]Running pre-release checks...[/bold]")
    checks_result = manager.run_pre_release_checks()

    # Display checks
    checks_table = Table(title="Pre-Release Checks")
    checks_table.add_column("Check", style="cyan")
    checks_table.add_column("Status", style="green")
    checks_table.add_column("Message", style="white")

    for check in checks_result.checks:
        status = "[green]✓[/green]" if check.passed else "[red]✗[/red]"
        checks_table.add_row(check.check_name, status, check.message)

    console.print(checks_table)
    console.print()

    if not checks_result.success:
        console.print("[red]✗ Pre-release checks failed[/red]")
        if not skip_checks:
            return 1
        console.print(
            "[yellow]Continuing despite failed checks (--skip-checks)[/yellow]"
        )
        console.print()

    if dry_run:
        console.print("[green]✓ Dry-run complete (no changes made)[/green]")
        return 0

    # Create tag if configured
    if config.create_tag:
        console.print("[bold]Creating git tag...[/bold]")
        tag_result = manager.create_release_tag()
        if tag_result.success:
            console.print(f"[green]✓ Tag created:[/green] {tag_result.url}")
        else:
            console.print(f"[red]✗ Failed to create tag:[/red] {tag_result.error}")
            return 1
        console.print()

    # Publish if configured
    if config.publish:
        console.print("[bold]Publishing to registry...[/bold]")
        pub_result = manager.publish_release()
        if pub_result.success:
            console.print(
                f"[green]✓ Published to:[/green] {pub_result.registry_provider_name}"
            )
            if pub_result.url:
                console.print(f"[cyan]URL:[/cyan] {pub_result.url}")
        else:
            console.print(f"[red]✗ Publishing failed:[/red] {pub_result.error}")
            return 1
        console.print()

    # Summary
    console.print("[bold][green]✓ Release successful![/green][/bold]")
    if checks_result.ci_provider_name:
        console.print(f"  CI Provider: {checks_result.ci_provider_name}")
    if checks_result.registry_provider_name:
        console.print(f"  Registry: {checks_result.registry_provider_name}")
    console.print(f"  Version: {version}")
    if config.create_tag:
        console.print(f"  Tag: v{version}")

    return 0


@app.command()
def check(
    version: str = typer.Argument(..., help="Version to check (e.g., 1.2.3)"),
    branch: str = typer.Option(
        "main", "--branch", "-b", help="Target branch for release"
    ),
    ci_provider: Optional[str] = typer.Option(
        None, "--ci", help="CI provider (auto-detect if not specified)"
    ),
    registry_provider: Optional[str] = typer.Option(
        None, "--registry", help="Registry provider (auto-detect if not specified)"
    ),
) -> int:
    """Check if a release is ready.

    Runs all pre-release checks without actually creating tags or publishing.

    Example:
        devloop release check 1.2.3
        devloop release check 2.0.0 --branch release
    """
    console.print("[bold]Checking release readiness[/bold]")
    console.print(f"Version: [cyan]{version}[/cyan]")
    console.print(f"Branch: [cyan]{branch}[/cyan]")
    console.print()

    # Create config
    config = ReleaseConfig(
        version=version,
        branch=branch,
        create_tag=False,
        publish=False,
        ci_provider=ci_provider,
        registry_provider=registry_provider,
    )

    # Create manager
    manager = ReleaseManager(config)

    # Run pre-release checks
    checks_result = manager.run_pre_release_checks()

    # Display checks
    checks_table = Table(title="Pre-Release Checks")
    checks_table.add_column("Check", style="cyan")
    checks_table.add_column("Status", style="green")
    checks_table.add_column("Message", style="white")

    for check in checks_result.checks:
        status = "[green]✓[/green]" if check.passed else "[red]✗[/red]"
        checks_table.add_row(check.check_name, status, check.message)

    console.print(checks_table)
    console.print()

    if checks_result.success:
        console.print("[green]✓ All checks passed - ready to release![/green]")
        if checks_result.ci_provider_name:
            console.print(f"  CI Provider: {checks_result.ci_provider_name}")
        if checks_result.registry_provider_name:
            console.print(f"  Registry: {checks_result.registry_provider_name}")
        return 0
    else:
        console.print("[red]✗ Some checks failed - not ready to release[/red]")
        console.print()
        console.print("[yellow]Failed checks:[/yellow]")
        for check in checks_result.checks:
            if not check.passed:
                console.print(f"  - {check.check_name}: {check.message}")
                if check.details:
                    console.print(f"    {check.details}")
        return 1
