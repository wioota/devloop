"""Tests for audit CLI commands."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from devloop.cli.commands.audit import audit


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_logger():
    """Create mock audit logger."""
    return Mock()


@pytest.fixture
def sample_entries():
    """Sample audit log entries for testing."""
    return [
        {
            "timestamp": "2024-01-15T10:30:00Z",
            "agent_name": "formatter",
            "action_type": "fix_applied",
            "message": "Applied black formatting",
            "success": True,
            "duration_ms": 150,
            "file_modifications": [{"path": "src/main.py", "action": "modified"}],
            "context": {"fix_type": "formatting", "severity": "low"},
        },
        {
            "timestamp": "2024-01-15T10:31:00Z",
            "agent_name": "linter",
            "action_type": "check",
            "message": "Ran ruff linter",
            "success": False,
            "duration_ms": 200,
            "error": "Found 3 linting errors",
            "file_modifications": [],
        },
        {
            "timestamp": "2024-01-15T10:32:00Z",
            "agent_name": "test_runner",
            "action_type": "test",
            "message": "Ran pytest",
            "success": True,
            "duration_ms": 5000,
            "file_modifications": [],
        },
    ]


class TestAuditGroup:
    """Tests for the audit command group."""

    def test_audit_group_exists(self, runner):
        """Test that audit group command exists."""
        result = runner.invoke(audit, ["--help"])
        assert result.exit_code == 0
        assert "Query and view audit logs" in result.output

    def test_audit_has_subcommands(self, runner):
        """Test that audit group has expected subcommands."""
        result = runner.invoke(audit, ["--help"])
        assert result.exit_code == 0
        assert "recent" in result.output
        assert "by-agent" in result.output
        assert "errors" in result.output
        assert "fixes" in result.output
        assert "file" in result.output
        assert "summary" in result.output


class TestRecentCommand:
    """Tests for the recent command."""

    def test_recent_default(self, runner, mock_logger, sample_entries):
        """Test recent command with default options."""
        mock_logger.query_recent.return_value = sample_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["recent"])
            assert result.exit_code == 0
            mock_logger.query_recent.assert_called_once_with(limit=20)

    def test_recent_with_limit(self, runner, mock_logger, sample_entries):
        """Test recent command with custom limit."""
        mock_logger.query_recent.return_value = sample_entries[:1]

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["recent", "--limit", "1"])
            assert result.exit_code == 0
            mock_logger.query_recent.assert_called_once_with(limit=1)

    def test_recent_json_output(self, runner, mock_logger, sample_entries):
        """Test recent command with JSON output."""
        mock_logger.query_recent.return_value = sample_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["recent", "--json"])
            assert result.exit_code == 0
            output = json.loads(result.output)
            assert len(output) == 3
            assert output[0]["agent_name"] == "formatter"

    def test_recent_empty_entries(self, runner, mock_logger):
        """Test recent command with no entries."""
        mock_logger.query_recent.return_value = []

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["recent"])
            assert result.exit_code == 0
            assert "No audit entries found" in result.output

    def test_recent_shows_file_modifications(self, runner, mock_logger, sample_entries):
        """Test recent command shows file modifications."""
        mock_logger.query_recent.return_value = [sample_entries[0]]

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["recent"])
            assert result.exit_code == 0
            assert "src/main.py" in result.output
            assert "modified" in result.output

    def test_recent_shows_error_on_failure(self, runner, mock_logger, sample_entries):
        """Test recent command shows error for failed entries."""
        mock_logger.query_recent.return_value = [sample_entries[1]]

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["recent"])
            assert result.exit_code == 0
            assert "Error:" in result.output
            assert "3 linting errors" in result.output

    def test_recent_shows_status_icons(self, runner, mock_logger, sample_entries):
        """Test recent command shows success/failure icons."""
        mock_logger.query_recent.return_value = sample_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["recent"])
            assert result.exit_code == 0
            assert "✓" in result.output  # Success icon
            assert "✗" in result.output  # Failure icon


class TestByAgentCommand:
    """Tests for the by_agent command."""

    def test_by_agent_filters_correctly(self, runner, mock_logger, sample_entries):
        """Test by_agent command filters by agent name."""
        mock_logger.query_by_agent.return_value = [sample_entries[0]]

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["by-agent", "formatter"])
            assert result.exit_code == 0
            mock_logger.query_by_agent.assert_called_once_with("formatter", limit=20)

    def test_by_agent_with_limit(self, runner, mock_logger, sample_entries):
        """Test by_agent command with custom limit."""
        mock_logger.query_by_agent.return_value = [sample_entries[0]]

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["by-agent", "formatter", "--limit", "5"])
            assert result.exit_code == 0
            mock_logger.query_by_agent.assert_called_once_with("formatter", limit=5)

    def test_by_agent_json_output(self, runner, mock_logger, sample_entries):
        """Test by_agent command with JSON output."""
        mock_logger.query_by_agent.return_value = [sample_entries[0]]

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["by-agent", "formatter", "--json"])
            assert result.exit_code == 0
            output = json.loads(result.output)
            assert len(output) == 1
            assert output[0]["agent_name"] == "formatter"

    def test_by_agent_empty_results(self, runner, mock_logger):
        """Test by_agent command with no matching entries."""
        mock_logger.query_by_agent.return_value = []

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["by-agent", "nonexistent"])
            assert result.exit_code == 0
            assert "No audit entries found for agent: nonexistent" in result.output

    def test_by_agent_shows_entry_details(self, runner, mock_logger, sample_entries):
        """Test by_agent command shows entry details."""
        mock_logger.query_by_agent.return_value = [sample_entries[0]]

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["by-agent", "formatter"])
            assert result.exit_code == 0
            assert "fix_applied" in result.output
            assert "Applied black formatting" in result.output


class TestErrorsCommand:
    """Tests for the errors command."""

    def test_errors_queries_failed_actions(self, runner, mock_logger, sample_entries):
        """Test errors command queries failed actions."""
        failed_entry = sample_entries[1]
        mock_logger.query_failed_actions.return_value = [failed_entry]

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["errors"])
            assert result.exit_code == 0
            mock_logger.query_failed_actions.assert_called_once_with(limit=20)

    def test_errors_with_limit(self, runner, mock_logger, sample_entries):
        """Test errors command with custom limit."""
        failed_entry = sample_entries[1]
        mock_logger.query_failed_actions.return_value = [failed_entry]

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["errors", "--limit", "5"])
            assert result.exit_code == 0
            mock_logger.query_failed_actions.assert_called_once_with(limit=5)

    def test_errors_json_output(self, runner, mock_logger, sample_entries):
        """Test errors command with JSON output."""
        failed_entry = sample_entries[1]
        mock_logger.query_failed_actions.return_value = [failed_entry]

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["errors", "--json"])
            assert result.exit_code == 0
            output = json.loads(result.output)
            assert len(output) == 1
            assert output[0]["success"] is False

    def test_errors_empty_results(self, runner, mock_logger):
        """Test errors command with no failed actions."""
        mock_logger.query_failed_actions.return_value = []

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["errors"])
            assert result.exit_code == 0
            assert "No failed actions found" in result.output

    def test_errors_shows_error_message(self, runner, mock_logger, sample_entries):
        """Test errors command displays error message."""
        failed_entry = sample_entries[1]
        mock_logger.query_failed_actions.return_value = [failed_entry]

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["errors"])
            assert result.exit_code == 0
            assert "linter" in result.output
            assert "3 linting errors" in result.output


class TestFixesCommand:
    """Tests for the fixes command."""

    def test_fixes_queries_correctly(self, runner, mock_logger, sample_entries):
        """Test fixes command queries fixes applied."""
        fix_entry = sample_entries[0]
        mock_logger.query_fixes_applied.return_value = [fix_entry]

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["fixes"])
            assert result.exit_code == 0
            mock_logger.query_fixes_applied.assert_called_once_with(
                agent_name=None, limit=20
            )

    def test_fixes_with_agent_filter(self, runner, mock_logger, sample_entries):
        """Test fixes command with agent filter."""
        fix_entry = sample_entries[0]
        mock_logger.query_fixes_applied.return_value = [fix_entry]

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["fixes", "--agent", "formatter"])
            assert result.exit_code == 0
            mock_logger.query_fixes_applied.assert_called_once_with(
                agent_name="formatter", limit=20
            )

    def test_fixes_with_limit(self, runner, mock_logger, sample_entries):
        """Test fixes command with custom limit."""
        fix_entry = sample_entries[0]
        mock_logger.query_fixes_applied.return_value = [fix_entry]

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["fixes", "--limit", "5"])
            assert result.exit_code == 0
            mock_logger.query_fixes_applied.assert_called_once_with(
                agent_name=None, limit=5
            )

    def test_fixes_json_output(self, runner, mock_logger, sample_entries):
        """Test fixes command with JSON output."""
        fix_entry = sample_entries[0]
        mock_logger.query_fixes_applied.return_value = [fix_entry]

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["fixes", "--json"])
            assert result.exit_code == 0
            output = json.loads(result.output)
            assert len(output) == 1
            assert output[0]["action_type"] == "fix_applied"

    def test_fixes_empty_results(self, runner, mock_logger):
        """Test fixes command with no fixes found."""
        mock_logger.query_fixes_applied.return_value = []

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["fixes"])
            assert result.exit_code == 0
            assert "No fixes found" in result.output

    def test_fixes_empty_results_with_agent_filter(self, runner, mock_logger):
        """Test fixes command with no fixes found for specific agent."""
        mock_logger.query_fixes_applied.return_value = []

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["fixes", "--agent", "formatter"])
            assert result.exit_code == 0
            assert "No fixes found by formatter" in result.output

    def test_fixes_shows_context(self, runner, mock_logger, sample_entries):
        """Test fixes command shows fix context."""
        fix_entry = sample_entries[0]
        mock_logger.query_fixes_applied.return_value = [fix_entry]

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["fixes"])
            assert result.exit_code == 0
            assert "formatting" in result.output
            assert "low" in result.output


class TestFileCommand:
    """Tests for the file command."""

    @pytest.fixture
    def file_entries(self):
        """Sample file modification entries."""
        return [
            {
                "timestamp": "2024-01-15T10:30:00Z",
                "agent_name": "formatter",
                "message": "Formatted file",
                "file_modifications": [
                    {
                        "path": "src/main.py",
                        "action": "modified",
                        "size_bytes_before": 1000,
                        "size_bytes_after": 1050,
                        "line_count_before": 50,
                        "line_count_after": 52,
                        "diff_lines": [
                            "--- a/src/main.py",
                            "+++ b/src/main.py",
                            "@@ -1,3 +1,3 @@",
                            "-old line",
                            "+new line",
                        ],
                    }
                ],
            }
        ]

    def test_file_queries_correctly(self, runner, mock_logger, file_entries):
        """Test file command queries file modifications."""
        mock_logger.query_file_modifications.return_value = file_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["file", "src/main.py"])
            assert result.exit_code == 0
            mock_logger.query_file_modifications.assert_called_once_with(
                Path("src/main.py"), limit=20
            )

    def test_file_with_limit(self, runner, mock_logger, file_entries):
        """Test file command with custom limit."""
        mock_logger.query_file_modifications.return_value = file_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["file", "src/main.py", "--limit", "5"])
            assert result.exit_code == 0
            mock_logger.query_file_modifications.assert_called_once_with(
                Path("src/main.py"), limit=5
            )

    def test_file_json_output(self, runner, mock_logger, file_entries):
        """Test file command with JSON output."""
        mock_logger.query_file_modifications.return_value = file_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["file", "src/main.py", "--json"])
            assert result.exit_code == 0
            output = json.loads(result.output)
            assert len(output) == 1
            assert output[0]["agent_name"] == "formatter"

    def test_file_empty_results(self, runner, mock_logger):
        """Test file command with no modifications found."""
        mock_logger.query_file_modifications.return_value = []

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["file", "nonexistent.py"])
            assert result.exit_code == 0
            assert "No modifications found for: nonexistent.py" in result.output

    def test_file_shows_size_changes(self, runner, mock_logger, file_entries):
        """Test file command shows size changes."""
        mock_logger.query_file_modifications.return_value = file_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["file", "src/main.py"])
            assert result.exit_code == 0
            assert "1000B" in result.output
            assert "1050B" in result.output
            assert "+50B" in result.output

    def test_file_shows_line_changes(self, runner, mock_logger, file_entries):
        """Test file command shows line count changes."""
        mock_logger.query_file_modifications.return_value = file_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["file", "src/main.py"])
            assert result.exit_code == 0
            assert "50" in result.output
            assert "52" in result.output
            assert "+2" in result.output

    def test_file_shows_diff_when_requested(self, runner, mock_logger, file_entries):
        """Test file command shows diff when --diff flag is used."""
        mock_logger.query_file_modifications.return_value = file_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["file", "src/main.py", "--diff"])
            assert result.exit_code == 0
            assert "Diff:" in result.output
            assert "-old line" in result.output
            assert "+new line" in result.output

    def test_file_truncates_long_diff(self, runner, mock_logger):
        """Test file command truncates long diffs."""
        long_diff_entry = [
            {
                "timestamp": "2024-01-15T10:30:00Z",
                "agent_name": "formatter",
                "message": "Formatted file",
                "file_modifications": [
                    {
                        "path": "src/main.py",
                        "action": "modified",
                        "diff_lines": [f"line {i}" for i in range(20)],
                    }
                ],
            }
        ]
        mock_logger.query_file_modifications.return_value = long_diff_entry

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["file", "src/main.py", "--diff"])
            assert result.exit_code == 0
            assert "... (10 more lines)" in result.output

    def test_file_handles_negative_size_change(self, runner, mock_logger):
        """Test file command handles size decrease."""
        shrink_entry = [
            {
                "timestamp": "2024-01-15T10:30:00Z",
                "agent_name": "formatter",
                "message": "Removed unused code",
                "file_modifications": [
                    {
                        "path": "src/main.py",
                        "action": "modified",
                        "size_bytes_before": 1000,
                        "size_bytes_after": 800,
                        "line_count_before": 50,
                        "line_count_after": 40,
                    }
                ],
            }
        ]
        mock_logger.query_file_modifications.return_value = shrink_entry

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["file", "src/main.py"])
            assert result.exit_code == 0
            assert "-200B" in result.output
            assert "-10" in result.output


class TestSummaryCommand:
    """Tests for the summary command."""

    def test_summary_queries_entries(self, runner, mock_logger, sample_entries):
        """Test summary command queries recent entries."""
        mock_logger.query_recent.return_value = sample_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["summary"])
            assert result.exit_code == 0
            mock_logger.query_recent.assert_called_once_with(limit=1000)

    def test_summary_json_output(self, runner, mock_logger, sample_entries):
        """Test summary command with JSON output."""
        mock_logger.query_recent.return_value = sample_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["summary", "--json"])
            assert result.exit_code == 0
            output = json.loads(result.output)
            assert "total_entries" in output
            assert output["total_entries"] == 3
            assert "success_rate" in output
            assert "by_agent" in output
            assert "by_action" in output

    def test_summary_empty_entries(self, runner, mock_logger):
        """Test summary command with no entries."""
        mock_logger.query_recent.return_value = []

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["summary"])
            assert result.exit_code == 0
            assert "No audit entries found" in result.output

    def test_summary_calculates_success_rate(self, runner, mock_logger, sample_entries):
        """Test summary command calculates correct success rate."""
        mock_logger.query_recent.return_value = sample_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["summary", "--json"])
            assert result.exit_code == 0
            output = json.loads(result.output)
            # 2 successes out of 3 = 66.7%
            assert "66.7%" in output["success_rate"]

    def test_summary_counts_agents(self, runner, mock_logger, sample_entries):
        """Test summary command counts entries by agent."""
        mock_logger.query_recent.return_value = sample_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["summary", "--json"])
            assert result.exit_code == 0
            output = json.loads(result.output)
            assert output["by_agent"]["formatter"] == 1
            assert output["by_agent"]["linter"] == 1
            assert output["by_agent"]["test_runner"] == 1

    def test_summary_counts_actions(self, runner, mock_logger, sample_entries):
        """Test summary command counts entries by action type."""
        mock_logger.query_recent.return_value = sample_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["summary", "--json"])
            assert result.exit_code == 0
            output = json.loads(result.output)
            assert output["by_action"]["fix_applied"] == 1
            assert output["by_action"]["check"] == 1
            assert output["by_action"]["test"] == 1

    def test_summary_totals_duration(self, runner, mock_logger, sample_entries):
        """Test summary command totals duration."""
        mock_logger.query_recent.return_value = sample_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["summary", "--json"])
            assert result.exit_code == 0
            output = json.loads(result.output)
            # 150 + 200 + 5000 = 5350ms
            assert output["total_duration_ms"] == 5350

    def test_summary_counts_file_modifications(
        self, runner, mock_logger, sample_entries
    ):
        """Test summary command counts file modifications."""
        mock_logger.query_recent.return_value = sample_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["summary", "--json"])
            assert result.exit_code == 0
            output = json.loads(result.output)
            # Only first entry has file modifications
            assert output["file_modifications"] == 1

    def test_summary_counts_fixes(self, runner, mock_logger, sample_entries):
        """Test summary command counts fixes applied."""
        mock_logger.query_recent.return_value = sample_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["summary", "--json"])
            assert result.exit_code == 0
            output = json.loads(result.output)
            # One fix_applied action
            assert output["fixes_applied"] == 1

    def test_summary_text_output_format(self, runner, mock_logger, sample_entries):
        """Test summary command text output format."""
        mock_logger.query_recent.return_value = sample_entries

        with patch(
            "devloop.cli.commands.audit.get_agent_audit_logger",
            return_value=mock_logger,
        ):
            result = runner.invoke(audit, ["summary"])
            assert result.exit_code == 0
            assert "Audit Log Summary" in result.output
            assert "Total entries: 3" in result.output
            assert "Total duration: 5350ms" in result.output
            assert "By Agent:" in result.output
            assert "By Action:" in result.output
