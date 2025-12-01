# DevLoop Renaming Plan

A comprehensive plan to rename the project from "devloop"/"DevLoop" to "devloop"/"DevLoop".

## Overview

This is a structured, executable plan for renaming the entire project. It covers:
- Directory structure changes
- Python package renaming
- Configuration and metadata updates
- Documentation updates
- GitHub/repository changes
- Git history handling

---

## Phase 1: Preparation (Pre-Execution)

### 1.1 Backup & Version Control
- [ ] Commit all current work
- [ ] Create a new branch: `git checkout -b rename/devloop`
- [ ] Verify clean working directory: `git status`

### 1.2 Checklist Verification
Before proceeding, verify:
- [ ] All tests passing: `poetry run pytest`
- [ ] No uncommitted changes
- [ ] Remote is synced

---

## Phase 2: Core Package Renaming

### 2.1 Python Package Structure
**Current:** `src/devloop/` → **New:** `src/devloop/`

```bash
# Step 1: Rename the package directory
mv src/devloop src/devloop

# Step 2: Update __init__.py files if they reference the package name
# (Usually not needed, but check for hardcoded strings)
```

**Files affected:**
- `src/devloop/` directory → `src/devloop/`
- All subdirectories remain the same structure

### 2.2 Python Module Imports
**Pattern:** `from devloop.*` → `from devloop.*`

Use ripgrep to find and replace all imports:

```bash
# Find all import statements
grep -r "from devloop" src/ tests/ --include="*.py"
grep -r "import devloop" src/ tests/ --include="*.py"

# Replace all occurrences (using sed or similar)
find src/ tests/ -name "*.py" -exec sed -i 's/from devloop/from devloop/g' {} \;
find src/ tests/ -name "*.py" -exec sed -i 's/import devloop/import devloop/g' {} \;
```

**Directories to search:**
- `src/**/*.py`
- `tests/**/*.py`
- Root-level test files (*.py)

### 2.3 Configuration Files

#### 2.3.1 pyproject.toml
```toml
# OLD
[tool.poetry]
name = "devloop"
packages = [{include = "devloop", from = "src"}]

[tool.poetry.scripts]
devloop = "devloop.cli.main:app"

# NEW
[tool.poetry]
name = "devloop"
packages = [{include = "devloop", from = "src"}]

[tool.poetry.scripts]
devloop = "devloop.cli.main:app"
```

**Changes:**
- Project name: `devloop` → `devloop`
- Package include: `devloop` → `devloop`
- CLI entry point: `devloop` → `devloop`

#### 2.3.2 setup.py
- Update package name from `devloop` to `devloop`
- Update py_modules to use `devloop` instead of `devloop`

---

## Phase 3: Configuration & Metadata

### 3.1 Directory Names in Config
**.devloop directory → .devloop**

This directory is referenced in many config files and code. Changes needed in:

```bash
# 1. Rename directory
mv .devloop .devloop

# 2. Update all references (run search & replace)
grep -r "\.devloop" . --include="*.py" --include="*.md" --include="*.json"

# Replace in Python files
find . -name "*.py" -exec sed -i 's/\.devloop/.devloop/g' {} \;

# Replace in Markdown files
find . -name "*.md" -exec sed -i 's/\.devloop/.devloop/g' {} \;
```

**Files containing references:**
- `src/devloop/core/config.py` (many references)
- `src/devloop/core/manager.py`
- `src/devloop/core/event_store.py`
- `src/devloop/agents/file_logger.py`
- `src/devloop/cli/main.py`
- `src/devloop/cli/commands/custom_agents.py`
- `src/devloop/cli/commands/feedback.py`
- `src/devloop/core/context_store.py`
- All documentation files (*.md)

### 3.2 String References in Code
**Pattern:** `"devloop"` → `"devloop"`

Search for hardcoded strings:
- Help text in CLI
- Error messages
- Log messages
- Comments

```bash
# Find all string references
grep -r '"devloop"' . --include="*.py"
grep -r "'devloop'" . --include="*.py"

# Example locations:
# - src/devloop/cli/main.py (help text)
# - src/devloop/cli/main_v1.py (help text)
# - src/devloop/core/summary_formatter.py (help text)
```

---

## Phase 4: Documentation Updates

### 4.1 README.md Changes
**Current section:**
```markdown
# DevLoop
# Quick Start
git clone https://github.com/wioota/devloop
cd devloop
devloop init /path/to/your/project
devloop watch .
```

**New section:**
```markdown
# DevLoop
# Quick Start
git clone https://github.com/wioota/devloop
cd devloop
devloop init /path/to/your/project
devloop watch .
```

**Search & replace:**
- `devloop` → `devloop` (command references)
- `DevLoop` → `DevLoop` (title references)
- `devloop` → `devloop` (code references)

### 4.2 Other Documentation Files
Update all `.md` files:
- `AGENTS.md` - References to "devloop"
- `AMP_ONBOARDING.md` - Amp integration guides
- `CODING_RULES.md` - Code style guides
- `INSTALLATION_AUTOMATION.md` - Installation docs
- All docs in `docs/` directory (if exists)
- All other markdown files referencing the tool

---

## Phase 5: GitHub & Repository

### 5.1 Repository Metadata
If using GitHub:
- [ ] Repository URL will change: `.../devloop` → `.../devloop`
- Update in:
  - `README.md` links
  - `CONTRIBUTING.md`
  - Issue/PR templates (if any)

