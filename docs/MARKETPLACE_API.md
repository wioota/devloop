# Agent Marketplace Registry API

Complete REST API and Python SDK for the devloop agent marketplace registry.

## Overview

The Marketplace Registry API provides HTTP endpoints and Python classes for:
- **Searching** agents by name, keyword, or category
- **Retrieving** agent metadata and details
- **Managing** agent registrations, ratings, and lifecycle
- **Monitoring** registry statistics and health

## Quick Start

### Installation

Install with marketplace API support:

```bash
pip install devloop[marketplace-api]
```

Or install FastAPI and uvicorn separately:

```bash
pip install fastapi uvicorn
```

### Start the HTTP Server

```python
from pathlib import Path
from devloop.marketplace import create_http_server

# Create and run server
server = create_http_server(
    registry_dir=Path("~/.devloop/registry"),
    host="127.0.0.1",
    port=8000,
)

server.run()
```

Then access the API at: `http://localhost:8000`

## Python API

### Basic Usage

```python
from pathlib import Path
from devloop.marketplace import RegistryAPI, create_registry_client

# Create API instance
client = create_registry_client(Path("~/.devloop/registry"))
api = RegistryAPI(client)

# Register an agent
metadata = {
    "name": "my-linter",
    "version": "1.0.0",
    "description": "Custom linter for Python",
    "author": "Your Name",
    "license": "MIT",
    "homepage": "https://github.com/you/my-linter",
}

response = api.register_agent(metadata)
if response.success:
    print(f"Agent registered: {response.data['agent']}")
else:
    print(f"Error: {response.error}")

# Search for agents
response = api.search_agents(query="linter", categories=["linting"])
print(f"Found {response.data['total_results']} agents")

# Get a specific agent
response = api.get_agent("my-linter")
if response.success:
    agent = response.data
    print(f"Agent: {agent['name']} v{agent['version']}")

# Rate an agent
response = api.rate_agent("my-linter", 4.5)
print(f"Average rating: {response.data['average_rating']}")
```

### API Response Format

All API methods return a `RegistryAPIResponse`:

```python
@dataclass
class RegistryAPIResponse:
    success: bool           # True if operation succeeded
    data: Optional[Any]     # Response data (if successful)
    error: Optional[str]    # Error message (if failed)
    timestamp: str          # ISO 8601 timestamp
```

Convert to dictionary:

```python
response = api.get_agent("my-agent")
response_dict = response.to_dict()
# {
#     "success": True,
#     "data": {...},
#     "timestamp": "2024-12-13T..."
# }
```

## HTTP REST API

Base URL: `http://localhost:8000/api/v1`

### Health Check

**GET** `/health`

Check API health and status.

```bash
curl http://localhost:8000/health
```

Response:
```json
{
    "success": true,
    "data": {
        "status": "healthy",
        "registry_stats": {
            "local": {
                "total_agents": 42,
                "active_agents": 40,
                "total_downloads": 1250,
                "average_rating": 4.3,
                "categories": {"linting": 10, "formatting": 8}
            }
        }
    },
    "timestamp": "2024-12-13T..."
}
```

### Agent Management

#### Register Agent

**POST** `/agents`

Register a new agent in the marketplace.

Request body:
```json
{
    "name": "my-linter",
    "version": "1.0.0",
    "description": "A custom linter",
    "author": "Your Name",
    "license": "MIT",
    "homepage": "https://example.com",
    "repository": "https://github.com/you/my-linter",
    "documentation": "https://docs.example.com",
    "categories": ["linting"],
    "keywords": ["linter", "code-quality"],
    "python_version": ">=3.11",
    "devloop_version": ">=0.5.0",
    "trusted": false,
    "experimental": false
}
```

Response:
```json
{
    "success": true,
    "data": {
        "agent": "my-linter",
        "version": "1.0.0",
        "message": "Agent registered successfully"
    },
    "timestamp": "2024-12-13T..."
}
```

#### Get Agent

**GET** `/agents/{agent_name}`

Retrieve detailed metadata for an agent.

Parameters:
- `version` (optional): Specific version to retrieve
- `search_remote` (optional): Search remote registries (default: true)

```bash
curl "http://localhost:8000/api/v1/agents/my-linter?version=1.0.0"
```

Response:
```json
{
    "success": true,
    "data": {
        "name": "my-linter",
        "version": "1.0.0",
        "description": "A custom linter",
        "author": "Your Name",
        "license": "MIT",
        "homepage": "https://example.com",
        "categories": ["linting"],
        "downloads": 42,
        "rating": {
            "average": 4.5,
            "count": 12
        },
        "published_at": "2024-12-01T...",
        "updated_at": "2024-12-13T..."
    },
    "timestamp": "2024-12-13T..."
}
```

