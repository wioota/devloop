"""Tests for proactive_feedback module.

Tests proactive feedback collection at development breakpoints.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devloop.core.proactive_feedback import (
    FeedbackPrompt,
    ProactiveFeedbackManager,
)
from devloop.core.event import Event


class TestFeedbackPrompt:
    """Tests for FeedbackPrompt dataclass."""

    def test_init_with_all_fields(self):
        """Test FeedbackPrompt initialization."""
        callback = MagicMock()
        prompt = FeedbackPrompt(
            id="prompt-1",
            agent_name="test_agent",
            event_type="file:modified",
            prompt_type="quick_rating",
            message="How was it?",
            context={"key": "value"},
            timestamp=1000.0,
            expires_at=2000.0,
            callback=callback,
        )

        assert prompt.id == "prompt-1"
        assert prompt.agent_name == "test_agent"
        assert prompt.event_type == "file:modified"
        assert prompt.prompt_type == "quick_rating"
        assert prompt.message == "How was it?"
        assert prompt.context == {"key": "value"}
        assert prompt.timestamp == 1000.0
        assert prompt.expires_at == 2000.0
        assert prompt.callback is callback

    def test_init_with_default_callback(self):
        """Test FeedbackPrompt with default callback."""
        prompt = FeedbackPrompt(
            id="prompt-1",
            agent_name="test_agent",
            event_type="file:modified",
            prompt_type="quick_rating",
            message="How was it?",
            context={},
            timestamp=1000.0,
            expires_at=2000.0,
        )

        assert prompt.callback is None

    def test_is_expired_false(self):
        """Test is_expired returns False for future expiration."""
        prompt = FeedbackPrompt(
            id="prompt-1",
            agent_name="test_agent",
            event_type="file:modified",
            prompt_type="quick_rating",
            message="How was it?",
            context={},
            timestamp=time.time(),
            expires_at=time.time() + 1000,
        )

        assert prompt.is_expired() is False

    def test_is_expired_true(self):
        """Test is_expired returns True for past expiration."""
        prompt = FeedbackPrompt(
            id="prompt-1",
            agent_name="test_agent",
            event_type="file:modified",
            prompt_type="quick_rating",
            message="How was it?",
            context={},
            timestamp=time.time() - 2000,
            expires_at=time.time() - 1000,
        )

        assert prompt.is_expired() is True


class TestProactiveFeedbackManager:
    """Tests for ProactiveFeedbackManager."""

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        bus = MagicMock()
        bus.subscribe = AsyncMock()
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def mock_feedback_api(self):
        """Create mock feedback API."""
        api = MagicMock()
        api.submit_feedback = AsyncMock()
        return api

    def test_init(self, mock_event_bus, mock_feedback_api):
        """Test ProactiveFeedbackManager initialization."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        assert manager.event_bus is mock_event_bus
        assert manager.feedback_api is mock_feedback_api
        assert manager.active_prompts == {}
        assert "after_agent_success" in manager.prompt_delays
        assert "quick_rating" in manager.prompt_lifetimes

    def test_prompt_delays_configuration(self, mock_event_bus, mock_feedback_api):
        """Test prompt delay configuration values."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        assert manager.prompt_delays["after_agent_success"] == 5
        assert manager.prompt_delays["after_agent_failure"] == 2
        assert manager.prompt_delays["after_file_save"] == 3
        assert manager.prompt_delays["after_build_success"] == 10
        assert manager.prompt_delays["after_build_failure"] == 5
        assert manager.prompt_delays["idle_period"] == 300

    def test_prompt_lifetimes_configuration(self, mock_event_bus, mock_feedback_api):
        """Test prompt lifetime configuration values."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        assert manager.prompt_lifetimes["quick_rating"] == 60
        assert manager.prompt_lifetimes["thumbs_only"] == 120
        assert manager.prompt_lifetimes["detailed_feedback"] == 300

    @pytest.mark.asyncio
    async def test_on_agent_completed_success(self, mock_event_bus, mock_feedback_api):
        """Test handling successful agent completion."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        event = Event(
            type="agent:test:completed",
            payload={"agent_name": "test_agent", "success": True},
            source="test",
        )

        with patch.object(
            manager, "_schedule_prompt", new_callable=AsyncMock
        ) as mock_schedule:
            await manager._on_agent_completed(event)

            mock_schedule.assert_called_once()
            call_kwargs = mock_schedule.call_args[1]
            assert call_kwargs["agent_name"] == "test_agent"
            assert call_kwargs["prompt_type"] == "quick_rating"
            assert "test_agent" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_on_agent_completed_failure(self, mock_event_bus, mock_feedback_api):
        """Test handling failed agent completion."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        event = Event(
            type="agent:test:completed",
            payload={"agent_name": "test_agent", "success": False},
            source="test",
        )

        with patch.object(
            manager, "_schedule_prompt", new_callable=AsyncMock
        ) as mock_schedule:
            await manager._on_agent_completed(event)

            mock_schedule.assert_called_once()
            call_kwargs = mock_schedule.call_args[1]
            assert call_kwargs["agent_name"] == "test_agent"
            assert call_kwargs["prompt_type"] == "thumbs_only"
            assert "issue" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_on_agent_completed_no_agent_name(
        self, mock_event_bus, mock_feedback_api
    ):
        """Test handling completion without agent name."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        event = Event(
            type="agent:test:completed",
            payload={"success": True},  # No agent_name
            source="test",
        )

        with patch.object(
            manager, "_schedule_prompt", new_callable=AsyncMock
        ) as mock_schedule:
            await manager._on_agent_completed(event)
            mock_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_file_modified_does_nothing(
        self, mock_event_bus, mock_feedback_api
    ):
        """Test file modified handler does nothing (placeholder)."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        event = Event(
            type="file:modified",
            payload={"path": "/test/file.py"},
            source="test",
        )

        # Should complete without error
        await manager._on_file_modified(event)

    @pytest.mark.asyncio
    async def test_on_build_success(self, mock_event_bus, mock_feedback_api):
        """Test handling successful build event."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        event = Event(
            type="build:success",
            payload={"build_id": "123"},
            source="test",
        )

        with patch.object(
            manager, "_schedule_prompt", new_callable=AsyncMock
        ) as mock_schedule:
            await manager._on_build_success(event)

            mock_schedule.assert_called_once()
            call_kwargs = mock_schedule.call_args[1]
            assert call_kwargs["agent_name"] == "build_system"
            assert call_kwargs["event_type"] == "build:success"
            assert call_kwargs["prompt_type"] == "quick_rating"

    @pytest.mark.asyncio
    async def test_on_build_failure(self, mock_event_bus, mock_feedback_api):
        """Test handling build failure event."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        event = Event(
            type="build:failure",
            payload={"error": "Build failed"},
            source="test",
        )

        with patch.object(
            manager, "_schedule_prompt", new_callable=AsyncMock
        ) as mock_schedule:
            await manager._on_build_failure(event)

            mock_schedule.assert_called_once()
            call_kwargs = mock_schedule.call_args[1]
            assert call_kwargs["agent_name"] == "build_system"
            assert call_kwargs["event_type"] == "build:failure"
            assert call_kwargs["prompt_type"] == "detailed_feedback"

    @pytest.mark.asyncio
    async def test_on_git_commit(self, mock_event_bus, mock_feedback_api):
        """Test handling git commit event."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        event = Event(
            type="git:commit",
            payload={"commit": "abc123"},
            source="test",
        )

        with patch.object(
            manager, "_schedule_prompt", new_callable=AsyncMock
        ) as mock_schedule:
            await manager._on_git_commit(event)

            mock_schedule.assert_called_once()
            call_kwargs = mock_schedule.call_args[1]
            assert call_kwargs["agent_name"] == "development_workflow"
            assert call_kwargs["delay_seconds"] == 1  # Immediate for commits

    @pytest.mark.asyncio
    async def test_on_git_commit_too_many_prompts(
        self, mock_event_bus, mock_feedback_api
    ):
        """Test git commit doesn't add prompt when too many active."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        # Add 2 active prompts
        manager.active_prompts["p1"] = MagicMock()
        manager.active_prompts["p2"] = MagicMock()

        event = Event(
            type="git:commit",
            payload={"commit": "abc123"},
            source="test",
        )

        with patch.object(
            manager, "_schedule_prompt", new_callable=AsyncMock
        ) as mock_schedule:
            await manager._on_git_commit(event)
            mock_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_schedule_prompt(self, mock_event_bus, mock_feedback_api):
        """Test scheduling a prompt."""
        with patch.object(asyncio, "create_task") as mock_create_task:
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)
            mock_create_task.reset_mock()

            await manager._schedule_prompt(
                agent_name="test_agent",
                event_type="test:event",
                prompt_type="quick_rating",
                message="Test message",
                context={"key": "value"},
                delay_seconds=5,
            )

            assert len(manager.active_prompts) == 1
            prompt = list(manager.active_prompts.values())[0]
            assert prompt.agent_name == "test_agent"
            assert prompt.message == "Test message"
            mock_create_task.assert_called()

    @pytest.mark.asyncio
    async def test_show_prompt_after_delay_expired(
        self, mock_event_bus, mock_feedback_api
    ):
        """Test prompt not shown when expired."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        # Create expired prompt
        prompt = FeedbackPrompt(
            id="expired-prompt",
            agent_name="test",
            event_type="test",
            prompt_type="quick_rating",
            message="Test",
            context={},
            timestamp=time.time() - 100,
            expires_at=time.time() - 50,  # Already expired
        )
        manager.active_prompts["expired-prompt"] = prompt

        with patch.object(
            manager, "_display_feedback_prompt", new_callable=AsyncMock
        ) as mock_display:
            with patch.object(asyncio, "sleep", new_callable=AsyncMock):
                await manager._show_prompt_after_delay(prompt, 0)
                mock_display.assert_not_called()

    @pytest.mark.asyncio
    async def test_show_prompt_after_delay_not_active(
        self, mock_event_bus, mock_feedback_api
    ):
        """Test prompt not shown when removed from active."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        prompt = FeedbackPrompt(
            id="removed-prompt",
            agent_name="test",
            event_type="test",
            prompt_type="quick_rating",
            message="Test",
            context={},
            timestamp=time.time(),
            expires_at=time.time() + 100,
        )
        # Don't add to active_prompts

        with patch.object(
            manager, "_display_feedback_prompt", new_callable=AsyncMock
        ) as mock_display:
            with patch.object(asyncio, "sleep", new_callable=AsyncMock):
                await manager._show_prompt_after_delay(prompt, 0)
                mock_display.assert_not_called()

    @pytest.mark.asyncio
    async def test_show_prompt_after_delay_success(
        self, mock_event_bus, mock_feedback_api
    ):
        """Test prompt shown when active and not expired."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        prompt = FeedbackPrompt(
            id="active-prompt",
            agent_name="test",
            event_type="test",
            prompt_type="quick_rating",
            message="Test",
            context={},
            timestamp=time.time(),
            expires_at=time.time() + 100,
        )
        manager.active_prompts["active-prompt"] = prompt

        with patch.object(
            manager, "_display_feedback_prompt", new_callable=AsyncMock
        ) as mock_display:
            with patch.object(asyncio, "sleep", new_callable=AsyncMock):
                await manager._show_prompt_after_delay(prompt, 0)
                mock_display.assert_called_once_with(prompt)

    @pytest.mark.asyncio
    async def test_display_feedback_prompt(self, mock_event_bus, mock_feedback_api):
        """Test displaying feedback prompt emits event."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        prompt = FeedbackPrompt(
            id="display-prompt",
            agent_name="test_agent",
            event_type="test:event",
            prompt_type="quick_rating",
            message="Test message",
            context={"key": "value"},
            timestamp=time.time(),
            expires_at=time.time() + 100,
        )

        await manager._display_feedback_prompt(prompt)

        mock_event_bus.emit.assert_called_once()
        emitted_event = mock_event_bus.emit.call_args[0][0]
        assert emitted_event.type == "feedback:prompt"
        assert emitted_event.payload["prompt_id"] == "display-prompt"

    @pytest.mark.asyncio
    async def test_auto_dismiss_prompt_immediate(
        self, mock_event_bus, mock_feedback_api
    ):
        """Test auto-dismiss when already expired."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        manager.active_prompts["auto-dismiss"] = MagicMock()

        with patch.object(asyncio, "sleep", new_callable=AsyncMock) as mock_sleep:
            await manager._auto_dismiss_prompt("auto-dismiss", time.time() - 10)
            mock_sleep.assert_not_called()
            assert "auto-dismiss" not in manager.active_prompts

    @pytest.mark.asyncio
    async def test_auto_dismiss_prompt_with_wait(
        self, mock_event_bus, mock_feedback_api
    ):
        """Test auto-dismiss with remaining time."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        manager.active_prompts["auto-dismiss"] = MagicMock()
        expires_at = time.time() + 0.1  # Very short wait

        with patch.object(asyncio, "sleep", new_callable=AsyncMock) as mock_sleep:
            await manager._auto_dismiss_prompt("auto-dismiss", expires_at)
            mock_sleep.assert_called_once()
            assert "auto-dismiss" not in manager.active_prompts

    @pytest.mark.asyncio
    async def test_submit_prompt_feedback_not_found(
        self, mock_event_bus, mock_feedback_api
    ):
        """Test submitting feedback for nonexistent prompt."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        result = await manager.submit_prompt_feedback(
            prompt_id="nonexistent",
            feedback_type=MagicMock(),
            value=5,
        )

        assert result is False
        mock_feedback_api.submit_feedback.assert_not_called()

    @pytest.mark.asyncio
    async def test_submit_prompt_feedback_success(
        self, mock_event_bus, mock_feedback_api
    ):
        """Test successfully submitting feedback."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        prompt = FeedbackPrompt(
            id="submit-prompt",
            agent_name="test_agent",
            event_type="test:event",
            prompt_type="quick_rating",
            message="Test",
            context={"original": "context"},
            timestamp=time.time(),
            expires_at=time.time() + 100,
        )
        manager.active_prompts["submit-prompt"] = prompt

        feedback_type = MagicMock()
        result = await manager.submit_prompt_feedback(
            prompt_id="submit-prompt",
            feedback_type=feedback_type,
            value=5,
            comment="Great!",
        )

        assert result is True
        assert "submit-prompt" not in manager.active_prompts
        mock_feedback_api.submit_feedback.assert_called_once()

    def test_get_active_prompts_empty(self, mock_event_bus, mock_feedback_api):
        """Test getting active prompts when none exist."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        prompts = manager.get_active_prompts()
        assert prompts == []

    def test_get_active_prompts_with_prompts(self, mock_event_bus, mock_feedback_api):
        """Test getting active prompts."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        prompt = FeedbackPrompt(
            id="active-1",
            agent_name="test_agent",
            event_type="test:event",
            prompt_type="quick_rating",
            message="Test message",
            context={},
            timestamp=time.time(),
            expires_at=time.time() + 100,
        )
        manager.active_prompts["active-1"] = prompt

        prompts = manager.get_active_prompts()

        assert len(prompts) == 1
        assert prompts[0]["id"] == "active-1"
        assert prompts[0]["agent_name"] == "test_agent"
        assert prompts[0]["message"] == "Test message"
        assert prompts[0]["time_remaining"] > 0

    def test_get_active_prompts_excludes_expired(
        self, mock_event_bus, mock_feedback_api
    ):
        """Test getting active prompts excludes expired ones."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        expired = FeedbackPrompt(
            id="expired",
            agent_name="test",
            event_type="test",
            prompt_type="quick_rating",
            message="Expired",
            context={},
            timestamp=time.time() - 100,
            expires_at=time.time() - 50,
        )
        active = FeedbackPrompt(
            id="active",
            agent_name="test",
            event_type="test",
            prompt_type="quick_rating",
            message="Active",
            context={},
            timestamp=time.time(),
            expires_at=time.time() + 100,
        )
        manager.active_prompts["expired"] = expired
        manager.active_prompts["active"] = active

        prompts = manager.get_active_prompts()

        assert len(prompts) == 1
        assert prompts[0]["id"] == "active"

    @pytest.mark.asyncio
    async def test_dismiss_prompt_success(self, mock_event_bus, mock_feedback_api):
        """Test successfully dismissing a prompt."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        manager.active_prompts["dismiss-me"] = MagicMock()

        result = await manager.dismiss_prompt("dismiss-me")

        assert result is True
        assert "dismiss-me" not in manager.active_prompts

    @pytest.mark.asyncio
    async def test_dismiss_prompt_not_found(self, mock_event_bus, mock_feedback_api):
        """Test dismissing nonexistent prompt."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        result = await manager.dismiss_prompt("nonexistent")

        assert result is False

    def test_cleanup_expired_prompts_none(self, mock_event_bus, mock_feedback_api):
        """Test cleanup with no expired prompts."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        active = FeedbackPrompt(
            id="active",
            agent_name="test",
            event_type="test",
            prompt_type="quick_rating",
            message="Active",
            context={},
            timestamp=time.time(),
            expires_at=time.time() + 100,
        )
        manager.active_prompts["active"] = active

        count = manager.cleanup_expired_prompts()

        assert count == 0
        assert "active" in manager.active_prompts

    def test_cleanup_expired_prompts_some(self, mock_event_bus, mock_feedback_api):
        """Test cleanup removes expired prompts."""
        with patch.object(asyncio, "create_task"):
            manager = ProactiveFeedbackManager(mock_event_bus, mock_feedback_api)

        expired = FeedbackPrompt(
            id="expired",
            agent_name="test",
            event_type="test",
            prompt_type="quick_rating",
            message="Expired",
            context={},
            timestamp=time.time() - 100,
            expires_at=time.time() - 50,
        )
        active = FeedbackPrompt(
            id="active",
            agent_name="test",
            event_type="test",
            prompt_type="quick_rating",
            message="Active",
            context={},
            timestamp=time.time(),
            expires_at=time.time() + 100,
        )
        manager.active_prompts["expired"] = expired
        manager.active_prompts["active"] = active

        count = manager.cleanup_expired_prompts()

        assert count == 1
        assert "expired" not in manager.active_prompts
        assert "active" in manager.active_prompts
