# DevLoop CLI Commands Reference

Complete reference for all DevLoop CLI commands.

## Core Workflow Commands

### Project Initialization & Management

```bash
# Initialize devloop in a project (interactive setup)
devloop init /path/to/project

# Start watching for file changes and running agents
devloop watch .

# Show configuration and agent status
devloop status

# Show operational health status
devloop health

# Stop the background daemon
devloop stop
```

### Task Verification (Claude Code & Amp Integration)

```bash
# Run code quality verification (Claude Code post-task hook equivalent)
devloop verify-work

# Extract findings and create Beads issues
devloop extract-findings-cmd
```

### Daemon Management

```bash
# Check daemon health and status
devloop daemon-status

# Update git hooks from latest templates
devloop update-hooks
```

## Release Management Commands

### Quick Release Workflow

```bash
# Check if ready to release (validates all preconditions)
devloop release check <version>

# Publish a release (full automated workflow)
devloop release publish <version>

# Dry-run to see what would happen
devloop release publish <version> --dry-run

# Specify explicit providers (if auto-detect fails)
devloop release publish <version> --ci github --registry pypi

# Skip specific steps
devloop release publish <version> --skip-tag --skip-publish
```

### Example Release Workflow

```bash
# 1. Verify readiness
devloop release check 0.5.1

# 2. If check passes, publish
devloop release publish 0.5.1

# 3. If check fails, fix issues and retry
devloop release check 0.5.1
```

## Agent Management Commands

### Custom Agents

```bash
# Create a custom pattern matcher agent
devloop custom create my_agent pattern_matcher \
  --description "Find patterns" \
  --triggers file:created,file:modified

# List custom agents
devloop custom list

# Show details of a custom agent
devloop custom show <agent-id>

# Delete a custom agent
devloop custom delete <agent-id>
```

### Feedback & Performance

```bash
# View summaries of findings
devloop summary

# View summaries for specific scope
devloop summary recent   # Last 24 hours
devloop summary today    # Today only
devloop summary session  # Last 4 hours

# Filter by agent and severity
devloop summary --agent linter --severity error

# Submit feedback on agent performance
devloop feedback submit <agent-name> rating <1-5>
devloop feedback submit <agent-name> helpful
devloop feedback submit <agent-name> not-helpful

# View agent feedback
devloop feedback list <agent-name>

# View performance metrics
devloop metrics summary

# View ROI and value tracking
devloop metrics roi
```

### Marketplace & Publishing

```bash
# Check agent readiness for publishing
devloop agent check ./my-agent

# Publish agent to marketplace
devloop agent publish ./my-agent

# Bump agent version
devloop agent version ./my-agent patch|minor|major

# Sign agent cryptographically
devloop agent sign ./my-agent

# Verify agent signature
devloop agent verify ./my-agent

# Show agent metadata and signature
devloop agent info ./my-agent --signature

# Mark agent version as deprecated
devloop agent deprecate my-agent -m "Use new-agent instead"

# Check tool dependencies
devloop agent dependencies check ./my-agent
devloop agent dependencies resolve ./my-agent
devloop agent dependencies list ./my-agent

# Search marketplace
devloop agent search "formatter"

# Install agent from marketplace
devloop agent install my-agent 1.0.0

# Marketplace server management
devloop marketplace server start --port 8000
devloop marketplace server stop
devloop marketplace status
```

### System Information

```bash
# Show version information
devloop version

# Verify external tool dependencies
devloop tools

# View telemetry and value tracking
devloop telemetry
```

## Amp Integration Commands

```bash
# Show current agent status for Amp
devloop amp-status

# Show agent findings for Amp display
devloop amp-findings

# Show context store index for Amp
devloop amp-context
```

## Beads (bd) Commands

### Quick Reference

```bash
# Check for ready work
bd ready --json

# Create new issues
bd create "Issue title" -t bug|feature|task -p 0-4 --json
bd create "Issue title" -p 1 --deps discovered-from:bd-123 --json

# Claim and update
bd update bd-42 --status in_progress --json
bd update bd-42 --priority 1 --json

# Complete work
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow Pattern

```bash
# 1. Start of session
bd ready              # See what's ready to work on
bd show <issue-id>    # Review issue details

# 2. During work
bd update <id> --status in_progress   # Claim the issue
bd create "Bug found" -p 1             # File discovered issues
bd dep add <new-id> <parent-id> --type discovered-from

# 3. End of session
bd close <id> --reason "Implemented in PR #42"
bd update <other-id> --status in_progress  # Update ongoing work
git add .beads/                             # Commit beads changes
git commit -m "Work session update"
git push origin main
```

## Command Usage Patterns for AI Agents

### Always Use DevLoop Commands

**NEVER use manual operations when a DevLoop command exists:**

❌ **Don't do this:**
```bash
git tag v1.0.0
git push origin v1.0.0
poetry publish
```

✅ **Do this instead:**
```bash
devloop release publish 1.0.0
```

### Why Use Commands Instead of Manual Operations

- ✅ Automatic validation and error checking
- ✅ Atomic operations (all-or-nothing)
- ✅ State management consistency
- ✅ Integration with CI/CD and registries
- ✅ Consistent naming and tagging
- ✅ Automatic Beads issue creation from findings
- ✅ Telemetry and metrics tracking
- ✅ Help text available: `devloop <command> --help`

### Essential Command Patterns

**For releases:**
```bash
devloop release check <version>    # ALWAYS run before publish
devloop release publish <version>  # Full automated workflow
```

**For verification:**
```bash
devloop verify-work               # Instead of manually running tests/checks
```

**For feedback:**
```bash
devloop feedback submit <agent> helpful  # Record observations
```

**For task integration:**
```bash
devloop extract-findings-cmd      # Create Beads issues from findings
```

## Getting Help

Every command supports `--help`:

```bash
devloop --help
devloop release --help
devloop release publish --help
bd --help
bd create --help
```
