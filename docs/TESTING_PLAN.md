# Context Store - Development Testing Plan

## Overview

This document outlines the testing approach for the Context Store feature. We'll test in a controlled development environment before deploying to production use.

## Test Environment Setup

### Prerequisites

```bash
# Ensure you're in the project directory
cd /home/wioot/dev/claude-agents

# Activate virtual environment
source .venv/bin/activate

# Verify tools are installed
ruff --version
black --version
pytest --version
```

### Create Test Project

```bash
# Create a test directory structure
mkdir -p test_context_store/{src,tests}

# Create test files with intentional issues
cat > test_context_store/src/sample.py << 'EOF'
import os
import sys
import datetime  # unused import


def hello(name):  # missing type annotation
    """Say hello"""
    x=1+2  # formatting issue
    return f"Hello {name}"

def unused_function():  # unused function
    pass
EOF

cat > test_context_store/tests/test_sample.py << 'EOF'
def test_hello():
    from src.sample import hello
    assert hello("World") == "Hello World"

def test_missing():  # This test will fail
    assert False
EOF
```

## Testing Phases

### Phase 1: Core Context Store Functionality

**Objective**: Verify context store can write, read, and organize findings.

#### Test 1.1: Basic Writing
```bash
# Start agents in watch mode
claude-agents watch test_context_store/

# In another terminal, trigger events
touch test_context_store/src/sample.py

# Verify context files created
ls -la test_context_store/.claude/context/
# Expected: immediate.json, relevant.json, background.json, index.json, metadata.json
```

**Success Criteria:**
- [ ] Context directory created
- [ ] JSON files are valid
- [ ] Findings from linter are captured
- [ ] Findings from formatter are captured
- [ ] Findings from test runner are captured

#### Test 1.2: Tier Assignment
```bash
# Read the tier files
cat test_context_store/.claude/context/immediate.json | jq '.'
cat test_context_store/.claude/context/relevant.json | jq '.'
cat test_context_store/.claude/context/background.json | jq '.'
```

**Success Criteria:**
- [ ] Blocking errors → immediate.json
- [ ] Warnings → relevant.json
- [ ] Style issues → background.json or auto_fixed.json
- [ ] Relevance scores calculated correctly

#### Test 1.3: Index Generation
```bash
# Check the index file
cat test_context_store/.claude/context/index.json | jq '.'
```

**Expected Structure:**
```json
{
  "last_updated": "...",
  "check_now": {
    "count": 0-3,
    "preview": "..."
  },
  "mention_if_relevant": {
    "count": 2-5,
    "summary": "..."
  },
  "deferred": {
    "count": 5-10
  }
}
```

**Success Criteria:**
- [ ] Counts are accurate
- [ ] Preview text is helpful
- [ ] Summary is concise

### Phase 2: Agent Integration

**Objective**: Verify all agents write to context store correctly.

#### Test 2.1: Linter Agent
```bash
# Modify file to trigger linter
echo "def bad_func( ):" >> test_context_store/src/sample.py

# Check context
cat test_context_store/.claude/context/relevant.json | jq '.findings[] | select(.agent == "linter")'
```

**Success Criteria:**
- [ ] New lint issues captured
- [ ] File, line, column recorded
- [ ] Severity classified correctly
- [ ] Auto-fixable flag set appropriately

#### Test 2.2: Formatter Agent
```bash
# Check formatting findings
cat test_context_store/.claude/context/background.json | jq '.findings[] | select(.agent == "formatter")'
```

**Success Criteria:**
- [ ] Formatting issues identified
- [ ] Auto-fixable marked as true
- [ ] Suggestions included

#### Test 2.3: Test Runner Agent
```bash
# Run tests to populate test results
python -m pytest test_context_store/tests/

# Check test context
cat test_context_store/.claude/context/immediate.json | jq '.findings[] | select(.agent == "test-runner")'
```

**Success Criteria:**
- [ ] Failed tests → immediate.json
- [ ] Passed tests not in findings (or in metadata only)
- [ ] Test failure details included

### Phase 3: Relevance Scoring

**Objective**: Verify relevance algorithm works correctly.

#### Test 3.1: File Scope Relevance
```bash
# Edit a file, check that findings for THAT file score higher
echo "# comment" >> test_context_store/src/sample.py

# Check relevance scores
cat test_context_store/.claude/context/relevant.json | jq '.findings[] | {file, relevance_score}'
```

