#!/bin/bash
# Rollback utility for Claude Agents
# Makes it easy to undo changes made by background agents

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in a project with Claude Agents
if [ ! -d ".claude" ]; then
    echo -e "${RED}❌ No .claude directory found. Are you in a project with Claude Agents?${NC}"
    exit 1
fi

show_help() {
    echo "Rollback Utility for Claude Agents"
    echo "=================================="
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  status          Show current rollback status"
    echo "  list            List recent changes that can be rolled back"
    echo "  last            Rollback the last change made"
    echo "  all             Rollback all changes from the current session"
    echo "  selective ID    Rollback specific change by backup ID"
    echo "  help            Show this help"
    echo ""
    echo "For Amp: Tell Amp 'rollback the last background agent changes'"
    echo ""
}

get_adapter() {
    # Find the adapter script
    if [ -f ".claude/integration/amp-enhanced-adapter.py" ]; then
        echo "python3 .claude/integration/amp-enhanced-adapter.py"
    elif [ -f "$HOME/.claude-agents/.claude/integration/amp-enhanced-adapter.py" ]; then
        echo "python3 $HOME/.claude-agents/.claude/integration/amp-enhanced-adapter.py"
    else
        echo -e "${RED}❌ Could not find adapter script${NC}"
        exit 1
    fi
}

ADAPTER_CMD=$(get_adapter)

rollback_last() {
    echo -e "${BLUE}🔄 Rolling back the last change...${NC}"
    result=$($ADAPTER_CMD rollback --scope last)

    if echo "$result" | grep -q '"status": "completed"'; then
        rolled_back=$(echo "$result" | grep -o '"rolled_back_count": [0-9]*' | cut -d' ' -f2)
        echo -e "${GREEN}✅ Successfully rolled back $rolled_back change(s)${NC}"

        # Show what was rolled back
        echo "$result" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for item in data.get('rolled_back', []):
    print(f'  • Restored: {item[\"file\"]}')
"
    else
        echo -e "${RED}❌ Rollback failed${NC}"
        echo "$result"
    fi
}

rollback_all() {
    echo -e "${YELLOW}⚠️  This will rollback ALL changes from background agents${NC}"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi

    echo -e "${BLUE}🔄 Rolling back all changes...${NC}"
    result=$($ADAPTER_CMD rollback --scope all)

    if echo "$result" | grep -q '"status": "completed"'; then
        rolled_back=$(echo "$result" | grep -o '"rolled_back_count": [0-9]*' | cut -d' ' -f2)
        echo -e "${GREEN}✅ Successfully rolled back $rolled_back change(s)${NC}"
    else
        echo -e "${RED}❌ Rollback failed${NC}"
        echo "$result"
    fi
}

rollback_selective() {
    backup_id="$1"
    if [ -z "$backup_id" ]; then
        echo -e "${RED}❌ Please provide a backup ID${NC}"
        echo "Use '$0 list' to see available backup IDs"
        exit 1
    fi

    echo -e "${BLUE}🔄 Rolling back change: $backup_id${NC}"
    result=$($ADAPTER_CMD rollback --scope selective --backup-ids "$backup_id")

    if echo "$result" | grep -q '"status": "completed"'; then
        rolled_back=$(echo "$result" | grep -o '"rolled_back_count": [0-9]*' | cut -d' ' -f2)
        echo -e "${GREEN}✅ Successfully rolled back $rolled_back change(s)${NC}"
    else
        echo -e "${RED}❌ Rollback failed${NC}"
        echo "$result"
    fi
}

show_status() {
    echo -e "${BLUE}📊 Rollback Status${NC}"
    echo "=================="

    if [ ! -f ".claude/context/change-log.json" ]; then
        echo -e "${GREEN}✅ No changes to rollback${NC}"
        return
    fi

    # Get context from adapter
    context=$($ADAPTER_CMD context)
    has_changes=$(echo "$context" | grep -o '"has_recent_changes": \w*' | cut -d' ' -f2)

    if [ "$has_changes" = "true" ]; then
        change_count=$(echo "$context" | grep -o '"change_count": [0-9]*' | cut -d' ' -f2)
        last_time=$(echo "$context" | grep -o '"last_change_time": "[^"]*"' | cut -d'"' -f4)

        echo -e "${YELLOW}⚠️  $change_count change(s) available for rollback${NC}"
        echo "Last change: $last_time"
        echo ""
        echo "Available commands:"
        echo "  $0 last     # Rollback last change"
        echo "  $0 all      # Rollback all changes"
        echo "  $0 list     # See detailed change list"
    else
        echo -e "${GREEN}✅ No changes to rollback${NC}"
    fi

    pending_fixes=$(echo "$context" | grep -o '"pending_fixes": [0-9]*' | cut -d' ' -f2)
    if [ "$pending_fixes" -gt 0 ]; then
        echo ""
        echo -e "${BLUE}💡 $pending_fixes safe fixes available to apply${NC}"
        echo "Run: claude-agents autofix"
    fi
}

list_changes() {
    echo -e "${BLUE}📝 Recent Changes${NC}"
    echo "================="

    if [ ! -f ".claude/context/change-log.json" ]; then
        echo "No change log found."
        return
    fi

    # Parse and display the change log
    python3 -c "
import json
import sys
from datetime import datetime

try:
    with open('.claude/context/change-log.json', 'r') as f:
        data = json.load(f)

    changes = data.get('changes', [])
    if not changes:
        print('No changes found.')
        sys.exit(0)

    print(f'Found {len(changes)} change(s):')
    print()

    for i, change in enumerate(reversed(changes[-10:])):  # Show last 10
        timestamp = change['timestamp']
        fix = change['fix']
        backup_id = change.get('rollback_id', 'N/A')

        # Format timestamp
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        time_str = dt.strftime('%H:%M:%S')

        print(f'{i+1}. [{time_str}] {fix[\"type\"].replace(\"_\", \" \").title()}')
        print(f'   File: {fix[\"file\"]}')
        print(f'   Description: {fix[\"description\"]}')
        print(f'   Backup ID: {backup_id}')
        print()

    if len(changes) > 10:
        print(f'... and {len(changes) - 10} older changes')
        print()

    print('Commands:')
    print('  rollback.sh last              # Rollback most recent')
    print('  rollback.sh selective <ID>    # Rollback specific change')
    print('  rollback.sh all               # Rollback all')

except Exception as e:
    print(f'Error reading change log: {e}')
"
}

# Main command handling
case "${1:-help}" in
    "status")
        show_status
        ;;
    "list")
        list_changes
        ;;
    "last")
        rollback_last
        ;;
    "all")
        rollback_all
        ;;
    "selective")
        rollback_selective "$2"
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
