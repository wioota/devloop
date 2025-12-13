"""Marketplace commands for discovering, searching, and managing agents."""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from devloop.marketplace import RegistryClient, RegistryConfig
from devloop.marketplace.installer import AgentInstaller
from devloop.marketplace.registry import AgentRegistry


logger = logging.getLogger(__name__)
app = typer.Typer(help="Agent marketplace commands", add_completion=False)
console = Console()


def get_marketplace_dir() -> Path:
    """Get marketplace configuration directory."""
    # Use .devloop/marketplace for now, will be configurable later
    devloop_dir = Path.home() / ".devloop"
    marketplace_dir = devloop_dir / "marketplace"
    return marketplace_dir


def get_registry_client() -> RegistryClient:
    """Get or create marketplace registry client."""
    marketplace_dir = get_marketplace_dir()
    config = RegistryConfig(registry_dir=marketplace_dir)
    registry = AgentRegistry(config)

    # TODO: Load remote registry URLs from config
    remote_urls = []

    return RegistryClient(registry, remote_urls)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (agent name or keyword)"),
    category: Optional[str] = typer.Option(None, help="Filter by category"),
    min_rating: float = typer.Option(0.0, help="Minimum rating (1-5)"),
    limit: int = typer.Option(20, help="Maximum results to show"),
    remote: bool = typer.Option(True, help="Search remote registries"),
) -> None:
    """Search for agents in the marketplace."""
    client = get_registry_client()

    categories = [category] if category else None
    results = client.search(
        query,
        search_remote=remote,
        categories=categories,
        min_rating=min_rating,
        max_results=limit,
    )

    all_results = results.get("local", []) + results.get("remote", [])

    if not all_results:
        console.print("[yellow]No agents found matching your search.[/yellow]")
        return

    # Display results in a table
    table = Table(title=f"Search Results: {query}")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="magenta")
    table.add_column("Author", style="green")
    table.add_column("Rating", style="yellow")
    table.add_column("Downloads")
    table.add_column("Status")

    for agent in all_results[:limit]:
        rating_str = f"★ {agent.rating.average:.1f}" if agent.rating else "N/A"
        status_tags = []
        if agent.trusted:
            status_tags.append("[green]✓ Trusted[/green]")
        if agent.experimental:
            status_tags.append("[yellow]⚠ Experimental[/yellow]")
        if agent.deprecated:
            status_tags.append("[red]✗ Deprecated[/red]")

        status = ", ".join(status_tags) if status_tags else "-"

        table.add_row(
            agent.name,
            agent.version,
            agent.author,
            rating_str,
            str(agent.downloads),
            status,
        )

    console.print(table)


