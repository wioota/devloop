# Metrics and Monitoring Guide

Complete guide to exporting DevLoop metrics, setting up monitoring dashboards, and defining SLOs.

## Overview

DevLoop provides comprehensive metrics for:

- **Performance**: Agent execution time, throughput, latencies
- **Reliability**: Success rates, error counts, retry attempts
- **Resources**: CPU usage, memory footprint, disk I/O
- **Business Value**: Issues prevented, time saved, quality improvements

---

## Table of Contents

1. [Metrics Overview](#metrics-overview)
2. [Prometheus Export](#prometheus-export)
3. [Grafana Dashboards](#grafana-dashboards)
4. [Key Metrics to Monitor](#key-metrics-to-monitor)
5. [SLO Definitions](#slo-definitions)
6. [Data Export](#data-export)
7. [Dashboarding Guide](#dashboarding-guide)
8. [Alerting](#alerting)
9. [Troubleshooting](#troubleshooting)

---

## Metrics Overview

### Metric Categories

| Category | Examples | Unit |
|----------|----------|------|
| **Performance** | Agent run time, queue depth | milliseconds |
| **Reliability** | Success rate, errors, retries | count, percentage |
| **Resources** | CPU, memory, disk I/O | percent, bytes |
| **Value** | Issues prevented, time saved | count, seconds |
| **Volume** | Events processed, files changed | count |

### Metric Collection Points

```
File Change
    ↓
[Event Bus] → metrics: event_received
    ↓
[Agent Queue] → metrics: queued_for_N_ms
    ↓
[Agent Execution] → metrics: execution_time_ms, success/failure
    ↓
[Result Storage] → metrics: findings_created
    ↓
[Amp Integration] → metrics: findings_posted
```

---

## Prometheus Export

### Enable Prometheus Export

**Configuration:**

```json
{
  "global": {
    "metrics": {
      "enabled": true,
      "format": "prometheus",
      "exporters": {
        "prometheus": {
          "enabled": true,
          "port": 8000,
          "path": "/metrics"
        }
      }
    }
  }
}
```

### Start Metrics Server

```bash
devloop watch . --metrics-enabled

# Server runs on http://localhost:8000/metrics
```

### Scrape Configuration

**Prometheus `prometheus.yml`:**

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'devloop'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Available Metrics

#### Agent Metrics

```
# Counter: Total agent runs
devloop_agent_runs_total{agent="linter",status="success"} 1234
devloop_agent_runs_total{agent="linter",status="failure"} 12

# Gauge: Current queue depth
devloop_agent_queue_depth{agent="linter"} 3

# Histogram: Execution time
devloop_agent_execution_duration_ms_bucket{agent="linter",le="100"} 450
devloop_agent_execution_duration_ms_bucket{agent="linter",le="500"} 890
devloop_agent_execution_duration_ms_bucket{agent="linter",le="+Inf"} 1000

# Gauge: Last run duration
devloop_agent_last_run_ms{agent="linter"} 245
```

#### System Metrics

```
# Gauge: Current resource usage
devloop_system_cpu_percent 12.5
devloop_system_memory_mb 250

# Gauge: Agent resource usage
devloop_agent_cpu_percent{agent="test-runner"} 15.2
devloop_agent_memory_mb{agent="test-runner"} 512

# Gauge: Filesystem metrics
devloop_files_watched 9842
devloop_files_changed_total 15243
```

#### Quality Metrics

```
# Counter: Issues found
devloop_issues_found_total{severity="critical"} 23
devloop_issues_found_total{severity="high"} 156
devloop_issues_found_total{severity="medium"} 892

# Counter: Issues auto-fixed
devloop_issues_autofixed_total 145

# Gauge: Current issues by severity
devloop_active_issues{severity="critical"} 12
devloop_active_issues{severity="high"} 45
devloop_active_issues{severity="medium"} 289
```

#### Event Metrics

```
# Counter: Events processed
devloop_events_processed_total 54821

# Histogram: Event processing latency
devloop_event_latency_ms_bucket{le="100"} 40000
devloop_event_latency_ms_bucket{le="500"} 52000
devloop_event_latency_ms_bucket{le="+Inf"} 54821

# Gauge: Queue size
devloop_event_queue_size 42
```

---

## Grafana Dashboards

### Dashboard Setup

#### Install Grafana Prometheus Plugin

```bash
# Via Docker Compose
docker-compose up grafana prometheus

# Via package manager
apt-get install grafana-server
systemctl start grafana-server

# Access at http://localhost:3000
```

#### Add Prometheus Data Source

1. Administration → Data Sources
2. Add Prometheus
3. URL: `http://localhost:9090`
4. Save & Test

### Dashboard 1: Agent Performance

**Queries:**

```
# Average execution time
avg(rate(devloop_agent_execution_duration_ms_sum[5m]) / rate(devloop_agent_execution_duration_ms_count[5m]))

# Success rate
rate(devloop_agent_runs_total{status="success"}[5m]) /
rate(devloop_agent_runs_total[5m])

# Queue depth
devloop_agent_queue_depth

# P95 latency
histogram_quantile(0.95, rate(devloop_agent_execution_duration_ms_bucket[5m]))
```

**Panels:**
- Line: Success rate % (one line per agent)
- Gauge: Current queue depth
- Bar: Average execution time per agent
- Heatmap: P50/P95/P99 latencies

### Dashboard 2: System Health

**Queries:**

```
# CPU usage
devloop_system_cpu_percent

# Memory usage
devloop_system_memory_mb / 1024  # Convert to GB

# Agent count
count(devloop_agent_runs_total) by (agent)

# Watched files
devloop_files_watched
```

**Panels:**
- Gauge: CPU usage %
- Gauge: Memory usage GB
- Table: Agent stats (runs, success rate)
- Stat: Total watched files

### Dashboard 3: Quality Metrics

**Queries:**

```
# Issues by severity (stacked)
sum(devloop_active_issues) by (severity)

# Issues over time
increase(devloop_issues_found_total[1h])

# Auto-fix rate
devloop_issues_autofixed_total / devloop_issues_found_total

# False positive rate
devloop_false_positives_total / devloop_issues_found_total
```

**Panels:**
- Stacked area: Issues by severity
- Line: Issues found per hour
- Gauge: Auto-fix rate %
- Stat: Total issues prevented (weekly)

### Dashboard 4: Value Metrics

**Queries:**

```
# CI failures prevented
rate(devloop_ci_failures_prevented[24h]) * 60 * 60 * 24

# Build time saved
rate(devloop_build_time_saved_seconds[24h]) * 60 * 60 * 24

# Developer time saved
rate(devloop_developer_time_saved_seconds[24h]) / 3600

# Push success rate
rate(devloop_successful_pushes[5m]) / rate(devloop_total_pushes[5m])
```

**Panels:**
- Stat: Total CI failures prevented (weekly)
- Stat: Total build time saved (weekly)
- Stat: Total developer hours saved (weekly)
- Gauge: Push success rate %

### Pre-Built Dashboard JSON

Save as `devloop-dashboard.json`:

```json
{
  "dashboard": {
    "title": "DevLoop Metrics",
    "panels": [
      {
        "title": "Agent Success Rate",
        "targets": [
          {
            "expr": "rate(devloop_agent_runs_total{status=\"success\"}[5m]) / rate(devloop_agent_runs_total[5m])"
          }
        ]
      },
      {
        "title": "Queue Depth",
        "targets": [
          {
            "expr": "devloop_agent_queue_depth"
          }
        ]
      }
    ]
  }
}
```

---

## Key Metrics to Monitor

### Performance SLI (Service Level Indicators)

```
SLI: Agent response time
  Measure: P95 execution time < 1 second
  Query: histogram_quantile(0.95, devloop_agent_execution_duration_ms) < 1000

SLI: Queue depth
  Measure: Max queue depth < 50
  Query: max(devloop_agent_queue_depth) < 50

SLI: Throughput
  Measure: > 100 events/minute
  Query: rate(devloop_events_processed_total[5m]) > (100/60)
```

### Reliability SLI

```
SLI: Agent success rate
  Measure: > 99% success
  Query: rate(devloop_agent_runs_total{status="success"}[5m]) / 
         rate(devloop_agent_runs_total[5m]) > 0.99

SLI: Error rate
  Measure: < 1% errors
  Query: rate(devloop_agent_runs_total{status="error"}[5m]) < 0.01

SLI: Availability
  Measure: 99.9% uptime
  Query: (total_time - downtime) / total_time > 0.999
```

### Resource SLI

```
SLI: CPU usage
  Measure: < 50% CPU
  Query: devloop_system_cpu_percent < 50

SLI: Memory usage
  Measure: < 500MB
  Query: devloop_system_memory_mb < 500

SLI: Disk I/O
  Measure: < 100MB/s
  Query: rate(devloop_disk_io_bytes[5m]) < 100000000
```

### Business Value SLI

```
SLI: Issues prevented
  Measure: > 100 issues prevented daily
  Query: increase(devloop_issues_found_total[24h]) > 100

SLI: Time saved
  Measure: > 2 hours saved daily
  Query: increase(devloop_developer_time_saved_seconds[24h]) / 3600 > 2

SLI: CI cost reduction
  Measure: > 20% reduction
  Query: 1 - (current_cost / baseline_cost) > 0.2
```

---

## SLO Definitions

### Example SLOs

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: devloop-slos
spec:
  groups:
  - name: devloop.rules
    interval: 30s
    rules:
    # Agent Response Time SLO
    - record: devloop_slo:agent_response_time:p95_1h
      expr: histogram_quantile(0.95, rate(devloop_agent_execution_duration_ms_bucket[1h]))
    
    - alert: DevLoopAgentResponseTimeSLOViolation
      expr: devloop_slo:agent_response_time:p95_1h > 1000
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "DevLoop P95 agent response time exceeds SLO ({{ $value }}ms)"
    
    # Success Rate SLO
    - record: devloop_slo:success_rate:5m
      expr: rate(devloop_agent_runs_total{status="success"}[5m]) / 
            rate(devloop_agent_runs_total[5m])
    
    - alert: DevLoopSuccessRateSLOViolation
      expr: devloop_slo:success_rate:5m < 0.99
      for: 15m
      labels:
        severity: critical
      annotations:
        summary: "DevLoop success rate below SLO ({{ $value | humanizePercentage }})"
```

### SLO by Environment

**Development:**
```
- Agent response time: P95 < 2 seconds
- Success rate: > 95%
- Memory usage: < 1GB
```

**Staging:**
```
- Agent response time: P95 < 1 second
- Success rate: > 98%
- Memory usage: < 500MB
```

**Production:**
```
- Agent response time: P95 < 500ms
- Success rate: > 99.5%
- Memory usage: < 250MB
```

---

## Data Export

### Export as CSV

```bash
# Export last 24 hours
devloop telemetry export \
  --format csv \
  --start "24h ago" \
  --output metrics.csv

# Output columns:
# timestamp, agent, execution_time_ms, status, cpu_percent, memory_mb
```

### Export as JSON

```bash
# Export with full details
devloop telemetry export \
  --format json \
  --start "7d ago" \
  --detailed \
  --output metrics.json
```

### Export to S3

```bash
devloop telemetry export \
  --format json \
  --destination s3://my-bucket/devloop-metrics/ \
  --start "24h ago"
```

### Export to Time-Series DB

```bash
# Send to InfluxDB
devloop telemetry export \
  --format influx \
  --url http://localhost:8086 \
  --database devloop \
  --start "1h ago"
```

---

## Dashboarding Guide

### Dashboard Structure

**Tier 1: Overview Dashboard**
- High-level health status
- Critical SLO indicators
- Quick status summary
- For: Team leads, DevOps

**Tier 2: Agent Performance Dashboard**
- Per-agent metrics
- Success/failure breakdown
- Queue analysis
- For: Developers, SREs

**Tier 3: Detailed Analytics Dashboard**
- Deep-dive analysis
- Historical trends
- Cost/value analysis
- For: Team leads, metrics enthusiasts

**Tier 4: Debugging Dashboard**
- Detailed logs and traces
- Error analysis
- System state snapshots
- For: DevLoop developers, debugging

### Dashboard Refresh Rates

```
- Overview:    1 minute (looking for critical issues)
- Performance: 15 seconds (monitoring current state)
- Analytics:   1 hour (historical trends)
- Debug:       5 seconds (active troubleshooting)
```

### Alerting Thresholds

```yaml
# Critical (page on-call)
- Success rate < 98%
- P95 latency > 2 seconds
- CPU > 80%
- Memory > 1GB

# Warning (ticket)
- Success rate < 99%
- P95 latency > 1 second
- CPU > 60%
- Memory > 500MB

# Info (log only)
- New agent added
- Configuration changed
- Metrics export successful
```

---

## Troubleshooting

### Issue: No Metrics Appearing

**Check 1: Is metrics export enabled?**
```bash
devloop status | grep -i metrics

# Should show: Metrics: enabled
```

**Check 2: Is Prometheus scraping?**
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Should show: devloop healthy
```

**Check 3: Are agents running?**
```bash
devloop watch . --verbose

# Should show agent execution logs
```

### Issue: High CPU from Metrics Collection

**Symptoms:**
- CPU goes up after enabling metrics
- Metrics server consuming 20%+ CPU

**Solutions:**
1. Increase Prometheus scrape interval:
   ```yaml
   scrape_interval: 60s  # Instead of 15s
   ```

2. Disable high-cardinality metrics:
   ```json
   {
     "metrics": {
       "disabledMetrics": ["event_latency_histogram"]
     }
   }
   ```

3. Sample metrics instead of collecting all:
   ```json
   {
     "metrics": {
       "sampleRate": 0.1  # Only 10% of events
     }
   }
   ```

### Issue: Grafana Dashboard Slow

**Symptoms:**
- Dashboard queries take 30+ seconds
- Panels not loading

**Solutions:**
1. Reduce time range (check smaller windows)
2. Increase Prometheus retention:
   ```
   --storage.tsdb.retention.time=30d
   ```
3. Pre-compute common queries:
   ```yaml
   recording_rules:
   - devloop_agent_success_rate:5m
   - devloop_agent_latency:p95_5m
   ```

### Issue: Metrics Growing Too Fast

**Symptoms:**
- Prometheus disk usage increasing rapidly
- Query latency increasing

**Solutions:**
1. Reduce metric granularity:
   ```json
   {
     "metrics": {
       "granularity": "1m"  # Instead of 10s
     }
   }
   ```

2. Enable sampling:
   ```json
   {
     "metrics": {
       "sampling": 0.1
     }
   }
   ```

3. Delete old metrics:
   ```
   --storage.tsdb.retention.time=7d
   ```

---

## Integration Examples

### Jenkins Integration

```groovy
pipeline {
  post {
    always {
      // Export DevLoop metrics
      sh 'devloop telemetry export --format json --output metrics.json'
      
      // Archive metrics
      archiveArtifacts artifacts: 'metrics.json'
      
      // Post to metrics server
      sh 'curl -X POST http://metrics.local/jenkins --data-binary @metrics.json'
    }
  }
}
```

### GitHub Actions Integration

```yaml
- name: Export DevLoop Metrics
  run: devloop telemetry export --format json --output metrics.json

- name: Upload Metrics
  uses: actions/upload-artifact@v3
  with:
    name: devloop-metrics
    path: metrics.json

- name: Post to Slack
  run: |
    devloop telemetry summary | \
    curl -X POST -d @- https://hooks.slack.com/...
```

### DataDog Integration

```bash
# Export metrics in DataDog format
devloop telemetry export \
  --format datadog \
  --api-key $DATADOG_API_KEY \
  --app-key $DATADOG_APP_KEY
```

---

## Best Practices

1. **Monitor per-agent**: Track each agent separately
2. **Set appropriate SLOs**: Use realistic baselines
3. **Alert on violations**: Don't just monitor
4. **Review regularly**: Monthly SLO reviews
5. **Export data**: Back up metrics regularly
6. **Version dashboards**: Track dashboard changes
7. **Document metrics**: Explain each metric
8. **Test alerts**: Verify alerts work
9. **Baseline before**: Measure baseline before optimization
10. **Share context**: Include dashboards in runbooks

---

## See Also

- [Performance Tuning](./PERFORMANCE_TUNING.md)
- [Resource Sharing](./RESOURCE_SHARING.md)
- [Prometheus Documentation](https://prometheus.io/docs)
- [Grafana Documentation](https://grafana.com/docs)
