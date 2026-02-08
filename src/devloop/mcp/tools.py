"""MCP tools for DevLoop findings management.

This module provides the MCP tools for interacting with DevLoop's findings:
- get_findings: Query findings with filters
- dismiss_finding: Mark a finding as seen/dismissed
- apply_fix: Apply an auto-fix for a specific finding

And verification tools for running code quality checks:
- run_formatter: Run black on specified files or project
- run_linter: Run ruff with optional --fix flag
- run_type_checker: Run mypy on specified paths
- run_tests: Run pytest with optional path/marker filters
"""

import asyncio
import logging
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from devloop.core.auto_fix import apply_fix as apply_fix_impl
from devloop.core.context_store import ContextStore, Finding, Severity, Tier

logger = logging.getLogger(__name__)


@dataclass
class FindingsFilter:
    """Filter parameters for querying findings.

    Attributes:
        file: Filter by file path (exact match)
        severity: Filter by severity level (error, warning, info, style)
        category: Filter by category (security, style, etc.)
        tier: Filter by tier (immediate, relevant, background, auto_fixed)
        limit: Maximum number of findings to return (default: 100)
    """

    file: Optional[str] = None
    severity: Optional[str] = None
    category: Optional[str] = None
    tier: Optional[str] = None
    limit: int = 100


def _finding_to_dict(finding: Finding) -> Dict[str, Any]:
    """Convert a Finding to a dictionary for JSON serialization.

    Args:
        finding: The Finding object to convert

    Returns:
        Dictionary representation of the finding
    """
    data = asdict(finding)
    # Convert enums to their string values
    data["severity"] = finding.severity.value
    data["scope_type"] = finding.scope_type.value
    return data


def _validate_paths(project_root: Path, paths: List[str]) -> List[str]:
    """Validate that all paths are within the project root.

    This prevents path traversal attacks by ensuring all provided paths
    resolve to locations within the project directory.

    Args:
        project_root: The project root directory
        paths: List of paths to validate

    Returns:
        List of validated paths (invalid paths are filtered out with warnings)
    """
    validated = []
    project_root_resolved = project_root.resolve()

    for p in paths:
        # Resolve the path relative to project root
        try:
            resolved = (project_root / p).resolve()
            # Check if resolved path is within project root
            if str(resolved).startswith(str(project_root_resolved)):
                validated.append(p)
            else:
                logger.warning(f"Path outside project root rejected: {p}")
        except (ValueError, OSError) as e:
            logger.warning(f"Invalid path rejected: {p} ({e})")

    return validated


