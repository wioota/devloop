# devloop-security-scanner

Detects security vulnerabilities in code using multiple scanning tools.

## Configuration

In `agents.json`:

```json
{
  "security": {
    "enabled_tools": ["bandit", "safety", "trivy"],
    "severity_threshold": "medium",
    "confidence_threshold": "medium"
  }
}
```

## Supported Scanners

- **Bandit**: Python security linter
- **Safety**: Python dependency vulnerability checker
- **Trivy**: Container and filesystem vulnerability scanner
