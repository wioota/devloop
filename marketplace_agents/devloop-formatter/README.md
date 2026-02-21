# devloop-formatter

Auto-formats code on file save using Black (Python) and Prettier (JS/TS/JSON/Markdown).

## Configuration

In `agents.json`:

```json
{
  "formatter": {
    "enabled": true,
    "formatOnSave": true,
    "reportOnly": false,
    "filePatterns": ["**/*.py", "**/*.js", "**/*.ts"]
  }
}
```

## Supported Formatters

- **Python**: Black
- **JavaScript/TypeScript**: Prettier
- **JSON/Markdown**: Prettier