async def get_findings(
    context_store: ContextStore,
    file: Optional[str] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    tier: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Get findings from the context store with optional filters.

    This is the MCP tool for querying findings. It supports filtering by
    file, severity, category, and tier, with a configurable result limit.

    Args:
        context_store: The context store to query
        file: Filter by file path (exact match)
        severity: Filter by severity level (error, warning, info, style)
        category: Filter by category name
        tier: Filter by tier (immediate, relevant, background, auto_fixed)
        limit: Maximum number of findings to return (default: 100)

    Returns:
        List of findings as dictionaries

    Example:
        >>> findings = await get_findings(store, severity="error", limit=10)
        >>> for f in findings:
        ...     print(f"{f['file']}:{f['line']} - {f['message']}")
    """
    # Convert tier string to Tier enum if provided
    tier_enum: Optional[Tier] = None
    if tier:
        try:
            tier_enum = Tier(tier.lower())
        except ValueError:
            logger.warning(f"Invalid tier value: {tier}")

    # Get findings from context store
    findings = await context_store.get_findings(tier=tier_enum, file_filter=file)

    # Apply additional filters (severity and category are not supported by
    # ContextStore.get_findings directly, so we filter here)
    if severity:
        try:
            severity_enum = Severity(severity.lower())
            findings = [f for f in findings if f.severity == severity_enum]
        except ValueError:
            logger.warning(f"Invalid severity value: {severity}")

    if category:
        findings = [f for f in findings if f.category == category]

    # Apply limit
    if limit and limit > 0:
        findings = findings[:limit]

    # Convert to dictionaries
    return [_finding_to_dict(f) for f in findings]


async def dismiss_finding(
    context_store: ContextStore,
    finding_id: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Dismiss a finding by marking it as seen.

    This marks the finding as seen/dismissed by the user. The finding remains
    in the store but will be deprioritized in future queries.

    Args:
        context_store: The context store containing the finding
        finding_id: The ID of the finding to dismiss
        reason: Optional reason for dismissal (for audit trail)

    Returns:
        Dict with success status and message

    Example:
        >>> result = await dismiss_finding(store, "abc123", reason="False positive")
        >>> if result["success"]:
        ...     print("Finding dismissed")
    """
    # Get all findings and find the one with matching ID
    findings = await context_store.get_findings()
    finding = next((f for f in findings if f.id == finding_id), None)

    if finding is None:
        logger.warning(f"Finding {finding_id} not found for dismissal")
        return {
            "success": False,
            "finding_id": finding_id,
            "message": f"Finding {finding_id} not found",
        }

    # Mark as seen
    finding.seen_by_user = True

    logger.info(f"Dismissed finding {finding_id}" + (f": {reason}" if reason else ""))

    return {
        "success": True,
        "finding_id": finding_id,
        "message": f"Finding {finding_id} dismissed",
        "reason": reason,
    }


async def apply_fix(
    context_store: ContextStore,
    finding_id: str,
) -> Dict[str, Any]:
    """Apply an auto-fix for a specific finding.

    This applies the automatic fix associated with a finding, if the finding
    is auto-fixable. The fix is applied using DevLoop's auto-fix system.

    Args:
        context_store: The context store containing the finding
        finding_id: The ID of the finding to fix

    Returns:
        Dict with success status and message

    Example:
        >>> result = await apply_fix(store, "abc123")
        >>> if result["success"]:
        ...     print("Fix applied successfully")
    """
    # Get all findings and find the one with matching ID
    findings = await context_store.get_findings()
    finding = next((f for f in findings if f.id == finding_id), None)

    if finding is None:
        logger.warning(f"Finding {finding_id} not found for apply_fix")
        return {
            "success": False,
            "finding_id": finding_id,
            "message": f"Finding {finding_id} not found",
        }

    if not finding.auto_fixable:
        logger.warning(f"Finding {finding_id} is not auto-fixable")
        return {
            "success": False,
            "finding_id": finding_id,
            "message": f"Finding {finding_id} is not auto-fixable",
        }

    # Apply the fix using the auto_fix module
    try:
        success = await apply_fix_impl(finding_id)

        if success:
            logger.info(f"Successfully applied fix for finding {finding_id}")
            return {
                "success": True,
                "finding_id": finding_id,
                "message": f"Fix applied successfully for finding {finding_id}",
            }
        else:
            logger.warning(f"Failed to apply fix for finding {finding_id}")
            return {
                "success": False,
                "finding_id": finding_id,
                "message": f"Fix application failed for finding {finding_id}",
            }

    except Exception as e:
        logger.error(f"Error applying fix for {finding_id}: {e}")
        return {
            "success": False,
            "finding_id": finding_id,
            "message": f"Error applying fix: {e}",
        }


# ============================================================================
# Verification Tools
# ============================================================================


async def run_formatter(
    project_root: Path,
    files: Optional[List[str]] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Run black formatter on specified files or project.

    This tool runs the black code formatter on the specified files,
    or on the entire src/ and tests/ directories if no files are specified.

    Args:
        project_root: Path to the project root directory
        files: Optional list of specific files to format
        timeout: Timeout in seconds (default: 30)

    Returns:
        Dict with success status, stdout, stderr, and returncode

    Example:
        >>> result = await run_formatter(Path("/project"), files=["src/main.py"])
        >>> if result["success"]:
        ...     print("Code formatted successfully")
    """
    cmd = ["black"]
    if files:
        validated_files = _validate_paths(project_root, files)
        if not validated_files:
            return {
                "success": False,
                "error": "No valid files to format (all paths were outside project root)",
            }
        cmd.extend(validated_files)
    else:
        cmd.extend(["src/", "tests/"])

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            logger.warning(f"Formatter timed out after {timeout}s")
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
            }

        return {
            "success": process.returncode == 0,
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "returncode": process.returncode,
        }

    except Exception as e:
        logger.error(f"Error running formatter: {e}")
        return {
            "success": False,
            "error": str(e),
        }


async def run_linter(
    project_root: Path,
    paths: Optional[List[str]] = None,
    fix: bool = False,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Run ruff linter on specified paths or project.

    This tool runs the ruff linter on the specified paths,
    or on the entire src/ and tests/ directories if no paths are specified.

    Args:
        project_root: Path to the project root directory
        paths: Optional list of specific paths to lint
        fix: If True, automatically fix fixable issues
        timeout: Timeout in seconds (default: 30)

    Returns:
        Dict with success status, stdout, stderr, and returncode

    Example:
        >>> result = await run_linter(Path("/project"), fix=True)
        >>> if result["success"]:
        ...     print("No linting issues found")
    """
    cmd = ["ruff", "check"]

    if fix:
        cmd.append("--fix")

    if paths:
        validated_paths = _validate_paths(project_root, paths)
        if not validated_paths:
            return {
                "success": False,
                "error": "No valid paths to lint (all paths were outside project root)",
            }
        cmd.extend(validated_paths)
    else:
        cmd.extend(["src/", "tests/"])

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            logger.warning(f"Linter timed out after {timeout}s")
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
            }

        return {
            "success": process.returncode == 0,
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "returncode": process.returncode,
        }

    except Exception as e:
        logger.error(f"Error running linter: {e}")
        return {
            "success": False,
            "error": str(e),
        }


async def run_type_checker(
    project_root: Path,
    paths: Optional[List[str]] = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Run mypy type checker on specified paths or project.

    This tool runs the mypy type checker on the specified paths,
    or on the src/ directory if no paths are specified.

    Args:
        project_root: Path to the project root directory
        paths: Optional list of specific paths to check
        timeout: Timeout in seconds (default: 60)

    Returns:
        Dict with success status, stdout, stderr, and returncode

    Example:
        >>> result = await run_type_checker(Path("/project"), paths=["src/"])
        >>> if result["success"]:
        ...     print("No type errors found")
    """
    cmd = ["mypy"]

    if paths:
        validated_paths = _validate_paths(project_root, paths)
        if not validated_paths:
            return {
                "success": False,
                "error": "No valid paths to check (all paths were outside project root)",
            }
        cmd.extend(validated_paths)
    else:
        cmd.append("src/")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            logger.warning(f"Type checker timed out after {timeout}s")
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
            }

        return {
            "success": process.returncode == 0,
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "returncode": process.returncode,
        }

    except Exception as e:
        logger.error(f"Error running type checker: {e}")
        return {
            "success": False,
            "error": str(e),
        }


async def run_tests(
    project_root: Path,
    path: Optional[str] = None,
    marker: Optional[str] = None,
    keyword: Optional[str] = None,
    verbose: bool = False,
    timeout: int = 300,
) -> Dict[str, Any]:
    """Run pytest tests with optional filters.

    This tool runs pytest with optional path, marker, and keyword filters.
    Tests have a longer default timeout (300s / 5 minutes) due to their
    potentially long running time.

    Args:
        project_root: Path to the project root directory
        path: Optional specific test path to run
        marker: Optional pytest marker to filter tests (e.g., "slow", "integration")
        keyword: Optional keyword expression to filter tests
        verbose: If True, run with verbose output (-v flag)
        timeout: Timeout in seconds (default: 300)

    Returns:
        Dict with success status, stdout, stderr, and returncode

    Example:
        >>> result = await run_tests(Path("/project"), marker="unit", verbose=True)
        >>> if result["success"]:
        ...     print("All tests passed")
    """
    cmd = ["pytest"]

    if verbose:
        cmd.append("-v")

    if marker:
        cmd.extend(["-m", marker])

    if keyword:
        cmd.extend(["-k", keyword])

    if path:
        validated_paths = _validate_paths(project_root, [path])
        if not validated_paths:
            return {
                "success": False,
                "error": f"Invalid test path (outside project root): {path}",
            }
        cmd.append(validated_paths[0])

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            logger.warning(f"Tests timed out after {timeout}s")
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
            }

        return {
            "success": process.returncode == 0,
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "returncode": process.returncode,
        }

    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# Agent Control Tools
# ============================================================================

# Valid agent names and their corresponding commands
AGENT_COMMANDS: Dict[str, List[str]] = {
    "formatter": ["black", "src/", "tests/"],
    "linter": ["ruff", "check", "src/", "tests/"],
    "type-checker": ["mypy", "src/"],
    "security-scanner": ["bandit", "-r", "src/", "-f", "json"],
    "test-runner": ["pytest", "-v"],
}


async def run_agent(
    project_root: Path,
    agent_name: str,
    timeout: int = 120,
) -> Dict[str, Any]:
    """Run a specific DevLoop agent.

    This tool triggers a specific agent to run on the project. Available agents:
    - formatter: Run black code formatter
    - linter: Run ruff linter
    - type-checker: Run mypy type checker
    - security-scanner: Run bandit security scanner
    - test-runner: Run pytest tests

    Args:
        project_root: Path to the project root directory
        agent_name: Name of the agent to run (formatter, linter, type-checker,
                   security-scanner, test-runner)
        timeout: Timeout in seconds (default: 120)

    Returns:
        Dict with success status, agent name, stdout, stderr, and returncode

    Example:
        >>> result = await run_agent(Path("/project"), "formatter")
        >>> if result["success"]:
        ...     print("Formatter completed successfully")
    """
    # Validate agent name
    if agent_name not in AGENT_COMMANDS:
        valid_agents = ", ".join(AGENT_COMMANDS.keys())
        logger.warning(f"Unknown agent: {agent_name}. Valid agents: {valid_agents}")
        return {
            "success": False,
            "agent": agent_name,
            "error": f"Unknown agent: {agent_name}. Valid agents: {valid_agents}",
        }

    cmd = AGENT_COMMANDS[agent_name]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            logger.warning(f"Agent {agent_name} timed out after {timeout}s")
            return {
                "success": False,
                "agent": agent_name,
                "error": f"Agent timed out after {timeout} seconds",
            }

        return {
            "success": process.returncode == 0,
            "agent": agent_name,
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "returncode": process.returncode,
        }

    except Exception as e:
        logger.error(f"Error running agent {agent_name}: {e}")
        return {
            "success": False,
            "agent": agent_name,
            "error": str(e),
        }


async def run_all_agents(
    project_root: Path,
    agents: Optional[List[str]] = None,
    stop_on_failure: bool = False,
    timeout: int = 300,
) -> Dict[str, Any]:
    """Run multiple DevLoop agents in sequence.

    This tool runs a full agent sweep on the project. By default, it runs
    formatter, linter, and type-checker. Optionally, you can specify which
    agents to run and whether to stop on first failure.

    Args:
        project_root: Path to the project root directory
        agents: Optional list of agent names to run. Defaults to
               ["formatter", "linter", "type-checker"]
        stop_on_failure: If True, stop running agents after first failure
        timeout: Timeout per agent in seconds (default: 300)

    Returns:
        Dict with overall success status, list of agents run, and individual results

    Example:
        >>> result = await run_all_agents(Path("/project"))
        >>> if result["success"]:
        ...     print("All agents completed successfully")
    """
    # Default agents to run
    if agents is None:
        agents = ["formatter", "linter", "type-checker"]

    # Filter to valid agents only
    valid_agents = [a for a in agents if a in AGENT_COMMANDS]
    invalid_agents = [a for a in agents if a not in AGENT_COMMANDS]

    if invalid_agents:
        logger.warning(f"Skipping unknown agents: {invalid_agents}")

    results: List[Dict[str, Any]] = []
    all_success = True

    for agent_name in valid_agents:
        result = await run_agent(project_root, agent_name, timeout=timeout)
        results.append(result)

        if not result["success"]:
            all_success = False
            if stop_on_failure:
                logger.info(
                    f"Stopping after {agent_name} failure (stop_on_failure=True)"
                )
                break

    return {
        "success": all_success,
        "agents_run": [r["agent"] for r in results],
        "results": results,
        "skipped_invalid": invalid_agents if invalid_agents else None,
    }


# ============================================================================
# Configuration and Status Tools
# ============================================================================


async def get_config(
    project_root: Path,
) -> Dict[str, Any]:
    """Get DevLoop configuration.

    This tool retrieves the current DevLoop configuration for the project,
    including enabled agents, global settings, and resource limits.

    Args:
        project_root: Path to the project root directory

    Returns:
        Dict with configuration information including:
        - project_root: Path to the project
        - config: The full configuration dictionary
        - enabled_agents: List of enabled agent names
        - global_settings: Summary of global configuration

    Example:
        >>> config = await get_config(Path("/project"))
        >>> print(f"Mode: {config['global_settings']['mode']}")
        >>> print(f"Enabled agents: {config['enabled_agents']}")
    """
    from devloop.core.config import Config

    try:
        config_path = project_root / ".devloop" / "agents.json"
        config_manager = Config(str(config_path))
        config_data = config_manager.load(validate=False, migrate=False)

        # Extract enabled agents
        agents = config_data.get("agents", {})
        enabled_agents = [
            name for name, settings in agents.items() if settings.get("enabled", False)
        ]

        # Extract global settings summary
        global_config = config_data.get("global", {})
        global_settings = {
            "mode": global_config.get("mode", "report-only"),
            "max_concurrent_agents": global_config.get("maxConcurrentAgents", 5),
            "notification_level": global_config.get("notificationLevel", "summary"),
            "context_store_enabled": global_config.get("contextStore", {}).get(
                "enabled", True
            ),
            "autonomous_fixes_enabled": global_config.get("autonomousFixes", {}).get(
                "enabled", False
            ),
        }

        return {
            "success": True,
            "project_root": str(project_root),
            "config": config_data,
            "enabled_agents": enabled_agents,
            "global_settings": global_settings,
        }

    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return {
            "success": False,
            "project_root": str(project_root),
            "error": str(e),
        }


async def get_status(
    project_root: Path,
) -> Dict[str, Any]:
    """Get DevLoop status.

    This tool retrieves the overall status of DevLoop for the project,
    including whether the watch daemon is running, last update time,
    and finding counts by severity.

    Args:
        project_root: Path to the project root directory

    Returns:
        Dict with status information including:
        - project_root: Path to the project
        - initialized: Whether DevLoop is initialized (has .devloop dir)
        - watch_running: Whether the watch daemon is running
        - last_update: Timestamp of last context update (or None)
        - finding_counts: Dict of finding counts by severity

    Example:
        >>> status = await get_status(Path("/project"))
        >>> if status["watch_running"]:
        ...     print("DevLoop is watching for changes")
        >>> print(f"Errors: {status['finding_counts'].get('error', 0)}")
    """
    devloop_dir = project_root / ".devloop"

    # Check if DevLoop is initialized
    initialized = devloop_dir.exists()

    if not initialized:
        return {
            "success": True,
            "project_root": str(project_root),
            "initialized": False,
            "watch_running": False,
            "last_update": None,
            "finding_counts": {},
        }

    # Check if watch daemon is running
    pid_file = devloop_dir / "watch.pid"
    watch_running = pid_file.exists()

    # Get last update time
    last_update_file = devloop_dir / "context" / ".last_update"
    last_update: Optional[float] = None
    if last_update_file.exists():
        last_update = last_update_file.stat().st_mtime

    # Get finding counts by reading tier JSON files directly
    # (ContextStore keeps findings in memory, so we read from disk for status)
    finding_counts: Dict[str, int] = {}
    try:
        import json as json_module

        context_dir = devloop_dir / "context"
        if context_dir.exists():
            # Read from all tier files
            tier_files = [
                "immediate.json",
                "relevant.json",
                "background.json",
                "auto_fixed.json",
            ]
            for tier_file in tier_files:
                tier_path = context_dir / tier_file
                if tier_path.exists():
                    try:
                        tier_data = json_module.loads(tier_path.read_text())
                        for finding_data in tier_data.get("findings", []):
                            severity_name = finding_data.get("severity", "unknown")
                            finding_counts[severity_name] = (
                                finding_counts.get(severity_name, 0) + 1
                            )
                    except (json_module.JSONDecodeError, OSError) as e:
                        logger.warning(f"Error reading {tier_file}: {e}")

    except Exception as e:
        logger.warning(f"Error getting finding counts: {e}")

    return {
        "success": True,
        "project_root": str(project_root),
        "initialized": initialized,
        "watch_running": watch_running,
        "last_update": last_update,
        "finding_counts": finding_counts,
    }


async def get_agent_status(
    project_root: Path,
    agent_name: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Get agent run history and status.

    This tool retrieves the run history for DevLoop agents. It reads from
    the event store to show recent agent executions, their success/failure
    status, duration, and any errors.

    Args:
        project_root: Path to the project root directory
        agent_name: Optional specific agent name to filter by
        limit: Maximum number of history entries per agent (default: 10)

    Returns:
        Dict with agent status information including run history

    Example:
        >>> status = await get_agent_status(Path("/project"))
        >>> for agent, info in status["agents"].items():
        ...     print(f"{agent}: {info['last_run_status']}")
    """
    from devloop.core.event_store import EventStore

    # Initialize event store
    db_path = project_root / ".devloop" / "events.db"

    if not db_path.exists():
        return {
            "success": True,
            "agents": {},
            "message": "No agent history found. Run agents first.",
        }

    event_store = EventStore(db_path)

    try:
        await event_store.initialize()

        # Query for agent completion events
        if agent_name:
            event_type = f"agent:{agent_name}:completed"
        else:
            event_type = None  # Will get all events

        events = await event_store.get_events(
            event_type=event_type,
            source=agent_name,
            limit=limit * 10 if not agent_name else limit,  # Get more if filtering
        )

        # Group events by agent
        agents_status: Dict[str, Dict[str, Any]] = {}

        for event in events:
            # Only process agent completion events
            if not event.type.startswith("agent:") or not event.type.endswith(
                ":completed"
            ):
                continue

            payload = event.payload
            event_agent_name = payload.get("agent_name", "unknown")

            # Skip if filtering by agent and doesn't match
            if agent_name and event_agent_name != agent_name:
                continue

            if event_agent_name not in agents_status:
                agents_status[event_agent_name] = {
                    "agent": event_agent_name,
                    "last_run": None,
                    "last_run_status": None,
                    "total_runs": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "average_duration": 0.0,
                    "history": [],
                }

            agent_info = agents_status[event_agent_name]
            agent_info["total_runs"] += 1

            if payload.get("success"):
                agent_info["success_count"] += 1
            else:
                agent_info["failure_count"] += 1

            # Update last run if this is more recent
            if (
                agent_info["last_run"] is None
                or event.timestamp > agent_info["last_run"]
            ):
                agent_info["last_run"] = event.timestamp
                agent_info["last_run_status"] = (
                    "success" if payload.get("success") else "failure"
                )

            # Add to history (limited)
            if len(agent_info["history"]) < limit:
                agent_info["history"].append(
                    {
                        "timestamp": event.timestamp,
                        "success": payload.get("success", False),
                        "duration": payload.get("duration", 0),
                        "message": payload.get("message", ""),
                        "error": payload.get("error"),
                    }
                )

        # Calculate average durations
        for agent_info in agents_status.values():
            if agent_info["history"]:
                total_duration = sum(h["duration"] for h in agent_info["history"])
                agent_info["average_duration"] = total_duration / len(
                    agent_info["history"]
                )

        await event_store.close()

        return {
            "success": True,
            "agents": agents_status,
            "summary": {
                "total_agents": len(agents_status),
                "agents_with_failures": sum(
                    1 for a in agents_status.values() if a["failure_count"] > 0
                ),
            },
        }

    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        return {
            "success": False,
            "agents": {},
            "error": str(e),
        }
