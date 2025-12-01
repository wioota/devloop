#!/usr/bin/env python3
"""
Test agents with a real Python file that has linting issues.

Creates a test file with known linting violations and runs the linter
agent to ensure it finds them.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from devloop.core.context_store import context_store, Tier
from devloop.core.event import EventBus
from devloop.core.manager import AgentManager
from devloop.agents.linter import LinterAgent


async def main():
    # Clear old findings
    print("Clearing old findings...")
    await context_store.initialize()
    await context_store.clear_findings()
    print()

    # Create event bus and manager
    event_bus = EventBus()
    manager = AgentManager(event_bus=event_bus)

    # Create linter agent
    linter = manager.create_agent(
        LinterAgent,
        name="linter",
        triggers=["file:modify"],
        config={"enabled": True, "filePatterns": ["**/*.py"]},
    )

    # Target file with issues
    target_file = Path("src/devloop/agents/linter.py")
    
    if not target_file.exists():
        print(f"File not found: {target_file}")
        return

    print(f"Running linter on: {target_file}")
    from devloop.core.event import Event
    
    event = Event(
        type="file:modify",
        source="test",
        payload={"path": str(target_file)},
    )

    # Run the agent
    result = await linter.handle(event)
    print(f"Agent result: {result.message}")
    print(f"Issues found: {result.data.get('issue_count', 0)}")
    print()

    # Check findings
    await asyncio.sleep(0.5)
    findings = await context_store.get_findings()
    
    print(f"Total findings stored: {len(findings)}")
    for finding in findings[:10]:
        print(f"  - {finding.category} at {finding.file}:{finding.line} - {finding.message[:50]}")
    print()

    # Check index
    index = await context_store.read_index()
    print("Index summary:")
    print(f"  check_now: {index['check_now']['count']}")
    print(f"  mention_if_relevant: {index['mention_if_relevant']['count']}")
    print(f"  deferred: {index['deferred']['count']}")
    print(f"  auto_fixed: {index['auto_fixed']['count']}")


if __name__ == "__main__":
    asyncio.run(main())
