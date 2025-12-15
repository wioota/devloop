# Metrics and Monitoring

## Overview

DevLoop tracks agent performance, resource usage, and findings for monitoring and optimization.

## Event Logging

All agent activity is logged to SQLite: `.devloop/events.db`

```bash
# View recent activity
devloop audit query --limit 20

# Filter by agent
devloop audit query --agent linter

# View health metrics
devloop health
```

## Log Files

Application logs: `.devloop/devloop.log`

```bash
# View logs in real-time
tail -f .devloop/devloop.log

# Verbose logging
devloop watch . --verbose --foreground
```

## Log Rotation

- Max file size: 100MB
- Keep 3 backups (300MB max)
- Auto-cleanup logs older than 7 days

## Metrics Tracked

- Agent execution time
- Success/failure rates
- Finding counts by severity
- Resource usage (CPU, memory)
- Timestamps and correlations

## Performance Analysis

```bash
# View agent performance
devloop perf-summary --agent formatter

# Learning insights
devloop learning-insights --agent linter

# Recommendations
devloop learning-recommendations linter
```

## CI Cost Reduction

Track actual savings from catching issues locally:

```bash
# Enable metrics tracking in .devloop/agents.json
# View telemetry stats
devloop telemetry stats
```

## See Also

- [README.md](../README.md#event-logging--observability) - Observability overview
- [configuration.md](./configuration.md) - Configuration guide
