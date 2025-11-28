"""Filesystem event collector using watchdog."""
import asyncio
import logging
from pathlib import Path
from typing import List

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from dev_agents.core.event import Event, EventBus, Priority


class FileSystemCollector(FileSystemEventHandler):
    """Collects filesystem events and emits them to the event bus."""

    def __init__(
        self,
        event_bus: EventBus,
        watch_paths: List[str] | None = None,
        ignore_patterns: List[str] | None = None
    ):
        self.event_bus = event_bus
        self.watch_paths = watch_paths or ["."]
        self.ignore_patterns = ignore_patterns or [
            "*/.git/*",
            "*/__pycache__/*",
            "*/.claude/*",
            "*/node_modules/*",
            "*/.venv/*",
            "*/venv/*"
        ]
        self.logger = logging.getLogger("collector.filesystem")
        self.observer = Observer()
        self._running = False
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

        self._emit_event("file:created", event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file/directory modified."""
        if event.is_directory or self.should_ignore(event.src_path):
            return

        self._emit_event("file:modified", event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file/directory deleted."""
        if event.is_directory or self.should_ignore(event.src_path):
            return

        self._emit_event("file:deleted", event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file/directory moved/renamed."""
        if event.is_directory or self.should_ignore(event.src_path):
            return

        self._emit_event("file:moved", event.src_path, {
            "dest_path": event.dest_path if hasattr(event, "dest_path") else None
        })

    def _emit_event(self, event_type: str, path: str, extra_payload: dict | None = None) -> None:
        """Emit a filesystem event to the event bus."""
        payload = {
            "path": path,
            "absolute_path": str(Path(path).absolute())
        }

        if extra_payload:
            payload.update(extra_payload)

        event = Event(
            type=event_type,
            payload=payload,
            source="filesystem",
            priority=Priority.NORMAL
        )

        # Schedule coroutine from watchdog thread to asyncio event loop
        # This is thread-safe and handles the watchdog (threading) -> asyncio bridge
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.event_bus.emit(event), self._loop)

    async def start(self) -> None:
        """Start watching filesystem."""
        if self._running:
            return

        self._running = True

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
        if not self._running:
            return

        self._running = False
        self.observer.stop()
        self.observer.join()
        self.logger.info("Filesystem collector stopped")
