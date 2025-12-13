# Debugging Guide

Comprehensive guide for debugging DevLoop issues, extracting diagnostic data, and troubleshooting problems.

## Overview

This guide covers:

- Debugging tools and commands
- State dump and inspection
- Trace mode for detailed execution flow
- Log analysis and extraction
- Common issues and solutions
- Performance profiling
- Remote debugging

---

## Table of Contents

1. [Quick Debugging](#quick-debugging)
2. [Debug Command](#debug-command)
3. [State Dump](#state-dump)
4. [Trace Mode](#trace-mode)
5. [Log Analysis](#log-analysis)
6. [Health Checks](#health-checks)
7. [Performance Profiling](#performance-profiling)
8. [Remote Debugging](#remote-debugging)
9. [Troubleshooting](#troubleshooting)

---

## Quick Debugging

### Check Status

```bash
# Quick status check
devloop status

# Output:
# DevLoop Status
# ═══════════════════════════════════
# Status: ✓ Running
# Daemon: PID 12345
# Project: /home/user/my-project
# 
# Agents (5/5 enabled):
#   linter:      ✓ Ready
#   formatter:   ✓ Ready
#   test-runner: ✓ Waiting (queue depth: 2)
#   type-checker: ✓ Ready
#   security:    ✗ Error (last error: timeout)
```

### View Recent Logs

```bash
# Last 50 lines of logs
tail -50 .devloop/devloop.log

# Real-time log monitoring
tail -f .devloop/devloop.log

# Search logs for errors
grep ERROR .devloop/devloop.log | tail -20
```

### Check Configuration

```bash
# View loaded configuration
devloop config show

# Validate configuration
devloop config validate

# Compare with defaults
devloop config diff --defaults
```

---

## Debug Command

### Basic Debug

```bash
# Run diagnostics and generate report
devloop debug

# Output:
# DevLoop Debug Report
# ═══════════════════════════════════════════════════════════
# 
# ✓ Prerequisites
#   - Python 3.11.5
#   - Poetry installed
#   - Git available
#   - Watchdog package: 3.0.0
# 
# ✓ Project Setup
#   - Project directory: /home/user/my-project
#   - .devloop exists: yes
#   - agents.json readable: yes
#   - Config valid: yes
# 
# ✓ Daemon
#   - Running: yes
#   - PID: 12345
#   - Memory: 125MB
#   - CPU: 5.2%
# 
# ✓ Agents (5/5)
#   - linter: READY (1,234 runs, 245ms avg)
#   - formatter: READY (892 runs, 142ms avg)
#   - test-runner: RUNNING (queue: 2)
#   - type-checker: READY (567 runs)
#   - security: ERROR (last: timeout 30s ago)
# 
# ⚠️  Issues
#   - security agent timeout (retry in 10s)
# 
# ℹ️  Recommendations
#   1. Check security agent logs
#   2. Consider increasing timeout from 30s to 60s
```

### Detailed Debug

```bash
# Include detailed analysis
devloop debug --detailed

# Includes:
# - File system watcher status
# - Event queue analysis
# - Memory usage breakdown
# - Disk space usage
# - Network connectivity
# - External tools availability
```

### Export Debug Package

```bash
# Create complete debug package for support
devloop debug --export

# Creates: devloop-debug-2025-12-13.tar.gz
# Contains:
#   - Configuration files
#   - Recent logs (sanitized)
#   - System information
#   - Agent metrics
#   - State snapshots
```

---

## State Dump

### Dump Current State

```bash
# Export full internal state
devloop debug state-dump

# Output: state-dump.json
# Contents:
# {
#   "timestamp": "2025-12-13T18:12:34Z",
#   "version": "0.4.1",
#   "daemon": {
#     "pid": 12345,
#     "uptime": "2h 34m",
#     "memory_mb": 250,
#     "cpu_percent": 5.2
#   },
#   "agents": {
#     "linter": {
#       "status": "READY",
#       "runs": 1234,
#       "last_run": "2025-12-13T18:12:20Z",
#       "queue_depth": 0,
#       "success_rate": 0.998
#     }
#   },
#   "files": {
#     "watched": 9842,
#     "changed_since_start": 542,
#     "pending_events": 3
#   },
#   "storage": {
#     "context_db": "1.2MB",
#     "events_db": "45.6MB",
#     "logs": "12.3MB"
#   }
# }
```

### Dump Context Store

```bash
# Export context store contents
devloop debug context-dump

# Shows all cached context:
# - File metadata
# - Project structure
# - Dependencies
# - Performance history
```

### Dump Event Queue

```bash
# See pending events
devloop debug queue-dump

# Output:
# Event Queue (3 pending)
# ═════════════════════════════════════
# 1. file:modified "src/main.py" (queued: 2.3s ago)
#    → formatter (waiting)
#    → linter (waiting)
# 
# 2. file:modified "tests/test_main.py" (queued: 1.1s ago)
#    → test-runner (waiting)
# 
# 3. file:created ".mypy_cache/lib/x.data.json" (queued: 50ms ago)
#    → (excluded, will be dropped)
```

---

## Trace Mode

### Enable Trace Mode

```bash
# Run with full trace logging
devloop watch . --trace

# Or enable for specific agent
devloop watch . --trace-agent linter

# Output includes detailed execution flow
```

### Trace Output Example

```
[2025-12-13 18:12:45.234] TRACE devloop.core.manager: Starting watch
[2025-12-13 18:12:45.235] TRACE devloop.collectors.filesystem: Initializer filesystem watcher
[2025-12-13 18:12:45.340] TRACE devloop.agents.linter: Registered linter agent
[2025-12-13 18:12:45.341] TRACE devloop.core.event_bus: Event bus ready (handlers: 5)

[2025-12-13 18:12:52.123] TRACE devloop.collectors.filesystem: Change detected: src/main.py (modified)
[2025-12-13 18:12:52.124] TRACE devloop.core.event_bus: Event published (file:modified)
[2025-12-13 18:12:52.125] TRACE devloop.agents.linter: Event received (debounce: 500ms)
[2025-12-13 18:12:52.626] TRACE devloop.agents.linter: Debounce complete, processing...
[2025-12-13 18:12:52.627] TRACE devloop.agents.linter: Running ruff on src/main.py
[2025-12-13 18:12:53.142] TRACE devloop.agents.linter: Ruff completed (found 2 issues)
[2025-12-13 18:12:53.143] TRACE devloop.agents.linter: Publishing findings
```

### Trace Mode Levels

```bash
# Level 1: Basic (function calls)
devloop watch . --trace-level 1

# Level 2: Detailed (+ variable values)
devloop watch . --trace-level 2

# Level 3: Very detailed (+ internal state)
devloop watch . --trace-level 3

# Level 4: Complete (+ system calls)
devloop watch . --trace-level 4
```

### Filter Traces

```bash
# Trace specific module
devloop watch . --trace --trace-filter "devloop.agents.*"

# Trace specific agent
devloop watch . --trace --trace-filter "linter"

# Exclude traces
devloop watch . --trace --trace-exclude "devloop.core.context_store"

# Multiple filters
devloop watch . --trace --trace-filter "linter,formatter" --trace-level 2
```

### Save Traces

```bash
# Save traces to file
devloop watch . --trace --trace-output trace.log

# Save in structured format
devloop watch . --trace --trace-format json --trace-output trace.jsonl
```

---

## Log Analysis

### View All Logs

```bash
# View logs with timestamps
devloop logs --follow

# View last N lines
devloop logs --tail 100

# View with time filter
devloop logs --since "1 hour ago"
devloop logs --until "2025-12-13 18:00:00"

# View specific level
devloop logs --level ERROR
devloop logs --level WARN
devloop logs --level INFO
```

### Search Logs

```bash
# Search for pattern
devloop logs --grep "timeout"

# Case insensitive search
devloop logs --grep "ERROR" --ignore-case

# Search in time range
devloop logs --grep "error" --since "1 hour ago"

# Inverse search (exclude pattern)
devloop logs --grep "DEBUG" --invert-match
```

### Extract Useful Logs

```bash
# Extract errors and warnings only
devloop logs extract --severity error,warn --output important.log

# Extract agent-specific logs
devloop logs extract --agent linter --output linter.log

# Extract logs for specific time period
devloop logs extract --since "1h ago" --output recent.log

# Extract with context
devloop logs extract --grep "timeout" --context 5 --output context.log
```

### Analyze Logs

```bash
# Generate log summary
devloop logs analyze

# Output:
# Log Analysis (last 24 hours)
# ═════════════════════════════════════
# Total lines: 12,345
# Errors: 23
# Warnings: 156
# 
# Most common errors:
#   1. timeout (8 occurrences)
#   2. memory exceeded (5 occurrences)
#   3. file not found (4 occurrences)
# 
# Most active agents:
#   1. linter: 4,523 operations
#   2. test-runner: 2,145 operations
#   3. formatter: 1,892 operations
```

### Log Rotation and Cleanup

```bash
# Check log disk usage
devloop logs size

# Rotate logs manually
devloop logs rotate

# Delete old logs
devloop logs clean --older-than "30 days"

# Compress logs
devloop logs compress --older-than "7 days"
```

---

## Health Checks

### Run Health Check

```bash
# Full health check
devloop health

# Output:
# DevLoop Health Check
# ═══════════════════════════════════════════
# 
# ✓ Daemon Health: OK
#   - Running: yes
#   - Response time: 45ms
#   - Memory: 245MB
# 
# ✓ Storage Health: OK
#   - Context DB: good
#   - Events DB: good
#   - Disk space: 50GB free
# 
# ✓ Agents Health: OK
#   - 5/5 agents responsive
#   - Avg response time: 234ms
# 
# ⚠️  Warnings
#   - Events DB growing fast (2MB/day)
#   - Memory increased 15% this week
# 
# Overall: HEALTHY
```

### Monitor Specific Components

```bash
# Check daemon health
devloop health daemon

# Check agent health
devloop health agents

# Check storage health
devloop health storage

# Check system resources
devloop health resources
```

---

## Performance Profiling

### Profile Agents

```bash
# Profile all agents
devloop profile agents --duration 60

# Profile specific agent
devloop profile agents --agent linter --duration 60

# Output:
# Agent Performance Profile (60 seconds)
# ═════════════════════════════════════════════
# 
# linter:
#   Calls: 45
#   Total time: 12.3s
#   Avg time: 273ms
#   Min time: 145ms
#   Max time: 892ms
#   P95: 745ms
#   CPU: 12.3%
#   Memory peak: 145MB
```

### Profile System

```bash
# Profile system during watch
devloop profile system --duration 300 --output profile.html

# Output: Interactive flamegraph HTML
```

### Memory Analysis

```bash
# Detect memory leaks
devloop health memory-analysis

# Output:
# Memory Analysis
# ═════════════════════════════════════
# Memory growth rate: 2.1MB/hour
# Likely cause: event queue not cleaning
# Recommendation: Reduce event log retention
```

---

## Remote Debugging

### SSH Debugging

```bash
# Export debug package over SSH
devloop debug --export | ssh user@remote.server "tar xzf - -C /tmp"

# Or directly
devloop debug export-to /path/to/export
scp /path/to/export/debug-*.tar.gz user@remote:/tmp/

# On remote, analyze
tar xzf debug-*.tar.gz
devloop debug analyze < debug-package/
```

### Streaming Logs

```bash
# Stream logs from remote
ssh user@remote.server "tail -f /path/to/project/.devloop/devloop.log"

# Or collect and analyze
ssh user@remote.server "devloop debug export" | tar xz
```

### Remote Profiling

```bash
# Enable profiling on remote
ssh user@remote.server "devloop profile agents --duration 60 --output /tmp/profile.json"

# Fetch results
scp user@remote.server:/tmp/profile.json ./

# Analyze locally
devloop debug analyze-profile profile.json
```

---

## Troubleshooting Guide

### Issue: DevLoop Hangs

**Symptoms:**
- No response to commands
- Consuming CPU
- No log output

**Debug:**
```bash
# Check status
devloop status --timeout 5

# Run trace to see where it's stuck
devloop debug trace --timeout 10

# Check for deadlocks
devloop health check-deadlocks
```

**Solutions:**
1. Check trace output for blocking operation
2. Restart daemon: `devloop stop && devloop watch .`
3. Check logs for infinite loops
4. Reduce concurrent agents

### Issue: High Memory Usage

**Symptoms:**
- Memory grows over time
- Eventually crashes or OOM

**Debug:**
```bash
# Check memory usage
devloop health resources --detailed

# Analyze memory growth
devloop health memory-analysis

# Check what's in memory
devloop debug context-dump | jq '.size_by_category'
```

**Solutions:**
1. Enable memory limits: Set `resourceLimits.maxMemory`
2. Reduce event log retention
3. Clear context cache: `devloop cleanup`
4. Check for leaking processes

### Issue: Agent Timeouts

**Symptoms:**
- Agent keeps timing out
- Takes 30+ seconds to complete
- Others agents waiting

**Debug:**
```bash
# Trace specific agent
devloop watch . --trace-agent agent-name

# Check execution time
devloop health agents --detailed

# Profile slow agent
devloop profile agents --agent agent-name --duration 60
```

**Solutions:**
1. Increase timeout: Update config
2. Check system load: `devloop health resources`
3. Check for slow external tools (e.g., slow linter)
4. Reduce batch size

### Issue: Lost Connection

**Symptoms:**
- "Connection lost" error
- Agent stops running
- Needs restart

**Debug:**
```bash
# Check daemon status
devloop status

# View recent errors
devloop logs --grep "connection" --context 5

# Run health check
devloop health
```

**Solutions:**
1. Restart daemon: `devloop stop && devloop watch .`
2. Check file permissions in `.devloop`
3. Check disk space
4. Check system stability

---

## Support Information

### Generate Support Bundle

```bash
# Create complete diagnostic bundle
devloop support-bundle

# Creates: devloop-support-YYYYMMDD-HHMMSS.tar.gz
# Contains:
#   - System information
#   - Configuration (sanitized)
#   - Recent logs
#   - Performance metrics
#   - Debug information
#   - Device information
```

### Report an Issue

```bash
# Create issue report
devloop debug report-issue

# Guides you through:
# 1. Describe the issue
# 2. Reproduce steps
# 3. Collect diagnostics
# 4. Generate report
# 5. Submit to GitHub Issues
```

---

## Best Practices

1. **Start with status**: `devloop status` first
2. **Check logs early**: Logs often have the answer
3. **Use trace mode**: For complex issues
4. **Profile before tuning**: Get data before optimizing
5. **Save debug packages**: For support requests
6. **Test in isolation**: Disable other agents to narrow down
7. **Check logs for warnings**: Don't wait for errors
8. **Document issues**: Save reproduction steps
9. **Clean up regularly**: `devloop cleanup` periodically
10. **Monitor health**: Use `devloop health` regularly

---

## See Also

- [Performance Tuning](./PERFORMANCE_TUNING.md)
- [Metrics and Monitoring](./METRICS_AND_MONITORING.md)
- [Configuration Guide](./configuration.md)
- [Troubleshooting](./troubleshooting.md)
