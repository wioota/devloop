"""Agent Health Monitor Agent - monitors other agents and triggers fixes on failures."""

import logging
from typing import Dict, Any

from dev_agents.core.agent import Agent, AgentResult
from dev_agents.core.auto_fix import auto_fix
from dev_agents.core.context_store import context_store
from dev_agents.core.event import Event


logger = logging.getLogger(__name__)


class AgentHealthMonitorAgent(Agent):
    """Monitors other agents for failures and triggers autonomous fixes."""

    def __init__(self, name: str, triggers: list[str], event_bus, config: Dict[str, Any]):
        super().__init__(name, triggers, event_bus)
        self.config = config

    async def handle(self, event: Event) -> AgentResult:
        """Handle agent completion events and trigger fixes on failures."""
        try:
            payload = event.payload

            # Extract result information
            agent_name = payload.get("agent_name", "")
            success = payload.get("success", True)
            error = payload.get("error", "")
            message = payload.get("message", "")

            # Skip if this is our own completion event to avoid loops
            if agent_name == self.name:
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    duration=0.0,
                    message="Skipped monitoring own completion"
                )

            # Check if the agent failed
            if not success or error:
                logger.info(f"Detected failure in {agent_name}: {error or message}")

                # Apply autonomous fixes
                applied_fixes = await auto_fix.apply_safe_fixes()

                if applied_fixes:
                    fix_summary = ", ".join(f"{k}: {v}" for k, v in applied_fixes.items())
                    agent_result = AgentResult(
                        agent_name=self.name,
                        success=True,
                        duration=0.0,
                        message=f"Applied fixes for {agent_name} failure: {fix_summary}",
                        data={"applied_fixes": applied_fixes}
                    )
                    context_store.write_finding(agent_result)
                    return agent_result
                else:
                    agent_result = AgentResult(
                        agent_name=self.name,
                        success=True,
                        duration=0.0,
                        message=f"No safe fixes available for {agent_name} failure",
                        data={"applied_fixes": {}}
                    )
                    context_store.write_finding(agent_result)
                    return agent_result

            # Agent succeeded, nothing to do
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0.0,
                message=f"{agent_name} completed successfully"
            )

        except Exception as e:
            logger.error(f"Error in health monitor: {e}")
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0.0,
                error=str(e)
            )
