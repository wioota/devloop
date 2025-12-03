#!/bin/bash
# Local verification script - run before pushing to catch issues in seconds instead of waiting for CI
# Usage: ./scripts/verify-before-push.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}[Verify] Running pre-push verification checks...${NC}\n"

FAILED=0

# 1. Check poetry.lock sync
echo -e "${YELLOW}[1/5] Checking poetry.lock sync...${NC}"
if git diff --name-only | grep -q "pyproject.toml"; then
    if ! git diff --name-only | grep -q "poetry.lock"; then
        echo -e "${RED}✗ ERROR: pyproject.toml changed but poetry.lock not updated${NC}"
        echo "Fix: poetry lock && git add poetry.lock"
        FAILED=1
    else
        echo -e "${GREEN}✓ poetry.lock is in sync${NC}"
    fi
else
    echo -e "${GREEN}✓ pyproject.toml not modified${NC}"
fi
echo ""

# 2. Check code formatting (Black)
echo -e "${YELLOW}[2/5] Checking code formatting with Black...${NC}"
if poetry run black --check src/ tests/ 2>/dev/null; then
    echo -e "${GREEN}✓ Code formatting OK${NC}"
else
    echo -e "${RED}✗ Code formatting issues found${NC}"
    echo "Fix: poetry run black src/ tests/"
    FAILED=1
fi
echo ""

# 3. Check linting (Ruff)
echo -e "${YELLOW}[3/5] Checking linting with Ruff...${NC}"
if poetry run ruff check src/ tests/ 2>/dev/null; then
    echo -e "${GREEN}✓ Linting OK${NC}"
else
    echo -e "${RED}✗ Linting issues found${NC}"
    echo "Fix: poetry run ruff check --fix src/ tests/"
    FAILED=1
fi
echo ""

# 4. Check type safety (mypy)
echo -e "${YELLOW}[4/5] Checking type safety with mypy...${NC}"
if poetry run mypy src/ 2>/dev/null | grep -q "error:"; then
    echo -e "${RED}✗ Type checking errors found${NC}"
    poetry run mypy src/ 2>&1 | head -20
    FAILED=1
else
    echo -e "${GREEN}✓ Type checking OK${NC}"
fi
echo ""

# 5. Run tests (quick smoke test)
echo -e "${YELLOW}[5/5] Running tests...${NC}"
if poetry run pytest -x --tb=short 2>&1 | tail -5; then
    echo -e "${GREEN}✓ Tests passed${NC}"
else
    echo -e "${RED}✗ Tests failed${NC}"
    FAILED=1
fi
echo ""

# Summary
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Safe to push.${NC}"
    exit 0
else
    echo -e "${RED}❌ Some checks failed. Fix issues above and re-run this script.${NC}"
    exit 1
fi
