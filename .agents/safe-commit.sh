#!/usr/bin/env bash

# Safe commit script - enforces commit + push discipline
# Usage: .agents/safe-commit.sh "commit message" [files...]
# Example: .agents/safe-commit.sh "Fix CLI tests" src/dev_agents/cli/
#
# This script ensures all work is committed AND pushed before moving on,
# implementing the mandatory discipline defined in AGENTS.md and CODING_RULES.md

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: Missing commit message${NC}"
    echo "Usage: .agents/safe-commit.sh \"commit message\" [files to add...]"
    echo ""
    echo "Examples:"
    echo "  .agents/safe-commit.sh \"Fix CLI tests\" src/ tests/"
    echo "  .agents/safe-commit.sh \"Add docs\""
    exit 1
fi

COMMIT_MESSAGE="$1"
shift

echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo "Safe Commit & Push"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Step 1: Stage files
echo -e "${YELLOW}Step 1: Staging files...${NC}"
if [ $# -gt 0 ]; then
    # Files provided as arguments
    git add "$@"
    echo "  Added: $@"
else
    # No files specified - stage all changes
    git add -A
    echo "  Added all changes"
fi
echo ""

# Verify something was staged
if git diff --cached --quiet; then
    echo -e "${YELLOW}Warning: Nothing to commit (working tree clean)${NC}"
    echo ""
    exit 0
fi

# Step 2: Show what will be committed
echo -e "${YELLOW}Step 2: Changes to commit:${NC}"
git diff --cached --name-only | sed 's/^/  /'
echo ""

# Step 3: Commit
echo -e "${YELLOW}Step 3: Committing...${NC}"
git commit -m "$COMMIT_MESSAGE"
COMMIT_SHA=$(git rev-parse --short HEAD)
echo -e "${GREEN}✓ Committed: $COMMIT_SHA${NC}"
echo "  Message: $COMMIT_MESSAGE"
echo ""

# Step 4: Push
echo -e "${YELLOW}Step 4: Pushing to origin/main...${NC}"
if git push origin main; then
    echo -e "${GREEN}✓ Pushed successfully${NC}"
else
    echo -e "${RED}✗ Push failed${NC}"
    echo "  Your commit is local but not pushed."
    echo "  Run: git push origin main"
    exit 1
fi
echo ""

# Step 5: Verify
echo -e "${YELLOW}Step 5: Verifying...${NC}"
if .agents/verify-task-complete; then
    echo ""
    echo -e "${GREEN}✨ All done! Changes committed and pushed.${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}⚠️  Verification failed${NC}"
    exit 1
fi
