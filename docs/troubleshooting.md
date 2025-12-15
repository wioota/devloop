# Troubleshooting

## Agents not running

```bash
# Check status
devloop status

# View logs
tail -f .devloop/devloop.log

# Verbose mode
devloop watch . --foreground --verbose
```

## Performance issues

Adjust resource limits in `.devloop/agents.json`:

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

## Files modified unexpectedly

1. Check changes: `git diff`
2. Revert: `git checkout -- .`
3. Disable auto-fix in configuration
4. Report issue with details

## Recovery Steps

1. Stop daemon: `devloop stop .`
2. Check logs: `tail -100 .devloop/devloop.log`
3. Verify git status: `git status`
4. Recover from git if needed: `git checkout <file>`
5. Report issue: [GitHub Issues](https://github.com/wioota/devloop/issues)
