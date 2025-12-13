# Claude Code Hooks Troubleshooting Guide

This guide helps diagnose and fix issues with the Claude Code integration hooks.

---

## Common Issues & Solutions

### Issue: "🚫 Protected file" Error in Claude Code

**Symptom**: Claude Code shows error message like:
```
🚫 Protected file: .beads/issues.jsonl

This file is protected by DevLoop...
```

**Cause**: Claude is trying to write to a protected file

**Solutions** (in order of preference):

#### 1. Ask the user to edit manually
```bash
nano .beads/issues.jsonl
```

#### 2. Describe what needs to change
Instead of making the change yourself, ask the user:
> "The .beads/issues.jsonl file needs this change: ..."
> "Can you update the file like this?"

#### 3. Whitelist the file (if you need to edit it repeatedly)

Create `.claude/file-protection-whitelist.json`:
```json
{
  "allowed_patterns": [
    ".beads/issues.jsonl"
  ]
}
```

Then restart Claude Code for changes to take effect.

---

### Issue: Hook Running Unnecessarily

**Symptom**: Hook blocks a file I should be able to edit

**Cause**: Protection is too broad (substring matching)

**Example**: 
- File `.beads/custom-data.json` matches pattern `.beads/`
- This is intentional (protects whole directory)

**Solution**: Use whitelist for specific files within protected directories

```json
{
  "allowed_patterns": [
    ".beads/custom-data.json",
    ".beads/reports/analysis.json"
  ]
}
```

---

### Issue: Whitelist Not Working

**Symptom**: File is in whitelist, but still blocked

**Possible causes**:

#### 1. Claude Code not restarted
Restart Claude Code for whitelist changes to take effect.

#### 2. Invalid JSON in whitelist file
```bash
# Check JSON syntax
python3 -m json.tool .claude/file-protection-whitelist.json
```

#### 3. Pattern doesn't match the file path
The hook uses exact substring matching on file paths.

**Debug**:
```bash
# Test what the hook sees
echo '{"tool_name":"Write","tool_input":{"path":".beads/custom.json"}}' | \
  .agents/hooks/claude-file-protection
```

If it's blocked, the pattern isn't matching. Check:
- Case sensitivity: `AGENTS.md` ≠ `agents.md`
- Full path vs relative: `.agents/` vs `./agents/`
- Escaped characters: spaces, quotes, etc.

---

### Issue: Hook Not Running

**Symptom**: Trying to write to protected file, but no error appears

**Cause**: Hook not registered in Claude Code

**Debug**:
```bash
# Check if hooks are registered
cat ~/.claude/settings.json | jq '.hooks'
```

**Solution**:

#### Option 1: Reinstall hooks
```bash
devloop init
# When prompted, choose "Y" to install hooks
```

#### Option 2: Register manually
1. Open Claude Code
2. Type `/hooks`
3. Select `+ Add Event`
4. Add these hooks:
   - **PreToolUse** → matcher: `Write|Edit` → command: `.agents/hooks/claude-file-protection`

---

### Issue: Permission Denied

**Symptom**: Error about permissions when trying to access whitelist

**Cause**: `.claude/` directory or whitelist file has wrong permissions

**Fix**:
```bash
# Ensure .claude directory exists and is readable
mkdir -p .claude
chmod 755 .claude

# Ensure whitelist is readable
chmod 644 .claude/file-protection-whitelist.json
```

---

### Issue: Hook Uses Wrong Project Directory

**Symptom**: Hook is protecting files from a different project

**Cause**: `CLAUDE_PROJECT_DIR` environment variable pointing to wrong location

**Debug**:
```bash
# Check what directory hook is using
CLAUDE_PROJECT_DIR=/path/to/project .agents/hooks/claude-file-protection
```

**Fix**: In Claude Code, make sure you're working in the correct project directory.

---

## Advanced Debugging

### Test Hook Directly

#### Test file protection with protected file
```bash
echo '{"tool_name":"Write","tool_input":{"path":"AGENTS.md"}}' | \
  .agents/hooks/claude-file-protection

# Should exit with code 2
echo $?  # Output: 2
```

#### Test file protection with safe file
```bash
echo '{"tool_name":"Write","tool_input":{"path":"src/test.py"}}' | \
  .agents/hooks/claude-file-protection

# Should exit with code 0
echo $?  # Output: 0
```

#### Test with whitelist
```bash
# Create whitelist
echo '{"allowed_patterns":["AGENTS.md"]}' > .claude/file-protection-whitelist.json

# Now AGENTS.md should be allowed
echo '{"tool_name":"Write","tool_input":{"path":"AGENTS.md"}}' | \
  .agents/hooks/claude-file-protection

echo $?  # Output: 0

# Clean up
rm .claude/file-protection-whitelist.json
```

