"""Tests for Beads integration."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from devloop.core.pattern_detector import DetectedPattern
from devloop.integrations.beads_integration import (
    BeadsIntegration,
    BeadsIssue,
    create_issues_from_patterns,
)


@pytest.fixture
def sample_pattern():
    """Create a sample detected pattern for testing."""
    return DetectedPattern(
        timestamp="2025-12-13T10:00:00Z",
        pattern_name="user_manual_fix_after_agent",
        severity="warning",
        message="User manually fixed code after agent ran",
        evidence={
            "occurrences": 3,
            "threads": ["T-abc123", "T-def456", "T-ghi789"],
            "file_types": ["*.py"],
        },
        confidence=0.85,
        recommendation="Improve agent auto-fix capabilities for Python files",
        affected_threads=["T-abc123", "T-def456", "T-ghi789"],
        acknowledged=False,
    )


@pytest.fixture
def beads_integration(tmp_path):
    """Create BeadsIntegration instance with temp directory."""
    return BeadsIntegration(devloop_dir=tmp_path, dry_run=False)


@pytest.fixture
def beads_integration_dry_run(tmp_path):
    """Create BeadsIntegration instance in dry-run mode."""
    return BeadsIntegration(devloop_dir=tmp_path, dry_run=True)


class TestBeadsIntegration:
    """Test BeadsIntegration class."""

    def test_init_default(self, tmp_path):
        """Test initialization with default settings."""
        integration = BeadsIntegration(devloop_dir=tmp_path)
        assert integration.parent_issue == "claude-agents-zjf"
        assert integration.dry_run is False
        assert integration.pattern_detector is not None

    def test_init_custom_parent(self, tmp_path):
        """Test initialization with custom parent issue."""
        integration = BeadsIntegration(
            devloop_dir=tmp_path,
            parent_issue="custom-parent-123",
        )
        assert integration.parent_issue == "custom-parent-123"

    def test_severity_to_priority(self, beads_integration):
        """Test severity to priority conversion."""
        assert beads_integration._severity_to_priority("error") == 1
        assert beads_integration._severity_to_priority("warning") == 2
        assert beads_integration._severity_to_priority("info") == 3
        assert beads_integration._severity_to_priority("unknown") == 2  # default

    def test_format_description(self, beads_integration, sample_pattern):
        """Test description formatting with thread references."""
        description = beads_integration._format_description(sample_pattern)

        # Check key components
        assert "Pattern Detected: user_manual_fix_after_agent" in description
        assert sample_pattern.message in description
        assert "**Severity**: warning" in description
        assert "**Confidence**: 85.00%" in description

        # Check thread references
        assert "**Affected Threads**:" in description
        assert "- T-abc123" in description
        assert "- T-def456" in description
        assert "- T-ghi789" in description

        # Check evidence
        assert "**Evidence**:" in description
        assert "```json" in description
        assert '"occurrences": 3' in description

        # Check recommendation
        assert "**Recommendation**:" in description
        assert sample_pattern.recommendation in description

        # Check metadata
        assert "Auto-generated from pattern detection" in description
        assert sample_pattern.timestamp in description

    def test_format_description_minimal(self, beads_integration):
        """Test description formatting with minimal pattern data."""
        minimal_pattern = DetectedPattern(
            pattern_name="test_pattern",
            severity="info",
            message="Test message",
            confidence=0.5,
        )

        description = beads_integration._format_description(minimal_pattern)

        assert "Pattern Detected: test_pattern" in description
        assert "Test message" in description
        assert "**Severity**: info" in description
        assert "**Confidence**: 50.00%" in description

    @patch("devloop.integrations.beads_integration.subprocess.run")
    def test_run_bd_create_success(self, mock_run, beads_integration):
        """Test successful bd create command."""
        # Mock successful subprocess call
        mock_result = Mock()
        mock_result.stdout = json.dumps({"id": "claude-agents-abc"})
        mock_run.return_value = mock_result

        result = beads_integration._run_bd_create(
            title="Test Issue",
            description="Test description",
            priority=2,
            issue_type="task",
            deps=["discovered-from:claude-agents-zjf"],
        )

        assert result is not None
        assert result.issue_id == "claude-agents-abc"
        assert result.title == "Test Issue"
        assert result.priority == 2
        assert result.issue_type == "task"

        # Verify command was called correctly
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "bd"
        assert cmd[1] == "create"
        assert "Test Issue" in cmd
        assert "--json" in cmd
        assert "--deps" in cmd

    @patch("devloop.integrations.beads_integration.subprocess.run")
    def test_run_bd_create_subprocess_error(self, mock_run, beads_integration):
        """Test bd create command with subprocess error."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "bd", stderr="Error creating issue"
        )

        result = beads_integration._run_bd_create(
            title="Test Issue",
            description="Test description",
            priority=2,
            issue_type="task",
            deps=[],
        )

        assert result is None

    @patch("devloop.integrations.beads_integration.subprocess.run")
    def test_run_bd_create_json_error(self, mock_run, beads_integration):
        """Test bd create command with invalid JSON response."""
        mock_result = Mock()
        mock_result.stdout = "invalid json"
        mock_run.return_value = mock_result

        result = beads_integration._run_bd_create(
            title="Test Issue",
            description="Test description",
            priority=2,
            issue_type="task",
            deps=[],
        )

        assert result is None

    def test_create_issue_from_pattern_dry_run(
        self, beads_integration_dry_run, sample_pattern
    ):
        """Test creating issue in dry-run mode."""
        result = beads_integration_dry_run.create_issue_from_pattern(sample_pattern)

        assert result is not None
        assert result.issue_id == "bd-dry-run"
        assert result.title == "Pattern: user_manual_fix_after_agent"
        assert result.priority == 2  # warning severity
        assert "discovered-from:claude-agents-zjf" in result.dependencies

    @patch("devloop.integrations.beads_integration.subprocess.run")
    def test_create_issue_from_pattern_success(
        self, mock_run, beads_integration, sample_pattern
    ):
        """Test creating issue from pattern successfully."""
        mock_result = Mock()
        mock_result.stdout = json.dumps({"id": "claude-agents-new"})
        mock_run.return_value = mock_result

        result = beads_integration.create_issue_from_pattern(sample_pattern)

        assert result is not None
        assert result.issue_id == "claude-agents-new"
        assert result.title == "Pattern: user_manual_fix_after_agent"
        assert "discovered-from:claude-agents-zjf" in result.dependencies

    @patch("devloop.integrations.beads_integration.subprocess.run")
    def test_create_issue_from_pattern_with_additional_deps(
        self, mock_run, beads_integration, sample_pattern
    ):
        """Test creating issue with additional dependencies."""
        mock_result = Mock()
        mock_result.stdout = json.dumps({"id": "claude-agents-new"})
        mock_run.return_value = mock_result

        result = beads_integration.create_issue_from_pattern(
            sample_pattern,
            additional_deps=["blocks:claude-agents-123"],
        )

        assert result is not None
        assert "discovered-from:claude-agents-zjf" in result.dependencies
        assert "blocks:claude-agents-123" in result.dependencies

    @patch("devloop.integrations.beads_integration.subprocess.run")
    def test_create_issue_from_pattern_error_severity(
        self, mock_run, beads_integration
    ):
        """Test priority mapping for error severity."""
        mock_result = Mock()
        mock_result.stdout = json.dumps({"id": "claude-agents-err"})
        mock_run.return_value = mock_result

        error_pattern = DetectedPattern(
            pattern_name="critical_error",
            severity="error",
            message="Critical error detected",
            confidence=0.9,
        )

        result = beads_integration.create_issue_from_pattern(error_pattern)

        assert result is not None
        assert result.priority == 1  # error severity = P1

    @patch.object(BeadsIntegration, "create_issue_from_pattern")
    def test_auto_create_from_high_confidence_patterns(
        self, mock_create, beads_integration, sample_pattern, tmp_path
    ):
        """Test auto-creating issues from high-confidence patterns."""
        # Mock pattern detector to return sample patterns
        high_conf_pattern = sample_pattern
        acknowledged_pattern = DetectedPattern(
            pattern_name="acknowledged_pattern",
            severity="info",
            message="Already handled",
            confidence=0.9,
            acknowledged=True,
        )

        beads_integration.pattern_detector.get_high_confidence_patterns = Mock(
            return_value=[high_conf_pattern, acknowledged_pattern]
        )

        # Mock successful issue creation
        mock_create.return_value = BeadsIssue(
            issue_id="claude-agents-auto",
            title="Pattern: user_manual_fix_after_agent",
            description="Test",
            priority=2,
            issue_type="task",
            dependencies=["discovered-from:claude-agents-zjf"],
        )

        result = beads_integration.auto_create_from_high_confidence_patterns(
            confidence_threshold=0.7,
            limit=10,
        )

        # Should only create issue for non-acknowledged pattern
        assert len(result) == 1
        assert mock_create.call_count == 1
        mock_create.assert_called_with(high_conf_pattern)

    @patch.object(BeadsIntegration, "create_issue_from_pattern")
    def test_auto_create_no_patterns(self, mock_create, beads_integration):
        """Test auto-create when no patterns are found."""
        beads_integration.pattern_detector.get_high_confidence_patterns = Mock(
            return_value=[]
        )

        result = beads_integration.auto_create_from_high_confidence_patterns()

        assert len(result) == 0
        mock_create.assert_not_called()


class TestConvenienceFunction:
    """Test convenience function."""

    @patch.object(BeadsIntegration, "auto_create_from_high_confidence_patterns")
    def test_create_issues_from_patterns(self, mock_auto_create):
        """Test convenience function delegates correctly."""
        mock_auto_create.return_value = [
            BeadsIssue(
                issue_id="test-123",
                title="Test",
                description="Test",
                priority=2,
                issue_type="task",
                dependencies=[],
            )
        ]

        result = create_issues_from_patterns(
            confidence_threshold=0.8,
            limit=5,
            parent_issue="custom-parent",
            dry_run=True,
        )

        assert len(result) == 1
        mock_auto_create.assert_called_once_with(
            confidence_threshold=0.8,
            limit=5,
        )

    @patch.object(BeadsIntegration, "auto_create_from_high_confidence_patterns")
    def test_create_issues_from_patterns_defaults(self, mock_auto_create):
        """Test convenience function with default arguments."""
        mock_auto_create.return_value = []

        result = create_issues_from_patterns()

        assert len(result) == 0
        mock_auto_create.assert_called_once_with(
            confidence_threshold=0.7,
            limit=10,
        )
