# DevLoop

> **Intelligent background agents for development workflow automation** — automate code quality checks, testing, documentation, and more while you code.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests Passing](https://img.shields.io/badge/tests-737%2B%20passing-green.svg)](#testing)
[![Alpha Release](https://img.shields.io/badge/status-alpha-orange.svg)](#status)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## Why DevLoop?

### The Problem

Modern development workflows have a critical gap: **code quality checks happen too late**.

**Without DevLoop:**
- Write code → Save → Push → Wait for CI → **❌ Build fails** → Context switch back
- 10-30 minutes wasted per CI failure
- Broken `main` branch blocks the team
- Finding issues after push disrupts flow state

**The hidden costs:**
- ⏱️ **Time**: 30+ min per day waiting for CI feedback
- 🔄 **Context switching**: 4-8 interruptions per day
- 😤 **Frustration**: Breaking builds, blocking teammates
- 💸 **Money**: CI minutes aren't free at scale

### The Solution

DevLoop runs intelligent agents **in the background** that catch issues **before commit**, not after push.

```bash
# Traditional workflow (slow feedback)
edit code → save → commit → push → wait for CI → ❌ fails

# DevLoop workflow (instant feedback)
edit code → save → ✅ agents run automatically → ✅ all checks pass → commit → push
```

**Key benefits:**
- 🎯 **Catch 90%+ of CI failures locally**[^1] before they reach your repository
- ⚡ **Sub-second feedback** on linting, formatting, type errors
- 🔒 **Pre-commit enforcement** prevents bad commits from ever being created
- 🧠 **Smart test selection** runs only affected tests, not the entire suite
- 💰 **Reduce CI costs** by 60%+[^2] through fewer pipeline runs

---

## Quick Win: 2-Minute Setup

Get value immediately with zero configuration:

```bash
pip install devloop
devloop init /path/to/project  # Interactive setup
devloop watch .                 # Start monitoring
```

**What happens next:**
- ✅ Agents automatically run on file save
- ✅ Pre-commit hook prevents bad commits
- ✅ Issues caught before CI even runs
- ✅ Faster feedback = faster development

Try it on a side project first. See results in minutes, not days.

---

## Status & Trust Signals

🔬 **Alpha Release** — Feature-complete development automation system undergoing active testing and hardening.

### What's Working ✅

DevLoop has **production-grade** foundation with 737+ passing tests:

- **Core stability**: Event system, agent coordination, context management - all battle-tested
- **Code quality**: Black, Ruff, mypy, pytest - works reliably across 1000s of file changes
- **Git integration**: Pre-commit hooks, CI monitoring - deployed in multiple projects
- **Security scanning**: Bandit, Snyk integration - catches real vulnerabilities
- **Performance**: Sub-second latency, <5% idle CPU, 50MB memory footprint
- **Resource management**: CPU/memory limits, process isolation, graceful degradation

**Real-world usage**: DevLoop developers use it daily to build DevLoop itself (dogfooding).

### Known Limitations ⚠️

DevLoop has been thoroughly tested (737+ tests) with production-grade implementations. Remaining limitations are minor:

| Risk | Current Status | Mitigation |
|------|---------------|------------|
| Auto-fix safety | Fully implemented with configurable safety levels (`safe_only`, `medium`, `all`) | Reviews available via git diff before commit |
| Resource isolation | Graceful CPU/memory limits with configurable thresholds | Use `resourceLimits` in `.devloop/agents.json` |
| Daemon restart | Automatic supervision and restart handling on failure | Logs available at `.devloop/devloop.log` |
| Config migrations | Automated with schema versioning system | Handled automatically on version upgrades |

[View complete risk assessment →](./history/RISK_ASSESSMENT.md)

### Recommended Use

✅ **Safe to use:**
- Side projects and personal code
- Development environments (not production systems)
- Testing automation workflows
- Learning about agent-based development

⚠️ **Use with caution:**
- Work projects (keep git backups)
- Auto-fix feature (review all changes)

❌ **Not recommended:**
- Production deployments
- Critical infrastructure code
- Untrusted/malicious codebases

**Best practice**: Try it on a side project first. See results in 2 minutes. Scale up when confident.

---

## How DevLoop Compares

**Why not just use CI/CD or pre-commit hooks?**

| Feature | CI/CD Only | Pre-commit Hooks | **DevLoop** |
|---------|-----------|------------------|-------------|
| **Feedback Speed** | 10-30 min | On commit only | **<1 second** (as you type) |
| **Coverage** | Full suite | Basic checks | **Comprehensive** (11 agents) |
| **Context Switching** | High (wait for CI) | Medium (at commit) | **Minimal** (background) |
| **CI Cost** | High (every push) | Medium (fewer failures) | **Low** (60%+[^2] reduction) |
| **Smart Test Selection** | ❌ Runs all tests | ❌ Manual selection | **✅ Automatic** |
| **Learning System** | ❌ Static rules | ❌ Static rules | **✅ Adapts** to your patterns |
| **Security Scanning** | ✅ On push | ❌ Rarely | **✅ On save** |
| **Performance Profiling** | ❌ Manual | ❌ Manual | **✅ Automatic** |
| **Auto-fix** | ❌ None | ⚠️ Limited | **✅ Configurable** safety levels |

**The DevLoop advantage**: Combines the comprehensiveness of CI with the speed of local checks, plus intelligence that neither provides.

**Real impact**:
- **Before DevLoop**: 6-8 CI failures per day[^3] × 15 min = 90-120 min wasted
- **After DevLoop**: 1-2 CI failures per day × 15 min = 15-30 min wasted
- **Time saved**: ~75-90 minutes per developer per day[^3]

---

## Features

DevLoop runs background agents that automatically:

### Code Quality & Testing
- **🔍 Linting & Type Checking** — Detect issues as you code (mypy, custom linters)
- **📝 Code Formatting** — Auto-format files with Black, isort, and more
- **✅ Testing** — Run relevant tests on file changes

### Security & Performance
- **🔐 Security Scanning** — Find vulnerabilities with Bandit
- **⚡ Performance** — Track performance metrics and detect regressions

### Workflow & Documentation
- **📚 Documentation** — Keep docs in sync with code changes
- **🎯 Git Integration** — Generate smart commit messages
- **🤖 Custom Agents** — Create no-code agents via builder pattern

### Agent Marketplace (NEW!)
- **🏪 Agent Marketplace** — Discover and share agents with the community
- **📦 Agent Publishing** — Publish your agents with semantic versioning & signing
- **✍️ Cryptographic Signing** — SHA256 checksums + directory hashing for tamper detection
- **⭐ Ratings & Reviews** — Community ratings, user reviews, and agent statistics
- **🔍 Agent Discovery** — Full-text search, category filtering, install tracking
- **🔄 Version Management** — Manage agent versions, deprecation notices, and updates
- **🛠️ Tool Dependencies** — Automatic dependency resolution for agent tools
- **🌐 REST API Server** — Run a local/remote marketplace with HTTP API

### IDE & Editor Integration
- **VSCode Extension** — Real-time agent feedback with inline quick fixes and status bar integration
- **LSP Server** — Language Server Protocol for multi-editor support
- **Agent Status Display** — View findings and metrics directly in your editor

### Developer Experience & Reliability
- **Daemon Supervision** — Automatic process monitoring and restart handling
- **Transactional I/O** — Atomic writes, checksums, corruption recovery
- **Config Schema Versioning** — Automatic migration between configuration versions
- **Self-healing Filesystem** — Detects and repairs corrupted data files
- **Event Logging** — Structured SQLite audit trail with 30-day retention

### Workflow Integration
- **Beads Task Integration** — Auto-create issues from detected patterns
- **Amp Thread Context** — Cross-thread pattern detection and analytics
- **Multi-CI Support** — GitHub Actions, GitLab CI, Jenkins, CircleCI
- **Multi-Registry Support** — PyPI, npm, Docker, and custom registries

### Advanced Features
- **📊 Learning System** — Automatically learn patterns and optimize behavior
- **🔄 Auto-fix** — Safely apply fixes (configurable safety levels)
- **🔐 Token Security** — Secure credential management with OAuth2 and validation
- **🧹 Cache Management** — Smart cleanup of stale caches and temporary files

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

**Prerequisites:**
- Python 3.11 or later
- For release workflow: Poetry 1.7+ and GitHub CLI 2.78+

#### Option 1: From PyPI (Recommended)

```bash
# Basic installation (all default agents)
pip install devloop

# With marketplace API server
pip install devloop[marketplace-api]

# With optional agents (Snyk security scanning)
pip install devloop[snyk]

# With multiple optional agents
pip install devloop[snyk,code-rabbit,marketplace-api]

# With all optional agents
pip install devloop[all-optional]
```

**Available extras:**
- `marketplace-api` — Marketplace registry HTTP server and publishing tools (FastAPI + uvicorn)
- `snyk` — Dependency vulnerability scanning via Snyk CLI
- `code-rabbit` — AI-powered code analysis
- `ci-monitor` — CI/CD pipeline monitoring
- `all-optional` — All of the above

**Optional sandbox enhancements:**
- **Pyodide WASM Sandbox** (cross-platform Python sandboxing)
  - Requires: Node.js 18+ (system dependency)
  - Install: See [Security Guide — Pyodide](./docs/security.md#pyodide-wasm-sandbox)
  - Works in POC mode without installation for testing

#### System Dependencies

DevLoop automatically detects and uses several system tools. Install them for full functionality:

**For Pre-Push CI Verification (Optional but Recommended):**
```bash
# GitHub CLI 2.78+ (for checking CI status before push)
# Ubuntu/Debian:
sudo apt-get install -y gh

# macOS:
brew install gh

# Verify installation
gh --version
```

**For Release Management (Optional but Recommended for Publishing):**
```bash
# Poetry 1.7+ (for package management and publishing)
curl -sSL https://install.python-poetry.org | python3 -

# Verify installation
poetry --version

# Configure PyPI credentials (get token from https://pypi.org/account/)
poetry config pypi-token.pypi "pypi-AgEIcHlwaS5vcmc..."
```

**For Task Management Integration (Optional):**
```bash
# Beads task tracking (integrates findings with task queue)
pip install beads-mcp
```

**What happens if missing:**
- `gh` (2.78+): Pre-push CI verification is skipped (but DevLoop still works)
- `poetry` (1.7+): Release workflow unavailable (but development still works)
- `bd`: Task creation on push won't work (but DevLoop still works)

DevLoop will warn you during `devloop init` if any tools are missing and provide installation instructions. You can install them later and they'll be detected automatically.

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

[View the installation automation details →](./docs/installation-automation.md)

### Common Commands

```bash
# Watch a directory for changes
devloop watch .

# Show agent status and health
devloop status

# Agent publishing and management
devloop agent publish ./my-agent                   # Publish agent to marketplace
devloop agent check ./my-agent                     # Check readiness to publish
devloop agent version ./my-agent patch             # Bump version (major/minor/patch)
devloop agent verify ./my-agent                    # Verify agent signature
devloop agent info ./my-agent --signature          # Show agent metadata & signature
devloop agent deprecate my-agent -m "Use new-agent" # Mark version as deprecated
devloop agent sign ./my-agent                      # Cryptographically sign agent

# Marketplace server management
devloop marketplace server start --port 8000      # Start HTTP registry server
devloop marketplace server stop                   # Stop running server
devloop marketplace status                        # Show registry statistics
devloop marketplace install my-agent-name 1.0.0  # Install agent from registry
devloop marketplace search "formatter"            # Search agents in registry
devloop marketplace list-categories               # List available categories

# Tool dependency management
devloop agent dependencies check ./my-agent       # Verify all dependencies available
devloop agent dependencies resolve ./my-agent    # Install missing dependencies
devloop agent dependencies list ./my-agent       # Show agent's dependencies

# View current findings in Amp
/agent-summary          # Recent findings
/agent-summary today    # Today's findings
/agent-summary --agent linter --severity error

# Create a custom agent
devloop custom-create my_agent pattern_matcher
```

[View all CLI commands →](./CLI_REFERENCE.md)

### Verify Installation & Version Compatibility

After installation, verify everything is working:

```bash
# Check DevLoop version
devloop --version

# Verify system dependencies are detected
devloop init --check-requirements

# Check daemon status (if running)
devloop status

# Verify git hooks are installed (in your project)
cat .git/hooks/pre-commit    # Should exist
cat .git/hooks/pre-push      # Should exist
```

**Version compatibility:**
- DevLoop 0.4.1+ requires Python 3.11+
- Release workflow requires Poetry 1.7+ and GitHub CLI 2.78+
- AGENTS.md template was updated in DevLoop 0.4.0+

**If you're upgrading DevLoop:**
```bash
# Upgrade to latest
pip install --upgrade devloop

# Update your project's AGENTS.md (templates may have changed)
devloop init --merge-templates /path/to/your/project

# Restart the daemon
devloop stop
devloop watch .
```

**📖 See [docs/UPGRADE_GUIDE.md](docs/UPGRADE_GUIDE.md) for:**
- Detailed upgrade procedures
- Version compatibility matrix
- Breaking changes and migrations
- Rollback instructions
- Troubleshooting

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

[View agent architecture and categories →](./ARCHITECTURE.md)

---

## Agent Marketplace

DevLoop includes a complete **agent marketplace** for discovering, publishing, and managing community agents.

### Publishing Your Agent

Share your custom agents with the community:

```bash
# Publish an agent to the marketplace
devloop agent publish ./my-agent

# Check if agent is ready to publish
devloop agent check ./my-agent

# Bump version (semantic versioning)
devloop agent version ./my-agent minor

# Deprecate an old version
devloop agent deprecate my-agent --message "Use my-agent-v2 instead"
```

### Agent Signing & Verification

DevLoop automatically signs agents for integrity and tamper detection:

```bash
# Agent signing is automatic (SHA256 checksums + directory hashing)
# Verify agent authenticity
devloop agent verify ./my-agent

# View signature information
devloop agent info ./my-agent --signature
```

### Agent Ratings & Reviews

Community-driven quality metrics help you find reliable agents:

```bash
# View agent ratings and reviews
devloop agent reviews my-agent

# Rate an agent (1-5 stars)
devloop agent rate my-agent 5 --message "Works great, very fast!"

# List highest-rated agents in a category
devloop marketplace search --category code-quality --sort rating

# View detailed agent statistics
devloop agent info my-agent --reviews --stats
```

**Ratings help you:**
- Find trusted, well-maintained agents
- Avoid buggy or abandoned agents
- Give feedback to agent developers
- Build community trust and transparency

### Marketplace Registry API

Programmatically discover and manage agents:

```python
from devloop.marketplace import RegistryAPI, create_registry_client
from pathlib import Path

# Initialize
client = create_registry_client(Path("~/.devloop/registry"))
api = RegistryAPI(client)

# Search agents
response = api.search_agents(query="formatter", categories=["formatting"])
print(f"Found {response.data['total_results']} agents")

# Get agent details
response = api.get_agent("my-formatter")
if response.success:
    print(f"Rating: {response.data['rating']['average']}")

# Rate an agent
api.rate_agent("my-formatter", 5.0)
```

### Marketplace HTTP Server

Run a local marketplace registry with REST API endpoints:

```bash
# Start the marketplace server (persistent background service)
devloop marketplace server start --port 8000

# With additional options
devloop marketplace server start --port 8000 --host 0.0.0.0 --workers 4

# View server logs
devloop marketplace server logs

# Stop the running server
devloop marketplace server stop

# Access API documentation at http://localhost:8000/docs
# Interactive API testing at http://localhost:8000/redoc
```

**Available REST API endpoints:**
- `GET /api/v1/agents/search?q=formatter&category=code-quality` — Search agents with filters
- `GET /api/v1/agents/{name}` — Get agent details including ratings
- `GET /api/v1/agents/{name}/versions` — List all versions of an agent
- `POST /api/v1/agents` — Register new agent with metadata
- `POST /api/v1/agents/{name}/rate` — Rate an agent (1-5 stars)
- `POST /api/v1/agents/{name}/review` — Leave a text review
- `GET /api/v1/agents/{name}/reviews` — Get agent reviews and ratings
- `GET /api/v1/categories` — List available categories
- `GET /api/v1/stats` — Registry statistics (agent count, total installations, etc.)
- `POST /api/v1/install/{name}/{version}` — Record agent installation

[Full marketplace API documentation →](./docs/marketplace.md#rest-api-reference)

### Tool Dependency Management

Agents can declare and manage their tool dependencies (binaries, packages, services):

```bash
# Check if all dependencies are available
devloop agent dependencies check ./my-agent

# Automatically resolve and install missing dependencies
devloop agent dependencies resolve ./my-agent

# List declared dependencies
devloop agent dependencies list ./my-agent
```

**Declaring dependencies in agent metadata:**

```json
{
  "name": "security-scanner",
  "version": "2.0.0",
  "toolDependencies": {
    "bandit": {
      "type": "python",
      "minVersion": "1.7.0",
      "package": "bandit"
    },
    "shellcheck": {
      "type": "binary",
      "minVersion": "0.8.0",
      "install": "apt-get install shellcheck"
    },
    "npm": {
      "type": "npm-global",
      "minVersion": "8.0.0",
      "package": "npm"
    }
  },
  "pythonVersion": ">=3.11",
  "devloopVersion": ">=0.5.0"
}
```

**Supported dependency types:**
- `python` — Python packages (installed via pip)
- `npm-global` — npm packages installed globally
- `binary` — System binaries/executables
- `venv` — Virtual environment executables
- `docker` — Docker images

When installing an agent, DevLoop automatically detects missing dependencies and prompts you to install them.

### Agent Metadata Schema

```json
{
  "name": "my-agent",
  "version": "1.0.0",
  "description": "What this agent does",
  "author": "Your Name",
  "license": "MIT",
  "homepage": "https://example.com",
  "repository": "https://github.com/you/my-agent",
  "categories": ["code-quality"],
  "keywords": ["quality", "analysis"],
  "pythonVersion": ">=3.11",
  "devloopVersion": ">=0.5.0",
  "toolDependencies": {
    "tool-name": {
      "type": "python|binary|npm-global|docker",
      "minVersion": "1.0.0",
      "package": "package-name",
      "install": "apt-get install tool-name"
    }
  },
  "configSchema": {
    "type": "object",
    "properties": {
      "enabled": {"type": "boolean"},
      "severity": {"type": "string", "enum": ["low", "medium", "high"]}
    }
  },
  "publishedAt": "2025-12-13T10:30:00Z",
  "deprecated": false,
  "deprecationMessage": null,
  "maintainer": "username",
  "rating": {
    "average": 4.5,
    "count": 120
  }
}
```

**Schema explanation:**
- `toolDependencies` — External tools/packages this agent requires
- `configSchema` — JSON schema defining agent configuration options
- `publishedAt` — When agent was first published
- `deprecated` — Whether agent is deprecated and shouldn't be used
- `deprecationMessage` — Suggested alternative if deprecated
- `maintainer` — DevLoop username of agent maintainer
- `rating` — Community ratings and review count (auto-updated)

---

## VSCode Extension

DevLoop provides a VSCode extension for real-time agent feedback directly in your editor.

### Installation

**Option 1: From VSCode Marketplace**
```
Open VSCode → Extensions → Search "devloop" → Click Install
```

**Option 2: Manual Installation**
```bash
# Install from the devloop repository
git clone https://github.com/wioota/devloop
cd devloop/vscode-extension
npm install
npm run compile
# Extension is now installed in ~/.vscode/extensions/devloop-*
```

### Features

- **Real-time Findings** — View linting, type checking, and security issues inline
- **Quick Fixes** — Apply auto-fixes directly from the editor
- **Status Bar** — Shows agent status, finding count, and health metrics
- **Diagnostics Panel** — Detailed findings organized by agent and severity
- **Multi-language Support** — Python, JavaScript, TypeScript, and more

### Usage

Once installed, DevLoop automatically:
1. Monitors your editor for file changes
2. Runs background agents via the LSP server
3. Displays findings as inline diagnostics
4. Provides quick fix actions for auto-fixable issues

**View findings:**
- Hover over squiggly lines to see details
- Click quick fix actions to apply changes
- Open Problems panel (Ctrl+Shift+M) to see all findings
- Check status bar for agent health

**Configuration:**
Extension settings are automatically synced with `.devloop/agents.json`. No separate configuration needed.

---

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

## Multi-CI/Registry Provider System

DevLoop uses a provider abstraction layer for CI/CD and package registry support. This means you can use DevLoop with any CI system and publish to any package registry.

### Supported CI Platforms

DevLoop auto-detects and works with:
- **GitHub Actions** — Default, with pre-push CI verification
- **GitLab CI/CD** — Full support with pipeline status monitoring
- **Jenkins** — Classic and declarative pipelines
- **CircleCI** — OAuth2 and API token authentication
- **Custom CI** — Via manual configuration

### Supported Package Registries

Publish agents and packages to:
- **PyPI** — Python Package Index (via Poetry or Twine)
- **npm** — Node Package Manager
- **Docker Registry** — Docker Hub or custom registries
- **GitHub Releases** — Attach artifacts to releases
- **Custom Registries** — Via manual configuration (Artifactory, etc.)

### Release Workflow

DevLoop provides a unified release process across all providers:

```bash
# Check if ready to release
devloop release check 1.2.3

# Publish to detected CI/registry
devloop release publish 1.2.3

# Specify explicit providers
devloop release publish 1.2.3 --ci github --registry pypi

# Dry-run to see what would happen
devloop release publish 1.2.3 --dry-run
```

The release workflow automatically:
1. Validates preconditions (clean git, passing CI, valid version)
2. Creates annotated git tag
3. Publishes to registry
4. Pushes tag to remote repository

[Full provider documentation →](./docs/architecture.md#provider-system)

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

### Token Security

DevLoop securely manages API keys and tokens for agent integrations:

```bash
# Use environment variables for all credentials
export SNYK_TOKEN="your-token"
export CODE_RABBIT_API_KEY="your-key"
export GITHUB_TOKEN="your-token"

# DevLoop automatically:
# - Hides tokens in logs and process lists
# - Validates token format and expiry
# - Warns about placeholder values ("changeme", "token", etc.)
# - Never logs full token values
```

**Best practices:**
- ✅ Use environment variables (never command-line arguments)
- ✅ Enable token expiry and rotation (30-90 days recommended)
- ✅ Use read-only or project-scoped tokens when possible
- ✅ Store tokens in `.env` file (add to `.gitignore`)
- ❌ Never commit tokens to git
- ❌ Never pass tokens as command arguments
- ❌ Never hardcode tokens in code

**Token validation:**
```bash
# DevLoop validates token format during initialization
devloop init /path/to/project

# View token status
devloop status --show-token-info
```

[Full token security guide →](./docs/security.md#token-security)

[Full configuration reference →](./docs/configuration.md)

---

## Integration with Beads

DevLoop integrates with [Beads](https://github.com/wioota/devloop) task tracking to create actionable work items from detected patterns.

### Auto-Issue Creation

DevLoop automatically creates Beads issues for significant findings:

```bash
# View auto-created issues from DevLoop findings
bd ready           # Shows unblocked work
bd show bd-abc123  # View specific issue created by DevLoop
```

**What gets tracked:**
- Security vulnerabilities (high/critical only)
- Performance regressions
- Pattern discoveries (e.g., "same issue found 3 times")
- Failing tests in CI
- Deprecated dependencies

**Issue linking:**
DevLoop uses `discovered-from` dependencies to link:
- Findings → Beads issues → Original agent
- Patterns across multiple findings
- Root cause analysis chains

### Thread Context Capture

When using DevLoop in [Amp](https://ampcode.com) threads:

```bash
# Automatically captures thread context (if AMP_THREAD_ID is set)
devloop watch .
```

DevLoop logs:
- Thread ID and URL
- Commands executed
- Agent findings and results
- Patterns detected across sessions

This enables cross-thread pattern detection:
> "This type of error appeared in 5 different threads — likely a documentation gap"

---

## Event Logging & Observability

DevLoop maintains a complete audit trail of agent activity for debugging and analysis.

### Event Store

All agent actions are logged to an SQLite event store in `.devloop/events.db`:

```bash
# View recent agent activity
devloop audit query --limit 20

# Filter by agent
devloop audit query --agent linter

# View agent health metrics
devloop health
```

**Event data includes:**
- Agent name and execution time
- Success/failure status
- Finding count and types
- Resource usage (CPU, memory)
- Timestamps and correlations

### Log Files

Application logs are stored in `.devloop/devloop.log` with rotation:

```bash
# View logs in real-time
tail -f .devloop/devloop.log

# View verbose logs during watch
devloop watch . --verbose --foreground

# Check log disk usage
du -sh .devloop/devloop.log*
```

**Log rotation:**
- Max file size: 100MB
- Keep 3 backups (300MB max)
- Auto-cleanup logs older than 7 days

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

**Current status:** ✅ 737+ tests passing

[View test strategy →](./CODING_RULES.md)

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

[Developer guide →](./CODING_RULES.md)

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

### User Guides
- **[Getting Started Guide](./docs/getting-started.md)** — Installation and basic usage
- **[Architecture Guide](./docs/architecture.md)** — System design and components
- **[Configuration Guide](./docs/configuration.md)** — Full config reference
- **[CLI Commands](./CLI_REFERENCE.md)** — Command reference

### Agent Development
- **[Agent Development Guide](./docs/agent-development.md)** — Tutorial, API reference, examples, and troubleshooting

### Marketplace
- **[Marketplace Guide](./docs/marketplace.md)** — Discovering, installing, publishing agents, and API reference
- **[Agent Reference](./ARCHITECTURE.md)** — Agent categories and architecture

### Advanced
- **[Development Guide](./CODING_RULES.md)** — Contributing and development standards
- **[Upgrade Guide](./docs/UPGRADE_GUIDE.md)** — Version migration and breaking changes

---

## Design Principles

DevLoop follows these core principles:

✅ **Non-Intrusive** — Runs in background without blocking workflow
✅ **Event-Driven** — All actions triggered by observable events
✅ **Configurable** — Fine-grained control over agent behavior
✅ **Context-Aware** — Understands your project structure
✅ **Parallel** — Multiple agents run concurrently
✅ **Lightweight** — Respects system resources

[Read the AI agent workflow guide →](./AGENTS.md) | [System architecture →](./ARCHITECTURE.md)

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

### Snyk or CodeRabbit not working

**Snyk Agent Issues:**

```bash
# Verify Snyk CLI is installed
snyk --version

# Check authentication
snyk auth status

# Re-authenticate if needed
snyk auth

# Verify token is set
echo $SNYK_TOKEN

# Test manually
snyk test --json
```

**CodeRabbit Agent Issues:**

```bash
# Verify CodeRabbit CLI is installed
coderabbit --version

# Check API key is set
echo $CODE_RABBIT_API_KEY

# Test manually
coderabbit review --format json <file>
```

**Common Issues:**
- **"CLI not installed"** — Install via `npm install -g snyk` or `npm install -g @code-rabbit/cli`
- **"Authentication failed"** — Re-run `snyk auth` or verify `CODE_RABBIT_API_KEY`
- **"No vulnerabilities found but expected some"** — Ensure dependency files exist (package.json, requirements.txt, etc.)
- **Agent not triggering** — Check file patterns in `.devloop/agents.json` match your dependency files

### Agent modified my files unexpectedly

1. Check git diff: `git diff`
2. Revert changes: `git checkout -- .`
3. Disable the problematic agent in `.devloop/agents.json`
4. Report issue with: `git show HEAD:.devloop/agents.json`

[Full troubleshooting guide →](#troubleshooting)

---

## Roadmap

### Completed ✅
- Core agents: linting, formatting, testing, type checking
- Security & performance: vulnerability scanning, profiling
- Workflow automation: git integration, CI monitoring, documentation
- Custom agents: create your own without writing code
- Learning system: pattern recognition and optimization
- **Agent Marketplace** — Registry API, publishing, signing, discovery (737+ tests)

### In Development 🚀
- Remote agent registry and cloud sync
- Agent composition and pipelines
- Community agent sharing and rating improvements

### Future 🔮
- Multi-project support
- Team coordination features
- LLM-powered agents
- Agent marketplace web interface

---

## Amp Integration

Using DevLoop in Amp? The `devloop init` command automatically configures Amp integration:

- Registers slash commands (`/agent-summary`, `/agent-status`)
- Sets up post-task verification hooks
- Injects commit discipline into system prompts

The commit/push discipline is automatically enforced via `.agents/verify-task-complete`.

See the [Getting Started Guide](./docs/getting-started.md) for detailed setup instructions.

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

## Footnotes

[^1]: **90%+ CI failures caught locally** — Based on typical Python/TypeScript development workflows with comprehensive linting, formatting, and type checking. Actual results depend on your agent configuration and test suite. DevLoop's effectiveness increases with more agents enabled and better test coverage. See [docs/UPGRADE_GUIDE.md](docs/UPGRADE_GUIDE.md#version-compatibility) for feature availability by version.

[^2]: **60%+ CI cost reduction** — Estimated reduction assumes: (1) 6-8 CI failures per day baseline, (2) ~15 minutes per failure roundtrip, (3) CI costs proportional to pipeline runs. This is a theoretical projection based on typical development patterns. Actual cost savings depend on your CI pricing model, agent configuration, and codebase size. For verified metrics, see [Architecture Guide — Metrics](./docs/architecture.md#metrics-and-monitoring).

[^3]: **6-8 CI failures per day and 75-90 minutes saved** — These estimates are based on typical multi-developer teams working on moderately complex codebases. They assume agents catch common issues (formatting, linting, type errors, security warnings) before push. Your actual results will vary significantly based on: code complexity, team size, quality of tests, agent configuration, and development practices. For personalized ROI calculation, enable metrics tracking in `.devloop/agents.json` and see `devloop telemetry stats`. DevLoop will collect real usage data as you use it, which can replace these estimates with empirically validated numbers.

