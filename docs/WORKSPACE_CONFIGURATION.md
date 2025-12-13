# Workspace Configuration Reference

Complete reference for workspace-level configuration in multi-project setups.

## Overview

Workspace configuration manages multiple DevLoop projects with centralized settings, resource limits, and coordination policies.

## Configuration File

**Location:** `.devloop-workspace/workspace.json`

```json
{
  "type": "workspace",
  "version": "1.0",
  "workspace_name": "my-workspace",
  "workspace_root": "/absolute/path/to/workspace",
  "projects": [],
  "global": {},
  "agent_defaults": {},
  "resource_sharing": {},
  "coordination": {}
}
```

---

## Top-Level Properties

### type

**Type:** `"workspace"` | `"standalone"`

Identifies this as a workspace configuration.

```json
{
  "type": "workspace"
}
```

### version

**Type:** `string` (semantic version)

Configuration schema version for migrations.

```json
{
  "version": "1.0"
}
```

Currently supported: `1.0`

### workspace_name

**Type:** `string`

Human-readable name for the workspace.

```json
{
  "workspace_name": "my-monorepo"
}
```

### workspace_root

**Type:** `string` (absolute path)

Root directory of the workspace. Auto-populated during `devloop workspace init`.

```json
{
  "workspace_root": "/home/user/monorepo"
}
```

---

## Projects

### projects

**Type:** `array`

List of projects in this workspace.

```json
{
  "projects": [
    {
      "name": "project-a",
      "path": "services/a",
      "enabled": true
    }
  ]
}
```

### Project Properties

#### name

**Type:** `string`

Unique identifier for the project.

```json
{
  "name": "api-service"
}
```

#### path

**Type:** `string` (relative to workspace_root)

Path to project directory.

```json
{
  "path": "services/api"
}
```

#### enabled

**Type:** `boolean` (default: `true`)

Whether agents run for this project.

```json
{
  "enabled": true
}
```

Disable without removing:
```json
{
  "enabled": false
}
```

#### config_override

**Type:** `string` (relative path, optional)

Path to project-specific agent configuration.

```json
{
  "config_override": "services/api/.devloop/agents.json"
}
```

If not specified, uses workspace defaults.

#### description

**Type:** `string` (optional)

Human-readable description.

```json
{
  "description": "API backend service"
}
```

#### tags

**Type:** `array` (optional)

Labels for categorization.

```json
{
  "tags": ["backend", "critical", "rust"]
}
```

#### dependencies

**Type:** `array` (optional)

Other projects this project depends on.

```json
{
  "dependencies": ["shared-lib", "database"]
}
```

When a dependency changes, this project's agents run automatically.

#### priority

**Type:** `0-3` (default: `2`)

Resource allocation priority.
- `0`: Critical (always gets resources)
- `1`: High
- `2`: Normal (default)
- `3`: Low (deferred when system loaded)

```json
{
  "priority": 0
}
```

---

## Global Configuration

### global

**Type:** `object`

Workspace-wide settings.

```json
{
  "global": {
    "mode": "report-only",
    "maxConcurrentAgents": 10,
    "resourceLimits": {},
    "contextSharing": {},
    "eventLogging": {}
  }
}
```

### Global Properties

#### mode

**Type:** `"report-only"` | `"active"`

- `report-only`: Find and report issues only
- `active`: Apply auto-fixes (if enabled in agents)

```json
{
  "global": {
    "mode": "report-only"
  }
}
```

#### maxConcurrentAgents

**Type:** `integer` (default: `5`)

Maximum agents running simultaneously across all projects.

```json
{
  "global": {
    "maxConcurrentAgents": 10
  }
}
```

When limit reached, agents queue and wait for resources.

#### notification_level

**Type:** `"none"` | `"summary"` | `"detailed"` (default: `"summary"`)

How much to log/display.

```json
{
  "global": {
    "notification_level": "summary"
  }
}
```

#### contextStoreEnabled

**Type:** `boolean` (default: `true`)

Enable context store for all projects.

```json
{
  "global": {
    "contextStoreEnabled": true
  }
}
```

#### contextStorePath

**Type:** `string` (relative path)

Location for shared context data.

```json
{
  "global": {
    "contextStorePath": ".devloop-workspace/shared-context"
  }
}
```

#### eventLogPath

**Type:** `string` (relative path)

Location for centralized event log.

```json
{
  "global": {
    "eventLogPath": ".devloop-workspace/workspace-events.db"
  }
}
```

