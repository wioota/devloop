# Report-Only Mode - Architecture Update

## Problem Identified

Having background agents automatically modify files creates conflicts with the coding agent (Claude Code):
- **Race conditions**: Coding agent writes → Background agent modifies → State out of sync
- **Competing intent**: Multiple writers to same files
- **User confusion**: "Did I write that or did an agent change it?"
- **Git complexity**: Multiple concurrent modifications

## Solution: Report-Only Architecture

Background agents are now **passive observers** that report findings to the coding agent, rather than active modifiers.

## Configuration Changes

### Updated `.claude/agents.json`

```json
{
  "global": {
    "mode": "report-only",           // NEW: Global mode indicator
    "contextStore": {                 // NEW: Where findings are stored
      "enabled": true,
      "path": ".claude/context"
    }
  },
  "agents": {
    "linter": {
      "config": {
        "autoFix": false,             // Already false - no auto-fixing
        "reportOnly": true            // NEW: Explicit report-only flag
      }
    },
    "formatter": {
      "config": {
        "formatOnSave": false,        // CHANGED: Was true, now false
        "reportOnly": true            // NEW: Check formatting, don't apply
      }
    }
  }
}
```

## Agent Behavior Changes

### LinterAgent
- ✅ **Already report-only**: `autoFix: false` prevents automatic fixes
- ✅ **Behavior**: Detects issues, reports them, doesn't modify files
- **Output**: "Found N issue(s) in file.py"

### FormatterAgent
- ✅ **Now report-only**: Added `reportOnly` mode
- ✅ **Behavior**: Checks if formatting needed, reports it, doesn't modify
- **Methods added**:
  - `_check_black()`: Uses `black --check` to detect formatting needs
  - `_check_prettier()`: Uses `prettier --check` to detect formatting needs
- **Output**: "Would format file.py with black (report-only mode)"

### TestRunnerAgent
- ✅ **Already report-only**: Only runs tests, doesn't modify code
- **Output**: "Passed 5, Failed 0, Skipped 1"

## How It Works Now

```
File Change Event
       ↓
   EventBus
       ↓
  ┌────┴────┬─────────────┬──────────────┐
  │         │             │              │
Linter  Formatter    TestRunner    (Future Agents)
  │         │             │              │
  └─────────┴─────────────┴──────────────┘
                ↓
        Agent Findings
                ↓
   (Future: Context Store)
                ↓
       Coding Agent Reads
                ↓
  Applies Fixes Intelligently
```

## Benefits

✅ **No File Conflicts**: Only coding agent (or user) modifies files
✅ **Transparent**: Clear what agents found vs. what coding agent did
✅ **Contextual**: Coding agent has full picture before making changes
✅ **Controllable**: User/coding agent decides when to apply fixes
✅ **Auditable**: Can track what was found and when

## What Changed in Code

### `src/claude_agents/agents/formatter.py`

1. Added `report_only` to `FormatterConfig`
2. Updated `handle()` to check `report_only` flag
3. Added `_check_formatter()` method
4. Added `_check_black()` - uses `black --check`
5. Added `_check_prettier()` - uses `prettier --check`

**Before**:
```python
# Run black and modify file
proc = await asyncio.create_subprocess_exec(
    "black", "--quiet", str(path), ...
)
```

**After (in report-only mode)**:
```python
# Check if formatting needed, don't modify
proc = await asyncio.create_subprocess_exec(
    "black", "--check", "--quiet", str(path), ...
)
# Returns: needs_formatting = True/False
```

## Next Steps (Future Implementation)

### Phase 1: Context Store ✅ Configured
- [x] Added `contextStore` config
- [ ] Implement context file writers
- [ ] Create `.claude/context/` directory structure
- [ ] Write agent findings to JSON files

### Phase 2: Coding Agent Integration
- [ ] Coding agent reads `.claude/context/` on task start
- [ ] Display findings in task context
- [ ] Apply fixes as part of coding workflow
- [ ] Clear findings after applying

### Phase 3: Enhanced Reporting
- [ ] Severity levels for findings
- [ ] Suggested fixes with diffs
- [ ] Priority ordering
- [ ] Aggregated summaries

## Testing Report-Only Mode

### Test 1: Create File with Issues
```bash
# Create file with formatting issues
cat > test_report_only.py << 'EOF'
def bad_spacing(x,y):
    return x+y
EOF
```

**Expected Output**:
```
INFO ✓ linter: Found 2 issue(s) in test_report_only.py
INFO ✓ formatter: Would format test_report_only.py with black (report-only mode)
```

**Verify**: File should NOT be modified

### Test 2: Check File Contents
```bash
cat test_report_only.py
# Should still show: def bad_spacing(x,y):
# NOT:              def bad_spacing(x, y):
```

## Migration Notes

If you want to **enable auto-formatting** again (not recommended with coding agent):
```json
{
  "formatter": {
    "config": {
      "formatOnSave": true,
      "reportOnly": false
    }
  }
}
```

## Architecture Alignment

This aligns with the vision in `INTERACTION_MODEL.md`:

> **Background Agents** observe and report
> **Coding Agents** (Claude Code/Amp) act on findings
> **Context Store** bridges the two

---

**Status**: ✅ Implemented and ready to test
**Date**: October 25, 2025
**Version**: 0.1.0 with report-only mode
