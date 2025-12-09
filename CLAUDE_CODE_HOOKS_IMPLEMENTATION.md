# Claude Code Hooks Implementation Guide

Detailed implementation plan for native Claude Code hooks to align with Git/Amp automation.

---

## Hook Scripts to Create

### 1. SessionStart Hook: Load Context on Startup

**File**: `.agents/hooks/claude-session-start`

```bash
#!/bin/bash
#
# SessionStart hook: Pre-load DevLoop findings when Claude Code starts
#
# This makes DevLoop findings available in Claude's context without
# requiring a manual /verify-work command.
#

set -e

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" || exit 0

# Try to load and display context
devloop amp_context 2>/dev/null || {
    # If devloop not available, just continue silently
    exit 0
}

exit 0
```

**What it does**:
- Runs when Claude Code starts a new session
- Loads the context index from `.devloop/context/index.json`
- Displays findings summary to Claude
- Non-blocking: failures don't prevent session start

**Output to Claude context**:
```json
{
  "check_now": {"count": 5, "severity_breakdown": {...}},
  "immediate": {"count": 2},
  "relevant": {"count": 3},
  "last_updated": "2025-12-09T10:30:00Z"
}
```

---

### 2. Stop Hook: Collect Findings on Completion

**File**: `.agents/hooks/claude-stop`

```bash
#!/bin/bash
#
# Stop hook: Collect DevLoop findings when Claude finishes responding
#
# This automatically runs verification after Claude's work, similar to
# Amp's post-task hook, but non-blocking to not interfere with user review.
#

set -e

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" || exit 0

# Check if devloop is available
if ! command -v devloop &>/dev/null; then
    exit 0
fi

# Check if this is a resumption from previous stop hook
# (prevent infinite loops)
input_json=$(cat)
stop_hook_active=$(echo "$input_json" | jq -r '.stop_hook_active // false')

if [ "$stop_hook_active" = "true" ]; then
    # Already running in a stop hook continuation, don't re-run
    exit 0
fi

# Collect findings silently
devloop amp_findings 2>/dev/null || true

exit 0
```

**What it does**:
- Runs when Claude Code finishes responding
- Collects and stores DevLoop findings for next session
- Non-blocking: doesn't interfere with Claude's output
- Prevents infinite loops with `stop_hook_active` check

**Hook Input** (via stdin):
```json
{
  "stop_hook_active": false,
  "transcript": [...]
}
```

**Output**: None to stdout (findings stored in `.devloop/context/`)

---

### 3. SubagentStop Hook: Extract Findings on Task Completion

**File**: `.agents/hooks/claude-subagent-stop`

```bash
#!/bin/bash
#
# SubagentStop hook: Create Beads issues when task completes
#
# This mirrors Amp's post-task hook behavior for Claude Code tasks.
# Automatically extracts DevLoop findings and creates Beads issues.
#

set -e

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" || exit 0

# Check if devloop and bd are available
if ! command -v devloop &>/dev/null || ! command -v bd &>/dev/null; then
    exit 0
fi

# Extract findings and create Beads issues
# Non-blocking - if this fails, don't interfere with task completion
devloop extract_findings_cmd 2>/dev/null || true

exit 0
```

**What it does**:
- Runs when a Claude Code task (subagent) completes
- Automatically creates Beads issues from DevLoop findings
- Similar to Amp's post-task findings extraction
- Non-blocking: failures don't affect task status

**Hook Input** (via stdin):
```json
{
  "subagent_tool_name": "Task",
  "subagent_args": {...},
  "subagent_status": "completed",
  "subagent_output": "..."
}
```

---

### 4. PreToolUse Hook: Protect Sensitive Files

**File**: `.agents/hooks/claude-file-protection`

