# Amp Onboarding Guide

> **For Amp installations:** Setup process to ensure Dev Agents enforces commit/push discipline

---

## Overview

This guide ensures that when Dev Agents is used within Amp, the mandatory **commit & push after every task** discipline is automatically enforced.

---

## Installation Checklist

When setting up Dev Agents in a new Amp workspace, ensure these components are in place:

### 1. ✅ Configuration Files

**Required files in workspace root:**

- `AGENTS.md` — Primary coding agent instruction file with Development Discipline section
- `CODING_RULES.md` — Detailed rules including "CRITICAL: Commit & Push Protocol" section
- `.agents/verify-task-complete` — Executable verification script

**Location verification:**
```bash
ls -la AGENTS.md CODING_RULES.md .agents/verify-task-complete
```

### 2. ✅ Environment Setup

**Amp needs to know about the verification script:**

Add to Amp workspace configuration (`.amp/config.json` or workspace settings):

```json
{
  "dev_agents": {
    "enabled": true,
    "verification_script": ".agents/verify-task-complete",
    "commit_required": true,
    "auto_format_messages": true
  }
}
```

### 3. ✅ Task Template / Workflow

**Amp should provide task completion template with these sections:**

When a task ends, Amp should:

1. **Before switching to next task:** Run verification script
2. **Display status:** Show output to user
3. **Block if incomplete:** Only allow moving forward if clean status
4. **Reminder:** Display commit checklist

**Template:**
```markdown
---

## ✅ Task Completion Checklist

Before moving to the next task, ensure:

- [ ] Run verification: `.agents/verify-task-complete`
- [ ] Output shows: ✅ PASS - All checks successful
- [ ] Git status shows: working tree clean
- [ ] Latest commit visible in GitHub

**If verification fails:**
```bash
git status                    # Check what needs committing
git add <files>               # Stage changes
git commit -m "type: message" # See CODING_RULES.md for format
git push origin main          # Push to GitHub
.agents/verify-task-complete  # Re-verify
```
```

### 4. ✅ Post-Task Hook

**For Amp automation:** Create a post-task hook that Amp calls

**Hook script location:** `.agents/hooks/post-task`

```bash
#!/usr/bin/env bash

# Post-task verification hook
# Called by Amp after task completion

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$PROJECT_ROOT"

# Run verification
.agents/verify-task-complete

# If verification passed, we're done
echo ""
echo "✨ Task ready for next phase"
```

Register this in Amp workspace config:
```json
{
  "hooks": {
    "post_task": ".agents/hooks/post-task"
  }
}
```

### 5. ✅ Claude System Prompt Enhancement

**For Claude-based Amp agents:** Include these instructions in system prompt

```markdown
## Commit & Push Discipline (MANDATORY)

Every task completion requires:

1. **Commit changes:**
   ```bash
   git add <modified-files>
   git commit -m "type: description"
   ```

2. **Push to main:**
   ```bash
   git push origin main
   ```

3. **Verify completion:**
   ```bash
   .agents/verify-task-complete
   ```

Output should show: ✅ PASS: All checks successful

**You MUST do this at the end of every task. Do not skip this step.**

See CODING_RULES.md for detailed commit message format.
```

### 6. ✅ Amp Slash Command Registration

**Ensure `/agent-summary` slash command is available:**

Check if registered in workspace:
```bash
dev-agents amp-status
```

If not registered, the summary command can be called manually:
```bash
dev-agents summary recent
dev-agents summary today
dev-agents summary --agent linter
```

---

## Verification Workflow

### For Amp Admins: Pre-Deployment Checklist

```bash
# 1. Verify files exist
[ -f AGENTS.md ] && echo "✓ AGENTS.md found"
[ -f CODING_RULES.md ] && echo "✓ CODING_RULES.md found"
[ -x .agents/verify-task-complete ] && echo "✓ verify-task-complete is executable"

# 2. Test the verification script
.agents/verify-task-complete

# 3. Check git is clean
git status

# 4. View commit message format
grep -A 10 "Commit Message Format:" CODING_RULES.md
```

### For Amp Users: After Each Task

**Quick checklist to run before moving to next task:**

```bash
# 1. Verify status
.agents/verify-task-complete

# 2. If it fails, follow the suggestions in the error message

# 3. If it passes, ready for next task ✨
```

