# Installation Automation Plan - Summary

> **Shift the burden from the user to the tool.**

---

## Problem Statement

Today, ensuring commit/push discipline requires:
1. User manually runs `dev-agents init`
2. User reads AGENTS.md and CODING_RULES.md
3. User configures Amp workspace (if in Amp)
4. User registers hooks
5. User registers slash commands
6. User injects system prompts
7. User remembers the protocol

**This is too much.** The tool should handle it.

---

## Solution: Fully Automated Installation

**Single command:**
```bash
dev-agents init /path/to/project
```

**Automatically handles:**
- ✅ Environment detection (Amp, git, existing setup)
- ✅ Core setup (.claude dir, agents.json, docs)
- ✅ Git hooks (pre-commit, pre-push)
- ✅ Amp registration (slash commands, hooks, prompts)
- ✅ Verification (test everything works)

**Result:** Production-ready system with discipline enforced

---

## Key Components

### 1. Environment Detection

```python
# Detects:
- Is running in Amp? → AMP_WORKSPACE env var
- Git repository? → .git exists
- Already initialized? → .claude exists
```

**Impact:** Decide what to install without user input

### 2. Core Setup

**Files created:**
- `.claude/agents.json` — Agent configuration
- `AGENTS.md` — System design (copied)
- `CODING_RULES.md` — Development rules (copied)
- `.agents/verify-task-complete` — Verification script (copied)
- `.agents/hooks/post-task` — Amp hook (copied)
- `.gitignore` — Updated with .claude entries

**Result:** Everything needed to run agents is in place

### 3. Git Integration

**Hooks created:**
- `.git/hooks/pre-commit` — Verify clean state before commit
- `.git/hooks/pre-push` — Run verification before push

**Impact:** Discipline enforced at git level, not just in CLI

### 4. Amp Integration

**If in Amp workspace, automatically:**
- Register `/agent-summary` slash command
- Register `/agent-status` slash command
- Register `.agents/hooks/post-task` as post-task hook
- Create `.amp-workspace.json` configuration
- Inject system prompt enhancements

**Impact:** Everything works out of the box in Amp

### 5. Verification

**After setup, verify:**
- All files exist
- Scripts are executable
- Git hooks are in place
- Amp configuration is valid
- System is ready to use

**Result:** User gets clear success/failure message

---

## User Experience

### Before (Manual)

```bash
$ dev-agents init /path/to/project
✓ Created: /path/to/project/.claude

Next steps:
  1. Review/edit: /path/to/project/.claude/agents.json
  2. Run: dev-agents watch /path/to/project
  3. Read: AGENTS.md
  4. Read: CODING_RULES.md
  5. Configure Amp (if in Amp)
  6. Register slash commands
  7. Register hooks
  8. Inject system prompts
  9. Set up git hooks
  ...
```

### After (Fully Automated)

```bash
$ dev-agents init /path/to/project

Dev Agents Installation
============================================================

→ Detecting environment...
  ✓ Amp workspace detected: workspace-123
  ✓ Git repository detected

→ Setting up core infrastructure...
  ✓ Created .claude directory
  ✓ Created agents.json configuration
  ✓ Copied AGENTS.md and CODING_RULES.md

→ Setting up git hooks...
  ✓ Created pre-commit hook
  ✓ Created pre-push hook

→ Configuring Amp integration...
  ✓ Registered slash commands
  ✓ Registered post-task hook
  ✓ Created system prompt config

→ Verifying installation...
  ✅ Installation successful

✓ Installation Complete!

Ready to use:
  • Amp slash commands: /agent-summary, /agent-status
  • Post-task verification: Automatic
  • Commit discipline: Enforced
  • Start watching: dev-agents watch /path/to/project
  • View config: cat /path/to/project/.claude/agents.json

Documentation:
  • AGENTS.md - System design and discipline
  • CODING_RULES.md - Development standards
  • AMP_ONBOARDING.md - Amp integration details
```

---

## Architecture

### Enhanced `dev-agents init` Command

```python
@app.command()
def init(
    path: Path = typer.Argument(Path.cwd()),
    create_config: bool = typer.Option(True),
    auto_amp: bool = typer.Option(True),          # New
    auto_git_hooks: bool = typer.Option(True),    # New
    interactive: bool = typer.Option(True),       # New
    verbose: bool = typer.Option(False),          # New
):
    """Initialize dev-agents with full automation."""
    # See INSTALLATION_AUTOMATION.md for details
```

### Workflow

