"""Documentation Lifecycle Agent - manages documentation lifecycle."""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from dev_agents.core.agent import Agent, AgentResult
from dev_agents.core.event import Event


@dataclass
class DocLifecycleConfig:
    """Configuration for documentation lifecycle management."""

    mode: str = "report-only"  # or "auto-fix"
    scan_interval: int = 86400  # Daily (seconds)
    archival_age_days: int = 30
    root_md_limit: int = 10

    completion_markers: List[str] = field(default_factory=lambda: [
        "COMPLETE ✅",
        "RESOLVED ✅",
        "Complete!",
        "Status: Complete"
    ])

    temporary_prefixes: List[str] = field(default_factory=lambda: [
        "SESSION_",
        "FIX_",
        "THREADING_",
        "STATUS"
    ])

    archive_dir: str = "docs/archive"
    enforce_docs_structure: bool = True
    detect_duplicates: bool = True
    similarity_threshold: float = 0.5

    keep_in_root: List[str] = field(default_factory=lambda: [
        "README.md",
        "CHANGELOG.md",
        "LICENSE",
        "LICENSE.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "CLAUDE.md",
        "CODING_RULES.md",
        "PUBLISHING_PLAN.md",
        "CI_QUALITY_COMMITMENT.md"
    ])

    never_archive: List[str] = field(default_factory=lambda: [
        "README.md",
        "CLAUDE.md",
        "CODING_RULES.md"
    ])


