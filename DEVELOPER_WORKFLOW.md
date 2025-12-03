# Developer Workflow Guide

This guide explains the layered validation system in place and how to work effectively with DevLoop's automated checks.

## Automated Checks: Three Layers

```
File Change → DevLoop watches → Immediate feedback
                  ↓
            Git Commit → Pre-commit hooks → Format/lint validation
                  ↓
              Git Push → Pre-push hooks + local verify script
                  ↓
                   CI → Comprehensive testing and validation
```

### Layer 1: DevLoop (Continuous, Automatic)

**What:** Background agents monitor file changes and automatically run checks.

**When:** Whenever you save a file in your editor

**What it catches:**
- Formatting issues (Black)
- Linting issues (Ruff)
- Type checking (mypy)
- Test failures
- Security issues (Bandit, Snyk)

**How to check findings:**
```bash
# View current findings in context store
cat .devloop/context/index.json | head -20

# View detailed findings
cat .devloop/context/relevant.json | python3 -m json.tool | head -100
```

**Status of DevLoop in this project:**
- ✅ Running continuously in background
- ✅ Monitoring all Python files
- ✅ 123 existing issues being tracked
- ⚠️ Not yet auto-fixing (report-only mode)
- ⚠️ Not blocking commits (informational)

---

### Layer 2: Pre-commit Hook (Git Commit)

**What:** Runs when you commit code locally.

**Checks:**
1. **Poetry lock file sync** — If `pyproject.toml` changed, `poetry.lock` must be updated too
2. **Beads issue sync** — Flushes any issue changes to `.beads/issues.jsonl`

**How it works:**
```bash
$ git commit -m "feat: Add new feature"

# Hook runs automatically
# → Checks if pyproject.toml changed without poetry.lock
# → Syncs beads issues
# → Commit succeeds if all checks pass
```

**If it fails:**
```
ERROR: pyproject.toml changed but poetry.lock not updated
Fix: Run 'poetry lock' and stage both files
  poetry lock
  git add poetry.lock
```

---

### Layer 3: Local Verification (Before Push)

**What:** Quick local check that simulates what CI will do.

**Run before pushing:**
```bash
./scripts/verify-before-push.sh
```

**What it checks:**
1. Poetry lock sync
2. Black (code formatting)
3. Ruff (linting)
4. mypy (type checking)
5. pytest (tests)

**Speed:** ~30-60 seconds total (vs 2-3 minutes for CI)

**Example output:**
```
[Verify] Running pre-push verification checks...

[1/5] Checking poetry.lock sync...
✓ poetry.lock is in sync

[2/5] Checking code formatting with Black...
✓ Code formatting OK

[3/5] Checking linting with Ruff...
✓ Linting OK

[4/5] Checking type safety with mypy...
✓ Type checking OK

[5/5] Running tests...
✓ Tests passed

✅ All checks passed! Safe to push.
```

**If something fails:**
```
[2/5] Checking code formatting with Black...
✗ Code formatting issues found
Fix: poetry run black src/ tests/

✗ Linting issues found
Fix: poetry run ruff check --fix src/ tests/

❌ Some checks failed. Fix issues above and re-run this script.
```

---

### Layer 4: Pre-push Hook (Git Push)

**What:** Runs when you push code to GitHub.

**Checks:**
1. **CI Status** — Waits up to 2 minutes for latest CI to complete
2. **CI Result** — Blocks push if CI failed, allows if passed
3. **Timeout** — If CI still running after 2 minutes, allows push with warning

**How it works:**
```bash
$ git push origin main

[CI Check] Running pre-push verification...
[CI Check] Checking CI status for branch: main
[CI Check] Previous CI run in progress, waiting for completion...
[CI Check] Still waiting... (5/120 seconds)
...
[CI Check] CI completed with status: success
[CI Check] ✅ Latest CI run passed
To github.com:wioota/devloop.git
   2ff0d92..7674f50  main -> main
```

**If CI failed:**
```
[CI Check] ❌ Last CI run failed with status: failure
[CI Check] View the failed run: gh run list --branch main
[CI Check] Please fix CI issues before pushing
```

---

### Layer 5: CI (Comprehensive Testing)

**What:** Runs on GitHub after push.

**Checks:**
1. Tests (Python 3.11 & 3.12)
2. Linting (Black, Ruff)
3. Type checking (mypy)
4. Security (Bandit, Snyk)

**View results:**
```bash
gh run list --limit 5
gh run view <run-id>
```

---

## Recommended Workflow

### For Daily Development

```bash
# 1. Make code changes in your editor
#    → DevLoop watches automatically
#    → You see findings in .devloop/context/

# 2. Commit your changes
git add <files>
git commit -m "feat: Your feature"
# → Pre-commit hook validates automatically

# 3. Before pushing, verify locally
./scripts/verify-before-push.sh
# → Takes 30-60 seconds
# → Catches formatting, linting, type, test issues

# 4. Push your code
git push origin main
# → Pre-push hook checks CI status
# → GitHub CI runs comprehensive checks
```

