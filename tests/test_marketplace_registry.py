"""Tests for agent marketplace registry."""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from devloop.marketplace.metadata import AgentMetadata, Dependency, Rating
from devloop.marketplace.registry import AgentRegistry, RegistryConfig


@pytest.fixture
def temp_registry_dir():
    """Create a temporary directory for registry tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def registry(temp_registry_dir):
    """Create a registry instance for testing."""
    config = RegistryConfig(registry_dir=temp_registry_dir)
    return AgentRegistry(config)


@pytest.fixture
def sample_metadata():
    """Create sample agent metadata."""
    return AgentMetadata(
        name="test-linter",
        version="1.0.0",
        description="A test linter agent",
        author="Test Author",
        license="MIT",
        homepage="https://example.com",
        categories=["linting"],
        keywords=["linter", "code-quality"],
    )


class TestAgentRegistry:
    """Test agent registry functionality."""
    
    def test_registry_initialization(self, temp_registry_dir):
        """Test registry initialization."""
        config = RegistryConfig(registry_dir=temp_registry_dir)
        registry = AgentRegistry(config)
        
        assert registry.config == config
        assert (temp_registry_dir / "agents").exists()
        assert (temp_registry_dir / "cache").exists()
    
    def test_register_agent(self, registry, sample_metadata):
        """Test registering an agent."""
        result = registry.register_agent(sample_metadata)
        
        assert result is True
        assert registry.get_agent("test-linter") is not None
    
    def test_register_agent_updates_timestamps(self, registry, sample_metadata):
        """Test that registration updates timestamps."""
        registry.register_agent(sample_metadata)
        
        agent = registry.get_agent("test-linter")
        assert agent.published_at is not None
        assert agent.updated_at is not None
    
    def test_register_agent_invalid_metadata(self, registry):
        """Test registering agent with invalid metadata."""
        invalid_metadata = AgentMetadata(
            name="",
            version="1.0.0",
            description="Test",
            author="Test",
            license="MIT",
        )
        
        result = registry.register_agent(invalid_metadata)
        assert result is False
    
    def test_get_agent(self, registry, sample_metadata):
        """Test retrieving an agent."""
        registry.register_agent(sample_metadata)
        
        agent = registry.get_agent("test-linter")
        assert agent is not None
        assert agent.name == "test-linter"
        assert agent.version == "1.0.0"
    
    def test_get_nonexistent_agent(self, registry):
        """Test retrieving a nonexistent agent."""
        agent = registry.get_agent("nonexistent")
        assert agent is None
    
    def test_get_agent_version(self, registry, sample_metadata):
        """Test retrieving a specific agent version."""
        registry.register_agent(sample_metadata)
        
        agent = registry.get_agent_version("test-linter", "1.0.0")
        assert agent is not None
        
        agent = registry.get_agent_version("test-linter", "2.0.0")
        assert agent is None
    
    def test_list_agents(self, registry):
        """Test listing all agents."""
        agent1 = AgentMetadata(
            name="agent-1",
            version="1.0.0",
            description="First agent",
            author="Author",
            license="MIT",
            homepage="https://example.com",
        )
        agent2 = AgentMetadata(
            name="agent-2",
            version="1.0.0",
            description="Second agent",
            author="Author",
            license="MIT",
            homepage="https://example.com",
        )
        
        registry.register_agent(agent1)
        registry.register_agent(agent2)
        
        agents = registry.list_agents()
        assert len(agents) == 2
    
    def test_list_agents_filter_deprecated(self, registry):
        """Test listing agents with deprecated filtering."""
        agent1 = AgentMetadata(
            name="agent-1",
            version="1.0.0",
            description="Test",
            author="Author",
            license="MIT",
            homepage="https://example.com",
            deprecated=False,
        )
        agent2 = AgentMetadata(
            name="agent-2",
            version="1.0.0",
            description="Test",
            author="Author",
            license="MIT",
            homepage="https://example.com",
            deprecated=True,
        )
        
        registry.register_agent(agent1)
        registry.register_agent(agent2)
        
        # Include deprecated
        agents = registry.list_agents(include_deprecated=True)
        assert len(agents) == 2
        
        # Exclude deprecated
        agents = registry.list_agents(include_deprecated=False)
        assert len(agents) == 1
        assert agents[0].name == "agent-1"
    
    def test_list_agents_filter_category(self, registry):
        """Test listing agents by category."""
        agent1 = AgentMetadata(
            name="linter-1",
            version="1.0.0",
            description="Test",
            author="Author",
            license="MIT",
            homepage="https://example.com",
            categories=["linting"],
        )
        agent2 = AgentMetadata(
            name="formatter-1",
            version="1.0.0",
            description="Test",
            author="Author",
            license="MIT",
            homepage="https://example.com",
            categories=["formatting"],
        )
        
        registry.register_agent(agent1)
        registry.register_agent(agent2)
        
        agents = registry.list_agents(category="linting")
        assert len(agents) == 1
        assert agents[0].name == "linter-1"
    
    def test_search_agents(self, registry):
        """Test searching for agents."""
        agent = AgentMetadata(
            name="my-linter",
            version="1.0.0",
            description="A custom linter for Python",
            author="Author",
            license="MIT",
            homepage="https://example.com",
            keywords=["linting", "python"],
        )
        
        registry.register_agent(agent)
        
        # Search by name
        results = registry.search_agents("linter")
        assert len(results) == 1
        
        # Search by keyword
        results = registry.search_agents("python")
        assert len(results) == 1
    
    def test_update_rating(self, registry, sample_metadata):
        """Test updating agent rating."""
        registry.register_agent(sample_metadata)
        
        result = registry.update_rating("test-linter", 4.5)
        assert result is True
        
        agent = registry.get_agent("test-linter")
        assert agent.rating is not None
        assert agent.rating.average == 4.5
        assert agent.rating.count == 1
    
    def test_update_rating_multiple_times(self, registry, sample_metadata):
        """Test updating rating multiple times."""
        registry.register_agent(sample_metadata)
        
        registry.update_rating("test-linter", 5.0)
        registry.update_rating("test-linter", 4.0)
        registry.update_rating("test-linter", 3.0)
        
        agent = registry.get_agent("test-linter")
        assert agent.rating.average == 4.0
        assert agent.rating.count == 3
        assert agent.rating.distribution[5] == 1
        assert agent.rating.distribution[4] == 1
        assert agent.rating.distribution[3] == 1
    
    def test_update_rating_invalid_value(self, registry, sample_metadata):
        """Test rating with invalid values."""
        registry.register_agent(sample_metadata)
        
        # Too high
        result = registry.update_rating("test-linter", 6.0)
        assert result is False
        
        # Too low
        result = registry.update_rating("test-linter", 0.5)
        assert result is False
    
    def test_increment_downloads(self, registry, sample_metadata):
        """Test incrementing download count."""
        registry.register_agent(sample_metadata)
        
        agent = registry.get_agent("test-linter")
        assert agent.downloads == 0
        
        registry.increment_downloads("test-linter")
        agent = registry.get_agent("test-linter")
        assert agent.downloads == 1
    
    def test_deprecate_agent(self, registry, sample_metadata):
        """Test deprecating an agent."""
        registry.register_agent(sample_metadata)
        
        result = registry.deprecate_agent("test-linter", "Use new-linter instead")
        assert result is True
        
        agent = registry.get_agent("test-linter")
        assert agent.deprecated is True
        assert agent.deprecation_message == "Use new-linter instead"
    
    def test_remove_agent(self, registry, sample_metadata):
        """Test removing an agent."""
        registry.register_agent(sample_metadata)
        
        assert registry.get_agent("test-linter") is not None
        
        result = registry.remove_agent("test-linter")
        assert result is True
        
        assert registry.get_agent("test-linter") is None
    
    def test_get_trusted_agents(self, registry):
        """Test getting trusted agents."""
        agent1 = AgentMetadata(
            name="trusted-1",
            version="1.0.0",
            description="Test",
            author="Author",
            license="MIT",
            homepage="https://example.com",
            trusted=True,
        )
        agent2 = AgentMetadata(
            name="untrusted-1",
            version="1.0.0",
            description="Test",
            author="Author",
            license="MIT",
            homepage="https://example.com",
            trusted=False,
        )
        
        registry.register_agent(agent1)
        registry.register_agent(agent2)
        
        trusted = registry.get_trusted_agents()
        assert len(trusted) == 1
        assert trusted[0].name == "trusted-1"
    
    def test_get_recommended_agents(self, registry):
        """Test getting recommended agents."""
        agent1 = AgentMetadata(
            name="popular-1",
            version="1.0.0",
            description="Test",
            author="Author",
            license="MIT",
            homepage="https://example.com",
        )
        
        registry.register_agent(agent1)
        registry.increment_downloads("popular-1")
        registry.update_rating("popular-1", 5.0)
        
        recommended = registry.get_recommended_agents(limit=5)
        assert len(recommended) >= 1
        assert recommended[0].name == "popular-1"
    
    def test_get_stats(self, registry):
        """Test getting registry statistics."""
        agent = AgentMetadata(
            name="test-agent",
            version="1.0.0",
            description="Test",
            author="Author",
            license="MIT",
            homepage="https://example.com",
            categories=["testing"],
        )
        
        registry.register_agent(agent)
        registry.increment_downloads("test-agent")
        registry.update_rating("test-agent", 4.5)
        
        stats = registry.get_stats()
        
        assert stats["total_agents"] == 1
        assert stats["active_agents"] == 1
        assert stats["total_downloads"] == 1
        assert stats["average_rating"] == 4.5
        assert stats["categories"]["testing"] == 1
    
    def test_registry_persistence(self, temp_registry_dir, sample_metadata):
        """Test that registry persists to disk."""
        # Create and populate registry
        config = RegistryConfig(registry_dir=temp_registry_dir)
        registry1 = AgentRegistry(config)
        registry1.register_agent(sample_metadata)
        
        # Create new registry from same directory
        registry2 = AgentRegistry(config)
        
        # Should load the persisted agent
        agent = registry2.get_agent("test-linter")
        assert agent is not None
        assert agent.name == "test-linter"


if __name__ == "__main__":
    pytest.main([__file__])
