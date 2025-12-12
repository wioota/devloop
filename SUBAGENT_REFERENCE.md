# Subagent Reference Guide

This project uses specialized subagents in both **Amp** and **Claude Code** to parallelize code quality checks and maintain developer workflow efficiency.

## Quick Start

### Using Amp Subagents

```bash
# During pre-commit hook
amp /code-quality-checker      # Parallel formatting, linting, type-checking, tests
amp /ci-monitor                # Background CI status monitoring
amp /async-findings-extractor  # Background DevLoop findings extraction
```

### Using Claude Code Subagents

```bash
# In Claude Code editor
/code-quality-checker          # Parallel code quality checks
/parallel-file-formatter       # Format multiple files by type
/ci-status-monitor             # Monitor CI pipeline
/test-coverage-analyzer        # Analyze test coverage gaps
```

---

## Subagent Inventory

### Amp Subagents

Located in `.amp/subagents/` (to be created in Phase 2)

| Agent | Purpose | When to Use | Tools |
|-------|---------|------------|-------|
| `code-quality-checker` | Parallel Black/Ruff/mypy/pytest | Pre-commit hook | Bash, Read |
| `ci-monitor` | Background CI status monitoring | After push (async) | Bash |
| `async-findings-extractor` | Extract DevLoop findings async | After task completion | Bash, Read, Grep |

### Claude Code Subagents

Located in `.claude/agents/`

| Agent | Purpose | When to Use | Tools |
|-------|---------|------------|-------|
| `code-quality-checker` | Parallel code quality validation | During development | Bash, Read, Grep |
| `parallel-file-formatter` | Format multiple files by type | Formatting large changes | Bash, Read |
| `ci-status-monitor` | Monitor CI/CD pipeline | Before/after pushes | Bash, WebFetch, Read |
| `test-coverage-analyzer` | Analyze test coverage gaps | After tests pass | Bash, Read, Grep |
| `test-quality-reviewer` | Review test quality/redundancy | After writing tests | Glob, Grep, Read, WebFetch |

---

## Detailed Subagent Specifications

### Code Quality Checker

**Purpose:** Run code quality checks in parallel (Black, Ruff, mypy, pytest)

**Location:**
- Amp: `.amp/subagents/code-quality-checker.md`
- Claude Code: `.claude/agents/code-quality-checker.md`

**When to use (PROACTIVE):**
- Writing code that needs formatting/linting/type-checking
- Before committing changes
- Verifying code quality

**Execution time:**
- Sequential: ~190 seconds (30s + 30s + 50s + 90s)
- Parallel: ~90 seconds (longest task dominates)
- With caching: ~5 seconds

**Key feature:** Runs all checks simultaneously instead of sequentially

**Example:**
```
Claude: "Let me check code quality"
/code-quality-checker

Agent: (Runs in parallel)
  - Black formatting check
  - Ruff linting
  - mypy type checking
  - pytest tests

✅ Result: All passed in ~90 seconds
```

---

### Parallel File Formatter

**Purpose:** Format multiple files across different languages simultaneously

**Location:** `.claude/agents/parallel-file-formatter.md`

**When to use (PROACTIVE in Claude Code):**
- Formatting many files across different languages
- Mass refactoring with formatting needs (convert to Tailwind, etc.)
- Style consistency pass across codebase

**Supported formats:**
- Python (Black)
- TypeScript/TSX (Prettier)
- JSON (Prettier)
- Markdown (Prettier)

**Execution time:**
- Sequential (one type at a time): ~60 seconds
- Parallel (all types together): ~30 seconds

**Key feature:** Groups by file type and runs formatters in parallel

**Example:**
```
Claude: "Format all these files"
/parallel-file-formatter

Agent: (Groups by type, runs in parallel)
  - Python files → Black
  - TypeScript files → Prettier
  - JSON files → Prettier
  - Markdown files → Prettier

✅ Result: 6 files formatted in ~30 seconds
```

---

### CI Status Monitor

**Purpose:** Monitor CI/CD pipeline health and alert on failures

**Location:**
- Amp: `.amp/subagents/ci-monitor.md`
- Claude Code: `.claude/agents/ci-status-monitor.md`

**When to use:**
- Before pushing major changes (check main branch health)
- After pushing (background monitoring)
- Team awareness ("is CI broken?")

