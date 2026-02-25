# DevLoop Architecture

A comprehensive background agent system that monitors development lifecycle events and provides intelligent assistance during software development.

## Overview

DevLoop agents operate autonomously, responding to filesystem changes, git operations, build events, and other SDLC triggers to enhance developer productivity.

## Core Principles

1. **Non-Intrusive**: Agents should assist without blocking or interfering with normal development workflow
2. **Event-Driven**: All agent actions are triggered by observable system events
3. **Configurable**: Developers can enable/disable agents and customize their behavior
4. **Context-Aware**: Agents understand project context and adapt behavior accordingly
5. **Parallel Execution**: Multiple agents can run concurrently without conflicts
6. **Resource-Conscious**: Agents should be lightweight and respect system resources

## System Architecture

### Components

1. **Event Monitor**: Watches for SDLC events and dispatches to appropriate agents
2. **Agent Manager**: Handles agent lifecycle, configuration, and coordination
3. **Context Engine**: Maintains project understanding and provides context to agents
4. **Action Queue**: Serializes agent actions that require exclusive access
5. **Notification System**: Communicates agent findings and suggestions to developer

### Event Sources

- **Filesystem Events**: File creation, modification, deletion (inotify/fswatch)
- **Git Hooks**: pre-commit, post-commit, pre-push, post-merge, etc.
- **Process Events**: Script completion, build success/failure, test results
- **Stream Events**: stdin, stdout, stderr monitoring
- **IDE Events**: File open, save, focus changes (via LSP or IDE integration)
- **Time-Based**: Scheduled tasks, idle detection
- **Network Events**: Dependency updates, CI/CD webhooks
- **System Events**: Low memory, high CPU, disk space warnings

## Implemented Agents (15)

These agents are fully implemented with tests and available in the current release.

### Code Quality
| Agent | Module | Description |
|-------|--------|-------------|
| **Linter** | `agents/linter.py` | Runs linters (ruff, eslint) on changed files |
| **Formatter** | `agents/formatter.py` | Auto-formats code (Black, prettier, gofmt) |
| **Type Checker** | `agents/type_checker.py` | Background type checking (mypy, pyright, pyre) |
| **Security Scanner** | `agents/security_scanner.py` | Detects vulnerabilities with Bandit |
| **Code Rabbit** | `agents/code_rabbit.py` | AI-powered code analysis and insights |

### Testing & Security
| Agent | Module | Description |
|-------|--------|-------------|
| **Test Runner** | `agents/test_runner.py` | Runs relevant tests on file changes |
| **Snyk** | `agents/snyk.py` | Dependency vulnerability scanning |
| **Performance Profiler** | `agents/performance_profiler.py` | Tracks performance metrics and regressions |

### Development Workflow
| Agent | Module | Description |
|-------|--------|-------------|
| **Git Commit Assistant** | `agents/git_commit_assistant.py` | Suggests commit messages based on staged changes |
| **CI Monitor** | `agents/ci_monitor.py` | Tracks GitHub Actions / CI pipeline status |
| **Doc Lifecycle** | `agents/doc_lifecycle.py` | Manages documentation organization |
| **Agent Health Monitor** | `agents/agent_health_monitor.py` | Monitors agent execution health and failure patterns |

### Infrastructure
| Agent | Module | Description |
|-------|--------|-------------|
| **Echo** | `agents/echo.py` | Test/demo agent for event system verification |
| **File Logger** | `agents/file_logger.py` | Logs file events for debugging |
| **Sandbox Helper** | `agents/sandbox_helper.py` | Manages sandbox execution environments |

## Implemented Infrastructure

Beyond agents, DevLoop includes these implemented subsystems:

- **Tool Registry** — Agent tool dependency management and resolution
- **Pattern Analysis** — Cross-session pattern detection from developer feedback
- **Audit Logging** — SQLite event store with 30-day retention
- **Transactional I/O** — Atomic writes, checksums, corruption recovery
- **Config Schema Versioning** — Automatic migration between config versions
- **Daemon Health** — Process supervision and restart handling
- **Custom Agent Framework** — No-code agent builder with templates
- **Backup Manager** — Self-healing filesystem with file repair
- **MCP Server** — Model Context Protocol integration for Claude Code
- **Marketplace Registry** — Agent publishing, signing, discovery, and HTTP API

## Planned Agents (Future Roadmap)

These agents are designed but not yet implemented. They represent the full vision for DevLoop.

### Code Quality (Planned)
- **Complexity Analyzer** — Warn about high-complexity code

### Testing (Planned)
- **Coverage Monitor** — Track test coverage trends
- **Test Generator** — Suggest missing test cases
- **Flaky Test Detector** — Identify unreliable tests

