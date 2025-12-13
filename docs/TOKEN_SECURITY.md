# Secure Token Management Guide

This document provides guidelines and best practices for managing API tokens and credentials securely within DevLoop.

## Overview

DevLoop integrates with multiple external services (GitHub, GitLab, PyPI, npm, Docker registries, etc.) that require authentication tokens. Improper token management can lead to serious security vulnerabilities:

- **Token exposure in logs**: Leaked tokens can be exploited immediately
- **Process list visibility**: Tokens passed as command-line arguments are visible to all users
- **Shell history leakage**: Tokens typed in commands are stored in shell history files
- **Hardcoded credentials**: Tokens in source code can be accidentally committed to version control

## Security Features

DevLoop's token manager provides:

1. **Token Expiry Validation**: Check if tokens have expired or expire soon
2. **Secure Retrieval**: Get tokens from environment variables, not hardcoded values
3. **Sanitization**: Automatically hide tokens in logs and command output
4. **Validation**: Verify token format and detect placeholder values
5. **OAuth2 Recommendations**: Guidance for user-facing applications
6. **Process List Warnings**: Alert when tokens are visible in process lists

## Best Practices

### 1. Store Tokens in Environment Variables

**✅ GOOD: Use environment variables**

```bash
export GITHUB_TOKEN="ghp_your_token_here"
export PYPI_TOKEN="pypi-your_token_here"

# Run devloop commands
devloop release publish 1.0.0
```

**❌ BAD: Pass tokens as command arguments**

```bash
# Token visible in process list!
poetry publish -u __token__ -p pypi-secret-token-12345
```

**❌ BAD: Hardcode tokens in code**

```python
# Never do this!
api_token = "ghp_hardcoded_token_12345"
registry = PyPIRegistry(api_token="pypi-secret-123")
```

### 2. Use Read-Only Tokens When Possible

Many services support read-only or limited-scope tokens:

- **GitHub**: Use fine-grained personal access tokens with minimal scopes
- **PyPI**: Create project-scoped tokens with upload-only permissions
- **GitLab**: Use project access tokens instead of personal tokens
- **npm**: Use automation tokens for CI/CD (read-only for installs)

**Example: GitHub fine-grained token**

```bash
# Create token with only repo:status and read:repo scopes
# https://github.com/settings/tokens?type=beta
export GITHUB_TOKEN="github_pat_minimal_permissions"
```

### 3. Enable Token Expiry

Set expiration dates for all tokens:

- **GitHub**: Maximum 90 days recommended
- **PyPI**: Set expiry when creating tokens
- **GitLab**: Use short-lived tokens for automation

**Check token expiry with DevLoop:**

```python
from devloop.security import get_github_token

token = get_github_token()
if token and token.expires_soon(days=7):
    print(f"⚠️  Token expires soon: {token.expires_at}")
```

### 4. Never Log Full Tokens

Use DevLoop's sanitization functions:

```python
from devloop.security import sanitize_log, sanitize_command

# Sanitize log messages
log_msg = f"Using token {token_value} for authentication"
safe_msg = sanitize_log(log_msg)  # "Using token gh**** for authentication"
logger.info(safe_msg)

# Sanitize commands before logging
cmd = ["curl", "--token", token_value, "api.github.com"]
safe_cmd = sanitize_command(cmd)  # ["curl", "--token", "****", "api.github.com"]
logger.info(f"Running: {' '.join(safe_cmd)}")
```

### 5. Use OAuth2 for User-Facing Applications

For applications with interactive users, use OAuth2 instead of personal access tokens:

```python
from devloop.security import get_token_manager

manager = get_token_manager()
recommendation = manager.recommend_oauth2("github")
print(recommendation)
```

**OAuth2 Benefits:**

- User-scoped access (not tied to a single account)
- Automatic token refresh
- Revocable access without changing passwords
- Better audit trail

## Environment Variable Naming Conventions

DevLoop automatically detects tokens from standard environment variables:

| Service | Environment Variables (in priority order) |
|---------|-------------------------------------------|
| GitHub  | `GITHUB_TOKEN`, `GH_TOKEN`                |
| GitLab  | `GITLAB_TOKEN`, `GL_TOKEN`                |
| PyPI    | `PYPI_TOKEN`, `POETRY_PYPI_TOKEN_PYPI`    |
| npm     | `NPM_TOKEN`                               |
| Docker  | `DOCKER_TOKEN`, `DOCKER_PASSWORD`         |

**Example `.env` file:**

```bash
# GitHub authentication
GITHUB_TOKEN=ghp_your_github_token_here

# PyPI authentication
PYPI_TOKEN=pypi-your_pypi_token_here

# GitLab authentication
GITLAB_TOKEN=glpat-your_gitlab_token_here
```

