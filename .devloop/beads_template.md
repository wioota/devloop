## Task Management with Beads

**All work must be tracked in Beads, NOT in markdown files.**

Beads provides:
- ✅ Persistent issue tracking synced via git
- ✅ Dependency tracking (blocks, related, parent-child, discovered-from)
- ✅ Ready work detection (unblocked issues only)
- ✅ Long-term memory across sessions
- ✅ Multi-agent coordination without conflicts

### Quick Start

**Check for ready work:**
```bash
bd ready --json
```

**Create new issues:**
```bash
bd create "Issue title" -t bug|feature|task -p 0-4 --json
bd create "Issue title" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**
```bash
bd update bd-42 --status in_progress --json
bd update bd-42 --priority 1 --json
```

**Complete work:**
```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Start of session:**
   ```bash
   bd ready              # See what's ready to work on
   bd show <issue-id>    # Review issue details
   ```

2. **During work:**
   ```bash
   bd update <id> --status in_progress   # Claim the issue
   bd create "Bug found" -p 1             # File discovered issues
   bd dep add <new-id> <parent-id> --type discovered-from
   ```

3. **End of session (MANDATORY):**
   ```bash
   bd close <id> --reason "Implemented in PR #42"
   bd update <other-id> --status in_progress  # Update ongoing work
   git add .beads/                             # Commit beads changes
   git commit -m "Work session update"
   git push origin main
   ```

### All Work MUST Use Beads (NOT Markdown)

**CRITICAL**: Do NOT create ANY markdown files for planning, tracking, or status. Everything goes in Beads.

**INSTEAD**: Create Beads issues for all work:
```bash
bd create "Task title" -t task|feature|epic|bug -p 0-4 -d "Full description and details"
```

Beads provides all needed structure:
- Task/epic/feature/bug/chore types
- Priority levels (0-4)
- Descriptions for details and planning
- Dependencies (blocks, related, parent-child, discovered-from)
- Status tracking (open, in_progress, closed)
- Synced to git for persistence

**Examples:**
- Planning feature? `bd create "Feature XYZ design" -t epic -d "Requirements: ... Design: ..."`
- Status update? `bd update <id> --status in_progress`
- Found issue during work? `bd create "Bug found" -p 1 --deps discovered-from:<parent-id>`
- Documenting decision? Add to issue description with `bd update <id> -d "Decision: ..."`

### Important Rules

- ✅ Use bd for ALL task tracking (MANDATORY - planning, design, status, everything)
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ✅ Put all planning/design in issue descriptions via `bd create`
- ✅ Update status with `bd update <id> --status in_progress`
- ❌ Do NOT create ANY markdown files for planning, tracking, status, or design
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems
- ❌ Do NOT clutter repo root with any planning documents
