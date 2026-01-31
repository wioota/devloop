# DevLoop Claude Code Context Integration - Quick Fixes

**Date:** 2026-01-31
**Status:** Ready for Implementation
**Problem:** DevLoop agent findings are not being passed to Claude Code in a timely manner

---

## Problem Summary

DevLoop runs background agents (linter, formatter, test runner, etc.) that detect issues, but Claude Code doesn't see these findings because:

1. **Pull-based architecture** — Claude must manually request findings
2. **Session-start hook silently fails** — Errors swallowed with `2>/dev/null`
3. **Hooks not registered** — No `.claude/settings.json` configures the hooks
4. **No continuous updates** — No notification when new findings appear
5. **Stale context** — `devloop watch` may not be running

---

## Solution: Quick Fixes

Implement four targeted fixes to make the existing system work properly.

---

## Implementation Plan

### Task 1: Fix Session-Start Hook

**File:** `.agents/hooks/claude-session-start`

**Changes:**
- Remove silent error suppression (`2>/dev/null || exit 0`)
- Add explicit check for `devloop` installation
- Add warning if `devloop watch` not running
- Display loaded context clearly

**New implementation:**

```bash
#!/bin/bash
# SessionStart hook: Load DevLoop findings when Claude Code starts
#
# This makes DevLoop findings available in Claude's context at session start.
# Provides clear warnings if DevLoop is not properly configured.

set -e
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" || exit 0

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "DevLoop Context Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if devloop is available
if ! command -v devloop &>/dev/null; then
    echo "⚠️  DevLoop not installed"
    echo "   Install with: pip install devloop"
    echo "   Agent findings will not be available."
    exit 0
fi

# Check if devloop watch is running
if ! pgrep -f "devloop watch" >/dev/null 2>&1; then
    echo "⚠️  DevLoop watch not running"
    echo "   Start with: devloop watch ."
    echo "   Agent findings won't be collected until started."
    echo ""
fi

# Check context freshness
CONTEXT_INDEX="$PROJECT_DIR/.devloop/context/index.json"
if [[ -f "$CONTEXT_INDEX" ]]; then
    # Get age of context file
    if [[ "$OSTYPE" == "darwin"* ]]; then
        LAST_UPDATED=$(stat -f %m "$CONTEXT_INDEX" 2>/dev/null)
    else
        LAST_UPDATED=$(stat -c %Y "$CONTEXT_INDEX" 2>/dev/null)
    fi
    NOW=$(date +%s)
    AGE_MINUTES=$(( (NOW - LAST_UPDATED) / 60 ))

    if [[ $AGE_MINUTES -gt 30 ]]; then
        echo "🟡 Context is stale (${AGE_MINUTES}m old)"
    fi
fi

# Load and display context
echo ""
CONTEXT=$(devloop amp_context 2>&1) || {
    echo "⚠️  Failed to load context: $CONTEXT"
    exit 0
}

# Parse and display summary
CHECK_NOW=$(echo "$CONTEXT" | grep -o '"count": [0-9]*' | head -1 | grep -o '[0-9]*' || echo "0")

if [[ "$CHECK_NOW" -gt 0 ]]; then
    echo "🔴 $CHECK_NOW issue(s) need attention"
    echo "   Run /agent-summary for details"
else
    echo "🟢 No immediate issues from agents"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit 0
```

---

### Task 2: Register Hooks in Claude Settings

**File:** `.claude/settings.json` (create new)

**Purpose:** Tell Claude Code which hooks to run and when.

**Implementation:**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "./.agents/hooks/claude-session-start"
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "./.agents/hooks/claude-stop"
      }
    ],
    "PreToolUse": [
      {
        "type": "command",
        "command": "./.agents/hooks/check-devloop-context",
        "toolNames": ["Bash", "Edit", "Write"]
      }
    ]
  }
}
```

**Note:** This file needs to be merged with any existing settings. The `settings.local.json` contains permissions but not hooks.

---

### Task 3: Create Lightweight Pre-Tool Context Check

**File:** `.agents/hooks/check-devloop-context` (create new)

**Purpose:** Quick check before file operations to surface new findings.

**Requirements:**
- Must complete in <100ms to avoid blocking workflow
- Only show warnings if there are actionable issues
- Don't repeat warnings within the same minute

**Implementation:**

```bash
#!/bin/bash
# Lightweight context check before tool use
# Must be FAST (<100ms) to avoid blocking workflow

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
CONTEXT_INDEX="$PROJECT_DIR/.devloop/context/index.json"
LAST_WARN_FILE="$PROJECT_DIR/.devloop/context/.last_warning"

# Skip if no context file
[[ ! -f "$CONTEXT_INDEX" ]] && exit 0

# Debounce: don't warn more than once per minute
if [[ -f "$LAST_WARN_FILE" ]]; then
    LAST_WARN=$(cat "$LAST_WARN_FILE" 2>/dev/null || echo "0")
    NOW=$(date +%s)
    if [[ $((NOW - LAST_WARN)) -lt 60 ]]; then
        exit 0
    fi
fi

# Quick check using grep (faster than jq/python)
CHECK_NOW=$(grep -o '"check_now":[^}]*"count": [0-9]*' "$CONTEXT_INDEX" 2>/dev/null | grep -o '[0-9]*$' || echo "0")

