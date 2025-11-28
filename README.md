# Dev Agents

> **Intelligent background agents for development workflow automation** — automate code quality checks, testing, documentation, and more while you code.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests Passing](https://img.shields.io/badge/tests-112%20passing-green.svg)](#testing)
[![Production Ready](https://img.shields.io/badge/status-production%20ready-brightgreen.svg)](#status)
[![License](https://img.shields.io/badge/license-TBD-blue.svg)](#license)

## Status

✅ **PRODUCTION READY** — Full implementation with Phase 1, 2, and 3 complete. [View detailed implementation status →](./IMPLEMENTATION_STATUS.md)

---

## Features

Dev Agents runs background agents that automatically:

- **🔍 Linting & Type Checking** — Detect issues as you code (mypy, custom linters)
- **📝 Code Formatting** — Auto-format files with Black, isort, and more
- **✅ Testing** — Run relevant tests on file changes
- **🔐 Security Scanning** — Find vulnerabilities with Bandit
- **📚 Documentation** — Keep docs in sync with code changes
- **⚡ Performance** — Track performance metrics and detect regressions
- **🎯 Git Integration** — Generate smart commit messages
- **🤖 Custom Agents** — Create no-code agents via builder pattern
- **📊 Learning System** — Automatically learn patterns and optimize behavior
- **🔄 Auto-fix** — Safely apply fixes (configurable safety levels)

All agents run **non-intrusively in the background**, respecting your workflow.

---

## Quick Start

### Installation

**Prerequisites:** Python 3.11+, Poetry

```bash
# Clone the repository
git clone https://github.com/wioota/dev-agents
cd dev-agents

# Install poetry (if needed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Initialize & Run

```bash
# 1. Initialize in your project
dev-agents init /path/to/your/project

# 2. (Optional) Configure behavior in .claude/agents.json
# 3. Start watching for changes
cd /path/to/your/project
dev-agents watch .

# 4. Make code changes and watch agents respond
```

**That's it!** Dev Agents will now monitor your project and run agents on file changes.

### Common Commands

```bash
# Watch a directory for changes
dev-agents watch .

# Show agent status and health
dev-agents status

# View current findings in Amp
/agent-summary          # Recent findings
/agent-summary today    # Today's findings
/agent-summary --agent linter --severity error

# Create a custom agent (Phase 3)
dev-agents phase3 custom-create my_agent pattern_matcher
```

[View all CLI commands →](./docs/cli-commands.md)

---

## Architecture

```
File Changes → Collectors → Event Bus → Agents → Results
  (Filesystem)   (Git, Etc)    (Pub/Sub)   (8 built-in + custom)
                                   ↓
                            Context Store
                          (shared state)
                                   ↓
                            Findings & Metrics
```

### Core Components

| Component | Purpose |
|-----------|---------|
| **Event Bus** | Pub/sub system for agent coordination |
| **Collectors** | Monitor filesystem, git, process, system events |
| **Agents** | Process events and produce findings |
| **Context Store** | Shared development context |
| **CLI** | Command-line interface and Amp integration |
| **Config** | JSON-based configuration system |

[Read the full architecture guide →](./docs/architecture.md)

---

## Agents

Dev Agents includes **8 built-in agents** out of the box:

### Phase 1: Core Agents
- **Linter Agent** — Runs linters on changed files
- **Formatter Agent** — Auto-formats code (Black, isort, etc.)
- **Type Checker Agent** — Background type checking (mypy)
- **Test Runner Agent** — Runs relevant tests on changes
- **Git Commit Assistant** — Suggests commit messages

### Phase 2: Extended Agents
- **Security Scanner Agent** — Detects vulnerabilities (Bandit)
- **Performance Profiler Agent** — Tracks performance metrics
- **Doc Lifecycle Agent** — Manages documentation organization

### Phase 3: Custom Agents
Create your own agents without writing code:

```python
from dev_agents.core.custom_agent import AgentBuilder, CustomAgentType

# Create a custom pattern matcher
config = (
    AgentBuilder("todo_finder", CustomAgentType.PATTERN_MATCHER)
    .with_description("Find TODO comments")
    .with_triggers("file:created", "file:modified")
    .with_config(patterns=[r"#\s*TODO:.*"])
    .build()
)
```

[View agent documentation →](./docs/agents.md)

---

## Configuration

Configure agent behavior in `.claude/agents.json`:

```json
{
  "global": {
    "autonomousFixes": {
      "enabled": true,
      "safetyLevel": "safe_only"
    },
    "maxConcurrentAgents": 5,
    "resourceLimits": {
      "maxCpu": 25,
      "maxMemory": "500MB"
    }
  },
  "agents": {
    "linter": {
      "enabled": true,
      "triggers": ["file:save", "git:pre-commit"],
      "config": {
        "debounce": 500,
        "filePatterns": ["**/*.py"]
      }
    }
  }
}
```

**Safety levels:**
- `safe_only` — Only fix whitespace/indentation
- `medium_risk` — Include import/formatting fixes
- `all` — Apply all fixes (use with caution)

[Full configuration reference →](./docs/configuration.md)

---

## Usage Examples

### Example 1: Auto-Format on Save

```bash
# Agent automatically runs Black, isort when you save a file
echo "x=1" > app.py  # Auto-formatted to x = 1

# View findings
/agent-summary recent
```

### Example 2: Run Tests on Changes

```bash
# Test runner agent detects changed test files
# Automatically runs: pytest path/to/changed_test.py

# Or view all test results
/agent-summary --agent test-runner
```

### Example 3: Create Custom Pattern Matcher

```bash
# Create agent to find TODO comments
dev-agents phase3 custom-create find_todos pattern_matcher \
  --description "Find TODO comments" \
  --triggers file:created,file:modified

# List your custom agents
dev-agents phase3 custom-list
```

### Example 4: Learn & Optimize

```bash
# View learned patterns
dev-agents phase3 learning-insights --agent linter

# Get recommendations
dev-agents phase3 learning-recommendations linter

# Check performance data
dev-agents phase3 perf-summary --agent formatter
```

[More examples →](./examples/)

---

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage report
poetry run pytest --cov=dev_agents

# Run specific test file
poetry run pytest tests/unit/agents/test_linter.py -v

# Run tests with output
poetry run pytest -v
```

**Current status:** ✅ 112+ tests passing

[View test strategy →](./docs/testing.md)

---

## Development

### Project Structure

```
dev-agents/
├── src/dev_agents/
│   ├── core/              # Event system, agents, context
│   ├── collectors/        # Event collectors
│   ├── agents/            # Built-in agents
│   └── cli/               # CLI interface
├── tests/                 # Unit and integration tests
├── docs/                  # Documentation
├── examples/              # Usage examples
└── pyproject.toml         # Poetry configuration
```

### Adding a New Agent

1. Create `src/dev_agents/agents/my_agent.py`:

```python
from dev_agents.core.agent import Agent, AgentResult
from dev_agents.core.event import Event

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

2. Register in `src/dev_agents/cli/main.py`

3. Add tests in `tests/unit/agents/test_my_agent.py`

[Developer guide →](./docs/development.md)

### Code Style

- **Formatter:** Black
- **Linter:** Ruff
- **Type Checker:** mypy
- **Python Version:** 3.11+

Run formatters:
```bash
poetry run black src tests
poetry run ruff check --fix src tests
poetry run mypy src
```

---

## Documentation

- **[Getting Started Guide](./docs/getting-started.md)** — Installation and basic usage
- **[Architecture Guide](./docs/architecture.md)** — System design and components
- **[Agent Reference](./docs/agents.md)** — All available agents
- **[Configuration Guide](./docs/configuration.md)** — Full config reference
- **[CLI Commands](./docs/cli-commands.md)** — Command reference
- **[Development Guide](./docs/development.md)** — Contributing guide
- **[Implementation Status](./IMPLEMENTATION_STATUS.md)** — What's implemented
- **[Phase 3 Complete](./PHASE3_COMPLETE.md)** — Learning & optimization features

---

## Design Principles

Dev Agents follows these core principles:

✅ **Non-Intrusive** — Runs in background without blocking workflow  
✅ **Event-Driven** — All actions triggered by observable events  
✅ **Configurable** — Fine-grained control over agent behavior  
✅ **Context-Aware** — Understands your project structure  
✅ **Parallel** — Multiple agents run concurrently  
✅ **Lightweight** — Respects system resources  

[Read the full design spec →](./AGENTS.md)

---

## Troubleshooting

### Agents not running

```bash
# Check status
dev-agents status

# View logs
tail -f .claude/agent.log

# Enable verbose mode
dev-agents watch . --verbose
```

### Performance issues

Check `.claude/agents.json`:

```json
{
  "global": {
    "maxConcurrentAgents": 2,
    "resourceLimits": {
      "maxCpu": 10,
      "maxMemory": "200MB"
    }
  }
}
```

### Custom agents not found

```bash
# Verify they exist
dev-agents phase3 custom-list

# Check storage
ls -la .claude/custom_agents/
```

[Full troubleshooting guide →](./docs/troubleshooting.md)

---

## Performance

- **Memory:** ~50MB base + ~10MB per agent
- **CPU:** <5% idle, 10-25% when processing
- **Startup:** <1 second
- **Event latency:** <100ms typical

All operations are async and non-blocking.

---

## Roadmap

### Completed ✅
- Phase 1: Core agents and event system
- Phase 2: Extended agents and advanced features
- Phase 3: Custom agents and learning system

### In Development 🚀
- Cloud pattern repository (opt-in)
- Agent composition and pipelines
- Community agent sharing

### Future 🔮
- Multi-project support
- Team coordination features
- LLM-powered agents

---

## Contributing

Contributions welcome! Please read [CODING_RULES.md](./CODING_RULES.md) for:

- Code style guidelines
- Testing requirements
- Commit message format
- Pull request process

### Development Setup

```bash
git clone https://github.com/wioota/dev-agents
cd dev-agents
poetry install
poetry run pytest
```

### Running Tests

```bash
# All tests
poetry run pytest

# Specific test file
poetry run pytest tests/unit/agents/test_linter.py

# With coverage
poetry run pytest --cov=dev_agents
```

---

## License

TBD

---

## Support

- 📚 **Documentation:** [./docs/](./docs/)
- 🐛 **Issues:** [GitHub Issues](https://github.com/wioota/dev-agents/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/wioota/dev-agents/discussions)
- 🤝 **Contributing:** [CONTRIBUTING.md](./CODING_RULES.md)

---

## Acknowledgments

Built with:
- [Watchdog](https://github.com/gorakhargosh/watchdog) — File system monitoring
- [Typer](https://typer.tiangolo.com/) — CLI framework
- [Pydantic](https://docs.pydantic.dev/) — Data validation
- [Rich](https://rich.readthedocs.io/) — Terminal output

---

**Made with ❤️ by the Dev Agents team**