#### eventLogRotation

**Type:** `object`

Event log rotation settings.

```json
{
  "global": {
    "eventLogRotation": {
      "enabled": true,
      "maxSizeBytes": 104857600,
      "maxAgeDays": 30,
      "maxBackups": 3,
      "compress": true
    }
  }
}
```

**Properties:**
- `enabled`: Enable log rotation
- `maxSizeBytes`: Max size before rotation (default: 100MB)
- `maxAgeDays`: Delete logs older than this (default: 30)
- `maxBackups`: Keep this many backups (default: 3)
- `compress`: Compress rotated logs (default: true)

#### resourceLimits

**Type:** `object`

Global resource limits across all projects.

```json
{
  "global": {
    "resourceLimits": {
      "maxCpu": 50,
      "maxMemory": "2GB",
      "checkInterval": 10
    }
  }
}
```

**Properties:**
- `maxCpu`: Max CPU percentage (0-100)
- `maxMemory`: Max memory (bytes, KB, MB, GB)
- `checkInterval`: Check frequency in seconds

---

## Agent Defaults

### agent_defaults

**Type:** `object`

Default agent configuration inherited by all projects.

```json
{
  "agent_defaults": {
    "linter": {
      "enabled": true,
      "triggers": ["file:modified"]
    },
    "formatter": {
      "enabled": true
    }
  }
}
```

Projects can override defaults in their `.devloop/agents.json`.

---

## Resource Sharing

### resource_sharing

**Type:** `object`

How resources are allocated across projects.

```json
{
  "resource_sharing": {
    "strategy": "equal",
    "cpuLimit": 50,
    "memoryLimit": "2GB",
    "perProjectLimits": {}
  }
}
```

### Resource Sharing Strategies

#### equal

All projects get equal resources.

```json
{
  "resource_sharing": {
    "strategy": "equal"
  }
}
```

With 3 projects and 60% CPU:
- Each project: 20% CPU

#### weighted

Projects weighted by importance.

```json
{
  "resource_sharing": {
    "strategy": "weighted",
    "weights": {
      "auth-service": 2,
      "api-service": 2,
      "worker-service": 1
    }
  }
}
```

Total weights: 5
- auth-service: 40% CPU
- api-service: 40% CPU
- worker-service: 20% CPU

#### priority

Critical projects get priority.

```json
{
  "resource_sharing": {
    "strategy": "priority"
  }
}
```

Uses project `priority` field. Critical projects get first allocation.

#### fifo

First-to-run gets resources.

```json
{
  "resource_sharing": {
    "strategy": "fifo"
  }
}
```

First agent to start gets full resources.

#### custom

