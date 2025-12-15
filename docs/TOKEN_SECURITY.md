# Token Security Guide

## Overview

DevLoop securely manages API keys and tokens for agent integrations (Snyk, Code Rabbit, GitHub, etc.).

## Best Practices

### ✅ DO

- **Use environment variables** for all credentials
  ```bash
  export SNYK_TOKEN="your-token"
  export CODE_RABBIT_API_KEY="your-key"
  export GITHUB_TOKEN="your-token"
  ```

- **Enable token expiry and rotation** (30-90 days recommended)
- **Use read-only or project-scoped tokens** when possible
- **Store tokens in `.env` file** (add to `.gitignore`)

###  ❌ DON'T

- Never commit tokens to git
- Never pass tokens as command arguments
- Never hardcode tokens in code
- Never log full token values

## Token Storage

DevLoop automatically:
- Hides tokens in logs and process lists
- Validates token format and expiry
- Warns about placeholder values ("changeme", "token", etc.)
- Never logs full token values

## Token Validation

```bash
# DevLoop validates token format during initialization
devloop init /path/to/project

# View token status (tokens are masked)
devloop status --show-token-info
```

## Supported Tokens

- `GITHUB_TOKEN` - GitHub API access (releases, CI status)
- `SNYK_TOKEN` - Snyk security scanning
- `CODE_RABBIT_API_KEY` - Code Rabbit AI analysis
- `PYPI_TOKEN` / `POETRY_PYPI_TOKEN_PYPI` - PyPI publishing

## Token Rotation

Rotate tokens regularly:

1. Generate new token from service provider
2. Update environment variable
3. Restart DevLoop: `devloop stop && devloop watch .`
4. Revoke old token

## Security Incident Response

If a token is compromised:

1. **Immediately revoke** the token at the service provider
2. **Generate a new token**
3. **Update your environment variables**
4. **Check git history** for accidental commits: `git log -p | grep -i token`
5. **Report to DevLoop** if the leak was due to a bug

## Related Documentation

- [CODING_RULES.md](../CODING_RULES.md) - Development standards
- [RELEASE_PROCESS.md](../RELEASE_PROCESS.md) - Release workflow security
