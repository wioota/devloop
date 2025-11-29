#!/usr/bin/env python3
"""Test the context store functionality."""

import json
import tempfile
from pathlib import Path

from src.devloop.core.context import ContextStore, Finding


def test_context_store():
    """Test basic context store operations."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        context_path = Path(temp_dir) / "context"
        store = ContextStore(context_path)

        # Test storing findings
        findings = [
            Finding(
                agent_name="linter",
                file_path="test.py",
                line_number=10,
                severity="error",
                message="Undefined variable 'x'",
                rule_id="undefined-variable",
            ),
            Finding(
                agent_name="linter",
                file_path="test.py",
                line_number=15,
                severity="warning",
                message="Unused import",
                rule_id="unused-import",
            ),
        ]

        store.store_findings("linter", findings)

        # Test retrieving findings
        retrieved = store.get_findings("linter")
        assert len(retrieved) == 1
        assert retrieved[0].file_path == "test.py"
        assert len(retrieved[0].findings) == 2

        # Test JSON file was created
        linter_file = context_path / "linter.json"
        assert linter_file.exists()

        # Test JSON content
        with open(linter_file) as f:
            data = json.load(f)
            assert data["agent_name"] == "linter"
            assert len(data["files"]) == 1
            assert data["files"][0]["file_path"] == "test.py"
            assert len(data["files"][0]["findings"]) == 2

        print("✅ Context store basic operations test passed")


def test_clear_findings():
    """Test clearing findings."""
    with tempfile.TemporaryDirectory() as temp_dir:
        context_path = Path(temp_dir) / "context"
        store = ContextStore(context_path)

        # Store some findings
        findings = [
            Finding(
                agent_name="formatter",
                file_path="main.py",
                severity="info",
                message="File needs formatting",
            ),
        ]
        store.store_findings("formatter", findings)

        # Verify they exist
        retrieved = store.get_findings("formatter")
        assert len(retrieved) == 1

        # Clear all findings for formatter
        store.clear_findings("formatter")

        # Verify they're gone
        retrieved = store.get_findings("formatter")
        assert len(retrieved) == 0

        # File should be gone
        formatter_file = context_path / "formatter.json"
        assert not formatter_file.exists()

        print("✅ Clear findings test passed")


def test_get_all_agents():
    """Test getting list of all agents with findings."""
    with tempfile.TemporaryDirectory() as temp_dir:
        context_path = Path(temp_dir) / "context"
        store = ContextStore(context_path)

        # Store findings for multiple agents
        store.store_findings("linter", [Finding(agent_name="linter", file_path="a.py", severity="error", message="test")])
        store.store_findings("formatter", [Finding(agent_name="formatter", file_path="b.py", severity="warning", message="test")])

        agents = store.get_all_agents()
        assert set(agents) == {"linter", "formatter"}

        print("✅ Get all agents test passed")


if __name__ == "__main__":
    print("🧪 Testing Context Store")
    test_context_store()
    test_clear_findings()
    test_get_all_agents()
    print("✅ All context store tests passed!")
