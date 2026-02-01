"""Tests for agent rules configuration and merging."""

import tempfile
from pathlib import Path

import pytest

from devloop.cli.agent_rules import AgentRules


class TestAgentRules:
    """Tests for AgentRules configuration management."""

    @pytest.fixture
    def temp_agents_dir(self):
        """Create a temporary agents directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / ".agents" / "agents"
            agents_dir.mkdir(parents=True)

            # Create formatter agent
            formatter_dir = agents_dir / "formatter"
            formatter_dir.mkdir()
            (formatter_dir / "rules.yaml").write_text("""
agent: formatter
preflight:
  - poetry run black src/
dependencies:
  - requires: black
    version: ">=24.0"
devloop_hints:
  - title: Formatting tip
    description: Format entire codebase at start
    workaround: poetry run black src/
""")

            # Create test-runner agent
            test_dir = agents_dir / "test-runner"
            test_dir.mkdir()
            (test_dir / "rules.yaml").write_text("""
agent: test-runner
preflight:
  - poetry run pytest tests/
dependencies:
  - requires: pytest
    version: ">=7.4"
""")

            yield str(agents_dir)

    def test_discover_agents(self, temp_agents_dir):
        """Test agent discovery."""
        rules = AgentRules(temp_agents_dir)
        agents = rules.discover_agents()
        assert "formatter" in agents
        assert "test-runner" in agents
        assert len(agents) == 2

    def test_load_agent_rules(self, temp_agents_dir):
        """Test loading rules for a specific agent."""
        rules = AgentRules(temp_agents_dir)
        formatter_rules = rules.load_agent_rules("formatter")

        assert formatter_rules is not None
        assert formatter_rules["agent"] == "formatter"
        assert "preflight" in formatter_rules
        assert "dependencies" in formatter_rules

    def test_load_all_rules(self, temp_agents_dir):
        """Test loading rules for all agents."""
        rules = AgentRules(temp_agents_dir)
        all_rules = rules.load_all_rules()

        assert "formatter" in all_rules
        assert "test-runner" in all_rules
        assert len(all_rules) == 2

    def test_generate_template(self, temp_agents_dir):
        """Test template generation from rules."""
        rules = AgentRules(temp_agents_dir)
        template = rules.generate_template()

        # Check that template contains expected sections
        assert "Auto-Generated Agent Configuration" in template
        assert "Preflight Checklist" in template
        assert "Dependencies" in template
        assert "Development Hints" in template

        # Check content
        assert "poetry run black src/" in template
        assert "poetry run pytest tests/" in template
        assert "black" in template
        assert "pytest" in template

    def test_template_contains_preflight_commands(self, temp_agents_dir):
        """Test that template includes all preflight commands."""
        rules = AgentRules(temp_agents_dir)
        template = rules.generate_template()

        assert "poetry run black src/" in template
        assert "poetry run pytest tests/" in template

    def test_template_contains_dependencies(self, temp_agents_dir):
        """Test that template includes all dependencies."""
        rules = AgentRules(temp_agents_dir)
        template = rules.generate_template()

        assert "black" in template
        assert "pytest" in template
        assert ">=24.0" in template
        assert ">=7.4" in template

    def test_template_contains_hints(self, temp_agents_dir):
        """Test that template includes all hints."""
        rules = AgentRules(temp_agents_dir)
        template = rules.generate_template()

        assert "Formatting tip" in template
        assert "Format entire codebase at start" in template

    def test_merge_templates_empty_existing(self, temp_agents_dir):
        """Test merging with empty existing content."""
        rules = AgentRules(temp_agents_dir)
        template = rules.generate_template()

        merged = rules.merge_templates("", template)
        assert "Auto-Generated Agent Configuration" in merged
        assert "Preflight Checklist" in merged
        assert "poetry run black src/" in merged

    def test_merge_templates_removes_old_autogen(self, temp_agents_dir):
        """Test that merging removes old auto-generated section."""
        rules = AgentRules(temp_agents_dir)
        new_template = rules.generate_template()

        # Simulate old AGENTS.md with auto-generated section
        old_content = """
# My Project

## Auto-Generated Agent Configuration

Old content here that should be removed

## Preflight Checklist

Old preflight

## Custom Section

This should be preserved
"""

        merged = rules.merge_templates(old_content, new_template)

        # Check that new content is present
        assert "Auto-Generated Agent Configuration" in merged
        # Check that custom section is preserved
        assert "Custom Section" in merged
        assert "This should be preserved" in merged

    def test_merge_templates_preserves_custom(self, temp_agents_dir):
        """Test that custom content is preserved during merge."""
        rules = AgentRules(temp_agents_dir)
        new_template = rules.generate_template()

        existing_with_custom = """
# Project Docs

## Architecture

Custom architecture documentation that should be preserved.

## Custom Workflow

Special workflow notes.
"""

        merged = rules.merge_templates(existing_with_custom, new_template)

        # Auto-generated content should be first
        assert merged.index("Auto-Generated") < merged.index("Architecture")
        # Custom content should be preserved
        assert "Custom architecture documentation" in merged
        assert "Special workflow notes" in merged

    def test_agent_rules_empty_rules(self, temp_agents_dir):
        """Test handling of agents with empty rules."""
        rules = AgentRules(temp_agents_dir)
        # Load non-existent agent
        result = rules.load_agent_rules("nonexistent")
        assert result is None

    def test_empty_agents_dir(self):
        """Test handling of empty agents directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / ".agents" / "agents"
            agents_dir.mkdir(parents=True)

            rules = AgentRules(str(agents_dir))
            agents = rules.discover_agents()
            assert len(agents) == 0

            all_rules = rules.load_all_rules()
            assert len(all_rules) == 0

            template = rules.generate_template()
            assert template == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
