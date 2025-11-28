# Dev Agents Documentation

Complete documentation for the dev-agents system.

---

## Quick Links

- **[Getting Started](./getting-started.md)** - Installation, configuration, and first steps
- **[Architecture](./architecture.md)** - System design and technical architecture
- **[CHANGELOG](../CHANGELOG.md)** - Version history and changes

---

## Documentation Structure

### Getting Started

- [Getting Started Guide](./getting-started.md) - Complete guide from installation to advanced usage
  - Prerequisites
  - Installation options
  - Quick start
  - Configuration
  - Claude Code integration
  - Troubleshooting

### Architecture & Design

- [Architecture Overview](./architecture.md) - System architecture and interaction patterns
  - System overview
  - Project structure
  - Core components
  - Interaction model
  - Agent communication
  - Integration patterns

### Reference Documentation

- [Agent Types](./reference/agent-types.md) - Detailed specifications for each agent
- [Configuration Schema](./reference/configuration-schema.md) - Complete configuration reference
- [Event System](./reference/event-system.md) - Event monitoring architecture
- [Tech Stack](./reference/tech-stack.md) - Technologies and dependencies
- [Commands](./reference/commands.md) - CLI command reference

### How-To Guides

- [Testing Strategy](./guides/testing-strategy.md) - Testing approach and best practices
- [Report-Only Mode](./guides/report-only-mode.md) - Running agents in report-only mode

### Contributing

- [Agent Development](./contributing/agents.md) - Rules and processes for agent development

### Archive

- [Historical Documentation](./archive/README.md) - Archived milestone and completion documents
  - Phase completion documents
  - Implementation histories
  - Bug fix summaries
  - Session statuses

---

## Core Documentation (Root)

- **[README.md](../README.md)** - Main project overview
- **[CHANGELOG.md](../CHANGELOG.md)** - Version history
- **[CLAUDE.md](../CLAUDE.md)** - Development background agents system overview
- **[CODING_RULES.md](../CODING_RULES.md)** - Development patterns and best practices
- **[PUBLISHING_PLAN.md](../PUBLISHING_PLAN.md)** - Future public release roadmap
- **[CI_QUALITY_COMMITMENT.md](../CI_QUALITY_COMMITMENT.md)** - CI/CD quality standards

---

## Special Topics

### Context Store

The context store is a key feature that enables LLM integration:

- Progressive disclosure (3-tier system)
- Finding-based API
- Relevance scoring
- Automatic tier assignment

See [Architecture](./architecture.md#context-store) for details.

### Claude Code Integration

Dev-agents integrates seamlessly with Claude Code:

- Shared context files
- Proactive status checking
- Background agent findings
- Coordinated execution

See [Getting Started - Claude Code Integration](./getting-started.md#claude-code-integration) for setup.

### Agent System

Dev-agents includes 8 production-ready agents:

1. **LinterAgent** - Code linting (ruff, eslint)
2. **FormatterAgent** - Code formatting (black, prettier)
3. **TestRunnerAgent** - Test execution (pytest, jest)
4. **TypeCheckerAgent** - Type checking (mypy, pyright)
5. **SecurityScannerAgent** - Security scanning (bandit)
6. **AgentHealthMonitorAgent** - Agent health monitoring
7. **GitCommitAssistantAgent** - Commit message generation
8. **PerformanceProfilerAgent** - Performance profiling

See [Agent Types](./reference/agent-types.md) for specifications.

---

## Recent Updates

See [CHANGELOG.md](../CHANGELOG.md) for complete version history.

**Latest (v0.1.0 - November 28, 2025):**
- Project renamed from claude-agents to dev-agents
- Context store implementation complete
- All 8 agents integrated
- 96 tests passing
- Full Claude Code integration

---

## Help & Support

### CLI Help

```bash
dev-agents --help        # General help
dev-agents watch --help  # Watch command help
dev-agents status        # Show agent status
```

### Troubleshooting

See [Getting Started - Troubleshooting](./getting-started.md#troubleshooting) for common issues and solutions.

### Feedback

Report issues at: https://github.com/wioota/dev-agents/issues

---

## Navigation

- **← [Back to README](../README.md)**
- **→ [Getting Started](./getting-started.md)**
- **→ [Architecture](./architecture.md)**

---

**Documentation Version:** 0.1.0 (November 2025)
