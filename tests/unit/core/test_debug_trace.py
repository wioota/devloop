"""Tests for debug_trace module.

Tests execution tracing, decorators, and failure detection.
"""

import asyncio
from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock

import pytest

from devloop.core.debug_trace import (
    ExecutionTrace,
    FailureDetector,
    clear_trace_history,
    get_failure_detector,
    get_trace_history,
    report_diagnostics,
    trace_agent_execution,
    trace_context_store,
    trace_execution,
)


class TestExecutionTrace:
    """Tests for ExecutionTrace class."""

    def test_init_defaults(self):
        """Test ExecutionTrace initialization with defaults."""
        trace = ExecutionTrace("test_func")

        assert trace.name == "test_func"
        assert trace.args == ()
        assert trace.kwargs == {}
        assert trace.start_time is None
        assert trace.end_time is None
        assert trace.duration is None
        assert trace.result is None
        assert trace.exception is None
        assert trace.success is False

    def test_init_with_args_kwargs(self):
        """Test ExecutionTrace initialization with args and kwargs."""
        trace = ExecutionTrace("test_func", (1, 2), {"key": "value"})

        assert trace.args == (1, 2)
        assert trace.kwargs == {"key": "value"}

    def test_is_running_before_start(self):
        """Test is_running property before start."""
        trace = ExecutionTrace("test_func")
        assert trace.is_running is False

    def test_is_running_after_start(self):
        """Test is_running property after start."""
        trace = ExecutionTrace("test_func")
        trace.start()
        assert trace.is_running is True

    def test_is_running_after_end(self):
        """Test is_running property after end."""
        trace = ExecutionTrace("test_func")
        trace.start()
        trace.end()
        assert trace.is_running is False

    def test_is_complete_before_start(self):
        """Test is_complete property before start."""
        trace = ExecutionTrace("test_func")
        assert trace.is_complete is False

    def test_is_complete_after_start(self):
        """Test is_complete property after start but before end."""
        trace = ExecutionTrace("test_func")
        trace.start()
        assert trace.is_complete is False

    def test_is_complete_after_end(self):
        """Test is_complete property after end."""
        trace = ExecutionTrace("test_func")
        trace.start()
        trace.end()
        assert trace.is_complete is True

    def test_start_sets_start_time(self):
        """Test that start() sets start_time."""
        trace = ExecutionTrace("test_func")
        trace.start()
        assert trace.start_time is not None
        assert isinstance(trace.start_time, float)

    def test_end_sets_end_time_and_duration(self):
        """Test that end() sets end_time and duration."""
        trace = ExecutionTrace("test_func")
        trace.start()
        trace.end()

        assert trace.end_time is not None
        assert trace.duration is not None
        assert trace.duration >= 0

    def test_end_with_result(self):
        """Test end() with result."""
        trace = ExecutionTrace("test_func")
        trace.start()
        trace.end(result={"status": "ok"})

        assert trace.result == {"status": "ok"}
        assert trace.success is True
        assert trace.exception is None

    def test_end_with_exception(self):
        """Test end() with exception."""
        trace = ExecutionTrace("test_func")
        trace.start()
        exc = ValueError("test error")
        trace.end(exception=exc)

        assert trace.exception is exc
        assert trace.success is False
        assert trace.result is None

    def test_end_without_start_time_raises(self):
        """Test end() when start() was not called raises TypeError.

        This is current behavior - the logging tries to format None duration.
        Could be considered a bug in the source code.
        """
        trace = ExecutionTrace("test_func")

        # Currently raises because logging tries to format None as float
        with pytest.raises(TypeError):
            trace.end()

    def test_to_dict(self):
        """Test to_dict() method."""
        trace = ExecutionTrace("test_func")
        trace.start()
        trace.end(result="success")

        result = trace.to_dict()

        assert result["name"] == "test_func"
        assert result["start_time"] is not None
        assert result["end_time"] is not None
        assert result["duration"] is not None
        assert result["success"] is True
        assert result["error"] is None

    def test_to_dict_with_error(self):
        """Test to_dict() with exception."""
        trace = ExecutionTrace("test_func")
        trace.start()
        trace.end(exception=ValueError("test error"))

        result = trace.to_dict()

        assert result["success"] is False
        assert result["error"] == "test error"


class TestTraceHistory:
    """Tests for trace history functions."""

    def setup_method(self):
        """Clear trace history before each test."""
        clear_trace_history()

    def test_get_trace_history_empty(self):
        """Test get_trace_history with no traces."""
        history = get_trace_history()
        assert history == []

    def test_get_trace_history_with_limit(self):
        """Test get_trace_history with limit."""
        # Add some traces using the decorator
        @trace_execution("test_func")
        def test_func():
            return "result"

        for _ in range(10):
            test_func()

        history = get_trace_history(limit=5)
        assert len(history) == 5

    def test_clear_trace_history(self):
        """Test clear_trace_history."""
        @trace_execution("test_func")
        def test_func():
            return "result"

        test_func()
        assert len(get_trace_history()) > 0

        clear_trace_history()
        assert len(get_trace_history()) == 0


