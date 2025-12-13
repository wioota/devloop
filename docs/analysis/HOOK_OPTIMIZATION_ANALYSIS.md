# Hook Duplication & Parallelization Analysis

## Executive Summary

The current hook system runs **~10+ code quality checks sequentially across 3+ different hooks**, causing significant cumulative wait time for developers. Many checks are duplicated (formatting, linting, type-checking, tests run multiple times). By **refactoring to use Amp/Claude Code subagents**, we can parallelize independent checks and reduce total wait time from **3-5 minutes to 30-60 seconds** while improving developer experience.

---

## Current Architecture

### Hook Execution Flow

```
git commit
  ↓
pre-commit hook
  ├─ Black formatting (sequential)
  ├─ Ruff import sorting (sequential)
  ├─ Ruff full linting (sequential)
  ├─ mypy type checking (sequential)
  ├─ pytest tests (sequential)
  ├─ verify-common-checks (sequential)
  │  ├─ Poetry lock sync
  │  ├─ Version consistency
  │  ├─ pre-commit-checks (DUPLICATE: runs all above again!)
  │  └─ Beads sync
  └─ Exit: 2-3 min total

git push
  ↓
pre-push hook
  ├─ Black formatting check (DUPLICATE)
  ├─ Ruff linting (DUPLICATE)
  ├─ mypy type checking (DUPLICATE)
  ├─ pytest with retry (DUPLICATE)
  ├─ CI status check (informational)
  └─ Exit: 2-3 min total

Amp task completion (post-task hook)
  ├─ verify-task-complete
  ├─ verify-common-checks (PARTIAL DUPLICATE)
  │  └─ pre-commit-checks subscript again!
  └─ extract-findings-to-beads
```

### Identified Duplication Points

| Check | Pre-commit | Pre-push | Post-task | Count |
|-------|-----------|----------|-----------|-------|
| Black formatting | ✓ | ✓ | ✓ (indirect) | 3 |
| Ruff linting | ✓ | ✓ | ✓ (indirect) | 3 |
| mypy type-checking | ✓ | ✓ | ✓ (indirect) | 3 |
| pytest tests | ✓ | ✓ | ✓ (indirect) | 3 |
| pre-commit-checks subscript | ✓ (via verify-common-checks) | - | ✓ (via verify-common-checks) | 2 |
| Poetry lock verification | ✓ | - | ✓ | 2 |
| Version consistency | ✓ | - | ✓ | 2 |

**Problem:** A developer commits → pushes → completes task in Amp runs the same formatting/linting/type/test checks **5+ times total**, taking 5-10 minutes.

---

## Timeline Impact

### Current (Sequential)

```
Pre-commit:
  Black format:        30s
  Ruff imports:        15s
  Ruff linting:        45s
  mypy:                60s
  Tests:               90s
  verify-common-checks: 30s (includes duplicates)
  ────────────────────────
  TOTAL:               ~4-5 minutes ❌

Push:
  Black check:         20s
  Ruff check:          30s
  mypy check:          50s
  Tests + retry:      120s
  ────────────────────
  TOTAL:               ~3-4 minutes ❌

Post-task:
  Git verification:    10s
  verify-common-checks: 2-3 min (duplication!)
  Findings extraction: 20s
  ────────────────────
  TOTAL:               ~3-4 minutes ❌

DEVELOPER TOTAL:     10-13 MINUTES ❌
```

### Proposed (Parallelized with Subagents)

```
Pre-commit:
  Format (staged files): 15s
  Lint (staged files):   20s parallel
  Type check (changed):  30s parallel  
  Tests (changed):       45s parallel
  Git checks:            10s sequential
  ────────────────────────
  TOTAL:                ~60 seconds ✅

Push:
  (Skipped - already passed in pre-commit, cached result)
  TOTAL:                ~0 seconds ✅

Post-task:
  Git verification:      10s
  Findings extraction:   20s (async in background)
  ────────────────────────
  TOTAL:                ~30 seconds ✅

DEVELOPER TOTAL:     ~90 SECONDS ✅
(vs. 10-13 minutes = 7-8x faster)
```

---

## Optimization Strategy

### 1. Deduplication & Consolidation

**Problem:** Same checks run in multiple hooks.

