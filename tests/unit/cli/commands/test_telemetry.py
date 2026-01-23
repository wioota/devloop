"""Tests for telemetry CLI commands."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from devloop.cli.commands.telemetry import export, recent, stats


class TestStats:
    """Tests for stats command."""

    @pytest.fixture
    def mock_telemetry(self):
        """Create mock telemetry logger."""
        mock_telem = Mock()
        mock_telem.get_stats.return_value = {
            "total_events": 100,
            "total_findings": 50,
            "ci_roundtrips_prevented": 5,
            "total_time_saved_ms": 300000,  # 300 seconds
            "events_by_type": {},
            "agents_executed": {},
        }
        return mock_telem

    def test_stats_default_log_file(self, mock_telemetry):
        """Test stats command with default log file."""
        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ) as mock_get_telemetry:
            with patch("devloop.cli.commands.telemetry.console"):
                stats(log_file=None)

                # Should call get_telemetry_logger without args
                mock_get_telemetry.assert_called_once_with()
                mock_telemetry.get_stats.assert_called_once()

    def test_stats_custom_log_file(self, mock_telemetry):
        """Test stats command with custom log file."""
        custom_file = Path("/custom/path/events.jsonl")

        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ) as mock_get_telemetry:
            with patch("devloop.cli.commands.telemetry.console"):
                stats(log_file=custom_file)

                # Should call get_telemetry_logger with custom file
                mock_get_telemetry.assert_called_once_with(custom_file)

    def test_stats_displays_summary_table(self, mock_telemetry):
        """Test stats displays summary table with metrics."""
        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ):
            with patch("devloop.cli.commands.telemetry.console") as mock_console:
                stats(log_file=None)

                # Should print table
                mock_console.print.assert_called()

    def test_stats_with_events_by_type(self, mock_telemetry):
        """Test stats displays events by type."""
        mock_telemetry.get_stats.return_value = {
            "total_events": 100,
            "total_findings": 50,
            "ci_roundtrips_prevented": 5,
            "total_time_saved_ms": 300000,
            "events_by_type": {
                "agent:executed": 75,
                "finding:created": 50,
            },
            "agents_executed": {},
        }

        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ):
            with patch("devloop.cli.commands.telemetry.console") as mock_console:
                stats(log_file=None)

                # Should print events table
                calls = [str(call) for call in mock_console.print.call_args_list]
                assert any("Events by Type" in call for call in calls)

    def test_stats_with_agents_executed(self, mock_telemetry):
        """Test stats displays agent execution stats."""
        mock_telemetry.get_stats.return_value = {
            "total_events": 100,
            "total_findings": 50,
            "ci_roundtrips_prevented": 5,
            "total_time_saved_ms": 300000,
            "events_by_type": {},
            "agents_executed": {
                "linter": {
                    "count": 25,
                    "total_duration_ms": 5000,
                },
                "formatter": {
                    "count": 30,
                    "total_duration_ms": 3000,
                },
            },
        }

        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ):
            with patch("devloop.cli.commands.telemetry.console") as mock_console:
                stats(log_file=None)

                # Should print agent stats table
                calls = [str(call) for call in mock_console.print.call_args_list]
                assert any("Agent Execution Stats" in call for call in calls)

    def test_stats_handles_zero_count(self, mock_telemetry):
        """Test stats handles agents with zero count."""
        mock_telemetry.get_stats.return_value = {
            "total_events": 0,
            "total_findings": 0,
            "ci_roundtrips_prevented": 0,
            "total_time_saved_ms": 0,
            "events_by_type": {},
            "agents_executed": {
                "linter": {
                    "count": 0,
                    "total_duration_ms": 0,
                }
            },
        }

        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ):
            with patch("devloop.cli.commands.telemetry.console"):
                stats(log_file=None)

                # Should complete without error


class TestRecent:
    """Tests for recent command."""

    @pytest.fixture
    def mock_telemetry(self):
        """Create mock telemetry logger."""
        mock_telem = Mock()
        mock_telem.get_events.return_value = []
        return mock_telem

    def test_recent_default_count(self, mock_telemetry):
        """Test recent command with default count."""
        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ):
            with patch("devloop.cli.commands.telemetry.console"):
                recent(count=10, log_file=None)

                # Should call get_events with default limit
                mock_telemetry.get_events.assert_called_once_with(limit=10)

    def test_recent_custom_count(self, mock_telemetry):
        """Test recent command with custom count."""
        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ):
            with patch("devloop.cli.commands.telemetry.console"):
                recent(count=25, log_file=None)

                # Should call get_events with custom limit
                mock_telemetry.get_events.assert_called_once_with(limit=25)

    def test_recent_no_events(self, mock_telemetry):
        """Test recent command when no events exist."""
        mock_telemetry.get_events.return_value = []

        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ):
            with patch("devloop.cli.commands.telemetry.console") as mock_console:
                recent(count=10, log_file=None)

                # Should print no events message
                calls = [str(call) for call in mock_console.print.call_args_list]
                assert any("No events recorded yet" in call for call in calls)

    def test_recent_with_events(self, mock_telemetry):
        """Test recent command with events."""
        mock_telemetry.get_events.return_value = [
            {
                "timestamp": "2024-01-01T12:00:00",
                "event_type": "agent:executed",
                "agent": "linter",
                "duration_ms": 1500,
                "findings": 5,
                "success": True,
            },
            {
                "timestamp": "2024-01-01T12:01:00",
                "event_type": "finding:created",
                "agent": "formatter",
                "success": False,
            },
        ]

        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ):
            with patch("devloop.cli.commands.telemetry.console") as mock_console:
                recent(count=10, log_file=None)

                # Should print table with events
                mock_console.print.assert_called()

    def test_recent_custom_log_file(self, mock_telemetry):
        """Test recent command with custom log file."""
        custom_file = Path("/custom/events.jsonl")

        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ) as mock_get_telemetry:
            with patch("devloop.cli.commands.telemetry.console"):
                recent(count=10, log_file=custom_file)

                # Should call get_telemetry_logger with custom file
                mock_get_telemetry.assert_called_once_with(custom_file)

    def test_recent_event_details_formatting(self, mock_telemetry):
        """Test recent formats event details correctly."""
        mock_telemetry.get_events.return_value = [
            {
                "timestamp": "2024-01-01T12:00:00",
                "event_type": "test",
            }
        ]

        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ):
            with patch("devloop.cli.commands.telemetry.console"):
                recent(count=10, log_file=None)

                # Should complete without error


class TestExport:
    """Tests for export command."""

    @pytest.fixture
    def mock_telemetry(self):
        """Create mock telemetry logger."""
        mock_telem = Mock()
        mock_telem.get_events.return_value = [
            {"event": 1, "timestamp": "2024-01-01"},
            {"event": 2, "timestamp": "2024-01-02"},
        ]
        return mock_telem

    def test_export_to_json(self, mock_telemetry, tmp_path):
        """Test export to JSON format."""
        output_file = tmp_path / "export.json"

        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ):
            with patch("devloop.cli.commands.telemetry.console") as mock_console:
                export(output_file=output_file, log_file=None)

                # Should create JSON file
                assert output_file.exists()

                # Should print success message
                calls = [str(call) for call in mock_console.print.call_args_list]
                assert any("Exported" in call and "events" in call for call in calls)

    def test_export_to_jsonl(self, mock_telemetry, tmp_path):
        """Test export to JSONL format."""
        output_file = tmp_path / "export.jsonl"

        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ):
            with patch("devloop.cli.commands.telemetry.console") as mock_console:
                export(output_file=output_file, log_file=None)

                # Should create JSONL file
                assert output_file.exists()

                # Should print success message
                calls = [str(call) for call in mock_console.print.call_args_list]
                assert any("Exported" in call for call in calls)

    def test_export_custom_log_file(self, mock_telemetry, tmp_path):
        """Test export with custom log file."""
        output_file = tmp_path / "export.json"
        custom_log = Path("/custom/events.jsonl")

        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ) as mock_get_telemetry:
            with patch("devloop.cli.commands.telemetry.console"):
                export(output_file=output_file, log_file=custom_log)

                # Should call get_telemetry_logger with custom file
                mock_get_telemetry.assert_called_once_with(custom_log)

    def test_export_creates_parent_directory(self, mock_telemetry, tmp_path):
        """Test export creates parent directory if needed."""
        output_file = tmp_path / "subdir" / "nested" / "export.json"

        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ):
            with patch("devloop.cli.commands.telemetry.console"):
                export(output_file=output_file, log_file=None)

                # Should create parent directories
                assert output_file.parent.exists()
                assert output_file.exists()

    def test_export_handles_error(self, mock_telemetry, tmp_path):
        """Test export handles write errors."""
        import typer as typer_module

        # Create a file that can't be written to (simulate permission error)
        output_file = tmp_path / "readonly.json"
        output_file.touch()
        output_file.chmod(0o444)  # Read-only

        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ):
            with patch("devloop.cli.commands.telemetry.console") as mock_console:
                with pytest.raises(typer_module.Exit) as exc_info:
                    export(output_file=output_file, log_file=None)

                # Should print error message
                calls = [str(call) for call in mock_console.print.call_args_list]
                assert any("Failed to export" in call for call in calls)

                # Should exit with code 1
                assert exc_info.value.exit_code == 1

    def test_export_default_log_file(self, mock_telemetry, tmp_path):
        """Test export with default log file."""
        output_file = tmp_path / "export.json"

        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ) as mock_get_telemetry:
            with patch("devloop.cli.commands.telemetry.console"):
                export(output_file=output_file, log_file=None)

                # Should call get_telemetry_logger without args
                mock_get_telemetry.assert_called_once_with()

    def test_export_gets_all_events(self, mock_telemetry, tmp_path):
        """Test export retrieves all events (up to 10000)."""
        output_file = tmp_path / "export.json"

        with patch(
            "devloop.cli.commands.telemetry.get_telemetry_logger",
            return_value=mock_telemetry,
        ):
            with patch("devloop.cli.commands.telemetry.console"):
                export(output_file=output_file, log_file=None)

                # Should call get_events with limit 10000
                mock_telemetry.get_events.assert_called_once_with(limit=10000)
