#!/usr/bin/env python3
"""Quick validation script for the prototype."""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_agents.agents import EchoAgent
from claude_agents.core import Event, EventBus, Priority


async def main():
    """Run basic validation."""
    print("🧪 Testing Claude Agents Prototype\n")

    # Test 1: Event Bus
    print("1. Testing EventBus...")
    event_bus = EventBus()
    queue = asyncio.Queue()
    await event_bus.subscribe("test:event", queue)

    test_event = Event(
        type="test:event",
        payload={"message": "hello"},
        priority=Priority.NORMAL
    )
    await event_bus.emit(test_event)

    received = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert received.type == "test:event"
    print("   ✓ EventBus working\n")

    # Test 2: Agent
    print("2. Testing EchoAgent...")
    agent = EchoAgent(
        name="test-echo",
        triggers=["test:hello"],  # Use exact match for now
        event_bus=event_bus
    )

    result_queue = asyncio.Queue()
    await event_bus.subscribe("agent:test-echo:completed", result_queue)

    await agent.start()
    assert agent._running
    print("   ✓ Agent started")

    # Give the agent's event loop a moment to start processing
    await asyncio.sleep(0.2)

    await event_bus.emit(Event(
        type="test:hello",
        payload={"data": "test"}
    ))

    # Give it time to process
    await asyncio.sleep(0.2)

    result_event = await asyncio.wait_for(result_queue.get(), timeout=3.0)
    assert result_event.payload["success"] is True
    print("   ✓ Agent processed event")

    await agent.stop()
    assert not agent._running
    print("   ✓ Agent stopped\n")

    # Test 3: Priority
    print("3. Testing Event Priority...")
    low = Event(type="test", payload={}, priority=Priority.LOW)
    high = Event(type="test", payload={}, priority=Priority.HIGH)
    assert high < low
    print("   ✓ Priority system working\n")

    print("✅ All basic tests passed!")
    print("\nPrototype is ready to use. Try:")
    print("  claude-agents watch /path/to/directory\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
