# Performance Tuning Guide

Comprehensive guide for tuning DevLoop performance with per-agent configuration options, debounce settings, sampling, and adaptive throttling for different system capacities.

## Overview

DevLoop provides fine-grained performance tuning options at multiple levels:

- **Global**: Workspace-wide settings
- **Per-Project**: Project-specific overrides
- **Per-Agent**: Individual agent configuration
- **Adaptive**: Dynamic tuning based on system load

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Tuning Parameters](#core-tuning-parameters)
3. [Agent Configuration](#agent-configuration)
4. [Debounce Settings](#debounce-settings)
5. [Sampling & Throttling](#sampling--throttling)
6. [Adaptive Throttling](#adaptive-throttling)
7. [Batch Processing](#batch-processing)
8. [Preset Configurations](#preset-configurations)
9. [System-Specific Tuning](#system-specific-tuning)
10. [Monitoring & Adjustments](#monitoring--adjustments)
11. [Troubleshooting](#troubleshooting)

---

## Quick Start

### For Slow Systems

Use preset for low-end hardware:

```bash
devloop init /path/to/project --performance-preset low-end
```

This applies:
- Debounce: 2000ms
- Batch size: 5
- Sample rate: 30%
- Max concurrent agents: 2

### For Fast Systems

Use preset for powerful hardware:

```bash
devloop init /path/to/project --performance-preset high-performance
```

This applies:
- Debounce: 300ms
- Batch size: 50
- Sample rate: 100%
- Max concurrent agents: 10

### For Balanced Systems

```bash
devloop init /path/to/project --performance-preset balanced
```

---

## Core Tuning Parameters

### Global Settings

**Location:** `.devloop/agents.json` or `.devloop-workspace/workspace.json`

```json
{
  "global": {
    "performance": {
      "debounceMs": 500,
      "batchSize": 20,
      "sampleRate": 1.0,
      "maxConcurrentAgents": 5,
      "maxQueueSize": 100,
      "adaptiveThrottling": {
        "enabled": true,
        "cpuThreshold": 0.8,
        "memoryThreshold": 0.8
      }
    }
  }
}
```

### Parameters Explained

| Parameter | Type | Default | Range | Effect |
|-----------|------|---------|-------|--------|
| `debounceMs` | int | 500 | 100-5000 | Wait time before processing events |
| `batchSize` | int | 20 | 1-100 | Events to process per batch |
| `sampleRate` | float | 1.0 | 0-1.0 | Percentage of events to process |
| `maxConcurrentAgents` | int | 5 | 1-20 | Simultaneous agents running |
| `maxQueueSize` | int | 100 | 10-1000 | Max pending events |
| `cpuThreshold` | float | 0.8 | 0-1.0 | CPU usage for throttling |
| `memoryThreshold` | float | 0.8 | 0-1.0 | Memory usage for throttling |

---

## Agent Configuration

### Per-Agent Tuning

Override global settings per agent:

```json
{
  "agents": {
    "linter": {
      "enabled": true,
      "triggers": ["file:modified"],
      "performance": {
        "debounceMs": 300,
        "batchSize": 10,
        "sampleRate": 1.0,
        "maxConcurrent": 2,
        "timeout": 30000
      }
    },
    "formatter": {
      "enabled": true,
      "performance": {
        "debounceMs": 500,
        "batchSize": 5,
        "sampleRate": 0.5,
        "maxConcurrent": 1,
        "timeout": 60000
      }
    },
    "test-runner": {
      "enabled": true,
      "performance": {
        "debounceMs": 1000,
        "batchSize": 1,
        "sampleRate": 1.0,
        "maxConcurrent": 1,
        "timeout": 300000
      }
    }
  }
}
```

### Agent-Specific Parameters

```json
{
  "agents": {
    "linter": {
      "performance": {
        "debounceMs": 300,
        "batchSize": 10,
        "sampleRate": 1.0,
        "maxConcurrent": 2,
        "timeout": 30000,
        "priority": "high",
        "retries": 3,
        "retryDelay": 1000,
        "cacheDuration": 300000
      }
    }
  }
}
```

| Parameter | Effect |
|-----------|--------|
| `timeout` | Kill agent if running > N ms |
| `priority` | `low`, `normal`, `high` - execution priority |
| `retries` | Retry failed runs N times |
| `retryDelay` | Wait N ms between retries |
| `cacheDuration` | Cache results for N ms |

---

## Debounce Settings

### What is Debouncing?

Debouncing prevents excessive agent runs by waiting for file changes to settle.

**Without debounce (every keystroke):**
```
Type: a → linter run
Type: b → linter run
Type: c → linter run
Type: d → linter run
[4 runs for 4 characters]
```

**With 500ms debounce:**
```
Type: a b c d ... [pause 500ms] → 1 linter run
[1 run after typing stops]
```

### Debounce Configuration

```json
{
  "global": {
    "performance": {
      "debounceMs": 500
    }
  },
  "agents": {
    "linter": {
      "performance": {
        "debounceMs": 300
      }
    },
    "formatter": {
      "performance": {
        "debounceMs": 1000
      }
    }
  }
}
```

### Debounce Presets

```json
{
  "debouncePresets": {
    "aggressive": 200,      // Very responsive
    "responsive": 500,      // Balanced
    "conservative": 1000,   // Save resources
    "very-conservative": 2000
  }
}
```

### Recommended Values

| Scenario | Debounce | Reason |
|----------|----------|--------|
| Typing code | 300-500ms | User expects quick feedback |
| Saving file | 1000ms | File write complete |
| Multi-file change | 2000ms+ | Wait for all changes |
| CI/CD pipeline | 500ms | Fast iteration |
| Resource-constrained | 2000ms+ | Minimize overhead |

---

## Sampling & Throttling

### Event Sampling

Process only a percentage of events:

```json
{
  "global": {
    "performance": {
      "sampleRate": 0.5
    }
  },
  "agents": {
    "formatter": {
      "performance": {
        "sampleRate": 0.3
      }
    }
  }
}
```

**Effects:**
- `sampleRate: 1.0` - Process all events
- `sampleRate: 0.5` - Process ~50% of events
- `sampleRate: 0.1` - Process ~10% of events (for non-critical checks)

**Use cases:**
- Non-critical agents: lower sample rate
- Critical agents: higher sample rate (1.0)
- Resource-constrained systems: lower sample rate

### File Pattern Sampling

Sample only certain file types:

```json
{
  "agents": {
    "type-checker": {
      "triggers": ["file:modified"],
      "performance": {
        "sampling": {
          "enabled": true,
          "filePatterns": ["**/*.ts", "**/*.tsx"],
          "sampleRate": 0.8,
          "minIntervalMs": 5000
        }
      }
    }
  }
}
```

### Min Interval Sampling

Run agent at minimum time intervals:

```json
{
  "agents": {
    "test-runner": {
      "performance": {
        "minIntervalMs": 5000
      }
    }
  }
}
```

Test runner won't run more than once per 5 seconds, even with many changes.

---

## Adaptive Throttling

### How Adaptive Throttling Works

DevLoop monitors system load and automatically reduces work when busy:

```
System Load: Low (< 50% CPU)
  → Run at full speed

System Load: Medium (50-80% CPU)
  → Reduce sample rate to 70%
  → Increase debounce to 750ms

System Load: High (80-95% CPU)
  → Reduce sample rate to 40%
  → Increase debounce to 1500ms

System Load: Critical (> 95% CPU)
  → Pause non-critical agents
  → Only run critical agents
```

### Configuration

```json
{
  "global": {
    "adaptiveThrottling": {
      "enabled": true,
      "cpuThreshold": 0.8,
      "memoryThreshold": 0.8,
      "checkInterval": 5,
      "throttleFactors": {
        "cpu_high": 0.6,
        "memory_high": 0.5,
        "combined_high": 0.3
      }
    }
  }
}
```

### Throttle Levels

```json
{
  "adaptiveThrottling": {
    "levels": [
      {
        "name": "normal",
        "cpuMax": 0.7,
        "memoryMax": 0.7,
        "sampleRate": 1.0,
        "debounceMultiplier": 1.0
      },
      {
        "name": "elevated",
        "cpuMax": 0.85,
        "memoryMax": 0.85,
        "sampleRate": 0.7,
        "debounceMultiplier": 1.5
      },
      {
        "name": "high",
        "cpuMax": 0.95,
        "memoryMax": 0.95,
        "sampleRate": 0.4,
        "debounceMultiplier": 2.0
      },
      {
        "name": "critical",
        "cpuMax": 1.0,
        "memoryMax": 1.0,
        "sampleRate": 0.1,
        "debounceMultiplier": 3.0
      }
    ]
  }
}
```

### Per-Agent Adaptive Settings

```json
{
  "agents": {
    "formatter": {
      "performance": {
        "adaptiveThrottling": {
          "enabled": true,
          "scalingFactor": 0.8,
          "minSampleRate": 0.1,
          "maxDebounce": 5000
        }
      }
    }
  }
}
```

---

## Batch Processing

### Batch Configuration

```json
{
  "global": {
    "performance": {
      "batchSize": 20
    }
  },
  "agents": {
    "linter": {
      "performance": {
        "batchSize": 10
      }
    }
  }
}
```

**Effects:**
- `batchSize: 1` - Process files one at a time (slow, low memory)
- `batchSize: 10` - Process in groups of 10 (balanced)
- `batchSize: 100` - Process large batches (fast, high memory)

### Smart Batching

Dynamically size batches based on system:

```json
{
  "performance": {
    "smartBatching": {
      "enabled": true,
      "minBatchSize": 1,
      "maxBatchSize": 50,
      "targetDuration": 1000
    }
  }
}
```

DevLoop adjusts batch size to process files in ~1 second.

---

## Preset Configurations

### Low-End Systems (< 2GB RAM, < 2 CPU)

```json
{
  "performance": {
    "preset": "low-end",
    "debounceMs": 2000,
    "batchSize": 5,
    "sampleRate": 0.3,
    "maxConcurrentAgents": 1,
    "adaptiveThrottling": {
      "enabled": true,
      "cpuThreshold": 0.6
    },
    "agents": {
      "linter": { "debounceMs": 2000, "batchSize": 3 },
      "formatter": { "debounceMs": 3000, "batchSize": 1 },
      "test-runner": { "enabled": false }
    }
  }
}
```

### Mid-Range Systems (4-8GB RAM, 4 CPU)

```json
{
  "performance": {
    "preset": "balanced",
    "debounceMs": 500,
    "batchSize": 20,
    "sampleRate": 1.0,
    "maxConcurrentAgents": 3,
    "adaptiveThrottling": {
      "enabled": true,
      "cpuThreshold": 0.75
    }
  }
}
```

### High-Performance Systems (16+ GB RAM, 8+ CPU)

```json
{
  "performance": {
    "preset": "high-performance",
    "debounceMs": 300,
    "batchSize": 50,
    "sampleRate": 1.0,
    "maxConcurrentAgents": 8,
    "adaptiveThrottling": {
      "enabled": true,
      "cpuThreshold": 0.85
    }
  }
}
```

### CI/CD Pipeline

```json
{
  "performance": {
    "preset": "ci-pipeline",
    "debounceMs": 100,
    "batchSize": 100,
    "sampleRate": 1.0,
    "maxConcurrentAgents": 10,
    "adaptiveThrottling": {
      "enabled": false
    },
    "timeoutMs": 600000
  }
}
```

---

## System-Specific Tuning

### Detect and Auto-Tune

```bash
# Auto-detect system capabilities and apply optimal settings
devloop init /path/to/project --auto-tune

# Or manually
devloop performance detect --output system-profile.json
devloop performance recommend --system-profile system-profile.json
```

### Manual System Analysis

```bash
# Check available resources
devloop performance analyze

# Output:
# CPU Cores: 4
# CPU Frequency: 2.4 GHz
# Total RAM: 8GB
# Available RAM: 6.2GB
# Disk Speed: SSD (fast)
# Network: Gigabit Ethernet
# 
# Recommendations:
# - Use "balanced" preset
# - Set maxConcurrentAgents: 3
# - Set batchSize: 20
# - Enable adaptive throttling
```

### Slow NFS/Network Drives

For projects on network filesystems:

```json
{
  "performance": {
    "debounceMs": 2000,
    "batchSize": 10,
    "fileSystemLatency": "high",
    "cacheWatchers": true,
    "cacheDuration": 10000
  }
}
```

### Large Codebases (100k+ files)

```json
{
  "performance": {
    "debounceMs": 1000,
    "sampleRate": 0.5,
    "exclusions": [
      "node_modules/**",
      ".git/**",
      "build/**",
      "dist/**"
    ],
    "indexing": {
      "enabled": true,
      "updateInterval": 60000
    }
  }
}
```

### Monorepos (many projects)

```json
{
  "performance": {
    "projectIsolation": true,
    "parallelProjectProcessing": true,
    "projectDebounce": 500,
    "smartResourceAllocation": true
  }
}
```

---

## Monitoring & Adjustments

### Performance Metrics

```bash
# View performance metrics
devloop performance metrics

# Output:
# Agent Performance
# ════════════════════════════════════════════
# linter:
#   Runs: 1,234
#   Avg Duration: 245ms
#   Success Rate: 99.8%
#   CPU Usage: 5.2%
#   Memory Usage: 125MB
# 
# formatter:
#   Runs: 892
#   Avg Duration: 142ms
#   Success Rate: 100%
#   CPU Usage: 2.1%
#   Memory Usage: 65MB
```

### Find Performance Bottlenecks

```bash
# Identify slow agents
devloop performance bottlenecks --top 5

# Output:
# Top Slow Agents
# ═══════════════════
# 1. test-runner:  avg 8.3s (timeout 30s)
# 2. security-scanner: avg 2.1s
# 3. type-checker: avg 1.8s
# ...
```

### Adjust Based on Metrics

```bash
# If test-runner is too slow:
# Option 1: Increase debounce
# Option 2: Reduce batch size
# Option 3: Lower sample rate

# If linter causes high CPU:
# Option 1: Reduce concurrent agents
# Option 2: Enable adaptive throttling
# Option 3: Increase debounce
```

### Export Performance Data

```bash
# Export metrics for analysis
devloop performance export --format json --output metrics.json

# Create CSV for spreadsheet analysis
devloop performance export --format csv --start "7 days ago" --output metrics.csv

# Generate performance report
devloop performance report --period 30d --output report.html
```

---

## Troubleshooting

### Issue: Agents Running Too Slowly

**Symptoms:**
- Feedback delayed > 5 seconds
- Agents often queued
- Developer frustrated

**Debug:**
```bash
# Check debounce settings
devloop performance show-config | grep debounce

# Check queue depth
devloop performance metrics --show-queue

# Check CPU usage
devloop performance metrics --show-cpu
```

**Solutions:**
1. Reduce `debounceMs` (300-500ms range)
2. Increase `maxConcurrentAgents`
3. Increase `batchSize`
4. Disable non-critical agents

### Issue: High CPU Usage

**Symptoms:**
- CPU constant at 80%+
- System becomes sluggish
- Laptop fans loud

**Debug:**
```bash
# Identify resource hogs
devloop performance bottlenecks --metric cpu

# Check adaptive throttling
devloop performance show-config | grep adaptiveThrottling
```

**Solutions:**
1. Enable adaptive throttling
2. Reduce `sampleRate`
3. Increase `debounceMs`
4. Reduce `maxConcurrentAgents`

### Issue: Memory Growing Over Time

**Symptoms:**
- Memory usage increases hour by hour
- Eventually crashes or swaps heavily

**Debug:**
```bash
# Check for memory leaks
devloop performance analyze-memory --duration 3600

# Look for unbounded caches
devloop performance show-config | grep -i cache
```

**Solutions:**
1. Set cache duration limits
2. Reduce `maxQueueSize`
3. Reduce `batchSize`
4. Increase cache cleanup interval

### Issue: Agents Keep Timing Out

**Symptoms:**
- Agents frequently time out
- Errors in logs

**Debug:**
```bash
# Check timeout settings
devloop performance show-config | grep -i timeout

# Check if system is overloaded
devloop performance metrics | grep "CPU\|Memory"
```

**Solutions:**
1. Increase `timeout` for specific agents
2. Reduce concurrent agents
3. Increase system resources
4. Profile agent to find bottleneck

### Issue: DevLoop Seems Stuck/Unresponsive

**Symptoms:**
- No agent activity
- No response to commands
- Consuming CPU

**Debug:**
```bash
# Check daemon health
devloop status

# View logs
tail -f .devloop/devloop.log

# Check for deadlocks
devloop performance deadlock-check
```

**Solutions:**
1. Restart: `devloop stop && devloop watch .`
2. Reduce `maxConcurrentAgents`
3. Increase `debounceMs`
4. Check for infinite loops in custom agents

---

## Advanced Topics

### Custom Performance Profiles

```json
{
  "performanceProfiles": {
    "light-testing": {
      "description": "Minimal agents for quick iteration",
      "enabled": ["linter"],
      "debounceMs": 1000,
      "sampleRate": 0.5
    },
    "full-check": {
      "description": "All agents for final verification",
      "enabled": ["*"],
      "debounceMs": 500,
      "sampleRate": 1.0
    }
  }
}
```

Switch profiles:
```bash
devloop watch . --performance-profile light-testing
devloop watch . --performance-profile full-check
```

### Time-Based Performance Scaling

Different settings at different times:

```json
{
  "timeBasedPerformance": {
    "peak-hours": {
      "times": ["09:00-17:00"],
      "debounceMs": 300,
      "sampleRate": 1.0
    },
    "off-hours": {
      "times": ["17:00-09:00"],
      "debounceMs": 2000,
      "sampleRate": 0.3
    }
  }
}
```

### Hardware Detection & Auto-Scaling

```bash
# Enable hardware-aware scaling
devloop init /path/to/project --hardware-aware
```

Automatically adjusts settings based on detected hardware changes.

---

## Best Practices

1. **Start Conservative**: Use low-end preset, then increase
2. **Test Changes**: Change one parameter at a time
3. **Monitor Results**: Track metrics before/after changes
4. **Document Decisions**: Comment why you chose specific values
5. **Regular Review**: Quarterly review as codebase grows
6. **Profile First**: Run `devloop performance analyze` before tuning
7. **Use Presets**: Start with presets rather than manual tuning
8. **Enable Adaptive**: Let DevLoop handle load automatically
9. **Reasonable Timeouts**: Don't set too low or too high
10. **Test on CI**: Validate settings work in CI/CD environment

---

## See Also

- [Multi-Project Setup](./MULTI_PROJECT_SETUP.md)
- [Resource Sharing](./RESOURCE_SHARING.md)
- [Configuration Guide](./configuration.md)
- [Architecture Guide](./architecture.md)
