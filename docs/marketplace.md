# Marketplace Guide

> Discover, publish, and manage community agents in the DevLoop marketplace.

---

## Overview

The DevLoop marketplace is a registry for sharing and discovering agents. It supports publishing with cryptographic signing, semantic versioning, ratings/reviews, and a REST API server.

---

## Discovering Agents

### Search

```bash
# Full-text search
devloop marketplace search "formatter"

# Filter by category
devloop marketplace search --category code-quality --sort rating

# List available categories
devloop marketplace list-categories
```

### Install

```bash
# Install a specific version
devloop marketplace install my-agent-name 1.0.0

# View agent details before installing
devloop agent info my-agent-name --reviews --stats
```

---

## Publishing Agents

### Prerequisites

Your agent directory needs an `agent.json` metadata file:

```json
{
  "name": "my-agent",
  "version": "1.0.0",
  "description": "What this agent does",
  "author": "Your Name",
  "license": "MIT",
  "homepage": "https://github.com/you/my-agent",
  "repository": "https://github.com/you/my-agent",
  "categories": ["code-quality"],
  "keywords": ["quality", "analysis"],
  "pythonVersion": ">=3.11",
  "devloopVersion": ">=0.5.0"
}
```

### Publish Workflow

```bash
# 1. Check readiness
devloop agent check ./my-agent

# 2. Publish (auto-signs with SHA256)
devloop agent publish ./my-agent

# 3. Verify the published signature
devloop agent verify ./my-agent

# 4. View published metadata
devloop agent info ./my-agent --signature
```

### Version Management

```bash
# Bump version (semantic versioning)
devloop agent version ./my-agent patch   # 1.0.0 → 1.0.1
devloop agent version ./my-agent minor   # 1.0.0 → 1.1.0
devloop agent version ./my-agent major   # 1.0.0 → 2.0.0

# Deprecate a version
devloop agent deprecate my-agent --message "Use my-agent-v2 instead"
```

### Cryptographic Signing

DevLoop automatically signs published agents:
- SHA256 checksums for each file
- Directory hash for tamper detection
- Verification via `devloop agent verify`

---

## Agent Ratings and Reviews

```bash
# Rate an agent (1-5 stars)
devloop agent rate my-agent 5 --message "Works great, very fast!"

# View reviews
devloop agent reviews my-agent

# View detailed stats
devloop agent info my-agent --reviews --stats
```

---

## Tool Dependencies

Agents can declare external tool dependencies:

```json
{
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
    }
  }
}
```

**Supported dependency types:**
- `python` — pip packages
- `npm-global` — Global npm packages
- `binary` — System executables
- `venv` — Virtual environment executables
- `docker` — Docker images

```bash
# Check dependencies
devloop agent dependencies check ./my-agent

# Auto-resolve missing dependencies
devloop agent dependencies resolve ./my-agent

# List declared dependencies
devloop agent dependencies list ./my-agent
```

---

## REST API Reference

Run a local marketplace server with HTTP endpoints:

### Server Management

```bash
# Start server
devloop marketplace server start --port 8000

# With options
devloop marketplace server start --port 8000 --host 0.0.0.0 --workers 4

# View logs
devloop marketplace server logs

# Stop server
devloop marketplace server stop

# Registry statistics
devloop marketplace status
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/agents/search?q=formatter&category=code-quality` | Search agents |
| `GET` | `/api/v1/agents/{name}` | Get agent details |
| `GET` | `/api/v1/agents/{name}/versions` | List versions |
| `POST` | `/api/v1/agents` | Register new agent |
| `POST` | `/api/v1/agents/{name}/rate` | Rate an agent |
| `POST` | `/api/v1/agents/{name}/review` | Leave a review |
| `GET` | `/api/v1/agents/{name}/reviews` | Get reviews |
| `GET` | `/api/v1/categories` | List categories |
| `GET` | `/api/v1/stats` | Registry statistics |
| `POST` | `/api/v1/install/{name}/{version}` | Record installation |

### API Documentation

When the server is running:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Python Client

```python
from devloop.marketplace import RegistryAPI, create_registry_client
from pathlib import Path

# Initialize client
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

---

## See Also

- [Agent Development Guide](./agent-development.md) — Creating agents
- [Architecture Guide](./architecture.md) — System design
- [Getting Started](./getting-started.md) — Installation
