# Agent Interaction Model

## Overview

This document describes how background agents interact with developers, coding assistants (Claude Code, Amp), and each other. The interaction model is designed to be non-intrusive, context-aware, and collaborative.

## Interaction Layers

```
┌─────────────────────────────────────────────────────────┐
│                      Developer                          │
│                    (You - Human)                        │
└────────────┬────────────────────────────┬───────────────┘
             │                            │
             │ Direct                     │ Via Coding Agent
             │ Interaction                │ Interaction
             │                            │
┌────────────▼────────────┐   ┌──────────▼───────────────┐
│   Background Agents     │   │   Coding Agents          │
│   (Event-Driven)        │◄──┤   (Claude Code, Amp)     │
│                         │   │                          │
│ • Linter Agent          │   │ Interactive AI Coding    │
│ • Test Runner Agent     │   │ Assistant                │
│ • Security Scanner      │   │                          │
│ • Commit Assistant      │   └──────────┬───────────────┘
│ • Doc Sync Agent        │              │
│ • etc.                  │              │ Consumes
└────────┬────────────────┘              │ Context
         │                               │
         │ Inter-Agent                   │
         │ Communication         ┌───────▼────────────┐
         │                       │  Shared Context    │
         └──────────────────────►│  & Event Store     │
                                 │                    │
                                 │ • Event History    │
                                 │ • Agent Results    │
                                 │ • Code Analysis    │
                                 │ • Project State    │
                                 └────────────────────┘
```

## 1. Developer ↔ Background Agent Interaction

### Interaction Modes

#### A. Passive Notifications (Default)

Background agents work silently and only surface important findings.

**Notification Levels**:
```python
class NotificationLevel(Enum):
    SILENT = "silent"          # No notifications, log only
    ERRORS = "errors"          # Only errors and critical issues
    SUMMARY = "summary"        # Periodic summaries (default)
    VERBOSE = "verbose"        # All agent actions
```

**Example Flow**:
```
[Developer saves file.py]
  ↓
[Linter Agent runs] → Finds 2 issues
  ↓
[Notification appears]:
  📋 Linter found 2 issues in file.py
     • line 42: unused import 'sys'
     • line 87: undefined variable 'foo'

  [Auto-fix] [Ignore] [View Details]
```

**Notification Channels**:
1. **Desktop Notifications** - System notifications for high-priority items
2. **Terminal Status Line** - Subtle status in terminal prompt
3. **IDE Integration** - LSP-style inline annotations
4. **Log Files** - Detailed logs in `.claude/logs/`
5. **Dashboard** - Web-based dashboard (optional)

---

#### B. Interactive Prompts

For decisions that require developer input.

**Example: Security Scanner finds potential secret**
```
⚠️  Security Scanner Alert

Potential API key detected in src/config.py:15

  api_key = "sk-1234567890abcdef"
           ^^^^^^^^^^^^^^^^^^^^^^^

This looks like an API key. What would you like to do?

1. Add to .gitignore and move to environment variable
2. Add exception (not a real secret)
3. Ignore this file going forward
4. Show me more details

Choice [1-4]:
```

**Example: Test failures before commit**
```
❌ Test Runner - 3 tests failed

Cannot commit with failing tests. Options:

1. View failed tests
2. Skip tests and commit anyway (--no-verify)
3. Fix tests (cancel commit)
4. Commit only passing files

Choice [1-4]:
```

---

#### C. CLI Commands

Direct control over agents via CLI.

```bash
# Agent status and control
claude-agents status                    # Show all agent status
claude-agents enable linter             # Enable specific agent
claude-agents disable test-runner       # Disable specific agent
claude-agents restart formatter         # Restart agent

# Manual triggers
claude-agents run linter                # Run linter manually
claude-agents run linter --file src/    # Run on specific path
claude-agents run all                   # Run all agents

# Results and history
claude-agents results                   # Show recent results
claude-agents results linter            # Show linter results
claude-agents history                   # Event history
claude-agents history --type git:commit # Filter by event type

# Configuration
claude-agents config show               # Show current config
claude-agents config edit               # Edit configuration
claude-agents config validate           # Validate config

# Debugging
claude-agents logs                      # View logs
claude-agents logs --follow             # Tail logs
claude-agents events stream             # Stream events in real-time
claude-agents debug linter              # Debug specific agent
```

---

#### D. File-Based Communication

Agents can create files for developer review.

