# Claude Agents v2 - Production Ready

**Background agents for automated development workflow**

Automatically lint, format, and test your code as you work. No configuration needed, works out of the box!

## ✨ Features

- 🔍 **Auto-linting** - Catch issues as you code (ruff, eslint)
- 🎨 **Auto-formatting** - Keep code clean (black, prettier)
- 🧪 **Auto-testing** - Run related tests automatically (pytest, jest)
- ⚡ **Fast** - Agents run in parallel, non-blocking
- 🎯 **Smart** - Only runs tests related to changed files
- 🛠️ **Configurable** - Full JSON configuration support
- 🌍 **Multi-language** - Python, JavaScript, TypeScript support

## 🚀 Quick Start

### 1. Install

```bash
cd /home/wioot/dev/claude-agents
pip install -e .
```

### 2. Install Tools (choose what you need)

```bash
# Python tools
pip install ruff black pytest

# JavaScript/TypeScript tools (optional)
npm install -g eslint prettier jest
```

### 3. Initialize Your Project

```bash
cd /path/to/your/project
claude-agents init
```

This creates `.claude/agents.json` with sensible defaults.

### 4. Start Watching

```bash
claude-agents watch
```

### 5. Edit Files and Watch the Magic! ✨

```python
# Edit app.py
def hello():
    x=1+2  # Linter: suggests spacing
    return"hello"  # Formatter: will fix this
```

**Output:**
```
[INFO] agent.linter: ✓ linter: Found 2 issues in app.py (0.12s)
[INFO] agent.formatter: ✓ formatter: Formatted app.py with black (0.08s)
[INFO] agent.test-runner: ✓ test-runner: ✓ 3 test(s) passed (0.95s)
```

## 📖 Usage

### Commands

```bash
# Watch current directory
claude-agents watch

# Watch specific directory
claude-agents watch /path/to/project

# Verbose mode
claude-agents watch --verbose

# Use custom config
claude-agents watch --config /path/to/agents.json
```

### Other Commands

```bash
# Initialize project
claude-agents init

# Show agent status
claude-agents status

# Show configuration
claude-agents config show

# Reset configuration
claude-agents config reset

# Show version
claude-agents version
```

## ⚙️ Configuration

Configuration is stored in `.claude/agents.json`:

```json
{
  "version": "1.0.0",
  "enabled": true,
  "agents": {
    "linter": {
      "enabled": true,
      "triggers": ["file:modified", "file:created"],
      "config": {
        "autoFix": false,
        "filePatterns": ["**/*.py", "**/*.js", "**/*.ts"],
        "linters": {
          "python": "ruff",
          "javascript": "eslint",
          "typescript": "eslint"
        }
      }
    },
    "formatter": {
      "enabled": true,
      "triggers": ["file:modified"],
      "config": {
        "formatOnSave": true,
        "filePatterns": ["**/*.py", "**/*.js", "**/*.ts"],
        "formatters": {
          "python": "black",
          "javascript": "prettier",
          "typescript": "prettier"
        }
      }
    },
    "test-runner": {
      "enabled": true,
      "triggers": ["file:modified", "file:created"],
      "config": {
        "runOnSave": true,
        "relatedTestsOnly": true,
        "testFrameworks": {
          "python": "pytest",
          "javascript": "jest",
          "typescript": "jest"
        }
      }
    }
  }
}
```

### Customizing

**Disable an agent:**
```json
{
  "agents": {
    "formatter": {
      "enabled": false
    }
  }
}
```

**Enable auto-fix:**
```json
{
  "agents": {
    "linter": {
      "config": {
        "autoFix": true
      }
    }
  }
}
```

**Run all tests (not just related):**
```json
{
  "agents": {
    "test-runner": {
      "config": {
        "relatedTestsOnly": false
      }
    }
  }
}
```

## 🏗️ How It Works

```
File Change → FileSystemCollector → EventBus → Agents (parallel)
                                        ↓
                        [Linter] [Formatter] [TestRunner]
                                        ↓
                              Results logged
```

1. **Watchdog** monitors your filesystem for changes
2. **EventBus** distributes events to interested agents
3. **Agents** run in parallel, processing events asynchronously
4. **Results** are logged to console

All without blocking your workflow!

## 🎯 Supported Tools

