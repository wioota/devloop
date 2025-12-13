"""Tests for marketplace Registry API."""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any

from devloop.marketplace.api import RegistryAPI, RegistryAPIResponse
from devloop.marketplace.metadata import AgentMetadata
from devloop.marketplace.registry import AgentRegistry, RegistryConfig
from devloop.marketplace.registry_client import create_registry_client


@pytest.fixture
def temp_registry_dir():
    """Create a temporary directory for registry tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def registry_client(temp_registry_dir):
    """Create a registry client for testing."""
    return create_registry_client(temp_registry_dir)


@pytest.fixture
def registry_api(registry_client):
    """Create a registry API instance for testing."""
    return RegistryAPI(registry_client)


@pytest.fixture
def sample_agent_metadata() -> Dict[str, Any]:
    """Create sample agent metadata."""
    return {
        "name": "test-linter",
        "version": "1.0.0",
        "description": "A test linter agent",
        "author": "Test Author",
        "license": "MIT",
        "homepage": "https://example.com",
        "repository": "https://github.com/example/test-linter",
        "categories": ["linting"],
        "keywords": ["linter", "code-quality"],
    }


class TestRegistryAPIResponse:
    """Test RegistryAPIResponse class."""

    def test_success_response(self):
        """Test creating a success response."""
        data = {"agent": "test", "version": "1.0.0"}
        response = RegistryAPIResponse(success=True, data=data)

        assert response.success is True
        assert response.data == data
        assert response.error is None

    def test_error_response(self):
        """Test creating an error response."""
        response = RegistryAPIResponse(success=False, error="Not found")

        assert response.success is False
        assert response.error == "Not found"
        assert response.data is None

    def test_response_to_dict(self):
        """Test converting response to dict."""
        data = {"test": "data"}
        response = RegistryAPIResponse(success=True, data=data)

        result = response.to_dict()

        assert result["success"] is True
        assert result["data"] == data
        assert "timestamp" in result


class TestRegistryAPI:
    """Test RegistryAPI functionality."""

    def test_register_agent(self, registry_api, sample_agent_metadata):
        """Test registering an agent."""
        response = registry_api.register_agent(sample_agent_metadata)

        assert response.success is True
        assert response.data["agent"] == "test-linter"
        assert response.data["version"] == "1.0.0"

    def test_register_agent_invalid_metadata(self, registry_api):
        """Test registering agent with invalid metadata."""
        invalid_metadata = {
            "name": "",  # Invalid: empty name
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
            "license": "MIT",
        }

        response = registry_api.register_agent(invalid_metadata)

        assert response.success is False
        assert "Invalid agent metadata" in response.error

    def test_get_agent(self, registry_api, sample_agent_metadata):
        """Test retrieving an agent."""
        # Register first
        registry_api.register_agent(sample_agent_metadata)

        # Get agent
        response = registry_api.get_agent("test-linter")

        assert response.success is True
        assert response.data["name"] == "test-linter"
        assert response.data["version"] == "1.0.0"

    def test_get_nonexistent_agent(self, registry_api):
        """Test retrieving a nonexistent agent."""
        response = registry_api.get_agent("nonexistent")

        assert response.success is False
        assert "not found" in response.error.lower()

    def test_list_agents(self, registry_api, sample_agent_metadata):
        """Test listing agents."""
        # Register an agent
        registry_api.register_agent(sample_agent_metadata)

        # List agents
        response = registry_api.list_agents()

        assert response.success is True
        assert len(response.data["agents"]) >= 1
        assert response.data["total"] >= 1

    def test_list_agents_with_category(self, registry_api, sample_agent_metadata):
        """Test listing agents by category."""
        # Register an agent
        registry_api.register_agent(sample_agent_metadata)

        # List by category
        response = registry_api.list_agents(category="linting")

        assert response.success is True
        assert len(response.data["agents"]) >= 1

    def test_list_agents_pagination(self, registry_api):
        """Test pagination in list_agents."""
        # Register multiple agents
        for i in range(5):
            metadata = {
                "name": f"agent-{i}",
                "version": "1.0.0",
                "description": f"Agent {i}",
                "author": "Test",
                "license": "MIT",
                "homepage": "https://example.com",
            }
            registry_api.register_agent(metadata)

        # Test offset and limit
        response1 = registry_api.list_agents(offset=0, max_results=2)
        response2 = registry_api.list_agents(offset=2, max_results=2)

        assert response1.success is True
        assert response2.success is True
        assert len(response1.data["agents"]) == 2
        assert len(response2.data["agents"]) == 2

    def test_get_categories(self, registry_api, sample_agent_metadata):
        """Test getting categories."""
        # Register an agent
        registry_api.register_agent(sample_agent_metadata)

        # Get categories
        response = registry_api.get_categories()

        assert response.success is True
        assert "linting" in response.data["categories"]

    def test_get_agents_by_category(self, registry_api, sample_agent_metadata):
        """Test getting agents by category."""
        # Register an agent
        registry_api.register_agent(sample_agent_metadata)

        # Get agents in category
        response = registry_api.get_agents_by_category("linting")

        assert response.success is True
        assert len(response.data["agents"]) >= 1

    def test_get_popular_agents(self, registry_api, sample_agent_metadata):
        """Test getting popular agents."""
        # Register and rate an agent
        registry_api.register_agent(sample_agent_metadata)
        registry_api.rate_agent("test-linter", 5.0)
        registry_api.download_agent("test-linter")

        # Get popular agents
        response = registry_api.get_popular_agents(limit=10)

        assert response.success is True
        assert len(response.data["agents"]) >= 1

    def test_get_trusted_agents(self, registry_api):
        """Test getting trusted agents."""
        # Register a trusted agent
        metadata = {
            "name": "trusted-agent",
            "version": "1.0.0",
            "description": "A trusted agent",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
            "trusted": True,
        }
        registry_api.register_agent(metadata)

        # Get trusted agents
        response = registry_api.get_trusted_agents()

        assert response.success is True
        assert len(response.data["agents"]) >= 1
        assert response.data["agents"][0]["name"] == "trusted-agent"

    def test_rate_agent(self, registry_api, sample_agent_metadata):
        """Test rating an agent."""
        # Register an agent
        registry_api.register_agent(sample_agent_metadata)

        # Rate it
        response = registry_api.rate_agent("test-linter", 4.5)

        assert response.success is True
        assert response.data["rating"] == 4.5
        assert response.data["average_rating"] == 4.5

    def test_rate_agent_multiple_times(self, registry_api, sample_agent_metadata):
        """Test rating an agent multiple times."""
        # Register an agent
        registry_api.register_agent(sample_agent_metadata)

        # Rate it multiple times
        registry_api.rate_agent("test-linter", 5.0)
        registry_api.rate_agent("test-linter", 4.0)
        registry_api.rate_agent("test-linter", 3.0)

        # Check final rating
        response = registry_api.rate_agent("test-linter", 4.0)

        assert response.success is True
        assert response.data["rating_count"] == 4

    def test_rate_agent_invalid_rating(self, registry_api, sample_agent_metadata):
        """Test rating with invalid values."""
        # Register an agent
        registry_api.register_agent(sample_agent_metadata)

        # Try invalid ratings
        response1 = registry_api.rate_agent("test-linter", 6.0)
        response2 = registry_api.rate_agent("test-linter", 0.5)

        assert response1.success is False
        assert response2.success is False

    def test_download_agent(self, registry_api, sample_agent_metadata):
        """Test recording a download."""
        # Register an agent
        registry_api.register_agent(sample_agent_metadata)

        # Download it
        response = registry_api.download_agent("test-linter")

        assert response.success is True
        assert response.data["downloads"] == 1

    def test_deprecate_agent(self, registry_api, sample_agent_metadata):
        """Test deprecating an agent."""
        # Register an agent
        registry_api.register_agent(sample_agent_metadata)

        # Deprecate it
        response = registry_api.deprecate_agent("test-linter", "Use new-linter instead")

        assert response.success is True
        assert response.data["deprecated"] is True

    def test_remove_agent(self, registry_api, sample_agent_metadata):
        """Test removing an agent."""
        # Register an agent
        registry_api.register_agent(sample_agent_metadata)

        # Remove it
        response = registry_api.remove_agent("test-linter")

        assert response.success is True
        assert response.data["removed"] is True

    def test_search_agents(self, registry_api, sample_agent_metadata):
        """Test searching for agents."""
        # Register an agent
        registry_api.register_agent(sample_agent_metadata)

        # Search for it
        response = registry_api.search_agents(query="linter")

        assert response.success is True
        assert response.data["total_results"] >= 1

    def test_search_agents_empty_query(self, registry_api, sample_agent_metadata):
        """Test search with empty query."""
        # Register an agent
        registry_api.register_agent(sample_agent_metadata)

        # Search with empty query
        response = registry_api.search_agents(query="")

        assert response.success is True

    def test_get_stats(self, registry_api, sample_agent_metadata):
        """Test getting registry statistics."""
        # Register an agent
        registry_api.register_agent(sample_agent_metadata)

        # Get stats
        response = registry_api.get_stats()

        assert response.success is True
        assert "local" in response.data
        assert response.data["local"]["total_agents"] >= 1

    def test_health_check(self, registry_api, sample_agent_metadata):
        """Test health check endpoint."""
        # Register an agent
        registry_api.register_agent(sample_agent_metadata)

        # Check health
        response = registry_api.health_check()

        assert response.success is True
        assert response.data["status"] == "healthy"


class TestRegistryAPIEdgeCases:
    """Test edge cases and error handling."""

    def test_register_duplicate_agent(self, registry_api, sample_agent_metadata):
        """Test registering duplicate agent names."""
        # Register first time
        response1 = registry_api.register_agent(sample_agent_metadata)
        assert response1.success is True

        # Register again with same name (should update)
        response2 = registry_api.register_agent(sample_agent_metadata)
        assert response2.success is True

    def test_rate_nonexistent_agent(self, registry_api):
        """Test rating a nonexistent agent."""
        response = registry_api.rate_agent("nonexistent", 4.0)

        assert response.success is False

    def test_download_nonexistent_agent(self, registry_api):
        """Test downloading a nonexistent agent."""
        response = registry_api.download_agent("nonexistent")

        assert response.success is False

    def test_list_with_deprecated_agents(self, registry_api):
        """Test filtering deprecated agents."""
        # Register deprecated and active agents
        active = {
            "name": "active-agent",
            "version": "1.0.0",
            "description": "Active agent",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
            "deprecated": False,
        }
        deprecated = {
            "name": "deprecated-agent",
            "version": "1.0.0",
            "description": "Deprecated agent",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
            "deprecated": True,
        }

        registry_api.register_agent(active)
        registry_api.register_agent(deprecated)

        # List without deprecated
        response = registry_api.list_agents(include_deprecated=False)
        assert response.success is True
        assert len(response.data["agents"]) == 1

        # List with deprecated
        response = registry_api.list_agents(include_deprecated=True)
        assert response.success is True
        assert len(response.data["agents"]) == 2


if __name__ == "__main__":
    pytest.main([__file__])
