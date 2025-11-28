"""System event collector using psutil for resource monitoring."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None

from devloop.collectors.base import BaseCollector


class SystemCollector(BaseCollector):
    """Collects system-related events like resource usage and idle time."""

    def __init__(
        self,
        event_bus: Any,  # EventBus type (avoiding circular import)
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__("system", event_bus, config)

        if not HAS_PSUTIL:
            self.logger.warning("psutil not available - system monitoring disabled")
            self._psutil_available = False
        else:
            self._psutil_available = True

        # Configuration
        self.check_interval = self.config.get("check_interval", 30)  # seconds
        self.cpu_threshold = self.config.get("cpu_threshold", 80)  # percent
        self.memory_threshold = self.config.get("memory_threshold", 85)  # percent
        self.idle_threshold = self.config.get("idle_threshold", 300)  # seconds

        # State tracking
        self._last_cpu_percent = 0
        self._last_memory_percent = 0
        self._last_idle_time = time.time()
        self._is_idle = False
        self._monitoring_task: Optional[asyncio.Task] = None

    def _get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics."""
        if not self._psutil_available:
            return {}

        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_used": psutil.virtual_memory().used,
                "memory_total": psutil.virtual_memory().total,
                "disk_usage": psutil.disk_usage("/").percent,
                "load_average": (
                    psutil.getloadavg() if hasattr(psutil, "getloadavg") else None
                ),
                "timestamp": time.time(),
            }
        except Exception as e:
            self.logger.error(f"Error getting system stats: {e}")
            return {}

    async def _check_system_resources(self) -> None:
        """Check system resources and emit events if thresholds are exceeded."""
        if not self._psutil_available:
            return

        stats = self._get_system_stats()
        if not stats:
            return

        # Check CPU usage
        cpu_percent = stats["cpu_percent"]
        if (
            cpu_percent > self.cpu_threshold
            and self._last_cpu_percent <= self.cpu_threshold
        ):
            await self._emit_event(
                "system:high_cpu",
                {
                    "cpu_percent": cpu_percent,
                    "threshold": self.cpu_threshold,
                    "timestamp": stats["timestamp"],
                },
                "high",
                "system",
            )

        self._last_cpu_percent = cpu_percent

        # Check memory usage
        memory_percent = stats["memory_percent"]
        if (
            memory_percent > self.memory_threshold
            and self._last_memory_percent <= self.memory_threshold
        ):
            await self._emit_event(
                "system:low_memory",
                {
                    "memory_percent": memory_percent,
                    "memory_used": stats["memory_used"],
                    "memory_total": stats["memory_total"],
                    "threshold": self.memory_threshold,
                    "timestamp": stats["timestamp"],
                },
                "critical",
                "system",
            )

        self._last_memory_percent = memory_percent

        # Check idle time (simplified - in a real implementation you'd use more sophisticated idle detection)
        current_time = time.time()
        # For demo purposes, consider system idle if no significant CPU usage for a period
        if cpu_percent < 5:  # Very low CPU usage
            if not self._is_idle:
                idle_duration = current_time - self._last_idle_time
                if idle_duration > self.idle_threshold:
                    await self._emit_event(
                        "system:idle",
                        {"idle_duration": idle_duration, "timestamp": current_time},
                        "normal",
                        "system",
                    )
                    self._is_idle = True
        else:
            if self._is_idle:
                await self._emit_event(
                    "system:active", {"timestamp": current_time}, "normal", "system"
                )
                self._is_idle = False
            self._last_idle_time = current_time

    async def _monitor_system(self) -> None:
        """Main monitoring loop."""
        self.logger.info(
            f"Starting system monitoring (interval: {self.check_interval}s)"
        )

        while self.is_running:
            try:
                await self._check_system_resources()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"Error in system monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)

    async def start(self) -> None:
        """Start the system collector."""
        if self.is_running:
            return

        if not self._psutil_available:
            self.logger.error("Cannot start system collector - psutil not available")
            return

        self._set_running(True)

        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitor_system())

        # Emit initial system status
        stats = self._get_system_stats()
        if stats:
            await self._emit_event("system:status", stats, "normal", "system")

        self.logger.info("System collector started")

    async def stop(self) -> None:
        """Stop the system collector."""
        if not self.is_running:
            return

        self._set_running(False)

        # Cancel monitoring task
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        self.logger.info("System collector stopped")

    async def emit_system_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Manually emit a system event (for testing or external triggers)."""
        await self._emit_event(f"system:{event_type}", payload, "normal", "system")
