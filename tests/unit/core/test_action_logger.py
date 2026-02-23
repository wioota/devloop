"""Tests for CLI action logger."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from devloop.core.action_logger import (
    ActionLogger,
    CLIAction,
    get_action_logger,
    log_cli_command,
)

# ---------------------------------------------------------------------------
# CLIAction
# ---------------------------------------------------------------------------


class TestCLIAction:
    def test_default_timestamp(self) -> None:
        action = CLIAction(command="devloop verify")
        assert action.timestamp  # Non-empty
        assert "T" in action.timestamp  # ISO format

    def test_to_dict_roundtrip(self) -> None:
        action = CLIAction(
            command="devloop watch .",
            exit_code=0,
            duration_ms=1500,
            notes="test run",
        )
        d = action.to_dict()
        assert d["command"] == "devloop watch ."
        assert d["exit_code"] == 0
        assert d["duration_ms"] == 1500

    def test_to_json(self) -> None:
        action = CLIAction(command="ruff check src/")
        js = action.to_json()
        data = json.loads(js)
        assert data["command"] == "ruff check src/"


# ---------------------------------------------------------------------------
# ActionLogger
# ---------------------------------------------------------------------------


@pytest.fixture
def log_path(tmp_path: Path) -> Path:
    return tmp_path / "cli-actions.jsonl"


@pytest.fixture
def logger(log_path: Path) -> ActionLogger:
    return ActionLogger(log_file=log_path)


class TestActionLoggerLogAction:
    def test_log_action_creates_file(
        self, logger: ActionLogger, log_path: Path
    ) -> None:
        action = CLIAction(command="devloop init .")
        logger.log_action(action)
        assert log_path.exists()
        data = json.loads(log_path.read_text().strip())
        assert data["command"] == "devloop init ."

    def test_log_action_appends(self, logger: ActionLogger, log_path: Path) -> None:
        for i in range(3):
            logger.log_action(CLIAction(command=f"cmd{i}"))
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 3


class TestActionLoggerLogCliCommand:
    def test_log_string_command(self, logger: ActionLogger, log_path: Path) -> None:
        logger.log_cli_command("devloop verify", exit_code=0)
        data = json.loads(log_path.read_text().strip())
        assert data["command"] == "devloop verify"
        assert data["exit_code"] == 0

    def test_log_list_command(self, logger: ActionLogger, log_path: Path) -> None:
        logger.log_cli_command(["poetry", "run", "pytest"], exit_code=0)
        data = json.loads(log_path.read_text().strip())
        assert data["command"] == "poetry run pytest"

    def test_captures_user_and_cwd(self, logger: ActionLogger, log_path: Path) -> None:
        with patch.dict("os.environ", {"USER": "testuser"}, clear=False):
            logger.log_cli_command("ls")
        data = json.loads(log_path.read_text().strip())
        assert data["user"] == "testuser"
        assert data["working_dir"]  # Non-empty

    def test_captures_thread_context(
        self, logger: ActionLogger, log_path: Path
    ) -> None:
        with patch.dict(
            "os.environ",
            {"AMP_THREAD_ID": "T-abc123", "AMP_THREAD_URL": "https://amp/t/123"},
            clear=False,
        ):
            logger.log_cli_command("devloop watch .")
        data = json.loads(log_path.read_text().strip())
        assert data["thread_id"] == "T-abc123"
        assert data["thread_url"] == "https://amp/t/123"
        assert "AMP_THREAD_ID" in data["environment"]

    def test_captures_ci_env_vars(self, logger: ActionLogger, log_path: Path) -> None:
        with patch.dict(
            "os.environ",
            {"GITHUB_ACTIONS": "true", "CI": "true"},
            clear=False,
        ):
            logger.log_cli_command("devloop verify")
        data = json.loads(log_path.read_text().strip())
        assert data["environment"]["GITHUB_ACTIONS"] == "true"
        assert data["environment"]["CI"] == "true"

    def test_no_env_when_none_captured(
        self, logger: ActionLogger, log_path: Path
    ) -> None:
        # Remove all capturable env vars
        with patch.dict(
            "os.environ",
            {},
            clear=True,
        ):
            # Need to also patch USER and working dir
            with patch("os.getcwd", return_value="/tmp"):
                logger.log_cli_command("ls")
        data = json.loads(log_path.read_text().strip())
        assert data["environment"] is None

    def test_error_message_captured(self, logger: ActionLogger, log_path: Path) -> None:
        logger.log_cli_command(
            "bad-cmd", exit_code=1, error_message="command not found"
        )
        data = json.loads(log_path.read_text().strip())
        assert data["error_message"] == "command not found"

    def test_duration_and_output_size(
        self, logger: ActionLogger, log_path: Path
    ) -> None:
        logger.log_cli_command(
            "pytest", exit_code=0, duration_ms=5000, output_size_bytes=12345
        )
        data = json.loads(log_path.read_text().strip())
        assert data["duration_ms"] == 5000
        assert data["output_size_bytes"] == 12345


# ---------------------------------------------------------------------------
# ActionLogger.read_recent
# ---------------------------------------------------------------------------


class TestActionLoggerReadRecent:
    def test_read_empty_log(self, logger: ActionLogger) -> None:
        assert logger.read_recent() == []

    def test_read_recent_returns_newest_first(
        self, logger: ActionLogger, log_path: Path
    ) -> None:
        for i in range(5):
            logger.log_action(CLIAction(command=f"cmd{i}"))
        actions = logger.read_recent()
        assert len(actions) == 5
        assert actions[0].command == "cmd4"  # Most recent
        assert actions[4].command == "cmd0"

    def test_read_recent_respects_limit(
        self, logger: ActionLogger, log_path: Path
    ) -> None:
        for i in range(10):
            logger.log_action(CLIAction(command=f"cmd{i}"))
        actions = logger.read_recent(limit=3)
        assert len(actions) == 3
        assert actions[0].command == "cmd9"

    def test_read_recent_skips_malformed_json(
        self, logger: ActionLogger, log_path: Path
    ) -> None:
        log_path.write_text(
            '{"command": "good"}\n' "not valid\n" '{"command": "also_good"}\n'
        )
        actions = logger.read_recent()
        assert len(actions) == 2


# ---------------------------------------------------------------------------
# ActionLogger.read_by_thread
# ---------------------------------------------------------------------------


class TestActionLoggerReadByThread:
    def test_read_empty_log(self, logger: ActionLogger) -> None:
        assert logger.read_by_thread("T-abc") == []

    def test_read_filters_by_thread(self, logger: ActionLogger, log_path: Path) -> None:
        entries = [
            {"command": "cmd1", "thread_id": "T-abc"},
            {"command": "cmd2", "thread_id": "T-xyz"},
            {"command": "cmd3", "thread_id": "T-abc"},
            {"command": "cmd4", "thread_id": None},
        ]
        with open(log_path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

        actions = logger.read_by_thread("T-abc")
        assert len(actions) == 2
        assert all(a.thread_id == "T-abc" for a in actions)

    def test_read_by_thread_skips_malformed(
        self, logger: ActionLogger, log_path: Path
    ) -> None:
        log_path.write_text('{"command": "good", "thread_id": "T-abc"}\n' "bad json\n")
        actions = logger.read_by_thread("T-abc")
        assert len(actions) == 1


# ---------------------------------------------------------------------------
# Global helpers
# ---------------------------------------------------------------------------


class TestGlobalHelpers:
    def test_get_action_logger_creates_instance(self, tmp_path: Path) -> None:
        import devloop.core.action_logger as mod

        mod._action_logger = None
        try:
            al = get_action_logger(devloop_dir=tmp_path)
            assert isinstance(al, ActionLogger)
            assert al.log_file == tmp_path / "cli-actions.jsonl"
        finally:
            mod._action_logger = None

    def test_get_action_logger_returns_singleton(self, tmp_path: Path) -> None:
        import devloop.core.action_logger as mod

        mod._action_logger = None
        try:
            al1 = get_action_logger(devloop_dir=tmp_path)
            al2 = get_action_logger(devloop_dir=tmp_path)
            assert al1 is al2
        finally:
            mod._action_logger = None

    def test_log_cli_command_convenience(self, tmp_path: Path) -> None:
        import devloop.core.action_logger as mod

        mod._action_logger = None
        try:
            log_cli_command("devloop verify", exit_code=0, devloop_dir=tmp_path)
            log_file = tmp_path / "cli-actions.jsonl"
            assert log_file.exists()
            data = json.loads(log_file.read_text().strip())
            assert data["command"] == "devloop verify"
        finally:
            mod._action_logger = None
