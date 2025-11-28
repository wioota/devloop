# Project Rename Plan

## Proposed Name: `dev-agents`

**Current:** dev-agents
**New:** dev-agents
**Rationale:** Not tied to specific AI, describes functionality, professional

## Alternative Names (if dev-agents unavailable)
1. devwatch
2. code-sentinel
3. backdrop
4. dev-conductor

---

## Renaming Checklist

### Phase 1: Preparation (5 min)
- [ ] Stop all running agents (`pkill -f "dev-agents"`)
- [ ] Commit current work
- [ ] Create backup branch: `git checkout -b backup-before-rename`
- [ ] Return to main: `git checkout main`
- [ ] Check PyPI availability: `pip search dev-agents` (or check pypi.org)
- [ ] Check GitHub availability: github.com/[username]/dev-agents
- [ ] Confirm final name choice

### Phase 2: Directory & Package Structure (10 min)

**Directories to rename:**
- [ ] `src/dev_agents/` → `src/dev_agents/`
- [ ] Repository name (GitHub): `dev-agents` → `dev-agents`
- [ ] Virtual environment references

**Commands:**
```bash
# Rename main package directory
mv src/dev_agents src/dev_agents

# Update git remote (after GitHub rename)
# git remote set-url origin https://github.com/[username]/dev-agents.git
```

### Phase 3: Code References (20 min)

**Python imports to update:**
- [ ] `from dev_agents.` → `from dev_agents.`
- [ ] `import dev_agents` → `import dev_agents`
- [ ] Module docstrings mentioning "dev-agents"
- [ ] CLI entry points
- [ ] Test imports

**Files to check (use grep):**
```bash
grep -r "dev_agents" src/ tests/ --include="*.py"
grep -r "dev-agents" . --include="*.py" --include="*.md" --include="*.json" --include="*.toml"
```

**Automated replacement:**
```bash
# Python code
find src/ tests/ -name "*.py" -type f -exec sed -i 's/dev_agents/dev_agents/g' {} +
find src/ tests/ -name "*.py" -type f -exec sed -i 's/dev-agents/dev-agents/g' {} +

# Configuration files
sed -i 's/dev_agents/dev_agents/g' pyproject.toml setup.py
sed -i 's/dev-agents/dev-agents/g' pyproject.toml setup.py
```

### Phase 4: Package Configuration (10 min)

**pyproject.toml:**
- [ ] `name = "dev-agents"`
- [ ] `packages = ["dev_agents"]`
- [ ] `[project.scripts]` → `dev-agents = "dev_agents.cli.main:app"`
- [ ] Update description
- [ ] Update repository URL

**setup.py (if exists):**
- [ ] Update name
- [ ] Update package references
- [ ] Update entry points

**Other config files:**
- [ ] `.claude/settings.local.json` - permission patterns
- [ ] `.claude/CLAUDE.md` - references to package
- [ ] `README.md` - all references
- [ ] `CLAUDE.md` - all references

### Phase 5: Documentation (15 min)

**Files to update:**
- [ ] `README.md` - Title, installation, usage examples
- [ ] `CLAUDE.md` - Overview, references
- [ ] `.claude/CLAUDE.md` - Integration instructions
- [ ] `.claude/README.md` - If exists
- [ ] All `docs/*.md` files
- [ ] `IMPLEMENTATION_COMPLETE.md`
- [ ] `CONTEXT_STORE_STATUS.md`
- [ ] `CLAUDE_CODE_TEST_GUIDE.md`
- [ ] `TESTING_PLAN.md`

**Update these patterns:**
```bash
# Documentation
find . -name "*.md" -type f -exec sed -i 's/dev-agents/dev-agents/g' {} +
find . -name "*.md" -type f -exec sed -i 's/dev_agents/dev_agents/g' {} +

# Be careful with .claude/CLAUDE.md - some references should stay
# as they refer to Claude Code integration
```

### Phase 6: Installation & CLI (10 min)

**Commands to update:**
- [ ] `dev-agents watch` → `dev-agents watch`
- [ ] `dev-agents --help` → `dev-agents --help`
- [ ] All CLI commands in docs
- [ ] Permissions in `.claude/settings.local.json`

**Files with command examples:**
- [ ] README.md
- [ ] All documentation
- [ ] Test files
- [ ] Integration scripts

### Phase 7: Context & Integration Files (5 min)

**Integration scripts:**
- [ ] `.claude/integration/claude-code-adapter.py` - Comments/docstrings
- [ ] `.claude/integration/generate_status.py` - Comments/docstrings
- [ ] Keep "Claude Code" references (these refer to the IDE)

**What NOT to change:**
- ❌ "Claude Code" - refers to Anthropic's IDE
- ❌ "Claude" when referring to the AI assistant
- ❌ `.claude/` directory name (industry standard for Claude Code)

### Phase 8: Git & Version Control (5 min)

- [ ] Update `.gitignore` if needed
- [ ] Create comprehensive commit message
- [ ] Tag the rename: `git tag -a rename-to-dev-agents -m "Rename project from dev-agents to dev-agents"`

