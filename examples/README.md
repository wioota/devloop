# DevLoop Examples

Example usage patterns and workflows for DevLoop.

## Basic Examples

### Example 1: Auto-Format on Save
When you save a Python file, DevLoop automatically formats it with Black and isort.

**See**: [examples/auto-format.py](./auto-format.py)

### Example 2: Run Tests on Changes
DevLoop detects which tests are affected by your changes and runs only those.

**See**: [examples/test-runner.py](./test-runner.py)

### Example 3: Custom Pattern Matcher
Create a custom agent to find TODO comments.

```bash
devloop custom-create find_todos pattern_matcher
```

### Example 4: Security Scanning
DevLoop automatically scans for vulnerabilities with Bandit.

**See**: [examples/security-scan.py](./security-scan.py)

## Advanced Examples

### Creating Custom Agents
See [docs/AGENT_DEVELOPMENT.md](../docs/AGENT_DEVELOPMENT.md) for detailed guide.

### Marketplace Publishing
See [docs/MARKETPLACE_GUIDE.md](../docs/MARKETPLACE_GUIDE.md) for publishing agents.

### Learning System
View learned patterns and recommendations:
```bash
devloop learning-insights --agent linter
devloop learning-recommendations linter
```

## Contributing Examples

Have an interesting DevLoop workflow? Submit a PR with:
1. Example file (e.g., `my-example.py`)
2. Documentation in this README
3. Any supporting files

See [CODING_RULES.md](../CODING_RULES.md) for contribution guidelines.
