# Provider System Documentation

DevLoop uses a provider-agnostic architecture to support multiple CI systems and package registries without vendor lock-in.

## Overview

The provider system consists of:

- **Abstract base classes** - Define interfaces for CI and registry providers
- **Concrete implementations** - Provider-specific implementations
- **Provider manager** - Discovery, registration, and instantiation
- **Auto-detection** - Automatic provider detection based on environment

## Supported CI Providers

DevLoop supports the following CI platforms out of the box:

### GitHub Actions

**CLI Tool**: `gh` (GitHub CLI)

**Detection**: Checks if `gh` is installed and authenticated

**Setup**:
```bash
# Install gh CLI
# macOS
brew install gh

# Linux (Debian/Ubuntu)
sudo apt install gh

# Authenticate
gh auth login
```

**Usage**:
```bash
# Auto-detect
devloop release check 1.2.3

# Explicit
devloop release check 1.2.3 --ci github
```

### GitLab CI

**CLI Tool**: `glab` (GitLab CLI)

**Detection**: Checks if `glab` is installed and authenticated

**Setup**:
```bash
# Install glab CLI
# macOS
brew install glab

# Linux (Debian/Ubuntu)
sudo apt install glab

# Authenticate
glab auth login
```

**Usage**:
```bash
# Auto-detect
devloop release check 1.2.3

# Explicit
devloop release check 1.2.3 --ci gitlab
```

### Jenkins

**API**: Jenkins REST API

**Detection**: Checks for `JENKINS_URL` environment variable and credentials

**Setup**:
```bash
# Set environment variables
export JENKINS_URL="https://jenkins.example.com"
export JENKINS_USER="your-username"
export JENKINS_TOKEN="your-api-token"
export JENKINS_JOB="your-job-name"  # Optional, can be configured per-project
```

**Getting a Jenkins API Token**:
1. Log in to Jenkins
2. Click your name (upper-right corner)
3. Click "Configure"
4. Click "Add new Token" under API Token section
5. Copy the generated token

**Usage**:
```bash
# Auto-detect
devloop release check 1.2.3

# Explicit
devloop release check 1.2.3 --ci jenkins
```

### CircleCI

**API**: CircleCI API v2

**Detection**: Checks for `CIRCLECI_PROJECT_SLUG` and `CIRCLECI_TOKEN` environment variables

**Setup**:
```bash
# Set environment variables
export CIRCLECI_PROJECT_SLUG="gh/username/repo"  # or bb/username/repo for Bitbucket
export CIRCLECI_TOKEN="your-circleci-token"
```

**Getting a CircleCI Token**:
1. Go to CircleCI User Settings
2. Click "Personal API Tokens"
3. Click "Create New Token"
4. Copy the generated token

**Usage**:
```bash
# Auto-detect
devloop release check 1.2.3

# Explicit
devloop release check 1.2.3 --ci circleci
```

## Supported Package Registries

### PyPI

**Tool**: Poetry or Twine

**Detection**: Checks for `pyproject.toml` and Poetry credentials

**Setup**:
```bash
# Configure PyPI token
poetry config pypi-token.pypi "pypi-..."
```

**Usage**:
```bash
# Auto-detect
devloop release publish 1.2.3

# Explicit
devloop release publish 1.2.3 --registry pypi
```

## Auto-Detection

DevLoop automatically detects available providers in the following order:

### CI Provider Detection Priority

1. **GitHub Actions** - If `gh` CLI is available and authenticated
2. **GitLab CI** - If `glab` CLI is available and authenticated
3. **Jenkins** - If `JENKINS_URL` environment variable is set
4. **CircleCI** - If `CIRCLECI_PROJECT_SLUG` environment variable is set

### Registry Provider Detection Priority

1. **PyPI** - If `pyproject.toml` exists and Poetry is configured

## Troubleshooting

### Provider Not Detected

If auto-detection fails, you can:

1. **Check provider availability**:
   ```python
   from devloop.providers import get_provider_manager

   manager = get_provider_manager()

   # List available CI providers
   print(manager.list_ci_providers())

   # List available registry providers
   print(manager.list_registry_providers())
   ```

2. **Test provider manually**:
   ```python
   from devloop.providers import GitHubActionsProvider, GitLabCIProvider

   # Test GitHub Actions
   gh = GitHubActionsProvider()
   print(f"GitHub Actions available: {gh.is_available()}")

   # Test GitLab CI
   gitlab = GitLabCIProvider()
   print(f"GitLab CI available: {gitlab.is_available()}")
   ```

3. **Use explicit provider specification**:
   ```bash
   devloop release check 1.2.3 --ci github
   devloop release check 1.2.3 --ci gitlab
   devloop release check 1.2.3 --ci jenkins
   devloop release check 1.2.3 --ci circleci
   ```

### GitHub Actions Issues

**Problem**: `gh: command not found`

**Solution**: Install GitHub CLI:
```bash
# macOS
brew install gh

# Linux (Debian/Ubuntu)
sudo apt install gh
```

**Problem**: `gh auth status` fails

**Solution**: Authenticate with GitHub:
```bash
gh auth login
```

### GitLab CI Issues

**Problem**: `glab: command not found`

**Solution**: Install GitLab CLI:
```bash
# macOS
brew install glab

# Linux (Debian/Ubuntu)
sudo apt install glab
```

**Problem**: `glab auth status` fails

