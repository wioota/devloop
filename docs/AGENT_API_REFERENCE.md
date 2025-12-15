# Agent API Reference

## Agent Base Class

```python
class Agent:
    """Base class for all DevLoop agents."""
    
    async def handle(self, event: Event) -> AgentResult:
        """Handle an event and return result."""
        pass
```

## AgentResult

```python
@dataclass
class AgentResult:
    agent_name: str
    success: bool
    duration: float
    message: str
    findings: List[Finding] = field(default_factory=list)
```

## Event

```python
@dataclass
class Event:
    type: str  # "file:modified", "git:pre-commit", etc.
    data: Dict[str, Any]
    timestamp: datetime
```

## Finding

```python
@dataclass
class Finding:
    severity: str  # "error", "warning", "info"
    message: str
    file_path: Optional[str]
    line_number: Optional[int]
    agent_name: str
```

## Custom Agent Builder

```python
class AgentBuilder:
    def __init__(self, name: str, agent_type: CustomAgentType)
    def with_description(self, description: str) -> Self
    def with_triggers(self, *triggers: str) -> Self
    def with_config(self, **config: Any) -> Self
    def build() -> Dict[str, Any]
```

## See Also

- [AGENT_DEVELOPMENT.md](./AGENT_DEVELOPMENT.md) - Development guide
- [AGENT_EXAMPLES.md](./AGENT_EXAMPLES.md) - Examples
