# Next Steps: Completing the Developer Discipline Framework

## Summary of What We've Built

We've created a comprehensive 5-layer validation system to improve developer discipline and catch issues before CI:

### ✅ Completed
1. **Pre-commit hook** — Prevents poetry.lock desync
2. **Improved pre-push hook** — Waits for CI instead of skipping
3. **Local verify script** — Quick CI simulation (30-60s)
4. **Documentation** — CODING_RULES, DEVELOPER_WORKFLOW, framework overview
5. **Process improvements** — Lessons learned and implementation details

### ⚠️ Current Issues
- Multiple DevLoop instances running (resource waste)
- 123 unresolved linting/formatting issues in context store
- DevLoop not blocking commits (informational only)
- No integration between DevLoop findings and Beads issues
- Type checking errors in codebase

## Prioritized Next Steps

### P1: Fix Critical Issues (Blocks Workflow)

#### 1. Consolidate DevLoop Instances
**Issue:** 5 DevLoop watch processes running simultaneously

**Fix:**
```bash
# Kill all instances
pkill -f "devloop watch"

# Start fresh single instance
cd /home/wioot/dev/claude-agents
devloop watch . &
```

**Why:** Resource efficiency, prevents duplicate findings

---

#### 2. Enable DevLoop Auto-Fix (claude-agents-sf3)
**Current:** DevLoop reports formatting issues but doesn't fix them

**Goal:** Auto-format on save, eliminate manual Black runs

**Implementation:**
1. Edit `.devloop/agents.json`
2. Change formatter agent: `"autoFix": true`
3. Monitor that it doesn't cause issues
4. Eventually extends to linter auto-fix too

**Impact:** Formatting issues disappear automatically, developers don't need to remember to format

---

### P2: High Value (Quick Wins)

#### 3. Run Local Verification Before Next Session
**Command:**
```bash
./scripts/verify-before-push.sh
```

**Expected:** Some mypy errors, some tests failing

**Action:** Fix errors found, commit improvements

**Impact:** Demonstrates the script works, catches real issues

---

#### 4. Fix Type Checking Errors
**Current state:** 4 mypy errors found by verification script

**Files affected:**
- `src/devloop/collectors/filesystem.py`
- `src/devloop/collectors/manager.py`
- `src/devloop/cli/main_v1.py`

**Action:** Review errors, add type annotations, fix incompatibilities

**Impact:** Clean type checking, CI passes more reliably

---

### P3: Medium Priority (Integrations)

#### 5. Integrate DevLoop with Beads (claude-agents-sut)
**Current:** DevLoop findings exist in `.devloop/context/` but not in issue tracking

**Goal:** Map critical findings to Beads issues

**Implementation:**
1. Create integration script that reads DevLoop findings
2. For high-priority issues: create/update Beads issues
3. Show findings in `bd ready` output
4. Link findings to parent tasks

**Impact:** Developers see code quality issues in their task list

**Example:**
```bash
bd ready
# → Shows "Type checking needed: 4 errors in src/devloop"
# → Shows "Formatting needed: src/devloop/core/config.py"
```

---

#### 6. Create Post-Merge Hook
**Goal:** Auto-update DevLoop context after merges

**Reason:** When someone else pushes code, DevLoop findings might be outdated

**Implementation:**
- Add `.git/hooks/post-merge` that signals DevLoop to re-scan
- Or trigger `devloop status` to refresh context

---

### P4: Polish (Nice to Have)

#### 7. IDE Integration
**Goal:** Show DevLoop findings inline in VSCode/editor

**Implementation:**
- Create LSP (Language Server Protocol) adapter
- Or VSCode extension that reads `.devloop/context/`
- Shows issues inline like linters do

---

#### 8. Automated Fixing Agent
**Goal:** Have agents not just report issues, but propose fixes

**Example:** Instead of just reporting unused imports, propose removal

**Implementation:**
- Extend agent framework with fix proposals
- Add `--apply-fix` flag to accept proposals
- Integrate with pre-commit hook

---

## Recommended Work Order

```
Session 1: NOW
├── Consolidate DevLoop instances
├── Review DEVELOPER_WORKFLOW.md to ensure it matches actual behavior
└── Run verify-before-push.sh to baseline issues

Session 2:
├── Fix type checking errors (4 errors)
├── Enable DevLoop auto-fix for formatter
└── Test that formatting works automatically

Session 3:
├── Integrate DevLoop findings with Beads
├── Create example: DevLoop finding → Beads issue → development task
└── Document the integration

Session 4:
├── Post-merge hook
├── Test with real merge
└── Monitor resource usage

Future Sessions:
├── IDE integration
├── Automated fixing proposals
└── Team rollout and documentation
```

## Success Metrics

### After Session 1
- [ ] Single DevLoop process running
- [ ] Verification script works locally
- [ ] Documentation clear and accurate

### After Session 2
- [ ] All type checking errors fixed
- [ ] DevLoop auto-fix enabled for formatting
- [ ] Zero Black formatting CI failures

### After Session 3
- [ ] DevLoop findings appear in Beads
- [ ] `bd ready` shows code quality issues
- [ ] Developers see unified task list

### Complete Implementation
- [ ] Zero CI failures due to code quality
- [ ] All developers use verify script
- [ ] DevLoop auto-fixes most issues
- [ ] Team discipline improved significantly

## Important Reminders

### When Working on This Codebase

1. **Always reference DEVELOPER_WORKFLOW.md** — It's the source of truth for the workflow

2. **Run verify script before pushing:**
   ```bash
   ./scripts/verify-before-push.sh
   ```

3. **If modifying pyproject.toml:**
   ```bash
   poetry lock
   git add poetry.lock
   ```

4. **Check DevLoop findings:**
   ```bash
   cat .devloop/context/index.json
   ```

5. **Update issues when done:**
   ```bash
   bd close <issue-id> --reason "Fixed in commit abc123"
   git push origin main
   ```

### For Coding Agents

- Read DEVELOPER_WORKFLOW.md fully before starting
- Always run verify-before-push.sh before pushing ANY code
- If type errors appear, fix them before pushing
- Document any special cases discovered in CODING_RULES.md
- Test locally first, CI second

## Conclusion

We've built the **foundation** for developer discipline. The next steps are about:

1. **Making it automatic** (DevLoop auto-fix)
2. **Making it visible** (integrate with Beads)
3. **Making it easy** (IDE integration)

The philosophy: **Shift the burden of validation from humans to machines.** Developers should focus on features, not on remembering formatting rules or chasing CI failures.

DevLoop is the engine. The validation system we've built is the transmission. Together, they should create a workflow where code quality is a side effect of development, not an afterthought.
