"""Base collector class."""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from dev_agents.core.event import Event, EventBus, Priority


class BaseCollector(ABC):
    """Base class for all event collectors."""

    def __init__(
        self,
        name: str,
        event_bus: EventBus,
        config: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.event_bus = event_bus
        self.config = config or {}
        self.logger = logging.getLogger(f"collector.{name}")
        self._running = False

    @abstractmethod
    async def start(self) -> None:
        """Start the collector."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the collector."""
        pass

    @property
    def is_running(self) -> bool:
        """Check if collector is running."""
        return self._running

    def _set_running(self, running: bool) -> None:
        """Set running state."""
        self._running = running

    async def _emit_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        priority: str = "normal",
        source: Optional[str] = None
    ) -> None:
        """Emit an event to the event bus."""
        prio = Priority.NORMAL if priority == "normal" else Priority.HIGH
        event = Event(
            type=event_type,
            payload=payload,
            source=source or self.name,
            priority=prio
        )
        await self.event_bus.emit(event)
