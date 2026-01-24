"""Tests for agent_rules module."""

from pathlib import Path

import pytest

from devloop.cli.agent_rules import (
    AgentRules,
    _is_auto_generated_section,
    _parse_markdown_sections,
    _remove_section,
)


class TestAgentRules:
    """Tests for AgentRules class."""

    @pytest.fixture
    def agents_dir(self, tmp_path):
        """Create test agents directory structure."""
        agents_path = tmp_path / ".agents" / "agents"
        agents_path.mkdir(parents=True)
        return agents_path

    @pytest.fixture
    def agent_rules(self, tmp_path):
        """Create AgentRules instance."""
        agents_dir = str(tmp_path / ".agents" / "agents")
        return AgentRules(agents_dir)

    def test_init(self, tmp_path):
        """Test AgentRules initialization."""
        agents_dir = str(tmp_path / ".agents" / "agents")
        rules = AgentRules(agents_dir)

        assert rules.agents_dir == agents_dir
        assert rules.agents_path == Path(agents_dir)

    def test_discover_agents_empty(self, agent_rules):
        """Test discover_agents with no agents."""
        agents = agent_rules.discover_agents()

        assert agents == []

    def test_discover_agents_with_rules(self, agents_dir, agent_rules):
        """Test discover_agents with agents that have rules.yaml."""
        # Create agents with rules.yaml
        formatter_dir = agents_dir / "formatter"
        formatter_dir.mkdir()
        (formatter_dir / "rules.yaml").write_text("name: formatter")

        linter_dir = agents_dir / "linter"
        linter_dir.mkdir()
        (linter_dir / "rules.yaml").write_text("name: linter")

        agents = agent_rules.discover_agents()

        assert sorted(agents) == ["formatter", "linter"]

    def test_discover_agents_without_rules(self, agents_dir, agent_rules):
        """Test discover_agents skips agents without rules.yaml."""
        # Create agent without rules.yaml
        test_dir = agents_dir / "test-agent"
        test_dir.mkdir()

        agents = agent_rules.discover_agents()

        assert agents == []

    def test_discover_agents_with_files_not_dirs(self, agents_dir, agent_rules):
        """Test discover_agents skips non-directory files."""
        # Create a file in agents directory
        (agents_dir / "README.md").write_text("# Agents")

        agents = agent_rules.discover_agents()

        assert agents == []

    def test_load_agent_rules_success(self, agents_dir, agent_rules):
        """Test load_agent_rules loads valid YAML."""
        formatter_dir = agents_dir / "formatter"
        formatter_dir.mkdir()
        rules_content = """
preflight:
  - poetry run black .
dependencies:
  - requires: black
    version: ">=23.0.0"
"""
        (formatter_dir / "rules.yaml").write_text(rules_content)

        rules = agent_rules.load_agent_rules("formatter")

        assert rules is not None
        assert "preflight" in rules
        assert "dependencies" in rules
        assert rules["preflight"] == ["poetry run black ."]

    def test_load_agent_rules_not_found(self, agent_rules):
        """Test load_agent_rules returns None when file not found."""
        rules = agent_rules.load_agent_rules("nonexistent")

        assert rules is None

    def test_load_agent_rules_empty_file(self, agents_dir, agent_rules):
        """Test load_agent_rules handles empty YAML file."""
        agent_dir = agents_dir / "empty"
        agent_dir.mkdir()
        (agent_dir / "rules.yaml").write_text("")

        rules = agent_rules.load_agent_rules("empty")

        assert rules == {}

    def test_load_agent_rules_invalid_yaml(self, agents_dir, agent_rules):
        """Test load_agent_rules handles invalid YAML."""
        agent_dir = agents_dir / "invalid"
        agent_dir.mkdir()
        (agent_dir / "rules.yaml").write_text("invalid: [unclosed")

        rules = agent_rules.load_agent_rules("invalid")

        assert rules is None

    def test_load_all_rules(self, agents_dir, agent_rules):
        """Test load_all_rules loads rules for all agents."""
        # Create multiple agents
        formatter_dir = agents_dir / "formatter"
        formatter_dir.mkdir()
        (formatter_dir / "rules.yaml").write_text("preflight:\n  - black .")

        linter_dir = agents_dir / "linter"
        linter_dir.mkdir()
        (linter_dir / "rules.yaml").write_text("preflight:\n  - ruff check")

        all_rules = agent_rules.load_all_rules()

        assert "formatter" in all_rules
        assert "linter" in all_rules
        assert all_rules["formatter"]["preflight"] == ["black ."]
        assert all_rules["linter"]["preflight"] == ["ruff check"]

    def test_load_all_rules_empty(self, agent_rules):
        """Test load_all_rules with no agents."""
        all_rules = agent_rules.load_all_rules()

        assert all_rules == {}

    def test_generate_template_empty(self, agent_rules):
        """Test generate_template with no agents."""
        template = agent_rules.generate_template()

        assert template == ""

    def test_generate_template_with_preflight(self, agents_dir, agent_rules):
        """Test generate_template includes preflight commands."""
        agent_dir = agents_dir / "formatter"
        agent_dir.mkdir()
        rules_content = """
preflight:
  - poetry run black .
  - poetry run ruff check .
"""
        (agent_dir / "rules.yaml").write_text(rules_content)

        template = agent_rules.generate_template()

        assert "Preflight Checklist" in template
        assert "poetry run black ." in template
        assert "poetry run ruff check ." in template
        assert "```bash" in template

    def test_generate_template_with_dependencies(self, agents_dir, agent_rules):
        """Test generate_template includes dependencies."""
        agent_dir = agents_dir / "formatter"
        agent_dir.mkdir()
        rules_content = """
dependencies:
  - requires: black
    version: ">=23.0.0"
  - requires: ruff
    version: ">=0.1.0"
"""
        (agent_dir / "rules.yaml").write_text(rules_content)

        template = agent_rules.generate_template()

        assert "Dependencies" in template
        assert "**black**" in template
        assert ">=23.0.0" in template
        assert "**ruff**" in template

    def test_generate_template_with_hints(self, agents_dir, agent_rules):
        """Test generate_template includes DevLoop hints."""
        agent_dir = agents_dir / "linter"
        agent_dir.mkdir()
        rules_content = """
devloop_hints:
  - title: "Pre-commit Integration"
    description: "Use pre-commit hooks for automatic linting"
    workaround: "pre-commit install"
"""
        (agent_dir / "rules.yaml").write_text(rules_content)

        template = agent_rules.generate_template()

        assert "Development Hints" in template
        assert "Pre-commit Integration" in template
        assert "Use pre-commit hooks" in template
        assert "pre-commit install" in template

    def test_generate_template_complete(self, agents_dir, agent_rules):
        """Test generate_template with all sections."""
        agent_dir = agents_dir / "formatter"
        agent_dir.mkdir()
        rules_content = """
preflight:
  - poetry run black .
dependencies:
  - requires: black
    version: ">=23.0.0"
devloop_hints:
  - title: "Formatting Tip"
    description: "Format before committing"
"""
        (agent_dir / "rules.yaml").write_text(rules_content)

        template = agent_rules.generate_template()

        assert "Auto-Generated Agent Configuration" in template
        assert "Preflight Checklist" in template
        assert "Dependencies" in template
        assert "Development Hints" in template

    def test_merge_templates_empty_existing(self):
        """Test merge_templates with no existing content."""
        generated = "# Generated Content"

        merged = AgentRules.merge_templates("", generated)

        assert merged == generated

    def test_merge_templates_with_existing(self):
        """Test merge_templates preserves custom content."""
        existing = """# Existing Content

## Custom Section

This is custom content.
"""
        generated = """# Auto-Generated Agent Configuration

## Preflight Checklist

Run these commands.
"""

        merged = AgentRules.merge_templates(existing, generated)

        assert "Auto-Generated Agent Configuration" in merged
        assert "Preflight Checklist" in merged
        assert "Custom Configuration" in merged
        assert "Custom Section" in merged
        assert "This is custom content" in merged

    def test_merge_templates_removes_old_generated(self):
        """Test merge_templates adds new generated content."""
        existing = """## Preflight Checklist

Old preflight commands.

## Custom Section

Custom content.
"""
        generated = """# Auto-Generated Agent Configuration

## Preflight Checklist

New preflight commands.
"""

        merged = AgentRules.merge_templates(existing, generated)

        # Should contain new generated content
        assert "Auto-Generated Agent Configuration" in merged
        assert "New preflight commands" in merged
        # Should preserve custom sections
        assert "Custom Section" in merged
        assert "Custom content" in merged


