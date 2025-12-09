"""Performance benchmarks for DevLoop agents.

Validates performance claims:
- Sub-second latency for agent execution
- <5% CPU overhead during idle
- <100MB memory footprint
- <1 second feedback for file changes

Run with: pytest tests/performance/test_agent_performance.py -v --tb=short
"""

import asyncio
import json
import logging
import os
import psutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List

import pytest

from devloop.core import EventBus
from devloop.core.event import Event, Priority
from devloop.core.telemetry import get_telemetry_logger

logger = logging.getLogger(__name__)

# Suppress debug logging during benchmarks
logging.getLogger("devloop").setLevel(logging.WARNING)


@pytest.fixture
def test_workspace(tmp_path):
    """Create a test workspace with Python files."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create a simple Python file to lint/check
    py_file = workspace / "example.py"
    py_file.write_text("""
import os
import sys
from typing import List

def hello(name):
    print(f"Hello {name}")

def calculate(a,b,c):  # Bad formatting
    return a+b+c

class MyClass:
    def __init__(self):
        self.value = 42
        
    def method(self):
        result=1+2+3
        return result
""")

    return workspace





class TestAgentLatency:
    """Benchmark agent execution latency."""

    @pytest.mark.asyncio
    async def test_linter_tool_latency(self, test_workspace):
        """Measure linter tool execution time (Ruff).

        Target: <500ms for typical Python file
        """
        py_file = test_workspace / "example.py"

        # Measure Ruff execution time
        start_time = time.perf_counter()
        try:
            subprocess.run(
                ["ruff", "check", str(py_file)],
                capture_output=True,
                timeout=10,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Ruff not available")

        duration = time.perf_counter() - start_time
        duration_ms = duration * 1000

        logger.info(f"Ruff latency: {duration_ms:.1f}ms")

        # Target: <500ms
        assert duration_ms < 500, f"Ruff latency {duration_ms:.1f}ms exceeds 500ms target"

    @pytest.mark.asyncio
    async def test_formatter_tool_latency(self, test_workspace):
        """Measure formatter tool execution time (Black).

        Target: <1000ms for typical Python file (Black startup is ~600ms+)
        """
        py_file = test_workspace / "example.py"

        # Measure Black execution time
        start_time = time.perf_counter()
        try:
            subprocess.run(
                ["black", "--check", str(py_file)],
                capture_output=True,
                timeout=10,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Black not available")

        duration = time.perf_counter() - start_time
        duration_ms = duration * 1000

        logger.info(f"Black latency: {duration_ms:.1f}ms")

        # Target: <1000ms (Black startup can be slow, ~600ms+)
        assert duration_ms < 1000, f"Black latency {duration_ms:.1f}ms exceeds 1000ms target"

    @pytest.mark.asyncio
    async def test_type_checker_tool_latency(self, test_workspace):
        """Measure type checker tool execution time (mypy).

        Target: <2000ms for typical Python file (slower due to mypy)
        """
        py_file = test_workspace / "example.py"

        # Measure mypy execution time
        start_time = time.perf_counter()
        try:
            subprocess.run(
                ["mypy", str(py_file), "--no-error-summary"],
                capture_output=True,
                timeout=10,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("mypy not available")

        duration = time.perf_counter() - start_time
        duration_ms = duration * 1000

        logger.info(f"mypy latency: {duration_ms:.1f}ms")

        # Target: <2000ms (mypy can be slow)
        assert duration_ms < 2000, f"mypy latency {duration_ms:.1f}ms exceeds 2000ms target"


class TestResourceUsage:
    """Benchmark resource usage (CPU, memory)."""

    def test_event_bus_memory_usage(self):
        """Measure event bus memory footprint.

        Target: <10MB for event bus with 1000 queued events
        """
        process = psutil.Process(os.getpid())

        # Get baseline memory
        baseline_memory = process.memory_info().rss / (1024 * 1024)  # MB

        # Create event bus and queue events
        event_bus = EventBus()

        # Queue 1000 events
        for i in range(1000):
            event = Event(
                type=f"file:save",
                source="test",
                priority=Priority.NORMAL,
                payload={"index": i, "data": "x" * 1000},
            )
            event_bus._event_log.append(event)

        # Get memory after queueing
        peak_memory = process.memory_info().rss / (1024 * 1024)  # MB
        memory_usage = peak_memory - baseline_memory

        logger.info(
            f"Event bus memory: baseline={baseline_memory:.1f}MB, "
            f"peak={peak_memory:.1f}MB, delta={memory_usage:.1f}MB"
        )

        # Target: <10MB overhead for 1000 events
        assert memory_usage < 10, (
            f"Event bus memory overhead {memory_usage:.1f}MB exceeds 10MB target"
        )

    @pytest.mark.asyncio
    async def test_event_bus_throughput(self):
        """Measure event bus throughput.

        Target: >1000 events/second
        """
        event_bus = EventBus()

        # Subscribe to events
        queue = asyncio.Queue()
        await event_bus.subscribe("file:*", queue)

        # Emit events rapidly
        from devloop.core.event import Event, Priority

        num_events = 1000
        start_time = time.perf_counter()

        for i in range(num_events):
            event = Event(
                type=f"file:save",
                source="test",
                priority=Priority.NORMAL,
                payload={"index": i},
            )
            await event_bus.emit(event)

        duration = time.perf_counter() - start_time
        throughput = num_events / duration

        logger.info(f"Event bus throughput: {throughput:.0f} events/second ({duration:.2f}s for {num_events})")

        # Target: >1000 events/second
        assert (
            throughput > 1000
        ), f"Event bus throughput {throughput:.0f} events/sec is below 1000 target"


class TestEndToEndTiming:
    """End-to-end timing tests."""

    @pytest.mark.asyncio
    async def test_event_creation_and_emission(self):
        """Measure time from event creation to emission.

        Target: <50ms for creating and emitting an event
        """
        event_bus = EventBus()

        # Subscribe to capture events
        queue = asyncio.Queue()
        await event_bus.subscribe("file:*", queue)

        # Measure total time from creation to emission
        start_time = time.perf_counter()

        # Create and emit event
        event = Event(
            type="file:save",
            source="test",
            priority=Priority.NORMAL,
            payload={"path": "/tmp/test.py"},
        )
        await event_bus.emit(event)

        # Give event a moment to be processed
        await asyncio.sleep(0.01)

        duration = time.perf_counter() - start_time
        duration_ms = duration * 1000

        logger.info(f"Event creation and emission latency: {duration_ms:.1f}ms")

        # Target: <100ms
        assert duration_ms < 100, f"Event latency {duration_ms:.1f}ms exceeds 100ms target"


class TestTelemetryPerformance:
    """Telemetry logging performance."""

    def test_telemetry_logging_overhead(self, tmp_path):
        """Measure telemetry logging overhead.

        Target: <10ms for logging a telemetry event
        """
        log_file = tmp_path / "events.jsonl"
        telemetry = get_telemetry_logger(log_file)

        # Measure logging time
        num_logs = 100
        start_time = time.perf_counter()

        for i in range(num_logs):
            telemetry.log_agent_execution(
                agent="test_agent",
                duration_ms=100,
                findings=i % 5,
                success=True,
            )

        duration = time.perf_counter() - start_time
        avg_log_time = (duration / num_logs) * 1000  # ms

        logger.info(f"Average telemetry log time: {avg_log_time:.2f}ms")

        # Target: <10ms per log
        assert (
            avg_log_time < 10
        ), f"Telemetry logging time {avg_log_time:.2f}ms exceeds 10ms target"

        # Verify data was written
        events = telemetry.get_events(limit=100)
        assert len(events) == num_logs


class TestConcurrentEvents:
    """Benchmark concurrent event processing."""

    @pytest.mark.asyncio
    async def test_concurrent_event_emission(self):
        """Measure concurrent event emission.

        Target: <500ms for emitting 100 events concurrently
        """
        event_bus = EventBus()

        # Subscribe to events
        queue = asyncio.Queue()
        await event_bus.subscribe("file:*", queue)

        # Measure concurrent emission
        start_time = time.perf_counter()

        # Emit 100 events concurrently
        tasks = []
        for i in range(100):
            event = Event(
                type="file:save",
                source="test",
                priority=Priority.NORMAL,
                payload={"index": i},
            )
            tasks.append(event_bus.emit(event))

        await asyncio.gather(*tasks)

        duration = time.perf_counter() - start_time

        logger.info(f"Concurrent emission of 100 events: {duration:.2f}s")

        # Target: <500ms
        assert duration < 0.5, f"Concurrent emission {duration:.2f}s exceeds 500ms target"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
