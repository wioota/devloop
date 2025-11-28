# Installation Automation Plan

> **Goal:** Eliminate manual setup. The `dev-agents init` command and related tools should fully automate all onboarding and discipline enforcement.

---

## Current State

Today, users must manually:
1. Run `dev-agents init /path/to/project`
2. Configure Amp workspace
3. Register hooks
4. Set up slash commands
5. Inject system prompts
6. Remember the commit/push protocol

**This is too much.** It should be automatic.

---

## Desired State

When a user installs dev-agents:

```bash
dev-agents init /path/to/project
```

Everything should be automatically:
- ✅ Set up in the project
- ✅ Configured for Amp (if in Amp environment)
- ✅ Hooks registered
- ✅ Slash commands available
- ✅ Discipline enforced
- ✅ Ready to use

---

## Installation Automation Workflow

### Phase 1: Environment Detection

**During `dev-agents init`, detect:**

```python
def detect_environment():
    """Detect if running in Amp and what settings to apply."""
    
    # Check if in Amp environment
    in_amp = os.getenv("AMP_WORKSPACE") is not None
    amp_workspace_id = os.getenv("AMP_WORKSPACE_ID")
    amp_api_endpoint = os.getenv("AMP_API_ENDPOINT")
    
    # Check git configuration
    has_git = subprocess.run(["git", "status"], capture_output=True).returncode == 0
    
    # Check if already initialized
    has_claude_dir = Path(".dev-agents").exists()
    
    return {
        "in_amp": in_amp,
        "amp_workspace_id": amp_workspace_id,
        "amp_api_endpoint": amp_api_endpoint,
        "has_git": has_git,
        "has_claude_dir": has_claude_dir,
    }
```

### Phase 2: Core Setup

**Always perform (regardless of environment):**

```python
def setup_core(path: Path):
    """Set up core dev-agents infrastructure."""
    
    # 1. Create .dev-agents directory
    claude_dir = path / ".dev-agents"
    claude_dir.mkdir(exist_ok=True)
    
    # 2. Create AGENTS.md (copy from installation)
    agents_md = copy_project_file("AGENTS.md", path)
    
    # 3. Create CODING_RULES.md (copy from installation)
    coding_rules = copy_project_file("CODING_RULES.md", path)
    
    # 4. Create agents.json configuration
    create_default_config(claude_dir / "agents.json")
    
    # 5. Set up git hooks if git repository
    if has_git_repo(path):
        setup_git_hooks(path)
    
    # 6. Create .gitignore entries for .dev-agents
    setup_gitignore(path)
```

### Phase 3: Amp Integration (if applicable)

**If running in Amp environment:**

```python
def setup_amp_integration(path: Path, workspace_id: str, api_endpoint: str):
    """Automatically register with Amp."""
    
    # 1. Create .amp-workspace.json
    create_workspace_config(
        path,
        workspace_id=workspace_id,
        dev_agents_enabled=True,
        verification_script=".agents/verify-task-complete"
    )
    
    # 2. Register slash commands
    register_slash_commands(api_endpoint, [
        {
            "name": "agent-summary",
            "description": "Show recent agent findings",
            "command": "dev-agents summary recent"
        },
        {
            "name": "agent-status", 
            "description": "Show agent health",
            "command": "dev-agents status"
        }
    ])
    
    # 3. Register post-task hook
    register_hook(api_endpoint, {
        "type": "post_task",
        "script": ".agents/hooks/post-task",
        "description": "Verify commit/push discipline"
    })
    
    # 4. Create system prompt enhancement
    create_system_prompt_config(path, {
        "include_commit_discipline": True,
        "verification_script": ".agents/verify-task-complete"
    })
```

### Phase 4: Git Hooks Setup

**If git repository detected:**

```python
def setup_git_hooks(path: Path):
    """Set up git hooks for automatic verification."""
    
    hooks_dir = path / ".git" / "hooks"
    
    # 1. Create pre-commit hook
    create_hook(hooks_dir / "pre-commit", """
    #!/bin/bash
    # dev-agents pre-commit hook
    # Prevents commits with uncommitted changes
    
    if ! git diff-index --quiet --cached HEAD --; then
        echo "Pre-commit hook: Uncommitted changes detected"
        exit 1
    fi
    """)
    
    # 2. Create pre-push hook
    create_hook(hooks_dir / "pre-push", """
    #!/bin/bash
    # dev-agents pre-push hook
    # Ensure clean state before push
    
    .agents/verify-task-complete || exit 1
    """)
    
    # Make executable
    chmod_x(hooks_dir / "pre-commit")
    chmod_x(hooks_dir / "pre-push")
```

### Phase 5: Verification & Testing

**After setup, verify everything works:**

