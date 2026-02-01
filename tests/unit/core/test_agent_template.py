"""Tests for agent_template module.

Tests agent templates, registry, factory, and marketplace functionality.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devloop.core.agent_template import (
    AgentFactory,
    AgentMarketplace,
    AgentTemplate,
    AgentTemplateRegistry,
)


class TestAgentTemplate:
    """Tests for AgentTemplate dataclass."""

    def test_init_with_all_fields(self):
        """Test AgentTemplate initialization with all fields."""
        template = AgentTemplate(
            name="test-agent",
            description="A test agent",
            category="testing",
            triggers=["file:modified"],
            config_schema={"type": "object"},
            template_code="class TestAgent: pass",
        )

        assert template.name == "test-agent"
        assert template.description == "A test agent"
        assert template.category == "testing"
        assert template.triggers == ["file:modified"]
        assert template.config_schema == {"type": "object"}
        assert template.template_code == "class TestAgent: pass"

    def test_from_dict(self):
        """Test creating template from dictionary."""
        data = {
            "name": "from-dict-agent",
            "description": "Created from dict",
            "category": "data",
            "triggers": ["file:created", "file:deleted"],
            "config_schema": {"properties": {"key": {"type": "string"}}},
            "template_code": "# code here",
        }

        template = AgentTemplate.from_dict(data)

        assert template.name == "from-dict-agent"
        assert template.description == "Created from dict"
        assert template.category == "data"
        assert template.triggers == ["file:created", "file:deleted"]
        assert template.config_schema == {"properties": {"key": {"type": "string"}}}
        assert template.template_code == "# code here"


class TestAgentTemplateRegistry:
    """Tests for AgentTemplateRegistry."""

    def test_init_loads_builtin_templates(self):
        """Test that initialization loads built-in templates."""
        registry = AgentTemplateRegistry()

        assert "file-watcher" in registry.templates
        assert "command-runner" in registry.templates
        assert "data-processor" in registry.templates

    def test_get_template_existing(self):
        """Test getting an existing template."""
        registry = AgentTemplateRegistry()

        template = registry.get_template("file-watcher")

        assert template is not None
        assert template.name == "file-watcher"
        assert template.category == "monitoring"

    def test_get_template_nonexistent(self):
        """Test getting a nonexistent template."""
        registry = AgentTemplateRegistry()

        template = registry.get_template("nonexistent")

        assert template is None

    def test_list_templates_all(self):
        """Test listing all templates."""
        registry = AgentTemplateRegistry()

        templates = registry.list_templates()

        assert len(templates) >= 3
        names = [t.name for t in templates]
        assert "file-watcher" in names
        assert "command-runner" in names
        assert "data-processor" in names

    def test_list_templates_by_category(self):
        """Test listing templates filtered by category."""
        registry = AgentTemplateRegistry()

        templates = registry.list_templates(category="monitoring")

        assert len(templates) == 1
        assert templates[0].name == "file-watcher"

    def test_list_templates_by_nonexistent_category(self):
        """Test listing templates with nonexistent category."""
        registry = AgentTemplateRegistry()

        templates = registry.list_templates(category="nonexistent")

        assert templates == []

    def test_get_categories(self):
        """Test getting available categories."""
        registry = AgentTemplateRegistry()

        categories = registry.get_categories()

        assert "monitoring" in categories
        assert "automation" in categories
        assert "data" in categories

    def test_builtin_file_watcher_template(self):
        """Test file-watcher template has correct structure."""
        registry = AgentTemplateRegistry()

        template = registry.get_template("file-watcher")

        assert template is not None
        assert "file:modified" in template.triggers
        assert "file:created" in template.triggers
        assert "file:deleted" in template.triggers
        assert "filePatterns" in template.config_schema["properties"]
        assert "FileWatcherAgent" in template.template_code

    def test_builtin_command_runner_template(self):
        """Test command-runner template has correct structure."""
        registry = AgentTemplateRegistry()

        template = registry.get_template("command-runner")

        assert template is not None
        assert "file:modified" in template.triggers
        assert "git:commit" in template.triggers
        assert "commands" in template.config_schema["properties"]
        assert "CommandRunnerAgent" in template.template_code

    def test_builtin_data_processor_template(self):
        """Test data-processor template has correct structure."""
        registry = AgentTemplateRegistry()

        template = registry.get_template("data-processor")

        assert template is not None
        assert template.category == "data"
        assert "inputFormat" in template.config_schema["properties"]
        assert "outputFormat" in template.config_schema["properties"]
        assert "DataProcessorAgent" in template.template_code


class TestAgentFactory:
    """Tests for AgentFactory."""

    def test_init_with_registry(self):
        """Test factory initialization with registry."""
        registry = AgentTemplateRegistry()
        factory = AgentFactory(registry)

        assert factory.template_registry is registry

    @pytest.mark.asyncio
    async def test_create_from_template_nonexistent(self):
        """Test creating agent from nonexistent template."""
        registry = AgentTemplateRegistry()
        factory = AgentFactory(registry)
        mock_event_bus = MagicMock()

        agent = await factory.create_from_template(
            template_name="nonexistent",
            agent_name="test",
            triggers=["file:modified"],
            event_bus=mock_event_bus,
            config={},
        )

        assert agent is None

    @pytest.mark.asyncio
    async def test_create_from_file_nonexistent(self):
        """Test creating agent from nonexistent file."""
        registry = AgentTemplateRegistry()
        factory = AgentFactory(registry)
        mock_event_bus = MagicMock()

        agent = await factory.create_from_file(
            file_path=Path("/nonexistent/agent.py"),
            agent_name="test",
            triggers=["file:modified"],
            event_bus=mock_event_bus,
        )

        assert agent is None

    @pytest.mark.asyncio
    async def test_create_from_file_no_agent_class(self, tmp_path):
        """Test creating agent from file without Agent class."""
        registry = AgentTemplateRegistry()
        factory = AgentFactory(registry)
        mock_event_bus = MagicMock()

        # Create a Python file without Agent class
        agent_file = tmp_path / "no_agent.py"
        agent_file.write_text("x = 1")

        agent = await factory.create_from_file(
            file_path=agent_file,
            agent_name="test",
            triggers=["file:modified"],
            event_bus=mock_event_bus,
        )

        assert agent is None

    @pytest.mark.asyncio
    async def test_create_from_file_with_agent_class(self, tmp_path):
        """Test creating agent from file with valid Agent class."""
        registry = AgentTemplateRegistry()
        factory = AgentFactory(registry)
        mock_event_bus = MagicMock()

        # Create a Python file with Agent class
        agent_file = tmp_path / "custom_agent.py"
        agent_file.write_text("""
