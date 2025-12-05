# Pyodide Sandbox Design

**Status:** Phase 3 Implementation
**Date:** 2025-12-05
**Author:** DevLoop Team

## Overview

Pyodide-based sandbox provides WASM-isolated Python code execution as an alternative to Bubblewrap (Linux namespaces) and future Capsule runtime integration.

## Why Pyodide?

### Selected Over Alternatives

| Solution | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Pyodide** | ✅ Open source (MPL 2.0)<br>✅ Runs locally<br>✅ True WASM sandboxing<br>✅ Cross-platform | ⚠️ Slower cold starts<br>⚠️ Larger binary (~30MB) | **SELECTED** |
| Cloudflare workerd | ✅ Open source<br>✅ Fast cold starts | ❌ "Not a hardened sandbox"<br>❌ Complex integration | Rejected |
| Wasmer Edge | ✅ Fast performance | ❌ Cloud-first (not local)<br>❌ SDK runs WASM, not Python in WASM | Rejected |
| Capsule | ✅ Purpose-built | ❌ Python support unavailable | Future option |

### Key Advantages

1. **True Sandboxing**: WASM provides memory-safe isolation
2. **Local Execution**: No cloud dependencies
3. **Cross-Platform**: Works on Linux, macOS, Windows
4. **Open Source**: Full control over runtime
5. **Package Support**: NumPy, Pandas, scikit-learn, etc.

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────┐
│           DevLoop Agent (Python)                     │
│  ┌────────────────────────────────────────────┐    │
│  │      PyodideSandbox (SandboxExecutor)      │    │
│  │                                             │    │
│  │  1. Validate command                       │    │
│  │  2. Prepare execution environment          │    │
│  │  3. Launch Node.js subprocess              │    │
│  └──────────────┬──────────────────────────────┘    │
│                 │                                    │
│                 │ IPC (stdin/stdout/stderr)          │
│                 ▼                                    │
│  ┌────────────────────────────────────────────┐    │
│  │       Node.js Process                       │    │
│  │  ┌──────────────────────────────────────┐  │    │
│  │  │    pyodide_runner.js                 │  │    │
│  │  │                                       │  │    │
│  │  │  1. Load Pyodide runtime             │  │    │
│  │  │  2. Setup virtual filesystem         │  │    │
│  │  │  3. Configure resource limits        │  │    │
│  │  │  4. Execute Python code              │  │    │
│  │  │  5. Capture output and metrics       │  │    │
│  │  └──────────────────────────────────────┘  │    │
│  │                                             │    │
│  │           Pyodide WASM Runtime              │    │
│  │  ┌──────────────────────────────────────┐  │    │
│  │  │  CPython Interpreter (WASM)          │  │    │
│  │  │  - Isolated memory space             │  │    │
│  │  │  - Virtual filesystem (MEMFS)        │  │    │
│  │  │  - No network access by default      │  │    │
│  │  └──────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

### Data Flow

1. **Command Validation**: PyodideSandbox validates Python execution request
2. **Environment Setup**: Prepare virtual filesystem with code and dependencies
3. **Process Launch**: Spawn Node.js subprocess running pyodide_runner.js
4. **WASM Execution**: Pyodide loads and executes Python in isolated WASM environment
5. **Result Collection**: Capture stdout/stderr, metrics, exit code
6. **Cleanup**: Terminate Node.js process, cleanup temp files

## Implementation

### PyodideSandbox Class

