#!/usr/bin/env python3
"""
Standalone demo of Claude Agents without requiring installation.
This demonstrates the core functionality directly.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_agents.core import Event, EventBus, Priority
from claude_agents.agents import EchoAgent, FileLoggerAgent

# Import real agents - they might fail if linters aren't installed, that's OK
try:
    from claude_agents.agents import LinterAgent
    LINTER_AVAILABLE = True
except ImportError as e:
    print(f"Note: LinterAgent requires dependencies: {e}")
    LINTER_AVAILABLE = False


async def demo_basic_functionality():
    """Demo basic event system and agents."""
    print("=" * 60)
    print("Claude Agents - Live Demo")
    print("=" * 60)
    print()

    # Create event bus
    event_bus = EventBus()
    print("✓ Event bus created")

    # Create echo agent
    echo = EchoAgent(
        name="echo",
        triggers=["file:modified", "file:created"],
        event_bus=event_bus
    )
    await echo.start()
    print("✓ Echo agent started")

    # Subscribe to results
    result_queue = asyncio.Queue()
    await event_bus.subscribe("agent:echo:completed", result_queue)

    # Emit a test event
    print("\n--- Emitting test event ---")
    test_event = Event(
        type="file:modified",
        payload={"path": "/home/user/app.py"},
        source="demo",
        priority=Priority.NORMAL
    )
    await event_bus.emit(test_event)

    # Wait for agent to process
    await asyncio.sleep(0.2)

    # Get result
    try:
        result_event = await asyncio.wait_for(result_queue.get(), timeout=1.0)
        print(f"\n✓ Agent processed event:")
        print(f"  Message: {result_event.payload['message']}")
        print(f"  Success: {result_event.payload['success']}")
        print(f"  Duration: {result_event.payload['duration']:.3f}s")
    except asyncio.TimeoutError:
        print("✗ Timeout waiting for result")

    # Stop agent
    await echo.stop()
    print("\n✓ Agent stopped cleanly")


async def demo_multiple_agents():
    """Demo multiple agents working in parallel."""
    print("\n" + "=" * 60)
    print("Multiple Agents Demo")
    print("=" * 60)
    print()

    event_bus = EventBus()

    # Create multiple agents
    agents = []

    echo = EchoAgent(name="echo", triggers=["file:*"], event_bus=event_bus)
    agents.append(echo)

    logger = FileLoggerAgent(
        name="logger",
        triggers=["file:modified"],
        event_bus=event_bus
    )
    agents.append(logger)

    # Start all agents
    for agent in agents:
        await agent.start()
        print(f"✓ Started: {agent.name}")

    # Emit multiple events
    print("\n--- Emitting multiple events ---")
    events = [
        Event(type="file:created", payload={"path": "test1.py"}, source="demo"),
        Event(type="file:modified", payload={"path": "test2.py"}, source="demo"),
        Event(type="file:deleted", payload={"path": "test3.py"}, source="demo"),
    ]

    for event in events:
        await event_bus.emit(event)
        print(f"  Emitted: {event.type} - {event.payload['path']}")

    # Give agents time to process
    await asyncio.sleep(0.3)

    print("\n✓ All agents processed events in parallel")

    # Check recent events
    recent = event_bus.get_recent_events(5)
    print(f"\n✓ Event bus tracked {len(recent)} recent events")

    # Stop all agents
    for agent in agents:
        await agent.stop()

    print("\n✓ All agents stopped")


async def demo_priority_events():
    """Demo priority-based event handling."""
    print("\n" + "=" * 60)
    print("Priority Events Demo")
    print("=" * 60)
    print()

    # Create events with different priorities
    events = [
        Event(type="test", payload={"msg": "Low priority"}, priority=Priority.LOW),
        Event(type="test", payload={"msg": "High priority"}, priority=Priority.HIGH),
        Event(type="test", payload={"msg": "Normal priority"}, priority=Priority.NORMAL),
        Event(type="test", payload={"msg": "Critical priority"}, priority=Priority.CRITICAL),
    ]

    # Sort by priority (high priority first)
    sorted_events = sorted(events)

    print("Events sorted by priority:")
    for i, event in enumerate(sorted_events, 1):
        print(f"  {i}. {event.priority.name}: {event.payload['msg']}")

    print("\n✓ Priority system working correctly")


async def main():
    """Run all demos."""
    try:
        # Demo 1: Basic functionality
        await demo_basic_functionality()

        # Demo 2: Multiple agents
        await demo_multiple_agents()

        # Demo 3: Priority events
        await demo_priority_events()

        print("\n" + "=" * 60)
        print("✅ All demos completed successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Install dependencies: pip install pydantic watchdog typer")
        print("  2. Run: ./run-agents.sh watch")
        print("  3. Edit files and watch agents work!")
        print()

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
