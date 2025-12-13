# DevLoop Marketplace Guide

Complete guide to discovering, installing, and publishing agents on the DevLoop Marketplace.

## Table of Contents

1. [Overview](#overview)
2. [Discovering Agents](#discovering-agents)
3. [Installing Agents](#installing-agents)
4. [Publishing Your Agent](#publishing-your-agent)
5. [Agent Metadata](#agent-metadata)
6. [Best Practices](#best-practices)
7. [Marketplace Policies](#marketplace-policies)
8. [Support & Feedback](#support--feedback)

## Overview

The DevLoop Marketplace is a central hub for discovering, sharing, and installing custom agents. It provides:

- **Searchable catalog** of community and official agents
- **Installation management** - easy install/update/remove
- **Quality metrics** - ratings, downloads, reviews
- **Version control** - compatible versions, changelogs
- **Documentation** - comprehensive guides and examples

### Marketplace Architecture

```
Developer creates agent
    ↓
Package & publish to marketplace
    ↓
Marketplace indexes and validates
    ↓
Listed in discover/search
    ↓
Users install via devloop CLI
    ↓
Agent integrates with DevLoop
```

## Discovering Agents

### Search Agents

Find agents using the CLI:

```bash
# Search by name or keyword
devloop search linter
devloop search "type checker"
devloop search formatter

# Search with filters
devloop search --category code-quality
devloop search --rating 4+
devloop search --downloads 100+

# View all agents (paginated)
devloop search --all --limit 20
```

### Web Marketplace

Browse at [https://marketplace.devloop.dev](https://marketplace.devloop.dev):

- **Categories** - Browse by agent type
- **Ratings** - Sort by community ratings
- **Trending** - See popular agents
- **Featured** - Official and recommended agents
- **Author** - Find agents by author

### Agent Details

Get detailed information:

```bash
devloop info my-awesome-agent

# Output:
# Name: My Awesome Agent
# Author: John Doe
# Version: 1.0.0
# Downloads: 1,234
# Rating: 4.5/5 (48 reviews)
# Triggers: file:save, git:pre-commit
# Description: ...
```

## Installing Agents

### Install from Marketplace

```bash
# Install latest version
devloop install my-awesome-agent

# Install specific version
devloop install my-awesome-agent@1.0.0

# Install with custom config
devloop install my-awesome-agent \
  --config '{"strict": true, "timeout": 10}'

# Install from local directory
devloop install ./my-local-agent
```

### Verify Installation

```bash
# List installed agents
devloop list agents

# Check agent status
devloop status my-awesome-agent

# Test agent
devloop test my-awesome-agent
```

### Configure Installed Agent

After installation, configure in `.devloop/agents.json`:

```json
{
  "agents": {
    "my-awesome-agent": {
      "enabled": true,
      "triggers": ["file:save"],
      "config": {
        "strict_mode": false,
        "timeout": 5.0
      }
    }
  }
}
```

### Update Agents

```bash
# Update specific agent
devloop update my-awesome-agent

# Update to specific version
devloop update my-awesome-agent@1.2.0

# Update all agents
devloop update --all

# Check for updates
devloop check-updates
```

### Remove Agents

```bash
# Remove agent
devloop uninstall my-awesome-agent

# Remove and clean config
devloop uninstall my-awesome-agent --clean
```

## Publishing Your Agent

### Preparation Checklist

Before publishing, ensure:

- ✅ Agent code is well-structured and tested
- ✅ README is comprehensive and clear
- ✅ Metadata is complete and accurate
- ✅ Tests pass locally (`pytest tests/`)
- ✅ Type hints are properly used
- ✅ Documentation includes examples
- ✅ License is specified (MIT, Apache-2.0, etc.)
- ✅ No hardcoded credentials or secrets

### Project Structure

Your agent should have this structure:

```
my-awesome-agent/
├── src/
│   └── my_awesome_agent/
│       ├── __init__.py
│       ├── agent.py              # Main agent implementation
│       ├── config.py             # Configuration class
│       └── utils.py              # Helper functions
├── tests/
│   ├── __init__.py
│   ├── test_agent.py             # Unit tests
│   └── test_integration.py       # Integration tests
├── docs/
│   ├── README.md                 # Main documentation
│   ├── EXAMPLES.md               # Usage examples
│   └── TROUBLESHOOTING.md        # Common issues
├── README.md                      # Project overview (required)
├── CHANGELOG.md                   # Version history
├── LICENSE                        # License file
├── pyproject.toml                # Package metadata (required)
└── .gitignore
```

### Package Configuration

Create `pyproject.toml`:

```toml
[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[project]
name = "my-awesome-agent"
version = "1.0.0"
description = "Awesome DevLoop agent for checking things"
authors = [{name = "Your Name", email = "you@example.com"}]
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.9"
keywords = ["devloop", "agent", "linting"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Software Development :: Libraries",
    "Topic :: Software Development :: Quality Assurance",
]

dependencies = [
    "devloop>=0.9.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21.0",
    "mypy>=1.0",
]

[project.entry-points."devloop.agents"]
my-awesome-agent = "my_awesome_agent.agent:MyAwesomeAgent"

[tool.poetry.urls]
Homepage = "https://github.com/myuser/my-awesome-agent"
Repository = "https://github.com/myuser/my-awesome-agent"
Documentation = "https://github.com/myuser/my-awesome-agent/blob/main/README.md"
```

### README Template

Create a comprehensive `README.md`:

```markdown
# My Awesome Agent

Brief description of what your agent does.

## Features

- Feature 1
- Feature 2
- Feature 3

## Installation

\`\`\`bash
devloop install my-awesome-agent
\`\`\`

## Configuration

Configure in `.devloop/agents.json`:

\`\`\`json
{
  "agents": {
    "my-awesome-agent": {
      "enabled": true,
      "triggers": ["file:save"],
      "config": {
        "strict_mode": false
      }
    }
  }
}
\`\`\`

## Usage

Describe how to use the agent and what events it responds to.

## Examples

Provide practical examples of:
- Configuration for different scenarios
- Expected output/results
- Common use cases

## Triggers

- `file:save` - When a file is saved
- `git:pre-commit` - Before a commit

## Output Format

Describe the structure of the agent's output/results.

## Troubleshooting

Document common issues and solutions.

## Contributing

How others can contribute improvements.

## License

MIT

## Author

Your name and contact
```

### Create Marketplace Metadata

Create `.devloop/marketplace.json` in your project:

```json
{
  "id": "my-awesome-agent",
  "name": "My Awesome Agent",
  "version": "1.0.0",
  "author": "Your Name",
  "email": "you@example.com",
  "homepage": "https://github.com/myuser/my-awesome-agent",
  "repository": "https://github.com/myuser/my-awesome-agent",
  "license": "MIT",
  "description": "Short description of what the agent does",
  "long_description": "Longer description with more details about features, use cases, etc.",
  "keywords": ["linting", "code-quality", "python"],
  "category": "code-quality",
  "tags": ["python", "linting", "static-analysis"],
  "triggers": ["file:save", "git:pre-commit"],
  "python_requires": ">=3.9",
  "devloop_requires": ">=0.9.0",
  "icon": "icon.png",
  "badges": [
    {
      "type": "build",
      "url": "https://github.com/myuser/my-awesome-agent/workflows/test/badge.svg"
    },
    {
      "type": "downloads",
      "url": "https://img.shields.io/pypi/dm/my-awesome-agent"
    }
  ],
  "installation_notes": "Optional: Special setup instructions",
  "configuration_notes": "Optional: Special configuration instructions"
}
```

### Add Screenshots/Assets

Include visual documentation:

```
my-awesome-agent/
├── icon.png                    # 128x128 PNG (agent icon)
├── screenshot-1.png           # Example output
├── screenshot-2.png           # Configuration UI
└── demo.gif                    # Optional: demo animation
```

### Testing Requirements

All published agents must pass:

```bash
# Unit tests
pytest tests/

# Type checking
mypy src/

# Code formatting
black --check src/

# Linting
ruff check src/

# Import sorting
isort --check-only src/

# Security scanning
bandit -r src/
```

Set up CI/CD (GitHub Actions example):

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest
      - run: mypy src/
      - run: black --check src/
      - run: ruff check src/
```

### Publish to Marketplace

```bash
# Build the package
poetry build

# Publish to marketplace
devloop publish my-awesome-agent \
  --token YOUR_MARKETPLACE_TOKEN \
  --remote https://marketplace.devloop.dev

# Output:
# ✓ Validating...
# ✓ Building...
# ✓ Testing...
# ✓ Publishing...
# Successfully published my-awesome-agent@1.0.0
# View at: https://marketplace.devloop.dev/agents/my-awesome-agent
```

## Agent Metadata

### Required Metadata

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Human-readable name |
| `version` | string | Semantic version (X.Y.Z) |
| `description` | string | One-line description |
| `author` | string | Author name |
| `license` | string | License identifier (MIT, Apache-2.0, etc.) |
| `category` | string | Agent category |

### Optional Metadata

| Field | Type | Description |
|-------|------|-------------|
| `long_description` | string | Detailed description |
| `keywords` | array | Search keywords |
| `tags` | array | Categorization tags |
| `homepage` | URL | Project website |
| `repository` | URL | Source code repository |
| `icon` | URL | Agent icon (128x128) |
| `screenshots` | array | Demo screenshots |
| `triggers` | array | Supported event triggers |
| `devloop_requires` | string | Minimum DevLoop version |
| `python_requires` | string | Python version requirement |

### Categories

Choose one primary category:

- `code-quality` - Linting, formatting, type checking
- `testing` - Test runners, coverage analysis
- `security` - Vulnerability scanning, security checks
- `performance` - Profiling, optimization
- `automation` - General automation tasks
- `integration` - Third-party integrations
- `workflow` - Development workflow tools
- `documentation` - Doc generation and checking
- `monitoring` - Metrics and monitoring
- `custom` - Specialized/custom tools

## Best Practices

### 1. Clear Documentation

- ✅ Explain what the agent does in one sentence
- ✅ Provide configuration examples
- ✅ Document all triggers
- ✅ Include before/after examples
- ✅ Add troubleshooting section

### 2. Proper Error Handling

- ✅ Always return `AgentResult`
- ✅ Provide helpful error messages
- ✅ Handle missing files gracefully
- ✅ Log errors for debugging

### 3. Performance

- ✅ Use async/await properly
- ✅ Don't block the event loop
- ✅ Filter events early
- ✅ Report execution time accurately

### 4. Testing

- ✅ Unit tests for agent logic
- ✅ Integration tests with events
- ✅ Mock external dependencies
- ✅ Test error cases

### 5. Version Management

- ✅ Follow semantic versioning
- ✅ Update CHANGELOG.md for releases
- ✅ Tag releases in git
- ✅ Note breaking changes

### 6. Security

- ❌ No hardcoded credentials
- ❌ No sensitive data in logs
- ❌ No external home-phone-home
- ✅ Validate inputs
- ✅ Use secure defaults

## Marketplace Policies

### Code of Conduct

All agents must:

1. **Not be malicious** - No spyware, crypto mining, etc.
2. **Not steal data** - No unauthorized data collection
3. **Not impersonate** - No claiming false authorship
4. **Respect privacy** - No tracking or analytics without consent
5. **Be compatible** - Work with advertised DevLoop versions

### Content Standards

Agents should:

- Have clear, appropriate names
- Include accurate descriptions
- Use professional icons/screenshots
- Avoid offensive or inappropriate content
- Document limitations honestly

### License Requirements

Agents must use an open-source license:

- MIT (recommended)
- Apache-2.0
- GPL-3.0
- BSD-3-Clause
- ISC
- MPL-2.0
- AGPL-3.0

### Quality Standards

Published agents must maintain:

- ✅ Working code (passes tests)
- ✅ Complete documentation
- ✅ Responsive to bug reports
- ✅ Regular security updates
- ✅ Compatibility with current DevLoop

### Removal Policies

Agents may be removed for:

- Malicious behavior
- Security vulnerabilities not addressed
- Copyright/licensing violations
- Spam or misleading content
- Abandoned projects (no updates in 12 months)

## Support & Feedback

### Getting Help

- **Documentation**: [docs.devloop.dev](https://docs.devloop.dev)
- **Community Forum**: [forum.devloop.dev](https://forum.devloop.dev)
- **Discord**: [discord.gg/devloop](https://discord.gg/devloop)
- **GitHub Issues**: Report bugs and feature requests

### Providing Feedback

Help us improve the marketplace:

```bash
# Rate an agent
devloop rate my-awesome-agent --rating 5 --comment "Great agent!"

# Report an issue
devloop report my-awesome-agent --issue "Security vulnerability"

# Suggest improvements
devloop feedback --message "Would be great if..."
```

### Share Your Agent

If you create an agent, share it:

1. Publish to marketplace
2. Announce on community forum
3. Add to awesome-devloop list
4. Share on social media

We love hearing about what you build!

---

## Next Steps

- [Agent Development Guide](./AGENT_DEVELOPMENT.md) - Create agents
- [Agent API Reference](./AGENT_API_REFERENCE.md) - Complete API docs
- [Example Agents](https://github.com/wioota/devloop-agent-examples) - Real-world examples
- [Community Forum](https://forum.devloop.dev) - Join the community
