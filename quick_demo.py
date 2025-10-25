#!/usr/bin/env python3
"""Quick automated demo of agents."""
import asyncio
import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_agents.core import EventBus
from claude_agents.collectors import FileSystemCollector
from claude_agents.agents import LinterAgent, FormatterAgent


async def demo():
    """Quick demo."""
    print("Quick Demo: Agents in Action\n")

    # Create temp dir
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Setup
        event_bus = EventBus()
        fs_collector = FileSystemCollector(event_bus=event_bus, watch_paths=[tmpdir])

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

        # Start
        await fs_collector.start()
        await linter.start()
        await formatter.start()

        print("✓ Agents started\n")
        await asyncio.sleep(0.5)

        # Create test file with issues
        test_file = tmppath / "demo.py"
        print(f"Creating: {test_file.name}")
        test_file.write_text("def hello(  x,y  ):\n    return x+y\n")

        # Wait for processing
        await asyncio.sleep(2)

        print("\n✓ Demo complete!")
        print("The agents processed the file in real-time.")

        # Stop
        await linter.stop()
        await formatter.stop()
        await fs_collector.stop()


if __name__ == "__main__":
    asyncio.run(demo())