class DocLifecycleAgent(Agent):
    """Agent for managing documentation lifecycle."""

    def __init__(
        self,
        name: str = "doc-lifecycle",
        triggers: Optional[List[str]] = None,
        event_bus = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            name=name,
            triggers=triggers or ["file:created:**.md", "file:modified:**.md", "schedule:daily"],
            event_bus=event_bus
        )

        # Parse config
        config_dict = config or {}
        self.config = DocLifecycleConfig(**config_dict) if config_dict else DocLifecycleConfig()

        self.project_root = Path.cwd()

    async def handle(self, event: Event) -> AgentResult:
        """Handle documentation lifecycle events."""
        try:
            # Scan all markdown files
            findings = await self.scan_documentation()

            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0.0,  # Would calculate actual duration
                message=f"Documentation scan complete: {len(findings)} findings",
                data={
                    "findings": findings,
                    "total_md_files": self._count_md_files(),
                    "root_md_files": self._count_root_md_files()
                }
            )
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0.0,
                message=f"Documentation scan failed: {str(e)}",
                error=str(e)
            )

    async def scan_documentation(self) -> List[Dict[str, Any]]:
        """Scan all documentation and return findings."""
        findings = []

        # Find all markdown files
        md_files = self._find_markdown_files()

        # Check root directory overflow
        root_md_count = self._count_root_md_files()
        if root_md_count > self.config.root_md_limit:
            findings.append({
                "type": "documentation",
                "severity": "info",
                "category": "root_overflow",
                "file": "(root directory)",
                "message": f"Root directory has {root_md_count} markdown files (limit: {self.config.root_md_limit})",
                "suggestion": "Consider moving reference docs to docs/ directory",
                "auto_fixable": False
            })

        # Analyze each file
        for md_file in md_files:
            file_findings = await self._analyze_file(md_file)
            findings.extend(file_findings)

        # Detect duplicates
        if self.config.detect_duplicates:
            duplicates = self._detect_duplicate_docs(md_files)
            for dup_group in duplicates:
                findings.append({
                    "type": "documentation",
                    "severity": "info",
                    "category": "duplicates",
                    "files": [str(f) for f in dup_group],
                    "message": f"Found {len(dup_group)} similar documentation files",
                    "suggestion": f"Consider consolidating: {', '.join(f.name for f in dup_group)}",
                    "auto_fixable": False
                })

        return findings

    def _find_markdown_files(self) -> List[Path]:
        """Find all markdown files in project."""
        # Search in current directory and docs/
        md_files = []

        # Root level markdown files
        md_files.extend(self.project_root.glob("*.md"))

        # docs/ directory if it exists
        docs_dir = self.project_root / "docs"
        if docs_dir.exists():
            md_files.extend(docs_dir.rglob("*.md"))

        return md_files

    def _count_md_files(self) -> int:
        """Count all markdown files."""
        return len(self._find_markdown_files())

    def _count_root_md_files(self) -> int:
        """Count markdown files in root directory."""
        return len(list(self.project_root.glob("*.md")))

    async def _analyze_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Analyze a single markdown file for lifecycle patterns."""
        findings = []

        # Skip if in never_archive list
        if file_path.name in self.config.never_archive:
            return findings

        try:
            content = file_path.read_text()

            # Check for completion markers
            for marker in self.config.completion_markers:
                if marker in content:
                    # Check if file is old enough to archive
                    age_days = self._get_file_age_days(file_path)

                    suggestion = self._suggest_archive_location(file_path)
                    message = f"Document marked as complete: {marker}"

                    if age_days > self.config.archival_age_days:
                        message += f" (> {self.config.archival_age_days} days old)"

                    findings.append({
                        "type": "documentation",
                        "severity": "info",
                        "category": "archival",
                        "file": str(file_path),
                        "message": message,
                        "suggestion": suggestion,
                        "auto_fixable": True,
                        "age_days": age_days
                    })
                    break  # Only report once per file

            # Check for temporary file patterns
            if self._is_temporary_file(file_path):
                findings.append({
                    "type": "documentation",
                    "severity": "info",
                    "category": "temporary",
                    "file": str(file_path),
                    "message": f"Temporary documentation file: {file_path.name}",
                    "suggestion": "Consider archiving or consolidating",
                    "auto_fixable": False
                })

            # Check for date stamps
            date_pattern = r'\*\*Date:\*\*\s+(\w+ \d+, \d{4})'
            dates = re.findall(date_pattern, content)
            if dates:
                findings.append({
                    "type": "documentation",
                    "severity": "info",
                    "category": "dated",
                    "file": str(file_path),
                    "message": f"Found date stamp: {dates[0]}",
                    "metadata": {"dates": dates},
                    "auto_fixable": False
                })

            # Check if file should be in docs/ instead of root
            if file_path.parent == self.project_root and file_path.name not in self.config.keep_in_root:
                findings.append({
                    "type": "documentation",
                    "severity": "info",
                    "category": "location",
                    "file": str(file_path),
                    "message": f"File in root should possibly be in docs/: {file_path.name}",
                    "suggestion": self._suggest_docs_location(file_path),
                    "auto_fixable": False
                })

        except Exception as e:
            findings.append({
                "type": "documentation",
                "severity": "warning",
                "category": "error",
                "file": str(file_path),
                "message": f"Failed to analyze: {e}",
                "auto_fixable": False
            })

        return findings

    def _is_temporary_file(self, file_path: Path) -> bool:
        """Check if file matches temporary file patterns."""
        for prefix in self.config.temporary_prefixes:
            if file_path.name.startswith(prefix):
                return True
        return False

    def _get_file_age_days(self, file_path: Path) -> int:
        """Get file age in days."""
        mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
        age = datetime.now() - mod_time
        return age.days

    def _suggest_archive_location(self, file_path: Path) -> str:
        """Suggest where to archive a file."""
        # Extract date from modification time
        mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
        archive_month = mod_time.strftime("%Y-%m")

        archive_path = Path(self.config.archive_dir) / archive_month / file_path.name.lower().replace('_', '-')
        return f"Archive to {archive_path}"

    def _suggest_docs_location(self, file_path: Path) -> str:
        """Suggest where to move a file in docs/."""
        name_lower = file_path.name.lower()

        # Suggest location based on name patterns
        if any(x in name_lower for x in ["guide", "howto", "tutorial"]):
            return f"Move to docs/guides/{file_path.name}"
        elif any(x in name_lower for x in ["reference", "api", "schema", "spec"]):
            return f"Move to docs/reference/{file_path.name}"
        elif any(x in name_lower for x in ["contributing", "development"]):
            return f"Move to docs/contributing/{file_path.name}"
        else:
            return f"Move to docs/{file_path.name}"

    def _detect_duplicate_docs(self, md_files: List[Path]) -> List[List[Path]]:
        """Detect potentially duplicate documentation files."""
        duplicates = []

        # Group by similar names (normalized)
        name_groups = {}
        for f in md_files:
            # Normalize name: lowercase, remove common suffixes/prefixes, remove version numbers
            normalized = f.stem.lower()
            normalized = re.sub(r'[_-]v\d+', '', normalized)  # Remove version numbers
            normalized = re.sub(r'[_-]complete.*', '', normalized)  # Remove "complete" suffix
            normalized = re.sub(r'[_-]summary.*', '', normalized)  # Remove "summary" suffix
            normalized = normalized.replace('_', '-')

            if normalized not in name_groups:
                name_groups[normalized] = []
            name_groups[normalized].append(f)

        # Return groups with > 1 file
        for group in name_groups.values():
            if len(group) > 1:
                duplicates.append(group)

        return duplicates

    async def auto_fix(self, finding: Dict[str, Any]) -> bool:
        """Automatically fix a documentation lifecycle issue."""
        if self.config.mode != "auto-fix":
            return False

        if finding.get("category") == "archival" and finding.get("auto_fixable"):
            # Move file to archive
            source = Path(finding["file"])
            suggestion = finding["suggestion"]

            # Extract destination from suggestion
            # Format: "Archive to docs/archive/YYYY-MM/filename.md"
            match = re.search(r'Archive to (.+)$', suggestion)
            if match:
                dest = Path(match.group(1))
                dest.parent.mkdir(parents=True, exist_ok=True)

                try:
                    source.rename(dest)
                    return True
                except Exception:
                    return False

        return False


# Export
__all__ = ["DocLifecycleAgent", "DocLifecycleConfig"]
