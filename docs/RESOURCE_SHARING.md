# Resource Sharing Implementation Guide

Comprehensive guide for implementing resource sharing across multiple DevLoop projects in a workspace.

## Overview

Resource sharing prevents system overload when multiple projects run agents simultaneously. DevLoop provides flexible allocation strategies, monitoring, and enforcement mechanisms.

## Core Concepts

### Resource Types

1. **CPU**: Percentage of available CPU cores
2. **Memory**: Absolute RAM allocation in MB/GB
3. **File Handles**: Maximum open files per agent
4. **Process Threads**: Maximum threads per agent

### Allocation Models

**Global Limits**: Total resources across entire workspace
```
Total CPU Available: 60% (max)
Total Memory Available: 2GB (max)
```

**Per-Project Limits**: Resources available to each project
```
Project A: 20% CPU, 512MB memory
Project B: 20% CPU, 512MB memory
Project C: 20% CPU, 512MB memory
```

**Per-Agent Limits**: Resources for individual agents
```
Linter agent: 5% CPU, 128MB memory
Formatter agent: 5% CPU, 128MB memory
Test runner: 10% CPU, 256MB memory
```

---

## Configuration

### Global Resource Limits

```json
{
  "global": {
    "resourceLimits": {
      "maxCpu": 60,
      "maxMemory": "2GB",
      "maxMemory_bytes": 2147483648,
      "checkInterval": 10,
      "enforcementAction": "pause",
      "resumeThreshold": 0.8
    }
  }
}
```

**Properties:**
- `maxCpu`: Maximum CPU percentage (0-100)
- `maxMemory`: Maximum memory (human-readable: "500MB", "2GB")
- `maxMemory_bytes`: Same as above, in bytes (if specified)
- `checkInterval`: Check frequency in seconds
- `enforcementAction`: `"pause"` (pause agents) or `"warn"` (warn only)
- `resumeThreshold`: Resume at this percentage below limit (0.8 = 80%)

### Per-Project Limits

```json
{
  "resource_sharing": {
    "perProjectLimits": {
      "auth-service": {
        "maxCpu": 20,
        "maxMemory": "512MB"
      },
      "api-service": {
        "maxCpu": 25,
        "maxMemory": "750MB"
      },
      "worker-service": {
        "maxCpu": 15,
        "maxMemory": "256MB"
      }
    }
  }
}
```

### Per-Agent Limits

Override in project's `.devloop/agents.json`:

```json
{
  "agents": {
    "linter": {
      "enabled": true,
      "resourceLimits": {
        "maxCpu": 5,
        "maxMemory": "128MB"
      }
    },
    "test-runner": {
      "enabled": true,
      "resourceLimits": {
        "maxCpu": 15,
        "maxMemory": "512MB"
      }
    }
  }
}
```

---

## Allocation Strategies

### 1. Equal Distribution

All projects get equal resources.

**Configuration:**
```json
{
  "resource_sharing": {
    "strategy": "equal",
    "cpuLimit": 60,
    "memoryLimit": "2GB"
  }
}
```

**Example with 3 projects:**
- Each project: 20% CPU, 686MB memory

**When to use:**
- Small teams with similar-sized services
- Development environments
- When services have similar workloads

### 2. Weighted Distribution

Projects get resources proportional to weight.

**Configuration:**
```json
{
  "resource_sharing": {
    "strategy": "weighted",
    "cpuLimit": 60,
    "memoryLimit": "2GB",
    "weights": {
      "auth-service": 2,
      "api-service": 2,
      "worker-service": 1
    }
  }
}
```

**Calculation:**
- Total weight: 2 + 2 + 1 = 5
- auth-service: (2/5) × 60% = 24% CPU, (2/5) × 2GB = 819MB
- api-service: (2/5) × 60% = 24% CPU, (2/5) × 2GB = 819MB
- worker-service: (1/5) × 60% = 12% CPU, (1/5) × 2GB = 410MB

**When to use:**
- Monorepos with critical and non-critical services
- Different service resource requirements
- Production environments with priorities

### 3. Priority-Based Distribution

Critical projects get priority, others share remainder.

**Configuration:**
```json
{
  "resource_sharing": {
    "strategy": "priority"
  }
}
```

With project priorities:
```json
{
  "projects": [
    { "name": "auth-service", "priority": 0 },    // Critical
    { "name": "api-service", "priority": 1 },     // High
    { "name": "worker-service", "priority": 2 }   // Normal
  ]
}
```

**Allocation (with 60% CPU, 2GB memory):**
1. Priority 0 projects: Guaranteed resources first
2. Priority 1 projects: Share remainder
3. Priority 2 projects: Get leftover

**When to use:**
- Clear service hierarchy
- Critical services must never wait
- Production workloads

