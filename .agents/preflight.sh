#!/bin/bash
set -e

echo "🚀 Running pre-flight checks..."

# Check if poetry is available
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry not found. Install with: curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Run Black formatter
echo "📝 Formatting code with Black..."
poetry run black src/ tests/

# Run Ruff linter with fixes
echo "🔧 Running Ruff linter with auto-fixes..."
poetry run ruff check src/ tests/ --fix

# Run unit tests
echo "🧪 Running unit tests..."
poetry run pytest tests/unit -q

echo "✅ Pre-flight checks complete!"
