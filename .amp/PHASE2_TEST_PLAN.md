# Phase 2: Testing & Refinement Plan

**Date**: 2025-12-14
**Status**: In Progress
**Beads Issue**: claude-agents-agt

---

## Overview

Phase 2 validates the Phase 1 implementation and adds whitelist mechanism for legitimate edits. This document outlines the testing strategy and refinement roadmap.

---

## 1. File Protection Testing

### 1.1 Protected Files Should Block

Test that these files cannot be written to:

```bash
# Test each protected pattern
- .beads/issues.jsonl
- .devloop/config.json
- .git/config
- .agents/hooks/my-hook
- .claude/settings.json
- AGENTS.md
- CODING_RULES.md
- AMP_ONBOARDING.md
```

**Test Script**:
```bash
#!/bin/bash
# Test Write/Edit calls to protected files
for file in .beads/issues.jsonl .devloop/config.json AGENTS.md; do
  # Simulate Claude Code hook input
  input='{"tool_name":"Write","tool_input":{"path":"'$file'","content":"test"}}'
  echo "$input" | ./.agents/hooks/claude-file-protection
  
  if [ $? -eq 2 ]; then
    echo "✅ Correctly blocked: $file"
  else
    echo "❌ FAILED to block: $file"
  fi
done
```

### 1.2 Safe Files Should Allow

Test that these files can be written:

```bash
- src/mymodule.py
- tests/test_something.py
- README.md (not protected)
- docs/guide.md
- examples/example.py
```

**Expected Behavior**: Exit code 0 (allow write)

### 1.3 Edge Cases

#### Relative Paths
```bash
# Test if relative paths are normalized correctly
./AGENTS.md → should block
./src/file.py → should allow
../parent_dir/AGENTS.md → should block
```

#### Symlinks
```bash
# Test if symlinks to protected files are handled
ln -s .beads/issues.jsonl link-to-beads
# Symlink should resolve to protected file → block
```

#### Unusual Filenames
```bash
# Test special characters and Unicode
"file with spaces.py" → allow
"file(1).py" → allow
"AGENTS.md.bak" → should allow (not exact match)
```

#### Absolute Paths
```bash
# Test absolute vs relative path handling
/home/user/project/AGENTS.md → block
/home/user/project/src/file.py → allow
```

---

## 2. Whitelist Mechanism

### 2.1 Whitelist File Format

Create `.claude/file-protection-whitelist.json`:

```json
{
  "allowed_patterns": [
    "AGENTS.md",
    ".devloop/custom-config.json"
  ],
  "description": "Files that should be modifiable despite being protected",
  "last_updated": "2025-12-14"
}
```

### 2.2 Whitelist Testing

#### Add to Whitelist
```bash
# Create whitelist allowing AGENTS.md edits
echo '{"allowed_patterns":["AGENTS.md"]}' > .claude/file-protection-whitelist.json

# Now writing to AGENTS.md should succeed
input='{"tool_name":"Write","tool_input":{"path":"AGENTS.md","content":"test"}}'
echo "$input" | ./.agents/hooks/claude-file-protection
# Should exit 0
```

#### Multiple Patterns
```bash
# Test whitelist with multiple patterns
{
  "allowed_patterns": [
    "AGENTS.md",
    ".devloop/local.json",
    "docs/setup.md"
  ]
}

# Each should be whitelisted
```

#### Invalid Whitelist Format
```bash
# Whitelist doesn't exist → use defaults
# Invalid JSON → use defaults  
# Missing allowed_patterns key → use defaults
```

---

## 3. Integration Testing

### 3.1 Non-Protected Tools

Test that non-Write/Edit tools are not affected:

```bash
# Read tool should not be blocked
input='{"tool_name":"Read","tool_input":{"path":"AGENTS.md"}}'
echo "$input" | ./.agents/hooks/claude-file-protection
# Should exit 0

# Bash tool should not be blocked
input='{"tool_name":"Bash","tool_input":{"cmd":"ls -la"}}'
echo "$input" | ./.agents/hooks/claude-file-protection
# Should exit 0
```

