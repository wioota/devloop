# Claude Code Integration Guide

## Overview

Claude-agents now provides seamless integration with Claude Code, allowing background agents to provide real-time code quality insights as you work.

## How It Works

1. **Background Agents Run**: Agents automatically analyze your code on file changes
2. **Results Stored**: Each agent writes findings to `.claude/context/{agent-name}.json`
3. **Consolidated View**: System creates `.claude/context/agent-results.json` with unified results
4. **Claude Code Access**: Use adapter to query agent insights during coding sessions

## Setup

### 1. Start Background Agents

```bash
# In your project directory
dev-agents watch .
```

### 2. Query Agent Results

Use the Claude Code adapter to check background agent findings:

```bash
# Check all agent results
python3 .claude/integration/claude-code-adapter.py check_results

# Get specific insights
python3 .claude/integration/claude-code-adapter.py insights --query-type lint
python3 .claude/integration/claude-code-adapter.py insights --query-type test
python3 .claude/integration/claude-code-adapter.py insights --query-type security
```

## Using with Claude Code

### Manual Queries

Ask Claude Code to check background agent results:

- "Check background agent results for any issues"
- "What do the linters say about my recent changes?"
- "Show me test results from background agents"
- "Are there security findings I should address?"

### Integration via Hooks (Optional)

Add to your Claude Code settings to automatically check agent results after file edits:

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

## Context Files

### Individual Agent Results

Each agent writes to its own file:
- `.claude/context/linter.json` - Linting issues
- `.claude/context/formatter.json` - Formatting suggestions
- `.claude/context/test-runner.json` - Test results
- `.claude/context/type-checker.json` - Type errors
- `.claude/context/security-scanner.json` - Security vulnerabilities
- `.claude/context/performance-profiler.json` - Performance insights
- `.claude/context/git-commit-assistant.json` - Commit message suggestions

### Consolidated Results

`.claude/context/agent-results.json` provides unified view:

```json
{
  "timestamp": "2025-10-25T22:58:34.441904",
  "agents": {
    "linter": {
      "status": "success",
      "timestamp": "...",
      "message": "Found 3 issues",
      "results": {
        "issues_found": 3,
        "auto_fixable": 2,
        "files_checked": 1
      }
    },
    "test-runner": {
      "status": "success",
      "results": {
        "passed": 10,
        "failed": 0,
        "total": 10
      }
    }
  }
}
```

## Adapter API

### check_results()

Returns summary of agent findings:

```json
{
  "status": "success",
  "timestamp": "...",
  "agents_run": 5,
  "actionable_items": [
    {
      "type": "lint_issues",
      "count": 3,
      "auto_fixable": 2,
      "priority": "medium"
    }
  ],
  "summary": "Background agents completed: linter: 3 issues, tests: 10 passed, 0 failed"
}
```

### get_agent_insights(query_type)

Returns specific insights:

**query_type="lint"**:
- Lint issues found
- Auto-fixable count
- Recommendations

**query_type="test"**:
- Test pass/fail status
- Coverage information
- Failed test details

**query_type="security"**:
- Vulnerabilities found
- Severity breakdown
- Remediation suggestions

## Workflow Examples

### Example 1: Pre-Commit Check

```
You: "I'm ready to commit. Check if there are any issues."

Claude Code: [Reads .claude/context/agent-results.json]
"The linter found 2 auto-fixable issues in auth.py.
All 15 tests are passing. No security issues detected.
Let me fix the linting issues first..."
```

### Example 2: Code Review

```
You: "Review my recent changes to user.py"

Claude Code: [Reads agent results]
"Looking at the background agent analysis:
- Linter: Line 45 has unused import 'sys'
- Type Checker: Missing return type annotation on line 67
- Security: No issues found
- Tests: All related tests passing

Let me help you address these..."
```

### Example 3: Debugging

```
You: "Tests are failing, help me debug"

Claude Code: [Reads test-runner.json]
"The test runner shows 2 failures in test_auth.py:
1. test_invalid_token: KeyError on line 23
2. test_expired_token: AssertionError

Let me examine the auth.py code..."
```

## Benefits

1. **Real-Time Feedback**: Get instant insights without manual checks
2. **Context-Aware Assistance**: Claude Code knows about issues before you ask
3. **Proactive Suggestions**: Agent findings inform Claude Code's recommendations
4. **Reduced Context Switching**: No need to run separate linting/testing commands
5. **Comprehensive Analysis**: Multiple agents provide different perspectives

## Troubleshooting

**No results showing**:
- Ensure `dev-agents watch` is running
- Check `.claude/context/` directory exists
- Verify agents are enabled in `.claude/agents.json`

**Outdated results**:
- Agent results update on file changes
- Save a file to trigger fresh analysis
- Manually run: `dev-agents run all`

**Missing agent-results.json**:
- File is created when agents complete
- Trigger manually: `python3 -c "from dev_agents.core.context_store import context_store; context_store.write_consolidated_results()"`

## Advanced Usage

### Custom Queries

Extend the adapter for project-specific needs:

```python
from dev_agents.core.context_store import context_store

# Get raw findings
findings = context_store.get_findings()

# Filter by agent
linter_findings = context_store.get_findings("linter")

# Get actionable items only
actionable = context_store.get_actionable_findings()
```

### Integration with Other Tools

Use agent results in CI/CD, git hooks, or custom scripts:

```bash
# In git pre-commit hook
results=$(python3 .claude/integration/claude-code-adapter.py check_results)
if echo "$results" | grep -q '"priority": "high"'; then
  echo "High priority issues found!"
  exit 1
fi
```

## See Also

- [Agent Types](./AGENTS.md) - Description of available agents
- [Configuration](./README.md) - Agent configuration options
- [CLAUDE.md](./CLAUDE.md) - Full Claude Code integration details
