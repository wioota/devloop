"""Daemon health checking and heartbeat mechanism."""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DaemonHealthCheck:
    """Manages daemon health checks and heartbeat signals."""

    def __init__(self, project_dir: Path, heartbeat_interval: int = 30):
        """Initialize health check.

        Args:
            project_dir: Project directory where .devloop is located
            heartbeat_interval: Seconds between heartbeat updates (default: 30)
        """
        self.project_dir = project_dir
        self.devloop_dir = project_dir / ".devloop"
        self.heartbeat_file = self.devloop_dir / "daemon.heartbeat"
        self.health_file = self.devloop_dir / "daemon.health"
        self.heartbeat_interval = heartbeat_interval
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the heartbeat task."""
        if self._running:
            logger.warning("Health check already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info(
            f"Started daemon health check (interval: {self.heartbeat_interval}s)"
        )

    async def stop(self):
        """Stop the heartbeat task."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped daemon health check")

    async def _heartbeat_loop(self):
        """Continuously update heartbeat file."""
        while self._running:
            try:
                await self._write_heartbeat()
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                # Continue despite errors
                await asyncio.sleep(self.heartbeat_interval)

    async def _write_heartbeat(self):
        """Write heartbeat timestamp to file."""
        try:
            self.devloop_dir.mkdir(parents=True, exist_ok=True)

            heartbeat_data = {
                "timestamp": datetime.now().isoformat(),
                "pid": os.getpid(),
                "uptime_seconds": time.time() - self._start_time
                if hasattr(self, "_start_time")
                else 0,
            }

            # Initialize start time on first heartbeat
            if not hasattr(self, "_start_time"):
                self._start_time = time.time()

            # Write atomically (write to temp file, then rename)
            temp_file = self.heartbeat_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(heartbeat_data, f, indent=2)

            temp_file.replace(self.heartbeat_file)

        except Exception as e:
            logger.error(f"Failed to write heartbeat: {e}")

    def check_health(self) -> dict:
        """Check if daemon is healthy based on heartbeat.

        Returns:
            dict with health status information
        """
        try:
            if not self.heartbeat_file.exists():
                return {
                    "status": "UNHEALTHY",
                    "message": "No heartbeat file found - daemon may not be running",
                    "healthy": False,
                }

            with open(self.heartbeat_file) as f:
                heartbeat_data = json.load(f)

            last_heartbeat = datetime.fromisoformat(heartbeat_data["timestamp"])
            seconds_since = (datetime.now() - last_heartbeat).total_seconds()

            # Consider unhealthy if no heartbeat for 2x the interval
            max_interval = self.heartbeat_interval * 2

            if seconds_since > max_interval:
                return {
                    "status": "UNHEALTHY",
                    "message": f"Last heartbeat {seconds_since:.0f}s ago (threshold: {max_interval}s)",
                    "healthy": False,
                    "last_heartbeat": heartbeat_data["timestamp"],
                    "pid": heartbeat_data.get("pid"),
                }

            return {
                "status": "HEALTHY",
                "message": f"Last heartbeat {seconds_since:.0f}s ago",
                "healthy": True,
                "last_heartbeat": heartbeat_data["timestamp"],
                "pid": heartbeat_data.get("pid"),
                "uptime_seconds": heartbeat_data.get("uptime_seconds", 0),
            }

        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Error checking health: {e}",
                "healthy": False,
            }


def check_daemon_health(project_dir: Path) -> dict:
    """Standalone function to check daemon health.

    Args:
        project_dir: Project directory

    Returns:
        Health status dict
    """
    health_checker = DaemonHealthCheck(project_dir)
    return health_checker.check_health()