**Example: Refactoring Suggester Agent**
```
[Agent creates: .claude/suggestions/refactor-2024-01-15.md]

# Refactoring Suggestions

Generated: 2024-01-15 10:30 AM

## High Priority

### 1. Duplicate Code in auth.py and user.py
**Lines**: auth.py:45-67, user.py:123-145
**Suggestion**: Extract to shared `validate_user_input()` function
**Estimated effort**: 15 minutes
**Files to create**: src/utils/validation.py

[View Diff] [Apply] [Dismiss]

### 2. Complex Function: process_payment()
**File**: payments.py:234
**Complexity**: 15 (threshold: 10)
**Suggestion**: Break into smaller functions
**Estimated effort**: 30 minutes

[View Details] [Apply] [Dismiss]
```

---

## 2. Coding Agent ↔ Background Agent Interaction

### Integration with Claude Code & Amp

Background agents and coding agents complement each other:

**Background Agents**: Reactive, event-driven, automated checks
**Coding Agents**: Interactive, on-demand, complex reasoning

### A. Shared Context Store

Both systems read/write to a shared context store:

```
.claude/
├── context/
│   ├── current-task.json          # What you're working on
│   ├── recent-changes.json        # Files changed recently
│   ├── test-results.json          # Latest test results
│   ├── lint-results.json          # Latest lint results
│   ├── code-analysis.json         # Code complexity, dependencies
│   └── issues.json                # Known issues and TODOs
├── agents.json                    # Agent configuration
└── events.db                      # Event history
```

**Context Schema**:
```json
{
  "currentTask": {
    "description": "Implementing user authentication",
    "branch": "feature/auth",
    "filesInProgress": ["src/auth.py", "tests/test_auth.py"],
    "relatedFiles": ["src/user.py", "src/models.py"],
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "recentChanges": [
    {
      "file": "src/auth.py",
      "type": "modified",
      "timestamp": "2024-01-15T10:25:00Z",
      "linesChanged": 42
    }
  ],
  "testResults": {
    "lastRun": "2024-01-15T10:26:00Z",
    "passed": 145,
    "failed": 2,
    "failedTests": ["test_auth.py::test_invalid_token"],
    "coverage": 87.5
  },
  "lintIssues": [
    {
      "file": "src/auth.py",
      "line": 42,
      "severity": "warning",
      "message": "Line too long (92 > 88 characters)"
    }
  ]
}
```

### B. Background Agents Informing Coding Agents

**Use Case 1: Developer asks Claude Code for help**

```
Developer: "Why are my tests failing?"

Claude Code:
  1. Reads .claude/context/test-results.json
  2. Sees Test Runner Agent ran tests 2 min ago
  3. Sees 2 failures in test_auth.py
  4. Reads failure details from context

Claude Code Response:
  "I can see the Test Runner Agent found 2 failing tests:

   1. test_invalid_token - AssertionError at line 67
   2. test_expired_token - KeyError: 'exp' at line 89

   The issue appears to be in src/auth.py:42 where you're accessing
   token['exp'] without checking if the key exists. Let me fix that..."
```

**Use Case 2: Security Scanner finds issue**

```
[Security Scanner Agent detects hardcoded secret]
  ↓
[Writes to .claude/context/security-issues.json]
  ↓
[Developer asks Claude Code to make a change]
  ↓
[Claude Code reads context before making changes]
  ↓
Claude Code: "Before I make that change, I notice the Security Scanner
found a potential API key in config.py. Would you like me to move that
to an environment variable first?"
```

### C. Coding Agents Triggering Background Agents

**Use Case: Claude Code makes changes**

```python
# Claude Code writes files via its Write tool
# This triggers filesystem events

[Claude Code writes src/auth.py]
  ↓
[Filesystem Event: file:modified]
  ↓
[Background Agents triggered]:
  • Linter Agent → Runs ESLint/Ruff
  • Formatter Agent → Auto-formats if configured
  • Test Runner Agent → Runs related tests
  • Type Checker Agent → Checks types
  ↓
[Results written to context store]
  ↓
[Claude Code can read results before responding to user]
```

**Example Integration in Claude Code**:
```
Developer: "Add error handling to the login function"

Claude Code: [Makes changes to auth.py]
  ↓
  [Waits 2 seconds for background agents]
  ↓
  [Reads .claude/context/lint-results.json]
  ↓
Claude Code: "I've added error handling to the login function.
The Linter Agent just ran and found one minor issue - missing
type hint on line 45. Let me fix that too..."
  ↓
  [Makes additional fix]
  ↓
Claude Code: "Done! All linter checks passing. The Test Runner Agent
also confirmed that all 12 related tests still pass."
```

### D. Agent Coordination Protocol

