"""Summary generator for dev-agent findings."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Tuple

from .context_store import Finding, Severity, Tier, context_store

logger = logging.getLogger(__name__)


@dataclass
class AgentSummary:
    """Summary for a specific agent."""

    agent_name: str
    finding_count: int
    severity_breakdown: Dict[str, int]
    top_issues: List[Finding]
    improvement_trend: str  # "improving", "worsening", "stable"


@dataclass
class SummaryReport:
    """Comprehensive summary report."""

    scope: str
    time_range: Tuple[datetime, datetime]
    total_findings: int

    # Breakdowns
    by_agent: Dict[str, AgentSummary]
    by_severity: Dict[str, int]
    by_category: Dict[str, int]

    # Trends
    trends: Dict[str, Any]

    # Priority items
    critical_issues: List[Finding]
    auto_fixable: List[Finding]

    # Insights
    insights: List[str]


class SummaryGenerator:
    """Generate intelligent summaries of dev-agent findings."""

    def __init__(self, context_store_instance=None):
        """Initialize summary generator.

        Args:
            context_store_instance: Context store to use (defaults to global)
        """
        self.context_store = context_store_instance or context_store

    async def generate_summary(
        self, scope: str = "recent", filters: Dict[str, Any] = None
    ) -> SummaryReport:
        """Generate intelligent summary of findings.

        Args:
            scope: Time scope ("recent", "today", "session", "all")
            filters: Optional filters (agent, severity, category)

        Returns:
            SummaryReport with findings analysis
        """
        filters = filters or {}

        # Get time range for scope
        time_range = self._get_time_range(scope)

        # Get all findings within time range
        findings = await self._get_findings_in_range(time_range)

        # Apply filters
        findings = self._filter_findings(findings, filters)

        # Generate report
        report = SummaryReport(
            scope=scope,
            time_range=time_range,
            total_findings=len(findings),
            by_agent=self._group_by_agent(findings),
            by_severity=self._count_by_severity(findings),
            by_category=self._count_by_category(findings),
            trends=self._calculate_trends(findings, scope),
            critical_issues=self._get_critical_issues(findings),
            auto_fixable=self._get_auto_fixable(findings),
            insights=self._generate_insights(findings, scope),
        )

        return report

    def _get_time_range(self, scope: str) -> Tuple[datetime, datetime]:
        """Get datetime range for scope."""
        now = datetime.now(UTC)

        if scope == "recent":
            # Last 24 hours
            start = now - timedelta(hours=24)
        elif scope == "today":
            # Start of today
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif scope == "session":
            # Last 4 hours (typical coding session)
            start = now - timedelta(hours=4)
        elif scope == "all":
            # All time - use a very old date
            start = datetime(2020, 1, 1, tzinfo=UTC)
        else:
            raise ValueError(f"Unknown scope: {scope}")

        return (start, now)

    async def _get_findings_in_range(
        self, time_range: Tuple[datetime, datetime]
    ) -> List[Finding]:
        """Get all findings within time range."""
        start_time, end_time = time_range

        # Get findings from all tiers
        all_findings = []
        for tier in [Tier.IMMEDIATE, Tier.RELEVANT, Tier.BACKGROUND]:
            tier_findings = await self.context_store.get_findings(tier=tier)
            all_findings.extend(tier_findings)

        # Filter by timestamp
        filtered_findings = []
        for finding in all_findings:
            try:
                finding_time = datetime.fromisoformat(
                    finding.timestamp.replace("Z", "+00:00")
                )
                if start_time <= finding_time <= end_time:
                    filtered_findings.append(finding)
            except (ValueError, AttributeError):
                # If timestamp parsing fails, include the finding
                filtered_findings.append(finding)

        return filtered_findings

    def _filter_findings(
        self, findings: List[Finding], filters: Dict[str, Any]
    ) -> List[Finding]:
        """Apply user-specified filters."""
        if not filters:
            return findings

        filtered = findings

        # Filter by agent
        if "agent" in filters:
            agent_filter = filters["agent"]
            filtered = [f for f in filtered if f.agent == agent_filter]

        # Filter by severity
        if "severity" in filters:
            severity_filter = filters["severity"]
            try:
                severity_enum = Severity(severity_filter)
                filtered = [f for f in filtered if f.severity == severity_enum]
            except ValueError:
                logger.warning(f"Invalid severity filter: {severity_filter}")

        # Filter by category
        if "category" in filters:
            category_filter = filters["category"]
            filtered = [f for f in filtered if f.category == category_filter]

        return filtered

    def _group_by_agent(self, findings: List[Finding]) -> Dict[str, AgentSummary]:
        """Group findings by agent type."""
        agent_groups: Dict[str, List[Finding]] = {}
        for finding in findings:
            agent_groups.setdefault(finding.agent, []).append(finding)

        summaries = {}
        for agent_name, agent_findings in agent_groups.items():
            # Count by severity
            severity_counts: Dict[str, int] = {}
            for finding in agent_findings:
                severity = finding.severity.value
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

            # Get top 3 issues by severity (errors first, then warnings, etc.)
            sorted_findings = sorted(
                agent_findings,
                key=lambda f: (
                    f.severity.value == "error",
                    f.severity.value == "warning",
                ),
                reverse=True,
            )
            top_issues = sorted_findings[:3]

            summaries[agent_name] = AgentSummary(
                agent_name=agent_name,
                finding_count=len(agent_findings),
                severity_breakdown=severity_counts,
                top_issues=top_issues,
                improvement_trend="stable",  # TODO: Implement trend calculation
            )

        return summaries

    def _count_by_severity(self, findings: List[Finding]) -> Dict[str, int]:
        """Count findings by severity."""
        counts: Dict[str, int] = {}
        for finding in findings:
            severity = finding.severity.value
            counts[severity] = counts.get(severity, 0) + 1
        return counts

    def _count_by_category(self, findings: List[Finding]) -> Dict[str, int]:
        """Count findings by category."""
        counts: Dict[str, int] = {}
        for finding in findings:
            counts[finding.category] = counts.get(finding.category, 0) + 1
        return counts

    def _calculate_trends(self, findings: List[Finding], scope: str) -> Dict[str, Any]:
        """Calculate improvement/worsening trends."""
        # TODO: Implement actual trend calculation comparing to previous periods
        # For now, return basic stats
        return {
            "comparison_period": "previous_24h",
            "change_percent": 0.0,  # No change
            "direction": "stable",
        }

    def _get_critical_issues(self, findings: List[Finding]) -> List[Finding]:
        """Get critical/blocking issues."""
        return [f for f in findings if f.blocking or f.severity == Severity.ERROR]

    def _get_auto_fixable(self, findings: List[Finding]) -> List[Finding]:
        """Get auto-fixable findings."""
        return [f for f in findings if f.auto_fixable]

    def _generate_insights(self, findings: List[Finding], scope: str) -> List[str]:
        """Generate actionable insights."""
        insights = []

        if not findings:
            return ["No findings in the selected scope"]

        # Count by agent
        agent_counts: Dict[str, int] = {}
        for finding in findings:
            agent_counts[finding.agent] = agent_counts.get(finding.agent, 0) + 1

        # Most active agent
        if agent_counts:
            top_agent = max(agent_counts.items(), key=lambda x: x[1])
            insights.append(
                f"Most active agent: {top_agent[0]} ({top_agent[1]} findings)"
            )

        # Severity breakdown insight
        error_count = sum(1 for f in findings if f.severity == Severity.ERROR)
        if error_count > 0:
            insights.append(f"{error_count} error-level findings requiring attention")

        # Auto-fixable insight
        auto_fixable_count = sum(1 for f in findings if f.auto_fixable)
        if auto_fixable_count > 0:
            insights.append(f"{auto_fixable_count} findings can be auto-fixed")

        return insights
