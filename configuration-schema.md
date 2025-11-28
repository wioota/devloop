# Configuration Schema Reference

This document provides a complete reference for configuring the background agent system.

## Configuration File Locations

```
.claude/
├── agents.json              # Main agent configuration
├── events.json              # Event system configuration
├── agents/                  # Agent-specific configs
│   ├── linter.json
│   ├── test-runner.json
│   └── ...
├── scripts/                 # Custom agent scripts
└── templates/               # Agent templates
```

## Main Configuration: agents.json

### Complete Schema

```json
{
  "$schema": "https://dev-agents.dev/schema/v1/agents.schema.json",
  "version": "1.0.0",
  "enabled": true,
  "agents": {
    "agent-name": {
      "enabled": boolean,
      "priority": "low" | "normal" | "high" | "critical",
      "triggers": string[],
      "config": object,
      "timeout": number,
      "retries": number,
      "parallel": boolean
    }
  },
  "global": {
    "maxConcurrentAgents": number,
    "notificationLevel": "none" | "errors" | "summary" | "verbose",
    "resourceLimits": {
      "maxCpu": number,
      "maxMemory": string,
      "maxDisk": string
    },
    "logging": {
      "level": "debug" | "info" | "warn" | "error",
      "path": string,
      "rotate": boolean
    }
  },
  "eventSystem": {
    "collectors": object,
    "dispatcher": object,
    "store": object
  }
}
```

### Example Configuration

```json
{
  "version": "1.0.0",
  "enabled": true,
  "agents": {
    "linter": {
      "enabled": true,
      "priority": "high",
      "triggers": ["file:save", "git:pre-commit"],
      "config": {
        "debounce": 500,
        "filePatterns": ["**/*.{js,ts,jsx,tsx}"],
        "autoFix": true,
        "autoFixOnSave": true,
        "incrementalOnly": true,
        "linters": {
          "javascript": "eslint",
          "typescript": "eslint",
          "python": "ruff",
          "go": "golangci-lint"
        }
      },
      "timeout": 30000,
      "retries": 0,
      "parallel": true
    },
    "formatter": {
      "enabled": true,
      "priority": "normal",
      "triggers": ["file:save"],
      "config": {
        "formatOnSave": true,
        "formatOnCommit": false,
        "filePatterns": ["**/*.{js,ts,jsx,tsx,json,md,css,scss}"],
        "formatters": {
          "javascript": "prettier",
          "typescript": "prettier",
          "python": "black",
          "go": "gofmt",
          "rust": "rustfmt",
          "json": "prettier",
          "markdown": "prettier"
        }
      },
      "timeout": 10000,
      "retries": 1,
      "parallel": true
    },
    "testRunner": {
      "enabled": true,
      "priority": "normal",
      "triggers": ["file:save"],
      "config": {
        "watchMode": true,
        "relatedTestsOnly": true,
        "runOnSave": true,
        "parallelExecution": true,
        "maxParallel": 4,
        "coverage": false,
        "testFrameworks": {
          "javascript": "jest",
          "typescript": "jest",
          "python": "pytest",
          "go": "go test"
        },
        "testPatterns": {
          "javascript": "**/*.{test,spec}.{js,ts,jsx,tsx}",
          "python": "**/test_*.py",
          "go": "**/*_test.go"
        }
      },
      "timeout": 120000,
      "retries": 0,
      "parallel": true
    },
    "commitAssistant": {
      "enabled": true,
      "priority": "high",
      "triggers": ["git:pre-commit"],
      "config": {
        "format": "conventional",
        "analyzeContext": true,
        "maxLength": 72,
        "includeScope": true,
        "includeBody": true,
        "includeBreakingChanges": true,
        "templates": {
          "feat": "feat({scope}): {summary}\n\n{body}",
          "fix": "fix({scope}): {summary}\n\n{body}",
          "docs": "docs({scope}): {summary}",
          "refactor": "refactor({scope}): {summary}",
          "test": "test({scope}): {summary}",
          "chore": "chore({scope}): {summary}"
        }
      },
      "timeout": 15000,
      "retries": 0,
      "parallel": false
    },
    "docSync": {
      "enabled": true,
      "priority": "low",
      "triggers": ["file:save", "git:pre-commit"],
      "config": {
        "watchPaths": ["src/**/*.{js,ts,py}", "docs/**/*.md"],
        "verifyExamples": true,
        "checkApiDocs": true,
        "autoUpdate": false,
        "docPatterns": {
          "api": "docs/api/**/*.md",
          "guide": "docs/guides/**/*.md",
          "readme": "**/README.md"
        }
      },
      "timeout": 20000,
      "retries": 1,
      "parallel": true
    },
    "securityScanner": {
      "enabled": true,
      "priority": "critical",
      "triggers": ["file:save", "dependency:updated", "git:pre-push"],
      "config": {
        "scanDependencies": true,
        "scanCode": true,
        "scanSecrets": true,
        "secretPatterns": [
          "api[_-]?key",
          "password",
          "secret",
          "token",
          "aws[_-]?access",
          "private[_-]?key"
        ],
        "excludePatterns": [
          "**/test/**",
          "**/*.test.*",
          "**/*.spec.*",
          "**/mock/**"
        ],
        "severity": ["high", "critical"]
      },
      "timeout": 60000,
      "retries": 1,
      "parallel": true
    }
  },
  "global": {
    "maxConcurrentAgents": 5,
    "notificationLevel": "summary",
    "resourceLimits": {
      "maxCpu": 25,
      "maxMemory": "500MB",
      "maxDisk": "1GB"
    },
    "logging": {
      "level": "info",
      "path": ".claude/logs/agents.log",
      "rotate": true,
      "maxSize": "10MB",
      "maxFiles": 5
    },
    "cache": {
      "enabled": true,
      "path": ".claude/cache",
      "maxSize": "100MB",
      "ttl": 3600
    }
  },
  "eventSystem": {
    "collectors": {
      "filesystem": {
        "enabled": true,
        "watchPaths": ["src/**/*", "tests/**/*", "docs/**/*"],
        "ignorePaths": [
          "node_modules/**",
          "dist/**",
          "build/**",
          ".git/**",
          "**/*.log",
          ".claude/**"
        ],
        "events": ["create", "modify", "delete", "rename"],
        "debounce": 100
      },
      "git": {
        "enabled": true,
        "hooks": [
          "pre-commit",
          "post-commit",
          "pre-push",
          "post-merge",
          "post-checkout"
        ],
        "async": false,
        "timeout": 30000
      },
      "process": {
        "enabled": true,
        "commands": [
          "npm run build",
          "npm test",
          "npm run lint"
        ],
        "captureOutput": true,
        "parseOutput": true
      }
    },
    "dispatcher": {
      "queueSize": 1000,
      "processingMode": "parallel",
      "maxWorkers": 4,
      "priorityLevels": 4
    },
    "store": {
      "enabled": true,
      "storage": "sqlite",
      "path": ".claude/events.db",
      "retention": {
        "days": 30,
        "maxEvents": 100000
      },
      "replay": {
        "enabled": true,
        "onStartup": false
      }
    }
  }
}
```

