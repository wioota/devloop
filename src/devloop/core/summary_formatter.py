"""Format summary reports for different outputs."""

from typing import Dict, Any, Optional
from pathlib import Path
from .summary_generator import SummaryReport
from .operational_health import OperationalHealthAnalyzer


class SummaryFormatter:
    """Format summary reports for different output formats."""

    @staticmethod
    def format_markdown(
        report: SummaryReport, devloop_dir: Optional[Path] = None
    ) -> str:
        """Format summary report as markdown."""
        lines = []

        # Header with emoji based on findings
        if report.total_findings == 0:
            emoji = "✅"
            status = "All Clear"
        elif report.critical_issues:
            emoji = "🚨"
            status = f"{len(report.critical_issues)} Critical Issues"
        else:
            emoji = "🔍"
            status = "Findings Summary"

        lines.append(f"## {emoji} DevLoop Summary ({status})")
        lines.append(f"**Scope:** {report.scope.title()}")
        lines.append(
            f"**Time Range:** {report.time_range[0].strftime('%Y-%m-%d %H:%M')} - {report.time_range[1].strftime('%Y-%m-%d %H:%M')}"
        )
        lines.append("")

        # Add operational health if devloop_dir provided
        if devloop_dir and devloop_dir.exists():
            try:
                analyzer = OperationalHealthAnalyzer(devloop_dir)
                health_report = analyzer.generate_health_report()
                lines.append(health_report)
            except Exception as e:
                # If health analysis fails, still show summary
                lines.append(f"(Health analysis skipped: {str(e)})")

        # Quick stats
        lines.append("### 📊 Quick Stats")
        lines.append(f"- **Total Findings:** {report.total_findings}")

        if report.by_severity:
            severity_parts = []
            for severity in ["error", "warning", "info", "style"]:
                count = report.by_severity.get(severity, 0)
                if count > 0:
                    severity_parts.append(f"{count} {severity}")
            if severity_parts:
                lines.append(f"- **By Severity:** {', '.join(severity_parts)}")

        if report.critical_issues:
            lines.append(f"- **Critical Issues:** {len(report.critical_issues)}")

        if report.auto_fixable:
            lines.append(f"- **Auto-fixable:** {len(report.auto_fixable)}")

        # Show trend if available
        if "direction" in report.trends:
            trend_emoji = {"improving": "📈", "worsening": "📉", "stable": "➡️"}.get(
                report.trends["direction"], "➡️"
            )
            lines.append(
                f"- **Trend:** {trend_emoji} {report.trends['direction'].title()}"
            )
        lines.append("")

        # Agent breakdown
        if report.by_agent:
            lines.append("### 📈 Agent Performance")
            for agent_name, summary in report.by_agent.items():
                severity_str = ", ".join(
                    f"{count} {sev}"
                    for sev, count in summary.severity_breakdown.items()
                )
                lines.append(
                    f"- **{agent_name}:** {summary.finding_count} findings ({severity_str})"
                )
            lines.append("")

        # Critical issues (top priority)
        if report.critical_issues:
            lines.append("### 🚨 Priority Issues")
            for i, finding in enumerate(report.critical_issues[:5], 1):  # Top 5
                location = f"{finding.file}:{finding.line or '?'}"
                message = finding.message[:100] + (
                    "..." if len(finding.message) > 100 else ""
                )
                lines.append(
                    f"{i}. **{finding.severity.value.title()}** in `{location}` - {message}"
                )
            lines.append("")

        # Auto-fixable items
        if report.auto_fixable and len(report.auto_fixable) > len(
            report.critical_issues
        ):
            non_critical_auto_fixable = [
                f for f in report.auto_fixable if f not in report.critical_issues
            ]
            if non_critical_auto_fixable:
                lines.append("### 🔧 Auto-fixable Issues")
                for i, finding in enumerate(non_critical_auto_fixable[:3], 1):  # Top 3
                    location = f"{finding.file}:{finding.line or '?'}"
                    message = finding.message[:80] + (
                        "..." if len(finding.message) > 80 else ""
                    )
                    lines.append(f"{i}. `{location}` - {message}")
                lines.append("")

        # Insights
        if report.insights:
            lines.append("### 💡 Insights")
            for insight in report.insights:
                lines.append(f"- {insight}")
            lines.append("")

        # Quick actions
        if report.auto_fixable:
            lines.append("### 🛠️ Quick Actions")
            lines.append(
                f"Run `devloop auto-fix` to apply {len(report.auto_fixable)} safe fixes automatically"
            )
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def format_json(report: SummaryReport) -> Dict[str, Any]:
        """Format summary report as JSON for API responses."""
        return {
            "summary": {
                "scope": report.scope,
                "total_findings": report.total_findings,
                "critical_count": len(report.critical_issues),
                "auto_fixable_count": len(report.auto_fixable),
                "trend": report.trends.get("direction", "stable"),
                "trend_percentage": report.trends.get("change_percent", 0.0),
            },
            "by_agent": {
                agent_name: {
                    "count": summary.finding_count,
                    "critical": sum(
                        1
                        for f in summary.top_issues
                        if f.severity.value == "error" or f.blocking
                    ),
                    "auto_fixable": sum(
                        1 for f in summary.top_issues if f.auto_fixable
                    ),
                }
                for agent_name, summary in report.by_agent.items()
            },
            "insights": report.insights,
            "critical_issues": [
                {
                    "file": issue.file,
                    "line": issue.line,
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "agent": issue.agent,
                }
                for issue in report.critical_issues[:5]
            ],
        }
