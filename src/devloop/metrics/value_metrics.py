"""Track and calculate ROI/value metrics for DevLoop usage.

This module collects data to validate the claims in the README:
- 75-90 minutes saved per developer per day
- Reduce CI costs by 60%+
- Catch 90%+ of CI failures locally
- 6-8 CI failures per day baseline
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from datetime import datetime, UTC, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ValueMetrics:
    """Calculated value metrics for a time period."""

    period_days: int
    date_range: tuple[datetime, datetime]

    # Time saving metrics
    ci_roundtrips_prevented: int = 0
    avg_roundtrip_time_min: float = 15.0  # Assumed average CI roundtrip time
    total_time_saved_min: float = 0.0

    # CI failure metrics
    ci_failures_prevented: int = 0
    ci_failures_allowed: int = 0
    ci_failure_rate: float = 0.0  # Percentage of checks that would have failed

    # Agent execution metrics
    agents_executed: int = 0
    findings_detected: int = 0
    pre_commit_checks_prevented: int = 0
    pre_push_checks_prevented: int = 0

    # Cost metrics
    ci_cost_baseline_per_failure_usd: float = 0.25  # Typical cost per CI run
    estimated_cost_saved_usd: float = 0.0

    # Adoption metrics
    days_active: int = 0
    commits_analyzed: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime to ISO format
        data["date_range"] = (
            self.date_range[0].isoformat(),
            self.date_range[1].isoformat(),
        )
        return data


@dataclass
class BeforeAfterComparison:
    """Compare metrics before and after DevLoop adoption."""

    before_period: ValueMetrics
    after_period: ValueMetrics

    # Calculated improvements
    time_saved_improvement_percent: float = 0.0
    ci_failures_reduction_percent: float = 0.0
    cost_reduction_percent: float = 0.0
    roi_estimate: str = ""

    def calculate_improvements(self) -> None:
        """Calculate percentage improvements between periods."""
        before_rate = (
            self.before_period.ci_failures_prevented
            + self.before_period.pre_push_checks_prevented
        )
        after_rate = (
            self.after_period.ci_failures_prevented
            + self.after_period.pre_push_checks_prevented
        )

        # Time saved comparison
        if self.before_period.total_time_saved_min > 0:
            self.time_saved_improvement_percent = (
                (
                    self.after_period.total_time_saved_min
                    - self.before_period.total_time_saved_min
                )
                / self.before_period.total_time_saved_min
                * 100
            )

        # CI failures prevented comparison
        if before_rate > 0:
            self.ci_failures_reduction_percent = (
                (after_rate - before_rate) / before_rate * 100
            )

        # Cost reduction
        if self.before_period.estimated_cost_saved_usd > 0:
            self.cost_reduction_percent = (
                (
                    self.after_period.estimated_cost_saved_usd
                    - self.before_period.estimated_cost_saved_usd
                )
                / self.before_period.estimated_cost_saved_usd
                * 100
            )

        # Calculate ROI estimate based on total and improvements
        total_cost_saved = self.after_period.estimated_cost_saved_usd
        improvements = (
            self.cost_reduction_percent
            + self.time_saved_improvement_percent
            + self.ci_failures_reduction_percent
        ) / 3

        if improvements > 100 or total_cost_saved > 50:
            self.roi_estimate = f"High ROI: ${total_cost_saved:.2f} saved"
        elif improvements > 50 or total_cost_saved > 10:
            self.roi_estimate = f"Positive ROI: ${total_cost_saved:.2f} saved"
        elif total_cost_saved > 0:
            self.roi_estimate = f"Modest ROI: ${total_cost_saved:.2f} saved"
        else:
            self.roi_estimate = "Data collection in progress"


class ValueMetricsCalculator:
    """Calculate value metrics from telemetry events."""

    def __init__(self, telemetry_data: list[dict[str, Any]]):
        """Initialize calculator with telemetry events.

        Args:
            telemetry_data: List of telemetry event dictionaries
        """
        self.events = telemetry_data

    def calculate_metrics(
        self,
        period_days: int = 30,
    ) -> ValueMetrics:
        """Calculate value metrics for a time period.

        Args:
            period_days: Number of days to analyze

        Returns:
            ValueMetrics for the period
        """
        end = datetime.now(UTC)
        start = end - timedelta(days=period_days)

        # Filter events in range
        events_in_range = self._filter_events_by_date(start, end)

        if not events_in_range:
            return ValueMetrics(
                period_days=period_days,
                date_range=(start, end),
            )

        metrics = ValueMetrics(
            period_days=period_days,
            date_range=(start, end),
        )

        # Count CI roundtrips prevented
        ci_preventions = [
            e
            for e in events_in_range
            if e.get("event_type") == "ci_roundtrip_prevented"
        ]
        metrics.ci_roundtrips_prevented = len(ci_preventions)
        metrics.total_time_saved_min = (
            metrics.ci_roundtrips_prevented * metrics.avg_roundtrip_time_min
        )

        # Count pre-push check preventions
        pre_push_events = [
            e for e in events_in_range if e.get("event_type") == "pre_push_check"
        ]
        prevented_pushes = [e for e in pre_push_events if not e.get("success", True)]
        metrics.pre_push_checks_prevented = len(prevented_pushes)

        # Count pre-commit checks
        pre_commit_events = [
            e for e in events_in_range if e.get("event_type") == "pre_commit_check"
        ]
        prevented_commits = [e for e in pre_commit_events if not e.get("success", True)]
        metrics.pre_commit_checks_prevented = len(prevented_commits)

        # Count agent executions
        agent_events = [
            e for e in events_in_range if e.get("event_type") == "agent_executed"
        ]
        metrics.agents_executed = len(agent_events)
        metrics.findings_detected = sum(e.get("findings", 0) for e in agent_events)

        # Calculate CI failure prevention rate
        total_checks = len(pre_push_events) + len(pre_commit_events)
        if total_checks > 0:
            total_prevented = len(prevented_pushes) + len(prevented_commits)
            metrics.ci_failure_rate = (total_prevented / total_checks) * 100

        # Calculate estimated cost savings
        # Assumption: each prevented CI failure saves ~15 minutes and costs ~$0.25
        metrics.estimated_cost_saved_usd = (
            metrics.ci_roundtrips_prevented * metrics.ci_cost_baseline_per_failure_usd
        )

        # Count days with activity
        active_dates = set()
        for event in events_in_range:
            try:
                ts = event.get("timestamp", "")
                if ts:
                    date = datetime.fromisoformat(ts).date()
                    active_dates.add(date)
            except (ValueError, TypeError):
                pass
        metrics.days_active = len(active_dates)

        return metrics

    def _filter_events_by_date(
        self,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """Filter events within a date range.

        Args:
            start: Start datetime
            end: End datetime

        Returns:
            List of events in range
        """
        filtered = []
        for event in self.events:
            try:
                ts = event.get("timestamp", "")
                if not ts:
                    continue
                event_time = datetime.fromisoformat(ts)
                if start <= event_time <= end:
                    filtered.append(event)
            except (ValueError, TypeError):
                continue
        return filtered

    def compare_periods(
        self,
        before_start: datetime,
        before_end: datetime,
        after_start: datetime,
        after_end: datetime,
    ) -> BeforeAfterComparison:
        """Compare metrics between two periods.

        Args:
            before_start: Start of before period
            before_end: End of before period
            after_start: Start of after period
            after_end: End of after period

        Returns:
            BeforeAfterComparison with calculated improvements
        """
        before_days = (before_end - before_start).days
        after_days = (after_end - after_start).days

        before_metrics = self.calculate_metrics(before_days)
        after_metrics = self.calculate_metrics(after_days)

        comparison = BeforeAfterComparison(
            before_period=before_metrics,
            after_period=after_metrics,
        )
        comparison.calculate_improvements()

        return comparison


class ValueMetricsReporter:
    """Generate reports of value metrics."""

    @staticmethod
    def format_metrics_report(metrics: ValueMetrics) -> str:
        """Format metrics as human-readable report.

        Args:
            metrics: ValueMetrics to report

        Returns:
            Formatted report string
        """
        lines = [
            "═══════════════════════════════════════════════════",
            "DevLoop Value Metrics Report",
            "═══════════════════════════════════════════════════",
            "",
            f"Period: {metrics.period_days} days",
            f"Active: {metrics.days_active} days",
            "",
            "CI Impact:",
            f"  CI roundtrips prevented: {metrics.ci_roundtrips_prevented}",
            f"  Pre-push checks prevented: {metrics.pre_push_checks_prevented}",
            f"  Pre-commit checks prevented: {metrics.pre_commit_checks_prevented}",
            f"  Estimated CI failure rate prevented: {metrics.ci_failure_rate:.1f}%",
            "",
            "Time Savings:",
            f"  Total time saved: ~{metrics.total_time_saved_min:.0f} minutes",
            f"  Average per day: ~{metrics.total_time_saved_min / max(metrics.period_days, 1):.1f} minutes",
            "",
            "Agent Activity:",
            f"  Agents executed: {metrics.agents_executed}",
            f"  Total findings detected: {metrics.findings_detected}",
            "",
            "Cost Savings:",
            f"  Estimated cost saved: ${metrics.estimated_cost_saved_usd:.2f}",
            "═══════════════════════════════════════════════════",
        ]
        return "\n".join(lines)

    @staticmethod
    def format_comparison_report(comparison: BeforeAfterComparison) -> str:
        """Format before/after comparison as report.

        Args:
            comparison: BeforeAfterComparison to report

        Returns:
            Formatted report string
        """
        lines = [
            "═══════════════════════════════════════════════════",
            "DevLoop ROI Analysis",
            "═══════════════════════════════════════════════════",
            "",
            "Before DevLoop:",
            f"  CI failures per period: ~{comparison.before_period.ci_roundtrips_prevented}",
            f"  Time wasted: ~{comparison.before_period.total_time_saved_min:.0f} minutes",
            "",
            "After DevLoop:",
            f"  CI failures prevented: {comparison.after_period.ci_roundtrips_prevented}",
            f"  Time saved: {comparison.after_period.total_time_saved_min:.0f} minutes",
            "",
            "Improvements:",
            f"  CI failures reduction: {comparison.ci_failures_reduction_percent:+.1f}%",
            f"  Time saved improvement: {comparison.time_saved_improvement_percent:+.1f}%",
            f"  Cost reduction: {comparison.cost_reduction_percent:+.1f}%",
            "",
            f"ROI: {comparison.roi_estimate}",
            "═══════════════════════════════════════════════════",
        ]
        return "\n".join(lines)
