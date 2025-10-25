#!/bin/bash
# Single-command installation script for claude-agents
# Usage: curl -fsSL https://raw.githubusercontent.com/wioota/claude-agents/main/install.sh | bash

set -e

echo "🚀 Installing Claude Agents..."
echo "=============================="

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is required but not installed. Aborting."; exit 1; }
command -v pip >/dev/null 2>&1 || { echo "❌ pip is required but not installed. Aborting."; exit 1; }

# Create project directory
PROJECT_DIR="$HOME/.claude-agents"
if [ -d "$PROJECT_DIR" ]; then
    echo "⚠️  Claude Agents already installed at $PROJECT_DIR"
    echo "   To reinstall, run: rm -rf $PROJECT_DIR && $0"
    exit 1
fi

echo "📁 Creating directory: $PROJECT_DIR"
mkdir -p "$PROJECT_DIR"

# Clone or download the repository
echo "⬇️  Downloading Claude Agents..."
if command -v git >/dev/null 2>&1; then
    git clone https://github.com/wioota/claude-agents.git "$PROJECT_DIR"
else
    # Fallback to curl/wget download
    echo "⚠️  Git not found, using direct download..."
    mkdir -p "$PROJECT_DIR" && cd "$PROJECT_DIR"
    curl -L https://github.com/wioota/claude-agents/archive/main.tar.gz | tar xz --strip-components=1
fi

cd "$PROJECT_DIR"

# Setup virtual environment
echo "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -e .

# Run setup
echo "⚙️  Running initial setup..."
python3 -c "
from claude_agents.core.config import Config
from claude_agents.core.manager import AgentManager
import os

# Create default config
config = Config()
config.save()

# Initialize agent manager
manager = AgentManager(config)

print('✅ Setup complete!')
print(f'📁 Installed at: {os.getcwd()}')
print(f'⚙️  Config saved to: {config.config_file}')
" 2>/dev/null || echo "⚠️  Setup completed with warnings (some features may not be available yet)"

# Create convenience scripts
echo "🔧 Creating convenience scripts..."

# Create coding rules validator script
cat > "$HOME/bin/validate-rules" << 'EOF'
#!/bin/bash
# Validate coding rules for current project
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$HOME/.claude-agents"

if [ -f "$PROJECT_DIR/validate_coding_rules.py" ]; then
    python3 "$PROJECT_DIR/validate_coding_rules.py" "$@"
else
    echo "❌ Coding rules validator not found. Please reinstall claude-agents."
    exit 1
fi
EOF

chmod +x "$HOME/bin/validate-rules"

# Create Git pre-commit hook for coding rules validation
if [ -d ".git" ]; then
    echo "🔗 Setting up Git hooks for coding rules validation..."
    mkdir -p .git/hooks

    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook to validate coding rules

# Find Python files being committed
python_files=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' | tr '\n' ' ')

if [ -n "$python_files" ]; then
    echo "🔍 Validating coding rules for changed Python files..."

    if command -v validate-rules >/dev/null 2>&1; then
        echo "$python_files" | xargs validate-rules
        if [ $? -ne 0 ]; then
            echo "❌ Coding rules validation failed. Please fix violations before committing."
            echo "   Run: validate-rules <filename> for details"
            exit 1
        fi
    else
        echo "⚠️  Coding rules validator not found. Install claude-agents for automatic validation."
    fi
fi

exit 0
EOF

    chmod +x .git/hooks/pre-commit
    echo "✅ Git pre-commit hook installed"
fi

cat > "$HOME/bin/claude-agents" << 'EOF'
#!/bin/bash
# Convenience script to run claude-agents from anywhere
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$HOME/.claude-agents"

if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
    python3 -m claude_agents "$@"
else
    echo "❌ Claude Agents virtual environment not found. Please reinstall."
    exit 1
fi
EOF

chmod +x "$HOME/bin/claude-agents"

# Setup shell integration
SHELL_RC=""
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [ -n "$SHELL_RC" ]; then
    echo "🔗 Adding to PATH in $SHELL_RC..."
    echo 'export PATH="$HOME/bin:$PATH"' >> "$SHELL_RC"
    echo 'alias ca="claude-agents"' >> "$SHELL_RC"
fi

echo ""
echo "🎉 Installation Complete!"
echo "========================="
echo "✅ Claude Agents installed to: $PROJECT_DIR"
echo "✅ Added to PATH: claude-agents or ca"
echo ""
echo "🚀 Quick Start:"
echo "   cd your-project"
echo "   ca start    # Start background agents"
echo "   ca status   # Check agent status"
echo "   ca stop     # Stop agents"
echo ""
echo "📚 For Amp integration:"
echo "   ca amp-setup  # Setup Amp integration"
echo ""
echo "🔄 To uninstall: ca uninstall"
