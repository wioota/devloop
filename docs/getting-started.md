# Getting Started with DevLoop

DevLoop provides intelligent background agents for development workflow automation.
This guide walks you through installation, initial setup, and everyday CLI usage.

## Prerequisites

**Required:**

- Python 3.11 or later (3.12 also supported)

**Optional but recommended:**

- [Poetry](https://python-poetry.org/) 1.7+ -- needed only if installing from source
- [GitHub CLI](https://cli.github.com/) (`gh`) 2.78+ -- enables the pre-push CI check hook
- [Beads MCP](https://github.com/wioota/devloop) -- provides the `bd` issue-tracking commands

## Installation

### From PyPI

```bash
pip install devloop
```

DevLoop ships several optional extras. Install only what you need:

```bash
# Marketplace API server (adds FastAPI + Uvicorn)
pip install "devloop[marketplace-api]"

# Individual optional agent integrations
pip install "devloop[snyk]"
pip install "devloop[code-rabbit]"
pip install "devloop[ci-monitor]"

# Everything at once
pip install "devloop[all-optional]"
```

### From source

```bash
git clone https://github.com/wioota/devloop.git
cd devloop
poetry install
```

To include optional extras from source:

```bash
poetry install --extras "marketplace-api"
# or install everything:
poetry install --extras "all-optional"
```

### Optional: Pyodide WASM sandbox

DevLoop can run untrusted agent code inside a Pyodide WebAssembly sandbox.
This feature requires **Node.js 18+**. During `devloop init`, you will be
prompted to install the Pyodide sandbox if Node.js is detected. You can also
install it later:

```bash
# Verify Node.js is available
node --version   # Must be v18 or later

# Re-run init to trigger the Pyodide prompt
devloop init /path/to/project
```

## Quick Setup

Initialize DevLoop in your project:

```bash
devloop init /path/to/project
```

This command performs the following steps:

1. **Creates the `.devloop/` directory** with an `agents.json` configuration file.
2. **Sets up git hooks** -- installs `pre-commit` (runs Black, Ruff, mypy, pytest)
   and `pre-push` (checks CI status via `gh`).
3. **Registers Claude Code slash commands** if you are running inside Claude Code
   (e.g., `/agent-summary`, `/agent-status`).
4. **Prompts for optional agent selection** -- choose which optional agents to
   enable (Snyk, Code Rabbit, CI Monitor, Pyodide sandbox).

After init completes, start the file watcher:

```bash
devloop watch .
```

### Non-interactive mode

If you are scripting or running in CI, skip all interactive prompts:

```bash
devloop init --non-interactive /path/to/project
```

## Common CLI Commands

Below is a quick-reference table of the most frequently used commands.

| Command | Description |
|---|---|
| `devloop watch .` | Start watching for file changes and running agents |
| `devloop status` | Show configuration and agent status |
| `devloop stop` | Stop the background daemon |
| `devloop health` | Show agent health and operational metrics |
| `devloop verify-work` | Run code-quality verification |
| `devloop agent publish ./my-agent` | Publish an agent to the marketplace |
| `devloop agent search "formatter"` | Search the marketplace for agents |
| `devloop agent install my-agent 1.0.0` | Install an agent from the marketplace |
| `devloop custom create my_agent pattern_matcher` | Create a custom agent |
| `devloop summary` | View summaries of agent findings |
| `devloop release check <version>` | Validate release preconditions |
| `devloop release publish <version>` | Publish a release (full automated workflow) |
| `devloop update-hooks` | Update git hooks from latest templates |
| `devloop extract-findings-cmd` | Extract findings and create Beads issues |

For the full list of commands, flags, and usage patterns, see
[CLI_REFERENCE.md](../CLI_REFERENCE.md).

## Amp Integration

DevLoop automatically detects when it is running inside Amp (or Claude Code)
and configures the integration during `devloop init`.

What gets set up:

- **Slash commands** -- `/agent-summary` and `/agent-status` are registered so
  you can query agent state directly from the chat interface.
- **Post-task verification hook** -- after every task, DevLoop enforces commit
  discipline by running `.agents/verify-task-complete`.
- **Claude Code hooks** -- installed under `.agents/hooks/` for pre-commit and
  post-task quality checks.

### Amp-specific CLI commands

```bash
# Show current agent status (formatted for Amp display)
devloop amp-status

# Show agent findings (formatted for Amp display)
devloop amp-findings

# Show context store index
devloop amp-context
```

### Skipping Amp setup

If you do not use Amp or Claude Code, pass `--skip-config` to avoid creating
the hooks configuration:

```bash
devloop init --skip-config /path/to/project
```

## Verifying Installation

After setup, confirm that everything is working:

```bash
# Check the installed version
devloop version

# Show agent and configuration status
devloop status

# Verify external tool dependencies (gh, node, etc.)
devloop tools

# Run the full task-completion check
.agents/verify-task-complete
```

All four commands should complete without errors.

## Upgrading

To upgrade DevLoop to the latest release:

```bash
pip install --upgrade devloop
```

After upgrading, re-run init to pick up new hook templates and configuration
changes. Existing settings in `agents.json` are preserved:

```bash
devloop init /path/to/project
```

DevLoop detects the previous version from the init manifest and prints a
summary of what changed (e.g., `Updated from v0.9.0 -> v0.10.2`).

See [UPGRADE_GUIDE.md](./UPGRADE_GUIDE.md) for detailed version migration
notes and breaking-change information.

## Next Steps

- [Configuration Guide](./configuration.md) -- tune agent behavior, thresholds,
  and notification settings.
- [Architecture Guide](./architecture.md) -- understand the daemon, agent
  categories, and event pipeline.
- [Agent Development Guide](./agent-development.md) -- build and publish your
  own custom agents.
