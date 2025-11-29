"""Event store for persistent event logging using SQLite."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional

from .event import Event

logger = logging.getLogger(__name__)


class EventStore:
    """SQLite-based event store for persistent event logging."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._connection: Optional[sqlite3.Connection] = None

    @property
    def connection(self) -> sqlite3.Connection:
        """Get the database connection, raising an exception if not initialized."""
        if self._connection is None:
            raise RuntimeError(
                "Database connection not initialized. Call initialize() first."
            )
        return self._connection

    async def initialize(self) -> None:
        """Initialize the event store database."""
        async with self._lock:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Use thread pool for SQLite operations since it's not async
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._init_db)

    def _init_db(self) -> None:
        """Initialize database schema (runs in thread pool)."""
        self._connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.connection.execute(
            """
        CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        timestamp REAL NOT NULL,
        source TEXT NOT NULL,
        payload TEXT NOT NULL,
        priority INTEGER NOT NULL,
        created_at REAL NOT NULL
        )
        """
        )

        # Create indexes for efficient queries
        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(type)
        """
        )
        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)
        """
        )
        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_source ON events(source)
        """
        )

        self.connection.commit()
        logger.info(f"Event store initialized at {self.db_path}")

    async def store_event(self, event: Event) -> None:
        """Store an event in the database."""
        async with self._lock:
            if not self._connection:
                logger.warning("Event store not initialized, skipping event storage")
                return

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._store_event_sync, event)

    def _store_event_sync(self, event: Event) -> None:
        """Store event synchronously (runs in thread pool)."""
        try:
            # Convert event to dict for JSON storage
            event_dict = {
                "id": event.id,
                "type": event.type,
                "timestamp": event.timestamp,
                "source": event.source,
                "payload": event.payload,
                "priority": (
                    event.priority.value
                    if hasattr(event.priority, "value")
                    else event.priority
                ),
                "created_at": datetime.now(UTC).timestamp(),
            }

            self.connection.execute(
                """
                INSERT OR REPLACE INTO events
                (id, type, timestamp, source, payload, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event_dict["id"],
                    event_dict["type"],
                    event_dict["timestamp"],
                    event_dict["source"],
                    json.dumps(event_dict["payload"]),
                    event_dict["priority"],
                    event_dict["created_at"],
                ),
            )

            self.connection.commit()

        except Exception as e:
            logger.error(f"Failed to store event {event.id}: {e}")

    async def get_events(
        self,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        since: Optional[float] = None,
    ) -> List[Event]:
        """Retrieve events from the database."""
        async with self._lock:
            if not self._connection:
                return []

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._get_events_sync, event_type, source, limit, offset, since
            )

    def _get_events_sync(
        self,
        event_type: Optional[str],
        source: Optional[str],
        limit: int,
        offset: int,
        since: Optional[float],
    ) -> List[Event]:
        """Retrieve events synchronously."""
        try:
            query = "SELECT id, type, timestamp, source, payload, priority FROM events WHERE 1=1"
            params: List[Any] = []

            if event_type:
                query += " AND type = ?"
                params.append(event_type)

            if source:
                query += " AND source = ?"
                params.append(source)

            if since:
                query += " AND timestamp >= ?"
                params.append(since)

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = self.connection.execute(query, params)
            rows = cursor.fetchall()

            events = []
            for row in rows:
                event_id, event_type, timestamp, source, payload_json, priority = row

                # Parse JSON
                payload = json.loads(payload_json)

                # Reconstruct event
                event = Event(
                    type=event_type,
                    payload=payload,
                    id=event_id,
                    timestamp=timestamp,
                    source=source,
                    priority=priority,
                )

                events.append(event)

            return events

        except Exception as e:
            logger.error(f"Failed to retrieve events: {e}")
            return []

    async def get_event_stats(self) -> Dict[str, Any]:
        """Get statistics about stored events."""
        async with self._lock:
            if not self._connection:
                return {}

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._get_event_stats_sync)

    def _get_event_stats_sync(self) -> Dict[str, Any]:
        """Get event statistics synchronously."""
        try:
            # Total events
            cursor = self.connection.execute("SELECT COUNT(*) FROM events")
            total_events = cursor.fetchone()[0]

            # Events by type
            cursor = self.connection.execute(
                """
                SELECT type, COUNT(*) as count
                FROM events
                GROUP BY type
                ORDER BY count DESC
            """
            )
            events_by_type = {row[0]: row[1] for row in cursor.fetchall()}

            # Events by source
            cursor = self.connection.execute(
                """
                SELECT source, COUNT(*) as count
                FROM events
                GROUP BY source
                ORDER BY count DESC
            """
            )
            events_by_source = {row[0]: row[1] for row in cursor.fetchall()}

            # Time range
            cursor = self.connection.execute(
                """
                SELECT MIN(timestamp), MAX(timestamp) FROM events
            """
            )
            time_range = cursor.fetchone()
            oldest_timestamp = time_range[0] if time_range[0] else None
            newest_timestamp = time_range[1] if time_range[1] else None

            return {
                "total_events": total_events,
                "events_by_type": events_by_type,
                "events_by_source": events_by_source,
                "oldest_timestamp": oldest_timestamp,
                "newest_timestamp": newest_timestamp,
                "database_size": (
                    self.db_path.stat().st_size if self.db_path.exists() else 0
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get event stats: {e}")
            return {}

    async def cleanup_old_events(self, days_to_keep: int = 30) -> int:
        """Clean up events older than specified days."""
        async with self._lock:
            if not self._connection:
                return 0

            cutoff_timestamp = datetime.now(UTC).timestamp() - (
                days_to_keep * 24 * 60 * 60
            )

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: self._cleanup_old_events_sync(cutoff_timestamp, days_to_keep),
            )

    def _cleanup_old_events_sync(
        self, cutoff_timestamp: float, days_to_keep: int
    ) -> int:
        """Clean up old events synchronously."""
        try:
            cursor = self.connection.execute(
                "DELETE FROM events WHERE timestamp < ?", (cutoff_timestamp,)
            )
            deleted_count = cursor.rowcount
            self.connection.commit()

            if deleted_count > 0:
                logger.info(
                    f"Cleaned up {deleted_count} events older than {days_to_keep} days"
                )

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")
            return 0

    async def close(self) -> None:
        """Close the database connection."""
        async with self._lock:
            if self._connection:
                self._connection.close()
                self._connection = None
                logger.info("Event store closed")


# Global instance
event_store = EventStore(Path(".devloop/events.db"))