```python
def verify_installation(path: Path, in_amp: bool):
    """Verify installation is complete and working."""
    
    checks = []
    
    # Core files exist
    checks.append(check_file_exists(path / ".dev-agents" / "agents.json"))
    checks.append(check_file_exists(path / "AGENTS.md"))
    checks.append(check_file_exists(path / "CODING_RULES.md"))
    checks.append(check_file_executable(path / ".agents" / "verify-task-complete"))
    
    # Git setup
    if has_git_repo(path):
        checks.append(check_git_hooks_installed(path))
        checks.append(check_git_clean(path))
    
    # Amp setup (if applicable)
    if in_amp:
        checks.append(check_amp_workspace_config(path))
        checks.append(check_slash_commands_registered())
        checks.append(check_post_task_hook_registered())
    
    # Summary
    if all(checks):
        return "✅ Installation successful"
    else:
        return "❌ Installation incomplete - see errors above"
```

---

## Enhanced `dev-agents init` Command

New signature:

```python
@app.command()
def init(
    path: Path = typer.Argument(Path.cwd(), help="Project directory"),
    create_config: bool = typer.Option(True, help="Create default configuration"),
    auto_amp: bool = typer.Option(True, help="Auto-detect and configure Amp"),
    auto_git_hooks: bool = typer.Option(True, help="Set up git hooks"),
    interactive: bool = typer.Option(True, help="Interactive setup"),
):
    """
    Initialize dev-agents in a project.
    
    This command:
    - Sets up .dev-agents directory and configuration
    - Creates AGENTS.md and CODING_RULES.md 
    - Registers git hooks (if git repo)
    - Auto-configures Amp integration (if in Amp)
    - Registers slash commands and hooks
    - Verifies everything is working
    
    Everything is automatic - no manual setup needed.
    """
    console.print("[bold]Dev Agents Installation[/bold]")
    console.print("=" * 60)
    
    # Step 1: Detect environment
    console.print("\n[cyan]→[/cyan] Detecting environment...")
    env = detect_environment()
    
    if env["in_amp"]:
        console.print(f"  ✓ Amp workspace detected: {env['amp_workspace_id']}")
    if env["has_git"]:
        console.print("  ✓ Git repository detected")
    
    # Step 2: Setup core
    console.print("\n[cyan]→[/cyan] Setting up core infrastructure...")
    setup_core(path)
    console.print("  ✓ Created .dev-agents directory")
    console.print("  ✓ Created agents.json configuration")
    console.print("  ✓ Copied AGENTS.md and CODING_RULES.md")
    
    # Step 3: Setup git hooks
    if auto_git_hooks and env["has_git"]:
        console.print("\n[cyan]→[/cyan] Setting up git hooks...")
        setup_git_hooks(path)
        console.print("  ✓ Created pre-commit hook")
        console.print("  ✓ Created pre-push hook")
    
    # Step 4: Setup Amp integration
    if auto_amp and env["in_amp"]:
        console.print("\n[cyan]→[/cyan] Configuring Amp integration...")
        setup_amp_integration(
            path,
            env["amp_workspace_id"],
            env["amp_api_endpoint"]
        )
        console.print("  ✓ Registered slash commands")
        console.print("  ✓ Registered post-task hook")
        console.print("  ✓ Created system prompt config")
    
    # Step 5: Verify
    console.print("\n[cyan]→[/cyan] Verifying installation...")
    result = verify_installation(path, env["in_amp"])
    console.print(f"  {result}")
    
    # Success output
    console.print("\n[green bold]✓ Installation Complete![/green bold]")
    console.print("\nReady to use:")
    
    if env["in_amp"]:
        console.print("  • Amp slash commands: /agent-summary, /agent-status")
        console.print("  • Post-task verification: Automatic")
        console.print("  • Commit discipline: Enforced")
    
    console.print(f"  • Start watching: [cyan]dev-agents watch {path}[/cyan]")
    console.print(f"  • View config: [cyan]cat {path}/.dev-agents/agents.json[/cyan]")
    console.print("\nDocumentation:")
    console.print("  • AGENTS.md - System design and discipline")
    console.print("  • CODING_RULES.md - Development standards")
    console.print("  • AMP_ONBOARDING.md - Amp integration details")
```

---

## Implementation Details

### Files Created During Init

```
project-root/
├── AGENTS.md                          ← Copied from installation
├── CODING_RULES.md                    ← Copied from installation
├── .dev-agents/
│   ├── agents.json                    ← Default configuration
│   └── .gitignore                     ← Ignore logs, caches
├── .agents/
│   ├── verify-task-complete          ← Linked/copied from installation
│   └── hooks/
│       └── post-task                  ← Linked/copied from installation
├── .git/hooks/                        ← If git repo
│   ├── pre-commit                     ← Verify clean state
│   └── pre-push                       ← Run verification
├── .gitignore                         ← Updated with .dev-agents entries
├── .amp-workspace.json                ← If in Amp (auto-generated)
└── .system-prompt-config.json         ← If in Amp (auto-generated)
```

