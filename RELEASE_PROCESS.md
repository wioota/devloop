# DevLoop Release Process

Provider-agnostic release workflow that works with any CI system and any package registry.

## Supported CI Platforms

DevLoop automatically detects and works with:
- **GitHub Actions** - Via `gh` CLI
- **GitLab CI/CD** - Via `glab` CLI
- **Jenkins** - Via Jenkins REST API
- **CircleCI** - Via CircleCI API v2
- **Custom CI Systems** - Via manual configuration

## Supported Package Registries

DevLoop automatically detects and publishes to:
- **PyPI** - Via `poetry` or `twine`
- **npm** - Via npm CLI
- **Docker Registry** - Via Docker CLI
- **Artifactory** - Via Artifactory REST API (planned)
- **Custom Registries** - Via manual configuration

See [PROVIDER_SYSTEM.md](./docs/PROVIDER_SYSTEM.md) for detailed provider documentation.

## Quick Release Commands

**Check if you're ready to release:**
```bash
devloop release check 1.2.3
```

**Publish a release (full workflow):**
```bash
devloop release publish 1.2.3
```

**Additional options:**
```bash
# Dry-run to see what would happen
devloop release publish 1.2.3 --dry-run

# Specify explicit providers (if auto-detect fails)
devloop release publish 1.2.3 --ci github --registry pypi

# Skip specific steps
devloop release publish 1.2.3 --skip-tag --skip-publish
```

## Automated Release Workflow

The `devloop release` commands run the following steps automatically:

### 1. Pre-Release Checks
Verifies all preconditions:
- Git working directory is clean (no uncommitted changes)
- You're on the correct release branch (default: `main`)
- CI passes on current branch (uses your CI provider)
- Package registry credentials are valid
- Version format is valid (semantic versioning: X.Y.Z)

### 2. Create Git Tag
Creates annotated tag:
- Tag name: `v{version}` (configurable with `--tag-prefix`)
- Fails if tag already exists

### 3. Publish to Registry
Publishes package:
- Uses detected or specified package registry
- Supports multiple registries per release (run multiple times)
- Returns package URL

### 4. Push Tag
Pushes tag to remote repository:
- Only if all previous steps succeed

## Manual Release Workflow

If you need more control or if `devloop release` is unavailable:

### For Python Projects (pyproject.toml)

1. **Update CHANGELOG.md**
   ```markdown
   ## [X.Y.Z] - YYYY-MM-DD

   ### Major Features
   - Feature 1
   - Feature 2

   ### Improvements
   - Improvement 1
   ```

2. **Bump version** using the script:
   ```bash
   python scripts/bump-version.py X.Y.Z
   ```

   This updates `pyproject.toml` (single source of truth). Note: `src/devloop/__init__.py` reads version dynamically from package metadata.

3. **Update dependency lock file**
   ```bash
   poetry lock   # For poetry projects
   pip freeze > requirements.txt  # For pip projects
   ```

4. **Commit changes**
   ```bash
   git add pyproject.toml CHANGELOG.md poetry.lock
   git commit -m "Release vX.Y.Z: Description of major changes"
   ```

5. **Create and push tag**
   ```bash
   git tag -a vX.Y.Z -m "DevLoop vX.Y.Z - Release notes here"
   git push origin main vX.Y.Z
   ```

### For Other Project Types

Replace the version file (`package.json` for npm, etc.) in step 2, and update the lock file appropriately in step 3.

## Release Checklist

Before pushing your release tag:

1. ✅ All CI tests pass (`devloop release check <version>` or manual CI check)
2. ✅ CHANGELOG.md updated with release notes
3. ✅ Version bumped in all relevant files
4. ✅ Lock files updated (`poetry.lock`, `package-lock.json`, etc.)
5. ✅ No uncommitted changes: `git status` should be clean
6. ✅ Release notes include migration guides (if breaking changes)
7. ✅ Manual testing on clean environment (for critical releases)

## Notes

