"""Event replay system for recovery after daemon crashes.

This module handles:
- Replaying missed events to agents during startup
- Detecting gaps in the event sequence
- Restoring agents to their last known state
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from devloop.core.event import EventBus
from devloop.core.event_store import event_store

if TYPE_CHECKING:
    from devloop.core.manager import AgentManager

logger = logging.getLogger(__name__)


class EventReplayer:
    """Handles replay of missed events after daemon recovery."""

    def __init__(self, event_bus: EventBus, agent_manager: AgentManager):
        """Initialize replayer.

        Args:
            event_bus: Event bus for emitting replayed events
            agent_manager: Agent manager to get agent names and trigger replays
        """
        self.event_bus = event_bus
        self.agent_manager = agent_manager

    async def replay_all_agents(self) -> dict[str, Any]:
        """Replay missed events for all registered agents.

        Returns:
            Dictionary with replay statistics:
            - total_replayed: Total events replayed
            - agents: Dict mapping agent names to number of events replayed
            - gaps: Any detected gaps in event sequence
        """
        logger.info("Starting event replay for all agents...")

        gaps = await event_store.detect_gaps()
        stats: dict[str, Any] = {
            "total_replayed": 0,
            "agents": {},
            "gaps": gaps,
        }

        # Log any detected gaps
        if gaps:
            logger.warning(f"Detected {len(gaps)} gaps in event sequence:")
            for gap_range, size in gaps.items():
                logger.warning(f"  Gap {gap_range}: {size} missing events")

        # Replay for each agent
        for agent in self.agent_manager.agents.values():
            agent_replayed = await self.replay_agent(agent.name)
            stats["agents"][agent.name] = agent_replayed
            stats["total_replayed"] = stats["total_replayed"] + agent_replayed

        if stats["total_replayed"] > 0:
            logger.info(f"Replayed {stats['total_replayed']} total events to agents")

        return stats

    async def replay_agent(self, agent_name: str) -> int:
        """Replay missed events for a specific agent.

        Args:
            agent_name: Name of agent to replay events for

        Returns:
            Number of events replayed
        """
        # Get missed events for this agent
        missed_events = await event_store.get_missed_events(agent_name)

        if not missed_events:
            logger.debug(f"No missed events for agent {agent_name}")
            return 0

        logger.info(f"Replaying {len(missed_events)} missed events to {agent_name}")

        # Re-emit missed events to subscribers
        for event in missed_events:
            # Emit to the same event bus (agents already subscribed)
            await self.event_bus.emit(event)

            # Update agent's replay state after each event
            # (in case of another crash during replay)
            await event_store.update_replay_state(
                agent_name, event.sequence, event.timestamp
            )

        logger.info(f"Replayed {len(missed_events)} events to {agent_name}")
        return len(missed_events)

    async def get_replay_summary(self) -> dict[str, Any]:
        """Get summary of replay state for all agents.

        Returns:
            Dictionary mapping agent names to their replay state
        """
        summary: dict[str, Any] = {}

        for agent in self.agent_manager.agents.values():
            state = await event_store.get_replay_state(agent.name)
            summary[agent.name] = state or {
                "last_processed_sequence": 0,
                "last_processed_timestamp": 0,
            }

        return summary
