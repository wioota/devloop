# DevLoop Development Workflow Template

**Note**: This project uses [bd (beads)](https://github.com/wioota/devloop) for issue tracking and devloop for development automation.

## ⚠️ IMPORTANT: Task Management with Beads

**Use Beads (`bd`) instead of markdown for all task management.** Beads provides proper dependency tracking, ready work detection, and long-term memory for agents.

**FORBIDDEN:** Do NOT create markdown task files (.md files for TODO lists, plans, checklists, etc). All work must be tracked in Beads.

Quick reference:
- `bd create "Task description" -p 1` - Create new issue
- `bd ready` - See what's ready to work on
- `bd update <id> --status in_progress` - Update status
- `bd close <id>` - Complete an issue
- See `.beads/issues.jsonl` in git for synced state

Run `bd quickstart` for interactive tutorial.

## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Auto-syncs to JSONL for version control
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

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

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`
6. **Commit together**: Always commit the `.beads/issues.jsonl` file together with the code changes so issue state stays in sync with code state

### Auto-Sync

bd automatically syncs with git:
- Exports to `.beads/issues.jsonl` after changes (5s debounce)
- Imports from JSONL when newer (e.g., after `git pull`)
- No manual export/import needed!

### ⛔️ EXTREME IMPORTANCE: NO MARKDOWN FILES FOR PLANNING

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

### Managing AI-Generated Planning Documents

**CRITICAL**: This project **completely prohibits** ephemeral planning markdown documents. All work uses Beads exclusively.

#### Permanent Documentation (Root Level ONLY - 6 Files)
Keep ONLY these 6 essential files in repository root:
- **README.md** - Project overview, quick start, links to docs
- **CHANGELOG.md** - Release notes and version history
- **AGENTS.md** - Architecture and development guidelines (this file)
- **CODING_RULES.md** - Development standards
- **LICENSE** - License file
- **.github/copilot-instructions.md** - GitHub Copilot instructions

All other documentation must be in the codebase or committed later as permanent docs.

#### All Work MUST Use Beads (MANDATORY - NOT Markdown)

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

#### Directory Structure (Strictly Enforced)
```
project-root/
├── README.md                    # ONLY permanent doc in root
├── CHANGELOG.md                 # ONLY permanent doc in root
├── AGENTS.md                    # ONLY permanent doc in root
├── CODING_RULES.md              # ONLY permanent doc in root
├── LICENSE                      # ONLY permanent doc in root
├── .github/
│   └── copilot-instructions.md  # ONLY permanent doc here
├── .beads/
│   └── issues.jsonl             # ALL PLANNING/TRACKING GOES HERE (single source of truth)
└── src/
```

**NO OTHER .md FILES IN ROOT.** No `*_PLAN.md`, `*_ANALYSIS.md`, `*_NOTES.md`, etc.

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

---

## Development Discipline

### Task Management with Beads (REQUIRED)

**All work must be tracked in Beads, NOT in markdown files.**

Beads provides:
- ✅ Persistent issue tracking synced via git
- ✅ Dependency tracking (blocks, related, parent-child, discovered-from)
- ✅ Ready work detection (unblocked issues only)
- ✅ Long-term memory across sessions
- ✅ Multi-agent coordination without conflicts

**Agent Workflow:**

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

**DO NOT:**
- ❌ Create `.md` files for task tracking
- ❌ Use markdown headers for planning
- ❌ Leave issues without status updates
- ❌ Forget to push `.beads/issues.jsonl` at session end

**Benefits:**
- Agents can find their next task immediately with `bd ready`
- Dependencies prevent duplicate work
- Full history and traceability
- Works across branches and machines

### Commit & Push After Every Task

**MANDATORY:** Every completed task must end with `git add`, `git commit`, and `git push origin main`.

This is **automatically enforced** by:
1. Git hooks (pre-commit, pre-push)
2. Amp post-task verification hook (if using Amp)
3. `.agents/verify-task-complete` script (if present)

---

## Secrets Management & Token Security

DevLoop provides comprehensive token security features to prevent credential exposure.

**Never Do:**
- ❌ Commit API keys, tokens, or credentials to version control
- ❌ Pass tokens as command-line arguments (visible in process lists)
- ❌ Hardcode tokens in code or configuration files
- ❌ Log full tokens or include them in error messages
- ❌ Store tokens in shell history

**Always Do:**
- ✅ Use environment variables for all tokens (`GITHUB_TOKEN`, `PYPI_TOKEN`, etc.)
- ✅ Enable token expiry and rotation (30-90 days recommended)
- ✅ Use read-only or project-scoped tokens when possible
- ✅ Scan commits for accidentally leaked secrets before pushing
- ✅ Use CI/CD secrets managers (GitHub Secrets, GitLab CI/CD Variables)

**DevLoop Token Security Features:**

```python
from devloop.security import get_github_token, sanitize_log, sanitize_command

# Get token from environment (never hardcode)
token = get_github_token()

if not token:
    print("Set GITHUB_TOKEN environment variable")
    exit(1)

# Check expiry
if token.is_expired():
    print("Token has expired, please rotate")
    exit(1)

if token.expires_soon(days=7):
    print("⚠️  Token expires soon, consider rotating")

# Sanitize logs (automatic token hiding)
log_msg = f"Authenticating with {token.value}"
safe_msg = sanitize_log(log_msg)  # "Authenticating with gh****"
logger.info(safe_msg)

# Sanitize commands (hide tokens in process list)
cmd = ["curl", "--token", token.value, "api.github.com"]
safe_cmd = sanitize_command(cmd)  # ["curl", "--token", "****", "api.github.com"]
```

**Token Validation:**

DevLoop automatically validates tokens and warns about security issues:
- Detects placeholder values ("changeme", "token", "password")
- Validates token format for GitHub, GitLab, PyPI
- Warns when tokens are passed as command arguments
- Checks token expiry dates

**For more details:** See your project's security documentation or [DevLoop Token Security Guide](https://github.com/wioota/devloop#token-security).

---

## DevLoop CLI Commands Reference

**IMPORTANT FOR AGENTS**: Always use these commands instead of manual operations. The CLI commands handle all validation, cleanup, and state management automatically.

### Core Workflow Commands

#### Project Initialization & Management
```bash
# Initialize devloop in a project (interactive setup)
devloop init /path/to/project

# Start watching for file changes and running agents
devloop watch .

# Show configuration and agent status
devloop status

# Show operational health status
devloop health

# Stop the background daemon
devloop stop
```

#### Task Verification & Integration
```bash
# Run code quality verification (Claude Code post-task hook equivalent)
devloop verify-work

# Extract findings and create Beads issues
devloop extract-findings-cmd
```

#### Daemon Management
```bash
# Check daemon health and status
devloop daemon-status

# Update git hooks from latest templates
devloop update-hooks
```

### Release Management Commands

**REQUIRED**: Use these for all releases. Do NOT do manual version bumping or tagging.

```bash
# Check if ready to release (validates all preconditions)
devloop release check <version>

# Publish a release (full automated workflow)
devloop release publish <version>

# Dry-run to see what would happen
devloop release publish <version> --dry-run

# Specify explicit providers (if auto-detect fails)
devloop release publish <version> --ci github --registry pypi
```

### Agent Management Commands

#### Custom Agents
```bash
# Create a custom pattern matcher agent
devloop custom create my_agent pattern_matcher \
  --description "Find patterns" \
  --triggers file:created,file:modified

# List custom agents
devloop custom list

# Delete a custom agent
devloop custom delete <agent-id>
```

#### Feedback & Performance
```bash
# View summaries of findings
devloop summary

# View summaries for specific scope
devloop summary recent   # Last 24 hours
devloop summary today    # Today only

# Filter by agent and severity
devloop summary --agent linter --severity error

# Submit feedback on agent performance
devloop feedback submit <agent-name> rating <1-5>

# View performance metrics
devloop metrics summary
```

#### System Information
```bash
# Show version information
devloop version

# Verify external tool dependencies
devloop tools

# View telemetry and value tracking
devloop telemetry
```

### Amp Integration Commands

```bash
# Show current agent status for Amp
devloop amp-status

# Show agent findings for Amp display
devloop amp-findings

# Show context store index for Amp
devloop amp-context
```

### Command Pattern for Agents

**For AI agents working on this codebase:**

1. **Always use `devloop` commands**, never manual shell operations
2. **For releases**: Always run `devloop release check` before `devloop release publish`
3. **For verification**: Use `devloop verify-work` instead of manually running tests/checks
4. **For feedback**: Use `devloop feedback` commands to record observations
5. **For task integration**: Use `devloop extract-findings-cmd` to create Beads issues

**Why use commands instead of manual operations:**
- ✅ Automatic validation and error checking
- ✅ Atomic operations (all-or-nothing)
- ✅ State management consistency
- ✅ Integration with CI/CD and registries
- ✅ Consistent naming and tagging
- ✅ Automatic Beads issue creation from findings
- ✅ Telemetry and metrics tracking
- ✅ Help text available: `devloop <command> --help`

---

## Pre-Flight Development Checklist

**CRITICAL:** Run this checklist at the start of each development session to prevent cascading failures from formatting debt.

### Why Formatting Debt Matters

Formatting and code quality issues compound quickly:

1. **Formatting debt accumulates** → Multiple unformatted files build up
2. **Pre-commit hook gets noisy** → Flags unrelated files that were modified
3. **Developer ignores hooks** → Pre-commit warnings become noise, not signals
4. **Bad commits slip through** → When developers disable hooks, real issues bypass pre-commit

Example: You fix 2 lines in `parser.py`, but Black wants to reformat 100 lines. The hook now flags both your changes AND the formatting debt, making it hard to see the actual change.

**Prevention: Format entire codebase at session start.**

### Pre-Flight Checklist

Run these commands **before** starting any work session:

```bash
# 1. Format entire codebase
poetry run black src/ tests/

# 2. Lint and check for issues
poetry run ruff check src/ tests/ --fix
poetry run mypy src/

# 3. Run full test suite (if time permits)
poetry run pytest

# 4. Verify hooks work
.agents/verify-task-complete
```

This takes ~2-5 minutes but saves 30+ minutes of dealing with formatting cascades later.

### Why This Matters for DevLoop

DevLoop's pre-commit hook needs a clean baseline to be effective:
- ✅ Catches *your* changes clearly
- ✅ Doesn't flag pre-existing formatting issues
- ✅ Stays non-intrusive and helpful
- ❌ Avoids alert fatigue that leads to hook disabling

**Best practice**: Make pre-flight checklist a habit at session start, right after `bd ready`.

---

## CI Verification (Pre-Push Hook)

**Automatic:** The `.git/hooks/pre-push` hook automatically checks CI status before allowing pushes.

### Workflow

1. Make changes and commit: `git add . && git commit -m "..."`
2. Push: `git push origin main`
3. **Pre-push hook runs automatically:**
   - Checks if `gh` CLI is installed
   - Gets the latest CI run status for your branch
   - If CI failed: blocks push and shows error
   - If CI passed: allows push to proceed
   - If no runs yet: allows push

### Manual CI Check

```bash
# View recent CI runs
gh run list --limit 10

# View a specific run
gh run view <run-id>

# View failed run details
gh run view <run-id> --log-failed
```

### If Push is Blocked

1. Check what failed: `gh run view <run-id> --log-failed`
2. Fix the issues locally
3. Commit and push again
4. Pre-push hook will verify the new CI run before allowing push

**Why this matters:** CI failures catch issues before they merge (formatting, type errors, broken tests, security issues). The pre-push hook ensures developers are aware of CI status before code reaches the repository.

---

## Documentation Practices (CRITICAL)

**Files are tracked in git and must never be accidentally deleted.**

### Prevention Rules

1. **Commit Message Discipline**
   - Always use descriptive commit messages
   - When deleting docs, include explicit annotation:
     ```bash
     git commit -m "docs: Remove outdated X documentation"
     git commit -m "chore: Clean up deprecated docs for Y"
     ```
   - Commit message must explain WHY files are deleted

2. **Pre-Commit Awareness**
   - Check for deleted files before committing:
     ```bash
     git status                          # See deleted files
     git log --diff-filter=D --summary   # View deletion history
     ```
   - If deletion is accidental: `git restore <filename>`

3. **CI Validation** (Automatic)
   - GitHub Actions automatically validates:
     - All links in README.md resolve to files
     - Documentation files weren't deleted without explanation
     - Any deletion without "docs:" prefix in message fails CI

4. **Update README.md**
   - After deleting docs, update all README.md references
   - CI will fail if README references non-existent files
   - Verify all links:
     ```bash
     grep -o '\]\(\.\/.*\.md\)\|\]\(docs/.*\.md\)' README.md | sort -u
     ```

### Example: Intentional Deletion

```bash
# 1. Before deleting, check what's in the file
git show HEAD:docs/old-feature.md | head -20

# 2. Remove the file
rm docs/old-feature.md

# 3. Update README.md to remove links to this file
# (CI will fail if you don't)

# 4. Stage changes
git add docs/ README.md

# 5. Commit with explicit documentation
git commit -m "docs: Remove old-feature documentation (archived in git history)"

# 6. CI validates that all README links still resolve
# ✅ Push succeeds if all links are valid
```

### Why This Matters

**Scenario (happened in commit 1e06145):**
- Developer adds metrics code
- 10 documentation files accidentally deleted
- No commit message mentions deletion
- README references non-existent files (broken links)
- Users can't find documentation

**Prevention:**
- CI now validates links before merge
- Pre-commit hook warns about deletions
- Commit message requirement enforces intentionality
- Documentation recovery always possible from git history

---

## Publishing & Security Considerations

**For public/published software**, add extra care to your DevLoop workflow:

### Secrets Management

DevLoop provides comprehensive token security features to prevent credential exposure.

**Never Do:**
- ❌ Commit API keys, tokens, or credentials to version control
- ❌ Pass tokens as command-line arguments (visible in process lists)
- ❌ Hardcode tokens in code or configuration files
- ❌ Log full tokens or include them in error messages
- ❌ Store tokens in shell history

**Always Do:**
- ✅ Use environment variables for all tokens (`GITHUB_TOKEN`, `PYPI_TOKEN`, etc.)
- ✅ Enable token expiry and rotation (30-90 days recommended)
- ✅ Use read-only or project-scoped tokens when possible
- ✅ Scan commits for accidentally leaked secrets before pushing
- ✅ Use CI/CD secrets managers (GitHub Secrets, GitLab CI/CD Variables)

### Version Consistency
- ✅ Version is the single source of truth
- ✅ Use semantic versioning (MAJOR.MINOR.PATCH)
- ✅ Tag releases with matching version numbers (`git tag v1.2.3`)

### Breaking Changes
- ✅ Document all breaking changes clearly in `CHANGELOG.md`
- ✅ Include migration guides in release notes
- ✅ Consider deprecation warnings before breaking changes

### Dependency Security
- ✅ Run security audits regularly
- ✅ Monitor for CVE updates in dependencies
- ✅ Update vulnerable dependencies promptly
- ✅ Review new dependency versions before merging

### Documentation Accuracy
- ✅ Test all installation instructions on a clean environment
- ✅ Verify all code examples actually work
- ✅ Keep README, API docs, and examples current with code changes

### Pre-Release Checklist

Before publishing to registries:
1. ✅ All CI tests pass
2. ✅ All code quality checks pass (linting, type checking, formatting)
3. ✅ Security scan shows no vulnerabilities
4. ✅ Documentation is current and tested
5. ✅ CHANGELOG updated with release notes
6. ✅ Version numbers consistent across files
7. ✅ No accidental secrets in commit history
8. ✅ Manual smoke test on clean environment
9. ✅ Release notes written with migration guides (if breaking changes)

---

## Release Process

DevLoop uses a **provider-agnostic release workflow** that works with any CI system and any package registry. No vendor lock-in—use GitHub Actions, GitLab CI, Jenkins, CircleCI, or any other platform. Publish to PyPI, npm, Artifactory, Docker registries, or custom artifact stores.

### Supported CI Platforms

DevLoop automatically detects and works with:
- **GitHub Actions** - Via `gh` CLI
- **GitLab CI/CD** - Via `glab` CLI
- **Jenkins** - Via Jenkins REST API
- **CircleCI** - Via CircleCI API v2
- **Custom CI Systems** - Via manual configuration

### Supported Package Registries

DevLoop automatically detects and publishes to:
- **PyPI** - Via `poetry` or `twine`
- **npm** - Via npm CLI
- **Docker Registry** - Via Docker CLI
- **Artifactory** - Via Artifactory REST API
- **Custom Registries** - Via manual configuration

### Quick Release Commands

Check if you're ready to release:
```bash
devloop release check 1.2.3
```

Publish a release (full workflow):
```bash
devloop release publish 1.2.3
```

Additional options:
```bash
# Dry-run to see what would happen
devloop release publish 1.2.3 --dry-run

# Specify explicit providers (if auto-detect fails)
devloop release publish 1.2.3 --ci github --registry pypi

# Skip specific steps
devloop release publish 1.2.3 --skip-tag --skip-publish
```

### Automated Release Workflow

The `devloop release` commands run the following steps automatically:

1. **Pre-Release Checks** - Verifies all preconditions:
   - Git working directory is clean (no uncommitted changes)
   - You're on the correct release branch (default: `main`)
   - CI passes on current branch (uses your CI provider)
   - Package registry credentials are valid
   - Version format is valid (semantic versioning: X.Y.Z)

2. **Create Git Tag** - Creates annotated tag:
   - Tag name: `v{version}` (configurable with `--tag-prefix`)
   - Fails if tag already exists

3. **Publish to Registry** - Publishes package:
   - Uses detected or specified package registry
   - Supports multiple registries per release (run multiple times)
   - Returns package URL

4. **Push Tag** - Pushes tag to remote repository:
   - Only if all previous steps succeed

### Manual Release Workflow

If you need more control or if `devloop release` is unavailable, follow these steps for your project type:

**For Python projects (pyproject.toml)**:
1. **Update CHANGELOG.md**
   ```markdown
   ## [X.Y.Z] - YYYY-MM-DD
   
   ### Major Features
   - Feature 1
   - Feature 2
   
   ### Improvements
   - Improvement 1
   ```

2. **Bump version** (keep version numbers in sync)

3. **Update dependency lock file**
   ```bash
   poetry lock   # For poetry projects
   pip freeze > requirements.txt  # For pip projects
   ```

4. **Commit changes**
   ```bash
   git add pyproject.toml CHANGELOG.md poetry.lock
   git commit -m "Release vX.Y.Z: Description of major changes"
   ```

5. **Create and push tag**
   ```bash
   git tag -a vX.Y.Z -m "DevLoop vX.Y.Z - Release notes here"
   git push origin main vX.Y.Z
   ```

**For other project types (Node.js, Docker, etc.)**:
Replace the version file (`package.json` for npm, etc.) in step 2, and update the lock file appropriately in step 3.

### Release Checklist

Before pushing your release tag:

1. ✅ All CI tests pass (`devloop release check <version>` or manual CI check)
2. ✅ CHANGELOG.md updated with release notes
3. ✅ Version bumped in all relevant files
4. ✅ Lock files updated (`poetry.lock`, `package-lock.json`, etc.)
5. ✅ No uncommitted changes: `git status` should be clean
6. ✅ Release notes include migration guides (if breaking changes)
7. ✅ Manual testing on clean environment (for critical releases)

### Notes

- The pre-commit hook will validate formatting, types, and tests
- If you need to bypass pre-commit for lock file changes: `git commit --no-verify`
- Always commit version and CHANGELOG updates before creating the release tag
- Follow [Semantic Versioning](https://semver.org/): MAJOR.MINOR.PATCH
- Release tags are permanent - create a new tag if mistakes are made

---

## Configuration

### Log Rotation

By default, DevLoop logs can grow unbounded. **Configure log rotation** to prevent disk space issues:

```json
{
  "global": {
    "logging": {
      "level": "info",
      "rotation": {
        "enabled": true,
        "maxSize": "100MB",
        "maxBackups": 3,
        "maxAgeDays": 7,
        "compress": true
      }
    }
  }
}
```

This keeps logs under control while preserving recent history.

### Agents Configuration

Agents are configured via `.devloop/agents.json`:

```json
{
  "enabled": true,
  "agents": {
    "linter": {
      "enabled": true,
      "triggers": ["file:save", "git:pre-commit"],
      "config": {
        "debounce": 500,
        "filePatterns": ["**/*.{js,ts,jsx,tsx}"]
      }
    },
    "testRunner": {
      "enabled": true,
      "triggers": ["file:save"],
      "config": {
        "watchMode": true,
        "relatedTestsOnly": true
      }
    }
  },
  "global": {
    "maxConcurrentAgents": 5,
    "notificationLevel": "summary",
    "resourceLimits": {
      "maxCpu": 25,
      "maxMemory": "500MB"
    }
  }
}
```

---

## Security & Privacy

- Agents run in isolated environments
- No external data transmission without explicit consent
- Local execution only (no cloud dependencies by default)
- Sensitive file patterns excluded from monitoring
- Audit log of all agent actions

---

## Success Metrics

- Developer interruptions (should decrease)
- Time to fix issues (should decrease)
- Code quality metrics (should improve)
- Test coverage (should increase)
- Resource usage (should remain acceptable)
- Developer satisfaction (should increase)

---

## Future Considerations

- **Multi-Project Support**: Agents working across multiple repositories
- **Team Coordination**: Shared agent insights across team members
- **Cloud Integration**: Optional cloud-based analysis for deeper insights
- **Custom Agent Marketplace**: Community-contributed agents
- **AI-Powered Agents**: Integration with LLMs for intelligent suggestions
- **Cross-Tool Integration**: Integration with popular dev tools (Docker, K8s, etc.)
