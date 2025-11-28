#!/usr/bin/env python3
"""
Amp adapter for background agent integration.
Provides utilities for Amp subagents to access background agent results.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

class AmpAdapter:
    """Adapter for Amp subagents to interact with background agents"""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.context_dir = self.project_root / ".claude" / "context"

    def get_agent_results(self, agent_name: Optional[str] = None,
                         since_minutes: Optional[int] = None) -> Dict[str, Any]:
        """Get background agent results, optionally filtered by agent or time"""

        results_file = self.context_dir / "agent-results.json"

        if not results_file.exists():
            return {
                "status": "no_results",
                "message": "No background agent results found yet",
                "agents": {}
            }

        try:
            with open(results_file, 'r') as f:
                data = json.load(f)

            # Filter by time if requested
            if since_minutes:
                cutoff = datetime.now() - timedelta(minutes=since_minutes)
                data = self._filter_by_time(data, cutoff)

            # Filter by agent if requested
            if agent_name:
                if agent_name in data.get("agents", {}):
                    return {
                        "status": "success",
                        "agent": agent_name,
                        "results": data["agents"][agent_name],
                        "timestamp": data.get("timestamp")
                    }
                else:
                    return {
                        "status": "agent_not_found",
                        "message": f"No results found for agent: {agent_name}",
                        "available_agents": list(data.get("agents", {}).keys())
                    }

            return {
                "status": "success",
                "results": data,
                "agent_count": len(data.get("agents", {})),
                "available_agents": list(data.get("agents", {}).keys())
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to read agent results: {str(e)}"
            }

    def get_recent_activity(self, minutes: int = 30) -> Dict[str, Any]:
        """Get recent background agent activity"""

        results_file = self.context_dir / "activity-log.json"

        if not results_file.exists():
            return {
                "status": "no_activity",
                "message": "No recent activity found"
            }

        try:
            with open(results_file, 'r') as f:
                activities = json.load(f)

            cutoff = datetime.now() - timedelta(minutes=minutes)
            recent = self._filter_activities_by_time(activities, cutoff)

            return {
                "status": "success",
                "recent_activities": recent,
                "count": len(recent),
                "time_window_minutes": minutes
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to read activity log: {str(e)}"
            }

    def get_auto_fixable_issues(self, agent_filter: Optional[str] = None,
                               safety_level: str = "safe_only") -> Dict[str, Any]:
        """Get auto-fixable issues that can be safely applied."""

        from auto_fix_engine import AutoFixEngine

        engine = AutoFixEngine(self.project_root)
        fixes = engine.get_auto_fixable_issues(agent_filter)

        # Filter by safety level
        safe_fixes = [fix for fix in fixes if self._is_safe_to_apply(fix, safety_level)]

        return {
            "status": "success",
            "auto_fixable_issues": safe_fixes,
            "total_count": len(fixes),
            "safe_count": len(safe_fixes),
            "safety_level": safety_level,
            "recommendations": self._generate_fix_recommendations(safe_fixes)
        }

    def apply_auto_fixes(self, agent_filter: Optional[str] = None,
                        safety_level: str = "safe_only") -> Dict[str, Any]:
        """Apply auto-fixable issues automatically."""

        from auto_fix_engine import AutoFixEngine

        engine = AutoFixEngine(self.project_root)
        fixes = engine.get_auto_fixable_issues(agent_filter)

        # Filter by safety level
        safe_fixes = [fix for fix in fixes if self._is_safe_to_apply(fix, safety_level)]

        if not safe_fixes:
            return {
                "status": "no_fixes",
                "message": f"No auto-fixable issues found at safety level '{safety_level}'"
            }

        result = engine.apply_auto_fixes(safe_fixes, safety_level)

        return {
            "status": "completed",
            "applied_fixes": result["applied"],
            "skipped_fixes": result["skipped"],
            "errors": result["errors"],
            "summary": result["summary"],
            "user_notification": self._create_user_notification(result)
        }

    def _is_safe_to_apply(self, fix: Dict[str, Any], safety_level: str) -> bool:
        """Check if a fix is safe to apply."""

        fix_safety = fix.get("safety_level", "unknown")

        if safety_level == "safe_only":
            return fix_safety == "safe"
        elif safety_level == "medium_risk":
            return fix_safety in ["safe", "medium"]
        elif safety_level == "all":
            return True

        return False

    def _generate_fix_recommendations(self, fixes: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations for applying fixes."""

        recommendations = []

        if not fixes:
            return ["No auto-fixable issues found"]

        # Group by type
        lint_fixes = [f for f in fixes if f["type"] == "lint_fix"]
        format_fixes = [f for f in fixes if f["type"] == "format_fix"]

        if lint_fixes:
            recommendations.append(f"Apply {len(lint_fixes)} automatic lint fixes")
        if format_fixes:
            recommendations.append(f"Apply {len(format_fixes)} automatic formatting fixes")

        recommendations.append("All fixes are low-risk and can be safely auto-applied")
        recommendations.append("Fixes will be backed up and can be rolled back if needed")

        return recommendations

    def _create_user_notification(self, result: Dict[str, Any]) -> str:
        """Create a user-friendly notification of applied fixes."""

        applied = result["summary"]["applied_count"]
        skipped = result["summary"]["skipped_count"]
        errors = result["summary"]["error_count"]

        if applied == 0:
            return "No fixes were applied"

        message = f"✅ Auto-applied {applied} fixes"

        if skipped > 0:
            message += f" ({skipped} skipped due to safety settings)"
        if errors > 0:
            message += f" ({errors} errors occurred)"

        return message

    def summarize_status(self) -> Dict[str, Any]:
        """Provide a human-readable summary of current background agent status"""

        results = self.get_agent_results()

        if results["status"] != "success":
            return results

        agents = results["results"].get("agents", {})
        summary = []
        issues = []
        recommendations = []

        for agent_name, agent_data in agents.items():
            status = agent_data.get("status", "unknown")
            agent_results = agent_data.get("results", {})

            if agent_name == "linter":
                issues_found = agent_results.get("issues_found", 0)
                auto_fixable = agent_results.get("auto_fixable", 0)
                summary.append(f"Linter: {issues_found} issues found ({auto_fixable} auto-fixable)")
                if issues_found > 0:
                    issues.append(f"{issues_found} lint issues detected")
                    if auto_fixable > 0:
                        recommendations.append(f"Consider auto-fixing {auto_fixable} lint issues")

            elif agent_name == "test-runner":
                passed = agent_results.get("passed", 0)
                failed = agent_results.get("failed", 0)
                summary.append(f"Tests: {passed} passed, {failed} failed")
                if failed > 0:
                    issues.append(f"{failed} tests failing")
                    recommendations.append("Address failing tests before proceeding")

            elif agent_name == "formatter":
                formatted = agent_results.get("files_formatted", 0)
                if formatted > 0:
                    summary.append(f"Formatter: {formatted} files formatted")

            elif agent_name == "security-scanner":
                vulnerabilities = agent_results.get("vulnerabilities_found", 0)
                if vulnerabilities > 0:
                    summary.append(f"Security: {vulnerabilities} issues found")
                    issues.append(f"{vulnerabilities} security vulnerabilities detected")
                    recommendations.append("Review security findings")

        return {
            "status": "success",
            "summary": summary,
            "issues": issues,
            "recommendations": recommendations,
            "overall_health": "good" if not issues else "needs_attention"
        }

    def _filter_by_time(self, data: Dict[str, Any], cutoff: datetime) -> Dict[str, Any]:
        """Filter results by timestamp"""
        if "timestamp" in data:
            result_time = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
            if result_time < cutoff:
                return {"agents": {}}

        return data

    def _filter_activities_by_time(self, activities: list, cutoff: datetime) -> list:
        """Filter activities by timestamp"""
        recent = []
        for activity in activities:
            if "timestamp" in activity:
                activity_time = datetime.fromisoformat(activity["timestamp"].replace('Z', '+00:00'))
                if activity_time >= cutoff:
                    recent.append(activity)
        return recent


def main():
    """Command-line interface for the adapter"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Amp Background Agent Adapter")
    parser.add_argument("command", choices=["status", "results", "activity", "summary", "auto-fixes", "apply-fixes"])
    parser.add_argument("--agent", help="Specific agent to query")
    parser.add_argument("--minutes", type=int, default=30, help="Time window in minutes")
    parser.add_argument("--safety", choices=["safe_only", "medium_risk", "all"],
                       default="safe_only", help="Safety level for auto-fixes")

    args = parser.parse_args()

    adapter = AmpAdapter()

    if args.command == "status":
        result = adapter.summarize_status()
    elif args.command == "results":
        result = adapter.get_agent_results(args.agent)
    elif args.command == "activity":
        result = adapter.get_recent_activity(args.minutes)
    elif args.command == "summary":
        result = adapter.summarize_status()
    elif args.command == "auto-fixes":
        result = adapter.get_auto_fixable_issues(args.agent, args.safety)
    elif args.command == "apply-fixes":
        result = adapter.apply_auto_fixes(args.agent, args.safety)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
