"""Telemetry commands for viewing value tracking data."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from devloop.core.telemetry import get_telemetry_logger

app = typer.Typer(help="View DevLoop telemetry and value tracking data")
console = Console()


@app.command()
def stats(
    log_file: Optional[Path] = typer.Option(
        None,
        "--log-file",
        help="Path to events.jsonl file (defaults to .devloop/events.jsonl)",
    ),
):
    """Show telemetry statistics."""
    if log_file:
        telemetry = get_telemetry_logger(log_file)
    else:
        telemetry = get_telemetry_logger()

    stats = telemetry.get_stats()

    # Print summary table
    table = Table(title="DevLoop Telemetry Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Events", str(stats["total_events"]))
    table.add_row("Total Findings", str(stats["total_findings"]))
    table.add_row("CI Roundtrips Prevented", str(stats["ci_roundtrips_prevented"]))
    table.add_row(
        "Total Time Saved",
        f"{stats['total_time_saved_ms'] / 1000:.1f}s",
    )

    console.print(table)

    # Print events by type
    if stats["events_by_type"]:
        console.print("\n[cyan]Events by Type:[/cyan]")
        event_table = Table()
        event_table.add_column("Event Type", style="cyan")
        event_table.add_column("Count", style="green")

        for event_type, count in stats["events_by_type"].items():
            event_table.add_row(event_type, str(count))

        console.print(event_table)

    # Print agent stats
    if stats["agents_executed"]:
        console.print("\n[cyan]Agent Execution Stats:[/cyan]")
        agent_table = Table()
        agent_table.add_column("Agent", style="cyan")
        agent_table.add_column("Executions", style="green")
        agent_table.add_column("Total Duration", style="green")
        agent_table.add_column("Avg Duration", style="green")

        for agent, data in stats["agents_executed"].items():
            count = data["count"]
            total_duration = data["total_duration_ms"]
            avg_duration = total_duration / count if count > 0 else 0

            agent_table.add_row(
                agent,
                str(count),
                f"{total_duration}ms",
                f"{avg_duration:.0f}ms",
            )

        console.print(agent_table)


@app.command()
def recent(
    count: int = typer.Option(
        10, "--count", "-n", help="Number of recent events to show"
    ),
    log_file: Optional[Path] = typer.Option(
        None,
        "--log-file",
        help="Path to events.jsonl file (defaults to .devloop/events.jsonl)",
    ),
):
    """Show recent telemetry events."""
    if log_file:
        telemetry = get_telemetry_logger(log_file)
    else:
        telemetry = get_telemetry_logger()

    events = telemetry.get_events(limit=count)

    if not events:
        console.print("[yellow]No events recorded yet[/yellow]")
        return

    table = Table(title=f"Recent {len(events)} Events")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Event Type", style="green")
    table.add_column("Details", style="white")

    for event in events:
        timestamp = event.get("timestamp", "")
        event_type = event.get("event_type", "")

        # Build details string
        details_parts = []
        if event.get("agent"):
            details_parts.append(f"agent={event['agent']}")
        if event.get("duration_ms"):
            details_parts.append(f"duration={event['duration_ms']}ms")
        if event.get("findings"):
            details_parts.append(f"findings={event['findings']}")
        if event.get("success") is not None:
            status = "✓" if event["success"] else "✗"
            details_parts.append(f"success={status}")

        details = " | ".join(details_parts) if details_parts else "-"

        table.add_row(timestamp, event_type, details)

    console.print(table)


@app.command()
def export(
    output_file: Path = typer.Argument(..., help="Output file path (JSON or JSONL)"),
    log_file: Optional[Path] = typer.Option(
        None,
        "--log-file",
        help="Path to events.jsonl file (defaults to .devloop/events.jsonl)",
    ),
):
    """Export telemetry data to file."""
    import json

    if log_file:
        telemetry = get_telemetry_logger(log_file)
    else:
        telemetry = get_telemetry_logger()

    # Get all events
    events = telemetry.get_events(limit=10000)

    # Write to file
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if output_file.suffix.lower() == ".json":
            # Export as JSON array
            with open(output_file, "w") as f:
                json.dump(events, f, indent=2)
        else:
            # Export as JSONL
            with open(output_file, "w") as f:
                for event in events:
                    f.write(json.dumps(event) + "\n")

        console.print(
            f"[green]✓[/green] Exported {len(events)} events to {output_file}"
        )

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to export: {e}")
        raise typer.Exit(code=1)