```bash
#!/bin/bash
#
# PreToolUse hook: Block modifications to protected files
#
# Prevents accidental modifications to critical DevLoop and Git files
# that could corrupt state or break workflows.
#

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR" || exit 0

# Read hook input from stdin
input_json=$(cat)

# Extract tool and file paths
tool_name=$(echo "$input_json" | jq -r '.tool_name // ""')
tool_input=$(echo "$input_json" | jq -r '.tool_input // {}')

# Only process Write/Edit tools
if [[ "$tool_name" != "Write" && "$tool_name" != "Edit" ]]; then
    exit 0
fi

# Get the file path being modified
file_path=$(echo "$tool_input" | jq -r '.path // ""')

# Normalize path
if [ -n "$file_path" ]; then
    file_path=$(realpath "$file_path" 2>/dev/null || echo "$file_path")
fi

# Protected patterns
protected_patterns=(
    ".beads/"
    ".devloop/"
    ".git/"
    ".agents/"
    "AGENTS.md"
    "CODING_RULES.md"
    "AMP_ONBOARDING.md"
)

# Check if file matches protected pattern
is_protected=0
for pattern in "${protected_patterns[@]}"; do
    if [[ "$file_path" == *"$pattern"* ]]; then
        is_protected=1
        break
    fi
done

if [ $is_protected -eq 1 ]; then
    # Block the write and provide helpful message
    cat >&2 <<EOF
🚫 Protected file: $file_path

This file is protected by DevLoop to prevent accidental modifications to:
- Development workflow configuration (.agents/)
- Issue tracking state (.beads/)
- Repository metadata (.git/)
- Development guidelines (AGENTS.md, CODING_RULES.md)

If you need to modify this file:
1. Use manual editing via terminal: \`nano $file_path\`
2. Or ask the user to make the change manually
3. Or bypass protection with explicit user permission

Description of what you were trying to do will help!
EOF
    exit 2  # Exit code 2 = blocking error
fi

exit 0
```

**What it does**:
- Runs before Claude Code writes/edits files
- Blocks modifications to `.beads/`, `.devloop/`, `.git/`, etc.
- Provides helpful message suggesting alternatives
- Prevents data loss from accidental overwrites

**Hook Input** (via stdin):
```json
{
  "tool_name": "Write",
  "tool_input": {"path": "path/to/file", "content": "..."}
}
```

**Output**: stderr message explaining why file is protected (if blocking)

---

## Settings Configuration

### Installation Script

Create `.agents/hooks/install-claude-hooks` to help users register hooks:

```bash
#!/bin/bash
#
# Install Claude Code hooks to ~/.claude/settings.json
#
# This sets up automated verification, findings collection, and file protection
# when using Claude Code with DevLoop.
#

set -e

# Determine settings file location
SETTINGS_FILE="$HOME/.claude/settings.json"

# If no user settings exist, create from template
if [ ! -f "$SETTINGS_FILE" ]; then
    mkdir -p "$(dirname "$SETTINGS_FILE")"
    cat > "$SETTINGS_FILE" <<'EOF'
{
  "hooks": {}
}
EOF
    echo "Created $SETTINGS_FILE"
fi

# Get project directory
PROJECT_ROOT="${1:-.}"
PROJECT_ROOT=$(cd "$PROJECT_ROOT" && pwd)

# Create hooks section in settings
cat > /tmp/claude_hooks_update.json <<EOF
{
  "hooks": {
    "SessionStart": {
      "hooks": [
        {
          "type": "command",
          "matcher": "startup",
          "command": "$PROJECT_ROOT/.agents/hooks/claude-session-start",
          "timeout": 30
        }
      ]
    },
    "Stop": {
      "hooks": [
        {
          "type": "command",
          "command": "$PROJECT_ROOT/.agents/hooks/claude-stop",
          "timeout": 30
        }
      ]
    },
    "SubagentStop": {
      "hooks": [
        {
          "type": "command",
          "command": "$PROJECT_ROOT/.agents/hooks/claude-subagent-stop",
          "timeout": 30
        }
      ]
    },
    "PreToolUse": {
      "hooks": [
        {
          "type": "command",
          "matcher": "Write|Edit",
          "command": "$PROJECT_ROOT/.agents/hooks/claude-file-protection",
          "timeout": 10
        }
      ]
    }
  }
}
EOF

# Merge with existing settings
python3 << 'PYTHON_EOF'
import json
import sys

settings_file = "$SETTINGS_FILE"
hooks_update = /tmp/claude_hooks_update.json

try:
    with open(settings_file, 'r') as f:
        settings = json.load(f)
except:
    settings = {}

with open(hooks_update, 'r') as f:
    updates = json.load(f)

# Deep merge hooks
if 'hooks' not in settings:
    settings['hooks'] = {}

for event, hooks_config in updates['hooks'].items():
    if event not in settings['hooks']:
        settings['hooks'][event] = hooks_config
    else:
        # If event exists, append new hooks
        if 'hooks' not in settings['hooks'][event]:
            settings['hooks'][event]['hooks'] = []
        settings['hooks'][event]['hooks'].extend(hooks_config['hooks'])

# Write back
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print(f"Updated {settings_file}")
PYTHON_EOF

echo "✓ Claude Code hooks installed"
echo ""
echo "Hooks registered:"
echo "  • SessionStart - Pre-load findings on startup"
echo "  • Stop - Collect findings on completion"
echo "  • SubagentStop - Extract findings on task completion"
echo "  • PreToolUse - Protect sensitive files"
echo ""
echo "View hooks: /hooks in Claude Code"
```