**Solution:** Create unified check script that caches results.

```bash
.agents/hooks/unified-check
├─ Check if cache is valid (based on file hashes)
├─ If valid, use cached result
├─ If invalid, run all checks once
└─ Output result for all hooks to use
```

**Benefits:**
- Eliminate duplicates
- Faster push/post-task (1-2 sec, just cache lookup)
- Single source of truth

### 2. Parallel Execution with Amp Subagents

**Problem:** All checks run sequentially (Black → Ruff → mypy → pytest).

**Solution:** Use Amp subagents to parallelize independent checks.

#### Amp Subagent: Code Quality Checker

```yaml
name: code-quality-checker
description: |
  Fast parallel code quality checks (formatting, linting, types, tests)
  Runs independently in background to not block main thread.
  PROACTIVELY USED during development.

tools:
  - Bash (for running checks)
  - Read (for file inspection)

system_prompt: |
  You are the Code Quality Checker subagent.
  Run code quality checks in parallel using GNU parallel or similar.
  
  Checks (run simultaneously):
  1. poetry run black --check src/ tests/
  2. poetry run ruff check src/
  3. cd src && poetry run mypy devloop/core/ devloop/agents/
  4. poetry run pytest tests/ -q
  
  Report failures clearly with fix suggestions.
  Cache results with file hashes for fast validation.
```

#### Amp Subagent: CI Monitor

```yaml
name: ci-monitor
description: |
  Background CI status monitoring for pre-push hook.
  Runs asynchronously - non-blocking.

tools:
  - Bash (for gh CLI)

system_prompt: |
  You are the CI Monitor subagent.
  Run in background after pre-push hook.
  
  Check latest main branch CI status:
  1. gh run list --branch main --limit 1
  2. If failed, create Beads issue with thread reference
  3. Alert developer asynchronously (no blocking)
  
  This doesn't block the push, just informs developer.
```

#### Amp Subagent: Async Findings Extractor

```yaml
name: async-findings-extractor
description: |
  Extract DevLoop findings asynchronously after task completion.
  Offloads work from post-task hook to background thread.

tools:
  - Bash
  - Read
  - Grep

system_prompt: |
  You are the Async Findings Extractor.
  Called after task completion (non-blocking).
  
  1. Parse DevLoop logs from .devloop/
  2. Detect patterns across multiple threads
  3. Create Beads issues with discovered-from links
  4. File in .beads/issues.jsonl
  
  This runs in parallel to allow immediate task move.
```

### 3. Smart Check Triggering

**Problem:** Run all tests even if only 1 file changed.

**Solution:** Intelligent change detection.

```bash
# Only run tests for changed modules
CHANGED_MODULES=$(git diff --cached --name-only | grep -o '^[^/]*' | sort -u)
poetry run pytest tests/ -k "$CHANGED_MODULES" -q

# Only check types for changed files
CHANGED_FILES=$(git diff --cached --name-only -- '*.py')
poetry run mypy $CHANGED_FILES

# Only format staged files (Black already does this implicitly)
```

**Benefits:**
- Tests: 120s → 30-45s (for typical changes)
- Type-checking: 60s → 20-30s
- Total pre-commit: 4-5min → 1-2min

### 4. Result Caching

**Problem:** Same checks repeat in pre-push and post-task.

**Solution:** Cache check results with file modification tracking.

```bash
# Cache format: .devloop/check-cache/{hash}.result
STAGED_HASH=$(git diff --cached | sha256sum | cut -d' ' -f1)

if [ -f ".devloop/check-cache/$STAGED_HASH.result" ]; then
    echo "Using cached result from $(cat .devloop/check-cache/$STAGED_HASH.result)"
else
    # Run checks
    # Store result
    echo "$(date +%s)" > ".devloop/check-cache/$STAGED_HASH.result"
fi
```

**Benefits:**
- Pre-push: 3-4min → 5 seconds (cache lookup)
- Massive improvement for rapid commit-push cycles

### 5. Async Background Processing

**Problem:** Post-task hook blocks task completion until findings extracted.

**Solution:** Move extraction to background subagent.