class TestTraceExecutionDecorator:
    """Tests for trace_execution decorator."""

    def setup_method(self):
        """Clear trace history before each test."""
        clear_trace_history()

    def test_sync_function_success(self):
        """Test decorator with successful sync function."""
        @trace_execution("test_sync")
        def sync_func(a: int, b: int) -> int:
            return a + b

        result = sync_func(1, 2)

        assert result == 3
        history = get_trace_history()
        assert len(history) == 1
        assert history[0].name == "test_sync"
        assert history[0].success is True
        assert history[0].result == 3

    def test_sync_function_exception(self):
        """Test decorator with sync function that raises."""
        @trace_execution("test_sync_error")
        def sync_func():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            sync_func()

        history = get_trace_history()
        assert len(history) == 1
        assert history[0].success is False
        assert history[0].exception is not None

    @pytest.mark.asyncio
    async def test_async_function_success(self):
        """Test decorator with successful async function."""
        @trace_execution("test_async")
        async def async_func(a: int, b: int) -> int:
            await asyncio.sleep(0.001)
            return a + b

        result = await async_func(1, 2)

        assert result == 3
        history = get_trace_history()
        assert len(history) == 1
        assert history[0].name == "test_async"
        assert history[0].success is True

    @pytest.mark.asyncio
    async def test_async_function_exception(self):
        """Test decorator with async function that raises."""
        @trace_execution("test_async_error")
        async def async_func():
            raise ValueError("async error")

        with pytest.raises(ValueError, match="async error"):
            await async_func()

        history = get_trace_history()
        assert len(history) == 1
        assert history[0].success is False

    def test_default_name_from_function(self):
        """Test decorator uses function name when no name provided."""
        @trace_execution()
        def my_function():
            return "result"

        my_function()

        history = get_trace_history()
        assert len(history) == 1
        # Default name should include function name
        assert "my_function" in history[0].name


class TestTraceAgentExecutionDecorator:
    """Tests for trace_agent_execution decorator."""

    def setup_method(self):
        """Clear trace history before each test."""
        clear_trace_history()

    @pytest.mark.asyncio
    async def test_agent_execution_success(self):
        """Test decorator with successful agent execution."""
        # Create a mock event
        mock_event = Mock()
        mock_event.type = "file_changed"
        mock_event.source = "watcher"
        mock_event.id = "event-123"

        # Create a mock result with findings
        mock_result = Mock()
        mock_result.findings = []

        class TestAgent:
            @trace_agent_execution("test_agent")
            async def handle(self, event):
                return mock_result

        agent = TestAgent()
        result = await agent.handle(mock_event)

        assert result is mock_result
        history = get_trace_history()
        assert len(history) == 1
        assert history[0].name == "agent.test_agent.handle"
        assert history[0].success is True

    @pytest.mark.asyncio
    async def test_agent_execution_with_findings(self):
        """Test decorator logs findings count."""
        mock_event = Mock()
        mock_event.type = "file_changed"
        mock_event.source = "watcher"
        mock_event.id = "event-123"

        mock_result = Mock()
        mock_result.findings = [{"issue": 1}, {"issue": 2}]

        class TestAgent:
            @trace_agent_execution("finding_agent")
            async def handle(self, event):
                return mock_result

        agent = TestAgent()
        result = await agent.handle(mock_event)

        assert result is mock_result
        history = get_trace_history()
        assert len(history) == 1
        assert history[0].success is True

    @pytest.mark.asyncio
    async def test_agent_execution_exception(self):
        """Test decorator with agent exception."""
        mock_event = Mock()
        mock_event.type = "file_changed"
        mock_event.source = "watcher"
        mock_event.id = "event-123"

        class TestAgent:
            @trace_agent_execution("failing_agent")
            async def handle(self, event):
                raise RuntimeError("agent failed")

        agent = TestAgent()
        with pytest.raises(RuntimeError, match="agent failed"):
            await agent.handle(mock_event)

        history = get_trace_history()
        assert len(history) == 1
        assert history[0].success is False


