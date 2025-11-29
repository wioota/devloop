#!/usr/bin/env python3
"""
End-to-end test for agent findings pipeline

Tests:
1. Create a file with linting issues
2. Run linter agent on it
3. Verify findings are stored in context
"""

import asyncio
import json
import tempfile
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from devloop.core.context_store import context_store, Tier
from devloop.core.event import Event, EventBus
from devloop.core.manager import AgentManager
from devloop.agents.linter import LinterAgent


async def main():
    print("=" * 60)
    print("End-to-End Agent Findings Test")
    print("=" * 60)
    print()

    # Create event bus
    event_bus = EventBus()
    
    # Create agent manager
    manager = AgentManager(event_bus=event_bus)

    # Create linter agent through manager
    linter = manager.create_agent(
        LinterAgent,
        name="linter",
        triggers=["file:modify"],
        config={"enabled": True, "filePatterns": ["**/*.py"]},
    )

    # Initialize context store
    await context_store.initialize()
    
    # Create test file with linting issues
    print("Step 1: Creating test file with linting issues...")
    test_content = """import os
import sys
import json  # unused import


def test_function( x , y ):  # whitespace issues
    return x+y  # spacing


# Lines that are too long to demonstrate E501 violations in the code
x = 1
y = 2
z = x + y + "this is a very long string that will exceed the line length limit of 88 characters used by ruff"
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text(test_content)
        print(f"  Created: {test_file}")
        print()

        # Verify file exists and has content
        assert test_file.exists(), "Test file not created"
        print(f"  File size: {test_file.stat().st_size} bytes")
        print()

        # Step 2: Run linter agent
        print("Step 2: Running linter agent on test file...")
        event = Event(
            type="file:modify",
            source="test",
            payload={"path": str(test_file)},
        )

        # Call the agent directly (simulating what the event bus would do)
        result = await linter.handle(event)
        print(f"  Agent result: {result.message}")
        print(f"  Agent data: {result.data}")
        print()

        # Step 3: Check context store
        print("Step 3: Checking context store for findings...")
        
        # Clear any test findings from health check
        await context_store.clear_findings()
        
        # Re-run agent to create fresh findings
        result = await linter.handle(event)
        
        # Wait a bit for async operations to complete
        await asyncio.sleep(0.5)
        
        # Get findings from all tiers
        findings_by_tier = {}
        for tier in [Tier.IMMEDIATE, Tier.RELEVANT, Tier.BACKGROUND, Tier.AUTO_FIXED]:
            findings = await context_store.get_findings(tier=tier)
            findings_by_tier[tier.value] = findings
            print(f"  {tier.value}: {len(findings)} findings")

        # Get total count
        all_findings = await context_store.get_findings()
        print(f"  Total: {len(all_findings)} findings")
        print()

        # Step 4: Check index
        print("Step 4: Checking index...")
        index = await context_store.read_index()
        print(f"  Index last_updated: {index['last_updated']}")
        print(f"  check_now count: {index['check_now']['count']}")
        print(f"  mention_if_relevant count: {index['mention_if_relevant']['count']}")
        print(f"  deferred count: {index['deferred']['count']}")
        print(f"  auto_fixed count: {index['auto_fixed']['count']}")
        print()

        # Step 5: Verify files exist
        print("Step 5: Checking context files...")
        context_dir = Path.cwd() / ".devloop" / "context"
        if context_dir.exists():
            files = list(context_dir.glob("*.json"))
            print(f"  Context files: {[f.name for f in files]}")
            for file in files:
                content = json.loads(file.read_text())
                if file.name == "index.json":
                    print(f"  {file.name}: {json.dumps(content, indent=2)}")
                else:
                    print(f"  {file.name}: {len(content.get('findings', []))} findings")
        else:
            print(f"  Context dir not found: {context_dir}")
        print()

        # Summary
        print("=" * 60)
        print("Test Summary")
        print("=" * 60)
        
        if all_findings:
            print(f"✓ SUCCESS: Found {len(all_findings)} findings in context")
            for finding in all_findings[:5]:  # Show first 5
                print(f"  - {finding.category} in {finding.file}:{finding.line}")
            if len(all_findings) > 5:
                print(f"  ... and {len(all_findings) - 5} more")
        else:
            print("✗ FAILURE: No findings recorded in context store")
            print("  This indicates findings from agent are not being stored")
            
        print()


if __name__ == "__main__":
    asyncio.run(main())
