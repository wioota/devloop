# CI Quality Commitment

## Overview

This document outlines our commitment to maintaining a clean, reliable CI/CD pipeline that ensures code quality and prevents regressions.

## Clean Bill of Health Requirements

All CI checks must pass with zero failures, warnings, or errors before code can be merged:

### ✅ Code Quality Checks
- **Black Formatting**: All Python code must be properly formatted
- **Ruff Linting**: Zero linting errors or warnings
- **Tests**: All unit tests must pass (currently 96 tests)
- **Type Checking**: Mypy validation (temporarily disabled pending type annotation fixes)

### ✅ Security Checks
- **Bandit Security Scan**: Address high and medium severity issues
  - High: Shell injection vulnerabilities (fixed)
  - Medium: Use of exec() in dynamic code loading
  - Low: Subprocess usage warnings (acceptable for controlled environments)

### ✅ Quality Gates
- No deprecated API usage (datetime.utcnow() → datetime.now(UTC))
- No unnecessary async decorators on sync functions
- Proper error handling without silent exceptions

## Development Workflow

### Pre-Commit Checklist
- [ ] Run `black --check src/ tests/` - passes formatting
- [ ] Run `ruff check src/` - zero linting issues
- [ ] Run `pytest -v` - all tests pass
- [ ] Run `bandit -r src/` - review security issues
- [ ] Address any deprecation warnings

### CI Failure Response
1. **Immediate Action**: Fix critical failures within 1 hour
2. **Investigation**: Identify root cause and prevent recurrence
3. **Documentation**: Update this document if new checks are added
4. **Prevention**: Add tests or linting rules for similar issues

## Tool Configuration

### Black
```toml
[tool.black]
line-length = 88
target-version = ['py311']
```

### Ruff
```toml
[tool.ruff]
line-length = 88
target-version = "py311"
```

### MyPy (Temporarily Relaxed)
```toml
[tool.mypy]
python_version = "3.11"
# Strict checks disabled until type annotations are complete
```

## Maintenance

### Monthly Review
- Review CI performance and failure patterns
- Update tool versions and configurations
- Assess test coverage and quality

### Tool Updates
- Keep Black, Ruff, MyPy, and Bandit updated
- Review new rules and enable beneficial ones
- Update Python version support as needed

## Accountability

**All team members are responsible for:**
- Ensuring their changes don't break CI
- Fixing CI failures promptly
- Maintaining code quality standards
- Updating this document when processes change

**Violation of these standards may result in:**
- Revert of breaking changes
- Mandatory code review for future PRs
- Additional quality checks added to prevent recurrence

## Emergency Procedures

If CI is broken for >4 hours:
1. Create emergency fix branch
2. Implement minimal fix to restore CI
3. Add comprehensive tests to prevent regression
4. Merge emergency fix with priority

---

*This commitment ensures reliable, high-quality code delivery and maintains trust in our CI pipeline.*
