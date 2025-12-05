# Sandbox Installation & Migration Guide

**Related Issue:** claude-agents-3yi (P0 Critical Security)
**Branch:** feature/hybrid-sandbox-isolation

## Overview

DevLoop now sandboxes all agent subprocess execution to prevent malicious code execution and sandbox escape attempts. This guide covers installation, configuration, and migration.

## Quick Start

### 1. Install Bubblewrap (Recommended)

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y bubblewrap
```

**Fedora/RHEL:**
```bash
sudo dnf install -y bubblewrap
```

**Arch Linux:**
```bash
sudo pacman -S bubblewrap
```

**macOS:**
```bash
# Bubblewrap is Linux-only
# macOS will use fallback sandbox (NoSandbox with whitelist)
```

### 2. Verify Installation

```bash
bwrap --version
```

### 3. Update DevLoop Configuration

The sandbox is **enabled by default** with sensible defaults in `.devloop/agents.json`:

```json
{
  "global": {
    "security": {
      "sandbox": {
        "mode": "auto",
        "allowed_tools": [
          "python3", "git", "ruff", "black", "mypy",
          "bandit", "pytest", "eslint", "snyk", "gh"
        ],
        "resource_limits": {
          "max_memory_mb": 500,
          "max_cpu_percent": 25,
          "timeout_seconds": 30
        },
        "network": {
          "allowed_domains": [
            "pypi.org",
            "github.com",
            "api.github.com"
          ]
        }
      }
    }
  }
}
```

### 4. Test Sandbox

```bash
# Run security tests
poetry run pytest tests/security/test_sandbox_escapes.py -v

# Check logs for sandbox mode in use
tail -f .devloop/devloop.log | grep "sandbox"
```

## Configuration Options

### Sandbox Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `auto` | Automatically select best available sandbox | **Recommended** - Let DevLoop choose |
| `capsule` | WASM-based isolation (Capsule runtime) | Pure Python agents (Jan 2025+) |
| `bubblewrap` | Linux namespace isolation | Tool-dependent agents |
| `seccomp` | Syscall filtering fallback | When Bubblewrap unavailable |
| `none` | No sandbox (whitelist only) | **Development only** |

### Per-Agent Configuration

Override sandbox settings for specific agents:

```json
{
  "agents": {
    "linter": {
      "enabled": true,
      "config": {
        "sandbox": {
          "mode": "bubblewrap",
          "timeout_seconds": 60,
          "allowed_tools": ["ruff"]
        }
      }
    },
    "type_checker": {
      "enabled": true,
      "config": {
        "sandbox": {
          "mode": "capsule",
          "max_memory_mb": 256
        }
      }
    }
  }
}
```

### Tool Whitelisting

Add custom tools to the whitelist:

```json
{
  "global": {
    "security": {
      "sandbox": {
        "allowed_tools": [
          "python3",
          "git",
          "ruff",
          "your-custom-tool"
        ]
      }
    }
  }
}
```

**Security Note:** Only add tools you trust! Each tool in the whitelist can be executed by agents.

### Resource Limits

Adjust resource limits for your environment:

```json
{
  "global": {
    "security": {
      "sandbox": {
        "resource_limits": {
          "max_memory_mb": 1024,  // Increase for large codebases
          "max_cpu_percent": 50,   // Increase for faster machines
          "timeout_seconds": 60    // Increase for slow operations
        }
      }
    }
  }
}
```

### Network Access

Control network access for agents:

```json
{
  "global": {
    "security": {
      "sandbox": {
        "network": {
          "allowed_domains": [
            "pypi.org",           // Python packages
            "github.com",         // GitHub API
            "api.github.com",     // GitHub API
            "registry.npmjs.org"  // npm packages (if needed)
          ]
        }
      }
    }
  }
}
```

**Note:** Currently, Bubblewrap sandbox disables ALL network access (`--unshare-net`). Network allowlist will be used when Capsule support is added.

## Migration Guide

### From Unsandboxed DevLoop

**No migration needed!** Sandbox is backwards-compatible:

1. ✅ All existing agents continue to work
2. ✅ Default whitelist includes all standard tools
3. ✅ Auto-mode selects best sandbox automatically
4. ✅ Graceful fallback if Bubblewrap unavailable

**What Changes:**
- Agents now run in isolated environments
- Non-whitelisted tools are blocked
- Resource limits enforced
- Network access restricted

**Breaking Changes:** None (unless you were using non-standard tools)

### Adding Custom Tools

If your agents use custom tools:

1. Add tool to whitelist in `.devloop/agents.json`
2. Ensure tool is in standard system paths (`/usr/bin`, `/usr/local/bin`)
3. Test with security tests

```json
{
  "global": {
    "security": {
      "sandbox": {
        "allowed_tools": [
          "python3",
          "git",
          "your-custom-tool"  // Add here
        ]
      }
    }
  }
}
```

### Disabling Sandbox (Not Recommended)

**WARNING:** Only disable sandbox in trusted environments!

```json
{
  "global": {
    "security": {
      "sandbox": {
        "mode": "none"
      }
    }
  }
}
```

This still enforces:
- Tool whitelisting
- Timeout limits

But removes:
- Filesystem isolation
- Network isolation
- Process isolation

## Troubleshooting

### "Bubblewrap sandbox requested but not available"

**Problem:** Bubblewrap not installed or not in PATH

**Solution:**
```bash
# Install bubblewrap (see Quick Start)
sudo apt-get install -y bubblewrap

