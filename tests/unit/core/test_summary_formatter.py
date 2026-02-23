"""Tests for summary formatter."""

from __future__ import annotations

from datetime import datetime, UTC


from devloop.core.context_store import Finding, Severity
from devloop.core.summary_generator import AgentSummary, SummaryReport
from devloop.core.summary_formatter import SummaryFormatter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(
    severity: Severity = Severity.WARNING,
    blocking: bool = False,
    auto_fixable: bool = False,
    file: str = "src/main.py",
    line: int | None = 1,
    message: str = "test finding",
    agent: str = "linter",
) -> Finding:
    return Finding(
        id="f-1",
        agent=agent,
        timestamp=datetime.now(UTC).isoformat(),
        file=file,
        line=line,
        severity=severity,
        blocking=blocking,
        auto_fixable=auto_fixable,
        message=message,
    )


def _make_report(
    total_findings: int = 0,
    by_agent: dict | None = None,
    by_severity: dict | None = None,
    critical_issues: list | None = None,
    auto_fixable: list | None = None,
    trends: dict | None = None,
    insights: list | None = None,
    scope: str = "recent",
) -> SummaryReport:
    now = datetime.now(UTC)
    return SummaryReport(
        scope=scope,
        time_range=(now, now),
        total_findings=total_findings,
        by_agent=by_agent or {},
        by_severity=by_severity or {},
        by_category={},
        trends=trends or {},
        critical_issues=critical_issues or [],
        auto_fixable=auto_fixable or [],
        insights=insights or [],
    )


# ---------------------------------------------------------------------------
# SummaryFormatter.format_markdown
# ---------------------------------------------------------------------------


class TestFormatMarkdown:
    def test_empty_report(self) -> None:
        report = _make_report()
        md = SummaryFormatter.format_markdown(report)
        assert "All Clear" in md
        assert "Total Findings:** 0" in md

    def test_critical_issues_header(self) -> None:
        critical = [_make_finding(severity=Severity.ERROR, blocking=True)]
        report = _make_report(
            total_findings=1,
            critical_issues=critical,
        )
        md = SummaryFormatter.format_markdown(report)
        assert "Critical Issues" in md
        assert "Priority Issues" in md

    def test_findings_without_critical(self) -> None:
        report = _make_report(total_findings=3)
        md = SummaryFormatter.format_markdown(report)
        assert "Findings Summary" in md

    def test_severity_breakdown(self) -> None:
        report = _make_report(
            total_findings=5,
            by_severity={"error": 2, "warning": 3},
        )
        md = SummaryFormatter.format_markdown(report)
        assert "2 error" in md
        assert "3 warning" in md

    def test_trend_display(self) -> None:
        report = _make_report(trends={"direction": "improving"})
        md = SummaryFormatter.format_markdown(report)
        assert "Improving" in md

    def test_trend_worsening(self) -> None:
        report = _make_report(trends={"direction": "worsening"})
        md = SummaryFormatter.format_markdown(report)
        assert "Worsening" in md

    def test_trend_stable(self) -> None:
        report = _make_report(trends={"direction": "stable"})
        md = SummaryFormatter.format_markdown(report)
        assert "Stable" in md

    def test_agent_breakdown(self) -> None:
        agent_summary = AgentSummary(
            agent_name="linter",
            finding_count=3,
            severity_breakdown={"error": 1, "warning": 2},
            top_issues=[],
            improvement_trend="stable",
        )
        report = _make_report(
            total_findings=3,
            by_agent={"linter": agent_summary},
        )
        md = SummaryFormatter.format_markdown(report)
        assert "linter" in md
        assert "3 findings" in md

    def test_critical_issues_list(self) -> None:
        critical = [
            _make_finding(
                severity=Severity.ERROR,
                file="src/app.py",
                line=42,
                message="undefined variable",
            ),
        ]
        report = _make_report(total_findings=1, critical_issues=critical)
        md = SummaryFormatter.format_markdown(report)
        assert "src/app.py:42" in md
        assert "undefined variable" in md

    def test_long_message_truncated(self) -> None:
        long_msg = "x" * 200
        critical = [_make_finding(severity=Severity.ERROR, message=long_msg)]
        report = _make_report(total_findings=1, critical_issues=critical)
        md = SummaryFormatter.format_markdown(report)
        assert "..." in md

    def test_auto_fixable_section(self) -> None:
        auto_fix = [
            _make_finding(auto_fixable=True, message="fix trailing whitespace"),
        ]
        report = _make_report(
            total_findings=1,
            auto_fixable=auto_fix,
        )
        md = SummaryFormatter.format_markdown(report)
        assert "Auto-fixable" in md or "auto-fix" in md.lower()

    def test_auto_fixable_separate_from_critical(self) -> None:
        critical = [_make_finding(severity=Severity.ERROR, blocking=True)]
        auto_fix = [
            critical[0],
            _make_finding(auto_fixable=True, message="whitespace"),
        ]
        report = _make_report(
            total_findings=2,
            critical_issues=critical,
            auto_fixable=auto_fix,
        )
        md = SummaryFormatter.format_markdown(report)
        assert "Auto-fixable Issues" in md

    def test_insights_section(self) -> None:
        report = _make_report(insights=["Most active agent: linter (5 findings)"])
        md = SummaryFormatter.format_markdown(report)
        assert "Insights" in md
        assert "Most active agent" in md

    def test_quick_actions_section(self) -> None:
        auto_fix = [_make_finding(auto_fixable=True)]
        report = _make_report(total_findings=1, auto_fixable=auto_fix)
        md = SummaryFormatter.format_markdown(report)
        assert "Quick Actions" in md
        assert "devloop auto-fix" in md

    def test_finding_with_no_line(self) -> None:
        critical = [_make_finding(severity=Severity.ERROR, line=None)]
        report = _make_report(total_findings=1, critical_issues=critical)
        md = SummaryFormatter.format_markdown(report)
        assert "?" in md  # line=None shows as ?


