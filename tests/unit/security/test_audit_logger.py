"""Tests for sandbox audit logger."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from devloop.security.audit_logger import (
    AuditEntry,
    SandboxAuditLogger,
    get_audit_logger,
)
from devloop.security.sandbox import SandboxResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def log_path(tmp_path: Path) -> Path:
    return tmp_path / "security-audit.log"


@pytest.fixture
def logger(log_path: Path) -> SandboxAuditLogger:
    return SandboxAuditLogger(log_path=log_path, retention_days=30)


@pytest.fixture
def sample_result() -> SandboxResult:
    return SandboxResult(
        stdout="ok",
        stderr="",
        exit_code=0,
        duration_ms=42,
        memory_peak_mb=10.5,
        cpu_usage_percent=5.0,
    )


def _write_entries(log_path: Path, entries: list[dict]) -> None:
    """Helper: write JSONL entries to the log file."""
    with open(log_path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# AuditEntry
# ---------------------------------------------------------------------------


class TestAuditEntry:
    def test_to_json_roundtrip(self) -> None:
        entry = AuditEntry(
            timestamp="2025-01-01T00:00:00+00:00",
            sandbox_mode="bubblewrap",
            command="ruff",
            args_count=2,
            cwd="/tmp",
            exit_code=0,
            duration_ms=100,
            memory_peak_mb=10.0,
            cpu_usage_percent=5.0,
            blocked=False,
        )
        data = json.loads(entry.to_json())
        assert data["command"] == "ruff"
        assert data["blocked"] is False
        assert data["block_reason"] is None


# ---------------------------------------------------------------------------
# Logging methods
# ---------------------------------------------------------------------------


class TestLogExecution:
    def test_log_execution_creates_file(
        self, logger: SandboxAuditLogger, log_path: Path, sample_result: SandboxResult
    ) -> None:
        logger.log_execution(
            sandbox_mode="bubblewrap",
            cmd=["ruff", "check", "."],
            cwd=Path("/project"),
            result=sample_result,
        )
        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["command"] == "ruff"
        assert data["args_count"] == 2

    def test_log_execution_empty_cmd(
        self, logger: SandboxAuditLogger, log_path: Path, sample_result: SandboxResult
    ) -> None:
        logger.log_execution(
            sandbox_mode="none",
            cmd=[],
            cwd=Path("/project"),
            result=sample_result,
        )
        data = json.loads(log_path.read_text().strip())
        assert data["command"] == "unknown"
        assert data["args_count"] == 0

    def test_log_execution_appends(
        self, logger: SandboxAuditLogger, log_path: Path, sample_result: SandboxResult
    ) -> None:
        for _ in range(3):
            logger.log_execution(
                sandbox_mode="bubblewrap",
                cmd=["python3", "test.py"],
                cwd=Path("/project"),
                result=sample_result,
            )
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 3


class TestLogBlockedCommand:
    def test_log_blocked_command(
        self, logger: SandboxAuditLogger, log_path: Path
    ) -> None:
        logger.log_blocked_command(
            sandbox_mode="bubblewrap",
            cmd=["rm", "-rf", "/"],
            cwd=Path("/project"),
            reason="Command not in whitelist",
        )
        data = json.loads(log_path.read_text().strip())
        assert data["blocked"] is True
        assert data["block_reason"] == "Command not in whitelist"
        assert data["exit_code"] == -1


class TestLogTimeout:
    def test_log_timeout(self, logger: SandboxAuditLogger, log_path: Path) -> None:
        logger.log_timeout(
            sandbox_mode="bubblewrap",
            cmd=["python3", "slow.py"],
            cwd=Path("/project"),
            duration_ms=30000,
        )
        data = json.loads(log_path.read_text().strip())
        assert data["timeout"] is True
        assert data["error"] == "Execution exceeded timeout"
        assert data["duration_ms"] == 30000


# ---------------------------------------------------------------------------
# Query methods
# ---------------------------------------------------------------------------


class TestQueryRecent:
    def test_query_empty_log(self, logger: SandboxAuditLogger) -> None:
        assert logger.query_recent() == []

    def test_query_recent_returns_newest_first(
        self, logger: SandboxAuditLogger, log_path: Path
    ) -> None:
        entries = [
            {
                "timestamp": f"2025-01-0{i}T00:00:00+00:00",
                "command": f"cmd{i}",
                "blocked": False,
            }
            for i in range(1, 4)
        ]
        _write_entries(log_path, entries)

        result = logger.query_recent(limit=10)
        assert len(result) == 3
        assert result[0]["command"] == "cmd3"  # newest first
        assert result[2]["command"] == "cmd1"

    def test_query_recent_respects_limit(
        self, logger: SandboxAuditLogger, log_path: Path
    ) -> None:
        entries = [
            {"timestamp": f"2025-01-{i:02d}T00:00:00+00:00", "command": f"cmd{i}"}
            for i in range(1, 11)
        ]
        _write_entries(log_path, entries)

        result = logger.query_recent(limit=3)
        assert len(result) == 3
        # Should be the last 3 entries, reversed
        assert result[0]["command"] == "cmd10"

    def test_query_recent_skips_invalid_json(
        self, logger: SandboxAuditLogger, log_path: Path
    ) -> None:
        log_path.write_text(
            '{"command": "good"}\n' "not valid json\n" '{"command": "also_good"}\n'
        )
        result = logger.query_recent()
        assert len(result) == 2


class TestQueryBlocked:
    def test_query_blocked_filters_correctly(
        self, logger: SandboxAuditLogger, log_path: Path
    ) -> None:
        entries = [
            {
                "timestamp": "2025-01-01T00:00:00+00:00",
                "command": "ruff",
                "blocked": False,
            },
            {
                "timestamp": "2025-01-02T00:00:00+00:00",
                "command": "rm",
                "blocked": True,
            },
            {
                "timestamp": "2025-01-03T00:00:00+00:00",
                "command": "python3",
                "blocked": False,
            },
            {
                "timestamp": "2025-01-04T00:00:00+00:00",
                "command": "curl",
                "blocked": True,
            },
        ]
        _write_entries(log_path, entries)

        result = logger.query_blocked(limit=10)
        assert len(result) == 2
        commands = [e["command"] for e in result]
        assert "rm" in commands
        assert "curl" in commands

    def test_query_blocked_empty_when_none_blocked(
        self, logger: SandboxAuditLogger, log_path: Path
    ) -> None:
        entries = [
            {
                "timestamp": "2025-01-01T00:00:00+00:00",
                "command": "ruff",
                "blocked": False,
            },
        ]
        _write_entries(log_path, entries)
        assert logger.query_blocked() == []


class TestQueryErrors:
    def test_query_errors_filters_nonzero_exit(
        self, logger: SandboxAuditLogger, log_path: Path
    ) -> None:
        entries = [
            {
                "timestamp": "2025-01-01T00:00:00+00:00",
                "command": "ruff",
                "exit_code": 0,
            },
            {
                "timestamp": "2025-01-02T00:00:00+00:00",
                "command": "mypy",
                "exit_code": 1,
            },
            {
                "timestamp": "2025-01-03T00:00:00+00:00",
                "command": "black",
                "exit_code": 0,
                "error": "disk full",
            },
        ]
        _write_entries(log_path, entries)

        result = logger.query_errors(limit=10)
        assert len(result) == 2
        commands = [e["command"] for e in result]
        assert "mypy" in commands
        assert "black" in commands

    def test_query_errors_empty_when_all_ok(
        self, logger: SandboxAuditLogger, log_path: Path
    ) -> None:
        entries = [
            {
                "timestamp": "2025-01-01T00:00:00+00:00",
                "command": "ruff",
                "exit_code": 0,
            },
        ]
        _write_entries(log_path, entries)
        assert logger.query_errors() == []


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


class TestCleanup:
    def test_cleanup_removes_old_entries(self, log_path: Path) -> None:
        audit = SandboxAuditLogger(log_path=log_path, retention_days=7)

        old_ts = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        recent_ts = datetime.now(timezone.utc).isoformat()

        entries = [
            {"timestamp": old_ts, "command": "old_cmd"},
            {"timestamp": recent_ts, "command": "recent_cmd"},
        ]
        _write_entries(log_path, entries)

        audit._cleanup_old_logs_sync()

        remaining = log_path.read_text().strip().splitlines()
        assert len(remaining) == 1
        assert json.loads(remaining[0])["command"] == "recent_cmd"

    def test_cleanup_keeps_malformed_lines(self, log_path: Path) -> None:
        audit = SandboxAuditLogger(log_path=log_path, retention_days=7)

        old_ts = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        log_path.write_text(
            json.dumps({"timestamp": old_ts, "command": "old"}) + "\n"
            "not valid json\n"
        )

        audit._cleanup_old_logs_sync()

        remaining = log_path.read_text().strip().splitlines()
        # Old entry removed, malformed line kept
        assert len(remaining) == 1
        assert remaining[0] == "not valid json"

    def test_cleanup_skipped_when_recently_modified(
        self, logger: SandboxAuditLogger, log_path: Path, sample_result: SandboxResult
    ) -> None:
        """_cleanup_old_logs skips if file mtime is recent (< 5 minutes)."""
        old_ts = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        _write_entries(log_path, [{"timestamp": old_ts, "command": "old"}])

        # File was just written, so mtime is very recent → cleanup is skipped
        logger._cleanup_old_logs()

        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1  # Not cleaned up

    def test_cleanup_runs_when_file_is_stale(self, log_path: Path) -> None:
        """_cleanup_old_logs runs when file mtime is > 5 minutes old."""
        audit = SandboxAuditLogger(log_path=log_path, retention_days=7)

        old_ts = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        _write_entries(log_path, [{"timestamp": old_ts, "command": "ancient"}])

        # Backdate the file mtime to 10 minutes ago
        import os

        old_mtime = time.time() - 600
        os.utime(log_path, (old_mtime, old_mtime))

        audit._cleanup_old_logs()

        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 0  # Cleaned up

    def test_cleanup_on_nonexistent_file(self, logger: SandboxAuditLogger) -> None:
        """_cleanup_old_logs is a no-op when log file doesn't exist."""
        logger._cleanup_old_logs()  # Should not raise


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------


class TestGetAuditLogger:
    def test_returns_singleton(self) -> None:
        import devloop.security.audit_logger as mod

        # Reset singleton
        mod._audit_logger = None
        try:
            logger1 = get_audit_logger()
            logger2 = get_audit_logger()
            assert logger1 is logger2
        finally:
            mod._audit_logger = None
