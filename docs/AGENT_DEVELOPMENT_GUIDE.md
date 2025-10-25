# Agent Development Guide

Complete guide for developing new agents in the claude-agents system.

## Table of Contents

1. [Overview](#overview)
2. [Agent Basics](#agent-basics)
3. [Creating a New Agent](#creating-a-new-agent)
4. [AgentResult Requirements](#agentresult-requirements)
5. [Configuration Patterns](#configuration-patterns)
6. [Testing Your Agent](#testing-your-agent)
7. [Claude Code Integration](#claude-code-integration)
8. [Best Practices](#best-practices)
9. [Common Pitfalls](#common-pitfalls)
10. [Examples](#examples)

## Overview

Agents in claude-agents are autonomous background processes that monitor filesystem events and perform automated code quality checks. Each agent:

- Responds to specific event triggers (file:modified, file:created, etc.)
- Executes asynchronously without blocking development workflow
- Produces standardized results for Claude Code integration
- Writes findings to context store for coding agent consumption

## Agent Basics

### Agent Lifecycle

1. **Initialization**: Agent is configured and registered with AgentManager
2. **Start**: Agent subscribes to event triggers and begins listening
3. **Event Processing**: Agent receives events, processes them, and produces results
4. **Result Publication**: Results are published as events and written to context store
5. **Stop**: Agent unsubscribes from events and cleans up

### Core Components

- **Agent Class**: Base class providing event loop and lifecycle management
- **AgentResult**: Standardized result format with validation
- **EventBus**: Pub/sub system for inter-agent communication
- **ContextStore**: Persistent storage for agent findings

## Creating a New Agent

### Step 1: Define Agent Structure

```python
from claude_agents.core.agent import Agent, AgentResult
from claude_agents.core.event import Event
from claude_agents.core.context_store import context_store
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class MyAgentConfig:
    """Configuration for MyAgent."""

    enabled_tools: List[str] = None
    threshold: int = 10
    exclude_patterns: List[str] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.enabled_tools is None:
            self.enabled_tools = ["default-tool"]
        if self.exclude_patterns is None:
            self.exclude_patterns = ["test_*", "*_test.py"]


class MyAgent(Agent):
    """Agent that does something useful."""

    def __init__(self, config: Dict[str, Any], event_bus):
        super().__init__(
            "my-agent",  # Agent name
            ["file:modified", "file:created"],  # Event triggers
            event_bus
        )
        self.config = MyAgentConfig(**config)
```

### Step 2: Implement Handle Method

```python
async def handle(self, event: Event) -> AgentResult:
    """Handle file change events."""
    try:
        # Extract file path from event
        file_path = event.payload.get("path")
        if not file_path:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0.0,
                message="No file path in event"
            )

        # Check if file exists
        path = Path(file_path)
        if not path.exists():
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0.0,
                message=f"File does not exist: {file_path}"
            )

        # Perform agent-specific processing
        results = await self._process_file(path)

        # Create result with all required parameters
        agent_result = AgentResult(
            agent_name=self.name,
            success=True,
            duration=0.0,  # Will be updated by Agent base class
            message=f"Processed {path.name}",
            data={
                "file": str(path),
                "results": results
            }
        )

        # Write to context store for Claude Code integration
        context_store.write_finding(agent_result)

        return agent_result

    except Exception as e:
        self.logger.error(f"Error processing {file_path}: {e}", exc_info=True)
        return AgentResult(
            agent_name=self.name,
            success=False,
            duration=0.0,
            message=f"Processing failed: {str(e)}",
            error=str(e)
        )
```

### Step 3: Register Agent

Add your agent to `src/claude_agents/core/config.py`:

```python
AGENT_REGISTRY = {
    "my-agent": "claude_agents.agents.my_agent.MyAgent",
    # ... other agents
}

AGENT_CONFIGS = {
    "my-agent": {
        "enabled": True,
        "triggers": ["file:modified", "file:created"],
        "config": {
            "enabled_tools": ["default-tool"],
            "threshold": 10,
            "exclude_patterns": ["test_*", "*_test.py"]
        }
    },
    # ... other configs
}
```

## AgentResult Requirements

### **CRITICAL**: All Required Parameters

**AgentResult requires these positional parameters:**

```python
AgentResult(
    agent_name="my-agent",  # REQUIRED: string, non-empty
    success=True,           # REQUIRED: boolean
    duration=0.0,           # REQUIRED: float/int, non-negative
    message="",             # Optional: string (defaults to "")
    data=None,              # Optional: dict or None
    error=None              # Optional: string or None
)
```

### Validation Rules

The `AgentResult.__post_init__` validates all parameters:

1. **agent_name**: Must be non-empty string
2. **success**: Must be boolean (not truthy value)
3. **duration**: Must be non-negative number
   - **Common mistake**: Forgetting duration parameter
   - Error message includes helpful hint
4. **message**: Must be string (can be empty)
5. **data**: Must be dict or None (not list/tuple/other)
6. **error**: Must be string or None

### Early Return Pattern

For early returns (skipped files, excluded patterns, etc.), always include `duration=0.0`:

```python
# ✓ CORRECT
return AgentResult(
    agent_name=self.name,
    success=True,
    duration=0.0,  # Required!
    message="Skipped non-Python file"
)

# ✗ WRONG - Missing duration parameter
return AgentResult(
    agent_name=self.name,
    success=True,
    message="Skipped non-Python file"
)
```

### Exception Handling Pattern

Always include `duration=0.0` and `error` field in exception handlers:

```python
except Exception as e:
    return AgentResult(
        agent_name=self.name,
        success=False,
        duration=0.0,  # Required!
        message=f"Failed: {str(e)}",
        error=str(e)  # Capture full error
    )
```

## Configuration Patterns

### Dataclass Configuration

**MANDATORY**: Use dataclass with `__post_init__` for validation:

```python
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AgentConfig:
    """Agent configuration with validation."""

    # Required fields with no defaults
    required_param: str

    # Optional fields with defaults
    threshold: int = 10
    patterns: List[str] = None

    def __post_init__(self):
        """Validate and initialize defaults."""
        # Validate required fields
        if not self.required_param:
            raise ValueError("required_param cannot be empty")

        # Initialize mutable defaults
        if self.patterns is None:
            self.patterns = []

        # Validate constraints
        if self.threshold < 0:
            raise ValueError("threshold must be non-negative")
```

### Snake Case Convention

**IMPORTANT**: Always use snake_case for configuration keys:

```python
# ✓ CORRECT
config = {
    "enabled_tools": ["mypy"],
    "complexity_threshold": 10,
    "min_lines_threshold": 50
}

# ✗ WRONG - camelCase causes errors
config = {
    "enabledTools": ["mypy"],
    "complexityThreshold": 10,
    "minLinesThreshold": 50
}
```

## Testing Your Agent

### Unit Test Structure

Create tests in `tests/unit/agents/test_my_agent.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from claude_agents.agents.my_agent import MyAgent, MyAgentConfig
from claude_agents.core.event import Event


class TestMyAgentConfig:
    """Test agent configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MyAgentConfig(required_param="value")

        assert config.required_param == "value"
        assert config.threshold == 10
        assert config.patterns == []


class TestMyAgent:
    """Test agent functionality."""

    @pytest.fixture
    def agent(self):
        """Create agent for testing."""
        config = {
            "required_param": "value",
            "threshold": 10
        }
        return MyAgent(config, MagicMock())

    def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.name == "my-agent"
        assert "file:modified" in agent.triggers
        assert isinstance(agent.config, MyAgentConfig)

    @pytest.mark.asyncio
    async def test_handle_missing_path(self, agent):
        """Test handling event without file path."""
        event = Event(
            type="file:modified",
            payload={},  # No path!
            source="test"
        )

        result = await agent.handle(event)

        assert result.success is False
        assert "No file path" in result.message
        assert result.duration == 0.0  # Early return

    @pytest.mark.asyncio
    async def test_handle_valid_file(self, agent):
        """Test handling valid file."""
        # Create temporary test file
        test_file = Path("temp_test.py")
        test_file.write_text("# Test file")

        try:
            event = Event(
                type="file:modified",
                payload={"path": str(test_file)},
                source="test"
            )

            result = await agent.handle(event)

            assert result.success is True
            assert result.agent_name == "my-agent"
            assert result.data is not None
        finally:
            test_file.unlink(missing_ok=True)
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific agent tests
pytest tests/unit/agents/test_my_agent.py

# Run with coverage
pytest --cov=src/claude_agents/agents/my_agent

# Run with verbose output
pytest -v
```

## Claude Code Integration

### Context Store Integration

**MANDATORY**: Write findings to context store:

```python
from claude_agents.core.context_store import context_store

# After creating AgentResult
agent_result = AgentResult(...)
context_store.write_finding(agent_result)
return agent_result
```

### Consolidated Results

AgentManager automatically triggers consolidation when agents complete. Your agent results will appear in:

- Individual file: `.claude/context/{agent-type}.json`
- Consolidated file: `.claude/context/agent-results.json`

### Adapter Integration

Claude Code adapter reads your results and surfaces:

1. **Agent failures**: High priority
2. **Code issues**: Medium/high priority (lint/test/security)
3. **Tool errors**: Low priority (installation hints)

Ensure your `data` dict includes helpful error messages:

```python
data={
    "file": str(path),
    "tool": "my-tool",
    "issues_found": len(issues),
    "errors": ["Tool not installed - run: pip install my-tool"]
}
```

## Best Practices

### 1. Check Tool Availability

Always check if required tools are installed:

```python
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-c", "import my_tool"],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    return AgentResult(
        agent_name=self.name,
        success=True,  # Not a failure, just unavailable
        duration=0.0,
        message="Tool not available",
        data={
            "errors": ["my_tool not installed - run: pip install my_tool"]
        }
    )
```

### 2. Use Path Objects

Always use `pathlib.Path` with validation:

```python
from pathlib import Path

path = Path(file_path)

# Validate path security
if path.is_absolute():
    path = path.resolve()
if not path.is_relative_to(project_root):
    return AgentResult(
        agent_name=self.name,
        success=False,
        duration=0.0,
        message="Path outside project root"
    )
```

### 3. Implement Resource Cleanup

Use async context managers for resources:

```python
async def _process_file(self, path: Path):
    """Process file with proper resource management."""
    try:
        async with aiofiles.open(path, 'r') as f:
            content = await f.read()
            # Process content
    finally:
        # Cleanup happens automatically
        pass
```

### 4. Use Structured Logging

Log consistently with context:

```python
self.logger.info(f"Processing {path.name}")
self.logger.warning(f"Issue found in {path}:{line}")
self.logger.error(f"Failed to process {path}: {error}", exc_info=True)
```

### 5. Handle Async Errors

Implement comprehensive async error handling:

```python
async def handle(self, event: Event) -> AgentResult:
    try:
        result = await self._process_file(path)
        return result
    except asyncio.TimeoutError:
        return AgentResult(
            agent_name=self.name,
            success=False,
            duration=0.0,
            message="Processing timeout",
            error="Operation timed out"
        )
    except Exception as e:
        self.logger.error(f"Unexpected error: {e}", exc_info=True)
        return AgentResult(
            agent_name=self.name,
            success=False,
            duration=0.0,
            message="Processing failed",
            error=str(e)
        )
```

## Common Pitfalls

### 1. Forgetting Duration Parameter

**Problem**: Creating AgentResult without duration causes TypeError

```python
# ✗ WRONG
return AgentResult(
    agent_name=self.name,
    success=True,
    message="Done"
)
# TypeError: missing 1 required positional argument: 'duration'
```

**Solution**: Always include duration=0.0 for early returns

```python
# ✓ CORRECT
return AgentResult(
    agent_name=self.name,
    success=True,
    duration=0.0,
    message="Done"
)
```

### 2. Using Wrong Data Type

**Problem**: Passing list/tuple as data causes TypeError

```python
# ✗ WRONG
return AgentResult(
    agent_name=self.name,
    success=True,
    duration=0.0,
    data=[1, 2, 3]  # Must be dict!
)
```

**Solution**: Use dict for data

```python
# ✓ CORRECT
return AgentResult(
    agent_name=self.name,
    success=True,
    duration=0.0,
    data={"items": [1, 2, 3]}
)
```

### 3. CamelCase Configuration

**Problem**: Using camelCase in config causes KeyError with dataclass

```python
# ✗ WRONG
config = {
    "enabledTools": ["mypy"],
    "complexityThreshold": 10
}
```

**Solution**: Use snake_case

```python
# ✓ CORRECT
config = {
    "enabled_tools": ["mypy"],
    "complexity_threshold": 10
}
```

### 4. Forgetting Context Store Write

**Problem**: Agent results don't appear in Claude Code

```python
# ✗ WRONG
agent_result = AgentResult(...)
return agent_result  # Not written to context!
```

**Solution**: Write to context store

```python
# ✓ CORRECT
agent_result = AgentResult(...)
context_store.write_finding(agent_result)
return agent_result
```

### 5. Not Checking File Existence

**Problem**: Agent crashes on non-existent files

```python
# ✗ WRONG
async def handle(self, event: Event) -> AgentResult:
    path = Path(event.payload["path"])
    content = path.read_text()  # Crashes if missing!
```

**Solution**: Always validate file existence

```python
# ✓ CORRECT
async def handle(self, event: Event) -> AgentResult:
    path = Path(event.payload.get("path", ""))
    if not path.exists():
        return AgentResult(
            agent_name=self.name,
            success=False,
            duration=0.0,
            message=f"File not found: {path}"
        )
    content = path.read_text()
```

## Examples

### Complete Agent Example

See `src/claude_agents/agents/linter.py` for a complete, production-ready example that demonstrates:

- Configuration with validation
- Tool availability checking
- File processing with error handling
- Context store integration
- Comprehensive logging

### Minimal Agent Template

```python
"""Minimal agent template."""

from claude_agents.core.agent import Agent, AgentResult
from claude_agents.core.event import Event
from claude_agents.core.context_store import context_store
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any


@dataclass
class MinimalAgentConfig:
    """Minimal agent configuration."""

    enabled: bool = True


class MinimalAgent(Agent):
    """Minimal agent implementation."""

    def __init__(self, config: Dict[str, Any], event_bus):
        super().__init__(
            "minimal-agent",
            ["file:modified"],
            event_bus
        )
        self.config = MinimalAgentConfig(**config)

    async def handle(self, event: Event) -> AgentResult:
        """Handle file events."""
        file_path = event.payload.get("path")

        if not file_path:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0.0,
                message="No file path in event"
            )

        path = Path(file_path)
        if not path.exists():
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0.0,
                message=f"File not found: {path}"
            )

        # Your processing logic here

        agent_result = AgentResult(
            agent_name=self.name,
            success=True,
            duration=0.0,
            message=f"Processed {path.name}",
            data={"file": str(path)}
        )

        context_store.write_finding(agent_result)
        return agent_result
```

## Additional Resources

- [CODING_RULES.md](../CODING_RULES.md) - Core patterns and best practices
- [TESTING_RESULTS.md](../TESTING_RESULTS.md) - Real-world bug fixes and lessons
- [CLAUDE.md](../.claude/CLAUDE.md) - Claude Code integration guide

## Summary Checklist

When creating a new agent, ensure:

- [ ] Agent inherits from `Agent` base class
- [ ] Configuration uses dataclass with `__post_init__` validation
- [ ] Configuration uses snake_case (not camelCase)
- [ ] `handle()` method returns `AgentResult` with all required parameters
- [ ] All `AgentResult` creations include `duration` parameter
- [ ] Early returns use `duration=0.0`
- [ ] Exception handlers include `duration=0.0` and `error` field
- [ ] Tool availability is checked before use
- [ ] Results are written to context store via `context_store.write_finding()`
- [ ] File existence is validated before processing
- [ ] Paths use `pathlib.Path` objects
- [ ] Logging is implemented for key operations
- [ ] Unit tests cover happy path and error cases
- [ ] Agent is registered in `config.py`
- [ ] Agent config is added to `AGENT_CONFIGS`

Following these guidelines will ensure your agent integrates seamlessly with the claude-agents system and provides reliable, helpful results to Claude Code users.
