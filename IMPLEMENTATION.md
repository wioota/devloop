# Implementation Guide

## Project Structure

```
claude-agents/
├── pyproject.toml              # Poetry configuration
├── README.md                   # Project documentation
├── .gitignore                  # Git ignore rules
├── .python-version             # Python version (3.11+)
│
├── src/
│   └── claude_agents/
│       ├── __init__.py
│       │
│       ├── core/               # Core framework
│       │   ├── __init__.py
│       │   ├── event.py        # Event system
│       │   ├── agent.py        # Base agent class
│       │   ├── manager.py      # Agent manager
│       │   ├── context.py      # Context store
│       │   └── config.py       # Configuration
│       │
│       ├── collectors/         # Event collectors
│       │   ├── __init__.py
│       │   ├── filesystem.py   # File system watcher
│       │   ├── git.py          # Git hooks
│       │   ├── process.py      # Process monitor
│       │   └── base.py         # Base collector
│       │
│       ├── agents/             # Built-in agents
│       │   ├── __init__.py
│       │   ├── linter.py
│       │   ├── formatter.py
│       │   ├── test_runner.py
│       │   ├── security.py
│       │   ├── commit_assistant.py
│       │   └── doc_sync.py
│       │
│       ├── storage/            # Storage backends
│       │   ├── __init__.py
│       │   ├── event_store.py  # Event storage
│       │   └── context_store.py # Context storage
│       │
│       ├── notification/       # Notification system
│       │   ├── __init__.py
│       │   ├── desktop.py
│       │   ├── terminal.py
│       │   └── notifier.py
│       │
│       ├── cli/                # CLI interface
│       │   ├── __init__.py
│       │   ├── main.py         # Main CLI entry
│       │   ├── commands/       # CLI commands
│       │   │   ├── status.py
│       │   │   ├── run.py
│       │   │   ├── config.py
│       │   │   └── logs.py
│       │   └── ui.py           # UI utilities
│       │
│       └── utils/              # Utilities
│           ├── __init__.py
│           ├── logging.py
│           ├── files.py
│           └── git.py
│
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_event.py
│   │   ├── test_agent.py
│   │   └── test_collectors.py
│   ├── integration/
│   │   ├── test_agent_chains.py
│   │   └── test_git_workflow.py
│   └── fixtures/
│       └── sample_repo/
│
├── docs/                       # Documentation
│   ├── CLAUDE.md              # Main spec (moved here)
│   ├── agent-types.md
│   ├── event-system.md
│   ├── configuration-schema.md
│   ├── INTERACTION_MODEL.md
│   ├── TECH_STACK.md
│   └── IMPLEMENTATION.md      # This file
│
└── examples/                   # Example configurations
    ├── basic/
    │   └── agents.json
    ├── javascript/
    │   └── agents.json
    └── python/
        └── agents.json
```

## Phase 1: Foundation (Weeks 1-2)

### Step 1.1: Project Setup

**Create pyproject.toml**:
```toml
[tool.poetry]
name = "claude-agents"
version = "0.1.0"
description = "Background agents for development workflow automation"
authors = ["Your Name <your.email@example.com>"]
readme = "README.md"
packages = [{include = "claude_agents", from = "src"}]

[tool.poetry.dependencies]
python = "^3.11"
pydantic = "^2.5"
pydantic-settings = "^2.1"
watchdog = "^3.0"
typer = "^0.9"
rich = "^13.7"
GitPython = "^3.1"
psutil = "^5.9"
aiosqlite = "^0.19"
python-dotenv = "^1.0"
asyncio = "^3.4"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4"
pytest-asyncio = "^0.21"
pytest-mock = "^3.12"
pytest-cov = "^4.1"
black = "^23.12"
ruff = "^0.1"
mypy = "^1.7"
pre-commit = "^3.6"

[tool.poetry.scripts]
claude-agents = "claude_agents.cli.main:app"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 88
target-version = ['py311']

[tool.ruff]
line-length = 88
target-version = "py311"
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]
```

### Step 1.2: Core Event System

