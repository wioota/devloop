# Claude Code Hooks Implementation Review

## Summary

The current implementation takes a **CLI-only approach** for Claude Code integration, treating it as a programmatic tool that users manually invoke. However, Claude Code actually provides **native hook events** that could automate verification at key lifecycle points. This review identifies the gap and recommends realignment with Claude Code's actual capabilities.

---

## Current Implementation

### What Was Built

The `ClaudeCodeAdapter` provides:
- **Query methods** for accessing DevLoop findings (`check_results`, `get_detailed_findings`, `get_agent_insights`)
- **Action methods** for manual verification (`run_verification`, `extract_findings`, `verify_and_extract`)
- **CLI/Programmatic interface** via slash commands and `devloop verify-work` CLI command
- **Manual triggering pattern**: User runs command → adapter executes verification → reports results

### Architecture

```
User runs: /verify-work (slash command)
    ↓
Claude Code invokes: devloop verify-work (CLI)
    ↓
ClaudeCodeAdapter.verify_and_extract()
    ↓
Runs .agents/verify-common-checks (blocking issues only)
    ↓
Runs .agents/hooks/extract-findings-to-beads
    ↓
Returns: JSON results to Claude Code
```

### Integration Points

- **Slash commands** (manual): `/verify-work`, `/extract-findings`
- **CLI commands** (manual): `devloop verify-work`, `devloop extract-findings`
- **No automated hooks** (missing the native Claude Code hook system)

---

## Claude Code Hook Events Available

Based on official documentation, Claude Code supports these hook events:

| Event | Timing | Use Case | Can Block |
|-------|--------|----------|-----------|
| **PreToolUse** | Before any tool call | Validate/prevent tool usage | Yes ✅ |
| **PostToolUse** | After any tool call | Log/verify tool results | No |
| **PermissionRequest** | Before permission dialogs | Auto-approve/deny | Yes ✅ |
| **UserPromptSubmit** | Before Claude processes user input | Inject context/validate | Yes ✅ |
| **Stop** | After Claude finishes responding | Trigger actions on completion | Yes ✅ |
| **SubagentStop** | After subagent completes | Trigger actions on task end | Yes ✅ |
| **Notification** | When showing notifications | Customize notifications | No |
| **SessionStart** | When session begins | Load context/setup | N/A |
| **SessionEnd** | When session closes | Cleanup/reporting | N/A |
| **PreCompact** | Before context compaction | Take actions before cleanup | N/A |

---

## Gap Analysis: Implementation vs Capabilities

### Missed Opportunities

**1. SessionStart Hook (Session Initialization)**
- **Current**: No automation
- **Could do**: Pre-load DevLoop findings when Claude Code starts
  ```json
  {
    "SessionStart": {
      "hooks": [{
        "type": "command",
        "matcher": "startup",
        "command": "$CLAUDE_PROJECT_DIR/.agents/hooks/session-start"
      }]
    }
  }
  ```
- **Benefit**: DevLoop findings available immediately without manual command

**2. Stop Hook (Claude Code Completion)**
- **Current**: No automation
- **Could do**: Auto-run verification when Claude finishes responding
  ```json
  {
    "Stop": {
      "hooks": [{
        "type": "command",
        "command": "$CLAUDE_PROJECT_DIR/.agents/hooks/claude-stop"
      }]
    }
  }
  ```
- **Benefit**: Verification runs automatically, similar to Git/Amp workflows
- **Best for**: Code changes that should be verified before user reviews

**3. SubagentStop Hook (Task Completion)**
- **Current**: No automation
- **Could do**: Extract findings and create Beads issues when task completes
  ```json
  {
    "SubagentStop": {
      "hooks": [{
        "type": "command",
        "command": "$CLAUDE_PROJECT_DIR/.agents/hooks/subagent-stop"
      }]
    }
  }
  ```
- **Benefit**: Similar enforcement pattern to Amp post-task hook

**4. PreToolUse Hook (Tool Permission/Validation)**
- **Current**: No enforcement
- **Could do**: Block file writes to protected files (e.g., .beads/)
  ```json
  {
    "PreToolUse": {
      "hooks": [{
        "type": "command",
        "matcher": "Write",
        "command": "$CLAUDE_PROJECT_DIR/.agents/hooks/file-protection"
      }]
    }
  }
  ```
- **Benefit**: Prevent accidental modifications to tracking/config files

**5. UserPromptSubmit Hook (Context Injection)**
- **Current**: No automation
- **Could do**: Inject DevLoop findings into Claude's context when user asks
  ```json
  {
    "UserPromptSubmit": {
      "hooks": [{
        "type": "command",
        "command": "$CLAUDE_PROJECT_DIR/.agents/hooks/inject-findings"
      }]
    }
  }
  ```
- **Benefit**: Claude always aware of recent quality findings without explicit request

---

## Recommended Implementation Strategy

### Phase 1: Session-based Automation (High Impact)

**Add SessionStart hook** to pre-load findings on session start:

```bash
# .agents/hooks/session-start
#!/bin/bash
# Pre-load DevLoop findings when Claude Code starts
cd "$CLAUDE_PROJECT_DIR"
devloop amp_context 2>/dev/null || true
```

**Add Stop hook** for automatic verification:

```bash
# .agents/hooks/claude-stop
#!/bin/bash
# Verify code quality when Claude finishes responding
# Non-blocking - just collect findings for next session
cd "$CLAUDE_PROJECT_DIR"
devloop amp_findings 2>/dev/null || true
```

This makes Claude Code's verification pattern closer to **Amp's post-task hook** but with auto-trigger on completion.

### Phase 2: Protection & Safety (Medium Impact)

**Add PreToolUse hook** to protect sensitive files:

