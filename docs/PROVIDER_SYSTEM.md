# Provider System Documentation

## Overview

DevLoop uses a provider abstraction layer for CI/CD and package registries.

## Supported CI Platforms

- **GitHub Actions** - via `gh` CLI
- **GitLab CI/CD** - via `glab` CLI
- **Jenkins** - via REST API
- **CircleCI** - via API v2
- **Custom CI** - manual configuration

## Supported Registries

- **PyPI** - via Poetry or Twine
- **npm** - via npm CLI
- **Docker Registry** - via Docker CLI
- **GitHub Releases** - via `gh` CLI
- **Custom Registries** - manual configuration

## Release Workflow

```bash
# Check release readiness
devloop release check 1.2.3

# Publish release
devloop release publish 1.2.3

# Specify providers explicitly
devloop release publish 1.2.3 --ci github --registry pypi
```

## Provider Auto-Detection

DevLoop automatically detects your CI and registry:

```bash
# Debug provider detection
devloop release debug
```

## See Also

- [RELEASE_PROCESS.md](../RELEASE_PROCESS.md) - Complete release workflow
- [CLI_REFERENCE.md](../CLI_REFERENCE.md) - Command reference
