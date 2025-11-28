"""
Context Reader - Utility for coding agents to read agent findings.

This module provides a simple interface for coding agents (like Claude Code)
to access findings from background agents.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from .context import FileFindings


class ContextReader:
    """Reader for agent findings stored in .claude/context/."""

    def __init__(self, base_path: Path = Path(".claude/context")):
        self.base_path = base_path

    def get_all_findings(self) -> Dict[str, List[FileFindings]]:
        """Get all findings from all agents."""
        findings = {}
        if not self.base_path.exists():
            return findings

        for json_file in self.base_path.glob("*.json"):
            agent_name = json_file.stem
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    findings[agent_name] = [
                        FileFindings(**file_data) for file_data in data.get("files", [])
                    ]
            except (json.JSONDecodeError, FileNotFoundError):
                continue

        return findings

    def get_agent_findings(self, agent_name: str) -> List[FileFindings]:
        """Get findings for a specific agent."""
        json_file = self.base_path / f"{agent_name}.json"
        if not json_file.exists():
            return []

        try:
            with open(json_file) as f:
                data = json.load(f)
                return [
                    FileFindings(**file_data) for file_data in data.get("files", [])
                ]
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def get_file_findings(self, file_path: str) -> Dict[str, List[FileFindings]]:
        """Get findings for a specific file from all agents."""
        all_findings = self.get_all_findings()
        file_findings = {}

        for agent_name, file_findings_list in all_findings.items():
            matching_files = [
                ff for ff in file_findings_list if ff.file_path == file_path
            ]
            if matching_files:
                file_findings[agent_name] = matching_files

        return file_findings

    def get_summary(self) -> Dict[str, Dict[str, int]]:
        """Get a summary of findings by agent and severity."""
        all_findings = self.get_all_findings()
        summary = {}

        for agent_name, file_findings_list in all_findings.items():
            agent_summary = {"error": 0, "warning": 0, "info": 0}
            for file_findings in file_findings_list:
                for finding in file_findings.findings:
                    severity = finding.severity
                    if severity in agent_summary:
                        agent_summary[severity] += 1
            summary[agent_name] = agent_summary

        return summary

    def has_findings(self, agent_name: Optional[str] = None) -> bool:
        """Check if there are any findings (optionally for a specific agent)."""
        if agent_name:
            return len(self.get_agent_findings(agent_name)) > 0
        else:
            return len(self.get_all_findings()) > 0


# Convenience function for coding agents
def read_agent_context(
    base_path: Path = Path(".claude/context"),
) -> Dict[str, List[FileFindings]]:
    """Read all agent findings - convenience function for coding agents."""
    reader = ContextReader(base_path)
    return reader.get_all_findings()


def get_context_summary(
    base_path: Path = Path(".claude/context"),
) -> Dict[str, Dict[str, int]]:
    """Get a summary of agent findings - convenience function for coding agents."""
    reader = ContextReader(base_path)
    return reader.get_summary()