```bash
# In post-task hook (non-blocking):
.agents/hooks/async-findings-extractor &  # Background
EXTRACTION_PID=$!

# Continue with task completion
echo "Task complete (findings extraction in background, PID: $EXTRACTION_PID)"

# Optionally wait with timeout:
timeout 30s wait $EXTRACTION_PID || true
```

**Benefits:**
- Post-task returns immediately
- Findings still extracted (just async)
- Developer can move to next task immediately

---

## Implementation Plan

### Phase 1: Deduplication (2-3 hours)

1. ✓ Create unified check script (`.agents/verify-all`)
2. ✓ Add caching layer
3. ✓ Update all hooks to use unified script
4. ✓ Test: pre-commit/pre-push/post-task consistency

**Expected Gain:** 30% faster (from 10-13min → 7-9min)

### Phase 2: Parallelization with Subagents (4-6 hours)

1. ✓ Create Amp subagent configs (code-quality-checker, ci-monitor, async-findings-extractor)
2. ✓ Refactor pre-commit hook to invoke subagents in parallel
3. ✓ Implement result aggregation
4. ✓ Test parallel execution + error handling
5. ✓ Document in AGENTS.md

**Expected Gain:** 60% faster (from 7-9min → 2-3min)

### Phase 3: Smart Triggering (3-4 hours)

1. ✓ Detect changed modules/files
2. ✓ Implement module-based test filtering
3. ✓ Implement file-based type-check filtering
4. ✓ Test with various commit sizes

**Expected Gain:** Additional 50% faster (from 2-3min → 1-1.5min)

### Phase 4: Result Caching (2-3 hours)

1. ✓ Implement check result hashing
2. ✓ Create cache storage + cleanup
3. ✓ Integrate with pre-push hook
4. ✓ Test cache invalidation

**Expected Gain:** Pre-push 95% faster (from 3-4min → 5-10s)

### Phase 5: Async Background Processing (1-2 hours)

1. ✓ Extract findings to background subagent
2. ✓ Update post-task hook
3. ✓ Test timeout/error handling
4. ✓ Document monitoring

**Expected Gain:** Post-task 90% faster (from 3-4min → 30s)

---

## Subagent Configurations

### Amp Subagent: code-quality-checker

```yaml
---
name: "code-quality-checker"
description: |
  Fast parallel code quality checks (Black, Ruff, mypy, pytest).
  Runs independently without blocking main thread.
  Can be invoked explicitly or automatically when pre-commit runs.
  PROACTIVELY USED by default.

tools:
  - bash
  - read

---

# Code Quality Checker Subagent

You are a specialized code quality verification agent. Your role is to run code quality checks in **parallel** to provide fast feedback to developers.

## Your Responsibilities

1. **Parallel Execution**: Run Black, Ruff, mypy, and pytest simultaneously using `GNU parallel` or similar
2. **Result Aggregation**: Collect failures and present them clearly
3. **Performance Optimization**: Only check staged/changed files when possible
4. **Result Caching**: Store check results with file hashes for quick re-validation

## Checks You Run (In Parallel)

```bash
# All run simultaneously:
poetry run black --check src/ tests/
poetry run ruff check src/
(cd src && poetry run mypy devloop/core/ devloop/agents/)
poetry run pytest tests/ -q
```

## Output Format

If all pass: `✅ All checks passed`
If any fail: Show failures grouped by check type, with fix suggestions

## Usage in Hooks

Called from pre-commit hook:
```bash
amp /code-quality-checker
```

Automatically returns after ~45s with results.
```
```

### Amp Subagent: ci-monitor

```yaml
---
name: "ci-monitor"
description: |
  Background CI status monitoring for pre-push.
  Runs asynchronously - non-blocking warning system.
  Checks main branch CI status and alerts if failed.

tools:
  - bash
  - read

---

# CI Monitor Subagent

You are the CI Status monitoring agent. Your job is to provide non-blocking CI status feedback after push.

## Responsibilities

1. Get latest CI run on main branch
2. Report status (pass/fail/pending)
3. If failed, create Beads issue with thread reference
4. Run asynchronously - never block user

## Execution

```bash
gh run list --branch main --limit 1 --json status,conclusion,createdAt
# Parse and report
```

This runs in background after push completes.
```
```

### Claude Code Subagent: parallel-formatter

