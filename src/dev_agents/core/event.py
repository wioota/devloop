"""Event system core - simplified for prototype."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Set


class Priority(Enum):
    """Event priority levels."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """Base event class."""

    type: str
    payload: Dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"
    priority: Priority = Priority.NORMAL

    def __lt__(self, other: Event) -> bool:
        """Compare events by priority for priority queue."""
        return self.priority.value > other.priority.value


class EventBus:
    """Central event bus for publishing and subscribing to events."""

    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._event_log: list[Event] = []  # For debugging

    async def subscribe(self, event_type: str, queue: asyncio.Queue) -> None:
        """Subscribe to events of a specific type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = set()
        self._subscribers[event_type].add(queue)

    async def unsubscribe(self, event_type: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from events."""
        if event_type in self._subscribers:
            self._subscribers[event_type].discard(queue)

    async def emit(self, event: Event) -> None:
        """Emit an event to all subscribers."""
        # Log event for debugging
        self._event_log.append(event)
        if len(self._event_log) > 100:  # Keep last 100 events
            self._event_log.pop(0)

        # Store event in event store (async, non-blocking)
        from .event_store import event_store

        # Don't await - fire and forget for performance
        asyncio.create_task(event_store.store_event(event))

        # Emit to matching subscribers (supporting patterns)
        notified_queues = set()

        for pattern, queues in self._subscribers.items():
            if self._matches_pattern(event.type, pattern):
                for queue in list(queues):
                    if queue not in notified_queues:  # Avoid duplicate notifications
                        try:
                            await queue.put(event)
                            notified_queues.add(queue)
                        except (asyncio.QueueFull, asyncio.CancelledError, RuntimeError):
                            pass  # Queue might be closed or in a bad state

    def _matches_pattern(self, event_type: str, pattern: str) -> bool:
        """Check if event type matches a subscription pattern."""
        # Exact match
        if event_type == pattern:
            return True

        # Global wildcard
        if pattern == "*":
            return True

        # Pattern matching (e.g., "file:*" matches "file:created")
        if pattern.endswith("*"):
            prefix = pattern[:-1]  # Remove the *
            return event_type.startswith(prefix)

        return False

    def get_recent_events(self, count: int = 10) -> list[Event]:
        """Get recent events for debugging."""
        return self._event_log[-count:]