**src/claude_agents/core/event.py**:
```python
"""Event system core."""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class Priority(Enum):
    """Event priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class EventMetadata:
    """Event metadata."""
    priority: Priority = Priority.NORMAL
    debounce: Optional[float] = None
    throttle: Optional[float] = None
    cancel_previous: bool = False
    requires_sync: bool = False
    correlation_id: Optional[str] = None
    parent_event_id: Optional[str] = None


@dataclass
class Event:
    """Base event class."""
    type: str
    payload: Dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"
    metadata: EventMetadata = field(default_factory=EventMetadata)

    def __lt__(self, other: Event) -> bool:
        """Compare events by priority for priority queue."""
        return self.metadata.priority.value > other.metadata.priority.value


class EventBus:
    """Central event bus for publishing and subscribing to events."""

    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._running = False

    async def subscribe(self, event_type: str, queue: asyncio.Queue) -> None:
        """Subscribe to events of a specific type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = set()
        self._subscribers[event_type].add(queue)

    async def unsubscribe(self, event_type: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from events."""
        if event_type in self._subscribers:
            self._subscribers[event_type].discard(queue)

    async def emit(self, event: Event) -> None:
        """Emit an event to all subscribers."""
        # Emit to specific event type subscribers
        if event.type in self._subscribers:
            for queue in self._subscribers[event.type]:
                await queue.put(event)

        # Also emit to wildcard subscribers (*)
        if "*" in self._subscribers:
            for queue in self._subscribers["*"]:
                await queue.put(event)

    async def emit_and_wait(
        self,
        event: Event,
        timeout: float = 30.0
    ) -> Any:
        """Emit an event and wait for a response."""
        response_queue = asyncio.Queue()
        response_event_type = f"{event.type}:response:{event.id}"

        await self.subscribe(response_event_type, response_queue)

        try:
            await self.emit(event)
            response_event = await asyncio.wait_for(
                response_queue.get(),
                timeout=timeout
            )
            return response_event.payload.get("result")
        finally:
            await self.unsubscribe(response_event_type, response_queue)


class EventQueue:
    """Priority queue for events."""

    def __init__(self, maxsize: int = 1000):
        self._queue: asyncio.PriorityQueue[Event] = asyncio.PriorityQueue(maxsize)
        self._debounce_cache: Dict[str, float] = {}
        self._throttle_cache: Dict[str, float] = {}

    def should_skip(self, event: Event) -> bool:
        """Check if event should be skipped due to debounce/throttle."""
        now = time.time()
        key = f"{event.type}:{event.payload.get('path', '')}"

        # Check debounce
        if event.metadata.debounce:
            last_time = self._debounce_cache.get(key, 0)
            if now - last_time < event.metadata.debounce / 1000:
                return True
            self._debounce_cache[key] = now

        # Check throttle
        if event.metadata.throttle:
            last_time = self._throttle_cache.get(key, 0)
            if now - last_time < event.metadata.throttle / 1000:
                return True
            self._throttle_cache[key] = now

        return False

    async def put(self, event: Event) -> None:
        """Add event to queue."""
        if not self.should_skip(event):
            await self._queue.put(event)

    async def get(self) -> Event:
        """Get next event from queue."""
        return await self._queue.get()

    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()

    def qsize(self) -> int:
        """Get queue size."""
        return self._queue.qsize()
```

### Step 1.3: Base Agent Class

**src/claude_agents/core/agent.py**:
```python
"""Base agent class."""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .event import Event, EventBus


class AgentConfig(BaseModel):
    """Agent configuration."""
    enabled: bool = True
    triggers: List[str] = Field(default_factory=list)
    priority: str = "normal"
    timeout: float = 30.0
    retries: int = 0
    parallel: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Agent execution result."""
    agent_name: str
    success: bool
    duration: float
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class Agent(ABC):
    """Base agent class."""

    def __init__(
        self,
        name: str,
        config: AgentConfig,
        event_bus: EventBus
    ):
        self.name = name
        self.config = config
        self.event_bus = event_bus
        self.logger = logging.getLogger(f"agent.{name}")
        self._running = False
        self._event_queue: asyncio.Queue[Event] = asyncio.Queue()

    @abstractmethod
    async def handle(self, event: Event) -> AgentResult:
        """Handle an event. Must be implemented by subclasses."""
        pass

    async def on_enable(self) -> None:
        """Called when agent is enabled."""
        pass

    async def on_disable(self) -> None:
        """Called when agent is disabled."""
        pass

    async def on_error(self, error: Exception, event: Event) -> None:
        """Called when an error occurs."""
        self.logger.error(f"Error handling event {event.type}: {error}")

    async def start(self) -> None:
        """Start the agent."""
        if self._running:
            return

        self._running = True
        await self.on_enable()

        # Subscribe to configured triggers
        for trigger in self.config.triggers:
            await self.event_bus.subscribe(trigger, self._event_queue)

        # Start event processing loop
        asyncio.create_task(self._process_events())
        self.logger.info(f"Agent {self.name} started")

    async def stop(self) -> None:
        """Stop the agent."""
        if not self._running:
            return

        self._running = False
        await self.on_disable()

        # Unsubscribe from events
        for trigger in self.config.triggers:
            await self.event_bus.unsubscribe(trigger, self._event_queue)

        self.logger.info(f"Agent {self.name} stopped")

    async def _process_events(self) -> None:
        """Process events from the queue."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                continue

            if not self.config.enabled:
                continue

            # Execute with timeout
            try:
                start_time = time.time()

                result = await asyncio.wait_for(
                    self.handle(event),
                    timeout=self.config.timeout
                )

                duration = time.time() - start_time
                result.duration = duration

                # Publish result
                await self._publish_result(result)

            except asyncio.TimeoutError:
                self.logger.warning(
                    f"Agent {self.name} timed out after {self.config.timeout}s"
                )
            except Exception as e:
                await self.on_error(e, event)

    async def _publish_result(self, result: AgentResult) -> None:
        """Publish agent result as an event."""
        await self.event_bus.emit(Event(
            type=f"agent:{self.name}:completed",
            payload=result.model_dump(),
            source=self.name
        ))
```

