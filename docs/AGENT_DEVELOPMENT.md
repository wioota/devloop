# Agent Development Guide

Welcome to the DevLoop Agent Development Guide. This guide covers everything you need to create, test, and publish custom agents for the DevLoop ecosystem.

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Agent Architecture](#agent-architecture)
3. [Creating Your First Agent](#creating-your-first-agent)
4. [Agent Lifecycle](#agent-lifecycle)
5. [Event System](#event-system)
6. [Configuration](#configuration)
7. [Best Practices](#best-practices)
8. [Testing](#testing)
9. [Publishing to Marketplace](#publishing-to-marketplace)
10. [Troubleshooting](#troubleshooting)

## Core Concepts

### What is an Agent?

An agent is an autonomous component in DevLoop that:
- **Responds to events** from the development lifecycle (file changes, git operations, test results, etc.)
- **Performs focused work** (linting, formatting, testing, scanning, etc.)
- **Publishes results** back to the system for visibility and downstream processing
- **Operates independently** without blocking developer workflow

### Agent vs. Tool

- **Agent**: Runs asynchronously, responds to events, autonomous decision-making
- **Tool**: Synchronous function called directly by user or other agents, explicit flow control

## Agent Architecture

### Class Hierarchy

```
Agent (ABC)
├── LinterAgent
├── FormatterAgent
├── TypeCheckerAgent
├── SecurityScannerAgent
├── PerformanceProfilerAgent
└── CustomAgent (for marketplace agents)
```

### Core Components

Every agent has:

1. **Name** - Unique identifier (e.g., "linter", "type-checker")
2. **Triggers** - Event patterns it listens for (e.g., "file:save", "git:pre-commit")
3. **Event Handler** - Async method that processes events
4. **Result Publishing** - Returns structured results

### Agent Lifecycle

```
Agent Created
    ↓
start() called - subscribes to triggers
    ↓
Event matches trigger → handle() called
    ↓
Result published back to event bus
    ↓
stop() called - unsubscribes from triggers
    ↓
Agent terminated
```

## Creating Your First Agent

### Simple Example: Echo Agent

Here's the simplest possible agent that echoes all events:

```python
"""Echo agent - logs received events."""

from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event


class EchoAgent(Agent):
    """Agent that echoes all events it receives."""

    async def handle(self, event: Event) -> AgentResult:
        """Echo the event."""
        message = f"Received {event.type} from {event.source}"
        
        # Log additional details if available
        if "path" in event.payload:
            message += f": {event.payload['path']}"
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0,
            message=message,
            data=event.payload,
        )
```

### Medium Example: File Counter Agent

Count lines in modified files:

```python
"""File counter agent - counts lines in modified files."""

from pathlib import Path
from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event


class FileCounterAgent(Agent):
    """Counts lines in modified files."""

    async def handle(self, event: Event) -> AgentResult:
        """Count lines in the modified file."""
        if "path" not in event.payload:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0,
                message="No file path in event",
            )
        
        file_path = event.payload["path"]
        
        try:
            path = Path(file_path)
            if not path.exists():
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    duration=0,
                    message=f"File not found: {file_path}",
                )
            
            # Count lines
            line_count = len(path.read_text().splitlines())
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0.01,
                message=f"{file_path}: {line_count} lines",
                data={"file": file_path, "lines": line_count},
            )
        
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0,
                error=str(e),
            )
```

### Advanced Example: Custom Linter Agent

Create a specialized linter for your project:

```python
"""Custom linter agent - checks for project-specific patterns."""

import re
from pathlib import Path
from typing import List, Tuple
from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event


class CustomLinterConfig:
    """Configuration for custom linter."""
    
    def __init__(self, patterns: List[Tuple[str, str]]):
        """Initialize with regex patterns.
        
        Args:
            patterns: List of (pattern, error_message) tuples
        """
        self.patterns = patterns
        self.compiled = [(re.compile(p), msg) for p, msg in patterns]


class CustomLinterAgent(Agent):
    """Checks files against custom patterns."""
    
    def __init__(self, name: str, triggers: List[str], config: CustomLinterConfig, **kwargs):
        super().__init__(name, triggers, **kwargs)
        self.config = config
    
    async def handle(self, event: Event) -> AgentResult:
        """Check file against patterns."""
        if "path" not in event.payload:
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message="No file path",
                data={"issues": []},
            )
        
        file_path = event.payload["path"]
        path = Path(file_path)
        
        if not path.exists() or not path.is_file():
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message=f"Skipped (not a file): {file_path}",
                data={"issues": []},
            )
        
        try:
            content = path.read_text()
        except (UnicodeDecodeError, IsADirectoryError):
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message=f"Skipped: {file_path}",
                data={"issues": []},
            )
        
        # Check patterns
        issues = []
        for pattern, message in self.config.compiled:
            matches = pattern.finditer(content)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    "line": line_num,
                    "column": match.start() - content.rfind('\n', 0, match.start()),
                    "message": message,
                })
        
        success = len(issues) == 0
        message = f"Found {len(issues)} issues" if issues else "No issues found"
        
        return AgentResult(
            agent_name=self.name,
            success=success,
            duration=0.05,
            message=message,
            data={"file": file_path, "issues": issues},
        )
```

## Event System

### Event Structure

Every event has:

```python
@dataclass
class Event:
    type: str                      # e.g., "file:save", "git:commit"
    payload: Dict[str, Any]        # Event-specific data
    source: str                    # Who generated the event
    timestamp: Optional[datetime]  # When it happened
```

### Common Event Types

| Event Type | Payload | Description |
|-----------|---------|-------------|
| `file:save` | `{"path": str}` | File saved |
| `file:create` | `{"path": str}` | File created |
| `file:delete` | `{"path": str}` | File deleted |
| `git:pre-commit` | `{"files": [str]}` | Before commit |
| `git:post-commit` | `{"commit": str}` | After commit |
| `test:complete` | `{"passed": bool, ...}` | Test run finished |
| `build:complete` | `{"success": bool, ...}` | Build finished |

### Event Matching

Triggers support patterns:

- Exact: `"file:save"` - matches exactly
- Wildcard: `"file:*"` - matches file:save, file:create, etc.
- Prefix: `"git:"` - matches all git events

### Subscribing to Events

Define triggers when creating your agent:

```python
# Listen to specific events
agent = MyAgent(
    name="my-linter",
    triggers=["file:save", "git:pre-commit"],
    ...
)
```

## Configuration

### Built-in Agent Configuration

Agents are configured in `.devloop/agents.json`:

```json
{
  "enabled": true,
  "agents": {
    "my-linter": {
      "enabled": true,
      "module": "my_package.my_linter",
      "class": "MyLinterAgent",
      "triggers": ["file:save"],
      "config": {
        "patterns": [
          ["console\\.log.*", "Remove debug logs"],
          ["TODO.*", "Address TODOs before commit"]
        ]
      }
    }
  }
}
```

### Custom Configuration

Pass configuration to your agent:

```python
class MyAgentConfig:
    """Configuration for my agent."""
    
    def __init__(self, strict_mode: bool = False, timeout: float = 5.0):
        self.strict_mode = strict_mode
        self.timeout = timeout


class MyAgent(Agent):
    def __init__(self, name: str, triggers: List[str], config: MyAgentConfig, **kwargs):
        super().__init__(name, triggers, **kwargs)
        self.config = config
    
    async def handle(self, event: Event) -> AgentResult:
        # Use self.config.strict_mode, self.config.timeout
        ...
```

## Best Practices

### 1. Keep Agents Focused

Each agent should do one thing well:

❌ **Bad** - Multi-tool agent:
```python
class DoEverythingAgent(Agent):
    async def handle(self, event: Event) -> AgentResult:
        # Lints, formats, checks types, runs tests, ...
```

✅ **Good** - Focused agent:
```python
class LinterAgent(Agent):
    async def handle(self, event: Event) -> AgentResult:
        # Only lints
```

### 2. Handle Errors Gracefully

Always handle exceptions and return clear error messages:

```python
async def handle(self, event: Event) -> AgentResult:
    try:
        # ... work ...
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=elapsed,
            message="Success",
            data={"results": ...}
        )
    except FileNotFoundError as e:
        return AgentResult(
            agent_name=self.name,
            success=False,
            duration=elapsed,
            error=f"File not found: {e}"
        )
    except Exception as e:
        self.logger.error(f"Unexpected error: {e}", exc_info=True)
        return AgentResult(
            agent_name=self.name,
            success=False,
            duration=elapsed,
            error=str(e)
        )
```

### 3. Be Async-Aware

Agents run asynchronously. Use async/await properly:

```python
# ✅ Good - async operation
async def handle(self, event: Event) -> AgentResult:
    result = await some_async_operation()
    return AgentResult(...)

# ❌ Bad - blocking operation
async def handle(self, event: Event) -> AgentResult:
    time.sleep(5)  # Blocks event loop!
    return AgentResult(...)
```

### 4. Track Performance

Always measure and report execution time:

```python
import time

async def handle(self, event: Event) -> AgentResult:
    start = time.time()
    
    # ... do work ...
    
    duration = time.time() - start
    
    return AgentResult(
        agent_name=self.name,
        success=True,
        duration=duration,  # Always include!
        message="Done",
    )
```

### 5. Respect File Paths

Handle various path formats robustly:

```python
from pathlib import Path

async def handle(self, event: Event) -> AgentResult:
    # Always use Path for flexibility
    file_path = Path(event.payload.get("path", "")).resolve()
    
    # Check existence and type
    if not file_path.exists():
        return AgentResult(...)
    
    if not file_path.is_file():
        return AgentResult(...)
    
    # Read safely
    try:
        content = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # Binary file, skip
        return AgentResult(...)
```

### 6. Filter Intelligently

Don't process every event - use file patterns:

```python
async def handle(self, event: Event) -> AgentResult:
    file_path = event.payload.get("path", "")
    
    # Skip non-Python files
    if not file_path.endswith('.py'):
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0,
            message="Skipped (not Python)",
        )
    
    # Skip generated files
    if "generated" in file_path or ".min.js" in file_path:
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0,
            message="Skipped (generated)",
        )
    
    # Now process
    ...
```

### 7. Provide Actionable Results

Results should help developers understand and fix issues:

```python
# ✅ Good result
return AgentResult(
    agent_name=self.name,
    success=False,
    duration=0.5,
    message="2 type errors found",
    data={
        "issues": [
            {
                "file": "src/main.py",
                "line": 42,
                "column": 15,
                "message": "Incompatible types: str cannot be assigned to int",
                "hint": "Add a type cast: int(value)"
            }
        ]
    }
)

# ❌ Poor result
return AgentResult(
    agent_name=self.name,
    success=False,
    duration=0.5,
    message="Error",
    error="mypy failed"
)
```

## Testing

### Unit Testing

Test your agent's `handle()` method:

```python
import pytest
from unittest.mock import Mock, AsyncMock
from devloop.core.event import Event, EventBus


@pytest.mark.asyncio
async def test_agent_handles_valid_event():
    """Test agent processes valid events."""
    # Setup
    event_bus = AsyncMock(spec=EventBus)
    agent = MyAgent(
        name="test-agent",
        triggers=["file:save"],
        event_bus=event_bus,
    )
    
    # Create test event
    event = Event(
        type="file:save",
        source="fs",
        payload={"path": "/tmp/test.py"},
    )
    
    # Execute
    result = await agent.handle(event)
    
    # Verify
    assert result.success is True
    assert result.agent_name == "test-agent"
    assert result.duration >= 0


@pytest.mark.asyncio
async def test_agent_handles_missing_file():
    """Test agent handles missing files gracefully."""
    event_bus = AsyncMock(spec=EventBus)
    agent = MyAgent(
        name="test-agent",
        triggers=["file:save"],
        event_bus=event_bus,
    )
    
    event = Event(
        type="file:save",
        source="fs",
        payload={"path": "/nonexistent/file.py"},
    )
    
    result = await agent.handle(event)
    
    assert result.success is False
    assert "not found" in result.error.lower()
```

### Integration Testing

Test agent with actual events:

```python
@pytest.mark.asyncio
async def test_agent_full_lifecycle(tmp_path):
    """Test agent start, process events, and stop."""
    event_bus = EventBus()
    agent = MyAgent(
        name="test-agent",
        triggers=["file:save"],
        event_bus=event_bus,
    )
    
    # Create test file
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')")
    
    # Start agent
    await agent.start()
    
    # Emit event
    event = Event(
        type="file:save",
        source="fs",
        payload={"path": str(test_file)},
    )
    await event_bus.emit(event)
    
    # Wait for processing
    await asyncio.sleep(0.1)
    
    # Stop agent
    await agent.stop()
    
    # Verify it processed the event
    # (check logs or results)
```

## Publishing to Marketplace

### Preparing Your Agent

1. **Structure your code**:
```
my-agent/
├── README.md
├── pyproject.toml
├── src/
│   └── my_agent/
│       ├── __init__.py
│       ├── agent.py
│       └── config.py
└── tests/
    └── test_agent.py
```

2. **Add metadata** to `pyproject.toml`:
```toml
[project]
name = "my-devloop-agent"
version = "1.0.0"
description = "My custom DevLoop agent"

[project.entry-points."devloop.agents"]
my-agent = "my_agent.agent:MyAgent"
```

3. **Write comprehensive README** with:
   - What the agent does
   - Installation instructions
   - Configuration example
   - Trigger patterns
   - Result schema

4. **Test thoroughly**:
```bash
pytest tests/
```

### Publishing

```bash
devloop publish my-agent --registry marketplace
```

This will:
- Validate your agent structure
- Run your tests
- Build the package
- Publish to DevLoop marketplace
- Generate documentation

### Marketplace Listing

After publishing, your agent appears in:
- DevLoop marketplace UI
- `devloop search` results
- Community agent directory

Include:
- **Icon** (128x128 PNG)
- **Screenshots** (of results/output)
- **Example configuration**
- **Sample event triggers**

## Troubleshooting

### Agent Not Triggering

**Symptom**: Agent never seems to run.

**Solutions**:
1. Check triggers are correct: `bd show <agent-config>`
2. Verify events are being emitted: `devloop debug events`
3. Check agent is enabled: `devloop status`
4. Look at logs: `devloop logs <agent-name>`

### Agent Crashing

**Symptom**: Agent stops running after an error.

**Solutions**:
1. Wrap code in try/except
2. Always return `AgentResult` (never raise)
3. Check for async issues (missing `await`)
4. View full error: `devloop logs <agent-name> --full`

### Performance Issues

**Symptom**: Agent is slow or blocks other work.

**Solutions**:
1. Don't do blocking I/O (use async)
2. Set resource limits: Configure in `.devloop/agents.json`
3. Add timeout for long operations
4. Skip files you don't need to process

### Testing Issues

**Symptom**: Tests pass locally but fail in CI.

**Solutions**:
1. Use `tmp_path` fixture for file operations (not hardcoded paths)
2. Mock external dependencies
3. Use `@pytest.mark.asyncio` for async tests
4. Check file permissions and encoding

## Next Steps

- [Agent API Reference](./AGENT_API_REFERENCE.md) - Complete API documentation
- [Marketplace Guide](./MARKETPLACE_GUIDE.md) - Publishing and discovery
- [Examples Repository](https://github.com/wioota/devloop-agent-examples) - Real-world examples
- [Community Forum](https://forum.devloop.dev) - Get help and share agents