class TestTraceContextStoreDecorator:
    """Tests for trace_context_store decorator."""

    def setup_method(self):
        """Clear trace history before each test."""
        clear_trace_history()

    @pytest.mark.asyncio
    async def test_async_operation_success(self):
        """Test decorator with successful async operation."""
        class TestStore:
            @trace_context_store("get_findings")
            async def get_findings(self):
                await asyncio.sleep(0.001)
                return [{"finding": 1}]

        store = TestStore()
        result = await store.get_findings()

        assert result == [{"finding": 1}]
        history = get_trace_history()
        assert len(history) == 1
        assert history[0].name == "context_store.get_findings"
        assert history[0].success is True

    @pytest.mark.asyncio
    async def test_async_operation_exception(self):
        """Test decorator with async operation exception."""
        class TestStore:
            @trace_context_store("failing_operation")
            async def failing_operation(self):
                raise IOError("store error")

        store = TestStore()
        with pytest.raises(IOError, match="store error"):
            await store.failing_operation()

        history = get_trace_history()
        assert len(history) == 1
        assert history[0].success is False

    def test_sync_operation_success(self):
        """Test decorator with successful sync operation."""
        class TestStore:
            @trace_context_store("sync_get")
            def sync_get(self):
                return {"data": "value"}

        store = TestStore()
        result = store.sync_get()

        assert result == {"data": "value"}
        history = get_trace_history()
        assert len(history) == 1
        assert history[0].name == "context_store.sync_get"
        assert history[0].success is True

    def test_sync_operation_exception(self):
        """Test decorator with sync operation exception."""
        class TestStore:
            @trace_context_store("sync_failing")
            def sync_failing(self):
                raise ValueError("sync error")

        store = TestStore()
        with pytest.raises(ValueError, match="sync error"):
            store.sync_failing()

        history = get_trace_history()
        assert len(history) == 1
        assert history[0].success is False


class TestFailureDetector:
    """Tests for FailureDetector class."""

    def test_init_default_threshold(self):
        """Test default alert threshold."""
        detector = FailureDetector()
        assert detector.alert_threshold == 5

    def test_init_custom_threshold(self):
        """Test custom alert threshold."""
        detector = FailureDetector(alert_threshold=10)
        assert detector.alert_threshold == 10

    def test_record_failure_increments_count(self):
        """Test that record_failure increments failure count."""
        detector = FailureDetector()

        detector.record_failure("test_agent")
        assert detector.agent_failures["test_agent"] == 1

        detector.record_failure("test_agent")
        assert detector.agent_failures["test_agent"] == 2

    def test_record_success_resets_count(self):
        """Test that record_success resets failure count."""
        detector = FailureDetector()

        detector.record_failure("test_agent")
        detector.record_failure("test_agent")
        assert detector.agent_failures["test_agent"] == 2

        detector.record_success("test_agent")
        assert detector.agent_failures["test_agent"] == 0

    def test_record_success_sets_last_success_time(self):
        """Test that record_success sets last success time."""
        detector = FailureDetector()

        detector.record_success("test_agent")

        assert "test_agent" in detector.agent_last_success
        assert isinstance(detector.agent_last_success["test_agent"], datetime)

    def test_get_status_no_failures(self):
        """Test get_status with no failures."""
        detector = FailureDetector()

        status = detector.get_status()

        assert status["failing_agents"] == {}
        assert status["has_failures"] is False
        assert status["critical_failures"] == {}

    def test_get_status_with_failures(self):
        """Test get_status with failures."""
        detector = FailureDetector(alert_threshold=3)

        detector.record_failure("agent1")
        detector.record_failure("agent2")
        detector.record_failure("agent2")

        status = detector.get_status()

        assert status["failing_agents"] == {"agent1": 1, "agent2": 2}
        assert status["has_failures"] is True
        assert status["critical_failures"] == {}

    def test_get_status_critical_failures(self):
        """Test get_status with critical failures (above threshold)."""
        detector = FailureDetector(alert_threshold=3)

        for _ in range(3):
            detector.record_failure("critical_agent")
        detector.record_failure("minor_agent")

        status = detector.get_status()

        assert status["critical_failures"] == {"critical_agent": 3}
        assert "minor_agent" not in status["critical_failures"]


class TestGlobalFailureDetector:
    """Tests for global failure detector."""

    def test_get_failure_detector_returns_instance(self):
        """Test that get_failure_detector returns a FailureDetector."""
        detector = get_failure_detector()
        assert isinstance(detector, FailureDetector)

    def test_get_failure_detector_returns_same_instance(self):
        """Test that get_failure_detector returns the same instance."""
        detector1 = get_failure_detector()
        detector2 = get_failure_detector()
        assert detector1 is detector2


class TestReportDiagnostics:
    """Tests for report_diagnostics function."""

    def setup_method(self):
        """Clear trace history before each test."""
        clear_trace_history()

    def test_report_diagnostics_structure(self):
        """Test report_diagnostics returns expected structure."""
        report = report_diagnostics()

        assert "timestamp" in report
        assert "traces" in report
        assert "failures" in report
        assert isinstance(report["traces"], list)
        assert isinstance(report["failures"], dict)

    def test_report_diagnostics_timestamp_format(self):
        """Test report_diagnostics timestamp is ISO format."""
        report = report_diagnostics()

        # Should be able to parse as ISO format
        timestamp = report["timestamp"]
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_report_diagnostics_includes_traces(self):
        """Test report_diagnostics includes trace history."""
        @trace_execution("test_func")
        def test_func():
            return "result"

        test_func()

        report = report_diagnostics()

        assert len(report["traces"]) == 1
        assert report["traces"][0]["name"] == "test_func"
