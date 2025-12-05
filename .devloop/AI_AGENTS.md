# AI Agent Integration
**Background agent integration instructions for all coding agents (Claude, Amp, etc.)**

This project uses background agents that enhance all AI coding agents' capabilities through automated code quality checks and context provision.

## 🤖 Proactive Agent Status Checking

**IMPORTANT**: All AI agents should proactively check background agent findings and surface them to users:

1. **After Edit/Write operations**: Check `.devloop/AGENT_STATUS.md` for immediate issues
2. **When starting tasks**: Check for existing findings that might be relevant
3. **Before commits**: Always surface any blocking issues

### How to Check
- Read `.devloop/AGENT_STATUS.md` - auto-updated summary of findings
- If immediate issues exist (⚠️ status), surface them to the user with:
  - File names and line numbers
  - Issue severity and count
  - Suggestion to address before proceeding
- For detailed analysis, run: `python3 .devloop/integration/claude-code-adapter.py insights --format text`

### When to Surface
- **Always surface** if 🔴 errors exist in files user just edited
- **Mention** if ⚠️ warnings accumulate (>5)
- **Silent** if ✅ all clear

## Background Agent System

- **Linter Agent**: Runs linting on file changes
- **Formatter Agent**: Applies code formatting
- **Test Runner Agent**: Executes relevant tests
- **Security Scanner**: Checks for vulnerabilities

## AI Agent Integration

### Hooks Configuration (Claude Code)

Add these hooks to your Claude Code settings for automatic integration:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .devloop/integration/claude-code-adapter.py check_results"
          }
        ]
      }
    ]
  }
}
```

### Skills Integration

Use these prompts with Claude Code for background agent integration:

- "Check background agent results for issues in the files I just modified"
- "What do the background linters say about my recent changes?"
- "Summarize the test results from background agents"
- "Are there any security findings from background agents I should address?"

### Context Access

Background agents write results to: `.devloop/context/agent-results.json`

Claude Code can read this file to access current status and findings.

### Communication Style
**IMPORTANT**: Be much less verbose in work summaries. Keep responses concise and to the point. Focus on what was accomplished and next steps only.

### Coding Rules Integration
**MANDATORY**: When using devloop, automatically follow the coding rules in `CODING_RULES.md`. Learn from every failure pattern and update your coding approach:

- **Pattern Recognition**: Identify recurring issues (tool availability, configuration errors, path handling, async patterns)
- **Rule Application**: Apply the 10 core patterns from CODING_RULES.md to all code you generate
- **Failure Learning**: When encountering issues, reference CODING_RULES.md patterns and update your approach
- **Prevention**: Use the documented patterns to prevent known failure modes
- **Evolution**: Suggest improvements to CODING_RULES.md when discovering new patterns

**Key Rules to Always Follow:**
1. Check tool availability before execution with helpful error messages
2. Use dataclass configuration with `__post_init__` validation
3. Implement comprehensive async error handling
4. Use Path objects with security validation
5. Standardize results with AgentResult format
6. Apply safe imports for optional dependencies
7. Implement proper resource lifecycle management
8. Use structured logging consistently

**Test Setup Requirements**
**MANDATORY**: When initializing projects with devloop, ensure proper test framework setup:

- **Auto-detect test frameworks** in the project (pytest, unittest, jest, etc.)
- **Create basic test structure** if none exists (tests/ directory, basic test files)
- **Configure test runners** appropriately for detected frameworks
- **Add test dependencies** to project configuration
- **Create example tests** to demonstrate functionality
- **Setup CI/CD integration** for automated testing

### Best Practices

- Use Claude Code's hooks to automatically check background agent results after file operations
- Leverage Claude Code's skills to analyze background agent findings
- Check context files when debugging or before commits
- Use background agent results to inform Claude Code's suggestions

## DevLoop Agent Status Verification

**CRITICAL**: Before starting any coding work, verify that `devloop watch` is running.

### Quick Check
```bash
./.agents/check-devloop-status
```

This will:
- ✅ Show the running devloop process if active
- ❌ Provide startup instructions if not running

### Why This Matters

- DevLoop agents provide real-time code quality feedback
- Missing issues won't be caught until commit time
- Faster feedback loop accelerates development
- Tests run in background automatically

### Starting DevLoop

```bash
# Recommended: Run in background with nohup
nohup devloop watch . > .devloop/devloop.log 2>&1 &

# Or directly:
devloop watch .
```

### If DevLoop Stops

Check the log for errors:
```bash
tail -50 .devloop/devloop.log
```

Common causes:
- Database lock (clean up with `rm -f .beads/daemon.lock`)
- Permission issues in `.devloop/`
- Virtual environment not activated

---

## Beads Daemon Management

**CRITICAL**: When stopping the Beads daemon, always use graceful shutdown to avoid data loss:

**✅ CORRECT - Graceful shutdown:**
```bash
bd daemon stop    # Cleanly shuts down daemon
```

**❌ WRONG - Hard kill (risk of data loss):**
```bash
pkill -9 -f beads  # Can leave lock files and WAL files
```

**Why this matters:**
- Hard killing leaves `.beads/daemon.lock` and `.beads/beads.db-wal` files
- If Beads was mid-write when killed, uncommitted transactions may be lost
- Future writes could fail or corrupt the issue database
- Devloop and Beads competing for database access causes lock contention

**Recovery if hard kill occurred:**
```bash
rm -f .beads/daemon.lock  # Clean up orphaned lock
bd status                 # Verify database integrity
```

Always use `bd daemon stop` for clean shutdowns.
