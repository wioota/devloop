# Security Guide

> Token management, sandbox security, and vulnerability scanning in DevLoop.

---

## Token Security

DevLoop manages API keys and tokens for agent integrations. All credentials must be stored as environment variables.

### Required Tokens

```bash
# CI verification
export GITHUB_TOKEN="your-github-token"

# Security scanning
export SNYK_TOKEN="your-snyk-token"

# Code analysis
export CODE_RABBIT_API_KEY="your-coderabbit-key"

# Package publishing
export PYPI_TOKEN="your-pypi-token"
```

### Best Practices

**Do:**
- Use environment variables for all credentials
- Enable token expiry and rotation (30-90 days recommended)
- Use read-only or project-scoped tokens when possible
- Store tokens in `.env` file (add to `.gitignore`)
- Scan commits for accidentally leaked secrets

**Don't:**
- Commit tokens to version control
- Pass tokens as command-line arguments
- Hardcode tokens in source code or configuration
- Log full token values in error messages

### Token Validation

DevLoop automatically:
- Hides tokens in logs and process output
- Validates token format during `devloop init`
- Warns about placeholder values ("changeme", "token", etc.)
- Checks token expiry where supported

```bash
devloop init /path/to/project     # Validates tokens during setup
devloop status --show-token-info  # View token status
```

### OAuth2 Support

DevLoop supports OAuth2 for CI provider integrations:
- **GitHub**: `gh auth login`
- **GitLab**: `glab auth login`
- **CircleCI**: API token via environment variable

---

## Sandbox Security

DevLoop provides sandboxed execution environments for agents to prevent unintended system modifications.

### Bubblewrap Sandbox (Default)

Linux-native sandboxing using bubblewrap (`bwrap`):
- Filesystem restrictions (read-only mounts, isolated tmpfs)
- Process isolation (separate PID namespace)
- CPU and memory limits via cgroups v2
- Audit logging of all sandbox operations

### Pyodide WASM Sandbox

For maximum isolation, DevLoop supports running Python agents in WebAssembly:

**Prerequisites:** Node.js 18+

```bash
# Automatic installation during init
devloop init /path/to/project

# Manual installation
devloop setup --install-pyodide

# Verify
devloop status --check-sandbox
```

**Properties:**
- Browser-grade isolation (WASM sandbox)
- No filesystem access outside sandbox
- Network access controlled by allowlist
- Works in POC mode without full installation

### Sandbox Configuration

```json
{
  "global": {
    "sandbox": {
      "type": "bubblewrap",
      "fallback": "pyodide",
      "networkAllowlist": ["pypi.org"],
      "resourceLimits": {
        "maxCpu": 25,
        "maxMemory": "500MB",
        "maxExecutionTime": 30000
      }
    }
  }
}
```

---

## Security Scanning

### Built-in Security Agents

| Agent | Tool | Scope |
|-------|------|-------|
| **Security Scanner** | Bandit | Python source code vulnerabilities |
| **Snyk** | Snyk CLI | Dependency vulnerabilities (all package managers) |

### Snyk Setup

```bash
npm install -g snyk
snyk auth
export SNYK_TOKEN="your-token"
```

Snyk supports: npm, pip, Ruby, Maven, Go, Rust, and more.

### CI Security Pipeline

GitHub Actions workflow includes:
1. **Bandit** — Code-level security scanning
2. **Snyk** — Dependency vulnerability scanning
3. Configurable severity threshold (default: `high`)
4. Reports available as CI artifacts

---

## Audit Logging

All agent actions are logged to an SQLite event store:

```bash
devloop audit query --limit 20     # Recent events
devloop audit query --agent snyk   # Filter by agent
```

- **Retention**: 30 days with automatic cleanup
- **Integrity**: File-level locking prevents race conditions
- **Privacy**: All data stored locally in `.devloop/events.db`

---

## Reporting Vulnerabilities

If you discover a security vulnerability in DevLoop:

1. **Do NOT** report it publicly via GitHub Issues
2. Use [GitHub Security Advisories](https://github.com/wioota/devloop/security/advisories/new)
3. Include steps to reproduce the issue
4. Allow 30 days before public disclosure

---

## See Also

- [Configuration Guide](./configuration.md) — Resource limits and agent settings
- [Getting Started](./getting-started.md) — Initial setup and token configuration
- [Architecture Guide](./architecture.md) — System design overview