**Protocol for Coding Agent <-> Background Agent interaction**:

```python
# When Claude Code is about to make changes
class CodingAgentProtocol:
    async def before_changes(self):
        """Pause background agents to avoid conflicts"""
        await agent_manager.pause_agents(
            agents=["linter", "formatter"],
            reason="coding-agent-active"
        )

    async def after_changes(self, files: List[str]):
        """Resume agents and wait for results"""
        await agent_manager.resume_agents()

        # Wait for agents to process changes
        results = await agent_manager.wait_for_results(
            files=files,
            agents=["linter", "test-runner"],
            timeout=10.0
        )

        return results

    async def get_context(self):
        """Get current context for decision making"""
        return await context_store.get_current_context()
```

### E. Agent Awareness in Claude Code

Claude Code can query agent status:

```python
# Example: Claude Code checks before committing
Developer: "Create a commit for these changes"

Claude Code internal:
  1. Check if Security Scanner is enabled
  2. Read recent security scan results
  3. Check if Test Runner found failures
  4. Read lint results

  If issues found:
    "I see the Security Scanner flagged a potential issue
    in config.py. Should I address that before committing?"

  Else:
    "All checks passing (linter, tests, security). Creating commit..."
```

---

## 3. Agent ↔ Agent Interaction

### Inter-Agent Communication Patterns

#### A. Event Broadcasting

Agents communicate via events:

```python
# Example: Linter Agent finds errors
class LinterAgent:
    async def handle(self, event: Event):
        results = await self.lint(event.payload.path)

        if results.has_errors:
            # Broadcast event that other agents can react to
            await event_bus.emit(Event(
                type="linter:errors-found",
                payload={
                    "file": event.payload.path,
                    "errors": results.errors,
                    "autoFixable": results.auto_fixable
                }
            ))

# Formatter Agent listens for linter errors
class FormatterAgent:
    triggers = ["linter:errors-found"]

    async def handle(self, event: Event):
        if event.payload.get("autoFixable"):
            # Auto-fix formatting issues
            await self.format(event.payload.file)
```

#### B. Agent Dependencies

Agents can depend on other agents:

```python
class CommitAssistantAgent:
    dependencies = ["linter", "test-runner", "security-scanner"]

    async def handle(self, event: Event):
        # Wait for dependency agents to complete
        lint_results = await self.wait_for("linter")
        test_results = await self.wait_for("test-runner")
        security_results = await self.wait_for("security-scanner")

        # Use results to generate commit message
        if test_results.failed > 0:
            return self.suggest_fix_tests_first()

        if security_results.has_issues:
            return self.suggest_fix_security_first()

        # Generate commit message
        return self.generate_commit_message(
            lint_results=lint_results,
            changes=event.payload.changes
        )
```

#### C. Agent Chains

Sequential agent execution:

```python
# Chain: file:save → linter → formatter → test-runner → commit-check

Agent Chain Definition:
{
  "name": "pre-commit-chain",
  "trigger": "git:pre-commit",
  "agents": [
    {
      "agent": "security-scanner",
      "required": true,  # Must pass to continue
      "blocking": true   # Wait for completion
    },
    {
      "agent": "linter",
      "required": true,
      "blocking": true
    },
    {
      "agent": "test-runner",
      "required": false,  # Can fail and continue
      "blocking": true
    },
    {
      "agent": "commit-assistant",
      "required": false,
      "blocking": false
    }
  ]
}
```

#### D. Shared State

Agents can read shared state:

```python
class SharedState:
    """Shared state accessible to all agents"""

    def __init__(self):
        self.current_branch = None
        self.files_changed = []
        self.test_status = None
        self.lint_status = None
        self.build_status = None

    async def update(self, key: str, value: Any):
        """Update shared state and notify subscribers"""
        setattr(self, key, value)
        await self.notify_subscribers(key, value)

# Agents can subscribe to state changes
class TestRunnerAgent:
    async def on_startup(self):
        await shared_state.subscribe(
            "files_changed",
            self.on_files_changed
        )

    async def on_files_changed(self, files: List[str]):
        # Run tests for changed files
        await self.run_tests_for(files)
```

#### E. Agent Coordination Patterns

**Pattern 1: Debounced Cascade**
```
file:save → [wait 500ms] → linter + formatter (parallel)
                         ↓
                    [wait for both]
                         ↓
                    test-runner
```

**Pattern 2: Priority-Based Execution**
```
git:pre-commit → [Critical Priority]: security-scanner
              ↓
              [High Priority]: linter, test-runner (parallel)
              ↓
              [Normal Priority]: doc-sync, commit-assistant
```