**Load environment variables:**

```bash
# Option 1: Source .env file
source .env

# Option 2: Use direnv (recommended)
# https://direnv.net/
echo "export GITHUB_TOKEN=..." > .envrc
direnv allow

# Option 3: Use poetry-dotenv
# https://github.com/mpeteuil/poetry-dotenv
poetry run devloop
```

## Token Rotation

Regularly rotate tokens to limit exposure window:

**Rotation Schedule:**

- **Production tokens**: Rotate every 30-90 days
- **Development tokens**: Rotate every 90 days
- **CI/CD tokens**: Rotate every 90 days
- **Emergency rotation**: Immediately if token exposure suspected

**Rotation Process:**

1. Create new token with same permissions
2. Update environment variables / CI secrets
3. Test new token works
4. Revoke old token
5. Update documentation

## CI/CD Integration

### GitHub Actions

Store tokens as **Repository Secrets**:

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Publish to PyPI
        env:
          PYPI_TOKEN: ${{ secrets.PYPI_TOKEN }}
        run: |
          poetry publish
```

**Security Tips:**

- Use environment-specific secrets (staging vs. production)
- Enable "Required reviewers" for production deployments
- Use OpenID Connect (OIDC) instead of tokens when possible

### GitLab CI

Use **CI/CD Variables** (masked and protected):

```yaml
# .gitlab-ci.yml
release:
  stage: deploy
  script:
    - poetry publish
  variables:
    PYPI_TOKEN: ${PYPI_TOKEN}  # Injected from CI/CD variables
  only:
    - tags
```

## Security Warnings

DevLoop automatically warns about insecure token usage:

```python
from devloop.security import TokenManager

manager = TokenManager(warn_on_insecure=True)

# Warning: Using hardcoded token
token = manager.get_token(
    TokenType.GITHUB,
    fallback_value="ghp_hardcoded_token"
)
# ⚠️  Using hardcoded github token. Store in environment variable instead: GITHUB_TOKEN
```

## Token Validation

Validate token format before use:

```python
from devloop.security import get_token_manager, TokenType

manager = get_token_manager()

# Validate GitHub token
is_valid, error = manager.validate_token(
    TokenType.GITHUB,
    "ghp_1234567890abcdefghij"
)

if not is_valid:
    print(f"Invalid token: {error}")
```

**Common Validation Errors:**

- Token too short (< 20 characters)
- Token appears to be placeholder ("changeme", "token", etc.)
- Token format doesn't match expected pattern

## Example: Secure Release Workflow

```python
#!/usr/bin/env python3
"""Secure release script using DevLoop token management."""

import sys
from devloop.security import get_pypi_token, sanitize_log
from devloop.release import ReleaseManager

def main(version: str) -> int:
    # Get token from environment (never hardcode)
    token = get_pypi_token()

    if not token:
        print("❌ PYPI_TOKEN not found in environment", file=sys.stderr)
        print("Set with: export PYPI_TOKEN=pypi-...", file=sys.stderr)
        return 1

    # Check expiry
    if token.is_expired():
        print("❌ Token has expired", file=sys.stderr)
        return 1

    if token.expires_soon(days=7):
        print("⚠️  Token expires soon, consider rotating", file=sys.stderr)

    # Use token securely
    manager = ReleaseManager(
        version=version,
        pypi_token=token.value  # Token value never logged
    )

    # Sanitize logs
    log_msg = sanitize_log(f"Publishing with token: {token.value}")
    print(log_msg)  # "Publishing with token: pypi-****"

    # Publish
    success = manager.publish_to_pypi()
    return 0 if success else 1

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: release.py <version>", file=sys.stderr)
        sys.exit(1)

    sys.exit(main(sys.argv[1]))
```

## Incident Response

If a token is exposed:

1. **Immediately revoke the token** in the service dashboard
2. **Generate a new token** with the same permissions
3. **Update all systems** using the old token
4. **Audit logs** to check if the token was used maliciously
5. **Review and improve** token storage practices
6. **Consider enabling 2FA** or IP restrictions if available

## Additional Resources

- [GitHub Token Security Best Practices](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/token-expiration-and-revocation)
- [PyPI API Tokens](https://pypi.org/help/#apitoken)
- [GitLab Token Security](https://docs.gitlab.com/ee/security/token_overview.html)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)

## API Reference

For detailed API documentation, see:

- `src/devloop/security/token_manager.py` - Token management implementation
- `tests/security/test_token_manager.py` - Usage examples and test cases
