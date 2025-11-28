# Claude Code Integration Guide

## Overview

This guide explains how to integrate claude-agents' context store with Claude Code, enabling intelligent, LLM-driven surfacing of background agent findings during development.

## Quick Start

### 1. Enable Background Agents

```bash
# Start agents in the background
cd /your/project
claude-agents watch .
```

### 2. Configure Claude Code Hooks (Optional)

Add to your Claude Code settings to automatically check context after file operations:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "reminder",
            "message": "Check .claude/context/index.json for any issues in files you just modified"
          }
        ]
      }
    ]
  }
}
```

### 3. Use Context in Conversations

Claude Code can read `.claude/context/index.json` to understand current issues:

**User:** "Are there any issues I should know about?"

**Claude checks:** `.claude/context/index.json`

**Claude responds:** "Yes, there are 2 warnings in auth.py and 3 style issues that can be auto-fixed. Would you like me to address them?"

## How It Works

### Context Flow

```
┌─────────────────┐
│  File Changes   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Background Agents│ (linter, formatter, tests)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Context Store  │ (relevance scoring)
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
immediate.json  relevant.json  background.json
    │         │         │
    └────┬────┴────┬────┘
         │         │
         ▼         ▼
    index.json  (summary)
         │
         ▼
  ┌──────────────┐
  │ Claude Code  │ (LLM decides when to surface)
  └──────────────┘
```

### Context Tiers

1. **immediate.json** - Blocking issues (build errors, type errors)
   - Show immediately in response
   - High priority

2. **relevant.json** - Non-blocking issues worth mentioning
   - Surface at task completion
   - Medium priority

3. **background.json** - Minor issues, available on request
   - Only show if explicitly asked
   - Low priority

4. **auto_fixed.json** - Log of silent fixes
   - Informational only

5. **index.json** - Quick summary for LLM
   - Fast to read
   - Guides decision-making

## LLM Decision Framework

### When Claude Code Should Check Context

#### 1. Post-Tool Execution (Automatic)

**After Edit or Write tools:**
```
User: "Add error handling to the login function"

[Claude uses Edit tool]

[Claude checks: .claude/context/index.json]

{
  "check_now": {
    "count": 1,
    "preview": "Type error in auth.py:42"
  }
}