### Python
- **Linter**: ruff (default), pylint, flake8
- **Formatter**: black (default)
- **Tests**: pytest (default), unittest

### JavaScript/TypeScript
- **Linter**: eslint (default)
- **Formatter**: prettier (default)
- **Tests**: jest (default), mocha

## 🧪 Examples

### Python Project

```bash
# Install tools
pip install ruff black pytest

# Init and watch
claude-agents init
claude-agents watch
```

Now edit `app.py` and `test_app.py` - agents will run automatically!

### JavaScript Project

```bash
# Install tools
npm install -g eslint prettier jest

# Init and watch
claude-agents init
claude-agents watch
```

Edit your `.js` files and watch agents work!

### Mixed Project

Claude Agents handles multiple languages automatically. Just install the tools you need:

```bash
pip install ruff black pytest
npm install -g eslint prettier jest

claude-agents watch
```

## 📊 Agent Details

### LinterAgent

**What it does**: Runs linters on code changes

**Supported**:
- Python: `ruff check`
- JavaScript/TypeScript: `eslint --format json`

**Features**:
- Parses JSON output
- Reports issues with file/line numbers
- Optional auto-fix with `autoFix: true`

### FormatterAgent

**What it does**: Auto-formats code on save

**Supported**:
- Python: `black`
- JavaScript/TypeScript/JSON/Markdown: `prettier --write`

**Features**:
- Preserves file encoding
- Respects project config (`.prettierrc`, `pyproject.toml`)
- Can be disabled per-language

### TestRunnerAgent

**What it does**: Runs tests related to changed files

**Supported**:
- Python: `pytest -v`
- JavaScript/TypeScript: `jest --json`

**Features**:
- **Smart test detection**:
  - Detects if file is test or source
  - Finds related tests automatically
  - Example: `app.py` → runs `test_app.py`
- Parses test results (passed/failed/skipped)
- Reports failures with details
- Optional: run all tests with `relatedTestsOnly: false`

## 🔧 Development

### Project Structure

```
src/claude_agents/
├── core/               # Framework
│   ├── event.py       # Event bus
│   ├── agent.py       # Base agent
│   ├── manager.py     # Agent manager
│   └── config.py      # Configuration
├── agents/            # Agent implementations
│   ├── linter.py      # Linter agent
│   ├── formatter.py   # Formatter agent
│   └── test_runner.py # Test runner agent
├── collectors/        # Event collectors
│   └── filesystem.py  # File watcher
└── cli/               # CLI interface
    └── main.py        # Commands
```

### Adding a New Agent

1. Create `src/claude_agents/agents/my_agent.py`:

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
            message="Did something cool!"
        )
```

2. Register in `agents/__init__.py`
3. Add to CLI in `cli/main.py`
4. Add default config in `core/config.py`

Done!

## 🐛 Troubleshooting

**"ruff not installed"**
```bash
pip install ruff
```

**"eslint not installed"**
```bash
npm install -g eslint
```

**"No tests found"**
- Test files must match patterns: `test_*.py`, `*.test.js`, etc.
- Or disable `relatedTestsOnly` in config

**Agents not running**
- Check `.claude/agents.json` - are agents enabled?
- Run with `--verbose` to see detailed logs

## 📚 Documentation

- [PHASE2_COMPLETE.md](./PHASE2_COMPLETE.md) - What we built
- [IMPLEMENTATION.md](./IMPLEMENTATION.md) - Implementation guide
- [INTERACTION_MODEL.md](./INTERACTION_MODEL.md) - How agents interact
- [CLAUDE.md](./CLAUDE.md) - System specification

## 🎉 What's New in v2

**v1 (Prototype)**:
- Basic event system
- Echo agent (for testing)
- Filesystem watcher

**v2 (Production)**:
- ✅ Real linting (ruff, eslint)
- ✅ Real formatting (black, prettier)
- ✅ Real testing (pytest, jest)
- ✅ Configuration file support
- ✅ Agent manager
- ✅ Multi-language support
- ✅ Intelligent test detection
- ✅ Auto-fix capabilities

## 🚦 Status

**Current**: Phase 2 Complete ✅
**Next**: Integration with Claude Code/Amp, Git hooks, Context store

## 🤝 Contributing

This is a personal project but feedback welcome! Open issues on GitHub.

## 📝 License

TBD

---

**Made with ❤️  for developers who want automated code quality**
