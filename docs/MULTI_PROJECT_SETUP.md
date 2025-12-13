# Multi-Project Setup & Workspace Support

This guide covers running DevLoop across single and multiple projects, workspace coordination, and resource sharing.

## Table of Contents

1. [Single Project Setup](#single-project-setup)
2. [Multi-Project Setup](#multi-project-setup)
3. [Workspace Configuration](#workspace-configuration)
4. [Resource Sharing](#resource-sharing)
5. [Coordination Strategies](#coordination-strategies)
6. [Testing Multi-Project Setups](#testing-multi-project-setups)
7. [Troubleshooting](#troubleshooting)

---

## Single Project Setup

The simplest and most common setup. DevLoop monitors a single project directory with isolated `.devloop` configuration.

### Basic Setup

```bash
# Initialize DevLoop in a single project
cd /path/to/my-project
devloop init .
devloop watch .
```

### Project Structure

```
my-project/
├── .devloop/                 # Project-specific configuration
│   ├── agents.json          # Agent configuration
│   ├── context/             # Context store (project-local)
│   ├── events.db            # Event log (project-local)
│   └── devloop.log          # Log file (project-local)
├── src/
├── tests/
└── pyproject.toml
```

### Key Points

- ✅ Each project has its own `.devloop` directory
- ✅ Agents run independently for each project
- ✅ Configuration is project-specific
- ✅ No cross-project interference
- ✅ Simplest to set up and maintain

### Configuration Example

```json
{
  "global": {
    "mode": "report-only",
    "maxConcurrentAgents": 5,
    "resourceLimits": {
      "maxCpu": 25,
      "maxMemory": "500MB"
    }
  },
  "agents": {
    "linter": { "enabled": true },
    "formatter": { "enabled": true },
    "test-runner": { "enabled": true }
  }
}
```

---

## Multi-Project Setup

Running DevLoop across multiple independent projects in the same workspace or monorepo.

### Use Cases

**When to use multi-project:**
- Monorepo with multiple independent services
- Workspace with multiple development projects
- Coordinating agents across related codebases
- Shared resource limitations across projects
- Centralized event logging and monitoring

### Architecture

```
workspace/
├── project-a/
│   ├── .devloop/              # Project-specific config
│   └── src/
├── project-b/
│   ├── .devloop/              # Project-specific config
│   └── src/
└── .devloop-workspace/        # Workspace-level config (optional)
    ├── workspace.json         # Workspace settings
    ├── shared-context/        # Optional: shared context store
    └── workspace-events.db    # Optional: centralized events
```

### Setup Methods

#### Method 1: Independent Project Initialization (Recommended for Most Cases)

Each project maintains its own configuration and runs independently:

```bash
# Initialize each project separately
cd workspace/project-a
devloop init .
devloop watch .  # Terminal 1

cd workspace/project-b
devloop init .
devloop watch .  # Terminal 2
```

**Advantages:**
- Isolates configuration per project
- Failures in one project don't affect others
- Clear separation of concerns
- Scales well for independent teams

**Disadvantages:**
- Duplicate configuration
- Separate resource monitoring
- No cross-project insights

#### Method 2: Shared Workspace Configuration (Coordinated Mode)

A single workspace configuration manages multiple projects:

```bash
# Initialize workspace-level configuration
mkdir .devloop-workspace
devloop workspace init .devloop-workspace

# Each project references workspace config
cd project-a
devloop init . --workspace-dir ../.devloop-workspace

cd project-b
devloop init . --workspace-dir ../.devloop-workspace

# Start watching all projects
devloop watch . --workspace-dir ../.devloop-workspace
```

**Advantages:**
- Centralized configuration
- Shared resource limits
- Unified event logging
- Cross-project coordination
- Consistent agent behavior

**Disadvantages:**
- More complex setup
- Shared state requires careful management
- Potential bottlenecks
- More debugging complexity

#### Method 3: Hybrid Approach (Recommended for Monorepos)

Combine workspace-level defaults with project-specific overrides:

```bash
# Workspace setup
.devloop-workspace/
├── workspace.json         # Default configuration
├── agents.json           # Default agent config
└── shared-context/       # Optional shared context

# Each project
project-a/
├── .devloop/
│   ├── agents.json       # Project overrides (optional)
│   └── .gitignore
```

### Configuration Example: Multi-Project Workspace

**`.devloop-workspace/workspace.json`**

```json
{
  "type": "workspace",
  "workspace_name": "my-monorepo",
  "projects": [
    {
      "name": "project-a",
      "path": "services/project-a",
      "config_override": "services/project-a/.devloop/agents.json"
    },
    {
      "name": "project-b",
      "path": "services/project-b",
      "config_override": "services/project-b/.devloop/agents.json"
    }
  ],
  "global": {
    "mode": "report-only",
    "maxConcurrentAgents": 10,
    "contextStoreEnabled": true,
    "contextStorePath": ".devloop-workspace/shared-context",
    "eventLogPath": ".devloop-workspace/workspace-events.db"
  },
  "agent_defaults": {
    "linter": { "enabled": true },
    "formatter": { "enabled": true },
    "test-runner": { "enabled": true }
  }
}
```

**`project-a/.devloop/agents.json`**

```json
{
  "type": "project",
  "workspace_dir": "../../.devloop-workspace",
  "project_name": "project-a",
  "global": {
    "mode": "report-only"
  },
  "agents": {
    "linter": {
      "enabled": true,
      "config": {
        "filePatterns": ["src/**/*.py"]
      }
    }
  }
}
```

---

## Workspace Configuration

### Workspace Initialization

```bash
# Create and initialize workspace configuration
devloop workspace init /path/to/workspace/.devloop-workspace

# This creates:
# - workspace.json (main configuration)
# - shared-context/ (optional context store)
# - agents.json (default agent configuration)
```

### Workspace Structure

```json
{
  "type": "workspace",
  "workspace_name": "my-workspace",
  "workspace_root": "/absolute/path/to/workspace",
  "projects": [
    {
      "name": "project-name",
      "path": "relative/path/to/project",
      "enabled": true,
      "config_override": "relative/path/to/.devloop/agents.json"
    }
  ],
  "global": {
    "mode": "report-only",
    "maxConcurrentAgents": 10,
    "resourceLimits": {
      "maxCpu": 50,
      "maxMemory": "2GB"
    },
    "contextStoreEnabled": true,
    "contextStorePath": ".devloop-workspace/shared-context",
    "eventLogPath": ".devloop-workspace/workspace-events.db"
  },
  "agent_defaults": {
    "linter": { "enabled": true },
    "formatter": { "enabled": true }
  }
}
```

### Commands

```bash
# Validate workspace configuration
devloop workspace validate /path/to/.devloop-workspace

# List all projects in workspace
devloop workspace list-projects /path/to/.devloop-workspace

# Check workspace status
devloop workspace status /path/to/.devloop-workspace

# Initialize specific projects
devloop workspace init-project /path/to/project-a --workspace-dir ../.devloop-workspace

# Add a new project to workspace
devloop workspace add-project /path/to/project-c --workspace-dir /path/to/.devloop-workspace
```

---

## Resource Sharing

When running multiple projects, consider shared resource limits to prevent system overload.

### Shared Resource Limits

```json
{
  "global": {
    "resourceLimits": {
      "maxCpu": 50,        // Total CPU across all projects
      "maxMemory": "2GB",  // Total memory across all projects
      "checkInterval": 10  // Check every 10 seconds
    },
    "workspaceResourceLimits": {
      "enabled": true,
      "maxCpuPerProject": 15,
      "maxMemoryPerProject": "500MB"
    }
  }
}
```

### Resource Allocation Strategies

#### 1. Equal Allocation

```json
{
  "workspaceResourceLimits": {
    "strategy": "equal",
    "projects": 2,
    "total_cpu_percent": 50,
    "total_memory_mb": 2048
  }
}
```

Per project:
- CPU: 25% (50 ÷ 2)
- Memory: 1024 MB (2048 ÷ 2)

#### 2. Weight-Based Allocation

```json
{
  "workspaceResourceLimits": {
    "strategy": "weighted",
    "total_cpu_percent": 50,
    "total_memory_mb": 2048,
    "projectWeights": {
      "project-a": 2,  // Gets 2x more resources
      "project-b": 1
    }
  }
}
```

Per project:
- project-a: CPU 33%, Memory 1365 MB
- project-b: CPU 17%, Memory 683 MB

#### 3. Priority-Based Allocation

```json
{
  "workspaceResourceLimits": {
    "strategy": "priority",
    "total_cpu_percent": 50,
    "total_memory_mb": 2048,
    "projectPriorities": {
      "project-a": 1,  // Critical
      "project-b": 2   // Standard
    }
  }
}
```

Critical projects get first allocation, then remainder shared equally.

### Monitoring Resource Usage

```bash
# View workspace resource metrics
devloop workspace metrics --workspace-dir .devloop-workspace

# View per-project resource usage
devloop status --workspace-dir .devloop-workspace --detailed

# Export resource metrics
devloop workspace export-metrics --format json --output metrics.json
```

---

## Coordination Strategies

### Event Coordination

When using shared event logging, synchronize events across projects:

```bash
# Query events across all projects
devloop audit query --workspace-dir .devloop-workspace --limit 100

# Filter events by project
devloop audit query --workspace-dir .devloop-workspace --project project-a

# Correlate events across projects
devloop audit correlate --workspace-dir .devloop-workspace
```

### Context Sharing

Optionally share context between projects:

```json
{
  "global": {
    "contextSharing": {
      "enabled": true,
      "sharedContextPath": ".devloop-workspace/shared-context",
      "projectContextPaths": {
        "project-a": "project-a/.devloop/context",
        "project-b": "project-b/.devloop/context"
      }
    }
  }
}
```

### Agent Coordination

Agents can coordinate across projects:

```json
{
  "agents": {
    "linter": {
      "enabled": true,
      "workspaceCoordination": {
        "enabled": true,
        "shareResults": true,
        "coordinationMode": "broadcast"
      }
    }
  }
}
```

Coordination modes:
- `broadcast`: Share findings across all projects
- `centralized`: Send findings to workspace aggregator
- `pairwise`: Coordinate only with specified projects
- `none`: No coordination (default)

### Dependencies Between Projects

Specify inter-project dependencies:

```json
{
  "projects": [
    {
      "name": "shared-lib",
      "path": "libs/shared",
      "dependents": []
    },
    {
      "name": "service-a",
      "path": "services/a",
      "dependencies": ["shared-lib"]
    },
    {
      "name": "service-b",
      "path": "services/b",
      "dependencies": ["shared-lib"]
    }
  ]
}
```

When `shared-lib` changes, agents run in service-a and service-b automatically.

---

## Testing Multi-Project Setups

### Creating a Test Workspace

```bash
#!/bin/bash
# Create test workspace structure
mkdir -p workspace/{projects/a,projects/b,.devloop-workspace}

# Initialize workspace
devloop workspace init workspace/.devloop-workspace

# Initialize each project
cd workspace/projects/a
devloop init .

cd ../b
devloop init .

# Verify setup
devloop workspace list-projects ../../.devloop-workspace
```

### Running Multi-Project Tests

```bash
# Run all tests for all projects
devloop workspace test --workspace-dir .devloop-workspace

# Run tests for specific project
devloop workspace test --workspace-dir .devloop-workspace --project project-a

# Run integration tests (cross-project)
devloop workspace test --workspace-dir .devloop-workspace --integration
```

### Concurrent Project Watching

```bash
# Terminal 1: Watch project-a
cd workspace/projects/a
devloop watch .

# Terminal 2: Watch project-b
cd workspace/projects/b
devloop watch .

# Terminal 3: Monitor workspace
devloop workspace monitor --workspace-dir ../.devloop-workspace
```

### Performance Testing

```bash
# Benchmark multi-project setup
devloop workspace benchmark --workspace-dir .devloop-workspace --duration 300

# Stress test with 100k files
devloop workspace stress-test --workspace-dir .devloop-workspace --file-count 100000
```

---

## Troubleshooting

### Common Issues

#### Issue: Agents running in one project interfere with another

**Solution:** Use independent project configurations with separate resource limits.

```bash
# Verify project isolation
devloop status --workspace-dir .devloop-workspace --project project-a
devloop status --workspace-dir .devloop-workspace --project project-b
```

#### Issue: Workspace events.db growing too large

**Solution:** Enable event rotation and cleanup.

```json
{
  "global": {
    "eventLogRotation": {
      "enabled": true,
      "maxSizeBytes": 104857600,  // 100MB
      "maxAgedays": 30,
      "maxBackups": 3
    }
  }
}
```

#### Issue: Resource limits not being enforced

**Solution:** Check workspace configuration and verify daemon is running.

```bash
# Check configuration
devloop workspace validate --workspace-dir .devloop-workspace

# Verify daemon health
devloop workspace status --workspace-dir .devloop-workspace --detailed

# Restart workspace daemon
devloop workspace stop --workspace-dir .devloop-workspace
devloop workspace watch --workspace-dir .devloop-workspace
```

#### Issue: Cross-project coordination not working

**Solution:** Verify event bus is properly configured.

```bash
# Check event coordination status
devloop workspace events --workspace-dir .devloop-workspace --status

# Enable debug logging
devloop watch . --workspace-dir ../.devloop-workspace --verbose
```

### Debugging Commands

```bash
# View workspace configuration
devloop workspace config --workspace-dir .devloop-workspace

# Export diagnostic data
devloop workspace export-diagnostics --workspace-dir .devloop-workspace --output diagnostics.tar.gz

# Validate all project configurations
devloop workspace validate-all --workspace-dir .devloop-workspace

# Check for configuration conflicts
devloop workspace check-conflicts --workspace-dir .devloop-workspace

# View resource allocation
devloop workspace resources --workspace-dir .devloop-workspace --detailed
```

### Log Analysis

```bash
# View workspace-level logs
tail -f .devloop-workspace/devloop.log

# View project-specific logs
tail -f projects/a/.devloop/devloop.log

# Correlate logs across projects
devloop workspace logs --workspace-dir .devloop-workspace --correlate --output correlated.log
```

---

## Best Practices

### For Single Projects

1. ✅ Keep `.devloop` directory in git (track `agents.json` and `.gitignore`)
2. ✅ Commit configuration changes with code changes
3. ✅ Review `.devloop/agents.json` in PRs
4. ✅ Document agent configuration in README

### For Multi-Project Monorepos

1. ✅ Use workspace-level configuration for shared defaults
2. ✅ Allow project-level overrides for specific needs
3. ✅ Centralize event logging for cross-project visibility
4. ✅ Set workspace-wide resource limits
5. ✅ Document workspace structure in root README
6. ✅ Keep `.devloop-workspace` in git
7. ✅ Use `devloop workspace` commands instead of individual `devloop` commands

### For Coordinated Workflows

1. ✅ Enable event sharing only when necessary
2. ✅ Use project dependencies to manage ordering
3. ✅ Monitor resource usage with workspace metrics
4. ✅ Test agent coordination before enabling in production
5. ✅ Document coordination strategy in AGENTS.md

### Resource Management

1. ✅ Set total workspace CPU limit to 50-70% of available
2. ✅ Set total workspace memory limit to 25-50% of available
3. ✅ Monitor metrics regularly with `devloop workspace metrics`
4. ✅ Adjust limits based on actual usage patterns
5. ✅ Use weight-based allocation for services with different requirements

---

## Migration Guide

### Single → Multi-Project (Independent Mode)

```bash
# 1. Existing single project setup
cd workspace
ls -la
# .devloop/
# project-a/
# project-b/

# 2. Initialize each project separately
cd project-a
devloop init .

cd ../project-b
devloop init .

# 3. Verify each project works independently
cd ../project-a
devloop watch .
```

### Single → Multi-Project (Workspace Mode)

```bash
# 1. Backup existing .devloop configurations
cp -r project-a/.devloop project-a/.devloop.backup
cp -r project-b/.devloop project-b/.devloop.backup

# 2. Create workspace configuration
mkdir .devloop-workspace
devloop workspace init .devloop-workspace

# 3. Update project configurations to reference workspace
devloop init project-a --workspace-dir .devloop-workspace
devloop init project-b --workspace-dir .devloop-workspace

# 4. Verify migration
devloop workspace validate .devloop-workspace
devloop workspace list-projects .devloop-workspace
```

---

## Examples

### Example 1: Small Team with Two Services

```
monorepo/
├── .devloop-workspace/
│   └── workspace.json
├── services/
│   ├── api/
│   │   └── .devloop/
│   │       └── agents.json
│   └── web/
│       └── .devloop/
│           └── agents.json
```

**Setup:**
```bash
devloop workspace init .devloop-workspace
devloop init services/api --workspace-dir .devloop-workspace
devloop init services/web --workspace-dir .devloop-workspace
```

### Example 2: Large Monorepo with Microservices

```
monorepo/
├── .devloop-workspace/
│   ├── workspace.json
│   └── shared-context/
├── services/
│   ├── auth/
│   ├── payments/
│   ├── notifications/
│   └── ... (10+ services)
└── libs/
    ├── shared-utils/
    └── database/
```

**Resource Allocation:**
```json
{
  "workspaceResourceLimits": {
    "strategy": "weighted",
    "total_cpu_percent": 60,
    "projectWeights": {
      "auth": 2,
      "payments": 2,
      "notifications": 1,
      "default": 1
    }
  }
}
```

### Example 3: CI/CD with Coordinated Testing

```bash
#!/bin/bash
# CI script for workspace
cd workspace

# Run all project tests
devloop workspace test --workspace-dir .devloop-workspace

# Check all projects pass linting
devloop workspace lint --workspace-dir .devloop-workspace

# Generate coverage report across all projects
devloop workspace coverage --workspace-dir .devloop-workspace --output coverage.html
```

---

## See Also

- [Configuration Guide](./configuration.md) — Full configuration reference
- [Architecture Guide](./architecture.md) — System design
- [Monorepo Setup Guide](./MONOREPO_SETUP.md) — Specific monorepo recommendations
