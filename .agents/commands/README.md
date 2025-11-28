# Amp Slash Commands

This directory contains custom slash commands for Amp that integrate with the dev-agents system.

## `/agent-summary`

Provides intelligent summaries of recent dev-agent findings with filtering and contextual insights.

### Usage

```
/agent-summary [scope] [--agent AGENT] [--severity SEVERITY] [--category CATEGORY]
```

### Parameters

- `scope` (optional): Time scope to analyze
  - `recent` (default): Last 24 hours
  - `today`: Current day
  - `session`: Last 4 hours
  - `all`: All time

- `--agent` (optional): Filter by specific agent name
- `--severity` (optional): Filter by severity (error, warning, info, style)
- `--category` (optional): Filter by category

### Examples

```
/agent-summary
/agent-summary today
/agent-summary --agent linter
/agent-summary recent --severity error
/agent-summary --category security
```

### Output

The command generates a comprehensive markdown report including:

- 📊 Quick statistics (total findings, critical issues, auto-fixable items)
- 📈 Agent performance breakdown
- 🚨 Priority issues requiring attention
- 💡 Actionable insights and trends
- 🛠️ Quick action suggestions

### Requirements

- Dev-agents must be running and monitoring the codebase
- Python virtual environment activated
- Context data available in `.claude/context/`

### Integration

This command automatically:
- Loads agent findings from the context store
- Applies intelligent filtering and grouping
- Generates contextual insights based on the codebase state
- Provides actionable recommendations for development workflow
