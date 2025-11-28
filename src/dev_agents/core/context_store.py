"""Context store for sharing agent findings with coding agents (Claude Code)."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Finding severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    STYLE = "style"


class ScopeType(str, Enum):
    """Finding scope types."""

    CURRENT_FILE = "current_file"
    RELATED_FILES = "related_files"
    PROJECT_WIDE = "project_wide"


class Tier(str, Enum):
    """Context tier for progressive disclosure."""

    IMMEDIATE = "immediate"  # Show now, blocking issues
    RELEVANT = "relevant"  # Mention at task completion
    BACKGROUND = "background"  # Show only on request
    AUTO_FIXED = "auto_fixed"  # Already fixed silently


@dataclass
class Finding:
    """A single finding from an agent."""

    id: str
    agent: str
    timestamp: str
    file: str
    line: int | None = None
    column: int | None = None

    severity: Severity = Severity.INFO
    blocking: bool = False
    category: str = "general"

    message: str = ""
    detail: str = ""
    suggestion: str = ""

    auto_fixable: bool = False
    fix_command: str | None = None

    scope_type: ScopeType = ScopeType.CURRENT_FILE
    caused_by_recent_change: bool = False
    is_new: bool = True

    relevance_score: float = 0.5
    disclosure_level: int = 0
    seen_by_user: bool = False

    workflow_hints: Dict[str, bool] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate Finding parameters."""
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("id must be a non-empty string")

        if not isinstance(self.agent, str) or not self.agent:
            raise ValueError("agent must be a non-empty string")

        if not isinstance(self.file, str) or not self.file:
            raise ValueError("file must be a non-empty string")

        # Convert string enums to proper enums
        if isinstance(self.severity, str):
            self.severity = Severity(self.severity)

        if isinstance(self.scope_type, str):
            self.scope_type = ScopeType(self.scope_type)

        # Validate numeric ranges
        if self.line is not None and self.line < 0:
            raise ValueError(f"line must be non-negative, got {self.line}")

        if self.column is not None and self.column < 0:
            raise ValueError(f"column must be non-negative, got {self.column}")

        if not 0.0 <= self.relevance_score <= 1.0:
            raise ValueError(
                f"relevance_score must be between 0.0 and 1.0, got {self.relevance_score}"
            )

        if self.disclosure_level < 0:
            raise ValueError(
                f"disclosure_level must be non-negative, got {self.disclosure_level}"
            )


@dataclass
class UserContext:
    """Context about user's current development state."""

    currently_editing: List[str] = field(default_factory=list)
    recently_modified: List[str] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)
    phase: Literal["active_coding", "pre_commit", "reviewing"] = "active_coding"
    explicit_request: str | None = None

    def matches_request(self, category: str) -> bool:
        """Check if category matches user's explicit request."""
        if not self.explicit_request:
            return False
        return category.lower() in self.explicit_request.lower()


@dataclass
class ContextIndex:
    """Summary index for quick LLM consumption."""

    last_updated: str
    check_now: Dict[str, Any]
    mention_if_relevant: Dict[str, Any]
    deferred: Dict[str, Any]
    auto_fixed: Dict[str, Any] = field(default_factory=dict)


