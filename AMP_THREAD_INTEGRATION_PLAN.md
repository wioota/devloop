# Amp Thread Integration for Self-Improvement Agent

## Overview

The Self-Improvement Agent can leverage Amp's thread context to capture rich user behavior data. This enables pattern detection across multiple threads and surfaces actionable insights tied to real Amp conversations.

## What We Get From Amp Threads

Amp provides:
1. **Thread URLs**: `https://ampcode.com/threads/T-{uuid}`
2. **Thread IDs**: `T-{uuid}` format for programmatic reference
3. **Thread Referencing**: Via `@T-uuid` or full URL in messages
4. **Thread Continuity**: Can continue any thread with `continue: 'T-abc123'`
5. **Read-Thread Tool**: Amp can fetch and extract context from threads
6. **Server-Side Storage**: All thread data persists on ampcode.com

## The Opportunity

When a user in an Amp thread:
1. Asks Claude to run devloop agents
2. Agent produces output (e.g., linter finds issues)
3. User manually fixes something OR re-asks the same question

We can correlate:
- **Thread A**: "User asked to format code" → linter found style issues → user manually fixed them
- **Thread B**: "User asked to format code" → linter found style issues → user manually fixed them
- **Pattern**: "Formatter not auto-applying fixes (3 occurrences)"

This creates **high-confidence insights** with **thread references** as evidence.

## Implementation Strategy

### Phase 0: Action Logging with Thread Support

Create `.devloop/cli-actions.jsonl`:
```json
{
  "timestamp": "2025-12-12T10:23:45Z",
  "command": "devloop watch",
  "thread_id": "T-7f395a45-7fae-4983-8de0-d02e61d30183",
  "thread_url": "https://ampcode.com/threads/T-7f395a45-7fae-4983-8de0-d02e61d30183"
}
```

**How to pass thread context**:
Option 1 (requires Amp hook):
```bash
# Amp's post-command hook injects env vars
export AMP_THREAD_ID="T-xxx"
devloop watch
```

Option 2 (user responsibility):
```bash
AMP_THREAD_ID=T-xxx devloop watch
```

Option 3 (detect from .amp config):
```python
# Read .amp/config.json for current thread context
thread_id = read_from_amp_config()
```

### Phase 1: Thread-Aware Pattern Detection

Build `.devloop/amp-thread-log.jsonl` that maps:
```json
{
  "thread_id": "T-7f395a45...",
  "user_prompt": "Format this code",
  "agent_actions": [
    {"action": "linter", "findings": 5, "auto_fixable": 5}
  ],
  "user_manual_actions": [
    {"action": "manual_format", "files": ["index.ts"], "after_seconds": 120}
  ],
  "pattern": "user_manual_fix_after_agent_suggestion"
}
```

Pattern detector asks: "When did user manually do what agent suggested?"

### Phase 2: Cross-Thread Analysis

Query all threads to find:
- Users asking same question repeatedly
- Same pattern (user manual fix) across multiple threads
- Patterns that correlate with specific agent types

### Phase 3: Thread-Linked Issues

Create beads issues with thread references:
```bash
bd create "Formatter not auto-applying fixes" \
  -p 1 \
  --deps discovered-from:claude-agents-zjf \
  -d "Pattern detected in threads:
      - T-7f395a45... (Dec 12)
      - T-8g406b56... (Dec 12)
      - T-9h517c67... (Dec 11)
      
      User manually applied formatting 3 times after linter output"
```

## Expected Insights

With Amp thread integration, we can detect:

1. **Messaging Issues**: "User manually fixed what agent output suggested" → agent not clear
2. **Feature Gaps**: "User asked for same help 5 times" → missing automation
3. **Silent Failures**: "Agent ran but user never acted on output" → low confidence
4. **Config Issues**: "Linter caught different errors in same type of file across threads" → inconsistent config
5. **Coordination Issues**: "Formatter ran after linter but user still had to fix" → agents not working together

## Technical Requirements

**Minimal**:
- Action logger that captures optional thread_id
- Amp thread mapper to correlate actions
- Pattern detector with thread-aware matching

**Nice to have**:
- Amp hook to auto-inject thread context
- .amp/config.json parser for thread detection
- Amp SDK integration for programmatic thread access

## User Experience

For devloop users in Amp:

```bash
# User in Amp thread does:
devloop watch
# Or with manual thread context:
AMP_THREAD_ID=T-abc123 devloop watch

# Devloop logs this with thread context
# Self-improvement agent correlates patterns across threads

# After multiple patterns detected:
bd ready  # Shows discovered issues like:
  # "Formatter not auto-applying (discovered from Amp threads T-xxx, T-yyy)"
```

For Amp users:

```
# When Claude helps with devloop tasks:
"Run the linter on this code"

# Claude execution is logged with thread context
# Later: "The self-improvement agent noticed users need to manually 
#         fix formatting 3 times across different threads. 
#         Issue created: devloop#42"
```

## Privacy Considerations

- Thread IDs are logged locally in `.devloop/` (not uploaded)
- Only thread ID and URL are captured (not thread content)
- Users can opt-out by not setting `AMP_THREAD_ID`
- Analysis is local-only (happens in .devloop daemon)

## Next Steps

1. **Implement action logger** (Phase 0)
   - Capture CLI commands with optional thread context
   - Store in cli-actions.jsonl

2. **Create thread mapper** (Phase 0)
   - Correlate actions with thread IDs
   - Store in amp-thread-log.jsonl

3. **Build pattern detector** (Phase 1)
   - Frequency analysis with thread context
   - Cross-thread pattern matching

4. **Document in AGENTS.md** (Phase 0)
   - How to pass thread context to devloop
   - Example hook for Amp users