Manual per-project allocation.

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
      }
    }
  }
}
```

### cpuLimit

**Type:** `integer` (0-100)

Maximum total CPU percentage used across all projects.

```json
{
  "resource_sharing": {
    "cpuLimit": 50
  }
}
```

### memoryLimit

**Type:** `string` (bytes, KB, MB, GB)

Maximum total memory used across all projects.

```json
{
  "resource_sharing": {
    "memoryLimit": "2GB"
  }
}
```

---

## Coordination

### coordination

**Type:** `object`

How projects coordinate with each other.

```json
{
  "coordination": {
    "enabled": true,
    "eventSharing": true,
    "resultAggregation": true,
    "dependencyOrdering": true
  }
}
```

### Coordination Properties

#### enabled

**Type:** `boolean`

Enable inter-project coordination.

```json
{
  "coordination": {
    "enabled": true
  }
}
```

#### eventSharing

**Type:** `boolean`

Share events between projects for cross-project insights.

```json
{
  "coordination": {
    "eventSharing": true
  }
}
```

#### resultAggregation

**Type:** `boolean`

Aggregate findings across projects.

```json
{
  "coordination": {
    "resultAggregation": true
  }
}
```

#### dependencyOrdering

**Type:** `boolean`

Run agents in dependency order.

```json
{
  "coordination": {
    "dependencyOrdering": true
  }
}
```

When enabled:
1. Dependency projects run first
2. Dependent projects run after dependencies succeed
3. Independent projects run in parallel

#### changeDetection

**Type:** `"project" | "workspace"`

Scope of change detection.

```json
{
  "coordination": {
    "changeDetection": "workspace"
  }
}
```

- `"project"`: Only detect changes in same project
- `"workspace"`: Detect changes across all projects

#### changeNotification

**Type:** `boolean`

Notify other projects when this project changes.

```json
{
  "coordination": {
    "changeNotification": true
  }
}
```

---

## Complete Example

```json
{
  "type": "workspace",
  "version": "1.0",
  "workspace_name": "backend-monorepo",
  "workspace_root": "/home/user/backend",
  
  "projects": [
    {
      "name": "shared-lib",
      "path": "libs/shared",
      "enabled": true,
      "description": "Shared utilities library",
      "tags": ["library", "critical"],
      "priority": 0
    },
    {
      "name": "auth-service",
      "path": "services/auth",
      "enabled": true,
      "config_override": "services/auth/.devloop/agents.json",
      "description": "Authentication service",
      "tags": ["backend", "critical"],
      "dependencies": ["shared-lib"],
      "priority": 0
    },
    {
      "name": "api-service",
      "path": "services/api",
      "enabled": true,
      "description": "Main API service",
      "tags": ["backend"],
      "dependencies": ["shared-lib", "auth-service"],
      "priority": 1
    },
    {
      "name": "worker-service",
      "path": "services/worker",
      "enabled": true,
      "description": "Background job worker",
      "tags": ["backend"],
      "dependencies": ["shared-lib"],
      "priority": 2
    }
  ],
  
  "global": {
    "mode": "report-only",
    "maxConcurrentAgents": 8,
    "notification_level": "summary",
    "contextStoreEnabled": true,
    "contextStorePath": ".devloop-workspace/shared-context",
    "eventLogPath": ".devloop-workspace/workspace-events.db",
    "eventLogRotation": {
      "enabled": true,
      "maxSizeBytes": 104857600,
      "maxAgeDays": 30,
      "maxBackups": 3,
      "compress": true
    },
    "resourceLimits": {
      "maxCpu": 60,
      "maxMemory": "2GB",
      "checkInterval": 10
    }
  },
  
  "agent_defaults": {
    "linter": {
      "enabled": true,
      "triggers": ["file:modified"]
    },
    "formatter": {
      "enabled": true,
      "triggers": ["file:modified"]
    },
    "test-runner": {
      "enabled": true,
      "triggers": ["file:modified"]
    },
    "type-checker": {
      "enabled": true,
      "triggers": ["file:modified"]
    }
  },
  
  "resource_sharing": {
    "strategy": "weighted",
    "cpuLimit": 60,
    "memoryLimit": "2GB",
    "weights": {
      "shared-lib": 1,
      "auth-service": 2,
      "api-service": 2,
      "worker-service": 1
    }
  },
  
  "coordination": {
    "enabled": true,
    "eventSharing": true,
    "resultAggregation": true,
    "dependencyOrdering": true,
    "changeDetection": "workspace",
    "changeNotification": true
  }
}
```

---

## Migration from Project to Workspace

### Step 1: Create Workspace

```bash
mkdir .devloop-workspace
devloop workspace init .devloop-workspace
```

### Step 2: Update Projects

For each project, update `.devloop/agents.json`:

```json
{
  "workspace_dir": "../../.devloop-workspace",
  "project_name": "auth-service",
  "agents": {}
}
```

### Step 3: Define Workspace Configuration

Edit `.devloop-workspace/workspace.json` with all projects and settings.

### Step 4: Verify

```bash
devloop workspace validate .devloop-workspace
devloop workspace list-projects .devloop-workspace
```

---

## Validation

### Validate Workspace Configuration

```bash
devloop workspace validate .devloop-workspace
```

Checks:
- Valid JSON syntax
- Required properties present
- Project paths exist
- No circular dependencies
- Resource limits reasonable
- Config version compatible

### Validate Specific Project

```bash
devloop workspace validate-project .devloop-workspace --project auth-service
```

### Export Configuration

```bash
devloop workspace export-config .devloop-workspace --output config-backup.json
```

---

## Environment Variables

Override configuration with environment variables:

```bash
# Override workspace name
DEVLOOP_WORKSPACE_NAME=my-workspace devloop workspace status

# Override max concurrent agents
DEVLOOP_MAX_CONCURRENT_AGENTS=15 devloop watch .

# Override resource limits
DEVLOOP_MAX_CPU=80 devloop watch .
```

---

## See Also

- [Multi-Project Setup Guide](./MULTI_PROJECT_SETUP.md)
- [Configuration Guide](./configuration.md)
- [Architecture Guide](./architecture.md)
