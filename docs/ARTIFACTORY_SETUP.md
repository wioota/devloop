# Artifactory Registry Provider Setup

DevLoop supports publishing packages to Artifactory, a universal package repository manager for enterprise teams.

## Quick Start

```bash
# Set environment variables
export ARTIFACTORY_URL="https://artifactory.example.com/artifactory"
export ARTIFACTORY_TOKEN="your-api-token"
export ARTIFACTORY_REPO="generic-repo"

# Release to Artifactory
devloop release publish 1.0.0 --registry artifactory
```

## Configuration

### Environment Variables

```bash
ARTIFACTORY_URL          # Artifactory base URL (required)
ARTIFACTORY_TOKEN        # API token for authentication (recommended)
ARTIFACTORY_USER         # Username (alternative to token)
ARTIFACTORY_PASSWORD     # Password (with username)
ARTIFACTORY_REPO         # Default repository name
```

### Python Code

```python
from devloop.providers.provider_manager import ProviderManager

manager = ProviderManager()
registry = manager.get_registry_provider(
    "artifactory",
    config={
        "base_url": "https://artifactory.example.com/artifactory",
        "api_token": "your-api-token",
        "repo": "generic-repo"
    }
)

# Check credentials
if registry.check_credentials():
    print("Connected to Artifactory")
    
# Publish artifact
success = registry.publish("dist/package-1.0.0.jar", "1.0.0")
```

## Authentication

### Token-Based (Recommended)

1. **Generate API Token** in Artifactory:
   - Log in to Artifactory
   - Go to User Profile → Edit Profile
   - Generate an API Token
   - Copy the token

2. **Set Environment Variable**:
   ```bash
   export ARTIFACTORY_TOKEN="AKCp..."
   ```

### Basic Authentication

If using username/password instead of token:

```python
registry = ArtifactoryRegistry(
    base_url="https://artifactory.example.com/artifactory",
    username="your-username",
    password="your-password",
    repo="generic-repo"
)
```

## Repository Types

Artifactory supports multiple repository types. Configure the appropriate one for your artifacts:

- **generic** - Any file type (build artifacts, binaries, etc.)
- **docker** - Docker images
- **maven** - Java Maven packages
- **npm** - Node.js packages
- **python** - Python packages (PyPI-compatible)
- **gradle** - Gradle dependencies
- **nuget** - .NET packages
- **cargo** - Rust packages

## Publishing Artifacts

### Single Artifact

```python
registry = manager.get_registry_provider("artifactory")

# Publish a built artifact
success = registry.publish(
    package_path="dist/my-app-1.0.0.jar",
    version="1.0.0"
)

if success:
    url = registry.get_package_url("my-app", "1.0.0")
    print(f"Published to: {url}")
```

### Multiple Artifacts

```python
artifacts = [
    "dist/app-1.0.0.jar",
    "dist/app-1.0.0.war",
    "dist/app-1.0.0-sources.jar"
]

for artifact in artifacts:
    registry.publish(artifact, "1.0.0")
```

## Querying Versions

### Get Latest Version

```python
latest = registry.get_version("my-app")
print(f"Latest version: {latest}")
```

### Get Version History

```python
versions = registry.get_versions("my-app", limit=10)

for v in versions:
    print(f"{v.version} - {v.released_at}")
    print(f"  URL: {v.url}")
    print(f"  Size: {v.metadata.get('size')} bytes")
```

## Multi-Registry Releases

Release to both PyPI and Artifactory:

```bash
# Release to PyPI
devloop release publish 1.0.0 --registry pypi

# Also release to Artifactory
devloop release publish 1.0.0 --registry artifactory
```

The release tag is created only once. Subsequent publishes to different registries reuse the existing tag.

## CI/CD Integration

### GitHub Actions

```yaml
- name: Publish to Artifactory
  env:
    ARTIFACTORY_URL: ${{ secrets.ARTIFACTORY_URL }}
    ARTIFACTORY_TOKEN: ${{ secrets.ARTIFACTORY_TOKEN }}
    ARTIFACTORY_REPO: ${{ secrets.ARTIFACTORY_REPO }}
  run: devloop release publish ${{ env.VERSION }} --registry artifactory
```

### GitLab CI

```yaml
publish_artifactory:
  script:
    - export ARTIFACTORY_URL=$ARTIFACTORY_URL
    - export ARTIFACTORY_TOKEN=$ARTIFACTORY_TOKEN
    - export ARTIFACTORY_REPO=$ARTIFACTORY_REPO
    - devloop release publish $VERSION --registry artifactory
  only:
    - tags
```

### Jenkins

```groovy
stage('Publish to Artifactory') {
    environment {
        ARTIFACTORY_URL = credentials('artifactory-url')
        ARTIFACTORY_TOKEN = credentials('artifactory-token')
        ARTIFACTORY_REPO = 'builds'
    }
    steps {
        sh 'devloop release publish 1.0.0 --registry artifactory'
    }
}
```

## Troubleshooting

### Connection Failed

**Error**: `Connection refused` or `HTTP 401`

**Causes**:
- Incorrect Artifactory URL
- Invalid API token or credentials
- Network/firewall issues

**Fix**:
```bash
# Verify URL is reachable
curl -H "X-JFrog-Art-Api: $ARTIFACTORY_TOKEN" \
  https://artifactory.example.com/artifactory/api/system/ping

# Check credentials
python -c "
from devloop.providers.artifactory_registry import ArtifactoryRegistry
r = ArtifactoryRegistry()
print('Credentials valid:', r.check_credentials())
"
```

### Repository Not Found

**Error**: `404 Not Found` when publishing

**Causes**:
- Repository name is incorrect
- Repository doesn't exist
- User doesn't have write permission

**Fix**:
```bash
# Verify repository exists
curl -H "X-JFrog-Art-Api: $ARTIFACTORY_TOKEN" \
  https://artifactory.example.com/artifactory/api/repositories

# Check permissions in Artifactory UI
```

### Version Extraction Failed

**Error**: Version not detected from filename

**Solution**: Artifactory provider extracts versions from filenames using pattern:
```
package-X.Y.Z[.extension]
```

Examples that work:
- `app-1.0.0.jar`
- `lib-2.5.1.whl`
- `tool-0.1.0-beta.tar.gz`

If your naming doesn't match, either:
1. Rename the artifact
2. Explicitly specify version in publish call

## Advanced Usage

### Custom Repository Paths

```python
registry = ArtifactoryRegistry(
    base_url="https://artifactory.example.com/artifactory",
    api_token="token",
    repo="releases"  # Different repo per release
)
```

### AQL Queries

The provider uses Artifactory Query Language (AQL) for version listing:

```python
# Internal: automatically used by get_versions()
aql_query = 'items.find({"name": "app*", "repo": "generic-repo"})'
```

For custom queries, use Artifactory REST API directly.

### Artifact Metadata

```python
versions = registry.get_versions("my-app", limit=5)

for v in versions:
    size = v.metadata.get("size")
    repo = v.metadata.get("repo")
    print(f"{v.version}: {size} bytes in {repo}")
```

## See Also

- [DevLoop Release Management](./RELEASE_PROCESS.md)
- [Provider System Architecture](./PROVIDER_SYSTEM.md)
- [Artifactory Documentation](https://jfrog.com/artifactory/)
