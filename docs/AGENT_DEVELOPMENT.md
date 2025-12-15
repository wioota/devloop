# Agent Development Guide

## Creating a Custom Agent

### Using the Builder Pattern

```python
from devloop.core.custom_agent import AgentBuilder, CustomAgentType

# Create a pattern matcher
config = (
    AgentBuilder("todo_finder", CustomAgentType.PATTERN_MATCHER)
    .with_description("Find TODO comments")
    .with_triggers("file:created", "file:modified")
    .with_config(patterns=[r"#\s*TODO:.*"])
    .build()
)
```

### Using the CLI

```bash
# Create custom agent
devloop custom-create find_todos pattern_matcher \
  --description "Find TODO comments" \
  --triggers file:created,file:modified

# List custom agents
devloop custom-list
```

## Agent Types

- **Pattern Matcher** - Find patterns in code
- **Custom Script** - Run custom logic
- **Webhook** - Call external APIs

## Agent Structure

```python
from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event

class MyAgent(Agent):
    async def handle(self, event: Event) -> AgentResult:
        # Your logic here
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0.1,
            message="Processed successfully"
        )
```

## Testing Your Agent

```python
# tests/unit/agents/test_my_agent.py
import pytest
from devloop.agents.my_agent import MyAgent

@pytest.mark.asyncio
async def test_my_agent():
    agent = MyAgent("my-agent")
    event = Event(type="file:modified", data={})
    result = await agent.handle(event)
    assert result.success
```

## See Also

- [AGENT_API_REFERENCE.md](./AGENT_API_REFERENCE.md) - API documentation
- [AGENT_EXAMPLES.md](./AGENT_EXAMPLES.md) - Examples
- [MARKETPLACE_GUIDE.md](./MARKETPLACE_GUIDE.md) - Publishing agents
