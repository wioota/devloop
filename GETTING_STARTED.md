# Getting Started with Claude Agents

## Prerequisites

You'll need:
- Python 3.11 or higher
- pip or poetry for package management
- The linters/formatters/test frameworks you want to use

## Installation

### Option 1: Using pip with virtual environment (Recommended)

```bash
# Navigate to the project
cd /home/wioot/dev/claude-agents

# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install claude-agents
pip install -e .

# Install tools you want to use
pip install ruff black pytest  # For Python
npm install -g eslint prettier jest  # For JavaScript (optional)
```

### Option 2: Using Poetry

```bash
cd /home/wioot/dev/claude-agents

# Install Poetry if you don't have it
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate shell
poetry shell

# Install tools
pip install ruff black pytest
```

### Option 3: System-wide with pipx

```bash
# Install pipx
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install claude-agents
pipx install /home/wioot/dev/claude-agents
```

## Quick Start

### 1. Test Installation

```bash
# Should show version
claude-agents version

# Should show help
claude-agents --help
```

### 2. Try on a Test Project

```bash
# Create a test project
mkdir ~/test-project
cd ~/test-project

# Create a simple Python file with issues
cat > app.py << 'EOF'
def hello( ):
    x=1+2
    return"Hello World"

def goodbye():
    y =  3  +  4
    return "Goodbye"
EOF

# Create a test file
cat > test_app.py << 'EOF'
from app import hello, goodbye

def test_hello():
    assert hello() == "Hello World"

def test_goodbye():
    assert goodbye() == "Goodbye"
EOF

# Initialize claude-agents
claude-agents init

# Start watching
claude-agents watch --verbose
```

### 3. Edit Files and Watch

In another terminal:

```bash
cd ~/test-project

# Make a change to trigger agents
echo "" >> app.py

# Or edit with your favorite editor
vim app.py
```

You should see output like:

```
[INFO] agent.linter: ✓ linter: Found 3 issues in app.py (0.15s)
[INFO] agent.formatter: ✓ formatter: Formatted app.py with black (0.08s)
[INFO] agent.test-runner: ✓ test-runner: ✓ 2 test(s) passed (0.95s)
```

## Usage Examples

### Example 1: Python Project

```bash
# Setup
mkdir my-python-app
cd my-python-app
python3 -m venv .venv
source .venv/bin/activate

# Install tools
pip install ruff black pytest

# Install claude-agents
pip install -e /home/wioot/dev/claude-agents

# Initialize
claude-agents init

# Start watching
claude-agents watch
```

**What happens:**
- Edit `.py` files → Linter runs (ruff)
- Save `.py` files → Formatter runs (black)
- Change source code → Related tests run (pytest)

### Example 2: JavaScript Project

```bash
# Setup
mkdir my-js-app
cd my-js-app
npm init -y

# Install tools
npm install --save-dev eslint prettier jest

# Install claude-agents
# (Use system installation or venv)

# Initialize
claude-agents init

# Edit config for JS
cat > .claude/agents.json << 'EOF'
{
  "version": "1.0.0",
  "enabled": true,
  "agents": {
    "linter": {
      "enabled": true,
      "triggers": ["file:modified"],
      "config": {
        "filePatterns": ["**/*.js"],
        "linters": {"javascript": "eslint"}
      }
    },
    "formatter": {
      "enabled": true,
      "triggers": ["file:modified"],
      "config": {
        "filePatterns": ["**/*.js"],
        "formatters": {"javascript": "prettier"}
      }
    },
    "test-runner": {
      "enabled": true,
      "triggers": ["file:modified"],
      "config": {
        "testFrameworks": {"javascript": "jest"}
      }
    }
  }
}
EOF

# Start watching
claude-agents watch
```

### Example 3: Mixed Python/JavaScript Project

```bash
# Install both sets of tools
pip install ruff black pytest
npm install -g eslint prettier jest

# Initialize
claude-agents init

# Watch - agents will handle both languages automatically
claude-agents watch
```

## Configuration

### View Current Config

```bash
claude-agents status
```

### Customize Configuration

Edit `.claude/agents.json`:

```json
{
  "version": "1.0.0",
  "enabled": true,
  "agents": {
    "linter": {
      "enabled": true,
      "triggers": ["file:modified", "file:created"],
      "config": {
        "autoFix": true,  // Enable auto-fix
        "filePatterns": ["**/*.py"],
        "linters": {
          "python": "ruff"
        }
      }
    },
    "formatter": {
      "enabled": false,  // Disable formatter
      "triggers": ["file:modified"],
      "config": {
        "formatOnSave": true,
        "filePatterns": ["**/*.py"],
        "formatters": {
          "python": "black"
        }
      }
    },
    "test-runner": {
      "enabled": true,
      "triggers": ["file:modified"],
      "config": {
        "runOnSave": true,
        "relatedTestsOnly": false,  // Run all tests
        "testFrameworks": {
          "python": "pytest"
        }
      }
    }
  }
}
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'pydantic'"

```bash
# Make sure you're in the virtual environment
source .venv/bin/activate

