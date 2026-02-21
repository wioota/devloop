"""HTTP API smoke tests for the agent marketplace.

Exercises REST endpoints via FastAPI TestClient against a populated
local registry. No actual HTTP server is started.
"""

from pathlib import Path

import pytest

from devloop.marketplace.http_server import RegistryHTTPServer
from devloop.marketplace.metadata import AgentMetadata
from devloop.marketplace.registry import AgentRegistry, RegistryConfig

try:
    from fastapi.testclient import TestClient

    TESTCLIENT_AVAILABLE = True
except ImportError:
    TESTCLIENT_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not TESTCLIENT_AVAILABLE, reason="FastAPI TestClient not available"
)


SAMPLE_AGENTS = [
    AgentMetadata(
        name="devloop-formatter",
        version="0.9.0",
        description="Auto-formats code on save using Black and Prettier.",
        author="DevLoop",
        license="MIT",
        repository="https://github.com/wioota/devloop",
        keywords=["formatting", "black", "prettier"],
        categories=["formatting", "code-quality"],
    ),
    AgentMetadata(
        name="devloop-linter",
        version="0.9.0",
        description="Runs linters on file changes with sandboxed execution.",
        author="DevLoop",
        license="MIT",
        repository="https://github.com/wioota/devloop",
        keywords=["linting", "ruff", "eslint"],
        categories=["linting", "code-quality"],
    ),
    AgentMetadata(
        name="devloop-security-scanner",
        version="0.9.0",
        description="Detects security vulnerabilities using Bandit, Safety, Trivy.",
        author="DevLoop",
        license="MIT",
        repository="https://github.com/wioota/devloop",
        keywords=["security", "vulnerability", "bandit"],
        categories=["security", "code-quality"],
    ),
]


@pytest.fixture
def registry_dir(tmp_path: Path) -> Path:
    mp_dir = tmp_path / "registry"
    mp_dir.mkdir()
    return mp_dir


@pytest.fixture
def populated_registry(registry_dir: Path) -> AgentRegistry:
    """Create a registry pre-populated with sample agents."""
    config = RegistryConfig(registry_dir=registry_dir)
    registry = AgentRegistry(config)
    for agent in SAMPLE_AGENTS:
        registry.register_agent(agent)
    return registry


@pytest.fixture
def client(registry_dir: Path, populated_registry: AgentRegistry) -> "TestClient":
    """Create a FastAPI TestClient backed by the populated registry."""
    server = RegistryHTTPServer(registry_dir=registry_dir, remote_urls=[])
    return TestClient(server.app)


class TestHealthAndStats:
    def test_health_check(self, client: "TestClient") -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_stats(self, client: "TestClient") -> None:
        resp = client.get("/api/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        stats = data["data"]["local"]
        assert stats["total_agents"] == 3

    def test_categories(self, client: "TestClient") -> None:
        resp = client.get("/api/v1/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        cats = data["data"]["categories"]
        assert "code-quality" in cats


class TestSearchAndDiscovery:
    def test_search_by_query(self, client: "TestClient") -> None:
        resp = client.get("/api/v1/agents/search", params={"q": "lint"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        agents = data["data"]["local"]
        names = [a["name"] for a in agents]
        assert "devloop-linter" in names

    def test_search_empty_query_returns_all(self, client: "TestClient") -> None:
        resp = client.get("/api/v1/agents/search", params={"q": ""})
        assert resp.status_code == 200
        agents = resp.json()["data"]["local"]
        assert len(agents) == 3

    def test_list_agents(self, client: "TestClient") -> None:
        resp = client.get("/api/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]["agents"]) == 3

    def test_list_agents_by_category(self, client: "TestClient") -> None:
        resp = client.get("/api/v1/agents", params={"category": "security"})
        assert resp.status_code == 200
        agents = resp.json()["data"]["agents"]
        names = [a["name"] for a in agents]
        assert names == ["devloop-security-scanner"]

    def test_get_specific_agent(self, client: "TestClient") -> None:
        resp = client.get("/api/v1/agents/devloop-formatter")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["name"] == "devloop-formatter"
        assert data["data"]["version"] == "0.9.0"

    def test_get_nonexistent_agent_404(self, client: "TestClient") -> None:
        resp = client.get("/api/v1/agents/no-such-agent")
        assert resp.status_code == 404

    def test_get_agents_by_category_endpoint(self, client: "TestClient") -> None:
        resp = client.get("/api/v1/categories/formatting")
        assert resp.status_code == 200
        agents = resp.json()["data"]["agents"]
        assert len(agents) == 1
        assert agents[0]["name"] == "devloop-formatter"

    def test_popular_agents(self, client: "TestClient") -> None:
        resp = client.get("/api/v1/agents/popular")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_trusted_agents(self, client: "TestClient") -> None:
        resp = client.get("/api/v1/agents/trusted")
        assert resp.status_code == 200
        # None are trusted, should return empty
        assert resp.json()["data"]["agents"] == []


class TestMutations:
    def test_register_agent_via_api(self, client: "TestClient") -> None:
        new_agent = {
            "name": "devloop-test-runner",
            "version": "0.9.0",
            "description": "Runs tests on file changes.",
            "author": "DevLoop",
            "license": "MIT",
            "repository": "https://github.com/wioota/devloop",
            "categories": ["testing"],
        }
        resp = client.post("/api/v1/agents", json=new_agent)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Verify it's findable
        resp = client.get("/api/v1/agents/devloop-test-runner")
        assert resp.status_code == 200

    def test_rate_agent(self, client: "TestClient") -> None:
        resp = client.post(
            "/api/v1/agents/devloop-formatter/rate",
            json=5.0,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_download_agent(self, client: "TestClient") -> None:
        resp = client.post("/api/v1/agents/devloop-linter/download")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_deprecate_agent(self, client: "TestClient") -> None:
        resp = client.post(
            "/api/v1/agents/devloop-formatter/deprecate",
            json="Use devloop-formatter-v2 instead",
        )
        assert resp.status_code == 200

    def test_remove_agent(self, client: "TestClient") -> None:
        resp = client.delete("/api/v1/agents/devloop-security-scanner")
        assert resp.status_code == 200

        # Should be gone
        resp = client.get("/api/v1/agents/devloop-security-scanner")
        assert resp.status_code == 404


class TestResponseFormat:
    """All responses should have consistent structure."""

    def test_success_response_has_required_fields(self, client: "TestClient") -> None:
        resp = client.get("/health")
        data = resp.json()
        assert "success" in data
        assert "timestamp" in data
        assert "data" in data

    def test_error_response_format(self, client: "TestClient") -> None:
        resp = client.get("/api/v1/agents/nonexistent")
        assert resp.status_code == 404
        data = resp.json()
        assert data["success"] is False
        assert "error" in data
