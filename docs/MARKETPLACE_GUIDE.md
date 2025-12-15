# Marketplace Guide

## Publishing Agents

```bash
# Check if ready to publish
devloop agent check ./my-agent

# Publish agent
devloop agent publish ./my-agent

# Bump version
devloop agent version ./my-agent patch
```

## Installing Agents

```bash
# Search for agents
devloop marketplace search "formatter"

# Install agent
devloop marketplace install my-agent-name 1.0.0

# List installed agents
devloop custom-list
```

## Agent Ratings

```bash
# Rate an agent
devloop agent rate my-agent 5 --message "Great agent!"

# View ratings
devloop agent reviews my-agent
```

## Agent Signing

DevLoop automatically signs agents with SHA256 checksums for integrity verification.

```bash
# Verify agent signature
devloop agent verify ./my-agent

# View signature info
devloop agent info ./my-agent --signature
```

## See Also

- [MARKETPLACE_API.md](./MARKETPLACE_API.md) - API reference
- [AGENT_DEVELOPMENT.md](./AGENT_DEVELOPMENT.md) - Creating agents