### Copied vs Linked Files

**Copied (independent copies):**
- AGENTS.md
- CODING_RULES.md
- .agents/verify-task-complete
- .agents/hooks/post-task

**Why:** Projects should have their own copies so they can be customized independently

### Environment Variables Used

```bash
# Amp detection
AMP_WORKSPACE          # Set when in Amp workspace
AMP_WORKSPACE_ID       # Workspace identifier
AMP_API_ENDPOINT       # Amp API for registrations
```

### Git Configuration Added

```bash
# In .git/config (auto-added)
[hooks "dev-agents"]
    enabled = true
    verify-on-push = true
    verify-on-commit = true
```

---

## AGENTS.md Enhancement

**Add new section to AGENTS.md:**

```markdown
## Automated Installation

### One-Command Setup

```bash
dev-agents init /path/to/project
```

This automatically:

1. **Environment Detection**
   - Detects if running in Amp
   - Detects if git repository exists
   - Checks existing configuration

2. **Core Setup**
   - Creates .dev-agents directory
   - Generates agents.json configuration
   - Copies AGENTS.md and CODING_RULES.md
   - Sets up .gitignore

3. **Git Integration** (if applicable)
   - Creates pre-commit hook for verification
   - Creates pre-push hook for verification
   - Registers commit discipline enforcement

4. **Amp Integration** (if in Amp)
   - Registers slash commands
   - Registers post-task hooks
   - Injects system prompt enhancements
   - Creates workspace configuration

5. **Verification**
   - Tests all setup
   - Shows status and next steps

### What Gets Installed

- ✅ Configuration files (agents.json)
- ✅ Documentation (AGENTS.md, CODING_RULES.md)
- ✅ Verification script (.agents/verify-task-complete)
- ✅ Git hooks (pre-commit, pre-push)
- ✅ Amp integration (slash commands, hooks, prompts)
- ✅ Commit discipline enforcement (automatic)

### Zero Manual Setup Required

After `dev-agents init`, everything is ready:
- Agents are configured and enabled
- Verification is automatic
- Commit discipline is enforced
- Amp integration is working (if in Amp)

Just start using: `dev-agents watch .`
```

---

## Implementation Phases

### Phase 1: Core Installation (Weeks 1-2)
- [ ] Implement environment detection
- [ ] Implement core setup (directory, files, config)
- [ ] Implement verification system
- [ ] Update `dev-agents init` command
- [ ] Test on multiple project types

### Phase 2: Git Integration (Weeks 2-3)
- [ ] Implement git hook creation
- [ ] Test hook execution
- [ ] Verify discipline enforcement
- [ ] Document git workflow

### Phase 3: Amp Integration (Weeks 3-4)
- [ ] Implement Amp environment detection
- [ ] Implement slash command registration
- [ ] Implement hook registration
- [ ] Implement system prompt injection
- [ ] Test in Amp environment

### Phase 4: Testing & Refinement (Weeks 4-5)
- [ ] Integration tests
- [ ] Edge case handling
- [ ] Error recovery
- [ ] Documentation
- [ ] Release

---

## Success Criteria

✅ User runs: `dev-agents init /path/to/project`
✅ No additional manual setup needed
✅ All features work out of the box
✅ Commit discipline automatically enforced
✅ Amp integration works seamlessly
✅ Clear success message with next steps
✅ Verification shows everything installed correctly

---

## Error Handling

**If environment detection fails:**
```bash
dev-agents init /path/to/project --skip-amp --skip-git-hooks
```

**If specific setup fails:**
- Continue with other setup
- Show which parts failed
- Provide recovery instructions
- Log errors to `.dev-agents/installation.log`

**If verification fails:**
- Show what failed
- Provide command to debug
- Suggest manual setup steps

---

## Documentation

Create:
- `INSTALLATION_GUIDE.md` — User-facing guide
- `INSTALLATION_AUTOMATION.md` — This document (architecture)
- Update `AGENTS.md` — Add "Automated Installation" section
- Update `README.md` — Simplify getting started

---

## Benefits

### For Users
- Single command setup
- No manual configuration
- Discipline automatically enforced
- Works in Amp out of the box

### For Developers
- Clear setup flow
- Fewer manual steps = fewer mistakes
- Discipline is system-enforced, not user-enforced
- Easy to onboard new team members

### For Maintenance
- Self-documenting setup
- Reproducible installations
- Easy to test
- Clear error messages

---

## Timeline

- **Total effort:** 3-4 weeks
- **Complexity:** Medium (environment detection + API calls)
- **Impact:** High (eliminates all manual setup)
- **Risk:** Low (graceful degradation for failures)

---

## Next Steps

1. Review and approve this plan
2. Create environment detection module
3. Create Amp API client for registrations
4. Implement enhanced `dev-agents init`
5. Add comprehensive tests
6. Document user-facing guides