from devloop.core.agent import Agent

class CustomAgent(Agent):
    async def handle(self, event):
        pass
""")

        agent = await factory.create_from_file(
            file_path=agent_file,
            agent_name="custom",
            triggers=["file:modified"],
            event_bus=mock_event_bus,
        )

        assert agent is not None
        assert agent.name == "custom"


class TestAgentFactoryCreateFromTemplate:
    """Tests for AgentFactory.create_from_template method."""

    @pytest.mark.asyncio
    async def test_create_from_template_no_agent_class(self):
        """Test creating from template without Agent class in code."""
        # Create a custom template with no Agent class
        registry = AgentTemplateRegistry()
        registry.templates["no-agent"] = AgentTemplate(
            name="no-agent",
            description="Template without Agent class",
            category="testing",
            triggers=["file:modified"],
            config_schema={},
            template_code="class NotAnAgent: pass",
        )

        factory = AgentFactory(registry)
        mock_event_bus = MagicMock()

        agent = await factory.create_from_template(
            template_name="no-agent",
            agent_name="test",
            triggers=["file:modified"],
            event_bus=mock_event_bus,
            config={},
        )

        assert agent is None

    @pytest.mark.asyncio
    async def test_create_from_template_success(self):
        """Test successfully creating agent from template."""
        # Create a simple template with a valid Agent subclass
        registry = AgentTemplateRegistry()
        registry.templates["simple-agent"] = AgentTemplate(
            name="simple-agent",
            description="Simple test agent",
            category="testing",
            triggers=["file:modified"],
            config_schema={},
            template_code="""
