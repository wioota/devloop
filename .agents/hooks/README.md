# Claude Code Integration Hooks

These scripts run automatically when Claude Code performs actions, providing automated verification, findings collection, and file protection.

## Hook Scripts

### 1. `claude-session-start`

**When**: Runs when Claude Code starts or resumes a session

**What it does**:
- Pre-loads DevLoop findings into Claude's context
- Makes quality issues visible immediately without manual commands
- Non-blocking: failures don't prevent session start

**Command**:
```bash
devloop amp_context
```

**Output**: JSON with findings summary

---

### 2. `claude-stop`

**When**: Runs when Claude Code finishes responding

**What it does**:
- Automatically collects DevLoop findings after Claude's work
- Stores findings for next session or manual review
- Similar to Amp's post-task hook but non-blocking
- Prevents infinite loops with `stop_hook_active` check

**Command**:
```bash
devloop amp_findings
```

**Output**: Findings stored to disk (no stdout)

---

### 3. `claude-file-protection`

**When**: Runs before Claude Code writes/edits files (PreToolUse hook)

**What it does**:
- Blocks modifications to protected files
- Prevents accidental overwrites of critical state
- Provides helpful error messages with alternatives

**Protected files**:
- `.beads/` — Issue tracking state
- `.devloop/` — Agent findings and context
- `.git/` — Repository metadata
- `.agents/hooks/` — Verification scripts
- `.claude/` — Claude Code configuration
- `AGENTS.md`, `CODING_RULES.md`, `AMP_ONBOARDING.md` — Documentation

**Exit codes**:
- `0` — File is safe to write
- `2` — File is protected, write blocked

**Example error**:
```
🚫 Protected file: .beads/issues.jsonl

This file is protected by DevLoop to prevent accidental modifications to:
- Development workflow configuration (.agents/)
- Issue tracking state (.beads/)
- Repository metadata (.git/, .claude/)
- Development guidelines (AGENTS.md, CODING_RULES.md)

If you need to modify this file:
1. Use manual editing via terminal: nano ".beads/issues.jsonl"
2. Or ask the user to make the change manually
3. Or describe what you're trying to do so the user can help
```

---

## Installation

### Automatic (During `devloop init`)

```bash
devloop init
# Prompts: "Install Claude Code hooks to ~/.claude/settings.json?"
```

Hooks are automatically created and registered.

### Manual Installation

1. **Copy hooks to project**:
   ```bash
   cp .agents/hooks/claude-* ~/.claude/project-hooks/
   ```

2. **Register in Claude Code**:
   - Open Claude Code
   - Type `/hooks` to open hooks menu
   - Select `+ Add Event` for each hook:
     - **SessionStart** → command → `.agents/hooks/claude-session-start`
     - **Stop** → command → `.agents/hooks/claude-stop`
     - **PreToolUse** → matcher: `Write|Edit` → `.agents/hooks/claude-file-protection`

---

## Testing Hooks Manually

### Test SessionStart

```bash
# Simulate what Claude Code does
PROJECT_DIR=. .agents/hooks/claude-session-start
```

Should show JSON context output or exit silently if devloop not found.

### Test Stop Hook

```bash
# Create test input
echo '{"stop_hook_active": false}' | .agents/hooks/claude-stop
```

Should collect findings silently (exit code 0).

### Test File Protection

```bash
# Try to write to protected file
echo '{"tool_name": "Write", "tool_input": {"path": ".beads/issues.jsonl"}}' | \
  .agents/hooks/claude-file-protection
```

Should fail with exit code 2 and show error message.

---

## Hook Environment

All hooks have access to:

- `CLAUDE_PROJECT_DIR` — Project root (where Claude Code was started)
- `CLAUDE_CODE_REMOTE` — "true" if running in web environment (hooks won't work)
- `PATH` — Standard shell PATH with devloop, bd, jq, etc.

---

## Troubleshooting

### Hooks Not Running

**Check registration**:
```bash
cat ~/.claude/settings.json | jq '.hooks'
```

Should show all three hook configurations.

### SessionStart Hook Fails

**Common issue**: DevLoop not installed or not in PATH

**Fix**:
```bash
which devloop  # Check if installed
pip install -e .  # Install from project root
```

### Stop Hook Not Collecting Findings

**Check logs**:
```bash
# View DevLoop logs
tail -f .devloop/devloop.log
```

**Verify devloop is running**:
```bash
ps aux | grep devloop
```

### File Protection Too Strict

**Can't edit a legitimate file?**

1. Ask the user to edit it manually:
   ```bash
   nano path/to/file
   ```

2. Or describe what needs to be changed so user can help

3. File protection can be adjusted by editing `.agents/hooks/claude-file-protection`

---

## Architecture

### Hook Event Flow

```
Claude Code Start
    ↓
SessionStart Hook
    ↓
devloop amp_context (load findings)
    ↓
Claude's context includes findings summary
    ↓
User works with Claude
    ↓
Claude finishes responding
    ↓
Stop Hook
    ↓
devloop amp_findings (collect findings)
    ↓
Findings stored for next session
    
User tries to write a file
    ↓
PreToolUse Hook
    ↓
Check if file is protected
    ↓
If protected: block and show error
If safe: allow write
```

### Non-Blocking Design

All hooks are **non-blocking**:
- SessionStart: Loads context, doesn't prevent session start if it fails
- Stop: Collects findings, doesn't interfere with Claude's response
- PreToolUse: Only blocks writes to protected files (has useful error messages)

This ensures Claude Code continues working even if hooks fail.

---

## Maintenance

### Update Hooks

To update hooks to latest version:

```bash
devloop update-hooks
# Or manually: devloop init --skip-config
```

### Disable Hooks

In Claude Code settings (`/hooks`):
- Uncheck individual hooks to disable them
- Or remove from `.claude/settings.json`

Note: CLI commands (`/verify-work`, `devloop verify-work`) still work without hooks.

### View Hook Logs

```bash
# Check if jq is installed (needed for JSON parsing)
which jq

# View recent Claude Code errors
tail -f ~/.claude/logs/  # (if available)
```

---

## Performance

- **SessionStart**: < 1 second (fast query)
- **Stop**: < 2 seconds (finds collection, non-blocking)
- **PreToolUse**: < 500ms (fast check)

If hooks are slow, check:
1. DevLoop daemon is running: `ps aux | grep devloop`
2. System resources: `top` or `free -h`
3. Network access (for remote projects)

---

## Security Notes

- Hooks run with your user permissions
- File protection doesn't prevent shell edits (`nano`, `vim`, etc.)
- Protection is advisory, not cryptographic
- Always commit changes appropriately

---

## References

- **DevLoop Documentation**: `AGENTS.md` and `CLAUDE.md`
- **Hook Installation**: `AMP_ONBOARDING.md`
- **Coding Rules**: `CODING_RULES.md`
- **Claude Code Docs**: https://code.claude.com/docs/en/hooks

---

## Questions?

See the comprehensive hook planning documents:
1. `CLAUDE_CODE_HOOKS_REVIEW.md` — Gap analysis and architecture
2. `CLAUDE_CODE_HOOKS_IMPLEMENTATION.md` — Technical details
3. `.amp/CLAUDE_CODE_HOOKS_CHECKLIST.md` — Implementation checklist

