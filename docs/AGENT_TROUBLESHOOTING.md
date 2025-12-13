# Agent Troubleshooting Guide

Common issues and solutions for DevLoop agent development and usage.

## Table of Contents

1. [Agent Not Running](#agent-not-running)
2. [Agent Crashing](#agent-crashing)
3. [Performance Issues](#performance-issues)
4. [Event Handling Problems](#event-handling-problems)
5. [Testing Issues](#testing-issues)
6. [Configuration Problems](#configuration-problems)
7. [Installation Problems](#installation-problems)
8. [Advanced Debugging](#advanced-debugging)

## Agent Not Running

### Symptom
Agent is installed but never seems to execute.

### Diagnostic Steps

1. **Check if agent is enabled:**
```bash
devloop status
# or check .devloop/agents.json
```

2. **Verify triggers are correct:**
```bash
devloop info my-agent
# Shows configured triggers
```

3. **Check if events are being emitted:**
```bash
devloop debug events --filter file:save
# Shows all file:save events
```

4. **View agent logs:**
```bash
devloop logs my-agent
# or
devloop logs my-agent --full
```

### Solutions

**Agent disabled:**
```json
{
  "agents": {
    "my-agent": {
      "enabled": true    // Make sure this is true
    }
  }
}
```

**Wrong trigger pattern:**
```json
{
  "agents": {
    "my-agent": {
      "triggers": ["file:save"]     // e.g., not "file:*" if not intended
    }
  }
}
```

**Events not matching:**
```bash
# Test if events match pattern
devloop debug events --filter "*" --verbose
# Look for events matching your trigger pattern
```

**Agent not started:**
```bash
# Restart the agent daemon
devloop restart
```

---

## Agent Crashing

### Symptom
Agent starts but stops after an error, logs show exceptions.

### Diagnostic Steps

1. **Check crash logs:**
```bash
devloop logs my-agent --full --since "1 hour ago"
```

2. **Enable debug logging:**
```bash
# In .devloop/agents.json
{
  "global": {
    "logging": {
      "level": "debug"
    }
  }
}
```

3. **Check recent changes:**
```bash
git diff HEAD~5 src/my_agent/
```

### Common Causes and Solutions

**Missing exception handling:**
```python
# ❌ Bad - raises exceptions
async def handle(self, event: Event) -> AgentResult:
    file_path = event.payload["path"]  # KeyError if missing!
    return AgentResult(...)

# ✅ Good - handles exceptions
async def handle(self, event: Event) -> AgentResult:
    file_path = event.payload.get("path")
    if not file_path:
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0,
            message="No file path",
        )
    return AgentResult(...)
```

**Async/await mistakes:**
```python
# ❌ Bad - blocking the event loop
async def handle(self, event: Event) -> AgentResult:
    import time
    time.sleep(5)  # BLOCKS EVENT LOOP!
    return AgentResult(...)

# ✅ Good - async sleep
async def handle(self, event: Event) -> AgentResult:
    import asyncio
    await asyncio.sleep(5)  # Doesn't block
    return AgentResult(...)
```

**Not returning AgentResult:**
```python
# ❌ Bad - raises TypeError
async def handle(self, event: Event) -> AgentResult:
    return "Success"  # Wrong type!

# ✅ Good - always return AgentResult
async def handle(self, event: Event) -> AgentResult:
    return AgentResult(
        agent_name=self.name,
        success=True,
        duration=0,
        message="Success",
    )
```

**Invalid AgentResult:**
```python
# ❌ Bad - invalid AgentResult
return AgentResult(
    agent_name="",  # Empty!
    success=True,
    duration=-1,  # Negative!
)

# ✅ Good - valid AgentResult
return AgentResult(
    agent_name=self.name,
    success=True,
    duration=0.5,
)
```

**Unhandled exceptions in callbacks:**
```python
# ❌ Bad - exception in callback
async def handle(self, event: Event) -> AgentResult:
    results = []
    for item in event.payload.get("items", []):
        result = await process(item)  # Can raise!
    return AgentResult(...)

# ✅ Good - wrap in try/except
async def handle(self, event: Event) -> AgentResult:
    results = []
    try:
        for item in event.payload.get("items", []):
            try:
                result = await process(item)
                results.append(result)
            except Exception as e:
                self.logger.warning(f"Skipped item: {e}")
                continue
    except Exception as e:
        self.logger.error(f"Failed to process: {e}", exc_info=True)
        return AgentResult(
            agent_name=self.name,
            success=False,
            duration=0,
            error=str(e),
        )
    
    return AgentResult(
        agent_name=self.name,
        success=True,
        duration=0.1,
        message=f"Processed {len(results)} items",
        data={"results": results},
    )
```

---

## Performance Issues

### Symptom
Agent is slow or blocks other agents/development.

### Diagnostic Steps

1. **Profile agent execution:**
```bash
devloop profile my-agent --samples 100
# Shows execution time distribution
```

2. **Check resource usage:**
```bash
devloop status --resources
# Shows CPU and memory usage
```

3. **Monitor event queue:**
```bash
devloop debug queue --agent my-agent
# Shows pending events
```

### Common Causes and Solutions

**Blocking I/O operations:**
```python
# ❌ Bad - blocking reads
async def handle(self, event: Event) -> AgentResult:
    with open(path) as f:
        content = f.read()  # Can block!
    return AgentResult(...)

# ✅ Good - use pathlib (non-blocking for small files)
async def handle(self, event: Event) -> AgentResult:
    from pathlib import Path
    content = Path(path).read_text()  # Non-blocking for small files
    return AgentResult(...)

# ✅ Better - for large files, use aiofill or similar
async def handle(self, event: Event) -> AgentResult:
    import aiofiles
    async with aiofiles.open(path) as f:
        content = await f.read()
    return AgentResult(...)
```

**Not filtering events early:**
```python
# ❌ Bad - process all events
async def handle(self, event: Event) -> AgentResult:
    # Expensive operation on every event
    return await expensive_check(event)

# ✅ Good - skip early
async def handle(self, event: Event) -> AgentResult:
    file_path = event.payload.get("path", "")
    
    # Skip if not Python file
    if not file_path.endswith('.py'):
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0,
            message="Skipped (not Python)",
        )
    
    # Skip if generated
    if ".generated" in file_path or ".min.py" in file_path:
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0,
            message="Skipped (generated)",
        )
    
    # Now do expensive check
    return await expensive_check(event)
```

**Processing too many files:**
```python
# ❌ Bad - processes all files in directory
async def handle(self, event: Event) -> AgentResult:
    path = Path(event.payload["path"])
    for file in path.parent.glob("**/*.py"):  # All files!
        result = await process(file)
    return AgentResult(...)

# ✅ Good - only process the specific file
async def handle(self, event: Event) -> AgentResult:
    file_path = event.payload.get("path")
    if file_path:
        result = await process(file_path)
    return AgentResult(...)
```

**No timeout on external calls:**
```python
# ❌ Bad - can hang indefinitely
async def handle(self, event: Event) -> AgentResult:
    result = await external_api_call()  # Can hang forever
    return AgentResult(...)

# ✅ Good - add timeout
async def handle(self, event: Event) -> AgentResult:
    try:
        result = await asyncio.wait_for(
            external_api_call(),
            timeout=5.0,
        )
    except asyncio.TimeoutError:
        return AgentResult(
            agent_name=self.name,
            success=False,
            duration=5.0,
            error="API call timeout",
        )
    return AgentResult(...)
```

**Resource limits not set:**
```bash
# Check resource limits
devloop status --limits

# Set resource limits in agents.json
{
  "global": {
    "resourceLimits": {
      "maxCpu": 25,           # Max 25% CPU
      "maxMemory": "500MB"    # Max 500MB memory
    }
  },
  "agents": {
    "my-agent": {
      "resourceLimits": {
        "maxCpu": 10,
        "maxMemory": "100MB"
      }
    }
  }
}
```

---

## Event Handling Problems

### Symptom
Agent receives events but doesn't process them correctly.

### Diagnostic Steps

1. **Debug specific event:**
```bash
devloop debug event --type file:save --show-payload
```

2. **Test event processing:**
```bash
devloop test my-agent --event-type file:save --event-data '{"path":"test.py"}'
```

3. **Check event filter:**
```bash
# Verify event pattern matching
devloop debug pattern --pattern "file:*" --event "file:save"
# Should show: MATCH
```

### Common Causes and Solutions

**Event payload missing expected keys:**
```python
# ❌ Bad - assumes keys exist
async def handle(self, event: Event) -> AgentResult:
    path = event.payload["path"]  # KeyError!
    return AgentResult(...)

# ✅ Good - safe extraction
async def handle(self, event: Event) -> AgentResult:
    path = event.payload.get("path")
    if not path:
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0,
            message="Missing path",
        )
    return AgentResult(...)
```

**Wrong trigger pattern:**
```python
# Check trigger patterns
def __init__(self, ...):
    # ❌ Bad - won't match "file:save"
    self.triggers = ["file"]  # Too broad!
    
    # ✅ Good - specific patterns
    self.triggers = ["file:save", "file:create"]
```

**Event timing issues:**
```python
# ❌ Bad - processes old cached data
last_result = None

async def handle(self, event: Event) -> AgentResult:
    global last_result
    if last_result:
        return last_result  # Stale data!
    last_result = await process(event)
    return last_result

# ✅ Good - always process fresh
async def handle(self, event: Event) -> AgentResult:
    result = await process(event)
    return result
```

---

## Testing Issues

### Symptom
Tests pass locally but fail in CI, or tests don't work correctly.

### Diagnostic Steps

1. **Run tests with verbose output:**
```bash
pytest tests/ -v --tb=short
```

2. **Check test dependencies:**
```bash
pip list | grep -E "pytest|asyncio"
```

3. **Run single test in isolation:**
```bash
pytest tests/test_agent.py::test_handle_event -s
```

### Common Causes and Solutions

**Missing pytest-asyncio marker:**
```python
# ❌ Bad - asyncio not marked
def test_agent():
    result = await agent.handle(event)  # SyntaxError!

# ✅ Good - mark as asyncio
@pytest.mark.asyncio
async def test_agent():
    result = await agent.handle(event)
    assert result.success
```

**Not using fixtures properly:**
```python
# ❌ Bad - hardcoded paths
def test_agent():
    event = Event(..., payload={"path": "/tmp/test.py"})
    # Fails if /tmp/test.py doesn't exist!

# ✅ Good - use tmp_path fixture
def test_agent(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')")
    event = Event(..., payload={"path": str(test_file)})
    # Always works!
```

**Mock not properly configured:**
```python
# ❌ Bad - mock doesn't simulate real behavior
@pytest.mark.asyncio
async def test_agent(mocker):
    mock_bus = mocker.MagicMock()
    agent = MyAgent(..., event_bus=mock_bus)
    # Mock doesn't implement async methods!

# ✅ Good - use AsyncMock
@pytest.mark.asyncio
async def test_agent(mocker):
    mock_bus = mocker.AsyncMock()
    agent = MyAgent(..., event_bus=mock_bus)
    # Now async methods work!
```

**Event loop issues:**
```python
# ❌ Bad - creates nested event loops
@pytest.mark.asyncio
async def test_agent():
    # This test is already in an event loop!
    loop = asyncio.new_event_loop()  # ERROR!

# ✅ Good - use the existing loop
@pytest.mark.asyncio
async def test_agent():
    result = await agent.handle(event)
    assert result.success
```

**CI environment differences:**
```python
# ❌ Bad - assumes Unix paths
path = "/home/user/project/file.py"

# ✅ Good - use Path for portability
from pathlib import Path
path = Path(__file__).parent / "fixtures" / "file.py"
```

---

## Configuration Problems

### Symptom
Agent configuration not being applied or causing errors.

### Diagnostic Steps

1. **Validate configuration:**
```bash
devloop validate config
# Shows any config errors
```

2. **Check agent configuration:**
```bash
cat .devloop/agents.json | jq '.agents.my-agent'
```

3. **Reload configuration:**
```bash
devloop reload config
```

### Common Causes and Solutions

**Invalid JSON:**
```json
// ❌ Bad - JSON errors
{
  "agents": {
    "my-agent": {
      "enabled": true,  // Extra comma!
    }
  }
}

// ✅ Good - valid JSON
{
  "agents": {
    "my-agent": {
      "enabled": true
    }
  }
}
```

**Missing required fields:**
```json
// ❌ Bad - missing "triggers"
{
  "agents": {
    "my-agent": {
      "enabled": true
      // No triggers!
    }
  }
}

// ✅ Good - has required fields
{
  "agents": {
    "my-agent": {
      "enabled": true,
      "triggers": ["file:save"]
    }
  }
}
```

**Environment variable not substituted:**
```json
// ❌ Bad - variable not substituted
{
  "agents": {
    "my-agent": {
      "config": {
        "token": "${API_TOKEN}"  // Not replaced!
      }
    }
  }
}

// ✅ Good - set environment variable first
// export API_TOKEN="secret-token"
{
  "agents": {
    "my-agent": {
      "config": {
        "token": "${API_TOKEN}"  // Now replaced
      }
    }
  }
}
```

---

## Installation Problems

### Symptom
Can't install agent or installation fails.

### Diagnostic Steps

1. **Check installation logs:**
```bash
devloop logs --component installer
```

2. **Verify compatibility:**
```bash
devloop check compatibility my-agent
# Shows Python version, DevLoop version, etc.
```

3. **Test installation in isolation:**
```bash
python -m venv test_env
source test_env/bin/activate
pip install my-agent
```

### Common Causes and Solutions

**Python version mismatch:**
```bash
# Check what Python version is required
devloop info my-agent | grep "Python"

# Check your Python version
python --version

# Use the right Python version
python3.11 -m pip install my-agent
```

**DevLoop version incompatible:**
```bash
# Check your DevLoop version
devloop --version

# Check agent's requirements
devloop info my-agent | grep "DevLoop"

# Upgrade if needed
pip install --upgrade devloop
```

**Dependencies not installed:**
```bash
# Check agent dependencies
pip show my-agent | grep Requires

# Install all dependencies
pip install my-agent[all]
```

---

## Advanced Debugging

### Enable Trace Logging

```bash
# Set environment variable
export DEVLOOP_LOG_LEVEL=debug

# Run agent with verbose logging
devloop run my-agent --verbose

# View detailed logs
devloop logs my-agent --full --grep "ERROR\|WARN"
```

### Dump Agent State

```bash
# Dump current state
devloop debug state --agent my-agent

# Output includes:
# - Current configuration
# - Event subscriptions
# - Performance metrics
# - Resource usage
# - Recent log entries
```

### Test Agent Directly

```bash
# Create test event
cat > test_event.json << 'EOF'
{
  "type": "file:save",
  "source": "fs",
  "payload": {"path": "test.py"}
}
EOF

# Test agent with event
devloop test my-agent --event-file test_event.json

# Output shows:
# - Execution time
# - Result
# - Any errors
```

### Monitor in Real-Time

```bash
# Watch agent execution
devloop monitor my-agent --live

# Shows:
# - Events received
# - Processing time
# - Results
# - Errors
```

---

## Getting Help

If you're stuck:

1. **Check the documentation:**
   - [Agent Development Guide](./AGENT_DEVELOPMENT.md)
   - [Agent API Reference](./AGENT_API_REFERENCE.md)

2. **Search existing issues:**
   ```bash
   devloop search-issues "my error message"
   ```

3. **Create a detailed bug report:**
   ```bash
   devloop report bug \
     --agent my-agent \
     --description "..." \
     --attach-logs \
     --attach-config
   ```

4. **Get community help:**
   - [Community Forum](https://forum.devloop.dev)
   - [Discord](https://discord.gg/devloop)
   - [GitHub Issues](https://github.com/wioota/devloop/issues)

---

## Quick Reference

| Problem | Solution |
|---------|----------|
| Agent not running | Check if enabled, verify triggers, check logs |
| Agent crashing | Add exception handling, check async/await |
| Slow agent | Add early filtering, check for blocking I/O |
| Events not processed | Check trigger pattern, verify event payload |
| Tests failing | Use pytest.mark.asyncio, use fixtures, mock async |
| Config not applied | Validate JSON, check env variables, reload |
| Installation fails | Check Python/DevLoop version, install deps |