#### Test path resolution
```bash
# Relative path
echo '{"tool_name":"Write","tool_input":{"path":"./AGENTS.md"}}' | \
  .agents/hooks/claude-file-protection
# Should still be blocked (normalized to absolute path)

# Symlink
ln -s .beads/issues.jsonl /tmp/test-link
echo '{"tool_name":"Write","tool_input":{"path":"/tmp/test-link"}}' | \
  .agents/hooks/claude-file-protection
# Should be blocked (symlink resolved to protected file)
rm /tmp/test-link
```

---

## Hook Exit Codes

Understanding exit codes helps debug issues:

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success - file can be written | Claude Code continues |
| 2 | Blocked - file is protected | Claude Code shows error and stops |
| 1+ | Error in hook script | Hook fails gracefully, Claude Code continues |

---

## Performance Troubleshooting

If hooks are slow:

### Check hook execution time
```bash
# Time the hook
time (echo '{"tool_name":"Write","tool_input":{"path":"test.py"}}' | \
  .agents/hooks/claude-file-protection)

# Should be < 500ms
```

### Common slow issues:

1. **Large whitelist file**
   - Keep whitelist patterns minimal
   - Patterns are checked sequentially

2. **Network filesystem**
   - Hook reads whitelist from disk
   - Network delays can add latency
   - Consider moving `.claude/` to local SSD

3. **Python startup overhead**
   - Hook uses Python for JSON parsing
   - First run may be slower (Python startup)
   - Subsequent runs should be cached

---

## File Protection Design

Understanding how protection works helps debug:

### Protection Mechanism

1. **Input validation**
   - Hook receives JSON from Claude Code
   - Parses tool name and file path
   - Non-blocking on parse errors

2. **Pattern matching**
   - Protected patterns checked in order
   - Substring matching (patterns can be wildcards)
   - Fast: typically < 1ms

3. **Whitelist override**
   - Whitelist checked if file is protected
   - Whitelist patterns also use substring matching
   - Allows protected files when explicitly whitelisted

4. **Error response**
   - If blocked: error message to stderr, exit 2
   - If allowed: silent success, exit 0
   - Errors include actionable suggestions

### Default Protected Patterns

These are always protected (unless whitelisted):

```
.beads/          — Issue tracking state
.devloop/        — DevLoop agent findings
.git/            — Git repository metadata
.agents/hooks/   — Verification hooks
.claude/         — Claude Code configuration
AGENTS.md        — Development guidelines
CODING_RULES.md  — Coding standards
AMP_ONBOARDING.md — Onboarding documentation
```

---

## Whitelist Best Practices

### ✅ Do

- **Use specific patterns**: `.beads/custom-data.json` instead of `.beads/`
- **Document why**: Add comments in whitelist explaining the need
- **Keep minimal**: Only whitelist files you actually need to modify
- **Review regularly**: Remove whitelisted files when no longer needed

### ❌ Don't

- **Don't whitelist entire directories**: `.devloop/` opens up all files
- **Don't over-whitelist**: Each exception reduces protection
- **Don't commit large whitelists**: Keep them project-specific
- **Don't use as "allow-all"**: Whitelist defeats purpose if overused

---

## Getting Help

If troubleshooting doesn't work:

1. **Check hook source code**: `.agents/hooks/claude-file-protection`
2. **Review test suite**: `tests/test_file_protection.py`
3. **Check hook documentation**: `.agents/hooks/README.md`
4. **Look for logs**: `~/.claude/logs/` (if available)
5. **Test in isolation**: Use the "Test Hook Directly" section above

---

## Reporting Issues

If you find a bug in the file protection hook:

1. Run the test suite:
   ```bash
   poetry run pytest tests/test_file_protection.py -v
   ```

2. Collect debug info:
   ```bash
   # Your Claude Code version
   echo "Claude Code version: $(claude --version 2>/dev/null || echo 'unknown')"
   
   # Python version
   python3 --version
   
   # Hook version
   head -5 .agents/hooks/claude-file-protection
   
   # Your OS
   uname -a
   ```

3. Create Beads issue with:
   - Exact error message
   - File path that triggered error
   - Debug output from above
   - Steps to reproduce

---

## Related Documentation

- **Hook Overview**: `.agents/hooks/README.md`
- **Implementation**: `.amp/PHASE2_TEST_PLAN.md`
- **Claude Code Docs**: https://code.claude.com/docs/en/hooks
- **DevLoop Docs**: `AGENTS.md` and `CLAUDE.md`
