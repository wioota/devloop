# Upgrade Guide

> Version migration instructions, breaking changes, and rollback procedures for DevLoop.

---

## Upgrading DevLoop

```bash
# Upgrade to latest version
pip install --upgrade devloop

# Update project templates (hooks, commands, settings)
devloop init --merge-templates /path/to/project

# Restart the daemon
devloop stop
devloop watch .
```

---

## Version Compatibility

| DevLoop Version | Python | Poetry | GitHub CLI | Key Changes |
|----------------|--------|--------|------------|-------------|
| 0.10.x | 3.11+ | 1.7+ | 2.78+ | Init orchestrator, MCP server |
| 0.9.x | 3.11+ | 1.7+ | 2.78+ | MCP server, PostToolUse hook |
| 0.8.x | 3.11+ | 1.7+ | 2.78+ | Insights command, Claude Code hooks |
| 0.7.x | 3.11+ | 1.7+ | 2.78+ | Test coverage infrastructure |
| 0.6.x | 3.11+ | 1.7+ | 2.78+ | Package registry, telemetry |
| 0.5.x | 3.11+ | 1.7+ | 2.78+ | VSCode extension, provider system |
| 0.4.x | 3.11+ | 1.7+ | 2.78+ | Event logging, dynamic versioning |
| 0.3.x | 3.11+ | — | — | Sandbox security, Claude Code |
| 0.2.x | 3.11+ | — | — | Project rename to DevLoop |

---

## Migration Guides

### 0.10.0: Init Orchestrator

**What changed:** `devloop init` now supports idempotent re-initialization. Running it on an existing project updates hooks, commands, and settings without destroying custom configuration.

**Action required:** None. This is backwards-compatible. Running `devloop init` on an existing project is now safe and recommended after upgrades.

```bash
# Safe to re-run on existing projects
devloop init /path/to/project
```

### 0.9.0: MCP Server

**What changed:** Added MCP (Model Context Protocol) server for Claude Code integration. PostToolUse hook shows findings after file edits.

**Action required:** None. MCP server is opt-in. To use it with Claude Code, add the MCP server to your Claude Code settings.

### 0.4.1: Dynamic Version Management

**What changed:** Version is now read dynamically from package metadata via `importlib.metadata.version("devloop")`. The `__version__` attribute in `src/devloop/__init__.py` was removed.

**Action required:** If your code reads `devloop.__version__`, update it:

```python
# Before (0.4.0 and earlier)
from devloop import __version__

# After (0.4.1+)
from importlib.metadata import version
devloop_version = version("devloop")
```

### 0.4.0: Event Logging / SQLite Backend

**What changed:** Event storage migrated from JSONL files to SQLite. Context store memory limits changed from 500 to 250 findings per tier. Audit log auto-cleanup enforced at 30 days.

**Action required:**
1. Old JSONL event files in `.devloop/` can be safely deleted
2. Memory limits are automatic — no configuration change needed
3. Audit logs older than 30 days will be automatically cleaned

### 0.3.0: Sandbox Security System

**What changed:** Sandbox execution is now mandatory by default. `agents.json` schema updated with sandbox configuration fields.

**Action required:**
1. Update `.devloop/agents.json` if you have a custom config:
   ```json
   {
     "global": {
       "sandbox": {
         "type": "bubblewrap",
         "enabled": true
       }
     }
   }
   ```
2. Install bubblewrap if not present: `sudo apt-get install bubblewrap`

### 0.2.0: Project Rename (dev-agents → DevLoop)

**What changed:** Complete rename from "dev-agents" to "devloop".

**Action required:**
```bash
# 1. Uninstall old package
pip uninstall dev-agents

# 2. Install new package
pip install devloop

# 3. Update imports
# from dev_agents → from devloop

# 4. Update CLI commands
# dev-agents → devloop

# 5. Rename config directory
mv .dev-agents .devloop
```

---

## Rollback Instructions

If an upgrade causes issues:

```bash
# Install a specific version
pip install devloop==0.9.0

# Restore previous config (if backed up)
git checkout HEAD~1 -- .devloop/agents.json

# Restart
devloop stop
devloop watch .
```

**Before upgrading**, always:
1. Commit your current code to git
2. Note your current DevLoop version: `devloop --version`
3. Back up `.devloop/agents.json` if customized

---

## Troubleshooting Upgrades

### Config migration fails

```bash
# Reset to default config
devloop init /path/to/project --force-config
```

### Hooks not updated after upgrade

```bash
# Re-install hooks from latest templates
devloop init --merge-templates /path/to/project

# Or update hooks directly
devloop update-hooks
```

### Old daemon still running

```bash
# Stop all DevLoop processes
devloop stop

# Verify no orphaned processes
ps aux | grep devloop

# Start fresh
devloop watch .
```

---

## See Also

- [CHANGELOG.md](../CHANGELOG.md) — Full version history
- [Getting Started](./getting-started.md) — Fresh installation
- [Configuration Guide](./configuration.md) — Settings reference
