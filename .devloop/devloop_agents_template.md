# AI Agent Development Workflow

**CRITICAL INSTRUCTIONS FOR AI CODING AGENTS**

This project uses [bd (beads)](https://github.com/wioota/devloop) for issue tracking and enforces strict development discipline.

---

## ⛔️ ABSOLUTE RULE #1: NO MARKDOWN FILES

**Use Beads for ALL planning, tracking, and analysis—not markdown files.**

### FORBIDDEN FILES (ZERO TOLERANCE)

❌ **NEVER** create these files:
- `*_PLAN.md` - Planning documents
- `*_ANALYSIS.md` - Analysis documents
- `*_SUMMARY.md` - Summary documents
- `*_STRATEGY.md` - Strategy documents
- `*_STATUS.md` - Status tracking documents
- `*_DESIGN.md` - Design documents
- `*_NOTES.md` - Note documents
- Any ad-hoc markdown planning/analysis/tracking files

### ALLOWED FILES (ONLY 6)

✅ **ONLY** these markdown files are permitted:
1. `README.md` - Project overview
2. `CHANGELOG.md` - Release notes
3. `AGENTS.md` - This file
4. `CODING_RULES.md` - Development standards
5. `LICENSE` - License file
6. `.github/copilot-instructions.md` - GitHub Copilot instructions

### USE BEADS INSTEAD

```bash
# Planning → Beads epic with description
bd create "Feature XYZ design" -t epic -d "Requirements: ... Design: ..."

# Analysis → Beads task with findings
bd create "Analysis: Component X" -d "Investigation: ... Findings: ..."

# Status tracking → Update beads status
bd update <id> --status in_progress

# Discovered work → Link with discovered-from
bd create "Bug found" -p 1 --deps discovered-from:<parent-id>
```

---

## ⛔️ ABSOLUTE RULE #2: USE BEADS FOR ALL TASK MANAGEMENT

**Beads (`bd`) is the ONLY task management system—no markdown TODOs, checklists, or other tracking.**

### QUICK REFERENCE

```bash
# Check what's ready to work on
bd ready --json

# Create new issue
bd create "Issue title" -t bug|feature|task|epic|chore -p 0-4 --json

# Claim issue before starting
bd update bd-42 --status in_progress --json

# Close completed issue
bd close bd-42 --reason "Completed in commit abc123" --json
```

### ISSUE TYPES

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### PRIORITIES

- `0` - **CRITICAL** (security, data loss, broken builds)
- `1` - **HIGH** (major features, important bugs)
- `2` - **MEDIUM** (default, nice-to-have)
- `3` - **LOW** (polish, optimization)
- `4` - **BACKLOG** (future ideas)

### MANDATORY WORKFLOW

**1. Session Start:**
```bash
bd ready              # See unblocked work
bd show <issue-id>    # Review issue details
```

**2. During Work:**
```bash
bd update <id> --status in_progress   # Claim the issue
bd create "Bug found" -p 1             # File discovered issues
bd dep add <new-id> <parent-id> --type discovered-from
```

**3. Session End (MANDATORY):**
```bash
bd close <id> --reason "Implemented in commit abc123"
git add .beads/issues.jsonl           # ALWAYS commit beads with code
git commit -m "feat: Implement feature XYZ"
git push origin main
```

### FORBIDDEN ACTIONS

❌ Create `.md` files for task tracking
❌ Use markdown headers for planning
❌ Leave issues without status updates
❌ Forget to push `.beads/issues.jsonl` at session end
❌ Use external issue trackers or TODO lists

---

## ⛔️ ABSOLUTE RULE #3: COMMIT & PUSH AFTER EVERY TASK

**EVERY completed task MUST end with commit and push.**

### ENFORCEMENT

This is automatically enforced by:
1. `.git/hooks/pre-commit` - Validates format, lint, types, tests
2. `.git/hooks/pre-push` - Checks CI status before push
3. `.agents/verify-task-complete` - Verifies all checks pass

### VERIFICATION

```bash
# Run this after completing work
.agents/verify-task-complete
# Expected: ✅ PASS: All checks successful
```

---

## ⛔️ ABSOLUTE RULE #4: PRE-FLIGHT CHECKLIST

**Run at the START of EVERY session to prevent formatting debt cascade.**

### WHY THIS MATTERS

Formatting debt compounds quickly:
1. Unformatted files accumulate → Pre-commit gets noisy
2. Hook flags unrelated files → Warnings become noise
3. Developer ignores hooks → Real issues bypass checks
4. Bad commits slip through → Quality degrades

### MANDATORY PRE-FLIGHT COMMANDS

Run these **BEFORE** starting any work:

```bash
# 1. Format entire codebase
poetry run black src/ tests/

# 2. Lint and auto-fix issues
poetry run ruff check src/ tests/ --fix
poetry run mypy src/

# 3. Run full test suite (if time permits)
poetry run pytest

# 4. Verify hooks work
.agents/verify-task-complete
```

**Best practice:** Run immediately after `bd ready` at session start.

---

## ⛔️ ABSOLUTE RULE #5: CI VERIFICATION (AUTOMATIC)

**Pre-push hook automatically blocks pushes if CI is failing.**

### WORKFLOW

1. Make changes: `git add . && git commit -m "..."`
2. Push: `git push origin main`
3. **Hook runs automatically:**
   - ✅ CI passed → Push proceeds
   - ❌ CI failed → Push blocked with error
   - ⚠️ No CI runs → Push allowed (first push)

### IF PUSH BLOCKED

```bash
# 1. Check what failed
gh run view <run-id> --log-failed

# 2. Fix issues locally
# (make changes)

# 3. Commit and push again
git add . && git commit -m "fix: Address CI failures"
git push origin main
# Hook verifies new CI run before allowing push
```

---

## 🔧 ESSENTIAL COMMANDS

**ALWAYS use devloop commands instead of manual operations.**

### CORE WORKFLOW

```bash
# Initialize devloop in project
devloop init /path/to/project

# Start watching for file changes
devloop watch .

# Run code quality verification
devloop verify-work

# Extract findings and create Beads issues
devloop extract-findings-cmd

# Update git hooks from latest templates
devloop update-hooks
```

### RELEASE MANAGEMENT

**REQUIRED:** Use these for ALL releases. Do NOT manually bump versions or tag.

```bash
# Check if ready to release
devloop release check <version>

# Publish release (full automated workflow)
devloop release publish <version>

# Dry-run to preview
devloop release publish <version> --dry-run
```

See [RELEASE_PROCESS.md](./RELEASE_PROCESS.md) for complete workflow.

### BEADS COMMANDS

```bash
# Check ready work
bd ready --json

# Create issue
bd create "Task" -t task -p 1 --json

# Update status
bd update bd-42 --status in_progress --json

# Close issue
bd close bd-42 --reason "Done" --json
```

See [CLI_REFERENCE.md](./CLI_REFERENCE.md) for complete documentation.

---

## 🔒 TOKEN SECURITY

**NEVER commit API keys, tokens, or credentials to version control.**

### FORBIDDEN

❌ Commit API keys, tokens, credentials
❌ Pass tokens as command-line arguments
❌ Hardcode tokens in code/config
❌ Log full tokens in error messages

### REQUIRED

✅ Use environment variables (`GITHUB_TOKEN`, `PYPI_TOKEN`)
✅ Enable token expiry and rotation (30-90 days)
✅ Use read-only or scoped tokens when possible
✅ Scan commits for leaked secrets before pushing

See [docs/TOKEN_SECURITY.md](./docs/TOKEN_SECURITY.md) for complete guide.

---

## 📋 DOCUMENTATION PRACTICES

**Tracked files must NEVER be accidentally deleted.**

### PREVENTION RULES

**1. Commit Message Discipline**
- Use descriptive commit messages
- When deleting docs: `git commit -m "docs: Remove outdated X (explain why)"`
- Explain WHY files are deleted

**2. Pre-Commit Awareness**
```bash
git status                          # Check for deletions
git restore <filename>              # Undo accidental deletion
```

**3. CI Validation (Automatic)**
- Validates all README.md links resolve
- Blocks deletions without "docs:" prefix
- Fails if README references non-existent files

**4. Update References**
- After deleting docs, update README.md links
- CI will fail if broken links exist

---

## 📚 REFERENCE DOCUMENTATION

**For detailed information:**

- [CLI_REFERENCE.md](./CLI_REFERENCE.md) - Complete command documentation
- [RELEASE_PROCESS.md](./RELEASE_PROCESS.md) - Release workflow
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design
- [CODING_RULES.md](./CODING_RULES.md) - Development standards
- [docs/TOKEN_SECURITY.md](./docs/TOKEN_SECURITY.md) - Token security

---

## ✅ CHECKLIST FOR AI AGENTS

### BEFORE STARTING ANY TASK

1. ✅ Run pre-flight checklist (format, lint, test)
2. ✅ Check `bd ready` for available work
3. ✅ Claim issue: `bd update <id> --status in_progress`

### DURING TASK

4. ✅ Use `bd create` for discovered work
5. ✅ **NEVER** create markdown planning files
6. ✅ **ALWAYS** use Beads for planning/analysis
7. ✅ Link discovered work: `bd dep add <new> <parent> --type discovered-from`

### AFTER TASK

8. ✅ Close issue: `bd close <id> --reason "..."`
9. ✅ Commit `.beads/issues.jsonl` with code changes
10. ✅ Push to origin: `git push origin main`
11. ✅ Verify: `.agents/verify-task-complete`

---

## 🚨 ZERO TOLERANCE VIOLATIONS

**These actions cause immediate failure:**

❌ Creating `*_PLAN.md`, `*_ANALYSIS.md`, or any ad-hoc markdown files
❌ Leaving issues without status updates
❌ Forgetting to push `.beads/issues.jsonl` at session end
❌ Committing without running pre-flight checklist
❌ Manually tagging releases without `devloop release`
❌ Committing API keys, tokens, or credentials
❌ Using markdown TODO lists or external trackers

---

## 💡 QUICK START FOR NEW AGENTS

**First time working on this project?**

```bash
# 1. Check what's ready
bd ready

# 2. Pick an issue and claim it
bd update bd-42 --status in_progress

# 3. Run pre-flight checklist
poetry run black src/ tests/
poetry run ruff check src/ tests/ --fix
poetry run mypy src/

# 4. Work on the issue
# (make changes)

# 5. When done, close issue and push
bd close bd-42 --reason "Completed in commit abc123"
git add .
git commit -m "feat: Implement feature"
git push origin main

# 6. Verify everything passed
.agents/verify-task-complete
```

**When in doubt:**
- Ask before creating files
- Use Beads for all tracking
- Run verification commands
- Check this file for rules
