"""MCP tools for DevLoop findings management.

This module provides the MCP tools for interacting with DevLoop's findings:
- get_findings: Query findings with filters
- dismiss_finding: Mark a finding as seen/dismissed
- apply_fix: Apply an auto-fix for a specific finding
"""

import logging
from dataclasses import asdict, dataclass
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
