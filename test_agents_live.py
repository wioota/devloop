#!/usr/bin/env python3
"""Live test of agents watching the project."""
import asyncio
import sys
import signal
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_agents.core import EventBus, Config
from claude_agents.collectors import FileSystemCollector
from claude_agents.agents import LinterAgent, FormatterAgent, TestRunnerAgent


async def main():
    """Run agents watching this project."""
    print("=" * 60)
    print("Claude Agents - Watching This Project")
    print("=" * 60)
    print()
    print(f"Watching: {Path.cwd()}")
    print()
    print("Try editing test_sample.py in another terminal!")
    print("Press Ctrl+C to stop")
    print()

    # Load config
    config = Config.load_or_default()

    # Create event bus
    event_bus = EventBus()

    # Create filesystem collector
    fs_collector = FileSystemCollector(
        event_bus=event_bus,
        watch_paths=[str(Path.cwd())]
    )

    # Create agents
    agents = []

    if config.is_agent_enabled("linter"):
        linter = LinterAgent(
            name="linter",
            triggers=["file:modified", "file:created"],
            event_bus=event_bus,
            config=config.get_agent_config("linter").get("config", {})
        )
        agents.append(linter)

    if config.is_agent_enabled("formatter"):
        formatter = FormatterAgent(
            name="formatter",
            triggers=["file:modified"],
            event_bus=event_bus,
            config=config.get_agent_config("formatter").get("config", {})
        )
        agents.append(formatter)

    if config.is_agent_enabled("test-runner"):
        test_runner = TestRunnerAgent(
            name="test-runner",
            triggers=["file:modified", "file:created"],
            event_bus=event_bus,
            config=config.get_agent_config("test-runner").get("config", {})
        )
        agents.append(test_runner)

    # Start everything
    await fs_collector.start()
    for agent in agents:
        await agent.start()

    print(f"✓ Started {len(agents)} agents")
    for agent in agents:
        print(f"  • {agent.name}")
    print()

    # Wait for shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    await shutdown_event.wait()

    # Stop everything
    for agent in agents:
        await agent.stop()
    await fs_collector.stop()

    print("\n✓ Stopped")


if __name__ == "__main__":
    asyncio.run(main())
