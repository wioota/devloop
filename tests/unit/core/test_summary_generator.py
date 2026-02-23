"""Tests for summary generator."""

from __future__ import annotations

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from devloop.core.context_store import Finding, Severity
from devloop.core.summary_generator import AgentSummary, SummaryGenerator, SummaryReport

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(
    agent: str = "linter",
    severity: Severity = Severity.WARNING,
    category: str = "style",
    blocking: bool = False,
    auto_fixable: bool = False,
    file: str = "src/main.py",
    line: int | None = 1,
    message: str = "test finding",
    timestamp: str | None = None,
) -> Finding:
    if timestamp is None:
        timestamp = datetime.now(UTC).isoformat()
    return Finding(
        id="f-1",
        agent=agent,
        timestamp=timestamp,
        file=file,
        line=line,
        severity=severity,
        blocking=blocking,
        category=category,
        auto_fixable=auto_fixable,
        message=message,
    )


def _mock_store(findings: list[Finding] | None = None) -> MagicMock:
    """Create a mock context store returning findings only for the first tier call."""
    store = MagicMock()
    # get_findings is called once per tier (3 tiers); return findings only on
    # the first call to avoid triple-counting.
    store.get_findings = AsyncMock(side_effect=[findings or [], [], []])
    return store


# ---------------------------------------------------------------------------
# SummaryGenerator._get_time_range
# ---------------------------------------------------------------------------


class TestGetTimeRange:
    def test_recent_scope(self) -> None:
        gen = SummaryGenerator(context_store_instance=_mock_store())
        start, end = gen._get_time_range("recent")
        assert (end - start).total_seconds() == pytest.approx(86400, abs=5)

    def test_today_scope(self) -> None:
        gen = SummaryGenerator(context_store_instance=_mock_store())
        start, end = gen._get_time_range("today")
        assert start.hour == 0 and start.minute == 0

    def test_session_scope(self) -> None:
        gen = SummaryGenerator(context_store_instance=_mock_store())
        start, end = gen._get_time_range("session")
        assert (end - start).total_seconds() == pytest.approx(14400, abs=5)

    def test_all_scope(self) -> None:
        gen = SummaryGenerator(context_store_instance=_mock_store())
        start, end = gen._get_time_range("all")
        assert start.year == 2020

    def test_unknown_scope_raises(self) -> None:
        gen = SummaryGenerator(context_store_instance=_mock_store())
        with pytest.raises(ValueError, match="Unknown scope"):
            gen._get_time_range("invalid")


# ---------------------------------------------------------------------------
# SummaryGenerator._filter_findings
# ---------------------------------------------------------------------------


class TestFilterFindings:
    def setup_method(self) -> None:
        self.gen = SummaryGenerator(context_store_instance=_mock_store())

    def test_no_filters(self) -> None:
        findings = [_make_finding(), _make_finding()]
        assert self.gen._filter_findings(findings, {}) == findings

    def test_filter_by_agent(self) -> None:
        findings = [
            _make_finding(agent="linter"),
            _make_finding(agent="formatter"),
            _make_finding(agent="linter"),
        ]
        result = self.gen._filter_findings(findings, {"agent": "linter"})
        assert len(result) == 2

    def test_filter_by_severity(self) -> None:
        findings = [
            _make_finding(severity=Severity.ERROR),
            _make_finding(severity=Severity.WARNING),
            _make_finding(severity=Severity.ERROR),
        ]
        result = self.gen._filter_findings(findings, {"severity": "error"})
        assert len(result) == 2

    def test_filter_by_invalid_severity(self) -> None:
        findings = [_make_finding()]
        # Invalid severity should not crash, returns unfiltered
        result = self.gen._filter_findings(findings, {"severity": "bogus"})
        assert len(result) == 1

    def test_filter_by_category(self) -> None:
        findings = [
            _make_finding(category="style"),
            _make_finding(category="security"),
        ]
        result = self.gen._filter_findings(findings, {"category": "security"})
        assert len(result) == 1


# ---------------------------------------------------------------------------
# SummaryGenerator._group_by_agent
# ---------------------------------------------------------------------------


class TestGroupByAgent:
    def test_empty(self) -> None:
        gen = SummaryGenerator(context_store_instance=_mock_store())
        assert gen._group_by_agent([]) == {}

    def test_single_agent(self) -> None:
        gen = SummaryGenerator(context_store_instance=_mock_store())
        findings = [_make_finding(agent="linter") for _ in range(3)]
        result = gen._group_by_agent(findings)
        assert "linter" in result
        assert result["linter"].finding_count == 3

    def test_multiple_agents(self) -> None:
        gen = SummaryGenerator(context_store_instance=_mock_store())
        findings = [
            _make_finding(agent="linter", severity=Severity.ERROR),
            _make_finding(agent="formatter", severity=Severity.WARNING),
            _make_finding(agent="linter", severity=Severity.WARNING),
        ]
        result = gen._group_by_agent(findings)
        assert len(result) == 2
        assert result["linter"].finding_count == 2
        assert result["linter"].severity_breakdown["error"] == 1
        assert result["linter"].severity_breakdown["warning"] == 1

    def test_top_issues_capped_at_3(self) -> None:
        gen = SummaryGenerator(context_store_instance=_mock_store())
        findings = [_make_finding(agent="linter") for _ in range(10)]
        result = gen._group_by_agent(findings)
        assert len(result["linter"].top_issues) == 3


