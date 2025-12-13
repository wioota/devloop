# DevLoop Upgrade Guide

This guide covers upgrading DevLoop across versions, handling breaking changes, and ensuring version compatibility.

## Table of Contents

1. [Before You Upgrade](#before-you-upgrade)
2. [Upgrade Procedures](#upgrade-procedures)
3. [Version Compatibility](#version-compatibility)
4. [Breaking Changes](#breaking-changes)
5. [Troubleshooting](#troubleshooting)

---

## Before You Upgrade

### Backup Your Data

Before upgrading, backup your DevLoop configuration and findings:

```bash
# Backup your .devloop directory
cp -r .devloop .devloop.backup-$(date +%Y%m%d)

# Backup your project configuration
cp pyproject.toml pyproject.toml.backup-$(date +%Y%m%d)
```

### Check Current Version

```bash
devloop --version
# or
python -c "import importlib.metadata; print(importlib.metadata.version('devloop'))"
```

### Review Release Notes

Always check the [CHANGELOG.md](../CHANGELOG.md) for the version you're upgrading to, especially sections marked with ⚠️ **BREAKING CHANGE**.

---

## Upgrade Procedures

### From pip

```bash
# Upgrade to latest version
pip install --upgrade devloop

# Or upgrade to a specific version
pip install devloop==0.5.0
```

### From Poetry (Development)

```bash
# Update poetry.lock
poetry update devloop

# Or update to a specific version
poetry update devloop --lock
```

### Post-Upgrade Verification

After upgrading, verify the installation:

```bash
# Check version
devloop --version

# Test basic functionality
devloop status

# Verify configuration migration (if applicable)
.agents/verify-task-complete
```

---

## Version Compatibility

### Python Version Requirements

| DevLoop Version | Python 3.11 | Python 3.12 | Python 3.13 |
|-----------------|-------------|-------------|-------------|
| 0.5.0+          | ✅ Supported | ✅ Supported | ⏳ Soon     |
| 0.4.x           | ✅ Supported | ✅ Supported | ❌ Not yet  |
| 0.3.x           | ✅ Supported | ⚠️ Limited  | ❌ No       |
| 0.2.x           | ✅ Supported | ❌ No       | ❌ No       |
| 0.1.x           | ✅ Supported | ❌ No       | ❌ No       |

**Action Required:** If you're on Python 3.10 or earlier, upgrade Python first:

```bash
# Check your Python version
python --version

# Install Python 3.11+ (macOS)
brew install python@3.11

# Install Python 3.11+ (Ubuntu/Debian)
sudo apt-get install python3.11

# Install Python 3.11+ (Windows)
# Download from https://www.python.org/downloads/
```

### Feature Compatibility

#### 0.5.0 Features

- ✅ VSCode Extension with LSP
- ✅ Provider System (multi-CI/registry support)
- ✅ Token security & OAuth2
- ✅ Beads integration
- ✅ AGENTS.md template system

**Deprecations:** None

#### 0.4.1 Features

- ✅ Structured event logging
- ✅ Agent metrics and health monitoring
- ✅ Dynamic version management
- ✅ Pre-flight checklist support

**Deprecations:** Pre-commit version consistency check (removed in 0.5.0)

#### 0.3.x Features

- ✅ Sandbox security system (Phases 1-3)
- ✅ Claude Code integration
- ✅ Beads integration (initial)

**Deprecations:** None

### Dependency Versions

DevLoop maintains compatibility with:

```toml
python = "^3.11"                 # 3.11, 3.12, not 4.x
pydantic = "^2.5"                # 2.5+, not 1.x or 3.x
watchdog = "^3.0"                # 3.0+
typer = ">=0.15,<1.0"            # 0.15+, but not 1.0+
rich = "^13.7"                   # 13.7+
```

---

## Breaking Changes

### 0.2.0: Project Rename (dev-agents → DevLoop)

**Severity:** 🔴 Critical

**What Changed:**
- Package renamed: `dev_agents` → `devloop`
- CLI renamed: `dev-agents` → `devloop`
- Config directory: `.dev-agents/` → `.devloop/`
- PyPI package: `dev-agents` → `devloop`

**Migration Steps:**

1. **Uninstall old package:**
   ```bash
   pip uninstall dev-agents
   ```

2. **Install new package:**
   ```bash
   pip install devloop
   ```

3. **Update imports in code:**
   ```python
   # Old
   from dev_agents.core import Agent
   
   # New
   from devloop.core import Agent
   ```

4. **Update configuration directory:**
   ```bash
   mv .dev-agents .devloop
   ```

5. **Update any custom scripts:**
   ```bash
   # Old
   dev-agents watch
   
   # New
   devloop watch
   ```

**Impact:** Complete compatibility reset. Requires full reinstall and code updates.

---

### 0.4.0: Event Logging & SQLite Backend

**Severity:** 🟡 Medium

**What Changed:**
- Event logging now uses SQLite backend (previously file-based)
- Event schema updated with new fields
- Audit log retention policies enforced (30 days default)
- Context store memory limits changed (500 → 250 findings)

**Migration Steps:**

1. **Automatic migration occurs on startup** — No manual action required

2. **If you need to preserve old JSONL logs:**
   ```bash
   # Backup old logs before upgrading
   cp -r .devloop/events .devloop/events.backup
   ```

3. **Verify event logging works:**
   ```bash
   # Check events are being recorded
   devloop audit recent
   ```

**Impact:** Event history may be reset. Old JSONL-based events won't be imported automatically.

---

### 0.3.0: Sandbox Security System

**Severity:** 🟡 Medium

**What Changed:**
- Sandbox execution now mandatory by default
- Pyodide WASM runtime required for certain agents
- `agents.json` configuration schema updated
- File permissions on `.devloop/` directories stricter

**Migration Steps:**

1. **Update `agents.json`:**
   ```bash
   # Backup old config
   cp .devloop/agents.json .devloop/agents.json.backup-0.2
   
   # Reinitialize to get new schema
   devloop init --skip-amp
   ```

2. **Install Pyodide (optional but recommended):**
   ```bash
   devloop init  # Prompts for Pyodide setup
   ```

3. **Test sandbox is working:**
   ```bash
   devloop status
   ```

**Impact:** Agents may behave differently due to sandbox restrictions. File access patterns may change.

---

### 0.4.1: Dynamic Version Management

**Severity:** 🟢 Minor

**What Changed:**
- Version is now read from `pyproject.toml` only (single source of truth)
- No longer stored in `src/devloop/__init__.py`
- Pre-commit version check removed

**Migration Steps:**

1. **Update your scripts (if any):**
   ```python
   # Old (won't work anymore)
   from devloop import __version__
   
   # New (correct way)
   import importlib.metadata
   version = importlib.metadata.version('devloop')
   ```

2. **Remove version from any custom files:**
   ```bash
   # If you have custom version files, consolidate to pyproject.toml
   grep -r "__version__" src/ | grep -v node_modules
   ```

**Impact:** Minimal. Most users won't be affected.

---

## Configuration Migrations

### 0.5.0: agents.json Schema Updates

**New fields in agents.json:**

```json
{
  "global": {
    "telemetry": {
      "enabled": false,
      "anonymized": true,
      "localStorage": ".devloop/telemetry"
    },
    "sandbox": {
      "backend": "bubblewrap",
      "timeout": 30
    }
  },
  "agents": {
    "formatter": {
      "enableAutoFix": false,
      "safeMode": true
    }
  }
}
```

**Auto-migration:** DevLoop will automatically add missing fields with sensible defaults.

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'devloop'"

**Cause:** Old package still installed or new package not in Python path

**Solution:**
```bash
# Remove old package completely
pip uninstall dev-agents devloop -y

# Reinstall fresh
pip install devloop

# Verify
python -c "import devloop; print(devloop.__version__)"
```

### ".devloop directory not found"

**Cause:** Configuration directory wasn't migrated or was deleted

**Solution:**
```bash
# Reinitialize DevLoop
devloop init

# This will recreate .devloop with correct structure
```

### "Event migration failed" or SQLite errors

**Cause:** Corrupted event database from previous version

**Solution:**
```bash
# Backup old events
mv .devloop/events.db .devloop/events.db.backup

# Let DevLoop recreate the database
devloop status

# Database will be recreated on first run
```

### "Sandbox not available" or "bubblewrap missing"

**Cause:** Bubblewrap sandbox not installed on system

**Solution:**

```bash
# macOS
brew install bubblewrap

# Ubuntu/Debian
sudo apt-get install bubblewrap

# Fedora/RHEL
sudo dnf install bubblewrap

# Then reinitialize
devloop init
```

### Configuration schema incompatibility

**Cause:** agents.json from older version has incompatible schema

**Solution:**
```bash
# Backup old config
cp .devloop/agents.json .devloop/agents.json.backup

# Regenerate config with current schema
devloop init --skip-amp --non-interactive

# Manually migrate custom settings if needed
# Compare backup with new file to see what changed
diff .devloop/agents.json.backup .devloop/agents.json
```

### "Pre-commit hook version check failed"

**Cause:** Running 0.4.0 or earlier with 0.4.1+ code (version check was removed)

**Solution:**
```bash
# Reinstall git hooks
devloop init

# Remove old hook if present
rm .git/hooks/pre-commit.old
```

---

## Rollback Instructions

If an upgrade causes issues, you can rollback:

### Rollback to Previous Version

```bash
# Downgrade pip package
pip install devloop==0.4.1

# Verify downgrade
devloop --version

# Check if your backup .devloop still works
# If not, restore from backup:
rm -rf .devloop
cp -r .devloop.backup-20251213 .devloop
```

### Restore from Backup

```bash
# List available backups
ls -la .devloop.backup-*

# Restore specific backup
rm -rf .devloop
cp -r .devloop.backup-20251213 .devloop

# Verify restoration
devloop status
```

---

## Version Support Schedule

| Version | Release Date | End of Support | Security Fixes |
|---------|--------------|----------------|----------------|
| 0.5.0   | 2025-12-13   | 2026-06-13     | ✅ Yes        |
| 0.4.1   | 2025-12-10   | 2025-12-13     | ⚠️ Limited    |
| 0.4.0   | 2025-12-09   | 2025-12-13     | ❌ No         |
| 0.3.x   | 2025-12-06   | 2025-12-10     | ❌ No         |
| 0.2.x   | 2025-11-29   | 2025-12-06     | ❌ No         |
| 0.1.0   | 2025-11-28   | 2025-11-30     | ❌ No         |

**Current:** Only 0.5.0+ receives security updates

---

## Getting Help

If you encounter upgrade issues:

1. **Check the CHANGELOG** for your version jump
2. **Review this guide's troubleshooting section**
3. **Open an issue** with:
   - Current version: `devloop --version`
   - Target version: the version you're upgrading to
   - Error messages: full output from failed upgrade
   - System info: OS, Python version, pip version

---

## Next Steps

After successful upgrade:

- ✅ Run `devloop init` to ensure configuration is current
- ✅ Check `.devloop/agents.json` for new options
- ✅ Review CHANGELOG for new features
- ✅ Test with `devloop status` and `devloop watch`
- ✅ Update any custom agent code for breaking changes
