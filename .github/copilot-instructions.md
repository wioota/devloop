# GitHub Copilot Instructions for DevLoop

## Project Overview

**DevLoop** is a comprehensive background agent system that monitors development lifecycle events and provides intelligent assistance during software development.

**Key Features:**
- Event-driven agent architecture
- Autonomous monitoring and response
- Configurable workflows for different development patterns
- Integration with existing tools (Git, LSP, IDEs)

## Tech Stack

- **Language**: Python 3.9+
- **Build**: Poetry
- **Testing**: Pytest
- **Code Quality**: Ruff, MyPy
- **CI/CD**: GitHub Actions
- **IaC**: DevLoop agents

## Coding Guidelines

### Testing
- Always write tests for new features
- Use pytest fixtures for setup/teardown
- Run `poetry run pytest` before committing
- Aim for 80%+ code coverage

### Code Style
- Run `poetry run ruff check . --fix` before committing
- Run `poetry run mypy .` for type checking
- Follow PEP 8 conventions
- Use type hints throughout

### Git Workflow
- Always commit `.beads/issues.jsonl` with code changes
- Use `bd sync` to flush changes to git immediately
- Write descriptive commit messages

## Issue Tracking with bd

**CRITICAL**: This project uses **bd (beads)** for ALL task tracking. Do NOT create markdown TODO lists.

### Essential Commands

```bash
# Find work
bd ready --json                    # Unblocked issues
bd stale --days 30 --json          # Forgotten issues

# Create and manage
bd create "Title" -t bug|feature|task -p 0-4 --json
bd update <id> --status in_progress --json
bd close <id> --reason "Done" --json

# Search
bd list --status open --priority 1 --json
bd show <id> --json

# Sync (CRITICAL at end of session!)
bd sync  # Force immediate export/commit/push
```

### Workflow

1. **Check ready work**: `bd ready --json`
2. **Claim task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** `bd create "Found bug" -p 1 --deps discovered-from:<parent-id> --json`
5. **Complete**: `bd close <id> --reason "Done" --json`
6. **Sync**: `bd sync` (flushes changes to git immediately)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

## Project Structure

```
devloop/
├── src/
│   ├── devloop/          # Main package
│   │   ├── agents/       # Agent implementations
│   │   ├── events/       # Event system
│   │   ├── config/       # Configuration
│   │   └── cli/          # CLI commands
├── tests/                # Test suite
├── docs/                 # Documentation
├── examples/             # Integration examples
└── .beads/
    ├── beads.db          # SQLite database (DO NOT COMMIT)
    └── issues.jsonl      # Git-synced issue storage
```

## Available Resources

### Key Documentation
- **AGENTS.md** - Comprehensive agent system guide
- **CODING_RULES.md** - Development discipline and workflow
- **README.md** - User-facing documentation
- **docs/** - Detailed technical documentation

### Scripts
- `scripts/test.sh` - Run test suite
- `scripts/lint.sh` - Run linters
- `scripts/format.sh` - Format code

## Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic bd commands
- ✅ Run `bd sync` at end of sessions
- ✅ Write tests for new features
- ✅ Run linters before committing
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT skip type checking
- ❌ Do NOT commit without running tests

---

**For detailed workflows and advanced features, see [AGENTS.md](../AGENTS.md)**