**Success Criteria:**
- [ ] Recently modified files have higher scores
- [ ] Unmodified files have lower scores
- [ ] Scores are in 0.0-1.0 range

#### Test 3.2: Severity Impact
```bash
# Introduce a blocking error
echo "syntax error here @#$" >> test_context_store/src/sample.py

# Check it goes to immediate
cat test_context_store/.claude/context/immediate.json | jq '.findings[] | select(.blocking == true)'
```

**Success Criteria:**
- [ ] Blocking errors always in immediate.json
- [ ] Syntax errors marked as blocking
- [ ] Relevance score >= 0.8

#### Test 3.3: Freshness Tracking
```bash
# Check timestamps and is_new flags
cat test_context_store/.claude/context/relevant.json | jq '.findings[] | {id, is_new, timestamp}'
```

**Success Criteria:**
- [ ] New findings marked with is_new: true
- [ ] Timestamps are recent
- [ ] Old findings (if any) marked is_new: false

### Phase 4: Claude Code Integration

**Objective**: Verify Claude Code can read and use context effectively.

#### Test 4.1: Manual Context Check
```bash
# Use Read tool to check index
# (This simulates what Claude Code would do)
cat test_context_store/.claude/context/index.json
```

**Success Criteria:**
- [ ] Index is human-readable
- [ ] Summary is actionable
- [ ] Counts are accurate

#### Test 4.2: Hook Integration (if Claude Code available)
```
User: "Edit the sample.py file to add a new function"

Expected Claude Behavior:
1. Use Edit tool
2. PostToolUse hook triggers context check
3. Claude reads index.json
4. Claude mentions relevant findings (if any)
```

**Success Criteria:**
- [ ] Hook executes without error
- [ ] Context is read successfully
- [ ] Relevant findings surfaced appropriately

#### Test 4.3: Completion Signal
```
User: "Done with this file"

Expected Claude Behavior:
1. Recognizes completion signal
2. Checks relevant.json
3. Summarizes findings
4. Offers to fix
```

**Success Criteria:**
- [ ] Completion signal detected
- [ ] Summary is concise
- [ ] Offer to fix is actionable

### Phase 5: Edge Cases & Error Handling

**Objective**: Verify robustness under edge conditions.

#### Test 5.1: Concurrent Writes
```bash
# Modify multiple files simultaneously
touch test_context_store/src/{file1,file2,file3}.py &
```

**Success Criteria:**
- [ ] No corrupted JSON files
- [ ] All findings captured
- [ ] No race conditions

#### Test 5.2: Large Number of Findings
```bash
# Create a file with 100+ issues
python -c "
with open('test_context_store/src/many_issues.py', 'w') as f:
    for i in range(100):
        f.write(f'def func{i}( ):pass\n')  # 100 style issues
"
```

**Success Criteria:**
- [ ] All findings captured
- [ ] Index summary is still readable
- [ ] Performance is acceptable (< 1s)

#### Test 5.3: Missing Tools
```bash
# Temporarily rename a tool
mv ~/.local/bin/ruff ~/.local/bin/ruff.bak

# Trigger linter
touch test_context_store/src/sample.py

# Restore
mv ~/.local/bin/ruff.bak ~/.local/bin/ruff
```

**Success Criteria:**
- [ ] Graceful degradation
- [ ] Error message is helpful
- [ ] Other agents continue working

#### Test 5.4: Malformed Context Files
```bash
# Corrupt a context file
echo "invalid json" > test_context_store/.claude/context/relevant.json

# Trigger agents
touch test_context_store/src/sample.py
```

**Success Criteria:**
- [ ] File is detected as corrupt
- [ ] File is backed up or recreated
- [ ] System recovers gracefully

### Phase 6: Performance & Resource Usage

**Objective**: Verify performance is acceptable.

#### Test 6.1: Write Latency
```bash
# Time the context write operation
time touch test_context_store/src/sample.py
# (Agents should complete in < 1s)
```

**Success Criteria:**
- [ ] Context write < 50ms
- [ ] Total agent execution < 1s
- [ ] No blocking operations

#### Test 6.2: Read Latency
```bash
# Time reading the index
time cat test_context_store/.claude/context/index.json
```

**Success Criteria:**
- [ ] Read < 10ms
- [ ] File size reasonable (< 100KB typically)

#### Test 6.3: Storage Usage
```bash
# Check context directory size
du -sh test_context_store/.claude/context/
```

