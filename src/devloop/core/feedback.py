"""Feedback system for agent behavior learning."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import aiofiles


class FeedbackType(Enum):
    """Types of feedback that can be given to agents."""

    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RATING = "rating"  # 1-5 stars
    COMMENT = "comment"
    DISMISS = "dismiss"  # User dismissed/ignored the agent's action


@dataclass
class Feedback:
    """Individual feedback item."""

    id: str
    agent_name: str
    event_type: str
    feedback_type: FeedbackType
    value: Any  # thumbs_up/down: bool, rating: int 1-5, comment: str, dismiss: None
    comment: Optional[str] = None
    context: Optional[Dict[str, Any]] = None  # Agent result data, file info, etc.
    timestamp: Optional[float] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

        # Validate feedback values
        if self.feedback_type == FeedbackType.RATING:
            if not isinstance(self.value, int) or not (1 <= self.value <= 5):
                raise ValueError("Rating must be an integer between 1 and 5")
        elif self.feedback_type in (FeedbackType.THUMBS_UP, FeedbackType.THUMBS_DOWN):
            if not isinstance(self.value, bool):
                raise ValueError("Thumbs feedback must be a boolean")
        elif self.feedback_type == FeedbackType.COMMENT:
            if not isinstance(self.value, str):
                raise ValueError("Comment feedback must be a string")
        elif self.feedback_type == FeedbackType.DISMISS:
            if self.value is not None:
                raise ValueError("Dismiss feedback value must be None")


@dataclass
class AgentPerformance:
    """Aggregated performance metrics for an agent."""

    agent_name: str
    total_executions: int = 0
    successful_executions: int = 0
    average_duration: float = 0.0
    feedback_count: int = 0
    thumbs_up_count: int = 0
    thumbs_down_count: int = 0
    average_rating: float = 0.0
    last_updated: Optional[float] = None

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = time.time()


class FeedbackStore:
    """Persistent storage for agent feedback and performance data."""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.feedback_file = storage_path / "feedback.jsonl"
        self.performance_file = storage_path / "performance.json"

    async def store_feedback(self, feedback: Feedback) -> None:
        """Store a feedback item."""
        feedback_dict = {
            "id": feedback.id,
            "agent_name": feedback.agent_name,
            "event_type": feedback.event_type,
            "feedback_type": feedback.feedback_type.value,
            "value": feedback.value,
            "comment": feedback.comment,
            "context": feedback.context,
            "timestamp": feedback.timestamp,
        }

        async with aiofiles.open(self.feedback_file, "a") as f:
            await f.write(json.dumps(feedback_dict) + "\n")

    async def get_feedback_for_agent(
        self, agent_name: str, limit: int = 100
    ) -> List[Feedback]:
        """Get recent feedback for a specific agent."""
        feedback_items: List[Feedback] = []

        if not self.feedback_file.exists():
            return feedback_items

        async with aiofiles.open(self.feedback_file, "r") as f:
            lines = await f.readlines()

        # Parse feedback items for this agent
        for line in reversed(lines):  # Most recent first
            if len(feedback_items) >= limit:
                break

            try:
                data = json.loads(line.strip())
                if data["agent_name"] == agent_name:
                    feedback_items.append(
                        Feedback(
                            id=data["id"],
                            agent_name=data["agent_name"],
                            event_type=data["event_type"],
                            feedback_type=FeedbackType(data["feedback_type"]),
                            value=data["value"],
                            comment=data["comment"],
                            context=data["context"],
                            timestamp=data["timestamp"],
                        )
                    )
            except (json.JSONDecodeError, KeyError):
                continue

        return feedback_items

    async def update_performance(
        self, agent_name: str, success: bool, duration: float
    ) -> None:
        """Update performance metrics for an agent."""
        performance = await self.get_performance(agent_name)

        performance.total_executions += 1
        if success:
            performance.successful_executions += 1

        # Update rolling average duration
        if performance.total_executions == 1:
            performance.average_duration = duration
        else:
            performance.average_duration = (
                (performance.average_duration * (performance.total_executions - 1))
                + duration
            ) / performance.total_executions

        performance.last_updated = time.time()

        await self._save_performance(performance)

    async def update_performance_with_feedback(
        self, agent_name: str, feedback: Feedback
    ) -> None:
        """Update performance metrics with feedback data."""
        performance = await self.get_performance(agent_name)

        performance.feedback_count += 1

        if feedback.feedback_type == FeedbackType.THUMBS_UP and feedback.value:
            performance.thumbs_up_count += 1
        elif feedback.feedback_type == FeedbackType.THUMBS_DOWN and feedback.value:
            performance.thumbs_down_count += 1
        elif feedback.feedback_type == FeedbackType.RATING:
            # Update rolling average rating
            if performance.feedback_count == 1:
                performance.average_rating = feedback.value
            else:
                performance.average_rating = (
                    (performance.average_rating * (performance.feedback_count - 1))
                    + feedback.value
                ) / performance.feedback_count

        performance.last_updated = time.time()

        await self._save_performance(performance)

    async def get_performance(self, agent_name: str) -> AgentPerformance:
        """Get performance metrics for an agent."""
        if not self.performance_file.exists():
            return AgentPerformance(agent_name=agent_name)

        async with aiofiles.open(self.performance_file, "r") as f:
            content = await f.read()

        try:
            data = json.loads(content)
            agent_data = data.get(agent_name, {})
            return AgentPerformance(
                agent_name=agent_name,
                total_executions=agent_data.get("total_executions", 0),
                successful_executions=agent_data.get("successful_executions", 0),
                average_duration=agent_data.get("average_duration", 0.0),
                feedback_count=agent_data.get("feedback_count", 0),
                thumbs_up_count=agent_data.get("thumbs_up_count", 0),
                thumbs_down_count=agent_data.get("thumbs_down_count", 0),
                average_rating=agent_data.get("average_rating", 0.0),
                last_updated=agent_data.get("last_updated", time.time()),
            )
        except (json.JSONDecodeError, KeyError):
            return AgentPerformance(agent_name=agent_name)

    async def _save_performance(self, performance: AgentPerformance) -> None:
        """Save performance data to disk."""
        # Load existing data
        data = {}
        if self.performance_file.exists():
            async with aiofiles.open(self.performance_file, "r") as f:
                content = await f.read()
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                data = {}

        # Update with new performance data
        data[performance.agent_name] = {
            "total_executions": performance.total_executions,
            "successful_executions": performance.successful_executions,
            "average_duration": performance.average_duration,
            "feedback_count": performance.feedback_count,
            "thumbs_up_count": performance.thumbs_up_count,
            "thumbs_down_count": performance.thumbs_down_count,
            "average_rating": performance.average_rating,
            "last_updated": performance.last_updated,
        }

        # Save back to file
        async with aiofiles.open(self.performance_file, "w") as f:
            await f.write(json.dumps(data, indent=2))


class FeedbackAPI:
    """API for collecting and managing feedback."""

    def __init__(self, feedback_store: FeedbackStore):
        self.feedback_store = feedback_store

    async def submit_feedback(
        self,
        agent_name: str,
        event_type: str,
        feedback_type: FeedbackType,
        value: Any,
        comment: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Submit feedback for an agent."""
        feedback = Feedback(
            id=str(uuid4()),
            agent_name=agent_name,
            event_type=event_type,
            feedback_type=feedback_type,
            value=value,
            comment=comment,
            context=context,
        )

        await self.feedback_store.store_feedback(feedback)
        await self.feedback_store.update_performance_with_feedback(agent_name, feedback)

        return feedback.id

    async def get_agent_insights(self, agent_name: str) -> Dict[str, Any]:
        """Get insights about an agent's performance and feedback."""
        performance = await self.feedback_store.get_performance(agent_name)
        recent_feedback = await self.feedback_store.get_feedback_for_agent(
            agent_name, limit=20
        )

        success_rate = (
            (performance.successful_executions / performance.total_executions * 100)
            if performance.total_executions > 0
            else 0
        )

        thumbs_up_rate = (
            (performance.thumbs_up_count / performance.feedback_count * 100)
            if performance.feedback_count > 0
            else 0
        )

        return {
            "agent_name": agent_name,
            "performance": {
                "total_executions": performance.total_executions,
                "success_rate": round(success_rate, 1),
                "average_duration": round(performance.average_duration, 2),
                "feedback_count": performance.feedback_count,
                "thumbs_up_rate": round(thumbs_up_rate, 1),
                "average_rating": round(performance.average_rating, 1),
            },
            "recent_feedback": [
                {
                    "type": f.feedback_type.value,
                    "value": f.value,
                    "comment": f.comment,
                    "timestamp": f.timestamp,
                }
                for f in recent_feedback[:5]  # Last 5 feedback items
            ],
        }