### 3.2 Empty Input

Test graceful handling of empty or invalid input:

```bash
# Empty input
echo "" | ./.agents/hooks/claude-file-protection
# Should exit 0 (non-blocking)

# Invalid JSON
echo "not json" | ./.agents/hooks/claude-file-protection
# Should exit 0 (non-blocking)

# Missing tool_name
echo '{"tool_input":{}}' | ./.agents/hooks/claude-file-protection
# Should exit 0 (not recognized as Write/Edit)
```

### 3.3 Project Directory Handling

Test CLAUDE_PROJECT_DIR environment variable:

```bash
# No env var → use current directory
./.agents/hooks/claude-file-protection

# With env var → use that directory
CLAUDE_PROJECT_DIR=/other/path ./.agents/hooks/claude-file-protection

# Non-existent directory → graceful handling
CLAUDE_PROJECT_DIR=/nonexistent ./.agents/hooks/claude-file-protection
# Should not crash
```

---

## 4. Error Message Validation

### 4.1 Clear Messaging

When blocking, error message should include:

✅ What happened (file blocked)
✅ Why (protected by DevLoop)
✅ Alternatives (manual edit, whitelist, ask user)
✅ Example of whitelist setup

**Current message**:
```
🚫 Protected file: /path/to/AGENTS.md

This file is protected by DevLoop to prevent accidental modifications.
If you need to modify this file:
1. Use manual editing via terminal: nano "/path/to/AGENTS.md"
2. Or ask the user to make the change manually
3. Or describe what you're trying to do
4. To whitelist this file, add it to .claude/file-protection-whitelist.json
```

### 4.2 Test Error Display
- ✅ Message goes to stderr
- ✅ Message is clear and actionable
- ✅ Exit code is 2 (blocking error)

---

## 5. DevLoop Integration Testing

### 5.1 DevLoop Available

When devloop is installed and working:

```bash
# SessionStart hook should load context
./.agents/hooks/claude-session-start
# Should run: devloop amp_context (or skip gracefully if not available)

# Stop hook should collect findings
echo "some findings" | ./.agents/hooks/claude-stop
# Should run: devloop amp_findings
```

### 5.2 DevLoop Missing

When devloop is not installed:

```bash
# Hooks should still work (non-blocking)
./.agents/hooks/claude-session-start
# Should exit 0, not crash

echo "findings" | ./.agents/hooks/claude-stop
# Should exit 0, not crash
```

### 5.3 DevLoop Command Failures

When devloop commands fail:

```bash
# Mock devloop returning error
devloop() { exit 1; }

./.agents/hooks/claude-session-start
# Should gracefully handle failure, exit 0
```

---

## 6. Regression Testing

### 6.1 Git Hooks Still Work

```bash
# Verify pre-commit hook still runs
git add .
git commit -m "test"
# Should run pre-commit hook, format code, etc.

# Verify pre-push hook still runs
git push origin main
# Should check CI status before allowing push
```

### 6.2 Amp Hooks Still Work

```bash
# Verify post-task hook still runs
# (when working in Amp)
```

### 6.3 CLI Commands Still Work

```bash
# Test devloop commands still functional
devloop status
devloop verify-work
devloop amp-context
devloop amp-findings
```

---

## 7. Documentation

### 7.1 File Protection Guide

Update `.agents/hooks/README.md`:

- [ ] Document protected files and why
- [ ] Document whitelist mechanism
- [ ] Document alternatives when protection blocks edits
- [ ] Provide examples of common use cases
- [ ] Add troubleshooting section

### 7.2 Whitelist How-To

Create `.claude/file-protection-whitelist.md`:

- [ ] When to use whitelist
- [ ] How to create whitelist file
- [ ] Example configurations
- [ ] Performance impact (minimal)

### 7.3 Error Message Updates

