"""Tests for agent pipeline execution."""

import asyncio

import pytest

from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event, EventBus
from devloop.core.pipeline import Pipeline


class MockAgent(Agent):
    """Mock agent for testing pipelines."""

    def __init__(self, name: str, event_bus: EventBus, should_fail: bool = False):
        super().__init__(name=name, triggers=[], event_bus=event_bus)
        self.should_fail = should_fail
        self.handle_count = 0

    async def handle(self, event: Event) -> AgentResult:
        self.handle_count += 1
        if self.should_fail:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0.01,
                message=f"{self.name} failed",
            )
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0.01,
            message=f"{self.name} passed",
        )


class ErrorAgent(Agent):
    """Agent that raises an exception."""

    def __init__(self, name: str, event_bus: EventBus):
        super().__init__(name=name, triggers=[], event_bus=event_bus)

    async def handle(self, event: Event) -> AgentResult:
        raise RuntimeError("Agent exploded")


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def test_event():
    return Event(type="file:modified", payload={"file": "test.py"})


class TestPipelineExecution:
    @pytest.mark.asyncio
    async def test_all_stages_pass(self, event_bus, test_event):
        agents = [
            MockAgent("formatter", event_bus),
            MockAgent("linter", event_bus),
            MockAgent("type-checker", event_bus),
        ]
        pipeline = Pipeline(
            name="quality",
            stages=agents,
            event_bus=event_bus,
            triggers=["file:modified"],
        )

        result = await pipeline.execute(test_event)

        assert result.success
        assert len(result.stages) == 3
        assert all(not s.skipped for s in result.stages)
        assert all(s.result.success for s in result.stages)
        assert not result.short_circuited
        for agent in agents:
            assert agent.handle_count == 1

    @pytest.mark.asyncio
    async def test_short_circuit_on_failure(self, event_bus, test_event):
        agents = [
            MockAgent("formatter", event_bus),
            MockAgent("linter", event_bus, should_fail=True),
            MockAgent("type-checker", event_bus),
        ]
        pipeline = Pipeline(
            name="quality",
            stages=agents,
            event_bus=event_bus,
            triggers=["file:modified"],
            short_circuit=True,
        )

        result = await pipeline.execute(test_event)

        assert not result.success
        assert result.short_circuited
        assert result.short_circuit_at == "linter"
        # formatter ran, linter ran and failed, type-checker skipped
        assert agents[0].handle_count == 1
        assert agents[1].handle_count == 1
        assert agents[2].handle_count == 0
        assert result.stages[2].skipped

    @pytest.mark.asyncio
    async def test_no_short_circuit(self, event_bus, test_event):
        agents = [
            MockAgent("formatter", event_bus),
            MockAgent("linter", event_bus, should_fail=True),
            MockAgent("type-checker", event_bus),
        ]
        pipeline = Pipeline(
            name="quality",
            stages=agents,
            event_bus=event_bus,
            triggers=["file:modified"],
            short_circuit=False,
        )

        result = await pipeline.execute(test_event)

        assert not result.success
        assert not result.short_circuited
        # All agents should have run
        for agent in agents:
            assert agent.handle_count == 1

    @pytest.mark.asyncio
    async def test_disabled_stage_skipped(self, event_bus, test_event):
        agents = [
            MockAgent("formatter", event_bus),
            MockAgent("linter", event_bus),
        ]
        agents[0].enabled = False

        pipeline = Pipeline(
            name="quality",
            stages=agents,
            event_bus=event_bus,
            triggers=["file:modified"],
        )

        result = await pipeline.execute(test_event)

        assert result.success
        assert result.stages[0].skipped
        assert not result.stages[1].skipped
        assert agents[0].handle_count == 0
        assert agents[1].handle_count == 1

    @pytest.mark.asyncio
    async def test_exception_in_stage(self, event_bus, test_event):
        agents = [
            MockAgent("formatter", event_bus),
            ErrorAgent("linter", event_bus),
            MockAgent("type-checker", event_bus),
        ]
        pipeline = Pipeline(
            name="quality",
            stages=agents,
            event_bus=event_bus,
            triggers=["file:modified"],
            short_circuit=True,
        )

        result = await pipeline.execute(test_event)

        assert not result.success
        assert result.short_circuited
        assert result.short_circuit_at == "linter"
        assert "Exception" in result.stages[1].result.message
        assert result.stages[2].skipped

    @pytest.mark.asyncio
    async def test_empty_pipeline(self, event_bus, test_event):
        pipeline = Pipeline(
            name="empty",
            stages=[],
            event_bus=event_bus,
            triggers=["file:modified"],
        )

        result = await pipeline.execute(test_event)

        assert result.success
        assert len(result.stages) == 0


class TestPipelineResult:
    @pytest.mark.asyncio
    async def test_success_message(self, event_bus, test_event):
        agents = [MockAgent("a", event_bus), MockAgent("b", event_bus)]
        pipeline = Pipeline(
            name="test", stages=agents, event_bus=event_bus, triggers=[]
        )
        result = await pipeline.execute(test_event)
        assert "2/2 stages passed" in result.message

    @pytest.mark.asyncio
    async def test_failure_message(self, event_bus, test_event):
        agents = [MockAgent("a", event_bus, should_fail=True)]
        pipeline = Pipeline(
            name="test", stages=agents, event_bus=event_bus, triggers=[]
        )
        result = await pipeline.execute(test_event)
        assert "failed at a" in result.message


class TestPipelineLifecycle:
    @pytest.mark.asyncio
    async def test_start_stop(self, event_bus):
        agents = [MockAgent("formatter", event_bus)]
        pipeline = Pipeline(
            name="quality",
            stages=agents,
            event_bus=event_bus,
            triggers=["file:modified"],
        )

        await pipeline.start()
        assert pipeline._running

        await pipeline.stop()
        assert not pipeline._running

    @pytest.mark.asyncio
    async def test_event_triggers_pipeline(self, event_bus):
        agents = [MockAgent("formatter", event_bus)]
        pipeline = Pipeline(
            name="quality",
            stages=agents,
            event_bus=event_bus,
            triggers=["file:modified"],
        )

        await pipeline.start()

        # Emit event
        await event_bus.emit(Event(type="file:modified", payload={"file": "test.py"}))

        # Give pipeline time to process
        await asyncio.sleep(0.1)

        await pipeline.stop()

        assert agents[0].handle_count == 1