**Pattern 3: Conditional Execution**
```
file:save → linter
         ↓
    [if has auto-fixable issues]
         ↓
    formatter → linter (re-check)
```

**Pattern 4: Aggregated Results**
```
file:save → Multiple agents run in parallel
         ↓
    [Results aggregated]
         ↓
    Single notification to developer with all findings
```

---

## 4. Integration Scenarios

### Scenario 1: Developer Working with Claude Code

```
1. Developer asks Claude Code: "Add login function to auth.py"

2. Claude Code:
   - Pauses background agents
   - Writes code to auth.py
   - Writes tests to test_auth.py
   - Resumes background agents

3. Background Agents (triggered by file:save):
   - Linter Agent: Checks auth.py → 2 style issues found
   - Formatter Agent: Auto-fixes style issues
   - Test Runner Agent: Runs tests → All pass
   - Security Scanner: Checks for vulnerabilities → OK
   - Type Checker Agent: Validates types → 1 missing type hint

4. Results written to .claude/context/

5. Claude Code reads context and responds:
   "I've added the login function. The background agents found one
   missing type hint which I've fixed. All tests passing!"

6. Developer: "Great, commit it"

7. Claude Code:
   - Triggers git:pre-commit event
   - Commit Assistant Agent generates message
   - Claude Code presents commit message for approval
   - Creates commit after approval
```

### Scenario 2: Developer Working Alone (No Coding Agent)

```
1. Developer edits auth.py manually

2. Developer saves file

3. Background Agents:
   - Linter Agent: Finds 3 issues
   - Test Runner Agent: 2 tests fail

4. Desktop Notification appears:
   "⚠️  3 lint issues, 2 test failures in auth.py"
   [View] [Fix]

5. Developer clicks [View]

6. Terminal shows:
   ```
   Lint Issues:
   • Line 42: unused import
   • Line 67: undefined variable 'token'
   • Line 89: line too long

   Test Failures:
   • test_invalid_token: KeyError: 'exp'
   • test_expired_token: AssertionError

   [Auto-fix lint] [Run tests again] [Details]
   ```

7. Developer clicks [Auto-fix lint]

8. Linter Agent fixes 2/3 issues (can't fix undefined variable)

9. Developer manually fixes line 67

10. Test Runner Agent automatically re-runs tests → All pass

11. Notification: "✅ All checks passing"
```

### Scenario 3: Git Commit Workflow

```
1. Developer: git commit -m "Add authentication"

2. Git pre-commit hook triggers agents

3. Agent Chain Executes:

   [Security Scanner] → Checking for secrets...
   ✅ No security issues

   [Linter] → Checking code style...
   ✅ All files pass

   [Test Runner] → Running affected tests...
   ✅ 47 tests passed

   [Commit Assistant] → Analyzing changes...
   💡 Suggested commit message:

   "feat(auth): add user authentication system

   - Implement login/logout functionality
   - Add JWT token validation
   - Create authentication middleware
   - Add comprehensive test coverage

   Tests: 47 passed
   Files changed: 3"

   Use this message? [y/n/edit]:

4. Developer: y

5. Commit proceeds with generated message
```

### Scenario 4: Claude Code + Background Agents Collaboration

```
Developer: "The tests are failing, can you fix them?"

Claude Code:
1. Reads .claude/context/test-results.json
2. Sees Test Runner Agent's results
3. Identifies failing test: test_invalid_token

Claude Code: "I can see test_invalid_token is failing because
of a KeyError on line 67. The token['exp'] access assumes 'exp'
exists. Let me add validation..."

4. Claude Code writes fix to auth.py

5. Test Runner Agent (auto-triggered):
   - Runs test_invalid_token → ✅ Pass
   - Runs all auth tests → ✅ All pass

6. Claude Code reads updated results:

Claude Code: "Fixed! The test is now passing. The Test Runner
Agent confirmed all 12 auth tests pass."

Developer: "Great! Are there any other issues?"

Claude Code:
1. Reads all agent results from context
2. Checks linter, security, type checker

Claude Code: "Everything looks good! The Linter and Security
Scanner found no issues. Type checking passes. Ready to commit?"

Developer: "Yes"

Claude Code:
1. Triggers git:pre-commit event
2. Waits for Commit Assistant Agent
3. Presents generated commit message
4. Creates commit
```

---

## 5. Configuration for Interaction

### Developer Preferences