class ContextStore:
    """
    Manages context storage for agent findings.

    Organizes findings into tiers for progressive disclosure:
    - immediate: Blocking issues, show immediately
    - relevant: Mention at task completion
    - background: Show only on explicit request
    - auto_fixed: Log of silent fixes
    """

    def __init__(self, context_dir: Path | str | None = None):
        """
        Initialize context store.

        Args:
            context_dir: Directory for context files. Defaults to .claude/context
        """
        if context_dir is None:
            context_dir = Path.cwd() / ".claude" / "context"
        self.context_dir = Path(context_dir)
        self._lock = asyncio.Lock()
        self._findings: Dict[Tier, List[Finding]] = {
            Tier.IMMEDIATE: [],
            Tier.RELEVANT: [],
            Tier.BACKGROUND: [],
            Tier.AUTO_FIXED: [],
        }
        logger.info(f"Context store initialized at {self.context_dir}")

    async def initialize(self) -> None:
        """Create context directory structure if it doesn't exist."""
        try:
            self.context_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Context directory ready: {self.context_dir}")
        except Exception as e:
            logger.error(f"Failed to create context directory: {e}")
            raise

    async def add_finding(
        self,
        finding: Finding | Dict[str, Any],
        user_context: UserContext | None = None,
    ) -> None:
        """
        Add a finding to the context store.

        Args:
            finding: Finding object or dict with finding data
            user_context: Optional user context for relevance scoring
        """
        # Convert dict to Finding if needed
        if isinstance(finding, dict):
            finding = Finding(**finding)

        # Compute relevance score
        if user_context:
            finding.relevance_score = self.compute_relevance(finding, user_context)

        # Assign to tier
        tier = self.assign_tier(finding)

        async with self._lock:
            self._findings[tier].append(finding)
            await self._write_tier(tier)
            await self._update_index()

        logger.debug(
            f"Added finding {finding.id} to {tier.value} (relevance: {finding.relevance_score:.2f})"
        )

    def compute_relevance(self, finding: Finding, user_context: UserContext) -> float:
        """
        Compute relevance score for a finding.

        Returns score between 0.0 and 1.0:
        - 0.0 - 0.3: background
        - 0.4 - 0.7: relevant
        - 0.8 - 1.0: immediate
        """
        score = 0.0

        # File scope (max 0.5)
        if finding.file in user_context.currently_editing:
            score += 0.5
        elif finding.file in user_context.recently_modified:
            score += 0.3
        elif finding.file in user_context.related_files:
            score += 0.2

        # Severity (max 0.4)
        if finding.blocking:
            score += 0.4
        elif finding.severity == Severity.ERROR:
            score += 0.3
        elif finding.severity == Severity.WARNING:
            score += 0.15
        elif finding.severity == Severity.INFO:
            score += 0.05

        # Freshness (max 0.3)
        if finding.is_new and finding.caused_by_recent_change:
            score += 0.3
        elif finding.is_new:
            score += 0.15

        # User intent (max 0.5, can override)
        if user_context.matches_request(finding.category):
            score += 0.5

        # Workflow phase adjustments
        if user_context.phase == "pre_commit":
            score += 0.2
        elif user_context.phase == "active_coding":
            score -= 0.2

        return min(score, 1.0)

    def assign_tier(self, finding: Finding) -> Tier:
        """
        Assign finding to a tier based on relevance and properties.

        Args:
            finding: Finding to assign

        Returns:
            Tier assignment
        """
        # Blockers always immediate
        if finding.blocking:
            return Tier.IMMEDIATE

        # Auto-fixable style issues
        if (
            finding.auto_fixable
            and finding.severity == Severity.STYLE
            and finding.relevance_score < 0.5
        ):
            return Tier.AUTO_FIXED

        # Score-based assignment
        if finding.relevance_score >= 0.8:
            return Tier.IMMEDIATE
        elif finding.relevance_score >= 0.4:
            return Tier.RELEVANT
        else:
            return Tier.BACKGROUND

    async def get_findings(
        self, tier: Tier | None = None, file_filter: str | None = None
    ) -> List[Finding]:
        """
        Get findings from the store.

        Args:
            tier: Optional tier filter
            file_filter: Optional file path filter

        Returns:
            List of findings matching filters
        """
        async with self._lock:
            if tier:
                findings = self._findings[tier].copy()
            else:
                findings = []
                for tier_findings in self._findings.values():
                    findings.extend(tier_findings)

            if file_filter:
                findings = [f for f in findings if f.file == file_filter]

            return findings

    async def clear_findings(
        self, tier: Tier | None = None, file_filter: str | None = None
    ) -> int:
        """
        Clear findings from the store.

        Args:
            tier: Optional tier filter
            file_filter: Optional file path filter

        Returns:
            Number of findings cleared
        """
        count = 0
        async with self._lock:
            if tier:
                tiers_to_clear = [tier]
            else:
                tiers_to_clear = list(Tier)

            for t in tiers_to_clear:
                if file_filter:
                    original_count = len(self._findings[t])
                    self._findings[t] = [
                        f for f in self._findings[t] if f.file != file_filter
                    ]
                    count += original_count - len(self._findings[t])
                else:
                    count += len(self._findings[t])
                    self._findings[t] = []

                await self._write_tier(t)

            await self._update_index()

        logger.info(f"Cleared {count} finding(s)")
        return count

    async def _write_tier(self, tier: Tier) -> None:
        """Write a tier's findings to disk."""
        tier_file = self.context_dir / f"{tier.value}.json"

        try:
            # Convert findings to dict
            findings_data = {
                "tier": tier.value,
                "count": len(self._findings[tier]),
                "findings": [
                    {
                        **asdict(f),
                        "severity": f.severity.value,
                        "scope_type": f.scope_type.value,
                    }
                    for f in self._findings[tier]
                ],
            }

            # Write atomically (write to temp, then rename)
            temp_file = tier_file.with_suffix(".tmp")
            temp_file.write_text(json.dumps(findings_data, indent=2))
            temp_file.replace(tier_file)

            logger.debug(f"Wrote {len(self._findings[tier])} findings to {tier_file}")

        except Exception as e:
            logger.error(f"Failed to write tier {tier.value}: {e}")
            raise

    async def _update_index(self) -> None:
        """Update the index file for quick LLM consumption."""
        index_file = self.context_dir / "index.json"

        try:
            # Gather summaries
            immediate = self._findings[Tier.IMMEDIATE]
            relevant = self._findings[Tier.RELEVANT]
            background = self._findings[Tier.BACKGROUND]
            auto_fixed = self._findings[Tier.AUTO_FIXED]

            # Build index
            index = {
                "last_updated": datetime.now(UTC).isoformat() + "Z",
                "check_now": {
                    "count": len(immediate),
                    "severity_breakdown": self._severity_breakdown(immediate),
                    "files": list(set(f.file for f in immediate)),
                    "preview": self._generate_preview(immediate),
                },
                "mention_if_relevant": {
                    "count": len(relevant),
                    "categories": self._category_breakdown(relevant),
                    "summary": self._generate_summary(relevant),
                },
                "deferred": {
                    "count": len(background),
                    "summary": f"{len(background)} background items",
                },
                "auto_fixed": {
                    "count": len(auto_fixed),
                    "summary": f"{len(auto_fixed)} items auto-fixed",
                },
            }

            # Write atomically
            temp_file = index_file.with_suffix(".tmp")
            temp_file.write_text(json.dumps(index, indent=2))
            temp_file.replace(index_file)

            logger.debug(f"Updated index: {index_file}")

        except Exception as e:
            logger.error(f"Failed to update index: {e}")
            raise

    def _severity_breakdown(self, findings: List[Finding]) -> Dict[str, int]:
        """Count findings by severity."""
        breakdown: Dict[str, int] = {}
        for f in findings:
            severity = f.severity.value
            breakdown[severity] = breakdown.get(severity, 0) + 1
        return breakdown

    def _category_breakdown(self, findings: List[Finding]) -> Dict[str, int]:
        """Count findings by category."""
        breakdown: Dict[str, int] = {}
        for f in findings:
            breakdown[f.category] = breakdown.get(f.category, 0) + 1
        return breakdown

    def _generate_preview(self, findings: List[Finding]) -> str:
        """Generate a brief preview of findings."""
        if not findings:
            return "No immediate issues"

        if len(findings) == 1:
            f = findings[0]
            return f"{f.severity.value.title()} in {f.file}:{f.line or '?'}"

        # Multiple findings
        severity_counts = self._severity_breakdown(findings)
        parts = [f"{count} {sev}" for sev, count in severity_counts.items()]
        return ", ".join(parts)

    def _generate_summary(self, findings: List[Finding]) -> str:
        """Generate a summary of findings."""
        if not findings:
            return "No relevant issues"

        category_counts = self._category_breakdown(findings)
        parts = [
            f"{count} {cat.replace('_', ' ')}" for cat, count in category_counts.items()
        ]
        return ", ".join(parts)

    async def read_index(self) -> Dict[str, Any]:
        """
        Read the index file.

        Returns:
            Index data as dict
        """
        index_file = self.context_dir / "index.json"

        try:
            if not index_file.exists():
                return {
                    "last_updated": datetime.now(UTC).isoformat() + "Z",
                    "check_now": {"count": 0, "preview": "No immediate issues"},
                    "mention_if_relevant": {
                        "count": 0,
                        "summary": "No relevant issues",
                    },
                    "deferred": {"count": 0, "summary": "No background items"},
                    "auto_fixed": {"count": 0, "summary": "No auto-fixed items"},
                }

            data = json.loads(index_file.read_text())
            return data

        except Exception as e:
            logger.error(f"Failed to read index: {e}")
            raise

    async def load_from_disk(self) -> None:
        """Load all findings from disk into memory."""
        async with self._lock:
            for tier in Tier:
                tier_file = self.context_dir / f"{tier.value}.json"

                if not tier_file.exists():
                    continue

                try:
                    data = json.loads(tier_file.read_text())
                    findings = []

                    for f_data in data.get("findings", []):
                        # Convert severity and scope_type back to enums
                        if "severity" in f_data:
                            f_data["severity"] = Severity(f_data["severity"])
                        if "scope_type" in f_data:
                            f_data["scope_type"] = ScopeType(f_data["scope_type"])

                        findings.append(Finding(**f_data))

                    self._findings[tier] = findings
                    logger.info(
                        f"Loaded {len(findings)} findings from {tier.value}.json"
                    )

                except Exception as e:
                    logger.error(f"Failed to load {tier_file}: {e}")
                    # Continue with other tiers


# Global instance
context_store = ContextStore()
