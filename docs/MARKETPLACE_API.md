# Marketplace API Documentation

## Overview

DevLoop includes a REST API for the agent marketplace.

## Starting the Server

```bash
# Start marketplace server
devloop marketplace server start --port 8000

# View logs
devloop marketplace server logs

# Stop server
devloop marketplace server stop
```

## API Endpoints

### Search Agents
```
GET /api/v1/agents/search?q=formatter&category=code-quality
```

### Get Agent Details
```
GET /api/v1/agents/{name}
```

### List Agent Versions
```
GET /api/v1/agents/{name}/versions
```

### Register Agent
```
POST /api/v1/agents
```

### Rate Agent
```
POST /api/v1/agents/{name}/rate
```

### List Categories
```
GET /api/v1/categories
```

### Registry Statistics
```
GET /api/v1/stats
```

## API Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## See Also

- [MARKETPLACE_GUIDE.md](./MARKETPLACE_GUIDE.md) - Publishing and installing agents
- [README.md](../README.md#agent-marketplace) - Marketplace overview