### 4. Dynamic/Adaptive Distribution

Resources reallocate based on actual usage.

**Configuration:**
```json
{
  "resource_sharing": {
    "strategy": "dynamic",
    "cpuLimit": 60,
    "memoryLimit": "2GB",
    "adaptation": {
      "enabled": true,
      "adjustmentFrequency": 30,
      "usageThreshold": 0.8,
      "reallocationFactor": 0.2
    }
  }
}
```

**How it works:**
1. Monitor actual usage
2. If project uses > 80% allocation for 30 seconds
3. Give it +20% more resources
4. Take from projects using < 50% of allocation

**Constraints:**
- Never exceed global limits
- Maintain minimum allocation per project
- Respect priority ordering

**When to use:**
- Highly variable workloads
- Auto-scaling needed
- AI/ML workloads with spiky resource usage

### 5. Custom/Manual Distribution

Explicitly specify per-project limits.

**Configuration:**
```json
{
  "resource_sharing": {
    "strategy": "custom",
    "perProjectLimits": {
      "auth-service": {
        "maxCpu": 30,
        "maxMemory": "800MB"
      },
      "api-service": {
        "maxCpu": 20,
        "maxMemory": "500MB"
      },
      "worker-service": {
        "maxCpu": 10,
        "maxMemory": "256MB"
      }
    }
  }
}
```

**Total check:**
- Sum: 30 + 20 + 10 = 60% CPU ✓
- Sum: 800MB + 500MB + 256MB = 1556MB < 2GB ✓

**When to use:**
- Precise tuning
- Known workload patterns
- Complex resource requirements

---

## Implementation Details

### Resource Monitoring

Monitor actual resource usage:

```python
# Check workspace resource usage
from devloop.core.resource_manager import ResourceManager

manager = ResourceManager(workspace_config)

# Get current usage
usage = manager.get_workspace_usage()
# {
#   "cpu_percent": 45.2,
#   "memory_mb": 1250,
#   "cpu_limit": 60,
#   "memory_limit_mb": 2048
# }

# Get per-project usage
project_usage = manager.get_project_usage("auth-service")
# {
#   "cpu_percent": 15.3,
#   "memory_mb": 400,
#   "cpu_limit": 20,
#   "memory_limit_mb": 512
# }
```

### Resource Enforcement

Pause/resume agents based on limits:

```python
# Check if resources available
can_run = manager.can_run_agent("linter")

if can_run:
    agent.start()
else:
    agent.wait_for_resources()

# When resources available again
manager.resume_paused_agents()
```

### Stress Testing

Test resource limits:

```bash
# Simulate high resource usage
devloop workspace stress-test .devloop-workspace \
  --duration 300 \
  --target-cpu 80 \
  --target-memory 90 \
  --output stress-test-report.json
```

---

## Monitoring & Metrics

### View Resource Metrics

```bash
# Workspace-level metrics
devloop workspace metrics --workspace-dir .devloop-workspace

# Output:
# Workspace Resource Usage
# ═════════════════════════
# CPU:        45.2% / 60% limit
# Memory:     1250MB / 2048MB limit
# 
# Per-Project:
# auth-service:    15.3% / 20% limit
# api-service:     18.1% / 25% limit
# worker-service:   11.8% / 15% limit
```

### Export Metrics

```bash
# Export as JSON for analysis
devloop workspace metrics --workspace-dir .devloop-workspace \
  --format json \
  --output metrics.json

# Export as CSV for time series
devloop workspace metrics --workspace-dir .devloop-workspace \
  --format csv \
  --start "2 hours ago" \
  --interval 1m \
  --output metrics.csv
```

### Analyze Historical Data

```bash
# Find peak resource usage
devloop workspace analytics peak-usage \
  --workspace-dir .devloop-workspace \
  --period 24h

# Find resource bottlenecks
devloop workspace analytics bottlenecks \
  --workspace-dir .devloop-workspace \
  --threshold 80

# Show allocation efficiency
devloop workspace analytics efficiency \
  --workspace-dir .devloop-workspace \
  --output efficiency-report.json
```

### Create Dashboards

```bash
# Start monitoring dashboard
devloop workspace dashboard \
  --workspace-dir .devloop-workspace \
  --refresh 5s \
  --metrics cpu,memory,agents
```

---

## Advanced Scenarios

### Scenario 1: Uneven Resource Requirements

Services with very different resource needs:

```json
{
  "resource_sharing": {
    "strategy": "custom",
    "perProjectLimits": {
      "compute-service": {
        "maxCpu": 40,
        "maxMemory": "1GB"
      },
      "doc-service": {
        "maxCpu": 10,
        "maxMemory": "256MB"
      },
      "sync-service": {
        "maxCpu": 10,
        "maxMemory": "256MB"
      }
    }
  }
}
```