```yaml
---
name: "parallel-formatter"
description: |
  Fast parallel file formatting for multiple files.
  Formats TypeScript, Python, JSON, Markdown in parallel using subagents.
  Each file type runs in its own execution context.

tools:
  - read
  - bash (limited)

---

# Parallel Formatter Subagent

You are the Parallel Formatter. Format multiple files efficiently.

## Approach

1. Group files by type (*.ts, *.py, *.json, *.md)
2. Use Claude Code's parallel subagent execution for each type
3. Apply correct formatter per type:
   - Python: Black
   - TypeScript: Prettier
   - JSON: jq/Prettier
   - Markdown: Prettier

## Key Constraint

Since subagents can't spawn subagents, you orchestrate formatting decisions and let the main Claude Code session handle parallel execution.
```
```

---

## Testing Strategy

### Pre-Commit Hook Tests

```bash
# Test 1: Single file change
git checkout -b test/single-file
echo "# Test" >> README.md
git add README.md
git commit -m "test"  # Should complete in ~30s

# Test 2: Multiple files with failures
git checkout -b test/with-failures
echo "import unused" >> src/devloop/core/test.py
git add src/devloop/core/test.py
git commit -m "test"  # Should fail on linting, ~20s

# Test 3: Large change
git checkout -b test/large-change
# Add 50 files
git add .
git commit -m "test"  # Should parallelize, ~60s max
```

### Cache Validation Tests

```bash
# Test 1: Cache hit
git commit -m "test1"    # ~60s (full check)
git commit --amend      # ~5s (cache hit)

# Test 2: Cache invalidation
git commit -m "test1"    # Cache hit ~5s
git checkout src/        # Change tracked file
git add .
git commit -m "test2"    # Cache miss, ~60s (full check)
```

### Subagent Parallelization Tests

```bash
# Measure individual vs parallel
time poetry run black --check src/          # ~20s
time poetry run ruff check src/             # ~30s
time poetry run mypy devloop/ > /dev/null   # ~50s
time poetry run pytest tests/ -q            # ~90s
# Sequential total: ~190s

# With parallel (subagents):
# Should complete in ~90s (longest task)
```

---

## Configuration Changes Required

### `.agents/AGENTS.md` updates

Add subagent configuration section:

```markdown
## Subagents

### code-quality-checker

Parallel code quality checks (formatting, linting, types, tests).
Invoked automatically in pre-commit hook.

### ci-monitor

Async CI status monitoring after push.
Runs in background, non-blocking.

### async-findings-extractor

Background DevLoop findings extraction after task completion.
Runs asynchronously to not block task move.
```

### Hook modifications

**Pre-commit hook:**
- Call unified `verify-all` script
- Invoke `code-quality-checker` subagent for parallelization
- Cache results

**Pre-push hook:**
- Check cache instead of re-running all checks
- Invoke `ci-monitor` subagent in background

**Post-task hook:**
- Keep git verification synchronous
- Move findings extraction to `async-findings-extractor` (background)

---

## Benefits Summary

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Pre-commit time | 4-5 min | 45-60s | **85% faster** |
| Pre-push time | 3-4 min | 5-10s | **95% faster** |
| Post-task time | 3-4 min | 20-30s | **85% faster** |
| Total dev cycle | 10-13 min | 1.5-2 min | **86% faster** |
| Duplicated checks | 5+ runs | 1 run | **5x reduction** |

---

## Risk Mitigation

**Risk:** Parallel execution produces inconsistent results
- **Mitigation:** Each check is independent; parallelize via separate processes, not threads

**Risk:** Cache invalidation bugs
- **Mitigation:** Use file hash-based cache keys; clear on `.git/index` change

**Risk:** Subagent latency
- **Mitigation:** Pre-warm subagent context during development (not on critical path)

**Risk:** Background tasks don't complete
- **Mitigation:** Log PID of background tasks; monitor with `ps`; force cleanup on exit

---

## Next Steps

1. **Create Beads issues** for each phase (dedup, parallelization, smart triggering, caching, async)
2. **Start Phase 1:** Deduplication (highest ROI, lowest risk)
3. **Prototype unified check script** with caching
4. **Measure baseline** pre-commit/pre-push/post-task times
5. **Implement & test** each phase iteratively
6. **Document in AGENTS.md** once stable
