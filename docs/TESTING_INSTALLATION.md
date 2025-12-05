# Testing DevLoop Installation

Comprehensive guide for testing DevLoop package installation and interactive features.

## Quick Reference

**Fast smoke test:**
```bash
(cd /tmp && python3 -m venv tdl && source tdl/bin/activate && \
 pip install -q devloop && python -c "import devloop; print(f'✓ v{devloop.__version__}')" && \
 devloop --help > /dev/null && echo "✓ CLI works" && \
 deactivate && rm -rf tdl)
```

**Full interactive test:**
```bash
(cd /tmp && python3 -m venv tdl && source tdl/bin/activate && \
 pip install -q devloop && mkdir tp && cd tp && git init -q && \
 echo -e "y\ny\ny\n" | devloop init . && echo "✓ Interactive init works!" && \
 cd .. && deactivate && rm -rf tdl tp)
```

## Testing Methods

### Method 1: Non-Interactive Mode (CI/Automated Testing)

Best for: CI pipelines, automated testing, scripted deployments

```bash
cd /tmp
python3 -m venv test-devloop
source test-devloop/bin/activate
pip install devloop

# Test import and version
python -c "import devloop; print(f'DevLoop v{devloop.__version__} installed')"

# Test CLI
devloop --help

# Test initialization
mkdir test-project && cd test-project
git init
devloop init . --non-interactive

# Verify generated files
ls -la .devloop/
cat .devloop/agents.json | head -20

# Cleanup
deactivate
rm -rf /tmp/test-devloop /tmp/test-project
```

**Expected output:**
- ✓ `.devloop/` directory created
- ✓ `agents.json` configuration file
- ✓ `CLAUDE.md` → `AGENTS.md` symlink
- ✓ All core agents enabled by default

---

### Method 2: Piped Input (Automated Interactive Testing)

Best for: Testing interactive prompts, automated acceptance testing

```bash
cd /tmp
python3 -m venv test-devloop
source test-devloop/bin/activate
pip install devloop

mkdir test-project && cd test-project
git init

# Simulate user input: Snyk=yes, CodeRabbit=no, CI=yes
echo -e "y\nn\ny\n" | devloop init .

# Verify optional agents were configured
grep -E "(snyk|code_rabbit|ci_monitor)" .devloop/agents.json

# Cleanup
deactivate
rm -rf /tmp/test-devloop /tmp/test-project
```

**Interactive prompts tested:**
1. Enable Snyk agent? (y/N)
2. Enable Code Rabbit agent? (y/N)
3. Enable CI Monitor agent? (y/N)

---

### Method 3: Using `expect` (Complex Interactive Scenarios)

Best for: Complex multi-step interactions, timeout testing, error scenarios

**Prerequisites:**
```bash
# Install expect
sudo apt-get install expect  # Debian/Ubuntu
brew install expect           # macOS
```

**Test script:**
```bash
# Create expect script
cat > /tmp/test-init.exp <<'EOF'
#!/usr/bin/expect -f
set timeout 30

spawn bash -c "cd /tmp/test-project && source /tmp/test-devloop/bin/activate && devloop init ."

expect {
    "Enable*Snyk*" {
        send "y\r"
        exp_continue
    }
    "Enable*Code Rabbit*" {
        send "n\r"
        exp_continue
    }
    "Enable*CI Monitor*" {
        send "y\r"
        exp_continue
    }
    "Initialized!" {
        puts "\n✓ Interactive init completed successfully"
    }
    timeout {
        puts "\n✗ Test timed out"
        exit 1
    }
}

expect eof
EOF

chmod +x /tmp/test-init.exp

# Setup
cd /tmp
python3 -m venv test-devloop
source test-devloop/bin/activate
pip install devloop
mkdir test-project && cd test-project
git init

# Run interactive test
/tmp/test-init.exp

# Verify results
cat .devloop/agents.json | grep -A 2 '"snyk"'

# Cleanup
deactivate
rm -rf /tmp/test-devloop /tmp/test-project /tmp/test-init.exp
```

---

### Method 4: Docker (Complete Isolation)

Best for: Cross-platform testing, clean-room verification, security testing

```bash
# Create test Dockerfile
cat > Dockerfile.test <<'EOF'
FROM python:3.11-slim

# Install git (required for devloop init)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install devloop
RUN pip install --no-cache-dir devloop

# Setup git config
RUN git config --global user.email "test@example.com" && \
    git config --global user.name "Test User"

WORKDIR /test

# Test script
CMD ["bash", "-c", "\
  git init && \
  devloop init . --non-interactive && \
  echo '✓ Files created:' && \
  ls -la .devloop/ && \
  echo '✓ Config preview:' && \
  head -20 .devloop/agents.json"]
EOF

# Build and run
docker build -f Dockerfile.test -t test-devloop .
docker run --rm test-devloop

# Cleanup
docker rmi test-devloop
rm Dockerfile.test
```

---

### Method 5: Testing Specific Version

Test a specific version before upgrading:

```bash
cd /tmp
python3 -m venv test-version
source test-version/bin/activate

# Test specific version
pip install devloop==0.3.0

# Verify version
python -c "import devloop; assert devloop.__version__ == '0.3.0', 'Version mismatch!'"

# Run full test suite
mkdir project && cd project && git init
devloop init . --non-interactive

# Cleanup
deactivate
rm -rf /tmp/test-version
```