```json
{
  "interaction": {
    "notificationLevel": "summary",
    "notificationChannels": ["desktop", "terminal"],
    "autoFix": {
      "enabled": true,
      "confirmBefore": false,
      "agents": ["formatter", "import-organizer"]
    },
    "interruptive": {
      "enabled": true,
      "conditions": [
        "security-issue-found",
        "tests-failing-before-commit",
        "breaking-change-detected"
      ]
    },
    "quiet": {
      "hours": {
        "enabled": false,
        "start": "22:00",
        "end": "08:00"
      }
    }
  },
  "codingAgentIntegration": {
    "enabled": true,
    "shareContext": true,
    "contextUpdateInterval": 5,
    "pauseAgentsWhenCodingAgentActive": true,
    "waitForAgentsAfterChanges": true,
    "waitTimeout": 10
  },
  "interAgentCommunication": {
    "enabled": true,
    "allowChains": true,
    "allowDependencies": true,
    "maxChainDepth": 5
  }
}
```

### Notification Templates

```python
# Desktop Notification
{
  "title": "🔍 Linter Found Issues",
  "message": "3 issues in auth.py (2 auto-fixable)",
  "actions": ["Auto-fix", "View", "Dismiss"],
  "urgency": "normal"
}

# Terminal Status Line
{
  "format": "⚡ {agent_name}: {status} | {summary}",
  "example": "⚡ Linter: ✅ | 0 issues"
}

# IDE Inline
{
  "type": "diagnostic",
  "severity": "warning",
  "message": "Linter: Line too long (92 > 88)",
  "source": "claude-agents:linter",
  "quickFixes": ["Format line", "Disable rule"]
}
```

---

## 6. Communication Protocols

### A. Context Update Protocol

```python
class ContextUpdateProtocol:
    """Protocol for updating shared context"""

    async def publish_result(
        self,
        agent_name: str,
        result: AgentResult
    ):
        """Agent publishes its result to context store"""
        await context_store.update(
            f"agents/{agent_name}/latest",
            {
                "timestamp": time.time(),
                "result": result.dict(),
                "duration": result.duration
            }
        )

        # Notify subscribers
        await event_bus.emit(Event(
            type=f"agent:{agent_name}:completed",
            payload=result.dict()
        ))
```

### B. Agent Handoff Protocol

```python
class AgentHandoffProtocol:
    """Protocol for one agent requesting another agent's help"""

    async def request_analysis(
        self,
        requesting_agent: str,
        target_agent: str,
        context: Dict[str, Any]
    ) -> AgentResult:
        """Request another agent to analyze something"""

        # Create handoff event
        event = Event(
            type=f"agent:handoff:{target_agent}",
            payload={
                "requestedBy": requesting_agent,
                "context": context,
                "priority": "high"
            }
        )

        # Wait for result
        result = await event_bus.emit_and_wait(
            event,
            timeout=30.0
        )

        return result
```

### C. Coding Agent Query Protocol

```python
class CodingAgentQueryProtocol:
    """Protocol for coding agents to query background agent state"""

    async def get_recent_results(
        self,
        agents: List[str] = None,
        since: float = None
    ) -> Dict[str, AgentResult]:
        """Get recent results from background agents"""

        results = {}
        for agent_name in (agents or agent_manager.get_all_agents()):
            result = await context_store.get(
                f"agents/{agent_name}/latest"
            )

            if since and result["timestamp"] < since:
                continue

            results[agent_name] = result

        return results

    async def wait_for_completion(
        self,
        agents: List[str],
        timeout: float = 10.0
    ) -> Dict[str, AgentResult]:
        """Wait for specific agents to complete their current work"""

        async def wait_for_agent(agent_name: str):
            return await event_bus.wait_for(
                f"agent:{agent_name}:completed",
                timeout=timeout
            )

        results = await asyncio.gather(
            *[wait_for_agent(a) for a in agents],
            return_exceptions=True
        )

        return dict(zip(agents, results))
```

---

## Summary

The interaction model creates a collaborative ecosystem:

1. **Developer ↔ Agents**: Non-intrusive notifications, interactive prompts when needed, full CLI control

2. **Coding Agent ↔ Background Agents**: Shared context store, agents inform coding decisions, coordinated execution

3. **Agent ↔ Agent**: Event-based communication, dependencies and chains, shared state

**Key Principles**:
- ✅ Non-blocking: Agents work in background
- ✅ Context-aware: All systems share context
- ✅ Collaborative: Agents and coding assistants work together
- ✅ Transparent: Developer always in control
- ✅ Intelligent: Agents communicate and coordinate

This creates a powerful development environment where background agents handle routine checks, coding agents (Claude Code/Amp) handle complex tasks, and you focus on creative problem-solving.
