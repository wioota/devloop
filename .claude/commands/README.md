# Claude Code Slash Commands

This directory contains custom slash commands for Claude Code that integrate with the devloop system.

## Available Commands

### `/devloop-status`

Check if devloop watch is running and show current status.

**Usage:**
```
/devloop-status
```

**Output:**
- Running status (✅ or ❌)
- Process ID and memory usage
- Instructions to start if not running

---

### `/agent-summary`

Generate an intelligent summary of recent dev-agent findings with operational health metrics.

**Usage:**
```
/agent-summary
```

**Output:**
- System health status
- Recent agent activity
- Agent performance metrics
- Findings breakdown by urgency
- Actionable insights and recommendations

---

### `/verify-work`

Run code quality verification and extract findings (equivalent to Amp's post-task enforcement).

**Usage:**
```
/verify-work
```

**What it does:**
1. Runs unified code quality verification:
   - Black formatting check
   - Ruff linting
   - mypy type checking
   - pytest test suite
2. Extracts DevLoop findings and creates Beads issues
3. Shows blocking issues and warnings
4. Lists created Beads issue IDs

**Output:**
- ✅ All checks passed or ❌ issues found
- List of blocking issues (must fix)
- List of warnings (non-blocking)
- Number of Beads issues created

**Similar to:** Amp's post-task hook for consistent enforcement across Claude Code and Amp

---

### `/extract-findings`

Extract DevLoop findings and automatically create Beads issues for tracking.

**Usage:**
```
/extract-findings
```

**What it does:**
1. Scans recent findings (last 24 hours) from `.devloop/context/`
2. Categorizes by type (formatter, linter, performance, security)
3. Creates Beads issues with appropriate priorities:
   - Formatter violations (P1) - can break CI
   - Linter errors (P1) - need fixing
   - Performance issues (P2) - nice to have
   - Security findings (P0-P1) - urgent
4. Links issues to current work automatically

**After running:**
Use `bd ready` to see newly created actionable issues.

---

### `/devloop-findings` (Deprecated)

Use `/extract-findings` instead - same functionality with better naming.

---

## How Slash Commands Work

Claude Code slash commands are markdown files that define prompts. When you type `/command-name`, Claude Code expands the prompt from the corresponding markdown file and executes it.

## Requirements

- Devloop must be installed and watch running
- Python virtual environment activated
- Context data available in `.devloop/context/`
- Beads (`bd`) installed for `/devloop-findings` command
