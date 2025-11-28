# Context Store Design

## Overview

The Context Store is the integration layer between background agents and coding agents (Claude Code). It provides intelligent filtering and progressive disclosure of agent findings based on relevance to the current development workflow.

## Architecture

### Core Principles

1. **Non-Intrusive**: Background findings should enhance, not interrupt, the coding flow
2. **Relevance-Driven**: Surface findings based on semantic relevance to current work
3. **Progressive Disclosure**: Show minimal info by default, details on demand
4. **LLM-Driven**: Leverage Claude's judgment to determine what's relevant when
5. **User Control**: Allow explicit preferences to override heuristics

### Three-Tier System

```
┌─────────────────────────────────────────────────────────┐
│                    Background Agents                    │
│              (linter, formatter, tests, etc.)           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
              ┌──────────────┐
              │ Relevance    │
              │ Scoring      │
              └──────┬───────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
   immediate.json  relevant.json  background.json
   [Show Now]     [Mention]      [On Request]
        │            │            │
        └────────────┼────────────┘
                     │
                     ▼
              ┌──────────────┐
              │ Claude Code  │
              │ (LLM decides)│
              └──────────────┘
```

### Directory Structure

```
.claude/
  └── context/
      ├── immediate.json      # Blocking issues, show immediately
      ├── relevant.json       # Mention at task completion
      ├── background.json     # Show only on explicit request
      ├── auto_fixed.json     # Log of silent fixes
      ├── index.json          # Quick summary for LLM
      └── metadata.json       # Timestamps, stats
```

## Finding Schema

### Core Finding Object

```json
{
  "id": "lint_auth_py_001",
  "agent": "linter",
  "timestamp": "2025-11-28T10:30:00Z",
  "file": "src/auth.py",
  "line": 42,
  "column": 10,

  "severity": "error|warning|info|style",
  "blocking": true,
  "category": "type_error|unused_import|formatting|security|test_failure",

  "message": "Missing type annotation for parameter 'user'",
  "detail": "Function 'authenticate' parameter 'user' has no type annotation",
  "suggestion": "Add type annotation: user: User",

  "auto_fixable": false,
  "fix_command": null,

  "scope_type": "current_file|related_files|project_wide",
  "caused_by_recent_change": true,
  "is_new": true,

  "relevance_score": 0.95,
  "disclosure_level": 0,
  "seen_by_user": false,

  "workflow_hints": {
    "show_during_coding": false,
    "show_at_commit": true,
    "auto_fix_silent": false
  },

  "context": {
    "related_files": ["src/auth_utils.py"],
    "related_findings": ["lint_auth_py_002"],
    "documentation_url": "https://..."
  }
}
```

## Relevance Scoring Algorithm

### Scoring Formula

```python
def compute_relevance(finding, user_context):
    """
    Returns 0.0 - 1.0 relevance score

    0.0 - 0.3: background (defer)
    0.4 - 0.7: relevant (mention at breakpoint)
    0.8 - 1.0: immediate (show now)
    """
    score = 0.0

    # File scope (max 0.5)
    if finding.file in user_context.currently_editing:
        score += 0.5
    elif finding.file in user_context.recently_modified:
        score += 0.3
    elif finding.file in user_context.related_files:
        score += 0.2

    # Severity (max 0.4)
    if finding.blocking:
        score += 0.4
    elif finding.severity == "error":
        score += 0.3
    elif finding.severity == "warning":
        score += 0.15
    elif finding.severity == "info":
        score += 0.05

    # Freshness (max 0.3)
    if finding.is_new and finding.caused_by_recent_change:
        score += 0.3
    elif finding.is_new:
        score += 0.15

    # User intent (max 0.5, can override)
    if user_context.explicit_request_matches(finding.category):
        score += 0.5

    # Workflow phase adjustments
    if user_context.phase == "pre_commit":
        score += 0.2
    elif user_context.in_active_coding:
        score -= 0.2  # Reduce interruptions

    return min(score, 1.0)
```

### Tier Assignment

