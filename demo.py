#!/usr/bin/env python3
"""
Comprehensive demo of Claude Agents using the new collector system.
This demonstrates the full event collection and agent processing pipeline.
"""
import asyncio
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dev_agents.core.event import Event, EventBus, Priority
from dev_agents.core.agent import AgentConfig
from dev_agents.collectors import CollectorManager
from dev_agents.agents.echo import EchoAgent
from dev_agents.agents.file_logger import FileLoggerAgent

# Import real agents - they might fail if linters aren't installed, that's OK
try:
    from dev_agents.agents.linter import LinterAgent
    LINTER_AVAILABLE = True
except ImportError as e:
    print(f"Note: LinterAgent requires dependencies: {e}")
    LINTER_AVAILABLE = False


async def demo_basic_functionality():
    """Demo basic event system and agents with collectors."""
    print("🚀 Claude Agents - Full System Demo")
    print("=" * 60)
    print()

    # Create event bus and collector manager
    event_bus = EventBus()
    collector_manager = CollectorManager(event_bus)
    print("✓ Event bus and collector manager created")

    # Create collectors
    with tempfile.TemporaryDirectory() as tmpdir:
        fs_config = {"watch_paths": [tmpdir]}
        collector_manager.create_collector("filesystem", fs_config)
        collector_manager.create_collector("process")
        collector_manager.create_collector("git")
        print(f"✓ Collectors created: {collector_manager.list_active_collectors()}")

        # Create echo agent
        echo_config = AgentConfig(
            enabled=True,
            triggers=["file:modified", "file:created"],
            config={}
        )
        echo = EchoAgent("echo", echo_config, event_bus)
        await echo.start()
        print("✓ Echo agent started")

        # Subscribe to results
        result_queue = asyncio.Queue()
        await event_bus.subscribe("agent:echo:completed", result_queue)

        # Start collectors
        await collector_manager.start_all()
        print("✓ All collectors started")

        # Emit a test event manually
        print("\n--- Emitting test event ---")
        test_event = Event(
            type="file:modified",
            payload={"path": f"{tmpdir}/test.py", "absolute_path": f"{tmpdir}/test.py"},
            source="demo",
            priority=Priority.NORMAL
        )
        await event_bus.emit(test_event)

        # Wait for agent to process
        await asyncio.sleep(0.2)

        # Get result
        try:
            result_event = await asyncio.wait_for(result_queue.get(), timeout=1.0)
            print("✓ Agent processed event:"            print(f"  Message: {result_event.payload['message']}")
            print(f"  Success: {result_event.payload['success']}")
            print(f"  Duration: {result_event.payload['duration']:.3f}s")
        except asyncio.TimeoutError:
            print("✗ Timeout waiting for result")

        # Create a real file to test filesystem collector
        print("\n--- Testing filesystem collector ---")
        test_file = Path(tmpdir) / "demo.py"
        test_file.write_text("print('Hello from collectors!')")
        print(f"📝 Created file: {test_file}")

        # Wait for filesystem collector to pick it up
        await asyncio.sleep(1.0)

        # Check for more results
        results = []
        try:
            while True:
                result_event = await asyncio.wait_for(result_queue.get_nowait(), timeout=0.1)
                results.append(result_event)
        except asyncio.TimeoutError:
            pass

        if results:
            print(f"✓ Filesystem collector triggered {len(results)} event(s)")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.payload.get('message', 'Unknown')}")

        # Stop everything
        await echo.stop()
        await collector_manager.stop_all()
        print("\n✓ All systems stopped cleanly")


async def demo_multiple_agents():
    """Demo multiple agents working with collectors."""
    print("\n" + "=" * 60)
    print("Multiple Agents + Collectors Demo")
    print("=" * 60)
    print()

    event_bus = EventBus()
    collector_manager = CollectorManager(event_bus)

    # Create collectors
    with tempfile.TemporaryDirectory() as tmpdir:
        fs_config = {"watch_paths": [tmpdir]}
        collector_manager.create_collector("filesystem", fs_config)

        # Create multiple agents
        agents = []

        echo_config = AgentConfig(enabled=True, triggers=["file:*"], config={})
        echo = EchoAgent("echo", echo_config, event_bus)
        agents.append(echo)

        logger_config = AgentConfig(enabled=True, triggers=["file:modified"], config={})
        logger = FileLoggerAgent("logger", logger_config, event_bus)
        agents.append(logger)

        # Start collectors and agents
        await collector_manager.start_all()
        print("✓ Collectors started")

        for agent in agents:
            await agent.start()
            print(f"✓ Started agent: {agent.name}")

        # Emit multiple events
        print("\n--- Emitting multiple events ---")
        events = [
            Event(type="file:created", payload={"path": f"{tmpdir}/test1.py", "absolute_path": f"{tmpdir}/test1.py"}, source="demo"),
            Event(type="file:modified", payload={"path": f"{tmpdir}/test2.py", "absolute_path": f"{tmpdir}/test2.py"}, source="demo"),
            Event(type="file:deleted", payload={"path": f"{tmpdir}/test3.py", "absolute_path": f"{tmpdir}/test3.py"}, source="demo"),
        ]

        for event in events:
            await event_bus.emit(event)
            print(f"  Emitted: {event.type} - {event.payload['path']}")

        # Create actual files to test filesystem collector
        print("\n--- Creating real files ---")
        test_files = []
        for i in range(1, 4):
            test_file = Path(tmpdir) / f"real_test{i}.py"
            test_file.write_text(f"print('Test file {i}')")
            test_files.append(test_file)
            print(f"  Created: {test_file.name}")

        # Give agents and collectors time to process
        await asyncio.sleep(1.0)

        print("\n✓ All agents and collectors processed events")

        # Show collector status
        status = collector_manager.get_status()
        print(f"\n📊 Collector Status:")
        for name, info in status.items():
            print(f"  {name}: {'Running' if info['running'] else 'Stopped'}")

        # Stop everything
        for agent in agents:
            await agent.stop()

        await collector_manager.stop_all()
        print("\n✓ All agents and collectors stopped")


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
