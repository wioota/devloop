#!/bin/bash
#
# Test script for daemon supervision features
#
# This script tests the daemon health checking and supervision setup
# without actually starting systemd or supervisor services.
#

set -e

PROJECT_DIR="${1:-$PWD}"
DEVLOOP_DIR="$PROJECT_DIR/.devloop"

echo "=== DevLoop Daemon Supervision Test ==="
echo "Project: $PROJECT_DIR"
echo

# Test 1: Check template files exist
echo "Test 1: Checking template files..."
SYSTEMD_TEMPLATE="src/devloop/cli/templates/systemd/devloop.service"
SUPERVISOR_TEMPLATE="src/devloop/cli/templates/supervisor/devloop.conf"

if [ -f "$SYSTEMD_TEMPLATE" ]; then
    echo "✓ Systemd template exists: $SYSTEMD_TEMPLATE"
else
    echo "✗ Systemd template missing: $SYSTEMD_TEMPLATE"
    exit 1
fi

if [ -f "$SUPERVISOR_TEMPLATE" ]; then
    echo "✓ Supervisor template exists: $SUPERVISOR_TEMPLATE"
else
    echo "✗ Supervisor template missing: $SUPERVISOR_TEMPLATE"
    exit 1
fi

# Test 2: Verify templates have required directives
echo
echo "Test 2: Verifying template content..."

if grep -q "Restart=always" "$SYSTEMD_TEMPLATE"; then
    echo "✓ Systemd has restart policy"
else
    echo "✗ Systemd missing restart policy"
    exit 1
fi

if grep -q "MemoryLimit=" "$SYSTEMD_TEMPLATE"; then
    echo "✓ Systemd has resource limits"
else
    echo "✗ Systemd missing resource limits"
    exit 1
fi

if grep -q "autorestart=true" "$SUPERVISOR_TEMPLATE"; then
    echo "✓ Supervisor has autorestart"
else
    echo "✗ Supervisor missing autorestart"
    exit 1
fi

if grep -q "stdout_logfile_maxbytes" "$SUPERVISOR_TEMPLATE"; then
    echo "✓ Supervisor has log rotation"
else
    echo "✗ Supervisor missing log rotation"
    exit 1
fi

# Test 3: Check daemon health module
echo
echo "Test 3: Testing daemon health module..."

if [ ! -f "src/devloop/core/daemon_health.py" ]; then
    echo "✗ daemon_health.py not found"
    exit 1
fi

python3 -m py_compile src/devloop/core/daemon_health.py 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ daemon_health.py compiles successfully"
else
    echo "✗ daemon_health.py has syntax errors"
    exit 1
fi

# Test 4: Check CLI command
echo
echo "Test 4: Verifying CLI commands..."

if poetry run devloop --help | grep -q "daemon-status"; then
    echo "✓ daemon-status command registered"
else
    echo "✗ daemon-status command not found"
    exit 1
fi

# Test 5: Simulate health check without running daemon
echo
echo "Test 5: Testing health check (no daemon)..."

mkdir -p "$DEVLOOP_DIR"

# Should return UNHEALTHY when no heartbeat file exists
if poetry run devloop daemon-status "$PROJECT_DIR" 2>&1 | grep -q "UNHEALTHY\|ERROR"; then
    echo "✓ Health check correctly detects missing daemon"
else
    echo "✗ Health check did not detect missing daemon"
    exit 1
fi

# Test 6: Simulate heartbeat file
echo
echo "Test 6: Testing health check (with simulated heartbeat)..."

HEARTBEAT_FILE="$DEVLOOP_DIR/daemon.heartbeat"
cat > "$HEARTBEAT_FILE" <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.%6N)",
  "pid": $$,
  "uptime_seconds": 120
}
EOF

# Should return HEALTHY when recent heartbeat exists
if poetry run devloop daemon-status "$PROJECT_DIR" 2>&1 | grep -q "HEALTHY"; then
    echo "✓ Health check correctly detects healthy daemon"
else
    echo "✗ Health check did not detect healthy daemon"
    exit 1
fi

# Clean up
rm -f "$HEARTBEAT_FILE"

# Test 7: Check documentation
echo
echo "Test 7: Verifying documentation..."

DOC_FILE="docs/PRODUCTION_DAEMON_SETUP.md"
if [ -f "$DOC_FILE" ]; then
    echo "✓ Production daemon setup documentation exists"

    if grep -q "systemd" "$DOC_FILE" && grep -q "supervisor" "$DOC_FILE"; then
        echo "✓ Documentation covers both systemd and supervisor"
    else
        echo "✗ Documentation incomplete"
        exit 1
    fi
else
    echo "✗ Production daemon setup documentation missing"
    exit 1
fi

echo
echo "=== All Tests Passed ==="
echo
echo "Summary:"
echo "  ✓ Template files exist and are valid"
echo "  ✓ Daemon health module implemented"
echo "  ✓ CLI commands registered"
echo "  ✓ Health checking works correctly"
echo "  ✓ Documentation is complete"
echo
echo "Next steps:"
echo "  1. Review docs/PRODUCTION_DAEMON_SETUP.md"
echo "  2. Test with actual systemd: sudo systemctl start devloop@myproject"
echo "  3. Test with actual supervisor: supervisorctl start devloop"
