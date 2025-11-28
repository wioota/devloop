#!/bin/bash
# CI Status Checker - checks GitHub Actions workflow status
# Usage: ./check-ci-status.sh [--wait] [--branch BRANCH]

set -e

WAIT=false
BRANCH=$(git rev-parse --abbrev-ref HEAD)
TIMEOUT=120  # 2 minutes max wait
CHECK_INTERVAL=10  # Check every 10 seconds

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --wait)
            WAIT=true
            shift
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "⚠️  'gh' CLI not found. Install with: brew install gh (or apt-get install gh)"
    echo "   Skipping CI status check."
    exit 0
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "⚠️  'gh' CLI not authenticated. Run: gh auth login"
    echo "   Skipping CI status check."
    exit 0
fi

# Get the latest commit SHA
COMMIT=$(git rev-parse HEAD)
COMMIT_SHORT=$(git rev-parse --short HEAD)

echo "🔍 Checking CI status for commit $COMMIT_SHORT on branch '$BRANCH'..."

# Function to check workflow status
check_status() {
    # Get workflow runs for this commit
    RUNS=$(gh run list --commit "$COMMIT" --json status,conclusion,name,databaseId 2>/dev/null || echo "[]")

    if [ "$RUNS" = "[]" ] || [ -z "$RUNS" ]; then
        return 1  # No runs found
    fi

    # Parse status
    IN_PROGRESS=$(echo "$RUNS" | jq '[.[] | select(.status == "in_progress")] | length')
    COMPLETED=$(echo "$RUNS" | jq '[.[] | select(.status == "completed")] | length')
    SUCCESS=$(echo "$RUNS" | jq '[.[] | select(.conclusion == "success")] | length')
    FAILURE=$(echo "$RUNS" | jq '[.[] | select(.conclusion == "failure")] | length')

    TOTAL=$(echo "$RUNS" | jq 'length')

    if [ "$IN_PROGRESS" -gt 0 ]; then
        echo "⏳ CI running... ($COMPLETED/$TOTAL completed)"
        return 2  # Still in progress
    elif [ "$FAILURE" -gt 0 ]; then
        echo ""
        echo "❌ CI FAILED for commit $COMMIT_SHORT"
        echo ""
        echo "Failed workflows:"
        echo "$RUNS" | jq -r '.[] | select(.conclusion == "failure") | "  - \(.name) (run #\(.databaseId))"'
        echo ""
        echo "View details: gh run list --commit $COMMIT"
        return 3  # Failed
    elif [ "$SUCCESS" -eq "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
        echo "✅ CI passed for commit $COMMIT_SHORT ($SUCCESS/$TOTAL workflows)"
        return 0  # Success
    else
        return 1  # Unknown state
    fi
}

# Initial check
if check_status; then
    exit 0
fi

STATUS=$?

if [ "$STATUS" -eq 3 ]; then
    # CI failed
    exit 1
fi

# If --wait flag is set, wait for CI to complete
if [ "$WAIT" = true ]; then
    echo "Waiting for CI to complete (timeout: ${TIMEOUT}s)..."
    ELAPSED=0

    while [ $ELAPSED -lt $TIMEOUT ]; do
        sleep $CHECK_INTERVAL
        ELAPSED=$((ELAPSED + CHECK_INTERVAL))

        if check_status; then
            exit 0
        fi

        STATUS=$?
        if [ "$STATUS" -eq 3 ]; then
            # CI failed
            exit 1
        fi
    done

    echo "⏱️  Timeout waiting for CI. Check status later with: gh run list"
    exit 0
else
    # No runs found yet or still queued
    if [ "$STATUS" -eq 1 ]; then
        echo "⏳ CI not started yet. Check later with: gh run list --commit $COMMIT"
    fi
    exit 0
fi
