"""Tests for contextual_feedback module.

Tests contextual feedback inference from developer behavior patterns.
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devloop.core.contextual_feedback import (
    ContextualFeedbackEngine,
    DeveloperAction,
)
from devloop.core.event import Event


class TestDeveloperAction:
    """Tests for DeveloperAction dataclass."""

    def test_init_with_all_fields(self):
        """Test DeveloperAction initialization with all fields."""
        action = DeveloperAction(
            action_type="file_save",
            file_path="/test/file.py",
            timestamp=1000.0,
            context={"key": "value"},
        )

        assert action.action_type == "file_save"
        assert action.file_path == "/test/file.py"
        assert action.timestamp == 1000.0
        assert action.context == {"key": "value"}

    def test_init_with_none_context(self):
        """Test DeveloperAction with None context uses empty dict."""
        action = DeveloperAction(
            action_type="file_edit",
            file_path="/test/file.py",
            timestamp=1000.0,
            context=None,
        )

        assert action.context == {}

    def test_init_default_context(self):
        """Test DeveloperAction default context."""
        action = DeveloperAction(
            action_type="cursor_move",
            file_path=None,
            timestamp=1000.0,
        )

        assert action.context == {}


class TestContextualFeedbackEngine:
    """Tests for ContextualFeedbackEngine."""

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

    @pytest.fixture
    def tmp_project(self, tmp_path):
        """Create temporary project directory."""
        return tmp_path / "project"

    def test_init(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test ContextualFeedbackEngine initialization."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        assert engine.event_bus is mock_event_bus
        assert engine.feedback_api is mock_feedback_api
        assert engine.project_dir == tmp_project
        assert engine.recent_actions == []
        assert engine.recent_agent_actions == []
        assert engine.action_window == 300
        assert engine.agent_action_window == 600

    def test_init_sets_up_event_listeners(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test that init sets up event listeners."""
        with patch.object(asyncio, "create_task") as mock_create_task:
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        # Should create tasks for event subscriptions
        assert mock_create_task.call_count == 2

    @pytest.mark.asyncio
    async def test_on_agent_completed_stores_action(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test agent completion stores action."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        event = Event(
            type="agent:test:completed",
            payload={"agent_name": "test_agent", "success": True, "duration": 1.5},
            source="test",
        )

        with patch.object(engine, "_analyze_immediate_feedback", new_callable=AsyncMock):
            await engine._on_agent_completed(event)

        assert len(engine.recent_agent_actions) == 1
        assert engine.recent_agent_actions[0]["agent_name"] == "test_agent"
        assert engine.recent_agent_actions[0]["success"] is True

    @pytest.mark.asyncio
    async def test_on_agent_completed_cleans_old_actions(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test agent completion cleans old actions."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        # Add old action
        engine.recent_agent_actions.append({
            "agent_name": "old_agent",
            "timestamp": time.time() - 1000,  # Very old
        })

        event = Event(
            type="agent:test:completed",
            payload={"agent_name": "new_agent", "success": True},
            source="test",
        )

        with patch.object(engine, "_analyze_immediate_feedback", new_callable=AsyncMock):
            await engine._on_agent_completed(event)

        # Old action should be removed
        assert len(engine.recent_agent_actions) == 1
        assert engine.recent_agent_actions[0]["agent_name"] == "new_agent"

    @pytest.mark.asyncio
    async def test_on_file_event_no_path(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test file event with no path returns early."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        event = Event(
            type="file:modified",
            payload={},  # No path
            source="test",
        )

        with patch.object(engine, "_analyze_file_patterns", new_callable=AsyncMock) as mock_analyze:
            await engine._on_file_event(event)
            mock_analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_file_event_stores_action(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test file event stores developer action."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        event = Event(
            type="file:modified",
            payload={"path": "/test/file.py"},
            source="test",
        )

        with patch.object(engine, "_analyze_file_patterns", new_callable=AsyncMock):
            await engine._on_file_event(event)

        assert len(engine.recent_actions) == 1
        assert engine.recent_actions[0].action_type == "file_modified"
        assert engine.recent_actions[0].file_path == "/test/file.py"

    @pytest.mark.asyncio
    async def test_on_file_event_tracks_interactions(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test file event tracks interaction times."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        event = Event(
            type="file:modified",
            payload={"path": "/test/file.py"},
            source="test",
        )

        with patch.object(engine, "_analyze_file_patterns", new_callable=AsyncMock):
            await engine._on_file_event(event)

        assert "/test/file.py" in engine.file_interaction_times
        assert len(engine.file_interaction_times["/test/file.py"]) == 1

    @pytest.mark.asyncio
    async def test_on_file_event_updates_last_modified(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test file modified event updates last modified time."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        event = Event(
            type="file:modified",
            payload={"path": "/test/file.py"},
            source="test",
        )

        with patch.object(engine, "_analyze_file_patterns", new_callable=AsyncMock):
            await engine._on_file_event(event)

        assert "/test/file.py" in engine.file_last_modified

    @pytest.mark.asyncio
    async def test_on_file_event_cleans_old_interactions(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test file event cleans old interactions."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        # Add old interaction
        engine.file_interaction_times["/test/file.py"] = [time.time() - 100000]  # Very old

        event = Event(
            type="file:modified",
            payload={"path": "/test/file.py"},
            source="test",
        )

        with patch.object(engine, "_analyze_file_patterns", new_callable=AsyncMock):
            await engine._on_file_event(event)

        # Old interaction should be removed, only new one remains
        assert len(engine.file_interaction_times["/test/file.py"]) == 1

    @pytest.mark.asyncio
    async def test_analyze_immediate_feedback_no_actions(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test immediate feedback analysis with no recent actions."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        agent_action = {
            "agent_name": "test_agent",
            "timestamp": time.time(),
        }

        with patch.object(engine, "_infer_feedback_from_file_changes", new_callable=AsyncMock) as mock_infer:
            await engine._analyze_immediate_feedback(agent_action)
            mock_infer.assert_not_called()

    @pytest.mark.asyncio
    async def test_analyze_immediate_feedback_with_file_actions(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test immediate feedback analysis with file actions."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        agent_time = time.time()
        agent_action = {
            "agent_name": "test_agent",
            "timestamp": agent_time,
        }

        # Add a recent file action within 30 seconds
        engine.recent_actions.append(DeveloperAction(
            action_type="file_modified",
            file_path="/test/file.py",
            timestamp=agent_time + 5,
        ))

        with patch.object(engine, "_infer_feedback_from_file_changes", new_callable=AsyncMock) as mock_infer:
            await engine._analyze_immediate_feedback(agent_action)
            mock_infer.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_file_patterns_no_interactions(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test file pattern analysis with no prior interactions."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        action = DeveloperAction(
            action_type="file_modified",
            file_path="/test/new_file.py",
            timestamp=time.time(),
        )

        # Should return without error
        await engine._analyze_file_patterns("/nonexistent/file.py", action)

    @pytest.mark.asyncio
    async def test_analyze_file_patterns_high_frequency(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test file pattern analysis detects high frequency editing."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        # Add many interactions in short time span
        now = time.time()
        engine.file_interaction_times["/test/file.py"] = [
            now - 10,
            now - 5,
            now - 2,
        ]

        action = DeveloperAction(
            action_type="file_modified",
            file_path="/test/file.py",
            timestamp=now,
        )

        with patch.object(engine, "_infer_feedback_from_interaction_pattern", new_callable=AsyncMock) as mock_infer:
            with patch.object(engine, "_infer_feedback_from_quick_modification", new_callable=AsyncMock):
                await engine._analyze_file_patterns("/test/file.py", action)
                mock_infer.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_file_patterns_quick_modification(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test file pattern analysis detects quick modification."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        now = time.time()
        engine.file_last_modified["/test/file.py"] = now - 30  # Modified 30 seconds ago
        engine.file_interaction_times["/test/file.py"] = [now]

        action = DeveloperAction(
            action_type="file_modified",
            file_path="/test/file.py",
            timestamp=now,
        )

        with patch.object(engine, "_infer_feedback_from_quick_modification", new_callable=AsyncMock) as mock_infer:
            await engine._analyze_file_patterns("/test/file.py", action)
            mock_infer.assert_called_once()

    @pytest.mark.asyncio
    async def test_infer_feedback_from_file_changes(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test inferring feedback from file changes."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        agent_action = {
            "agent_name": "test_agent",
            "timestamp": time.time(),
        }

        file_actions = [
            DeveloperAction(
                action_type="file_modified",
                file_path="/test/file.py",
                timestamp=time.time(),
            ),
        ]

        await engine._infer_feedback_from_file_changes(agent_action, file_actions)

        mock_feedback_api.submit_feedback.assert_called_once()
        call_kwargs = mock_feedback_api.submit_feedback.call_args[1]
        assert call_kwargs["agent_name"] == "test_agent"
        assert call_kwargs["value"] == 3  # Neutral rating

    @pytest.mark.asyncio
    async def test_infer_feedback_from_file_changes_no_modified(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test no feedback when no modified files."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        agent_action = {"agent_name": "test_agent", "timestamp": time.time()}

        file_actions = [
            DeveloperAction(
                action_type="file_created",  # Not modified
                file_path="/test/file.py",
                timestamp=time.time(),
            ),
        ]

        await engine._infer_feedback_from_file_changes(agent_action, file_actions)

        mock_feedback_api.submit_feedback.assert_not_called()

    @pytest.mark.asyncio
    async def test_infer_feedback_from_interaction_pattern_no_agents(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test no feedback when no recent agents."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        await engine._infer_feedback_from_interaction_pattern("/test/file.py", 0.02, "high_frequency")

        mock_feedback_api.submit_feedback.assert_not_called()

    @pytest.mark.asyncio
    async def test_infer_feedback_from_interaction_pattern_high_frequency(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test feedback for very high frequency interaction."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        engine.recent_agent_actions.append({
            "agent_name": "test_agent",
            "timestamp": time.time(),
        })

        await engine._infer_feedback_from_interaction_pattern("/test/file.py", 0.03, "high_frequency")

        mock_feedback_api.submit_feedback.assert_called_once()
        call_kwargs = mock_feedback_api.submit_feedback.call_args[1]
        assert call_kwargs["value"] == 2  # Low rating for very high frequency

    @pytest.mark.asyncio
    async def test_infer_feedback_from_interaction_pattern_moderate(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test feedback for moderate frequency interaction."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        engine.recent_agent_actions.append({
            "agent_name": "test_agent",
            "timestamp": time.time(),
        })

        await engine._infer_feedback_from_interaction_pattern("/test/file.py", 0.015, "moderate_frequency")

        mock_feedback_api.submit_feedback.assert_called_once()
        call_kwargs = mock_feedback_api.submit_feedback.call_args[1]
        assert call_kwargs["value"] == 3  # Neutral for moderate frequency

    @pytest.mark.asyncio
    async def test_infer_feedback_from_interaction_pattern_normal(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test no feedback for normal frequency interaction."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        engine.recent_agent_actions.append({
            "agent_name": "test_agent",
            "timestamp": time.time(),
        })

        await engine._infer_feedback_from_interaction_pattern("/test/file.py", 0.005, "normal")

        mock_feedback_api.submit_feedback.assert_not_called()

    @pytest.mark.asyncio
    async def test_infer_feedback_from_quick_modification_no_agent(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test no feedback when no recent agent."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        action = DeveloperAction(
            action_type="file_modified",
            file_path="/test/file.py",
            timestamp=time.time(),
        )

        await engine._infer_feedback_from_quick_modification("/test/file.py", action)

        mock_feedback_api.submit_feedback.assert_not_called()

    @pytest.mark.asyncio
    async def test_infer_feedback_from_quick_modification_with_agent(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test feedback for quick modification with recent agent."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        engine.recent_agent_actions.append({
            "agent_name": "test_agent",
            "timestamp": time.time() - 60,  # 1 minute ago
        })

        action = DeveloperAction(
            action_type="file_modified",
            file_path="/test/file.py",
            timestamp=time.time(),
        )

        await engine._infer_feedback_from_quick_modification("/test/file.py", action)

        mock_feedback_api.submit_feedback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_contextual_insights_empty(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test getting contextual insights with no data."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        insights = await engine.get_contextual_insights("test_agent")

        assert insights["agent_name"] == "test_agent"
        assert insights["agent_actions_count"] == 0
        assert insights["correlated_developer_actions"] == 0

    @pytest.mark.asyncio
    async def test_get_contextual_insights_with_data(self, mock_event_bus, mock_feedback_api, tmp_project):
        """Test getting contextual insights with data."""
        with patch.object(asyncio, "create_task"):
            engine = ContextualFeedbackEngine(mock_event_bus, mock_feedback_api, tmp_project)

        now = time.time()
        engine.recent_agent_actions.append({
            "agent_name": "test_agent",
            "timestamp": now - 100,
        })
        engine.recent_actions.append(DeveloperAction(
            action_type="file_modified",
            file_path="/test/file.py",
            timestamp=now - 50,  # Within 5 minutes after agent action
        ))

        insights = await engine.get_contextual_insights("test_agent")

        assert insights["agent_name"] == "test_agent"
        assert insights["agent_actions_count"] == 1
        assert insights["correlated_developer_actions"] == 1
        assert "file_changes" in insights["inference_types"]
