# Architecture Guide

> System design, provider abstraction, and observability for DevLoop.

---

## System Overview

```
File Changes → Collectors → Event Bus → Agents → Results
  (Filesystem)   (Git, etc)   (Pub/Sub)   (15 built-in + custom)
                                  ↓
                           Context Store
                         (shared state)
                                  ↓
                           Findings & Metrics
```

DevLoop is an event-driven system where **collectors** observe development activity, publish events to an **event bus**, and **agents** subscribe to relevant events to produce findings.

---

## Core Components

### Event Bus

Pub/sub system for agent coordination. Agents subscribe to event types they care about (e.g., `file:modified`, `git:pre-commit`). Events are dispatched asynchronously to all matching subscribers.

### Collectors

| Collector | Source | Events |
|-----------|--------|--------|
| **Filesystem** | inotify/fswatch | `file:created`, `file:modified`, `file:deleted` |
| **Git** | Git hooks | `git:pre-commit`, `git:post-commit`, `git:pre-push` |
| **Process** | Build/test completion | `process:exit`, `test:complete` |
| **System** | OS metrics | `system:low-memory`, `system:high-cpu` |

### Agent Manager

Coordinates agent lifecycle:
- Loads agent configuration from `.devloop/agents.json`
- Manages concurrent execution (respects `maxConcurrentAgents`)
- Enforces resource limits (CPU, memory)
- Tracks agent health metrics

### Context Store

Three-tier progressive disclosure system for development findings:

| Tier | Purpose | Retention |
|------|---------|-----------|
| **Immediate** | Critical issues needing attention now | Until addressed |
| **Relevant** | Issues related to current work context | Session-based |
| **Background** | Informational findings for later review | 7 days |

- Finding-based API with structured metadata
- Relevance scoring based on file scope, severity, and freshness
- Local-first architecture (all data stays on your machine)

### Event Store

SQLite-backed audit trail (`.devloop/events.db`):
- Agent execution timing and success rates
- Finding counts and severity distribution
- 30-day retention with automatic cleanup
- File-level locking for concurrent access safety

```bash
devloop audit query --limit 20        # Recent activity
devloop audit query --agent linter    # Filter by agent
```

---

## Provider System

DevLoop uses a provider abstraction layer for CI/CD and package registry operations, enabling the same commands to work across different platforms.

### CI Providers

| Provider | Detection | Tool |
|----------|-----------|------|
| **GitHub Actions** | `.github/workflows/` | `gh` CLI |
| **GitLab CI/CD** | `.gitlab-ci.yml` | `glab` CLI |
| **Jenkins** | `Jenkinsfile` | REST API |
| **CircleCI** | `.circleci/config.yml` | API v2 |
| **Custom** | Manual config | Configurable |

### Registry Providers

| Registry | Detection | Tool |
|----------|-----------|------|
| **PyPI** | `pyproject.toml` | Poetry / Twine |
| **npm** | `package.json` | npm CLI |
| **Docker** | `Dockerfile` | Docker CLI |
| **Artifactory** | Manual config | REST API (AQL) |
| **GitHub Releases** | GitHub repo | `gh` CLI |

### Auto-Detection

```bash
devloop release debug  # Shows detected CI and registry providers
```

DevLoop checks for configuration files and installed CLIs to automatically select the right provider.

### Release Workflow

```bash
devloop release check 1.2.3    # Validate preconditions
devloop release publish 1.2.3   # Full automated workflow
```

The release workflow: validate preconditions → create annotated git tag → publish to registry → push tag to remote.

See [RELEASE_PROCESS.md](../RELEASE_PROCESS.md) for complete release documentation.

---

## Metrics and Monitoring

### Agent Health

```bash
devloop health            # View agent health dashboard
devloop audit query       # Browse event log
devloop telemetry stats   # Usage analytics
```

### Tracked Metrics

- **Execution time** — Per-agent latency percentiles
- **Success rate** — Pass/fail ratio over time
- **Finding counts** — By agent, severity, and category
- **Resource usage** — CPU and memory per agent execution
- **Event throughput** — Events processed per minute

### Observability Stack

- **Local telemetry** — JSONL-based traces in `.devloop/`
- **Optional cloud backends** — Jaeger, Prometheus, OTLP export
- **OpenTelemetry-compatible** — Vendor-neutral APIs

---

## Directory Structure

```
project-root/
├── .devloop/
│   ├── agents.json          # Agent configuration
│   ├── events.db            # SQLite event store
│   ├── devloop.log          # Application logs (with rotation)
│   ├── context/             # Finding storage
│   └── custom_agents/       # User-created agents
├── .agents/
│   ├── verify-task-complete # Task completion verifier
│   └── hooks/               # Amp integration hooks
├── CLAUDE.md → AGENTS.md    # Symlink for Claude Code
└── AGENTS.md                # Agent workflow instructions
```

---

## See Also

- [Configuration Guide](./configuration.md) — Agent settings and log rotation
- [Agent Development](./agent-development.md) — Creating custom agents
- [ARCHITECTURE.md](../ARCHITECTURE.md) — Agent categories and roadmap
- [Getting Started](./getting-started.md) — Installation and setup
