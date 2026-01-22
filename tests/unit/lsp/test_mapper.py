"""Tests for LSP Finding to Diagnostic mapper."""

from datetime import datetime

import pytest
from lsprotocol.types import (
    Diagnostic,
    DiagnosticSeverity,
    Position,
    Range,
)

from devloop.core.context_store import Finding, Severity
from devloop.lsp.mapper import FindingMapper


def _make_finding(**kwargs):
    """Helper to create a Finding with default timestamp."""
    if "timestamp" not in kwargs:
        kwargs["timestamp"] = datetime.now().isoformat()
    return Finding(**kwargs)


class TestFindingMapper:
    """Tests for FindingMapper class."""

    def test_to_diagnostic_basic(self):
        """Test converting a basic finding to diagnostic."""
        finding = _make_finding(
            id="test-123",
            agent="linter",
            category="style",
            severity=Severity.WARNING,
            message="Line too long",
            file="/path/to/file.py",
            line=10,
            column=5,
        )

        diagnostic = FindingMapper.to_diagnostic(finding)

        assert diagnostic is not None
        assert diagnostic.message == "Line too long"
        assert diagnostic.severity == DiagnosticSeverity.Warning
        assert diagnostic.code == "style"
        assert diagnostic.source == "devloop:linter"
        assert diagnostic.range.start.line == 9  # 0-indexed
        assert diagnostic.range.start.character == 4  # 0-indexed

    def test_to_diagnostic_with_suggestion(self):
        """Test diagnostic includes suggestion in message."""
        finding = _make_finding(
            id="test-456",
            agent="formatter",
            category="format",
            severity=Severity.INFO,
            message="Missing blank line",
            suggestion="Add blank line after import",
            file="/path/to/file.py",
            line=5,
        )

        diagnostic = FindingMapper.to_diagnostic(finding)

        assert diagnostic is not None
        assert "Missing blank line" in diagnostic.message
        assert "💡 Suggestion: Add blank line after import" in diagnostic.message

    def test_to_diagnostic_with_detail(self):
        """Test diagnostic includes detail in related information."""
        finding = _make_finding(
            id="test-789",
            agent="type_checker",
            category="type",
            severity=Severity.ERROR,
            message="Type mismatch",
            detail="Expected 'str' but got 'int'",
            file="/path/to/file.py",
            line=20,
        )

        diagnostic = FindingMapper.to_diagnostic(finding)

        assert diagnostic is not None
        assert diagnostic.related_information is not None
        assert len(diagnostic.related_information) == 1
        assert (
            diagnostic.related_information[0].message == "Expected 'str' but got 'int'"
        )

    def test_to_diagnostic_without_location_returns_none(self):
        """Test that findings without line number return None."""
        finding = _make_finding(
            id="test-000",
            agent="security",
            category="security",
            severity=Severity.ERROR,
            message="Security issue",
            file="/path/to/file.py",
            line=None,  # No line number
        )

        diagnostic = FindingMapper.to_diagnostic(finding)
        assert diagnostic is None

    def test_to_diagnostic_without_column(self):
        """Test diagnostic handles missing column number."""
        finding = _make_finding(
            id="test-111",
            agent="linter",
            category="style",
            severity=Severity.WARNING,
            message="Issue",
            file="/path/to/file.py",
            line=15,
            column=None,
        )

        diagnostic = FindingMapper.to_diagnostic(finding)

        assert diagnostic is not None
        assert diagnostic.range.start.character == 0  # Default to 0

    def test_to_diagnostic_custom_data(self):
        """Test diagnostic includes custom data for code actions."""
        finding = _make_finding(
            id="test-222",
            agent="formatter",
            category="format",
            severity=Severity.INFO,
            message="Auto-fixable",
            file="/path/to/file.py",
            line=1,
            auto_fixable=True,
            fix_command="black {file}",
            blocking=False,
        )

        diagnostic = FindingMapper.to_diagnostic(finding)

        assert diagnostic is not None
        assert diagnostic.data is not None
        assert diagnostic.data["finding_id"] == "test-222"
        assert diagnostic.data["auto_fixable"] is True
        assert diagnostic.data["fix_command"] == "black {file}"
        assert diagnostic.data["agent"] == "formatter"
        assert diagnostic.data["blocking"] is False

    def test_severity_mapping(self):
        """Test all severity levels map correctly."""
        severity_tests = [
            (Severity.ERROR, DiagnosticSeverity.Error),
            (Severity.WARNING, DiagnosticSeverity.Warning),
            (Severity.INFO, DiagnosticSeverity.Information),
            (Severity.STYLE, DiagnosticSeverity.Hint),
        ]

        for finding_severity, expected_diagnostic_severity in severity_tests:
            finding = _make_finding(
                id=f"test-{finding_severity.value}",
                agent="test",
                category="test",
                severity=finding_severity,
                message="Test",
                file="/test.py",
                line=1,
            )

            diagnostic = FindingMapper.to_diagnostic(finding)
            assert diagnostic is not None
            assert diagnostic.severity == expected_diagnostic_severity

    def test_to_diagnostics_multiple_findings(self):
        """Test converting multiple findings to diagnostics."""
        findings = [
            _make_finding(
                id="f1",
                agent="linter",
                category="style",
                severity=Severity.WARNING,
                message="Issue 1",
                file="/test.py",
                line=1,
            ),
            _make_finding(
                id="f2",
                agent="linter",
                category="style",
                severity=Severity.ERROR,
                message="Issue 2",
                file="/test.py",
                line=2,
            ),
            _make_finding(
                id="f3",
                agent="linter",
                category="style",
                severity=Severity.INFO,
                message="Issue 3 (no line)",
                file="/test.py",
                line=None,  # Should be excluded
            ),
        ]

        diagnostics = FindingMapper.to_diagnostics(findings)

        # Only 2 diagnostics (third excluded due to no line)
        assert len(diagnostics) == 2
        assert all(isinstance(d, Diagnostic) for d in diagnostics)
        assert diagnostics[0].message == "Issue 1"
        assert diagnostics[1].message == "Issue 2"

    def test_to_diagnostics_empty_list(self):
        """Test converting empty list returns empty list."""
        diagnostics = FindingMapper.to_diagnostics([])
        assert diagnostics == []

    def test_group_by_file(self):
        """Test grouping findings by file path."""
        findings = [
            _make_finding(
                id="f1",
                agent="linter",
                category="style",
                severity=Severity.WARNING,
                message="Issue 1",
                file="/path/file1.py",
                line=1,
            ),
            _make_finding(
                id="f2",
                agent="linter",
                category="style",
                severity=Severity.WARNING,
                message="Issue 2",
                file="/path/file2.py",
                line=1,
            ),
            _make_finding(
                id="f3",
                agent="linter",
                category="style",
                severity=Severity.WARNING,
                message="Issue 3",
                file="/path/file1.py",  # Same as f1
                line=2,
            ),
        ]

        grouped = FindingMapper.group_by_file(findings)

        assert len(grouped) == 2
        assert "/path/file1.py" in grouped
        assert "/path/file2.py" in grouped
        assert len(grouped["/path/file1.py"]) == 2
        assert len(grouped["/path/file2.py"]) == 1

    def test_group_by_file_multiple_files(self):
        """Test grouping with multiple files."""
        findings = [
            _make_finding(
                id="f1",
                agent="linter",
                category="style",
                severity=Severity.WARNING,
                message="Issue 1",
                file="/path/file1.py",
                line=1,
            ),
            _make_finding(
                id="f2",
                agent="linter",
                category="style",
                severity=Severity.WARNING,
                message="Issue 2",
                file="/path/file2.py",
                line=1,
            ),
            _make_finding(
                id="f3",
                agent="linter",
                category="style",
                severity=Severity.WARNING,
                message="Issue 3",
                file="/path/file1.py",
                line=2,
            ),
        ]

        grouped = FindingMapper.group_by_file(findings)

        assert len(grouped) == 2
        assert "/path/file1.py" in grouped
        assert "/path/file2.py" in grouped
        assert len(grouped["/path/file1.py"]) == 2
        assert len(grouped["/path/file2.py"]) == 1

    def test_group_by_file_empty_list(self):
        """Test grouping empty list returns empty dict."""
        grouped = FindingMapper.group_by_file([])
        assert grouped == {}

    def test_diagnostic_range_calculation(self):
        """Test diagnostic range calculation for edge cases."""
        # Test line 0 (should stay 0, not go negative)
        finding = _make_finding(
            id="test",
            agent="test",
            category="test",
            severity=Severity.INFO,
            message="Test",
            file="/test.py",
            line=1,  # Will be 0 after conversion
            column=1,
        )

        diagnostic = FindingMapper.to_diagnostic(finding)
        assert diagnostic is not None
        assert diagnostic.range.start.line == 0
        assert diagnostic.range.start.character == 0

        # Test range spans single character
        assert diagnostic.range.end.line == diagnostic.range.start.line
        assert diagnostic.range.end.character == diagnostic.range.start.character + 1
