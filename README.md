# Claude Agents - Prototype

Background agents for development workflow automation.

**⚠️ This is a PROTOTYPE** - A minimal working implementation to validate the core architecture.

## What Works

- ✅ Event bus with pub/sub pattern
- ✅ Base agent framework with lifecycle management
- ✅ Filesystem watcher using watchdog
- ✅ Two example agents (EchoAgent, FileLoggerAgent)
- ✅ Simple CLI interface
- ✅ Basic tests

## Installation

```bash
# Install poetry if you don't have it
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
cd claude-agents
poetry install

# Activate virtual environment
poetry shell
```

## Quick Start

### 1. Initialize in a project

```bash
claude-agents init /path/to/your/project
```

This creates a `.claude/` directory.

### 2. Watch for file changes

```bash
cd /path/to/your/project
claude-agents watch .
```

### 3. Make some file changes

In another terminal, edit files in your project:

```bash
echo "hello" > test.txt
echo "world" >> test.txt
```

### 4. Observe the agents

You should see:
- Console output from the EchoAgent logging each event
- A `.claude/file-changes.log` file with JSON logs

### 5. Stop watching

Press `Ctrl+C` to stop the watch process.

## Example Output

```
Claude Agents Prototype
Watching: /home/user/myproject

✓ Agents started:
  • echo - logs all file events
  • file-logger - writes changes to .claude/file-changes.log

Waiting for file changes... (Ctrl+C to stop)

[INFO] agent.echo: ✓ echo: Received file:created from filesystem: test.txt (0.00s)
[INFO] agent.file-logger: ✓ file-logger: Logged file:created: test.txt (0.00s)
[INFO] agent.echo: ✓ echo: Received file:modified from filesystem: test.txt (0.00s)
[INFO] agent.file-logger: ✓ file-logger: Logged file:modified: test.txt (0.00s)
```

## Architecture Validation

This prototype validates:

1. **Event System**: Events flow correctly from collectors → event bus → agents
2. **Agent Framework**: Agents can subscribe to events and process them asynchronously
3. **Lifecycle Management**: Agents start, run, and stop cleanly
4. **Filesystem Watching**: Watchdog integration works and emits correct events
5. **Extensibility**: Easy to add new agents by subclassing `Agent`

## What's Next

Once this prototype is validated, we'll build:

1. **More Collectors**: Git hooks, process monitoring, IDE integration
2. **Real Agents**: Linter, formatter, test runner, security scanner, etc.
3. **Context Store**: Shared context for agent coordination
4. **Notifications**: Desktop notifications, terminal UI
5. **Configuration**: Full JSON-based configuration system
6. **Agent Chains**: Dependencies and sequential execution
7. **Coding Agent Integration**: Claude Code/Amp integration

## Testing

```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=claude_agents

# Run tests verbosely
poetry run pytest -v
```

## Development

The codebase is organized as:

```
src/claude_agents/
├── core/           # Event system, base agent class
├── collectors/     # Event collectors (filesystem, git, etc.)
├── agents/         # Built-in agents
└── cli/            # CLI interface
```

### Adding a New Agent

Create a new file in `src/claude_agents/agents/`:

```python
from claude_agents.core.agent import Agent, AgentResult
from claude_agents.core.event import Event


class MyAgent(Agent):
    async def handle(self, event: Event) -> AgentResult:
        # Your logic here
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0,
            message="Did something cool"
        )
```

Then register it in `cli/main.py`:

```python
my_agent = MyAgent(
    name="my-agent",
    triggers=["file:modified"],
    event_bus=event_bus
)
await my_agent.start()
```

## CLI Commands

```bash
# Watch a directory
claude-agents watch [PATH]

# Watch with verbose logging
claude-agents watch --verbose

# Initialize .claude directory
claude-agents init [PATH]

# Show version
claude-agents version
```

## Architecture

```
Filesystem Changes → FileSystemCollector → EventBus → Agents → Results
                                              ↓
                                          Event Log
```

## License

TBD

## Contributing

This is a prototype. Feedback welcome!
