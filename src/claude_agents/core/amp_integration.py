"""Integration commands for Amp/Claude Code."""

import asyncio
from typing import Dict

from claude_agents.core.auto_fix import apply_safe_fixes
from claude_agents.core.config import config
from claude_agents.core.context_store import context_store


async def check_agent_findings():
    """Check what findings agents have discovered."""
    findings = context_store.get_findings()
    actionable = context_store.get_actionable_findings()

    summary = {
        "total_findings": sum(len(f) for f in findings.values()),
        "actionable_findings": sum(len(f) for f in actionable.values()),
        "findings_by_agent": {k: len(v) for k, v in findings.items()},
        "actionable_by_agent": {k: len(v) for k, v in actionable.items()},
    }

    return {
        "summary": summary,
        "all_findings": findings,
        "actionable_findings": actionable,
    }


async def apply_autonomous_fixes():
    """Apply safe fixes automatically."""
    global_config = config.get_global_config()

    if not global_config.autonomous_fixes.enabled:
        return {
            "message": "Autonomous fixes are disabled in configuration",
            "applied_fixes": {},
            "total_applied": 0,
            "config_status": {
                "enabled": False,
                "safety_level": global_config.autonomous_fixes.safety_level
            }
        }

    results = await apply_safe_fixes()

    total_applied = sum(results.values())
    message = f"Applied {total_applied} safe fixes"

    if results:
        details = []
        for agent_type, count in results.items():
            details.append(f"{count} {agent_type} fixes")
        message += f": {', '.join(details)}"
    else:
        message += " (no safe fixes found)"

    return {
        "message": message,
        "applied_fixes": results,
        "total_applied": total_applied,
        "config_status": {
            "enabled": True,
            "safety_level": global_config.autonomous_fixes.safety_level
        }
    }


async def show_agent_status():
    """Show current status of background agents."""
    findings = context_store.get_findings()
    actionable = context_store.get_actionable_findings()
    global_config = config.get_global_config()

    status = {
        "agent_activity": {},
        "pending_actions": {},
        "recent_findings": {},
        "autonomous_fixes_config": {
            "enabled": global_config.autonomous_fixes.enabled,
            "safety_level": global_config.autonomous_fixes.safety_level
        },
    }

    for agent_type, agent_findings in findings.items():
        if agent_findings:
            latest = max(agent_findings, key=lambda x: x.get("timestamp", ""))
            status["agent_activity"][agent_type] = {
                "last_active": latest.get("timestamp"),
                "last_message": latest.get("message"),
                "total_findings": len(agent_findings),
            }

    for agent_type, agent_findings in actionable.items():
        status["pending_actions"][agent_type] = len(agent_findings)

    # Show recent findings (last 5 per agent)
    for agent_type, agent_findings in findings.items():
        recent = sorted(agent_findings, key=lambda x: x.get("timestamp", ""), reverse=True)[:5]
        status["recent_findings"][agent_type] = [
            {
                "timestamp": f.get("timestamp"),
                "message": f.get("message"),
                "actionable": any(f.get("message", "") in af.get("message", "")
                                for af in actionable.get(agent_type, []))
            }
            for f in recent
        ]

    return status


# Amp subagent command mappings
AMP_COMMANDS = {
    "check_agent_findings": check_agent_findings,
    "apply_autonomous_fixes": apply_autonomous_fixes,
    "show_agent_status": show_agent_status,
}


async def execute_amp_command(command: str, **kwargs):
    """Execute an Amp integration command."""
    if command not in AMP_COMMANDS:
        raise ValueError(f"Unknown command: {command}")

    return await AMP_COMMANDS[command](**kwargs)
