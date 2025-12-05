# Hybrid Sandbox Architecture Design

**Issue:** claude-agents-3yi (P0 Critical)
**Branch:** feature/hybrid-sandbox-isolation
**Goal:** Implement best-of-both-worlds sandboxing using Capsule (WASM) + Bubblewrap (Linux)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent Manager                            │
│                  (Orchestration Layer)                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ├──────────────────┬──────────────────────┐
                     │                  │                      │
         ┌───────────▼─────────┐  ┌────▼──────────┐  ┌────────▼─────────┐
         │  Sandbox Executor   │  │   Sandbox     │  │   Sandbox        │
         │    (Abstract)       │  │  Executor     │  │  Executor        │
         └───────────┬─────────┘  │  (Abstract)   │  │  (Abstract)      │
                     │            └───────────────┘  └──────────────────┘
         ┌───────────┴──────────┐
         │                      │
    ┌────▼─────────┐    ┌──────▼────────┐
    │   Capsule    │    │  Bubblewrap   │
    │   Sandbox    │    │   Sandbox     │
    │   (WASM)     │    │   (Linux)     │
    └──────────────┘    └───────────────┘
         │                      │
    ┌────▼─────────┐    ┌──────▼────────┐
    │ Pure Python  │    │ Tool-Dependent│
    │   Agents     │    │    Agents     │
    │              │    │               │
    │ • type_check │    │ • linter      │
    │ • formatter  │    │ • git_commit  │
    │ • security   │    │ • ci_monitor  │
    │ • complexity │    │               │
    └──────────────┘    └───────────────┘
```

## Agent Classification

### Capsule-Compatible (Pure Python - WASM Isolation)

| Agent | Pure Python? | External Tools | Sandbox Mode |
|-------|-------------|----------------|--------------|
| **type_checker** | ✅ (mypy) | None | Capsule/WASM |
| **formatter** | ✅ (black) | None | Capsule/WASM |
| **security_scanner** | ✅ (bandit) | None | Capsule/WASM |
| **performance_profiler** | ✅ (radon) | None | Capsule/WASM |

### Bubblewrap-Required (Native Tools - Linux Isolation)

| Agent | Pure Python? | External Tools | Sandbox Mode |
|-------|-------------|----------------|--------------|
| **linter** | ❌ | ruff (native) | Bubblewrap |
| **git_commit_assistant** | ❌ | git (native) | Bubblewrap |
| **ci_monitor** | ⚠️ | gh CLI | Bubblewrap |
| **test_runner** | ⚠️ | pytest (Python) | Capsule* |
| **snyk** | ❌ | snyk (native) | Bubblewrap |

*pytest could run in Capsule if all test dependencies are WASM-compatible

## Component Design

### 1. Base Abstraction Layer

```python
# src/devloop/security/sandbox.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
import asyncio


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""
    mode: Literal["capsule", "bubblewrap", "seccomp", "none"]
    max_memory_mb: int = 500
    max_cpu_percent: int = 25
    timeout_seconds: int = 30
    allowed_tools: List[str] = None
    allowed_network_domains: List[str] = None
    allowed_env_vars: List[str] = None

    def __post_init__(self):
        if self.allowed_tools is None:
            self.allowed_tools = DEFAULT_ALLOWED_TOOLS


@dataclass
class SandboxResult:
    """Result from sandbox execution."""
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    memory_peak_mb: float
    cpu_usage_percent: float
    fuel_consumed: Optional[int] = None  # WASM-specific


class SandboxExecutor(ABC):
    """Abstract base for all sandbox implementations."""

    def __init__(self, config: SandboxConfig):
        self.config = config

    @abstractmethod
    async def execute(
        self,
        cmd: List[str],
        cwd: Path,
        env: Optional[Dict[str, str]] = None
    ) -> SandboxResult:
        """Execute command in sandbox."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this sandbox implementation is available."""
        pass

    @abstractmethod
    def validate_command(self, cmd: List[str]) -> bool:
        """Validate command against whitelist."""
        pass


DEFAULT_ALLOWED_TOOLS = [
    "python3", "python",
    "git",
    "ruff", "black", "mypy", "bandit", "radon",
    "pytest",
    "eslint", "prettier",
    "snyk",
    "gh",
]
```

### 2. Capsule Implementation

```python
# src/devloop/security/capsule_sandbox.py

import capsule  # Will be available in Jan 2025
from devloop.security.sandbox import SandboxExecutor, SandboxResult, SandboxConfig