# ---------------------------------------------------------------------------
# SummaryGenerator._count_by_severity / _count_by_category
# ---------------------------------------------------------------------------


class TestCountBy:
    def setup_method(self) -> None:
        self.gen = SummaryGenerator(context_store_instance=_mock_store())

    def test_count_by_severity(self) -> None:
        findings = [
            _make_finding(severity=Severity.ERROR),
            _make_finding(severity=Severity.ERROR),
            _make_finding(severity=Severity.WARNING),
        ]
        result = self.gen._count_by_severity(findings)
        assert result == {"error": 2, "warning": 1}

    def test_count_by_category(self) -> None:
        findings = [
            _make_finding(category="style"),
            _make_finding(category="security"),
            _make_finding(category="style"),
        ]
        result = self.gen._count_by_category(findings)
        assert result == {"style": 2, "security": 1}


# ---------------------------------------------------------------------------
# SummaryGenerator._get_critical_issues / _get_auto_fixable
# ---------------------------------------------------------------------------


class TestCriticalAndAutoFixable:
    def setup_method(self) -> None:
        self.gen = SummaryGenerator(context_store_instance=_mock_store())

    def test_critical_includes_errors(self) -> None:
        findings = [
            _make_finding(severity=Severity.ERROR),
            _make_finding(severity=Severity.WARNING),
        ]
        result = self.gen._get_critical_issues(findings)
        assert len(result) == 1

    def test_critical_includes_blocking(self) -> None:
        findings = [
            _make_finding(severity=Severity.WARNING, blocking=True),
            _make_finding(severity=Severity.WARNING, blocking=False),
        ]
        result = self.gen._get_critical_issues(findings)
        assert len(result) == 1

    def test_auto_fixable(self) -> None:
        findings = [
            _make_finding(auto_fixable=True),
            _make_finding(auto_fixable=False),
            _make_finding(auto_fixable=True),
        ]
        result = self.gen._get_auto_fixable(findings)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# SummaryGenerator._calculate_trends
# ---------------------------------------------------------------------------


class TestCalculateTrends:
    def test_returns_stable(self) -> None:
        gen = SummaryGenerator(context_store_instance=_mock_store())
        result = gen._calculate_trends([], "recent")
        assert result["direction"] == "stable"
        assert result["change_percent"] == 0.0


# ---------------------------------------------------------------------------
# SummaryGenerator._generate_insights
# ---------------------------------------------------------------------------


class TestGenerateInsights:
    def setup_method(self) -> None:
        self.gen = SummaryGenerator(context_store_instance=_mock_store())

    def test_empty_findings(self) -> None:
        result = self.gen._generate_insights([], "recent")
        assert "No findings" in result[0]

    def test_most_active_agent(self) -> None:
        findings = [
            _make_finding(agent="linter"),
            _make_finding(agent="linter"),
            _make_finding(agent="formatter"),
        ]
        result = self.gen._generate_insights(findings, "recent")
        assert any("linter" in i for i in result)

    def test_error_insight(self) -> None:
        findings = [_make_finding(severity=Severity.ERROR)]
        result = self.gen._generate_insights(findings, "recent")
        assert any("error-level" in i for i in result)

    def test_auto_fixable_insight(self) -> None:
        findings = [_make_finding(auto_fixable=True)]
        result = self.gen._generate_insights(findings, "recent")
        assert any("auto-fixed" in i for i in result)


# ---------------------------------------------------------------------------
# SummaryGenerator.generate_summary (async integration)
# ---------------------------------------------------------------------------


class TestGenerateSummary:
    @pytest.mark.asyncio
    async def test_generate_summary_empty(self) -> None:
        gen = SummaryGenerator(context_store_instance=_mock_store([]))
        report = await gen.generate_summary("recent")
        assert isinstance(report, SummaryReport)
        assert report.total_findings == 0
        assert report.scope == "recent"

    @pytest.mark.asyncio
    async def test_generate_summary_with_findings(self) -> None:
        findings = [
            _make_finding(agent="linter", severity=Severity.ERROR, blocking=True),
            _make_finding(
                agent="formatter", severity=Severity.WARNING, auto_fixable=True
            ),
        ]
        gen = SummaryGenerator(context_store_instance=_mock_store(findings))
        report = await gen.generate_summary("all")
        assert report.total_findings == 2
        assert len(report.critical_issues) == 1
        assert len(report.auto_fixable) == 1
        assert "linter" in report.by_agent
        assert "formatter" in report.by_agent

    @pytest.mark.asyncio
    async def test_generate_summary_with_filters(self) -> None:
        findings = [
            _make_finding(agent="linter"),
            _make_finding(agent="formatter"),
        ]
        gen = SummaryGenerator(context_store_instance=_mock_store(findings))
        report = await gen.generate_summary("all", filters={"agent": "linter"})
        assert report.total_findings == 1


# ---------------------------------------------------------------------------
# AgentSummary dataclass
# ---------------------------------------------------------------------------


class TestAgentSummary:
    def test_creation(self) -> None:
        summary = AgentSummary(
            agent_name="linter",
            finding_count=5,
            severity_breakdown={"error": 2, "warning": 3},
            top_issues=[],
            improvement_trend="stable",
        )
        assert summary.agent_name == "linter"
        assert summary.finding_count == 5
