"""Contextual feedback inference from developer behavior patterns."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .event import Event, EventBus
from .feedback import FeedbackAPI, FeedbackType


@dataclass
class DeveloperAction:
    """Represents a developer action that can provide implicit feedback."""

    action_type: (
        str  # 'file_save', 'file_edit', 'cursor_move', 'suggestion_accept', etc.
    )
    file_path: Optional[str]
    timestamp: float
    context: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}


class ContextualFeedbackEngine:
    """Engine that infers feedback from developer behavior patterns."""

    def __init__(
        self, event_bus: EventBus, feedback_api: FeedbackAPI, project_dir: Path
    ):
        self.event_bus = event_bus
        self.feedback_api = feedback_api
        self.project_dir = project_dir

        # Track recent developer actions
        self.recent_actions: List[DeveloperAction] = []
        self.action_window = 300  # 5 minutes window for action correlation

        # Track agent actions to correlate with developer responses
        self.recent_agent_actions: List[Dict[str, Any]] = []
        self.agent_action_window = 600  # 10 minutes

        # File interaction patterns
        self.file_interaction_times: Dict[str, List[float]] = {}
        self.file_last_modified: Dict[str, float] = {}

        # Initialize event subscriptions
        self._setup_event_listeners()

    def _setup_event_listeners(self):
        """Set up listeners for various developer actions."""
        # Listen for agent completion events to correlate with developer actions
        asyncio.create_task(
            self.event_bus.subscribe("agent:*:completed", self._on_agent_completed)
        )

        # Listen for file system events that indicate developer activity
        asyncio.create_task(self.event_bus.subscribe("file:*", self._on_file_event))

        # Could be extended to listen for IDE events like cursor movements, selections, etc.

    async def _on_agent_completed(self, event: Event) -> None:
        """Handle agent completion and look for correlated developer feedback."""
        agent_name = event.payload.get("agent_name")
        success = event.payload.get("success", False)
        duration = event.payload.get("duration", 0)

        # Store agent action for correlation
        agent_action = {
            "agent_name": agent_name,
            "success": success,
            "duration": duration,
            "timestamp": time.time(),
            "event": event.payload,
        }

        self.recent_agent_actions.append(agent_action)

        # Clean old agent actions
        cutoff = time.time() - self.agent_action_window
        self.recent_agent_actions = [
            action
            for action in self.recent_agent_actions
            if action["timestamp"] > cutoff
        ]

        # Check for immediate feedback patterns
        await self._analyze_immediate_feedback(agent_action)

    async def _on_file_event(self, event: Event) -> None:
        """Handle file system events as developer actions."""
        file_path = event.payload.get("path")
        if not file_path:
            return

        action = DeveloperAction(
            action_type=f"file_{event.type.split(':')[1]}",  # file_modified, file_created, etc.
            file_path=file_path,
            timestamp=time.time(),
            context={"event_payload": event.payload},
        )

        self.recent_actions.append(action)

        # Track file interaction patterns
        if file_path not in self.file_interaction_times:
            self.file_interaction_times[file_path] = []

        self.file_interaction_times[file_path].append(action.timestamp)

        # Keep only recent interactions (last 24 hours)
        cutoff = time.time() - 86400
        self.file_interaction_times[file_path] = [
            t for t in self.file_interaction_times[file_path] if t > cutoff
        ]

        # Update last modified time
        if event.type == "file:modified":
            self.file_last_modified[file_path] = action.timestamp

        # Analyze patterns
        await self._analyze_file_patterns(file_path, action)

    async def _analyze_immediate_feedback(self, agent_action: Dict[str, Any]) -> None:
        """Analyze immediate feedback patterns after agent actions."""
        agent_time = agent_action["timestamp"]

        # Look for developer actions within 30 seconds after agent action
        immediate_window = 30
        recent_actions = [
            action
            for action in self.recent_actions
            if agent_time <= action.timestamp <= agent_time + immediate_window
        ]

        if not recent_actions:
            return

        # Analyze the pattern of immediate actions
        file_actions = [a for a in recent_actions if a.action_type.startswith("file_")]

        if file_actions:
            # Developer made file changes shortly after agent action
            # This could indicate engagement with agent results
            await self._infer_feedback_from_file_changes(agent_action, file_actions)

    async def _analyze_file_patterns(
        self, file_path: str, latest_action: DeveloperAction
    ) -> None:
        """Analyze file interaction patterns to infer feedback."""
        if file_path not in self.file_interaction_times:
            return

        interactions = self.file_interaction_times[file_path]

        # Look for patterns that might indicate satisfaction/dissatisfaction
        if len(interactions) >= 3:
            # Calculate interaction frequency
            time_span = interactions[-1] - interactions[0]
            if time_span > 0:
                frequency = len(interactions) / time_span  # interactions per second

                # High frequency of interactions might indicate dissatisfaction
                # (developer repeatedly editing the same file)
                if frequency > 0.01:  # More than 1 interaction per 100 seconds
                    await self._infer_feedback_from_interaction_pattern(
                        file_path, frequency, "high_frequency_editing"
                    )

        # Check if file was modified shortly after being touched by agents
        last_modified = self.file_last_modified.get(file_path, 0)
        if latest_action.timestamp - last_modified < 60:  # Modified within 1 minute
            await self._infer_feedback_from_quick_modification(file_path, latest_action)

    async def _infer_feedback_from_file_changes(
        self, agent_action: Dict[str, Any], file_actions: List[DeveloperAction]
    ) -> None:
        """Infer feedback from file changes after agent action."""

        # If developer modifies files that agent just processed, it might indicate
        # they're refining the agent's work (mixed feedback)
        modified_files = set(
            a.file_path for a in file_actions if a.action_type == "file_modified"
        )

        if modified_files:
            # Submit neutral/mixed feedback
            await self.feedback_api.submit_feedback(
                agent_name=agent_action["agent_name"],
                event_type="file_interaction",
                feedback_type=FeedbackType.RATING,
                value=3,  # Neutral rating
                comment="Developer refined agent output",
                context={
                    "agent_action": agent_action,
                    "modified_files": list(modified_files),
                    "inference_type": "file_changes_after_agent",
                },
            )

    async def _infer_feedback_from_interaction_pattern(
        self, file_path: str, frequency: float, pattern_type: str
    ) -> None:
        """Infer feedback from file interaction patterns."""
        # Find agents that recently worked on this file
        recent_agents = []
        for agent_action in self.recent_agent_actions[-10:]:  # Last 10 agent actions
            # This is a simplified check - in reality we'd need to correlate
            # agent actions with specific files
            recent_agents.append(agent_action["agent_name"])

        if not recent_agents:
            return

        # High frequency editing might indicate dissatisfaction
        if frequency > 0.02:  # Very high frequency
            feedback_value = 2  # Low rating
            comment = f"High frequency file editing detected ({frequency:.3f} interactions/sec)"
        elif frequency > 0.01:  # Moderately high
            feedback_value = 3  # Neutral rating
            comment = f"Moderate file interaction frequency ({frequency:.3f} interactions/sec)"
        else:
            return  # Normal frequency, no inference needed

        # Submit feedback for the most recent agent
        most_recent_agent = recent_agents[-1]
        await self.feedback_api.submit_feedback(
            agent_name=most_recent_agent,
            event_type="file_interaction_pattern",
            feedback_type=FeedbackType.RATING,
            value=feedback_value,
            comment=comment,
            context={
                "file_path": file_path,
                "interaction_frequency": frequency,
                "pattern_type": pattern_type,
                "inference_type": "interaction_pattern",
            },
        )

    async def _infer_feedback_from_quick_modification(
        self, file_path: str, action: DeveloperAction
    ) -> None:
        """Infer feedback from quick file modifications."""
        # Find the most recent agent that might have worked on this file
        # This is simplified - in a real implementation we'd track agent-file associations
        recent_agent = None
        for agent_action in reversed(self.recent_agent_actions[-5:]):
            # Simplified check - look for agents that completed recently
            if time.time() - agent_action["timestamp"] < 300:  # Within 5 minutes
                recent_agent = agent_action["agent_name"]
                break

        if not recent_agent:
            return

        # Quick modification might indicate the developer is actively working
        # with the agent's output, which is generally positive
        await self.feedback_api.submit_feedback(
            agent_name=recent_agent,
            event_type="quick_file_modification",
            feedback_type=FeedbackType.THUMBS_UP,
            value=True,
            comment="Developer quickly engaged with agent output",
            context={
                "file_path": file_path,
                "time_since_agent": time.time() - (recent_agent and 0 or time.time()),
                "inference_type": "quick_modification",
            },
        )

    async def get_contextual_insights(self, agent_name: str) -> Dict[str, Any]:
        """Get contextual insights about developer behavior patterns."""
        # Analyze recent actions for patterns
        cutoff_time = time.time() - 3600  # Last hour

        agent_related_actions = []
        for action in self.recent_agent_actions:
            if action["agent_name"] == agent_name and action["timestamp"] > cutoff_time:
                agent_related_actions.append(action)

        # Count correlated developer actions
        correlated_file_actions = 0
        for agent_action in agent_related_actions:
            agent_time = agent_action["timestamp"]
            # Count developer actions within 5 minutes after agent action
            correlated = sum(
                1
                for action in self.recent_actions
                if agent_time <= action.timestamp <= agent_time + 300
            )
            correlated_file_actions += correlated

        return {
            "agent_name": agent_name,
            "time_window_hours": 1,
            "agent_actions_count": len(agent_related_actions),
            "correlated_developer_actions": correlated_file_actions,
            "inference_types": [
                "file_changes",
                "interaction_patterns",
                "quick_modifications",
            ],
            "confidence_level": "medium",  # Could be improved with ML
        }
