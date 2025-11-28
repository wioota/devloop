"""Echo agent - simply logs received events (for testing)."""
from dev_agents.core.agent import Agent, AgentResult
from dev_agents.core.event import Event


class EchoAgent(Agent):
    """Agent that echoes all events it receives."""

    async def handle(self, event: Event) -> AgentResult:
        """Echo the event."""
        message = f"Received {event.type} from {event.source}"

        # Log payload for file events
        if "file" in event.type and "path" in event.payload:
            message += f": {event.payload['path']}"

        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0,
            message=message,
            data=event.payload
        )
