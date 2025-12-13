# DevLoop Telemetry & Value Tracking

DevLoop includes structured event logging to track your development workflow and measure its value. This documentation explains how to use telemetry features.

## Overview

DevLoop automatically logs structured events to `.devloop/events.jsonl` (JSONL format - one JSON object per line). This allows you to:

- **Track DevLoop's Impact**: See how many CI roundtrips you've prevented, issues caught locally, etc.
- **Measure Time Saved**: Understand the actual time impact DevLoop provides
- **Analyze Patterns**: Identify which agents are most valuable for your workflow
- **Generate Reports**: Export data for ROI analysis or team dashboards

## Automatic Event Logging

DevLoop automatically logs the following events:

### Agent Executions
When an agent successfully executes:
```json
{
  "event_type": "agent_executed",
  "timestamp": "2024-01-15T10:23:45Z",
  "agent": "linter",
  "duration_ms": 123,
  "findings": 3,
  "severity_levels": ["error", "warning"],
  "success": true
}
```

### Pre-Commit Checks
When pre-commit hook runs:
```json
{
  "event_type": "pre_commit_check",
  "timestamp": "2024-01-15T10:24:00Z",
  "success": true,
  "duration_ms": 500,
  "details": {"checks_run": 3}
}
```

### Pre-Push Checks
When pre-push hook prevents a bad push:
```json
{
  "event_type": "pre_push_check",
  "timestamp": "2024-01-15T10:25:00Z",
  "success": false,
  "prevented_bad_push": true,
  "reason": "failure",
  "duration_ms": 200
}
```

### CI Roundtrips Prevented
When pre-push prevents unnecessary CI runs:
```json
{
  "event_type": "ci_roundtrip_prevented",
  "timestamp": "2024-01-15T10:25:30Z",
  "reason": "lint-error",
  "check_that_would_fail": "linter"
}
```

### Value Events
Manual events you can log for custom tracking:
```json
{
  "event_type": "value_event",
  "timestamp": "2024-01-15T10:30:00Z",
  "duration_ms": 1200,
  "event_name": "interruption_prevented",
  "description": "Prevented need to debug in CI"
}
```

## CLI Commands

### View Statistics
```bash
devloop telemetry stats
```

Shows summary statistics:
- Total events logged
- Events by type
- Agent execution stats (count, duration)
- CI roundtrips prevented
- Time saved

Example output:
```
DevLoop Telemetry Statistics
┌─────────────────────────────┬──────────┐
│ Metric                      │ Value    │
├─────────────────────────────┼──────────┤
│ Total Events                │ 147      │
│ Total Findings              │ 23       │
│ CI Roundtrips Prevented     │ 5        │
│ Total Time Saved            │ 45.2s    │
└─────────────────────────────┴──────────┘
```

### View Recent Events
```bash
devloop telemetry recent --count 20
```

Shows recent telemetry events with timestamps and details.

### Export Data
```bash
devloop telemetry export report.json
devloop telemetry export report.jsonl
```

Export all events to JSON (array) or JSONL (one per line) format for further analysis.

## Usage Examples

### Python API - Manual Event Logging

You can programmatically log events:

```python
from devloop.core.telemetry import get_telemetry_logger

telemetry = get_telemetry_logger()

# Log an agent execution
telemetry.log_agent_execution(
    agent="my-custom-agent",
    duration_ms=250,
    findings=2,
    severity_levels=["warning"],
    success=True
)

# Log a CI roundtrip prevented
telemetry.log_ci_roundtrip_prevented(
    reason="security-scan",
    check_that_would_fail="bandit"
)

# Log a value event
telemetry.log_value_event(
    event_name="context_switch_prevented",
    time_saved_ms=300,
    description="Caught issue before context switch to CI debug"
)
```

### Get Statistics

```python
telemetry = get_telemetry_logger()
stats = telemetry.get_stats()

print(f"Total findings: {stats['total_findings']}")
print(f"CI roundtrips prevented: {stats['ci_roundtrips_prevented']}")
print(f"Total time saved: {stats['total_time_saved_ms']/1000:.1f}s")
```

