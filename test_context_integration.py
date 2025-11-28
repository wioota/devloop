#!/usr/bin/env python3
"""Integration test for context store with linter agent."""
import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dev_agents.agents.linter import LinterAgent
from dev_agents.core.context_store import context_store
from dev_agents.core.event import Event, EventBus


async def test_linter_context_integration():
    """Test that linter agent writes findings to context store."""

    print("=" * 70)
    print("Integration Test: Linter Agent → Context Store")
    print("=" * 70)

    # Setup
    test_dir = Path("test_context_integration")
    context_dir = test_dir / ".claude" / "context"

    # Initialize context store
    context_store.context_dir = context_dir
    await context_store.initialize()
    print(f"✓ Context store initialized: {context_dir}")

    # Clear any existing findings
    await context_store.clear_findings()
    print("✓ Cleared existing findings")

    # Create event bus
    event_bus = EventBus()

    # Create linter agent
    linter = LinterAgent(
        name="linter",
        triggers=["file:modified"],
        event_bus=event_bus,
        config={
            "enabled": True,
            "autoFix": False,
            "filePatterns": ["**/*.py"]
        }
    )
    print("✓ Created linter agent")

    # Create test file event
    test_file = test_dir / "src" / "sample.py"
    event = Event(
        type="file:modified",
        payload={"path": str(test_file)},
        source="test"
    )
    print(f"✓ Created event for: {test_file}")

    # Run linter
    print("\nRunning linter...")
    result = await linter.handle(event)
    print(f"  Agent result: {result.message}")
    print(f"  Success: {result.success}")
    if result.data:
        print(f"  Issues found: {result.data.get('issue_count', 0)}")

    # Check context store
    print("\nChecking context store...")

    # Read index
    index = await context_store.read_index()
    print(f"\nIndex summary:")
    print(f"  Immediate issues: {index['check_now']['count']}")
    print(f"  Relevant issues: {index['mention_if_relevant']['count']}")
    print(f"  Background issues: {index['deferred']['count']}")
    print(f"  Auto-fixed: {index['auto_fixed']['count']}")

    # Check immediate findings
    from dev_agents.core.context_store import Tier
    immediate_findings = await context_store.get_findings(tier=Tier.IMMEDIATE)
    if immediate_findings:
        print(f"\nImmediate findings ({len(immediate_findings)}):")
        for f in immediate_findings[:3]:  # Show first 3
            print(f"  - {f.severity.value}: {f.message} ({f.file}:{f.line})")

    # Check relevant findings
    relevant_findings = await context_store.get_findings(tier=Tier.RELEVANT)
    if relevant_findings:
        print(f"\nRelevant findings ({len(relevant_findings)}):")
        for f in relevant_findings[:3]:  # Show first 3
            print(f"  - {f.severity.value}: {f.message} ({f.file}:{f.line})")

    # Verify files exist
    print("\nVerifying context files...")
    files_to_check = [
        "index.json",
        "immediate.json",
        "relevant.json",
        "background.json",
        "auto_fixed.json"
    ]

    for filename in files_to_check:
        filepath = context_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"  ✓ {filename} ({size} bytes)")
        else:
            print(f"  ✗ {filename} (missing)")

    # Success criteria
    print("\n" + "=" * 70)
    print("Test Results:")
    print("=" * 70)

    total_findings = len(immediate_findings) + len(relevant_findings)

    success = True
    if not (context_dir / "index.json").exists():
        print("✗ FAIL: index.json not created")
        success = False
    elif total_findings == 0:
        print("✗ FAIL: No findings written to context store")
        success = False
    else:
        print(f"✓ PASS: {total_findings} findings written to context store")
        print(f"✓ PASS: Context files created successfully")

    if success:
        print("\n🎉 Integration test PASSED!")
        return 0
    else:
        print("\n❌ Integration test FAILED!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_linter_context_integration())
    sys.exit(exit_code)
