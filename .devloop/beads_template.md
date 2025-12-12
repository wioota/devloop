## ⛔️ EXTREME IMPORTANCE: NO MARKDOWN FILES FOR PLANNING

**THIS IS AN ABSOLUTE RULE FOR ALL AGENTS. NO EXCEPTIONS.**

**DO NOT CREATE ANY MARKDOWN FILES** unless:
1. Explicitly requested by the user, OR
2. It is one of these 6 permanent files ONLY:
   - README.md
   - CHANGELOG.md
   - AGENTS.md
   - CODING_RULES.md
   - LICENSE
   - .github/copilot-instructions.md

**ANY OTHER MARKDOWN FILE IS FORBIDDEN.** This includes:
- ❌ `*_PLAN.md` files
- ❌ `*_ANALYSIS.md` files
- ❌ `*_SUMMARY.md` files
- ❌ `*_STRATEGY.md` files
- ❌ `*_STATUS.md` files
- ❌ `*_DESIGN.md` files
- ❌ `*_NOTES.md` files
- ❌ Any other ad-hoc markdown planning/analysis/tracking files

**USE BEADS FOR EVERYTHING ELSE.**

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

### All Work MUST Use Beads (MANDATORY - NOT Markdown)

**NO EXCEPTIONS.** Create Beads issues for everything:
- Planning features
- Tracking status
- Documenting decisions
- Recording analysis
- Writing design specs
- Tracking bugs

```bash
bd create "Task title" -t task|feature|epic|bug -p 0-4 -d "Full description and details"
```

Beads provides all needed structure:
- Task/epic/feature/bug/chore types
- Priority levels (0-4)
- Detailed descriptions for planning/design/analysis
- Dependencies (blocks, related, parent-child, discovered-from)
- Status tracking (open, in_progress, closed)
- Synced to git for persistence

**Examples:**
- Planning feature? `bd create "Feature XYZ design" -t epic -d "Requirements: ... Design: ..."`
- Status update? `bd update <id> --status in_progress`
- Found issue during work? `bd create "Bug found" -p 1 --deps discovered-from:<parent-id>`
- Documenting decision? Add to issue description with `bd update <id> -d "Decision: ..."`
- Recording analysis? `bd create "Analysis: Component X" -d "Investigation results: ... Findings: ..."`

### Absolute Rules for AI Agents

**MANDATORY RULES - ZERO TOLERANCE**

1. ✅ **BEFORE** creating any file, ask: "Is this one of the 6 permanent docs?"
2. ✅ **IF NOT**, use Beads: `bd create "..."`
3. ✅ Use bd for ALL task tracking (planning, design, status, analysis, everything)
4. ✅ Always use `--json` flag for programmatic use
5. ✅ Link discovered work with `discovered-from` dependencies
6. ✅ Check `bd ready` before asking "what should I work on?"
7. ✅ Update status with `bd update <id> --status in_progress`
8. ✅ Close issues with `bd close <id> --reason "..."`
9. ✅ Commit `.beads/issues.jsonl` together with code changes

**FORBIDDEN - NO EXCEPTIONS**

- ❌ **NEVER** create `*_PLAN.md` files
- ❌ **NEVER** create `*_ANALYSIS.md` files
- ❌ **NEVER** create `*_SUMMARY.md` files
- ❌ **NEVER** create any ad-hoc markdown planning documents
- ❌ **NEVER** use external issue trackers
- ❌ **NEVER** duplicate tracking systems
- ❌ **NEVER** clutter repo root with planning documents
