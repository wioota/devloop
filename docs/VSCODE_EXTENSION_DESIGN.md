# VSCode Extension Design

## Overview

The DevLoop VSCode extension provides real-time agent feedback, inline diagnostics, and quick fixes directly in the editor. It integrates with the existing DevLoop agent system through an LSP (Language Server Protocol) server.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VSCode Extension                          │
├─────────────────────────────────────────────────────────────┤
│  - Diagnostic Provider (findings → diagnostics)              │
│  - Code Action Provider (quick fixes)                        │
│  - Status Bar (agent activity)                               │
│  - Webview Panel (agent dashboard)                           │
│  - Feedback Commands                                         │
└─────────────────────┬───────────────────────────────────────┘
                      │ LSP Protocol
                      │ (JSON-RPC over stdio)
┌─────────────────────▼───────────────────────────────────────┐
│                  DevLoop LSP Server                          │
├─────────────────────────────────────────────────────────────┤
│  - Language Server (pygls)                                   │
│  - Finding → Diagnostic Mapper                               │
│  - Code Action Generator                                     │
│  - Event Bus Listener                                        │
│  - File Watcher Integration                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              Existing DevLoop System                         │
├─────────────────────────────────────────────────────────────┤
│  - Context Store (Findings)                                  │
│  - Event Bus                                                 │
│  - Agent Manager                                             │
│  - Auto-Fix System                                           │
│  - Feedback API                                              │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. LSP Server (`src/devloop/lsp/server.py`)

**Responsibilities:**
- Run as a language server using `pygls` library
- Listen to DevLoop event bus for agent findings
- Map Finding objects to LSP Diagnostics
- Provide code actions for auto-fixable findings
- Forward feedback from IDE to DevLoop feedback API

**Key Features:**
- **Real-time Updates**: Subscribe to `agent:*:completed` events
- **File-based Diagnostics**: Group findings by file for efficient updates
- **Incremental Sync**: Only send diagnostics for changed files
- **Finding Mapping**:
  ```python
  Finding → Diagnostic
  - file → uri
  - line/column → range
  - severity (error/warning/info/style) → DiagnosticSeverity
  - message → message
  - detail → relatedInformation
  - agent → source
  - code → category
  ```

**Protocol Methods:**
- `initialize`: Setup workspace and capabilities
- `textDocument/didOpen`: Register file for diagnostics
- `textDocument/didChange`: Handle file edits
- `textDocument/didSave`: Trigger agent re-scan
- `textDocument/codeAction`: Provide quick fixes
- `workspace/executeCommand`: Execute agent commands

### 2. VSCode Extension (`vscode-extension/`)

**Structure:**
```
vscode-extension/
├── package.json           # Extension manifest
├── src/
│   ├── extension.ts       # Extension entry point
│   ├── lspClient.ts       # LSP client setup
│   ├── diagnostics.ts     # Diagnostic provider
│   ├── codeActions.ts     # Code action provider
│   ├── statusBar.ts       # Status bar item
│   ├── agentPanel.ts      # Webview dashboard
│   └── feedback.ts        # Feedback commands
├── syntaxes/              # (Optional) syntax highlighting
└── README.md              # Extension documentation
```

**Features:**

#### a. Diagnostic Provider
- Displays findings as inline squiggles
- Color-coded by severity:
  - Red: Error (blocking issues)
  - Yellow: Warning (non-blocking issues)
  - Blue: Info (suggestions)
  - Gray: Style (formatting hints)
- Hover shows full finding detail and suggestion
- Problem panel shows all findings across files

#### b. Code Action Provider
- Lightbulb icon for auto-fixable findings
- Quick fix menu shows:
  - Primary action: Apply agent fix
  - Secondary actions: Dismiss, Provide feedback
- Supports multi-file fixes (related_files scope)

#### c. Status Bar
- Shows agent activity: `DevLoop: 3 agents running`
- Click to open agent dashboard
- Badge shows count of blocking issues

#### d. Agent Dashboard (Webview)
- Tree view of agents grouped by status:
  - Active (currently running)
  - Completed (recent)
  - Failed (errors)
- For each agent:
  - Status, duration, findings count
  - Expandable findings list
  - Quick actions (rerun, disable, configure)
- Summary statistics
- Feedback submission UI

#### e. Commands
- `devloop.openDashboard`: Open agent dashboard
- `devloop.applyFix`: Apply specific fix
- `devloop.applyAllFixes`: Apply all safe fixes
- `devloop.dismissFinding`: Dismiss a finding
- `devloop.provideFeedback`: Submit feedback for agent
- `devloop.pauseAgent`: Pause specific agent
- `devloop.resumeAgent`: Resume specific agent
- `devloop.showAgentConfig`: Open agent configuration

### 3. Finding → Diagnostic Mapping

**Severity Mapping:**
```python
Finding.severity → LSP DiagnosticSeverity
- Severity.ERROR → DiagnosticSeverity.Error
- Severity.WARNING → DiagnosticSeverity.Warning
- Severity.INFO → DiagnosticSeverity.Information
- Severity.STYLE → DiagnosticSeverity.Hint
```

**Scope Handling:**
- `current_file`: Show in current file only
- `related_files`: Show in related files with "Related to X" message
- `project_wide`: Show in Problems panel with "(Project)" prefix