@app.command()
def info(
    name: str = typer.Argument(..., help="Agent name"),
    version: Optional[str] = typer.Option(None, help="Specific version"),
) -> None:
    """Show detailed information about an agent."""
    client = get_registry_client()
    agent = client.get_agent(name, version)

    if not agent:
        console.print(f"[red]Agent not found: {name}[/red]")
        return

    # Build info panel
    info_text = Text()
    info_text.append("Name:        ", style="bold")
    info_text.append(f"{agent.name}\n")

    info_text.append("Version:     ", style="bold")
    info_text.append(f"{agent.version}\n")

    info_text.append("Author:      ", style="bold")
    info_text.append(f"{agent.author}\n")

    info_text.append("License:     ", style="bold")
    info_text.append(f"{agent.license}\n")

    if agent.homepage:
        info_text.append("Homepage:    ", style="bold")
        info_text.append(f"{agent.homepage}\n")

    if agent.repository:
        info_text.append("Repository:  ", style="bold")
        info_text.append(f"{agent.repository}\n")

    info_text.append("\nDescription:\n", style="bold")
    info_text.append(agent.description + "\n")

    if agent.categories:
        info_text.append("\nCategories:  ", style="bold")
        info_text.append(", ".join(agent.categories) + "\n")

    if agent.keywords:
        info_text.append("Keywords:    ", style="bold")
        info_text.append(", ".join(agent.keywords) + "\n")

    if agent.rating:
        info_text.append("\nRating:      ", style="bold")
        info_text.append(
            f"★ {agent.rating.average:.1f} ({agent.rating.count} ratings)\n"
        )

    info_text.append("Downloads:   ", style="bold")
    info_text.append(f"{agent.downloads}\n")

    # Requirements
    info_text.append("\nRequirements:\n", style="bold")
    info_text.append(f"  Python:      {agent.python_version}\n")
    info_text.append(f"  DevLoop:     {agent.devloop_version}\n")

    if agent.dependencies:
        info_text.append("  Dependencies:\n", style="bold")
        for dep in agent.dependencies:
            optional = " (optional)" if dep.optional else ""
            info_text.append(f"    - {dep.name} {dep.version}{optional}\n")

    # Status
    if agent.deprecated:
        info_text.append("\n[red]⚠ DEPRECATED[/red]")
        if agent.deprecation_message:
            info_text.append(f": {agent.deprecation_message}")
    elif agent.trusted:
        info_text.append("\n[green]✓ Verified by DevLoop maintainers[/green]")
    elif agent.experimental:
        info_text.append("\n[yellow]⚠ Experimental - use with caution[/yellow]")

    console.print(Panel(info_text, title=f"[bold]{agent.name}[/bold]"))


@app.command()
def list(
    category: Optional[str] = typer.Option(None, help="Filter by category"),
    limit: int = typer.Option(20, help="Maximum agents to show"),
    sort: str = typer.Option("rating", help="Sort by: rating, downloads, name"),
) -> None:
    """List agents in the marketplace."""
    client = get_registry_client()

    if category:
        agents = client.get_agents_by_category(category, limit=limit)
        title = f"Agents in {category}"
    else:
        agents = client.get_popular_agents(limit=limit)
        title = "Popular Agents"

    if not agents:
        console.print("[yellow]No agents found.[/yellow]")
        return

    table = Table(title=title)
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="magenta")
    table.add_column("Author", style="green")
    table.add_column("Rating")
    table.add_column("Downloads")

    for agent in agents:
        rating_str = f"★ {agent.rating.average:.1f}" if agent.rating else "N/A"
        table.add_row(
            agent.name,
            agent.version,
            agent.author,
            rating_str,
            str(agent.downloads),
        )

    console.print(table)


@app.command()
def categories() -> None:
    """List all agent categories."""
    client = get_registry_client()
    categories = client.get_categories()

    if not categories:
        console.print("[yellow]No categories available.[/yellow]")
        return

    table = Table(title="Agent Categories")
    table.add_column("Category", style="cyan")
    table.add_column("Count")

    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        table.add_row(cat, str(count))

    console.print(table)


@app.command()
def rate(
    name: str = typer.Argument(..., help="Agent name"),
    rating: float = typer.Argument(..., help="Rating (1-5 stars)"),
) -> None:
    """Rate an agent."""
    if not 1 <= rating <= 5:
        console.print("[red]Rating must be between 1 and 5.[/red]")
        return

    client = get_registry_client()

    if client.rate_agent(name, rating):
        agent = client.get_agent(name)
        if agent and agent.rating:
            console.print(
                f"[green]✓ Rated {name} {rating} stars[/green]\n"
                f"New average: ★ {agent.rating.average:.1f} ({agent.rating.count} ratings)"
            )
    else:
        console.print(f"[red]Failed to rate agent: {name}[/red]")