### For Complex Changes (pyproject.toml, dependencies, schema)

```bash
# 1. Make the change
# 2. If pyproject.toml modified:
poetry lock
git add pyproject.toml poetry.lock

# 3. Test locally before commit
poetry run pytest
poetry run black src/ tests/
poetry run ruff check src/ tests/
poetry run mypy src/

# 4. Commit (hook validates poetry.lock sync)
git commit -m "deps: Update dependencies"

# 5. Run verification script
./scripts/verify-before-push.sh

# 6. Push
git push origin main
```

---

## Understanding the Discipline

### Why Three Hooks + Verification Script?

**Pre-commit hook** — Catches critical errors that would fail CI (poetry.lock)
- ✅ Fast (seconds)
- ✅ Prevents worst failures
- ✅ Runs automatically

**Verification script** — Simulates CI locally before pushing
- ✅ Fast (30-60 seconds vs 2-3 minutes)
- ✅ Optional but strongly encouraged
- ✅ Same checks as CI but faster feedback loop

**Pre-push hook** — Final validation before accepting push
- ✅ Validates CI actually passed
- ✅ Prevents pushing broken code
- ✅ Waits for CI completion

**CI** — Comprehensive, definitive check
- ✅ Full test suite
- ✅ All security scans
- ✅ All project requirements
- ✅ Runs on clean environment

### The Feedback Loop Effect

| Approach | Speed | Adoption |
|----------|-------|----------|
| Wait for CI (30s delay) | ❌ Slow | ❌ Low — hard to learn from feedback |
| Pre-commit hooks (5s) | ✅ Fast | ✅ High — immediate feedback trains discipline |
| Verification script (30s) | ✅ Fast | ✅ High — optional but effective |
| All three together | ✅ Fast | ✅ Very High — layered validation catches errors early |

**Key insight:** When feedback is <10 seconds, developers naturally learn the rules. When it's 30+ seconds, they form bad habits (pushing broken code, waiting for CI).

---

## DevLoop Status & Future

### Current State

✅ **Running:** DevLoop watching all Python files  
✅ **Detecting:** 123 issues in relevant.json  
✅ **Monitoring:** Linting, formatting, type checking, security  
⚠️ **Not auto-fixing:** Currently report-only mode  
⚠️ **Not blocking:** Informational only, doesn't prevent commits  

### Next Steps

1. **Enable auto-fix** — Make formatter agent auto-fix Black issues
2. **Integrate with Beads** — Map DevLoop findings to issues
3. **Block on critical** — Prevent commits if high-priority issues exist
4. **Feedback loop** — Show developer which agent caught the issue

### Vision

DevLoop should eventually replace the need for pre-commit hooks:
- ✅ Watches for changes
- ✅ Runs checks immediately
- ✅ Auto-fixes what it can
- ✅ Reports unfixable issues
- ✅ Integrates with issue tracking

The hooks become *backup* validation, not the primary mechanism.

---

## Troubleshooting

### CI failed but local checks passed

**Common causes:**
- Python version difference (CI uses 3.11 & 3.12, you might be using different)
- Dependency version mismatch (poetry.lock not up-to-date)
- Test flakiness (rare but happens)

**Fix:**
```bash
# Sync dependencies
poetry lock

# Run all Python versions locally if possible
# Or check CI logs for specific error
gh run view <run-id> --log-failed
```

### Pre-push hook timing out

**Normal behavior:**
- If CI is still running, hook waits up to 2 minutes
- After timeout, allows push but shows warning

**If you want to force push without waiting:**
```bash
git push origin main --no-verify
```

### DevLoop not detecting issues

**Check if running:**
```bash
ps aux | grep devloop | grep -v grep
```

**Restart if needed:**
```bash
devloop watch . &  # In background
# or
devloop watch .    # In foreground to see logs
```

**Check findings:**
```bash
cat .devloop/context/index.json
```

---

## For Coding Agents (Claude, Copilot)

When working on this codebase, follow this discipline:

1. **Before any commit:** 
   - Check if you modified `pyproject.toml` → run `poetry lock`
   - Always run local format: `poetry run black src/ tests/`

2. **Before any push:**
   - Run: `./scripts/verify-before-push.sh`
   - Fix any issues
   - Only push when all checks pass

3. **Document special cases:**
   - See `CODING_RULES.md` for patterns (tool availability, error handling, etc.)
   - See `AGENTS.md` for system design and constraints

4. **Update the issue:**
   - Run `bd close <issue-id> --reason "..."` when task is complete
   - Push the `.beads/issues.jsonl` changes together with code

---

## Questions?

- See `CODING_RULES.md` for code patterns and standards
- See `AGENTS.md` for system design and architecture
- See `history/LESSONS_LEARNED.md` for process improvements
- See `history/PROCESS_IMPROVEMENTS_IMPLEMENTED.md` for how hooks work
