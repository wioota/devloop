"""Structured event logging for DevLoop value tracking and metrics."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class EventSeverity(Enum):
    """Event severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class TelemetryEventType(Enum):
    """Types of telemetry events to track."""

    AGENT_EXECUTED = "agent_executed"
    AGENT_FINDING = "agent_finding"
    PRE_COMMIT_CHECK = "pre_commit_check"
    PRE_PUSH_CHECK = "pre_push_check"
    CI_ROUNDTRIP_PREVENTED = "ci_roundtrip_prevented"
    VALUE_EVENT = "value_event"


@dataclass
class TelemetryEvent:
    """Structured telemetry event."""

    event_type: TelemetryEventType
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    agent: Optional[str] = None
    duration_ms: Optional[int] = None
    findings: Optional[int] = None
    severity_levels: Optional[list[str]] = None
    success: Optional[bool] = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert enum to string
        data["event_type"] = self.event_type.value
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class TelemetryLogger:
    """Manages structured event logging to JSONL file."""

    def __init__(self, log_file: Path):
        """Initialize telemetry logger.

        Args:
            log_file: Path to .devloop/events.jsonl file
        """
        self.log_file = log_file
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Ensure log directory exists."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_event(self, event: TelemetryEvent) -> None:
        """Log a structured event to JSONL file.

        Args:
            event: TelemetryEvent to log
        """
        try:
            with open(self.log_file, "a") as f:
                f.write(event.to_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to log telemetry event: {e}")

    def log_agent_execution(
        self,
        agent: str,
        duration_ms: int,
        findings: int = 0,
        severity_levels: Optional[list[str]] = None,
        success: bool = True,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log an agent execution event.

        Args:
            agent: Agent name (e.g., "linter", "test-runner")
            duration_ms: Execution duration in milliseconds
            findings: Number of findings/issues detected
            severity_levels: List of severity levels found (e.g., ["error", "warning"])
            success: Whether agent executed successfully
            details: Additional context (file count, etc.)
        """
        event = TelemetryEvent(
            event_type=TelemetryEventType.AGENT_EXECUTED,
            agent=agent,
            duration_ms=duration_ms,
            findings=findings,
            severity_levels=severity_levels or [],
            success=success,
            details=details or {},
        )
        self.log_event(event)

    def log_agent_finding(
        self,
        agent: str,
        finding_type: str,
        severity: EventSeverity,
        description: str,
        file: Optional[str] = None,
        line: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log an individual agent finding.

        Args:
            agent: Agent name
            finding_type: Type of finding (e.g., "lint-error", "type-error")
            severity: Severity level
            description: Finding description
            file: File path where issue was found
            line: Line number
            details: Additional context
        """
        event = TelemetryEvent(
            event_type=TelemetryEventType.AGENT_FINDING,
            agent=agent,
            severity_levels=[severity.value],
            details={
                "finding_type": finding_type,
                "description": description,
                "file": file,
                "line": line,
                **(details or {}),
            },
        )
        self.log_event(event)

    def log_pre_commit_check(
        self,
        checks_run: int,
        passed: bool,
        duration_ms: int,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log pre-commit hook execution.

        Args:
            checks_run: Number of checks executed
            passed: Whether all checks passed
            duration_ms: Total duration in milliseconds
            details: Check-specific details
        """
        event = TelemetryEvent(
            event_type=TelemetryEventType.PRE_COMMIT_CHECK,
            duration_ms=duration_ms,
            success=passed,
            findings=0 if passed else 1,  # Count as finding if failed
            details={"checks_run": checks_run, **(details or {})},
        )
        self.log_event(event)

    def log_pre_push_check(
        self,
        checks_run: int,
        passed: bool,
        duration_ms: int,
        prevented_bad_push: bool = False,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log pre-push hook execution.

        Args:
            checks_run: Number of checks executed
            passed: Whether all checks passed
            duration_ms: Total duration in milliseconds
            prevented_bad_push: Whether this prevented a bad push to CI
            details: Check-specific details
        """
        event = TelemetryEvent(
            event_type=TelemetryEventType.PRE_PUSH_CHECK,
            duration_ms=duration_ms,
            success=passed,
            findings=0 if passed else 1,
            details={
                "checks_run": checks_run,
                "prevented_bad_push": prevented_bad_push,
                **(details or {}),
            },
        )
        self.log_event(event)

    def log_ci_roundtrip_prevented(
        self,
        reason: str,
        check_that_would_fail: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log when a CI roundtrip was prevented.

        Args:
            reason: Why CI would have failed (e.g., "lint-error", "test-failure")
            check_that_would_fail: Name of the CI check that would have failed
            details: Additional context
        """
        event = TelemetryEvent(
            event_type=TelemetryEventType.CI_ROUNDTRIP_PREVENTED,
            details={
                "reason": reason,
                "check_that_would_fail": check_that_would_fail,
                **(details or {}),
            },
        )
        self.log_event(event)

    def log_value_event(
        self,
        event_name: str,
        time_saved_ms: Optional[int] = None,
        description: str = "",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log a value/impact event.

        Args:
            event_name: Name of the value event (e.g., "interruption_prevented")
            time_saved_ms: Time saved in milliseconds (if applicable)
            description: Human-readable description
            details: Additional context
        """
        event = TelemetryEvent(
            event_type=TelemetryEventType.VALUE_EVENT,
            duration_ms=time_saved_ms,
            details={
                "event_name": event_name,
                "description": description,
                **(details or {}),
            },
        )
        self.log_event(event)

    def get_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent events from log file.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of events (most recent last)
        """
        if not self.log_file.exists():
            return []

        events = []
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            event = json.loads(line)
                            events.append(event)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in telemetry log: {line}")

            # Return last N events
            return events[-limit:]
        except Exception as e:
            logger.error(f"Failed to read telemetry events: {e}")
            return []

    def _get_events_streaming(self) -> list[dict[str, Any]]:
        """Stream events without loading all into memory at once.

        Returns:
            List of all events (loaded in small batches internally)
        """
        if not self.log_file.exists():
            return []

        events = []
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            event = json.loads(line)
                            events.append(event)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in telemetry log: {line}")
            return events
        except Exception as e:
            logger.error(f"Failed to read telemetry events: {e}")
            return []

    def get_stats(self) -> dict[str, Any]:
        """Get statistics from telemetry log.

        Returns:
            Dictionary with stats: total_events, events_by_type, total_findings, etc.
        """
        events = self._get_events_streaming()

        if not events:
            return {
                "total_events": 0,
                "events_by_type": {},
                "total_findings": 0,
                "total_time_saved_ms": 0,
                "ci_roundtrips_prevented": 0,
            }

        stats: dict[str, Any] = {
            "total_events": len(events),
            "events_by_type": {},
            "total_findings": 0,
            "total_time_saved_ms": 0,
            "ci_roundtrips_prevented": 0,
            "agents_executed": {},
        }

        for event in events:
            event_type: Optional[str] = event.get("event_type")  # type: ignore
            if event_type is not None:
                events_by_type: dict[str, Any] = stats["events_by_type"]  # type: ignore
                events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

            findings: Any = event.get("findings", 0)  # type: ignore
            if findings:
                stats["total_findings"] += findings  # type: ignore

            duration: Any = event.get("duration_ms", 0)  # type: ignore
            if duration and event_type == "value_event":
                stats["total_time_saved_ms"] += duration  # type: ignore

            if event_type == "ci_roundtrip_prevented":
                stats["ci_roundtrips_prevented"] += 1  # type: ignore

            agent: Optional[str] = event.get("agent")  # type: ignore
            if agent:
                agents_executed: dict[str, Any] = stats["agents_executed"]  # type: ignore
                if agent not in agents_executed:
                    agents_executed[agent] = {
                        "count": 0,
                        "total_duration_ms": 0,
                    }
                agent_stats: dict[str, Any] = agents_executed[agent]  # type: ignore
                agent_stats["count"] += 1
                if duration:
                    agent_stats["total_duration_ms"] += duration

        return stats


# Global telemetry instance
_telemetry_logger: Optional[TelemetryLogger] = None


def get_telemetry_logger(log_file: Optional[Path] = None) -> TelemetryLogger:
    """Get or create global telemetry logger instance.

    Args:
        log_file: Path to events.jsonl file (defaults to .devloop/events.jsonl)

    Returns:
        TelemetryLogger instance
    """
    global _telemetry_logger

    if _telemetry_logger is None:
        if log_file is None:
            log_file = Path(".devloop/events.jsonl")
        _telemetry_logger = TelemetryLogger(log_file)

    return _telemetry_logger
