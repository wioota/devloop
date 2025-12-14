# AI Agent Development Workflow

**CRITICAL INSTRUCTIONS FOR AI CODING AGENTS**

This project uses [bd (beads)](https://github.com/wioota/devloop) for issue tracking and enforces strict development discipline.

---

## ⛔️ ABSOLUTE RULE #1: NO MARKDOWN FILES

**THIS IS AN ABSOLUTE RULE FOR ALL AGENTS. NO EXCEPTIONS.**

### **FORBIDDEN FILES**

❌ **NEVER** create `*_PLAN.md` files
❌ **NEVER** create `*_ANALYSIS.md` files
❌ **NEVER** create `*_SUMMARY.md` files
❌ **NEVER** create `*_STRATEGY.md` files
❌ **NEVER** create `*_STATUS.md` files
❌ **NEVER** create `*_DESIGN.md` files
❌ **NEVER** create `*_NOTES.md` files
❌ **NEVER** create any ad-hoc markdown planning/analysis/tracking files

### **ALLOWED FILES (ONLY 6)**

✅ `README.md` - Project overview
✅ `CHANGELOG.md` - Release notes
✅ `AGENTS.md` - This file
✅ `CODING_RULES.md` - Development standards
✅ `LICENSE` - License file
✅ `.github/copilot-instructions.md` - GitHub Copilot instructions

### **WHAT TO DO INSTEAD**

**USE BEADS (`bd`) FOR ALL PLANNING, TRACKING, ANALYSIS:**

```bash
# Planning a feature
bd create "Feature XYZ design" -t epic -d "Requirements: ... Design: ..."

# Recording analysis
bd create "Analysis: Component X" -d "Investigation results: ... Findings: ..."

# Tracking status
bd update <id> --status in_progress

# Found bug during work
bd create "Bug found" -p 1 --deps discovered-from:<parent-id>
```

---

## ⛔️ ABSOLUTE RULE #2: USE BEADS FOR ALL TASK MANAGEMENT

**Beads (`bd`) is the ONLY task management system. Do NOT use markdown, TODOs, or other tracking methods.**

### **Quick Reference**

```bash
# Check what's ready to work on
bd ready --json

# Create new issue
bd create "Issue title" -t bug|feature|task -p 0-4 --json

# Claim issue before starting work
bd update bd-42 --status in_progress --json

# Close completed issue
bd close bd-42 --reason "Completed" --json
```

### **Issue Types**

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### **Priorities**

- `0` - **CRITICAL** (security, data loss, broken builds)
- `1` - **HIGH** (major features, important bugs)
- `2` - **MEDIUM** (default, nice-to-have)
- `3` - **LOW** (polish, optimization)
- `4` - **BACKLOG** (future ideas)

### **MANDATORY Workflow**

**1. Start of session:**
```bash
bd ready              # See what's ready to work on
bd show <issue-id>    # Review issue details
```

**2. During work:**
```bash
bd update <id> --status in_progress   # Claim the issue
bd create "Bug found" -p 1             # File discovered issues
bd dep add <new-id> <parent-id> --type discovered-from
```

**3. End of session (MANDATORY):**
```bash
bd close <id> --reason "Implemented in PR #42"
git add .beads/issues.jsonl           # Commit beads changes
git commit -m "Work session update"
git push origin main
```

### **FORBIDDEN Actions**

❌ Create `.md` files for task tracking
❌ Use markdown headers for planning
❌ Leave issues without status updates
❌ Forget to push `.beads/issues.jsonl` at session end

---

## ⛔️ ABSOLUTE RULE #3: COMMIT & PUSH AFTER EVERY TASK

**EVERY completed task MUST end with `git add`, `git commit`, `git push origin main`**

This is **automatically enforced** by:
1. Git hooks (pre-commit, pre-push)
2. Amp post-task verification hook
3. `.agents/verify-task-complete` script

**Verification command:**
```bash
.agents/verify-task-complete
# Should show: ✅ PASS: All checks successful
```

---

## ⛔️ ABSOLUTE RULE #4: PRE-FLIGHT CHECKLIST

**CRITICAL:** Run this checklist **at the start of each development session** to prevent cascading failures.

### **Why This Matters**

Formatting debt compounds quickly:
1. **Formatting debt accumulates** → Multiple unformatted files build up
2. **Pre-commit hook gets noisy** → Flags unrelated files
3. **Developer ignores hooks** → Pre-commit warnings become noise
4. **Bad commits slip through** → Real issues bypass pre-commit

### **Pre-Flight Commands (MANDATORY)**

Run these **BEFORE** starting any work:

```bash
# 1. Format entire codebase
poetry run black src/ tests/

# 2. Lint and check for issues
poetry run ruff check src/ tests/ --fix
poetry run mypy src/

# 3. Run full test suite (if time permits)
poetry run pytest

# 4. Verify hooks work
.agents/verify-task-complete
```

**Best practice**: Make pre-flight checklist a habit at session start, right after `bd ready`.

---

## ⛔️ ABSOLUTE RULE #5: CI VERIFICATION (AUTOMATIC)

**The `.git/hooks/pre-push` hook automatically checks CI status before allowing pushes.**

### **Workflow**

1. Make changes and commit: `git add . && git commit -m "..."`
2. Push: `git push origin main`
3. **Pre-push hook runs automatically:**
   - Checks if `gh` CLI is installed
   - Gets the latest CI run status for your branch
   - If CI failed: blocks push and shows error
   - If CI passed: allows push to proceed
   - If no runs yet: allows push

### **If Push is Blocked**

1. Check what failed: `gh run view <run-id> --log-failed`
2. Fix the issues locally
3. Commit and push again
4. Pre-push hook will verify the new CI run before allowing push

---

## 🔧 ESSENTIAL COMMANDS

**ALWAYS use devloop commands instead of manual operations.**

### **Core Workflow**

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

### **Release Management**

**REQUIRED**: Use these for ALL releases. Do NOT do manual version bumping or tagging.

```bash
# Check if ready to release
devloop release check <version>

# Publish a release (full automated workflow)
devloop release publish <version>
```

See [RELEASE_PROCESS.md](./RELEASE_PROCESS.md) for complete release workflow.

### **Beads Commands**

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

See [CLI_REFERENCE.md](./CLI_REFERENCE.md) for complete command documentation.

---

## 📋 DOCUMENTATION PRACTICES

**Files tracked in git must NEVER be accidentally deleted.**

### **Prevention Rules**

**1. Commit Message Discipline**
- Always use descriptive commit messages
- When deleting docs, include explicit annotation:
  ```bash
  git commit -m "docs: Remove outdated X documentation"
  ```
- Commit message must explain WHY files are deleted

**2. Pre-Commit Awareness**
- Check for deleted files before committing:
  ```bash
  git status                          # See deleted files
  ```
- If deletion is accidental: `git restore <filename>`

**3. CI Validation (Automatic)**
- GitHub Actions automatically validates:
  - All links in README.md resolve to files
  - Documentation files weren't deleted without explanation
  - Any deletion without "docs:" prefix in message fails CI

**4. Update README.md**
- After deleting docs, update all README.md references
- CI will fail if README references non-existent files

---

## 🔒 TOKEN SECURITY

**NEVER commit API keys, tokens, or credentials to version control.**

### **Secrets Management**

❌ **NEVER Do:**
- Commit API keys, tokens, or credentials
- Pass tokens as command-line arguments
- Hardcode tokens in code or configuration
- Log full tokens or include them in error messages

✅ **ALWAYS Do:**
- Use environment variables for all tokens (`GITHUB_TOKEN`, `PYPI_TOKEN`, etc.)
- Enable token expiry and rotation (30-90 days)
- Use read-only or project-scoped tokens when possible
- Scan commits for accidentally leaked secrets before pushing

See [docs/TOKEN_SECURITY.md](./docs/TOKEN_SECURITY.md) for complete token security guide.

---

## 📚 REFERENCE DOCUMENTATION

**For detailed information, see:**

- **[CLI_REFERENCE.md](./CLI_REFERENCE.md)** - Complete command documentation
- **[RELEASE_PROCESS.md](./RELEASE_PROCESS.md)** - Release workflow and troubleshooting
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design and agent categories
- **[CODING_RULES.md](./CODING_RULES.md)** - Development standards
- **[docs/TOKEN_SECURITY.md](./docs/TOKEN_SECURITY.md)** - Token security guide

---

## ✅ CHECKLIST FOR AI AGENTS

**Before starting ANY task:**

1. ✅ Run pre-flight checklist (format, lint, test)
2. ✅ Check `bd ready` for available work
3. ✅ Claim issue with `bd update <id> --status in_progress`

**During task:**

4. ✅ Use `bd create` for discovered work
5. ✅ **NEVER** create markdown planning files
6. ✅ **ALWAYS** use Beads for planning/analysis

**After task:**

7. ✅ Close issue with `bd close <id> --reason "..."`
8. ✅ Commit `.beads/issues.jsonl` with code changes
9. ✅ Push to origin: `git push origin main`
10. ✅ Verify with `.agents/verify-task-complete`

---

## 🚨 ZERO TOLERANCE VIOLATIONS

**These actions will cause immediate failure:**

❌ Creating `*_PLAN.md`, `*_ANALYSIS.md`, or any ad-hoc markdown files
❌ Leaving issues without status updates
❌ Forgetting to push `.beads/issues.jsonl` at session end
❌ Committing without running pre-flight checklist
❌ Manually tagging releases without `devloop release`
❌ Committing API keys, tokens, or credentials

**When in doubt: Ask before creating files, use Beads for tracking, run verification commands.**

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
