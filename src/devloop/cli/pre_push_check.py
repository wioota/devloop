#!/usr/bin/env python3
"""Pre-push CI check using provider abstraction."""

import json
import subprocess
import sys
from typing import Optional

from devloop.providers.provider_manager import get_provider_manager


def get_current_branch() -> Optional[str]:
    """Get current git branch."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def main() -> int:
    """Check CI status before push."""
    branch = get_current_branch()
    if not branch:
        print("ERROR: Could not determine current branch")
        return 1

    # Auto-detect provider
    manager = get_provider_manager()
    provider = manager.auto_detect_ci_provider()

    if not provider:
        print("WARNING: No CI provider available")
        return 0

    if not provider.is_available():
        print(f"WARNING: CI provider '{provider.get_provider_name()}' not available")
        return 0

    # Get latest run
    runs = provider.list_runs(branch, limit=1)
    if not runs:
        print("INFO: No CI runs found")
        return 0

    run = runs[0]

    # Output status as JSON for the calling script
    output = {
        "provider": provider.get_provider_name(),
        "branch": branch,
        "status": run.status.value,
        "conclusion": run.conclusion.value if run.conclusion else None,
        "url": run.url,
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