class CapsuleSandbox(SandboxExecutor):
    """WASM-based sandbox using Capsule runtime."""

    def __init__(self, config: SandboxConfig):
        super().__init__(config)
        self.runtime = None

    async def is_available(self) -> bool:
        """Check if Capsule is installed."""
        try:
            import capsule
            return True
        except ImportError:
            return False

    def validate_command(self, cmd: List[str]) -> bool:
        """Validate command is Python-based (no native binaries)."""
        executable = cmd[0]

        # Capsule can only run Python code or WASM binaries
        if executable not in ["python3", "python"]:
            return False

        # Check if the Python module is allowed
        if "-m" in cmd:
            module_idx = cmd.index("-m") + 1
            module_name = cmd[module_idx]
            return module_name in self.config.allowed_tools

        return True

    async def execute(
        self,
        cmd: List[str],
        cwd: Path,
        env: Optional[Dict[str, str]] = None
    ) -> SandboxResult:
        """Execute Python code in WASM sandbox."""

        if not self.validate_command(cmd):
            raise ValueError(f"Command not allowed in Capsule: {cmd[0]}")

        # Convert command to Capsule task
        # This is a placeholder - actual implementation depends on Capsule API
        @capsule.task(
            compute=self._compute_tier(),
            ram=f"{self.config.max_memory_mb}MB",
            timeout=f"{self.config.timeout_seconds}s",
            allow_network=self.config.allowed_network_domains,
            allow_env=self.config.allowed_env_vars or [],
        )
        async def run_agent_code():
            # Execute the Python code in isolated WASM context
            # Implementation details depend on Capsule's Python API
            pass

        # Execute and capture results
        start_time = asyncio.get_event_loop().time()
        result = await run_agent_code()
        duration = (asyncio.get_event_loop().time() - start_time) * 1000

        return SandboxResult(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            duration_ms=int(duration),
            memory_peak_mb=result.peak_memory_mb,
            cpu_usage_percent=0,  # Not applicable in WASM
            fuel_consumed=result.fuel_consumed,
        )

    def _compute_tier(self) -> str:
        """Map CPU percent to Capsule compute tier."""
        if self.config.max_cpu_percent <= 10:
            return "LIGHT"
        elif self.config.max_cpu_percent <= 25:
            return "MEDIUM"
        else:
            return "HEAVY"
```

### 3. Bubblewrap Implementation

```python
# src/devloop/security/bubblewrap_sandbox.py

import asyncio
import shutil
from pathlib import Path
from devloop.security.sandbox import SandboxExecutor, SandboxResult, SandboxConfig


class BubblewrapSandbox(SandboxExecutor):
    """Linux namespace-based sandbox using Bubblewrap."""

    async def is_available(self) -> bool:
        """Check if bwrap is installed."""
        return shutil.which("bwrap") is not None

    def validate_command(self, cmd: List[str]) -> bool:
        """Validate command against whitelist."""
        executable = cmd[0]

        # Check if tool is whitelisted
        if executable not in self.config.allowed_tools:
            return False

        # Verify executable exists and is not a symlink to unexpected location
        exe_path = shutil.which(executable)
        if not exe_path:
            return False

        # Additional security: verify it's in expected system paths
        allowed_paths = ["/usr/bin", "/usr/local/bin", "/bin"]
        if not any(exe_path.startswith(p) for p in allowed_paths):
            return False

        return True

    async def execute(
        self,
        cmd: List[str],
        cwd: Path,
        env: Optional[Dict[str, str]] = None
    ) -> SandboxResult:
        """Execute command in Bubblewrap sandbox."""

        if not self.validate_command(cmd):
            raise ValueError(f"Command not allowed: {cmd[0]}")

        # Build bwrap command with strict isolation
        bwrap_cmd = [
            "bwrap",
            # Filesystem isolation
            "--ro-bind", "/usr", "/usr",
            "--ro-bind", "/bin", "/bin",
            "--ro-bind", "/lib", "/lib",
            "--ro-bind", "/lib64", "/lib64",
            "--bind", str(cwd), str(cwd),  # Read-write access to project dir
            "--dev", "/dev",
            "--proc", "/proc",
            "--tmpfs", "/tmp",
            # Network isolation (disable by default)
            "--unshare-net",
            # Process isolation
            "--unshare-pid",
            "--unshare-ipc",
            "--unshare-uts",
            # Die with parent (prevent orphans)
            "--die-with-parent",
            # Working directory
            "--chdir", str(cwd),
            # Execute command
            *cmd
        ]

        # Add environment variables
        for key, value in (env or {}).items():
            if key in (self.config.allowed_env_vars or []):
                bwrap_cmd.insert(1, "--setenv")
                bwrap_cmd.insert(2, key)
                bwrap_cmd.insert(3, value)

        # Execute with resource limits
        start_time = asyncio.get_event_loop().time()

        process = await asyncio.create_subprocess_exec(
            *bwrap_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            # TODO: Add resource limits via cgroups
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout_seconds
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"Command exceeded {self.config.timeout_seconds}s timeout")

        duration = (asyncio.get_event_loop().time() - start_time) * 1000

        return SandboxResult(
            stdout=stdout.decode() if stdout else "",
            stderr=stderr.decode() if stderr else "",
            exit_code=process.returncode or 0,
            duration_ms=int(duration),
            memory_peak_mb=0,  # TODO: Get from cgroups
            cpu_usage_percent=0,  # TODO: Get from cgroups
        )
```

### 4. Sandbox Factory

```python
# src/devloop/security/factory.py

from typing import Optional
from devloop.security.sandbox import SandboxExecutor, SandboxConfig
from devloop.security.capsule_sandbox import CapsuleSandbox
from devloop.security.bubblewrap_sandbox import BubblewrapSandbox
from devloop.security.seccomp_sandbox import SeccompSandbox  # Fallback


