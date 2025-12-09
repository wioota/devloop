"""CLI command for querying and viewing audit logs."""

import json
from pathlib import Path
from typing import Optional

import click

from devloop.core.agent_audit_logger import (
    get_agent_audit_logger,
)


@click.group()
def audit():
    """Query and view audit logs."""
    pass


@audit.command()
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Number of entries to show (default: 20)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def recent(limit: int, output_json: bool):
    """Show recent agent audit entries."""
    logger = get_agent_audit_logger()
    entries = logger.query_recent(limit=limit)

    if output_json:
        click.echo(json.dumps(entries, indent=2))
    else:
        if not entries:
            click.echo("No audit entries found.")
            return

        click.echo(f"Recent Agent Actions ({len(entries)} entries)\n")
        for i, entry in enumerate(entries, 1):
            timestamp = entry.get("timestamp", "unknown")
            agent = entry.get("agent_name", "unknown")
            action = entry.get("action_type", "unknown")
            message = entry.get("message", "")
            success = entry.get("success", True)
            duration = entry.get("duration_ms", 0)

            status_icon = "✓" if success else "✗"

            click.echo(f"{i}. [{status_icon}] {agent} - {action}")
            click.echo(f"   Time: {timestamp} ({duration}ms)")
            click.echo(f"   {message}")

            # Show file modifications
            mods = entry.get("file_modifications", [])
            if mods:
                click.echo("   Files:")
                for mod in mods:
                    path = mod.get("path", "unknown")
                    mod_action = mod.get("action", "unknown")
                    click.echo(f"     - {path} ({mod_action})")

            # Show error if failed
            if not success and entry.get("error"):
                click.echo(f"   Error: {entry['error']}")

            click.echo()


@audit.command()
@click.argument("agent_name")
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Number of entries to show",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def by_agent(agent_name: str, limit: int, output_json: bool):
    """Show audit entries for a specific agent."""
    logger = get_agent_audit_logger()
    entries = logger.query_by_agent(agent_name, limit=limit)

    if output_json:
        click.echo(json.dumps(entries, indent=2))
    else:
        if not entries:
            click.echo(f"No audit entries found for agent: {agent_name}")
            return

        click.echo(f"Audit Entries for {agent_name} ({len(entries)} entries)\n")
        for entry in entries:
            timestamp = entry.get("timestamp", "unknown")
            action = entry.get("action_type", "unknown")
            message = entry.get("message", "")
            success = entry.get("success", True)

            status_icon = "✓" if success else "✗"
            click.echo(f"[{status_icon}] {action}: {message}")
            click.echo(f"    {timestamp}\n")


@audit.command()
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Number of entries to show",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def errors(limit: int, output_json: bool):
    """Show failed agent actions and errors."""
    logger = get_agent_audit_logger()
    entries = logger.query_failed_actions(limit=limit)

    if output_json:
        click.echo(json.dumps(entries, indent=2))
    else:
        if not entries:
            click.echo("No failed actions found.")
            return

        click.echo(f"Failed Agent Actions ({len(entries)} entries)\n")
        for i, entry in enumerate(entries, 1):
            timestamp = entry.get("timestamp", "unknown")
            agent = entry.get("agent_name", "unknown")
            action = entry.get("action_type", "unknown")
            message = entry.get("message", "")
            error = entry.get("error", "Unknown error")

            click.echo(f"{i}. {agent} - {action}")
            click.echo(f"   Time: {timestamp}")
            click.echo(f"   {message}")
            click.echo(f"   Error: {error}\n")


@audit.command()
@click.option(
    "--agent",
    type=str,
    default=None,
    help="Filter by agent name",
)
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Number of entries to show",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def fixes(agent: Optional[str], limit: int, output_json: bool):
    """Show fixes applied by agents."""
    logger = get_agent_audit_logger()
    entries = logger.query_fixes_applied(agent_name=agent, limit=limit)

    if output_json:
        click.echo(json.dumps(entries, indent=2))
    else:
        if not entries:
            agent_filter = f" by {agent}" if agent else ""
            click.echo(f"No fixes found{agent_filter}.")
            return

        agent_filter = f" by {agent}" if agent else ""
        click.echo(f"Fixes Applied{agent_filter} ({len(entries)} entries)\n")

        for entry in entries:
            timestamp = entry.get("timestamp", "unknown")
            agent_name = entry.get("agent_name", "unknown")
            message = entry.get("message", "")
            context = entry.get("context", {})
            fix_type = context.get("fix_type", "unknown")
            severity = context.get("severity", "unknown")

            click.echo(f"{agent_name}: {message}")
            click.echo(f"   Type: {fix_type}, Severity: {severity}")
            click.echo(f"   {timestamp}\n")


