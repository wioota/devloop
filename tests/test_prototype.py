"""Basic tests for the prototype."""
import asyncio

import pytest

from dev_agents.agents import EchoAgent
from dev_agents.core import Event, EventBus, Priority


@pytest.mark.asyncio
async def test_event_bus():
    """Test basic event bus functionality."""
    event_bus = EventBus()
    queue = asyncio.Queue()

    # Subscribe to events
    await event_bus.subscribe("test:event", queue)

    # Emit an event
    event = Event(
        type="test:event",
        payload={"message": "hello"},
        priority=Priority.NORMAL
    )
    await event_bus.emit(event)

    # Check we received it
    received = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert received.type == "test:event"
    assert received.payload["message"] == "hello"


@pytest.mark.asyncio
async def test_echo_agent():
    """Test echo agent."""
    event_bus = EventBus()

    # Create agent
    agent = EchoAgent(
        name="test-echo",
        triggers=["test:*"],
        event_bus=event_bus
    )

    # Start agent
    await agent.start()

    # Create a queue to listen for results
    result_queue = asyncio.Queue()
    await event_bus.subscribe("agent:test-echo:completed", result_queue)

    # Emit a test event
    await event_bus.emit(Event(
        type="test:hello",
        payload={"data": "test"}
    ))

    # Wait for result
    result_event = await asyncio.wait_for(result_queue.get(), timeout=2.0)
    assert result_event.payload["success"] is True
    assert "test:hello" in result_event.payload["message"]

    # Stop agent
    await agent.stop()


@pytest.mark.asyncio
async def test_agent_lifecycle():
    """Test agent start/stop."""
    event_bus = EventBus()

    agent = EchoAgent(
        name="lifecycle-test",
        triggers=["test:*"],
        event_bus=event_bus
    )

    # Agent should not be running initially
    assert not agent._running

    # Start agent
    await agent.start()
    assert agent._running

    # Stop agent
    await agent.stop()
    assert not agent._running


def test_event_priority():
    """Test event priority comparison."""
    low = Event(type="test", payload={}, priority=Priority.LOW)
    high = Event(type="test", payload={}, priority=Priority.HIGH)

    # Higher priority should be "less than" (comes first in priority queue)
    assert high < low
