#!/usr/bin/env python3
"""
Claude Code adapter for background agent integration.
Provides utilities for Claude Code to:
- Access background agent findings from context store
- Run verification checks (unified with Amp/Git hooks)
- Extract findings to Beads issues
- Show enforcement status and recommendations
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List


class ClaudeCodeAdapter:
    """Adapter for Claude Code to interact with background agent context store"""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.context_dir = self.project_root / ".claude" / "context"
        self.verify_script = self.project_root / ".agents" / "verify-common-checks"
        self.extract_script = (
            self.project_root / ".agents" / "hooks" / "extract-findings-to-beads"
        )

    def check_results(self) -> Dict[str, Any]:
        """Check recent background agent results (for hooks and quick checks)"""

        index_file = self.context_dir / "index.json"

        if not index_file.exists():
            return {
                "status": "no_results",
                "message": "Background agents haven't run yet or context store not initialized",
                "actionable": False,
                "display": "No background agent findings",
            }

        try:
            with open(index_file, "r") as f:
                index = json.load(f)

            check_now = index.get("check_now", {})
            check_now_count = check_now.get("count", 0)

            # Quick determination if there are actionable items
            actionable = check_now_count > 0

            if actionable:
                # Get immediate findings for details
                immediate_findings = self._get_findings("immediate")
                display = self._format_immediate_display(check_now, immediate_findings)
            else:
                display = "✅ No immediate issues from background agents"

            return {
                "status": "success",
                "actionable": actionable,
                "check_now_count": check_now_count,
                "index": index,
                "display": display,
                "timestamp": index.get("last_updated"),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to check results: {str(e)}",
                "display": f"Error reading agent results: {str(e)}",
            }

    def get_detailed_findings(self, tier: str = "all") -> Dict[str, Any]:
        """Get detailed findings for Claude Code to analyze"""

        if tier == "all":
            tiers = ["immediate", "relevant", "background", "auto_fixed"]
        else:
            tiers = [tier]

        findings = {}
        for t in tiers:
            findings[t] = self._get_findings(t)

        return {
            "status": "success",
            "findings": findings,
            "summary": self._create_detailed_summary(findings),
        }

    def get_agent_insights(self, query_type: str = "general") -> Dict[str, Any]:
        """Get insights for Claude Code skills"""

        index_file = self.context_dir / "index.json"

        if not index_file.exists():
            return {
                "status": "no_results",
                "insights": ["Background agents haven't run yet"],
            }

        try:
            with open(index_file, "r") as f:
                index = json.load(f)

            immediate_findings = self._get_findings("immediate")
            relevant_findings = self._get_findings("relevant")

            insights = {"status": "success", "query_type": query_type, "insights": []}

            # Generate insights based on query type
            if query_type == "lint":
                insights["insights"] = self._get_lint_insights(
                    immediate_findings, relevant_findings
                )
            elif query_type == "test":
                insights["insights"] = self._get_test_insights(
                    immediate_findings, relevant_findings
                )
            elif query_type == "security":
                insights["insights"] = self._get_security_insights(
                    immediate_findings, relevant_findings
                )
            elif query_type == "format":
                insights["insights"] = self._get_format_insights(
                    immediate_findings, relevant_findings
                )
            else:
                insights["insights"] = self._get_general_insights(
                    index, immediate_findings
                )

            return insights

        except Exception as e:
            return {"status": "error", "insights": [f"Error: {str(e)}"]}

    def _get_findings(self, tier: str) -> List[Dict[str, Any]]:
        """Get findings from a specific tier file"""
        tier_file = self.context_dir / f"{tier}.json"

        if not tier_file.exists():
            return []

        try:
            with open(tier_file, "r") as f:
                data = json.load(f)
                return data.get("findings", [])
        except Exception:
            return []

    def _format_immediate_display(
        self, check_now: Dict[str, Any], findings: List[Dict[str, Any]]
    ) -> str:
        """Format immediate findings for display"""
        count = check_now.get("count", 0)

        if count == 0:
            return "✅ No immediate issues"

        # Group by file
        by_file: Dict[str, List[Dict[str, Any]]] = {}
        for finding in findings:
            file_path = finding.get("file", "unknown")
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(finding)

        lines = [f"⚠️ {count} immediate issue(s) found:", ""]

        for file_path, file_findings in list(by_file.items())[:3]:  # Show max 3 files
            file_name = Path(file_path).name
            lines.append(f"📄 {file_name}:")
            for finding in file_findings[:3]:  # Show max 3 findings per file
                severity = finding.get("severity", "info")
                emoji = (
                    "🔴"
                    if severity == "error"
                    else "🟡" if severity == "warning" else "🔵"
                )
                message = finding.get("message", "No message")
                line = finding.get("line")
                location = f":{line}" if line else ""
                lines.append(f"  {emoji} {message} {location}")

        if len(by_file) > 3:
            lines.append(f"\n... and {len(by_file) - 3} more files")

        return "\n".join(lines)

    def _create_detailed_summary(self, findings: Dict[str, List]) -> str:
        """Create a detailed summary of all findings"""
        lines = ["Background Agent Findings Summary", "=" * 40]

        for tier, tier_findings in findings.items():
            if tier_findings:
                lines.append(f"\n{tier.upper()} ({len(tier_findings)} findings):")

                # Group by agent
                by_agent: Dict[str, List[Dict[str, Any]]] = {}
                for finding in tier_findings:
                    agent = finding.get("agent", "unknown")
                    if agent not in by_agent:
                        by_agent[agent] = []
                    by_agent[agent].append(finding)

                for agent, agent_findings in by_agent.items():
                    lines.append(f"  {agent}: {len(agent_findings)} findings")

        return "\n".join(lines)

    def _get_lint_insights(self, immediate: List, relevant: List) -> List[str]:
        """Get lint-specific insights from findings"""
        insights = []

        lint_findings = [f for f in immediate + relevant if f.get("agent") == "linter"]

        if not lint_findings:
            insights.append("✅ No linting issues found")
            return insights

        errors = [f for f in lint_findings if f.get("severity") == "error"]
        warnings = [f for f in lint_findings if f.get("severity") == "warning"]
        auto_fixable = [f for f in lint_findings if f.get("auto_fixable")]

        insights.append(f"Found {len(lint_findings)} linting issue(s):")
        if errors:
            insights.append(f"  • {len(errors)} errors")
        if warnings:
            insights.append(f"  • {len(warnings)} warnings")
        if auto_fixable:
            insights.append(f"  • {len(auto_fixable)} auto-fixable")
            insights.append("  💡 Consider running auto-fix")

        # Show top issues
        for finding in lint_findings[:3]:
            file_name = Path(finding.get("file", "")).name
            message = finding.get("message", "")
            insights.append(f"  - {file_name}: {message}")

        return insights

    def _get_test_insights(self, immediate: List, relevant: List) -> List[str]:
        """Get test-specific insights"""
        insights = []

        test_findings = [
            f for f in immediate + relevant if f.get("agent") == "test-runner"
        ]

        if not test_findings:
            insights.append("✅ No test failures")
            return insights

        insights.append(f"⚠️ {len(test_findings)} test issue(s) found:")

        for finding in test_findings[:5]:
            message = finding.get("message", "")
            insights.append(f"  • {message}")

        return insights

    def _get_security_insights(self, immediate: List, relevant: List) -> List[str]:
        """Get security-specific insights"""
        insights = []

        sec_findings = [
            f for f in immediate + relevant if f.get("agent") == "security-scanner"
        ]

        if not sec_findings:
            insights.append("✅ No security issues detected")
            return insights

        high = [f for f in sec_findings if f.get("blocking")]

        insights.append(f"🔒 {len(sec_findings)} security issue(s) found:")
        if high:
            insights.append(f"  ⚠️ {len(high)} high-priority (blocking)")

        for finding in sec_findings[:3]:
            message = finding.get("message", "")
            severity = finding.get("severity", "info")
            insights.append(f"  • [{severity.upper()}] {message}")

        return insights

    def _get_format_insights(self, immediate: List, relevant: List) -> List[str]:
        """Get formatting-specific insights"""
        insights = []

        format_findings = [
            f for f in immediate + relevant if f.get("agent") == "formatter"
        ]

        if not format_findings:
            insights.append("✅ No formatting issues")
            return insights

        insights.append(f"📝 {len(format_findings)} formatting issue(s):")

        for finding in format_findings[:5]:
            message = finding.get("message", "")
            insights.append(f"  • {message}")

        return insights

    def _get_general_insights(self, index: Dict, immediate: List) -> List[str]:
        """Get general insights across all agents"""
        insights = []

        check_now = index.get("check_now", {})
        check_count = check_now.get("count", 0)

        if check_count == 0:
            insights.append("✅ All background checks passed - looking good!")
            return insights

        severity_breakdown = check_now.get("severity_breakdown", {})

        insights.append(f"⚠️ {check_count} immediate issue(s) need attention:")

        for severity, count in severity_breakdown.items():
            if count > 0:
                emoji = (
                    "🔴"
                    if severity == "error"
                    else "🟡" if severity == "warning" else "🔵"
                )
                insights.append(f"  {emoji} {count} {severity}(s)")

        # Group by agent
        by_agent: Dict[str, int] = {}
        for finding in immediate:
            agent = finding.get("agent", "unknown")
            if agent not in by_agent:
                by_agent[agent] = 0
            by_agent[agent] += 1

        insights.append("\nBy agent:")
        for agent, count in by_agent.items():
            insights.append(f"  • {agent}: {count}")

        # Show auto-fixable
        auto_fixable = [f for f in immediate if f.get("auto_fixable")]
        if auto_fixable:
            insights.append(f"\n💡 {len(auto_fixable)} issue(s) can be auto-fixed")

        return insights

    def run_verification(self) -> Dict[str, Any]:
        """Run unified code quality verification (same as Amp post-task hook).

        Returns:
            Dict with verification results, messages, and enforcement status
        """
        if not self.verify_script.exists():
            return {
                "status": "error",
                "message": "Verification script not found",
                "verified": False,
                "can_proceed": False,
            }

        try:
            result = subprocess.run(
                [str(self.verify_script)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Parse output for status
            output = result.stdout + result.stderr
            passed = result.returncode == 0

            # Extract key results from output
            has_failures = "❌" in output or "FAIL" in output
            blocking_issues = []
            warnings = []

            if has_failures:
                lines = output.split("\n")
                for line in lines:
                    if "❌" in line or "ERROR:" in line:
                        blocking_issues.append(line.strip())
                    elif "⚠️" in line or "Warning" in line:
                        warnings.append(line.strip())

            return {
                "status": "success" if passed else "failed",
                "verified": passed,
                "can_proceed": passed,
                "blocking_issues": blocking_issues,
                "warnings": warnings,
                "output": output,
                "message": (
                    "✅ All checks passed"
                    if passed
                    else "❌ Verification failed - see issues above"
                ),
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "verified": False,
                "can_proceed": False,
                "message": "Verification timed out after 120 seconds",
            }
        except Exception as e:
            return {
                "status": "error",
                "verified": False,
                "can_proceed": False,
                "message": f"Verification error: {str(e)}",
            }

    def extract_findings(self) -> Dict[str, Any]:
        """Extract DevLoop findings and create Beads issues (same as Amp post-task hook).

        Returns:
            Dict with extraction results and created issue IDs
        """
        if not self.extract_script.exists():
            return {
                "status": "error",
                "message": "Extraction script not found",
                "extracted": False,
                "issues_created": 0,
            }

        try:
            result = subprocess.run(
                [str(self.extract_script)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=60,
            )

            output = result.stdout + result.stderr
            passed = result.returncode == 0

            # Parse created issues from output
            created_issues = []
            for line in output.split("\n"):
                if "Created" in line and ": " in line:
                    # Extract issue ID from output like "Created formatter issue: claude-agents-xyz"
                    parts = line.split(": ")
                    if len(parts) > 1:
                        created_issues.append(parts[-1].strip())

            return {
                "status": "success" if passed else "partial",
                "extracted": passed,
                "issues_created": len(created_issues),
                "issue_ids": created_issues,
                "output": output,
                "message": f"Extracted findings: {len(created_issues)} Beads issue(s) created",
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "extracted": False,
                "issues_created": 0,
                "message": "Findings extraction timed out",
            }
        except Exception as e:
            return {
                "status": "error",
                "extracted": False,
                "issues_created": 0,
                "message": f"Extraction error: {str(e)}",
            }

    def verify_and_extract(self) -> Dict[str, Any]:
        """Run full verification and extraction workflow (like Amp post-task).

        Combines verification with findings extraction for complete enforcement.
        """
        verification = self.run_verification()
        extraction = self.extract_findings()

        return {
            "status": verification.get("status"),
            "verification": verification,
            "extraction": extraction,
            "verified": verification.get("verified", False),
            "can_save": verification.get(
                "verified", False
            ),  # Claude Code: block save if verification fails?
            "summary": {
                "checks_passed": verification.get("verified", False),
                "issues_found": len(verification.get("blocking_issues", [])),
                "warnings": len(verification.get("warnings", [])),
                "beads_issues_created": extraction.get("issues_created", 0),
            },
        }


def main():
    """Command-line interface for the adapter"""
    import argparse

    parser = argparse.ArgumentParser(description="Claude Code Background Agent Adapter")
    parser.add_argument(
        "command",
        choices=[
            "check_results",
            "insights",
            "detailed",
            "verify",
            "extract",
            "verify-and-extract",
        ],
    )
    parser.add_argument(
        "--query-type",
        choices=["general", "lint", "test", "security", "format"],
        default="general",
        help="Type of insights to get",
    )
    parser.add_argument(
        "--tier",
        choices=["all", "immediate", "relevant", "background", "auto_fixed"],
        default="all",
        help="Tier of findings to get",
    )
    parser.add_argument(
        "--format", choices=["json", "text"], default="json", help="Output format"
    )

    args = parser.parse_args()

    adapter = ClaudeCodeAdapter()

    if args.command == "check_results":
        result = adapter.check_results()
    elif args.command == "insights":
        result = adapter.get_agent_insights(args.query_type)
    elif args.command == "detailed":
        result = adapter.get_detailed_findings(args.tier)
    elif args.command == "verify":
        result = adapter.run_verification()
    elif args.command == "extract":
        result = adapter.extract_findings()
    elif args.command == "verify-and-extract":
        result = adapter.verify_and_extract()

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        # Text format - just print the display or insights
        if "display" in result:
            print(result["display"])
        elif "insights" in result:
            for insight in result["insights"]:
                print(insight)
        elif "summary" in result:
            print(result["summary"])


if __name__ == "__main__":
    main()