### 5.2 Git Configuration
```bash
# Update git remote (if changing repo name)
git remote set-url origin https://github.com/wioota/devloop.git

# Or keep as-is if just renaming the project, not the repo
```

### 5.3 Workflow Files
Update `.github/workflows/*.yml`:
- References to `devloop` command
- References to package paths
- References in documentation links

---

## Phase 6: Testing & Validation

### 6.1 Import Testing
```bash
# Verify imports work
cd /path/to/project
poetry install

# Test basic imports
python -c "from devloop.core.agent import Agent; print('✓ Imports work')"
python -c "from devloop.cli.main import app; print('✓ CLI imports work')"
```

### 6.2 Test Suite
```bash
# Run all tests
poetry run pytest tests/ -v

# Run specific test categories
poetry run pytest tests/unit/ -v
poetry run pytest tests/integration/ -v
```

### 6.3 CLI Testing
```bash
# Test CLI command availability
devloop --help
devloop status
devloop watch . --help
```

### 6.4 Documentation Check
- [ ] All code examples in docs use correct command names
- [ ] All import examples use `devloop` not `devloop`
- [ ] All directory references use `.devloop` not `.devloop`

---

## Phase 7: Version & Release

### 7.1 Version Update
Update version if needed:
```toml
# pyproject.toml
[tool.poetry]
version = "0.2.0"  # Or appropriate version bump
```

### 7.2 Changelog
Add entry to `CHANGELOG.md`:
```markdown
## [0.2.0] - YYYY-MM-DD

### Changed
- **BREAKING:** Renamed project from "DevLoop" to "DevLoop"
  - Python package: `devloop` → `devloop`
  - CLI command: `devloop` → `devloop`
  - Config directory: `.devloop` → `.devloop`
  - All imports updated to use `devloop`
```

---

## Phase 8: Final Steps

### 8.1 Commit Changes
```bash
# Stage all changes
git add -A

# Create comprehensive commit message
git commit -m "refactor: rename project from devloop to devloop

- Rename Python package: src/devloop → src/devloop
- Update CLI command: devloop → devloop
- Rename config dir: .devloop → .devloop
- Update all imports throughout codebase
- Update all documentation and examples
- Update configuration files (pyproject.toml, setup.py)
- Update README and all markdown files

This is a breaking change for users of the previous version.
Installation command changes to: pip install devloop
CLI command changes to: devloop [command]"
```

### 8.2 Push to Remote
```bash
git push origin rename/devloop

# Create PR if using GitHub, or merge directly:
git checkout main
git merge rename/devloop
git push origin main
```

### 8.3 Tag Release
```bash
git tag -a v0.2.0 -m "Release: Rename to DevLoop"
git push origin v0.2.0
```

---

## Checklist Summary

**Pre-Execution:**
- [ ] All tests passing
- [ ] Clean working directory
- [ ] Branch created

**Package & Code:**
- [ ] `src/devloop/` → `src/devloop/`
- [ ] All imports updated
- [ ] All string references updated
- [ ] Configuration files updated

**Configuration:**
- [ ] `.devloop/` → `.devloop/`
- [ ] All path references updated
- [ ] CLI entry point updated

**Documentation:**
- [ ] README.md updated
- [ ] All markdown files updated
- [ ] Code examples corrected
- [ ] Install instructions updated

**Testing:**
- [ ] Tests running successfully
- [ ] CLI working
- [ ] Imports verified

**Release:**
- [ ] Version updated
- [ ] Changelog updated
- [ ] Changes committed
- [ ] Changes pushed
- [ ] Tag created

---

## Estimated Impact

**Files to modify:** ~150+ files across:
- Python source code
- Test files
- Configuration files
- Documentation files
- GitHub workflows

**Breaking changes:**
- Users must reinstall: `pip install devloop`
- CLI command changes from `devloop` to `devloop`
- Config directory changes from `.devloop` to `.devloop`
- All imports must be updated if used as a library

**Non-breaking with migration:**
- Provide migration guide for users
- Consider keeping symlinks in `.devloop/.devloop` for backward compat
- Document upgrade path

---

## Scripts for Batch Operations

### Bulk Search & Replace Script
```bash
#!/bin/bash
# save as: scripts/rename-devloop.sh

# Search patterns to replace
declare -a patterns=(
    "devloop:devloop"
    "devloop:devloop"
    "DevLoop:DevLoop"
    ".devloop:.devloop"
)

for pattern in "${patterns[@]}"; do
    old="${pattern%:*}"
    new="${pattern#*:}"
    echo "Replacing: $old → $new"
    find . -type f \( -name "*.py" -o -name "*.md" -o -name "*.json" \) -exec sed -i "s/$old/$new/g" {} \;
done

echo "Renaming directories..."
mv src/devloop src/devloop 2>/dev/null || true
mv .devloop .devloop 2>/dev/null || true

echo "✓ Bulk renaming complete"
```

---

## Next Steps

1. **Review this plan** - Ensure no items are missed
2. **Execute in order** - Follow phases sequentially
3. **Test thoroughly** - Run full test suite after each phase
4. **Commit frequently** - Small, logical commits are better than one huge commit
5. **Document any issues** - If problems arise, document solution for reference

---

## Questions to Resolve Before Execution

1. Should we keep the GitHub repo name or change it too?
2. Do we need backward compatibility or is breaking change acceptable?
3. Should we migrate existing .devloop directories or force users to reinit?
4. Will we maintain the old devloop package for legacy users?
