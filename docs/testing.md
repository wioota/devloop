# Testing Guide

Running tests and understanding the DevLoop test strategy.

## Running Tests

### All Tests

```bash
poetry run pytest
```

### With Coverage Report

```bash
poetry run pytest --cov=devloop --cov-report=html
```

### Specific Test File

```bash
poetry run pytest tests/unit/agents/test_linter.py -v
```

### Specific Test

```bash
poetry run pytest tests/unit/agents/test_linter.py::test_linter_detects_errors -v
```

### Watch Mode

```bash
poetry run pytest-watch
```

## Test Organization

```
tests/
├── unit/
│   ├── agents/           # Agent unit tests
│   ├── collectors/       # Collector tests
│   ├── core/            # Core system tests
│   └── cli/             # CLI tests
├── integration/         # Integration tests
└── fixtures/            # Shared test data
```

## Current Status

✅ **737+ tests passing** across:
- 11 built-in agents
- Event system and coordination
- Configuration management
- CLI interface
- Security features
- Marketplace functionality

## Test Strategy

DevLoop uses:
- **pytest** for test framework
- **pytest-cov** for coverage
- **pytest-asyncio** for async tests
- **fixtures** for setup/teardown

See [docs/TESTING_STRATEGY.md](./docs/TESTING_STRATEGY.md) for detailed testing architecture (if it exists).

## Debugging Tests

### Enable Verbose Output

```bash
poetry run pytest -vv
```

### Show Print Statements

```bash
poetry run pytest -s
```

### Run with Debugging

```bash
poetry run pytest --pdb
```

### Generate Coverage Report

```bash
poetry run pytest --cov=devloop --cov-report=term-missing
```

## Contributing Tests

When adding new features:

1. Write tests first (TDD approach recommended)
2. Ensure tests pass: `poetry run pytest`
3. Check coverage: `poetry run pytest --cov=devloop`
4. Keep coverage above 85%

See [CODING_RULES.md](../CODING_RULES.md) for testing requirements.