**Progressive Disclosure:**
- `immediate` tier: Always shown
- `relevant` tier: Shown for currently open files
- `background` tier: Shown only in Problems panel (not inline)
- `auto_fixed` tier: Not shown (logged in Output panel)

### 4. Communication Protocol

**LSP Server Lifecycle:**
1. VSCode launches LSP server on activation: `python -m devloop.lsp.server`
2. LSP server connects to existing DevLoop daemon (or starts one)
3. LSP server subscribes to event bus
4. Findings propagate: Agent → Context Store → Event → LSP → VSCode

**Custom Protocol Extensions:**
```typescript
// Custom notification: findings updated
server.sendNotification("devloop/findingsUpdated", {
  uri: "file:///path/to/file.py",
  findings: [...],
})

// Custom command: apply fix
server.sendRequest("devloop/applyFix", {
  findingId: "linter-file.py-123",
})

// Custom notification: agent status
server.sendNotification("devloop/agentStatus", {
  agents: [
    { name: "linter", status: "running", duration: 1.5 },
  ],
})
```

### 5. Auto-Fix Integration

**Flow:**
1. User invokes "Quick Fix" on diagnostic
2. VSCode requests code actions from LSP server
3. LSP server returns actions based on `Finding.auto_fixable`
4. User selects action
5. LSP server calls `devloop.core.auto_fix.apply_fix(finding_id)`
6. Auto-fix system applies change with backup
7. LSP server sends `workspace/applyEdit` to VSCode
8. File updates in editor
9. New diagnostic scan triggered automatically

**Safety Levels:**
- Safe fixes: Applied immediately
- Medium-risk fixes: Confirmation prompt
- High-risk fixes: Requires explicit user action

### 6. Event Subscriptions

LSP server subscribes to these events:

```python
event_bus.subscribe("agent:*:completed", on_agent_completed)
event_bus.subscribe("agent:*:failed", on_agent_failed)
event_bus.subscribe("file:modified", on_file_modified)
event_bus.subscribe("finding:created", on_finding_created)
event_bus.subscribe("finding:resolved", on_finding_resolved)
```

## Implementation Plan

### Phase 1: LSP Server Core
- [ ] Set up pygls-based LSP server
- [ ] Implement Finding → Diagnostic mapping
- [ ] Connect to DevLoop event bus
- [ ] Basic file diagnostics (immediate tier only)

### Phase 2: VSCode Extension Basics
- [ ] Extension manifest and activation
- [ ] LSP client connection
- [ ] Diagnostic display
- [ ] Status bar integration

### Phase 3: Quick Fixes
- [ ] Code action provider in LSP server
- [ ] Code action provider in VSCode
- [ ] Auto-fix integration
- [ ] Undo/rollback support

### Phase 4: Agent Dashboard
- [ ] Webview panel structure
- [ ] Agent status display
- [ ] Finding explorer
- [ ] Feedback submission UI

### Phase 5: Advanced Features
- [ ] Progressive disclosure (all tiers)
- [ ] Multi-file fixes
- [ ] Agent configuration UI
- [ ] Performance optimizations

## Configuration

**VSCode Settings:**
```json
{
  "devloop.enabled": true,
  "devloop.autoFix.enabled": true,
  "devloop.autoFix.safetyLevel": "safe_only",
  "devloop.diagnostics.showBackgroundFindings": false,
  "devloop.statusBar.enabled": true,
  "devloop.agents.linter.enabled": true,
  "devloop.agents.formatter.enabled": true
}
```

## Testing Strategy

1. **LSP Server Tests** (`tests/lsp/`)
   - Finding mapping accuracy
   - Event handling
   - Code action generation
   - Multi-file updates

2. **Extension Tests** (`vscode-extension/src/test/`)
   - Diagnostic display
   - Code action invocation
   - Command execution
   - Webview rendering

3. **Integration Tests**
   - End-to-end finding propagation
   - Auto-fix application
   - Feedback submission
   - Multi-agent scenarios

## Security Considerations

1. **Workspace Trust**: Only activate in trusted workspaces
2. **Command Validation**: Validate all commands before execution
3. **File Access**: Respect VSCode workspace boundaries
4. **Auto-Fix Safety**: Require explicit opt-in for auto-fixes
5. **Feedback Privacy**: Don't send code snippets in feedback (only metadata)

## Performance Optimizations

1. **Incremental Updates**: Only send changed diagnostics
2. **Debouncing**: Batch rapid finding updates (500ms debounce)
3. **File Filtering**: Only process workspace files
4. **Memory Management**: Auto-trim old findings (keep last 1000)
5. **Lazy Loading**: Load agent dashboard only when opened

## Future Enhancements

1. **Inline Annotations**: Show agent suggestions as inline hints
2. **Code Lens**: Show "Run Agent" actions above functions/classes
3. **Test Coverage Overlay**: Highlight untested code
4. **Performance Metrics**: Show agent execution times in editor
5. **Multi-Root Workspace**: Support multiple DevLoop projects
6. **Remote Development**: Support SSH/container development
7. **Collaborative Findings**: Share findings across team (opt-in)

## References

- [LSP Specification](https://microsoft.github.io/language-server-protocol/)
- [pygls Documentation](https://pygls.readthedocs.io/)
- [VSCode Extension API](https://code.visualstudio.com/api)
- [VSCode LSP Client](https://code.visualstudio.com/api/language-extensions/language-server-extension-guide)