@app.command()
def stats() -> None:
    """Show marketplace statistics."""
    client = get_registry_client()
    stats = client.get_registry_stats()

    local_stats = stats["local"]

    stats_text = Text()
    stats_text.append("Total Agents:        ", style="bold")
    stats_text.append(f"{local_stats['total_agents']}\n")

    stats_text.append("Active Agents:       ", style="bold")
    stats_text.append(f"{local_stats['active_agents']}\n")

    stats_text.append("Trusted Agents:      ", style="bold")
    stats_text.append(f"{local_stats['trusted_agents']}\n")

    stats_text.append("Total Downloads:     ", style="bold")
    stats_text.append(f"{local_stats['total_downloads']}\n")

    stats_text.append("Average Rating:      ", style="bold")
    stats_text.append(f"★ {local_stats['average_rating']:.1f}\n")

    if local_stats["categories"]:
        stats_text.append(
            f"\nCategories ({len(local_stats['categories'])}):\n", style="bold"
        )
        for cat, count in sorted(
            local_stats["categories"].items(), key=lambda x: -x[1]
        )[:10]:
            stats_text.append(f"  {cat}: {count}\n")

    console.print(Panel(stats_text, title="[bold]Marketplace Statistics[/bold]"))


def _get_installer() -> AgentInstaller:
    """Get or create an agent installer."""
    marketplace_dir = get_marketplace_dir()
    config = RegistryConfig(registry_dir=marketplace_dir)
    registry = AgentRegistry(config)
    client = RegistryClient(registry)
    return AgentInstaller(marketplace_dir, client)


def _get_review_store():
    """Get or create a review store."""
    from devloop.marketplace.reviews import ReviewStore

    marketplace_dir = get_marketplace_dir()
    reviews_dir = marketplace_dir / "reviews"
    return ReviewStore(reviews_dir)


@app.command()
def install(
    name: str = typer.Argument(..., help="Agent name to install"),
    version: Optional[str] = typer.Option(None, help="Specific version"),
    force: bool = typer.Option(
        False, help="Force installation even if already installed"
    ),
) -> None:
    """Install an agent from the marketplace."""
    installer = _get_installer()

    success, msg = installer.install(name, version, force=force)

    if success:
        console.print(f"[green]✓ {msg}[/green]")
    else:
        console.print(f"[red]✗ {msg}[/red]")


@app.command()
def uninstall(
    name: str = typer.Argument(..., help="Agent name to uninstall"),
    force: bool = typer.Option(False, help="Remove even if other agents depend on it"),
) -> None:
    """Uninstall an agent."""
    installer = _get_installer()

    success, msg = installer.uninstall(name, remove_dependencies=force)

    if success:
        console.print(f"[green]✓ {msg}[/green]")
    else:
        console.print(f"[red]✗ {msg}[/red]")


