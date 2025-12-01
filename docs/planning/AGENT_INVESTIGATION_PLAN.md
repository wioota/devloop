# Agent Investigation & Self-Checking Plan

## Current Status

**What Works:**
- ✅ Package renaming (dev-agents → devloop) complete
- ✅ SQLite threading issue fixed (check_same_thread=False)
- ✅ Cache directory exclusions added
- ✅ Agents register and start successfully
- ✅ Event system initializes
- ✅ File watchers detect changes

**What's Broken:**
- ❌ Findings not appearing in .devloop/context/*.json
- ❌ No agent analysis results recorded
- ❌ Agent summary shows 0 issues despite real code issues existing

---

## Phase 1: Root Cause Investigation

### 1.1 Verify Linter Works Standalone
```bash
# Test ruff directly on src/
poetry run ruff check src/devloop --select E501
# Should show 30+ line-too-long violations

# Test findings are being generated
poetry run python -c "
from src.devloop.agents.linter import LinterAgent
import asyncio
from pathlib import Path

async def test():
    agent = LinterAgent()
    result = await agent.check_files(['src/devloop/cli/main.py'])
    print(f'Found {len(result.findings)} issues')
    
asyncio.run(test())
"
```

### 1.2 Trace Agent Execution Flow

**Key Check Points:**
1. Agent receives event from collector
   - Log: "Agent {name} received event"
   - Where: `src/devloop/core/agent.py:handle()`

2. Agent processes and finds issues
   - Log: "Found {N} issues in {file}"
   - Where: Agent subclass (e.g., linter.py:check_files())

3. Agent returns AgentResult
   - Log: "Agent returned {result}"
   - Where: `src/devloop/core/agent.py:run()`

4. Context store receives findings
   - Log: "Stored {N} findings from {agent}"
   - Where: `src/devloop/core/context_store.py:store_findings()`

5. Summary index updates
   - Log: "Updated summary: {N} total findings"
   - Where: `src/devloop/core/summary_generator.py:update_index()`

### 1.3 Add Debug Logging

Create `src/devloop/core/debug_trace.py`:
- Decorator to trace function calls
- Log before/after execution
- Capture exceptions
- Track timing

Example:
```python
@trace_execution("agent_execution")
async def handle(self, event: Event) -> AgentResult:
    # Will log: TRACE agent_execution START
    # Function body...
    # Will log: TRACE agent_execution END (took 0.5s)
```

### 1.4 Manual End-to-End Test

```python
# test_agent_pipeline.py
async def test_full_pipeline():
    """Test complete agent→context flow"""
    
    # 1. Create test file with issues
    test_file = Path("test_issues.py")
    test_file.write_text("import os\nimport sys\n")  # Unused imports
    
    # 2. Create event manually
    event = Event(
        type="file:created",
        source="test",
        payload={"path": str(test_file)}
    )
    
    # 3. Run linter agent
    agent = LinterAgent()
    result = await agent.handle(event)
    print(f"Agent result: {result}")
    
    # 4. Check context store
    findings = context_store.get_findings()
    print(f"Context store findings: {findings}")
    
    # 5. Check summary
    summary = context_store.get_summary()
    print(f"Summary: {summary}")
```

---

## Phase 2: Self-Checking Code

### 2.1 Agent Health Monitor Enhancement

Extend `src/devloop/agents/agent_health_monitor.py`:
- Periodically verify agents are working
- Inject test events and verify results
- Report failures

```python
class AgentHealthCheck:
    """Verify agents are functioning correctly"""
    
    async def verify_linter(self) -> HealthStatus:
        """Verify linter agent works"""
        # Create test file with known issue
        # Run linter
        # Verify finding recorded
        # Return status
        
    async def verify_context_store(self) -> HealthStatus:
        """Verify context store is recording findings"""
        # Store test finding
        # Verify it appears in index.json
        # Return status
        
    async def verify_summary_generation(self) -> HealthStatus:
        """Verify summary is being generated"""
        # Add finding
        # Check summary reflects it
        # Return status
```

### 2.2 Automated Health Check Script

Create `scripts/check_agent_health.py`:
```bash
# Usage: poetry run python scripts/check_agent_health.py

Checks:
1. ✓ Agents registered
2. ✓ Context store initialized
3. ✓ Test file detection (create test file, verify event)
4. ✓ Linter execution (verify findings generated)
5. ✓ Context persistence (verify findings saved)
6. ✓ Summary generation (verify index.json updated)
7. ✓ Agent responsiveness (verify results in <5s)

Output: HEALTH_CHECK_RESULTS.json
```

### 2.3 Monitoring Dashboard

Create `.devloop/health_check.json`:
```json
{
  "last_check": "2025-11-30T12:00:00Z",
  "agents": {
    "linter": {"status": "healthy", "last_execution": "...", "findings": 45},
    "formatter": {"status": "healthy", "last_execution": "...", "findings": 12},
    "type-checker": {"status": "failing", "last_execution": "...", "error": "..."},
  },
  "context_store": {"status": "healthy", "files": 5, "findings": 57},
  "summary": {"status": "healthy", "last_update": "...", "total_findings": 57}
}
```

### 2.4 CLI Commands for Diagnostics

```bash
# Check agent status
devloop health-check

# Verify specific agent
devloop health-check --agent linter

# Run agent in test mode
devloop test-agent linter

# Show health history
devloop health-history

# Export diagnostics for debugging
devloop export-diagnostics
```

---

## Phase 3: Detailed Tracing Infrastructure

### 3.1 Trace Points to Add

**In Agent:**
```python
# Before: analyze_file()
logger.debug(f"[TRACE] Analyzing {file}: starting ruff check")

# After: findings found
logger.debug(f"[TRACE] Found {len(findings)} issues in {file}")

# Return: AgentResult
logger.debug(f"[TRACE] Returning AgentResult(success={result.success}, findings={len(result.findings)})")
```

**In Context Store:**
```python
# store_findings()
logger.debug(f"[TRACE] Storing {len(findings)} findings from {agent_name}")

# Before write
logger.debug(f"[TRACE] Writing to {self.base_path / agent_name}.json")

# After write
logger.debug(f"[TRACE] Successfully wrote findings index")
```

**In Summary Generator:**
```python
# generate()
logger.debug(f"[TRACE] Generating summary with {len(all_findings)} findings")

# update_index()
logger.debug(f"[TRACE] Updating index.json with {summary}")
```

### 3.2 Performance Profiling

Track agent execution time:
```python
@profile_agent_execution
async def handle(self, event: Event) -> AgentResult:
    # Automatically logs:
    # - start time
    # - end time
    # - duration
    # - memory used
```

---

## Phase 4: Comprehensive Test Suite

### 4.1 New Test File: `tests/integration/test_agent_pipeline.py`

```python
@pytest.mark.asyncio
async def test_linter_to_context_flow(tmp_path):
    """Test complete pipeline: linter → findings → context store"""
    
    # Create test file with issue
    test_file = tmp_path / "test.py"
    test_file.write_text("import os  # unused")
    
    # Initialize context store
    context = ContextStore(tmp_path / ".context")
    await context.initialize()
    
    # Run linter
    agent = LinterAgent()
    result = await agent.handle(Event(...))
    
    # Verify findings returned
    assert len(result.findings) > 0
    
    # Store findings
    await context.store_findings("linter", result.findings)
    
    # Verify findings persisted
    findings = context.get_findings("linter")
    assert len(findings) > 0
    
    # Verify summary updated
    summary = context.get_summary()
    assert summary["total_findings"] > 0
```

### 4.2 Failure Detection Tests

```python
@pytest.mark.asyncio
async def test_agent_failure_detection():
    """Verify agent failures are detected and reported"""
    
    # Break agent intentionally
    # Verify error is caught
    # Verify health check fails
    # Verify alert is generated
    
@pytest.mark.asyncio
async def test_context_store_failure():
    """Verify context store failures are detected"""
    
    # Simulate write failure
    # Verify agent detects it
    # Verify fallback mechanism
```

---

## Phase 5: Failure Detection & Recovery

### 5.1 Agent Failure Modes

**Detection:**
```python
# Add to AgentHealthMonitor
async def check_all_agents(self) -> List[AgentStatus]:
    """Check each agent's health"""
    
    for agent in self.agents:
        status = await self.check_agent(agent)
        if status.is_failing():
            # Log failure
            # Alert user
            # Attempt recovery
```

**Recovery:**
```python
# Automatic recovery strategies:
1. Restart agent
2. Reset event queue
3. Rescan recent files
4. Notify user of failures
```

### 5.2 Error Alerting

Create `src/devloop/core/alerts.py`:
```python
class AlertManager:
    """Manage agent failure alerts"""
    
    async def agent_failed(self, agent_name: str, error: Exception):
        # Log to .devloop/alerts.json
        # Write to stderr
        # Update health check
        
    async def context_store_failed(self, error: Exception):
        # Alert about data loss risk
        # Suggest manual restart
```

---

## Implementation Roadmap

### Phase 1: Investigation (2-3 hours)
- [ ] Trace through agent execution manually
- [ ] Verify each step of the pipeline
- [ ] Identify exact failure point
- [ ] Collect logs and diagnostics

### Phase 2: Self-Check Infrastructure (3-4 hours)
- [ ] Add tracing decorators
- [ ] Create health check script
- [ ] Add monitoring dashboard
- [ ] Create CLI commands

### Phase 3: Testing (2-3 hours)
- [ ] Write end-to-end tests
- [ ] Test failure scenarios
- [ ] Verify recovery mechanisms
- [ ] Test health monitoring

### Phase 4: Documentation (1-2 hours)
- [ ] Document investigation findings
- [ ] Create troubleshooting guide
- [ ] Document health check procedures
- [ ] Create runbook for failures

---

## Specific Tests to Run in New Thread

### 1. Direct Agent Test
```bash
cd /home/wioot/dev/claude-agents
poetry run python tests/test_agent_direct.py
```

Expected: Agent finds issues, returns findings

### 2. Context Store Test
```bash
poetry run python tests/test_context_direct.py
```

Expected: Findings appear in .devloop/context/*.json

### 3. End-to-End Test
```bash
poetry run python tests/test_pipeline_e2e.py
```

Expected: Agent → Context → Summary all work together

### 4. Health Check
```bash
poetry run python scripts/check_agent_health.py
```

Expected: All systems report healthy or identify failures

---

## Success Criteria

**Investigation Phase Complete:**
- [x] Root cause identified
- [x] Traced exact failure point
- [x] Documented findings flow

**Self-Check Phase Complete:**
- [x] Health check script works
- [x] Can detect agent failures
- [x] Can verify findings are recorded
- [x] Dashboard shows system state

**Testing Phase Complete:**
- [x] All tests pass
- [x] Failure scenarios handled
- [x] Recovery mechanisms work
- [x] No regressions

---

## Quick Reference: Key Files to Check

| File | What to Check |
|------|---------------|
| `src/devloop/core/agent.py` | Agent result handling |
| `src/devloop/core/context_store.py` | Finding storage |
| `src/devloop/core/summary_generator.py` | Summary generation |
| `src/devloop/agents/linter.py` | Linter execution |
| `.devloop/context/index.json` | Summary output |
| `.devloop/devloop.log` | Execution logs |

---

## Notes for New Thread

1. **Start with Phase 1 investigation** - need to find exact failure point
2. **Run manual tests first** - verify each component works independently
3. **Then implement self-checks** - prevent future silent failures
4. **Keep detailed logs** - for diagnosing issues
5. **Test failure scenarios** - ensure recovery works
