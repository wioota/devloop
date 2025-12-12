"""Caching strategy for agent marketplace registries."""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .metadata import AgentMetadata


logger = logging.getLogger(__name__)


class RegistryCache:
    """Cache for remote agent registries with TTL and validation."""

    def __init__(self, cache_dir: Path, ttl_hours: int = 24):
        """Initialize cache."""
        self.cache_dir = cache_dir
        self.ttl_hours = ttl_hours
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, url: str) -> Path:
        """Get cache file path for a registry URL."""
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        return self.cache_dir / f"registry_{url_hash}.json"

    def _get_metadata_file(self) -> Path:
        """Get cache metadata file."""
        return self.cache_dir / "cache_metadata.json"

    def _get_cache_metadata(self) -> Dict:
        """Load cache metadata."""
        metadata_file = self._get_metadata_file()
        if not metadata_file.exists():
            return {}

        try:
            with open(metadata_file) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache metadata: {e}")
            return {}

    def _save_cache_metadata(self, metadata: Dict) -> None:
        """Save cache metadata."""
        metadata_file = self._get_metadata_file()
        try:
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache metadata: {e}")

    def get(self, url: str) -> Optional[List[AgentMetadata]]:
        """Get cached agents for a registry URL (if not expired)."""
        cache_path = self._get_cache_path(url)

        if not cache_path.exists():
            return None

        try:
            # Check if cache is expired
            metadata = self._get_cache_metadata()
            url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
            entry = metadata.get(f"registry_{url_hash}")

            if not entry:
                return None

            cached_at = datetime.fromisoformat(entry.get("cached_at", ""))
            if datetime.now() - cached_at > timedelta(hours=self.ttl_hours):
                # Cache expired
                logger.debug(f"Cache expired for {url}")
                return None

            # Load and deserialize
            with open(cache_path) as f:
                data = json.load(f)

            agents = [AgentMetadata.from_dict(a) for a in data.get("agents", [])]
            logger.debug(f"Loaded {len(agents)} agents from cache for {url}")
            return agents

        except Exception as e:
            logger.warning(f"Failed to load cache for {url}: {e}")
            return None

    def set(self, url: str, agents: List[AgentMetadata]) -> bool:
        """Cache agents from a registry."""
        cache_path = self._get_cache_path(url)

        try:
            data = {
                "agents": [a.to_dict() for a in agents],
                "timestamp": datetime.now().isoformat(),
            }

            with open(cache_path, "w") as f:
                json.dump(data, f, indent=2)

            # Update metadata
            metadata = self._get_cache_metadata()
            url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
            metadata[f"registry_{url_hash}"] = {
                "url": url,
                "cached_at": datetime.now().isoformat(),
                "agent_count": len(agents),
            }
            self._save_cache_metadata(metadata)

            logger.debug(f"Cached {len(agents)} agents from {url}")
            return True

        except Exception as e:
            logger.warning(f"Failed to cache agents from {url}: {e}")
            return False

    def invalidate(self, url: Optional[str] = None) -> None:
        """Invalidate cache for a specific URL or all caches."""
        if url:
            # Invalidate specific URL
            cache_path = self._get_cache_path(url)
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"Invalidated cache for {url}")
        else:
            # Invalidate all caches
            for cache_file in self.cache_dir.glob("registry_*.json"):
                cache_file.unlink()
            logger.info("Invalidated all registry caches")

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        metadata = self._get_cache_metadata()

        total_agents = sum(
            e.get("agent_count", 0) for e in metadata.values() if isinstance(e, dict)
        )
        total_cached = len([e for e in metadata.values() if isinstance(e, dict)])

        return {
            "total_cached_registries": total_cached,
            "total_cached_agents": total_agents,
            "ttl_hours": self.ttl_hours,
            "cache_dir": str(self.cache_dir),
        }

    def cleanup_expired(self) -> int:
        """Remove expired cache entries and return count of removed entries."""
        metadata = self._get_cache_metadata()
        removed_count = 0

        entries_to_remove = []
        for entry_key, entry_data in list(metadata.items()):
            if not isinstance(entry_data, dict):
                continue

            try:
                cached_at = datetime.fromisoformat(entry_data.get("cached_at", ""))
                if datetime.now() - cached_at > timedelta(hours=self.ttl_hours):
                    entries_to_remove.append(entry_key)
                    # Remove cache file
                    cache_file = self.cache_dir / f"{entry_key}.json"
                    if cache_file.exists():
                        cache_file.unlink()
                    removed_count += 1
            except Exception:
                pass

        # Update metadata
        for key in entries_to_remove:
            del metadata[key]

        if removed_count > 0:
            self._save_cache_metadata(metadata)
            logger.info(f"Cleaned up {removed_count} expired cache entries")

        return removed_count
