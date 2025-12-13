# Large Repository Optimization Guide

Comprehensive guide for running DevLoop on large codebases with 10k+ files, optimizing filesystem watching, exclusion patterns, and monorepo setups.

## Overview

Running DevLoop on large repositories requires careful configuration to avoid filesystem watching overhead and I/O bottlenecks. This guide covers:

- Smart exclusion filtering
- Filesystem optimization strategies
- Monorepo configuration
- Performance monitoring for large repos
- Testing with 100k+ file projects

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Filesystem Exclusions](#filesystem-exclusions)
3. [Smart Filtering](#smart-filtering)
4. [Monorepo Configuration](#monorepo-configuration)
5. [Large Repo Benchmarks](#large-repo-benchmarks)
6. [Performance Optimization](#performance-optimization)
7. [Monitoring Large Repos](#monitoring-large-repos)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### For Large Repos (10k-100k files)

```bash
# Initialize with large-repo preset
devloop init /path/to/project --repo-size large

# This configures:
# - Smart exclusion patterns
# - Optimized debounce settings
# - Reduced concurrent agents
# - File count warnings
```

### For Monorepos (multiple projects)

```bash
# Initialize workspace for monorepo
devloop workspace init .devloop-workspace --for-monorepo

# Each project gets optimized settings
devloop init services/api --workspace-dir ../.devloop-workspace
devloop init services/web --workspace-dir ../.devloop-workspace
```

---

## Filesystem Exclusions

### Default Exclusions

```json
{
  "fileSystemWatcher": {
    "exclusions": [
      ".git/**",
      ".gitignore",
      ".github/**",
      ".devloop/**",
      "node_modules/**",
      "__pycache__/**",
      ".pytest_cache/**",
      ".mypy_cache/**",
      "venv/**",
      ".venv/**",
      "build/**",
      "dist/**",
      "*.egg-info/**",
      ".tox/**",
      "coverage/**",
      ".coverage",
      "*.pyc",
      "*.o",
      "*.so",
      "target/**",
      "vendor/**",
      ".bundle/**"
    ]
  }
}
```

### Project-Specific Exclusions

```json
{
  "fileSystemWatcher": {
    "projectExclusions": {
      "Python": [
        "venv/**",
        ".venv/**",
        "__pycache__/**",
        ".pytest_cache/**",
        ".mypy_cache/**",
        "*.egg-info/**"
      ],
      "Node": [
        "node_modules/**",
        ".next/**",
        "dist/**",
        "build/**"
      ],
      "Rust": [
        "target/**",
        ".cargo/**"
      ]
    }
  }
}
```

### Custom Exclusions

```json
{
  "fileSystemWatcher": {
    "exclusions": [
      ".git/**",
      "node_modules/**",
      "build/**",
      "dist/**",
      ".cache/**",
      "vendor/**",
      "public/uploads/**",
      "tmp/**",
      "*.min.js",
      "*.min.css",
      "docs/generated/**"
    ],
    "exclusionPatterns": [
      "**/*test*/**",
      "**/*.tmp",
      "**/.*"
    ]
  }
}
```

### Negation (Re-include Excluded Files)

Include specific files in excluded directories:

```json
{
  "fileSystemWatcher": {
    "exclusions": [
      "node_modules/**"
    ],
    "inclusions": [
      "node_modules/my-local-package/**"
    ]
  }
}
```

---

## Smart Filtering

### File Count Monitoring

```json
{
  "fileSystemWatcher": {
    "monitoring": {
      "enabled": true,
      "fileCountWarning": 50000,
      "fileCountCritical": 200000,
      "checkInterval": 300
    }
  }
}
```

Warns when:
- File count exceeds 50k (warning)
- File count exceeds 200k (critical - consider splitting)

### Directory Size Limits

```json
{
  "fileSystemWatcher": {
    "directorySizeLimits": {
      "enabled": true,
      "warningThresholdMB": 500,
      "criticalThresholdMB": 2000,
      "ignored": ["node_modules", "build", ".git"]
    }
  }
}
```

### Selective Watching

Watch only specific directories:

```json
{
  "fileSystemWatcher": {
    "watchMode": "selective",
    "watchPaths": [
      "src/**",
      "tests/**",
      "lib/**"
    ],
    "excludeFromWatchPaths": [
      "src/generated/**",
      "src/vendor/**"
    ]
  }
}
```

### Pattern-Based Filtering

```json
{
  "fileSystemWatcher": {
    "filePatterns": {
      "watch": [
        "**/*.ts",
        "**/*.tsx",
        "**/*.py",
        "**/*.json",
        "**/*.yaml",
        "**/*.toml"
      ],
      "ignore": [
        "**/*.min.js",
        "**/*.lock",
        "**/*.snapshot"
      ]
    }
  }
}
```

---

## Monorepo Configuration

### Workspace Structure for Monorepos

```
monorepo/
├── .devloop-workspace/
│   ├── workspace.json
│   └── shared-exclusions.json
├── packages/
│   ├── core/
│   │   └── .devloop/agents.json
│   ├── ui/
│   │   └── .devloop/agents.json
│   └── api/
│       └── .devloop/agents.json
└── services/
    ├── auth/
    │   └── .devloop/agents.json
    └── payment/
        └── .devloop/agents.json
```

### Shared Exclusions

**`.devloop-workspace/shared-exclusions.json`**

```json
{
  "global": [
    ".git/**",
    ".github/**",
    ".devloop/**",
    ".devloop-workspace/**"
  ],
  "byLanguage": {
    "node": [
      "node_modules/**",
      ".next/**",
      "dist/**",
      "build/**"
    ],
    "python": [
      "venv/**",
      "__pycache__/**",
      ".pytest_cache/**"
    ]
  },
  "largeDirectories": [
    "docs/**",
    "public/**",
    "coverage/**"
  ]
}
```

**Workspace Configuration:**

```json
{
  "fileSystemWatcher": {
    "sharedExclusions": ".devloop-workspace/shared-exclusions.json",
    "perProjectExclusions": {}
  }
}
```

### Per-Service Configuration

**`packages/core/.devloop/agents.json`**

```json
{
  "fileSystemWatcher": {
    "watchMode": "selective",
    "watchPaths": ["src/**", "tests/**"],
    "excludePatterns": [
      "src/generated/**",
      "*.snapshot"
    ]
  }
}
```

### Dependency-Based Watching

Watch related projects when dependencies change:

```json
{
  "fileSystemWatcher": {
    "dependencyWatching": {
      "enabled": true,
      "watchDependents": true,
      "maxDepth": 2
    }
  },
  "projects": [
    {
      "name": "api",
      "path": "services/api",
      "dependencies": ["packages/core", "packages/utils"]
    }
  ]
}
```

When `packages/core` changes, the `api` service's agents automatically run.

---

## Large Repo Benchmarks

### File Count Impact

**Baseline: 1,000 files**
- Initial scan: 150ms
- Watch overhead: <5% CPU
- Memory footprint: 50MB

**10,000 files**
- Initial scan: 800ms
- Watch overhead: 8-12% CPU
- Memory footprint: 150MB
- Recommendation: Use selective watching

**50,000 files**
- Initial scan: 4s
- Watch overhead: 15-20% CPU
- Memory footprint: 400MB
- Recommendation: Reduce debounce, enable exclusions

**100,000 files**
- Initial scan: 12s
- Watch overhead: 25-35% CPU
- Memory footprint: 800MB+
- Recommendation: Split into multiple projects

**200,000+ files**
- Not recommended: Causes significant overhead
- Solution: Split into separate workspaces or use monorepo mode

### Recommended Configuration by Size

#### 1k-10k files

```json
{
  "fileSystemWatcher": {
    "debounceMs": 300,
    "batchSize": 20,
    "sampleRate": 1.0
  }
}
```

#### 10k-50k files

```json
{
  "fileSystemWatcher": {
    "debounceMs": 500,
    "batchSize": 10,
    "sampleRate": 1.0,
    "smartExclusions": true
  }
}
```

#### 50k-100k files

```json
{
  "fileSystemWatcher": {
    "debounceMs": 1000,
    "batchSize": 5,
    "sampleRate": 0.7,
    "selectiveWatching": true,
    "watchPaths": ["src/**", "lib/**"]
  }
}
```

#### 100k+ files

```json
{
  "fileSystemWatcher": {
    "debounceMs": 2000,
    "batchSize": 3,
    "sampleRate": 0.5,
    "selectiveWatching": true,
    "watchPaths": ["src/**"],
    "indexing": {
      "enabled": true,
      "updateInterval": 60000
    }
  }
}
```

---

## Performance Optimization

### Enable Filesystem Indexing

For very large repos, use filesystem indexing:

```json
{
  "fileSystemWatcher": {
    "indexing": {
      "enabled": true,
      "updateInterval": 60000,
      "incremental": true,
      "persistIndex": true
    }
  }
}
```

The index speeds up:
- Change detection
- File pattern matching
- Dependency graph building

### Incremental Watching

Only watch changed files:

```json
{
  "fileSystemWatcher": {
    "incrementalMode": {
      "enabled": true,
      "trackingFile": ".devloop-workspace/.file-tracker"
    }
  }
}
```

### Debounce Optimization

For large repos, increase debounce to allow batching:

```json
{
  "fileSystemWatcher": {
    "adaptiveDebounce": {
      "enabled": true,
      "minMs": 300,
      "maxMs": 3000,
      "adjustmentFactor": 1.2
    }
  }
}
```

Auto-increases debounce if processing takes longer than expected.

### Memory Optimization

Limit memory for watching:

```json
{
  "fileSystemWatcher": {
    "memoryLimits": {
      "maxWatcherMemory": "500MB",
      "cacheSize": 10000,
      "cacheTTL": 60000
    }
  }
}
```

### Disk I/O Optimization

```json
{
  "fileSystemWatcher": {
    "diskOptimization": {
      "enableReadAhead": true,
      "readAheadSize": 65536,
      "bufferSize": 16384,
      "asyncReads": true
    }
  }
}
```

---

## Monitoring Large Repos

### File Count Status

```bash
# Check current file count
devloop status --repo-stats

# Output:
# Repository Statistics
# ═══════════════════════════════════
# Total Files: 47,392
# Watched Directories: 12
# Excluded Files: 38,291 (80.8%)
# Watch Overhead: 12.3% CPU
# Watcher Memory: 245MB
# 
# Largest Directories:
#  1. node_modules: 8,392 files (excluded)
#  2. .git: 2,145 files (excluded)
#  3. src: 342 files (watched)
```

### Monitor Watch Performance

```bash
# Watch performance metrics
devloop telemetry metrics --filter "watch.*"

# Output:
# Watch Performance
# ═════════════════════════════════════
# Files Watched: 9,101
# Change Events/min: 234
# Avg Debounce Time: 542ms
# Batch Size: 15
# CPU Usage: 8.2%
# Memory: 234MB
```

### Detect Large Directories

```bash
# Find largest directories not being excluded
devloop optimize scan-repo

# Output:
# Large Directories (not excluded)
# ════════════════════════════════════════
# src/generated/: 5,234 files (542MB)
#   → Consider adding to exclusions
# 
# docs/api/: 2,123 files (124MB)
#   → Consider enabling doc watching only in specific agents
# 
# data/samples/: 1,892 files (234MB)
#   → Consider adding to exclusions
```

---

## Practical Examples

### Example 1: Django Project (50k files)

```json
{
  "fileSystemWatcher": {
    "watchMode": "selective",
    "watchPaths": ["myapp/**", "tests/**"],
    "exclusions": [
      ".git/**",
      ".venv/**",
      "__pycache__/**",
      ".pytest_cache/**",
      ".mypy_cache/**",
      ".tox/**",
      "htmlcov/**",
      "*.egg-info/**",
      "node_modules/**"
    ],
    "debounceMs": 1000,
    "batchSize": 10,
    "monitoring": {
      "fileCountWarning": 50000
    }
  }
}
```

### Example 2: Monorepo (TypeScript, 100k+ files)

**`.devloop-workspace/workspace.json`**

```json
{
  "projects": [
    {
      "name": "core",
      "path": "packages/core",
      "watchPaths": ["src/**", "tests/**"]
    },
    {
      "name": "api",
      "path": "services/api",
      "watchPaths": ["src/**", "tests/**"],
      "dependencies": ["packages/core"]
    }
  ],
  "fileSystemWatcher": {
    "globalExclusions": [
      ".git/**",
      "node_modules/**",
      "dist/**",
      "build/**",
      ".next/**"
    ],
    "indexing": {
      "enabled": true,
      "updateInterval": 60000
    },
    "debounceMs": 500
  }
}
```

### Example 3: Microservices Monorepo (200+ services)

```json
{
  "fileSystemWatcher": {
    "watchMode": "selective",
    "watchPaths": ["services/*/src/**"],
    "exclusions": [
      ".git/**",
      "**/node_modules/**",
      "**/venv/**",
      "**/build/**",
      "**/dist/**",
      "terraform/**",
      "infrastructure/**"
    ],
    "smartExclusions": {
      "enabled": true,
      "autoExcludeLargeDirectories": true,
      "threshold": "500MB"
    },
    "indexing": {
      "enabled": true,
      "incrementalUpdates": true
    }
  }
}
```

---

## Testing Large Repos

### Create Test Repository

```bash
#!/bin/bash
# Create test repo with 100k files

mkdir test-repo
cd test-repo
git init

# Generate files
for i in {1..1000}; do
  mkdir -p "src/module-$i"
  for j in {1..100}; do
    echo "# File $j" > "src/module-$i/file-$j.py"
  done
done

# Create some large directories
mkdir -p vendor
for i in {1..5000}; do
  echo "# dependency" > "vendor/dep-$i.py"
done

git add .
git commit -m "Initial 100k file repo"
```

### Benchmark DevLoop

```bash
# Measure initial scan time
time devloop init . --no-watch

# Measure watch performance
devloop watch . --foreground --stats

# Monitor for 5 minutes
devloop telemetry metrics --duration 300 --output metrics.json

# Analyze results
devloop optimize analyze --metrics metrics.json
```

### Profile Watch Overhead

```bash
# Compare watch overhead
devloop optimize profile \
  --baseline "without-devloop.json" \
  --active "with-devloop.json" \
  --metric cpu,memory,disk-io

# Output:
# Watch Overhead Analysis
# ═════════════════════════════════════
# CPU: +12.3%
# Memory: +245MB
# Disk I/O: +8.5%
```

---

## Troubleshooting

### Issue: Watch Overhead Too High

**Symptoms:**
- CPU constantly 20%+
- System slow
- High disk I/O

**Solutions:**
1. Check exclusions: `devloop optimize scan-repo`
2. Enable selective watching
3. Increase debounce
4. Reduce concurrent agents

### Issue: Slow File Change Detection

**Symptoms:**
- Changes take 5+ seconds to detect
- Agent runs seem delayed

**Solutions:**
1. Reduce debounce (but watch CPU)
2. Enable filesystem indexing
3. Reduce batch size
4. Check disk performance

### Issue: Out of Memory

**Symptoms:**
- Memory grows to 1GB+
- System starts swapping
- DevLoop crashes

**Solutions:**
1. Check for memory leaks: `devloop health --memory`
2. Reduce cache size
3. Enable selective watching
4. Enable incremental mode
5. Reduce batch size

### Issue: Git Repository Causes Problems

**Symptoms:**
- DevLoop slow when .git directory large
- High CPU when git operations running

**Solutions:**
1. Always exclude .git: `".git/**"` in exclusions
2. Consider shallow clone for test repos
3. Use git worktrees instead of submodules

---

## Best Practices

1. **Always exclude build artifacts**: `build/**`, `dist/**`
2. **Always exclude package managers**: `node_modules/**`, `venv/**`, `vendor/**`
3. **Test exclusions**: Run `devloop optimize scan-repo` after config changes
4. **Use selective watching**: Only watch source directories
5. **Enable monitoring**: Set `fileCountWarning` for your repo size
6. **Start conservative**: Use larger debounce, then reduce
7. **Profile first**: Run benchmarks before tuning
8. **Document rationale**: Comment why exclusions are needed
9. **Monorepo mode**: Use workspace configuration for multiple services
10. **Regular review**: Re-evaluate exclusions as codebase grows

---

## See Also

- [Multi-Project Setup](./MULTI_PROJECT_SETUP.md)
- [Performance Tuning](./PERFORMANCE_TUNING.md)
- [Resource Sharing](./RESOURCE_SHARING.md)
- [Configuration Guide](./configuration.md)
