# Production Daemon Setup

This guide explains how to set up DevLoop as a production daemon using systemd or supervisor for proper process supervision, automatic restarts, and health monitoring.

## Overview

DevLoop can run as a supervised daemon process that:
- ✅ Automatically restarts on crashes
- ✅ Monitors daemon health with heartbeat checks
- ✅ Integrates with system process managers (systemd/supervisor)
- ✅ Provides health status endpoints
- ✅ Enforces resource limits
- ✅ Manages log rotation

## Quick Start

### Option 1: Systemd (Recommended for Linux)

1. **Copy the service template:**
   ```bash
   sudo cp src/devloop/cli/templates/systemd/devloop.service \
       /etc/systemd/system/devloop@.service
   ```

2. **Enable and start for your project:**
   ```bash
   # Replace 'myproject' with your project name
   sudo systemctl enable devloop@myproject
   sudo systemctl start devloop@myproject
   ```

3. **Check status:**
   ```bash
   sudo systemctl status devloop@myproject
   devloop daemon-status ~/dev/myproject
   ```

### Option 2: Supervisor

1. **Install supervisor:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install supervisor

   # macOS
   brew install supervisor
   ```

2. **Configure for your project:**
   ```bash
   # Copy template and customize
   cp src/devloop/cli/templates/supervisor/devloop.conf \
       /etc/supervisor/conf.d/devloop-myproject.conf

   # Edit the file to set PROJECT_DIR and USER
   sudo nano /etc/supervisor/conf.d/devloop-myproject.conf
   ```

3. **Start the daemon:**
   ```bash
   sudo supervisorctl reread
   sudo supervisorctl update
   sudo supervisorctl start devloop
   ```

4. **Check status:**
   ```bash
   sudo supervisorctl status devloop
   devloop daemon-status ~/dev/myproject
   ```

## Systemd Setup (Detailed)

### Service Template

The systemd service template (`devloop.service`) provides:

**Features:**
- Automatic restart on failure
- Resource limits (512MB RAM, 25% CPU)
- Security hardening (private tmp, protected system)
- Structured logging
- Rate-limited restart attempts

**Configuration:**

```ini
[Unit]
Description=DevLoop Development Workflow Automation
After=network.target

[Service]
Type=simple
User=%i
WorkingDirectory=%h/dev/%i
ExecStart=/usr/bin/env devloop watch --foreground %h/dev/%i
Restart=always
RestartSec=5
StandardOutput=append:%h/.devloop/devloop.log
StandardError=append:%h/.devloop/devloop-error.log

# Resource limits
MemoryLimit=512M
CPUQuota=25%

# Security hardening
PrivateTmp=yes
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=%h/dev/%i/.devloop

[Install]
WantedBy=multi-user.target
```

### Installation Steps

1. **Install the service template:**
   ```bash
   sudo cp src/devloop/cli/templates/systemd/devloop.service \
       /etc/systemd/system/devloop@.service
   ```

2. **Reload systemd:**
   ```bash
   sudo systemctl daemon-reload
   ```

3. **Enable the service for your project:**
   ```bash
   # For a project at ~/dev/myproject
   sudo systemctl enable devloop@myproject
   ```

4. **Start the service:**
   ```bash
   sudo systemctl start devloop@myproject
   ```

### Management Commands

```bash
# Start daemon
sudo systemctl start devloop@myproject

# Stop daemon
sudo systemctl stop devloop@myproject

# Restart daemon
sudo systemctl restart devloop@myproject

# Check status
sudo systemctl status devloop@myproject

# View logs
sudo journalctl -u devloop@myproject -f

# Check health
devloop daemon-status ~/dev/myproject
```

### Customizing Resource Limits

Edit `/etc/systemd/system/devloop@.service`:

```ini
# Increase memory limit to 1GB
MemoryLimit=1G

# Increase CPU quota to 50%
CPUQuota=50%

# Add I/O limits
IOWeight=500
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart devloop@myproject
```

## Supervisor Setup (Detailed)

### Configuration Template

The supervisor config (`devloop.conf`) provides:

**Features:**
- Automatic restart with retry limits
- Log rotation
- Process priority management
- Environment variable support

**Configuration:**

```ini
[program:devloop]
command=/usr/bin/env devloop watch --foreground %(ENV_PROJECT_DIR)s
directory=%(ENV_PROJECT_DIR)s
user=%(ENV_USER)s
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=%(ENV_PROJECT_DIR)s/.devloop/devloop.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=3

startretries=5
startsecs=5
stopwaitsecs=10
priority=999
environment=PYTHONUNBUFFERED=1
```

### Installation Steps

1. **Install supervisor:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install supervisor

   # macOS (requires homebrew)
   brew install supervisor
   ```