```python
def assign_tier(relevance_score, finding):
    """Assign finding to immediate/relevant/background tier"""

    # Blockers always immediate
    if finding.blocking:
        return "immediate"

    # Score-based
    if relevance_score >= 0.8:
        return "immediate"
    elif relevance_score >= 0.4:
        return "relevant"
    else:
        # Auto-fixable style goes to background
        if finding.auto_fixable and finding.severity == "style":
            return "auto_fixed"  # Will be fixed silently
        return "background"
```

## LLM Integration Points

### 1. Tool Execution Hooks (Claude Code)

**PostToolUse Hook:**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{
          "type": "command",
          "command": "claude-agents context check --scope modified_files"
        }]
      }
    ]
  }
}
```

**LLM reads:** `.claude/context/index.json`

```json
{
  "last_updated": "2025-11-28T10:30:00Z",
  "check_now": {
    "count": 1,
    "severity_breakdown": {"error": 1},
    "files": ["src/auth.py"],
    "preview": "Type error in src/auth.py:42"
  },
  "mention_if_relevant": {
    "count": 5,
    "categories": {"warnings": 2, "style": 3},
    "summary": "2 warnings, 3 style issues"
  },
  "deferred": {
    "count": 15,
    "summary": "15 background items"
  }
}
```

### 2. Completion Signal Detection

**LLM recognizes signals:**
- "done", "finished", "that's it"
- "commit this", "ready to commit"
- "what's next?", "what else?"
- "looks good", "ship it"

**LLM action:**
```python
if user_signals_completion():
    check(".claude/context/relevant.json")
    if findings:
        summarize("Before committing: X items need attention")
        offer_to_fix()
```

### 3. Semantic Relevance Matching

**User Query → Context Check:**
```
"Why is the build failing?"     → immediate.json (errors/blockers)
"Any issues in auth.py?"        → filter all tiers for auth.py
"What's the test coverage?"     → test-runner context
"Should I commit?"              → relevant.json summary
```

### 4. Context Switch Detection

**Triggers:**
- File/branch switch (git operations)
- New topic in conversation
- Explicit context request

**LLM action:**
- Summarize deferred items from previous context
- Load context for new scope

## User Configuration Modes

### Config Schema

```json
{
  "contextStore": {
    "enabled": true,
    "mode": "balanced",
    "location": ".claude/context",

    "modes": {
      "flow": {
        "interrupt_threshold": "error_blocking_only",
        "auto_fix_style": true,
        "defer_warnings": true,
        "batch_interval": "10min"
      },
      "balanced": {
        "interrupt_threshold": "error",
        "auto_fix_style": false,
        "defer_warnings": false,
        "batch_interval": "5min"
      },
      "quality": {
        "interrupt_threshold": "warning",
        "auto_fix_style": false,
        "show_all_immediately": true,
        "batch_interval": "1min"
      }
    },

    "auto_fix": {
      "enabled": true,
      "categories": ["formatting", "import_order"],
      "max_per_file": 10,
      "require_confirmation": false
    }
  }
}
```

## Progressive Disclosure Levels

### Level 0: Silent Collection
- Findings written to context store
- No output to user
- Available on demand

### Level 1: Ambient Awareness
```
[3 deferred] ✓ file saved
```

### Level 2: Summary (at breakpoints)
```
Background findings:
  • 2 warnings in related files
  • 8 style issues (auto-fixable)

Type 'show findings' for details
```

### Level 3: Categorized List
```
Warnings (2):
  • auth_utils.py: unused import
  • config.py: deprecated API usage

Style Issues (8):
  • 5 files need formatting
  • 3 files have import order issues
```

### Level 4: Full Details
```
auth_utils.py:12
  ⚠️  Unused import 'datetime'
  Suggestion: Remove unused import
  [Auto-fix available]
```

## Agent Integration

### Agent Updates Required

Each agent (linter, formatter, test-runner) needs to:

1. **Write findings to context store** instead of just logging
2. **Include metadata** for relevance scoring
3. **Mark auto-fixable items**
4. **Track change attribution** (new vs pre-existing)

### Example Agent Integration

```python
from claude_agents.core.context_store import ContextStore

