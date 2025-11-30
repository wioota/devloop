# Development Background Agents System

## ⚠️ IMPORTANT: Task Management with Beads

**Use Beads (`bd`) instead of markdown for all task management.** Beads provides proper dependency tracking, ready work detection, and long-term memory for agents.

**FORBIDDEN:** Do NOT create markdown task files (.md files for TODO lists, plans, checklists, etc). All work must be tracked in Beads.

Quick reference:
- `bd create "Task description" -p 1` - Create new issue
- `bd ready` - See what's ready to work on
- `bd update <id> --status in_progress` - Update status
- `bd close <id>` - Complete an issue
- See `.beads/issues.jsonl` in git for synced state

Run `bd quickstart` for interactive tutorial.

---

## Overview

A comprehensive background agent system that monitors development lifecycle events and provides intelligent assistance during software development. These agents operate autonomously, responding to filesystem changes, git operations, build events, and other SDLC triggers to enhance developer productivity.

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

## Agent Categories

### 1. Code Quality Agents
- **Linter Agent**: Runs linters on changed files
- **Formatter Agent**: Auto-formats code on save
- **Type Checker Agent**: Monitors type errors in background
- **Security Scanner**: Detects potential security issues
- **Complexity Analyzer**: Warns about high-complexity code

### 2. Testing Agents
- **Test Runner Agent**: Runs relevant tests on file changes
- **Coverage Monitor**: Tracks test coverage trends
- **Test Generator**: Suggests missing test cases
- **Flaky Test Detector**: Identifies unreliable tests

### 3. Git & Version Control Agents
- **Commit Message Assistant**: Suggests commit messages based on changes
- **Merge Conflict Resolver**: Provides context for conflicts
- **Branch Hygiene Agent**: Suggests cleanup of stale branches
- **Code Review Preparer**: Generates PR descriptions and checklists

### 4. Documentation Agents
- **Doc Sync Agent**: Ensures docs match code changes
- **Comment Updater**: Flags outdated comments
- **README Maintainer**: Suggests README updates
- **API Doc Generator**: Updates API documentation

### 5. Dependency & Build Agents
- **Dependency Updater**: Monitors for package updates
- **Build Optimizer**: Suggests build improvements
- **Bundle Analyzer**: Tracks bundle size changes
- **Import Organizer**: Optimizes import statements

### 6. Performance & Monitoring Agents
- **Performance Profiler**: Detects performance regressions
- **Memory Leak Detector**: Monitors for memory issues
- **Log Analyzer**: Parses logs for patterns
- **Error Aggregator**: Collects and categorizes errors

### 7. Productivity Agents
- **Focus Time Tracker**: Monitors development sessions
- **Context Preloader**: Loads relevant files when switching branches
- **Snippet Manager**: Suggests code snippets
- **Refactoring Suggester**: Identifies refactoring opportunities

## Summary & Reporting System

### Agent Summary Command (`/agent-summary`)

A powerful command-line interface and Amp slash command that provides intelligent summaries of recent dev-agent findings, tailored to development context.

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

See [INSTALLATION_AUTOMATION.md](./INSTALLATION_AUTOMATION.md) for complete technical details.

---

## Development Discipline

### Task Management with Beads (REQUIRED)

**All work must be tracked in Beads, NOT in markdown files.**

Beads provides:
- ✅ Persistent issue tracking synced via git
- ✅ Dependency tracking (blocks, related, parent-child, discovered-from)
- ✅ Ready work detection (unblocked issues only)
- ✅ Long-term memory across sessions
- ✅ Multi-agent coordination without conflicts

**Agent Workflow:**

1. **Start of session:**
   ```bash
   bd ready              # See what's ready to work on
   bd show <issue-id>    # Review issue details
   ```

2. **During work:**
   ```bash
   bd update <id> --status in_progress   # Claim the issue
   bd create "Bug found" -p 1             # File discovered issues
   bd dep add <new-id> <parent-id> --type discovered-from
   ```

3. **End of session (MANDATORY):**
   ```bash
   bd close <id> --reason "Implemented in PR #42"
   bd update <other-id> --status in_progress  # Update ongoing work
   git add .beads/                             # Commit beads changes
   git commit -m "Work session update"
   git push origin main
   ```

**DO NOT:**
- ❌ Create `.md` files for task tracking
- ❌ Use markdown headers for planning
- ❌ Leave issues without status updates
- ❌ Forget to push `.beads/issues.jsonl` at session end

**Benefits:**
- Agents can find their next task immediately with `bd ready`
- Dependencies prevent duplicate work
- Full history and traceability
- Works across branches and machines

### Commit & Push After Every Task

**MANDATORY:** Every completed task must end with `git add`, `git commit`, and `git push origin main`.

This is **automatically enforced** by:
1. Git hooks (pre-commit, pre-push)
2. Amp post-task verification hook
3. `.agents/verify-task-complete` script

See CODING_RULES.md for detailed protocol.

**Verification command:**
```bash
.agents/verify-task-complete
# Should show: ✅ PASS: All checks successful
```

### CI Verification (Pre-Push Hook)

**Automatic:** The `.git/hooks/pre-push` hook automatically checks CI status before allowing pushes.

**Workflow:**
1. Make changes and commit: `git add . && git commit -m "..."`
2. Push: `git push origin main`
3. **Pre-push hook runs automatically:**
   - Checks if `gh` CLI is installed
   - Gets the latest CI run status for your branch
   - If CI failed: blocks push and shows error
   - If CI passed: allows push to proceed
   - If no runs yet: allows push

**Manual CI check (if needed):**
```bash
# View recent CI runs
gh run list --limit 10

# View a specific run
gh run view <run-id>

# View failed run details
gh run view <run-id> --log-failed
```

**If push is blocked:**
1. Check what failed: `gh run view <run-id> --log-failed`
2. Fix the issues locally
3. Commit and push again
4. Pre-push hook will verify the new CI run before allowing push

**Why this matters:** CI failures catch issues before they merge (formatting, type errors, broken tests, security issues). The pre-push hook ensures developers are aware of CI status before code reaches the repository.

---

## Configuration

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

## See Also

- [Agent Types](./agent-types.md) - Detailed specifications for each agent
- [Event System](./event-system.md) - Event monitoring architecture
- [Configuration Schema](./configuration-schema.md) - Complete configuration reference
- [Development Guide](./DEVELOPMENT.md) - Implementation guidelines
- [Testing Strategy](./TESTING.md) - Testing approach for agents

## Future Considerations

- **Multi-Project Support**: Agents working across multiple repositories
- **Team Coordination**: Shared agent insights across team members
- **Cloud Integration**: Optional cloud-based analysis for deeper insights
- **Custom Agent Marketplace**: Community-contributed agents
- **AI-Powered Agents**: Integration with LLMs for intelligent suggestions
- **Cross-Tool Integration**: Integration with popular dev tools (Docker, K8s, etc.)
