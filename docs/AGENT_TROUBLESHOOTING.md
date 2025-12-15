# Agent Troubleshooting

## Agent Not Running

### Check Agent Status

```bash
devloop status
```

### Check Agent Configuration

```bash
# Verify agent is enabled
cat .devloop/agents.json | grep -A 5 "your-agent-name"
```

### Check Logs

```bash
# View agent execution logs
tail -f .devloop/devloop.log | grep "your-agent-name"
```

## Agent Fails Silently

Enable verbose logging:

```bash
devloop watch . --foreground --verbose
```

## Agent Running Too Often

Add debouncing:

```json
{
  "agents": {
    "my-agent": {
      "enabled": true,
      "config": {
        "debounce": 1000
      }
    }
  }
}
```

## Agent Using Too Many Resources

Set resource limits:

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

## Agent Dependencies Missing

```bash
# Check agent dependencies
devloop agent dependencies check ./my-agent

# Install missing dependencies
devloop agent dependencies resolve ./my-agent
```

## See Also

- [AGENT_DEVELOPMENT.md](./AGENT_DEVELOPMENT.md) - Development guide
- [troubleshooting.md](./troubleshooting.md) - General troubleshooting
