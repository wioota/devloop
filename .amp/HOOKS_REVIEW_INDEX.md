# Claude Code Hooks Review - Document Index

**Review Date**: 2025-12-09
**Reviewer**: Amp Code Agent
**Status**: Complete - Gap identified, implementation plan created

---

## Overview

Comprehensive review of Claude Code hooks implementation reveals **significant gap**: current implementation provides only manual CLI commands, while Claude Code offers native hook events for automatic verification at key lifecycle points.

**Recommendation**: Implement native hooks to achieve parity with Git and Amp workflows.

---

## Documents (Read in This Order)

### 1. **Executive Summary** (Start Here)
📄 **File**: `.amp/claude_code_hooks_findings.md`
📊 **Size**: 7.6 KB
⏱️ **Read Time**: 10 minutes

Quick overview of findings without technical details:
- The gap (CLI-only vs native hooks)
- Key findings (5 missing integrations)
- Risk assessment
- Recommended action

**Best for**: Quick understanding, decision making

---

### 2. **Main Review Document**
📄 **File**: `CLAUDE_CODE_HOOKS_REVIEW.md`
📊 **Size**: 12 KB
⏱️ **Read Time**: 20 minutes

Detailed analysis and recommendations:
- Current implementation overview
- All available Claude Code hook events
- Gap analysis (what we're missing)
- Architectural realignment strategy
- Implementation priority & execution plan
- Key decisions & reasoning
- Risks & mitigation

**Sections**:
- Current Implementation (what we built)
- Claude Code Hook Events (what's available)
- Gap Analysis (what we're missing)
- Recommended Strategy (Phase 1, 2, 3)
- Architecture Realignment (consistency across systems)
- Implementation Priority (must/should/nice-to-have)
- Execution Plan (step-by-step)
- Key Decisions (answered FAQ)
- Risks & Mitigation

**Best for**: Understanding the gap and rationale

---

### 3. **Implementation Technical Plan**
📄 **File**: `CLAUDE_CODE_HOOKS_IMPLEMENTATION.md`
📊 **Size**: 16 KB
⏱️ **Read Time**: 30 minutes

Detailed technical implementation guide with code examples:
- Full hook script implementations (copy-paste ready)
- Settings configuration
- Integration with `devloop init`
- Hook registration process
- Testing strategy with examples
- Rollout plan

**Hook Scripts Included**:
1. `claude-session-start` - Load findings on startup
2. `claude-stop` - Collect findings on completion
3. `claude-subagent-stop` - Extract findings on task end
4. `claude-file-protection` - Block protected files
5. `install-claude-hooks` - Registration helper

**Best for**: Implementation team, developers

---

### 4. **Implementation Checklist**
📄 **File**: `.amp/CLAUDE_CODE_HOOKS_CHECKLIST.md`
📊 **Size**: 7.7 KB
⏱️ **Read Time**: Reference document

Structured checklist for implementing changes:
- Phase 1: Core automation (~2 hours)
- Phase 2: File protection (~1 hour)
- Phase 3: Advanced features (future)
- Testing & validation steps
- Success criteria
- Known issues & workarounds

**Best for**: Implementation tracking, QA

---

## Key Findings Summary

### The Gap

| Aspect | Git | Amp | Claude Code (Current) | Claude Code (Proposed) |
|--------|-----|-----|---|---|
| **Trigger** | pre-commit | post-task | Manual command | SessionStart/Stop hooks |
| **Automation** | ✅ Automatic | ✅ Automatic | ❌ Manual | ✅ Automatic |
| **Blocking** | ✅ Yes | ❌ No | N/A | ❌ No |
| **Findings** | From CI | Extracted | On-demand | Auto-collected |
| **Consistency** | ✅ Aligned | ✅ Aligned | ❌ Inconsistent | ✅ Aligned |

### Missing Hooks

| Hook | Timing | Current | Status |
|------|--------|---------|--------|
| SessionStart | Session startup | ❌ Not used | Should implement |
| Stop | Claude finishes | ❌ Not used | Should implement |
| SubagentStop | Task completes | ❌ Not used | Could implement |
| PreToolUse | Before file writes | ❌ Not used | Should implement |
| UserPromptSubmit | User input | ❌ Not used | Could implement |

### Impact Assessment

**Complexity**: Low (3-4 bash scripts, ~100 lines total)
**Risk**: Low (non-blocking, additive, CLI fallback)
**Effort**: 3-4 hours total (~2h Phase 1, ~1h Phase 2)
**Benefit**: High (consistent with Git/Amp, better UX)

---

## Implementation Phases

### Phase 1: Core Automation (Must Have) - ~2 hours

**What**: SessionStart + Stop hooks + file protection
**Why**: Aligns Claude Code with Amp pattern
**Impact**: Auto-load/collect findings, block dangerous writes
**Risk**: Very low (non-blocking)

**Includes**:
- ✅ 3 hook scripts
- ✅ Hook registration system
- ✅ Update devloop init
- ✅ Core documentation

### Phase 2: Refinement (Should Have) - ~1 hour

**What**: Testing, whitelist mechanism, error handling
**Why**: Safety & production readiness
**Impact**: Fewer false positives, better guidance

### Phase 3: Advanced (Nice to Have) - Future

**What**: UserPromptSubmit, SubagentStop, context injection
**Why**: Enhanced integration, better user experience

---

## Architecture After Implementation

```
Git Workflow
├─ File save
├─ .git/hooks/pre-commit
│  └─ .agents/verify-common-checks (blocking)
└─ Result: Verified before commit

Amp Workflow
├─ Task complete
├─ .agents/hooks/post-task
│  ├─ .agents/verify-common-checks (non-blocking)
│  └─ extract-findings-to-beads
└─ Result: Verified, findings filed

Claude Code Workflow (Proposed)
├─ Session start
├─ SessionStart hook
│  └─ Load findings to context
├─ Claude finishes
├─ Stop hook
│  └─ Collect findings
├─ Task complete
├─ SubagentStop hook
│  └─ Extract findings to Beads
└─ Result: Automatic, non-blocking, consistent
```

---

## Quick Reference: Hook Events

### Core Hooks (Must Implement)

**SessionStart**
- When: Session begins
- Matcher: `startup`
- Command: Load findings
- Output: JSON context for Claude

**Stop**
- When: Claude finishes responding
- Input: `stop_hook_active` flag
- Command: Collect findings (silent)
- Output: Store to disk

**PreToolUse (Write)**
- When: Before file write
- Input: File path
- Command: Check if protected
- Output: stderr error message

### Optional Hooks (Future)

**UserPromptSubmit**
- When: User submits prompt
- Input: Prompt text
- Command: Inject findings if relevant
- Output: Add context to prompt

**SubagentStop**
- When: Task completes
- Input: Task output
- Command: Extract findings
- Output: Create Beads issues

---

## Decision Criteria

### Why Implement Phase 1?

✅ Consistent with Git/Amp patterns
✅ Reduces user friction (no manual commands)
✅ Automatic findings collection
✅ Safety mechanism (file protection)
✅ Low risk (non-blocking, additive)
✅ Clear user benefit

### Why Not Block on Stop Hook?

Claude Code is still running. Blocking would prevent:
- Saving changes
- Pushing commits
- Task completion

Non-blocking approach mirrors Amp's post-task hook (warnings only).

### Why Keep CLI Commands?

- Manual control when users want it
- Debugging & troubleshooting
- Integration with other tools
- Fallback for web Claude Code (no hooks)

---

## Success Metrics

After implementation, success = all of:

1. ✅ SessionStart hook loads findings on startup
2. ✅ Stop hook collects findings on completion
3. ✅ PreToolUse hook blocks protected files
4. ✅ All hooks non-blocking (Claude continues if they fail)
5. ✅ CLI commands still work as fallback
6. ✅ Documentation clear and complete
7. ✅ Tests pass (unit + integration)
8. ✅ Clean install works without manual config

---

## FAQ

**Q: Why is this important?**
A: Currently Claude Code is inconsistent with Git/Amp - it requires manual commands while the others automate. Native hooks align all three systems.

**Q: Will this break existing workflows?**
A: No. Hooks are additive. CLI commands remain. Existing workflows unaffected.

**Q: What if hooks fail?**
A: Graceful failure. Claude Code continues. Errors logged in verbose mode only.

**Q: How long does Phase 1 take?**
A: ~2 hours (1h hook scripts, 1h integration + testing)

**Q: When should we do this?**
A: After current work is stable. Recommended: next sprint/release.

---

## Implementation Timeline

```
Week 1: Review findings, get approval
        Create hook scripts (claude-session-start, claude-stop, claude-file-protection)
        Update devloop init
        
Week 2: Testing (unit + integration)
        Documentation updates (AMP_ONBOARDING.md, README.md)
        Create .agents/hooks/README.md
        
Week 3: Manual testing with Claude Code
        Gather feedback
        Fix issues
        
Week 4: Merge to main
        Release notes
        User communication
```

---

## Files to Review

**For quick decision**:
1. This index
2. `.amp/claude_code_hooks_findings.md`

**For implementation**:
1. `CLAUDE_CODE_HOOKS_REVIEW.md` (understanding)
2. `CLAUDE_CODE_HOOKS_IMPLEMENTATION.md` (technical)
3. `.amp/CLAUDE_CODE_HOOKS_CHECKLIST.md` (tasks)

**For code**:
- Hook scripts in IMPLEMENTATION.md (copy-paste ready)

---

## Contacts & Questions

**Questions about findings?** → See CLAUDE_CODE_HOOKS_REVIEW.md
**Questions about implementation?** → See CLAUDE_CODE_HOOKS_IMPLEMENTATION.md
**Need a checklist?** → See CLAUDE_CODE_HOOKS_CHECKLIST.md

---

## Document Status

✅ CLAUDE_CODE_HOOKS_REVIEW.md - Complete
✅ CLAUDE_CODE_HOOKS_IMPLEMENTATION.md - Complete
✅ .amp/claude_code_hooks_findings.md - Complete
✅ .amp/CLAUDE_CODE_HOOKS_CHECKLIST.md - Complete
✅ This index - Complete

All documents are production-ready and can be shared with team.

---

## Next Action

1. Read `.amp/claude_code_hooks_findings.md` (executive summary)
2. Decide: Implement Phase 1? (recommended: YES)
3. If YES, read IMPLEMENTATION.md and start checklist
4. If NO, maintain CLI-only approach (less consistent but works)

---

**Created**: 2025-12-09
**Format**: Complete analysis with actionable recommendations
**Status**: Ready for implementation
