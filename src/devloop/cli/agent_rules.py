"""Agent rules configuration management and merging."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class AgentRules:
    """Manages per-agent rules and configuration files."""

    def __init__(self, agents_dir: str = ".agents/agents"):
        """Initialize agent rules manager.

        Args:
            agents_dir: Directory containing agent subdirectories with rules.yaml files
        """
        self.agents_dir = agents_dir
        self.agents_path = Path(agents_dir)

    def discover_agents(self) -> List[str]:
        """Discover all agents with rules.yaml files.

        Returns:
            List of agent names
        """
        agents = []
        if self.agents_path.exists():
            for agent_dir in self.agents_path.iterdir():
                if agent_dir.is_dir():
                    rules_file = agent_dir / "rules.yaml"
                    if rules_file.exists():
                        agents.append(agent_dir.name)
        return sorted(agents)

    def load_agent_rules(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Load rules for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Parsed rules dictionary or None if not found
        """
        rules_file = self.agents_path / agent_name / "rules.yaml"
        if not rules_file.exists():
            return None

        try:
            with open(rules_file) as f:
                return yaml.safe_load(f) or {}
        except (IOError, yaml.YAMLError):
            return None

    def load_all_rules(self) -> Dict[str, Dict[str, Any]]:
        """Load rules for all discovered agents.

        Returns:
            Dictionary mapping agent names to their rules
        """
        rules = {}
        for agent_name in self.discover_agents():
            agent_rules = self.load_agent_rules(agent_name)
            if agent_rules:
                rules[agent_name] = agent_rules
        return rules

    def generate_template(self) -> str:
        """Generate AGENTS.md template from all agent rules.

        Returns:
            Markdown template ready for merging with existing AGENTS.md
        """
        all_rules = self.load_all_rules()
        if not all_rules:
            return ""

        template_parts = []
        template_parts.append("# Auto-Generated Agent Configuration\n")
        template_parts.append(
            "This section was generated from agent rules. "
            "Do not edit manually - update `.agents/agents/*/rules.yaml` instead.\n\n"
        )

        # Section: Preflight Tasks
        preflight_commands = []
        for agent_name, rules in sorted(all_rules.items()):
            if "preflight" in rules and rules["preflight"]:
                preflight_commands.extend(rules["preflight"])

        if preflight_commands:
            template_parts.append("## Preflight Checklist\n\n")
            template_parts.append(
                "Run these commands at the start of each session:\n\n"
            )
            for cmd in preflight_commands:
                template_parts.append(f"```bash\n{cmd}\n```\n\n")

        # Section: Dependencies
        all_dependencies = []
        for agent_name, rules in sorted(all_rules.items()):
            if "dependencies" in rules and rules["dependencies"]:
                for dep in rules["dependencies"]:
                    all_dependencies.append(dep)

        if all_dependencies:
            template_parts.append("## Dependencies\n\n")
            for dep in all_dependencies:
                requires = dep.get("requires", "unknown")
                version = dep.get("version", "any")
                template_parts.append(f"- **{requires}**: {version}\n")
            template_parts.append("\n")

        # Section: DevLoop Hints
        all_hints = []
        for agent_name, rules in sorted(all_rules.items()):
            if "devloop_hints" in rules and rules["devloop_hints"]:
                for hint in rules["devloop_hints"]:
                    all_hints.append(hint)

        if all_hints:
            template_parts.append("## Development Hints\n\n")
            for hint in all_hints:
                title = hint.get("title", "Tip")
                description = hint.get("description", "")
                workaround = hint.get("workaround")

                template_parts.append(f"### {title}\n\n")
                template_parts.append(f"{description}\n\n")
                if workaround:
                    template_parts.append("**Workaround**:\n\n")
                    template_parts.append(f"```bash\n{workaround}\n```\n\n")

        return "".join(template_parts)

    @staticmethod
    def merge_templates(existing_md: str, generated_template: str) -> str:
        """Intelligently merge generated template with existing AGENTS.md.

        This function:
        1. Detects and preserves existing custom content
        2. Skips duplicate sections
        3. Merges related content by topic
        4. Maintains semantic structure

        Args:
            existing_md: Current AGENTS.md content
            generated_template: Generated template from agent rules

        Returns:
            Merged AGENTS.md content
        """
        # If no existing content, just return generated
        if not existing_md.strip():
            return generated_template

        # Parse both documents into sections
        existing_sections = _parse_markdown_sections(existing_md)

        # Start with generated content (it's the "source of truth" from rules)
        merged_parts = []

        # Detect auto-generated marker
        if "Auto-Generated Agent Configuration" in existing_md:
            # Remove old auto-generated section
            existing_md = _remove_section(
                existing_md, "Auto-Generated Agent Configuration"
            )

        # Add generated content first
        merged_parts.append(generated_template)

        # Then add custom content from existing file (preserve user modifications)
        custom_sections = [
            sec
            for sec in existing_sections
            if not _is_auto_generated_section(sec["title"])
        ]

        if custom_sections:
            merged_parts.append("\n# Custom Configuration\n\n")
            for section in custom_sections:
                merged_parts.append(f"## {section['title']}\n\n")
                merged_parts.append(section["content"])
                merged_parts.append("\n")

        return "".join(merged_parts)


def _parse_markdown_sections(content: str) -> List[Dict[str, str]]:
    """Parse markdown into sections.

    Args:
        content: Markdown content

    Returns:
        List of sections with title and content
    """
    sections = []
    current_title = "Preamble"
    current_content = []

    for line in content.split("\n"):
        if line.startswith("## "):
            # Save previous section
            if current_content or current_title != "Preamble":
                sections.append(
                    {
                        "title": current_title,
                        "content": "\n".join(current_content),
                    }
                )
            # Start new section
            current_title = line[3:].strip()
            current_content = []
        else:
            current_content.append(line)

    # Save last section
    if current_content or current_title != "Preamble":
        sections.append(
            {
                "title": current_title,
                "content": "\n".join(current_content),
            }
        )

    return sections


def _is_auto_generated_section(title: str) -> bool:
    """Check if a section is auto-generated.

    Args:
        title: Section title

    Returns:
        True if section is auto-generated
    """
    auto_sections = {
        "Preflight Checklist",
        "Dependencies",
        "Development Hints",
        "Agent Configuration",
        "Auto-Generated Agent Configuration",
    }
    return title in auto_sections


def _remove_section(content: str, section_title: str) -> str:
    """Remove a section from markdown content.

    Args:
        content: Markdown content
        section_title: Title of section to remove

    Returns:
        Content with section removed
    """
    sections = _parse_markdown_sections(content)
    remaining = [
        sec for sec in sections if sec["title"].lower() != section_title.lower()
    ]

    # Reconstruct
    parts = []
    for section in remaining:
        if section["title"] != "Preamble":
            parts.append(f"## {section['title']}\n")
        parts.append(section["content"])
        if section != remaining[-1]:
            parts.append("\n")

    return "\n".join(parts)
