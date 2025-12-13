# Configuration Guide

Complete reference for DevLoop configuration options.

## Configuration Files

DevLoop uses several configuration files:

### `.devloop/agents.json` - Agent Configuration

Main configuration file controlling which agents are enabled and how they behave.

```json
{
  "enabled": true,
  "agents": {
    "linter": {
      "enabled": true,
      "triggers": ["file:save", "git:pre-commit"],
      "config": {
        "debounce": 500,
        "filePatterns": ["**/*.{js,ts,jsx,tsx}"]
      }
    },
    "formatter": {
      "enabled": true,
      "triggers": ["file:save"],
      "config": {
        "autoFix": true,
        "tools": ["black", "isort"]
      }
    }
  },
  "global": {
    "maxConcurrentAgents": 5,
    "notificationLevel": "summary",
    "resourceLimits": {
      "maxCpu": 25,
      "maxMemory": "500MB"
    },
    "logging": {
      "level": "info",
      "rotation": {
        "enabled": true,
        "maxSize": "100MB",
        "maxBackups": 3,
        "maxAgeDays": 7
      }
    }
  }
}
```

### `.devloop/custom_agents/` - Custom Agents

Directory containing custom agents created with `devloop custom-create`.

### `.devloop/devloop.log` - Application Logs

Main application log file. Rotates automatically based on size and age.

View logs:
```bash
tail -f .devloop/devloop.log
```

### `.devloop/events.db` - Event Store

SQLite database containing structured event logging for all agent activity.

Query events:
```bash
devloop audit query --limit 20
```

## Environment Variables

### Token Configuration

```bash
# GitHub token (for pre-push CI verification)
export GITHUB_TOKEN="gh_..."

# PyPI token (for releases)
export PYPI_TOKEN="pypi-..."

# Other registry tokens as needed
```

### DevLoop Runtime Options

```bash
# Set logging level (debug, info, warning, error)
export DEVLOOP_LOG_LEVEL=debug

# Set Amp thread context (for cross-thread pattern detection)
export AMP_THREAD_ID="T-abc123"
export AMP_THREAD_URL="https://ampcode.com/threads/..."

# Run in non-daemon mode
export DEVLOOP_FOREGROUND=1
```

## Agent Configuration

Each agent can be configured individually:

```json
{
  "agents": {
    "agent_name": {
      "enabled": true,
      "triggers": ["event:type"],
      "config": {
        // Agent-specific options
      }
    }
  }
}
```

### Common Agent Options

- `enabled` (boolean) - Enable/disable the agent
- `triggers` (array) - Events that trigger the agent
- `config` (object) - Agent-specific configuration

### Global Configuration

Under `global`:

- `maxConcurrentAgents` (integer) - Maximum agents to run in parallel
- `notificationLevel` (string) - How to report findings (summary, detailed, quiet)
- `resourceLimits` (object) - CPU and memory constraints
- `logging` (object) - Log level and rotation settings

## Configuration Migrations

When upgrading DevLoop, configuration files may need updates.

```bash
# Migrate configuration
devloop init --merge-templates /path/to/project
```

This automatically handles:
- Schema version updates
- New agent additions
- Deprecated option removal
- Default setting updates

## See Also

- [AGENTS.md](../AGENTS.md) - System architecture and principles
- [README.md](../README.md) - Quick start and overview
- [UPGRADE_GUIDE.md](./UPGRADE_GUIDE.md) - Version compatibility and migrations
