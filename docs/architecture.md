# Dev Agents Architecture

Complete technical architecture and interaction model for the dev-agents system.

---

## Table of Contents

- [System Overview](#system-overview)
- [Project Structure](#project-structure)
- [Core Components](#core-components)
- [Interaction Model](#interaction-model)
- [Agent Communication](#agent-communication)
- [Integration Patterns](#integration-patterns)

---

## System Overview

Dev-agents is an event-driven background agent system that monitors development lifecycle events and provides intelligent assistance during software development.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      Developer                          │
│                    (You - Human)                        │
└────────────┬────────────────────────────┬───────────────┘
             │                            │
             │ Direct                     │ Via Coding Agent
             │ Interaction                │ Interaction
             │                            │
┌────────────▼────────────┐   ┌──────────▼───────────────┐
│   Background Agents     │   │   Coding Agents          │
│   (Event-Driven)        │◄──┤   (Claude Code, etc)     │
│                         │   │                          │
│ • Linter Agent          │   │ Interactive AI Coding    │
│ • Test Runner Agent     │   │ Assistant                │
│ • Security Scanner      │   │                          │
│ • Type Checker          │   └──────────┬───────────────┘
│ • Formatter Agent       │              │
│ • etc.                  │              │ Consumes
└────────┬────────────────┘              │ Context
         │                               │
         │ Inter-Agent            ┌──────▼────────────┐
         │ Communication          │  Shared Context   │
         │                        │  & Event Store    │
         └───────────────────────►│                   │
                                  │ • Event History   │
                                  │ • Agent Results   │
                                  │ • Code Analysis   │
                                  │ • Project State   │
                                  └───────────────────┘
```

### Core Principles

1. **Non-Intrusive**: Agents assist without blocking workflow
2. **Event-Driven**: All actions triggered by observable events
3. **Configurable**: Full control over agent behavior
4. **Context-Aware**: Agents understand project context
5. **Parallel Execution**: Multiple agents run concurrently
6. **Resource-Conscious**: Lightweight and efficient

---

## Project Structure

```
dev-agents/
├── pyproject.toml              # Package configuration
├── README.md                   # Project documentation
├── CHANGELOG.md                # Version history
├── .gitignore                  # Git ignore rules
│
├── src/
│   └── dev_agents/
│       ├── __init__.py
│       │
│       ├── core/               # Core framework
│       │   ├── __init__.py
│       │   ├── event.py        # Event system (EventBus, Event)
│       │   ├── agent.py        # Base agent class
│       │   ├── manager.py      # Agent manager
│       │   ├── context_store.py # Context store (Finding-based API)
│       │   ├── event_store.py  # Event persistence (SQLite)
│       │   ├── config.py       # Configuration management
│       │   ├── feedback.py     # Feedback collection system
│       │   ├── performance.py  # Performance monitoring
│       │   └── auto_fix.py     # Auto-fix utilities
│       │
│       ├── collectors/         # Event collectors
│       │   ├── __init__.py
│       │   ├── base.py         # Base collector
│       │   ├── filesystem.py   # File system watcher (watchdog)
│       │   ├── git.py          # Git hooks
│       │   └── process.py      # Process monitor
│       │
│       ├── agents/             # Built-in agents
│       │   ├── __init__.py
│       │   ├── linter.py       # Code linting (ruff, eslint)
│       │   ├── formatter.py    # Code formatting (black, prettier)
│       │   ├── test_runner.py  # Test execution (pytest, jest)
│       │   ├── security_scanner.py # Security scanning (bandit)
│       │   ├── type_checker.py # Type checking (mypy)
│       │   ├── agent_health_monitor.py # Agent health monitoring
│       │   ├── git_commit_assistant.py # Commit message generation
│       │   └── performance_profiler.py # Performance profiling
│       │
│       └── cli/                # CLI interface
│           ├── __init__.py
│           ├── main.py         # Main CLI entry (typer)
│           └── amp_integration.py # Amp/Claude Code integration
│
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py             # Pytest configuration
│   ├── unit/                   # Unit tests
│   │   ├── core/
│   │   ├── agents/
│   │   └── collectors/
│   └── integration/            # Integration tests
│
├── docs/                       # Documentation
│   ├── getting-started.md      # Installation and usage
│   ├── architecture.md         # This file
│   ├── reference/              # Reference documentation
│   ├── guides/                 # How-to guides
│   └── archive/                # Historical documents
│
└── .claude/                    # Project configuration
    ├── agents.json             # Agent configuration
    ├── CLAUDE.md               # System overview
    ├── context/                # Context store (runtime)
    ├── events.db               # Event store (runtime)
    └── integration/            # Integration scripts
```

---

## Core Components

### 1. Event System

**File:** `src/dev_agents/core/event.py`

The event system is the backbone of all agent communication.

```python
@dataclass
class Event:
    """Represents a system event"""
    type: str                    # e.g., "file:modified"
    payload: Dict[str, Any]      # Event data
    id: str = field(default_factory=uuid4)
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"
    priority: EventPriority = EventPriority.NORMAL

class EventBus:
    """Central event routing system"""

    async def emit(self, event: Event) -> None:
        """Emit event to all subscribed handlers"""

    async def subscribe(self, pattern: str, handler: Callable) -> None:
        """Subscribe to events matching pattern"""
```

**Event Types:**
- `file:created`, `file:modified`, `file:deleted` - Filesystem events
- `git:pre-commit`, `git:post-commit` - Git hook events
- `agent:*:completed` - Agent lifecycle events
- `schedule:*` - Scheduled events

### 2. Agent Base Class

**File:** `src/dev_agents/core/agent.py`

All agents inherit from the base `Agent` class.

```python
class Agent:
    """Base class for all agents"""

    def __init__(
        self,
        name: str,
        triggers: List[str],
        event_bus: EventBus
    ):
        self.name = name
        self.triggers = triggers
        self.event_bus = event_bus

    async def handle(self, event: Event) -> AgentResult:
        """Handle an event (implemented by subclasses)"""
        raise NotImplementedError

    async def start(self) -> None:
        """Start the agent (subscribe to events)"""

    async def stop(self) -> None:
        """Stop the agent (unsubscribe)"""

@dataclass
class AgentResult:
    """Standardized agent result"""
    agent_name: str
    success: bool
    duration: float
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
```

### 3. Context Store

**File:** `src/dev_agents/core/context_store.py`

The context store provides a Finding-based API for agent results.

```python
@dataclass
class Finding:
    """Structured finding from an agent"""
    id: str
    agent: str                    # Agent that found it
    file: str                     # File path
    line: Optional[int]           # Line number
    severity: Severity            # error, warning, info
    message: str                  # Human-readable message
    category: str                 # e.g., "style", "security"
    auto_fixable: bool = False
    relevance: float = 1.0        # 0.0-1.0 relevance score

class ContextStore:
    """Manages agent findings and context"""

    async def add_finding(self, finding: Finding) -> None:
        """Add a finding to the store"""

    async def get_findings(
        self,
        tier: str = None,           # "immediate", "relevant", "background"
        agent: str = None,
        file: str = None
    ) -> List[Finding]:
        """Retrieve findings"""
```

**Context Store Structure:**
```
.claude/context/
├── index.json         # Quick summary for LLMs
├── immediate.json     # Blocking issues (tier 1)
├── relevant.json      # Relevant issues (tier 2)
├── background.json    # FYI issues (tier 3)
└── auto_fixed.json    # Already fixed items
```

### 4. Agent Manager

**File:** `src/dev_agents/core/manager.py`

Coordinates multiple agents.

```python
class AgentManager:
    """Manages agent lifecycle"""

    def register(self, agent: Agent) -> None:
        """Register an agent"""

    async def start_all(self) -> None:
        """Start all registered agents"""

    async def stop_all(self) -> None:
        """Stop all agents"""

    def list_agents(self) -> List[str]:
        """List all registered agent names"""
```

### 5. Configuration System

**File:** `src/dev_agents/core/config.py`

Loads and manages agent configuration from `.claude/agents.json`.

```python
class ConfigWrapper:
    """Wrapper for agent configuration"""

    def is_agent_enabled(self, agent_name: str) -> bool:
        """Check if agent is enabled"""

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get agent-specific configuration"""
```

**Example Configuration:**
```json
{
  "version": "1.0.0",
  "enabled": true,
  "agents": {
    "linter": {
      "enabled": true,
      "triggers": ["file:modified"],
      "config": {
        "autoFix": false,
        "filePatterns": ["**/*.py"]
      }
    }
  }
}
```

---

## Interaction Model

### Developer ↔ Agent Interaction

#### 1. Background Mode (Default)

```bash
# Start agents in background (daemon)
dev-agents watch

# Agents run silently, write findings to context store
# Check status anytime:
dev-agents amp_status
dev-agents amp_findings
```

#### 2. Foreground Mode (Debugging)

```bash
# Start agents with live output
dev-agents watch --foreground --verbose

# See agent output in real-time:
# [INFO] agent.linter: ✓ linter: Found 2 issues (0.12s)
# [INFO] agent.formatter: ✓ formatter: Formatted file (0.08s)
```

#### 3. CLI Commands

```bash
# Agent control
dev-agents status              # Show agent configuration
dev-agents init                # Initialize project
dev-agents stop                # Stop background daemon

# Query results
dev-agents amp_status          # Agent status (JSON)
dev-agents amp_findings        # All findings (JSON)
dev-agents amp_context         # Context index (JSON)
```

### Coding Agent ↔ Background Agent Interaction

Background agents and coding agents (Claude Code, Amp) work together via the shared context store.

#### Integration Flow

```
1. Claude Code makes changes to file.py
   ↓
2. Filesystem event triggers background agents
   ↓
3. Agents analyze file and write findings to context
   ↓
4. Claude Code reads context before responding
   ↓
5. Claude Code can mention findings to user
```

#### Context Store Protocol

```python
# Background agents write:
await context_store.add_finding(Finding(
    agent="linter",
    file="src/app.py",
    line=42,
    severity=Severity.ERROR,
    message="Undefined variable 'foo'",
    relevance=0.95
))

# Claude Code reads:
index = json.load(open(".claude/context/index.json"))
if index["check_now"]["count"] > 0:
    # Surface findings to user
    immediate_findings = json.load(open(".claude/context/immediate.json"))
```

### Agent ↔ Agent Communication

Agents communicate via events on the EventBus.

#### Event Broadcasting Pattern

```python
# Linter finds auto-fixable issues
await event_bus.emit(Event(
    type="linter:errors-found",
    payload={
        "file": "app.py",
        "autoFixable": True,
        "errors": [...]
    }
))

# Formatter listens and auto-fixes
class FormatterAgent:
    triggers = ["linter:errors-found"]

    async def handle(self, event: Event):
        if event.payload.get("autoFixable"):
            await self.format(event.payload["file"])
```

#### Agent Chains

Agents can be chained for sequential execution:

```python
# Pre-commit chain
file:save → security-scanner → linter → test-runner → commit-check
```

---

## Integration Patterns

### Pattern 1: Claude Code Integration

**Scenario:** Developer asks Claude Code for help after editing files

```
1. Developer edits files manually
2. Background agents run and find issues
3. Developer asks Claude Code: "Are there any issues?"
4. Claude Code reads .claude/context/index.json
5. Claude Code responds: "The linter found 3 issues..."
```

**Implementation:**
```python
# Claude Code (in its system) checks context after file operations
def after_edit_tool(file_path: str):
    index = read_file(".claude/context/index.json")
    if index["check_now"]["count"] > 0:
        mention_findings_to_user(index)
```

### Pattern 2: Proactive Feedback

Claude Code can proactively check agent status:

```
User: "Add a new function to app.py"

Claude Code:
  [Uses Edit tool]
  [Waits 2s for agents]
  [Checks .claude/context/index.json]

  "I've added the function. The linter found 1 style issue
   which I've already fixed. All tests passing!"
```

### Pattern 3: Pre-Commit Validation

```
1. Developer: git commit -m "Add feature"
2. Git pre-commit hook triggers
3. Agents run in sequence:
   - Security Scanner → ✅ Pass
   - Linter → ✅ Pass
   - Test Runner → ❌ 2 tests fail
4. Commit blocked
5. Developer can read error details in context store
```

---

## Agent Communication Protocols

### 1. Context Update Protocol

```python
# Agent publishes result
await context_store.add_finding(finding)

# Emits event for other agents
await event_bus.emit(Event(
    type=f"agent:{agent_name}:completed",
    payload={"findings": [...]}
))
```

### 2. Agent Coordination

**Debounced Cascade:**
```
file:save → [wait 500ms] → linter + formatter (parallel)
                         ↓
                    [wait for both]
                         ↓
                    test-runner
```

**Priority-Based Execution:**
```
git:pre-commit → [Critical]: security-scanner
              ↓
              [High]: linter, test-runner (parallel)
              ↓
              [Normal]: commit-assistant
```

### 3. Shared State

Agents can access shared project state:

```python
# Current state available to all agents
class ProjectState:
    current_branch: str
    files_changed: List[str]
    test_status: TestStatus
    lint_status: LintStatus
```

---

## Extension Points

### Creating Custom Agents

```python
from dev_agents.core.agent import Agent, AgentResult
from dev_agents.core.event import Event

class MyCustomAgent(Agent):
    def __init__(self, config: dict, event_bus):
        super().__init__(
            name="my-custom-agent",
            triggers=["file:modified"],
            event_bus=event_bus
        )
        self.config = config

    async def handle(self, event: Event) -> AgentResult:
        # Your agent logic here
        file_path = event.payload.get("path")

        # Do analysis...

        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0.5,
            message=f"Analyzed {file_path}",
            data={"issues": [...]}
        )
```

### Registering Custom Agents

```python
# In main.py
from my_agents import MyCustomAgent

if config.is_agent_enabled("my-custom-agent"):
    custom_agent = MyCustomAgent(
        config=config.get_agent_config("my-custom-agent"),
        event_bus=event_bus
    )
    agent_manager.register(custom_agent)
```

---

## Performance Considerations

### Resource Management

- **Debouncing:** File events debounced by 500ms to avoid rapid re-runs
- **Concurrency Limits:** Max 5 agents run concurrently by default
- **Memory:** Context store uses JSON files (lightweight)
- **Storage:** Event store uses SQLite (efficient queries)

### Optimization Strategies

1. **Related Tests Only:** Test runner only runs affected tests
2. **Incremental Analysis:** Linter caches results
3. **Async Execution:** All agents async for parallelism
4. **Resource Monitoring:** Performance agent tracks CPU/memory usage

---

## Security & Privacy

- **Local-First:** All data stays on your machine
- **No Network:** No external API calls by default
- **Sandboxing:** Agents run in isolated async contexts
- **File Exclusions:** `.git/`, `node_modules/`, etc. ignored
- **Audit Log:** All agent actions logged to `.claude/events.db`

---

## Summary

The dev-agents architecture provides:

✅ **Event-driven system** for reactive automation
✅ **Modular agent design** for easy extension
✅ **Shared context store** for agent coordination
✅ **Claude Code integration** via context files
✅ **Local-first approach** for privacy
✅ **Configurable behavior** for flexibility

---

## Related Documentation

- [Getting Started](./getting-started.md) - Installation and usage
- [CLAUDE.md](../CLAUDE.md) - System overview and principles
- [Reference Docs](./reference/) - API and configuration reference
- [CHANGELOG.md](../CHANGELOG.md) - Version history

---

**Architecture Version:** 0.1.0 (November 2025)
