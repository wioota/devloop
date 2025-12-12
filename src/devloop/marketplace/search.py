"""Advanced search and filtering for agent marketplace."""

from dataclasses import dataclass
from typing import List, Optional

from .metadata import AgentMetadata


@dataclass
class SearchFilter:
    """Criteria for filtering agents."""

    query: Optional[str] = None
    category: Optional[str] = None
    min_rating: float = 0.0
    trusted_only: bool = False
    exclude_deprecated: bool = True
    min_python_version: Optional[str] = None
    min_devloop_version: Optional[str] = None
    experimental: Optional[
        bool
    ] = None  # None = include both, True = only experimental, False = only stable


class SearchEngine:
    """Advanced search and filtering engine for agents."""

    def search(
        self, agents: List[AgentMetadata], filters: SearchFilter
    ) -> List[AgentMetadata]:
        """
        Search and filter agents based on criteria.

        Returns agents sorted by relevance (rating, downloads, name).
        """
        results = agents

        # Filter by text query
        if filters.query:
            results = self._filter_by_query(results, filters.query)

        # Filter by category
        if filters.category:
            results = [a for a in results if filters.category in a.categories]

        # Filter by minimum rating
        if filters.min_rating > 0:
            results = [
                a
                for a in results
                if a.rating and a.rating.average >= filters.min_rating
            ]

        # Filter deprecated
        if filters.exclude_deprecated:
            results = [a for a in results if not a.deprecated]

        # Filter trusted
        if filters.trusted_only:
            results = [a for a in results if a.trusted]

        # Filter experimental
        if filters.experimental is not None:
            results = [a for a in results if a.experimental == filters.experimental]

        # Filter by Python version requirement
        if filters.min_python_version:
            results = [
                a
                for a in results
                if self._check_version_compatible(
                    filters.min_python_version, a.python_version
                )
            ]

        # Filter by DevLoop version requirement
        if filters.min_devloop_version:
            results = [
                a
                for a in results
                if self._check_version_compatible(
                    filters.min_devloop_version, a.devloop_version
                )
            ]

        # Sort by relevance
        results.sort(
            key=lambda a: (
                -(a.rating.average if a.rating else 0),
                -a.downloads,
                a.name,
            )
        )

        return results

    def _filter_by_query(
        self, agents: List[AgentMetadata], query: str
    ) -> List[AgentMetadata]:
        """Filter agents by text query (name, description, keywords)."""
        query_lower = query.lower()
        return [
            a
            for a in agents
            if (
                query_lower in a.name.lower()
                or query_lower in a.description.lower()
                or any(query_lower in k.lower() for k in a.keywords)
            )
        ]

    def _check_version_compatible(self, required: str, agent_spec: str) -> bool:
        """Check if agent spec satisfies the required version constraint."""
        # Simple version compatibility check
        # In production, would use packaging.specifiers for full semver support
        try:
            parts_required = self._parse_version(required)
            parts_agent = self._parse_agent_spec(agent_spec)

            # For now, do simple major version check
            return parts_agent["major"] >= parts_required["major"]
        except Exception:
            return True  # If parsing fails, assume compatible

    def _parse_version(self, version: str) -> dict:
        """Parse a version string (e.g., '3.9' or '3.11')."""
        parts = version.split(".")
        return {
            "major": int(parts[0]) if len(parts) > 0 else 0,
            "minor": int(parts[1]) if len(parts) > 1 else 0,
        }

    def _parse_agent_spec(self, spec: str) -> dict:
        """Parse an agent version spec (e.g., '>=3.11' or '^3.9')."""
        # Remove common operators
        spec_clean = spec.replace(">=", "").replace("^", "").replace("~", "").strip()
        return self._parse_version(spec_clean)


def create_search_filter(
    query: Optional[str] = None,
    category: Optional[str] = None,
    min_rating: float = 0.0,
    trusted_only: bool = False,
    exclude_deprecated: bool = True,
    min_python_version: Optional[str] = None,
    min_devloop_version: Optional[str] = None,
    experimental: Optional[bool] = None,
) -> SearchFilter:
    """Create a search filter with provided parameters."""
    return SearchFilter(
        query=query,
        category=category,
        min_rating=min_rating,
        trusted_only=trusted_only,
        exclude_deprecated=exclude_deprecated,
        min_python_version=min_python_version,
        min_devloop_version=min_devloop_version,
        experimental=experimental,
    )
