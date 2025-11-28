"""Agent manager for centralized control with feedback and performance."""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional

from dev_agents.core.agent import Agent
from dev_agents.core.context_store import context_store
from dev_agents.core.event import Event, EventBus
from dev_agents.core.feedback import FeedbackAPI, FeedbackStore
from dev_agents.core.performance import PerformanceMonitor


class AgentManager:
    """Manages agent lifecycle and coordination with feedback and performance."""

    def __init__(
        self,
        event_bus: EventBus,
        project_dir: Optional[Path] = None,
        enable_feedback: bool = True,
        enable_performance: bool = True,
    ):
        self.event_bus = event_bus
        self.agents: Dict[str, Agent] = {}
        self.logger = logging.getLogger("agent_manager")
        self._paused_agents: set[str] = set()

        # Initialize feedback and performance systems
        self.project_dir = project_dir or Path.cwd()
        self.feedback_api = None
        self.performance_monitor = None

        if enable_feedback:
            feedback_storage = self.project_dir / ".claude" / "feedback"
            feedback_store = FeedbackStore(feedback_storage)
            self.feedback_api = FeedbackAPI(feedback_store)

        if enable_performance:
            performance_storage = self.project_dir / ".claude" / "performance"
            self.performance_monitor = PerformanceMonitor(performance_storage)

    def register(self, agent: Agent) -> None:
        """Register an agent."""
        # Inject feedback and performance systems if not already set
        if hasattr(agent, "feedback_api") and agent.feedback_api is None:
            agent.feedback_api = self.feedback_api
        if hasattr(agent, "performance_monitor") and agent.performance_monitor is None:
            agent.performance_monitor = self.performance_monitor

        self.agents[agent.name] = agent
        self.logger.info(f"Registered agent: {agent.name}")

    def create_agent(
        self, agent_class, name: str, triggers: List[str], **kwargs
    ) -> Agent:
        """Create and register an agent with feedback/performance systems."""
        # Build kwargs for agent constructor
        agent_kwargs = {
            "name": name,
            "triggers": triggers,
            "event_bus": self.event_bus,
            **kwargs,
        }

        # Add optional feedback/performance parameters if the agent class supports them
        import inspect

        sig = inspect.signature(agent_class.__init__)
        if "feedback_api" in sig.parameters:
            agent_kwargs["feedback_api"] = self.feedback_api
        if "performance_monitor" in sig.parameters:
            agent_kwargs["performance_monitor"] = self.performance_monitor

        agent = agent_class(**agent_kwargs)
        self.register(agent)
        return agent

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

    async def get_agent_insights(self, agent_name: str) -> Optional[Dict[str, any]]:
        """Get insights for a specific agent."""
        if not self.feedback_api:
            return None
        return await self.feedback_api.get_agent_insights(agent_name)

    async def get_system_health(self) -> Optional[Dict[str, any]]:
        """Get current system health metrics."""
        if not self.performance_monitor:
            return None
        return await self.performance_monitor.get_system_health()

    async def submit_feedback(
        self,
        agent_name: str,
        feedback_type,
        value,
        event_type=None,
        comment=None,
        context=None,
    ):
        """Submit feedback for an agent."""
        if not self.feedback_api:
            return None
        return await self.feedback_api.submit_feedback(
            agent_name=agent_name,
            event_type=event_type or "manual",
            feedback_type=feedback_type,
            value=value,
            comment=comment,
            context=context,
        )

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
