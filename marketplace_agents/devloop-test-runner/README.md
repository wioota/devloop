# devloop-test-runner

Runs tests on file changes with smart related-test detection and project context awareness.

## Configuration

In `agents.json`:

```json
{
  "testRunner": {
    "enabled": true,
    "runOnSave": true,
    "relatedTestsOnly": true,
    "autoDetectFrameworks": true
  }
}
```

## Supported Frameworks

- **Python**: pytest, unittest
- **JavaScript/TypeScript**: jest, mocha