# ---------------------------------------------------------------------------
# SummaryFormatter.format_json
# ---------------------------------------------------------------------------


class TestFormatJson:
    def test_empty_report(self) -> None:
        report = _make_report()
        result = SummaryFormatter.format_json(report)
        assert result["summary"]["total_findings"] == 0
        assert result["summary"]["critical_count"] == 0
        assert result["summary"]["trend"] == "stable"
        assert result["by_agent"] == {}
        assert result["insights"] == []
        assert result["critical_issues"] == []

    def test_with_findings(self) -> None:
        critical = [
            _make_finding(
                severity=Severity.ERROR,
                file="src/app.py",
                line=10,
                message="bad",
                agent="linter",
            ),
        ]
        agent_summary = AgentSummary(
            agent_name="linter",
            finding_count=1,
            severity_breakdown={"error": 1},
            top_issues=critical,
            improvement_trend="stable",
        )
        report = _make_report(
            total_findings=1,
            by_agent={"linter": agent_summary},
            critical_issues=critical,
            trends={"direction": "worsening", "change_percent": 15.0},
        )
        result = SummaryFormatter.format_json(report)
        assert result["summary"]["total_findings"] == 1
        assert result["summary"]["critical_count"] == 1
        assert result["summary"]["trend"] == "worsening"
        assert result["summary"]["trend_percentage"] == 15.0
        assert result["by_agent"]["linter"]["count"] == 1
        assert len(result["critical_issues"]) == 1
        assert result["critical_issues"][0]["file"] == "src/app.py"

    def test_auto_fixable_count_in_agent(self) -> None:
        finding = _make_finding(auto_fixable=True)
        agent_summary = AgentSummary(
            agent_name="formatter",
            finding_count=1,
            severity_breakdown={"warning": 1},
            top_issues=[finding],
            improvement_trend="stable",
        )
        report = _make_report(
            total_findings=1,
            by_agent={"formatter": agent_summary},
        )
        result = SummaryFormatter.format_json(report)
        assert result["by_agent"]["formatter"]["auto_fixable"] == 1

    def test_scope_in_summary(self) -> None:
        report = _make_report(scope="today")
        result = SummaryFormatter.format_json(report)
        assert result["summary"]["scope"] == "today"
