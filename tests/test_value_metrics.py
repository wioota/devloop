"""Tests for value metrics tracking and reporting."""

import json
from datetime import datetime, UTC, timedelta
from pathlib import Path

import pytest

from devloop.metrics.value_metrics import (
    BeforeAfterComparison,
    ValueMetrics,
    ValueMetricsCalculator,
    ValueMetricsReporter,
)


@pytest.fixture
def sample_telemetry_events() -> list[dict]:
    """Create sample telemetry events for testing."""
    now = datetime.now(UTC)
    events = [
        # CI roundtrip prevented events
        {
            "event_type": "ci_roundtrip_prevented",
            "timestamp": (now - timedelta(days=2)).isoformat(),
            "details": {
                "reason": "lint-error",
                "check_that_would_fail": "ruff check",
            },
        },
        {
            "event_type": "ci_roundtrip_prevented",
            "timestamp": (now - timedelta(days=5)).isoformat(),
            "details": {
                "reason": "type-error",
                "check_that_would_fail": "mypy",
            },
        },
        # Pre-push check events
        {
            "event_type": "pre_push_check",
            "timestamp": (now - timedelta(days=1)).isoformat(),
            "success": False,
            "duration_ms": 5000,
            "details": {"checks_run": 3, "prevented_bad_push": True},
        },
        {
            "event_type": "pre_push_check",
            "timestamp": (now - timedelta(days=3)).isoformat(),
            "success": True,
            "duration_ms": 4500,
            "details": {"checks_run": 3, "prevented_bad_push": False},
        },
        # Pre-commit check events
        {
            "event_type": "pre_commit_check",
            "timestamp": (now - timedelta(days=1)).isoformat(),
            "success": True,
            "duration_ms": 2000,
            "details": {"checks_run": 2},
        },
        {
            "event_type": "pre_commit_check",
            "timestamp": (now - timedelta(days=2)).isoformat(),
            "success": False,
            "duration_ms": 3000,
            "details": {"checks_run": 2},
        },
        # Agent execution events
        {
            "event_type": "agent_executed",
            "timestamp": (now - timedelta(days=1)).isoformat(),
            "agent": "linter",
            "duration_ms": 1500,
            "findings": 5,
            "success": True,
        },
        {
            "event_type": "agent_executed",
            "timestamp": (now - timedelta(days=2)).isoformat(),
            "agent": "formatter",
            "duration_ms": 2000,
            "findings": 3,
            "success": True,
        },
        {
            "event_type": "agent_executed",
            "timestamp": (now - timedelta(days=3)).isoformat(),
            "agent": "type-checker",
            "duration_ms": 3000,
            "findings": 2,
            "success": True,
        },
    ]
    return events


class TestValueMetricsCalculator:
    """Test ValueMetricsCalculator class."""

    def test_calculate_metrics_with_events(self, sample_telemetry_events):
        """Test calculating metrics from telemetry events."""
        calculator = ValueMetricsCalculator(sample_telemetry_events)
        metrics = calculator.calculate_metrics(period_days=30)

        assert metrics.period_days == 30
        assert metrics.ci_roundtrips_prevented == 2
        assert metrics.pre_push_checks_prevented == 1
        assert metrics.pre_commit_checks_prevented == 1
        assert metrics.agents_executed == 3
        assert metrics.findings_detected == 10  # 5 + 3 + 2

    def test_calculate_metrics_empty_events(self):
        """Test calculating metrics with no events."""
        calculator = ValueMetricsCalculator([])
        metrics = calculator.calculate_metrics(period_days=30)

        assert metrics.period_days == 30
        assert metrics.ci_roundtrips_prevented == 0
        assert metrics.agents_executed == 0
        assert metrics.findings_detected == 0

    def test_time_saved_calculation(self, sample_telemetry_events):
        """Test that time saved is calculated correctly."""
        calculator = ValueMetricsCalculator(sample_telemetry_events)
        metrics = calculator.calculate_metrics(period_days=30)

        # 2 CI roundtrips × 15 minutes each = 30 minutes
        assert metrics.total_time_saved_min == 30.0

    def test_cost_saved_calculation(self, sample_telemetry_events):
        """Test that cost savings are calculated correctly."""
        calculator = ValueMetricsCalculator(sample_telemetry_events)
        metrics = calculator.calculate_metrics(period_days=30)

        # 2 CI roundtrips × $0.25 = $0.50
        assert metrics.estimated_cost_saved_usd == 0.50

    def test_ci_failure_rate(self, sample_telemetry_events):
        """Test CI failure rate calculation."""
        calculator = ValueMetricsCalculator(sample_telemetry_events)
        metrics = calculator.calculate_metrics(period_days=30)

        # 2 prevented out of 4 total checks = 50%
        assert metrics.ci_failure_rate == 50.0

    def test_days_active_count(self, sample_telemetry_events):
        """Test counting active days."""
        calculator = ValueMetricsCalculator(sample_telemetry_events)
        metrics = calculator.calculate_metrics(period_days=30)

        # Events span 4 different days (at days 1, 2, 3, and 5 from now)
        assert metrics.days_active == 4

    def test_filter_events_by_date(self, sample_telemetry_events):
        """Test filtering events by date range."""
        calculator = ValueMetricsCalculator(sample_telemetry_events)
        
        now = datetime.now(UTC)
        start = now - timedelta(days=2)
        end = now
        
        filtered = calculator._filter_events_by_date(start, end)
        
        # Should include events from the last 2 days
        assert len(filtered) > 0
        # All filtered events should be in range
        for event in filtered:
            event_time = datetime.fromisoformat(event["timestamp"])
            assert start <= event_time <= end

    def test_compare_periods(self, sample_telemetry_events):
        """Test comparing metrics between two periods."""
        calculator = ValueMetricsCalculator(sample_telemetry_events)
        
        now = datetime.now(UTC)
        before_start = now - timedelta(days=60)
        before_end = now - timedelta(days=30)
        after_start = now - timedelta(days=30)
        after_end = now
        
        comparison = calculator.compare_periods(
            before_start, before_end, after_start, after_end
        )
        
        assert comparison.before_period.period_days == 30
        assert comparison.after_period.period_days == 30


