# Doc Lifecycle Agent Specification

**Agent Name:** `DocLifecycleAgent`
**Category:** Documentation & Maintenance
**Priority:** Medium
**Status:** Specification (Not Yet Implemented)

---

## Problem Statement

LLM-assisted development creates significant documentation churn:
- Temporary status files persist beyond usefulness
- Completion markers ("COMPLETE ✅") signal archival readiness
- Multiple guides cover similar topics
- Root directory accumulates 30+ markdown files
- No systematic documentation lifecycle management

**Example:** This project has 35 markdown files in root, with 10+ being historical completion docs.

---

## Agent Purpose

Automatically manage the lifecycle of project documentation by:
1. Detecting documentation that's become historical
2. Suggesting consolidation opportunities
3. Maintaining organized documentation structure
4. Preventing documentation cruft accumulation
5. Keeping CHANGELOG.md and archive indices updated

---

## Core Capabilities

### 1. Documentation Pattern Detection

**Triggers:**
- `file:created` for new .md files
- `file:modified` for .md files
- `schedule:daily` for comprehensive scans

**Patterns to Detect:**

#### Completion Markers
```markdown
# Phase X - COMPLETE ✅
# Implementation - Complete!
Status: RESOLVED ✅
```

**Action:** Flag for archival (suggest moving to `docs/archive/YYYY-MM/`)

#### Date Stamps
```markdown
**Date:** November 28, 2025
Session Status - October 25, 2025
```

**Action:** Track age, suggest archival after 30 days if marked complete

#### Duplicate Prefixes
```
README.md
README_v2.md
getting-started.md
GETTING_STARTED.md
QUICKSTART.md
```

**Action:** Detect similar names/content, suggest consolidation

#### Temporary Status Files
```
SESSION_STATUS.md
PROTOTYPE_STATUS.md
FIX_SUMMARY.md
THREADING_FIX.md
```

**Action:** Flag as temporary, suggest extraction to CHANGELOG.md

---

### 2. Content Analysis

**Techniques:**

#### Similarity Detection
- Compare markdown headers across files
- Detect overlapping content (>50% similar sections)
- Identify redundant getting-started guides

#### Metadata Extraction
- Parse dates from content
- Extract completion status
- Identify document category from headers

#### Link Analysis
- Detect broken internal links
- Find orphaned documents (not linked from anywhere)
- Track documentation graph

---

### 3. Automated Actions

**Report-Only Mode (Default):**

Generates findings like:
```json
{
  "type": "documentation",
  "severity": "info",
  "category": "lifecycle",
  "finding": "Historical document ready for archival",
  "file": "PHASE2_COMPLETE.md",
  "suggestion": "Archive to docs/archive/2025-10/phase2-complete.md",
  "reasoning": "Marked COMPLETE ✅, dated October 2025, > 30 days old",
  "auto_fixable": true
}
```

**Auto-Fix Mode (Opt-in):**

With user approval, can:
- Move files to archive
- Update internal links
- Consolidate duplicates
- Update CHANGELOG.md
- Generate archive indices

---

### 4. Structure Enforcement

**Maintains Documentation Standards:**

```
project/
├── README.md                 # Single source of truth
├── CHANGELOG.md             # Auto-updated with milestones
├── docs/
│   ├── index.md             # Auto-generated index
│   ├── getting-started.md   # Consolidated guide (no duplicates)
│   ├── architecture.md      # Technical design
│   │
│   ├── reference/           # API & configuration docs
│   ├── guides/              # How-to guides
│   ├── contributing/        # Contribution guidelines
│   │
│   └── archive/
│       ├── 2025-11/         # Dated archives
│       ├── 2025-10/
│       └── README.md        # Archive index
```

**Detects Violations:**
- Root directory has > 10 .md files → "Consider moving to docs/"
- Multiple getting-started guides → "Consolidate into docs/getting-started.md"
- Archive missing date directories → "Create docs/archive/YYYY-MM/ structure"

---

## Configuration

**File:** `.dev-agents/agents.json`

