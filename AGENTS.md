# Agent Development Rules & Processes

## Overview

This document contains specific rules and processes for Amp (the AI agent) when developing and modifying the dev-agents codebase.

## Core Rules

### 1. Commit Progress Hook
**MANDATORY**: Before completing any task or ending a session, commit all progress with a descriptive message.

**Process**:
1. Always check git status: `git status`
2. Stage relevant changes: `git add <files>` or `git add .`
3. Commit with clear message: `git commit -m "brief description of changes"`
4. If significant work is done, push to remote: `git push`

**Rule**: Never end a session without committing progress. This ensures work is never lost and provides clear development history.

### 2. Todo List Management
- Use the todo system proactively to track progress
- Update todo status as work is completed
- Break complex tasks into smaller, trackable items

### 3. Code Quality Standards
- Follow all patterns in CODING_RULES.md
- Run tests before committing: `pytest -v`
- Fix linting issues: `ruff check src/ tests/`
- Format code: `black src/ tests/`

### 4. Error Handling
- Test error conditions thoroughly
- Provide clear error messages
- Log errors appropriately
- Handle edge cases gracefully

### 5. Documentation Updates
- Update documentation when functionality changes
- Add code comments for complex logic
- Keep examples current and working

## Development Workflow

### Starting Work
1. Check current status: `git status`
2. Pull latest changes: `git pull` (if collaborative)
3. Create/update todo list for the task
4. Begin implementation

### During Development
1. Test changes incrementally
2. Run linting/formatting as needed
3. Update todos as tasks complete
4. Commit small, logical chunks of work

### Ending Session
1. **MANDATORY**: Run final tests: `pytest`
2. **MANDATORY**: Fix any failing tests or critical issues
3. **MANDATORY**: Commit all changes: `git commit -m "description"`
4. **MANDATORY**: Push if appropriate: `git push`

## Quality Gates

### Pre-Commit Checklist
- [ ] Tests pass: `pytest`
- [ ] Code lints clean: `ruff check src/ tests/`
- [ ] Code formatted: `black --check src/ tests/`
- [ ] No syntax errors: `python -m py_compile src/dev_agents/**/*.py`
- [ ] Documentation updated if needed
- [ ] Todo list updated

### Session End Checklist
- [ ] All work committed
- [ ] Repository in clean state
- [ ] No uncommitted changes
- [ ] Progress documented

## Emergency Procedures

If something breaks critically:
1. Don't panic - work can be recovered
2. Check git status to see what changed
3. Use `git stash` if needed to temporarily save work
4. Fix the issue
5. `git stash pop` to restore work
6. Commit the fix

## Tool Usage Guidelines

### Git
- Commit early and often
- Use descriptive commit messages
- Don't commit broken code
- Use branches for experimental features

### Testing
- Write tests for new functionality
- Run full test suite before committing
- Don't break existing functionality
- Test error conditions

### Code Quality
- Fix linting issues before committing
- Format code consistently
- Add type hints where possible
- Document complex functions

## Accountability

As Amp, you are responsible for:
- Following these processes consistently
- Maintaining code quality standards
- Ensuring work is properly committed
- Providing clear progress updates
- Fixing issues promptly

**Violation of these rules may result in lost work or broken functionality.**
