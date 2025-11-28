"""Proactive feedback collection at natural development breakpoints."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable

from .event import Event, EventBus
from .feedback import FeedbackAPI, FeedbackType


@dataclass
class FeedbackPrompt:
    """Represents a proactive feedback prompt."""

    id: str
    agent_name: str
    event_type: str
    prompt_type: str  # 'quick_rating', 'detailed_feedback', 'thumbs_only'
    message: str
    context: Dict[str, any]
    timestamp: float
    expires_at: float
    callback: Optional[Callable] = None

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class ProactiveFeedbackManager:
    """Manages proactive feedback prompts at natural development breakpoints."""

    def __init__(
        self,
        event_bus: EventBus,
        feedback_api: FeedbackAPI
    ):
        self.event_bus = event_bus
        self.feedback_api = feedback_api

        # Active prompts waiting for developer response
        self.active_prompts: Dict[str, FeedbackPrompt] = {}

        # Prompt timing configuration
        self.prompt_delays = {
            "after_agent_success": 5,    # 5 seconds after successful agent action
            "after_agent_failure": 2,    # 2 seconds after failed agent action
            "after_file_save": 3,        # 3 seconds after file save
            "after_build_success": 10,   # 10 seconds after successful build
            "after_build_failure": 5,    # 5 seconds after build failure
            "idle_period": 300,          # 5 minutes of inactivity
        }

        # Prompt expiration times
        self.prompt_lifetimes = {
            "quick_rating": 60,      # 1 minute for quick ratings
            "thumbs_only": 120,      # 2 minutes for thumbs up/down
            "detailed_feedback": 300, # 5 minutes for detailed feedback
        }

        self._setup_event_listeners()

    def _setup_event_listeners(self):
        """Set up listeners for development events that trigger feedback prompts."""
        # Agent completion events
        asyncio.create_task(self.event_bus.subscribe("agent:*:completed", self._on_agent_completed))

        # File system events
        asyncio.create_task(self.event_bus.subscribe("file:saved", self._on_file_saved))
        asyncio.create_task(self.event_bus.subscribe("file:modified", self._on_file_modified))

        # Build/test events (could be extended)
        asyncio.create_task(self.event_bus.subscribe("build:success", self._on_build_success))
        asyncio.create_task(self.event_bus.subscribe("build:failure", self._on_build_failure))

        # Git events
        asyncio.create_task(self.event_bus.subscribe("git:commit", self._on_git_commit))

    async def _on_agent_completed(self, event: Event) -> None:
        """Handle agent completion and schedule feedback prompt."""
        agent_name = event.payload.get("agent_name")
        success = event.payload.get("success", False)

        if success:
            await self._schedule_prompt(
                agent_name=agent_name,
                event_type="agent:completed",
                prompt_type="quick_rating",
                message=f"How was the {agent_name} agent's recent action?",
                context=event.payload,
                delay_seconds=self.prompt_delays["after_agent_success"]
            )
        else:
            # For failures, ask for feedback more urgently
            await self._schedule_prompt(
                agent_name=agent_name,
                event_type="agent:completed",
                prompt_type="thumbs_only",
                message=f"{agent_name} encountered an issue. Was this expected?",
                context=event.payload,
                delay_seconds=self.prompt_delays["after_agent_failure"]
            )

    async def _on_file_saved(self, event: Event) -> None:
        """Handle file save events."""
        # Only prompt occasionally to avoid being annoying
        if asyncio.get_event_loop().time() % 10 < 1:  # ~10% of the time
            await self._schedule_prompt(
                agent_name="filesystem",  # Generic agent for file operations
                event_type="file:saved",
                prompt_type="thumbs_only",
                message="How are you finding the file monitoring features?",
                context=event.payload,
                delay_seconds=self.prompt_delays["after_file_save"]
            )

    async def _on_file_modified(self, event: Event) -> None:
        """Handle file modification events."""
        # Less frequent prompts for modifications
        pass  # Could be implemented for specific scenarios

    async def _on_build_success(self, event: Event) -> None:
        """Handle successful build events."""
        await self._schedule_prompt(
            agent_name="build_system",
            event_type="build:success",
            prompt_type="quick_rating",
            message="Build completed successfully! How did the automated checks perform?",
            context=event.payload,
            delay_seconds=self.prompt_delays["after_build_success"]
        )

    async def _on_build_failure(self, event: Event) -> None:
        """Handle build failure events."""
        await self._schedule_prompt(
            agent_name="build_system",
            event_type="build:failure",
            prompt_type="detailed_feedback",
            message="Build failed. How can we improve the error detection and reporting?",
            context=event.payload,
            delay_seconds=self.prompt_delays["after_build_failure"]
        )

    async def _on_git_commit(self, event: Event) -> None:
        """Handle git commit events."""
        # Occasional feedback about the overall development experience
        if len(self.active_prompts) < 2:  # Don't overwhelm with too many prompts
            await self._schedule_prompt(
                agent_name="development_workflow",
                event_type="git:commit",
                prompt_type="quick_rating",
                message="How is your development workflow going?",
                context=event.payload,
                delay_seconds=1  # Immediate for commits
            )

    async def _schedule_prompt(
        self,
        agent_name: str,
        event_type: str,
        prompt_type: str,
        message: str,
        context: Dict[str, any],
        delay_seconds: int
    ) -> None:
        """Schedule a feedback prompt to be shown after a delay."""
        prompt_id = f"{agent_name}_{event_type}_{int(time.time())}"

        lifetime = self.prompt_lifetimes.get(prompt_type, 60)
        expires_at = time.time() + delay_seconds + lifetime

        prompt = FeedbackPrompt(
            id=prompt_id,
            agent_name=agent_name,
            event_type=event_type,
            prompt_type=prompt_type,
            message=message,
            context=context,
            timestamp=time.time() + delay_seconds,
            expires_at=expires_at
        )

        self.active_prompts[prompt_id] = prompt

        # Schedule the prompt display
        asyncio.create_task(self._show_prompt_after_delay(prompt, delay_seconds))

    async def _show_prompt_after_delay(self, prompt: FeedbackPrompt, delay: int) -> None:
        """Show the feedback prompt after the specified delay."""
        await asyncio.sleep(delay)

        # Check if prompt is still active and not expired
        if prompt.id in self.active_prompts and not prompt.is_expired():
            await self._display_feedback_prompt(prompt)

    async def _display_feedback_prompt(self, prompt: FeedbackPrompt) -> None:
        """Display the feedback prompt to the developer."""
        # In a real implementation, this would integrate with the IDE or terminal UI
        # For now, we'll emit an event that can be caught by UI components

        await self.event_bus.emit(Event(
            type="feedback:prompt",
            payload={
                "prompt_id": prompt.id,
                "agent_name": prompt.agent_name,
                "prompt_type": prompt.prompt_type,
                "message": prompt.message,
                "context": prompt.context,
                "expires_at": prompt.expires_at
            },
            source="proactive_feedback"
        ))

        # Set up a timeout to auto-dismiss the prompt
        asyncio.create_task(self._auto_dismiss_prompt(prompt.id, prompt.expires_at))

    async def _auto_dismiss_prompt(self, prompt_id: str, expires_at: float) -> None:
        """Auto-dismiss a prompt when it expires."""
        remaining_time = expires_at - time.time()
        if remaining_time > 0:
            await asyncio.sleep(remaining_time)

        if prompt_id in self.active_prompts:
            del self.active_prompts[prompt_id]

    async def submit_prompt_feedback(
        self,
        prompt_id: str,
        feedback_type: FeedbackType,
        value: any,
        comment: Optional[str] = None
    ) -> bool:
        """Submit feedback for a proactive prompt."""
        if prompt_id not in self.active_prompts:
            return False

        prompt = self.active_prompts[prompt_id]

        # Submit the feedback
        await self.feedback_api.submit_feedback(
            agent_name=prompt.agent_name,
            event_type=f"proactive_{prompt.event_type}",
            feedback_type=feedback_type,
            value=value,
            comment=comment,
            context={
                "prompt_id": prompt_id,
                "original_context": prompt.context,
                "feedback_source": "proactive_prompt"
            }
        )

        # Remove the prompt
        del self.active_prompts[prompt_id]
        return True

    def get_active_prompts(self) -> List[Dict[str, any]]:
        """Get list of currently active feedback prompts."""
        current_time = time.time()
        active = []

        for prompt in self.active_prompts.values():
            if not prompt.is_expired():
                active.append({
                    "id": prompt.id,
                    "agent_name": prompt.agent_name,
                    "message": prompt.message,
                    "prompt_type": prompt.prompt_type,
                    "time_remaining": max(0, prompt.expires_at - current_time)
                })

        return active

    async def dismiss_prompt(self, prompt_id: str) -> bool:
        """Dismiss a feedback prompt without submitting feedback."""
        if prompt_id in self.active_prompts:
            del self.active_prompts[prompt_id]
            return True
        return False

    def cleanup_expired_prompts(self) -> int:
        """Clean up expired prompts and return count removed."""
        current_time = time.time()
        expired_ids = [
            pid for pid, prompt in self.active_prompts.items()
            if prompt.is_expired()
        ]

        for pid in expired_ids:
            del self.active_prompts[pid]

        return len(expired_ids)