# Install dependencies
pip install pydantic watchdog typer rich
```

### "ModuleNotFoundError: No module named 'claude_agents'"

```bash
# Install in development mode
cd /home/wioot/dev/claude-agents
pip install -e .
```

### "command not found: claude-agents"

```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Or reinstall
pip install -e /home/wioot/dev/claude-agents
```

### "ruff not installed" / "black not installed"

```bash
# Install Python tools
pip install ruff black pytest
```

### "eslint not installed" / "prettier not installed"

```bash
# Install JavaScript tools globally
npm install -g eslint prettier jest

# Or in project
npm install --save-dev eslint prettier jest
```

### Agents not running

1. Check configuration:
```bash
claude-agents status
```

2. Verify agents are enabled in `.claude/agents.json`

3. Run with verbose mode:
```bash
claude-agents watch --verbose
```

4. Check if tools are installed:
```bash
which ruff black pytest eslint prettier jest
```

## Tips & Best Practices

### 1. Start Simple

Enable one agent at a time:

```json
{
  "agents": {
    "linter": {"enabled": true},
    "formatter": {"enabled": false},
    "test-runner": {"enabled": false}
  }
}
```

### 2. Use Project-Specific Config

Each project can have its own `.claude/agents.json`:

```
my-project/
├── .claude/
│   └── agents.json  ← Project-specific config
├── src/
└── tests/
```

### 3. Ignore Patterns

By default, these are ignored:
- `.git/`
- `node_modules/`
- `__pycache__/`
- `.venv/`
- `.claude/`

### 4. Related Tests Only

For faster feedback, use `relatedTestsOnly: true`:

```json
{
  "test-runner": {
    "config": {
      "relatedTestsOnly": true
    }
  }
}
```

Changes to `app.py` will only run `test_app.py`, not the entire suite.

### 5. Auto-Fix

Enable auto-fix for linter to automatically fix simple issues:

```json
{
  "linter": {
    "config": {
      "autoFix": true
    }
  }
}
```

## Advanced Usage

### Custom Watch Path

```bash
# Watch specific directory
claude-agents watch ./src

# Watch from different location
claude-agents watch /path/to/project
```

### Custom Config File

```bash
# Use custom config
claude-agents watch --config /path/to/custom-agents.json
```

### Reset Configuration

```bash
# Reset to defaults
claude-agents config reset
```

### View Configuration

```bash
# Show current config as JSON
claude-agents config show
```

## Integration with IDEs

### VS Code

Add to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Watch with Claude Agents",
      "type": "shell",
      "command": "claude-agents watch",
      "isBackground": true,
      "problemMatcher": []
    }
  ]
}
```

Run task with `Cmd+Shift+P` → "Tasks: Run Task" → "Watch with Claude Agents"

### Terminal Multiplexer (tmux/screen)

```bash
# In one pane, run your app
python app.py

# In another pane, run agents
claude-agents watch

# Split screen to see both!
```

## Next Steps

1. **Read the docs**: See `PHASE2_COMPLETE.md` for full feature list
2. **Customize config**: Edit `.claude/agents.json` for your workflow
3. **Try git hooks**: Coming soon - pre-commit integration
4. **Claude Code integration**: Coming soon - shared context

## Help & Support

```bash
# Get help
claude-agents --help
claude-agents watch --help

# Check version
claude-agents version

# View status
claude-agents status
```

## Example Session

```bash
$ cd my-project
$ claude-agents init
✓ Created: .claude
✓ Created: .claude/agents.json
✓ Initialized!

$ claude-agents watch
Claude Agents v2
Watching: /home/user/my-project

✓ Started agents:
  • linter
  • formatter
  • test-runner

Waiting for file changes... (Ctrl+C to stop)

# (Edit app.py in another terminal)

[INFO] agent.linter: ✓ linter: Found 2 issues in app.py (0.12s)
[INFO] agent.formatter: ✓ formatter: Formatted app.py with black (0.08s)
[INFO] agent.test-runner: ✓ test-runner: ✓ 5 test(s) passed (1.05s)

# (Edit continues...)
```

---

**You're all set! Happy coding with Claude Agents! 🚀**
