#!/bin/bash
# Update git remote URL after GitHub repository rename

echo "🔄 Updating git remote URL"
echo ""

# Check current remote
CURRENT_REMOTE=$(git remote get-url origin)
echo "Current remote: $CURRENT_REMOTE"

# New remote URL
NEW_REMOTE="https://github.com/wioota/dev-agents.git"
echo "New remote:     $NEW_REMOTE"
echo ""

# Confirm
read -p "Update remote URL? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Update remote
git remote set-url origin "$NEW_REMOTE"

# Verify
echo ""
echo "✅ Remote updated!"
echo ""
git remote -v
echo ""

# Test connectivity
echo "Testing connection to new remote..."
if git ls-remote origin &> /dev/null; then
    echo "✅ Connection successful!"
else
    echo "⚠️  Warning: Could not connect to remote."
    echo "   Make sure the GitHub repository has been renamed first."
    echo "   Go to: https://github.com/wioota/claude-agents/settings"
fi
