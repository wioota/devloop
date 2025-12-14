"""Tests for agent marketplace caching."""

import tempfile
from pathlib import Path

import pytest

from devloop.marketplace.cache import RegistryCache
from devloop.marketplace.metadata import AgentMetadata, Rating


@pytest.fixture
def cache_dir():
    """Create a temporary directory for cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache(cache_dir):
    """Create a cache instance."""
    return RegistryCache(cache_dir, ttl_hours=24)


@pytest.fixture
def sample_agents():
    """Create sample agents for caching."""
    return [
        AgentMetadata(
            name="agent-1",
            version="1.0.0",
            description="First agent",
            author="Author",
            license="MIT",
            homepage="https://example.com",
            rating=Rating(average=4.5, count=10),
            downloads=100,
        ),
        AgentMetadata(
            name="agent-2",
            version="1.0.0",
            description="Second agent",
            author="Author",
            license="MIT",
            homepage="https://example.com",
            rating=Rating(average=4.0, count=5),
            downloads=50,
        ),
    ]


class TestRegistryCache:
    """Test registry caching functionality."""

    def test_cache_initialization(self, cache_dir):
        """Test cache initialization."""
        cache = RegistryCache(cache_dir)

        assert cache.cache_dir == cache_dir
        assert cache.ttl_hours == 24
        assert cache_dir.exists()

    def test_set_and_get_cache(self, cache, sample_agents):
        """Test setting and retrieving cache."""
        url = "https://registry.example.com/agents"

        result = cache.set(url, sample_agents)
        assert result is True

        retrieved = cache.get(url)
        assert retrieved is not None
        assert len(retrieved) == 2
        assert retrieved[0].name == "agent-1"
        assert retrieved[1].name == "agent-2"

    def test_cache_expiration(self, cache_dir, sample_agents):
        """Test that cache expires after TTL."""
        cache = RegistryCache(cache_dir, ttl_hours=0)  # Immediate expiration

        url = "https://registry.example.com/agents"
        cache.set(url, sample_agents)

        # Cache should be expired immediately
        retrieved = cache.get(url)
        assert retrieved is None

    def test_cache_nonexistent_url(self, cache):
        """Test getting cache for nonexistent URL."""
        retrieved = cache.get("https://nonexistent.example.com")

        assert retrieved is None

    def test_invalidate_specific_cache(self, cache, sample_agents):
        """Test invalidating a specific cache."""
        url = "https://registry.example.com/agents"

        cache.set(url, sample_agents)
        assert cache.get(url) is not None

        cache.invalidate(url)
        assert cache.get(url) is None

    def test_invalidate_all_caches(self, cache, sample_agents):
        """Test invalidating all caches."""
        urls = [
            "https://registry1.example.com/agents",
            "https://registry2.example.com/agents",
            "https://registry3.example.com/agents",
        ]

        for url in urls:
            cache.set(url, sample_agents)

        # All should be cached
        for url in urls:
            assert cache.get(url) is not None

        # Invalidate all
        cache.invalidate()

        # All should be gone
        for url in urls:
            assert cache.get(url) is None

    def test_cache_stats(self, cache, sample_agents):
        """Test getting cache statistics."""
        urls = [
            "https://registry1.example.com/agents",
            "https://registry2.example.com/agents",
        ]

        for url in urls:
            cache.set(url, sample_agents)

        stats = cache.get_stats()

        assert stats["total_cached_registries"] == 2
        assert stats["total_cached_agents"] == 4  # 2 agents * 2 registries
        assert stats["ttl_hours"] == 24

    def test_cache_with_different_agents(self, cache, cache_dir):
        """Test caching different numbers of agents."""
        url1 = "https://registry1.example.com"
        url2 = "https://registry2.example.com"

        agents1 = [
            AgentMetadata(
                name=f"agent-{i}",
                version="1.0.0",
                description=f"Agent {i}",
                author="Author",
                license="MIT",
                homepage="https://example.com",
            )
            for i in range(5)
        ]

        agents2 = [
            AgentMetadata(
                name=f"tool-{i}",
                version="1.0.0",
                description=f"Tool {i}",
                author="Author",
                license="MIT",
                homepage="https://example.com",
            )
            for i in range(3)
        ]

        cache.set(url1, agents1)
        cache.set(url2, agents2)

        retrieved1 = cache.get(url1)
        retrieved2 = cache.get(url2)

        assert len(retrieved1) == 5
        assert len(retrieved2) == 3
        assert retrieved1[0].name == "agent-0"
        assert retrieved2[0].name == "tool-0"

    def test_cleanup_expired_caches(self, cache_dir):
        """Test cleanup of expired caches with very small TTL."""
        # Create cache with very small TTL that will expire quickly
        cache = RegistryCache(cache_dir, ttl_hours=0)  # Will expire immediately

        agents = [
            AgentMetadata(
                name="test",
                version="1.0.0",
                description="Test",
                author="Author",
                license="MIT",
                homepage="https://example.com",
            )
        ]

        # Cache something
        cache.set("https://example.com", agents)

        # Immediately try to retrieve - should be expired
        retrieved = cache.get("https://example.com")
        assert retrieved is None  # Expired immediately

        # Cleanup should find and remove the expired entry
        removed = cache.cleanup_expired()

        # At least one should be removed
        assert removed >= 1

    def test_cache_deserialization_preserves_data(self, cache, sample_agents):
        """Test that cached data preserves all fields."""
        url = "https://registry.example.com"
        original = sample_agents[0]

        cache.set(url, [original])
        retrieved = cache.get(url)

        agent = retrieved[0]
        assert agent.name == original.name
        assert agent.version == original.version
        assert agent.description == original.description
        assert agent.author == original.author
        assert agent.rating.average == original.rating.average
        assert agent.downloads == original.downloads


if __name__ == "__main__":
    pytest.main([__file__])
