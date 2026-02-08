"""MCP subscriptions for DevLoop.

This module provides subscription support for MCP resources, enabling real-time
updates when findings or status change.

The ResourceWatcher monitors .devloop/context/.last_update for changes and
notifies subscribers when updates occur.
"""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


class ResourceWatcher:
    """Watches for changes to DevLoop resources.

    Monitors the .last_update file in the context directory to detect when
    findings have been updated. Uses polling with a configurable interval.
    """

    def __init__(self, devloop_dir: Path, check_interval: float = 2.0):
        """Initialize the resource watcher.

        Args:
            devloop_dir: Path to the .devloop directory
            check_interval: How often to check for changes (in seconds)
        """
        self.devloop_dir = devloop_dir
        self.check_interval = check_interval
        self.last_mtime: Optional[float] = None
        self._running = False

    async def start(
        self, on_change_callback: Callable[[], Coroutine[Any, Any, None]]
    ) -> None:
        """Start watching for changes.

        Args:
            on_change_callback: Async function to call when changes are detected
        """
        self._running = True
        last_update_file = self.devloop_dir / "context" / ".last_update"

        while self._running:
            try:
                if last_update_file.exists():
                    mtime = last_update_file.stat().st_mtime
                    if self.last_mtime is not None and mtime > self.last_mtime:
                        logger.debug("Detected change in .last_update file")
                        await on_change_callback()
                    self.last_mtime = mtime
            except Exception as e:
                logger.warning(f"Error checking for changes: {e}")

            await asyncio.sleep(self.check_interval)

    def stop(self) -> None:
        """Stop watching for changes."""
        self._running = False


class SubscriptionManager:
    """Manages subscriptions to DevLoop resources.

    Handles subscribing, unsubscribing, and notifying subscribers when
    resources change.
    """

    def __init__(self, devloop_dir: Path, check_interval: float = 2.0):
        """Initialize the subscription manager.

        Args:
            devloop_dir: Path to the .devloop directory
            check_interval: How often to check for changes (in seconds)
        """
        self.devloop_dir = devloop_dir
        self.check_interval = check_interval
        self._subscribers: Dict[str, Dict[str, Callable]] = {}
        self._watcher: Optional[ResourceWatcher] = None
        self._watcher_task: Optional[asyncio.Task] = None

    async def subscribe(
        self,
        resource_uri: str,
        callback: Callable[[str], Coroutine[Any, Any, None]],
    ) -> str:
        """Subscribe to changes for a resource.

        Args:
            resource_uri: The resource URI to subscribe to
            callback: Async function to call with the resource URI when it changes

        Returns:
            A subscription ID that can be used to unsubscribe
        """
        subscription_id = str(uuid.uuid4())

        if resource_uri not in self._subscribers:
            self._subscribers[resource_uri] = {}

        self._subscribers[resource_uri][subscription_id] = callback
        logger.debug(f"Subscribed {subscription_id} to {resource_uri}")

        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from resource changes.

        Args:
            subscription_id: The subscription ID returned from subscribe()

        Returns:
            True if the subscription was found and removed, False otherwise
        """
        for resource_uri, subscribers in self._subscribers.items():
            if subscription_id in subscribers:
                del subscribers[subscription_id]
                logger.debug(f"Unsubscribed {subscription_id} from {resource_uri}")
                # Clean up empty subscription lists
                if not subscribers:
                    del self._subscribers[resource_uri]
                return True
        return False

    async def notify(self, resource_uri: str) -> None:
        """Notify all subscribers of a resource change.

        Args:
            resource_uri: The resource URI that changed
        """
        subscribers = self._subscribers.get(resource_uri, {})
        for subscription_id, callback in subscribers.items():
            try:
                await callback(resource_uri)
            except Exception as e:
                logger.warning(
                    f"Error notifying subscriber {subscription_id} for {resource_uri}: {e}"
                )

    async def _on_change(self) -> None:
        """Called when the watcher detects a change."""
        # Notify all findings resources
        findings_uris = [
            "devloop://findings/immediate",
            "devloop://findings/relevant",
            "devloop://findings/background",
            "devloop://findings/summary",
        ]
        for uri in findings_uris:
            await self.notify(uri)

    async def start(self) -> None:
        """Start the subscription manager and watcher."""
        if self._watcher is not None:
            return  # Already started

        self._watcher = ResourceWatcher(self.devloop_dir, self.check_interval)
        self._watcher_task = asyncio.create_task(self._watcher.start(self._on_change))
        logger.info("Subscription manager started")

    async def stop(self) -> None:
        """Stop the subscription manager and watcher."""
        if self._watcher is not None:
            self._watcher.stop()
            self._watcher = None

        if self._watcher_task is not None:
            try:
                await asyncio.wait_for(self._watcher_task, timeout=1.0)
            except asyncio.TimeoutError:
                self._watcher_task.cancel()
            self._watcher_task = None

        logger.info("Subscription manager stopped")

    def get_subscribed_resources(self) -> List[str]:
        """Get a list of resources that have active subscriptions.

        Returns:
            List of resource URIs with active subscriptions
        """
        return list(self._subscribers.keys())
