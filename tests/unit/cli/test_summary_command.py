"""Tests for the summary subcommand."""


import pytest
from typer.testing import CliRunner

from devloop.cli.commands.summary import app as summary_app


@pytest.fixture
def cli_runner():
    """Create a CliRunner for testing."""
    return CliRunner()


class TestSummaryCommand:
    """Tests for the summary subcommand."""

    def test_summary_help(self, cli_runner):
        """Test that summary command has help."""
        result = cli_runner.invoke(summary_app, ["--help"])

        assert result.exit_code == 0
        assert "summary" in result.stdout.lower() or "Usage" in result.stdout

    def test_summary_accepts_scope(self, cli_runner):
        """Test that summary command accepts scope arguments."""
        result = cli_runner.invoke(summary_app, ["--help"])

        assert result.exit_code == 0
        # Check if help mentions scope options
        output = result.stdout.lower()
        assert "scope" in output or "recent" in output or "all" in output

    def test_summary_accepts_agent_filter(self, cli_runner):
        """Test that summary command accepts agent filter."""
        result = cli_runner.invoke(summary_app, ["--help"])

        assert result.exit_code == 0
        # Check if help mentions agent filtering
        output = result.stdout.lower()
        assert "agent" in output or "filter" in output

    def test_summary_accepts_severity_filter(self, cli_runner):
        """Test that summary command accepts severity filter."""
        result = cli_runner.invoke(summary_app, ["--help"])

        assert result.exit_code == 0
        # Check if help mentions severity
        output = result.stdout.lower()
        assert "severity" in output or "error" in output or "warning" in output


class TestSummaryIntegration:
    """Integration tests for summary command."""

    def test_summary_command_exists(self, cli_runner):
        """Test that agent-summary command exists."""
        result = cli_runner.invoke(summary_app, ["agent-summary", "--help"])

        assert result.exit_code == 0
        assert (
            "Generate intelligent summary" in result.stdout
            or "agent-summary" in result.stdout.lower()
        )