**Success Criteria:**
- [ ] < 1MB for typical usage
- [ ] Old findings pruned appropriately

## Self-Hosting Test (Dogfooding)

**Objective**: Run claude-agents on itself during development.

### Setup

```bash
# Start agents watching this project
cd /home/wioot/dev/claude-agents
claude-agents watch .
```

### Monitor During Development

**Watch for:**
1. **Excessive interruptions**: Are agents too noisy?
2. **Missed issues**: Are important issues not surfaced?
3. **False positives**: Are irrelevant findings surfaced?
4. **Performance**: Does it slow down development?

### Issue Logging

If issues arise:

```bash
# Disable agents
pkill -f claude-agents

# Log the issue
echo "$(date): [ISSUE] Description of what went wrong" >> CONTEXT_STORE_ISSUES.log
echo "  - What you were doing" >> CONTEXT_STORE_ISSUES.log
echo "  - What happened" >> CONTEXT_STORE_ISSUES.log
echo "  - Expected behavior" >> CONTEXT_STORE_ISSUES.log
echo "" >> CONTEXT_STORE_ISSUES.log
```

### Issue Categories to Watch

1. **Interruption Issues**
   - Context shown when not relevant
   - Interruptions during flow state
   - Too many notifications

2. **Relevance Issues**
   - Important findings missed
   - Irrelevant findings surfaced
   - Incorrect tier assignment

3. **Performance Issues**
   - Slow file saves
   - High CPU/memory usage
   - Lag in terminal

4. **Correctness Issues**
   - Corrupted context files
   - Missing findings
   - Incorrect metadata

## Test Checklist

### Before Starting
- [ ] Virtual environment activated
- [ ] All tools installed (ruff, black, pytest)
- [ ] Backup of current work
- [ ] Test project created

### Phase 1: Core Functionality
- [ ] Test 1.1: Basic Writing
- [ ] Test 1.2: Tier Assignment
- [ ] Test 1.3: Index Generation

### Phase 2: Agent Integration
- [ ] Test 2.1: Linter Agent
- [ ] Test 2.2: Formatter Agent
- [ ] Test 2.3: Test Runner Agent

### Phase 3: Relevance Scoring
- [ ] Test 3.1: File Scope Relevance
- [ ] Test 3.2: Severity Impact
- [ ] Test 3.3: Freshness Tracking

### Phase 4: Claude Code Integration
- [ ] Test 4.1: Manual Context Check
- [ ] Test 4.2: Hook Integration
- [ ] Test 4.3: Completion Signal

### Phase 5: Edge Cases
- [ ] Test 5.1: Concurrent Writes
- [ ] Test 5.2: Large Number of Findings
- [ ] Test 5.3: Missing Tools
- [ ] Test 5.4: Malformed Context Files

### Phase 6: Performance
- [ ] Test 6.1: Write Latency
- [ ] Test 6.2: Read Latency
- [ ] Test 6.3: Storage Usage

### Dogfooding
- [ ] Agents running on claude-agents project
- [ ] Monitored during development
- [ ] Issues logged if encountered
- [ ] Performance acceptable

## Success Criteria Summary

The context store implementation is ready for production when:

1. **Functional**: All tests pass
2. **Performant**: < 50ms write latency, < 10ms read latency
3. **Reliable**: No data corruption, graceful error handling
4. **Relevant**: > 80% of surfaced findings are actionable
5. **Non-intrusive**: < 5% interruption rate
6. **Dogfood Ready**: Successfully used on itself without issues

## Next Steps After Testing

1. **Address Issues**: Fix any bugs found during testing
2. **Tune Parameters**: Adjust relevance scoring based on results
3. **Documentation**: Update user guide with findings
4. **Demo**: Create demo video showing the feature
5. **Release**: Merge to main and tag version

## Rollback Plan

If critical issues are found:

```bash
# Disable context store in config
# Edit .claude/agents.json:
{
  "contextStore": {
    "enabled": false
  }
}

# Or stop agents entirely
pkill -f claude-agents

# Document issues for debugging session
git checkout -b debug/context-store-issues
# Create DEBUGGING.md with details
```

## Contact & Support

If you encounter issues during testing:
1. Log in CONTEXT_STORE_ISSUES.log
2. Disable agents if blocking work
3. Schedule debugging session
4. Review logs together

---

**Testing Start Date**: TBD
**Testing Duration**: 1-2 days
**Tester**: User (you)
**Status**: Ready to begin after implementation
