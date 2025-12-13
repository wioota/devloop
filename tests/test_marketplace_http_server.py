"""Tests for marketplace HTTP server."""

import pytest
import tempfile
from pathlib import Path

try:
    from fastapi.testclient import TestClient

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from devloop.marketplace.http_server import create_http_server


@pytest.fixture
def temp_registry_dir():
    """Create a temporary directory for registry tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def http_server(temp_registry_dir):
    """Create an HTTP server for testing."""
    if not FASTAPI_AVAILABLE:
        pytest.skip("FastAPI not available")

    server = create_http_server(
        registry_dir=temp_registry_dir,
        host="127.0.0.1",
        port=8000,
    )
    return server


@pytest.fixture
def client(http_server):
    """Create a test client."""
    return TestClient(http_server.app)


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestRegistryHTTPServer:
    """Test HTTP server endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"

    def test_register_agent(self, client):
        """Test agent registration endpoint."""
        metadata = {
            "name": "test-linter",
            "version": "1.0.0",
            "description": "A test linter agent",
            "author": "Test Author",
            "license": "MIT",
            "homepage": "https://example.com",
        }

        response = client.post("/api/v1/agents", json=metadata)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["agent"] == "test-linter"

    def test_register_agent_invalid(self, client):
        """Test registering agent with invalid metadata."""
        metadata = {
            "name": "",  # Invalid: empty name
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
            "license": "MIT",
        }

        response = client.post("/api/v1/agents", json=metadata)
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    def test_get_agent(self, client):
        """Test get agent endpoint."""
        # Register first
        metadata = {
            "name": "test-linter",
            "version": "1.0.0",
            "description": "A test linter",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
        }
        client.post("/api/v1/agents", json=metadata)

        # Get agent
        response = client.get("/api/v1/agents/test-linter")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "test-linter"

    def test_get_nonexistent_agent(self, client):
        """Test getting a nonexistent agent."""
        response = client.get("/api/v1/agents/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False

    def test_list_agents(self, client):
        """Test list agents endpoint."""
        # Register an agent
        metadata = {
            "name": "test-agent",
            "version": "1.0.0",
            "description": "Test agent",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
            "categories": ["testing"],
        }
        client.post("/api/v1/agents", json=metadata)

        # List agents
        response = client.get("/api/v1/agents")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["agents"]) >= 1

    def test_list_agents_pagination(self, client):
        """Test pagination in list endpoint."""
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
            client.post("/api/v1/agents", json=metadata)

        # Test with limit and offset
        response = client.get("/api/v1/agents?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["agents"]) == 2

    def test_search_agents(self, client):
        """Test search endpoint."""
        # Register an agent
        metadata = {
            "name": "my-linter",
            "version": "1.0.0",
            "description": "A custom linter",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
            "keywords": ["linter"],
        }
        client.post("/api/v1/agents", json=metadata)

        # Search for it
        response = client.get("/api/v1/agents/search?q=linter")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_categories(self, client):
        """Test get categories endpoint."""
        # Register an agent with category
        metadata = {
            "name": "test-agent",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
            "categories": ["linting", "formatting"],
        }
        client.post("/api/v1/agents", json=metadata)

        # Get categories
        response = client.get("/api/v1/categories")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "linting" in data["data"]["categories"]
        assert "formatting" in data["data"]["categories"]

    def test_get_agents_by_category(self, client):
        """Test get agents by category endpoint."""
        # Register an agent
        metadata = {
            "name": "linter-agent",
            "version": "1.0.0",
            "description": "A linter",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
            "categories": ["linting"],
        }
        client.post("/api/v1/agents", json=metadata)

        # Get agents in category
        response = client.get("/api/v1/categories/linting")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["category"] == "linting"

    def test_get_popular_agents(self, client):
        """Test get popular agents endpoint."""
        # Register and rate an agent
        metadata = {
            "name": "popular-agent",
            "version": "1.0.0",
            "description": "Popular",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
        }
        client.post("/api/v1/agents", json=metadata)
        client.post("/api/v1/agents/popular-agent/rate", json=5.0)

        # Get popular
        response = client.get("/api/v1/agents/popular")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_rate_agent(self, client):
        """Test rate agent endpoint."""
        # Register first
        metadata = {
            "name": "test-agent",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
        }
        client.post("/api/v1/agents", json=metadata)

        # Rate it
        response = client.post("/api/v1/agents/test-agent/rate", json=4.5)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["rating"] == 4.5

    def test_rate_agent_invalid(self, client):
        """Test rating with invalid value."""
        # Register first
        metadata = {
            "name": "test-agent",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
        }
        client.post("/api/v1/agents", json=metadata)

        # Try invalid rating
        response = client.post("/api/v1/agents/test-agent/rate", json=6.0)
        assert response.status_code == 422  # Validation error

    def test_download_agent(self, client):
        """Test download agent endpoint."""
        # Register first
        metadata = {
            "name": "test-agent",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
        }
        client.post("/api/v1/agents", json=metadata)

        # Download it
        response = client.post("/api/v1/agents/test-agent/download")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["downloads"] == 1

    def test_deprecate_agent(self, client):
        """Test deprecate agent endpoint."""
        # Register first
        metadata = {
            "name": "test-agent",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
        }
        client.post("/api/v1/agents", json=metadata)

        # Deprecate it
        response = client.post(
            "/api/v1/agents/test-agent/deprecate", json="Use new-agent instead"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_remove_agent(self, client):
        """Test remove agent endpoint."""
        # Register first
        metadata = {
            "name": "test-agent",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
        }
        client.post("/api/v1/agents", json=metadata)

        # Remove it
        response = client.delete("/api/v1/agents/test-agent")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_stats(self, client):
        """Test get stats endpoint."""
        # Register an agent
        metadata = {
            "name": "test-agent",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
        }
        client.post("/api/v1/agents", json=metadata)

        # Get stats
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "local" in data["data"]
        assert data["data"]["local"]["total_agents"] >= 1


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestRegistryHTTPServerIntegration:
    """Test full workflows through HTTP API."""

    def test_complete_agent_lifecycle(self, client):
        """Test complete agent lifecycle through API."""
        agent_name = "lifecycle-agent"

        # 1. Register agent
        metadata = {
            "name": agent_name,
            "version": "1.0.0",
            "description": "Test lifecycle",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
            "categories": ["testing"],
        }
        response = client.post("/api/v1/agents", json=metadata)
        assert response.status_code == 200

        # 2. Get agent
        response = client.get(f"/api/v1/agents/{agent_name}")
        assert response.status_code == 200

        # 3. Rate it
        response = client.post(f"/api/v1/agents/{agent_name}/rate", json=4.5)
        assert response.status_code == 200

        # 4. Download it
        response = client.post(f"/api/v1/agents/{agent_name}/download")
        assert response.status_code == 200

        # 5. List agents
        response = client.get("/api/v1/agents")
        assert response.status_code == 200
        assert len(response.json()["data"]["agents"]) >= 1

        # 6. Deprecate it
        response = client.post(
            f"/api/v1/agents/{agent_name}/deprecate", json="Use new-agent instead"
        )
        assert response.status_code == 200

        # 7. Remove it
        response = client.delete(f"/api/v1/agents/{agent_name}")
        assert response.status_code == 200

        # 8. Verify removed
        response = client.get(f"/api/v1/agents/{agent_name}")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__])
