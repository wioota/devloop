"""Debug tracing utilities for agent execution flow.

Provides decorators and utilities for tracing agent execution,
detecting failures, and diagnosing issues.
"""

import asyncio
import functools
import logging
import time
from datetime import datetime, UTC
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class ExecutionTrace:
    """Records execution details for debugging"""

    def __init__(self, name: str, args: tuple = None, kwargs: dict = None):
        self.name = name
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration: Optional[float] = None
        self.result: Any = None
        self.exception: Optional[Exception] = None
        self.success = False

    @property
    def is_running(self) -> bool:
        return self.start_time is not None and self.end_time is None

    @property
    def is_complete(self) -> bool:
        return self.end_time is not None

    def start(self):
        """Mark start of execution"""
        self.start_time = time.time()
        logger.debug(f"[TRACE] {self.name} START")

    def end(self, result: Any = None, exception: Exception = None):
        """Mark end of execution"""
        self.end_time = time.time()
        self.duration = (
            self.end_time - self.start_time if self.start_time is not None else None
        )
        self.result = result
        self.exception = exception
        self.success = exception is None

        if exception:
            logger.error(
                f"[TRACE] {self.name} END (failed after {self.duration:.3f}s): {exception}"
            )
        else:
            logger.debug(f"[TRACE] {self.name} END ({self.duration:.3f}s)")

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary"""
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "success": self.success,
            "error": str(self.exception) if self.exception else None,
        }


# Global trace history (in-memory for now)
_trace_history: list[ExecutionTrace] = []


def get_trace_history(limit: int = 100) -> list[ExecutionTrace]:
    """Get recent execution traces"""
    return _trace_history[-limit:]


def clear_trace_history():
    """Clear trace history"""
    global _trace_history
    _trace_history = []


def trace_execution(name: str = None):
    """Decorator for tracing function execution

    Usage:
        @trace_execution("my_function")
        async def my_func():
            pass
    """

    def decorator(func: Callable) -> Callable:
        trace_name = name or f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            trace = ExecutionTrace(trace_name, args, kwargs)
            trace.start()
            _trace_history.append(trace)

            try:
                result = await func(*args, **kwargs)
                trace.end(result=result)
                return result
            except Exception as e:
                trace.end(exception=e)
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            trace = ExecutionTrace(trace_name, args, kwargs)
            trace.start()
            _trace_history.append(trace)

            try:
                result = func(*args, **kwargs)
                trace.end(result=result)
                return result
            except Exception as e:
                trace.end(exception=e)
                raise

        # Use appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def trace_agent_execution(agent_name: str):
    """Specialized decorator for agent handle() execution"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, event, *args, **kwargs):
            trace_name = f"agent.{agent_name}.handle"
            trace = ExecutionTrace(
                trace_name,
                (event.type, event.source),
                {"event_id": event.id},
            )
            trace.start()
            _trace_history.append(trace)

            try:
                logger.debug(
                    f"[AGENT] {agent_name} processing event: {event.type} from {event.source}"
                )

                result = await func(self, event, *args, **kwargs)

                if hasattr(result, "findings") and result.findings:
                    logger.debug(
                        f"[AGENT] {agent_name} found {len(result.findings)} issues"
                    )

                trace.end(result=result)
                return result

            except Exception as e:
                logger.error(f"[AGENT] {agent_name} failed: {e}")
                trace.end(exception=e)
                raise

        return wrapper

    return decorator


def trace_context_store(operation: str):
    """Trace context store operations"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            trace_name = f"context_store.{operation}"
            trace = ExecutionTrace(trace_name)
            trace.start()
            _trace_history.append(trace)

            try:
                logger.debug(f"[CONTEXT] {operation} starting...")
                result = await func(self, *args, **kwargs)
                logger.debug(f"[CONTEXT] {operation} completed successfully")
                trace.end(result=result)
                return result
            except Exception as e:
                logger.error(f"[CONTEXT] {operation} failed: {e}")
                trace.end(exception=e)
                raise

        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            trace_name = f"context_store.{operation}"
            trace = ExecutionTrace(trace_name)
            trace.start()
            _trace_history.append(trace)

            try:
                logger.debug(f"[CONTEXT] {operation} starting...")
                result = func(self, *args, **kwargs)
                logger.debug(f"[CONTEXT] {operation} completed successfully")
                trace.end(result=result)
                return result
            except Exception as e:
                logger.error(f"[CONTEXT] {operation} failed: {e}")
                trace.end(exception=e)
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class FailureDetector:
    """Detects and reports agent failures"""

    def __init__(self, alert_threshold: int = 5):
        """
        Initialize failure detector

        Args:
            alert_threshold: Number of consecutive failures before alerting
        """
        self.alert_threshold = alert_threshold
        self.agent_failures: Dict[str, int] = {}
        self.agent_last_success: Dict[str, datetime] = {}

    def record_failure(self, agent_name: str):
        """Record a failure for an agent"""
        self.agent_failures[agent_name] = self.agent_failures.get(agent_name, 0) + 1

        failure_count = self.agent_failures[agent_name]

        if failure_count >= self.alert_threshold:
            logger.error(
                f"[FAILURE] Agent '{agent_name}' failed {failure_count} times. "
                f"Agent may be broken and needs investigation."
            )

    def record_success(self, agent_name: str):
        """Record a successful execution"""
        self.agent_failures[agent_name] = 0
        self.agent_last_success[agent_name] = datetime.now(UTC)
        logger.debug(f"[SUCCESS] Agent '{agent_name}' executed successfully")

    def get_status(self) -> Dict[str, Any]:
        """Get overall failure status"""
        failing_agents = {
            name: count for name, count in self.agent_failures.items() if count > 0
        }

        return {
            "failing_agents": failing_agents,
            "has_failures": len(failing_agents) > 0,
            "critical_failures": {
                name: count
                for name, count in failing_agents.items()
                if count >= self.alert_threshold
            },
        }


# Global failure detector
_failure_detector = FailureDetector()


def get_failure_detector() -> FailureDetector:
    """Get the global failure detector"""
    return _failure_detector


def report_diagnostics() -> Dict[str, Any]:
    """Generate diagnostic report"""
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "traces": [t.to_dict() for t in get_trace_history()],
        "failures": _failure_detector.get_status(),
    }
