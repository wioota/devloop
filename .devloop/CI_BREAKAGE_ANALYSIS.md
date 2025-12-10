# CI Breakage Analysis & Tightening Recommendations

## Current State
**Problem**: Formatting issues (Black) slipped through to CI even though:
- Pre-commit hook runs Black check ✓
- Formatter agent configured with `autoFix: true` ✓  
- Local CI checks exist ✓

**Recent Failure**: Two test files had formatting issues that passed local checks but failed on GitHub Actions.

---

## Root Cause Analysis

### 1. **Formatter Agent Not Auto-Fixing Despite Configuration**
**Current config:**
```json
"formatter": {
  "enabled": true,
  "triggers": ["file:modified"],
  "config": {
    "formatOnSave": true,
    "autoFix": true,
    "reportOnly": false
  }
}
```

**Problem:**
- Global mode is `"report-only"` which overrides agent-level `autoFix: true`
- Agent findings are only written to `.devloop/context/` but NOT applied to files
- No mechanism to auto-stage formatted files for commit

**Gap**: Agent detected issues but didn't fix them.

---

### 2. **Pre-Commit Hook Runs *After* Files Already Committed**
**Current flow:**
1. Test files created (no formatting)
2. Test files modified/staged
3. `git commit` triggered
4. Pre-commit hook runs and **checks** formatting
5. **Too late** - hook can't prevent commit if code was already formatted incorrectly

**Problem**: Pre-commit hook is reactive, not preventive. By the time it runs, Python objects have already been deserialized and committed.

**Gap**: No formatting enforcement *before* the commit is created.

---

