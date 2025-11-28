"""File logger agent - logs file changes to a file."""

import json
from pathlib import Path

from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event


class FileLoggerAgent(Agent):
    """Agent that logs file changes to .devloop/file-changes.log"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_file = Path(".devloop/file-changes.log")
        self.log_file.parent.mkdir(exist_ok=True)

    async def handle(self, event: Event) -> AgentResult:
        """Log file change to file."""
        # Only handle file events
        if not event.type.startswith("file:"):
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message="Skipped non-file event",
            )

        # Create log entry
        log_entry = {
            "timestamp": event.timestamp,
            "event_type": event.type,
            "path": event.payload.get("path", "unknown"),
            "source": event.source,
        }

        # Append to log file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0,
            message=f"Logged {event.type}: {event.payload.get('path', 'unknown')}",
        )