class TestParseMarkdownSections:
    """Tests for _parse_markdown_sections helper."""

    def test_parse_empty(self):
        """Test parsing empty content."""
        sections = _parse_markdown_sections("")

        assert len(sections) == 1
        assert sections[0]["title"] == "Preamble"
        assert sections[0]["content"] == ""

    def test_parse_no_sections(self):
        """Test parsing content with no sections."""
        content = "Just some text\nwithout sections"

        sections = _parse_markdown_sections(content)

        assert len(sections) == 1
        assert sections[0]["title"] == "Preamble"
        assert "Just some text" in sections[0]["content"]

    def test_parse_single_section(self):
        """Test parsing single section."""
        content = """## Section 1

Content for section 1.
"""

        sections = _parse_markdown_sections(content)

        assert len(sections) == 1
        assert sections[0]["title"] == "Section 1"
        assert "Content for section 1" in sections[0]["content"]

    def test_parse_multiple_sections(self):
        """Test parsing multiple sections."""
        content = """## Section 1

Content 1.

## Section 2

Content 2.

## Section 3

Content 3.
"""

        sections = _parse_markdown_sections(content)

        assert len(sections) == 3
        assert sections[0]["title"] == "Section 1"
        assert sections[1]["title"] == "Section 2"
        assert sections[2]["title"] == "Section 3"

    def test_parse_with_preamble(self):
        """Test parsing content with preamble before sections."""
        content = """Preamble text here.

## Section 1

Section content.
"""

        sections = _parse_markdown_sections(content)

        assert len(sections) == 2
        assert sections[0]["title"] == "Preamble"
        assert "Preamble text" in sections[0]["content"]
        assert sections[1]["title"] == "Section 1"


