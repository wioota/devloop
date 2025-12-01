# DevLoop Release Process

This document describes how to release new versions of DevLoop to PyPI.

## Prerequisites

1. **PyPI Account**: Create an account at https://pypi.org
2. **API Token**: Generate an API token at https://pypi.org/manage/account/tokens/
3. **GitHub Secret**: Add the token as `PYPI_TOKEN` to the repository secrets:
   - Go to: Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `PYPI_TOKEN`
   - Value: Your PyPI API token

## Release Steps

### 1. Update Version

Update the version in `pyproject.toml`:

```toml
[tool.poetry]
name = "devloop"
version = "0.2.1"  # Bump version here
```

### 2. Update Changelog

Add your changes to `CHANGELOG.md` under a new version section:

```markdown
## [0.2.1] - 2025-11-30

### Added
- New feature 1
- New feature 2

### Fixed
- Bug fix 1
```

### 3. Create Release Tag

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "Release v0.2.1"
git tag v0.2.1
git push origin main
git push origin v0.2.1
```

### 4. Automated Workflow

The `.github/workflows/release.yml` workflow will automatically:

1. **Build distribution packages**
   - Creates source distribution (.tar.gz)
   - Creates wheel distribution (.whl)

2. **Publish to PyPI**
   - Uses the `PYPI_TOKEN` secret
   - Publishes to production PyPI

3. **Create GitHub Release**
   - Creates a release entry on GitHub
   - Includes changelog information

4. **Upload Artifacts**
   - Stores distribution packages for 30 days
   - Available in the Actions tab

## Verification

After the workflow completes:

1. **Check PyPI**: https://pypi.org/project/devloop/
2. **Test installation**: `pip install devloop==0.2.1`
3. **Check GitHub Release**: Go to Releases tab in your repo

## Troubleshooting

### PyPI Token Issues

- **Invalid token**: Ensure token is set correctly in GitHub secrets
- **Token expired**: Generate a new token and update the secret
- **Unauthorized**: Check that token has "Entire repository" scope

### Build Failures

- Check that all tests pass locally: `poetry run pytest`
- Check that linting passes: `poetry run ruff check src/`
- Verify `pyproject.toml` is valid: `poetry check`

### Manual Publishing (if needed)

If the workflow fails and you need to publish manually:

```bash
# Build locally
poetry build

# Publish using token
poetry publish -u __token__ -p your_pypi_token
```

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., 0.2.1)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

## CI/CD Integration

The release workflow:

1. **Runs tests** (if any fail, the release is blocked)
2. **Builds packages** (sdist + wheel)
3. **Publishes to PyPI** (with automatic authentication)
4. **Creates GitHub release** (with changelog)

No manual intervention needed after pushing the tag.
