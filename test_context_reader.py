#!/usr/bin/env python3
"""Test the context reader functionality."""

import json
import tempfile
from pathlib import Path

from src.devloop.core.context import ContextStore, Finding
from src.devloop.core.context_reader import ContextReader


def test_context_reader():
    """Test context reader operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        context_path = Path(temp_dir) / "context"
        store = ContextStore(context_path)
        reader = ContextReader(context_path)

        # Store some test findings
        findings = [
            Finding(
                agent_name="linter",
                file_path="app.py",
                line_number=5,
                severity="error",
                message="Syntax error",
                rule_id="syntax-error",
            ),
            Finding(
                agent_name="linter",
                file_path="utils.py",
                severity="warning",
                message="Unused variable",
                rule_id="unused-var",
            ),
            Finding(
                agent_name="formatter",
                file_path="app.py",
                severity="info",
                message="Needs formatting",
                rule_id="format-black",
            ),
        ]

        store.store_findings("linter", findings[:2])
        store.store_findings("formatter", findings[2:])

        # Test reading all findings
        all_findings = reader.get_all_findings()
        assert "linter" in all_findings
        assert "formatter" in all_findings

        # Linter has findings for 2 files
        linter_files = all_findings["linter"]
        assert len(linter_files) == 2
        total_linter_findings = sum(len(ff.findings) for ff in linter_files)
        assert total_linter_findings == 2

        # Formatter has findings for 1 file
        formatter_files = all_findings["formatter"]
        assert len(formatter_files) == 1
        assert len(formatter_files[0].findings) == 1

        # Test reading specific agent
        linter_findings = reader.get_agent_findings("linter")
        assert len(linter_findings) == 2  # Should have 2 files

        # Test file-specific findings
        app_findings = reader.get_file_findings("app.py")
        assert "linter" in app_findings
        assert "formatter" in app_findings

        # Test summary
        summary = reader.get_summary()
        assert summary["linter"]["error"] == 1
        assert summary["linter"]["warning"] == 1
        assert summary["formatter"]["info"] == 1

        # Test has_findings
        assert reader.has_findings()
        assert reader.has_findings("linter")
        assert not reader.has_findings("nonexistent")

        print("✅ Context reader tests passed")


if __name__ == "__main__":
    print("🧪 Testing Context Reader")
    test_context_reader()
    print("✅ All context reader tests passed!")
