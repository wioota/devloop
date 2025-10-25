# Quick Start Guide (Without Poetry)

If you don't have Poetry installed, you can still test the prototype with pip.

## Option 1: Using pip in a virtual environment

```bash
cd /home/wioot/dev/claude-agents

# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies
pip install pydantic watchdog typer rich pytest pytest-asyncio

# Install in development mode
pip install -e .

# Run the CLI
claude-agents --help
```

## Option 2: Install Poetry (Recommended)

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add to PATH (add this to your ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"

# Install dependencies
cd /home/wioot/dev/claude-agents
poetry install

# Run with poetry
poetry run claude-agents --help

# Or activate the shell
poetry shell
claude-agents --help
```

## Testing the Prototype

### 1. Create a test directory

```bash
mkdir ~/test-claude-agents
cd ~/test-claude-agents
```

### 2. Initialize

```bash
claude-agents init .
```

### 3. Start watching

```bash
claude-agents watch . --verbose
```

### 4. In another terminal, make changes

```bash
cd ~/test-claude-agents
echo "hello" > test.txt
echo "world" >> test.txt
mv test.txt renamed.txt
rm renamed.txt
```

### 5. Check the logs

```bash
cat .claude/file-changes.log
```

## Running Tests

```bash
# With poetry
poetry run pytest -v

# Without poetry (if installed with pip)
pytest -v
```

## Next Steps

Once the prototype is validated:
1. Review the architecture
2. Decide what to build next
3. Add more sophisticated agents
4. Build the configuration system
5. Add git hook integration
