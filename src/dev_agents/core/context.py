"""
Context Store for Agent Findings

Stores agent findings in .dev-agents/context/ for coding agents to read and act upon.
This enables background agents to report issues without directly modifying files.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Finding(BaseModel):
    """A single finding from an agent."""

    agent_name: str = Field(..., description="Name of the agent that made this finding")
    file_path: str = Field(..., description="Relative path to the file")
    line_number: Optional[int] = Field(None, description="Line number if applicable")
    column_number: Optional[int] = Field(
        None, description="Column number if applicable"
    )
    severity: str = Field(..., description="Severity level: 'error', 'warning', 'info'")
    message: str = Field(..., description="Human-readable message")
    rule_id: Optional[str] = Field(None, description="Rule or error code identifier")
    suggestion: Optional[str] = Field(None, description="Suggested fix or action")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional agent-specific data"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When the finding was made"
    )


class FileFindings(BaseModel):
    """Findings for a specific file."""

    file_path: str
    findings: List[Finding] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)


class ContextStore:
    """Stores agent findings in .dev-agents/context/ directory."""

    def __init__(self, base_path: Path = Path(".dev-agents/context")):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, agent_name: str) -> Path:
        """Get the JSON file path for an agent."""
        return self.base_path / f"{agent_name}.json"

    def store_findings(self, agent_name: str, findings: List[Finding]) -> None:
        """Store findings for an agent."""
        file_path = self._get_file_path(agent_name)

        # Group findings by file
        file_findings: Dict[str, FileFindings] = {}

        # Read existing findings if file exists
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text())
                # Handle different data formats for backward compatibility
                if isinstance(data, list):
                    # Old format: list of agent results - ignore
                    pass
                elif isinstance(data, dict) and "files" in data:
                    # New format: findings with files
                    for item in data["files"]:
                        file_findings[item["file_path"]] = FileFindings(**item)
                # else: unknown format, start fresh
            except (json.JSONDecodeError, KeyError, TypeError):
                # If file is corrupted or has unexpected format, start fresh
                pass

        # Add new findings
        for finding in findings:
            file_path_rel = finding.file_path
            if file_path_rel not in file_findings:
                file_findings[file_path_rel] = FileFindings(file_path=file_path_rel)

            # Remove any existing identical findings (by message and location)
            file_findings[file_path_rel].findings = [
                f
                for f in file_findings[file_path_rel].findings
                if not (
                    f.message == finding.message
                    and f.line_number == finding.line_number
                    and f.agent_name == finding.agent_name
                )
            ]

            # Add the new finding
            file_findings[file_path_rel].findings.append(finding)
            file_findings[file_path_rel].last_updated = datetime.now()

        # Write back to file
        data = {
            "agent_name": agent_name,
            "last_updated": datetime.now().isoformat(),
            "files": [ff.dict() for ff in file_findings.values()],
        }

        file_path.write_text(json.dumps(data, indent=2, default=str))

    def get_findings(self, agent_name: str) -> List[FileFindings]:
        """Get all findings for an agent."""
        file_path = self._get_file_path(agent_name)

        if not file_path.exists():
            return []

        try:
            data = json.loads(file_path.read_text())
            return [FileFindings(**item) for item in data.get("files", [])]
        except (json.JSONDecodeError, KeyError):
            return []

    def clear_findings(self, agent_name: str, file_path: Optional[str] = None) -> None:
        """Clear findings for an agent, optionally for a specific file."""
        if file_path is None:
            # Clear all findings for this agent
            self._get_file_path(agent_name).unlink(missing_ok=True)
        else:
            # Clear findings for specific file
            all_findings = self.get_findings(agent_name)
            remaining_findings = [
                ff for ff in all_findings if ff.file_path != file_path
            ]

            if remaining_findings:
                data = {
                    "agent_name": agent_name,
                    "last_updated": datetime.now().isoformat(),
                    "files": [ff.dict() for ff in remaining_findings],
                }
                self._get_file_path(agent_name).write_text(
                    json.dumps(data, indent=2, default=str)
                )
            else:
                # No findings left, remove the file
                self._get_file_path(agent_name).unlink(missing_ok=True)

    def get_all_agents(self) -> List[str]:
        """Get list of all agents that have stored findings."""
        return [f.stem for f in self.base_path.glob("*.json")]

    def clear_all(self) -> None:
        """Clear all findings from all agents."""
        for file_path in self.base_path.glob("*.json"):
            file_path.unlink()


# Global context store instance
context_store = ContextStore()
