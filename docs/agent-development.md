# Agent Development Guide

> Tutorial, API reference, examples, and troubleshooting for creating DevLoop agents.

---

## Overview

DevLoop agents are async Python classes that respond to development events (file changes, git operations, etc.) and produce findings. You can create agents by subclassing `Agent` or using the no-code `AgentBuilder`.

---

## Quick Start: Custom Agent (No Code)

Create agents without writing Python using the CLI:

```bash
# Create a pattern matcher agent
devloop custom-create todo_finder pattern_matcher \
  --description "Find TODO comments" \
  --triggers file:created,file:modified

# List custom agents
devloop custom-list

# Remove a custom agent
devloop custom-remove todo_finder
```

---

## Creating an Agent (Python)

### 1. Subclass `Agent`

```python
# src/devloop/agents/my_agent.py
from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event


class MyAgent(Agent):
    """Describe what this agent does."""

    name = "my_agent"

    async def handle(self, event: Event) -> AgentResult:
        # Process the event
        files_to_check = event.get("files", [])

        findings = []
        for filepath in files_to_check:
            # Your analysis logic here
            issues = self.analyze(filepath)
            findings.extend(issues)

        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0.1,
            message=f"Found {len(findings)} issues",
            findings=findings,
        )

    def analyze(self, filepath: str) -> list:
        """Your custom analysis logic."""
        return []
```

### 2. Register the Agent

Add to agent configuration in `.devloop/agents.json`:

```json
{
  "agents": {
    "my_agent": {
      "enabled": true,
      "triggers": ["file:modified", "file:created"],
      "config": {
        "debounce": 500,
        "filePatterns": ["**/*.py"]
      }
    }
  }
}
```

### 3. Add Tests

```python
# tests/unit/agents/test_my_agent.py
import pytest
from devloop.agents.my_agent import MyAgent


@pytest.fixture
def agent():
    return MyAgent(config={"enabled": True})


@pytest.mark.asyncio
async def test_handle_returns_result(agent):
    event = {"type": "file:modified", "files": ["test.py"]}
    result = await agent.handle(event)
    assert result.success is True
    assert result.agent_name == "my_agent"
```

---

## API Reference

### `Agent` Base Class

```python
class Agent:
    name: str                          # Unique agent identifier
    config: dict                       # Agent configuration

    async def handle(self, event: Event) -> AgentResult:
        """Process an event and return results."""
        ...

    async def setup(self) -> None:
        """Called once when agent is loaded."""
        ...

    async def teardown(self) -> None:
        """Called when agent is being unloaded."""
        ...
```

### `AgentResult`

```python
@dataclass
class AgentResult:
    agent_name: str       # Name of the agent that produced this result
    success: bool         # Whether the agent completed successfully
    duration: float       # Execution time in seconds
    message: str          # Human-readable summary
    findings: list = []   # List of Finding objects
    metrics: dict = {}    # Optional performance metrics
```

### `Event`

Events are dictionaries with at minimum a `type` field:

```python
{
    "type": "file:modified",       # Event type
    "files": ["src/app.py"],       # Affected files
    "timestamp": "2026-02-24T...", # When it occurred
}
```

### `AgentBuilder` (No-Code)

```python
from devloop.core.custom_agent import AgentBuilder, CustomAgentType

config = (
    AgentBuilder("my_agent", CustomAgentType.PATTERN_MATCHER)
    .with_description("Find patterns in code")
    .with_triggers("file:created", "file:modified")
    .with_config(patterns=[r"#\s*FIXME:.*"], file_patterns=["**/*.py"])
    .build()
)
```

Available agent types:
- `PATTERN_MATCHER` — Match regex patterns in files
- `COMMAND_RUNNER` — Execute shell commands on events
- `FILE_WATCHER` — React to specific file changes
- `DATA_PROCESSOR` — Transform and analyze data

---

## Examples

### Pattern Matcher: Find Security TODOs

```python
config = (
    AgentBuilder("security_todos", CustomAgentType.PATTERN_MATCHER)
    .with_description("Find security-related TODOs")
    .with_triggers("file:modified")
    .with_config(
        patterns=[r"#\s*TODO.*security", r"#\s*FIXME.*auth"],
        file_patterns=["**/*.py"],
        severity="warning",
    )
    .build()
)
```

### Command Runner: Run Tests on Change

```python
config = (
    AgentBuilder("quick_test", CustomAgentType.COMMAND_RUNNER)
    .with_description("Run related tests on file change")
    .with_triggers("file:modified")
    .with_config(
        command="pytest {file} -x --tb=short",
        file_patterns=["**/test_*.py"],
        timeout=30,
    )
    .build()
)
```

---

## Agent Marketplace

### Publishing Your Agent

```bash
# Check agent is ready to publish
devloop agent check ./my-agent

# Publish to marketplace
devloop agent publish ./my-agent

# Bump version
devloop agent version ./my-agent patch
```

### Agent Metadata

Create `agent.json` in your agent directory:

```json
{
  "name": "my-agent",
  "version": "1.0.0",
  "description": "What this agent does",
  "author": "Your Name",
  "license": "MIT",
  "categories": ["code-quality"],
  "keywords": ["quality", "analysis"],
  "pythonVersion": ">=3.11",
  "devloopVersion": ">=0.5.0"
}
```

See the [Marketplace Guide](./marketplace.md) for full publishing workflow.

---

## Troubleshooting

### Agent not triggering

1. Check it's enabled in `.devloop/agents.json`
2. Verify file patterns match your files
3. Check logs: `tail -f .devloop/devloop.log`
4. Run in verbose mode: `devloop watch . --verbose --foreground`

### Agent running too slowly

1. Increase debounce: `"debounce": 1000`
2. Narrow file patterns to reduce scope
3. Check resource limits in config
4. Use `devloop health` to see execution times

### Agent producing wrong findings

1. Check agent configuration (severity, patterns)
2. Review agent logs for errors
3. Test manually: run the underlying tool directly
4. File a bug: `bd create "Agent X incorrect findings" -t bug`

### Import errors

Ensure your agent module is importable:
```bash
python -c "from devloop.agents.my_agent import MyAgent"
```

### Custom agents not found

```bash
devloop custom-list                 # Verify registration
ls -la .devloop/custom_agents/      # Check storage
```

---

## See Also

- [Marketplace Guide](./marketplace.md) — Publishing and discovering agents
- [Architecture Guide](./architecture.md) — System design and event flow
- [Configuration Guide](./configuration.md) — Agent settings reference
- [ARCHITECTURE.md](../ARCHITECTURE.md) — Agent categories and roadmap