2. **Create project-specific config:**
   ```bash
   sudo nano /etc/supervisor/conf.d/devloop-myproject.conf
   ```

3. **Configure the file:**
   ```ini
   [program:devloop-myproject]
   command=/usr/bin/env devloop watch --foreground /home/user/dev/myproject
   directory=/home/user/dev/myproject
   user=youruser
   autostart=true
   autorestart=true
   redirect_stderr=true
   stdout_logfile=/home/user/dev/myproject/.devloop/devloop.log
   stdout_logfile_maxbytes=10MB
   stdout_logfile_backups=3

   startretries=5
   startsecs=5
   stopwaitsecs=10
   priority=999
   environment=PYTHONUNBUFFERED=1
   ```

4. **Load and start:**
   ```bash
   sudo supervisorctl reread
   sudo supervisorctl update
   sudo supervisorctl start devloop-myproject
   ```

### Management Commands

```bash
# Start daemon
sudo supervisorctl start devloop-myproject

# Stop daemon
sudo supervisorctl stop devloop-myproject

# Restart daemon
sudo supervisorctl restart devloop-myproject

# Check status
sudo supervisorctl status devloop-myproject

# View logs
sudo supervisorctl tail -f devloop-myproject

# Check health
devloop daemon-status ~/dev/myproject
```

## Health Monitoring

### Heartbeat Mechanism

DevLoop writes a heartbeat file every 30 seconds to `.devloop/daemon.heartbeat`:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "pid": 12345,
  "uptime_seconds": 3600
}
```

The daemon is considered **unhealthy** if:
- No heartbeat file exists
- Last heartbeat is older than 60 seconds (2x interval)
- Health check returns an error

### Checking Daemon Health

**CLI Command:**
```bash
devloop daemon-status ~/dev/myproject
```

**Output:**
```
✅ Daemon Status: HEALTHY
Message: Last heartbeat 15s ago
PID: 12345
Uptime: 1h 30m
```

**Programmatic Check:**
```python
from pathlib import Path
from devloop.core.daemon_health import check_daemon_health

health = check_daemon_health(Path("/home/user/dev/myproject"))
print(health["status"])  # HEALTHY, UNHEALTHY, or ERROR
print(health["healthy"])  # True or False
```

### External Monitoring Integration

**Nagios/Icinga:**
```bash
#!/bin/bash
# check_devloop.sh - Nagios plugin for DevLoop health

PROJECT_DIR="/home/user/dev/myproject"
HEALTH_FILE="$PROJECT_DIR/.devloop/daemon.heartbeat"

if [ ! -f "$HEALTH_FILE" ]; then
    echo "CRITICAL - No heartbeat file found"
    exit 2
fi

LAST_BEAT=$(jq -r '.timestamp' "$HEALTH_FILE")
NOW=$(date -u +%s)
LAST_BEAT_SEC=$(date -d "$LAST_BEAT" +%s)
DIFF=$((NOW - LAST_BEAT_SEC))

if [ $DIFF -gt 120 ]; then
    echo "CRITICAL - Last heartbeat ${DIFF}s ago"
    exit 2
elif [ $DIFF -gt 60 ]; then
    echo "WARNING - Last heartbeat ${DIFF}s ago"
    exit 1
else
    echo "OK - Last heartbeat ${DIFF}s ago"
    exit 0
fi
```

**Prometheus:**
```python
# prometheus_exporter.py - Export DevLoop metrics to Prometheus

from pathlib import Path
from prometheus_client import Gauge, start_http_server
from devloop.core.daemon_health import check_daemon_health
import time

# Define metrics
daemon_health = Gauge('devloop_daemon_health', 'Daemon health status (1=healthy, 0=unhealthy)')
daemon_uptime = Gauge('devloop_daemon_uptime_seconds', 'Daemon uptime in seconds')

def collect_metrics(project_dir: Path):
    health = check_daemon_health(project_dir)
    daemon_health.set(1 if health['healthy'] else 0)
    if 'uptime_seconds' in health:
        daemon_uptime.set(health['uptime_seconds'])

if __name__ == '__main__':
    start_http_server(9100)
    project_dir = Path('/home/user/dev/myproject')

    while True:
        collect_metrics(project_dir)
        time.sleep(30)
