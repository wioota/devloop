# Agent API Reference

Complete API documentation for DevLoop Agent development.

## Table of Contents

1. [Core Classes](#core-classes)
2. [Event System](#event-system)
3. [Agent Result](#agent-result)
4. [Base Agent Class](#base-agent-class)
5. [Advanced Features](#advanced-features)
6. [Built-in Agents](#built-in-agents)

## Core Classes

### Agent

Base class for all agents.

#### Class Definition

```python
class Agent(ABC):
    """Base agent class with performance monitoring and feedback."""
    
    def __init__(
        self,
        name: str,
        triggers: List[str],
        event_bus: EventBus,
        feedback_api: Optional[FeedbackAPI] = None,
        performance_monitor: Optional[PerformanceMonitor] = None,
        resource_tracker: Optional[AgentResourceTracker] = None,
    ):
```

#### Constructor Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | `str` | Yes | Unique agent identifier (e.g., "linter", "type-checker") |
| `triggers` | `List[str]` | Yes | Event patterns to listen for (e.g., `["file:save"]`) |
| `event_bus` | `EventBus` | Yes | Event bus for subscribing to events |
| `feedback_api` | `FeedbackAPI` | No | API for performance feedback tracking |
| `performance_monitor` | `PerformanceMonitor` | No | Performance monitoring system |
| `resource_tracker` | `AgentResourceTracker` | No | Resource usage tracking |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Agent name |
| `triggers` | `List[str]` | Subscribed event patterns |
| `event_bus` | `EventBus` | Event bus instance |
| `enabled` | `bool` | Whether agent is enabled (can be toggled at runtime) |
| `logger` | `logging.Logger` | Agent logger (e.g., `logging.getLogger("agent.linter")`) |

#### Methods

##### `async def handle(event: Event) -> AgentResult` (Abstract)

Handle an event. **Must be implemented by subclasses.**

**Parameters:**
- `event` (`Event`): The event to process

**Returns:**
- `AgentResult`: Result of processing

**Example:**
```python
async def handle(self, event: Event) -> AgentResult:
    """Implement your agent logic here."""
    file_path = event.payload.get("path")
    
    # Process the event
    try:
        result = await process_file(file_path)
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=result.duration,
            message=f"Processed {file_path}",
            data={"result": result.data}
        )
    except Exception as e:
        return AgentResult(
            agent_name=self.name,
            success=False,
            duration=0,
            error=str(e)
        )
```

##### `async def start() -> None`

Start the agent and subscribe to configured triggers.

**Example:**
```python
agent = MyAgent(...)
await agent.start()  # Now listening to events
```

##### `async def stop() -> None`

Stop the agent and unsubscribe from all triggers.

**Example:**
```python
await agent.stop()  # No longer listening to events
```

---

## Event System

### Event

Represents a development lifecycle event.

#### Class Definition

```python
@dataclass
class Event:
    """Development lifecycle event."""
    type: str                              # Event type identifier
    payload: Dict[str, Any]                # Event-specific data
    source: str                            # Who generated the event
    timestamp: Optional[datetime] = None   # When it occurred
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `type` | `str` | Event type (e.g., "file:save", "git:commit") |
| `payload` | `Dict[str, Any]` | Event data (structure depends on event type) |
| `source` | `str` | Source that generated event (e.g., "fs", "git", "test") |
| `timestamp` | `Optional[datetime]` | When event occurred (auto-set if not provided) |

#### Event Type Patterns

Events support pattern matching in triggers:

| Pattern | Matches |
|---------|---------|
| `"file:save"` | Exact event type `file:save` |
| `"file:*"` | Any file event (file:save, file:create, etc.) |
| `"*:save"` | Any save event |
| `"*"` | All events |

#### Common Event Types

##### File Events

| Type | Payload | Source |
|------|---------|--------|
| `file:save` | `{"path": str, "size": int}` | `fs` |
| `file:create` | `{"path": str}` | `fs` |
| `file:delete` | `{"path": str}` | `fs` |
| `file:rename` | `{"old_path": str, "new_path": str}` | `fs` |

##### Git Events

| Type | Payload | Source |
|------|---------|--------|
| `git:pre-commit` | `{"files": List[str]}` | `git` |
| `git:post-commit` | `{"commit_hash": str, "message": str}` | `git` |
| `git:pre-push` | `{"branch": str, "commits": List[str]}` | `git` |
| `git:post-merge` | `{"from_branch": str, "conflict_files": List[str]}` | `git` |

##### Process Events

| Type | Payload | Source |
|------|---------|--------|
| `process:start` | `{"pid": int, "command": str}` | `process` |
| `process:exit` | `{"pid": int, "exit_code": int, "duration": float}` | `process` |
| `test:start` | `{"test_name": str, "framework": str}` | `test` |
| `test:complete` | `{"passed": bool, "duration": float, "failures": List[str]}` | `test` |

### EventBus

Central event pub/sub system.

#### Methods

##### `async def subscribe(pattern: str, queue: asyncio.Queue) -> None`

Subscribe a queue to events matching a pattern.

**Parameters:**
- `pattern` (`str`): Event pattern (e.g., "file:save", "file:*")
- `queue` (`asyncio.Queue`): Queue to receive events

**Example:**
```python
queue = asyncio.Queue()
await event_bus.subscribe("file:save", queue)
event = await queue.get()  # Wait for next file:save event
```

##### `async def unsubscribe(pattern: str, queue: asyncio.Queue) -> None`

Unsubscribe a queue from a pattern.

**Parameters:**
- `pattern` (`str`): Event pattern
- `queue` (`asyncio.Queue`): Queue to unsubscribe

##### `async def emit(event: Event) -> None`

Emit an event to all subscribed agents.

**Parameters:**
- `event` (`Event`): Event to publish

**Example:**
```python
event = Event(
    type="file:save",
    source="fs",
    payload={"path": "/home/user/project/main.py"}
)
await event_bus.emit(event)
```

---

## Agent Result

### AgentResult

Result of agent processing.

#### Class Definition

```python
@dataclass
class AgentResult:
    """Agent execution result."""
    agent_name: str           # Name of the agent
    success: bool             # Whether execution succeeded
    duration: float           # Execution time in seconds
    message: str = ""         # Human-readable message
    data: Dict[str, Any] | None = None  # Result data
    error: str | None = None  # Error message (if failed)
```

#### Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `agent_name` | `str` | Yes | Name of agent (should match `self.name`) |
| `success` | `bool` | Yes | Whether execution succeeded |
| `duration` | `float` | Yes | Time taken (seconds, must be ≥ 0) |
| `message` | `str` | No | Human-readable summary (default: "") |
| `data` | `Dict[str, Any]` | No | Structured result data |
| `error` | `str` | No | Error message (if `success=False`) |

#### Validation

AgentResult validates on creation:

```python
# ✅ Valid
AgentResult(
    agent_name="linter",
    success=True,
    duration=0.5,
    message="Found 2 issues",
    data={"issues": [...]}
)

# ❌ Invalid - missing agent_name
AgentResult(
    success=True,
    duration=0.5,
)
# Raises: ValueError("agent_name cannot be empty")

# ❌ Invalid - negative duration
AgentResult(
    agent_name="linter",
    success=True,
    duration=-0.5,
)
# Raises: ValueError("duration must be non-negative")

# ❌ Invalid - duration not a number
AgentResult(
    agent_name="linter",
    success=True,
    duration="slow",
)
# Raises: TypeError("duration must be a number")
```

#### Result Examples

##### Success Case

```python
return AgentResult(
    agent_name="linter",
    success=True,
    duration=0.42,
    message="No issues found",
    data={
        "files_checked": 15,
        "issues": []
    }
)
```

##### Failure Case

```python
return AgentResult(
    agent_name="type-checker",
    success=False,
    duration=0.15,
    error="mypy failed: type mismatch in line 42",
    data={
        "type_errors": [
            {
                "file": "src/main.py",
                "line": 42,
                "message": "str not compatible with int"
            }
        ]
    }
)
```

##### Skipped/Neutral Case

```python
return AgentResult(
    agent_name="formatter",
    success=True,
    duration=0.01,
    message="Skipped: generated file",
    data={"skipped": True}
)
```

---

## Base Agent Class

### Common Pattern: Configuration Class

Best practice is to create a configuration class:

```python
from dataclasses import dataclass
from typing import List


@dataclass
class MyAgentConfig:
    """Configuration for MyAgent."""
    
    # Required config
    enabled: bool = True
    
    # Optional config with defaults
    timeout: float = 5.0
    max_issues: int = 100
    patterns: List[str] = None
    
    def __post_init__(self):
        """Validate configuration."""
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        
        if self.patterns is None:
            self.patterns = []


class MyAgent(Agent):
    """Custom agent with configuration."""
    
    def __init__(
        self,
        name: str,
        triggers: List[str],
        config: MyAgentConfig,
        **kwargs
    ):
        super().__init__(name, triggers, **kwargs)
        self.config = config
    
    async def handle(self, event: Event) -> AgentResult:
        """Process event using configuration."""
        # Use self.config here
        ...
```

### Common Pattern: File Path Handling

```python
from pathlib import Path


async def handle(self, event: Event) -> AgentResult:
    """Handle event with robust file path handling."""
    
    # Extract and validate path
    file_path_str = event.payload.get("path")
    if not file_path_str:
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0,
            message="No file path in event",
        )
    
    # Convert to Path object
    file_path = Path(file_path_str).resolve()
    
    # Check if exists
    if not file_path.exists():
        return AgentResult(
            agent_name=self.name,
            success=False,
            duration=0,
            error=f"File not found: {file_path}",
        )
    
    # Check if it's a file (not directory)
    if not file_path.is_file():
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0,
            message=f"Skipped: not a file",
        )
    
    # Read file safely
    try:
        content = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0,
            message=f"Skipped: binary file",
        )
    except Exception as e:
        return AgentResult(
            agent_name=self.name,
            success=False,
            duration=0,
            error=str(e),
        )
    
    # Process content
    ...
```

### Common Pattern: Performance Tracking

```python
import time


async def handle(self, event: Event) -> AgentResult:
    """Handle event with performance tracking."""
    
    start_time = time.time()
    
    try:
        # Do work
        result = await do_work()
        
        duration = time.time() - start_time
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=duration,
            message=f"Done in {duration:.2f}s",
            data=result,
        )
    
    except Exception as e:
        duration = time.time() - start_time
        
        self.logger.error(f"Error: {e}", exc_info=True)
        
        return AgentResult(
            agent_name=self.name,
            success=False,
            duration=duration,
            error=str(e),
        )
```

---

## Advanced Features

### Performance Monitoring

The base `Agent` class automatically monitors performance if a `PerformanceMonitor` is provided:

```python
from devloop.core.performance import PerformanceMonitor

monitor = PerformanceMonitor()
agent = MyAgent(
    name="my-agent",
    triggers=["file:save"],
    event_bus=event_bus,
    performance_monitor=monitor,
)

# Metrics are automatically collected
# Access with: monitor.get_metrics("agent.my-agent.handle")
```

### Feedback Integration

Provide feedback about agent results:

```python
from devloop.core.feedback import FeedbackAPI

feedback = FeedbackAPI()
agent = MyAgent(
    name="my-agent",
    triggers=["file:save"],
    event_bus=event_bus,
    feedback_api=feedback,
)

# After handling events, provide feedback:
await feedback.provide_feedback(
    agent_name="my-agent",
    event_type="file:save",
    result_quality="good",  # good, bad, neutral
    notes="Result was accurate and helpful"
)
```

### Resource Tracking

Track resource usage (CPU, memory):

```python
from devloop.core.performance import AgentResourceTracker

tracker = AgentResourceTracker()
agent = MyAgent(
    name="my-agent",
    triggers=["file:save"],
    event_bus=event_bus,
    resource_tracker=tracker,
)

# Resource usage is automatically tracked
# Access with: tracker.get_agent_stats("my-agent")
```

### Logging

Use the built-in logger:

```python
async def handle(self, event: Event) -> AgentResult:
    self.logger.debug(f"Processing: {event.type}")
    
    try:
        result = await process(event)
        self.logger.info(f"Success: {result.message}")
        return AgentResult(...)
    except Exception as e:
        self.logger.error(f"Failed: {e}", exc_info=True)
        return AgentResult(...)
```

---

## Built-in Agents

### LinterAgent

Run linters on code files.

**Class:** `devloop.agents.linter.LinterAgent`

**Configuration:**
```python
class LinterConfig:
    linters: List[str]           # ["ruff", "eslint", "flake8"]
    file_patterns: List[str]     # ["**/*.py", "**/*.js"]
    debounce: float = 0.5        # Debounce time (seconds)
    timeout: float = 30.0        # Timeout per file
```

**Triggers:** `["file:save"]`

**Result Data:**
```python
{
    "file": str,
    "issues": [
        {
            "line": int,
            "column": int,
            "code": str,
            "message": str,
            "severity": "error" | "warning",
        }
    ]
}
```

### FormatterAgent

Auto-format code files.

**Class:** `devloop.agents.formatter.FormatterAgent`

**Configuration:**
```python
class FormatterConfig:
    formatters: List[str]        # ["black", "prettier"]
    file_patterns: List[str]     # ["**/*.py", "**/*.js"]
    auto_fix: bool = True        # Apply fixes automatically
```

**Triggers:** `["file:save"]`

**Result Data:**
```python
{
    "file": str,
    "modified": bool,
    "lines_changed": int,
}
```

### TypeCheckerAgent

Run type checkers on code.

**Class:** `devloop.agents.type_checker.TypeCheckerAgent`

**Configuration:**
```python
class TypeCheckerConfig:
    checker: str = "mypy"        # "mypy", "pyright", "tsserver"
    strict: bool = False
    timeout: float = 30.0
```

**Triggers:** `["file:save", "git:pre-commit"]`

**Result Data:**
```python
{
    "file": str,
    "type_errors": [
        {
            "line": int,
            "column": int,
            "message": str,
        }
    ]
}
```

### SecurityScannerAgent

Scan for security vulnerabilities.

**Class:** `devloop.agents.security_scanner.SecurityScannerAgent`

**Configuration:**
```python
class SecurityConfig:
    scanner: str = "bandit"      # "bandit", "semgrep"
    severity: str = "medium"     # "low", "medium", "high"
```

**Triggers:** `["file:save", "git:pre-commit"]`

**Result Data:**
```python
{
    "file": str,
    "vulnerabilities": [
        {
            "line": int,
            "code": str,
            "severity": str,
            "message": str,
            "fix": str,
        }
    ]
}
```

---

## Type Hints

All agents should use proper type hints:

```python
from typing import Any, Dict, List, Optional
from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event


class MyAgent(Agent):
    """Agent with proper type hints."""
    
    async def handle(self, event: Event) -> AgentResult:
        """Process an event."""
        payload: Dict[str, Any] = event.payload
        file_path: Optional[str] = payload.get("path")
        
        results: List[Dict[str, Any]] = []
        
        # ... process ...
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0.5,
            data={"results": results}
        )
```

---

## Constants and Enums

### Event Sources

```python
EVENT_SOURCES = {
    "fs": "Filesystem events",
    "git": "Git operations",
    "test": "Test runner",
    "build": "Build system",
    "process": "External process",
    "system": "System events",
}
```

### Result Severity Levels

```python
SEVERITY = {
    "error": 0,      # Must be fixed
    "warning": 1,    # Should be addressed
    "info": 2,       # For reference
    "hint": 3,       # Nice to know
}
```

---

## See Also

- [Agent Development Guide](./AGENT_DEVELOPMENT.md) - Tutorial and examples
- [Marketplace Guide](./MARKETPLACE_GUIDE.md) - Publishing agents
- [Event System Details](./EVENT_SYSTEM.md) - Deep dive on events
