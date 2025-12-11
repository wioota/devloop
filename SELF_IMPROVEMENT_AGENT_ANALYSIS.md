# Self-Improvement Agent: Existing Infrastructure Analysis

## Current State

The devloop project already has comprehensive telemetry, logging, and event infrastructure in place. Here's what exists:

### 1. **Telemetry System** (`src/devloop/core/telemetry.py`)
- **Purpose**: Structured event logging in JSONL format
- **Storage**: `.devloop/events.jsonl`
- **Tracks**:
  - Agent executions (duration, findings, severity levels)
  - Pre-commit/push checks (success/failure, prevented bad pushes)
  - CI roundtrips prevented
  - Value events (manual logging of custom events)
- **Access**: Via `devloop telemetry stats|recent|export` commands
- **Status**: ✅ Production-ready with documentation in TELEMETRY.md

### 2. **Agent Audit Logger** (`src/devloop/core/agent_audit_logger.py`)
- **Purpose**: Immutable append-only audit trail of agent operations
- **Storage**: `.devloop/agent-audit.log` (30-day retention)
- **Tracks**:
  - File modifications (created/modified/deleted)
  - Command execution
  - Fixes applied
  - Findings reported
  - Errors occurred
  - Configuration changes
- **Data stored per entry**:
  - Timestamp (ISO 8601 with timezone)
  - Agent name
  - Action type
  - File diffs, sizes, line counts, SHA256 hashes
  - Duration, success status, error messages
- **Access**: Via `devloop audit recent|by_agent|errors|fixes|file|summary` commands
- **Status**: ✅ Production-ready

### 3. **Feedback System** (`src/devloop/core/feedback.py`)
- **Purpose**: Collect user feedback on agent actions
- **Storage**: 
  - `.devloop/feedback/feedback.jsonl` (individual feedback)
  - `.devloop/feedback/performance.json` (aggregated metrics)
- **Tracks**:
  - User ratings (thumbs up/down, 1-5 stars, comments)
  - Dismissals (when users ignore agent suggestions)
  - Performance metrics (execution count, success rate, avg duration)
- **API**: `FeedbackAPI` for programmatic submission and querying
- **Status**: ✅ Production-ready but not heavily integrated

### 4. **Event System** (`src/devloop/core/event.py` & `src/devloop/core/event_store.py`)
- **Purpose**: Real-time event bus and SQLite-based event persistence
- **Storage**:
  - In-memory event log (last 100 events for debugging)
  - SQLite database: `.devloop/events.db` (indexed by type, timestamp, source)
- **Features**:
  - Priority-based event dispatch
  - Pattern matching for subscriptions
  - Event type indexing
  - 30-day auto-cleanup
- **Status**: ✅ Production-ready

### 5. **Performance Monitoring** (`src/devloop/core/performance.py`)
- **Purpose**: Track resource usage and performance metrics
- **Storage**: `.devloop/metrics.jsonl` (30-day retention)
- **Tracks**:
  - CPU, memory, disk I/O, network usage
  - Per-operation performance metrics
  - Per-agent resource usage
- **Features**:
  - PerformanceOptimizer for debouncing
  - AgentResourceTracker for enforcement
- **Status**: ✅ Production-ready

### 6. **CLI Logging** (`src/devloop/cli/main.py`)
- **Purpose**: Application-level logging
- **Storage**: `.devloop/devloop.log`
- **Features**:
  - Rotating file handler for daemon mode
  - RichHandler for formatted console output
  - Functions: `setup_logging()`, `setup_logging_with_rotation()`
- **Status**: ✅ Production-ready

### 7. **Agent Health Monitoring** (`src/devloop/agents/agent_health_monitor.py`)
- **Purpose**: Detect agent failures and apply autonomous fixes
- **Storage**: Health data (source: `.devloop/health_check.json`)
- **Status**: ✅ Exists but can be enhanced

## What's MISSING for Self-Improvement Agent

### 1. **CLI Action Logging** ⚠️
- **Gap**: Individual CLI commands (e.g., `bd ready`, `devloop watch`, etc.) are not logged
- **Needed for**: Detecting command repetition patterns
- **Implementation**: Need to add action logging middleware to CLI command handler

### 2. **Amp Thread Integration** ✅ ACHIEVABLE
- **Opportunity**: Amp has built-in thread referencing via `read_thread` tool
- **Available**: 
  - Can reference threads by URL or ID: `@T-uuid-format` or full URL
  - Amp automatically fetches and extracts relevant context
  - SDK supports thread continuation: `continue: 'T-abc123'`
  - **Key insight**: Amp runs in current workspace, can access environment
