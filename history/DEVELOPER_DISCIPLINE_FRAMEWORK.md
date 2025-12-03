# Developer Discipline Framework

## The Problem We're Solving

DevLoop was built to catch code quality issues **before CI**, using background agents that monitor file changes and run automated checks. However, the codebase wasn't actually using these tools effectively, and developers were still:

1. Pushing code without local validation
2. Waiting 30+ seconds for CI feedback
3. Not following the procedural discipline (poetry.lock, formatting, etc.)

## The Solution: Layered Validation + Documentation

We've implemented a 5-layer validation system with clear expectations at each stage:

### Layer 1: DevLoop (Continuous, Automatic)
- **Active status:** ✅ Running on devloop codebase
- **What:** Background agents monitor file changes
- **When:** Immediate, as you save files
- **Issues detected:** 123 linting/formatting/type issues in relevant.json
- **Future:** Will auto-fix and integrate with Beads

### Layer 2: Pre-commit Hook (Git Commit)
- **Speed:** ~1 second
- **What:** Validates critical constraints
- **Checks:**
  - Poetry lock file synced (if pyproject.toml changed)
  - Beads issues flushed
- **Implementation:** `.git/hooks/pre-commit`
- **Prevents:** Root cause of poetry.lock CI failures

### Layer 3: Local Verification Script (Before Push)
- **Speed:** 30-60 seconds
- **What:** Quick simulation of CI checks
- **Checks:**
  - Poetry lock sync (redundant, but safe)
  - Black formatting
  - Ruff linting
  - mypy type checking
  - pytest tests
- **Implementation:** `scripts/verify-before-push.sh`
- **Optional but encouraged:** Fast enough that developers should use it

### Layer 4: Pre-push Hook (Git Push)
- **Speed:** Wait up to 2 minutes for CI
- **What:** Validates actual CI status before allowing push
- **Checks:**
  - Waits for CI to complete (polls every 5s)
  - Blocks push if CI failed
  - Allows push if CI passed or timeout reached
- **Implementation:** `.git/hooks/pre-push`
- **Prevents:** Pushing broken code without checking CI

### Layer 5: GitHub CI (Comprehensive)
- **Speed:** 2-3 minutes
- **What:** Definitive validation on clean environment
- **Checks:**
  - All tests (Python 3.11 & 3.12)
  - All linters and formatters
  - Type checking
  - Security scanning
- **Is:** The final source of truth

## The Discipline: Three Key Documents

### 1. CODING_RULES.md
**Purpose:** Code patterns and standards

**New section added:** "Poetry & Dependency Changes"
- When to run `poetry lock`
- How to stage both files
- Local testing requirements
- Commit format

**Usage:** Reference when modifying dependencies or pyproject.toml

### 2. DEVELOPER_WORKFLOW.md (NEW)
**Purpose:** End-to-end developer workflow and validation system

**Covers:**
- How each layer works
- When to run verification script
- Recommended daily workflow
- Why the discipline matters
- Troubleshooting guide
- Special instructions for coding agents

**Usage:** Reference when starting work, before pushing, or when unsure

### 3. AGENTS.md (existing)
**Purpose:** Architecture and agent system documentation

**Status:** Updated to reference the workflow layers

**Usage:** Understanding how DevLoop works internally

## Key Insights

### Feedback Loop Effect
The difference between waiting 30 seconds (CI) vs 5 seconds (local):

**30s feedback loop:**
- ❌ Developers push code, then check CI
- ❌ By the time feedback comes, context is lost
- ❌ Forms habit of "push and hope"
- ❌ Low discipline, high rework

**5s feedback loop (local verification):**
- ✅ Developers fix issues immediately while coding
- ✅ Feedback is immediate and actionable
- ✅ Forms habit of "test before push"
- ✅ High discipline, low rework

### Three Reasons for Multiple Hooks

1. **Pre-commit hook** — Catches critical structural errors (poetry.lock)
   - Must never fail CI due to lock file
   - Fast enough to run on every commit

