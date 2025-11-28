"""Collector manager for coordinating all event collectors."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type

from devloop.collectors.base import BaseCollector
from devloop.collectors.filesystem import FileSystemCollector
from devloop.collectors.git import GitCollector
from devloop.collectors.process import ProcessCollector
from devloop.collectors.system import SystemCollector
from devloop.core.event import EventBus


class CollectorManager:
    """Manages all event collectors and their lifecycle."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.collectors: Dict[str, BaseCollector] = {}
        self.logger = logging.getLogger("collector_manager")
        self._running = False

        # Register built-in collectors
        self._collector_classes: Dict[str, Type[BaseCollector]] = {
            "filesystem": FileSystemCollector,
            "git": GitCollector,
            "process": ProcessCollector,
            "system": SystemCollector,
        }

    def register_collector_class(
        self, name: str, collector_class: Type[BaseCollector]
    ) -> None:
        """Register a new collector class."""
        self._collector_classes[name] = collector_class
        self.logger.info(f"Registered collector class: {name}")

    def create_collector(
        self, name: str, config: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseCollector]:
        """Create a collector instance."""
        if name not in self._collector_classes:
            self.logger.error(f"Unknown collector type: {name}")
            return None

        try:
            collector_class = self._collector_classes[name]
            collector = collector_class(self.event_bus, config)
            self.collectors[name] = collector
            self.logger.info(f"Created collector: {name}")
            return collector
        except Exception as e:
            self.logger.error(f"Failed to create collector {name}: {e}")
            return None

    async def start_collector(self, name: str) -> bool:
        """Start a specific collector."""
        if name not in self.collectors:
            self.logger.error(f"Collector not found: {name}")
            return False

        try:
            await self.collectors[name].start()
            self.logger.info(f"Started collector: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start collector {name}: {e}")
            return False

    async def stop_collector(self, name: str) -> bool:
        """Stop a specific collector."""
        if name not in self.collectors:
            self.logger.warning(f"Collector not found: {name}")
            return False

        try:
            await self.collectors[name].stop()
            self.logger.info(f"Stopped collector: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop collector {name}: {e}")
            return False

    async def start_all(self) -> None:
        """Start all registered collectors."""
        if self._running:
            return

        self._running = True
        self.logger.info("Starting all collectors...")

        # Start collectors in dependency order
        start_order = ["filesystem", "git", "process"]  # filesystem first, then others

        started_count = 0
        for name in start_order:
            if name in self.collectors:
                if await self.start_collector(name):
                    started_count += 1

        # Start any remaining collectors not in the ordered list
        for name, collector in self.collectors.items():
            if name not in start_order and not collector.is_running:
                if await self.start_collector(name):
                    started_count += 1

        self.logger.info(f"Started {started_count}/{len(self.collectors)} collectors")

    async def stop_all(self) -> None:
        """Stop all collectors."""
        if not self._running:
            return

        self._running = False
        self.logger.info("Stopping all collectors...")

        # Stop in reverse order
        stop_tasks = []
        for collector in self.collectors.values():
            if collector.is_running:
                stop_tasks.append(self._safe_stop_collector(collector))

        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

        self.logger.info("All collectors stopped")

    async def _safe_stop_collector(self, collector: BaseCollector) -> None:
        """Safely stop a collector with error handling."""
        try:
            await collector.stop()
        except Exception as e:
            self.logger.error(f"Error stopping collector {collector.name}: {e}")

    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all collectors."""
        return {
            name: {
                "running": collector.is_running,
                "type": type(collector).__name__,
                "config": collector.config,
            }
            for name, collector in self.collectors.items()
        }

    def get_collector(self, name: str) -> Optional[BaseCollector]:
        """Get a collector by name."""
        return self.collectors.get(name)

    def list_available_collectors(self) -> List[str]:
        """List all available collector types."""
        return list(self._collector_classes.keys())

    def list_active_collectors(self) -> List[str]:
        """List names of active collectors."""
        return list(self.collectors.keys())
