# Technology Stack Discussion

## Overview

This document discusses the framework and technology choices for implementing the background agent system. We need to decide between native implementation vs. leveraging existing frameworks.

## Framework Options

### Option 1: Native Python Implementation

**Approach**: Build from scratch using Python standard library + minimal dependencies

**Pros**:
- Full control over architecture and behavior
- Minimal dependencies, fewer security concerns
- Lightweight and fast
- No framework lock-in
- Tailored exactly to our needs
- Better understanding of internals

**Cons**:
- More development time
- Need to implement event loop, queuing, etc.
- More testing required
- Reinventing some wheels

**Core Dependencies**:
- `watchdog` - Filesystem monitoring
- `asyncio` - Async event processing
- `sqlite3` - Event storage (stdlib)
- `pydantic` - Configuration validation
- `typer` - CLI interface

**Recommended Stack**:
```python
# Core
asyncio           # Event loop and async processing
concurrent.futures # Thread/process pools

# Filesystem monitoring
watchdog          # Cross-platform file system events

# Configuration & validation
pydantic          # Data validation and settings
python-dotenv     # Environment variables

# Storage
sqlite3           # Event store (stdlib)
aiosqlite         # Async SQLite

# CLI
typer             # CLI framework
rich              # Terminal formatting

# Git integration
GitPython         # Git operations

# Process management
psutil            # Process monitoring
```

---

### Option 2: Pydantic AI / Pydantic

**Approach**: Use Pydantic for data validation and configuration management

**Pros**:
- Excellent type safety and validation
- Great developer experience
- Well-documented and widely used
- Plays well with Python type hints
- Can be combined with other tools

**Cons**:
- Not a complete framework for agent orchestration
- Still need to build event system, agent lifecycle, etc.
- Pydantic AI is relatively new

**Use Case**:
- Configuration validation and parsing
- Event schema validation
- Agent configuration type safety
- Can be used WITH native implementation or other frameworks

**Recommendation**: Use Pydantic for configuration regardless of other choices

---

### Option 3: CrewAI

**Approach**: Build agents using CrewAI's agent orchestration framework

**Pros**:
- Purpose-built for multi-agent systems
- Role-based agent design
- Task delegation and collaboration
- Built-in LLM integration
- Crew (team) concept matches our needs

**Cons**:
- Focused on LLM-powered agents (may be overkill)
- Less control over low-level event handling
- Heavier weight than needed
- Opinionated architecture
- Our agents are more event-driven than conversational

**Best For**:
- LLM-powered intelligent agents
- Collaborative multi-agent tasks
- Complex reasoning and decision-making

**Our Fit**:
- Moderate - good for intelligent agents (commit message assistant, refactoring suggester)
- Not ideal for simple reactive agents (linter, formatter)
- Could use CrewAI for subset of "intelligent" agents

---

### Option 4: LangChain / LangGraph

**Approach**: Use LangChain for agent orchestration and LangGraph for workflows

**Pros**:
- Mature ecosystem
- Great LLM integration
- Tools and chain abstractions
- LangGraph for stateful workflows
- Large community and examples

**Cons**:
- Heavy dependency tree
- Primarily designed for LLM applications
- Complex abstraction layers
- May be overengineered for our use case
- Performance overhead

**Best For**:
- LLM-heavy applications
- Complex conversational agents
- RAG systems
- Multi-step LLM workflows

**Our Fit**:
- Low - most of our agents don't need LLMs
- Overkill for reactive agents
- Could consider for specific intelligent agents

---

### Option 5: Temporal.io

**Approach**: Use Temporal for durable workflow orchestration

**Pros**:
- Built for distributed workflows
- Durable execution (survives crashes)
- Event-driven architecture
- Strong guarantees
- Excellent for complex workflows

**Cons**:
- Requires Temporal server
- More infrastructure complexity
- Steeper learning curve
- Overkill for single-developer tools

**Best For**:
- Distributed systems
- Long-running workflows
- Mission-critical processes
- Team environments

**Our Fit**:
- Low - too heavy for local development agents
- Better for production orchestration systems

---

### Option 6: Celery

**Approach**: Use Celery for task queue and distributed processing

**Pros**:
- Battle-tested task queue
- Supports multiple brokers (Redis, RabbitMQ)
- Scheduling and retries built-in
- Good for background tasks

**Cons**:
- Requires message broker
- More infrastructure
- Focused on task distribution, not agent orchestration
- Heavier than needed

**Best For**:
- Distributed task processing
- Background jobs
- Scheduled tasks

**Our Fit**:
- Moderate - good for task distribution
- Too heavy for simple local agents
- Overkill for single-machine use

---

### Option 7: Prefect / Dagster

**Approach**: Use modern workflow orchestration framework

**Pros**:
- Modern Python workflow orchestration
- Great UI and observability
- Task dependencies and DAGs
- Scheduling and retries

