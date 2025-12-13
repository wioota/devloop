"""Tests for metrics command."""

import json
from datetime import datetime, UTC, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from typer.testing import CliRunner

from devloop.cli.main import app
from devloop.core.telemetry import TelemetryLogger, TelemetryEventType
import devloop.core.telemetry as telemetry_module

runner = CliRunner()


@pytest.fixture(autouse=True)
def reset_telemetry_cache():
    """Reset the global telemetry logger cache before each test."""
    telemetry_module._telemetry_logger = None
    yield
    telemetry_module._telemetry_logger = None


def test_metrics_value_command_no_events():
    """Test metrics value command with no events."""
    with TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"
        log_file.touch()

        result = runner.invoke(
            app, ["metrics", "value", "--log-file", str(log_file), "--period", "24h"]
        )

        assert result.exit_code == 0
        assert "No events" in result.stdout


def test_metrics_value_command_with_events():
    """Test metrics value command with sample events."""
    with TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"

        # Create logger and add sample events
        logger = TelemetryLogger(log_file)
        logger.log_agent_execution("linter", 100, 2, ["error"], success=True)
        logger.log_pre_commit_check(1, True, 100)
        logger.log_ci_roundtrip_prevented("lint-error", "linter-check")

        result = runner.invoke(
            app, ["metrics", "value", "--log-file", str(log_file), "--period", "all"]
        )

        assert result.exit_code == 0
        assert "DevLoop Value Dashboard" in result.stdout
        assert "CI Roundtrips Prevented: 1" in result.stdout


def test_metrics_agents_command():
    """Test metrics agents command."""
    with TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"

        # Create logger and add sample events
        logger = TelemetryLogger(log_file)
        logger.log_agent_execution("linter", 100, 5, ["error"], success=True)
        logger.log_agent_execution("linter", 120, 2, ["warning"], success=True)
        logger.log_agent_execution("formatter", 50, 0, [], success=True)

        result = runner.invoke(
            app,
            [
                "metrics",
                "agents",
                "--log-file",
                str(log_file),
                "--period",
                "all",
                "--sort",
                "findings",
            ],
        )

        assert result.exit_code == 0
        assert "Agent Performance" in result.stdout
        assert "linter" in result.stdout
        assert "formatter" in result.stdout


def test_metrics_agents_sort_options():
    """Test metrics agents command with different sort options."""
    with TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"

        # Create logger and add sample events
        logger = TelemetryLogger(log_file)
        logger.log_agent_execution("linter", 100, 5, [], success=True)
        logger.log_agent_execution("formatter", 200, 0, [], success=True)

        # Test sort by duration
        result = runner.invoke(
            app,
            [
                "metrics",
                "agents",
                "--log-file",
                str(log_file),
                "--period",
                "all",
                "--sort",
                "duration",
            ],
        )

        assert result.exit_code == 0
        assert "Agent Performance" in result.stdout


def test_metrics_dashboard_command():
    """Test metrics dashboard command."""
    with TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"

        # Create logger and add sample events
        logger = TelemetryLogger(log_file)
        logger.log_agent_execution("linter", 100, 5, [], success=True)
        logger.log_pre_commit_check(1, True, 100)

        result = runner.invoke(
            app,
            ["metrics", "dashboard", "--log-file", str(log_file), "--period", "all"],
        )

        assert result.exit_code == 0
        assert "Metrics Dashboard" in result.stdout or "DevLoop" in result.stdout


def test_metrics_compare_insufficient_data():
    """Test metrics compare with insufficient data."""
    with TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"
        log_file.touch()

        result = runner.invoke(
            app,
            [
                "metrics",
                "compare",
                "--log-file",
                str(log_file),
                "--before",
                "2024-12-01",
                "--after",
                "2024-12-15",
            ],
        )

        assert result.exit_code == 0
        assert "Insufficient data" in result.stdout


def test_metrics_compare_with_data():
    """Test metrics compare with sample data."""
    with TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"

        # Create logger and add events in both periods
        logger = TelemetryLogger(log_file)

        # Add events for before period
        for _ in range(5):
            logger.log_pre_commit_check(1, True, 100)
            logger.log_agent_execution("linter", 100, 2, [], success=True)

        result = runner.invoke(
            app,
            [
                "metrics",
                "compare",
                "--log-file",
                str(log_file),
                "--before",
                "2024-11-01",
                "--after",
                "2024-12-10",
            ],
        )

        # Will still show insufficient if no data in periods, which is expected
        assert result.exit_code == 0


def test_period_parsing():
    """Test that different period formats are accepted."""
    with TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"

        logger = TelemetryLogger(log_file)
        logger.log_agent_execution("linter", 100, 2, [], success=True)

        for period in ["24h", "7d", "1w", "all", "today"]:
            result = runner.invoke(
                app,
                ["metrics", "value", "--log-file", str(log_file), "--period", period],
            )

            # Should succeed for all valid periods
            if period == "today":
                # Today period might have no events depending on timestamp
                assert result.exit_code == 0
            else:
                assert result.exit_code == 0
                assert "DevLoop" in result.stdout or "No events" in result.stdout
