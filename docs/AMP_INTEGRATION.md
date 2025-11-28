# Amp Integration Guide

## Overview

This guide explains how to integrate dev-agents' context store with Amp, enabling intelligent surfacing of background agent findings during development sessions.

## Quick Start

### 1. Enable Background Agents

```bash
# Start agents in the background
cd /your/project
dev-agents watch .
```

### 2. Amp Context Access

Amp can read agent findings through two methods:

#### Method A: Direct Context File Access (Recommended)

Amp can read the context index file directly:

```bash
# Check for immediate issues
cat .claude/context/index.json
```

The index file contains:
- `check_now`: Critical issues requiring immediate attention
- `mention_if_relevant`: Issues to mention during relevant tasks  
- `deferred`: Background issues available on request
- `auto_fixed`: Issues that were automatically resolved

#### Method B: Amp Subagent Commands

Amp can execute subagent commands to get agent information:

```
check_agent_findings() - Get summary of all agent findings
apply_autonomous_fixes() - Apply safe fixes automatically
show_agent_status() - Show current agent activity
```

## How It Works

### Context Store Structure

```
.claude/context/
├── index.json          # LLM-optimized summary for quick reading
├── immediate.json      # Critical blocking issues
├── relevant.json       # Task-relevant findings  
├── background.json     # Background issues
└── auto_fixed.json     # Automatically resolved issues
```

### Three-Tier Context System

1. **Immediate**: Show now, blocking issues (errors, critical warnings)
2. **Relevant**: Mention during relevant tasks (style issues, optimizations)  
3. **Background**: Show only when requested (informational findings)

### Relevance Scoring

Findings are prioritized based on:
- **File Context**: Currently editing vs. recently modified
- **Severity**: Error > Warning > Info > Style
- **Freshness**: Recent changes get higher priority
- **User Intent**: Matches current development tasks

## Usage Examples

### Check for Issues

**Amp Query:** "Are there any issues with the code I just wrote?"

**Amp should check:** `.claude/context/index.json`

**Amp can respond:** "The linter found 2 issues in auth.py: missing type annotations on lines 15-17. Would you like me to fix them?"

### During Development

**Amp Query:** "Help me implement the user authentication feature"

**Amp should check:** Context for relevant security findings

**Amp can respond:** "I see there are some security scan results for authentication code. Let me review those while we implement this feature."

### Post-Commit Checks

**Amp Query:** "Did the tests pass?"

**Amp should check:** Test runner findings in context

**Amp can respond:** "The test runner found 3 failing tests in the new authentication module. Here's what failed..."

## Configuration

Add to your Amp configuration for automatic context checking:

```json
{
  "dev_agents": {
    "enabled": true,
    "context_check_interval": 30,
    "auto_fix_safety_level": "conservative"
  }
}
```

## Integration Commands

### check_agent_findings()

Returns comprehensive findings summary:
```json
{
  "summary": {
    "total_findings": 15,
    "actionable_findings": 8,
    "findings_by_agent": {"linter": 5, "test_runner": 3}
  },
  "all_findings": {...},
  "actionable_findings": {...}
}
```

### apply_autonomous_fixes()

Applies safe automatic fixes:
```json
{
  "message": "Applied 3 safe fixes: 2 linter fixes, 1 formatter fix",
  "applied_fixes": {"linter": 2, "formatter": 1},
  "total_applied": 3
}
```

### show_agent_status()

Shows current agent activity:
```json
{
  "agent_activity": {
    "linter": {
      "last_active": "2025-11-28T15:30:00Z",
      "last_message": "Found 2 issues in auth.py",
      "total_findings": 12
    }
  },
  "pending_actions": {"formatter": 3, "test_runner": 1},
  "recent_findings": {...}
}
```

## Best Practices

### When to Check Context

- **After file saves**: Check for immediate issues
- **Before commits**: Verify no blocking issues
- **During debugging**: Look for relevant findings
- **Code reviews**: Surface all findings for the files being reviewed

### Context-Aware Responses

Make responses context-aware:
- **With issues**: "I found some issues while implementing this..."
- **Without issues**: "The code looks good, but let me check if there are any optimization suggestions..."
- **Auto-fix available**: "There are some issues I can fix automatically. Should I proceed?"

### Progressive Disclosure

- **Immediate issues**: Always mention proactively
- **Relevant issues**: Mention when they relate to current work
- **Background issues**: Only when specifically asked

## Troubleshooting

### Context Not Updating

```bash
# Check if agents are running
dev-agents status

# Restart agents
dev-agents stop
dev-agents watch .
```

### No Findings Showing

```bash
# Check context directory exists
ls -la .claude/context/

# Verify agents have processed files
cat .claude/context/index.json
```

### Performance Issues

```bash
# Limit context retention
echo '{"contextStore": {"maxFindings": 100}}' > .claude/agents.json
```

---

**Status**: ✅ **Amp Integration Ready**

Amp can now access agent findings through both direct file access and subagent commands, enabling intelligent, context-aware development assistance.
