"""Beads integration for auto-creating issues from detected patterns.

This module provides automatic issue creation in Beads based on patterns
detected by the self-improvement agent. It creates properly formatted issues
with thread references and discovered-from dependencies.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..core.pattern_detector import DetectedPattern, PatternDetector

logger = logging.getLogger(__name__)


@dataclass
class BeadsIssue:
    """Represents a created Beads issue."""

    issue_id: str
    title: str
    description: str
    priority: int
    issue_type: str
    dependencies: list[str]


class BeadsIntegration:
    """Integrates with Beads to auto-create issues from detected patterns."""

    def __init__(
        self,
        devloop_dir: Optional[Path] = None,
        parent_issue: str = "claude-agents-zjf",
        dry_run: bool = False,
    ):
        """Initialize Beads integration.

        Args:
            devloop_dir: Path to .devloop directory (defaults to ~/.devloop)
            parent_issue: Parent issue ID for discovered-from links
            dry_run: If True, don't actually create issues (for testing)
        """
        self.pattern_detector = PatternDetector(devloop_dir)
        self.parent_issue = parent_issue
        self.dry_run = dry_run

    def create_issue_from_pattern(
        self,
        pattern: DetectedPattern,
        additional_deps: Optional[list[str]] = None,
    ) -> Optional[BeadsIssue]:
        """Create a Beads issue from a detected pattern.

        Args:
            pattern: The detected pattern to create an issue for
            additional_deps: Additional dependency strings (e.g., ['blocks:bd-123'])

        Returns:
            BeadsIssue if created successfully, None otherwise
        """
        # Format issue title
        title = f"Pattern: {pattern.pattern_name}"

        # Format description with thread references
        description = self._format_description(pattern)

        # Determine priority from severity
        priority = self._severity_to_priority(pattern.severity)

        # Build dependency list
        deps = [f"discovered-from:{self.parent_issue}"]
        if additional_deps:
            deps.extend(additional_deps)

        # Create the issue
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create issue: {title}")
            logger.info(f"[DRY RUN] Description: {description[:100]}...")
            logger.info(f"[DRY RUN] Priority: {priority}, Deps: {deps}")
            return BeadsIssue(
                issue_id="bd-dry-run",
                title=title,
                description=description,
                priority=priority,
                issue_type="task",
                dependencies=deps,
            )

        try:
            result = self._run_bd_create(
                title=title,
                description=description,
                priority=priority,
                issue_type="task",
                deps=deps,
            )

            if result:
                logger.info(
                    f"Created Beads issue {result.issue_id} for pattern {pattern.pattern_name}"
                )
                return result
            else:
                logger.error(
                    f"Failed to create issue for pattern {pattern.pattern_name}"
                )
                return None

        except Exception as e:
            logger.error(
                f"Error creating Beads issue for pattern {pattern.pattern_name}: {e}"
            )
            return None

    def auto_create_from_high_confidence_patterns(
        self,
        confidence_threshold: float = 0.7,
        limit: int = 10,
    ) -> list[BeadsIssue]:
        """Automatically create issues from high-confidence patterns.

        Args:
            confidence_threshold: Minimum confidence score (0.0 to 1.0)
            limit: Maximum number of issues to create

        Returns:
            List of created BeadsIssue objects
        """
        # Get high-confidence patterns
        patterns = self.pattern_detector.get_high_confidence_patterns(
            confidence_threshold=confidence_threshold,
            limit=limit,
        )

        if not patterns:
            logger.info("No high-confidence patterns found for auto-issue creation")
            return []

        logger.info(f"Found {len(patterns)} high-confidence patterns")

        # Create issues for each pattern
        created_issues = []
        for pattern in patterns:
            # Skip if already acknowledged
            if pattern.acknowledged:
                logger.debug(f"Skipping acknowledged pattern: {pattern.pattern_name}")
                continue

            issue = self.create_issue_from_pattern(pattern)
            if issue:
                created_issues.append(issue)

        logger.info(f"Created {len(created_issues)} Beads issues from patterns")
        return created_issues

    def _format_description(self, pattern: DetectedPattern) -> str:
        """Format pattern data into a Beads issue description.

        Args:
            pattern: The detected pattern

        Returns:
            Formatted markdown description
        """
        lines = []

        # Header
        lines.append(f"## Pattern Detected: {pattern.pattern_name}")
        lines.append("")

        # Message
        lines.append(f"**Message**: {pattern.message}")
        lines.append("")

        # Severity and confidence
        lines.append(f"**Severity**: {pattern.severity}")
        lines.append(f"**Confidence**: {pattern.confidence:.2%}")
        lines.append("")

        # Thread references
        if pattern.affected_threads:
            lines.append("**Affected Threads**:")
            for thread_id in pattern.affected_threads:
                lines.append(f"- {thread_id}")
            lines.append("")

        # Evidence
        if pattern.evidence:
            lines.append("**Evidence**:")
            lines.append("```json")
            lines.append(json.dumps(pattern.evidence, indent=2))
            lines.append("```")
            lines.append("")

        # Recommendation
        if pattern.recommendation:
            lines.append("**Recommendation**:")
            lines.append(pattern.recommendation)
            lines.append("")

        # Metadata
        lines.append("---")
        lines.append(f"*Auto-generated from pattern detection at {pattern.timestamp}*")

        return "\n".join(lines)

    def _severity_to_priority(self, severity: str) -> int:
        """Convert severity level to Beads priority.

        Args:
            severity: Severity level (info, warning, error)

        Returns:
            Priority number (0-4, where 0 is highest)
        """
        severity_map = {
            "error": 1,  # High priority
            "warning": 2,  # Medium priority
            "info": 3,  # Low priority
        }
        return severity_map.get(severity.lower(), 2)

    def _run_bd_create(
        self,
        title: str,
        description: str,
        priority: int,
        issue_type: str,
        deps: list[str],
    ) -> Optional[BeadsIssue]:
        """Run bd create command and parse result.

        Args:
            title: Issue title
            description: Issue description
            priority: Priority (0-4)
            issue_type: Issue type (task, bug, feature, etc.)
            deps: List of dependency strings

        Returns:
            BeadsIssue if successful, None otherwise
        """
        # Build command
        cmd = [
            "bd",
            "create",
            title,
            "--description",
            description,
            "--priority",
            str(priority),
            "--type",
            issue_type,
            "--json",
        ]

        # Add dependencies
        if deps:
            cmd.extend(["--deps", ",".join(deps)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse JSON output
            output = json.loads(result.stdout)

            # Extract issue ID (format varies by bd version)
            issue_id = output.get("id") or output.get("issue_id") or "unknown"

            return BeadsIssue(
                issue_id=issue_id,
                title=title,
                description=description,
                priority=priority,
                issue_type=issue_type,
                dependencies=deps,
            )

        except subprocess.CalledProcessError as e:
            logger.error(f"bd create failed: {e.stderr}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse bd create output: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error running bd create: {e}")
            return None


# Convenience function for direct usage
def create_issues_from_patterns(
    confidence_threshold: float = 0.7,
    limit: int = 10,
    parent_issue: str = "claude-agents-zjf",
    dry_run: bool = False,
) -> list[BeadsIssue]:
    """Convenience function to create issues from high-confidence patterns.

    Args:
        confidence_threshold: Minimum confidence score (0.0 to 1.0)
        limit: Maximum number of issues to create
        parent_issue: Parent issue ID for discovered-from links
        dry_run: If True, don't actually create issues

    Returns:
        List of created BeadsIssue objects
    """
    integration = BeadsIntegration(parent_issue=parent_issue, dry_run=dry_run)
    return integration.auto_create_from_high_confidence_patterns(
        confidence_threshold=confidence_threshold,
        limit=limit,
    )