```python
class PyodideSandbox(SandboxExecutor):
    """WASM-based sandbox using Pyodide runtime.

    Provides cross-platform Python code execution in isolated WASM environment.
    """

    def __init__(self, config: SandboxConfig):
        super().__init__(config)
        self._node_path: Optional[str] = None
        self._pyodide_runner: Optional[Path] = None

    async def is_available(self) -> bool:
        """Check if Node.js and pyodide_runner.js are available."""
        # Check for Node.js
        # Check for pyodide_runner.js script
        # Verify Pyodide can be loaded

    def validate_command(self, cmd: List[str]) -> bool:
        """Validate Python execution command."""
        # Only allow python3/python commands
        # Validate script path exists
        # Check against whitelist

    async def execute(
        self, cmd: List[str], cwd: Path, env: Optional[Dict[str, str]] = None
    ) -> SandboxResult:
        """Execute Python code in Pyodide WASM sandbox."""
        # 1. Prepare execution environment
        # 2. Launch Node.js subprocess with pyodide_runner.js
        # 3. Monitor execution with timeout
        # 4. Collect output and metrics
        # 5. Return SandboxResult
```

### Pyodide Runner (Node.js)

```javascript
// pyodide_runner.js
const { loadPyodide } = require('pyodide');

async function runPython(code, options) {
    // Load Pyodide runtime
    const pyodide = await loadPyodide({
        indexURL: "https://cdn.jsdelivr.net/pyodide/v0.25.0/full/"
    });

    // Setup virtual filesystem
    pyodide.FS.writeFile("/tmp/script.py", code);

    // Configure resource limits (via V8 flags or monitoring)

    // Execute Python code
    const result = await pyodide.runPythonAsync(code);

    // Return output and metrics
    return {
        stdout: result,
        stderr: "",
        exitCode: 0,
        durationMs: Date.now() - startTime,
        memoryPeakMb: process.memoryUsage().heapUsed / 1024 / 1024
    };
}
```

## Security Model

### Isolation Layers

1. **WASM Memory Isolation**: Separate memory space for Python execution
2. **Virtual Filesystem**: MEMFS prevents access to host filesystem
3. **No Network Access**: Network APIs disabled by default
4. **Resource Limits**:
   - Memory: Enforced via Node.js heap limits
   - CPU: Enforced via timeout
   - No subprocess spawning capability

### Threat Model

**Protected Against:**
- ✅ Filesystem access outside virtual environment
- ✅ Network access to external resources
- ✅ Memory bombs (via heap limits)
- ✅ Infinite loops (via timeout)
- ✅ Malicious imports (only bundled packages available)

**Limitations:**
- ⚠️ CPU exhaustion within timeout window (hard to prevent in WASM)
- ⚠️ Side-channel attacks (WASM Spectre mitigations apply)

### Comparison with Bubblewrap

| Feature | Bubblewrap | Pyodide |
|---------|------------|---------|
| **Filesystem Isolation** | Linux namespaces | Virtual filesystem (MEMFS) |
| **Network Isolation** | `--unshare-net` | No network APIs |
| **Process Isolation** | PID namespaces | Single-process WASM |
| **Resource Limits** | cgroups v2 | Node.js heap limits |
| **Platform Support** | Linux only | Cross-platform |
| **Performance** | Native speed | ~1.5-2x overhead |
| **Package Support** | All system packages | WASM-compiled packages only |

## Performance Characteristics

### Benchmarks (Expected)

| Metric | Target | Notes |
|--------|--------|-------|
| **Cold Start** | <3s | Initial Pyodide load |
| **Warm Start** | <500ms | Cached Pyodide runtime |
| **Execution Overhead** | <2x | Compared to native Python |
| **Memory Overhead** | ~50MB | Pyodide runtime + code |

### Optimization Strategies

1. **Runtime Caching**: Keep Pyodide loaded in long-running Node.js process
2. **Package Pre-loading**: Bundle common packages (NumPy, etc.)
3. **Memory Snapshots**: Serialize loaded runtime state (future)

## Configuration

### agents.json Integration

```json
{
  "agents": {
    "type-checker": {
      "sandbox": {
        "mode": "auto",
        "preferredModes": ["pyodide", "bubblewrap", "none"],
        "max_memory_mb": 500,
        "timeout_seconds": 30
      }
    }
  }
}
```

### Fallback Strategy

1. Try Pyodide (if Node.js available)
2. Fall back to Bubblewrap (if Linux)
3. Fall back to NoSandbox (with whitelist + timeout)

## Installation

