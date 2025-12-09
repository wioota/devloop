"""Tests for agent audit logger."""

import json
import tempfile
from pathlib import Path
from typing import Optional

import pytest

from devloop.core.agent_audit_logger import (
    AgentAuditLogger,
    AgentAuditEntry,
    ActionType,
    FileModification,
    get_agent_audit_logger,
)


@pytest.fixture
def temp_log_dir():
    """Create temporary directory for audit logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def logger(temp_log_dir):
    """Create audit logger with temporary directory."""
    return AgentAuditLogger(temp_log_dir / "audit.log")


class TestAuditEntry:
    """Tests for AuditEntry dataclass."""

    def test_audit_entry_creation(self):
        """Test creating an audit entry."""
        entry = AgentAuditEntry(
            timestamp="2024-01-01T00:00:00+00:00",
            agent_name="test-agent",
            action_type="file_modified",
            message="Test message",
            success=True,
            duration_ms=100,
        )
        
        assert entry.agent_name == "test-agent"
        assert entry.action_type == "file_modified"
        assert entry.success is True
        assert entry.duration_ms == 100

    def test_audit_entry_to_json(self):
        """Test converting entry to JSON."""
        entry = AgentAuditEntry(
            timestamp="2024-01-01T00:00:00+00:00",
            agent_name="test-agent",
            action_type="file_modified",
            message="Test message",
            success=True,
            duration_ms=100,
        )
        
        json_str = entry.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["agent_name"] == "test-agent"
        assert parsed["action_type"] == "file_modified"
        assert parsed["success"] is True


class TestFileModification:
    """Tests for FileModification dataclass."""

    def test_file_modification_created(self):
        """Test FileModification for created file."""
        mod = FileModification(
            path="/test/file.py",
            action="created",
            size_bytes_after=100,
            line_count_after=10,
            hash_after="abc123",
        )
        
        assert mod.action == "created"
        assert mod.size_bytes_before is None
        assert mod.size_bytes_after == 100

    def test_file_modification_to_dict(self):
        """Test converting to dictionary."""
        mod = FileModification(
            path="/test/file.py",
            action="modified",
            size_bytes_before=100,
            size_bytes_after=110,
            line_count_before=10,
            line_count_after=11,
        )
        
        d = mod.to_dict()
        assert d["path"] == "/test/file.py"
        assert d["action"] == "modified"
        assert d["size_bytes_before"] == 100
        assert d["size_bytes_after"] == 110


class TestAgentAuditLogger:
    """Tests for AgentAuditLogger."""

    def test_logger_initialization(self, temp_log_dir):
        """Test logger initialization."""
        log_path = temp_log_dir / "test-audit.log"
        logger = AgentAuditLogger(log_path)
        
        assert logger.log_path == log_path
        assert logger.log_path.parent.exists()

    def test_log_action(self, logger, temp_log_dir):
        """Test logging an action."""
        logger.log_action(
            agent_name="formatter",
            action_type=ActionType.FILE_MODIFIED,
            message="Formatted file",
            success=True,
            duration_ms=50,
        )
        
        # Verify log file was created
        assert logger.log_path.exists()
        
        # Read and verify entry
        with open(logger.log_path) as f:
            line = f.readline()
            entry = json.loads(line)
        
        assert entry["agent_name"] == "formatter"
        assert entry["action_type"] == "file_modified"
        assert entry["success"] is True
        assert entry["duration_ms"] == 50

    def test_log_file_modified(self, logger, tmp_path):
        """Test logging file modification with diff."""
        test_file = tmp_path / "test.py"
        
        before = "def hello():\n    print('world')\n"
        after = "def hello():\n    print('hello')\n"
        
        logger.log_file_modified(
            agent_name="formatter",
            file_path=test_file,
            before_content=before,
            after_content=after,
            message="Formatted test.py",
        )
        
        # Read entry
        with open(logger.log_path) as f:
            entry = json.loads(f.readline())
        
        assert entry["agent_name"] == "formatter"
        assert entry["action_type"] == "file_modified"
        assert len(entry["file_modifications"]) == 1
        
        mod = entry["file_modifications"][0]
        assert mod["action"] == "modified"
        assert mod["line_count_before"] == 2
        assert mod["line_count_after"] == 2
        assert mod["diff_lines"] is not None
        assert len(mod["diff_lines"]) > 0

    def test_log_fix_applied(self, logger, tmp_path):
        """Test logging fix application."""
        test_file = tmp_path / "test.py"
        
        before = "x=1"
        after = "x = 1"
        
        logger.log_fix_applied(
            agent_name="formatter",
            file_path=test_file,
            before_content=before,
            after_content=after,
            fix_type="formatting",
            severity="info",
        )
        
        with open(logger.log_path) as f:
            entry = json.loads(f.readline())
        
        assert entry["action_type"] == "fix_applied"
        assert entry["context"]["fix_type"] == "formatting"
        assert entry["context"]["severity"] == "info"

    def test_log_command_execution(self, logger):
        """Test logging command execution."""
        logger.log_command_execution(
            agent_name="test-runner",
            command="pytest tests/",
            exit_code=0,
            success=True,
            duration_ms=1500,
            message="Tests passed",
        )
        
        with open(logger.log_path) as f:
            entry = json.loads(f.readline())
        
        assert entry["action_type"] == "command_executed"
        assert entry["command"] == "pytest tests/"
        assert entry["exit_code"] == 0
        assert entry["success"] is True

    def test_log_finding_reported(self, logger):
        """Test logging a finding."""
        logger.log_finding_reported(
            agent_name="linter",
            finding_type="line-too-long",
            severity="warning",
            message="Line exceeds max length",
            file_path=Path("test.py"),
            line_number=42,
            fixable=True,
        )
        
        with open(logger.log_path) as f:
            entry = json.loads(f.readline())
        
        assert entry["action_type"] == "finding_reported"
        assert entry["context"]["finding_type"] == "line-too-long"
        assert entry["context"]["line_number"] == 42
        assert entry["context"]["fixable"] is True

    def test_log_error(self, logger):
        """Test logging an error."""
        logger.log_error(
            agent_name="formatter",
            error="File not found",
            message="Failed to format file",
            duration_ms=100,
        )
        
        with open(logger.log_path) as f:
            entry = json.loads(f.readline())
        
        assert entry["action_type"] == "error_occurred"
        assert entry["success"] is False
        assert entry["error"] == "File not found"

    def test_query_recent(self, logger):
        """Test querying recent entries."""
        # Add multiple entries
        for i in range(5):
            logger.log_action(
                agent_name=f"agent-{i}",
                action_type=ActionType.FILE_MODIFIED,
                message=f"Action {i}",
                success=True,
                duration_ms=10 * i,
            )
        
        entries = logger.query_recent(limit=10)
        
        assert len(entries) == 5
        # Most recent should be first
        assert entries[0]["agent_name"] == "agent-4"
        assert entries[-1]["agent_name"] == "agent-0"

    def test_query_recent_with_limit(self, logger):
        """Test query with limit."""
        for i in range(10):
            logger.log_action(
                agent_name="agent",
                action_type=ActionType.FILE_MODIFIED,
                message=f"Action {i}",
                success=True,
                duration_ms=0,
            )
        
        entries = logger.query_recent(limit=5)
        assert len(entries) == 5

    def test_query_by_agent(self, logger):
        """Test querying by agent name."""
        logger.log_action(
            agent_name="formatter",
            action_type=ActionType.FILE_MODIFIED,
            message="Action 1",
            success=True,
            duration_ms=0,
        )
        logger.log_action(
            agent_name="linter",
            action_type=ActionType.FINDING_REPORTED,
            message="Action 2",
            success=True,
            duration_ms=0,
        )
        logger.log_action(
            agent_name="formatter",
            action_type=ActionType.FILE_MODIFIED,
            message="Action 3",
            success=True,
            duration_ms=0,
        )
        
        entries = logger.query_by_agent("formatter", limit=10)
        assert len(entries) == 2
        assert all(e["agent_name"] == "formatter" for e in entries)

    def test_query_by_action_type(self, logger):
        """Test querying by action type."""
        logger.log_action(
            agent_name="agent-1",
            action_type=ActionType.FILE_MODIFIED,
            message="Modified",
            success=True,
            duration_ms=0,
        )
        logger.log_action(
            agent_name="agent-2",
            action_type=ActionType.ERROR_OCCURRED,
            message="Error",
            success=False,
            duration_ms=0,
            error="Test error",
        )
        
        entries = logger.query_by_action_type(ActionType.FILE_MODIFIED)
        assert len(entries) == 1
        assert entries[0]["action_type"] == "file_modified"

    def test_query_failed_actions(self, logger):
        """Test querying failed actions."""
        logger.log_action(
            agent_name="agent-1",
            action_type=ActionType.FILE_MODIFIED,
            message="Success",
            success=True,
            duration_ms=0,
        )
        logger.log_action(
            agent_name="agent-2",
            action_type=ActionType.FILE_MODIFIED,
            message="Failed",
            success=False,
            duration_ms=0,
            error="Test error",
        )
        
        entries = logger.query_failed_actions()
        assert len(entries) == 1
        assert entries[0]["agent_name"] == "agent-2"

    def test_query_fixes_applied(self, logger, tmp_path):
        """Test querying fixes."""
        test_file = tmp_path / "test.py"
        
        logger.log_fix_applied(
            agent_name="formatter",
            file_path=test_file,
            before_content="x=1",
            after_content="x = 1",
            fix_type="spacing",
        )
        logger.log_fix_applied(
            agent_name="linter",
            file_path=test_file,
            before_content="import unused",
            after_content="",
            fix_type="unused-import",
        )
        
        entries = logger.query_fixes_applied()
        assert len(entries) == 2
        
        entries = logger.query_fixes_applied(agent_name="formatter")
        assert len(entries) == 1
        assert entries[0]["context"]["fix_type"] == "spacing"

    def test_diff_generation_for_small_changes(self, logger, tmp_path):
        """Test diff generation for small file changes."""
        test_file = tmp_path / "test.py"
        
        before = "def hello():\n    pass\n"
        after = "def hello():\n    print('hello')\n"
        
        logger.log_file_modified(
            agent_name="formatter",
            file_path=test_file,
            before_content=before,
            after_content=after,
        )
        
        with open(logger.log_path) as f:
            entry = json.loads(f.readline())
        
        mod = entry["file_modifications"][0]
        assert mod["diff_lines"] is not None
        # Should have diff header + changes
        assert any("@@ " in line for line in mod["diff_lines"])

    def test_diff_truncation_for_large_changes(self, logger, tmp_path):
        """Test diff is truncated for very large changes."""
        test_file = tmp_path / "large.py"
        
        # Create a large file with many lines
        before = "\n".join(f"line {i}" for i in range(200))
        after = "\n".join(f"line {i + 1000}" for i in range(200))
        
        logger.log_file_modified(
            agent_name="formatter",
            file_path=test_file,
            before_content=before,
            after_content=after,
        )
        
        with open(logger.log_path) as f:
            entry = json.loads(f.readline())
        
        mod = entry["file_modifications"][0]
        assert mod["diff_lines"] is not None
        # Should have truncation marker
        assert any("truncated" in line.lower() for line in mod["diff_lines"])

    def test_file_hash_calculation(self, logger, tmp_path):
        """Test SHA256 hash calculation for files."""
        test_file = tmp_path / "test.py"
        
        before = "content before"
        after = "content after"
        
        logger.log_file_modified(
            agent_name="formatter",
            file_path=test_file,
            before_content=before,
            after_content=after,
        )
        
        with open(logger.log_path) as f:
            entry = json.loads(f.readline())
        
        mod = entry["file_modifications"][0]
        
        # Verify hashes are present and different
        assert mod["hash_before"] is not None
        assert mod["hash_after"] is not None
        assert mod["hash_before"] != mod["hash_after"]
        assert len(mod["hash_before"]) == 64  # SHA256 hex length
        assert len(mod["hash_after"]) == 64

    def test_action_type_enum_conversion(self, logger):
        """Test ActionType enum is properly handled."""
        logger.log_action(
            agent_name="test",
            action_type=ActionType.FIX_APPLIED,
            message="Test",
            success=True,
            duration_ms=0,
        )
        
        with open(logger.log_path) as f:
            entry = json.loads(f.readline())
        
        assert entry["action_type"] == "fix_applied"

    def test_nonexistent_log_file_query(self, temp_log_dir):
        """Test querying when log file doesn't exist."""
        logger = AgentAuditLogger(temp_log_dir / "nonexistent.log")
        
        entries = logger.query_recent()
        assert entries == []

    def test_invalid_json_in_log_handling(self, logger):
        """Test handling of invalid JSON in log file."""
        # Write invalid JSON to log file
        with open(logger.log_path, "w") as f:
            f.write("invalid json\n")
            f.write('{"valid": "json"}\n')
        
        entries = logger.query_recent()
        # Should skip invalid line and return valid entry
        assert len(entries) == 1
        assert entries[0]["valid"] == "json"

    def test_singleton_pattern(self, temp_log_dir, monkeypatch):
        """Test get_agent_audit_logger returns singleton."""
        # Reset global instance
        import devloop.core.agent_audit_logger
        devloop.core.agent_audit_logger._agent_audit_logger = None
        
        logger1 = get_agent_audit_logger()
        logger2 = get_agent_audit_logger()
        
        assert logger1 is logger2