```bash
# .agents/hooks/file-protection
#!/bin/bash
# Block modifications to .beads/ and other protected files
# Input: JSON via stdin with file paths being modified

PROTECTED_PATHS=".beads/ .devloop/ .git/"
# Parse JSON and check if any protected files would be modified
```

This prevents accidental modifications to DevLoop state files.

### Phase 3: Context Enrichment (Nice to Have)

**Add UserPromptSubmit hook** to inject findings into context when relevant:

```bash
# .agents/hooks/inject-findings
#!/bin/bash
# If user is asking about code quality, inject recent findings
# This makes findings "visible" without explicit command
```

---

## Architecture Realignment

### Current (CLI-Only)

```
Git/Amp: Automatic → Hook System
Claude Code: Manual → CLI Commands
```

### Recommended (Native Hooks)

```
Git: Automatic → .git/hooks
Amp: Automatic → .agents/hooks/post-task
Claude Code: Automatic → .claude/settings.json hooks
```

### Benefits

1. **Consistent timing**: All three systems verify at completion points
2. **Reduced friction**: Users don't need to remember `/verify-work` command
3. **Better integration**: Hooks can inject findings, block dangerous actions, etc.
4. **Same enforcement**: Identical verification logic across all workflows

---

## Implementation Priority

### Must Have (Breaks Current Assumption)

**SessionStart + Stop hooks** - Makes Claude Code work similar to Git/Amp automation:
- ✅ Auto-load findings on session start (non-blocking)
- ✅ Auto-collect findings on completion (non-blocking)
- ✅ No user action required
- ✅ Native to Claude Code's architecture

### Should Have (Safety/Protection)

**PreToolUse hook** - Prevents accidental damage:
- ✅ Block writes to `.beads/`, `.devloop/` configuration
- ✅ Provide helpful suggestions when files would be modified

### Nice to Have (Polish)

**UserPromptSubmit hook** - Context enrichment:
- ✅ Inject findings into context when relevant
- ✅ Make findings visible without explicit request

---

## Execution Plan

### Step 1: Create Hook Scripts

Create new scripts in `.agents/hooks/`:

```bash
.agents/hooks/
├── session-start        # Pre-load findings on startup
├── claude-stop         # Collect findings on completion
├── file-protection     # Block protected files
└── inject-findings     # Context enrichment (future)
```

### Step 2: Update Settings Template

Update Claude Code settings template to register hooks:

```json
{
  ".claude/settings.json": {
    "hooks": {
      "SessionStart": {
        "hooks": [{
          "type": "command",
          "matcher": "startup",
          "command": "$CLAUDE_PROJECT_DIR/.agents/hooks/session-start"
        }]
      },
      "Stop": {
        "hooks": [{
          "type": "command",
          "command": "$CLAUDE_PROJECT_DIR/.agents/hooks/claude-stop"
        }]
      },
      "PreToolUse": {
        "hooks": [{
          "type": "command",
          "matcher": "Write",
          "command": "$CLAUDE_PROJECT_DIR/.agents/hooks/file-protection"
        }]
      }
    }
  }
}
```

### Step 3: Update Documentation

- Update `AMP_ONBOARDING.md` with Claude Code hooks section
- Update `AGENTS.md` with native hook architecture
- Add `.agents/hooks/README.md` explaining hook events

### Step 4: Keep CLI as Fallback

Don't remove CLI commands - keep them as:
- Manual override for users who prefer explicit control
- Fallback for local Claude Code CLI (hooks may have limitations)
- Integration with other tools that invoke DevLoop

---

## Key Decisions

### Why Not Block on Stop?

**Current approach**: Non-blocking verification on Stop hook
- **Reason**: Claude Code is still running. If we block, Claude can't save/push
- **Behavior**: Collects findings silently, available for next session

**Alternative**: Blocking verification (not recommended)
- **Issue**: Would prevent Claude from committing changes
- **Conflicts**: With Amp's non-blocking post-task approach

### Why Start with SessionStart + Stop?

- **SessionStart**: Pre-loads context (non-blocking, safe)
- **Stop**: Collects findings automatically (non-blocking, safe)
- Together: Mimic Git/Amp automation without blocking

### Why Keep CLI Commands?

- **Fallback**: Users who prefer manual control
- **Debugging**: Can invoke directly without hooks
- **Integration**: Other tools can call `devloop verify-work`
- **Portability**: Works with Claude Code CLI (not web)

---

## Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| Hooks timeout during verification | Set reasonable timeout (30-60s), non-blocking |
| Hooks output interferes with Claude | Minimize output, only stderr for blocking decisions |
| Users don't understand hooks | Document in setup and AMP_ONBOARDING.md |
| Hooks break on different machines | Use `$CLAUDE_PROJECT_DIR` environment variable |
| Users disable hooks accidentally | Include verification reminder in SessionStart |

---

## Testing Strategy

1. **Manual testing**: Register hooks in `.claude/settings.json` and test each event
2. **Timeout testing**: Verify hooks respect timeout limits
3. **Error handling**: Test hook failures don't break Claude Code
4. **Integration testing**: Verify findings are correctly loaded/saved
5. **Documentation**: Ensure setup instructions work on clean install

---

## Summary

**Finding**: Claude Code provides native hook events that can automate verification similar to Git and Amp, but current implementation only uses manual CLI commands.

**Recommendation**: Implement SessionStart and Stop hooks to achieve consistent automation across all three systems (Git, Amp, Claude Code).

**Impact**: 
- ✅ Better user experience (no manual verification step)
- ✅ Consistent with Git/Amp patterns
- ✅ Automatic findings collection
- ✅ Maintains safety (non-blocking, non-intrusive)

**Effort**: 3-4 new hook scripts + settings template + documentation updates (~1-2 hours)

**Priority**: Should implement before considering Claude Code integration complete.