---

## Testing Pyodide Installation (v0.3.0+)

New in v0.3.0: Automatic Pyodide installation for WASM sandbox.

```bash
cd /tmp
python3 -m venv test-pyodide
source test-pyodide/bin/activate
pip install devloop

mkdir project && cd project
git init
devloop init . --non-interactive

# Verify Pyodide files
ls -la .devloop/pyodide/ 2>/dev/null && echo "✓ Pyodide installed" || echo "✗ Pyodide not found"

# Cleanup
deactivate
rm -rf /tmp/test-pyodide
```

---

## Common Test Scenarios

### 1. Fresh Installation Test
```bash
# Simulates new user installing devloop
cd /tmp && python3 -m venv fresh && source fresh/bin/activate
pip install devloop
devloop --help
deactivate && rm -rf fresh
```

### 2. Project Initialization Test
```bash
# Simulates initializing devloop in existing project
cd /tmp && python3 -m venv init-test && source init-test/bin/activate
pip install devloop
mkdir my-project && cd my-project && git init
devloop init .
deactivate && cd /tmp && rm -rf init-test my-project
```

### 3. Upgrade Test
```bash
# Test upgrading from older version
cd /tmp && python3 -m venv upgrade && source upgrade/bin/activate
pip install devloop==0.2.2
pip install --upgrade devloop
python -c "import devloop; print(f'Upgraded to {devloop.__version__}')"
deactivate && rm -rf upgrade
```

### 4. Dependencies Test
```bash
# Verify all dependencies install correctly
cd /tmp && python3 -m venv deps && source deps/bin/activate
pip install devloop
pip list | grep -E "(pydantic|watchdog|typer|rich|aiofiles|psutil)"
deactivate && rm -rf deps
```

---

## Troubleshooting Tests

### Permission Issues
```bash
# Test in restricted environment
cd /tmp && python3 -m venv restricted && source restricted/bin/activate
pip install devloop
mkdir readonly && chmod 555 readonly
cd readonly
devloop init . 2>&1 | grep -i "permission"
cd .. && chmod 755 readonly && rm -rf readonly
deactivate && rm -rf restricted
```

### Missing Git
```bash
# Test without git installed (should fail gracefully)
cd /tmp && python3 -m venv no-git && source no-git/bin/activate
pip install devloop
mkdir project && cd project
PATH=/usr/bin devloop init . 2>&1 | grep -i git || echo "✓ Graceful failure"
deactivate && rm -rf no-git project
```

### Network Issues
```bash
# Test with --no-cache-dir (simulates slow/unreliable network)
cd /tmp && python3 -m venv network && source network/bin/activate
pip install --no-cache-dir devloop
deactivate && rm -rf network
```

---

## Continuous Integration Examples

### GitHub Actions
```yaml
name: Test Installation
on: [push, pull_request]

jobs:
  test-install:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']

    steps:
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Test installation
        run: |
          pip install devloop
          python -c "import devloop; print(f'✓ v{devloop.__version__}')"
          devloop --help

      - name: Test init
        run: |
          git config --global user.email "test@example.com"
          git config --global user.name "Test"
          mkdir test && cd test && git init
          devloop init . --non-interactive
          ls -la .devloop/
```

### GitLab CI
```yaml
test_installation:
  image: python:3.11
  script:
    - pip install devloop
    - python -c "import devloop; print(f'✓ v{devloop.__version__}')"
    - devloop --help
    - git config --global user.email "test@example.com"
    - git config --global user.name "Test"
    - mkdir test && cd test && git init
    - devloop init . --non-interactive
```

---

## Cleanup Script

Comprehensive cleanup of all test artifacts:

```bash
#!/bin/bash
# cleanup-all-tests.sh

echo "Cleaning up all test environments..."

# Remove venvs
rm -rf /tmp/test-devloop* /tmp/tdl /tmp/fresh /tmp/init-test
rm -rf /tmp/upgrade /tmp/deps /tmp/restricted /tmp/network /tmp/no-git

# Remove test projects
rm -rf /tmp/test-project* /tmp/tp /tmp/my-project /tmp/project /tmp/readonly

# Remove expect scripts
rm -f /tmp/test-init.exp

# Remove Docker artifacts
docker rmi test-devloop 2>/dev/null || true
rm -f Dockerfile.test

echo "✓ Cleanup complete"
```

---

## Best Practices

1. **Always use temporary directories** (`/tmp`) for testing
2. **Clean up after tests** to avoid disk space issues
3. **Test multiple Python versions** (3.11, 3.12+)
4. **Verify both interactive and non-interactive modes**
5. **Test upgrade paths** from previous versions
6. **Check for leaked secrets** in test environments
7. **Use virtual environments** to avoid system pollution
8. **Test in clean environments** (Docker) for reproducibility

## Security Considerations

- Never include real API keys in automated tests
- Use throwaway credentials for test environments
- Clean up sensitive data after tests
- Verify `.gitignore` is respected during init
- Test with restricted permissions to verify error handling

---

**Last Updated:** 2025-12-05
**DevLoop Version:** 0.3.0+
