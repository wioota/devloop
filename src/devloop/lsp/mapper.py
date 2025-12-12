"""Maps DevLoop Finding objects to LSP Diagnostic objects."""

from typing import List, Optional

from lsprotocol.types import (
    Diagnostic,
    DiagnosticRelatedInformation,
    DiagnosticSeverity,
    Location,
    Position,
    Range,
)

from devloop.core.context_store import Finding, Severity


class FindingMapper:
    """Maps Finding objects to LSP Diagnostics."""

    # Severity mapping
    SEVERITY_MAP = {
        Severity.ERROR: DiagnosticSeverity.Error,
        Severity.WARNING: DiagnosticSeverity.Warning,
        Severity.INFO: DiagnosticSeverity.Information,
        Severity.STYLE: DiagnosticSeverity.Hint,
    }

    @classmethod
    def to_diagnostic(cls, finding: Finding) -> Optional[Diagnostic]:
        """Convert a Finding to an LSP Diagnostic.

        Args:
            finding: The Finding object to convert

        Returns:
            LSP Diagnostic or None if finding has no location
        """
        # Findings without location can't be shown as diagnostics
        if finding.line is None:
            return None

        # Create position range
        start_line = max(0, finding.line - 1)  # LSP is 0-indexed
        start_char = finding.column - 1 if finding.column else 0
        end_char = start_char + 1  # Default to single character

        diagnostic_range = Range(
            start=Position(line=start_line, character=start_char),
            end=Position(line=start_line, character=end_char),
        )

        # Map severity
        severity = cls.SEVERITY_MAP.get(
            finding.severity, DiagnosticSeverity.Information
        )

        # Build message
        message = finding.message
        if finding.suggestion:
            message += f"\n\n💡 Suggestion: {finding.suggestion}"

        # Build related information
        related_info: List[DiagnosticRelatedInformation] = []
        if finding.detail:
            # Related info could point to the same location with detail
            related_info.append(
                DiagnosticRelatedInformation(
                    location=Location(
                        uri=f"file://{finding.file}",
                        range=diagnostic_range,
                    ),
                    message=finding.detail,
                )
            )

        # Build diagnostic
        diagnostic = Diagnostic(
            range=diagnostic_range,
            severity=severity,
            code=finding.category,
            source=f"devloop:{finding.agent}",
            message=message,
            related_information=related_info if related_info else None,
        )

        # Add custom data for code actions
        diagnostic.data = {
            "finding_id": finding.id,
            "auto_fixable": finding.auto_fixable,
            "fix_command": finding.fix_command,
            "agent": finding.agent,
            "blocking": finding.blocking,
        }

        return diagnostic

    @classmethod
    def to_diagnostics(cls, findings: List[Finding]) -> List[Diagnostic]:
        """Convert multiple Findings to LSP Diagnostics.

        Args:
            findings: List of Finding objects

        Returns:
            List of LSP Diagnostics (excludes findings without location)
        """
        diagnostics = []
        for finding in findings:
            diagnostic = cls.to_diagnostic(finding)
            if diagnostic:
                diagnostics.append(diagnostic)
        return diagnostics

    @classmethod
    def group_by_file(cls, findings: List[Finding]) -> dict[str, List[Finding]]:
        """Group findings by file path.

        Args:
            findings: List of Finding objects

        Returns:
            Dictionary mapping file paths to lists of findings
        """
        grouped = {}
        for finding in findings:
            if finding.file:
                if finding.file not in grouped:
                    grouped[finding.file] = []
                grouped[finding.file].append(finding)
        return grouped
