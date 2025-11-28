# CI Integration

Automated GitHub Actions CI/CD status monitoring and checks integrated into your development workflow.

## Features

### 1. Pre-Commit CI Warning

**Automatically warns you before committing if previous CI failed**

```bash
git commit -m "fix: update logic"
```

Output:
```
⚠️  WARNING: Previous CI run FAILED on branch 'main'
   Workflow: CI

   You're about to commit on top of failing CI.
   Consider fixing CI issues first.

   View details: gh run list --branch main
```

**How it works:**
- Git pre-commit hook checks latest CI status for your branch
- Warns (but doesn't block) if previous CI run failed
- Shows which workflow failed
- Provides command to view details

**Location:** `.git/hooks/pre-commit`

---

### 2. Post-Push CI Check

**Automatically checks CI status after successful push**

```bash
# Option 1: Use the wrapper script
.devloop/scripts/git-push-with-ci origin main

# Option 2: Create a git alias (recommended)
git config alias.pushci '!.devloop/scripts/git-push-with-ci'
git pushci origin main
```

Output:
```
📤 Pushing to remote...
✅ Push successful!

🔍 Checking CI status (waiting up to 2 minutes)...
⏳ CI running... (1/4 completed)
⏳ CI running... (2/4 completed)
⏳ CI running... (3/4 completed)
✅ CI passed for commit abc1234 (4/4 workflows)
```

**How it works:**
- Wrapper script runs `git push` first
- Waits 5 seconds for GitHub to register the push
- Checks CI status every 10 seconds for up to 2 minutes
- Reports when CI passes or fails

**Location:** `.devloop/scripts/git-push-with-ci`

---

### 3. Background CI Monitor Agent

**Periodically checks CI status while you work**

The CI Monitor agent runs in the background and:
- Checks CI status every 5 minutes (configurable)
- Reports failures as findings in context store
- Integrates with agent summaries

**Configuration:** `.devloop/agents.json`

```json
{
  "ci-monitor": {
    "enabled": true,
    "triggers": ["time:tick", "git:post-push"],
    "config": {
      "check_interval": 300,
      "monitor_branches": ["main", "develop"],
      "notify_on_failure": true,
      "auto_check_after_push": true
    }
  }
}
```

**Customize check interval:**
```json
{
  "config": {
    "check_interval": 600  # Check every 10 minutes
  }
}
```

---

### 4. Manual CI Status Check

**Check CI status anytime with the standalone script**

```bash
# Check current branch
.devloop/scripts/check-ci-status.sh

# Wait for CI to complete (up to 2 minutes)
.devloop/scripts/check-ci-status.sh --wait

# Check specific branch
.devloop/scripts/check-ci-status.sh --branch develop

# Custom timeout
.devloop/scripts/check-ci-status.sh --wait --timeout 300
```

---

## Setup

### Prerequisites

1. **Install GitHub CLI:**
   ```bash
   # macOS
   brew install gh

   # Ubuntu/Debian
   sudo apt install gh

   # Or download from: https://cli.github.com/
   ```

2. **Authenticate:**
   ```bash
   gh auth login
   ```

3. **Verify:**
   ```bash
   gh auth status
   ```

### Recommended: Create Git Alias

Add to your `.git/config` or global git config:

```bash
git config alias.pushci '!.devloop/scripts/git-push-with-ci'
```

Now use:
```bash
git pushci origin main
```

---

## How CI Checks Work

### CI Status Detection

The integration uses GitHub CLI (`gh`) to check workflow runs:

```bash
gh run list --branch main --limit 5 --json status,conclusion,name
```

**Statuses:**
- `in_progress` - CI is currently running
- `completed` + `success` - All checks passed ✅
- `completed` + `failure` - One or more checks failed ❌

### When Checks Occur

| Trigger | When | Tool |
|---------|------|------|
| **Pre-commit** | Before every commit | Git hook |
| **Post-push** | After successful push (manual) | Wrapper script |
| **Periodic** | Every 5 minutes | Background agent |
| **Manual** | On-demand | Standalone script |

---

## Findings & Context Store

CI Monitor agent writes findings to the context store:

**Example finding:**
```json
{
  "agent": "ci-monitor",
  "category": "ci",
  "severity": "error",
  "message": "CI workflow 'test' failed on branch 'main'",
  "file_path": ".github/workflows/",
  "location": "Run #12345",
  "suggestion": "View details: gh run view 12345\nRerun: gh run rerun 12345"
}
```

**Access findings:**
```bash
devloop summary agent-summary --category ci
```

---

## Troubleshooting

### "gh CLI not found"

Install GitHub CLI:
```bash
brew install gh  # macOS
sudo apt install gh  # Ubuntu
```

### "gh CLI not authenticated"

Authenticate with GitHub:
```bash
gh auth login
```

### "No CI runs found"

This is normal if:
- GitHub hasn't registered the push yet (wait 10-30 seconds)
- No CI workflow is configured for this branch
- CI workflows are triggered only on specific branches

### Disable CI checks

**Disable pre-commit warning:**
```bash
rm .git/hooks/pre-commit
```

**Disable background monitor:**
Edit `.devloop/agents.json`:
```json
{
  "ci-monitor": {
    "enabled": false
  }
}
```

---

## CI Workflow Configuration

Your CI is defined in `.github/workflows/ci.yml`:

- **test** - Runs pytest on Python 3.11 & 3.12
- **lint** - Runs Black and Ruff
- **type-check** - Runs mypy type checking
- **security** - Runs Bandit security scanner

---

## Examples

### Daily Workflow

```bash
# 1. Make changes
vim src/devloop/core/agent.py

# 2. Commit (warns if previous CI failed)
git commit -m "feat: add new feature"

# 3. Push and check CI
git pushci origin main

# 4. CI runs automatically
# Wait for results...
✅ CI passed for commit abc1234 (4/4 workflows)

# 5. Background agent monitors CI every 5 minutes
# Alerts you if any failures occur
```

### Checking CI Before Merge

```bash
# Check CI status for feature branch
.devloop/scripts/check-ci-status.sh --branch feature/new-thing

# Wait for CI to complete
.devloop/scripts/check-ci-status.sh --branch feature/new-thing --wait

# If passing, merge
git checkout main
git merge feature/new-thing
```

---

## Benefits

✅ **Catch CI failures early** - Know immediately if push broke CI
✅ **Prevent broken commits** - Warning before committing on failing CI
✅ **Continuous monitoring** - Background agent tracks CI health
✅ **Context integration** - CI status in agent findings
✅ **Zero configuration** - Works automatically with GitHub Actions

---

## See Also

- [GitHub CLI Documentation](https://cli.github.com/manual/)
- [GitHub Actions Workflows](.github/workflows/ci.yml)
- [Agent Configuration](.devloop/agents.json)
