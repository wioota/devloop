# Claude Code Hooks - Critical Findings Summary

**Date**: 2025-12-09
**Review**: Claude Code native hooks vs current CLI-only implementation
**Status**: Gap identified, implementation plan created

---

## The Gap

**Current Implementation**: CLI-only (manual commands)
- `/verify-work` slash command
- `devloop verify-work` CLI
- User must explicitly trigger verification

**Claude Code Capability**: Native hook events (automatic)
- `SessionStart` - Run on session startup
- `Stop` - Run when Claude finishes
- `SubagentStop` - Run when task completes
- `PreToolUse` - Run before file writes
- + 5 other events

**Missing**: Integration with Claude Code's actual hook system

---

## Key Findings

### 1. SessionStart Hook Not Used ❌

Claude Code automatically triggers `SessionStart` when:
- Claude Code launches
- Session is resumed

**What we could do**:
```bash
# Pre-load DevLoop findings on startup
devloop amp_context  # Show findings immediately to Claude
```

**Current behavior**: No automation, requires manual `/verify-work` command

**Impact**: 
- 🔴 Medium - User must remember to run command
- 🟢 Can pre-load findings into Claude's context
- 🟢 Would reduce friction

### 2. Stop Hook Not Used ❌

Claude Code automatically triggers `Stop` when:
- Claude finishes responding
- After tool calls complete
- Before user provides next input

**What we could do**:
```bash
# Collect findings automatically after Claude's response
devloop amp_findings  # Store for next session (non-blocking)
```

**Current behavior**: No automation, findings only available on manual request