### 3. **No Automated Formatting in Dev Workflow**
Test files were likely created directly without going through:
- IDE auto-format on save
- Manual `black` run
- Pre-commit hook formatting (which only checks, doesn't fix)

**Gap**: Multiple ways to commit code without proper formatting.

---

### 4. **CI Checks Duplicate Local Checks**
Both `.github/workflows/ci.yml` and `.git/hooks/pre-commit-checks` run:
- Black format check
- Ruff linting  
- Type checking
- Tests

**Problem**: No feedback loop from CI failures back to devloop. When CI fails, agents don't know to improve their detection/fixing.

**Gap**: CI and local development are isolated.

---

### 5. **Pre-Push Hook Only Checks *Previous* Run Status**
```bash
# Pre-push hook logic:
# Check CI status of LAST commit, not current one
```

When you commit and push:
1. Commit (e.g., `f42bc6e`) is made
2. Push triggers hook
3. Hook checks CI of *previous* commit (`a16fc28`)
4. If previous failed, push is blocked
5. Your new commit's CI hasn't run yet

**Gap**: No early feedback. You commit broken code, push is blocked, you wait for CI, fix, commit again.

---

## Tightening Strategy: 3-Layer Defense

### Layer 1: Prevent at Commit (Pre-Commit)
**Status**: ✓ Mostly working, needs enhancement

**Action 1A: Make pre-commit hook auto-fix**
```bash
# Instead of just checking Black:
poetry run black src/ tests/  # FIX, don't just check

# Then re-stage formatted files:
git add -u
```

**Action 1B: Activate formatter agent auto-fixing**
```json
{
  "global": {
    "mode": "fix-mode",  // Not "report-only"
    "autonomousFixes": {
      "enabled": true,
      "safetyLevel": "safe_only"
    }
  }
}
```

**Action 1C: Stage auto-fixed files**
Agent should:
1. Detect formatting issues
2. Auto-fix files (Black, Prettier)
3. Auto-stage them: `git add <fixed-files>`
4. Log to `.devloop/context/auto_fixed.json`

---

### Layer 2: Catch at Pre-Push (Local Validation)
**Status**: ✗ Incomplete

**Problem**: Hook only checks previous commit's CI status, not current commit.

**Action 2A: Replace pre-push hook with real validation**
```bash
# New pre-push validation (instead of checking old CI):
set -e

echo "[Pre-push] Running final validation..."

# 1. Re-run all local checks on current code
poetry run black --check src/ tests/
poetry run ruff check src/
poetry run mypy devloop/core/ devloop/agents/
poetry run pytest tests/ -q

echo "[Pre-push] ✅ All local checks passed"

# 2. Only then check CI status from most recent run
# (This is informational, not blocking)
LAST_RUN=$(gh run list --branch main --limit 1 --json status --jq '.[0].status')
if [ "$LAST_RUN" == "failure" ]; then
    echo "[Pre-push] ⚠️  Warning: Latest CI run failed on main"
    echo "Consider checking: gh run view <run-id> --log-failed"
fi

exit 0  # Allow push if local checks pass
```

**Action 2B: Add formatting check as CI gate**
```yaml
# .github/workflows/ci.yml
jobs:
  format-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: poetry run black --check src/ tests/
      - run: poetry run ruff check src/
```

Make this a required check before merging.

---

### Layer 3: Fail Fast at CI (GitHub)
**Status**: ✓ Working but slow feedback

**Problem**: Takes ~1 minute to detect formatting issues. By then you've already waited, committed, pushed.

**Action 3A: Early CI feedback**
```yaml
# .github/workflows/ci.yml - run format checks FIRST
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: poetry run black --check src/ tests/
      - run: poetry run ruff check src/
      # Stop here if formatting fails, don't run tests
      
  test:
    needs: [validate]  # Only run if validate passes
    runs-on: ubuntu-latest
    steps: ...
```

**Action 3B: Fail CI on any format issue**
Current CI continues even if Black fails. Should exit immediately.

---

### Layer 4: DevLoop Agent Integration
**Status**: ✗ Not integrated

**Problem**: Formatter agent runs but doesn't integrate with git workflow.

**Action 4A: Agent post-fix workflow**
```json
{
  "formatter": {
    "enabled": true,
    "triggers": ["file:modified", "file:created"],
    "config": {
      "formatOnSave": true,
      "autoFix": true,
      "postFixActions": [
        "git add --update",
        "log-to-context"
      ]
    }
  }
}
```

**Action 4B: CI failure loop back to agent**
When CI fails on formatting:
1. GitHub Actions detects failure
2. Triggers webhook (GitHub Actions native)
3. Local devloop reads CI status
4. Agent increases priority on formatter checks
5. Agent runs on all files immediately
6. Fixes and stages them

---

## Recommended Implementation Order

**Immediate (Quick wins):**
1. ✅ Fix pre-commit hook to auto-format, not just check
2. ✅ Activate formatter agent `autoFix` mode
3. ✅ Make agent auto-stage fixed files

**Short-term (1-2 hours):**
4. Replace pre-push hook validation logic
5. Add explicit format-gate job in CI
6. Make CI format checks run first

**Medium-term (Architecture):**
7. Set up GitHub webhook → devloop integration
8. Create CI failure recovery workflow in agents.json

---

## Testing the Improvements

Create test scenario:
```bash
# 1. Create improperly formatted Python file
echo 'def foo(  x  ):  return x' > test_bad_format.py

# 2. Stage it
git add test_bad_format.py

# 3. Try to commit (should auto-fix)
git commit -m "test: bad formatting"

# 4. Check if file was auto-fixed and re-staged
git diff --cached  # Should show formatted version

# 5. Complete commit
git commit --amend  # Include the fixed formatting

# 6. Push (should pass all checks)
git push origin main
```

---

## Current Gaps Summary

| Layer | Gap | Impact | Fix Priority |
|-------|-----|--------|--------------|
| Agent | Auto-fix disabled globally | Issues detected but not fixed | HIGH |
| Pre-commit | Only checks, doesn't fix | Broken code gets committed | HIGH |
| Pre-push | Checks old CI status, not current | No early feedback loop | HIGH |
| CI | Sequential jobs, slow feedback | Takes 1+ min to detect issues | MEDIUM |
| Integration | No webhook/feedback loop | Manual CI checking required | MEDIUM |

---

## Prevention Matrix

```
Code Flow:
┌─────────────────────────────────────────────────────┐
│ 1. File saved in IDE                                 │
│    → Formatter agent auto-fixes (if enabled)        │
│    → File auto-staged if fixed                       │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 2. git commit triggered                              │
│    → Pre-commit hook runs FULL checks               │
│    → If formatting wrong: auto-fixes + re-stages    │
│    → If linting wrong: fails (developer fixes)      │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 3. git push triggered                                │
│    → Pre-push hook re-runs LOCAL validation         │
│    → Format check, lint check, type check, tests    │
│    → Only allows push if all pass                   │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 4. GitHub Actions runs (fail-fast)                   │
│    → Format checks run FIRST (exit early if fail)   │
│    → Linting, type checks, tests                    │
│    → All required for merge                         │
└─────────────────────────────────────────────────────┘
```

**Current state**: Layers 1 & 2 are weak. Layer 3 is slow.  
**Target state**: All 4 layers are tight and fast.
