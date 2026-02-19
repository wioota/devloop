"""REST API for agent marketplace registry.

Provides HTTP endpoints for searching, retrieving, and managing agents
in the marketplace. Supports both local and remote registry queries.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from .metadata import AgentMetadata
from .registry_client import RegistryClient  # noqa: F401

logger = logging.getLogger(__name__)


class RegistryAPIResponse:
    """Base response object for registry API."""

    def __init__(
        self,
        success: bool = True,
        data: Optional[Any] = None,
        error: Optional[str] = None,
        timestamp: Optional[str] = None,
    ):
        """Initialize API response."""
        self.success = success
        self.data = data
        self.error = error
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        result = {
            "success": self.success,
            "timestamp": self.timestamp,
        }
        if self.data is not None:
            result["data"] = self.data
        if self.error is not None:
            result["error"] = self.error
        return result


class RegistryAPI:
    """REST API interface for agent marketplace registry."""

    def __init__(self, registry_client: RegistryClient):
        """Initialize registry API."""
        self.client = registry_client

    def search_agents(
        self,
        query: str = "",
        categories: Optional[List[str]] = None,
        min_rating: float = 0.0,
        search_remote: bool = True,
        max_results: int = 50,
        offset: int = 0,
    ) -> RegistryAPIResponse:
        """
        Search for agents.

        Args:
            query: Search query string
            categories: Optional list of categories to filter by
            min_rating: Minimum rating (1-5) to include
            search_remote: Whether to search remote registries
            max_results: Maximum number of results to return
            offset: Number of results to skip (for pagination)

        Returns:
            RegistryAPIResponse with search results
        """
        try:
            results = self.client.search(
                query=query,
                search_remote=search_remote,
                categories=categories,
                min_rating=min_rating,
                max_results=max_results + offset,
            )

            # Apply offset
            if offset > 0:
                if results["local"]:
                    results["local"] = results["local"][offset:]
                if results["remote"]:
                    results["remote"] = results["remote"][offset:]

            return RegistryAPIResponse(
                data={
                    "local": [a.to_dict() for a in results["local"]],
                    "remote": [a.to_dict() for a in results["remote"]],
                    "query": query,
                    "total_results": len(results["local"]) + len(results["remote"]),
                }
            )
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return RegistryAPIResponse(
                success=False,
                error=f"Search failed: {str(e)}",
            )

    def get_agent(
        self,
        name: str,
        version: Optional[str] = None,
        search_remote: bool = True,
    ) -> RegistryAPIResponse:
        """
        Get a specific agent.

        Args:
            name: Agent name
            version: Optional specific version
            search_remote: Whether to search remote registries

        Returns:
            RegistryAPIResponse with agent metadata
        """
        try:
            agent = self.client.get_agent(
                name=name,
                version=version,
                search_remote=search_remote,
            )

            if not agent:
                return RegistryAPIResponse(
                    success=False,
                    error=f"Agent not found: {name}",
                )

            return RegistryAPIResponse(data=agent.to_dict())
        except Exception as e:
            logger.error(f"Failed to get agent {name}: {e}")
            return RegistryAPIResponse(
                success=False,
                error=f"Failed to get agent: {str(e)}",
            )

    def list_agents(
        self,
        category: Optional[str] = None,
        include_deprecated: bool = False,
        sort_by: str = "rating",
        max_results: int = 100,
        offset: int = 0,
    ) -> RegistryAPIResponse:
        """
        List agents with optional filtering.

        Args:
            category: Optional category to filter by
            include_deprecated: Whether to include deprecated agents
            sort_by: Sort field ('rating', 'downloads', 'name')
            max_results: Maximum number of results
            offset: Number of results to skip

        Returns:
            RegistryAPIResponse with agent list
        """
        try:
            agents = self.client.local.list_agents(
                category=category,
                include_deprecated=include_deprecated,
            )

            # Sort by requested field
            if sort_by == "downloads":
                agents.sort(key=lambda a: (-a.downloads, a.name))
            elif sort_by == "name":
                agents.sort(key=lambda a: a.name)
            else:  # rating (default)
                agents.sort(
                    key=lambda a: (
                        -(a.rating.average if a.rating else 0),
                        -a.downloads,
                        a.name,
                    )
                )

            # Apply pagination
            total = len(agents)
            agents = agents[offset : offset + max_results]

            return RegistryAPIResponse(
                data={
                    "agents": [a.to_dict() for a in agents],
                    "total": total,
                    "returned": len(agents),
                    "offset": offset,
                }
            )
        except Exception as e:
            logger.error(f"List agents failed: {e}")
            return RegistryAPIResponse(
                success=False,
                error=f"List agents failed: {str(e)}",
            )

    def get_agents_by_category(
        self,
        category: str,
        search_remote: bool = True,
        max_results: int = 50,
    ) -> RegistryAPIResponse:
        """
        Get all agents in a category.

        Args:
            category: Category name
            search_remote: Whether to search remote registries
            max_results: Maximum number of results

        Returns:
            RegistryAPIResponse with agents in category
        """
        try:
            agents = self.client.get_agents_by_category(
                category=category,
                search_remote=search_remote,
                limit=max_results,
            )

            return RegistryAPIResponse(
                data={
                    "category": category,
                    "agents": [a.to_dict() for a in agents],
                    "count": len(agents),
                }
            )
        except Exception as e:
            logger.error(f"Failed to get agents for category {category}: {e}")
            return RegistryAPIResponse(
                success=False,
                error=f"Failed to get agents for category: {str(e)}",
            )

    def get_categories(self) -> RegistryAPIResponse:
        """
        Get list of available categories.

        Returns:
            RegistryAPIResponse with categories and agent counts
        """
        try:
            categories = self.client.get_categories()

            # Sort by agent count (descending)
            sorted_categories = sorted(
                categories.items(),
                key=lambda x: (-x[1], x[0]),
            )

            return RegistryAPIResponse(
                data={
                    "categories": dict(sorted_categories),
                    "total_categories": len(categories),
                }
            )
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
            return RegistryAPIResponse(
                success=False,
                error=f"Failed to get categories: {str(e)}",
            )

    def get_popular_agents(
        self,
        limit: int = 10,
    ) -> RegistryAPIResponse:
        """
        Get popular/recommended agents.

        Args:
            limit: Maximum number of agents to return

        Returns:
            RegistryAPIResponse with popular agents
        """
        try:
            agents = self.client.get_popular_agents(limit=limit)

            return RegistryAPIResponse(
                data={
                    "agents": [a.to_dict() for a in agents],
                    "count": len(agents),
                }
            )
        except Exception as e:
            logger.error(f"Failed to get popular agents: {e}")
            return RegistryAPIResponse(
                success=False,
                error=f"Failed to get popular agents: {str(e)}",
            )

    def get_trusted_agents(self) -> RegistryAPIResponse:
        """
        Get all trusted/verified agents.

        Returns:
            RegistryAPIResponse with trusted agents
        """
        try:
            agents = self.client.local.get_trusted_agents()

            return RegistryAPIResponse(
                data={
                    "agents": [a.to_dict() for a in agents],
                    "count": len(agents),
                }
            )
        except Exception as e:
            logger.error(f"Failed to get trusted agents: {e}")
            return RegistryAPIResponse(
                success=False,
                error=f"Failed to get trusted agents: {str(e)}",
            )

    def rate_agent(self, name: str, rating: float) -> RegistryAPIResponse:
        """
        Rate an agent.

        Args:
            name: Agent name
            rating: Rating value (1-5)

        Returns:
            RegistryAPIResponse indicating success/failure
        """
        try:
            if not 1 <= rating <= 5:
                return RegistryAPIResponse(
                    success=False,
                    error="Rating must be between 1 and 5",
                )

            success = self.client.rate_agent(name, rating)

            if not success:
                return RegistryAPIResponse(
                    success=False,
                    error=f"Failed to rate agent: {name}",
                )

            agent = self.client.local.get_agent(name)
            return RegistryAPIResponse(
                data={
                    "agent": name,
                    "rating": rating,
                    "average_rating": (
                        agent.rating.average if agent and agent.rating else 0
                    ),
                    "rating_count": agent.rating.count if agent and agent.rating else 0,
                }
            )
        except Exception as e:
            logger.error(f"Failed to rate agent {name}: {e}")
            return RegistryAPIResponse(
                success=False,
                error=f"Failed to rate agent: {str(e)}",
            )

    def download_agent(self, name: str) -> RegistryAPIResponse:
        """
        Record a download for an agent.

        Args:
            name: Agent name

        Returns:
            RegistryAPIResponse indicating success/failure
        """
        try:
            success = self.client.download_agent(name)

            if not success:
                return RegistryAPIResponse(
                    success=False,
                    error=f"Failed to record download for: {name}",
                )

            agent = self.client.local.get_agent(name)
            return RegistryAPIResponse(
                data={
                    "agent": name,
                    "downloads": agent.downloads if agent else 0,
                }
            )
        except Exception as e:
            logger.error(f"Failed to record download for {name}: {e}")
            return RegistryAPIResponse(
                success=False,
                error=f"Failed to record download: {str(e)}",
            )

    def get_stats(self) -> RegistryAPIResponse:
        """
        Get registry statistics.

        Returns:
            RegistryAPIResponse with registry stats
        """
        try:
            stats = self.client.get_registry_stats()

            return RegistryAPIResponse(data=stats)
        except Exception as e:
            logger.error(f"Failed to get registry stats: {e}")
            return RegistryAPIResponse(
                success=False,
                error=f"Failed to get stats: {str(e)}",
            )

    def register_agent(self, metadata_dict: Dict[str, Any]) -> RegistryAPIResponse:
        """
        Register a new agent.

        Args:
            metadata_dict: Agent metadata as dictionary

        Returns:
            RegistryAPIResponse indicating success/failure
        """
        try:
            # Parse metadata from dictionary
            metadata = AgentMetadata.from_dict(metadata_dict)

            # Validate metadata
            errors = metadata.validate()
            if errors:
                return RegistryAPIResponse(
                    success=False,
                    error=f"Invalid agent metadata: {', '.join(errors)}",
                )

            # Register in local registry
            success = self.client.local.register_agent(metadata)

            if not success:
                return RegistryAPIResponse(
                    success=False,
                    error=f"Failed to register agent: {metadata.name}",
                )

            return RegistryAPIResponse(
                data={
                    "agent": metadata.name,
                    "version": metadata.version,
                    "message": "Agent registered successfully",
                }
            )
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            return RegistryAPIResponse(
                success=False,
                error=f"Failed to register agent: {str(e)}",
            )

    def deprecate_agent(
        self,
        name: str,
        message: str,
    ) -> RegistryAPIResponse:
        """
        Deprecate an agent.

        Args:
            name: Agent name
            message: Deprecation message

        Returns:
            RegistryAPIResponse indicating success/failure
        """
        try:
            success = self.client.local.deprecate_agent(name, message)

            if not success:
                return RegistryAPIResponse(
                    success=False,
                    error=f"Failed to deprecate agent: {name}",
                )

            return RegistryAPIResponse(
                data={
                    "agent": name,
                    "deprecated": True,
                    "message": message,
                }
            )
        except Exception as e:
            logger.error(f"Failed to deprecate agent {name}: {e}")
            return RegistryAPIResponse(
                success=False,
                error=f"Failed to deprecate agent: {str(e)}",
            )

    def remove_agent(self, name: str) -> RegistryAPIResponse:
        """
        Remove an agent from registry.

        Args:
            name: Agent name

        Returns:
            RegistryAPIResponse indicating success/failure
        """
        try:
            success = self.client.local.remove_agent(name)

            if not success:
                return RegistryAPIResponse(
                    success=False,
                    error=f"Failed to remove agent: {name}",
                )

            return RegistryAPIResponse(
                data={
                    "agent": name,
                    "removed": True,
                }
            )
        except Exception as e:
            logger.error(f"Failed to remove agent {name}: {e}")
            return RegistryAPIResponse(
                success=False,
                error=f"Failed to remove agent: {str(e)}",
            )

    def health_check(self) -> RegistryAPIResponse:
        """
        Health check endpoint.

        Returns:
            RegistryAPIResponse indicating API health
        """
        try:
            stats = self.client.get_registry_stats()
            return RegistryAPIResponse(
                data={
                    "status": "healthy",
                    "registry_stats": stats,
                }
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return RegistryAPIResponse(
                success=False,
                error=f"Health check failed: {str(e)}",
            )