### Phase 9: Testing (15 min)

**Reinstall package:**
```bash
pip uninstall dev-agents
pip install -e .
```

**Test commands:**
```bash
dev-agents --help
dev-agents --version
dev-agents watch . --help
```

**Run tests:**
```bash
python -m pytest tests/ -v
python test_context_integration.py
```

**Test imports:**
```python
python -c "from dev_agents.core.agent import Agent; print('✓ Import works')"
python -c "from dev_agents.core.context_store import context_store; print('✓ Context store works')"
```

### Phase 10: Cleanup (5 min)

- [ ] Delete old `.pyc` files: `find . -name "*.pyc" -delete`
- [ ] Delete old `__pycache__`: `find . -type d -name "__pycache__" -exec rm -rf {} +`
- [ ] Regenerate virtual environment if needed
- [ ] Update any running background processes

---

## Automated Rename Script

Create `rename_project.sh`:

```bash
#!/bin/bash
set -e

OLD_NAME="dev-agents"
OLD_PKG="dev_agents"
NEW_NAME="dev-agents"
NEW_PKG="dev_agents"

echo "🔄 Renaming project: $OLD_NAME → $NEW_NAME"
echo "Package: $OLD_PKG → $NEW_PKG"
echo ""

# Stop running agents
echo "1. Stopping running agents..."
pkill -f "$OLD_NAME" || true

# Backup
echo "2. Creating backup branch..."
git checkout -b "backup-before-rename-$(date +%Y%m%d)" || true
git checkout main

# Rename directory
echo "3. Renaming package directory..."
mv "src/$OLD_PKG" "src/$NEW_PKG"

# Update Python files
echo "4. Updating Python imports..."
find src/ tests/ -name "*.py" -type f -exec sed -i "s/$OLD_PKG/$NEW_PKG/g" {} +
find src/ tests/ -name "*.py" -type f -exec sed -i "s/$OLD_NAME/$NEW_NAME/g" {} +

# Update config files
echo "5. Updating configuration..."
sed -i "s/$OLD_PKG/$NEW_PKG/g" pyproject.toml
sed -i "s/$OLD_NAME/$NEW_NAME/g" pyproject.toml

# Update documentation
echo "6. Updating documentation..."
find . -name "*.md" -type f -exec sed -i "s/$OLD_NAME/$NEW_NAME/g" {} +
find . -name "*.md" -type f -exec sed -i "s/$OLD_PKG/$NEW_PKG/g" {} +

# Update .claude/settings.local.json
echo "7. Updating settings..."
sed -i "s/$OLD_NAME/$NEW_NAME/g" .claude/settings.local.json
sed -i "s/$OLD_PKG/$NEW_PKG/g" .claude/settings.local.json

# Cleanup
echo "8. Cleaning up..."
find . -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo ""
echo "✅ Rename complete!"
echo ""
echo "Next steps:"
echo "1. Review changes: git diff"
echo "2. Test installation: pip install -e ."
echo "3. Test CLI: $NEW_NAME --help"
echo "4. Run tests: python -m pytest"
echo "5. Commit: git add -A && git commit -m 'Rename project to $NEW_NAME'"
echo "6. Update GitHub repo name manually"
```

---

## Special Considerations

### Claude Code Integration
Keep these references as-is:
- "Claude Code" (the IDE name)
- "Claude" (the AI assistant)
- `.claude/` directory (standard)
- Comments explaining Claude Code integration

### Backward Compatibility
Consider creating a deprecation notice:
```python
# src/dev_agents/__init__.py
import warnings

# Backward compatibility check
try:
    import dev_agents
    warnings.warn(
        "Package renamed from 'dev-agents' to 'dev-agents'. "
        "Please update imports and uninstall old package.",
        DeprecationWarning
    )
except ImportError:
    pass
```

### PyPI Publishing
If package is on PyPI:
1. Publish new `dev-agents` package
2. Update `dev-agents` to be a stub that redirects
3. Add deprecation notice to old package

### GitHub
1. Rename repository: Settings → Repository name
2. Update remote: `git remote set-url origin [new-url]`
3. GitHub will redirect old URLs automatically

---

## Timeline Estimate

- **Preparation:** 5 minutes
- **Rename execution:** 30 minutes
- **Testing:** 15 minutes
- **Documentation review:** 10 minutes
- **Total:** ~60 minutes

## Rollback Plan

If issues arise:
```bash
# Return to backup branch
git checkout backup-before-rename

# Or revert the commit
git revert HEAD

# Or use reflog
git reflog
git reset --hard HEAD@{n}
```

---

## Post-Rename Verification

Checklist:
- [ ] `dev-agents --help` works
- [ ] `dev-agents watch .` starts agents
- [ ] Tests pass
- [ ] Documentation renders correctly
- [ ] GitHub repo renamed
- [ ] Old imports don't exist in codebase
- [ ] Package installs correctly