### Git & Version Control (Planned)
- **Merge Conflict Resolver** — Provide context for conflicts
- **Branch Hygiene Agent** — Suggest cleanup of stale branches
- **Code Review Preparer** — Generate PR descriptions and checklists

### Documentation (Planned)
- **Comment Updater** — Flag outdated comments
- **README Maintainer** — Suggest README updates
- **API Doc Generator** — Update API documentation

### Dependency & Build (Planned)
- **Dependency Updater** — Monitor for package updates
- **Build Optimizer** — Suggest build improvements
- **Bundle Analyzer** — Track bundle size changes
- **Import Organizer** — Optimize import statements

### Performance & Monitoring (Planned)
- **Memory Leak Detector** — Monitor for memory issues
- **Log Analyzer** — Parse logs for patterns
- **Error Aggregator** — Collect and categorize errors

### Productivity (Planned)
- **Focus Time Tracker** — Monitor development sessions
- **Context Preloader** — Load relevant files when switching branches
- **Snippet Manager** — Suggest code snippets
- **Refactoring Suggester** — Identify refactoring opportunities

## Summary & Reporting System

### Agent Summary Command (`/agent-summary`)

A powerful command-line interface and Amp slash command that provides intelligent summaries of recent dev-agent findings.

#### Features

- **Intelligent Summarization**: Groups findings by agent, severity, and category
- **Time-based Scoping**: Filter by `recent` (24h), `today`, `session` (4h), or `all` time
- **Advanced Filtering**: Filter by specific agents, severity levels, or categories
- **Contextual Insights**: Provides actionable insights and trend analysis
- **Multiple Output Formats**: Markdown reports and JSON APIs for different integrations

#### Usage Examples

```bash
# Recent findings summary
/agent-summary

# Today's findings
/agent-summary today

# Filter by specific agent
/agent-summary --agent linter

# Critical issues only
/agent-summary recent --severity error
```

#### Integration Points

- **CLI Command**: `devloop summary agent-summary [options]`
- **Amp Slash Command**: `/agent-summary` - registered via `.agents/commands/agent-summary` executable script
- **JSON API**: For programmatic access and third-party integrations

## Implementation

DevLoop is a comprehensive development automation system featuring:

### Core Infrastructure
- Event monitoring system (filesystem, git, process, system)
- Agent framework with pub/sub coordination
- JSON-based configuration management
- Context store for shared development state

### Built-in Agents
- **Code Quality**: Linter, formatter, type checker
- **Testing**: Test runner with smart test selection
- **Security**: Vulnerability scanning with Bandit
- **Performance**: Complexity analysis and profiling
- **Workflow**: Git commit assistant, CI monitor, doc lifecycle
- **Monitoring**: Agent health monitoring
- **Custom**: No-code agent builder

### Advanced Features
- Learning system: Pattern recognition from developer feedback
- Performance optimization: Resource usage analytics
- Auto-fix engine: Safe, configurable automatic fixes
- Context awareness: Project understanding and adaptation

## Automated Installation & Setup

### One-Command Project Initialization

```bash
devloop init /path/to/project
```

This command **automatically handles everything:**

1. **Environment Detection**
   - Detects Amp workspace (if applicable)
   - Detects git repository
   - Checks existing setup

2. **Core Infrastructure**
   - Creates `.devloop` directory
   - Generates `agents.json` configuration
   - Copies `AGENTS.md` and `CODING_RULES.md`
   - Sets up `.gitignore` for agent files

3. **Git Integration** (if applicable)
   - Creates `pre-commit` hook for verification
   - Creates `pre-push` hook for verification
   - Enables commit discipline enforcement at git level

4. **Amp Integration** (if in Amp workspace)
   - Automatically registers slash commands (`/agent-summary`, `/agent-status`)
   - Registers post-task hook (`.agents/hooks/post-task`)
   - Injects commit discipline instructions into Claude system prompt
   - Creates workspace configuration

5. **Verification**
   - Tests all setup components
   - Shows installation status
   - Provides next steps

### What You Get

After `devloop init`:

- ✅ All agents configured and enabled
- ✅ Commit/push discipline automatically enforced
- ✅ Git hooks monitoring your workflow
- ✅ Amp integration ready (if in Amp)
- ✅ Verification system active
- ✅ Ready to start: `devloop watch .`

**Zero manual configuration required.** The system is production-ready immediately after `devloop init`.

### Advanced Options

```bash
# Skip Amp auto-configuration
devloop init /path/to/project --skip-amp

# Skip git hooks
devloop init /path/to/project --skip-git-hooks

# Non-interactive (no prompts)
devloop init /path/to/project --non-interactive

# Show detailed setup logs
devloop init /path/to/project --verbose
```

See [docs/installation-automation.md](./docs/installation-automation.md) for complete technical details.

## Amp Thread Context Capture