#### Delete Agent

**DELETE** `/agents/{agent_name}`

Remove an agent from the registry.

```bash
curl -X DELETE http://localhost:8000/api/v1/agents/my-linter
```

### Search & Discovery

#### Search Agents

**GET** `/agents/search`

Search for agents by name, description, or keywords.

Parameters:
- `q` (required): Search query
- `categories` (optional): Filter by categories
- `min_rating` (optional): Minimum rating (1-5)
- `search_remote` (optional): Search remote registries (default: true)
- `limit` (optional): Max results (default: 50, max: 200)
- `offset` (optional): Result offset for pagination (default: 0)

```bash
curl "http://localhost:8000/api/v1/agents/search?q=linter&categories=linting&min_rating=4.0&limit=20"
```

Response:
```json
{
    "success": true,
    "data": {
        "local": [...],
        "remote": [...],
        "query": "linter",
        "total_results": 5
    },
    "timestamp": "2024-12-13T..."
}
```

#### List All Agents

**GET** `/agents`

List all agents with optional filtering.

Parameters:
- `category` (optional): Filter by category
- `include_deprecated` (optional): Include deprecated agents (default: false)
- `sort` (optional): Sort field - `rating`, `downloads`, or `name` (default: rating)
- `limit` (optional): Max results (default: 100, max: 500)
- `offset` (optional): Result offset (default: 0)

```bash
curl "http://localhost:8000/api/v1/agents?category=linting&sort=downloads&limit=20"
```

#### Get Popular Agents

**GET** `/agents/popular`

Get the most popular/recommended agents.

Parameters:
- `limit` (optional): Max results (default: 10, max: 100)

```bash
curl "http://localhost:8000/api/v1/agents/popular?limit=5"
```

#### Get Trusted Agents

**GET** `/agents/trusted`

Get all trusted/verified agents.

```bash
curl http://localhost:8000/api/v1/agents/trusted
```

### Categories

#### List Categories

**GET** `/categories`

Get available agent categories with counts.

```bash
curl http://localhost:8000/api/v1/categories
```

Response:
```json
{
    "success": true,
    "data": {
        "categories": {
            "linting": 15,
            "formatting": 12,
            "testing": 8,
            "security": 5
        },
        "total_categories": 4
    },
    "timestamp": "2024-12-13T..."
}
```

#### Get Agents by Category

**GET** `/categories/{category_name}`

Get all agents in a specific category.

Parameters:
- `search_remote` (optional): Search remote registries (default: true)
- `limit` (optional): Max results (default: 50, max: 200)

```bash
curl "http://localhost:8000/api/v1/categories/linting?limit=10"
```

### Ratings & Downloads

#### Rate Agent

**POST** `/agents/{agent_name}/rate`

Rate an agent (1-5 stars).

Request body:
```json
4.5
```

```bash
curl -X POST http://localhost:8000/api/v1/agents/my-linter/rate \
  -H "Content-Type: application/json" \
  -d "4.5"
```

Response:
```json
{
    "success": true,
    "data": {
        "agent": "my-linter",
        "rating": 4.5,
        "average_rating": 4.3,
        "rating_count": 12
    },
    "timestamp": "2024-12-13T..."
}
```

#### Record Download

**POST** `/agents/{agent_name}/download`

Record a download for an agent.

```bash
curl -X POST http://localhost:8000/api/v1/agents/my-linter/download
```

Response:
```json
{
    "success": true,
    "data": {
        "agent": "my-linter",
        "downloads": 43
    },
    "timestamp": "2024-12-13T..."
}
```

### Lifecycle Management

#### Deprecate Agent

**POST** `/agents/{agent_name}/deprecate`

Mark an agent as deprecated.

Request body:
```json
"Use new-linter instead"
```

```bash
curl -X POST http://localhost:8000/api/v1/agents/old-linter/deprecate \
  -H "Content-Type: application/json" \
  -d '"Use new-linter instead"'
```

### Statistics

#### Get Registry Stats

**GET** `/stats`

Get comprehensive registry statistics.

```bash
curl http://localhost:8000/api/v1/stats
```

Response:
```json
{
    "success": true,
    "data": {
        "local": {
            "total_agents": 42,
            "active_agents": 40,
            "deprecated_agents": 2,
            "trusted_agents": 8,
            "experimental_agents": 3,
            "total_downloads": 1250,
            "average_rating": 4.3,
            "categories": {
                "linting": 10,
                "formatting": 8,
                "testing": 6,
                "security": 5
            }
        },
        "remote_registries": 0,
        "timestamp": "2024-12-13T..."
    },
    "timestamp": "2024-12-13T..."
}
```