- **Implementation approach**:
  - Devloop background daemon can capture `$AMP_THREAD_ID` from environment
  - When Amp calls devloop CLI, inject thread ID into action log
  - Log captures: what user asked → what agent did → what user changed manually
  - Create `.devloop/amp-thread-log.jsonl` mapping threads to agent activity
  - Pattern detector correlates: "in thread X, user manually did Y after agent failed"

### 3. **Pattern Detection System** ⚠️
- **Gap**: No automated analysis of patterns in logs
- **Existing data**: Raw telemetry and audit logs exist
- **Needed**: 
  - Frequency analysis (e.g., "user ran `bd ready` 4 times in 2 hours")
  - Time-series anomaly detection
  - Command correlation analysis
  - User behavior pattern matching

### 4. **Agent Insights Command** ⚠️
- **Gap**: No `/agent-insights` command or equivalent
- **Needed**: Expose pattern analysis results to users
- **Could integrate with**: Feedback system to surface suggestions

### 5. **Beads Integration for Auto-Issue Creation** ⚠️
- **Gap**: No mechanism to auto-create beads issues from discovered patterns
- **Needed**: 
  - Query beads for existing issues
  - Create new issues with `discovered-from` links
  - Auto-populate issue descriptions with analysis results

### 6. **Pattern Definition Schema** ⚠️
- **Gap**: No formalized patterns that trigger insights
- **Examples needed**:
  - "Repeated command within X time" → unclear automation visibility
  - "Dismissed suggestions" → messaging clarity issue
  - "Failed operations workaround" → feature gap
  - "Silent completions" → feedback visibility issue
  - "Frequent re-runs" → unclear state or UI issues
  - **[NEW]** "User manually fixed what agent produced" → agent output quality or messaging issue
  - **[NEW]** "User asked for same help multiple times across threads" → missing feature

## Data Flow for Self-Improvement Agent (With Amp Thread Integration)

```
Amp Thread + User Prompt
    ↓
CLI Commands (with injected thread context)
    ↓
[NEW] Action Logger
    ├─ cli-actions.jsonl (CLI commands)
    ├─ amp-thread-log.jsonl (Amp thread mapping)
    └─ session-context.jsonl (optional user feedback)
    ↓
Analysis Engine
    ├─→ Read: audit logs, telemetry, feedback, action logs, thread mappings
    ├─→ Correlate: what user asked in Amp → what agent did → what user changed manually
    ├─→ Cross-reference: "same question asked in threads A, B, C" → pattern
    ├─→ Analyze: patterns, anomalies, correlations
    ├─→ Store: analysis results
    ↓
Pattern Detector
    ├─→ Frequency analysis (command repetition)
    ├─→ Cross-thread analysis (repeated questions)
    ├─→ Manual workaround detection (user fixing agent output)
    ├─→ Match against pattern definitions
    ├─→ Calculate severity/impact/confidence
    ├─→ Generate recommendations
    ↓
Insights API
    ├─→ /agent-insights command
    ├─→ Feedback API integration
    ├─→ Thread context awareness
    ↓
Beads Integration
    ├─→ Auto-create issues
    ├─→ Link with discovered-from (including thread IDs)
    ├─→ Tag with analysis data + thread references
    └─→ Enable cross-thread pattern discovery
```

### Amp Thread Mapping Example

`.devloop/amp-thread-log.jsonl`:
```json
{
  "timestamp": "2025-12-12T10:23:45Z",
  "thread_id": "T-7f395a45-7fae-4983-8de0-d02e61d30183",
  "thread_url": "https://ampcode.com/threads/T-7f395a45-7fae-4983-8de0-d02e61d30183",
  "user_prompt": "Implement linter integration",
  "agent_actions": [
    {
      "action": "cli_command",
      "command": "devloop watch",
      "output": "Linter found 5 issues",
      "timestamp": "2025-12-12T10:24:00Z"
    }
  ],
  "user_manual_actions": [
    {
      "action": "manual_fix",
      "description": "Manually fixed formatting that linter suggested",
      "time_after_agent_action": "120s",
      "timestamp": "2025-12-12T10:26:00Z"
    }
  ],
  "insights": [
    {
      "pattern": "user_manual_fix_after_agent",
      "severity": "medium",
      "message": "User manually applied formatting fix instead of linter auto-applying it"
    }
  ]
}
```

Pattern Detector notices: "User fixed what linter suggested" → Issue: "Linter auto-fix not working" or "Linter output unclear"

## Amp Thread Integration (Technical Approach)

### How to Capture Thread Context

