#!/usr/bin/env python3
"""Test filesystem collector threading/async fix."""
import asyncio
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_agents.core import EventBus
from claude_agents.collectors import FileSystemCollector


async def test_filesystem_events():
    """Test that filesystem events are properly emitted from watchdog thread to asyncio."""
    print("Testing filesystem collector threading/async integration...")
    print()

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Created temp directory: {tmpdir}")

        # Create event bus
        event_bus = EventBus()
        print("✓ Event bus created")

        # Create filesystem collector
        fs_collector = FileSystemCollector(
            event_bus=event_bus,
            watch_paths=[tmpdir]
        )
        print("✓ Filesystem collector created")

        # Subscribe to file events
        event_queue = asyncio.Queue()
        await event_bus.subscribe("file:created", event_queue)
        await event_bus.subscribe("file:modified", event_queue)
        print("✓ Subscribed to file events")

        # Start the collector
        await fs_collector.start()
        print("✓ Filesystem collector started")

        # Give watchdog a moment to initialize
        await asyncio.sleep(0.5)

        # Create a test file (this will trigger the event from watchdog thread)
        test_file = Path(tmpdir) / "test.py"
        print(f"\nCreating test file: {test_file}")
        test_file.write_text("print('Hello, World!')")

        # Wait for event to be emitted
        print("Waiting for file:created event...")
        try:
            event = await asyncio.wait_for(event_queue.get(), timeout=3.0)
            print(f"✓ Received event: {event.type}")
            print(f"  - Path: {event.payload['path']}")
            print(f"  - Source: {event.source}")
            print(f"  - Priority: {event.priority.name}")
            print()
            print("✅ SUCCESS: Threading/async bridge is working!")
            success = True
        except asyncio.TimeoutError:
            print("✗ TIMEOUT: No event received")
            print("❌ FAILED: Threading/async bridge not working")
            success = False

        # Stop the collector
        await fs_collector.stop()
        print("✓ Filesystem collector stopped")

        return success


async def main():
    """Run the test."""
    try:
        success = await test_filesystem_events()
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
