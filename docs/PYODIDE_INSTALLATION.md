# Pyodide Installation Guide

Setting up Pyodide WASM sandbox for DevLoop (cross-platform Python sandboxing).

## What is Pyodide?

Pyodide enables running Python code in isolation using WebAssembly (WASM). This provides an additional security layer for sandboxing untrusted code in DevLoop agents.

**Benefits:**
- Cross-platform Python sandboxing
- No native binary dependencies (uses WASM)
- Safe code execution without full OS access
- Available on all major platforms

## Prerequisites

- **Node.js 18+** (system dependency)
- Python 3.11+
- npm (comes with Node.js)

## Installation

### Step 1: Check Node.js Installation

```bash
node --version    # Should be 18.x or higher
npm --version     # Should be 8.x or higher
```

If not installed:
- **macOS**: `brew install node`
- **Ubuntu/Debian**: `sudo apt-get install nodejs npm`
- **Windows**: Download from https://nodejs.org/

### Step 2: Install Pyodide Support

Via pip with DevLoop extras:
```bash
pip install devloop[pyodide]
```

Or via npm (for Pyodide development):
```bash
npm install -g pyodide
```

### Step 3: Verify Installation

```bash
python -c "from pyodide import create_runtime; print('Pyodide ready')"
```

### Step 4: Enable in Configuration

Update `.devloop/agents.json`:

```json
{
  "global": {
    "sandbox": {
      "enabled": true,
      "engine": "pyodide",
      "timeout": 5000,
      "memory_limit_mb": 256
    }
  }
}
```

## Proof-of-Concept Mode (No Installation)

For testing without full installation:

```bash
# Run POC mode
devloop poc run --sandbox pyodide --code "print('hello')"

# No additional setup required - Pyodide POC works out of box
```

## Using Sandboxed Code

Once installed, DevLoop agents can safely execute code:

```python
from devloop.core.sandbox import run_in_sandbox

# Execute code safely
result = await run_in_sandbox("""
import os
print(f"Current user: {os.getenv('USER')}")
# Access to OS is restricted
""", engine='pyodide')
```

## Troubleshooting

### "Node.js not found"

Install Node.js from https://nodejs.org/ or via your package manager.

### "Pyodide module not found"

```bash
# Reinstall with extra
pip install --upgrade devloop[pyodide]
```

### Sandbox times out

Increase timeout in configuration:
```json
{
  "global": {
    "sandbox": {
      "timeout": 10000
    }
  }
}
```

## Performance

Pyodide WASM sandbox has minimal overhead:
- **Startup**: ~100ms per sandbox
- **Execution**: Near-native speed (WASM JIT compiled)
- **Memory**: ~50MB overhead per runtime

For performance-sensitive code, consider disabling sandboxing or increasing memory limits.

## Security Model

Pyodide sandbox provides:
- **Code isolation**: No direct filesystem access
- **Memory isolation**: Separate heap per runtime
- **I/O restrictions**: Controlled stdin/stdout/stderr
- **Import restrictions**: Limited to safe stdlib modules

**Not suitable for:**
- Arbitrary file system operations
- Network access
- Native C extension execution
- System call access

## Advanced Configuration

### Resource Limits

```json
{
  "global": {
    "sandbox": {
      "engine": "pyodide",
      "timeout": 5000,
      "memory_limit_mb": 256,
      "max_cpus": 1,
      "cpu_throttle": 50
    }
  }
}
```

### Custom Environment

```json
{
  "global": {
    "sandbox": {
      "env_vars": {
        "SAFE_VAR": "value"
      },
      "disable_modules": ["os", "subprocess"]
    }
  }
}
```

## See Also

- [DevLoop README](../README.md) - Main documentation
- [AGENTS.md](../AGENTS.md) - System architecture
- [Pyodide Documentation](https://pyodide.org/) - Official Pyodide docs
