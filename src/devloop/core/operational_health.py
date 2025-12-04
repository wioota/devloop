"""Operational health and performance analytics for DevLoop."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class HealthStatus:
    """System health status."""
    overall_status: str  # HEALTHY, DEGRADED, UNHEALTHY
    passed_checks: int
    failed_checks: int
    total_checks: int
    last_check: Optional[datetime]
    check_details: list


@dataclass
class AgentPerformance:
    """Per-agent performance metrics."""
    agent_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_duration: float
    success_rate: float


@dataclass
class ActivityTimeline:
    """Activity and run frequency metrics."""
    last_run: Optional[datetime]
    time_since_last_run: str
    estimated_frequency: str  # e.g., "~5 runs/day"


class OperationalHealthAnalyzer:
    """Analyze operational health and performance of DevLoop."""

    def __init__(self, devloop_dir: Path):
        self.devloop_dir = devloop_dir
        self.health_file = devloop_dir / "health_check.json"
        self.performance_file = devloop_dir / "feedback" / "performance.json"
        self.context_dir = devloop_dir / "context"
        self.log_file = devloop_dir / "devloop.log"

    def get_health_status(self) -> HealthStatus:
        """Get current system health status."""
        if not self.health_file.exists():
            return HealthStatus(
                overall_status="UNKNOWN",
                passed_checks=0,
                failed_checks=0,
                total_checks=0,
                last_check=None,
                check_details=[]
            )

        try:
            with open(self.health_file) as f:
                data = json.load(f)

            summary = data.get("summary", {})
            last_check = None
            if data.get("details"):
                try:
                    last_check = datetime.fromisoformat(
                        data["details"][0]["timestamp"].replace("+00:00", "+00:00")
                    )
                except (ValueError, IndexError, KeyError):
                    pass

            return HealthStatus(
                overall_status=summary.get("status", "UNKNOWN"),
                passed_checks=summary.get("passed", 0),
                failed_checks=summary.get("failed", 0),
                total_checks=summary.get("total_checks", 0),
                last_check=last_check,
                check_details=data.get("details", [])
            )
        except Exception as e:
            return HealthStatus(
                overall_status="ERROR",
                passed_checks=0,
                failed_checks=0,
                total_checks=0,
                last_check=None,
                check_details=[{"error": str(e)}]
            )

    def get_agent_performance(self) -> Dict[str, AgentPerformance]:
        """Get per-agent performance metrics."""
        if not self.performance_file.exists():
            return {}

        try:
            with open(self.performance_file) as f:
                data = json.load(f)

            performance = {}
            for agent_name, metrics in data.items():
                total = metrics.get("total_executions", 0)
                successful = metrics.get("successful_executions", 0)
                failed = total - successful
                avg_duration = metrics.get("average_duration", 0)
                success_rate = (successful / total * 100) if total > 0 else 0

                performance[agent_name] = AgentPerformance(
                    agent_name=agent_name,
                    total_executions=total,
                    successful_executions=successful,
                    failed_executions=failed,
                    average_duration=avg_duration,
                    success_rate=success_rate
                )

            return performance
        except Exception:
            return {}

    def get_activity_timeline(self) -> ActivityTimeline:
        """Get activity timeline and frequency metrics."""
        last_run = None
        time_since = "unknown"
        frequency = "unknown"

        if self.log_file.exists():
            try:
                last_mod_time = datetime.fromtimestamp(self.log_file.stat().st_mtime)
                last_run = last_mod_time

                # Calculate time since last run
                time_diff = datetime.now() - last_mod_time
                if time_diff.total_seconds() < 60:
                    time_since = "just now"
                elif time_diff.total_seconds() < 3600:
                    mins = int(time_diff.total_seconds() / 60)
                    time_since = f"{mins} minute{'s' if mins > 1 else ''} ago"
                elif time_diff.total_seconds() < 86400:
                    hours = int(time_diff.total_seconds() / 3600)
                    time_since = f"{hours} hour{'s' if hours > 1 else ''} ago"
                else:
                    days = int(time_diff.total_seconds() / 86400)
                    time_since = f"{days} day{'s' if days > 1 else ''} ago"

                # Estimate frequency from log file size and modification history
                # Rough estimate: ~1KB per run
                file_size = self.log_file.stat().st_size
                estimated_runs = max(1, file_size // 1024)

                # Estimate daily frequency (assuming logs are from past ~30 days)
                daily_estimate = max(1, estimated_runs // 7)  # Conservative estimate
                frequency = f"~{daily_estimate} run{'s' if daily_estimate > 1 else ''}/day"

            except Exception:
                pass

        return ActivityTimeline(
            last_run=last_run,
            time_since_last_run=time_since,
            estimated_frequency=frequency
        )

    def get_findings_summary(self) -> Dict[str, Any]:
        """Get summary of findings by urgency level."""
        index_file = self.context_dir / "index.json"
        if not index_file.exists():
            return {
                "immediate": 0,
                "relevant": 0,
                "deferred": 0,
                "by_agent": {}
            }

        try:
            with open(index_file) as f:
                data = json.load(f)

            return {
                "immediate": data.get("check_now", {}).get("count", 0),
                "relevant": data.get("mention_if_relevant", {}).get("count", 0),
                "deferred": data.get("deferred", {}).get("count", 0),
                "auto_fixed": data.get("auto_fixed", {}).get("count", 0),
            }
        except Exception:
            return {
                "immediate": 0,
                "relevant": 0,
                "deferred": 0,
                "auto_fixed": 0,
            }

    def get_agent_breakdown(self) -> Dict[str, int]:
        """Get finding breakdown by agent type."""
        relevant_file = self.context_dir / "relevant.json"
        if not relevant_file.exists():
            return {}

        try:
            with open(relevant_file) as f:
                data = json.load(f)

            breakdown = {}
            for finding in data.get("findings", []):
                agent = finding.get("agent", "unknown")
                breakdown[agent] = breakdown.get(agent, 0) + 1

            return breakdown
        except Exception:
            return {}

    def generate_health_report(self) -> str:
        """Generate a comprehensive health report."""
        health = self.get_health_status()
        performance = self.get_agent_performance()
        timeline = self.get_activity_timeline()
        findings = self.get_findings_summary()
        agent_breakdown = self.get_agent_breakdown()

        lines = []

        # Health indicator
        health_emoji = {
            "HEALTHY": "✅",
            "DEGRADED": "⚠️",
            "UNHEALTHY": "❌",
            "UNKNOWN": "❓"
        }.get(health.overall_status, "❓")

        lines.append(f"### {health_emoji} System Health: {health.overall_status}")
        lines.append(f"- Checks: {health.passed_checks}/{health.total_checks} passed")
        if health.last_check:
            lines.append(f"- Last check: {health.last_check.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Activity
        lines.append("### ⏱️ Activity")
        lines.append(f"- Last run: {timeline.time_since_last_run}")
        lines.append(f"- Frequency: {timeline.estimated_frequency}")
        lines.append("")

        # Agent performance
        if performance:
            lines.append("### 🏃 Agent Performance")
            for agent_name, perf in sorted(performance.items()):
                duration_ms = perf.average_duration * 1000
                status = "✅" if perf.success_rate == 100 else "⚠️"
                lines.append(
                    f"- {status} **{agent_name}**: "
                    f"{perf.total_executions} runs, "
                    f"{perf.success_rate:.0f}% success, "
                    f"avg {duration_ms:.1f}ms"
                )
            lines.append("")

        # Findings summary
        total_findings = findings["immediate"] + findings["relevant"] + findings["deferred"]
        lines.append("### 📋 Findings")
        lines.append(f"- **Immediate:** {findings['immediate']} (critical)")
        lines.append(f"- **Relevant:** {findings['relevant']} (should review)")
        lines.append(f"- **Deferred:** {findings['deferred']} (background)")
        lines.append(f"- **Auto-fixed:** {findings['auto_fixed']}")
        lines.append(f"- **Total:** {total_findings}")

        if agent_breakdown:
            lines.append("")
            lines.append("### 📊 Findings by Agent")
            for agent, count in sorted(agent_breakdown.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- **{agent}:** {count}")

        lines.append("")

        return "\n".join(lines)