class TestIsAutoGeneratedSection:
    """Tests for _is_auto_generated_section helper."""

    def test_auto_generated_sections(self):
        """Test recognizes auto-generated sections."""
        auto_sections = [
            "Preflight Checklist",
            "Dependencies",
            "Development Hints",
            "Agent Configuration",
            "Auto-Generated Agent Configuration",
        ]

        for section in auto_sections:
            assert _is_auto_generated_section(section) is True

    def test_custom_sections(self):
        """Test custom sections not flagged as auto-generated."""
        custom_sections = [
            "Custom Section",
            "User Guide",
            "Examples",
            "Notes",
        ]

        for section in custom_sections:
            assert _is_auto_generated_section(section) is False


class TestRemoveSection:
    """Tests for _remove_section helper."""

    def test_remove_existing_section(self):
        """Test removing an existing section."""
        content = """## Section 1

Content 1.

## Section 2

Content 2.

## Section 3

Content 3.
"""

        result = _remove_section(content, "Section 2")

        assert "Section 2" not in result
        assert "Content 2" not in result
        assert "Section 1" in result
        assert "Section 3" in result

    def test_remove_nonexistent_section(self):
        """Test removing non-existent section keeps sections."""
        content = """## Section 1

Content 1.
"""

        result = _remove_section(content, "Nonexistent")

        # Content should still have Section 1
        assert "Section 1" in result
        assert "Content 1" in result

    def test_remove_section_case_insensitive(self):
        """Test section removal is case-insensitive."""
        content = """## Auto-Generated Section

Content here.
"""

        result = _remove_section(content, "auto-generated section")

        assert "Auto-Generated Section" not in result
        assert "Content here" not in result