### Step 1.4: Agent Manager

**src/claude_agents/core/manager.py**:
```python
"""Agent manager."""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional

from .agent import Agent, AgentConfig, AgentResult
from .event import Event, EventBus


class AgentManager:
    """Manages agent lifecycle and coordination."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.agents: Dict[str, Agent] = {}
        self.logger = logging.getLogger("agent_manager")
        self._paused_agents: set[str] = set()

    def register(self, agent: Agent) -> None:
        """Register an agent."""
        self.agents[agent.name] = agent
        self.logger.info(f"Registered agent: {agent.name}")

    async def start_all(self) -> None:
        """Start all registered agents."""
        tasks = [agent.start() for agent in self.agents.values()]
        await asyncio.gather(*tasks)
        self.logger.info(f"Started {len(self.agents)} agents")

    async def stop_all(self) -> None:
        """Stop all agents."""
        tasks = [agent.stop() for agent in self.agents.values()]
        await asyncio.gather(*tasks)
        self.logger.info("Stopped all agents")

    async def start_agent(self, name: str) -> None:
        """Start a specific agent."""
        if name in self.agents:
            await self.agents[name].start()

    async def stop_agent(self, name: str) -> None:
        """Stop a specific agent."""
        if name in self.agents:
            await self.agents[name].stop()

    async def pause_agents(
        self,
        agents: Optional[List[str]] = None,
        reason: str = ""
    ) -> None:
        """Pause specific agents (or all)."""
        target_agents = agents or list(self.agents.keys())

        for agent_name in target_agents:
            if agent_name in self.agents:
                self.agents[agent_name].config.enabled = False
                self._paused_agents.add(agent_name)

        self.logger.info(f"Paused agents: {target_agents} (reason: {reason})")

    async def resume_agents(
        self,
        agents: Optional[List[str]] = None
    ) -> None:
        """Resume paused agents."""
        target_agents = agents or list(self._paused_agents)

        for agent_name in target_agents:
            if agent_name in self.agents:
                self.agents[agent_name].config.enabled = True
                self._paused_agents.discard(agent_name)

        self.logger.info(f"Resumed agents: {target_agents}")

    async def wait_for_results(
        self,
        agents: List[str],
        timeout: float = 10.0
    ) -> Dict[str, AgentResult]:
        """Wait for specific agents to complete."""
        results = {}
        result_queues = {}

        # Subscribe to completion events
        for agent_name in agents:
            queue = asyncio.Queue()
            result_queues[agent_name] = queue
            await self.event_bus.subscribe(
                f"agent:{agent_name}:completed",
                queue
            )

        try:
            # Wait for all results
            async def wait_for_agent(name: str) -> tuple[str, AgentResult]:
                event = await asyncio.wait_for(
                    result_queues[name].get(),
                    timeout=timeout
                )
                return name, AgentResult(**event.payload)

            completed = await asyncio.gather(
                *[wait_for_agent(name) for name in agents],
                return_exceptions=True
            )

            for item in completed:
                if isinstance(item, tuple):
                    name, result = item
                    results[name] = result

        finally:
            # Unsubscribe
            for agent_name, queue in result_queues.items():
                await self.event_bus.unsubscribe(
                    f"agent:{agent_name}:completed",
                    queue
                )

        return results

    def get_status(self) -> Dict[str, Dict[str, any]]:
        """Get status of all agents."""
        return {
            name: {
                "running": agent._running,
                "enabled": agent.config.enabled,
                "paused": name in self._paused_agents,
                "triggers": agent.config.triggers
            }
            for name, agent in self.agents.items()
        }
```

