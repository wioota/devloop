"""Tests for insights CLI command."""

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from devloop.cli.commands.insights import (
    _format_evidence,
    _format_threads,
    _severity_style,
    app,
)
from devloop.core.pattern_detector import DetectedPattern

runner = CliRunner()


class TestFormatHelpers:
    """Tests for formatting helper functions."""

    def test_format_threads_empty(self):
        """Test formatting empty thread list."""
        assert _format_threads([]) == "-"

    def test_format_threads_single(self):
        """Test formatting single thread."""
        assert _format_threads(["T-123"]) == "T-123"

    def test_format_threads_multiple(self):
        """Test formatting multiple threads."""
        assert _format_threads(["T-1", "T-2", "T-3"]) == "T-1, T-2, T-3"

    def test_format_threads_truncated(self):
        """Test formatting too many threads."""
        threads = ["T-1", "T-2", "T-3", "T-4", "T-5"]
        result = _format_threads(threads, max_display=3)
        assert result == "T-1, T-2, T-3 (+2 more)"

    def test_format_evidence_empty(self):
        """Test formatting empty evidence."""
        assert _format_evidence({}) == "-"

    def test_format_evidence_basic(self):
        """Test formatting basic evidence."""
        evidence = {"command": "test", "occurrences": 5}
        result = _format_evidence(evidence)
        assert "command: test" in result
        assert "occurrences: 5" in result

    def test_format_evidence_skips_examples(self):
        """Test that examples are skipped in evidence formatting."""
        evidence = {"command": "test", "examples": ["a", "b"]}
        result = _format_evidence(evidence)
        assert "examples" not in result

    def test_severity_style_error(self):
        """Test severity style for error."""
        assert _severity_style("error") == "red bold"

    def test_severity_style_warning(self):
        """Test severity style for warning."""
        assert _severity_style("warning") == "yellow"

    def test_severity_style_info(self):
        """Test severity style for info."""
        assert _severity_style("info") == "blue"

    def test_severity_style_unknown(self):
        """Test severity style for unknown severity."""
        assert _severity_style("unknown") == "white"


class TestListPatterns:
    """Tests for list_patterns command."""

    @pytest.fixture
    def mock_detector(self):
        """Create mock pattern detector."""
        detector = Mock()
        detector.get_recent_patterns.return_value = []
        detector.get_patterns_by_type.return_value = []
        detector.get_patterns_for_thread.return_value = []
        return detector

    @pytest.fixture
    def sample_pattern(self):
        """Create sample detected pattern."""
        return DetectedPattern(
            pattern_name="command_repetition",
            severity="info",
            message="Command 'test' executed 5 times",
            evidence={"command": "test", "occurrences": 5},
            confidence=0.8,
            recommendation="Consider automating",
            affected_threads=["T-1", "T-2"],
        )

    def test_list_patterns_no_results(self, mock_detector):
        """Test list_patterns with no results."""
        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "No patterns detected" in result.output

    def test_list_patterns_with_results(self, mock_detector, sample_pattern):
        """Test list_patterns with results."""
        mock_detector.get_recent_patterns.return_value = [sample_pattern]

        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "command_repetition" in result.output

    def test_list_patterns_severity_filter(self, mock_detector, sample_pattern):
        """Test list_patterns with severity filter."""
        mock_detector.get_recent_patterns.return_value = [sample_pattern]

        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["list", "--severity", "info"])
            assert result.exit_code == 0
            mock_detector.get_recent_patterns.assert_called_with(
                limit=50, severity="info"
            )

    def test_list_patterns_pattern_filter(self, mock_detector, sample_pattern):
        """Test list_patterns with pattern filter."""
        mock_detector.get_patterns_by_type.return_value = [sample_pattern]

        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["list", "--pattern", "command_repetition"])
            assert result.exit_code == 0
            mock_detector.get_patterns_by_type.assert_called_with("command_repetition")

    def test_list_patterns_thread_filter(self, mock_detector, sample_pattern):
        """Test list_patterns with thread filter."""
        mock_detector.get_patterns_for_thread.return_value = [sample_pattern]

        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["list", "--thread", "T-123"])
            assert result.exit_code == 0
            mock_detector.get_patterns_for_thread.assert_called_with("T-123")

    def test_list_patterns_json_format(self, mock_detector, sample_pattern):
        """Test list_patterns with JSON format."""
        mock_detector.get_recent_patterns.return_value = [sample_pattern]

        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["list", "--format", "json"])
            assert result.exit_code == 0
            assert '"pattern_name": "command_repetition"' in result.output

    def test_list_patterns_detailed_format(self, mock_detector, sample_pattern):
        """Test list_patterns with detailed format."""
        mock_detector.get_recent_patterns.return_value = [sample_pattern]

        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["list", "--format", "detailed"])
            assert result.exit_code == 0
            assert "Recommendation:" in result.output

    def test_list_patterns_min_confidence(self, mock_detector, sample_pattern):
        """Test list_patterns with min_confidence filter."""
        low_conf = DetectedPattern(
            pattern_name="low_conf",
            severity="info",
            message="Low confidence",
            evidence={},
            confidence=0.3,
        )
        mock_detector.get_recent_patterns.return_value = [sample_pattern, low_conf]

        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["list", "--min-confidence", "0.5"])
            assert result.exit_code == 0
            # Should only show high confidence pattern
            assert "command_repetition" in result.output

    def test_list_patterns_error_handling(self, mock_detector):
        """Test list_patterns error handling."""
        mock_detector.get_recent_patterns.side_effect = Exception("Database error")

        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 1
            assert "Error" in result.output


