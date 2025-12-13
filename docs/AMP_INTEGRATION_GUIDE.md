# Amp Integration Guide

Guide for running DevLoop with optional Amp integration, graceful degradation when Amp is unavailable, and standalone operation.

## Overview

DevLoop runs in three modes:

1. **Full Integration**: With Amp workspace and thread context
2. **Standalone**: Without Amp available (default fallback)
3. **Degraded**: Partial integration when Amp is partially unavailable

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Integration Modes](#integration-modes)
3. [Standalone Operation](#standalone-operation)
4. [Graceful Degradation](#graceful-degradation)
5. [Error Handling](#error-handling)
6. [Testing Integration](#testing-integration)
7. [Troubleshooting](#troubleshooting)
8. [Configuration](#configuration)

---

## Quick Start

### Standalone Installation (No Amp)

```bash
# Install DevLoop normally
pip install devloop

# Initialize project
devloop init /path/to/project

# Works completely independently
devloop watch .
```

### With Amp Integration

```bash
# Inside Amp workspace
devloop init .

# Automatically detects Amp environment
# Thread context captured automatically
# Slash commands available: /agent-summary, /agent-status

devloop watch .
```

---

## Integration Modes

### Mode 1: Full Amp Integration

**When:**
- Running inside Amp workspace
- AMP_THREAD_ID environment variable set
- DevLoop initialized with Amp support

**Features:**
- Thread context captured automatically
- Findings posted to Amp chat
- Slash commands work: `/agent-summary`
- Cross-thread pattern detection
- Integration with Amp task system

**Environment:**
```bash
AMP_THREAD_ID=T-abc123def456...
AMP_THREAD_URL=https://ampcode.com/threads/T-abc123def456...
devloop watch .
```

### Mode 2: Standalone Operation

**When:**
- Running outside Amp workspace
- No AMP_THREAD_ID set
- DevLoop not initialized with Amp support

**Features:**
- All core features work
- Local findings only
- Standard CLI output
- No cross-thread detection
- Works on any system

**Command:**
```bash
devloop watch .
```

### Mode 3: Degraded Integration

**When:**
- Amp workspace detected but unavailable
- Partial Amp dependencies missing
- Network issues with Amp

**Features:**
- Core features work perfectly
- Some Amp features disabled
- Clear warnings about what's unavailable
- Automatic fallback to standalone mode
- Can retry when Amp becomes available

**Example:**
```
⚠️  Amp integration degraded:
  - Amp workspace detected but unavailable
  - Thread context capture disabled
  - Slash commands disabled
  - Continuing in standalone mode...
```

---

## Standalone Operation

### Installation

```bash
# Standard pip installation
pip install devloop

# No additional Amp dependencies required
```

### Configuration

**`.devloop/agents.json`**

```json
{
  "global": {
    "mode": "report-only",
    "amp_integration": {
      "enabled": false
    }
  }
}
```

### Workflow

All features work without Amp:

```bash
# Initialize project
devloop init /path/to/project

# Watch for changes
devloop watch .

# View findings
devloop status
devloop summary

# Query events
devloop audit query --limit 50

# Create custom agents
devloop custom-create my-agent pattern_matcher
```

### Output Without Amp

```
DevLoop - Development Workflow Automation
═════════════════════════════════════════

Watching: /home/user/my-project
Agents: linter, formatter, test-runner, type-checker
Status: ✓ Ready

[2025-12-13 18:15:23] files:modified → 3 files changed
[2025-12-13 18:15:24] linter:start
[2025-12-13 18:15:25] linter:end [8 issues, 245ms]
[2025-12-13 18:15:25] formatter:start
[2025-12-13 18:15:26] formatter:end [0 issues, 312ms]
```

### Findings Export

Without Amp, export findings to files:

```bash
# Export as JSON
devloop summary --format json --output findings.json

# Export as HTML report
devloop summary --format html --output report.html

# Export as CSV for processing
devloop audit query --format csv --output events.csv
```

---

## Graceful Degradation

### Detection and Logging

When Amp integration is unavailable, DevLoop:

1. **Detects** Amp environment
2. **Attempts** connection/initialization
3. **Logs** what works and what doesn't
4. **Falls back** to standalone mode
5. **Continues** with all core features
6. **Notifies** user of degraded features

### Configuration for Graceful Degradation

```json
{
  "global": {
    "amp_integration": {
      "enabled": true,
      "required": false,
      "gracefulDegradation": {
        "enabled": true,
        "retryIntervalSeconds": 60,
        "maxRetries": 5
      }
    }
  }
}
```

**Properties:**
- `enabled`: Try to integrate with Amp
- `required`: Fail if Amp unavailable (recommended: false)
- `gracefulDegradation.enabled`: Allow fallback to standalone
- `gracefulDegradation.retryIntervalSeconds`: How often to retry Amp connection
- `gracefulDegradation.maxRetries`: Max retry attempts

### Automatic Retry

When Amp becomes unavailable, DevLoop automatically retries:

```
[2025-12-13 18:15:23] ⚠️  Amp integration lost
[2025-12-13 18:15:23] Falling back to standalone mode
[2025-12-13 18:15:24] All core features operational

[Retry scheduled in 60 seconds...]

[2025-12-13 18:16:24] Attempting to reconnect to Amp...
[2025-12-13 18:16:25] ✓ Amp integration restored
[2025-12-13 18:16:25] Re-enabling Amp features
```

---

## Error Handling

### Graceful Errors

**Scenario 1: Amp Unavailable**

```
⚠️  Could not initialize Amp integration:
  Error: Amp workspace not found
  
Continuing without Amp support...
All features work locally.
```

**Scenario 2: Missing Amp Credentials**

```
⚠️  Amp credentials not found:
  - Set AMP_THREAD_ID to enable thread context
  - Set AMP_THREAD_URL for accurate linking
  
Running in standalone mode without thread tracking.
```

**Scenario 3: Network Issues**

```
⚠️  Amp network error:
  Error: Connection timeout (5s)
  
Fallback to standalone mode.
Retrying connection in 60 seconds...
```

### Error Levels

**Info:**
- "Amp workspace detected"
- "Amp features available"
- "Successfully posted finding to Amp"

**Warning:**
- "Amp workspace not accessible"
- "Amp credentials missing"
- "Amp connection slow"

**Error:**
- "Amp initialization failed (will retry)"
- "Amp sync lost (falling back to standalone)"

**None logged for expected states:**
- Running standalone (normal)
- Amp not available (expected)

### User-Friendly Messages

Don't expose internal errors:

```
❌ BAD:
Exception: JSONDecodeError in AmpIntegration.post_finding()

✅ GOOD:
⚠️  Could not post finding to Amp thread
  Continuing offline...
```

---

## Testing Integration

### Test Standalone Mode

```bash
# Disable all Amp features
devloop init . --no-amp

# Verify standalone operation
devloop watch . --verbose

# Should see:
# ✓ Running in standalone mode
# ✓ Core agents initialized
# ✓ File watching active
```

### Test Graceful Degradation

```bash
# 1. Start DevLoop with Amp enabled
devloop watch .

# 2. Stop Amp service (simulate failure)
# 3. Watch logs for graceful fallback
# 4. Verify agents continue running
# 5. Restart Amp service
# 6. Watch for reconnection
```

### Test Standalone Performance

Compare performance with/without Amp:

```bash
# Without Amp
devloop init . --no-amp --performance-preset balanced
time devloop watch . --duration 60

# With Amp
devloop init . --amp-integration
time devloop watch . --duration 60

# Should see minimal overhead
```

### Automated Testing

**`tests/integration/test_amp_degradation.py`**

```python
def test_graceful_degradation_when_amp_unavailable():
    """Test DevLoop continues when Amp is unavailable."""
    # 1. Initialize with Amp enabled
    devloop = DevLoop(amp_integration=True)
    
    # 2. Disable Amp
    with mock.patch('devloop.amp.available', False):
        # 3. Verify agents still run
        assert devloop.watch() is not None
        
    # 4. Verify no exceptions raised
    # 5. Verify fallback message logged

def test_agent_functionality_without_amp():
    """Test agents work completely without Amp."""
    devloop = DevLoop(amp_integration=False)
    
    # Create test file
    test_file = Path("test.py")
    test_file.write_text("x=1")
    
    # Run agents
    results = devloop.process_file(test_file)
    
    # Should have findings even without Amp
    assert len(results) > 0

def test_automatic_reconnection():
    """Test Amp reconnection after becoming available."""
    devloop = DevLoop(amp_integration=True)
    
    # 1. Start with Amp unavailable
    with mock.patch('devloop.amp.available', False):
        devloop.start()
        assert not devloop.amp_connected
    
    # 2. Make Amp available
    with mock.patch('devloop.amp.available', True):
        # Should reconnect
        time.sleep(61)  # Wait for retry
        assert devloop.amp_connected
```

---

## Configuration

### Environment Variables

```bash
# Enable/disable Amp integration
DEVLOOP_AMP_ENABLED=true

# Set thread ID (enables thread context)
AMP_THREAD_ID=T-abc123def456...
AMP_THREAD_URL=https://ampcode.com/threads/T-abc123def456...

# Amp connection settings
DEVLOOP_AMP_TIMEOUT=5
DEVLOOP_AMP_RETRY_INTERVAL=60

# Force standalone mode
DEVLOOP_FORCE_STANDALONE=true
```

### Configuration File

**`.devloop/agents.json`**

```json
{
  "global": {
    "amp_integration": {
      "enabled": true,
      "required": false,
      "timeout": 5,
      "gracefulDegradation": {
        "enabled": true,
        "retryIntervalSeconds": 60,
        "maxRetries": 5,
        "logLevel": "warn"
      },
      "features": {
        "thread_context": true,
        "slash_commands": true,
        "findings_sync": true,
        "cross_thread_detection": true
      }
    }
  }
}
```

### Per-Feature Configuration

Enable/disable specific Amp features:

```json
{
  "global": {
    "amp_integration": {
      "features": {
        "thread_context": true,       // Capture thread ID
        "slash_commands": true,       // Enable /agent-summary
        "findings_sync": true,        // Post to chat
        "cross_thread_detection": true // Pattern detection
      }
    }
  }
}
```

---

## Amp Unavailability Scenarios

### Scenario 1: Amp Not Installed

**System:** Standalone system without Amp

```bash
devloop init /path/to/project
devloop watch .

# Works fine, no Amp features available
```

**Log output:**
```
✓ DevLoop initialized
✓ Core features active
ℹ️ Amp integration not available (not in Amp workspace)
✓ Ready to watch for changes
```

### Scenario 2: Amp Server Down

**System:** Amp workspace but server unavailable

```
⚠️  Amp server unavailable:
  Connection timeout
  
Status: Degraded
  - Local features: ✓ All working
  - Amp features: ✗ Temporarily disabled
  
Retry: Attempting connection in 60 seconds...
```

### Scenario 3: Amp Workspace Lost

**System:** Originally in Amp workspace, lost connection

```
⚠️  Amp workspace disconnected:
  Lost connection to workspace
  
Status: Standalone
  - All core features: ✓ Working
  - Thread context: ✗ Not available
  
Will retry connection if workspace becomes available.
```

### Scenario 4: Credentials Expired

**System:** Amp credentials expired

```
⚠️  Amp credentials expired:
  Token validation failed
  
Status: Standalone
  - Local features: ✓ Working
  - Amp posting: ✗ Disabled (auth failed)
  
To re-enable: Update credentials and restart DevLoop
```

---

## Troubleshooting

### Issue: Amp Features Not Available

**Check 1: Are you in an Amp workspace?**
```bash
# Should print workspace info
amp workspace info

# If not, you're running standalone (normal)
```

**Check 2: Is AMP_THREAD_ID set?**
```bash
echo $AMP_THREAD_ID

# If empty, thread context won't work
export AMP_THREAD_ID=T-xxxxx
```

**Check 3: Is DevLoop seeing Amp?**
```bash
devloop status --verbose | grep -i amp

# Should show Amp integration status
```

### Issue: Amp Integration Slow

**Symptoms:**
- `devloop watch` takes long to start
- Delays before agent runs

**Solutions:**
1. Increase timeout: `DEVLOOP_AMP_TIMEOUT=10`
2. Disable non-critical features:
   ```json
   {
     "amp_integration": {
       "features": {
         "cross_thread_detection": false
       }
     }
   }
   ```
3. Switch to standalone: `DEVLOOP_FORCE_STANDALONE=true`

### Issue: Findings Not Appearing in Amp

**Check 1: Is integration enabled?**
```bash
devloop status | grep "Amp integration"
```

**Check 2: Are you in a thread?**
```bash
echo $AMP_THREAD_ID
# Should not be empty
```

**Check 3: Do you have permission?**
```bash
# Check if findings are being logged locally
devloop summary --limit 5
```

If local findings exist but not in Amp:
- Check network connectivity
- Check Amp credentials
- Check logs: `tail -f .devloop/devloop.log`

### Issue: "Amp Not Found" Error

**Check 1: Is Amp available?**
```bash
which amp
# If not found, Amp not installed

# This is fine - DevLoop works without it
```

**Check 2: Are you in Amp workspace?**
```bash
amp workspace list
# Should list your workspace

# If empty, you're not in Amp
```

### Issue: DevLoop Hangs on Startup

**Symptoms:**
- Sits for 30+ seconds before responding
- Freezes during initialization

**Solution 1: Disable Amp timeout wait**
```bash
DEVLOOP_AMP_ENABLED=false devloop watch .
```

**Solution 2: Reduce Amp timeout**
```bash
DEVLOOP_AMP_TIMEOUT=2 devloop watch .
```

**Solution 3: Force standalone**
```bash
DEVLOOP_FORCE_STANDALONE=true devloop watch .
```

---

## Best Practices

1. **Always test standalone first**: Verify core functionality works without Amp
2. **Use graceful degradation**: Never require Amp (`required: false`)
3. **Set reasonable timeouts**: `5-10 seconds` for Amp connections
4. **Log clearly**: Users should understand what's available
5. **Fail open**: Continue working if Amp unavailable
6. **Retry gracefully**: Reconnect automatically when Amp comes back
7. **Don't break on errors**: Never interrupt user workflow for Amp issues
8. **Test degradation**: Ensure graceful fallback works
9. **Document expectations**: Tell users what works with/without Amp
10. **Monitor in production**: Alert on sustained Amp unavailability

---

## Decision Tree

```
Is Amp available?
├─ YES
│  ├─ Is AMP_THREAD_ID set?
│  │  ├─ YES → Full integration with thread context
│  │  └─ NO → Integration without thread context
│  └─ Is Amp reachable?
│     ├─ YES → Full Amp integration
│     └─ NO → Graceful degradation to standalone
└─ NO → Standalone operation (all features work)
```

---

## Migration Guide

### From Amp-Only to Standalone-Compatible

1. **Audit code** for Amp dependencies
2. **Make Amp optional** in initialization
3. **Add fallback paths** for all Amp features
4. **Test without Amp** thoroughly
5. **Document** what works without Amp
6. **Update docs** with standalone instructions

### From Standalone to Amp-Integrated

1. **Add Amp detection** in initialization
2. **Implement graceful degradation**
3. **Add thread context capture** (optional)
4. **Enable slash commands** (optional)
5. **Test integration** with Amp
6. **Test degradation** with Amp unavailable

---

## See Also

- [Installation Guide](./getting-started.md)
- [Configuration Guide](./configuration.md)
- [AMP_ONBOARDING.md](../AMP_ONBOARDING.md)
