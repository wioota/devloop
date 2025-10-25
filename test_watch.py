#!/usr/bin/env python3
"""Quick test of watch functionality."""
import asyncio
import signal
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_agents.core import EventBus, Config
from claude_agents.collectors import FileSystemCollector
from claude_agents.agents import EchoAgent


async def test_watch():
    """Test watch with echo agent."""
    print("Starting watch test...")
    print("Edit test_sample.py to trigger events")
    print("Press Ctrl+C to stop\n")

    # Create event bus
    event_bus = EventBus()

    # Create filesystem collector
    fs_collector = FileSystemCollector(
        event_bus=event_bus,
        watch_paths=[str(Path.cwd())]
    )

    # Create echo agent
    echo = EchoAgent(
        name="echo",
        triggers=["file:modified", "file:created"],
        event_bus=event_bus
    )

    # Start everything
    await fs_collector.start()
    await echo.start()

    print("✓ Watching started\n")

    # Wait for shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)

    await shutdown_event.wait()

    # Stop everything
    await echo.stop()
    await fs_collector.stop()

    print("\n✓ Stopped")


if __name__ == "__main__":
    asyncio.run(test_watch())