class TestDetectPatterns:
    """Tests for detect_patterns command."""

    @pytest.fixture
    def mock_detector(self):
        """Create mock pattern detector."""
        detector = Mock()
        detector.detect_patterns.return_value = []
        return detector

    @pytest.fixture
    def sample_pattern(self):
        """Create sample detected pattern."""
        return DetectedPattern(
            pattern_name="command_repetition",
            severity="info",
            message="Command 'test' executed 5 times",
            evidence={},
            confidence=0.8,
        )

    def test_detect_patterns_no_results(self, mock_detector):
        """Test detect_patterns with no results."""
        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["detect"])
            assert result.exit_code == 0
            assert "No patterns detected" in result.output

    def test_detect_patterns_with_results(self, mock_detector, sample_pattern):
        """Test detect_patterns with results."""
        mock_detector.detect_patterns.return_value = [sample_pattern]

        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["detect"])
            assert result.exit_code == 0
            assert "command_repetition" in result.output

    def test_detect_patterns_custom_hours(self, mock_detector):
        """Test detect_patterns with custom hours."""
        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["detect", "--hours", "48"])
            assert result.exit_code == 0
            mock_detector.detect_patterns.assert_called_with(
                time_window_hours=48,
                min_occurrences=2,
                save_results=True,
            )

    def test_detect_patterns_no_save(self, mock_detector):
        """Test detect_patterns with save disabled."""
        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["detect", "--no-save"])
            assert result.exit_code == 0
            mock_detector.detect_patterns.assert_called_with(
                time_window_hours=24,
                min_occurrences=2,
                save_results=False,
            )

    def test_detect_patterns_error_handling(self, mock_detector):
        """Test detect_patterns error handling."""
        mock_detector.detect_patterns.side_effect = Exception("Analysis error")

        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["detect"])
            assert result.exit_code == 1
            assert "Error" in result.output


class TestPatternSummary:
    """Tests for pattern_summary command."""

    @pytest.fixture
    def mock_detector(self):
        """Create mock pattern detector."""
        detector = Mock()
        detector.get_recent_patterns.return_value = []
        return detector

    @pytest.fixture
    def sample_patterns(self):
        """Create sample detected patterns."""
        return [
            DetectedPattern(
                pattern_name="command_repetition",
                severity="info",
                message="Command 'test' executed 5 times",
                evidence={},
                confidence=0.8,
            ),
            DetectedPattern(
                pattern_name="command_repetition",
                severity="info",
                message="Command 'build' executed 3 times",
                evidence={},
                confidence=0.6,
            ),
            DetectedPattern(
                pattern_name="cross_thread_pattern",
                severity="warning",
                message="Pattern across threads",
                evidence={},
                confidence=0.7,
            ),
        ]

    def test_pattern_summary_no_results(self, mock_detector):
        """Test pattern_summary with no results."""
        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["summary"])
            assert result.exit_code == 0
            assert "No patterns recorded" in result.output

    def test_pattern_summary_with_results(self, mock_detector, sample_patterns):
        """Test pattern_summary with results."""
        mock_detector.get_recent_patterns.return_value = sample_patterns

        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["summary"])
            assert result.exit_code == 0
            assert "Pattern Summary" in result.output
            assert "By Severity" in result.output

    def test_pattern_summary_error_handling(self, mock_detector):
        """Test pattern_summary error handling."""
        mock_detector.get_recent_patterns.side_effect = Exception("Query error")

        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app, ["summary"])
            assert result.exit_code == 1
            assert "Error" in result.output


class TestDefaultCommand:
    """Tests for default command behavior."""

    @pytest.fixture
    def mock_detector(self):
        """Create mock pattern detector."""
        detector = Mock()
        detector.get_recent_patterns.return_value = []
        return detector

    def test_default_invokes_list(self, mock_detector):
        """Test that invoking without subcommand defaults to list."""
        with patch(
            "devloop.cli.commands.insights.get_pattern_detector",
            return_value=mock_detector,
        ):
            result = runner.invoke(app)
            assert result.exit_code == 0
            mock_detector.get_recent_patterns.assert_called()