**Option A: Environment Variable (Simplest)**
```python
# In devloop CLI initialization
import os

amp_thread_id = os.environ.get('AMP_THREAD_ID')
amp_thread_url = os.environ.get('AMP_THREAD_URL')

# Log with every CLI command
action_logger.log_cli_action(
    command=sys.argv,
    thread_id=amp_thread_id,  # Injected by Amp or AGENTS.md hook
    timestamp=time.time()
)
```

**Problem**: Amp doesn't currently set this. Need to add to Amp integration docs or create AGENTS.md hook.

**Option B: Amp Hook / Post-Command Logging (Recommended)**
```bash
# In AGENTS.md or .agents/hooks/post-command
# When Amp executes devloop CLI, it calls post-command hook
export AMP_THREAD_ID="$THREAD_ID"
export AMP_THREAD_URL="$THREAD_URL"
devloop "$@"
```

**Option C: Read-Thread Tool Integration**
- Amp's `read_thread` tool can parse current thread context
- Could expose thread metadata to child processes
- Requires Amp SDK integration (lower priority)

### Implementation Steps (Phase 0)

1. **Create action logger** (`src/devloop/core/action_logger.py`)
   - Log all CLI commands with timestamp
   - Capture optional thread_id/thread_url
   - Store in `.devloop/cli-actions.jsonl`

2. **Add Amp thread mapper** (`src/devloop/core/amp_thread_mapper.py`)
   - Create `.devloop/amp-thread-log.jsonl`
   - Track: thread_id → agent_actions → user_manual_actions
   - Detect: which manual actions followed which agent actions

3. **Update AGENTS.md documentation**
   - Document how to pass thread context to devloop
   - Provide hook example for Amp users

4. **Add to CODING_RULES.md**
   - Developers understand thread context is captured
   - How patterns are used to improve UX

## Implementation Priority

### Phase 0 (Amp Thread Support - NEW!)
1. Create action logger with thread context support
2. Create Amp thread mapper
3. Document Amp integration in AGENTS.md

### Phase 1 (Foundation)
1. Add CLI action logging middleware
2. Define pattern schema (what patterns trigger insights)
3. Implement basic pattern detector (frequency analysis)
4. Build thread-aware pattern matching

### Phase 2 (Insights Surface)
5. Create `/agent-insights` command
6. Build analysis engine for log querying
7. Integrate with feedback system
8. Surface thread context in insights

### Phase 3 (Automation)
9. Implement Beads integration
10. Auto-create issues from patterns with thread references
11. Build anomaly detection (time-series analysis)
12. Enable cross-thread pattern discovery

## Files to Create/Modify

**New Files**:
- `src/devloop/core/action_logger.py` - CLI action logging
- `src/devloop/core/pattern_analyzer.py` - Pattern detection and analysis
- `src/devloop/cli/commands/insights.py` - `/agent-insights` CLI command
- `src/devloop/integrations/beads_integration.py` - Beads auto-issue creation

**Modify Existing**:
- `src/devloop/cli/main.py` - Add action logging middleware
- `src/devloop/core/feedback.py` - Integrate insights into feedback
- `src/devloop/core/performance.py` - Export analysis-friendly metrics

## Key Decisions Made

1. **Use existing log files**: Leverage telemetry.jsonl, agent-audit.log, feedback.jsonl
2. **Add new action log**: Separate `.devloop/cli-actions.jsonl` for CLI commands
3. **Pattern-driven**: Define specific patterns that trigger insights (not generic ML)
4. **Human-in-loop**: Surface insights, let users decide on action
5. **Beads integration**: Auto-create issues with discovered-from links for traceability

## Amp Integration Advantage

By capturing Amp thread context, we unlock powerful insights:

**Cross-Thread Pattern Detection**: 
- "Same question asked in 5 different threads" → Missing feature/documentation
- "User had to fix agent output in 3 threads" → Agent quality issue
- "Linter caught different errors in similar code across threads" → Config inconsistency

**User Intent Tracking**:
- Map Amp prompt → agent action → user correction
- Understand what users tried to do vs. what succeeded
- Identify silent failures (agent ran, but user ignored output)

**Data for Improvement**:
- Thread ID in auto-created beads issues enables historical analysis
- Can correlate: "this issue pattern started appearing in thread T-xxx"
- Support team can reference threads when investigating issues

## Success Metrics (from issue)

- ✓ Catch UX gaps before users abandon workflows
- ✓ Self-drive improvements to devloop's own UX
- ✓ Reduce support questions about agent behavior
- ✓ Enable data-driven decisions about CLI messaging
- ✓ **[NEW]** Cross-thread pattern detection (multiple users hitting same problem)
- ✓ **[NEW]** Traceable insights (linked to actual Amp threads for context)
