# Command Reference

## Setup Commands

```bash
# Navigate to project
cd /home/wioot/dev/claude-agents

# Install with Poetry (recommended)
poetry install
poetry shell

# Or install with pip
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Validation

```bash
# Run validation script
python3 validate_prototype.py

# Expected output:
# ✓ EventBus working
# ✓ Agent started
# ✓ Agent processed event
# ✓ Agent stopped
# ✓ Priority system working
# ✅ All basic tests passed!
```

## CLI Commands

```bash
# Initialize .claude directory in a project
claude-agents init [PATH]

# Watch directory for file changes
claude-agents watch [PATH]

# Watch with verbose logging
claude-agents watch --verbose
claude-agents watch -v

# Show version
claude-agents version

# Help
claude-agents --help
```

## Testing Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=claude_agents

# Run specific test file
pytest tests/test_prototype.py
```

## Development Commands

```bash
# Format code with black
black src/ tests/

# Lint with ruff
ruff check src/ tests/

# Type check with mypy (if installed)
mypy src/
```

## Example Workflow

```bash
# Terminal 1: Start watching a test directory
cd /home/wioot/dev/claude-agents
poetry shell
mkdir test-dir
claude-agents watch test-dir --verbose

# Terminal 2: Make changes
cd /home/wioot/dev/claude-agents/test-dir
echo "hello" > test.txt
echo "world" >> test.txt
mv test.txt renamed.txt
rm renamed.txt

# Terminal 1 output:
# [INFO] agent.echo: ✓ echo: Received file:created from filesystem: test.txt
# [INFO] agent.file-logger: ✓ file-logger: Logged file:created: test.txt
# [INFO] agent.echo: ✓ echo: Received file:modified from filesystem: test.txt
# ...

# Check the log file
cat test-dir/.claude/file-changes.log
```

## Debugging

```bash
# Watch with verbose logging
claude-agents watch --verbose

# Check Python version
python3 --version

# Check if modules are importable
python3 -c "from claude_agents.core import Event; print('OK')"

# List installed packages
pip list | grep claude
```

## Git Commands (for development)

```bash
# Initialize git (if not already done)
git init

# Create .gitignore (already created)
# Add files
git add .

# Commit
git commit -m "Initial prototype implementation"

# Create a repository on GitHub and push
git remote add origin <your-repo-url>
git push -u origin main
```

## File Locations

```bash
# View project structure
tree -L 3 -I __pycache__

# View source code
ls -la src/claude_agents/

# View documentation
ls -la *.md

# View logs (after running watch)
cat .claude/file-changes.log
```

## Quick Tests

```bash
# Test event bus
python3 -c "
import asyncio
from src.claude_agents.core import Event, EventBus

async def test():
    bus = EventBus()
    queue = asyncio.Queue()
    await bus.subscribe('test', queue)
    await bus.emit(Event(type='test', payload={}))
    event = await queue.get()
    print(f'✓ Received: {event.type}')

asyncio.run(test())
"

# Test agent import
python3 -c "
from src.claude_agents.agents import EchoAgent
print('✓ EchoAgent imported successfully')
"
```

## Poetry-Specific Commands

```bash
# Install dependencies
poetry install

# Add a new dependency
poetry add <package-name>

# Add a dev dependency
poetry add --group dev <package-name>

# Update dependencies
poetry update

# Show dependencies
poetry show

# Run command in poetry environment
poetry run claude-agents --help

# Open shell in poetry environment
poetry shell

# Exit poetry shell
exit
```

## Useful Aliases (add to ~/.bashrc or ~/.zshrc)

```bash
# Add these to your shell config
alias ca='claude-agents'
alias caw='claude-agents watch'
alias cav='claude-agents watch --verbose'
```

## Troubleshooting

```bash
# If claude-agents command not found:
# 1. Make sure you're in the virtual environment
poetry shell
# or
source .venv/bin/activate

# 2. Reinstall in editable mode
pip install -e .

# If imports fail:
# Make sure you're in the project directory
cd /home/wioot/dev/claude-agents

# If watchdog not working:
# Install watchdog
pip install watchdog

# If tests fail:
# Install test dependencies
pip install pytest pytest-asyncio
```