### Scenario 2: Peak vs. Idle Profiles

Use different profiles based on time:

```json
{
  "resource_sharing": {
    "profiles": {
      "peak": {
        "cpuLimit": 80,
        "memoryLimit": "3GB",
        "times": ["09:00-17:00"]
      },
      "idle": {
        "cpuLimit": 20,
        "memoryLimit": "512MB",
        "times": ["17:00-09:00"]
      }
    }
  }
}
```

### Scenario 3: CI vs. Development Environments

Different limits for CI and local development:

```bash
# Development environment: aggressive limits
DEVLOOP_RESOURCE_PROFILE=dev devloop watch .

# CI environment: conservative limits
DEVLOOP_RESOURCE_PROFILE=ci devloop watch .
```

Profiles in `workspace.json`:
```json
{
  "resource_profiles": {
    "dev": {
      "cpuLimit": 60,
      "memoryLimit": "2GB"
    },
    "ci": {
      "cpuLimit": 90,
      "memoryLimit": "4GB"
    }
  }
}
```

### Scenario 4: Overflow Handling

When resources exceed limits, queue agents:

```json
{
  "global": {
    "resourceLimits": {
      "maxCpu": 60,
      "maxMemory": "2GB",
      "overflow": {
        "enabled": true,
        "queueing": true,
        "maxQueueSize": 50,
        "maxWaitTime": 300
      }
    }
  }
}
```

When full:
- Queue agents up to `maxQueueSize`
- Run agents in priority order
- Fail if wait > `maxWaitTime`

---

## Tuning Guide

### Measuring Current Usage

```bash
# Run baseline measurement (no agents)
devloop workspace metrics --baseline --duration 60 --output baseline.json

# Run with agents active
devloop watch . --workspace-dir .devloop-workspace --metrics-output active.json

# Compare
devloop workspace metrics compare baseline.json active.json
```

### Calculating Allocation

```bash
# System has: 8 CPU cores, 16GB RAM
# Available: 60% CPU = 4.8 cores, 75% = 12GB

# For 3 projects:
# Equal: Each gets 1.6 cores, 4GB
# Weighted (2:2:1): 2.56, 2.56, 1.28 cores...
```

### Auto-Tuning

Let DevLoop suggest optimal limits:

```bash
# Run auto-tune (monitors for 1 hour)
devloop workspace autotune \
  --workspace-dir .devloop-workspace \
  --duration 3600 \
  --output suggestions.json

# Apply suggestions
devloop workspace apply-tuning suggestions.json --workspace-dir .devloop-workspace
```

---

## Troubleshooting

### Issue: Agents Keep Getting Paused

**Symptoms:**
- Agents frequently pause/resume
- Slow overall execution

**Debug:**
```bash
# Check resource usage
devloop workspace metrics --detailed

# Check enforcement logs
tail -f .devloop-workspace/resource-enforcement.log

# Identify bottleneck
devloop workspace analytics bottlenecks --threshold 70
```

**Solutions:**
1. Increase global limits if available
2. Reduce per-agent resource usage
3. Switch to weighted/priority strategy
4. Spread agents across time

### Issue: Uneven Resource Distribution

**Symptoms:**
- Some projects under-utilized
- Others resource-constrained

**Debug:**
```bash
# Compare actual vs. configured
devloop workspace metrics --compare-config
```

**Solutions:**
1. Switch to weighted/dynamic strategy
2. Adjust weights/priorities
3. Increase limits for critical projects

### Issue: Out of Memory

**Symptoms:**
- OOM killer triggered
- DevLoop daemon crashes

**Debug:**
```bash
# Find memory leaks
devloop workspace health --detailed --memory-analysis

# Check per-agent memory
devloop audit query --agent "*" --metric memory
```

**Solutions:**
1. Reduce memory limits
2. Add swap space
3. Disable memory-intensive agents
4. Increase system RAM

---

## Best Practices

1. **Start Conservative**: Begin with 50% CPU, 25% memory
2. **Monitor First**: Run for a week before tuning
3. **Auto-Tune**: Use `devloop workspace autotune`
4. **Test Changes**: Always test allocation changes in dev first
5. **Document Rationale**: Note why you chose specific limits
6. **Regular Review**: Re-evaluate quarterly as workloads change
7. **Alert on Violations**: Set up monitoring for limit breaches
8. **Graceful Degradation**: Use `pause` enforcement, not `kill`

---

## See Also

- [Multi-Project Setup](./MULTI_PROJECT_SETUP.md)
- [Workspace Configuration](./WORKSPACE_CONFIGURATION.md)
- [Performance Guide](./PERFORMANCE.md)
