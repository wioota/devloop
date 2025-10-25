#!/bin/bash
# Run claude-agents directly from source without installation

cd "$(dirname "$0")"
export PYTHONPATH="$PWD/src:$PYTHONPATH"
python3 -m claude_agents.cli.main "$@"