class LinterAgent(Agent):
    def __init__(self, ...):
        super().__init__(...)
        self.context_store = ContextStore()

    async def handle(self, event: Event) -> AgentResult:
        # Run linter
        issues = await self._run_linter(event.data["path"])

        # Write to context store
        for issue in issues:
            finding = {
                "id": f"lint_{file}_{line}",
                "agent": "linter",
                "file": event.data["path"],
                "line": issue.line,
                "severity": issue.severity,
                "message": issue.message,
                "auto_fixable": issue.fixable,
                "caused_by_recent_change": self._is_recent(event),
                # ... other metadata
            }
            await self.context_store.add_finding(finding)

        return AgentResult(...)
```

## Implementation Phases

### Phase 1: Core Infrastructure (This PR)
- [ ] ContextStore class
- [ ] Relevance scoring
- [ ] Tier assignment
- [ ] JSON file management
- [ ] Agent integration

### Phase 2: LLM Integration (Next PR)
- [ ] Claude Code hooks
- [ ] Index.json generation
- [ ] Integration guide for LLM
- [ ] Completion signal detection

### Phase 3: Progressive Disclosure (Future)
- [ ] CLI commands (show findings, etc.)
- [ ] Disclosure level tracking
- [ ] User interaction patterns

### Phase 4: Learning & Optimization (Roadmap)
- [ ] Flow state detection
- [ ] User behavior learning
- [ ] Adaptive relevance scoring
- [ ] Performance analytics

## Testing Strategy

### Unit Tests
- Relevance scoring with various inputs
- Tier assignment logic
- Finding serialization/deserialization
- Context store file operations

### Integration Tests
- Agent → Context Store → File system
- Multiple agents writing concurrently
- Context reading by external tools

### User Acceptance Testing
- Run on real development work
- Monitor interruption frequency
- Validate relevance accuracy
- Gather user feedback

## Success Metrics

### Developer Experience
- **Interruption Rate**: < 5% of file saves should trigger immediate context
- **Relevance Accuracy**: > 80% of surfaced findings should be acted upon
- **Time to Fix**: Reduced by showing issues proactively
- **False Positives**: < 10% of surfaced items should be ignored

### System Performance
- **Write Latency**: < 50ms to write finding
- **Read Latency**: < 10ms to read index
- **Storage**: < 1MB per 1000 findings
- **Concurrency**: Support 10+ agents writing simultaneously

## Security & Privacy

- All data stays local (no external transmission)
- Context files excluded from git (add to .gitignore)
- Sensitive file patterns excluded from context
- Option to disable context store entirely

## Future Enhancements

### Roadmap Items
1. **Flow State Detection**: Track user coding patterns to optimize interruptions
2. **Behavior Learning**: Adapt relevance scoring based on what user fixes vs ignores
3. **Team Context**: Share anonymized patterns across team
4. **AI-Powered Suggestions**: Use LLM to generate fix suggestions
5. **Cross-Project Learning**: Improve recommendations across projects
6. **IDE Integration**: Native IDE plugins for context visualization
7. **Voice/Chat Interface**: Natural language queries about context

## References

- [CLAUDE.md](../CLAUDE.md) - Overall system architecture
- [INTERACTION_MODEL.md](./INTERACTION_MODEL.md) - Agent interaction patterns
- [CODING_RULES.md](../CODING_RULES.md) - Development patterns
- [.claude/CLAUDE.md](../.claude/CLAUDE.md) - Claude Code integration

## Questions & Decisions

### Decisions Made
1. **Three-tier system**: Simple, clear separation of concerns
2. **Score-based assignment**: Deterministic, testable, tunable
3. **LLM-driven surfacing**: Leverage semantic understanding
4. **Progressive disclosure**: Minimize interruptions, maximize value
5. **Local-first**: All data stays on developer's machine

### Open Questions
1. ~~Should we track flow state in v1?~~ → No, roadmap item
2. How do we handle first-time user experience? → Progressive disclosure + onboarding
3. Should security findings always be immediate? → Yes, override mode settings
4. Do we need a focus mode? → Not in v1, can be added via mode config

### Future Considerations
- Multi-project context sharing
- Cloud backup (optional)
- Context analytics dashboard
- Custom relevance rules per project
