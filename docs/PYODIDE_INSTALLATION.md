# Pyodide Installation Guide

## Overview

Pyodide provides cross-platform Python sandboxing via WebAssembly for secure agent execution.

## Requirements

- Node.js 18+ (system dependency)

## Installation

### Ubuntu/Debian

```bash
# Install Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version  # Should be 18.x or higher
```

### macOS

```bash
# Install Node.js via Homebrew
brew install node@18

# Verify installation
node --version
```

### Windows

Download and install from [nodejs.org](https://nodejs.org/)

## Verification

```bash
# DevLoop will automatically detect Pyodide capability
devloop init /path/to/project
```

## POC Mode

DevLoop includes a proof-of-concept mode that works without full Pyodide installation for testing purposes.

## Troubleshooting

### Node.js version too old

```bash
# Check version
node --version

# Upgrade Node.js (Ubuntu)
sudo apt-get update
sudo apt-get install -y nodejs

# Upgrade Node.js (macOS)
brew upgrade node
```

### Pyodide not detected

DevLoop will warn during `devloop init` if Pyodide is unavailable and provide installation instructions.

## See Also

- [README.md](../README.md#installation) - Main installation guide
- [configuration.md](./configuration.md) - Agent configuration