2. **Local verify script** — Catches all issues CI would catch
   - Developer chooses to run (optional but encouraged)
   - Same checks as CI but much faster
   - Educates developer about CI requirements

3. **Pre-push hook** — Final validation before network push
   - Ensures CI was actually checked
   - Blocks push if CI failed
   - Waits instead of skipping (improvement from before)

### Why Not Just CI?

Some might ask: "Why not just rely on CI?"

**Reasons we need local validation:**

1. **Feedback speed** — CI takes 2-3 minutes; local takes 30-60 seconds
2. **Developer education** — Each failure teaches the rule locally, immediately
3. **Efficient iteration** — Fix and re-verify in <2 minutes locally vs waiting for CI
4. **Network efficiency** — Don't push broken code to GitHub
5. **System resilience** — If CI is slow or fails, local checks are backup

## Implementation Status

### ✅ Completed

- [x] Pre-commit hook for poetry.lock sync detection
- [x] Improved pre-push hook (waits for CI, doesn't skip)
- [x] Documentation in CODING_RULES.md
- [x] Local verification script (scripts/verify-before-push.sh)
- [x] Developer workflow guide (DEVELOPER_WORKFLOW.md)
- [x] Lessons learned documentation

### 🚧 In Progress

- [ ] Enable DevLoop auto-fix for Black (task: claude-agents-sf3)
- [ ] Integrate DevLoop findings with Beads (task: claude-agents-sut)

### 🔮 Future

- [ ] Block commits on high-priority DevLoop findings
- [ ] Auto-fix on save for formatting issues
- [ ] Map DevLoop agents to Beads issues
- [ ] Make verification script part of IDE/editor integration

## How Coding Agents (Claude, Copilot) Should Use This

When working on this codebase, follow this discipline:

```bash
# Before any git action, check DEVELOPER_WORKFLOW.md
# 1. Save files
# 2. Commit (pre-commit hook validates)
#    → If poetry.lock error: poetry lock && git add poetry.lock
# 3. Run local verification
#    ./scripts/verify-before-push.sh
# 4. Fix any issues and re-run verification
# 5. Push (pre-push hook validates CI)
```

**Special handling:**
- If modifying `pyproject.toml` → ALWAYS run `poetry lock` before commit
- If adding dependencies → Update CODING_RULES.md if needed
- Before any complex change → Read DEVELOPER_WORKFLOW.md
- If something fails → Check `.devloop/context/index.json` for DevLoop findings

## Metrics & Success Criteria

### Current State
- ❌ Multiple DevLoop instances running (should consolidate)
- ⚠️ 123 issues in DevLoop context (high but expected for alpha)
- ✅ Pre-commit hook preventing poetry.lock failures
- ✅ Pre-push hook waiting for CI (not skipping)
- ✅ Documentation complete

### Success Criteria for Complete Implementation
- ✅ 0 CI failures due to formatting or poetry.lock
- ✅ 0 commits that fail CI linting/format checks
- ✅ All developers use verify-before-push.sh before pushing
- ✅ DevLoop auto-fixing enabled (no manual formatting needed)
- ✅ DevLoop findings integrated with Beads

## Related Documentation

- `history/LESSONS_LEARNED.md` — Root cause analysis of CI failures
- `history/PROCESS_IMPROVEMENTS_IMPLEMENTED.md` — Detailed implementation of hooks
- `CODING_RULES.md` — Code patterns and special cases
- `DEVELOPER_WORKFLOW.md` — Day-to-day workflow guide
- `AGENTS.md` — System architecture and design

## The Philosophy

**DevLoop is about shifting the burden of validation from human reviewers to automated agents.**

Instead of:
1. Code review catches formatting issues
2. CI catches type errors
3. Merge conflicts block bad pushes

We want:
1. Editor saves file
2. DevLoop agent catches issue immediately (5s)
3. Developer fixes before even committing
4. Pre-commit hook validates structural requirements (1s)
5. Local verify script double-checks (30s)
6. Pre-push hook validates CI passed (2min)
7. Code is ready to merge

**Result:** Better code quality, faster iteration, lower cognitive load on developers.