When using DevLoop within Amp threads, DevLoop automatically captures thread context to enable cross-thread pattern detection and self-improvement insights.

### How It Works

DevLoop logs all CLI commands with optional Amp thread context:
- **Thread ID**: `T-{uuid}` format
- **Thread URL**: Full ampcode.com thread URL
- **Timestamp**: When the command was executed
- **Context**: Working directory, environment, exit code

This data enables the self-improvement agent to:
1. Detect patterns repeated across multiple threads
2. Identify messaging or feature gaps
3. Suggest improvements based on user behavior
4. Create actionable Beads issues with thread references

### Usage

#### Option 1: Auto-Detection (Recommended for Amp Users)

If you're using Amp with devloop integrated, thread context is captured automatically:

```bash
# In Amp thread, just run devloop normally
devloop watch
devloop format
bd ready

# Thread context is automatically injected
```

#### Option 2: Manual Thread ID (For CI/Scripts)

Pass thread context explicitly:

```bash
export AMP_THREAD_ID="T-7f395a45-7fae-4983-8de0-d02e61d30183"
export AMP_THREAD_URL="https://ampcode.com/threads/T-7f395a45-7fae-4983-8de0-d02e61d30183"

devloop watch
```

Or inline:

```bash
AMP_THREAD_ID=T-abc123 devloop format
```

### Data Privacy

- ✅ **Local Only**: Thread IDs are stored in `.devloop/` (never uploaded)
- ✅ **Minimal Data**: Only thread ID and URL are captured, not thread content
- ✅ **Opt-in**: Users control whether to set `AMP_THREAD_ID`
- ✅ **Analysis Local**: All pattern detection happens locally

### Self-Improvement Agent

The self-improvement agent uses thread context to:

1. **Cross-Thread Pattern Detection**
   - "Same question asked in 5 different threads" → Missing feature/documentation
   - "User manually fixed agent output 3 times" → Messaging or quality issue

2. **Evidence-Based Insights**
   - Surfaces patterns with thread references
   - Shows which threads the pattern was detected in
   - Creates actionable Beads issues with `discovered-from` links

3. **Continuous Improvement**
   - Monitors user behavior across sessions
   - Detects silent failures (agent ran but user ignored output)
   - Suggests UX/messaging improvements based on actual usage

### Viewing Captured Data

To see what's being logged:

```bash
# View recent CLI actions
tail -f ~/.devloop/cli-actions.jsonl

# View Amp thread analysis
tail -f ~/.devloop/amp-thread-log.jsonl

# View detected patterns (once implemented)
devloop insights --thread T-abc123
```

## Configuration

### Log Rotation

By default, DevLoop logs can grow unbounded. **Configure log rotation** to prevent disk space issues:

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

This keeps logs under control while preserving recent history. See [Configuration Guide — Log Rotation](./docs/configuration.md#log-rotation) for details.

### Agents Configuration

Agents are configured via `.devloop/agents.json`:

```json
{
  "enabled": true,
  "agents": {
    "linter": {
      "enabled": true,
      "triggers": ["file:save", "git:pre-commit"],
      "config": {
        "debounce": 500,
        "filePatterns": ["**/*.{js,ts,jsx,tsx}"]
      }
    },
    "testRunner": {
      "enabled": true,
      "triggers": ["file:save"],
      "config": {
        "watchMode": true,
        "relatedTestsOnly": true
      }
    }
  },
  "global": {
    "maxConcurrentAgents": 5,
    "notificationLevel": "summary",
    "resourceLimits": {
      "maxCpu": 25,
      "maxMemory": "500MB"
    }
  }
}
```

## Security & Privacy

- Agents run in isolated environments
- No external data transmission without explicit consent
- Local execution only (no cloud dependencies by default)
- Sensitive file patterns excluded from monitoring
- Audit log of all agent actions

## Success Metrics

- Developer interruptions (should decrease)
- Time to fix issues (should decrease)
- Code quality metrics (should improve)
- Test coverage (should increase)
- Resource usage (should remain acceptable)
- Developer satisfaction (should increase)

## Future Considerations

- **Multi-Project Support**: Agents working across multiple repositories
- **Team Coordination**: Shared agent insights across team members
- **Cloud Integration**: Optional cloud-based analysis for deeper insights
- **Custom Agent Marketplace**: Community-contributed agents
- **AI-Powered Agents**: Integration with LLMs for intelligent suggestions
- **Cross-Tool Integration**: Integration with popular dev tools (Docker, K8s, etc.)

## See Also

- [CLI_REFERENCE.md](./CLI_REFERENCE.md) - Complete command documentation
- [RELEASE_PROCESS.md](./RELEASE_PROCESS.md) - Release workflow
- [CODING_RULES.md](./CODING_RULES.md) - Development standards and testing approach
