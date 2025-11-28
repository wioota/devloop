"""Integration commands for Amp/Claude Code."""

from dev_agents.core.auto_fix import apply_safe_fixes
from dev_agents.core.config import config
from dev_agents.core.context_store import context_store
from dev_agents.core.summary_generator import SummaryGenerator
from dev_agents.core.summary_formatter import SummaryFormatter
from typing import Any, Callable, Coroutine, Dict


async def check_agent_findings():
    """Check what findings agents have discovered."""
    findings = await context_store.get_findings()

    # Group findings by agent
    findings_by_agent = {}
    for finding in findings:
        agent = finding.agent
        if agent not in findings_by_agent:
            findings_by_agent[agent] = []
        findings_by_agent[agent].append(
            {
                "id": finding.id,
                "file": finding.file,
                "severity": finding.severity.value,
                "message": finding.message,
                "blocking": finding.blocking,
                "auto_fixable": finding.auto_fixable,
            }
        )

    summary = {
        "total_findings": len(findings),
        "findings_by_agent": {k: len(v) for k, v in findings_by_agent.items()},
        "blockers": len([f for f in findings if f.blocking]),
        "auto_fixable": len([f for f in findings if f.auto_fixable]),
    }

    return {
        "summary": summary,
        "findings": findings_by_agent,
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
                "safety_level": global_config.autonomous_fixes.safety_level,
            },
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
            "safety_level": global_config.autonomous_fixes.safety_level,
        },
    }


async def show_agent_status():
    """Show current status of background agents."""
    findings = await context_store.get_findings()

    # Group findings by agent
    findings_by_agent = {}
    for finding in findings:
        agent = finding.agent
        if agent not in findings_by_agent:
            findings_by_agent[agent] = []
        findings_by_agent[agent].append(finding)

    status = {
        "agent_activity": {},
        "total_findings": len(findings),
        "findings_by_agent": {k: len(v) for k, v in findings_by_agent.items()},
    }

    # Show agent activity
    for agent_type, agent_findings in findings_by_agent.items():
        if agent_findings:
            latest = max(agent_findings, key=lambda x: x.timestamp)
            status["agent_activity"][agent_type] = {
                "last_active": latest.timestamp,
                "last_message": latest.message,
                "total_findings": len(agent_findings),
                "blocking_issues": len([f for f in agent_findings if f.blocking]),
            }

    # Show recent findings (last 3 per agent)
    status["recent_findings"] = {}
    for agent_type, agent_findings in findings_by_agent.items():
        recent = sorted(agent_findings, key=lambda x: x.timestamp, reverse=True)[:3]
        status["recent_findings"][agent_type] = [
            {
                "timestamp": f.timestamp,
                "message": f.message,
                "severity": f.severity.value,
                "blocking": f.blocking,
            }
            for f in recent
        ]

    return status


async def generate_agent_summary(scope: str = "recent", filters: dict = None):
    """Generate agent summary report for Amp/Claude Code slash command."""
    if filters is None:
        filters = {}

    generator = SummaryGenerator(context_store)
    report = await generator.generate_summary(scope, filters)

    formatter = SummaryFormatter()
    return {
        "summary": formatter.format_json(report),
        "formatted_report": formatter.format_markdown(report),
        "quick_stats": {
            "total_findings": report.total_findings,
            "critical_issues": len(report.critical_issues),
            "auto_fixable": len(report.auto_fixable),
            "trend": report.trends.get("direction", "stable"),
        },
    }


# Amp subagent command mappings
AMP_COMMANDS: Dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {
    "check_agent_findings": check_agent_findings,
    "apply_autonomous_fixes": apply_autonomous_fixes,
    "show_agent_status": show_agent_status,
    "generate_agent_summary": generate_agent_summary,
}


from typing import Any, Callable, Coroutine

async def execute_amp_command(command: str, **kwargs) -> Any:
    """Execute an Amp integration command."""
    if command not in AMP_COMMANDS:
        raise ValueError(f"Unknown command: {command}")

    func: Callable[..., Coroutine[Any, Any, Any]] = AMP_COMMANDS[command]
    return await func(**kwargs)
