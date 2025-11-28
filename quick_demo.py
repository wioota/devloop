#!/usr/bin/env python3
"""Quick automated demo of agents using the new collector system."""
import asyncio
import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dev_agents.core.event import EventBus
from dev_agents.collectors import CollectorManager
from dev_agents.agents import LinterAgent, FormatterAgent


async def demo():
    """Quick demo using the new collector manager."""
    print("🚀 Claude Agents - Collector Manager Demo\n")

    # Create temp dir
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Setup event bus and collector manager
        event_bus = EventBus()
        collector_manager = CollectorManager(event_bus)

        # Create collectors using the manager
        fs_config = {"watch_paths": [tmpdir]}
        collector_manager.create_collector("filesystem", fs_config)

        # For demo purposes, we'll also create process collector
        collector_manager.create_collector("process")
        collector_manager.create_collector("git")

        # Create agents (using old API for now - will migrate to new API later)
        linter = LinterAgent(
            name="linter",
            triggers=["file:created", "file:modified"],
            event_bus=event_bus,
            config={"autoFix": False}
        )

        formatter = FormatterAgent(
            name="formatter",
            triggers=["file:modified"],
            event_bus=event_bus,
            config={"formatOnSave": True}
        )

        # Start everything
        await collector_manager.start_all()
        await linter.start()
        await formatter.start()

        print("✓ Collectors and agents started\n")
        print(f"📊 Active collectors: {collector_manager.list_active_collectors()}")
        print(f"📊 Collector status: {list(collector_manager.get_status().keys())}\n")

        await asyncio.sleep(0.5)

        # Create test file with issues
        test_file = tmppath / "demo.py"
        print(f"📝 Creating test file: {test_file.name}")
        test_file.write_text("def hello(  x,y  ):\n    return x+y\n")

        # Wait for processing
        await asyncio.sleep(2)

        print("\n✅ Demo complete!")
        print("The collectors monitored the file creation and agents processed it in real-time.")

        # Stop everything
        await linter.stop()
        await formatter.stop()
        await collector_manager.stop_all()


if __name__ == "__main__":
    asyncio.run(demo())