**Execution time:**
- First check: ~3-5 seconds
- Cached status: ~0.5 seconds
- Background: Non-blocking

**Key features:**
- Non-blocking (runs in background)
- Alerts on failures with actionable info
- Links to failed runs and logs
- Suggests fixes

**Example:**
```
Claude: "Check CI status before push"
/ci-status-monitor

Agent: (Checks GitHub Actions)
✅ Main branch: Healthy
   All checks passed 2 minutes ago
   Safe to push
```

---

### Test Coverage Analyzer

**Purpose:** Analyze test coverage and identify gaps

**Location:** `.claude/agents/test-coverage-analyzer.md`

**When to use (PROACTIVE in Claude Code):**
- After test suite passes (check coverage health)
- Before releases (ensure adequate coverage)
- When adding new features (assess coverage impact)
- During refactoring (verify coverage didn't drop)

**Execution time:** ~10 seconds

**Key features:**
- Identifies critical coverage gaps
- Prioritizes which tests to write next
- Assesses test quality (not just coverage %)
- Provides actionable recommendations

**Example:**
```
Claude: "Check test coverage"
/test-coverage-analyzer

Agent: (Analyzes coverage report)
📊 Overall: 87% (excellent)
   
   Gaps identified:
   🔴 GitHub provider: 45% (critical)
   🟡 Post-task hook: 72% (medium)
   
   Recommendation: Write 15-20 tests for provider

✅ Result: Action items prioritized
```

---

### Test Quality Reviewer

**Purpose:** Review tests for redundancy, anti-patterns, and quality issues

**Location:** `.claude/agents/test-quality-reviewer.md`

**When to use (PROACTIVE in Claude Code):**
- After writing test files
- When test suite grows large
- Before releases
- During code review

**Execution time:** ~30-60 seconds

**Key features:**
- Detects redundant tests
- Flags testing anti-patterns
- Assesses test effectiveness
- Suggests consolidation/cleanup

**Example:**
```
Claude: "Review test quality"
/test-quality-reviewer

Agent: (Analyzes test files)
📋 Summary: Good (45 tests analyzed)
   
   Issues found:
   - 3 redundant test groups
   - 2 tests testing implementation details
   - 1 flaky test pattern detected
   
   Recommendations:
   - Consolidate auth tests (5 redundant)
   - Remove mock-only tests (not testing behavior)

✅ Result: Test suite optimization plan
```

---

### Async Findings Extractor

**Purpose:** Extract DevLoop findings asynchronously (background)

**Location:** `.amp/subagents/async-findings-extractor.md`

**When to use:**
- Post-task completion in Amp (async, doesn't block)
- Background processing of development findings
- Creating linked Beads issues

**Execution time:**
- Async/background: Doesn't block user
- Typical completion: 30-60 seconds
- User can continue immediately

**Key features:**
- Non-blocking (runs in background)
- Monitors and logs progress
- Creates Beads issues with thread references
- Graceful error handling

**Example:**
```
Amp task complete
Post-task hook triggers:
  /async-findings-extractor &  # Background

User sees: "Task verified. Moving to next task."
(Findings extraction continues in background)

Later: DevLoop findings appear in .beads/issues.jsonl
       as linked issues with thread references
```

---

## Integration with Hooks

### Pre-commit Hook

```bash
# Calls code-quality-checker in Amp
# Parallel execution: formatting, linting, typing, tests
# Time: ~90 seconds (vs 4-5 minutes sequential)
```

### Pre-push Hook

```bash
# Checks cache from pre-commit
# If cached (5 seconds), skips checks
# If cache miss, runs full code-quality-checker
# Invokes ci-monitor in background
```

### Post-task Hook (Amp)

```bash
# Verifies commit/push completion
# Invokes async-findings-extractor in background (non-blocking)
# Returns immediately so user can move to next task
```

---

## Usage Patterns

### Pattern 1: Explicit Invocation

User asks Claude/Amp to run a specific subagent:

```
Claude/Amp: "Run code quality checks"
/code-quality-checker
```

Result: Subagent runs with full context output.

### Pattern 2: Automatic PROACTIVE Usage

Subagent description marked with "PROACTIVELY USED":
- Claude/Amp automatically invokes when context matches
- User doesn't need to explicitly request
- Seamless integration into workflow

### Pattern 3: Background Async

Subagent invoked in background without blocking:

```bash
/async-findings-extractor &  # Background PID
# User continues work
# Results appear asynchronously
```

### Pattern 4: Chained Subagents

One subagent calls another (Claude Code only):

```
Code Quality Check fails
  ↓
Formatter offers to fix formatting
  ↓
Re-run quality check
  ↓
Tests pass
```

---

## Performance Characteristics

### Execution Time Summary

| Subagent | Sequential | Parallel | Cached |
|-----------|-----------|----------|--------|
| code-quality-checker | 190s | 90s | 5s |
| parallel-file-formatter | 60s | 30s | N/A |
| ci-status-monitor | 5s | 5s | 0.5s |
| test-coverage-analyzer | 15s | 15s | 5s |
| test-quality-reviewer | 60s | 60s | N/A |

### Resource Usage

- **code-quality-checker**: ~300MB RAM, 25% CPU
- **parallel-file-formatter**: ~100MB RAM, 10% CPU
- **ci-status-monitor**: ~50MB RAM, <1% CPU
- **test-coverage-analyzer**: ~200MB RAM, 15% CPU
- **test-quality-reviewer**: ~250MB RAM, 20% CPU

All designed to be lightweight and non-blocking.

---

## Troubleshooting

### Subagent Not Found

**Problem:** "Subagent XYZ not found"

**Solution:**
1. Check if subagent file exists (`.claude/agents/` or `.amp/subagents/`)
2. Verify file name matches subagent name
3. Check YAML frontmatter (name, description, tools)
4. Reload Claude Code or Amp session

### Subagent Timeout

**Problem:** Subagent runs longer than expected or times out

**Solution:**
1. Check if resources (disk, CPU) are constrained
2. Reduce scope (e.g., fewer files, specific module)
3. Run synchronously first to debug (not in background)
4. Check logs in `.devloop/` for errors

### Tool Access Error

**Problem:** "Tool XYZ not available to subagent"

**Solution:**
1. Check tool list in subagent YAML frontmatter
2. Verify tool name is correct (Bash, Read, Grep, etc.)
3. Some tools may require extra permissions/installation
4. Try reducing tool requirements and re-testing

### Inconsistent Results

**Problem:** Subagent produces different results on repeat runs

**Solution:**
1. Check if results are cached (clear cache to force re-run)
2. Verify input files haven't changed unexpectedly
3. Run with verbose output to see what changed
4. Check system resources (disk space, memory)

---

## Best Practices

### ✅ DO

- Use subagents for their designed purpose (don't try to use formatter for linting)
- Let PROACTIVE subagents trigger automatically when appropriate
- Run subagents early and often (fast feedback)
- Trust cached results (they're validated)
- Monitor background subagents with logs

### ❌ DON'T

- Run all subagents on every file change (use selectively)
- Ignore subagent recommendations without understanding them
- Force synchronous runs of background subagents
- Modify subagent configs without understanding the impact
- Rely on subagents as sole quality gate (still use CI/CD)

---

## Configuration

### Adding New Subagents

1. **Create YAML frontmatter** with name, description, tools
2. **Write system prompt** with detailed instructions
3. **Add examples** of when to use
4. **Test manually** before deploying
5. **Document in this reference** for team knowledge

### Customizing Existing Subagents

1. Edit the `.md` file directly
2. Modify system prompt or tools as needed
3. Test to ensure behavior matches expectations
4. Commit changes to version control

### Disabling Subagents

To disable a subagent temporarily:
- Rename file: `agent-name.md.disabled`
- Or comment out the YAML frontmatter
- Or set `disabled: true` in frontmatter (if supported)

---

## Related Documentation

- **HOOK_OPTIMIZATION_ANALYSIS.md** - Detailed optimization strategy
- **AGENTS.md** - Overall architecture and guidelines
- **CODING_RULES.md** - Development standards
- **README.md** - Project overview

---

## Summary

Subagents enable **developer workflow optimization** through:

1. **Parallelization** - Run independent checks together (7-8x faster)
2. **Specialization** - Each agent is expert in its domain
3. **Background Processing** - Non-blocking async work
4. **Intelligence** - PROACTIVE triggering when appropriate
5. **Feedback** - Clear, actionable results

**Target impact:** Reduce dev cycle wait time from 10-13 minutes to 90 seconds (86% faster).
