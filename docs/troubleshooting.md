# Troubleshooting Guide

Common issues and solutions for DevLoop.

## General Issues

### Agents not running

**Check daemon status:**
```bash
devloop status
```

**View logs:**
```bash
tail -f .devloop/devloop.log
```

**Enable verbose mode:**
```bash
devloop watch . --foreground --verbose
```

### Performance issues

**Check resource usage:**
```bash
devloop health
```

**Adjust limits in `.devloop/agents.json`:**
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

**List custom agents:**
```bash
devloop custom-list
```

**Check storage:**
```bash
ls -la .devloop/custom_agents/
```

### Agent modified files unexpectedly

1. **Check what changed:**
   ```bash
   git diff
   ```

2. **Revert changes:**
   ```bash
   git checkout -- .
   ```

3. **Disable problematic agent** in `.devloop/agents.json`

4. **Report issue** with full configuration

## Installation Issues

### DevLoop command not found

**Verify installation:**
```bash
pip list | grep devloop
```

**Reinstall:**
```bash
pip install --upgrade devloop
```

**Check PATH:**
```bash
which devloop
```

### Python version incompatible

**Check Python version:**
```bash
python --version
```

**DevLoop requires Python 3.11+**. Install a newer version:
```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt-get install python3.11

# Windows
# Download from https://www.python.org/downloads/
```

## Configuration Issues

### Config migration failed

When upgrading DevLoop, run:
```bash
devloop init --merge-templates /path/to/project
```

If that doesn't work, manually update `.devloop/agents.json` based on the error message.

### Invalid configuration

**Validate config:**
```bash
devloop init --check-requirements
```

**Reset to defaults:**
```bash
rm .devloop/agents.json
devloop init .
```

## Git Integration Issues

### Pre-commit hook not working

**Check hook exists:**
```bash
cat .git/hooks/pre-commit
```

**Make hook executable:**
```bash
chmod +x .git/hooks/pre-commit
```

**Reinstall hooks:**
```bash
devloop init . --skip-all-but-hooks
```

### Pre-push hook blocked

**Check CI status:**
```bash
gh run list --limit 10
gh run view <run-id> --log-failed
```

**Force push (not recommended):**
```bash
git push origin main --force-with-lease
```

## Event Logging

### No events recorded

**Check event database:**
```bash
devloop audit query --limit 5
```

**Check if enabled in config:**
```bash
grep -A5 '"logging"' .devloop/agents.json
```

**Enable event logging:**
Update `.devloop/agents.json`:
```json
{
  "global": {
    "logging": {
      "level": "info"
    }
  }
}
```

## Marketplace Issues

### Cannot install agent

**Check marketplace status:**
```bash
devloop marketplace status
```

**Start marketplace server:**
```bash
devloop marketplace server start --port 8000
```

**Check credentials:**
```bash
devloop status --show-token-info
```

### Agent publishing failed

**Check agent validity:**
```bash
devloop agent check ./my-agent
```

**Enable verbose output:**
```bash
devloop agent publish ./my-agent --verbose
```

## Help & Support

- **Documentation**: [./docs/](./docs/)
- **Issues**: [GitHub Issues](https://github.com/wioota/devloop/issues)
- **Discussions**: [GitHub Discussions](https://github.com/wioota/devloop/discussions)

When reporting issues, include:
1. DevLoop version: `devloop --version`
2. Python version: `python --version`
3. Last 50 lines of `.devloop/devloop.log`
4. Your `.devloop/agents.json` (sanitized)
5. Steps to reproduce
