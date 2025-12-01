# DevLoop Log Rotation Configuration

## Problem
DevLoop logs can grow unbounded, consuming significant disk space over time. The default configuration has no log rotation limits.

## Solution
Configure log rotation in `.devloop/agents.json` to automatically:
- Rotate logs when they exceed 100MB
- Keep only 3 backups of previous logs
- Compress rotated logs to save space
- Delete logs older than 7 days

## Configuration

Add this to your `.devloop/agents.json` under `"global"` → `"logging"`:

```json
{
  "global": {
    "logging": {
      "level": "info",
      "rotation": {
        "enabled": true,
        "maxSize": "100MB",
        "maxBackups": 3,
        "maxAgeDays": 7,
        "compress": true
      }
    }
  }
}
```

## What This Does

- **level: "info"**: Reduces verbosity from debug to info (less noise, smaller logs)
- **maxSize: "100MB"**: Rotate log when it reaches 100MB
- **maxBackups: 3**: Keep only 3 previous versions (devloop.log.1.gz, devloop.log.2.gz, devloop.log.3.gz)
- **maxAgeDays: 7**: Delete logs older than 7 days
- **compress: true**: Compress rotated logs with gzip

## Cleanup Existing Logs

If you already have large log files:

```bash
# Stop DevLoop first
devloop stop

# Remove existing logs
rm .devloop/*.log .devloop/*.log.*.gz

# Restart DevLoop
devloop watch .
```

## Monitoring

Check log disk usage:

```bash
du -sh .devloop/
```

The log directory should now stay under control (typically <500MB even with active development).
