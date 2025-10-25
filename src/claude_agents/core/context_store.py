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

    def write_finding(self, result: AgentResult, metadata: Optional[Dict[str, Any]] = None) -> None:
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
        with open(findings_file, 'w') as f:
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
            with open(file_path, 'r') as f:
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
        base_name = agent_name.split('-')[0]
        return base_name

    def _is_actionable(self, finding: Dict) -> bool:
        """Determine if a finding can be automatically acted upon."""
        # Skip failed findings
        if not finding.get("success", False):
            return False

        agent_name = finding.get("agent_name", "")
        message = finding.get("message", "").lower()

        # Linter: Auto-fix safe issues
        if agent_name.startswith("linter"):
            # Auto-fix import sorting, unused imports, etc.
            return any(keyword in message for keyword in [
                "unused import", "import sort", "whitespace", "indentation"
            ])

        # Formatter: Auto-format if needed
        elif agent_name.startswith("formatter"):
            return "would format" in message or "needs formatting" in message

        # Test runner: Not typically auto-actionable
        elif agent_name.startswith("test-runner"):
            return False

        return False


# Global instance
context_store = ContextStore()
