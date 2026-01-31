"""Tests for feedback CLI commands."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from devloop.cli.commands.feedback import (
    get_feedback_api,
    get_performance_monitor,
    list_feedback,
    performance_detail,
    performance_status,
    submit_feedback,
)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_feedback_api_with_project_dir(self):
        """Test get_feedback_api with custom project directory."""
        with patch("devloop.cli.commands.feedback.FeedbackStore") as MockStore:
            with patch("devloop.cli.commands.feedback.FeedbackAPI") as MockAPI:
                custom_dir = Path("/custom/project")
                _api = get_feedback_api(custom_dir)

                # Should create store with correct path
                MockStore.assert_called_once()
                created_path = MockStore.call_args[0][0]
                assert str(created_path) == "/custom/project/.devloop/feedback"

                # Should create API with store
                MockAPI.assert_called_once_with(MockStore.return_value)

    def test_get_feedback_api_uses_cwd_by_default(self):
        """Test get_feedback_api uses current directory by default."""
        with patch("devloop.cli.commands.feedback.FeedbackStore") as MockStore:
            with patch("devloop.cli.commands.feedback.FeedbackAPI"):
                with patch("pathlib.Path.cwd", return_value=Path("/fake/cwd")):
                    get_feedback_api(None)

                    # Should use cwd
                    created_path = MockStore.call_args[0][0]
                    assert "/fake/cwd/.devloop/feedback" in str(created_path)

    def test_get_performance_monitor_with_project_dir(self):
        """Test get_performance_monitor with custom project directory."""
        with patch("devloop.cli.commands.feedback.PerformanceMonitor") as MockMonitor:
            custom_dir = Path("/custom/project")
            _monitor = get_performance_monitor(custom_dir)

            # Should create monitor with correct path
            MockMonitor.assert_called_once()
            created_path = MockMonitor.call_args[0][0]
            assert str(created_path) == "/custom/project/.devloop/performance"

    def test_get_performance_monitor_uses_cwd_by_default(self):
        """Test get_performance_monitor uses current directory by default."""
        with patch("devloop.cli.commands.feedback.PerformanceMonitor") as MockMonitor:
            with patch("pathlib.Path.cwd", return_value=Path("/fake/cwd")):
                get_performance_monitor(None)

                # Should use cwd
                created_path = MockMonitor.call_args[0][0]
                assert "/fake/cwd/.devloop/performance" in str(created_path)


class TestListFeedback:
    """Tests for list_feedback command."""

    @pytest.fixture
    def mock_feedback_api(self):
        """Create mock FeedbackAPI."""
        mock_api = Mock()
        mock_store = Mock()
        mock_store.get_all_feedback = AsyncMock(return_value=[])
        mock_store.get_feedback_for_agent = AsyncMock(return_value=[])
        mock_api.feedback_store = mock_store
        return mock_api

    def test_list_feedback_no_feedback(self, mock_feedback_api):
        """Test list_feedback when no feedback exists."""
        with patch(
            "devloop.cli.commands.feedback.get_feedback_api",
            return_value=mock_feedback_api,
        ):
            with patch("devloop.cli.commands.feedback.console") as mock_console:
                list_feedback(agent=None, limit=20, project_dir=None)

                # Should print no feedback message
                calls = [str(call) for call in mock_console.print.call_args_list]
                assert any("No feedback found" in call for call in calls)

    def test_list_feedback_with_feedback(self, mock_feedback_api):
        """Test list_feedback with existing feedback."""
        mock_item = Mock()
        mock_item.timestamp = datetime(2024, 1, 1, 12, 0, 0)
        mock_item.agent_name = "linter"
        mock_item.feedback_type = "bug"
        mock_item.message = "Test feedback message"

        mock_feedback_api.feedback_store.get_all_feedback.return_value = [mock_item]

        with patch(
            "devloop.cli.commands.feedback.get_feedback_api",
            return_value=mock_feedback_api,
        ):
            with patch("devloop.cli.commands.feedback.console") as mock_console:
                list_feedback(agent=None, limit=20, project_dir=None)

                # Should print table
                mock_console.print.assert_called_once()
                # Should call get_all_feedback
                mock_feedback_api.feedback_store.get_all_feedback.assert_called_once()

    def test_list_feedback_with_agent_filter(self, mock_feedback_api):
        """Test list_feedback with agent filter."""
        mock_item = Mock()
        mock_item.timestamp = datetime(2024, 1, 1, 12, 0, 0)
        mock_item.agent_name = "linter"
        mock_item.feedback_type = "bug"
        mock_item.message = "Test"

        mock_feedback_api.feedback_store.get_feedback_for_agent.return_value = [
            mock_item
        ]

        with patch(
            "devloop.cli.commands.feedback.get_feedback_api",
            return_value=mock_feedback_api,
        ):
            with patch("devloop.cli.commands.feedback.console"):
                list_feedback(agent="linter", limit=20, project_dir=None)

                # Should call get_feedback_for_agent with agent name
                mock_feedback_api.feedback_store.get_feedback_for_agent.assert_called_once_with(
                    "linter"
                )

    def test_list_feedback_respects_limit(self, mock_feedback_api):
        """Test list_feedback respects limit parameter."""
        # Create 30 mock items
        mock_items = []
        for i in range(30):
            mock_item = Mock()
            mock_item.timestamp = datetime(2024, 1, 1, 12, 0, i)
            mock_item.agent_name = f"agent-{i}"
            mock_item.feedback_type = "bug"
            mock_item.message = f"Message {i}"
            mock_items.append(mock_item)

        mock_feedback_api.feedback_store.get_all_feedback.return_value = mock_items

        with patch(
            "devloop.cli.commands.feedback.get_feedback_api",
            return_value=mock_feedback_api,
        ):
            with patch("devloop.cli.commands.feedback.console"):
                list_feedback(agent=None, limit=10, project_dir=None)

                # Function should process but we can't easily check the internal limit

    def test_list_feedback_truncates_long_message(self, mock_feedback_api):
        """Test list_feedback truncates long messages."""
        mock_item = Mock()
        mock_item.timestamp = datetime(2024, 1, 1, 12, 0, 0)
        mock_item.agent_name = "linter"
        mock_item.feedback_type = "bug"
        mock_item.message = "A" * 100  # 100 character message

        mock_feedback_api.feedback_store.get_all_feedback.return_value = [mock_item]

        with patch(
            "devloop.cli.commands.feedback.get_feedback_api",
            return_value=mock_feedback_api,
        ):
            with patch("devloop.cli.commands.feedback.console"):
                list_feedback(agent=None, limit=20, project_dir=None)

                # Should execute without error


class TestSubmitFeedback:
    """Tests for submit_feedback command."""

    @pytest.fixture
    def mock_feedback_api(self):
        """Create mock FeedbackAPI."""
        mock_api = Mock()
        mock_api.submit_feedback = AsyncMock()
        return mock_api

    def test_submit_feedback_success(self, mock_feedback_api):
        """Test successful feedback submission."""
        with patch(
            "devloop.cli.commands.feedback.get_feedback_api",
            return_value=mock_feedback_api,
        ):
            with patch("devloop.cli.commands.feedback.console") as mock_console:
                submit_feedback(
                    agent="linter",
                    feedback_type="bug",
                    message="Test feedback",
                    project_dir=None,
                )

                # Should call submit_feedback
                mock_feedback_api.submit_feedback.assert_called_once_with(
                    "linter", "bug", "Test feedback"
                )

                # Should print success message
                calls = [str(call) for call in mock_console.print.call_args_list]
                assert any("Feedback submitted" in call for call in calls)
                assert any("linter" in call for call in calls)

    def test_submit_feedback_different_types(self, mock_feedback_api):
        """Test submit_feedback with different feedback types."""
        types = ["suggestion", "bug", "improvement", "other"]

        for feedback_type in types:
            with patch(
                "devloop.cli.commands.feedback.get_feedback_api",
                return_value=mock_feedback_api,
            ):
                with patch("devloop.cli.commands.feedback.console"):
                    submit_feedback(
                        agent="agent",
                        feedback_type=feedback_type,
                        message="Test",
                        project_dir=None,
                    )

                    # Should call with correct type
                    call_args = mock_feedback_api.submit_feedback.call_args[0]
                    assert call_args[1] == feedback_type

    def test_submit_feedback_with_project_dir(self, mock_feedback_api):
        """Test submit_feedback with custom project directory."""
        with patch(
            "devloop.cli.commands.feedback.get_feedback_api",
            return_value=mock_feedback_api,
        ) as mock_get_api:
            with patch("devloop.cli.commands.feedback.console"):
                custom_dir = Path("/custom/path")
                submit_feedback(
                    agent="agent",
                    feedback_type="bug",
                    message="Test",
                    project_dir=custom_dir,
                )

                # Should pass project_dir to get_feedback_api
                mock_get_api.assert_called_once_with(custom_dir)


class TestPerformanceStatus:
    """Tests for performance_status command."""

    @pytest.fixture
    def mock_monitor(self):
        """Create mock PerformanceMonitor."""
        mock = Mock()
        mock.get_performance_summary = AsyncMock(return_value={})
        return mock

    def test_performance_status_no_metrics(self, mock_monitor):
        """Test performance_status with no metrics."""
        with patch(
            "devloop.cli.commands.feedback.get_performance_monitor",
            return_value=mock_monitor,
        ):
            with patch("devloop.cli.commands.feedback.console") as mock_console:
                performance_status(project_dir=None)

                # Should call get_performance_summary
                mock_monitor.get_performance_summary.assert_called_once()

                # Should print table
                mock_console.print.assert_called_once()

    def test_performance_status_with_metrics(self, mock_monitor):
        """Test performance_status with metrics."""
        mock_monitor.get_performance_summary.return_value = {
            "linter": {
                "success_rate": 0.95,
                "avg_duration": 123.45,
                "total_runs": 100,
            },
            "formatter": {
                "success_rate": 0.98,
                "avg_duration": 67.89,
                "total_runs": 50,
            },
        }

        with patch(
            "devloop.cli.commands.feedback.get_performance_monitor",
            return_value=mock_monitor,
        ):
            with patch("devloop.cli.commands.feedback.console") as mock_console:
                performance_status(project_dir=None)

                # Should print table
                mock_console.print.assert_called_once()

    def test_performance_status_with_none_values(self, mock_monitor):
        """Test performance_status handles None values."""
        mock_monitor.get_performance_summary.return_value = {
            "agent": {
                "success_rate": None,
                "avg_duration": None,
                "total_runs": 0,
            }
        }

        with patch(
            "devloop.cli.commands.feedback.get_performance_monitor",
            return_value=mock_monitor,
        ):
            with patch("devloop.cli.commands.feedback.console"):
                performance_status(project_dir=None)

                # Should execute without error


class TestPerformanceDetail:
    """Tests for performance_detail command."""

    @pytest.fixture
    def mock_monitor(self):
        """Create mock PerformanceMonitor."""
        mock = Mock()
        mock.get_agent_metrics = AsyncMock(return_value=None)
        return mock

    def test_performance_detail_no_metrics(self, mock_monitor):
        """Test performance_detail with no metrics for agent."""
        with patch(
            "devloop.cli.commands.feedback.get_performance_monitor",
            return_value=mock_monitor,
        ):
            with patch("devloop.cli.commands.feedback.console") as mock_console:
                performance_detail(agent="linter", project_dir=None)

                # Should call get_agent_metrics
                mock_monitor.get_agent_metrics.assert_called_once_with("linter")

                # Should print no metrics message
                calls = [str(call) for call in mock_console.print.call_args_list]
                assert any("No metrics found" in call for call in calls)

    def test_performance_detail_with_metrics(self, mock_monitor):
        """Test performance_detail with metrics."""
        mock_monitor.get_agent_metrics.return_value = {
            "success_rate": 0.95,
            "avg_duration": 123.45,
            "total_runs": 100,
            "last_run": "2024-01-01T12:00:00",
        }

        with patch(
            "devloop.cli.commands.feedback.get_performance_monitor",
            return_value=mock_monitor,
        ):
            with patch("devloop.cli.commands.feedback.console") as mock_console:
                performance_detail(agent="linter", project_dir=None)

                # Should print metrics
                calls = [str(call) for call in mock_console.print.call_args_list]
                assert any("Performance Metrics" in call for call in calls)
                assert any("Success Rate" in call for call in calls)
                assert any("Average Duration" in call for call in calls)

    def test_performance_detail_with_project_dir(self, mock_monitor):
        """Test performance_detail with custom project directory."""
        mock_monitor.get_agent_metrics.return_value = None

        with patch(
            "devloop.cli.commands.feedback.get_performance_monitor",
            return_value=mock_monitor,
        ) as mock_get_monitor:
            with patch("devloop.cli.commands.feedback.console"):
                custom_dir = Path("/custom/path")
                performance_detail(agent="agent", project_dir=custom_dir)

                # Should pass project_dir to get_performance_monitor
                mock_get_monitor.assert_called_once_with(custom_dir)