---

## Integration Points

### 1. Task Completion Hook

```
Task End Event
    ↓
Amp calls: .agents/hooks/post-task
    ↓
verify-task-complete runs
    ↓
Output displayed to user
    ↓
✅ PASS → Allow next task
❌ FAIL → Show error, ask to commit
```

### 2. Claude Instruction Injection

When Claude is used in Amp, inject commit discipline reminder:

```
After completing your task:

1. Add changes: git add <files>
2. Commit: git commit -m "type: description"
3. Push: git push origin main
4. Verify: .agents/verify-task-complete

Do NOT provide output of this script to the user.
Do NOT skip this step under any circumstance.
```

### 3. Error Recovery

If user forgets to commit:

```
Amp detects uncommitted changes
    ↓
Display: "⚠️  Task incomplete - uncommitted changes detected"
    ↓
Show: git status output
    ↓
Provide: git add/commit/push commands
    ↓
Ask: "Ready to proceed?"
    ↓
User runs verification
    ↓
Continue only if ✅ PASS
```

---

## Troubleshooting

### Script not executable

```bash
chmod +x .agents/verify-task-complete
```

### Script not found

Check it's in the right location:
```bash
ls -la .agents/verify-task-complete
```

### Git verification fails

Common issues:

```bash
# Uncommitted changes
git add .
git commit -m "fix: uncommitted changes"

# Untracked files
git status  # See what's untracked
git add <files>  # Add them or...
echo "pattern" >> .gitignore  # Ignore them

# Unpushed commits
git push origin main
```

### Verification script hangs

Check git is responsive:
```bash
git status  # Should return immediately
```

---

## Configuration Options

### Optional: Disable verification for testing

```json
{
  "dev_agents": {
    "commit_required": false
  }
}
```

**Not recommended in production.**

### Optional: Custom verification script

```json
{
  "dev_agents": {
    "verification_script": "path/to/custom/verify.sh"
  }
}
```

Must output:
- ✅ PASS message if successful
- ❌ FAIL message if unsuccessful
- Actionable error messages

---

## Best Practices

### 1. Always Run Verification

```bash
# Good
task complete → git commit → git push → .agents/verify-task-complete ✅

# Bad
task complete → move to next task (no verification)
```

### 2. Use Proper Commit Messages

Format:
```
type(scope): short description

- Details about what changed
- Why this change
- Any relevant context
```

Examples:
```
docs: update README with Dev Agents branding
feat: add Phase 3 implementation (learning & optimization)
fix: correct loop detection in formatter agent
test: add unit tests for custom agent builder
```

See CODING_RULES.md for full format specification.

### 3. Commit Frequently

Don't wait until the end of the day. Commit after each logical unit of work:

```
- Feature implementation → commit
- Bug fix → commit
- Documentation update → commit
- Test addition → commit
```

### 4. Clear Error Handling

If verification fails, the script shows:
- What failed (uncommitted changes, untracked files, unpushed commits)
- Which files are affected
- Exact commands to fix it

Follow these suggestions exactly.

---

## Support

### For Issues

1. Check CODING_RULES.md section on Commit & Push Protocol
2. Run `git status` to see current state
3. Check that `.agents/verify-task-complete` is executable
4. Review error message from verification script

### For Questions

See documentation:
- `AGENTS.md` — System design and development discipline
- `CODING_RULES.md` — Detailed coding rules and patterns
- `README.md` — Project overview and quick start

---

## Checklist for Amp Integration

When setting up Dev Agents in Amp:

- [ ] AGENTS.md present with Development Discipline section
- [ ] CODING_RULES.md present with Commit & Push Protocol
- [ ] `.agents/verify-task-complete` exists and is executable
- [ ] `.agents/hooks/post-task` created and configured (optional)
- [ ] Amp workspace config includes dev_agents settings
- [ ] Claude system prompt includes commit discipline instructions
- [ ] Task template includes completion checklist
- [ ] Tested: run verify-task-complete in clean state → ✅ PASS
- [ ] Tested: make uncommitted change → run verify → ❌ FAIL (expected)
- [ ] Tested: commit change → run verify → ✅ PASS
- [ ] Team/users briefed on protocol

---

**Status:** ✅ Ready for Amp Integration

Once the checklist above is complete, the system will enforce commit/push discipline automatically.