**Impact**:
- 🔴 High - Makes Claude Code inconsistent with Git/Amp patterns
- 🟢 Automatic verification (similar to Amp post-task)
- 🟢 Non-blocking (doesn't interfere)

### 3. SubagentStop Hook Not Used ❌

Claude Code automatically triggers `SubagentStop` when:
- Task tool completes
- Multi-step task finishes

**What we could do**:
```bash
# Extract findings to Beads issues automatically
devloop extract_findings_cmd
```

**Current behavior**: No automation, must manually extract findings

**Impact**:
- 🔴 Medium - Findings don't get filed as issues automatically
- 🟢 Similar to Amp post-task findings extraction
- 🟢 Automatic Beads issue creation

### 4. PreToolUse Hook Not Used ❌

Claude Code automatically triggers `PreToolUse` before:
- Write tool (create/edit files)
- Other tool calls

**What we could do**:
```bash
# Block writes to protected files
# - .beads/ (would corrupt issue state)
# - .devloop/ (would corrupt findings)
# - .git/ (would corrupt repo)
# - .agents/ (would corrupt hooks)
```

**Current behavior**: No protection, Claude could accidentally overwrite critical files

**Impact**:
- 🔴 High - Could cause data loss
- 🟢 Prevents accidental overwrites
- 🟢 Provides helpful error messages

### 5. Manual Verification Commands Still Needed ✅

The CLI commands (`devloop verify-work`, etc.) are good for:
- Explicit user control
- Debugging
- Integration with other tools
- Fallback when hooks unavailable

**Recommendation**: Keep CLI commands, add hooks for automation

---

## Architecture Comparison

### Git Workflow
```
file save → .git/hooks/pre-commit → verification
```
✅ Automatic, blocking, consistent

### Amp Workflow
```
task complete → .agents/hooks/post-task → verification
```
✅ Automatic, non-blocking, consistent

### Claude Code (Current)
```
Claude finishes → user runs /verify-work → verification
```
❌ Manual, inconsistent with other workflows

### Claude Code (Proposed)
```
Claude finishes → SessionStart/Stop hooks → verification
```
✅ Automatic, non-blocking, consistent with Amp

---

## Risk Assessment

### Breaking Changes

**None** - Hooks are additive:
- CLI commands keep working
- Existing workflows unaffected
- Opt-in during `devloop init`

### Safety Concerns

**Hook failures**: All hooks non-blocking
- If hook errors, Claude Code continues
- Errors logged in verbose mode (Ctrl+O)
- No data loss from hook failure

**File protection**: PreToolUse hook could be too strict
- Can whitelist specific use cases
- Provides helpful error messages
- Users can ask for manual edit

---

## Implementation Complexity

### High Priority (must have)

✅ SessionStart hook (load findings)
- 1 script (~20 lines)
- 0 dependencies
- No risk

✅ Stop hook (collect findings)
- 1 script (~30 lines)
- Requires `jq` for JSON parsing
- Non-blocking, safe

### Medium Priority (should have)

🟡 PreToolUse hook (file protection)
- 1 script (~60 lines)
- Requires `jq`
- Must be careful not to block legitimate edits

### Low Priority (nice to have)

🟢 UserPromptSubmit hook (inject findings)
- Future enhancement
- Automatic context enrichment
- Can defer to v2

---

## Recommended Action

### Phase 1: Implement SessionStart + Stop (Must Have)

**Effort**: 1-2 hours
**Scripts**: 2 new hook scripts
**Risk**: Very low (non-blocking)
**Benefit**: 
- Auto-load findings on startup
- Auto-collect findings on completion
- Aligns with Amp pattern

### Phase 2: Implement PreToolUse (Should Have)

**Effort**: 1 hour
**Scripts**: 1 new hook script
**Risk**: Low (has override mechanism)
**Benefit**:
- Prevents accidental file overwrites
- Protects DevLoop state
- Provides helpful guidance

### Phase 3: Keep CLI as Fallback

**Keep**: `/verify-work` and `devloop verify-work` commands
**Keep**: `devloop extract_findings_cmd` CLI
**Benefit**:
- Manual control when needed
- Integration with other tools
- Debugging aid

---

## Success Metrics

After implementing hooks:

✅ Claude Code behaves consistently with Git/Amp
✅ No manual `/verify-work` command needed for basic workflow
✅ Findings automatically collected on session completion
✅ Users cannot accidentally corrupt `.beads/` or `.devloop/`
✅ Fallback CLI commands still available
✅ Documentation clear on hook behavior

---

## Next Steps

1. ✅ Review this findings document (current task)
2. ⏳ Create hook scripts (`.agents/hooks/claude-*`)
3. ⏳ Update `devloop init` to create/register hooks
4. ⏳ Update documentation (AMP_ONBOARDING.md)
5. ⏳ Test on clean install
6. ⏳ Gather user feedback

---

## References

- **Claude Code Hooks Docs**: https://code.claude.com/docs/en/hooks
- **Review Document**: `CLAUDE_CODE_HOOKS_REVIEW.md`
- **Implementation Plan**: `CLAUDE_CODE_HOOKS_IMPLEMENTATION.md`
- **Current Implementation**: `src/devloop/core/claude_adapter.py`

---

## Questions to Address

**Q**: Why not use Stop hook for blocking verification?
**A**: Would prevent Claude from committing changes. Stop hook runs while Claude is still responding. Non-blocking allows save/push flow.

**Q**: How do hooks work with Claude Code web version?
**A**: Web version cannot use local hooks (no filesystem access). Hooks work with Claude Code CLI only.

**Q**: What if user disables hooks?
**A**: CLI commands still work. User can run `/verify-work` manually. Hooks are convenience, not requirement.

**Q**: How do we prevent hook infinite loops?
**A**: Stop hook checks `stop_hook_active` flag in input. SubagentStop hook only creates new issues (idempotent).

---

## Summary

Claude Code provides native hook events perfect for automating DevLoop verification. Current implementation misses this capability by only providing CLI commands. Implementing SessionStart and Stop hooks would:

✅ Align Claude Code with Git/Amp patterns
✅ Reduce user friction (no manual commands)
✅ Maintain safety (non-blocking)
✅ Keep CLI as fallback
✅ Add file protection (PreToolUse)

**Recommendation**: Implement Phase 1 (SessionStart + Stop) as part of standard setup. File protection (PreToolUse) can follow if safe.