@audit.command()
@click.argument("file_path")
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Number of modifications to show",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
@click.option(
    "--diff",
    is_flag=True,
    help="Show diff for each modification",
)
def file(file_path: str, limit: int, output_json: bool, diff: bool):
    """Show modification history for a file."""
    logger = get_agent_audit_logger()
    entries = logger.query_file_modifications(Path(file_path), limit=limit)

    if output_json:
        click.echo(json.dumps(entries, indent=2))
    else:
        if not entries:
            click.echo(f"No modifications found for: {file_path}")
            return

        click.echo(f"Modification History for {file_path} ({len(entries)} entries)\n")

        for i, entry in enumerate(entries, 1):
            timestamp = entry.get("timestamp", "unknown")
            agent = entry.get("agent_name", "unknown")
            message = entry.get("message", "")

            click.echo(f"{i}. {agent}: {message}")
            click.echo(f"   {timestamp}")

            mods = entry.get("file_modifications", [])
            if mods:
                for mod in mods:
                    before_size = mod.get("size_bytes_before")
                    after_size = mod.get("size_bytes_after")
                    before_lines = mod.get("line_count_before")
                    after_lines = mod.get("line_count_after")

                    if before_size is not None and after_size is not None:
                        size_change = after_size - before_size
                        size_sign = "+" if size_change >= 0 else ""
                        click.echo(
                            f"   Size: {before_size}B → {after_size}B "
                            f"({size_sign}{size_change}B)"
                        )

                    if before_lines is not None and after_lines is not None:
                        line_change = after_lines - before_lines
                        line_sign = "+" if line_change >= 0 else ""
                        click.echo(
                            f"   Lines: {before_lines} → {after_lines} "
                            f"({line_sign}{line_change})"
                        )

                    # Show diff if requested
                    if diff and mod.get("diff_lines"):
                        click.echo("   Diff:")
                        for diff_line in mod["diff_lines"][:10]:  # Show first 10 lines
                            click.echo(f"     {diff_line}")
                        if len(mod["diff_lines"]) > 10:
                            click.echo(
                                f"     ... ({len(mod['diff_lines']) - 10} more lines)"
                            )

            click.echo()


@audit.command()
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def summary(output_json: bool):
    """Show summary statistics of audit log."""
    logger = get_agent_audit_logger()
    entries = logger.query_recent(limit=1000)

    if not entries:
        click.echo("No audit entries found.")
        return

    # Calculate statistics
    agents: dict[str, int] = {}
    actions: dict[str, int] = {}
    total_duration = 0
    success_count = 0
    fail_count = 0
    file_mods = 0
    fixes_count = 0

    for entry in entries:
        agent = entry.get("agent_name", "unknown")
        action = entry.get("action_type", "unknown")

        agents[agent] = agents.get(agent, 0) + 1
        actions[action] = actions.get(action, 0) + 1

        total_duration += entry.get("duration_ms", 0)

        if entry.get("success", True):
            success_count += 1
        else:
            fail_count += 1

        mods = entry.get("file_modifications", [])
        file_mods += len(mods)

        if action == "fix_applied":
            fixes_count += 1

    if output_json:
        stats = {
            "total_entries": len(entries),
            "success_rate": (
                f"{100 * success_count / len(entries):.1f}%" if entries else "0%"
            ),
            "total_duration_ms": total_duration,
            "file_modifications": file_mods,
            "fixes_applied": fixes_count,
            "by_agent": agents,
            "by_action": actions,
        }
        click.echo(json.dumps(stats, indent=2))
    else:
        click.echo("Audit Log Summary\n")
        click.echo(f"Total entries: {len(entries)}")
        click.echo(
            f"Success rate: {100 * success_count / len(entries):.1f}%"
            if entries
            else "N/A"
        )
        click.echo(f"Total duration: {total_duration}ms")
        click.echo(f"File modifications: {file_mods}")
        click.echo(f"Fixes applied: {fixes_count}\n")

        click.echo("By Agent:")
        for agent, count in sorted(agents.items(), key=lambda x: x[1], reverse=True):
            click.echo(f"  {agent}: {count}")

        click.echo("\nBy Action:")
        for action, count in sorted(actions.items(), key=lambda x: x[1], reverse=True):
            click.echo(f"  {action}: {count}")