## Agent Metadata Schema

Complete agent metadata format:

```json
{
    "name": "my-linter",
    "version": "1.0.0",
    "description": "A custom linter for Python code",
    "author": "Your Name or Organization",
    "license": "MIT",
    "homepage": "https://example.com",
    "repository": "https://github.com/you/my-linter",
    "documentation": "https://docs.example.com",
    "keywords": ["linting", "python", "code-quality"],
    "categories": ["linting", "code-quality"],
    "python_version": ">=3.11",
    "devloop_version": ">=0.5.0",
    "dependencies": [
        {
            "name": "some-package",
            "version": ">=1.0.0,<2.0.0",
            "optional": false,
            "description": "Required dependency"
        }
    ],
    "trusted": false,
    "experimental": false,
    "deprecated": false,
    "custom": {
        "additional_field": "value"
    }
}
```

### Required Fields

- `name` - Unique identifier (alphanumeric, dash, underscore)
- `version` - Semantic version (X.Y.Z)
- `description` - Short description (≤500 chars)
- `author` - Author name or organization
- `license` - SPDX license identifier

### Recommended Fields

- `homepage` - or `repository` (at least one required)
- `repository` - Git repository URL
- `categories` - List of categories
- `keywords` - List of keywords for search
- `documentation` - Link to documentation

## Error Handling

### HTTP Status Codes

- `200` - Success
- `400` - Bad request (validation error)
- `404` - Not found (agent doesn't exist)
- `422` - Validation error (invalid parameters)
- `500` - Server error
- `503` - Service unavailable

### Error Response Format

```json
{
    "success": false,
    "error": "Agent not found: nonexistent",
    "timestamp": "2024-12-13T..."
}
```

## Examples

### Complete Workflow

```python
from pathlib import Path
from devloop.marketplace import create_registry_client, RegistryAPI

# Initialize
client = create_registry_client(Path("~/.devloop/registry"))
api = RegistryAPI(client)

# 1. Register agent
agent_metadata = {
    "name": "my-formatter",
    "version": "1.0.0",
    "description": "Fast code formatter for Python",
    "author": "Jane Doe",
    "license": "Apache-2.0",
    "homepage": "https://example.com",
    "categories": ["formatting"],
    "keywords": ["formatter", "code-quality"],
}

response = api.register_agent(agent_metadata)
print(f"Registered: {response.data['agent']}")

# 2. List agents by category
response = api.get_agents_by_category("formatting")
print(f"Formatters: {len(response.data['agents'])} agents")

# 3. Search for similar agents
response = api.search_agents(query="formatter")
print(f"Search results: {response.data['total_results']} agents")

# 4. Rate an agent
response = api.rate_agent("my-formatter", 5.0)
print(f"Rating: {response.data['average_rating']}")

# 5. Get statistics
response = api.get_stats()
stats = response.data['local']
print(f"Registry has {stats['total_agents']} agents")

# 6. Deprecate old version
response = api.deprecate_agent("old-formatter", "Use my-formatter v2.0 instead")
print("Agent deprecated")
```

### Using the HTTP API with curl

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-linter",
    "version": "1.0.0",
    "description": "Custom linter",
    "author": "Jane Doe",
    "license": "MIT",
    "homepage": "https://example.com"
  }'

# 2. Search
curl "http://localhost:8000/api/v1/agents/search?q=linter&limit=10"

# 3. Get agent
curl http://localhost:8000/api/v1/agents/my-linter

# 4. Rate
curl -X POST http://localhost:8000/api/v1/agents/my-linter/rate \
  -H "Content-Type: application/json" \
  -d "4.5"

# 5. Record download
curl -X POST http://localhost:8000/api/v1/agents/my-linter/download

# 6. Get stats
curl http://localhost:8000/api/v1/stats
```

## Performance Considerations

- **Caching**: Remote registry responses are cached for 24 hours
- **Pagination**: Use `limit` and `offset` for large result sets
- **Filtering**: Use `categories` and `min_rating` to reduce result size
- **Batch Operations**: For multiple operations, consider batching requests

## Security

- The API is designed for local/trusted use by default
- Deploy behind a reverse proxy (nginx, etc.) for public exposure
- Consider authentication/authorization for write operations
- Validate all inputs (done by default, but check response.success)

## See Also

- [Marketplace Documentation](./MARKETPLACE.md)
- [Agent Development Guide](./AGENT_DEVELOPMENT.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