```

## Restart Policies

### Systemd Restart Policy

The systemd service automatically restarts with these settings:

- **Restart=always**: Restart on any exit (clean or crash)
- **RestartSec=5**: Wait 5 seconds between restart attempts
- **StartLimitBurst=5**: Maximum 5 restart attempts
- **StartLimitInterval=600**: Within 10 minutes

**Behavior:**
- Daemon crashes → Wait 5s → Restart
- Restart fails 5 times in 10 minutes → Stop trying
- After 10 minutes → Reset restart counter

### Supervisor Restart Policy

The supervisor config uses:

- **autorestart=true**: Always restart on exit
- **startretries=5**: Maximum 5 consecutive restart attempts
- **startsecs=5**: Process must stay alive 5s to count as "started"
- **stopwaitsecs=10**: Wait 10s for graceful shutdown

**Behavior:**
- Daemon crashes → Restart immediately
- Restart fails 5 times → Stop and require manual intervention
- Process runs >5s → Reset retry counter

### Custom Restart Policies

**Systemd - Only restart on failure:**
```ini
[Service]
Restart=on-failure
RestartSec=10
```

**Systemd - Restart with exponential backoff:**
```ini
[Service]
Restart=always
RestartSec=5
StartLimitBurst=10
StartLimitInterval=300
```

**Supervisor - Never restart:**
```ini
[program:devloop]
autorestart=false
```

## Security Considerations

### Systemd Security Hardening

The default service template includes:

```ini
# Prevent privilege escalation
NoNewPrivileges=yes

# Isolate temporary files
PrivateTmp=yes

# Protect system directories
ProtectSystem=strict
ProtectHome=read-only

# Allow writes only to .devloop
ReadWritePaths=%h/dev/%i/.devloop
```

### Additional Hardening (Optional)

```ini
# Prevent network access (if DevLoop doesn't need it)
PrivateNetwork=yes

# Restrict system calls
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

# Hide /proc files from other users
ProtectProc=invisible

# Prevent kernel module loading
ProtectKernelModules=yes
```

### Running as Non-Root User

**Best Practice:** Always run DevLoop as a regular user, never as root.

**Systemd:**
```ini
[Service]
User=youruser
Group=youruser
```

**Supervisor:**
```ini
[program:devloop]
user=youruser
```

## Troubleshooting

### Daemon Won't Start

1. **Check systemd status:**
   ```bash
   sudo systemctl status devloop@myproject
   sudo journalctl -u devloop@myproject -n 50
   ```

2. **Check supervisor status:**
   ```bash
   sudo supervisorctl status devloop-myproject
   sudo supervisorctl tail devloop-myproject stderr
   ```

3. **Verify DevLoop command:**
   ```bash
   # Test command manually
   devloop watch --foreground ~/dev/myproject
   ```

4. **Check permissions:**
   ```bash
   ls -la ~/dev/myproject/.devloop/
   # Ensure user has write access
   ```

### Health Check Failures

1. **Check heartbeat file:**
   ```bash
   cat ~/dev/myproject/.devloop/daemon.heartbeat
   jq . ~/dev/myproject/.devloop/daemon.heartbeat  # Pretty print
   ```

2. **Verify daemon is running:**
   ```bash
   ps aux | grep devloop
   ```

3. **Check logs for errors:**
   ```bash
   tail -f ~/dev/myproject/.devloop/devloop.log
   tail -f ~/dev/myproject/.devloop/devloop-error.log
   ```

### Frequent Restarts

1. **Check restart count:**
   ```bash
   # Systemd
   systemctl show devloop@myproject | grep Restart

   # Supervisor
   sudo supervisorctl status devloop-myproject
   ```

2. **Review error logs:**
   ```bash
   # Find common errors
   grep ERROR ~/dev/myproject/.devloop/devloop.log | tail -20
   ```

3. **Increase resources if needed:**
   ```ini
   # Systemd - increase memory
   MemoryLimit=1G
   ```

4. **Disable restart temporarily for debugging:**
   ```bash
   # Systemd
   sudo systemctl edit devloop@myproject
   # Add: Restart=no

   # Supervisor
   sudo nano /etc/supervisor/conf.d/devloop-myproject.conf
   # Set: autorestart=false
   ```

## Best Practices

1. **Use systemd on Linux servers** - Better integration, security, and resource management
2. **Use supervisor for development** - Simpler setup, cross-platform
3. **Monitor health regularly** - Set up external monitoring alerts
4. **Review logs periodically** - Catch issues before they become critical
5. **Set appropriate resource limits** - Prevent runaway processes
6. **Test restart policies** - Ensure daemon recovers from failures
7. **Keep templates updated** - Run `devloop update-hooks` after upgrades

## See Also

- [DevLoop Documentation](../README.md)
- [Configuration Guide](./CONFIGURATION.md)
- [Systemd Documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Supervisor Documentation](http://supervisord.org/configuration.html)