### Requirements

- Node.js 18+ (for Pyodide runner)
- npm/npx (for Pyodide package)

### Setup Script

```bash
# Install Pyodide in project
npm install pyodide

# Verify installation
node -e "const {loadPyodide} = require('pyodide'); console.log('✓ Pyodide available')"
```

### Package.json

```json
{
  "name": "devloop-pyodide-sandbox",
  "version": "1.0.0",
  "dependencies": {
    "pyodide": "^0.25.0"
  }
}
```

## Testing Strategy

### Unit Tests

```python
# tests/security/test_pyodide_sandbox.py

class TestPyodideSandbox:
    async def test_basic_execution(self):
        """Verify basic Python code execution."""

    async def test_filesystem_isolation(self):
        """Verify no access to host filesystem."""

    async def test_network_isolation(self):
        """Verify network access blocked."""

    async def test_timeout_enforcement(self):
        """Verify timeout kills execution."""

    async def test_memory_limits(self):
        """Verify memory limits enforced."""

    async def test_package_imports(self):
        """Verify NumPy, Pandas import successfully."""
```

### Integration Tests

- Run alongside Bubblewrap to compare results
- Verify fallback mechanism works correctly
- Test with real agent workloads (mypy, etc.)

## Limitations

### Known Issues

1. **Cold Start Time**: 2-3s initial Pyodide load (vs <100ms Bubblewrap)
2. **Package Availability**: Limited to WASM-compiled packages
3. **Binary Size**: ~30MB Pyodide distribution
4. **Resource Monitoring**: Less granular than cgroups

### Not Suitable For

- ❌ Running native Python packages with C extensions (unless WASM-compiled)
- ❌ Subprocess execution (git, etc.) - use Bubblewrap instead
- ❌ Ultra-low latency requirements (<100ms)

## Deployment

### Production Considerations

1. **Package Management**: Pre-install common packages in container image
2. **Runtime Caching**: Use persistent Node.js process for Pyodide
3. **Monitoring**: Track Pyodide initialization failures
4. **Fallback**: Always configure Bubblewrap as fallback on Linux

### Docker Integration

```dockerfile
# Add Node.js and Pyodide to devloop container
FROM python:3.12-slim

# Install Node.js
RUN apt-get update && apt-get install -y nodejs npm

# Install Pyodide
COPY package.json /app/
RUN cd /app && npm install

# Install DevLoop
RUN pip install devloop

CMD ["devloop", "watch", "."]
```

## Future Enhancements

### Phase 3+

1. **Runtime Pooling**: Keep warm Pyodide instances for faster execution
2. **Memory Snapshots**: Serialize loaded runtime state for instant startup
3. **Custom Package Bundles**: Build WASM packages for project dependencies
4. **Streaming I/O**: Support real-time stdout/stderr streaming
5. **Multi-threading**: Use Pyodide workers for parallel execution

### Capsule Migration Path

When Capsule adds Python support:
1. Implement `CapsuleSandbox` with same interface
2. Add to `preferredModes`: `["capsule", "pyodide", "bubblewrap", "none"]`
3. Gradual migration based on performance comparison

## References

- [Pyodide Documentation](https://pyodide.org/en/stable/)
- [Pyodide in Web Workers](https://pyodide.org/en/stable/usage/webworker.html)
- [Sandboxing Python with WASM](https://www.atlantbh.com/sandboxing-python-code-execution-with-wasm/)
- [Python Workers (Cloudflare)](https://blog.cloudflare.com/python-workers/)
- [WASM as a Secure Sandbox](https://www.tspi.at/2025/10/02/wasmsandbox.html)

## Appendix: POC Checklist

- [x] Design document created
- [ ] PyodideSandbox class implemented
- [ ] pyodide_runner.js script created
- [ ] package.json with Pyodide dependency
- [ ] Unit tests for PyodideSandbox
- [ ] Integration with sandbox factory
- [ ] Performance benchmarks
- [ ] Documentation updates
- [ ] Installation script
