#!/usr/bin/env python3
"""
Generate a readable status file for Claude Code to display to users.
This script reads from the context store and creates a summary in .claude/AGENT_STATUS.md
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def generate_status(project_root: Path = None):
    """Generate status markdown file from context store"""

    if project_root is None:
        project_root = Path.cwd()

    context_dir = project_root / ".claude" / "context"
    output_file = project_root / ".claude" / "AGENT_STATUS.md"

    # Read index
    index_file = context_dir / "index.json"

    if not index_file.exists():
        with open(output_file, 'w') as f:
            f.write("# Background Agent Status\n\n")
            f.write("_No agent findings available yet. Background agents haven't run or context store not initialized._\n")
        return

    try:
        with open(index_file, 'r') as f:
            index = json.load(f)

        # Read immediate findings
        immediate_file = context_dir / "immediate.json"
        immediate_findings = []
        if immediate_file.exists():
            with open(immediate_file, 'r') as f:
                immediate_data = json.load(f)
                immediate_findings = immediate_data.get("findings", [])

        # Generate markdown
        lines = []
        lines.append("# Background Agent Status\n")
        lines.append(f"_Last updated: {index.get('last_updated', 'unknown')}_\n")

        check_now = index.get("check_now", {})
        check_count = check_now.get("count", 0)

        if check_count == 0:
            lines.append("## ✅ Status: All Clear\n")
            lines.append("No immediate issues found by background agents.\n")
        else:
            lines.append(f"## ⚠️ Status: {check_count} Issue(s) Require Attention\n")

            severity_breakdown = check_now.get("severity_breakdown", {})

            for severity, count in severity_breakdown.items():
                if count > 0:
                    emoji = "🔴" if severity == "error" else "🟡" if severity == "warning" else "🔵"
                    lines.append(f"- {emoji} **{count} {severity}(s)**\n")

            # Group by file
            by_file = {}
            for finding in immediate_findings:
                file_path = finding.get("file", "unknown")
                if file_path not in by_file:
                    by_file[file_path] = []
                by_file[file_path].append(finding)

            lines.append("\n### Affected Files\n")

            for file_path, file_findings in sorted(by_file.items()):
                file_name = Path(file_path).name
                lines.append(f"\n#### `{file_name}`\n")

                # Group by agent
                by_agent = {}
                for finding in file_findings:
                    agent = finding.get("agent", "unknown")
                    if agent not in by_agent:
                        by_agent[agent] = []
                    by_agent[agent].append(finding)

                for agent, agent_findings in by_agent.items():
                    lines.append(f"\n**{agent}** ({len(agent_findings)} issue(s)):\n\n")

                    for finding in agent_findings[:10]:  # Show max 10 per agent
                        severity = finding.get("severity", "info")
                        emoji = "🔴" if severity == "error" else "🟡" if severity == "warning" else "🔵"
                        message = finding.get("message", "No message")
                        line = finding.get("line")
                        location = f" (line {line})" if line else ""
                        auto_fix = " _[auto-fixable]_" if finding.get("auto_fixable") else ""

                        lines.append(f"- {emoji} {message}{location}{auto_fix}\n")

                    if len(agent_findings) > 10:
                        lines.append(f"\n_... and {len(agent_findings) - 10} more_\n")

        # Add summary stats
        lines.append("\n---\n")
        lines.append("\n### Summary\n\n")
        lines.append(f"- **Immediate issues:** {index.get('check_now', {}).get('count', 0)}\n")
        lines.append(f"- **Relevant items:** {index.get('mention_if_relevant', {}).get('count', 0)}\n")
        lines.append(f"- **Background items:** {index.get('deferred', {}).get('count', 0)}\n")
        lines.append(f"- **Auto-fixed:** {index.get('auto_fixed', {}).get('count', 0)}\n")

        # Add action items
        auto_fixable = [f for f in immediate_findings if f.get("auto_fixable")]
        if auto_fixable:
            lines.append(f"\n### 💡 Quick Actions\n\n")
            lines.append(f"- {len(auto_fixable)} issue(s) can be auto-fixed\n")

        lines.append("\n---\n")
        lines.append("\n_This file is auto-generated from background agent findings._\n")
        lines.append("_To get detailed insights, run: `python3 .claude/integration/claude-code-adapter.py insights --format text`_\n")

        # Write output
        with open(output_file, 'w') as f:
            f.write(''.join(lines))

        return True

    except Exception as e:
        print(f"Error generating status: {e}", file=sys.stderr)
        with open(output_file, 'w') as f:
            f.write("# Background Agent Status\n\n")
            f.write(f"_Error generating status: {e}_\n")
        return False


if __name__ == "__main__":
    success = generate_status()
    sys.exit(0 if success else 1)
