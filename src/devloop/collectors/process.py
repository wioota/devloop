"""Process event collector using psutil monitoring."""

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


class ProcessCollector(BaseCollector):
    """Collects process-related events like script completion and build events."""

    def __init__(
        self,
        event_bus: Any,  # EventBus type (avoiding circular import)
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__("process", event_bus, config)

        if not HAS_PSUTIL:
            self.logger.warning("psutil not available - process monitoring disabled")
            self._psutil_available = False
        else:
            self._psutil_available = True

        self.monitored_processes: Dict[int, Dict[str, Any]] = {}
        self.monitoring_patterns = self.config.get(
            "patterns",
            [
                "pytest",
                "python",
                "node",
                "npm",
                "yarn",
                "make",
                "gradle",
                "maven",
                "cargo",
                "go",
                "rustc",
            ],
        )
        self._monitoring_task: Optional[asyncio.Task] = None

    def _should_monitor_process(self, process: Any) -> bool:
        """Check if a process should be monitored."""
        if not self._psutil_available:
            return False

        try:
            cmdline = process.cmdline()
            process_name = process.name().lower()

            # Check if process name matches any pattern
            for pattern in self.monitoring_patterns:
                if pattern.lower() in process_name:
                    return True

            # Check command line for build/dev scripts
            cmdline_str = " ".join(cmdline).lower()
            if any(
                script in cmdline_str
                for script in ["test", "build", "lint", "format", "check", "run"]
            ):
                return True

        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass

        return False

    async def _monitor_processes(self) -> None:
        """Monitor running processes and track their completion."""
        if not self._psutil_available:
            return

        while self.is_running:
            try:
                # Get current processes
                current_pids = set()

                for process in psutil.process_iter(
                    ["pid", "name", "cmdline", "create_time"]
                ):
                    try:
                        pid = process.info["pid"]
                        current_pids.add(pid)

                        # Check if we should monitor this process
                        if self._should_monitor_process(process):
                            if pid not in self.monitored_processes:
                                # New process to monitor
                                self.monitored_processes[pid] = {
                                    "info": process.info,
                                    "start_time": process.info.get(
                                        "create_time", time.time()
                                    ),
                                }
                                self.logger.debug(
                                    f"Started monitoring process {pid}: {process.info['name']}"
                                )

                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        continue

                # Check for completed processes
                completed_pids = []
                for pid, process_data in self.monitored_processes.items():
                    if pid not in current_pids:
                        # Process completed
                        completed_pids.append(pid)
                        await self._handle_process_completion(pid, process_data)

                # Remove completed processes
                for pid in completed_pids:
                    del self.monitored_processes[pid]

            except Exception as e:
                self.logger.error(f"Error monitoring processes: {e}")

            await asyncio.sleep(1.0)  # Check every second

    async def _handle_process_completion(
        self, pid: int, process_data: Dict[str, Any]
    ) -> None:
        """Handle process completion event."""
        try:
            info = process_data["info"]
            start_time = process_data["start_time"]
            duration = time.time() - start_time

            # Determine event type based on process
            event_type = "process:completed"
            process_name = info.get("name", "unknown")

            # Categorize the process
            if any(term in process_name.lower() for term in ["pytest", "test"]):
                event_type = "test:completed"
            elif any(
                term in process_name.lower()
                for term in ["lint", "flake8", "ruff", "eslint"]
            ):
                event_type = "lint:completed"
            elif any(
                term in process_name.lower() for term in ["format", "black", "prettier"]
            ):
                event_type = "format:completed"
            elif any(
                term in process_name.lower()
                for term in ["build", "make", "gradle", "maven", "cargo"]
            ):
                event_type = "build:completed"

            payload = {
                "pid": pid,
                "name": process_name,
                "cmdline": info.get("cmdline", []),
                "duration": duration,
                "start_time": start_time,
                "end_time": time.time(),
            }

            await self._emit_event(event_type, payload, "normal", "process")
            self.logger.info(
                f"Process completed: {process_name} (PID: {pid}, duration: {duration:.2f}s)"
            )

        except Exception as e:
            self.logger.error(f"Error handling process completion for PID {pid}: {e}")

    async def start(self) -> None:
        """Start the process collector."""
        if self.is_running:
            return

        if not self._psutil_available:
            self.logger.error("Cannot start process collector - psutil not available")
            return

        self._set_running(True)

        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitor_processes())

        self.logger.info("Process collector started")

    async def stop(self) -> None:
        """Stop the process collector."""
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

        # Clear monitored processes
        self.monitored_processes.clear()

        self.logger.info("Process collector stopped")

    async def emit_process_event(
        self, event_type: str, payload: Dict[str, Any]
    ) -> None:
        """Manually emit a process event (for testing or external triggers)."""
        await self._emit_event(f"process:{event_type}", payload, "normal", "process")
