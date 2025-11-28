# Claude Code Integration Test Guide

## Quick Start Test

**Goal:** Verify that Claude Code can read and use context from background agents.

### Step 1: Start Background Agents

```bash
cd /home/wioot/dev/claude-agents/test_context_integration
claude-agents watch .
```

You should see:
```
Claude Agents v2
Watching: /home/wioot/dev/claude-agents/test_context_integration

Context store: /home/wioot/dev/claude-agents/test_context_integration/.claude/context
✓ Started agents:
  • linter

Waiting for file changes...
```

### Step 2: Trigger Agent by Modifying File

In another terminal:
```bash
# Make a small change to trigger linter
echo "" >> test_context_integration/src/sample.py
```

Watch the agent output - it should show lint issues found.

### Step 3: Check Context Files Exist

```bash
ls -la test_context_integration/.claude/context/
```

You should see:
- `index.json` - Quick summary
- `immediate.json` - Blocking issues
- `relevant.json` - Relevant issues
- `background.json` - Background issues
- `auto_fixed.json` - Auto-fixed items

### Step 4: Read Context as Claude Code Would

```bash
# View the index (what Claude Code reads first)
cat test_context_integration/.claude/context/index.json | python3 -m json.tool
```

You should see something like:
```json
{
  "last_updated": "2025-11-28T00:49:29Z",
  "check_now": {
    "count": 4,
    "severity_breakdown": {"error": 4},
    "files": ["test_context_integration/src/sample.py"],
    "preview": "4 error"
  },
  "mention_if_relevant": {
    "count": 0,
    "summary": "No relevant issues"
  }
}
```

### Step 5: Test with Claude Code (Manual)

**In a Claude Code conversation:**

```
User: "Check .claude/context/index.json and tell me what issues were found"

[Claude Code uses Read tool to read the index.json]

Claude: "I found 4 errors in test_context_integration/src/sample.py:
- 3 unused imports (os, sys, datetime)
- 1 additional linting issue

Would you like me to fix these?"
```

### Step 6: Test Decision Framework

**Scenario 1: After Edit**
```
User: "Add a new function to src/sample.py"

[Claude uses Edit tool]

[Claude should automatically check index.json]

Expected: Claude mentions if there are new issues in the file just edited
```

**Scenario 2: Completion Signal**
```
User: "Done with sample.py"

[Claude should check relevant.json]

Expected: Claude summarizes any deferred issues before committing
```

**Scenario 3: Direct Question**
```
User: "Are there any linting issues in this project?"

[Claude should check index.json and immediate.json]

Expected: Claude lists all immediate issues
```

## Detailed Test: LLM Decision Making

### Test 1: Immediate Issues Surface

**Setup:**
```bash
# Create file with blocking error
cat > test_context_integration/src/broken.py << 'EOF'
def foo(:  # syntax error
    pass
EOF
```

**Expected Claude Behavior:**
- Reads `index.json`
- Sees `check_now.count > 0`
- Surfaces the syntax error immediately
- Offers to fix

### Test 2: Relevant Issues at Completion

**Setup:**
```bash
# Create file with warnings
cat > test_context_integration/src/warnings.py << 'EOF'
x = 1  # unused variable
y = 2  # unused variable
EOF
```

**User says:** "Done with warnings.py"

**Expected Claude Behavior:**
- Checks `relevant.json`
- Mentions the 2 warnings
- Offers to clean up

### Test 3: Background Items on Request

**User asks:** "Show me all issues in the project"

**Expected Claude Behavior:**
- Reads all tier files
- Shows comprehensive summary
- Groups by severity and file

## Verification Checklist

After running the agents:

- [ ] `.claude/context/` directory created
- [ ] `index.json` exists and has valid JSON
- [ ] `immediate.json` has findings for errors
- [ ] Index `check_now.count` matches number of immediate issues
- [ ] Index `preview` is human-readable
- [ ] Findings have all required fields (id, agent, file, line, message)
- [ ] Relevance scores are between 0 and 1
- [ ] Tier assignment seems correct (errors → immediate)

## Common Issues & Solutions

### Issue: No context files created

**Check:**
```bash
# Is the context store initialized?
grep -r "context_store.initialize" src/claude_agents/cli/main.py
```

**Solution:** The CLI should have this code (already added):
```python
context_store.context_dir = path / ".claude" / "context"
await context_store.initialize()
```

### Issue: Findings not showing up

**Check:**
```bash
# Do findings exist in memory?
python3 test_context_integration.py
```

**Debug:**
```python
# Check if linter is writing findings
# Add debug logging to linter.py _write_findings_to_context()
logger.info(f"Writing finding: {finding.id}")
```

### Issue: Context files empty

**Check:**
```bash
# Are findings being added?
cat test_context_integration/.claude/context/immediate.json | python3 -m json.tool
```

**Look for:**
- `"count": 0` means no findings in this tier
- `"findings": []` means empty array

## Success Criteria

✅ **Phase 1 Complete When:**
- [ ] Background agents write findings to context store
- [ ] Context files are created and valid JSON
- [ ] Index file provides quick summary
- [ ] Findings have all required metadata
- [ ] Claude Code can read index.json
- [ ] Claude Code can interpret findings

✅ **Production Ready When:**
- [ ] All agents (linter, formatter, test-runner) integrated
- [ ] Claude Code reliably surfaces relevant issues
- [ ] No false positives (irrelevant findings surfaced)
- [ ] No false negatives (important issues missed)
- [ ] Performance is acceptable (< 50ms to write)

## Next Steps

1. **Test remaining agents:** Once formatter and test-runner are integrated, test them the same way
2. **Test concurrent writes:** Modify multiple files simultaneously
3. **Test large projects:** Run on real codebase with 100+ files
4. **Tune relevance scoring:** Adjust scores based on what Claude surfaces
5. **Document learnings:** Update design docs with real-world findings

## Example Claude Code Interaction

```
User: "I'm working on authentication. Are there any issues I should know about?"

Claude: [Reads .claude/context/index.json]
{
  "check_now": {"count": 1, "preview": "Type error in auth.py:42"},
  "mention_if_relevant": {"count": 2, "summary": "2 warnings"}
}

Claude: "Yes, found 3 items related to your work:

Immediate:
• Type error in auth.py:42 - missing type annotation on 'user' parameter

Also Worth Noting:
• 2 warnings in auth_utils.py (unused imports)

Should I fix the type error first?"

User: "Yes, fix it"

Claude: [Uses Edit tool to add type annotation]

Claude: [Checks index.json again - issue should be gone]

Claude: "✓ Fixed the type annotation. The file now passes type checking.
Would you like me to clean up those 2 warnings as well?"
```

---

**Ready to test!** Start with Step 1 and work through the guide.
