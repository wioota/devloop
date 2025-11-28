"""Git event collector using git hooks and monitoring."""

from __future__ import annotations

import subprocess  # nosec B404 - Required for git operations
from pathlib import Path
from typing import Any, Dict, Optional

from dev_agents.collectors.base import BaseCollector
from dev_agents.core.event import EventBus


class GitCollector(BaseCollector):
    """Collects git-related events through hooks and monitoring."""

    def __init__(self, event_bus: EventBus, config: Optional[Dict[str, Any]] = None):
        super().__init__("git", event_bus, config)
        self.git_hooks = [
            "pre-commit",
            "prepare-commit-msg",
            "commit-msg",
            "post-commit",
            "pre-rebase",
            "post-checkout",
            "post-merge",
            "pre-push",
            "post-rewrite",
        ]
        self.repo_path = Path(self.config.get("repo_path", ".")).absolute()
        self.installed_hooks: Dict[str, Path] = {}

    def _is_git_repo(self) -> bool:
        """Check if current directory is a git repository."""
        try:
            result = subprocess.run(  # nosec
            ["git", "rev-parse", "--git-dir"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _get_hooks_dir(self) -> Path:
        """Get the git hooks directory."""
        return self.repo_path / ".git" / "hooks"

    def _install_hook(self, hook_name: str) -> bool:
        """Install a git hook script."""
        hooks_dir = self._get_hooks_dir()
        hook_path = hooks_dir / hook_name

        # Create hook script content
        hook_script = f"""#!/bin/bash
# Claude Agents Git Hook - {hook_name}

# Export environment for Python
export PYTHONPATH="$(dirname $(dirname $(dirname $(dirname $(dirname "$0")))))/src"

# Call the collector
python3 -c "
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))
from dev_agents.collectors.git import GitCollector

async def emit_hook_event():
    # Import here to avoid circular imports
    from dev_agents.core.event import EventBus, Event, Priority
    import os

    event_bus = EventBus()
    collector = GitCollector(event_bus)

    payload = {{
        'hook': '{hook_name}',
        'repo_path': '{str(self.repo_path)}',
        'args': list(sys.argv[1:]),
        'env': dict(os.environ)
    }}

    await collector._emit_event(f'git:{hook_name}', payload, 'high')

asyncio.run(emit_hook_event())
"

# Continue with original hook if it exists
if [ -f "$0.original" ]; then
    exec "$0.original" "$@"
fi
"""

        try:
            # Backup original hook if it exists
            if hook_path.exists():
                backup_path = hook_path.with_suffix(".original")
                if not backup_path.exists():
                    hook_path.rename(backup_path)
                    self.logger.info(f"Backed up original {hook_name} hook")

            # Write new hook
            hook_path.write_text(hook_script)
            hook_path.chmod(0o755)

            self.installed_hooks[hook_name] = hook_path
            self.logger.info(f"Installed {hook_name} hook")
            return True

        except Exception as e:
            self.logger.error(f"Failed to install {hook_name} hook: {e}")
            return False

    def _uninstall_hooks(self) -> None:
        """Uninstall all git hooks."""
        for hook_name, hook_path in self.installed_hooks.items():
            try:
                # Restore original hook if it exists
                original_path = hook_path.with_suffix(".original")
                if original_path.exists():
                    original_path.rename(hook_path)
                    self.logger.info(f"Restored original {hook_name} hook")
                elif hook_path.exists():
                    hook_path.unlink()
                    self.logger.info(f"Removed {hook_name} hook")

            except Exception as e:
                self.logger.error(f"Failed to uninstall {hook_name} hook: {e}")

        self.installed_hooks.clear()

    async def start(self) -> None:
        """Start the git collector."""
        if self.is_running:
            return

        if not self._is_git_repo():
            self.logger.warning(f"Not a git repository: {self.repo_path}")
            return

        self._set_running(True)

        # Install git hooks
        hooks_dir = self._get_hooks_dir()
        hooks_dir.mkdir(parents=True, exist_ok=True)

        installed_count = 0
        for hook_name in self.git_hooks:
            if self.config.get("auto_install_hooks", True):
                if self._install_hook(hook_name):
                    installed_count += 1

        self.logger.info(f"Git collector started - installed {installed_count} hooks")

    async def stop(self) -> None:
        """Stop the git collector."""
        if not self.is_running:
            return

        # Uninstall hooks if we installed them
        if self.config.get("auto_install_hooks", True):
            self._uninstall_hooks()

        self._set_running(False)
        self.logger.info("Git collector stopped")

    async def emit_git_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Manually emit a git event (for testing or external triggers)."""
        await self._emit_event(f"git:{event_type}", payload, "normal", "git")
