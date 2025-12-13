# Getting Started with Dev Agents

Complete guide to installing, configuring, and using dev-agents for automated code quality and testing.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [Claude Code Integration](#claude-code-integration)
- [Troubleshooting](#troubleshooting)
- [Tips & Best Practices](#tips--best-practices)
- [Advanced Usage](#advanced-usage)

---

## Prerequisites

You'll need:
- **Python 3.10 or higher**
- **pip** or **poetry** for package management
- The linters/formatters/test frameworks you want to use (optional)

---

## Installation

### Option 1: Using pip with virtual environment (Recommended)

```bash
# Navigate to the project
cd /path/to/dev-agents

# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dev-agents
pip install -e .

# Install optional tools you want to use
pip install ruff black pytest mypy bandit  # For Python
npm install -g eslint prettier jest  # For JavaScript (optional)
```

### Option 2: Using Poetry

```bash
cd /path/to/dev-agents

# Install Poetry if you don't have it
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate shell
poetry shell

# Install optional tools
pip install ruff black pytest
```

### Option 3: System-wide with pipx

```bash
# Install pipx
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install dev-agents
pipx install /path/to/dev-agents
```

### Verify Installation

```bash
# Should show version
dev-agents version

# Should show help
dev-agents --help
```

---

## Quick Start

### 1. Create a Test Project

```bash
# Create a test project
mkdir ~/test-project
cd ~/test-project

# Create a simple Python file with intentional issues
cat > app.py << 'EOF'
import os
import sys
import datetime

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
```

### 2. Initialize Dev Agents

```bash
# Initialize dev-agents in the project
dev-agents init

# This creates:
# .claude/
# └── agents.json  (default configuration)
```

You should see:
```
✓ Created: .claude
✓ Created: .claude/agents.json

✓ Initialized!

Next steps:
  1. Review/edit: .claude/agents.json
  2. Run: dev-agents watch ~/test-project
```

### 3. Start Watching (Foreground Mode)

```bash
# Start in foreground mode to see output
dev-agents watch --foreground --verbose
```

You should see:
```
Dev Agents v0.1.0
Watching: /home/user/test-project (foreground mode)

Context store: /home/user/test-project/.claude/context
Event store: /home/user/test-project/.claude/events.db

✓ Started agents:
  • linter
  • formatter
  • test-runner
  • type-checker
  • security-scanner

Waiting for file changes... (Ctrl+C to stop)
```

### 4. Trigger Agents by Editing Files

In another terminal:

```bash
cd ~/test-project

# Make a change to trigger agents
echo "" >> app.py

# Or edit with your editor
vim app.py
```

You should see output like:
```
[INFO] agent.linter: ✓ linter: Found 3 issues in app.py (0.15s)
[INFO] agent.formatter: ✓ formatter: Formatted app.py with black (0.08s)
[INFO] agent.test-runner: ✓ test-runner: ✓ 2 test(s) passed (0.95s)
```

### 5. Check Context Store

```bash
# View agent findings
ls -la .claude/context/

# Check the index (quick summary)
cat .claude/context/index.json
```

---

## Usage Examples

### Example 1: Python Project

```bash
# Setup
mkdir my-python-app
cd my-python-app
python3 -m venv .venv
source .venv/bin/activate

# Install tools
pip install ruff black pytest mypy

# Install dev-agents
pip install -e /path/to/dev-agents

# Initialize
dev-agents init

# Start watching (background mode - default)
dev-agents watch
```

**What happens:**
- Edit `.py` files → Linter runs (ruff)
- Save `.py` files → Formatter runs (black)
- Change source code → Related tests run (pytest)
- Type hints → Type checker runs (mypy)
- Security patterns → Security scanner runs (bandit)

### Example 2: JavaScript Project

```bash
# Setup
mkdir my-js-app
cd my-js-app
npm init -y

# Install tools
npm install --save-dev eslint prettier jest

# Initialize dev-agents
dev-agents init

# Customize for JavaScript
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
dev-agents watch
```

### Example 3: Background Mode (Default)

```bash
# Start in background (daemon mode)
dev-agents watch

# Output:
# ✓ Dev Agents started in background (PID: 12345)
# Run 'dev-agents stop' to stop the daemon

# Check status
dev-agents amp_status

# Check findings
dev-agents amp_findings

# View context
dev-agents amp_context

# Stop daemon
dev-agents stop
```

---

## Configuration

### View Current Configuration

```bash
dev-agents status
```

Output:
```
Agent Configuration
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Agent                ┃ Enabled ┃ Triggers              ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ linter               │ ✓      │ file:modified         │
│ formatter            │ ✓      │ file:modified         │
│ test-runner          │ ✓      │ file:modified         │
│ type-checker         │ ✓      │ file:modified         │
│ security-scanner     │ ✓      │ file:modified         │
└──────────────────────┴────────┴──────────────────────┘
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
      "enabled": true,
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
        "relatedTestsOnly": true,  // Run only related tests
        "testFrameworks": {
          "python": "pytest"
        }
      }
    },
    "type-checker": {
      "enabled": true,
      "triggers": ["file:modified"],
      "config": {
        "strict_mode": false,
        "exclude_patterns": ["test*", "*_test.py"]
      }
    },
    "security-scanner": {
      "enabled": true,
      "triggers": ["file:modified"],
      "config": {
        "severity_threshold": "medium",
        "confidence_threshold": "medium"
      }
    }
  }
}
```

---

## Claude Code Integration

Dev-agents creates context files that Claude Code (or any LLM) can read to understand agent findings.

### Context Store Structure

```
.claude/
├── context/
│   ├── index.json         # Quick summary (read this first)
│   ├── immediate.json     # Blocking issues (check now!)
│   ├── relevant.json      # Relevant issues
│   ├── background.json    # FYI issues
│   └── auto_fixed.json    # Already fixed
└── events.db              # Event history
```

### Step 1: Start Agents

```bash
cd /path/to/your/project
dev-agents watch
```

### Step 2: Make Changes

```bash
# Edit a file (triggers agents)
echo "def foo(): pass" >> src/app.py
```

### Step 3: Check Context Files

```bash
# View the index (what Claude Code reads first)
cat .claude/context/index.json
```

Example output:
```json
{
  "last_updated": "2025-11-28T12:34:56Z",
  "check_now": {
    "count": 4,
    "severity_breakdown": {"error": 4},
    "files": ["src/app.py"],
    "preview": "4 errors"
  },
  "mention_if_relevant": {
    "count": 0,
    "summary": "No relevant issues"
  }
}
```

### Step 4: Use with Claude Code

**In a Claude Code conversation:**

```
User: "Check .claude/context/index.json and tell me about any issues"

[Claude Code uses Read tool]

Claude: "I found 4 errors in src/app.py:
- 3 unused imports (os, sys, datetime)
- 1 formatting issue

Would you like me to fix these?"
```

### Proactive Checking

Claude Code can check agent status after editing files:

```
User: "Add a new function to src/app.py"

[Claude uses Edit tool]
[Claude automatically checks .claude/context/index.json]

Claude: "I've added the function. Note: The linter found 1 new issue
(unused variable 'x' on line 42). Should I fix that?"
```

See `.claude/CLAUDE.md` for full integration instructions.

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'pydantic'"

```bash
# Make sure you're in the virtual environment
source .venv/bin/activate

# Install dependencies
pip install -e .
```

### "ModuleNotFoundError: No module named 'dev_agents'"

```bash
# Install in development mode
cd /path/to/dev-agents
pip install -e .
```

### "command not found: dev-agents"

```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Or reinstall
pip install -e /path/to/dev-agents

# Or use full path
~/.local/bin/dev-agents --help
```

### "ruff not installed" / "black not installed"

```bash
# Install Python tools
pip install ruff black pytest mypy bandit
```

### "eslint not installed" / "prettier not installed"

```bash
# Install JavaScript tools globally
npm install -g eslint prettier jest

# Or in project
npm install --save-dev eslint prettier jest
```

### Agents not running

1. **Check configuration:**
```bash
dev-agents status
```

2. **Verify agents are enabled** in `.claude/agents.json`

3. **Run with verbose mode:**
```bash
dev-agents watch --foreground --verbose
```

4. **Check if tools are installed:**
```bash
which ruff black pytest eslint prettier jest
```

5. **Check daemon status (if using background mode):**
```bash
# Check if daemon is running
cat .claude/dev-agents.pid

# Check logs
cat .claude/dev-agents.log
```

### Stop stuck daemon

```bash
# Stop gracefully
dev-agents stop

# Or force kill
pkill -f "dev-agents watch"
```

---

## Tips & Best Practices

### 1. Start Simple

Enable one agent at a time when getting started:

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
- `*.pyc`, `*.log`, etc.

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

### 6. Background vs Foreground

- **Background (default):** Agents run as daemon, no terminal output
- **Foreground:** See live output, useful for debugging

```bash
# Background (production)
dev-agents watch

# Foreground (debugging)
dev-agents watch --foreground --verbose
```

---

## Advanced Usage

### Custom Watch Path

```bash
# Watch specific directory
dev-agents watch ./src

# Watch from different location
dev-agents watch /path/to/project
```

### Custom Config File

```bash
# Use custom config
dev-agents watch --config /path/to/custom-agents.json
```

### Query Agent Status (Programmatically)

```bash
# Get agent status as JSON
dev-agents amp_status

# Get findings
dev-agents amp_findings

# Get context index
dev-agents amp_context
```

### Integration with IDEs

#### VS Code

Add to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Start Dev Agents",
      "type": "shell",
      "command": "dev-agents watch --foreground",
      "isBackground": true,
      "problemMatcher": []
    }
  ]
}
```

Run: `Cmd+Shift+P` → "Tasks: Run Task" → "Start Dev Agents"

#### Terminal Multiplexer (tmux/screen)

```bash
# In one pane, run your app
python app.py

# In another pane, run agents
dev-agents watch --foreground

# Split screen to see both!
```

---

## Next Steps

1. **Read the docs:**
   - [CHANGELOG.md](../CHANGELOG.md) - Version history and features
   - [CLAUDE.md](../CLAUDE.md) - System architecture
   - [Reference docs](./reference/) - Agent specifications

2. **Customize config:** Edit `.claude/agents.json` for your workflow

3. **Integrate with Claude Code:** See `.claude/CLAUDE.md`

4. **Explore agents:** Check [agent-types.md](../agent-types.md) for full capabilities

---

## Help & Support

```bash
# Get help
dev-agents --help
dev-agents watch --help

# Check version
dev-agents version

# View status
dev-agents status
```

---

## Example Complete Session

```bash
$ cd my-project

$ dev-agents init
✓ Created: .claude
✓ Created: .claude/agents.json
✓ Initialized!

$ dev-agents watch --foreground
Dev Agents v0.1.0
Watching: /home/user/my-project (foreground mode)

Context store: /home/user/my-project/.claude/context
Event store: /home/user/my-project/.claude/events.db

✓ Started agents:
  • linter
  • formatter
  • test-runner
  • type-checker
  • security-scanner

Waiting for file changes... (Ctrl+C to stop)

# (Edit app.py in another terminal)

[INFO] agent.linter: ✓ linter: Found 2 issues in app.py (0.12s)
[INFO] agent.formatter: ✓ formatter: Formatted app.py with black (0.08s)
[INFO] agent.type-checker: ✓ type-checker: No type errors (0.45s)
[INFO] agent.test-runner: ✓ test-runner: ✓ 5 test(s) passed (1.05s)

# (Continue editing...)
```

---

**You're all set! Happy coding with Dev Agents! 🚀**
