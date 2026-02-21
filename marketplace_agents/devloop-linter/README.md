# devloop-linter

Runs linters on file changes with sandboxed execution and auto-fix support.

## Configuration

In `agents.json`:

```json
{
  "linter": {
    "enabled": true,
    "autoFix": false,
    "filePatterns": ["**/*.py"],
    "linters": {"python": "ruff", "javascript": "eslint"},
    "debounce": 500
  }
}
```

## Supported Linters

- **Python**: Ruff
- **JavaScript/TypeScript**: ESLint
