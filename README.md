# DevLoop

> **Intelligent background agents for development workflow automation** — automate code quality checks, testing, documentation, and more while you code.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests Passing](https://img.shields.io/badge/tests-167%20passing-green.svg)](#testing)
[![Production Ready](https://img.shields.io/badge/status-production%20ready-brightgreen.svg)](#status)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Status

✅ **PRODUCTION READY** — Full-featured development automation system. [View detailed implementation status →](./IMPLEMENTATION_STATUS.md)

---

## Features

DevLoop runs background agents that automatically:

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
git clone https://github.com/wioota/devloop
cd devloop

# Install poetry (if needed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Initialize & Run (Fully Automated)

```bash
# 1. Initialize in your project (handles everything automatically)
devloop init /path/to/your/project
```

The `init` command automatically:
- ✅ Sets up .devloop directory and configuration
- ✅ Creates AGENTS.md and CODING_RULES.md
- ✅ Sets up git hooks (if git repo)
- ✅ Registers Amp integration (if in Amp)
- ✅ Configures commit/push discipline enforcement
- ✅ Verifies everything works

Then just:
```bash
# 2. Start watching for changes
cd /path/to/your/project
devloop watch .

# 3. Make code changes and watch agents respond
```

**That's it!** No manual configuration needed. DevLoop will automatically monitor your project, run agents on file changes, and enforce commit discipline.

[View the installation automation details →](./INSTALLATION_AUTOMATION.md)

### Common Commands

```bash
# Watch a directory for changes
devloop watch .

# Show agent status and health
devloop status

# View current findings in Amp
/agent-summary          # Recent findings
/agent-summary today    # Today's findings
/agent-summary --agent linter --severity error

# Create a custom agent
devloop custom-create my_agent pattern_matcher
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

DevLoop includes **9 built-in agents** out of the box:

### Code Quality
- **Linter Agent** — Runs linters on changed files
- **Formatter Agent** — Auto-formats code (Black, isort, etc.)
- **Type Checker Agent** — Background type checking (mypy)

### Testing & Security
- **Test Runner Agent** — Runs relevant tests on changes
- **Security Scanner Agent** — Detects vulnerabilities (Bandit)
- **Performance Profiler Agent** — Tracks performance metrics

### Development Workflow
- **Git Commit Assistant** — Suggests commit messages
- **CI Monitor Agent** — Tracks GitHub Actions status
- **Doc Lifecycle Agent** — Manages documentation organization

### Custom Agents
Create your own agents without writing code:

```python
from devloop.core.custom_agent import AgentBuilder, CustomAgentType

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

Configure agent behavior in `.devloop/agents.json`:

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
devloop custom-create find_todos pattern_matcher \
  --description "Find TODO comments" \
  --triggers file:created,file:modified

# List your custom agents
devloop custom-list
```

### Example 4: Learn & Optimize

```bash
# View learned patterns
devloop learning-insights --agent linter

# Get recommendations
devloop learning-recommendations linter

# Check performance data
devloop perf-summary --agent formatter
```

[More examples →](./examples/)

---

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage report
poetry run pytest --cov=devloop

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
devloop/
├── src/devloop/
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

1. Create `src/devloop/agents/my_agent.py`:

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

2. Register in `src/devloop/cli/main.py`

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
- **[Learning & Optimization](./PHASE3_COMPLETE.md)** — Advanced features

---

## Design Principles

DevLoop follows these core principles:

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
devloop status

# View logs
tail -f .devloop/agent.log

# Enable verbose mode
devloop watch . --verbose
```

### Performance issues

Check `.devloop/agents.json`:

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
devloop custom-list

# Check storage
ls -la .devloop/custom_agents/
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
- Core agents: linting, formatting, testing, type checking
- Security & performance: vulnerability scanning, profiling
- Workflow automation: git integration, CI monitoring, documentation
- Custom agents: create your own without writing code
- Learning system: pattern recognition and optimization

### In Development 🚀
- Cloud pattern repository (opt-in)
- Agent composition and pipelines
- Community agent sharing

### Future 🔮
- Multi-project support
- Team coordination features
- LLM-powered agents

---

## Amp Integration

Using DevLoop in Amp? See [AMP_ONBOARDING.md](./AMP_ONBOARDING.md) for:

- Installation and registration checklist
- Required configuration
- Post-task verification workflow
- Troubleshooting guide

The commit/push discipline is automatically enforced via `.agents/verify-task-complete`.

---

## Contributing

Contributions welcome! Please read [CODING_RULES.md](./CODING_RULES.md) for:

- Code style guidelines
- Testing requirements
- Commit message format
- Pull request process

### Development Setup

```bash
git clone https://github.com/wioota/devloop
cd devloop
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
poetry run pytest --cov=devloop
```

---

## License

DevLoop is released under the [MIT License](LICENSE).

This means you can freely use, modify, and distribute this software for any purpose, including commercial use, as long as you include the original copyright notice and license text.

---

## Support

- 📚 **Documentation:** [./docs/](./docs/)
- 🐛 **Issues:** [GitHub Issues](https://github.com/wioota/devloop/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/wioota/devloop/discussions)
- 🤝 **Contributing:** [CONTRIBUTING.md](./CODING_RULES.md)

---

## Acknowledgments

Built with:
- [Watchdog](https://github.com/gorakhargosh/watchdog) — File system monitoring
- [Typer](https://typer.tiangolo.com/) — CLI framework
- [Pydantic](https://docs.pydantic.dev/) — Data validation
- [Rich](https://rich.readthedocs.io/) — Terminal output

---

**Made with ❤️ by the DevLoop team**

