"""Tests for telemetry module."""

import json
import tempfile
from pathlib import Path


from devloop.core.telemetry import (
    EventSeverity,
    TelemetryEvent,
    TelemetryEventType,
    TelemetryLogger,
)


def test_telemetry_event_creation():
    """Test creating a telemetry event."""
    event = TelemetryEvent(
        event_type=TelemetryEventType.AGENT_EXECUTED,
        agent="linter",
        duration_ms=123,
        findings=3,
        severity_levels=["error", "warning"],
        success=True,
    )

    assert event.event_type == TelemetryEventType.AGENT_EXECUTED
    assert event.agent == "linter"
    assert event.duration_ms == 123
    assert event.findings == 3
    assert event.success is True


def test_telemetry_event_to_dict():
    """Test converting event to dictionary."""
    event = TelemetryEvent(
        event_type=TelemetryEventType.AGENT_EXECUTED,
        agent="linter",
        duration_ms=100,
    )

    data = event.to_dict()
    assert data["event_type"] == "agent_executed"
    assert data["agent"] == "linter"
    assert data["duration_ms"] == 100


def test_telemetry_event_to_json():
    """Test converting event to JSON string."""
    event = TelemetryEvent(
        event_type=TelemetryEventType.AGENT_EXECUTED,
        agent="linter",
        duration_ms=100,
    )

    json_str = event.to_json()
    data = json.loads(json_str)

    assert data["event_type"] == "agent_executed"
    assert data["agent"] == "linter"


def test_telemetry_logger_log_event():
    """Test logging an event to file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"
        logger = TelemetryLogger(log_file)

        event = TelemetryEvent(
            event_type=TelemetryEventType.AGENT_EXECUTED,
            agent="linter",
            duration_ms=100,
        )

        logger.log_event(event)

        assert log_file.exists()
        with open(log_file) as f:
            line = f.readline()
            data = json.loads(line)
            assert data["event_type"] == "agent_executed"


def test_telemetry_logger_log_agent_execution():
    """Test logging agent execution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"
        logger = TelemetryLogger(log_file)

        logger.log_agent_execution(
            agent="linter",
            duration_ms=150,
            findings=2,
            severity_levels=["error"],
            success=True,
        )

        assert log_file.exists()
        with open(log_file) as f:
            data = json.loads(f.readline())
            assert data["event_type"] == "agent_executed"
            assert data["agent"] == "linter"
            assert data["duration_ms"] == 150
            assert data["findings"] == 2


def test_telemetry_logger_get_events():
    """Test retrieving recent events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"
        logger = TelemetryLogger(log_file)

        # Log multiple events
        for i in range(5):
            logger.log_agent_execution(
                agent=f"agent_{i}",
                duration_ms=100 + i,
                findings=i,
                success=True,
            )

        events = logger.get_events(limit=3)
        assert len(events) == 3
        assert events[-1]["agent"] == "agent_4"


def test_telemetry_logger_get_stats():
    """Test getting statistics from logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"
        logger = TelemetryLogger(log_file)

        # Log different types of events
        logger.log_agent_execution(
            agent="linter",
            duration_ms=100,
            findings=2,
            success=True,
        )
        logger.log_agent_execution(
            agent="linter",
            duration_ms=150,
            findings=1,
            success=True,
        )
        logger.log_pre_push_check(
            checks_run=1,
            passed=True,
            duration_ms=200,
        )
        logger.log_ci_roundtrip_prevented(
            reason="lint-error",
            check_that_would_fail="linter",
        )
        logger.log_value_event(
            event_name="time_saved",
            time_saved_ms=500,
        )

        stats = logger.get_stats()

        assert stats["total_events"] == 5
        assert stats["total_findings"] == 3
        assert stats["ci_roundtrips_prevented"] == 1
        assert stats["total_time_saved_ms"] == 500
        assert "agent_executed" in stats["events_by_type"]
        assert "linter" in stats["agents_executed"]


def test_telemetry_logger_log_agent_finding():
    """Test logging individual agent findings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"
        logger = TelemetryLogger(log_file)

        logger.log_agent_finding(
            agent="linter",
            finding_type="line-too-long",
            severity=EventSeverity.WARNING,
            description="Line exceeds 88 characters",
            file="src/main.py",
            line=42,
        )

        events = logger.get_events(limit=1)
        assert len(events) == 1
        assert events[0]["event_type"] == "agent_finding"
        assert events[0]["agent"] == "linter"
        assert events[0]["details"]["finding_type"] == "line-too-long"
        assert events[0]["details"]["file"] == "src/main.py"


def test_telemetry_logger_log_pre_commit_check():
    """Test logging pre-commit checks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"
        logger = TelemetryLogger(log_file)

        logger.log_pre_commit_check(
            checks_run=3,
            passed=True,
            duration_ms=500,
            details={"checks": ["lint", "type-check", "format"]},
        )

        events = logger.get_events(limit=1)
        assert events[0]["event_type"] == "pre_commit_check"
        assert events[0]["success"] is True
        assert events[0]["details"]["checks_run"] == 3


def test_telemetry_logger_log_pre_push_check():
    """Test logging pre-push checks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"
        logger = TelemetryLogger(log_file)

        logger.log_pre_push_check(
            checks_run=1,
            passed=False,
            duration_ms=100,
            prevented_bad_push=True,
            details={"reason": "CI failure"},
        )

        events = logger.get_events(limit=1)
        assert events[0]["event_type"] == "pre_push_check"
        assert events[0]["success"] is False
        assert events[0]["details"]["prevented_bad_push"] is True


def test_telemetry_logger_log_ci_roundtrip_prevented():
    """Test logging prevented CI roundtrips."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"
        logger = TelemetryLogger(log_file)

        logger.log_ci_roundtrip_prevented(
            reason="test-failure",
            check_that_would_fail="pytest",
            details={"test_name": "test_auth"},
        )

        events = logger.get_events(limit=1)
        assert events[0]["event_type"] == "ci_roundtrip_prevented"
        assert events[0]["details"]["reason"] == "test-failure"


def test_telemetry_logger_log_value_event():
    """Test logging value events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "events.jsonl"
        logger = TelemetryLogger(log_file)

        logger.log_value_event(
            event_name="interruption_prevented",
            time_saved_ms=1000,
            description="Prevented context switch to CI debugger",
        )

        events = logger.get_events(limit=1)
        assert events[0]["event_type"] == "value_event"
        assert events[0]["duration_ms"] == 1000
        assert events[0]["details"]["event_name"] == "interruption_prevented"


def test_telemetry_logger_export_json(tmp_path):
    """Test exporting events as JSON."""
    log_file = tmp_path / "events.jsonl"
    output_file = tmp_path / "export.json"

    logger = TelemetryLogger(log_file)

    # Log some events
    logger.log_agent_execution(
        agent="linter",
        duration_ms=100,
        findings=1,
        success=True,
    )

    # Export to JSON
    import json

    events = logger.get_events(limit=100)
    with open(output_file, "w") as f:
        json.dump(events, f)

    assert output_file.exists()
    with open(output_file) as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["event_type"] == "agent_executed"


def test_telemetry_logger_creates_directory():
    """Test that logger creates directory if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "subdir" / "events.jsonl"
        TelemetryLogger(log_file)

        # Directory should be created
        assert log_file.parent.exists()