```json
{
  "doc-lifecycle": {
    "enabled": true,
    "triggers": [
      "file:created:**.md",
      "file:modified:**.md",
      "schedule:daily"
    ],
    "config": {
      "mode": "report-only",  // or "auto-fix"
      "scan_interval": 86400,  // Daily scan (seconds)
      "archival_age_days": 30,  // Flag for archive after X days
      "root_md_limit": 10,  // Warn if > X files in root

      "patterns": {
        "completion_markers": [
          "COMPLETE ✅",
          "RESOLVED ✅",
          "Complete!",
          "Status: Complete"
        ],
        "temporary_prefixes": [
          "SESSION_",
          "FIX_",
          "THREADING_",
          "STATUS"
        ],
        "archive_triggers": [
          "Phase \\d+ -.*COMPLETE",
          "Implementation.*Complete"
        ]
      },

      "structure": {
        "archive_dir": "docs/archive",
        "archive_date_format": "YYYY-MM",
        "enforce_docs_structure": true,
        "auto_update_changelog": true,
        "generate_indices": true
      },

      "consolidation": {
        "detect_duplicates": true,
        "similarity_threshold": 0.5,  // 50% similar = suggest merge
        "suggest_merges": true
      },

      "exclusions": {
        "keep_in_root": [
          "README.md",
          "CHANGELOG.md",
          "LICENSE",
          "CONTRIBUTING.md",
          "CODE_OF_CONDUCT.md",
          "SECURITY.md"
        ],
        "never_archive": [
          "README.md",
          "CLAUDE.md",
          "CODING_RULES.md"
        ]
      }
    }
  }
}
```

---

## Agent Implementation

### Class Structure

```python
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import re

from dev_agents.core.agent import Agent, AgentResult
from dev_agents.core.event import Event

@dataclass
class DocLifecycleConfig:
    """Configuration for documentation lifecycle management."""

    mode: str = "report-only"  # or "auto-fix"
    scan_interval: int = 86400  # Daily
    archival_age_days: int = 30
    root_md_limit: int = 10

    completion_markers: List[str] = None
    archive_dir: str = "docs/archive"
    enforce_docs_structure: bool = True

    def __post_init__(self):
        if self.completion_markers is None:
            self.completion_markers = [
                "COMPLETE ✅",
                "RESOLVED ✅",
                "Complete!",
                "Status: Complete"
            ]


class DocLifecycleAgent(Agent):
    """Agent for managing documentation lifecycle."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        event_bus = None
    ):
        super().__init__(
            name="doc-lifecycle",
            triggers=[
                "file:created:**.md",
                "file:modified:**.md",
                "schedule:daily"
            ],
            event_bus=event_bus
        )

        self.config = DocLifecycleConfig(**config) if config else DocLifecycleConfig()
        self.project_root = Path.cwd()

    async def analyze(self, event: Event) -> AgentResult:
        """Analyze documentation and suggest lifecycle actions."""

        findings = []

        # Scan all markdown files
        md_files = self._find_markdown_files()

        # Check root directory overflow
        root_md_count = len([f for f in md_files if f.parent == self.project_root])
        if root_md_count > self.config.root_md_limit:
            findings.append({
                "type": "documentation",
                "severity": "info",
                "file": "(root)",
                "message": f"Root directory has {root_md_count} markdown files (limit: {self.config.root_md_limit})",
                "suggestion": "Consider moving reference docs to docs/ directory"
            })

        # Analyze each file
        for md_file in md_files:
            file_findings = await self._analyze_file(md_file)
            findings.extend(file_findings)

        # Detect duplicates
        duplicates = self._detect_duplicate_docs(md_files)
        for dup_group in duplicates:
            findings.append({
                "type": "documentation",
                "severity": "info",
                "files": [str(f) for f in dup_group],
                "message": f"Found {len(dup_group)} similar documentation files",
                "suggestion": f"Consider consolidating: {', '.join(f.name for f in dup_group)}"
            })

        return AgentResult(
            success=True,
            data={
                "total_md_files": len(md_files),
                "root_md_files": root_md_count,
                "findings_count": len(findings),
                "findings": findings
            },
            metadata={
                "agent": self.name,
                "scan_time": datetime.now().isoformat()
            }
        )

    def _find_markdown_files(self) -> List[Path]:
        """Find all markdown files in project."""
        return list(self.project_root.rglob("*.md"))

    async def _analyze_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Analyze a single markdown file for lifecycle patterns."""
        findings = []

        try:
            content = file_path.read_text()

            # Check for completion markers
            for marker in self.config.completion_markers:
                if marker in content:
                    findings.append({
                        "type": "documentation",
                        "severity": "info",
                        "category": "archival",
                        "file": str(file_path),
                        "message": f"Document marked as complete: {marker}",
                        "suggestion": self._suggest_archive_location(file_path),
                        "auto_fixable": True
                    })
                    break

            # Check file age if marked complete
            if findings and self._is_old_enough_to_archive(file_path):
                findings[-1]["message"] += f" (> {self.config.archival_age_days} days old)"

            # Check for date stamps
            date_pattern = r'\*\*Date:\*\*\s+(\w+ \d+, \d{4})'
            dates = re.findall(date_pattern, content)
            if dates:
                findings.append({
                    "type": "documentation",
                    "severity": "info",
                    "file": str(file_path),
                    "message": f"Found date stamp: {dates[0]}",
                    "metadata": {"dates": dates}
                })

        except Exception as e:
            findings.append({
                "type": "documentation",
                "severity": "warning",
                "file": str(file_path),
                "message": f"Failed to analyze: {e}"
            })

        return findings

    def _is_old_enough_to_archive(self, file_path: Path) -> bool:
        """Check if file is old enough to archive."""
        age_days = (datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)).days
        return age_days > self.config.archival_age_days

    def _suggest_archive_location(self, file_path: Path) -> str:
        """Suggest where to archive a file."""
        # Extract date from modification time
        mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
        archive_month = mod_time.strftime("%Y-%m")

        archive_path = Path(self.config.archive_dir) / archive_month / file_path.name.lower().replace('_', '-')
        return f"Archive to {archive_path}"

    def _detect_duplicate_docs(self, md_files: List[Path]) -> List[List[Path]]:
        """Detect potentially duplicate documentation files."""
        duplicates = []

        # Group by similar names
        name_groups = {}
        for f in md_files:
            # Normalize name
            normalized = f.stem.lower().replace('_', '-').replace('v2', '').replace('v1', '')

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

        if finding.get("category") == "archival":
            # Move file to archive
            source = Path(finding["file"])
            suggestion = finding["suggestion"]

            # Extract destination from suggestion
            # Format: "Archive to docs/archive/YYYY-MM/filename.md"
            match = re.search(r'Archive to (.+)$', suggestion)
            if match:
                dest = Path(match.group(1))
                dest.parent.mkdir(parents=True, exist_ok=True)

                source.rename(dest)
                return True

        return False
```

