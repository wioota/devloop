"""MCP resources for DevLoop.

This module provides MCP resources that expose DevLoop data in a read-only fashion:
- devloop://findings/immediate - Blocking issues
- devloop://findings/relevant - Issues for task completion
- devloop://findings/background - Low-priority issues
- devloop://findings/summary - Quick index with counts
- devloop://status - Server status
- devloop://agents - Available agents list
"""

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from mcp.types import AnyUrl, Resource

from devloop import __version__
from devloop.core.context_store import ContextStore, Tier

logger = logging.getLogger(__name__)


def list_resources() -> List[Resource]:
    """Return the list of available resources.

    Returns:
        List of MCP Resource objects
    """
    return [
        Resource(
            uri=AnyUrl("devloop://findings/immediate"),
            name="Immediate Findings",
            description="Blocking issues that require immediate attention",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("devloop://findings/relevant"),
            name="Relevant Findings",
            description="Issues to mention at task completion",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("devloop://findings/background"),
            name="Background Findings",
            description="Low-priority issues shown on request",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("devloop://findings/summary"),
            name="Findings Summary",
            description="Summary of all findings with counts by tier, severity, and category",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("devloop://status"),
            name="DevLoop Status",
            description="Overall DevLoop status including watch daemon state and last update",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("devloop://agents"),
            name="Available Agents",
            description="List of available DevLoop agents and their status",
            mimeType="application/json",
        ),
    ]


def _finding_to_dict(finding: Any) -> Dict[str, Any]:
    """Convert a Finding to a dictionary for JSON serialization."""
    data = asdict(finding)
    # Convert enums to their string values
    data["severity"] = finding.severity.value
    data["scope_type"] = finding.scope_type.value
    return data


async def get_findings_resource(context_store: ContextStore, tier: str) -> str:
    """Get findings for a specific tier as JSON.

    Args:
        context_store: The context store to read from
        tier: The tier to get (immediate, relevant, background, auto_fixed)

    Returns:
        JSON string of findings list

    Raises:
        ValueError: If the tier is invalid
    """
    try:
        tier_enum = Tier(tier.lower())
    except ValueError:
        raise ValueError(f"Invalid tier: {tier}")

    findings = await context_store.get_findings(tier=tier_enum)
    return json.dumps([_finding_to_dict(f) for f in findings], indent=2)


async def get_summary_resource(context_store: ContextStore) -> str:
    """Get findings summary with counts.

    Args:
        context_store: The context store to read from

    Returns:
        JSON string with summary data
    """
    # Get all findings from all tiers
    all_findings = []
    tier_counts: Dict[str, int] = {}

    for tier in Tier:
        findings = await context_store.get_findings(tier=tier)
        tier_counts[tier.value] = len(findings)
        all_findings.extend(findings)

    # Count by severity
    severity_counts: Dict[str, int] = {}
    for finding in all_findings:
        sev = finding.severity.value
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # Count by category
    category_counts: Dict[str, int] = {}
    for finding in all_findings:
        cat = finding.category
        category_counts[cat] = category_counts.get(cat, 0) + 1

    summary = {
        "total_findings": len(all_findings),
        "tiers": tier_counts,
        "severity_counts": severity_counts,
        "category_counts": category_counts,
    }

    return json.dumps(summary, indent=2)


async def get_status_resource(project_root: Path) -> str:
    """Get DevLoop status as JSON.

    Args:
        project_root: Path to the project root

    Returns:
        JSON string with status data
    """
    devloop_dir = project_root / ".devloop"
    initialized = devloop_dir.exists()

    # Check if watch daemon is running
    watch_running = False
    if initialized:
        pid_file = devloop_dir / "watch.pid"
        watch_running = pid_file.exists()

    # Get last update time
    last_update = None
    if initialized:
        last_update_file = devloop_dir / "context" / ".last_update"
        if last_update_file.exists():
            last_update = last_update_file.stat().st_mtime

    status = {
        "initialized": initialized,
        "watch_running": watch_running,
        "last_update": last_update,
        "server_version": __version__,
        "project_root": str(project_root),
    }

    return json.dumps(status, indent=2)


async def get_agents_resource(project_root: Path) -> str:
    """Get available agents as JSON.

    Args:
        project_root: Path to the project root

    Returns:
        JSON string with agents data
    """
    # List of available agents
    available_agents = [
        {
            "name": "formatter",
            "description": "Code formatter using Black",
            "command": "run_formatter",
        },
        {
            "name": "linter",
            "description": "Code linter using Ruff",
            "command": "run_linter",
        },
        {
            "name": "type_checker",
            "description": "Type checker using mypy",
            "command": "run_type_checker",
        },
        {
            "name": "test_runner",
            "description": "Test runner using pytest",
            "command": "run_tests",
        },
        {
            "name": "security_scanner",
            "description": "Security scanner for vulnerability detection",
            "command": "run_agent",
        },
        {
            "name": "performance_profiler",
            "description": "Performance profiler for code complexity",
            "command": "run_agent",
        },
    ]

    # Check config for enabled agents
    enabled_agents = []
    config_path = project_root / ".devloop" / "agents.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            agents_config = config.get("agents", {})
            for name, settings in agents_config.items():
                if settings.get("enabled", True):
                    enabled_agents.append(name)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Error reading config: {e}")

    result = {
        "available_agents": available_agents,
        "enabled_agents": enabled_agents,
    }

    return json.dumps(result, indent=2)


async def read_resource(uri: str, project_root: Path) -> str:
    """Read a resource by URI.

    This is the main entry point for reading resources. It dispatches to the
    appropriate resource handler based on the URI.

    Args:
        uri: The resource URI (e.g., "devloop://findings/immediate")
        project_root: Path to the project root

    Returns:
        JSON string with resource data

    Raises:
        ValueError: If the URI is unknown
    """
    # Initialize context store for findings resources
    context_dir = project_root / ".devloop" / "context"
    context_store = ContextStore(context_dir=context_dir, enable_path_validation=False)
    await context_store.initialize()

    if uri == "devloop://findings/immediate":
        return await get_findings_resource(context_store, "immediate")
    elif uri == "devloop://findings/relevant":
        return await get_findings_resource(context_store, "relevant")
    elif uri == "devloop://findings/background":
        return await get_findings_resource(context_store, "background")
    elif uri == "devloop://findings/summary":
        return await get_summary_resource(context_store)
    elif uri == "devloop://status":
        return await get_status_resource(project_root)
    elif uri == "devloop://agents":
        return await get_agents_resource(project_root)
    else:
        raise ValueError(f"Unknown resource URI: {uri}")
