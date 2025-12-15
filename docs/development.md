# Development Guide

## Setup

```bash
git clone https://github.com/wioota/devloop
cd devloop
poetry install
poetry run pytest
```

## Code Style

- **Formatter:** Black
- **Linter:** Ruff
- **Type Checker:** mypy
- **Python Version:** 3.11+

```bash
poetry run black src tests
poetry run ruff check --fix src tests
poetry run mypy src
```

## Contributing

See [CODING_RULES.md](../CODING_RULES.md) for:
- Code style guidelines
- Testing requirements
- Commit message format
- Pull request process

## Project Structure

```
devloop/
├── src/devloop/
│   ├── core/              # Event system, agents, context
│   ├── collectors/        # Event collectors
│   ├── agents/            # Built-in agents
│   └── cli/               # CLI interface
├── tests/                 # Unit and integration tests
└── pyproject.toml         # Poetry configuration
```
