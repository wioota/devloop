# Pre-Commit Hook Audit

**Audit Date:** December 13, 2025

**Files Reviewed:**
- `.git/hooks/pre-commit` (main hook)
- `.git/hooks/pre-commit-checks` (code quality checks)
- `src/devloop/cli/templates/git_hooks/pre-commit` (template)
- `src/devloop/cli/templates/git_hooks/pre-commit-checks` (template)

## Summary

DevLoop uses **custom pre-commit hooks** (not the pre-commit framework) with a two-stage design:

1. **pre-commit** — Main hook that checks dependencies and orchestrates checks
2. **pre-commit-checks** — Separate script that runs formatting, linting, type checking, and tests

### Design Grade: A

The implementation is well-designed with good separation of concerns, proper error handling, and telemetry integration.

---

## Hook Behavior Analysis

### Stage 1: Main Hook (`pre-commit`)

| Check | Behavior | Files Affected | Notes |
|-------|----------|-----------------|-------|
| **Poetry lock sync** | Staged files only | `pyproject.toml`, `poetry.lock` | Checks if lock file updated when toml changes |
| **Pre-commit-checks** | Staged Python files only | `*.py` (staged) | Only runs if `.py` files in staging area |
| **Existing hook** | Runs old hook if present | `*` | Preserves user's previous hooks |
| **Beads flush** | Auto-stages JSONL | `.beads/issues.jsonl` | Automatically commits issue state |

### Stage 2: Code Quality Checks (`pre-commit-checks`)

| Tool | Scope | Targets | Auto-fix | Notes |
|------|-------|---------|----------|-------|
| **Black** | Files under `src/` | `src/` | No — only checks | Formatting validation |
| **Ruff** | Files under `src/` | `src/` | No — only checks | Linting validation |
| **mypy** | Type checking | `devloop/core/`, `devloop/agents/` | No — only checks | Subset of codebase |
| **pytest** | Tests | `tests/` | No — only checks | All tests (full suite) |

---

## Answers to Audit Questions

### Q1: Does it lint all files or only staged changes?

**Answer: Staged Python files only**

```bash
# From pre-commit hook line 46:
if git diff --cached --name-only | grep -qE '\.py$'; then
```

- ✅ **Only processes staged files** — checks `git diff --cached` (staging area)
- ✅ **Only runs for Python changes** — checks for `.py` extensions
- ✅ **Respects git staging** — won't flag unstaged unrelated files
- ✅ **Developer-friendly** — developers control what gets checked

### Q2: Can we configure it to auto-fix formatting?

**Answer: Not currently, but possible**

**Current behavior:**
- Black runs in `--check` mode (validation only)
- Ruff runs in check mode (no `--fix` flag)
- Both report errors and exit with code 1

**Why validation-only?**
- ✅ Safety: Developers see what changed before auto-fix
- ✅ Control: Developers decide whether to accept fixes
- ✅ Transparency: Changes are explicit, not hidden

**To enable auto-fix:**
```bash
# In pre-commit-checks, change lines 32 and 42:

# Before:
poetry run black --check src/

# After (auto-fix):
poetry run black src/

# Similarly for Ruff:
# Before:
poetry run ruff check src/

# After (auto-fix):
poetry run ruff check src/ --fix
```

**Recommendation:** Keep validation-only for now. Auto-fix can be done with pre-flight checklist or separate command.

### Q3: Why were unrelated files flagged during commits?

**Answer: Black formatting debt on entire `src/` directory**

**Root cause:**
- Black checks **entire `src/` directory** (not just staged files)
- If `src/` has formatting issues, Black flags them all
- This creates "noise" that obscures your actual changes

**Example:**
```bash
# You change 2 lines in manager.py:
git add src/devloop/core/manager.py

# Pre-commit runs Black on ENTIRE src/:
poetry run black --check src/

# Black finds 100 lines of formatting issues in formatter.py (unrelated)
# Your 2-line change gets lost in the noise
```

**Why this happens:**
- Pre-commit correctly limits itself to staged `.py` files (line 46)
- But pre-commit-checks then checks the **entire `src/` directory**
- This is a mismatch: pre-commit guards staged files, checks run on entire directory