---

## Integration with devloop init

### Update Main Init Flow

Modify `src/devloop/cli/main.py` init command to register Claude hooks:

```python
def init(path: Path = typer.Argument(Path.cwd())):
    """Initialize DevLoop in project"""
    # ... existing init code ...
    
    # Step: Create Claude hook scripts
    agents_dir = path / ".agents" / "hooks"
    agents_dir.mkdir(parents=True, exist_ok=True)
    
    hook_scripts = {
        "claude-session-start": create_session_start_script(),
        "claude-stop": create_stop_script(),
        "claude-subagent-stop": create_subagent_stop_script(),
        "claude-file-protection": create_file_protection_script(),
        "install-claude-hooks": create_install_script(),
    }
    
    for script_name, script_content in hook_scripts.items():
        script_path = agents_dir / script_name
        with open(script_path, "w") as f:
            f.write(script_content)
        script_path.chmod(0o755)
        console.print(f"[green]✓[/green] Created {script_name}")
    
    # Step: Offer to install hooks
    if typer.confirm("Install Claude Code hooks to ~/.claude/settings.json?", default=True):
        result = subprocess.run(
            [str(agents_dir / "install-claude-hooks"), str(path)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            console.print(f"[green]✓[/green] Claude Code hooks installed")
        else:
            console.print(f"[yellow]⚠[/yellow] Could not auto-install hooks")
            console.print(f"To install manually, run:")
            console.print(f"  {agents_dir / 'install-claude-hooks'} {path}")
```

---

## Hook Registration Manual (for Users)

If automated installation doesn't work, users can register hooks manually:

**Step 1**: Run `/hooks` in Claude Code
**Step 2**: Select `+ Add Event`
**Step 3**: Choose `SessionStart`, then `+ Add Matcher` → `startup`
**Step 4**: Add hook command:
```
$CLAUDE_PROJECT_DIR/.agents/hooks/claude-session-start
```

**Repeat** for Stop, SubagentStop, PreToolUse events.

---

## Testing Hook Implementation

### Manual Testing

```bash
# 1. Create a test hook that echoes input
cat > ~/.claude/test_hook.sh <<'EOF'
#!/bin/bash
echo "Test hook executed" >&2
cat  # Echo stdin
exit 0
EOF
chmod +x ~/.claude/test_hook.sh

# 2. Register in .claude/settings.json
# (via /hooks menu in Claude Code)

# 3. Trigger the event (start Claude Code)
# Check output in verbose mode (Ctrl+O)
```

### Unit Testing

```python
# tests/test_claude_hooks.py
def test_session_start_hook_loads_findings():
    """SessionStart hook should load DevLoop findings"""
    # Setup: Create mock findings
    # Run: session-start hook
    # Verify: findings loaded to stdout
    
def test_stop_hook_collects_findings():
    """Stop hook should collect findings non-blocking"""
    # Setup: Create mock hook input
    # Run: stop hook
    # Verify: findings stored, exit code 0
    
def test_file_protection_blocks_protected_files():
    """File protection should block protected file writes"""
    # Setup: Create PreToolUse input for .beads/file.json write
    # Run: file-protection hook
    # Verify: Exit code 2, error message in stderr
```

