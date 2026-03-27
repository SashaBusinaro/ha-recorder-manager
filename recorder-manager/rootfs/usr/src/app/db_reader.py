"""Read-only SQLite access to the Home Assistant recorder database."""

import os
import sqlite3
import asyncio
import logging

logger = logging.getLogger("recorder-manager.db")


class DbReader:
    """Read-only interface to home-assistant_v2.db."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        """Open a read-only connection to the database."""
        uri = f"file:{self.db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_file_size(self) -> int:
        """Return the database file size in bytes."""
        try:
            return os.path.getsize(self.db_path)
        except OSError:
            return 0

    def _query_entity_stats(self) -> dict:
        """Query per-entity row counts and writes per minute."""
        stats = {}
        try:
            conn = self._connect()
            cursor = conn.cursor()

            # Check if we have the modern normalized schema (states_meta)
            cursor.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='states_meta'"
            )
            has_states_meta = cursor.fetchone() is not None

            if has_states_meta:
                # Modern schema: states + states_meta
                # Row count per entity
                cursor.execute("""
                    SELECT sm.entity_id,
                           COUNT(*) AS row_count,
                           MIN(s.last_updated_ts) AS min_ts,
                           MAX(s.last_updated_ts) AS max_ts
                    FROM states s
                    JOIN states_meta sm ON s.metadata_id = sm.metadata_id
                    GROUP BY sm.entity_id
                """)
            else:
                # Legacy schema: entity_id directly in states
                cursor.execute("""
                    SELECT entity_id,
                           COUNT(*) AS row_count,
                           MIN(last_updated) AS min_ts,
                           MAX(last_updated) AS max_ts
                    FROM states
                    GROUP BY entity_id
                """)

            for row in cursor.fetchall():
                entity_id = row["entity_id"]
                row_count = row["row_count"]
                min_ts = row["min_ts"]
                max_ts = row["max_ts"]

                # Calculate writes per minute
                writes_per_minute = 0.0
                if (
                    min_ts is not None
                    and max_ts is not None
                    and row_count > 1
                ):
                    # Timestamps are Unix epoch floats in modern schema
                    try:
                        time_span_minutes = (
                            float(max_ts) - float(min_ts)
                        ) / 60.0
                        if time_span_minutes > 0:
                            writes_per_minute = (
                                row_count / time_span_minutes
                            )
                    except (ValueError, TypeError):
                        writes_per_minute = 0.0

                stats[entity_id] = {
                    "row_count": row_count,
                    "writes_per_minute": writes_per_minute,
                }

            conn.close()
        except Exception as e:
            logger.error("Failed to query entity stats: %s", e)

        return stats

    async def get_overview(self) -> dict:
        """Get database overview: file size and entity stats."""
        file_size = self._get_file_size()
        stats = await asyncio.to_thread(self._query_entity_stats)

        total_rows = sum(s["row_count"] for s in stats.values())
        entity_count = len(stats)

        # Format file size
        file_size_mb = round(file_size / (1024 * 1024), 2)

        return {
            "file_size_bytes": file_size,
            "file_size_mb": file_size_mb,
            "total_rows": total_rows,
            "entity_count": entity_count,
            "entities": [
                {
                    "entity_id": eid,
                    "row_count": s["row_count"],
                    "writes_per_minute": round(s["writes_per_minute"], 4),
                }
                for eid, s in sorted(
                    stats.items(),
                    key=lambda x: x[1]["row_count"],
                    reverse=True,
                )
            ],
        }

    async def get_entity_stats(self) -> dict:
        """Get per-entity statistics as a dict keyed by entity_id."""
        return await asyncio.to_thread(self._query_entity_stats)
