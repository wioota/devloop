# CLI Commands Reference

Complete reference of all DevLoop command-line interface commands.

## Watch Command

Monitor a directory for changes and automatically run agents.

```bash
devloop watch <path>
```

**Options:**
- `--verbose` - Show detailed output
- `--foreground` - Run in foreground (don't daemonize)

## Status Command

Check the status of the DevLoop daemon and agents.

```bash
devloop status
```

Shows:
- Daemon status (running/stopped)
- Agent health metrics
- Recent activity
- Resource usage

## Stop Command

Stop the DevLoop daemon.

```bash
devloop stop <path>
```

## Init Command

Initialize DevLoop in a project.

```bash
devloop init <path>
```

**Options:**
- `--non-interactive` - Skip interactive prompts
- `--check-requirements` - Verify system dependencies
- `--merge-templates` - Update AGENTS.md templates

## Agent Commands

### Marketplace Commands

```bash
# Search marketplace
devloop marketplace search "<query>"

# List categories
devloop marketplace list-categories

# Install an agent
devloop marketplace install <agent-name> <version>

# Server management
devloop marketplace server start --port 8000
devloop marketplace server stop
devloop marketplace status
```

### Agent Publishing

```bash
# Check if ready to publish
devloop agent check ./my-agent

# Publish to marketplace
devloop agent publish ./my-agent

# Sign agent
devloop agent sign ./my-agent

# Verify signature
devloop agent verify ./my-agent

# Show agent info
devloop agent info ./my-agent --signature

# Manage versions
devloop agent version ./my-agent patch
devloop agent deprecate my-agent -m "Use newer version"
```

### Custom Agent Management

```bash
# Create custom agent
devloop custom-create my_agent pattern_matcher

# List custom agents
devloop custom-list

# Show custom agent details
devloop custom-show my_agent
```

### Agent Dependencies

```bash
# Check dependencies
devloop agent dependencies check ./my-agent

# Resolve missing dependencies
devloop agent dependencies resolve ./my-agent

# List dependencies
devloop agent dependencies list ./my-agent
```

## Release Commands

```bash
# Check if ready for release
devloop release check 1.2.3

# Publish release
devloop release publish 1.2.3

# Options
devloop release publish 1.2.3 --dry-run
devloop release publish 1.2.3 --ci github --registry pypi
devloop release debug
```

## Audit & Observability

```bash
# Query event log
devloop audit query --limit 20

# Filter by agent
devloop audit query --agent linter

# Health metrics
devloop health
```

## Learning & Optimization

```bash
# View learning insights
devloop learning-insights --agent linter

# Get recommendations
devloop learning-recommendations linter

# Performance summary
devloop perf-summary --agent formatter
```

## Version & Help

```bash
# Show version
devloop --version

# Show help
devloop --help

# Help for specific command
devloop <command> --help
```

See [AGENTS.md](../AGENTS.md) for more details on command options and configuration.
