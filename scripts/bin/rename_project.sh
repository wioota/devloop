#!/bin/bash
set -e

OLD_NAME="claude-agents"
OLD_PKG="claude_agents"
NEW_NAME="dev-agents"
NEW_PKG="dev_agents"

echo "🔄 Renaming project: $OLD_NAME → $NEW_NAME"
echo "Package: $OLD_PKG → $NEW_PKG"
echo ""
echo "This will:"
echo "  1. Stop running agents"
echo "  2. Create backup branch"
echo "  3. Rename src/$OLD_PKG to src/$NEW_PKG"
echo "  4. Update all code references"
echo "  5. Update configuration files"
echo "  6. Update documentation"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Stop running agents
echo ""
echo "📍 Step 1: Stopping running agents..."
pkill -f "$OLD_NAME" || echo "  (no running agents found)"

# Backup
echo ""
echo "📍 Step 2: Creating backup branch..."
BACKUP_BRANCH="backup-before-rename-$(date +%Y%m%d-%H%M%S)"
git checkout -b "$BACKUP_BRANCH" 2>/dev/null || echo "  (branch already exists)"
git checkout main

# Rename directory
echo ""
echo "📍 Step 3: Renaming package directory..."
if [ -d "src/$OLD_PKG" ]; then
    mv "src/$OLD_PKG" "src/$NEW_PKG"
    echo "  ✓ Renamed src/$OLD_PKG → src/$NEW_PKG"
else
    echo "  ⚠ Package directory not found (may already be renamed)"
fi

# Update Python files
echo ""
echo "📍 Step 4: Updating Python imports..."
COUNT=$(find src/ tests/ -name "*.py" -type f 2>/dev/null | wc -l)
echo "  Processing $COUNT Python files..."
find src/ tests/ -name "*.py" -type f -exec sed -i "s/$OLD_PKG/$NEW_PKG/g" {} + 2>/dev/null || true
find src/ tests/ -name "*.py" -type f -exec sed -i "s/$OLD_NAME/$NEW_NAME/g" {} + 2>/dev/null || true
echo "  ✓ Updated Python imports"

# Update config files
echo ""
echo "📍 Step 5: Updating configuration..."
if [ -f "pyproject.toml" ]; then
    sed -i "s/$OLD_PKG/$NEW_PKG/g" pyproject.toml
    sed -i "s/$OLD_NAME/$NEW_NAME/g" pyproject.toml
    echo "  ✓ Updated pyproject.toml"
fi
if [ -f "setup.py" ]; then
    sed -i "s/$OLD_PKG/$NEW_PKG/g" setup.py
    sed -i "s/$OLD_NAME/$NEW_NAME/g" setup.py
    echo "  ✓ Updated setup.py"
fi

# Update documentation
echo ""
echo "📍 Step 6: Updating documentation..."
COUNT=$(find . -name "*.md" -type f 2>/dev/null | wc -l)
echo "  Processing $COUNT markdown files..."
find . -name "*.md" -type f -exec sed -i "s/$OLD_NAME/$NEW_NAME/g" {} + 2>/dev/null || true
find . -name "*.md" -type f -exec sed -i "s/$OLD_PKG/$NEW_PKG/g" {} + 2>/dev/null || true
echo "  ✓ Updated documentation"

# Update .claude/settings.local.json
echo ""
echo "📍 Step 7: Updating .claude settings..."
if [ -f ".claude/settings.local.json" ]; then
    sed -i "s/$OLD_NAME/$NEW_NAME/g" .claude/settings.local.json
    sed -i "s/$OLD_PKG/$NEW_PKG/g" .claude/settings.local.json
    echo "  ✓ Updated .claude/settings.local.json"
fi

# Update .claude/CLAUDE.md
if [ -f ".claude/CLAUDE.md" ]; then
    # Be careful - keep "Claude Code" references
    sed -i "s/claude-agents/$NEW_NAME/g" .claude/CLAUDE.md
    sed -i "s/claude_agents/$NEW_PKG/g" .claude/CLAUDE.md
    echo "  ✓ Updated .claude/CLAUDE.md"
fi

# Cleanup
echo ""
echo "📍 Step 8: Cleaning up..."
find . -name "*.pyc" -delete 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo "  ✓ Removed cache files"

echo ""
echo "✅ Rename complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Review changes:        git diff"
echo "  2. Test installation:     pip uninstall $OLD_NAME && pip install -e ."
echo "  3. Test CLI:              $NEW_NAME --help"
echo "  4. Run tests:             python -m pytest tests/ -v"
echo "  5. Commit changes:        git add -A && git commit -m 'Rename project to $NEW_NAME'"
echo "  6. Update GitHub:         Manually rename repo in GitHub settings"
echo ""
echo "💾 Backup branch created: $BACKUP_BRANCH"
echo "   (rollback with: git checkout $BACKUP_BRANCH)"