### Export for Analysis

```python
telemetry = get_telemetry_logger()
events = telemetry.get_events(limit=1000)

import json
with open("events.json", "w") as f:
    json.dump(events, f, indent=2)
```

## Understanding Your Data

### Key Metrics

**Total Events**: Overall activity level
- Higher = more agent activity
- Baseline for understanding usage patterns

**Total Findings**: Issues detected locally
- Higher = more value (catching issues early)
- Compare to CI failures to see detection rate

**CI Roundtrips Prevented**: Push attempts blocked
- Each prevented = saved ~10-30 min of CI wait + debug time
- Key value metric

**Time Saved**: Manually logged interruptions prevented
- Actual developer time impact
- Most important for ROI analysis

### Agent Performance

By agent statistics show:
- **Executions**: How often the agent runs
- **Total Duration**: Cumulative execution time
- **Avg Duration**: Performance per execution

Example analysis:
```
Linter: 50 executions, 2500ms total, 50ms avg
Type-Checker: 50 executions, 8500ms total, 170ms avg
Test Runner: 25 executions, 45000ms total, 1800ms avg
```

This shows which agents are heavy (Test Runner) vs lightweight (Linter).

## Data Privacy

Telemetry data is:
- **Local only**: Stored in `.devloop/events.jsonl` in your repository
- **Never sent anywhere**: No cloud connectivity
- **Your data**: You control what's logged and can delete anytime
- **Repo-local**: Each repository has its own events file

To disable telemetry, simply don't log events. Event logging is passive (doesn't happen unless code explicitly logs).

## Analysis Ideas

### ROI Calculation

```python
# Estimate time saved per CI roundtrip prevented (adjust for your CI)
ci_roundtrips = stats['ci_roundtrips_prevented']
time_per_roundtrip = 20 * 60  # 20 minutes in seconds
manual_time_saved = stats['total_time_saved_ms'] / 1000

total_time_saved_hours = (ci_roundtrips * time_per_roundtrip + manual_time_saved) / 3600
developer_hourly_rate = 150  # adjust for your salary
roi_dollars = total_time_saved_hours * developer_hourly_rate
```

### Workflow Optimization

```python
# Find most impactful agents
by_type = stats['events_by_type']
prevention_rate = stats['ci_roundtrips_prevented'] / by_type.get('pre_push_check', 1)

# Identify slow agents
agents = stats['agents_executed']
slow_agents = [(name, data['total_duration_ms'] / data['count']) 
               for name, data in agents.items()]
```

### Team Dashboard

Export events regularly to build team-wide metrics:
- Track trends over time
- Compare developer workflows
- Identify best practices
- Measure process improvements

## Configuration

Telemetry is enabled by default. Events are logged to:
```
.devloop/events.jsonl
```

To change location, pass custom path:
```python
from devloop.core.telemetry import TelemetryLogger
from pathlib import Path

telemetry = TelemetryLogger(Path("custom/location/events.jsonl"))
```

## Cleanup

Events are kept indefinitely in `.devloop/events.jsonl`. To manage file size:

```bash
# View file size
ls -lh .devloop/events.jsonl

# Archive old data
mv .devloop/events.jsonl .devloop/events-2024.jsonl

# Start fresh
rm .devloop/events.jsonl  # Will be recreated on next event
```

Or implement archival in a script:
```python
import json
from datetime import datetime, timedelta
from pathlib import Path

# Archive events older than 30 days
cutoff = datetime.now() - timedelta(days=30)
events = []

with open(".devloop/events.jsonl") as f:
    for line in f:
        event = json.loads(line)
        if event['timestamp'] > cutoff.isoformat():
            events.append(event)

with open(".devloop/events.jsonl", "w") as f:
    for event in events:
        f.write(json.dumps(event) + "\n")
```

## See Also

- [AGENTS.md](./AGENTS.md) - Agent architecture and configuration
- [ROADMAP.md](./ROADMAP.md) - Future features and improvements