# Verify installation
bwrap --version
```

**Workaround:** Use `"mode": "auto"` to auto-select fallback

### "Command not allowed: X"

**Problem:** Tool not in whitelist

**Solution:** Add tool to `allowed_tools`:

```json
{
  "global": {
    "security": {
      "sandbox": {
        "allowed_tools": ["X"]
      }
    }
  }
}
```

### "Command exceeded Xs timeout"

**Problem:** Operation takes longer than timeout

**Solution:** Increase timeout:

```json
{
  "global": {
    "security": {
      "sandbox": {
        "resource_limits": {
          "timeout_seconds": 60
        }
      }
    }
  }
}
```

### Tests Skipped (Bubblewrap not available)

**Expected on macOS and Windows** - Bubblewrap is Linux-only.

DevLoop will automatically use fallback sandbox (NoSandbox with whitelist enforcement).

To test on macOS/Windows:
```bash
# Run NoSandbox tests
poetry run pytest tests/security/test_sandbox_escapes.py::TestNoSandboxFallback -v
```

## Security Best Practices

### 1. Minimal Whitelist

Only allow tools you actually need:

```json
{
  "allowed_tools": [
    "python3",  // Required for Python agents
    "git",      // Required for git operations
    "ruff"      // Only if using ruff
  ]
}
```

### 2. Strict Timeouts

Prevent runaway processes:

```json
{
  "resource_limits": {
    "timeout_seconds": 30  // Kill after 30s
  }
}
```

### 3. Review Logs

Monitor sandbox activity:

```bash
tail -f .devloop/devloop.log | grep -i sandbox
```

Look for:
- ✅ "Using Bubblewrap sandbox" (good)
- ⚠️ "Using NO sandbox" (bad - only in dev)
- ❌ "Command not allowed" (potential attack)

### 4. Update Regularly

Keep Bubblewrap updated:

```bash
sudo apt-get update && sudo apt-get upgrade bubblewrap
```

### 5. Test Custom Agents

Always test custom agents with security tests:

```bash
poetry run pytest tests/security/ -v
```

## Future: Capsule (WASM) Support

**Coming January 2025:** Capsule runtime for WASM-based sandboxing.

**Benefits:**
- Faster startup (~10ms vs ~50ms)
- Better isolation
- Cross-platform (macOS, Windows, Linux)

**How to Prepare:**

1. Identify pure-Python agents (no external tools)
2. Set mode to `capsule` when available:

```json
{
  "agents": {
    "type_checker": {
      "config": {
        "sandbox": {
          "mode": "capsule"  // Will auto-enable when available
        }
      }
    }
  }
}
```

DevLoop will automatically fall back to Bubblewrap until Capsule is available.

## Support

**Issues:** Report sandbox issues to `claude-agents-3yi` (Beads)

**Documentation:** See `docs/HYBRID_SANDBOX_DESIGN.md` for technical details

**Tests:** Run `poetry run pytest tests/security/ -v` to verify sandbox
