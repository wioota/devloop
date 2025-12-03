# Lessons Learned: CI Failure During Optional Agents Implementation

## Incident

Two commits failed CI with: `pyproject.toml changed significantly since poetry.lock was last generated. Run 'poetry lock' to fix the lock file.`

- Commit: "Phase 2A & 2B: Interactive optional agent selection and poetry extras"
- Root cause: Added `[tool.poetry.extras]` section without running `poetry lock`

## Root Cause Analysis

### The Specific Issue
When modifying `pyproject.toml` in a Poetry project, the lock file must be updated. This is a **deterministic, preventable error** that should never reach CI.

### Process Gaps

1. **No local validation** — Should have caught immediately when running tests locally
2. **Weak pre-push validation** — Pre-push hook skips CI check if "in progress"
3. **Missing task checklist** — No verification step before pushing

### Why CI Validation Alone Isn't Enough

The current workflow is:
1. Make changes
2. Commit & push (immediately)
3. Wait for CI feedback (10-30 seconds later)

This creates a **feedback loop delay** that trains bad habits. By the time CI fails, the context is lost and momentum is broken.

## Improvements Needed

### 1. Pre-commit Hook: Lock File Sync Check (CRITICAL)
**What:** Add git pre-commit hook that prevents commits if `pyproject.toml` changed but `poetry.lock` didn't

**Implementation:**
```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check if pyproject.toml changed
if git diff --cached --name-only | grep -q "pyproject.toml"; then
  # If lock file not staged, fail
  if ! git diff --cached --name-only | grep -q "poetry.lock"; then
    echo "ERROR: pyproject.toml changed but poetry.lock not updated"
    echo "Run: poetry lock"
    exit 1
  fi
fi
```

**Impact:** Prevents the root cause immediately, within seconds of the change.

### 2. Improve Pre-push CI Check (HIGH)
**Current behavior:** Pre-push hook skips validation if CI is in progress
```bash
# Current code
[CI Check] Previous CI run still in progress, skipping check
```

**Should be:**
- Wait for CI completion (up to 60 seconds)
- Fail push if previous run failed
- Allow push only if latest CI passed

**Impact:** Ensures CI validation is actually enforced, not skipped.

### 3. Document Poetry Workflow (MEDIUM)
**What:** Add section to CODING_RULES.md

```markdown
## Special Case: Modifying pyproject.toml

When you change `pyproject.toml`:
1. Update `poetry.lock`: `poetry lock`
2. Test locally: `poetry run pytest`
3. Commit both files together
4. Pre-commit hook will verify they're synced
```

**Impact:** Makes the requirement explicit and searchable.

### 4. Create Local CI Verification Script (OPTIONAL)
**What:** `scripts/verify-before-push.sh` that runs:
- `poetry lock --check` (verify lock file is up-to-date)
- `poetry run pytest` (verify tests pass)
- `poetry run ruff check` (verify linting)
- `poetry run mypy src` (verify types)

**Usage:** `./scripts/verify-before-push.sh` before pushing

**Impact:** Shifts feedback from 10-30s CI delay to 5s local validation.

## Key Insight

**Local validation is 5-10x faster than waiting for CI.** When the feedback loop is that fast, developers learn the rules quickly and naturally. When CI takes 30 seconds, it's easy to form the habit of pushing broken code and checking CI later.

## Action Items

- [ ] claude-agents-0v3: Add pre-commit hook to detect poetry.lock desync
- [ ] claude-agents-2bc: Improve pre-push CI validation 
- [ ] claude-agents-080: Document pre-commit CI checklist
- [ ] (Optional) claude-agents-verify: Create local verification script

## Process Improvement

Going forward:
1. **Before any commit:** Think: "Did I modify pyproject.toml, package versions, config schema?"
2. **If yes:** Run the corresponding validation (`poetry lock`, migrations, schema checks)
3. **Before any push:** Run `./scripts/verify-before-push.sh` to catch issues in seconds, not CI

The pre-commit hook makes step 2 automatic. The local verification script makes step 3 optional but encouraged.
