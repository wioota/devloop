"""Agent manager for centralized control."""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional

from dev_agents.core.agent import Agent
from dev_agents.core.context_store import context_store
from dev_agents.core.event import Event, EventBus


class AgentManager:
    """Manages agent lifecycle and coordination."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.agents: Dict[str, Agent] = {}
        self.logger = logging.getLogger("agent_manager")
        self._paused_agents: set[str] = set()

    def register(self, agent: Agent) -> None:
        """Register an agent."""
        self.agents[agent.name] = agent
        self.logger.info(f"Registered agent: {agent.name}")

    async def start_all(self) -> None:
        """Start all registered agents."""
        # Subscribe to agent completion events for consolidated results
        await self.event_bus.subscribe("agent:*:completed", self._on_agent_completed)

        tasks = [agent.start() for agent in self.agents.values() if agent.enabled]
        await asyncio.gather(*tasks)
        self.logger.info(
            f"Started {len([a for a in self.agents.values() if a.enabled])} agents"
        )

    async def stop_all(self) -> None:
        """Stop all agents."""
        tasks = [agent.stop() for agent in self.agents.values()]
        await asyncio.gather(*tasks)
        self.logger.info("Stopped all agents")

    async def start_agent(self, name: str) -> bool:
        """Start a specific agent."""
        if name in self.agents:
            await self.agents[name].start()
            return True
        return False

    async def stop_agent(self, name: str) -> bool:
        """Stop a specific agent."""
        if name in self.agents:
            await self.agents[name].stop()
            return True
        return False

    def enable_agent(self, name: str) -> bool:
        """Enable an agent."""
        if name in self.agents:
            self.agents[name].enabled = True
            self.logger.info(f"Enabled agent: {name}")
            return True
        return False

    def disable_agent(self, name: str) -> bool:
        """Disable an agent."""
        if name in self.agents:
            self.agents[name].enabled = False
            self.logger.info(f"Disabled agent: {name}")
            return True
        return False

    async def pause_agents(
        self, agents: Optional[List[str]] = None, reason: str = ""
    ) -> None:
        """Pause specific agents (or all)."""
        target_agents = agents or list(self.agents.keys())

        for agent_name in target_agents:
            if agent_name in self.agents:
                self.agents[agent_name].enabled = False
                self._paused_agents.add(agent_name)

        self.logger.info(f"Paused agents: {target_agents} (reason: {reason})")

    async def resume_agents(self, agents: Optional[List[str]] = None) -> None:
        """Resume paused agents."""
        target_agents = agents or list(self._paused_agents)

        for agent_name in target_agents:
            if agent_name in self.agents:
                self.agents[agent_name].enabled = True
                self._paused_agents.discard(agent_name)

        self.logger.info(f"Resumed agents: {target_agents}")

    def get_status(self) -> Dict[str, Dict[str, any]]:
        """Get status of all agents."""
        return {
            name: {
                "running": agent._running,
                "enabled": agent.enabled,
                "paused": name in self._paused_agents,
                "triggers": agent.triggers,
            }
            for name, agent in self.agents.items()
        }

    def get_agent(self, name: str) -> Optional[Agent]:
        """Get an agent by name."""
        return self.agents.get(name)

    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self.agents.keys())

    async def _on_agent_completed(self, event: Event) -> None:
        """Handle agent completion events and update consolidated results."""
        try:
            # Update consolidated results for Claude Code integration
            context_store.write_consolidated_results()
        except Exception as e:
            self.logger.error(f"Failed to write consolidated results: {e}")
