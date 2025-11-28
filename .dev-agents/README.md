# Claude Agents Integration

This directory contains the integration layer that allows Claude Code and Amp to work with background agents.

## Overview

The integration provides:
- **Tool-agnostic context sharing** via JSON files in `.claude/context/`
- **Tool-specific adapters** for optimal integration with each coding assistant
- **Registration files** (CLAUDE.md and AGENTS.md) with tool-specific instructions

## Directory Structure

```
.claude/
├── CLAUDE.md              # Claude Code integration instructions
├── AGENTS.md              # Amp integration instructions
├── README.md              # This file
├── context/               # Shared context files (JSON)
│   ├── agent-results.json # Latest background agent results
│   └── activity-log.json  # Historical activity (future)
└── integration/           # Tool-specific adapters
    ├── amp-adapter.py     # Amp subagent utilities
    └── claude-code-adapter.py # Claude Code hook/skill utilities
```

## For Amp Users

Amp reads `AGENTS.md` and can spawn subagents to monitor background agent activity.

### Example Usage

```bash
# In Amp, spawn a subagent to check background agent status
"Spawn a subagent to check current background agent results"

# Monitor activity during development
"Use a subagent to monitor background agent activity during this refactoring"

# Get specific insights
"Have a subagent analyze the recent lint results"

# Auto-fix commands
"Automatically apply safe background agent fixes"
"Apply auto-fixable lint issues"
```

### Adapter Usage

The Amp adapter can be called directly for testing:

```bash
# Get status summary
python3 .claude/integration/amp-adapter.py status

# Get specific agent results
python3 .claude/integration/amp-adapter.py results --agent linter

# Get recent activity
python3 .claude/integration/amp-adapter.py activity --minutes 60

# Check auto-fixable issues
python3 .claude/integration/amp-adapter.py auto-fixes

# Apply fixes automatically
python3 .claude/integration/amp-adapter.py apply-fixes --safety safe_only
```

## For Claude Code Users

Claude Code reads `CLAUDE.md` and can use hooks and skills to integrate with background agents.

### Hook Configuration

Add to your Claude Code settings:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/integration/claude-code-adapter.py check_results"
          }
        ]
      }
    ]
  }
}
```

### Skills Usage

```bash
# Check for issues after changes
"Check background agent results for issues in the files I just modified"

# Get test status
"What do the background linters say about my recent changes?"

# Security checks
"Are there any security findings from background agents?"
```

### Adapter Usage

The Claude Code adapter can be called directly for testing:

```bash
# Check recent results
python3 .claude/integration/claude-code-adapter.py check_results

# Get lint insights
python3 .claude/integration/claude-code-adapter.py insights --query-type lint

# Get general insights
python3 .claude/integration/claude-code-adapter.py insights
```

## Context File Format

Background agents write results to `context/agent-results.json`:

```json
{
  "format": "dev-agents-v1",
  "timestamp": "2024-01-15T14:30:00Z",
  "agents": {
    "linter": {
      "status": "completed",
      "results": {"issues_found": 3, "auto_fixable": 2}
    },
    "test-runner": {
      "status": "completed",
      "results": {"passed": 47, "failed": 0}
    }
  },
  "tool_agnostic": true,
  "readable_by": ["claude-code", "amp"]
}
```

## Development

### Adding New Agents

1. Update the context JSON schema if needed
2. Add agent-specific logic to both adapters
3. Update the AGENTS.md and CLAUDE.md files with new usage examples
4. Test integration with both tools

### Testing Integration

```bash
# Test both adapters
python3 .claude/integration/amp-adapter.py status
python3 .claude/integration/claude-code-adapter.py check_results

# Verify context files exist and are readable
cat .claude/context/agent-results.json | jq .
```

## Troubleshooting

### Amp Issues
- Ensure AGENTS.md exists and is readable
- Check that subagents can execute the adapter scripts
- Verify Python and dependencies are available

### Claude Code Issues
- Check hook configuration in settings
- Ensure adapter scripts are executable
- Verify CLAUDE.md is present

### General Issues
- Check file permissions on `.claude/` directory
- Verify JSON context files are valid
- Ensure background agents are writing results correctly