---

## Integration Points

### 1. Context Store
Writes findings to `.dev-agents/context/` for Claude Code integration:
```json
{
  "agent": "doc-lifecycle",
  "category": "documentation",
  "findings": [
    {
      "file": "PHASE2_COMPLETE.md",
      "action": "archive",
      "destination": "docs/archive/2025-10/"
    }
  ]
}
```

### 2. Git Integration
Before commits, check for documentation issues:
```bash
# Git hook: pre-commit
dev-agents check-docs
```

### 3. CLI Commands
```bash
# Scan documentation
dev-agents doc-scan

# Show archival candidates
dev-agents doc-archive --suggest

# Auto-fix issues (with confirmation)
dev-agents doc-fix --interactive

# Generate documentation index
dev-agents doc-index
```

---

## Success Metrics

- **Root Directory:** < 10 markdown files
- **Archive Organization:** All completed docs archived by month
- **Duplicate Detection:** 90% accuracy in detecting similar docs
- **False Positives:** < 5% incorrect archival suggestions
- **User Satisfaction:** Developers find suggestions helpful

---

## Future Enhancements

### Phase 1 (Current Spec)
- Pattern detection
- Archival suggestions
- Duplicate detection
- Report-only mode

### Phase 2 (Advanced)
- Content similarity analysis (NLP/embeddings)
- Auto-generated doc indices
- Broken link detection and fixing
- Documentation quality scoring

### Phase 3 (AI-Powered)
- LLM-based consolidation suggestions
- Auto-merge similar sections
- Generate summaries for archives
- Documentation style consistency

---

## Testing Strategy

**Unit Tests:**
- Pattern detection accuracy
- File age calculation
- Archive path generation
- Duplicate detection logic

**Integration Tests:**
- Full project scan
- Archive automation
- Index generation
- Link validation

**Acceptance Tests:**
- Run on this project (35 markdown files)
- Verify correct categorization
- Test auto-fix on safe test files
- Validate archive structure

---

## Implementation Priority

**Priority:** Medium (after core agents stabilized)
**Effort:** 2-3 days
**Dependencies:** None (standalone agent)
**Blocker:** None

**Suggested Timeline:**
1. Week 1: Core pattern detection + report-only mode
2. Week 2: Auto-fix mode + archive automation
3. Week 3: CLI commands + testing
4. Week 4: Documentation + real-world validation

---

## Related Documents

- **DOCUMENTATION_CONSOLIDATION_PLAN.md** - Manual consolidation plan for current state
- **CODING_RULES.md** - Agent development patterns
- **agent-types.md** - Agent specifications reference

---

## Approval Required

This specification requires user approval before implementation. Key decisions:

1. **Archival Age:** 30 days for completed docs? ⏳
2. **Root MD Limit:** 10 files maximum? 📁
3. **Auto-Fix Mode:** Enable by default or opt-in? ⚙️
4. **Archive Structure:** docs/archive/YYYY-MM/ format? 📂
5. **Implementation Priority:** After current issues resolved? 🚀

---

**Status:** Specification Complete - Awaiting User Review