async def create_sandbox(
    config: SandboxConfig,
    agent_type: str
) -> SandboxExecutor:
    """
    Create appropriate sandbox based on config and agent requirements.

    Auto-selects best available sandbox:
    1. Capsule for pure-Python agents (if available)
    2. Bubblewrap for tool-dependent agents (if available)
    3. Seccomp as fallback
    4. None mode if explicitly disabled
    """

    # Pure Python agents prefer Capsule
    pure_python_agents = {
        "type_checker", "formatter", "security_scanner",
        "performance_profiler", "test_runner"
    }

    if agent_type in pure_python_agents and config.mode in ["capsule", "auto"]:
        capsule = CapsuleSandbox(config)
        if await capsule.is_available():
            return capsule

    # Tool-dependent agents need Bubblewrap
    if config.mode in ["bubblewrap", "auto"]:
        bwrap = BubblewrapSandbox(config)
        if await bwrap.is_available():
            return bwrap

    # Fallback to seccomp
    if config.mode in ["seccomp", "auto"]:
        return SeccompSandbox(config)

    # No sandbox (development only)
    if config.mode == "none":
        from devloop.security.no_sandbox import NoSandbox
        return NoSandbox(config)

    raise RuntimeError("No suitable sandbox implementation available")
```

## Configuration Schema

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
  },
  "agents": {
    "type_checker": {
      "sandbox": {
        "mode": "capsule",
        "max_memory_mb": 256
      }
    },
    "linter": {
      "sandbox": {
        "mode": "bubblewrap",
        "allowed_tools": ["ruff"]
      }
    }
  }
}
```

## Migration Path

### Phase 1: Foundation (Week 1)
- ✅ Base abstraction layer
- ✅ Bubblewrap implementation (works today)
- ✅ Seccomp fallback
- ✅ Tool whitelisting

### Phase 2: WASM Integration (Week 2-3)
- ⏳ Capsule integration (wait for Jan 2025 Python support)
- ⏳ Agent classification logic
- ⏳ Auto-selection factory

### Phase 3: Testing & Hardening (Week 4)
- 🔒 Security test suite (escape attempts)
- 🔒 Malicious config tests
- 🔒 Resource exhaustion tests
- 🔒 Performance benchmarks

### Phase 4: Documentation & Rollout
- 📖 Migration guide
- 📖 Security best practices
- 📖 Troubleshooting guide

## Security Test Scenarios

```python
# tests/security/test_sandbox_escapes.py

async def test_shell_injection_blocked():
    """Ensure shell=True is never used."""
    # Attempt: cmd = ["bash", "-c", "cat /etc/passwd"]
    # Expected: Command rejected (bash not whitelisted)
    pass

async def test_symlink_attack_blocked():
    """Ensure symlinks can't point to sensitive files."""
    # Attempt: Create symlink to /etc/passwd, try to read
    # Expected: Isolated filesystem prevents access
    pass

async def test_resource_limits_enforced():
    """Ensure CPU/memory limits are enforced."""
    # Attempt: Spawn infinite loop or memory bomb
    # Expected: Process killed by sandbox
    pass

async def test_network_isolation():
    """Ensure network access is restricted."""
    # Attempt: Connect to arbitrary domain
    # Expected: Connection blocked (unless allowlisted)
    pass

async def test_malicious_pyproject_toml():
    """Ensure malicious build hooks are sandboxed."""
    # Attempt: pyproject.toml with [tool.poetry.scripts]
    #          malicious = "rm -rf /"
    # Expected: Command blocked or executed in sandbox
    pass
```

## Performance Expectations

| Sandbox | Startup | Overhead | Isolation |
|---------|---------|----------|-----------|
| Capsule | ~10ms | ~12% | ⭐⭐⭐⭐⭐ |
| Bubblewrap | ~50ms | ~5% | ⭐⭐⭐⭐ |
| Seccomp | ~1ms | ~2% | ⭐⭐⭐ |
| None | 0ms | 0% | ❌ |

## Success Metrics

- ✅ Zero subprocess calls with `shell=True`
- ✅ All tools whitelisted and validated
- ✅ Resource limits enforced (no runaway processes)
- ✅ Network access controlled
- ✅ Malicious configs cannot escape sandbox
- ✅ Performance overhead < 15%
- ✅ Agent execution time increase < 100ms

## Open Questions

1. **Capsule API:** Exact Python API not yet released (Jan 2025)
2. **WASM Package Availability:** Which Python packages work in Capsule?
3. **Hybrid Communication:** How do Capsule agents report findings back?
4. **Git in WASM:** Can we use isomorphic-git for git operations in Capsule?
5. **Testing Infrastructure:** How to test WASM sandboxing in CI?

## Next Steps

1. Implement base abstraction + Bubblewrap (works immediately)
2. Add comprehensive security tests
3. Monitor Capsule Python support launch (Jan 2025)
4. Integrate Capsule when available
5. Benchmark and optimize