- The pre-commit hook will validate formatting, types, and tests
- If you need to bypass pre-commit for lock file changes: `git commit --no-verify`
- Always commit version and CHANGELOG updates before creating the release tag
- Follow [Semantic Versioning](https://semver.org/): MAJOR.MINOR.PATCH
- Release tags are permanent - create a new tag if mistakes are made
- DevLoop automatically syncs release information to your CI platform

## Multi-Provider Releases

For projects that publish to multiple registries:

```bash
# Publish to PyPI
devloop release publish 1.2.3 --registry pypi

# Also publish to Artifactory (when provider available)
devloop release publish 1.2.3 --registry artifactory
```

Tag and CI checks only run once (when creating the first tag). Subsequent publishes to different registries reuse the existing tag.

## Troubleshooting Auto-Detection

If `devloop release` commands fail with "no provider available", the auto-detection couldn't find your CI or registry setup.

### General Debugging

Check what providers are available:
```bash
devloop release debug  # Shows detected CI and registry
```

This helps identify which auto-detection failed.

### CI Provider Setup

**GitHub Actions:**
```bash
# Requirements: gh CLI installed and authenticated
which gh
gh auth status

# If missing: brew install gh (macOS) or apt install gh (Linux)
gh auth login

# Then retry with explicit provider
devloop release check 1.2.3 --ci github
```

**GitLab CI:**
```bash
# Requirements: glab CLI and GitLab token
which glab
glab auth status

# If missing or not logged in
glab auth login

devloop release check 1.2.3 --ci gitlab
```

**Jenkins:**
```bash
# Requirements: curl or API access to Jenkins
# Set environment variables:
export JENKINS_URL="https://your-jenkins.example.com"
export JENKINS_TOKEN="your-token"
export JENKINS_USER="your-user"

devloop release check 1.2.3 --ci jenkins
```

### Package Registry Setup

**PyPI:**
```bash
# Requirements: poetry and PyPI token
poetry --version

# Configure token
poetry config pypi-token.pypi "pypi-..."

devloop release check 1.2.3 --registry pypi
```

**npm:**
```bash
# Requirements: npm CLI and authentication
npm --version
npm whoami  # Should show your npm username

# If not logged in
npm login

devloop release check 1.2.3 --registry npm
```

**Docker Registry:**
```bash
# Requirements: Docker CLI and authentication
docker --version
docker ps  # Should work if authenticated

devloop release check 1.2.3 --registry docker
```

**Custom Registry:**
For non-standard registries, see [PROVIDER_SYSTEM.md](./docs/PROVIDER_SYSTEM.md) for custom provider setup.

### Manual Override

If auto-detection still fails, explicitly specify both:
```bash
devloop release publish 1.2.3 --ci github --registry pypi
```

This will validate that the tools are installed and authenticated before attempting the release.

See [PROVIDER_SYSTEM.md](./docs/PROVIDER_SYSTEM.md) for detailed provider setup and troubleshooting for your specific CI/registry combination.

## Publishing & Security Considerations

**For public/published software**, add extra care to your DevLoop workflow:

### Version Consistency
- ✅ `pyproject.toml` is the single source of truth (version is read dynamically via `importlib.metadata`)
- ✅ Use semantic versioning (MAJOR.MINOR.PATCH)
- ✅ Tag releases with matching version numbers (`git tag v1.2.3`)
- **Automated**: Use `python scripts/bump-version.py <version>` to update versions

### Breaking Changes
- ✅ Document all breaking changes clearly in `CHANGELOG.md`
- ✅ Include migration guides in release notes
- ✅ Consider deprecation warnings before breaking changes
- **Agent support**: Add agents to detect API/interface changes and prompt for documentation

### Dependency Security
- ✅ Run security audits: `pip audit`, `poetry audit`, Dependabot
- ✅ Monitor for CVE updates in dependencies
- ✅ Update vulnerable dependencies promptly
- ✅ Review new dependency versions before merging
- **Agent support**: Security scanner agents should flag vulnerable dependencies

### Documentation Accuracy
- ✅ Test all installation instructions on a clean environment
- ✅ Verify all code examples actually work
- ✅ Keep README, API docs, and examples current with code changes
- **Agent support**: Doc-sync agent should flag outdated documentation

### Security Policy
- ✅ Add `SECURITY.md` with vulnerability disclosure procedures
- ✅ Provide a secure reporting channel (don't report exploits publicly)
- ✅ Acknowledge and credit security researchers
- ✅ Establish response timeline (e.g., 30 days before public disclosure)

### Changelog Maintenance
- ✅ Keep detailed `CHANGELOG.md` with every release
- ✅ Group changes by type (features, fixes, security, breaking)
- ✅ Link to related issues/PRs
- ✅ Include version-specific migration notes
- **Agent support**: Commit assistant can suggest changelog entries based on commit messages

### Pre-Release Checklist
Before publishing to registries (PyPI, npm, crates.io, etc.):
1. ✅ All CI tests pass
2. ✅ All code quality checks pass (linting, type checking, formatting)
3. ✅ Security scan shows no vulnerabilities
4. ✅ Documentation is current and tested
5. ✅ CHANGELOG updated with release notes
6. ✅ Version numbers consistent across files
7. ✅ No accidental secrets in commit history
8. ✅ Manual smoke test on clean environment
9. ✅ Release notes written with migration guides (if breaking changes)

**Agent setup**: Create a pre-release agent that validates these checks before allowing deployment.