## Agent-Specific Configuration Schemas

### Linter Agent

```typescript
interface LinterConfig {
  debounce: number;                    // Debounce delay in ms
  filePatterns: string[];              // Glob patterns for files to lint
  autoFix: boolean;                    // Enable auto-fixing
  autoFixOnSave: boolean;              // Auto-fix on save
  incrementalOnly: boolean;            // Only lint changed lines
  linters: Record<string, string>;     // Language -> linter mapping
  rules?: Record<string, any>;         // Override linter rules
  ignorePatterns?: string[];           // Patterns to ignore
}
```

### Formatter Agent

```typescript
interface FormatterConfig {
  formatOnSave: boolean;
  formatOnCommit: boolean;
  filePatterns: string[];
  formatters: Record<string, string>;
  options?: Record<string, any>;       // Formatter-specific options
  ignorePatterns?: string[];
}
```

### Test Runner Agent

```typescript
interface TestRunnerConfig {
  watchMode: boolean;
  relatedTestsOnly: boolean;           // Only run tests related to changed files
  runOnSave: boolean;
  parallelExecution: boolean;
  maxParallel: number;
  coverage: boolean;
  testFrameworks: Record<string, string>;
  testPatterns: Record<string, string>;
  coverageThresholds?: {
    statements: number;
    branches: number;
    functions: number;
    lines: number;
  };
  bail?: boolean;                      // Stop on first failure
  verbose?: boolean;
}
```

### Security Scanner Agent