```
dev-agents init
    ↓
detect_environment()
    ├─ in_amp?
    ├─ has_git?
    └─ has_claude_dir?
    ↓
setup_core(path)
    ├─ create .claude
    ├─ copy AGENTS.md, CODING_RULES.md
    ├─ generate agents.json
    └─ update .gitignore
    ↓
setup_git_hooks(path) [if has_git]
    ├─ create pre-commit
    └─ create pre-push
    ↓
setup_amp_integration(path) [if in_amp]
    ├─ register slash commands
    ├─ register hooks
    └─ inject system prompts
    ↓
verify_installation(path)
    ├─ test all files exist
    ├─ test scripts executable
    ├─ test git hooks work
    ├─ test Amp config valid
    └─ show status
    ↓
Success!
```

---

## Implementation Phases

### Phase 1: Core Installation (Week 1-2)
- Environment detection module
- Core setup function
- Verification system
- Enhanced init command
- Basic tests

### Phase 2: Git Integration (Week 2-3)
- Git hook creation
- Hook testing
- Verification in git workflow
- Documentation

### Phase 3: Amp Integration (Week 3-4)
- Amp environment detection
- Slash command registration API
- Hook registration API
- System prompt injection
- Amp testing

### Phase 4: Polish & Testing (Week 4-5)
- Integration tests
- Error handling
- Edge cases
- User documentation
- Release

---

## Success Criteria

When done, a user should be able to:

1. **Install dev-agents**
   ```bash
   poetry install
   ```

2. **Initialize in a project**
   ```bash
   dev-agents init /path/to/project
   ```

3. **Start using**
   ```bash
   cd /path/to/project
   dev-agents watch .
   ```

4. **Discipline enforced automatically**
   - Git hooks prevent non-compliant commits
   - Amp post-task hook verifies completion
   - Verification script shows status
   - All checks pass without user intervention

---

## Files Involved

### Modified
- `src/dev_agents/cli/main.py` — Enhanced init command
- `AGENTS.md` — New "Automated Installation" section
- `README.md` — Updated quick start

### New
- `INSTALLATION_AUTOMATION.md` — Complete architecture
- `src/dev_agents/core/installation.py` — Installation logic
- `src/dev_agents/core/amp_api.py` — Amp API client
- `tests/integration/test_installation.py` — Integration tests

### Reference (provided to user)
- `AMP_ONBOARDING.md` — Manual setup guide (backup)
- `.amp-config-example.json` — Configuration reference
- `.agents/hooks/post-task` — Hook script

---

## Key Design Decisions

### 1. Copy vs Link
Files are **copied** into projects, not linked. This allows:
- Projects to customize independently
- Offline operation
- Version independence

### 2. Graceful Degradation
If part of setup fails:
- Continue with other setup
- Show which parts failed
- Provide recovery instructions

### 3. Opt-Out Available
Advanced users can skip parts:
```bash
dev-agents init --skip-amp --skip-git-hooks
```

### 4. Non-Interactive Mode
For CI/CD and scripting:
```bash
dev-agents init --non-interactive
```

---

## Documentation Updates

### For Users
- Update README.md quick start
- Create INSTALLATION_GUIDE.md (user-facing)
- Keep AMP_ONBOARDING.md (reference)

### For Developers
- INSTALLATION_AUTOMATION.md (architecture)
- Code comments and docstrings
- Integration test examples

### For Amp Integration
- .amp-config-example.json (reference)
- System prompt templates (in init code)

---

## Timeline & Effort

| Phase | Duration | Effort | Risk |
|-------|----------|--------|------|
| Phase 1 (Core) | 1-2 weeks | Medium | Low |
| Phase 2 (Git) | 1 week | Low | Low |
| Phase 3 (Amp) | 1-2 weeks | Medium | Medium |
| Phase 4 (Polish) | 1 week | Low | Low |
| **Total** | **3-4 weeks** | **Medium** | **Low** |

---

## Benefits

### For Users
- Single command setup
- Zero manual configuration
- Discipline automatically enforced
- Works everywhere (local, Amp, CI/CD)

### For Teams
- Consistent setup across projects
- Easy onboarding for new members
- Clear discipline enforcement
- Audit trail in git

### For Maintenance
- Fewer support questions
- Self-documenting setup
- Easy to test
- Clear error messages

---

## Next Steps

1. **Approval** — Review this plan
2. **Start Phase 1** — Begin core installation module
3. **Design Review** — Review environment detection logic
4. **Implementation** — Build and test
5. **Documentation** — Write user guides
6. **Testing** — Integration testing
7. **Release** — Announce and document

---

**Goal: Make the tool work for the user, not the user work for the tool.**

