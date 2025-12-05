# Pyodide Sandbox Installation Guide

This guide covers installing the optional Pyodide WASM sandbox for cross-platform Python execution.

## Quick Start

### Option 1: POC Mode (Default - No Installation Required)

The Pyodide sandbox works in POC mode by default without any additional dependencies. This allows testing the integration without the 30MB Pyodide download.

```bash
# No additional installation needed
devloop watch .
```

**POC mode features:**
- ✅ Tests PyodideSandbox integration
- ✅ Validates commands and configuration
- ✅ Returns simulation results
- ❌ Doesn't execute actual Python code in WASM

### Option 2: Full Pyodide Mode (Real WASM Execution)

For production use with actual WASM-isolated Python execution:

#### Prerequisites

1. **Node.js 18+** (system dependency)

```bash
# Check if Node.js is installed
node --version  # Should be v18.0.0 or higher

# Install Node.js if needed:
# Ubuntu/Debian:
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# macOS:
brew install node

# Windows:
# Download from https://nodejs.org/
```

#### Install Pyodide

```bash
# Navigate to DevLoop security module
cd $(python -c "import devloop.security; import os; print(os.path.dirname(devloop.security.__file__))")

# Install Pyodide npm package
npm install

# Verify installation
node -e "console.log(require('pyodide') ? '✓ Pyodide installed' : '✗ Failed')"
```

#### Disable POC Mode

Remove the POC mode environment variable to use real Pyodide:

```bash
# In your shell profile (~/.bashrc, ~/.zshrc, etc.)
# Make sure PYODIDE_POC_MODE is NOT set

# Verify POC mode is disabled
echo $PYODIDE_POC_MODE  # Should be empty
```

## Automated Installation Script

For convenience, use the automated installation script:

```bash
# Run DevLoop's Pyodide installer
devloop install pyodide

# Or use the standalone script
python -m devloop.scripts.install_pyodide
```

This script will:
1. Check for Node.js (and guide installation if missing)
2. Install Pyodide npm package in the correct location
3. Verify the installation
4. Update configuration

## Verification

Test that Pyodide sandbox is working:

```bash
# Check sandbox availability
python -c "
import asyncio
from devloop.security.pyodide_sandbox import PyodideSandbox
from devloop.security.sandbox import SandboxConfig

async def check():
    sandbox = PyodideSandbox(SandboxConfig())
    available = await sandbox.is_available()
    print(f'Pyodide sandbox: {\"✓ Available\" if available else \"✗ Not available\"}')

asyncio.run(check())
"
```

## Configuration

Enable Pyodide in `.devloop/agents.json`:

```json
{
  "agents": {
    "type-checker": {
      "sandbox": {
        "mode": "auto",
        "preferredModes": ["pyodide", "bubblewrap", "none"]
      }
    }
  }
}
```

**Sandbox selection priority:**
1. **pyodide** - If Node.js + Pyodide installed
2. **bubblewrap** - If Linux with bwrap
3. **none** - Fallback (whitelist + timeout only)

## Troubleshooting

### Node.js Not Found

**Error:** `Pyodide sandbox not available - Node.js not found`

**Solution:**
```bash
# Install Node.js (see Prerequisites section)
node --version  # Verify installation
```

### Pyodide Runner Not Found

**Error:** `Pyodide runner not found at .../pyodide_runner.js`

**Solution:**
```bash
# Reinstall DevLoop
pip install --force-reinstall devloop

# Or check file exists
ls -la $(python -c "import devloop.security; import os; print(os.path.dirname(devloop.security.__file__))")/pyodide_runner.js
```

### Pyodide Package Not Found

**Error:** `Cannot find module 'pyodide'`

**Solution:**
```bash
# Install Pyodide in security module directory
cd $(python -c "import devloop.security; import os; print(os.path.dirname(devloop.security.__file__))")
npm install pyodide
```

### POC Mode Not Disabling

**Issue:** Pyodide still running in POC mode even with npm package installed

**Solution:**
```bash
# Check environment variable
echo $PYODIDE_POC_MODE  # Should be empty

# If set, unset it
unset PYODIDE_POC_MODE

# Or restart your shell
exec $SHELL
```

## Performance

### Cold Start Times

| Mode | First Execution | Subsequent |
|------|----------------|------------|
| **POC Mode** | ~50ms | ~50ms |
| **Full Pyodide** | 2-3 seconds | ~500ms |
| **Bubblewrap** | ~100ms | ~100ms |

### Memory Usage

- **POC Mode:** ~10MB (Node.js overhead)
- **Full Pyodide:** ~50MB (Pyodide runtime + code)
- **Bubblewrap:** ~5MB (minimal overhead)

## Uninstallation

Remove Pyodide to save disk space (30MB):

```bash
# Navigate to security module
cd $(python -c "import devloop.security; import os; print(os.path.dirname(devloop.security.__file__))")

# Remove Pyodide
rm -rf node_modules package-lock.json

# Verify removal
ls node_modules  # Should not exist
```

DevLoop will automatically fall back to POC mode or other sandbox methods.

## When to Use Pyodide

**Use Pyodide when:**
- ✅ Cross-platform support needed (Windows, macOS, Linux)
- ✅ WASM-level isolation required
- ✅ Python-only workloads (linting, type checking)
- ✅ Can tolerate 2-3s cold start

**Use Bubblewrap when:**
- ✅ Linux-only deployment
- ✅ Need to run system tools (git, ruff, etc.)
- ✅ Require <100ms startup time
- ✅ Need native performance

**Use POC mode when:**
- ✅ Testing DevLoop integration
- ✅ CI/CD environments without Node.js
- ✅ Don't need actual WASM execution

## Advanced Configuration

### Custom Pyodide CDN

Override Pyodide CDN URL in `pyodide_runner.js`:

```javascript
const pyodide = await loadPyodide({
    indexURL: "https://your-cdn.com/pyodide/v0.25.0/full/"
});
```

### Pre-load Python Packages

Add common packages to Pyodide startup:

```javascript
// In pyodide_runner.js, after loadPyodide()
await pyodide.loadPackage(['numpy', 'pandas']);
```

### Memory Limits

Configure Node.js heap limits:

```bash
# Set max heap size (e.g., 512MB)
NODE_OPTIONS="--max-old-space-size=512" devloop watch .
```

## Docker Integration

Add to your Dockerfile:

```dockerfile
FROM python:3.12-slim

# Install Node.js
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean

# Install DevLoop
RUN pip install devloop

# Install Pyodide
RUN cd $(python -c "import devloop.security; import os; print(os.path.dirname(devloop.security.__file__))") \
    && npm install

# Verify installation
RUN python -c "import asyncio; from devloop.security.pyodide_sandbox import PyodideSandbox; from devloop.security.sandbox import SandboxConfig; asyncio.run(PyodideSandbox(SandboxConfig()).is_available())"

CMD ["devloop", "watch", "."]
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/wioota/devloop/issues
- Documentation: https://github.com/wioota/devloop#readme
- Design Doc: docs/PYODIDE_SANDBOX_DESIGN.md
