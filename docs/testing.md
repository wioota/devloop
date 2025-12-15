# Testing Guide

## Running Tests

```bash
# All tests
poetry run pytest

# With coverage
poetry run pytest --cov=devloop

# Specific test file
poetry run pytest tests/unit/agents/test_linter.py -v
```

## Test Status

✅ 737+ tests passing

## Test Organization

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests
└── fixtures/       # Test fixtures and data
```

## Writing Tests

See [CODING_RULES.md](../CODING_RULES.md) for testing standards and requirements.