---

## Rollout Plan

### Phase 1: Create Hook Scripts (Low Risk)

- Create `.agents/hooks/claude-*` scripts
- Add to git (can be ignored by users)
- Test locally with Claude Code

### Phase 2: Update Init Command

- Add hook script creation to `devloop init`
- Add optional hook installation prompt
- Test on clean install

### Phase 3: Documentation

- Update `AMP_ONBOARDING.md` with Claude hooks section
- Create `.agents/hooks/README.md` explaining each hook
- Add troubleshooting guide

### Phase 4: Feedback & Iteration

- Gather user feedback on hook behavior
- Adjust timeouts/behavior as needed
- Document edge cases

---

## Timeout Recommendations

| Hook | Timeout | Reason |
|------|---------|--------|
| SessionStart | 30s | Should be fast, user waiting |
| Stop | 30s | Non-blocking, but not forever |
| SubagentStop | 30s | Part of task completion |
| PreToolUse | 10s | Blocks writes, keep snappy |

---

## Environment Variables

All hooks have access to:

- `CLAUDE_PROJECT_DIR` - Project root (where Claude Code was started)
- `CLAUDE_CODE_REMOTE` - "true" if running in web environment
- `PATH` - Standard shell PATH with devloop, bd, etc.

---

## Error Handling

### Hook Failures

**Exit code 0**: Success, stdout shown in verbose mode
- SessionStart/UserPromptSubmit: stdout added to context
- Other events: logged only

**Exit code 2**: Blocking error, stderr shown to Claude
- PreToolUse: Blocks tool call, shows error
- PermissionRequest: Denies permission
- Stop/SubagentStop: Shows error to Claude

**Other codes**: Non-blocking error, stderr shown in verbose mode

### Safe Defaults

All hooks should:
- Fail gracefully if DevLoop not installed
- Fail gracefully if dependencies missing
- Never prevent Claude Code from working
- Log errors to stderr (visible in verbose mode)

---

## Security Notes

### Hooks Execute Automatically

Hooks run with full user permissions. The file-protection hook provides:
- ✅ Blocking dangerous file writes
- ✅ Preventing accidental DevLoop state corruption
- ✅ Clear error messages with alternatives

### Sensitive Files Protected

`.beads/` - Issue tracking state (don't overwrite)
`.devloop/` - Agent findings and context (don't overwrite)
`.git/` - Repository metadata (don't overwrite)
`.agents/` - Hook scripts and verification logic (don't modify)

---

## Documentation Updates

### Add to AMP_ONBOARDING.md

```markdown
## Claude Code Hooks

Claude Code supports native hook events for automatic verification:

- **SessionStart** - Load findings when Claude Code starts
- **Stop** - Collect findings when Claude finishes
- **SubagentStop** - Extract findings when task completes
- **PreToolUse** - Protect sensitive DevLoop files

Hooks are installed automatically during `devloop init`.
```

### Create .agents/hooks/README.md

```markdown
# Claude Code Integration Hooks

These scripts run automatically when Claude Code performs actions:

- `claude-session-start` - Load findings on startup
- `claude-stop` - Collect findings on completion
- `claude-subagent-stop` - Extract findings on task end
- `claude-file-protection` - Block protected file writes
- `install-claude-hooks` - Register hooks in ~/.claude/settings.json

See AMP_ONBOARDING.md for setup and troubleshooting.
```

---

## Summary

This implementation provides:

✅ Automatic findings loading (SessionStart)
✅ Automatic findings collection (Stop)
✅ Automatic findings extraction (SubagentStop)
✅ File protection to prevent data loss (PreToolUse)
✅ Non-blocking (failures don't break Claude Code)
✅ Consistent with Git/Amp patterns
✅ User-friendly error messages