**Cons**:
- Designed for data pipelines
- More than we need
- Additional infrastructure

**Best For**:
- Data pipelines
- ETL workflows
- Scheduled batch jobs

**Our Fit**:
- Low - workflow focus doesn't match event-driven agents

---

### Option 8: Hybrid Approach

**Approach**: Combine best tools for different purposes

**Example Stack**:
```python
# Core orchestration: Native Python + asyncio
# Configuration: Pydantic
# Intelligent agents: CrewAI (subset)
# Task queue: Simple in-memory queue
# Storage: SQLite
# CLI: Typer
```

**Pros**:
- Best tool for each job
- Flexible and adaptable
- Can evolve over time
- Pragmatic approach

**Cons**:
- More complex integration
- Multiple paradigms to learn
- Potential inconsistencies

---

## Recommendation

### Primary Recommendation: **Native Python + Pydantic**

**Rationale**:

1. **Event-Driven Nature**: Our agents are primarily reactive to filesystem, git, and process events - not LLM-driven
2. **Performance**: Need lightweight, fast event processing
3. **Local Execution**: Single-developer tool, no distributed requirements
4. **Control**: Need fine-grained control over event handling, prioritization, debouncing
5. **Simplicity**: Many agents are simple (run linter, format file) - don't need heavy frameworks

**Core Architecture**:
```python
# Event system - Native asyncio
class EventSystem:
    async def collect_events(self): ...
    async def dispatch_events(self): ...

# Agent framework - Native + Pydantic
class Agent(BaseModel):  # Pydantic for config
    name: str
    triggers: List[str]

    async def handle(self, event: Event): ...

# Configuration - Pydantic
class AgentConfig(BaseSettings):
    enabled: bool
    triggers: List[str]
    config: Dict[str, Any]
```

**Optional Enhancements**:
- Use **CrewAI** for 2-3 "intelligent" agents:
  - Commit Message Assistant
  - Code Review Preparer
  - Refactoring Suggester
  - Doc Sync Agent
- Keep other agents simple and native

**Technology Stack**:
```
Core:
- Python 3.11+
- asyncio (event loop)
- Pydantic (config + validation)

Filesystem:
- watchdog (file monitoring)

Storage:
- SQLite + aiosqlite

CLI:
- Typer + Rich

Git:
- GitPython

Process Monitoring:
- psutil

Testing:
- pytest + pytest-asyncio
- pytest-mock

Optional (for intelligent agents):
- CrewAI (subset of agents)
- Anthropic API (Claude integration)
```

---

## Implementation Phases

### Phase 1: Foundation (Native)
- Event system (asyncio-based)
- Agent framework
- Configuration (Pydantic)
- Simple agents (linter, formatter, test runner)
- CLI interface

### Phase 2: Integration
- Git hook integration
- Process monitoring
- Event storage
- More reactive agents

### Phase 3: Intelligence (Optional CrewAI)
- Integrate CrewAI for intelligent agents
- LLM-powered agents (commit assistant, etc.)
- Keep reactive agents native

---

## Decision Criteria

Choose **Native + Pydantic** if:
- ✅ Need lightweight, fast performance
- ✅ Event-driven, reactive agents
- ✅ Local development tool
- ✅ Want full control
- ✅ Minimal dependencies preferred

Add **CrewAI** if:
- ✅ Want LLM-powered intelligent agents
- ✅ Complex reasoning needed
- ✅ Agent collaboration valuable

Choose **LangChain/LangGraph** if:
- ❌ Heavily LLM-focused
- ❌ Need RAG or complex LLM chains
- (Not our primary use case)

Choose **Temporal/Celery** if:
- ❌ Distributed system
- ❌ Need strong durability guarantees
- ❌ Multi-machine orchestration
- (Overkill for local dev agents)

---

## Final Recommendation

**Start with Native Python + Pydantic**:
1. Implement core event system and agent framework natively
2. Use Pydantic for all configuration and validation
3. Build 5-7 core reactive agents (linter, formatter, test runner, etc.)
4. Get feedback and iterate

**Then consider adding CrewAI**:
1. Identify 2-3 agents that benefit from LLM reasoning
2. Implement as CrewAI agents alongside native agents
3. Evaluate if the added complexity is worth it

**Advantages**:
- Start simple and fast
- Add complexity only where needed
- Avoid framework lock-in
- Easy to test and debug
- Can evolve based on actual needs

**Dependencies footprint**:
```toml
[tool.poetry.dependencies]
python = "^3.11"
pydantic = "^2.0"
pydantic-settings = "^2.0"
watchdog = "^3.0"
typer = "^0.9"
rich = "^13.0"
GitPython = "^3.1"
psutil = "^5.9"
aiosqlite = "^0.19"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
pytest-asyncio = "^0.21"
pytest-mock = "^3.11"
black = "^23.0"
ruff = "^0.1"
```

This gives us a clean, fast, maintainable foundation that can be extended as needed.