**Solution**: Authenticate with GitLab:
```bash
glab auth login
```

### Jenkins Issues

**Problem**: "Jenkins is not available"

**Solution**: Ensure environment variables are set:
```bash
export JENKINS_URL="https://jenkins.example.com"
export JENKINS_USER="your-username"
export JENKINS_TOKEN="your-api-token"
export JENKINS_JOB="your-job-name"
```

**Problem**: "Authentication failed"

**Solution**:
- Verify your Jenkins API token is valid
- Check that you have permission to access the job
- Ensure the Jenkins URL is correct (no trailing slash)

### CircleCI Issues

**Problem**: "CircleCI is not available"

**Solution**: Ensure environment variables are set:
```bash
export CIRCLECI_PROJECT_SLUG="gh/username/repo"
export CIRCLECI_TOKEN="your-circleci-token"
```

**Problem**: "Project slug format invalid"

**Solution**: Project slug must be in format:
- `gh/username/repo` for GitHub
- `bb/username/repo` for Bitbucket

## Custom Providers

You can create custom providers by extending the base classes:

### Custom CI Provider

```python
from devloop.providers import CIProvider, WorkflowRun, RunStatus, RunConclusion
from typing import List, Optional
from datetime import datetime

class MyCustomCIProvider(CIProvider):
    def get_status(self, branch: str) -> Optional[WorkflowRun]:
        # Implementation here
        pass

    def list_runs(self, branch: str, limit: int = 10, workflow_name: Optional[str] = None) -> List[WorkflowRun]:
        # Implementation here
        pass

    def get_logs(self, run_id: str) -> Optional[str]:
        # Implementation here
        pass

    def rerun(self, run_id: str) -> bool:
        # Implementation here
        pass

    def cancel(self, run_id: str) -> bool:
        # Implementation here
        pass

    def get_workflows(self) -> List[WorkflowDefinition]:
        # Implementation here
        pass

    def is_available(self) -> bool:
        # Check if provider is available and configured
        pass

    def get_provider_name(self) -> str:
        return "My Custom CI"
```

### Registering Custom Providers

```python
from devloop.providers import get_provider_manager

manager = get_provider_manager()
manager.register_ci_provider("mycustom", MyCustomCIProvider)
```

Then use it:
```bash
devloop release check 1.2.3 --ci mycustom
```

## API Reference

### CIProvider

Abstract base class for all CI providers.

**Methods**:
- `get_status(branch: str) -> Optional[WorkflowRun]` - Get latest run for a branch
- `list_runs(branch: str, limit: int, workflow_name: Optional[str]) -> List[WorkflowRun]` - List runs
- `get_logs(run_id: str) -> Optional[str]` - Get logs for a run
- `rerun(run_id: str) -> bool` - Rerun a workflow
- `cancel(run_id: str) -> bool` - Cancel a running workflow
- `get_workflows() -> List[WorkflowDefinition]` - Get workflow definitions
- `is_available() -> bool` - Check if provider is available
- `get_provider_name() -> str` - Get provider name

### PackageRegistry

Abstract base class for all package registry providers.

**Methods**:
- `publish(version: str) -> bool` - Publish a version
- `get_url(version: str) -> Optional[str]` - Get package URL
- `is_available() -> bool` - Check if registry is available
- `get_provider_name() -> str` - Get provider name

### ProviderManager

Manages provider discovery and instantiation.

**Methods**:
- `get_ci_provider(name: str, config: dict) -> Optional[CIProvider]` - Get CI provider
- `get_registry_provider(name: str, config: dict) -> Optional[PackageRegistry]` - Get registry provider
- `auto_detect_ci_provider() -> Optional[CIProvider]` - Auto-detect CI provider
- `auto_detect_registry_provider() -> Optional[PackageRegistry]` - Auto-detect registry
- `register_ci_provider(name: str, provider_class: type)` - Register custom CI provider
- `register_registry_provider(name: str, provider_class: type)` - Register custom registry
- `list_ci_providers() -> List[str]` - List available CI providers
- `list_registry_providers() -> List[str]` - List available registries

## Environment Variables Reference

### GitHub Actions
- None required (uses `gh` CLI authentication)

### GitLab CI
- None required (uses `glab` CLI authentication)

### Jenkins
- `JENKINS_URL` - Jenkins server URL (required)
- `JENKINS_USER` - Jenkins username (required)
- `JENKINS_TOKEN` - Jenkins API token (required)
- `JENKINS_JOB` - Jenkins job name (optional, can be configured per-project)

### CircleCI
- `CIRCLECI_PROJECT_SLUG` - Project slug in format `vcs/org/repo` (required)
- `CIRCLECI_TOKEN` - CircleCI API token (required)

### PyPI
- None required (uses Poetry configuration)

## Security Best Practices

1. **Never commit tokens** to version control
2. **Use environment variables** or secure credential managers
3. **Rotate tokens regularly** (every 30-90 days recommended)
4. **Use read-only tokens** when possible
5. **Scope tokens** to specific projects/repositories
6. **Store tokens securely** (use system keychain, 1Password, etc.)

## See Also

- [Release Process](../AGENTS.md#release-process) - Release workflow documentation
- [Token Security](./TOKEN_SECURITY.md) - Security best practices for tokens
- [CI Provider Interface](../src/devloop/providers/ci_provider.py) - Source code
- [Provider Manager](../src/devloop/providers/provider_manager.py) - Source code