[Claude's response:]
"Added error handling to the login function. I noticed a type error
on line 42 - the 'user' parameter is missing a type annotation.
Should I add that while we're here?"
```

**Decision Rule:**
- Check `index.json` after Edit/Write
- If `check_now.count > 0` AND file matches current work → Surface findings
- If `mention_if_relevant.count > 0` → Brief mention

#### 2. Completion Signals (User-Triggered)

**User signals:**
- "done", "finished", "that's it", "looks good"
- "commit this", "ready to commit", "ship it"
- "what's next?", "anything else?"

**Claude's action:**
```
User: "That should do it for the auth feature"

[Claude checks: .claude/context/relevant.json]

{
  "count": 5,
  "summary": "2 warnings, 3 style issues"
}

[Claude's response:]
"Auth feature complete! Before we commit, found:
- 2 warnings in auth.py (error handling patterns)
- 3 style issues (I can auto-fix these)

Want me to clean those up, or commit as-is?"
```

**Decision Rule:**
- Check `relevant.json` on completion signals
- Provide actionable summary
- Offer to fix

#### 3. Semantic Relevance (Question-Triggered)

**User asks about errors/issues:**
```
User: "Why is the build failing?"

[Claude checks: .claude/context/immediate.json]

{
  "count": 2,
  "preview": "2 error in test_auth.py"
}

[Claude's response:]
"The build is failing because of 2 test failures in test_auth.py:
- test_login_invalid_credentials (line 45)
- test_logout_session_cleanup (line 67)

Both started failing after we changed the session handling.
Let me check what's wrong..."
```

**Decision Rule:**
- User question matches finding category → Check that context
- Examples:
  - "Why failing?" → immediate.json (errors)
  - "Any warnings?" → relevant.json (warnings)
  - "Test results?" → Filter for test-runner findings

#### 4. Context Switches (Workflow-Triggered)

**Moving to different work:**
```
User: "Now let's work on the database layer"

[Claude detects topic switch]
[Claude checks: relevant.json for previous work]

[Claude's response:]
"Sure, let's work on the database layer. FYI: there are 3 deferred
items from the auth work (2 warnings, 1 style issue). We can come
back to those later."
```

**Decision Rule:**
- On topic/scope change: Briefly summarize deferred items
- Don't block, just inform

### When NOT to Check Context

**Avoid checking context when:**
- User asking unrelated questions ("what's the weather?")
- Every single message (too verbose)
- During active rapid coding (interrupts flow)
- For auto-fixable style issues (handle silently)
- In the middle of explaining something

## Reading Context Files

### Quick Check (Recommended)

```python
# Read the index for fast decision-making
index = json.loads(Path(".claude/context/index.json").read_text())

if index["check_now"]["count"] > 0:
    # Surface immediate issues
    print(f"Found {index['check_now']['count']} immediate issues")
    print(f"Preview: {index['check_now']['preview']}")

if index["mention_if_relevant"]["count"] > 0:
    # Consider mentioning at breakpoint
    print(f"Also: {index['mention_if_relevant']['summary']}")
```

### Detailed Check (When Needed)

```python
# Read specific tier for details
immediate = json.loads(Path(".claude/context/immediate.json").read_text())

for finding in immediate["findings"]:
    print(f"{finding['severity']} in {finding['file']}:{finding['line']}")
    print(f"  {finding['message']}")
    if finding['auto_fixable']:
        print(f"  [Can auto-fix]")
```

## Response Templates

### Template 1: Surfacing Immediate Issues

```
[After Edit tool]

"Added the [feature].

⚠️  Found 1 immediate issue in the file I just edited:
- Type error on line 42: missing type annotation

Should I fix that now?"
```

### Template 2: Task Completion Summary

```
[After completion signal]

"[Feature] complete!

Before committing:
✓ All tests passing
⚠️  2 warnings to review
🔧 3 style issues (I can auto-fix)

Ready to commit as-is, or want me to address those warnings?"
```

### Template 3: Answering Direct Questions

```
User: "Any issues in auth.py?"

"Yes, found 3 items in auth.py:
1. Warning (line 23): Unused import 'datetime'
2. Warning (line 45): Deprecated API usage
3. Style (line 67): Missing trailing comma

Want me to fix these?"
```

### Template 4: Context Switch Mention

```
[User switches topic]

"Sure, let's work on [new topic].

(FYI: 2 deferred items from previous work - we can handle those later)

For [new topic], should we..."
```

### Template 5: No Issues Found

```
[After check]

"No issues found! The code looks clean."
```

## Configuration Modes

Users can configure how aggressive context checking should be:

### Flow Mode (Minimal Interruption)
```json
{
  "contextStore": {
    "mode": "flow",
    "interrupt_threshold": "error_blocking_only",
    "auto_fix_style": true,
    "defer_warnings": true
  }
}
```

**LLM behavior:**
- Only surface blocking errors immediately
- Auto-fix style silently
- Defer warnings to completion signal

### Balanced Mode (Default)
```json
{
  "contextStore": {
    "mode": "balanced",
    "interrupt_threshold": "error",
    "auto_fix_style": false,
    "defer_warnings": false
  }
}
```

**LLM behavior:**
- Surface errors immediately
- Mention warnings at breakpoints
- Ask before auto-fixing

### Quality Mode (Maximum Awareness)
```json
{
  "contextStore": {
    "mode": "quality",
    "interrupt_threshold": "warning",
    "show_all_immediately": true
  }
}
```

**LLM behavior:**
- Surface warnings immediately
- Show all findings
- Proactive about code quality

## Best Practices

### DO:
✅ Check context after file modifications
✅ Surface blocking issues immediately
✅ Summarize at task completion
✅ Offer to fix when appropriate
✅ Keep mentions brief and actionable
✅ Respect the user's flow state

### DON'T:
❌ Check context on every message
❌ Interrupt rapid coding for style issues
❌ Show pre-existing issues unrelated to current work
❌ Be verbose about minor issues
❌ Force fixes without asking
❌ Repeat the same finding multiple times

## Example Conversation

```
User: "Add authentication to the API"

Claude: "I'll add authentication to the API."
[Uses Edit tool to add auth code]
[Checks: .claude/context/index.json]
[Sees: 0 immediate, 0 relevant]

Claude: "Added authentication with JWT tokens. The code includes:
- Login endpoint with credential validation
- JWT token generation
- Protected route middleware

All checks passed - no issues found!"

---

User: "done"

Claude: [Checks: .claude/context/relevant.json]
[Sees: 2 style issues in files just edited]

Claude: "Great! Before we commit:
- Found 2 style issues (import ordering)
- I can auto-fix these in 1 second

Want me to clean those up?"

User: "yes"

Claude: [Fixes issues]
[Verifies: .claude/context/index.json shows 0 issues]

Claude: "✓ Style issues fixed. Ready to commit!"

---

User: "commit it"

Claude: [Runs git commit]
[Final check: .claude/context/relevant.json]
[Sees: all clear]

Claude: "✓ Committed: 'Add JWT authentication to API'
All checks passing - clean commit!"
```

## Troubleshooting

### Context Not Updating

**Problem:** Files don't exist in `.claude/context/`

**Solution:**
```bash
# Ensure agents are running
claude-agents watch .

# Check that context directory was created
ls -la .claude/context/

# Manually initialize if needed
mkdir -p .claude/context
```

### Too Many Interruptions

**Problem:** Claude mentions findings too often

**Solution:**
```json
// Set to flow mode
{
  "contextStore": {
    "mode": "flow"
  }
}
```

### Missing Important Issues

**Problem:** Blocking errors not surfaced

**Solution:**
- Check that `immediate.json` exists
- Verify agents are running
- Ensure file patterns include your files

## Advanced: Custom Queries

### Filter by File

```python
# Get findings for specific file
relevant = json.loads(Path(".claude/context/relevant.json").read_text())
auth_findings = [
    f for f in relevant["findings"]
    if f["file"].endswith("auth.py")
]
```

### Filter by Category

```python
# Get only type errors
findings = json.loads(Path(".claude/context/immediate.json").read_text())
type_errors = [
    f for f in findings["findings"]
    if "type" in f["category"]
]
```

### Check Test Status

```python
# Get test results
findings = json.loads(Path(".claude/context/immediate.json").read_text())
test_findings = [
    f for f in findings["findings"]
    if f["agent"] == "test-runner"
]

passed = sum(1 for f in test_findings if "passed" in f["message"])
failed = sum(1 for f in test_findings if "failed" in f["message"])
```

## Future Enhancements

Planned improvements:
- Flow state detection (reduce interruptions during rapid coding)
- Learning from user actions (which findings they act on)
- Multi-project context (share patterns across projects)
- Predictive surfacing (anticipate what user will ask about)

## Support

For issues or questions:
- Check [TESTING_PLAN.md](./TESTING_PLAN.md) for testing guidance
- Review [CONTEXT_STORE_DESIGN.md](./CONTEXT_STORE_DESIGN.md) for architecture
- See [CLAUDE.md](../CLAUDE.md) for overall system design

---

**Remember:** The goal is to enhance developer flow, not interrupt it. When in doubt, defer findings to natural breakpoints.
