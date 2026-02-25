# Configuration Guide

This guide covers all DevLoop configuration options, including global settings,
per-agent configuration, log rotation, and environment variables.

---

## Configuration File

DevLoop stores its configuration in `.devloop/agents.json` at the root of your
project. This file is created automatically when you run `devloop init`.

- **Format**: JSON
- **Location**: `.devloop/agents.json`
- **Created by**: `devloop init /path/to/project`

The configuration is organized into two top-level sections: `global` (settings
that apply to all agents) and `agents` (per-agent overrides and options).

---

## Global Settings

The `global` section controls resource limits, notification behavior, and
autonomous fix policies that apply across all agents.

```json
{
  "global": {
    "maxConcurrentAgents": 5,
    "notificationLevel": "summary",
    "resourceLimits": {
      "maxCpu": 25,
      "maxMemory": "500MB"
    },
    "autonomousFixes": {
      "enabled": false,
      "safetyLevel": "safe_only"
    }
  }
}
```

### Resource Limits

These settings prevent DevLoop from consuming excessive system resources while
running background agents.

| Setting              | Type   | Default  | Description                          |
|----------------------|--------|----------|--------------------------------------|
| `maxCpu`             | int    | `25`     | Maximum CPU percentage per agent     |
| `maxMemory`          | string | `"500MB"`| Memory limit per agent               |
| `maxConcurrentAgents`| int    | `5`      | Maximum number of agents running simultaneously |

If an agent exceeds its resource limits, DevLoop will throttle or suspend it
and emit a warning to the log.

### Notification Level

Controls how much output DevLoop produces during normal operation.

- `"silent"` — No notifications; errors only
- `"summary"` — One-line summaries per agent run (default)
- `"verbose"` — Full output from each agent

### Autonomous Fix Settings

When `autonomousFixes.enabled` is `true`, DevLoop can automatically apply
certain code fixes without prompting. The `safetyLevel` controls which
categories of fixes are applied.

### Auto-Fix Safety Levels

- `safe_only` — Only whitespace and indentation fixes (default, recommended)
- `medium_risk` — Includes import sorting and formatting fixes
- `all` — Applies all suggested fixes, including code transformations (use with caution)

It is strongly recommended to keep autonomous fixes disabled or set to
`safe_only` until you are comfortable with the changes DevLoop applies. You can
always review what would be fixed by running `devloop verify-work` first.

---

## Agent Configuration

Each agent is configured under the `agents` key. The key name identifies the
agent, and the value is an object with that agent's settings.

```json
{
  "agents": {
    "linter": {
      "enabled": true,
      "triggers": ["file:save", "git:pre-commit"],
      "config": {
        "debounce": 500,
        "filePatterns": ["**/*.py"]
      }
    },
    "test-runner": {
      "enabled": true,
      "triggers": ["file:modified"],
      "config": {
        "debounce": 1000,
        "filePatterns": ["src/**/*.py", "tests/**/*.py"]
      }
    },
    "security-scanner": {
      "enabled": false,
      "triggers": ["git:pre-push"],
      "config": {
        "debounce": 0,
        "filePatterns": ["**/*"]
      }
    }
  }
}
```

### Common Agent Options

| Option              | Type   | Description                                      |
|---------------------|--------|--------------------------------------------------|
| `enabled`           | bool   | Enable or disable the agent                      |
| `triggers`          | array  | Events that cause the agent to run               |
| `config.debounce`   | int    | Milliseconds to wait after a trigger before running |
| `config.filePatterns`| array | Glob patterns for files the agent should monitor |

The `debounce` setting is useful for file-watch triggers. When a file is saved
multiple times in quick succession (for example, during a bulk format), the
agent waits for the debounce period to elapse before running, avoiding
redundant executions.

### Available Triggers

File system triggers:

- `file:save` — Any file save event
- `file:created` — A new file is created
- `file:modified` — An existing file is modified
- `file:deleted` — A file is deleted

Git hook triggers:

- `git:pre-commit` — Runs before a commit is finalized
- `git:post-commit` — Runs after a commit is finalized
- `git:pre-push` — Runs before a push to a remote

You can combine multiple triggers in the `triggers` array. The agent will run
whenever any of the listed events occur.

---

## Log Rotation

DevLoop writes operational logs to `.devloop/devloop.log`. Over time, this file
can grow large. Log rotation prevents unbounded disk usage by automatically
archiving and cleaning up old log files.

### Configuration

Add a `logging` section under `global` to configure log level and rotation
behavior.

```json
{
  "global": {
    "logging": {
      "level": "info",
      "rotation": {
        "enabled": true,
        "maxSize": "100MB",
        "maxBackups": 3,
        "maxAgeDays": 7,
        "compress": true
      }
    }
  }
}
```

### Log Levels

- `"debug"` — Verbose output for troubleshooting
- `"info"` — Standard operational messages (default)
- `"warn"` — Warnings and errors only
- `"error"` — Errors only

### Log Rotation Defaults

| Setting      | Default  | Description                                 |
|--------------|----------|---------------------------------------------|
| `enabled`    | `true`   | Whether rotation is active                  |
| `maxSize`    | `"100MB"`| Maximum size before rotating                |
| `maxBackups` | `3`      | Number of rotated files to keep (300MB total) |
| `maxAgeDays` | `7`      | Delete rotated logs older than this many days |
| `compress`   | `true`   | Gzip-compress rotated log files             |

When a log file reaches `maxSize`, it is renamed with a numeric suffix (e.g.,
`devloop.log.1`) and a new log file is started. If `compress` is enabled, the
rotated file is gzipped to `devloop.log.1.gz`. Files beyond `maxBackups` or
older than `maxAgeDays` are deleted automatically.

### Viewing Logs

Follow the log in real time:

```bash
tail -f .devloop/devloop.log
```

Run the watcher in the foreground with verbose output:

```bash
devloop watch . --verbose --foreground
```

Check disk usage of all log files:

```bash
du -sh .devloop/devloop.log*
```

---

## Environment Variables

DevLoop reads several environment variables for integration with external
services and CI systems.

| Variable             | Purpose                                      |
|----------------------|----------------------------------------------|
| `SNYK_TOKEN`         | Snyk API token for security scanning         |
| `CODE_RABBIT_API_KEY`| CodeRabbit API key for code review           |
| `GITHUB_TOKEN`       | GitHub token used by the pre-push CI check   |
| `AMP_THREAD_ID`      | Amp thread context identifier (auto-set)     |

These variables should be set in your shell profile or CI environment. Never
commit tokens or API keys to version control. See the
[Security](./security.md) guide for best practices on managing secrets.

---

## Config Schema Versioning

The configuration file includes an internal schema version that DevLoop uses to
track the format.

- DevLoop automatically migrates your configuration when you upgrade to a new
  version.
- The schema version is stored as a `schemaVersion` field in `agents.json`.
- No manual migration steps are required on upgrade. DevLoop handles all
  transformations transparently.

If you need to check the current schema version:

```bash
cat .devloop/agents.json | python3 -m json.tool | grep schemaVersion
```

---

## See Also

- [Getting Started](./getting-started.md) — Installation and first-run setup
- [Architecture](./architecture.md) — System design and agent categories
- [Security](./security.md) — Token management and security practices
