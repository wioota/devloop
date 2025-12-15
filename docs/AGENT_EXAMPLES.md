# Agent Examples

## Example 1: Pattern Matcher

Find TODO comments:

```python
from devloop.core.custom_agent import AgentBuilder, CustomAgentType

config = (
    AgentBuilder("todo_finder", CustomAgentType.PATTERN_MATCHER)
    .with_description("Find TODO comments")
    .with_triggers("file:created", "file:modified")
    .with_config(patterns=[r"#\s*TODO:.*", r"//\s*TODO:.*"])
    .build()
)
```

## Example 2: Custom Script Agent

Run custom logic:

```python
from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event

class CountLinesAgent(Agent):
    async def handle(self, event: Event) -> AgentResult:
        file_path = event.data.get("file_path")
        if not file_path:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0,
                message="No file path provided"
            )
        
        with open(file_path) as f:
            line_count = len(f.readlines())
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0.1,
            message=f"File has {line_count} lines"
        )
```

## Example 3: Security Scanner

Scan for secrets:

```python
config = (
    AgentBuilder("secret_scanner", CustomAgentType.PATTERN_MATCHER)
    .with_description("Find potential secrets")
    .with_triggers("file:created", "file:modified")
    .with_config(
        patterns=[
            r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]",
            r"password\s*=\s*['\"][^'\"]+['\"]",
            r"secret\s*=\s*['\"][^'\"]+['\"]",
        ]
    )
    .build()
)
```

## See Also

- [AGENT_DEVELOPMENT.md](./AGENT_DEVELOPMENT.md) - Development guide
- [AGENT_API_REFERENCE.md](./AGENT_API_REFERENCE.md) - API reference
