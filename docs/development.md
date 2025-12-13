# Development Guide

Guidelines for contributing to DevLoop.

## Setting Up for Development

```bash
git clone https://github.com/wioota/devloop
cd devloop
poetry install
poetry shell
```

## Project Structure

```
devloop/
├── src/devloop/
│   ├── core/              # Event system, agents, context
│   │   ├── agent.py       # Agent base class
│   │   ├── event.py       # Event definitions
│   │   └── context.py     # Context store
│   ├── collectors/        # Event collectors
│   │   ├── filesystem.py
│   │   ├── git.py
│   │   └── process.py
│   ├── agents/            # Built-in agents
│   │   ├── linter.py
│   │   ├── formatter.py
│   │   └── ...
│   └── cli/               # CLI interface
│       └── main.py
├── tests/                 # Unit and integration tests
├── docs/                  # Documentation
└── pyproject.toml         # Poetry configuration
```

## Code Style

DevLoop follows strict code quality standards:

### Formatters & Linters

```bash
# Format with Black
poetry run black src tests

# Lint with Ruff
poetry run ruff check --fix src tests

# Type check with mypy
poetry run mypy src
```

### Pre-commit Hook

The pre-commit hook automatically runs formatting and linting on staged files.

Run manually:
```bash
.git/hooks/pre-commit
```

### Python Version

- **Minimum**: Python 3.11
- **Target**: Python 3.11+
- **Supported**: 3.11, 3.12

## Adding a New Agent

1. Create `src/devloop/agents/my_agent.py`:

```python
from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event

class MyAgent(Agent):
    async def handle(self, event: Event) -> AgentResult:
        # Your logic here
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0.1,
            message="Processed successfully"
        )
```

2. Register in `src/devloop/cli/main.py`

3. Add tests in `tests/unit/agents/test_my_agent.py`

4. Update `docs/agents.md` documentation

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=devloop

# Run specific test
poetry run pytest tests/unit/agents/test_linter.py -v

# Watch mode
poetry run pytest-watch
```

**Coverage requirement**: Aim for >85% coverage on new code.

## Making Changes

### Commit Discipline

Use the pre-commit hook to ensure code quality:

```bash
git add .
git commit -m "Feature/fix description"
```

If the hook fails:
1. Fix the issues it reports
2. Run formatters if needed: `black src tests && ruff check --fix src tests`
3. Try committing again

### Git Workflow

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Run tests: `poetry run pytest`
4. Commit: `git commit -m "..."`
5. Push: `git push origin feature/my-feature`
6. Create a PR

### Commit Messages

Follow the format from [CODING_RULES.md](../CODING_RULES.md):

```
<type>: <subject>

<body>

<footer>
```

## Publishing

See [AGENTS.md](../AGENTS.md) for the complete release process.

Quick version:
```bash
# Update version
python scripts/bump-version.py X.Y.Z

# Update CHANGELOG.md
# Edit CHANGELOG.md with release notes

# Commit
git add pyproject.toml CHANGELOG.md poetry.lock
git commit -m "Release vX.Y.Z"

# Tag
git tag -a vX.Y.Z -m "Release notes"

# Push
git push origin main vX.Y.Z
```

## Documentation

All features should have corresponding documentation:
- Code comments for complex logic
- Docstrings on public APIs
- Update `docs/` for user-facing features
- Update `CHANGELOG.md` for releases

## Resources

- [CODING_RULES.md](../CODING_RULES.md) - Style and discipline rules
- [AGENTS.md](../AGENTS.md) - System architecture
- [README.md](../README.md) - Project overview
