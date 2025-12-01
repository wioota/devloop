#!/usr/bin/env python3
"""Demo script showing the context store integration with devloop."""

import asyncio
import tempfile
from pathlib import Path

from src.devloop.core.context_reader import ContextReader, get_context_summary
from src.devloop.core.event import Event


async def demo_context_store():
    """Demonstrate context store functionality."""
    print("🔍 Dev-Agents Context Store Demo")
    print("=" * 40)

    # Create a test file with issues
    test_code = '''import os  # unused import
import json

def hello():
    x = 1  # unused variable
    print("Hello World")

class MyClass:
    def __init__(self):
        self.value = 42
'''

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "demo.py"
        test_file.write_text(test_code)

        print(f"📄 Created test file: {test_file}")
        print(f"📄 File contents:")
        print(test_code)
        print()

        # Start devloop watching this file
        print("🚀 Starting devloop to analyze the file...")

        # Import here to avoid circular imports
        from src.devloop.core.context import context_store
        from src.devloop.agents.linter import LinterAgent

        # Temporarily change context store path for demo
        original_path = context_store.base_path
        new_path = Path(temp_dir) / ".claude" / "context"
        new_path.mkdir(parents=True, exist_ok=True)
        context_store.base_path = new_path

        try:
            # Create and run linter agent
            agent = LinterAgent(
                name="linter",
                triggers=["file:modified"],
                event_bus=None,
            )

            event = Event(
                type="file:modified",
                payload={"path": str(test_file)},
            )

            print("🔍 Running linter agent...")
            result = await agent.handle(event)
            print(f"📊 Agent result: {result.message}")

            # Read findings from context store
            print("\n📋 Findings stored in context:")
            reader = ContextReader(context_store.base_path)
            findings = reader.get_agent_findings("linter")

            if findings:
                for file_findings in findings:
                    print(f"📁 File: {file_findings.file_path}")
                    for finding in file_findings.findings:
                        print(f"   {finding.severity.upper()}: {finding.message}")
                        if finding.line_number:
                            print(f"   📍 Line {finding.line_number}: {finding.rule_id}")
                        print()
            else:
                print("❌ No findings stored")

            # Show summary
            print("📈 Summary of all findings:")
            summary = reader.get_summary()
            for agent_name, agent_summary in summary.items():
                print(f"🤖 {agent_name}:")
                for severity, count in agent_summary.items():
                    if count > 0:
                        print(f"   {severity}: {count}")

            print("\n✅ Context store demo completed successfully!")

        finally:
            # Restore original path
            context_store.base_path = original_path


if __name__ == "__main__":
    asyncio.run(demo_context_store())