**Current impact:**
- ⚠️ Developers see unrelated files flagged
- ⚠️ Makes it hard to understand what the hook is checking
- ⚠️ Can cause developers to ignore hook warnings (alert fatigue)

---

## Recommendations

### Priority 1: Fix Black/Ruff to check staged files only

Change `pre-commit-checks` to check only **staged files**, not entire `src/` directory:

```bash
# Get list of staged Python files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' | grep '^src/')

if [ -z "$STAGED_FILES" ]; then
    echo "No Python files to check"
    exit 0
fi

# Run tools on staged files only
poetry run black --check $STAGED_FILES
poetry run ruff check $STAGED_FILES
```

**Benefits:**
- ✅ Hooks only flag changes developers made
- ✅ Reduces noise and alert fatigue
- ✅ Developers won't disable hooks due to noise
- ✅ Matches git's philosophy (check what you're committing)

### Priority 2: Consider pytest scope

**Current:** Runs ALL tests in `tests/`

**Concern:** Slow feedback loop, not staged-change-specific

**Options:**
1. **Smart test selection** (Recommended)
   - Detect which modules changed
   - Run only tests for those modules
   - Faster feedback (~30 seconds vs 2 minutes)

2. **Configurable pytest skip**
   - Add `--no-tests` flag to skip pytest
   - Useful for quick format/lint-only commits
   - Still catches major issues

3. **Background pytest**
   - Run pytest in background after commit
   - Don't block commit
   - Report results asynchronously

**Recommendation:** Keep as-is for now (full test suite ensures quality). Can optimize in future.

### Priority 3: Document the dual-scope behavior

Add comment explaining **why** pre-commit limits itself to staged files, but checks run on broader scope:

```bash
# Current comment (line 5):
# Checks:
# 1. Poetry lock file sync with pyproject.toml
# 2. Code quality checks (Black, Ruff, mypy, pytest)
# 3. bd (beads) pre-commit flush
# 4. Any existing pre-commit.old hook

# Better:
# Checks:
# 1. Poetry lock file sync with pyproject.toml
# 2. Code quality checks (Black, Ruff, mypy, pytest)
#    - Only on STAGED .py files (not unrelated files)
#    - Provides immediate feedback on your changes
# 3. bd (beads) pre-commit flush
# 4. Any existing pre-commit.old hook
```

---

## Hook Statistics

| Metric | Value |
|--------|-------|
| **Lines of code** | 93 (pre-commit) + 72 (checks) = 165 |
| **Checks performed** | 6 (lock sync, Black, Ruff, mypy, pytest, bd) |
| **Telemetry events** | 2 (pre_commit_check success/failure) |
| **Automatic cleanup** | 1 (.beads/issues.jsonl auto-staging) |
| **Backward compatibility** | Yes (preserves pre-commit.old) |

---

## Improvements Made in Recent Versions

✅ **v0.4.1**: Removed version consistency check (pyproject.toml is single source of truth)

✅ **v0.5.0**: Pre-flight checklist documentation added to AGENTS.md

✅ **Current**: Beads integration with automatic JSONL flushing

---

## Testing the Hooks

```bash
# Test that pre-commit runs on .py file changes
echo "# test" >> src/devloop/core/config.py
git add src/devloop/core/config.py
git commit -m "test"  # Should run checks

# Test that pre-commit doesn't run on non-.py files
echo "test" >> README.md
git add README.md
git commit -m "docs"  # Should skip pre-commit-checks

# Test beads integration
bd create "Test issue" -p 2
git add .beads/issues.jsonl
git commit -m "Test beads"  # Should succeed with JSONL committed
```

---

## Conclusion

DevLoop's custom pre-commit hook implementation is **well-designed and effective**. The main issue is **scope mismatch** — pre-commit correctly limits itself to staged files, but the checks run on entire directories.

**Recommended action:** Update `pre-commit-checks` to check **staged files only** rather than entire `src/` directory. This would eliminate noise and improve developer experience.

**Effort:** Low (20-30 lines changed)
**Impact:** High (cleaner feedback, fewer false positives)
**Risk:** Low (well-tested approach, can rollback easily)