from devloop.core.agent import Agent

class SimpleAgent(Agent):
    async def handle(self, event):
        return None
""",
        )

        factory = AgentFactory(registry)
        mock_event_bus = MagicMock()

        agent = await factory.create_from_template(
            template_name="simple-agent",
            agent_name="my-simple-agent",
            triggers=["file:modified"],
            event_bus=mock_event_bus,
            config={},
        )

        assert agent is not None
        assert agent.name == "my-simple-agent"


class TestAgentMarketplace:
    """Tests for AgentMarketplace."""

    def test_init_creates_directories(self, tmp_path):
        """Test marketplace initialization creates directories."""
        marketplace_path = tmp_path / "marketplace"

        marketplace = AgentMarketplace(marketplace_path)

        assert marketplace_path.exists()
        assert marketplace.index_file == marketplace_path / "index.json"
        assert marketplace.agents_dir == marketplace_path / "agents"

    @pytest.mark.asyncio
    async def test_publish_agent_nonexistent_file(self, tmp_path):
        """Test publishing nonexistent agent file."""
        marketplace = AgentMarketplace(tmp_path / "marketplace")

        result = await marketplace.publish_agent(
            agent_file=Path("/nonexistent/agent.py"),
            metadata={"name": "test"},
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_publish_agent_success(self, tmp_path):
        """Test successfully publishing an agent."""
        marketplace = AgentMarketplace(tmp_path / "marketplace")

        # Create an agent file
        agent_file = tmp_path / "my_agent.py"
        agent_file.write_text("class MyAgent: pass")

        result = await marketplace.publish_agent(
            agent_file=agent_file,
            metadata={"name": "my-agent", "description": "My custom agent"},
        )

        assert result is True
        assert (marketplace.agents_dir / "my-agent" / "agent.py").exists()
        assert (marketplace.agents_dir / "my-agent" / "metadata.json").exists()

    @pytest.mark.asyncio
    async def test_download_agent_nonexistent(self, tmp_path):
        """Test downloading nonexistent agent."""
        marketplace = AgentMarketplace(tmp_path / "marketplace")

        result = await marketplace.download_agent("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_download_agent_success(self, tmp_path):
        """Test successfully downloading an agent."""
        marketplace = AgentMarketplace(tmp_path / "marketplace")

        # Publish an agent first
        agent_file = tmp_path / "agent.py"
        agent_file.write_text("class Agent: pass")
        await marketplace.publish_agent(
            agent_file=agent_file,
            metadata={"name": "download-test"},
        )

        result = await marketplace.download_agent("download-test")

        assert result is not None
        assert result.exists()
        assert result.name == "agent.py"

    @pytest.mark.asyncio
    async def test_list_agents_empty(self, tmp_path):
        """Test listing agents when marketplace is empty."""
        marketplace = AgentMarketplace(tmp_path / "marketplace")

        agents = await marketplace.list_agents()

        assert agents == []

    @pytest.mark.asyncio
    async def test_list_agents_with_agents(self, tmp_path):
        """Test listing agents after publishing."""
        marketplace = AgentMarketplace(tmp_path / "marketplace")

        # Publish some agents
        agent_file = tmp_path / "agent.py"
        agent_file.write_text("class Agent: pass")

        await marketplace.publish_agent(
            agent_file=agent_file,
            metadata={"name": "agent1", "category": "testing"},
        )
        await marketplace.publish_agent(
            agent_file=agent_file,
            metadata={"name": "agent2", "category": "monitoring"},
        )

        agents = await marketplace.list_agents()

        assert len(agents) == 2
        names = [a["name"] for a in agents]
        assert "agent1" in names
        assert "agent2" in names

    @pytest.mark.asyncio
    async def test_list_agents_by_category(self, tmp_path):
        """Test listing agents filtered by category."""
        marketplace = AgentMarketplace(tmp_path / "marketplace")

        agent_file = tmp_path / "agent.py"
        agent_file.write_text("class Agent: pass")

        await marketplace.publish_agent(
            agent_file=agent_file,
            metadata={"name": "agent1", "category": "testing"},
        )
        await marketplace.publish_agent(
            agent_file=agent_file,
            metadata={"name": "agent2", "category": "monitoring"},
        )

        agents = await marketplace.list_agents(category="testing")

        assert len(agents) == 1
        assert agents[0]["name"] == "agent1"

    @pytest.mark.asyncio
    async def test_list_agents_invalid_json(self, tmp_path):
        """Test listing agents with invalid index file."""
        marketplace = AgentMarketplace(tmp_path / "marketplace")

        # Create invalid index file
        marketplace.index_file.write_text("not valid json")

        agents = await marketplace.list_agents()

        assert agents == []

    @pytest.mark.asyncio
    async def test_update_index_handles_invalid_metadata(self, tmp_path):
        """Test _update_index handles invalid metadata files."""
        marketplace = AgentMarketplace(tmp_path / "marketplace")
        marketplace.agents_dir.mkdir(parents=True, exist_ok=True)

        # Create agent dir with invalid metadata
        agent_dir = marketplace.agents_dir / "bad-agent"
        agent_dir.mkdir()
        (agent_dir / "metadata.json").write_text("invalid json")

        # Should not raise, just skip the invalid agent
        await marketplace._update_index()

        agents = await marketplace.list_agents()
        assert agents == []

    @pytest.mark.asyncio
    async def test_publish_adds_published_at(self, tmp_path):
        """Test that publish adds published_at timestamp."""
        marketplace = AgentMarketplace(tmp_path / "marketplace")

        agent_file = tmp_path / "agent.py"
        agent_file.write_text("class Agent: pass")

        await marketplace.publish_agent(
            agent_file=agent_file,
            metadata={"name": "timestamp-test"},
        )

        metadata_file = marketplace.agents_dir / "timestamp-test" / "metadata.json"
        metadata = json.loads(metadata_file.read_text())

        assert "published_at" in metadata
        assert isinstance(metadata["published_at"], float)

    @pytest.mark.asyncio
    async def test_publish_preserves_existing_published_at(self, tmp_path):
        """Test that publish preserves existing published_at."""
        marketplace = AgentMarketplace(tmp_path / "marketplace")

        agent_file = tmp_path / "agent.py"
        agent_file.write_text("class Agent: pass")

        original_time = 12345.0
        await marketplace.publish_agent(
            agent_file=agent_file,
            metadata={"name": "preserve-time", "published_at": original_time},
        )

        metadata_file = marketplace.agents_dir / "preserve-time" / "metadata.json"
        metadata = json.loads(metadata_file.read_text())

        assert metadata["published_at"] == original_time

    @pytest.mark.asyncio
    async def test_publish_uses_filename_as_fallback_name(self, tmp_path):
        """Test that publish uses filename if name not in metadata."""
        marketplace = AgentMarketplace(tmp_path / "marketplace")

        agent_file = tmp_path / "fallback_agent.py"
        agent_file.write_text("class Agent: pass")

        await marketplace.publish_agent(
            agent_file=agent_file,
            metadata={},  # No name provided
        )

        # Should use file stem as name
        assert (marketplace.agents_dir / "fallback_agent" / "agent.py").exists()