@app.command()
def list_installed() -> None:
    """List installed agents."""
    installer = _get_installer()

    installed = installer.list_installed()

    if not installed:
        console.print("[yellow]No agents installed.[/yellow]")
        return

    table = Table(title="Installed Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="magenta")
    table.add_column("Installed", style="green")
    table.add_column("Type")

    for record in installed:
        type_str = "Direct" if record.installed_by_user else "Dependency"
        table.add_row(
            record.agent_name,
            record.version,
            record.installed_at[:10],  # Just the date
            type_str,
        )

    console.print(table)


@app.command()
def review(
    name: str = typer.Argument(..., help="Agent name to review"),
    rating: float = typer.Argument(..., help="Rating (1-5 stars)"),
    title: str = typer.Option(..., help="Review title"),
    comment: str = typer.Option(..., help="Review text"),
    verified: bool = typer.Option(False, help="Mark as verified purchase"),
) -> None:
    """Add or update a review for an agent."""
    if not 1 <= rating <= 5:
        console.print("[red]Rating must be between 1 and 5.[/red]")
        return

    store = _get_review_store()
    username = "anonymous"  # TODO: Get from config/env

    success = store.add_review(
        name, username, rating, title, comment, verified_purchase=verified
    )

    if success:
        stats = store.get_agent_stats(name)
        console.print(
            f"[green]✓ Review added for {name}[/green]\n"
            f"New average: ★ {stats['average_rating']:.1f} "
            f"({stats['total_reviews']} reviews)"
        )
    else:
        console.print(f"[red]Failed to add review for {name}[/red]")


@app.command()
def reviews(
    name: str = typer.Argument(..., help="Agent name"),
    limit: int = typer.Option(10, help="Maximum reviews to show"),
    sort: str = typer.Option("recent", help="Sort by: recent, helpful"),
) -> None:
    """View reviews for an agent."""
    store = _get_review_store()
    stats = store.get_agent_stats(name)

    if stats["total_reviews"] == 0:
        console.print(f"[yellow]No reviews yet for {name}[/yellow]")
        return

    # Header with stats
    header = (
        f"[bold]{name}[/bold] - "
        f"★ {stats['average_rating']:.1f} "
        f"({stats['total_reviews']} reviews)"
    )
    console.print(Panel(header))

    # Get reviews
    if sort == "helpful":
        reviews_list = store.get_helpful_reviews(name, limit)
    else:
        reviews_list = store.get_recent_reviews(name, limit)

    # Display reviews
    table = Table(show_header=True, header_style="bold")
    table.add_column("Rating", style="yellow")
    table.add_column("Title", style="cyan")
    table.add_column("Reviewer", style="green")
    table.add_column("Helpful")

    for review_item in reviews_list:
        rating_str = "★" * int(review_item.rating)
        verified = " ✓" if review_item.verified_purchase else ""
        reviewer = f"{review_item.reviewer}{verified}"
        table.add_row(
            rating_str, review_item.title, reviewer, str(review_item.helpful_count)
        )

    console.print(table)

    # Show full review on request
    if len(reviews_list) > 0:
        console.print(
            "\n[dim]Tip: Use 'devloop agent review-details' to see full reviews[/dim]"
        )


@app.command()
def review_details(
    name: str = typer.Argument(..., help="Agent name"),
    reviewer: Optional[str] = typer.Option(None, help="Filter by reviewer"),
) -> None:
    """View detailed reviews for an agent."""
    store = _get_review_store()
    all_reviews = store.get_reviews(name)

    if not all_reviews:
        console.print(f"[yellow]No reviews for {name}[/yellow]")
        return

    # Filter by reviewer if specified
    if reviewer:
        all_reviews = [r for r in all_reviews if r.reviewer == reviewer]

    for review_item in all_reviews:
        rating_str = "★" * int(review_item.rating)
        verified = (
            "[green]✓ Verified Purchase[/green]"
            if review_item.verified_purchase
            else "[dim]Unverified[/dim]"
        )

        review_text = Text()
        review_text.append(f"{rating_str} {review_item.title}\n", style="bold")
        review_text.append(f"by {review_item.reviewer} • {verified}\n")
        review_text.append(f"Helpful: {review_item.helpful_count} • ")
        review_text.append(f"{review_item.created_at[:10]}\n\n")
        review_text.append(review_item.comment)

        console.print(Panel(review_text, border_style="cyan"))
        console.print()


@app.command()
def review_stats(
    name: Optional[str] = typer.Argument(None, help="Agent name (optional)")
) -> None:
    """View review statistics."""
    store = _get_review_store()

    if name:
        stats = store.get_agent_stats(name)
        console.print(f"[bold]{name}[/bold]")
        console.print(f"Average Rating: ★ {stats['average_rating']:.1f}")
        console.print(f"Total Reviews: {stats['total_reviews']}")
        console.print(f"Verified Purchases: {stats['verified_purchases']}")

        if stats["rating_distribution"]:
            console.print("\nRating Distribution:")
            for rating in sorted(stats["rating_distribution"].keys(), reverse=True):
                count = stats["rating_distribution"][rating]
                bar = "█" * count
                console.print(f"  {rating}★ {bar} ({count})")
    else:
        overall_stats = store.get_stats()
        console.print("[bold]Overall Review Statistics[/bold]")
        console.print(f"Total Reviews: {overall_stats['total_reviews']}")
        console.print(f"Agents Reviewed: {overall_stats['agents_reviewed']}")
        console.print(
            f"Overall Average: ★ {overall_stats['overall_average_rating']:.1f}"
        )


if __name__ == "__main__":
    app()
