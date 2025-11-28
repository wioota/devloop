"""Base agent class - simplified for prototype."""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List

from .event import Event, EventBus


@dataclass
class AgentResult:
    """Agent execution result."""

    agent_name: str
    success: bool
    duration: float
    message: str = ""
    data: Dict[str, Any] | None = None
    error: str | None = None

    def __post_init__(self):
        """Validate AgentResult parameters."""
        # Validate agent_name
        if not isinstance(self.agent_name, str):
            raise TypeError(
                f"agent_name must be a string, got {type(self.agent_name).__name__}"
            )
        if not self.agent_name:
            raise ValueError("agent_name cannot be empty")

        # Validate success
        if not isinstance(self.success, bool):
            raise TypeError(
                f"success must be a boolean, got {type(self.success).__name__}"
            )

        # Validate duration
        if not isinstance(self.duration, (int, float)):
            raise TypeError(
                f"duration must be a number, got {type(self.duration).__name__}. "
                "Did you forget to include duration parameter in AgentResult creation?"
            )
        if self.duration < 0:
            raise ValueError(f"duration must be non-negative, got {self.duration}")

        # Validate message
        if not isinstance(self.message, str):
            raise TypeError(
                f"message must be a string, got {type(self.message).__name__}"
            )

        # Validate data
        if self.data is not None and not isinstance(self.data, dict):
            raise TypeError(
                f"data must be a dict or None, got {type(self.data).__name__}"
            )

        # Validate error
        if self.error is not None and not isinstance(self.error, str):
            raise TypeError(
                f"error must be a string or None, got {type(self.error).__name__}"
            )


class Agent(ABC):
    """Base agent class."""

    def __init__(self, name: str, triggers: List[str], event_bus: EventBus):
        self.name = name
        self.triggers = triggers
        self.event_bus = event_bus
        self.enabled = True
        self.logger = logging.getLogger(f"agent.{name}")
        self._running = False
        self._event_queue: asyncio.Queue[Event] = asyncio.Queue()

    @abstractmethod
    async def handle(self, event: Event) -> AgentResult:
        """Handle an event. Must be implemented by subclasses."""
        pass

    async def start(self) -> None:
        """Start the agent."""
        if self._running:
            return

        self._running = True

        # Subscribe to configured triggers
        for trigger in self.triggers:
            await self.event_bus.subscribe(trigger, self._event_queue)

        # Start event processing loop
        asyncio.create_task(self._process_events())
        self.logger.info(f"Agent {self.name} started, listening to {self.triggers}")

    async def stop(self) -> None:
        """Stop the agent."""
        if not self._running:
            return

        self._running = False

        # Unsubscribe from events
        for trigger in self.triggers:
            await self.event_bus.unsubscribe(trigger, self._event_queue)

        self.logger.info(f"Agent {self.name} stopped")

    async def _process_events(self) -> None:
        """Process events from the queue."""
        while self._running:
            try:
                # Wait for event with timeout to allow checking _running
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if not self.enabled:
                continue

            # Execute handler
            try:
                start_time = time.time()
                result = await self.handle(event)
                result.duration = time.time() - start_time

                # Publish result
                await self._publish_result(result)

                # Log result
                status = "✓" if result.success else "✗"
                self.logger.info(
                    f"{status} {self.name}: {result.message} ({result.duration:.2f}s)"
                )

            except Exception as e:
                self.logger.error(f"Error in {self.name}: {e}", exc_info=True)
                await self._publish_result(
                    AgentResult(
                        agent_name=self.name,
                        success=False,
                        duration=time.time() - start_time,
                        error=str(e),
                    )
                )

    async def _publish_result(self, result: AgentResult) -> None:
        """Publish agent result as an event."""
        await self.event_bus.emit(
            Event(
                type=f"agent:{self.name}:completed",
                payload={
                    "agent_name": result.agent_name,
                    "success": result.success,
                    "duration": result.duration,
                    "message": result.message,
                    "data": result.data,
                    "error": result.error,
                },
                source=self.name,
            )
        )
