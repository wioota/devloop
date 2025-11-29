#!/usr/bin/env python3
"""Integration test for context store with real agents."""

import asyncio
import tempfile
from pathlib import Path

from src.devloop.agents.linter import LinterAgent
from src.devloop.core.context_reader import ContextReader
from src.devloop.core.event import Event


async def test_agent_context_integration():
    """Test that agents write findings to context store."""
    # Create a test file with linting issues
    test_file_content = '''
import os
x = 1  # unused variable
print("hello")
'''

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text(test_file_content)

        # Create context directory
        context_dir = Path(temp_dir) / ".claude" / "context"
        context_dir.mkdir(parents=True, exist_ok=True)

        # Create linter agent with context store path
        from src.devloop.core.context import context_store
        # Temporarily change context store path
        original_path = context_store.base_path
        context_store.base_path = context_dir

        try:
            # Create and run linter agent
            agent = LinterAgent(
                name="linter",
                triggers=["file:modified"],
                event_bus=None,  # Not needed for this test
            )

            # Create a mock event
            event = Event(
                type="file:modified",
                payload={"path": str(test_file)},
            )

            # Run the agent
            result = await agent.handle(event)

            # Check that findings were stored
            reader = ContextReader(context_dir)
            findings = reader.get_agent_findings("linter")

            # Should have found some issues
            total_findings = sum(len(ff.findings) for ff in findings)
            assert total_findings > 0, "Should have found linting issues"

            # Verify the finding details
            assert len(findings) == 1
            assert findings[0].file_path == str(test_file)
            assert len(findings[0].findings) == 1
            finding = findings[0].findings[0]
            assert finding.severity == "error"
            assert "unused" in finding.message.lower()
            assert finding.rule_id == "F401"

            print("✅ Agent context integration test passed")

        finally:
            # Restore original path
            context_store.base_path = original_path


if __name__ == "__main__":
    print("🧪 Testing Agent Context Integration")
    asyncio.run(test_agent_context_integration())
    print("✅ All integration tests passed!")
