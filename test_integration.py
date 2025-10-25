#!/usr/bin/env python3
"""Integration test with real agents."""
import asyncio
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_agents.core import EventBus
from claude_agents.collectors import FileSystemCollector
from claude_agents.agents import EchoAgent, FileLoggerAgent


async def test_integration():
    """Test filesystem collector with real agents."""
    print("Integration Test: Filesystem Collector + Agents")
    print("=" * 60)
    print()

    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Test directory: {tmpdir}\n")

        # Create event bus
        event_bus = EventBus()
        print("✓ Event bus created")

        # Create filesystem collector
        fs_collector = FileSystemCollector(
            event_bus=event_bus,
            watch_paths=[tmpdir]
        )
        print("✓ Filesystem collector created")

        # Create agents
        echo = EchoAgent(
            name="echo",
            triggers=["file:created", "file:modified"],
            event_bus=event_bus
        )

        logger = FileLoggerAgent(
            name="logger",
            triggers=["file:modified"],
            event_bus=event_bus
        )
        print("✓ Agents created")

        # Subscribe to agent results
        result_queue = asyncio.Queue()
        await event_bus.subscribe("agent:echo:completed", result_queue)
        print("✓ Subscribed to agent results")

        # Start everything
        await fs_collector.start()
        await echo.start()
        await logger.start()
        print("✓ Everything started\n")

        # Give system time to initialize
        await asyncio.sleep(0.5)

        # Create test file
        test_file = Path(tmpdir) / "integration_test.py"
        print(f"Creating file: {test_file.name}")
        test_file.write_text("def hello():\n    return 'Hello, World!'\n")

        # Wait for agent to process
        print("Waiting for agents to process...")
        try:
            result = await asyncio.wait_for(result_queue.get(), timeout=3.0)
            print(f"\n✓ Agent completed!")
            print(f"  - Message: {result.payload['message']}")
            print(f"  - Success: {result.payload['success']}")
            print(f"  - Duration: {result.payload['duration']:.3f}s")
            print()

            # Modify file
            print(f"Modifying file: {test_file.name}")
            test_file.write_text("def hello():\n    return 'Hello, Universe!'\n")

            # Wait for second processing
            result = await asyncio.wait_for(result_queue.get(), timeout=3.0)
            print(f"\n✓ Agent completed again!")
            print(f"  - Message: {result.payload['message']}")
            print()

            print("=" * 60)
            print("✅ INTEGRATION TEST PASSED")
            print("=" * 60)
            print("\nThe threading/async bridge is working correctly!")
            print("Filesystem events are being properly emitted from watchdog")
            print("thread to asyncio event loop and processed by agents.")
            success = True

        except asyncio.TimeoutError:
            print("\n✗ Timeout waiting for agent")
            print("❌ INTEGRATION TEST FAILED")
            success = False

        # Stop everything
        await echo.stop()
        await logger.stop()
        await fs_collector.stop()
        print("\n✓ All components stopped cleanly")

        return success


async def main():
    """Run integration test."""
    try:
        success = await test_integration()
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
