"""Filesystem event collector using watchdog."""

import asyncio
from pathlib import Path
from typing import Any, Dict

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from dev_agents.collectors.base import BaseCollector
from dev_agents.core.event import EventBus


class FileSystemCollector(BaseCollector, FileSystemEventHandler):
    """Collects filesystem events and emits them to the event bus."""

    def __init__(self, event_bus: EventBus, config: Dict[str, Any] | None = None):
        super().__init__("filesystem", event_bus, config)

        self.watch_paths = self.config.get("watch_paths", ["."])
        self.ignore_patterns = self.config.get(
            "ignore_patterns",
            [
                "*/.git/*",
                "*/__pycache__/*",
                "*/.dev-agents/*",
                "*/node_modules/*",
                "*/.venv/*",
                "*/venv/*",
            ],
        )
        self.observer = Observer()
        self._loop = None  # Store reference to the event loop

    def should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        path_obj = Path(path)

        for pattern in self.ignore_patterns:
            # Simple pattern matching (could be improved with fnmatch)
            pattern_clean = pattern.replace("*/", "").replace("/*", "")
            if pattern_clean in str(path_obj):
                return True

        return False

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file/directory created."""
        if event.is_directory or self.should_ignore(event.src_path):
            return

        self._emit_event_sync("file:created", event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file/directory modified."""
        if event.is_directory or self.should_ignore(event.src_path):
            return

        self._emit_event_sync("file:modified", event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file/directory deleted."""
        if event.is_directory or self.should_ignore(event.src_path):
            return

        self._emit_event_sync("file:deleted", event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file/directory moved/renamed."""
        if event.is_directory or self.should_ignore(event.src_path):
            return

        self._emit_event_sync(
            "file:moved",
            event.src_path,
            {"dest_path": event.dest_path if hasattr(event, "dest_path") else None},
        )

    def _emit_event_sync(
        self, event_type: str, path: str, extra_payload: Dict[str, Any] | None = None
    ) -> None:
        """Emit a filesystem event to the event bus (synchronous version for watchdog threads)."""
        payload = {"path": path, "absolute_path": str(Path(path).absolute())}

        if extra_payload:
            payload.update(extra_payload)

        # Schedule coroutine from watchdog thread to asyncio event loop
        # This is thread-safe and handles the watchdog (threading) -> asyncio bridge
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._emit_event(event_type, payload, "normal", "filesystem"),
                self._loop,
            )

    async def start(self) -> None:
        """Start watching filesystem."""
        if self.is_running:
            return

        self._set_running(True)

        # Capture the current event loop for thread-safe event emission
        self._loop = asyncio.get_running_loop()

        # Schedule watches for all paths
        for path in self.watch_paths:
            watch_path = Path(path).absolute()
            if watch_path.exists():
                self.observer.schedule(self, str(watch_path), recursive=True)
                self.logger.info(f"Watching: {watch_path}")
            else:
                self.logger.warning(f"Path does not exist: {watch_path}")

        self.observer.start()
        self.logger.info("Filesystem collector started")

    async def stop(self) -> None:
        """Stop watching filesystem."""
        if not self.is_running:
            return

        self._set_running(False)
        self.observer.stop()
        self.observer.join()
        self.logger.info("Filesystem collector stopped")
