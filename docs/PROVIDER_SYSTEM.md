# DevLoop Provider System

## Overview

DevLoop uses a **pluggable provider architecture** to support multiple CI/CD systems and package registries. This design allows DevLoop to work with any CI platform (GitHub Actions, GitLab CI, Jenkins, etc.) and any package registry (PyPI, Artifactory, GitLab Registry, etc.).

## Architecture

### Core Abstractions

**CIProvider** - Abstract base class for CI systems
- `get_status(branch)` - Get latest workflow run for a branch
- `list_runs(branch, limit, workflow_name)` - List recent runs
- `get_logs(run_id)` - Retrieve run logs
- `rerun(run_id)` - Rerun a workflow
- `cancel(run_id)` - Cancel a running workflow
- `get_workflows()` - List all workflows
- `is_available()` - Check if provider is available/authenticated
- `get_provider_name()` - Return human-readable name

**PackageRegistry** - Abstract base class for package registries
- `publish(package_path, version)` - Publish a package
- `get_version(package_name)` - Get latest version
- `get_versions(package_name, limit)` - Get version history
- `check_credentials()` - Validate authentication
- `is_available()` - Check if registry is accessible
- `get_provider_name()` - Return human-readable name
- `get_package_url(package_name, version)` - Get package URL

### Provider Manager

The `ProviderManager` handles provider discovery and registration:

```python
from devloop.providers.provider_manager import get_provider_manager

manager = get_provider_manager()

# Get specific provider
ci = manager.get_ci_provider("github")
registry = manager.get_registry_provider("pypi")

# Auto-detect provider
ci = manager.auto_detect_ci_provider()
registry = manager.auto_detect_registry_provider()

# List available providers
ci_providers = manager.list_ci_providers()
registry_providers = manager.list_registry_providers()
```

## Built-in Providers

### CI Providers

**GitHub Actions** (`github`, `github-actions`)
- Uses `gh` CLI for API access
- Requires GitHub authentication
- Supports workflow runs, logs, reruns, cancellations

### Registry Providers

**PyPI** (`pypi`, `python`)
- Uses `poetry` CLI for publishing
- Supports package version retrieval
- Optional custom index URL support

## Creating Custom Providers

### Custom CI Provider

```python
from devloop.providers.ci_provider import CIProvider, WorkflowRun, RunStatus

class GitLabCIProvider(CIProvider):
    """GitLab CI provider implementation."""
    
    def __init__(self):
        self.api_token = os.getenv("GITLAB_TOKEN")
    
    def get_status(self, branch: str) -> Optional[WorkflowRun]:
        """Implementation using GitLab API"""
        pass
    
    def list_runs(self, branch: str, limit: int = 10, 
                  workflow_name: Optional[str] = None) -> List[WorkflowRun]:
        """Implementation using GitLab API"""
        pass
    
    # ... implement other abstract methods ...
    
    def get_provider_name(self) -> str:
        return "GitLab CI"
```

### Register Custom Provider

```python
from devloop.providers.provider_manager import get_provider_manager
from my_providers import GitLabCIProvider

manager = get_provider_manager()
manager.register_ci_provider("gitlab", GitLabCIProvider)

# Now you can use it
provider = manager.get_ci_provider("gitlab")
```

### Custom Registry Provider

```python
from devloop.providers.registry_provider import PackageRegistry

class ArtifactoryRegistry(PackageRegistry):
    """Artifactory registry provider implementation."""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
    
    def publish(self, package_path: str, version: str) -> bool:
        """Implementation using Artifactory API"""
        pass
    
    # ... implement other abstract methods ...
    
    def get_provider_name(self) -> str:
        return "Artifactory"
```

## Configuration

### Global Configuration

DevLoop can be configured to use specific providers via `.devloop/agents.json`:

```json
{
  "global": {
    "providers": {
      "ci": {
        "provider": "github",
        "config": {
          "repo_url": "https://github.com/owner/repo"
        }
      },
      "registry": {
        "provider": "pypi",
        "config": {
          "index_url": "https://pypi.org"
        }
      }
    }
  }
}
```

### Agent-level Configuration

Agents can be configured with specific providers:

```json
{
  "agents": {
    "ci-monitor": {
      "enabled": true,
      "config": {
        "ci_provider": "github",
        "ci_config": {}
      }
    }
  }
}
```

## Auto-Detection

DevLoop automatically detects available providers based on repository structure:

1. **CI Detection**
   - Checks for `.github/workflows/` (GitHub Actions)
   - Checks for `.gitlab-ci.yml` (GitLab CI)
   - Checks for `Jenkinsfile` (Jenkins)
   - Uses first available provider with valid authentication

2. **Registry Detection**
   - For Python projects: defaults to PyPI
   - Checks for custom `pyproject.toml` configuration
   - Checks for environment variables (PYPI_TOKEN, etc.)

## Integration Examples

### Pre-push Hook

```bash
# Automatically uses detected CI provider
# Falls back to GitHub CLI if Python provider unavailable
.git/hooks/pre-push
```

### CI Monitor Agent

```python
from devloop.agents.ci_monitor import CIMonitorAgent
from devloop.providers.provider_manager import get_provider_manager

# Auto-detect provider
manager = get_provider_manager()
provider = manager.auto_detect_ci_provider()

agent = CIMonitorAgent(
    name="ci-monitor",
    triggers=["git:post-push"],
    event_bus=event_bus,
    ci_provider=provider
)
```

### Release Workflow

```python
from devloop.providers.provider_manager import get_provider_manager

manager = get_provider_manager()
ci = manager.get_ci_provider("github")
registry = manager.get_registry_provider("pypi")

# Check CI status before publishing
status = ci.get_status("main")
if status.conclusion == RunConclusion.SUCCESS:
    # Publish package
    registry.publish(".", "1.0.0")
```

## Migration Guide

### From GitHub-only Setup

**Before** (GitHub-specific):
```python
import subprocess

result = subprocess.run(["gh", "run", "list", ...], ...)
conclusion = json.loads(result.stdout)[0]["conclusion"]
```

**After** (Provider-agnostic):
```python
from devloop.providers.provider_manager import get_provider_manager

manager = get_provider_manager()
provider = manager.auto_detect_ci_provider()
runs = provider.list_runs("main")
conclusion = runs[0].conclusion
```

### Benefits

- ✅ Works with any CI platform
- ✅ Works with any package registry
- ✅ No CLI tool dependencies (uses Python APIs)
- ✅ Community extensible
- ✅ Type-safe and testable
- ✅ Graceful degradation if provider unavailable

## Testing

Mock providers for testing:

```python
from devloop.providers.ci_provider import CIProvider, WorkflowRun, RunStatus

class MockCIProvider(CIProvider):
    def get_status(self, branch: str):
        return WorkflowRun(
            id="mock-123",
            name="test-workflow",
            branch=branch,
            status=RunStatus.COMPLETED,
            conclusion=RunConclusion.SUCCESS,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    
    # ... implement other methods for testing ...
```

## Future Enhancements

1. **GitLab CI Provider** - Full support for GitLab CI/CD
2. **Jenkins Provider** - Support for Jenkins pipelines
3. **CircleCI Provider** - Support for CircleCI
4. **Artifactory Registry** - Enterprise artifact repository
5. **GitLab Registry** - GitLab's container/package registry
6. **Custom Provider Plugins** - Load providers from external packages
7. **Provider Chaining** - Fallback providers if primary unavailable
8. **Caching** - Cache provider status to reduce API calls
9. **Metrics** - Collect provider usage statistics
10. **Provider Diagnostics** - Debug provider configuration issues
