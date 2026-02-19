"""Client for interacting with agent registries (local and remote)."""

import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .cache import RegistryCache
from .metadata import AgentMetadata
from .registry import AgentRegistry, RegistryConfig
from .search import SearchEngine

logger = logging.getLogger(__name__)


class RegistryClient:
    """Client for searching and managing agents in registries."""

    def __init__(
        self,
        local_registry: AgentRegistry,
        remote_urls: Optional[List[str]] = None,
        cache_ttl_hours: int = 24,
    ):
        """Initialize registry client."""
        self.local = local_registry
        self.remote_urls = remote_urls or []
        self.search_engine = SearchEngine()

        # Setup caching
        cache_dir = local_registry.config.registry_dir / "cache"
        self.cache = RegistryCache(cache_dir, ttl_hours=cache_ttl_hours)

        # Remote registry caches
        self._cache_timestamps: Dict[str, datetime] = {}
        self._remote_cache: Dict[str, List[AgentMetadata]] = {}

    def search(
        self,
        query: str,
        search_remote: bool = True,
        categories: Optional[List[str]] = None,
        min_rating: float = 0.0,
        max_results: int = 50,
    ) -> Dict[str, List[AgentMetadata]]:
        """
        Search for agents across registries.

        Returns dict with 'local' and 'remote' keys containing results.
        """
        results: Dict[str, List[AgentMetadata]] = {
            "local": [],
            "remote": [],
        }

        # Search local registry
        local_results = self.local.search_agents(query)

        # Filter by category if specified
        if categories:
            local_results = [
                a
                for a in local_results
                if any(cat in a.categories for cat in categories)
            ]

        # Filter by minimum rating
        if min_rating > 0:
            local_results = [
                a for a in local_results if a.rating and a.rating.average >= min_rating
            ]

        results["local"] = local_results[:max_results]

        # Search remote registries if requested
        if search_remote and self.remote_urls:
            remote_results = self._search_remote(query, categories, min_rating)
            results["remote"] = remote_results[:max_results]

        return results

    def _search_remote(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        min_rating: float = 0.0,
    ) -> List[AgentMetadata]:
        """Search remote registries."""
        results = []

        for url in self.remote_urls:
            try:
                agents = self._fetch_remote_registry(url)

                # Filter by query
                filtered = [
                    a
                    for a in agents
                    if (
                        query.lower() in a.name.lower()
                        or query.lower() in a.description.lower()
                    )
                ]

                # Filter by category
                if categories:
                    filtered = [
                        a
                        for a in filtered
                        if any(cat in a.categories for cat in categories)
                    ]

                # Filter by rating
                if min_rating > 0:
                    filtered = [
                        a
                        for a in filtered
                        if a.rating and a.rating.average >= min_rating
                    ]

                results.extend(filtered)
            except Exception as e:
                logger.warning(f"Failed to search remote registry {url}: {e}")

        return results

    def _fetch_remote_registry(self, url: str) -> List[AgentMetadata]:
        """Fetch registry data from remote URL (with caching)."""
        # Check cache
        cache_key = hashlib.sha256(url.encode()).hexdigest()

        if cache_key in self._cache_timestamps:
            cache_age = datetime.now() - self._cache_timestamps[cache_key]
            cache_ttl = timedelta(hours=self.local.config.cache_ttl_hours)

            if cache_age < cache_ttl and cache_key in self._remote_cache:
                logger.debug(f"Using cached remote registry: {url}")
                cached: List[AgentMetadata] = self._remote_cache[cache_key]
                return cached

        # Fetch remote registry
        # NOTE: In production, this would use aiohttp or requests
        # For now, we'll just return empty to indicate remote support exists
        logger.info(f"Would fetch remote registry from: {url}")

        return []

    def get_agent(
        self,
        name: str,
        version: Optional[str] = None,
        search_remote: bool = True,
    ) -> Optional[AgentMetadata]:
        """Get a specific agent by name and optional version."""
        # Check local first
        agent = self.local.get_agent(name)
        if agent and (not version or agent.version == version):
            return agent

        # Check remote
        if search_remote and self.remote_urls:
            for url in self.remote_urls:
                try:
                    agents = self._fetch_remote_registry(url)
                    for a in agents:
                        if a.name == name and (not version or a.version == version):
                            return a
                except Exception as e:
                    logger.warning(f"Failed to fetch agent from {url}: {e}")

        return None

    def get_popular_agents(self, limit: int = 10) -> List[AgentMetadata]:
        """Get popular agents from all registries."""
        agents = self.local.get_recommended_agents(limit=limit * 2)

        if self.remote_urls:
            for url in self.remote_urls:
                try:
                    remote_agents = self._fetch_remote_registry(url)
                    agents.extend(remote_agents)
                except Exception:
                    pass

        # Deduplicate and sort by rating/downloads
        seen = set()
        unique = []
        for agent in agents:
            if agent.name not in seen:
                seen.add(agent.name)
                unique.append(agent)

        unique.sort(
            key=lambda a: (
                -(a.rating.average if a.rating else 0),
                -a.downloads,
            )
        )

        return unique[:limit]

    def get_agents_by_category(
        self,
        category: str,
        limit: int = 50,
        search_remote: bool = True,
    ) -> List[AgentMetadata]:
        """Get agents in a specific category."""
        agents = self.local.get_agents_by_category(category)

        if search_remote and self.remote_urls:
            for url in self.remote_urls:
                try:
                    remote_agents = self._fetch_remote_registry(url)
                    agents.extend(
                        [a for a in remote_agents if category in a.categories]
                    )
                except Exception:
                    pass

        # Deduplicate
        seen = set()
        unique = []
        for agent in agents:
            if agent.name not in seen:
                seen.add(agent.name)
                unique.append(agent)

        return unique[:limit]

    def get_categories(self) -> Dict[str, int]:
        """Get list of available categories with agent counts."""
        categories: Dict[str, int] = {}

        # Get from local
        for agent in self.local.get_all_agents():
            for cat in agent.categories:
                categories[cat] = categories.get(cat, 0) + 1

        # Get from remote
        if self.remote_urls:
            for url in self.remote_urls:
                try:
                    remote_agents = self._fetch_remote_registry(url)
                    for agent in remote_agents:
                        for cat in agent.categories:
                            categories[cat] = categories.get(cat, 0) + 1
                except Exception:
                    pass

        return categories

    def rate_agent(self, name: str, rating: float) -> bool:
        """Rate an agent."""
        return self.local.update_rating(name, rating)

    def download_agent(self, name: str) -> bool:
        """Record a download for an agent."""
        return self.local.increment_downloads(name)

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about registries."""
        local_stats = self.local.get_stats()

        return {
            "local": local_stats,
            "remote_registries": len(self.remote_urls),
            "timestamp": datetime.now().isoformat(),
        }


def create_registry_client(
    registry_dir: Path, remote_urls: Optional[List[str]] = None
) -> RegistryClient:
    """Create a registry client with default configuration."""
    config = RegistryConfig(registry_dir=registry_dir)
    registry = AgentRegistry(config)
    return RegistryClient(registry, remote_urls)
