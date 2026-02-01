"""Central agent registry for marketplace discovery."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .metadata import AgentMetadata, Rating

logger = logging.getLogger(__name__)


@dataclass
class RegistryConfig:
    """Configuration for agent registry."""

    registry_dir: Path  # Directory to store registry data
    cache_ttl_hours: int = 24  # Cache expiration time
    max_local_agents: int = 1000  # Max agents in local registry

    def ensure_dirs_exist(self) -> None:
        """Create necessary directories."""
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        (self.registry_dir / "agents").mkdir(exist_ok=True)
        (self.registry_dir / "cache").mkdir(exist_ok=True)


class AgentRegistry:
    """Local agent registry for caching and managing agent metadata."""

    def __init__(self, config: RegistryConfig):
        """Initialize registry."""
        self.config = config
        self.config.ensure_dirs_exist()
        self._agents: Dict[str, AgentMetadata] = {}
        self._load_registry()

    def _get_agents_dir(self) -> Path:
        """Get directory where agent metadata is stored."""
        return self.config.registry_dir / "agents"

    def _get_index_file(self) -> Path:
        """Get path to registry index file."""
        return self._get_agents_dir() / "index.json"

    def _load_registry(self) -> None:
        """Load registry from disk."""
        index_file = self._get_index_file()

        if not index_file.exists():
            self._agents = {}
            return

        try:
            with open(index_file) as f:
                data = json.load(f)

            for agent_data in data.get("agents", []):
                metadata = AgentMetadata.from_dict(agent_data)
                self._agents[metadata.name] = metadata

            logger.info(f"Loaded {len(self._agents)} agents from registry")
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            self._agents = {}

    def _save_registry(self) -> None:
        """Save registry to disk."""
        index_file = self._get_index_file()

        data = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "agent_count": len(self._agents),
            "agents": [agent.to_dict() for agent in self._agents.values()],
        }

        try:
            with open(index_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved registry with {len(self._agents)} agents")
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")

    def register_agent(self, metadata: AgentMetadata) -> bool:
        """Register or update an agent in the registry."""
        # Validate metadata
        errors = metadata.validate()
        if errors:
            logger.error(f"Invalid agent metadata for {metadata.name}: {errors}")
            return False

        # Check size limit
        if (
            metadata.name not in self._agents
            and len(self._agents) >= self.config.max_local_agents
        ):
            logger.error(f"Registry full: cannot add {metadata.name}")
            return False

        # Update timestamps
        now = datetime.now().isoformat()
        if not metadata.published_at:
            metadata.published_at = now
        metadata.updated_at = now

        self._agents[metadata.name] = metadata
        self._save_registry()

        logger.info(f"Registered agent: {metadata.name}@{metadata.version}")
        return True

    def get_agent(self, name: str) -> Optional[AgentMetadata]:
        """Get agent metadata by name."""
        return self._agents.get(name)

    def get_agent_version(self, name: str, version: str) -> Optional[AgentMetadata]:
        """Get specific version of agent (for future multi-version support)."""
        agent = self._agents.get(name)
        if agent and agent.version == version:
            return agent
        return None

    def list_agents(
        self,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
        include_deprecated: bool = False,
    ) -> List[AgentMetadata]:
        """List agents with optional filtering."""
        agents = list(self._agents.values())

        # Filter deprecated
        if not include_deprecated:
            agents = [a for a in agents if not a.deprecated]

        # Filter by category
        if category:
            agents = [a for a in agents if category in a.categories]

        # Filter by keyword
        if keyword:
            keyword_lower = keyword.lower()
            agents = [
                a
                for a in agents
                if (
                    keyword_lower in a.name.lower()
                    or keyword_lower in a.description.lower()
                    or any(keyword_lower in k.lower() for k in a.keywords)
                )
            ]

        # Sort by rating (highest first), then by downloads
        agents.sort(
            key=lambda a: (
                -(a.rating.average if a.rating else 0),
                -a.downloads,
                a.name,
            )
        )

        return agents

    def search_agents(self, query: str) -> List[AgentMetadata]:
        """Search agents by name or keyword."""
        return self.list_agents(keyword=query)

    def get_agents_by_category(self, category: str) -> List[AgentMetadata]:
        """Get all agents in a specific category."""
        return self.list_agents(category=category)

    def get_trusted_agents(self) -> List[AgentMetadata]:
        """Get all trusted/verified agents."""
        agents = [a for a in self._agents.values() if a.trusted and not a.deprecated]
        agents.sort(key=lambda a: (-a.downloads, a.name))
        return agents

    def get_recommended_agents(self, limit: int = 10) -> List[AgentMetadata]:
        """Get recommended agents (highest rated and most downloaded)."""
        agents = [a for a in self._agents.values() if not a.deprecated]
        agents.sort(
            key=lambda a: (
                -(a.rating.average if a.rating else 0),
                -a.downloads,
            )
        )
        return agents[:limit]

    def update_rating(self, agent_name: str, rating_value: float) -> bool:
        """Update agent rating (add a new rating)."""
        agent = self._agents.get(agent_name)
        if not agent:
            return False

        # Validate rating
        if not 1 <= rating_value <= 5:
            return False

        # Initialize rating if needed
        if agent.rating is None:
            agent.rating = Rating(average=rating_value, count=1, distribution={})
        else:
            # Update average and count
            old_sum = agent.rating.average * agent.rating.count
            new_count = agent.rating.count + 1
            agent.rating.average = (old_sum + rating_value) / new_count
            agent.rating.count = new_count

        # Update distribution
        rating_int = int(rating_value)
        agent.rating.distribution[rating_int] = (
            agent.rating.distribution.get(rating_int, 0) + 1
        )

        agent.updated_at = datetime.now().isoformat()
        self._save_registry()

        return True

    def increment_downloads(self, agent_name: str) -> bool:
        """Increment download count for an agent."""
        agent = self._agents.get(agent_name)
        if not agent:
            return False

        agent.downloads += 1
        agent.updated_at = datetime.now().isoformat()
        self._save_registry()

        return True

    def deprecate_agent(self, agent_name: str, message: str) -> bool:
        """Mark an agent as deprecated."""
        agent = self._agents.get(agent_name)
        if not agent:
            return False

        agent.deprecated = True
        agent.deprecation_message = message
        agent.updated_at = datetime.now().isoformat()
        self._save_registry()

        logger.info(f"Deprecated agent: {agent_name}")
        return True

    def remove_agent(self, agent_name: str) -> bool:
        """Remove an agent from the registry."""
        if agent_name not in self._agents:
            return False

        del self._agents[agent_name]
        self._save_registry()

        logger.info(f"Removed agent: {agent_name}")
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        agents = list(self._agents.values())

        total_downloads = sum(a.downloads for a in agents)
        avg_rating = 0
        if agents:
            ratings = [a.rating.average for a in agents if a.rating]
            if ratings:
                avg_rating = sum(ratings) / len(ratings)

        categories: Dict[str, int] = {}
        for agent in agents:
            for cat in agent.categories:
                categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_agents": len(agents),
            "active_agents": len([a for a in agents if not a.deprecated]),
            "deprecated_agents": len([a for a in agents if a.deprecated]),
            "trusted_agents": len([a for a in agents if a.trusted]),
            "experimental_agents": len([a for a in agents if a.experimental]),
            "total_downloads": total_downloads,
            "average_rating": round(avg_rating, 2),
            "categories": categories,
        }

    def get_all_agents(self) -> List[AgentMetadata]:
        """Get all agents in registry."""
        return list(self._agents.values())