- [ ] Review error messages for clarity
- [ ] Add examples to error output
- [ ] Link to documentation

### 7.4 Troubleshooting Guide

Create `.agents/TROUBLESHOOTING.md`:

- [ ] "Hook blocked my edit" → solutions
- [ ] "Hook not running" → debug steps
- [ ] "Changes to protected file keep getting blocked" → whitelist setup
- [ ] "Performance is slow" → expected behavior

---

## 8. Code Quality

### 8.1 Shell Script Validation

```bash
# All scripts pass shellcheck
shellcheck .agents/hooks/claude-*
# Should have no warnings
```

### 8.2 Python Code Quality

```bash
# Hook uses Python inline - validate syntax
python3 -m py_compile .agents/hooks/claude-file-protection
# Should succeed

# Check Python code quality (if extracted to module)
ruff check src/
mypy src/
# Should pass
```

### 8.3 Test Coverage

```bash
# Unit tests for file protection logic
pytest tests/test_file_protection.py -v
```

---

## 9. Edge Cases

### 9.1 Permission Issues

```bash
# Test when file cannot be read
chmod 000 .agents/hooks/claude-file-protection
# Should still not crash
chmod 644 .agents/hooks/claude-file-protection
```

### 9.2 Large Input

```bash
# Test with large tool_input JSON
# Should handle efficiently
```

### 9.3 Special Characters in Paths

```bash
# Test filenames with:
# - Spaces: "my file.py"
# - Quotes: "file\"with\"quotes.py"
# - Unicode: "файл.py"
# - Newlines in JSON (escaped): "file\nwith\nnewlines.py"
```

---

## 10. Testing Execution Plan

### Phase 2a: Manual Testing (Days 1-2)
- [ ] Run protected file tests manually
- [ ] Test whitelist mechanism manually
- [ ] Test edge cases manually
- [ ] Verify error messages
- [ ] Check integration with devloop

### Phase 2b: Automated Testing (Days 2-3)
- [ ] Create test scripts in `tests/`
- [ ] Run shellcheck on all hooks
- [ ] Add unit tests for file protection logic
- [ ] Run full test suite (pytest)

### Phase 2c: Documentation (Days 3)
- [ ] Update hook README
- [ ] Create whitelist guide
- [ ] Create troubleshooting guide
- [ ] Update AMP_ONBOARDING.md if needed

### Phase 2d: Verification (Day 3-4)
- [ ] Manual testing with Claude Code
- [ ] Regression testing (git, amp, cli)
- [ ] Code review for shell/python
- [ ] Final validation

---

## Success Criteria

### Must Have ✅
- [ ] All protected files are blocked
- [ ] Safe files are allowed
- [ ] Error messages are clear
- [ ] Whitelist mechanism works
- [ ] No false positives (legitimate edits not blocked)
- [ ] No false negatives (protected files not bypassed)
- [ ] All tests pass
- [ ] No regressions in git/amp/cli

### Should Have ✅
- [ ] Edge cases handled
- [ ] Shell scripts pass shellcheck
- [ ] Python code is correct
- [ ] Documentation is complete
- [ ] Troubleshooting guide available

### Nice to Have
- [ ] Performance optimized
- [ ] Logging for debugging
- [ ] Custom error messages per file type

---

## Commit Strategy

Each day's work will be committed:

**Day 1 (Manual Testing)**:
```bash
git commit -m "test(phase2): Manual testing of file protection"
```

**Day 2 (Automation)**:
```bash
git commit -m "test(phase2): Add automated test suite for file protection"
```

**Day 3 (Documentation)**:
```bash
git commit -m "docs(phase2): Complete file protection documentation"
```

**Day 4 (Final)**:
```bash
git commit -m "feat(phase2): File protection refinement complete"
```

---

## Notes

- All testing is local (no devloop instance required unless testing integration)
- Whitelist is optional - works fine without it
- Hook failures are non-blocking by design
- Error messages should guide users toward solutions