class TestValueMetrics:
    """Test ValueMetrics dataclass."""

    def test_value_metrics_creation(self):
        """Test creating ValueMetrics instance."""
        now = datetime.now(UTC)
        start = now - timedelta(days=30)
        
        metrics = ValueMetrics(
            period_days=30,
            date_range=(start, now),
            ci_roundtrips_prevented=5,
            total_time_saved_min=75.0,
            estimated_cost_saved_usd=1.25,
        )
        
        assert metrics.period_days == 30
        assert metrics.ci_roundtrips_prevented == 5
        assert metrics.total_time_saved_min == 75.0

    def test_value_metrics_to_dict(self):
        """Test converting ValueMetrics to dictionary."""
        now = datetime.now(UTC)
        start = now - timedelta(days=30)
        
        metrics = ValueMetrics(
            period_days=30,
            date_range=(start, now),
            ci_roundtrips_prevented=5,
        )
        
        data = metrics.to_dict()
        assert isinstance(data, dict)
        assert data["period_days"] == 30
        assert data["ci_roundtrips_prevented"] == 5
        # Date range should be ISO strings
        assert isinstance(data["date_range"][0], str)
        assert isinstance(data["date_range"][1], str)


class TestBeforeAfterComparison:
    """Test BeforeAfterComparison class."""

    def test_calculate_improvements(self):
        """Test calculating improvements between periods."""
        now = datetime.now(UTC)
        
        before = ValueMetrics(
            period_days=30,
            date_range=(now - timedelta(days=60), now - timedelta(days=30)),
            ci_roundtrips_prevented=2,
            total_time_saved_min=30.0,
            estimated_cost_saved_usd=0.50,
            days_active=25,
        )
        
        after = ValueMetrics(
            period_days=30,
            date_range=(now - timedelta(days=30), now),
            ci_roundtrips_prevented=5,
            total_time_saved_min=75.0,
            estimated_cost_saved_usd=1.25,
            days_active=25,
        )
        
        comparison = BeforeAfterComparison(
            before_period=before,
            after_period=after,
        )
        comparison.calculate_improvements()
        
        # Should show improvements
        assert comparison.time_saved_improvement_percent == 150.0
        assert comparison.cost_reduction_percent == 150.0
        # Cost savings are $1.25 with improvements, should give Positive ROI
        assert ("High ROI" in comparison.roi_estimate or "Positive ROI" in comparison.roi_estimate)


class TestValueMetricsReporter:
    """Test ValueMetricsReporter class."""

    def test_format_metrics_report(self):
        """Test formatting metrics as report."""
        now = datetime.now(UTC)
        
        metrics = ValueMetrics(
            period_days=30,
            date_range=(now - timedelta(days=30), now),
            ci_roundtrips_prevented=5,
            pre_push_checks_prevented=2,
            pre_commit_checks_prevented=3,
            agents_executed=10,
            findings_detected=25,
            total_time_saved_min=75.0,
            estimated_cost_saved_usd=1.25,
            days_active=25,
        )
        
        report = ValueMetricsReporter.format_metrics_report(metrics)
        
        assert isinstance(report, str)
        assert "Value Metrics Report" in report
        assert "5" in report  # CI roundtrips
        assert "75" in report  # Time saved
        assert "25" in report  # Findings
        assert "$1.25" in report  # Cost saved

    def test_format_comparison_report(self):
        """Test formatting comparison as report."""
        now = datetime.now(UTC)
        
        before = ValueMetrics(
            period_days=30,
            date_range=(now - timedelta(days=60), now - timedelta(days=30)),
            ci_roundtrips_prevented=2,
            total_time_saved_min=30.0,
        )
        
        after = ValueMetrics(
            period_days=30,
            date_range=(now - timedelta(days=30), now),
            ci_roundtrips_prevented=5,
            total_time_saved_min=75.0,
        )
        
        comparison = BeforeAfterComparison(
            before_period=before,
            after_period=after,
        )
        comparison.calculate_improvements()
        
        report = ValueMetricsReporter.format_comparison_report(comparison)
        
        assert isinstance(report, str)
        assert "ROI Analysis" in report
        assert "Before DevLoop" in report
        assert "After DevLoop" in report
        assert "Improvements" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