```typescript
interface SecurityScannerConfig {
  scanDependencies: boolean;
  scanCode: boolean;
  scanSecrets: boolean;
  secretPatterns: string[];            // Regex patterns for secrets
  excludePatterns: string[];
  severity: ('low' | 'medium' | 'high' | 'critical')[];
  databases?: string[];                // Vulnerability databases to check
  customRules?: string;                // Path to custom rules file
}
```

### Commit Assistant Agent

```typescript
interface CommitAssistantConfig {
  format: 'conventional' | 'semantic' | 'custom';
  analyzeContext: boolean;
  maxLength: number;
  includeScope: boolean;
  includeBody: boolean;
  includeBreakingChanges: boolean;
  templates: Record<string, string>;   // Type -> template mapping
  scopes?: string[];                   // Allowed scopes
  customTemplate?: string;
}
```

### Doc Sync Agent

```typescript
interface DocSyncConfig {
  watchPaths: string[];
  verifyExamples: boolean;             // Verify code examples in docs
  checkApiDocs: boolean;
  autoUpdate: boolean;
  docPatterns: Record<string, string>;
  linkCheck?: boolean;                 // Check for broken links
  spellCheck?: boolean;
}
```

### Dependency Updater Agent

```typescript
interface DependencyUpdaterConfig {
  checkFrequency: 'hourly' | 'daily' | 'weekly';
  autoUpdate: 'none' | 'patch' | 'minor' | 'all';
  groupUpdates: boolean;               // Group related updates
  excludePackages: string[];
  securityOnly: boolean;
  createPR: boolean;                   // Create PR for updates
  prLabels?: string[];
}
```

### Performance Profiler Agent

```typescript
interface PerformanceProfilerConfig {
  regressionThreshold: number;         // % threshold for regression
  baselineBranch: string;
  autoBenchmark: boolean;
  trackMetrics: ('cpu' | 'memory' | 'duration' | 'network')[];
  samplingInterval?: number;           // Sampling interval in ms
  flamegraph?: boolean;                // Generate flamegraphs
}
```

## Global Configuration Options

### Resource Limits

```typescript
interface ResourceLimits {
  maxCpu: number;                      // Max CPU % per agent
  maxMemory: string;                   // Max memory (e.g., "500MB")
  maxDisk: string;                     // Max disk usage
  timeout?: number;                    // Global timeout in ms
}
```

### Logging Configuration

```typescript
interface LoggingConfig {
  level: 'debug' | 'info' | 'warn' | 'error';
  path: string;
  rotate: boolean;
  maxSize: string;
  maxFiles: number;
  format?: 'json' | 'text';
}
```

### Notification Configuration

```typescript
interface NotificationConfig {
  level: 'none' | 'errors' | 'summary' | 'verbose';
  channels: ('console' | 'file' | 'desktop' | 'webhook')[];
  webhookUrl?: string;
  desktop?: {
    enabled: boolean;
    sound: boolean;
    urgentOnly: boolean;
  };
}
```

### Cache Configuration

```typescript
interface CacheConfig {
  enabled: boolean;
  path: string;
  maxSize: string;
  ttl: number;                         // Time to live in seconds
  strategy?: 'lru' | 'lfu' | 'fifo';
}
```

## Event System Configuration

### Filesystem Collector

```json
{
  "enabled": true,
  "watchPaths": ["src/**/*"],
  "ignorePaths": ["node_modules/**", ".git/**"],
  "events": ["create", "modify", "delete", "rename"],
  "debounce": 100,
  "recursive": true,
  "followSymlinks": false
}
```

### Git Collector

```json
{
  "enabled": true,
  "hooks": ["pre-commit", "post-commit", "pre-push"],
  "async": false,
  "timeout": 30000,
  "installHooks": true,
  "hookPath": ".git/hooks"
}
```

### Process Collector

```json
{
  "enabled": true,
  "commands": ["npm run build"],
  "captureOutput": true,
  "parseOutput": true,
  "outputParsers": {
    "npm": "npm-parser",
    "jest": "jest-parser"
  }
}
```

### Event Dispatcher

```json
{
  "queueSize": 1000,
  "processingMode": "parallel",
  "maxWorkers": 4,
  "priorityLevels": 4,
  "batchSize": 10,
  "batchWindow": 1000
}
```

### Event Store