if [[ "$CHECK_NOW" -gt 0 ]]; then
    echo "⚠️  DevLoop: $CHECK_NOW issue(s) from background agents"
    echo "   Run /agent-summary for details"

    # Update last warning time
    date +%s > "$LAST_WARN_FILE" 2>/dev/null || true
fi

exit 0
```

---

### Task 4: Add Last-Update Marker in AgentManager

**File:** `src/devloop/core/manager.py`

**Purpose:** Write a marker file after findings update so hooks can detect changes quickly without parsing JSON.

**Changes to `_listen_for_agent_completion` method (around line 235):**

```python
async def _listen_for_agent_completion(self, queue: asyncio.Queue):
    """Listen for agent completion events and update consolidated results."""
    import time

    while True:
        event = await queue.get()
        try:
            # Update consolidated results for Claude Code integration
            await context_store._update_index()

            # Write a marker file for hooks to detect recent updates quickly
            marker_file = self.project_dir / ".devloop" / "context" / ".last_update"
            try:
                agent_name = event.payload.get("agent_name", "unknown") if hasattr(event, "payload") else "unknown"
                marker_file.write_text(f"{time.time()}\n{agent_name}\n")
            except Exception:
                pass  # Non-critical, don't fail on marker write

        except Exception as e:
            self.logger.error(f"Failed to write consolidated results: {e}")
        finally:
            queue.task_done()
```

---

### Task 5: Enhance DevLoop Status Check

**File:** `.agents/hooks/check-devloop-status` (modify existing)

**Purpose:** Comprehensive status check that can be called manually or from other hooks.

**Implementation:**

```bash
#!/bin/bash
# Check if devloop watch is running and context is fresh

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
CONTEXT_INDEX="$PROJECT_DIR/.devloop/context/index.json"
MAX_STALE_MINUTES=30

echo "DevLoop Status Check"
echo "━━━━━━━━━━━━━━━━━━━━"

# Check 1: Is devloop watch process running?
if pgrep -f "devloop watch" >/dev/null 2>&1; then
    WATCH_PID=$(pgrep -f "devloop watch" | head -1)
    echo "🟢 devloop watch: Running (PID: $WATCH_PID)"
else
    echo "🔴 devloop watch: NOT running"
    echo "   → Start with: devloop watch ."
fi

# Check 2: Is context file present and fresh?
if [[ -f "$CONTEXT_INDEX" ]]; then
    # Get file age
    if [[ "$OSTYPE" == "darwin"* ]]; then
        LAST_UPDATED=$(stat -f %m "$CONTEXT_INDEX" 2>/dev/null)
    else
        LAST_UPDATED=$(stat -c %Y "$CONTEXT_INDEX" 2>/dev/null)
    fi
    NOW=$(date +%s)
    AGE_MINUTES=$(( (NOW - LAST_UPDATED) / 60 ))

    if [[ $AGE_MINUTES -gt $MAX_STALE_MINUTES ]]; then
        echo "🟡 Context: Stale (${AGE_MINUTES}m since last update)"
        echo "   → Agents may not be running properly"
    else
        echo "🟢 Context: Fresh (${AGE_MINUTES}m ago)"
    fi

    # Show finding counts
    CHECK_NOW=$(grep -o '"check_now":[^}]*"count": [0-9]*' "$CONTEXT_INDEX" 2>/dev/null | grep -o '[0-9]*$' || echo "0")
    RELEVANT=$(grep -o '"mention_if_relevant":[^}]*"count": [0-9]*' "$CONTEXT_INDEX" 2>/dev/null | grep -o '[0-9]*$' || echo "0")

    echo ""
    echo "Findings:"
    echo "  Immediate: $CHECK_NOW"
    echo "  Relevant:  $RELEVANT"
else
    echo "🟡 Context: No index file found"
    echo "   → Run: devloop watch . to start"
fi

echo ""
```

---

## File Summary

| File | Action | Description |
|------|--------|-------------|
| `.agents/hooks/claude-session-start` | Modify | Fix silent failures, add status checks |
| `.claude/settings.json` | Create | Register hooks with Claude Code |
| `.agents/hooks/check-devloop-context` | Create | Fast pre-tool context check |
| `.agents/hooks/check-devloop-status` | Modify | Enhanced status detection |
| `src/devloop/core/manager.py` | Modify | Add `.last_update` marker file |

---

## Testing Plan

1. **Session-start hook:**
   - Start new Claude Code session
   - Verify DevLoop status is displayed
   - Test with `devloop watch` running and not running
   - Test with stale context file

2. **Hook registration:**
   - Verify hooks fire at correct times
   - Check PreToolUse doesn't add noticeable latency

3. **Context updates:**
   - Save a file with linting errors
   - Verify warning appears on next tool use
   - Check debouncing works (no spam)

4. **Status check:**
   - Run `.agents/hooks/check-devloop-status` manually
   - Verify accurate reporting of watch status and context freshness

---

## Future Improvements (Out of Scope)

After these quick fixes are working:

1. **MCP Server Integration** — Build proper real-time bidirectional communication
2. **PostToolUse Hook** — Show relevant findings after file modifications
3. **Automatic `devloop watch` Start** — Start watch daemon on session start if not running
4. **Finding Deduplication** — Avoid showing the same finding multiple times

---

## Success Criteria

- [ ] Claude Code shows DevLoop status on session start
- [ ] Warnings appear if `devloop watch` not running
- [ ] New agent findings surface within 60 seconds
- [ ] No noticeable latency impact on normal workflow
- [ ] Clear error messages instead of silent failures
