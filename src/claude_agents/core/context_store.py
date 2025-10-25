"""Context store for agent findings and coding agent integration."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_agents.core.agent import AgentResult


class ContextStore:
    """Manages agent findings for coding agent integration."""

    def __init__(self, base_path: str = ".claude/context"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def write_finding(
        self, result: AgentResult, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Write an agent finding to the context store."""
        if not result.success and not result.message:
            return  # Skip failed operations with no message

        finding = {
            "agent_name": result.agent_name,
            "timestamp": datetime.now().isoformat(),
            "success": result.success,
            "message": result.message,
            "error": result.error,
            "data": result.data or {},
            "metadata": metadata or {},
        }

        # Determine file based on agent type
        agent_type = self._get_agent_type(result.agent_name)
        findings_file = self.base_path / f"{agent_type}.json"

        # Read existing findings
        existing = self._read_findings(findings_file)

        # Add new finding
        existing.append(finding)

        # Keep only recent findings (last 100 per agent type)
        existing = existing[-100:]

        # Write back
        with open(findings_file, "w") as f:
            json.dump(existing, f, indent=2)

    def get_findings(self, agent_type: Optional[str] = None) -> Dict[str, List[Dict]]:
        """Get all findings, optionally filtered by agent type."""
        findings = {}

        if agent_type:
            findings_file = self.base_path / f"{agent_type}.json"
            findings[agent_type] = self._read_findings(findings_file)
        else:
            # Get all agent types
            for file_path in self.base_path.glob("*.json"):
                agent_type = file_path.stem
                findings[agent_type] = self._read_findings(file_path)

        return findings

    def clear_findings(self, agent_type: Optional[str] = None) -> None:
        """Clear findings, optionally for specific agent type."""
        if agent_type:
            findings_file = self.base_path / f"{agent_type}.json"
            if findings_file.exists():
                findings_file.unlink()
        else:
            for file_path in self.base_path.glob("*.json"):
                file_path.unlink()

    def get_actionable_findings(self) -> Dict[str, List[Dict]]:
        """Get findings that can be automatically acted upon."""
        all_findings = self.get_findings()
        actionable = {}

        for agent_type, findings in all_findings.items():
            actionable_findings = []
            for finding in findings:
                if self._is_actionable(finding):
                    actionable_findings.append(finding)

            if actionable_findings:
                actionable[agent_type] = actionable_findings

        return actionable

    def _read_findings(self, file_path: Path) -> List[Dict]:
        """Read findings from a file."""
        if not file_path.exists():
            return []

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                # Only return if it's a list of findings (our expected format)
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    return data
                else:
                    # Not our format, skip
                    return []
        except (json.JSONDecodeError, IOError, IndexError):
            return []

    def _get_agent_type(self, agent_name: str) -> str:
        """Map agent name to type."""
        # Extract base type from agent name (e.g., "linter" from "linter-1")
        base_name = agent_name.split("-")[0]
        return base_name

    def write_consolidated_results(self) -> None:
        """Write consolidated agent results for Claude Code integration."""
        all_findings = self.get_findings()

        # Build consolidated results
        consolidated = {"timestamp": datetime.now().isoformat(), "agents": {}}

        for agent_type, findings in all_findings.items():
            if not findings:
                continue

            # Get most recent finding for each agent
            latest = findings[-1]

            # Extract results summary from agent data
            agent_data = latest.get("data", {})

            consolidated["agents"][agent_type] = {
                "status": "success" if latest.get("success") else "failed",
                "timestamp": latest.get("timestamp"),
                "message": latest.get("message", ""),
                "results": self._extract_results_summary(
                    agent_type, agent_data, latest
                ),
            }

        # Write consolidated file
        results_file = self.base_path / "agent-results.json"
        with open(results_file, "w") as f:
            json.dump(consolidated, f, indent=2)

    def _extract_results_summary(
        self, agent_type: str, data: Dict, finding: Dict
    ) -> Dict[str, Any]:
        """Extract results summary from agent data."""
        summary = {}

        if agent_type == "linter":
            summary["issues_found"] = len(data.get("issues", []))
            summary["auto_fixable"] = sum(
                1 for issue in data.get("issues", []) if issue.get("fixable", False)
            )
            summary["files_checked"] = 1 if data.get("file") else 0

        elif agent_type == "test-runner":
            summary["passed"] = data.get("passed", 0)
            summary["failed"] = data.get("failed", 0)
            summary["total"] = data.get("total", 0)
            summary["duration"] = data.get("duration", 0)

        elif agent_type == "formatter":
            summary["needs_formatting"] = data.get("needs_formatting", False)
            summary["files_formatted"] = 1 if data.get("needs_formatting") else 0
            summary["formatter_used"] = data.get("formatter", "")

        elif agent_type == "security-scanner" or agent_type == "security":
            summary["vulnerabilities_found"] = len(data.get("issues", []))
            summary["high_severity"] = sum(
                1 for issue in data.get("issues", []) if issue.get("severity") == "high"
            )
            summary["medium_severity"] = sum(
                1
                for issue in data.get("issues", [])
                if issue.get("severity") == "medium"
            )

        elif agent_type == "type-checker" or agent_type == "type":
            summary["issues_found"] = len(data.get("issues", []))
            summary["errors"] = sum(
                1
                for issue in data.get("issues", [])
                if issue.get("severity") == "error"
            )
            summary["warnings"] = sum(
                1
                for issue in data.get("issues", [])
                if issue.get("severity") == "warning"
            )

        elif agent_type == "performance-profiler" or agent_type == "performance":
            summary["functions_analyzed"] = data.get("functions_analyzed", 0)
            summary["high_complexity"] = len(data.get("high_complexity_functions", []))
            complexity_summary = data.get("complexity_summary", {})
            summary["average_complexity"] = complexity_summary.get(
                "average_complexity", 0
            )

        else:
            # Generic summary for unknown agent types
            summary["message"] = finding.get("message", "")
            summary["success"] = finding.get("success", False)

        return summary

    def _is_actionable(self, finding: Dict) -> bool:
        """Determine if a finding can be automatically acted upon."""
        agent_name = finding.get("agent_name", "")
        message = finding.get("message", "").lower()
        error = finding.get("error", "").lower()
        success = finding.get("success", False)

        # Check successful findings first
        if success:
            # Linter: Auto-fix safe issues
            if agent_name.startswith("linter"):
                # Auto-fix import sorting, unused imports, etc.
                return any(
                    keyword in message
                    for keyword in [
                        "unused import",
                        "import sort",
                        "whitespace",
                        "indentation",
                    ]
                )

            # Formatter: Auto-format if needed
            elif agent_name.startswith("formatter"):
                return "would format" in message or "needs formatting" in message

            # Test runner: Not typically auto-actionable
            elif agent_name.startswith("test-runner"):
                return False

            return False

        # Check failed findings for error messages that indicate fixable code issues
        else:
            # Linter errors that indicate syntax or import issues
            if agent_name.startswith("linter"):
                # Syntax errors, import errors, etc.
                return any(
                    keyword in error
                    for keyword in [
                        "syntax",
                        "import",
                        "indentation",
                        "undefined",
                        "unexpected",
                        "invalid syntax",
                        "nameerror",
                    ]
                )

            # Formatter errors (usually configuration issues, not code issues)
            elif agent_name.startswith("formatter"):
                return False  # Formatter errors are usually config-related

            # Type checker errors that indicate real code issues
            elif agent_name.startswith("type-checker"):
                return any(
                    keyword in error
                    for keyword in ["type", "annotation", "mypy", "attribute", "module"]
                )

            # Test runner errors that might indicate code issues
            elif agent_name.startswith("test-runner"):
                return any(
                    keyword in error
                    for keyword in ["syntax", "import", "attribute", "module"]
                )

            return False


# Global instance
context_store = ContextStore()