```json
{
  "enabled": true,
  "storage": "sqlite",
  "path": ".claude/events.db",
  "retention": {
    "days": 30,
    "maxEvents": 100000,
    "compress": true
  },
  "replay": {
    "enabled": true,
    "onStartup": false,
    "filterTypes": ["file:save", "git:commit"]
  }
}
```

## Environment Variables

```bash
# Agent system
CLAUDE_AGENTS_ENABLED=true
CLAUDE_AGENTS_CONFIG_PATH=.claude/agents.json
CLAUDE_AGENTS_LOG_LEVEL=info

# Resource limits
CLAUDE_AGENTS_MAX_CPU=25
CLAUDE_AGENTS_MAX_MEMORY=500M
CLAUDE_AGENTS_MAX_CONCURRENT=5

# Event system
CLAUDE_AGENTS_EVENT_STORE_PATH=.claude/events.db
CLAUDE_AGENTS_EVENT_RETENTION_DAYS=30

# Notifications
CLAUDE_AGENTS_NOTIFICATION_LEVEL=summary
CLAUDE_AGENTS_WEBHOOK_URL=https://example.com/webhook
```

## Configuration Validation

### JSON Schema

The configuration is validated against a JSON schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
    },
    "enabled": {
      "type": "boolean"
    },
    "agents": {
      "type": "object",
      "additionalProperties": {
        "$ref": "#/definitions/agent"
      }
    }
  },
  "required": ["version", "agents"],
  "definitions": {
    "agent": {
      "type": "object",
      "properties": {
        "enabled": {"type": "boolean"},
        "priority": {
          "enum": ["low", "normal", "high", "critical"]
        },
        "triggers": {
          "type": "array",
          "items": {"type": "string"}
        },
        "config": {"type": "object"},
        "timeout": {"type": "number", "minimum": 0},
        "retries": {"type": "number", "minimum": 0},
        "parallel": {"type": "boolean"}
      },
      "required": ["enabled", "triggers"]
    }
  }
}
```

### Validation CLI

```bash
# Validate configuration
dev-agents config validate

# Show current configuration
dev-agents config show

# Edit configuration
dev-agents config edit

# Reset to defaults
dev-agents config reset
```

## Configuration Precedence

1. Command-line arguments
2. Environment variables
3. Project configuration (`.claude/agents.json`)
4. User configuration (`~/.claude/agents.json`)
5. System configuration (`/etc/claude/agents.json`)
6. Default configuration

## Configuration Examples

### Minimal Configuration

```json
{
  "version": "1.0.0",
  "enabled": true,
  "agents": {
    "linter": {
      "enabled": true,
      "triggers": ["file:save"]
    }
  }
}
```

### JavaScript/TypeScript Project

```json
{
  "version": "1.0.0",
  "enabled": true,
  "agents": {
    "linter": {
      "enabled": true,
      "triggers": ["file:save", "git:pre-commit"],
      "config": {
        "linters": {"javascript": "eslint", "typescript": "eslint"}
      }
    },
    "formatter": {
      "enabled": true,
      "triggers": ["file:save"],
      "config": {
        "formatters": {"javascript": "prettier", "typescript": "prettier"}
      }
    },
    "testRunner": {
      "enabled": true,
      "triggers": ["file:save"],
      "config": {
        "testFrameworks": {"javascript": "jest", "typescript": "jest"}
      }
    }
  }
}
```

### Python Project

```json
{
  "version": "1.0.0",
  "enabled": true,
  "agents": {
    "linter": {
      "enabled": true,
      "triggers": ["file:save"],
      "config": {
        "linters": {"python": "ruff"}
      }
    },
    "formatter": {
      "enabled": true,
      "triggers": ["file:save"],
      "config": {
        "formatters": {"python": "black"}
      }
    },
    "testRunner": {
      "enabled": true,
      "triggers": ["file:save"],
      "config": {
        "testFrameworks": {"python": "pytest"}
      }
    }
  }
}
```

### Monorepo Configuration

```json
{
  "version": "1.0.0",
  "enabled": true,
  "agents": {
    "linter": {
      "enabled": true,
      "triggers": ["file:save"],
      "config": {
        "filePatterns": [
          "packages/*/src/**/*.{js,ts}",
          "apps/*/src/**/*.{js,ts}"
        ]
      }
    }
  },
  "eventSystem": {
    "collectors": {
      "filesystem": {
        "watchPaths": ["packages/**/src", "apps/**/src"]
      }
    }
  }
}
```
