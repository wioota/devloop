# Tool Dependency Resolution Design

**Issue:** claude-agents-b0dc
**Date:** 2026-03-13

## Problem

Agents in the marketplace can declare external tool dependencies (e.g. `bandit`, `shellcheck`) but the installer ignores them entirely. Users install an agent and discover it silently fails at runtime because a required tool is missing.

## Approach

Check-only at install time. Installation always succeeds, but immediately prints warnings for any missing tool dependencies with exact remediation commands. No auto-installation of any tools.

## Schema Changes

Add `toolDependencies` to `AgentMetadata` (matching documented format):

```json
{
  "toolDependencies": {
    "bandit": {
      "type": "python",
      "minVersion": "1.7.0",
      "package": "bandit"
    },
    "shellcheck": {
      "type": "binary",
      "minVersion": "0.8.0",
      "install": "apt-get install shellcheck"
    }
  }
}
```

Supported types: `python`, `binary`, `npm-global`, `venv`, `docker`.

## Components

### `ToolDependency` dataclass (metadata.py)
Fields: `name`, `type`, `min_version` (optional), `package` (optional), `install` (optional hint).

### `ToolDependencyChecker` (new file: `marketplace/tool_checker.py`)
- `check(deps) -> list[ToolCheckResult]` — checks all deps, returns results
- Per-type detection:
  - `binary` — `shutil.which(name)`
  - `python` — `importlib.metadata.version(package)`
  - `npm-global` — `shutil.which(name)`
  - `venv` — `shutil.which(name)` within active venv
  - `docker` — `shutil.which('docker')` + `docker image inspect`
- Version checking via `--version` flag parsing (best-effort), `importlib.metadata` for Python packages
- Returns: present/missing, found version, required version, remediation command

### Integration (`installer.py`)
After `_install_agent()` succeeds, call checker on `agent.tool_dependencies`. If any missing, log warnings with remediation commands. Return success regardless.

## Data Flow

```
install()
  └─ resolve_dependencies()
  └─ _install_agent()  ← writes metadata, records install
  └─ check_tool_deps() ← new step
       └─ ToolDependencyChecker.check()
       └─ [missing deps] → print warnings + remediation commands
  └─ return (True, success_message + warnings)
```

## Error Handling

- Tool check failures (e.g. permission errors running `--version`) are caught and treated as "unable to verify" — reported as a warning, not a failure
- Missing `install` hint: print generic message ("install <name> using your system package manager")
- Version parse failures: report tool as present but version unverifiable

## Testing

- Unit tests for `ToolDependencyChecker` with mocked `shutil.which` and `importlib.metadata`
- One test per dependency type (python, binary, npm-global, docker)
- Integration test: install mock agent with tool deps, assert warning output, assert install succeeds