### Step 1.5: Configuration Management

**src/claude_agents/core/config.py**:
```python
"""Configuration management."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class GlobalConfig(BaseModel):
    """Global configuration."""
    max_concurrent_agents: int = Field(default=5, alias="maxConcurrentAgents")
    notification_level: str = Field(default="summary", alias="notificationLevel")
    resource_limits: Dict[str, Any] = Field(default_factory=dict, alias="resourceLimits")
    logging: Dict[str, Any] = Field(default_factory=dict)


class EventSystemConfig(BaseModel):
    """Event system configuration."""
    collectors: Dict[str, Any] = Field(default_factory=dict)
    dispatcher: Dict[str, Any] = Field(default_factory=dict)
    store: Dict[str, Any] = Field(default_factory=dict)


class Config(BaseModel):
    """Main configuration."""
    version: str = "1.0.0"
    enabled: bool = True
    agents: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    global_config: GlobalConfig = Field(default_factory=GlobalConfig, alias="global")
    event_system: EventSystemConfig = Field(
        default_factory=EventSystemConfig,
        alias="eventSystem"
    )

    @classmethod
    def load(cls, path: Path) -> Config:
        """Load configuration from file."""
        if not path.exists():
            return cls()

        with open(path) as f:
            data = json.load(f)

        return cls(**data)

    def save(self, path: Path) -> None:
        """Save configuration to file."""
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(
                self.model_dump(by_alias=True, exclude_none=True),
                f,
                indent=2
            )

    def get_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific agent."""
        return self.agents.get(agent_name)
```

## Step 1.6: Basic CLI

**src/claude_agents/cli/main.py**:
```python
"""CLI entry point."""
import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Claude Agents - Development workflow automation")
console = Console()


@app.command()
def status():
    """Show agent status."""
    table = Table(title="Agent Status")

    table.add_column("Agent", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Triggers", style="yellow")

    # TODO: Get actual status from agent manager
    table.add_row("linter", "✅ Running", "file:save, git:pre-commit")
    table.add_row("formatter", "✅ Running", "file:save")
    table.add_row("test-runner", "⏸️  Paused", "file:save")

    console.print(table)


@app.command()
def run(agent: str = typer.Argument(..., help="Agent to run")):
    """Run an agent manually."""
    console.print(f"[green]Running agent: {agent}[/green]")
    # TODO: Implement agent execution


@app.command()
def init(path: Path = typer.Argument(Path.cwd(), help="Project path")):
    """Initialize claude-agents in a project."""
    claude_dir = path / ".claude"
    claude_dir.mkdir(exist_ok=True)

    config_file = claude_dir / "agents.json"
    if config_file.exists():
        console.print("[yellow]Configuration already exists[/yellow]")
        return

    # Create default config
    default_config = {
        "version": "1.0.0",
        "enabled": True,
        "agents": {
            "linter": {
                "enabled": True,
                "triggers": ["file:save"]
            }
        }
    }

    with open(config_file, "w") as f:
        import json
        json.dump(default_config, f, indent=2)

    console.print(f"[green]✓[/green] Initialized in {claude_dir}")


if __name__ == "__main__":
    app()
```

## Next Steps - Implementation Roadmap

### Week 1-2: Core Foundation
- ✅ Project structure
- ✅ Event system (Event, EventBus, EventQueue)
- ✅ Base agent class
- ✅ Agent manager
- ✅ Configuration management
- ✅ Basic CLI

### Week 3-4: Event Collectors
- Filesystem collector (watchdog)
- Git hook collector
- Process monitor collector
- Collector manager
- Tests for collectors

### Week 5-6: First Agents
- Linter agent (simple)
- Formatter agent (simple)
- Test runner agent (moderate)
- Agent tests
- Integration tests

### Week 7-8: Storage & Context
- Event store (SQLite)
- Context store (JSON + SQLite)
- Context update protocol
- Storage tests

### Week 9-10: Notifications
- Terminal notifications
- Desktop notifications
- Notification manager
- Notification tests

### Week 11-12: Polish & Integration
- Complete CLI commands
- Git hooks installation
- Documentation
- Example configurations
- End-to-end tests

Would you like me to:
1. Start implementing the core components now?
2. Create more detailed implementation docs for specific components?
3. Set up the actual project structure with all the files?
4. Discuss any architectural decisions before we proceed?
