# Configuration Guide

## Configuration File

DevLoop uses `.devloop/agents.json` for configuration:

```json
{
  "global": {
    "autonomousFixes": {
      "enabled": false,
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

## Global Settings

### Auto-fix Safety Levels

- `safe_only` - Only fix whitespace/indentation (default, recommended)
- `medium_risk` - Include import/formatting fixes
- `all` - Apply all fixes (use with caution)

⚠️ **Warning:** Auto-fixes run without backups. Use carefully.

### Resource Limits

Control agent resource usage:

```json
{
  "global": {
    "maxConcurrentAgents": 3,
    "resourceLimits": {
      "maxCpu": 10,
      "maxMemory": "200MB"
    }
  }
}
```

## Agent Configuration

Each agent can be individually configured:

```json
{
  "agents": {
    "agent-name": {
      "enabled": true,
      "triggers": ["event:type"],
      "config": {
        "option": "value"
      }
    }
  }
}
```

## Common Triggers

- `file:save` - File saved
- `file:modified` - File changed
- `file:created` - New file created
- `git:pre-commit` - Before git commit
- `git:pre-push` - Before git push

## See Also

- [CLI_REFERENCE.md](../CLI_REFERENCE.md) - Complete command reference
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture
