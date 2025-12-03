# DevLoop

> **Intelligent background agents for development workflow automation** — automate code quality checks, testing, documentation, and more while you code.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests Passing](https://img.shields.io/badge/tests-167%20passing-green.svg)](#testing)
[![Alpha Release](https://img.shields.io/badge/status-alpha-orange.svg)](#status)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## ⚠️ ALPHA SOFTWARE - NOT FOR PRODUCTION

**DevLoop is currently in active development and is not recommended for production use.**

This is **research-quality software**. Use at your own risk. See [Known Limitations & Risks](./history/RISK_ASSESSMENT.md) for details on:

- ✗ Subprocess execution not sandboxed (security risk)
- ✗ Auto-fix may corrupt code (enable only if willing to review changes)
- ✗ Race conditions possible in file operations (concurrent agent modifications)
- ✗ Limited error recovery (daemon may not restart automatically)
- ✗ Configuration migrations not yet supported
- ✗ No process supervision (manual daemon management)

**Suitable for:** Development on side projects, testing automation, research  
**Not suitable for:** Critical code, production systems, untrusted projects

[View complete risk assessment →](./history/RISK_ASSESSMENT.md)

---

## Status

🔬 **ALPHA** — Full-featured development automation system in active development. [View detailed implementation status →](./IMPLEMENTATION_STATUS.md)

---

## Features

DevLoop runs background agents that automatically:

- **🔍 Linting & Type Checking** — Detect issues as you code (mypy, custom linters)
- **📝 Code Formatting** — Auto-format files with Black, isort, and more
- **✅ Testing** — Run relevant tests on file changes
- **🔐 Security Scanning** — Find vulnerabilities with Bandit
- **📚 Documentation** — Keep docs in sync with code changes
- **⚡ Performance** — Track performance metrics and detect regressions
- **🎯 Git Integration** — Generate smart commit messages
- **🤖 Custom Agents** — Create no-code agents via builder pattern
- **📊 Learning System** — Automatically learn patterns and optimize behavior
- **🔄 Auto-fix** — Safely apply fixes (configurable safety levels)

All agents run **non-intrusively in the background**, respecting your workflow.

---

## Quick Start

### ⚠️ Before You Start

**ALPHA SOFTWARE DISCLAIMER:**
- This is research-quality code. Data loss is possible.
- Only use on projects you can afford to lose or easily recover.
- Make sure to commit your code to git before enabling DevLoop.
- Do not enable auto-fix on important code.
- Some agents may fail silently (see logs for details).

### Installation

**Prerequisites:** Python 3.11+

#### Option 1: From PyPI (Recommended)

```bash
# Basic installation (all default agents)
pip install devloop

# With optional agents (Snyk security scanning)
pip install devloop[snyk]

# With multiple optional agents
pip install devloop[snyk,code-rabbit]

# With all optional agents
pip install devloop[all-optional]
```

**Available extras:**
- `snyk` — Dependency vulnerability scanning via Snyk CLI
- `code-rabbit` — AI-powered code analysis
- `ci-monitor` — CI/CD pipeline monitoring
- `all-optional` — All of the above

#### Option 2: From Source

```bash
# Clone the repository
git clone https://github.com/wioota/devloop
cd devloop

# Install poetry (if needed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Initialize & Run (Fully Automated)

```bash
# 1. Initialize in your project (interactive setup)
devloop init /path/to/your/project
```

The `init` command will:
- ✅ Set up .devloop directory with default agents
- ✅ Ask which optional agents you want to enable:
  - **Snyk** — Scan dependencies for vulnerabilities
  - **Code Rabbit** — AI-powered code analysis
  - **CI Monitor** — Track CI/CD pipeline status
- ✅ Create configuration file with your selections
- ✅ Set up git hooks (if git repo)
- ✅ Registers Amp integration (if in Amp)

```bash
# 1a. Alternative: Non-interactive setup (skip optional agent prompts)
devloop init /path/to/your/project --non-interactive
```

Then just:
```bash
# 2. Start watching for changes
cd /path/to/your/project
devloop watch .

# 3. Make code changes and watch agents respond
```

**That's it!** No manual configuration needed. DevLoop will automatically monitor your project, run agents on file changes, and enforce commit discipline.

[View the installation automation details →](./INSTALLATION_AUTOMATION.md)

### Common Commands

```bash
# Watch a directory for changes
devloop watch .

# Show agent status and health
devloop status

# View current findings in Amp
/agent-summary          # Recent findings
/agent-summary today    # Today's findings
/agent-summary --agent linter --severity error

# Create a custom agent
devloop custom-create my_agent pattern_matcher
```

[View all CLI commands →](./docs/cli-commands.md)

---

## Architecture

```
File Changes → Collectors → Event Bus → Agents → Results
  (Filesystem)   (Git, Etc)    (Pub/Sub)   (8 built-in + custom)
                                   ↓
                            Context Store
                          (shared state)
                                   ↓
                            Findings & Metrics
```

### Core Components

| Component | Purpose |
|-----------|---------|
| **Event Bus** | Pub/sub system for agent coordination |
| **Collectors** | Monitor filesystem, git, process, system events |
| **Agents** | Process events and produce findings |
| **Context Store** | Shared development context |
| **CLI** | Command-line interface and Amp integration |
| **Config** | JSON-based configuration system |

[Read the full architecture guide →](./docs/architecture.md)

---

## Agents

DevLoop includes **11 built-in agents** out of the box:

### Code Quality
- **Linter Agent** — Runs linters on changed files
- **Formatter Agent** — Auto-formats code (Black, isort, etc.)
- **Type Checker Agent** — Background type checking (mypy)
- **Code Rabbit Agent** — AI-powered code analysis and insights

### Testing & Security
- **Test Runner Agent** — Runs relevant tests on changes
- **Security Scanner Agent** — Detects code vulnerabilities (Bandit)
- **Snyk Agent** — Scans dependencies for known vulnerabilities
- **Performance Profiler Agent** — Tracks performance metrics

### Development Workflow
- **Git Commit Assistant** — Suggests commit messages
- **CI Monitor Agent** — Tracks GitHub Actions status
- **Doc Lifecycle Agent** — Manages documentation organization

### Custom Agents
Create your own agents without writing code:

```python
from devloop.core.custom_agent import AgentBuilder, CustomAgentType

# Create a custom pattern matcher
config = (
    AgentBuilder("todo_finder", CustomAgentType.PATTERN_MATCHER)
    .with_description("Find TODO comments")
    .with_triggers("file:created", "file:modified")
    .with_config(patterns=[r"#\s*TODO:.*"])
    .build()
)
```

[View agent documentation →](./docs/agents.md)

### Code Rabbit Integration

Code Rabbit Agent provides AI-powered code analysis with insights on code quality, style, and best practices.

**Setup:**

```bash
# 1. Install code-rabbit CLI
npm install -g @code-rabbit/cli
# or
pip install code-rabbit

# 2. Set your API key
export CODE_RABBIT_API_KEY="your-api-key-here"

# 3. Agent runs automatically on file changes
# Results appear in agent findings and context store
```

**Configuration:**

```json
{
  "code-rabbit": {
    "enabled": true,
    "triggers": ["file:modified", "file:created"],
    "config": {
      "apiKey": "${CODE_RABBIT_API_KEY}",
      "minSeverity": "warning",
      "filePatterns": ["**/*.py", "**/*.js", "**/*.ts"]
    }
  }
}
```

**Features:**
- Real-time code analysis as you type
- AI-generated insights on code improvements
- Integration with DevLoop context store
- Configurable severity filtering
- Automatic debouncing to avoid excessive runs

### Snyk Integration

Snyk Agent provides security vulnerability scanning for project dependencies across multiple package managers.

**Setup:**

```bash
# 1. Install snyk CLI
npm install -g snyk
# or
brew install snyk

# 2. Authenticate with Snyk (creates ~/.snyk token)
snyk auth

# 3. Set your API token for DevLoop
export SNYK_TOKEN="your-snyk-token"

# 4. Agent runs automatically on dependency file changes
# Results appear in agent findings and context store
```

**Configuration:**

```json
{
  "snyk": {
    "enabled": true,
    "triggers": ["file:modified", "file:created"],
    "config": {
      "apiToken": "${SNYK_TOKEN}",
      "severity": "high",
      "filePatterns": [
        "**/package.json",
        "**/requirements.txt",
        "**/Gemfile",
        "**/pom.xml",
        "**/go.mod",
        "**/Cargo.toml"
      ]
    }
  }
}
```

**Features:**
- Scans all major package managers (npm, pip, Ruby, Maven, Go, Rust)
- Detects known security vulnerabilities in dependencies
- Shows CVSS scores and fix availability
- Integration with DevLoop context store
- Configurable severity filtering (critical/high/medium/low)
- Automatic debouncing to avoid excessive scans

**Supported Package Managers:**
- **npm** / **yarn** / **pnpm** (JavaScript/Node.js)
- **pip** / **pipenv** / **poetry** (Python)
- **bundler** (Ruby)
- **maven** / **gradle** (Java)
- **go mod** (Go)
- **cargo** (Rust)

---

## Configuration

Configure agent behavior in `.devloop/agents.json`:

```json
{
  "global": {
    "autonomousFixes": {
      "enabled": false,
      "safetyLevel": "safe_only"
    },
    "maxConcurrentAgents": 5,
    "resourceLimits": {
      "maxCpu": 25,
      "maxMemory": "500MB"
    }
  },
  "agents": {
    "linter": {
      "enabled": true,
      "triggers": ["file:save", "git:pre-commit"],
      "config": {
        "debounce": 500,
        "filePatterns": ["**/*.py"]
      }
    }
  }
}
```

**Safety levels (Auto-fix):**
- `safe_only` — Only fix whitespace/indentation (default, recommended)
- `medium_risk` — Include import/formatting fixes
- `all` — Apply all fixes (use with caution)

⚠️ **Auto-fix Warning:** Currently auto-fixes run without backups or review. **DO NOT enable auto-fix in production** or on critical code. Track [secure auto-fix with backups issue](https://github.com/wioota/devloop/issues/emc).

[Full configuration reference →](./docs/configuration.md)

---

## CI/CD Integration

DevLoop includes GitHub Actions integration with automated security scanning.

### GitHub Actions Workflow

The default CI pipeline includes:

1. **Tests** — Run pytest on Python 3.11 & 3.12
2. **Lint** — Check code formatting (Black) and style (Ruff)
3. **Type Check** — Verify type safety with mypy
4. **Security (Bandit)** — Scan code for security issues
5. **Security (Snyk)** — Scan dependencies for vulnerabilities

### Setting Up Snyk in CI

To enable Snyk scanning in your CI pipeline:

**1. Get a Snyk API Token:**
```bash
# Create account at https://snyk.io
# Get token from https://app.snyk.io/account/
```

**2. Add token to GitHub secrets:**
```bash
# In your GitHub repository:
# Settings → Secrets and variables → Actions
# Add new secret: SNYK_TOKEN = your-token
```

**3. Snyk job runs automatically:**
- Scans all dependencies for known vulnerabilities
- Fails build if high/critical vulnerabilities found
- Uploads report as artifact for review
- Works with all supported package managers

**Configuration:**
- **Severity threshold:** high (fails on critical or high)
- **Supported managers:** npm, pip, Ruby, Maven, Go, Rust
- **Report:** `snyk-report.json` available as artifact

---

## Usage Examples

### Example 1: Auto-Format on Save

```bash
# Agent automatically runs Black, isort when you save a file
echo "x=1" > app.py  # Auto-formatted to x = 1

# View findings
/agent-summary recent
```

### Example 2: Run Tests on Changes

```bash
# Test runner agent detects changed test files
# Automatically runs: pytest path/to/changed_test.py

# Or view all test results
/agent-summary --agent test-runner
```

### Example 3: Create Custom Pattern Matcher

```bash
# Create agent to find TODO comments
devloop custom-create find_todos pattern_matcher \
  --description "Find TODO comments" \
  --triggers file:created,file:modified

# List your custom agents
devloop custom-list
```

### Example 4: Learn & Optimize

```bash
# View learned patterns
devloop learning-insights --agent linter

# Get recommendations
devloop learning-recommendations linter

# Check performance data
devloop perf-summary --agent formatter
```

[More examples →](./examples/)

---

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage report
poetry run pytest --cov=devloop

# Run specific test file
poetry run pytest tests/unit/agents/test_linter.py -v

# Run tests with output
poetry run pytest -v
```

**Current status:** ✅ 112+ tests passing

[View test strategy →](./docs/testing.md)

---

## Development

### Project Structure

```
devloop/
├── src/devloop/
│   ├── core/              # Event system, agents, context
│   ├── collectors/        # Event collectors
│   ├── agents/            # Built-in agents
│   └── cli/               # CLI interface
├── tests/                 # Unit and integration tests
├── docs/                  # Documentation
├── examples/              # Usage examples
└── pyproject.toml         # Poetry configuration
```

### Adding a New Agent

1. Create `src/devloop/agents/my_agent.py`:

```python
from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event

class MyAgent(Agent):
    async def handle(self, event: Event) -> AgentResult:
        # Your logic here
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0.1,
            message="Processed successfully"
        )
```

2. Register in `src/devloop/cli/main.py`

3. Add tests in `tests/unit/agents/test_my_agent.py`

[Developer guide →](./docs/development.md)

### Code Style

- **Formatter:** Black
- **Linter:** Ruff
- **Type Checker:** mypy
- **Python Version:** 3.11+

Run formatters:
```bash
poetry run black src tests
poetry run ruff check --fix src tests
poetry run mypy src
```

---

## Documentation

- **[Getting Started Guide](./docs/getting-started.md)** — Installation and basic usage
- **[Architecture Guide](./docs/architecture.md)** — System design and components
- **[Agent Reference](./docs/agents.md)** — All available agents
- **[Configuration Guide](./docs/configuration.md)** — Full config reference
- **[CLI Commands](./docs/cli-commands.md)** — Command reference
- **[Development Guide](./docs/development.md)** — Contributing guide
- **[Implementation Status](./IMPLEMENTATION_STATUS.md)** — What's implemented
- **[Learning & Optimization](./PHASE3_COMPLETE.md)** — Advanced features

---

## Design Principles

DevLoop follows these core principles:

✅ **Non-Intrusive** — Runs in background without blocking workflow  
✅ **Event-Driven** — All actions triggered by observable events  
✅ **Configurable** — Fine-grained control over agent behavior  
✅ **Context-Aware** — Understands your project structure  
✅ **Parallel** — Multiple agents run concurrently  
✅ **Lightweight** — Respects system resources  

[Read the full design spec →](./AGENTS.md)

---

## Troubleshooting

### ⚠️ If Something Goes Wrong

**Recovery steps:**
1. Stop the daemon: `devloop stop .`
2. Check the logs: `tail -100 .devloop/devloop.log`
3. Verify your code in git: `git status`
4. Recover from git if files were modified: `git checkout <file>`
5. Report the issue: [GitHub Issues](https://github.com/wioota/devloop/issues)

### Agents not running

```bash
# Check status
devloop status

# View logs (useful for debugging)
tail -f .devloop/devloop.log

# Enable verbose mode for more details
devloop watch . --foreground --verbose
```

### Performance issues

Check `.devloop/agents.json`:

```json
{
  "global": {
    "maxConcurrentAgents": 2,
    "resourceLimits": {
      "maxCpu": 10,
      "maxMemory": "200MB"
    }
  }
}
```

### Custom agents not found

```bash
# Verify they exist
devloop custom-list

# Check storage
ls -la .devloop/custom_agents/
```

### Agent modified my files unexpectedly

1. Check git diff: `git diff`
2. Revert changes: `git checkout -- .`
3. Disable the problematic agent in `.devloop/agents.json`
4. Report issue with: `git show HEAD:.devloop/agents.json`

[Full troubleshooting guide →](./docs/troubleshooting.md)

---

## Performance

- **Memory:** ~50MB base + ~10MB per agent
- **CPU:** <5% idle, 10-25% when processing
- **Startup:** <1 second
- **Event latency:** <100ms typical

All operations are async and non-blocking.

---

## Roadmap

### Completed ✅
- Core agents: linting, formatting, testing, type checking
- Security & performance: vulnerability scanning, profiling
- Workflow automation: git integration, CI monitoring, documentation
- Custom agents: create your own without writing code
- Learning system: pattern recognition and optimization

### In Development 🚀
- Cloud pattern repository (opt-in)
- Agent composition and pipelines
- Community agent sharing

### Future 🔮
- Multi-project support
- Team coordination features
- LLM-powered agents

---

## Amp Integration

Using DevLoop in Amp? See [AMP_ONBOARDING.md](./AMP_ONBOARDING.md) for:

- Installation and registration checklist
- Required configuration
- Post-task verification workflow
- Troubleshooting guide

The commit/push discipline is automatically enforced via `.agents/verify-task-complete`.

---

## Contributing

Contributions welcome! Please read [CODING_RULES.md](./CODING_RULES.md) for:

- Code style guidelines
- Testing requirements
- Commit message format
- Pull request process

### Development Setup

```bash
git clone https://github.com/wioota/devloop
cd devloop
poetry install
poetry run pytest
```

### Running Tests

```bash
# All tests
poetry run pytest

# Specific test file
poetry run pytest tests/unit/agents/test_linter.py

# With coverage
poetry run pytest --cov=devloop
```

---

## License

DevLoop is released under the [MIT License](LICENSE).

This means you can freely use, modify, and distribute this software for any purpose, including commercial use, as long as you include the original copyright notice and license text.

---

## Support

- 📚 **Documentation:** [./docs/](./docs/)
- 🐛 **Issues:** [GitHub Issues](https://github.com/wioota/devloop/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/wioota/devloop/discussions)
- 🤝 **Contributing:** [CONTRIBUTING.md](./CODING_RULES.md)

---

## Acknowledgments

Built with:
- [Watchdog](https://github.com/gorakhargosh/watchdog) — File system monitoring
- [Typer](https://typer.tiangolo.com/) — CLI framework
- [Pydantic](https://docs.pydantic.dev/) — Data validation
- [Rich](https://rich.readthedocs.io/) — Terminal output

---

**Made with ❤️ by the DevLoop team**

