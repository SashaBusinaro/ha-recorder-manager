"""Read-only SQLite access to the Home Assistant recorder database."""

import os
import time
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
                # Modern schema: states + states_meta + state_attributes
                cursor.execute("""
                    SELECT sm.entity_id,
                           COUNT(s.state_id) AS row_count,
                           SUM(LENGTH(sa.shared_attrs)) AS size_bytes
                    FROM states s
                    JOIN states_meta sm ON s.metadata_id = sm.metadata_id
                    LEFT JOIN state_attributes sa ON s.attributes_id = sa.attributes_id
                    GROUP BY sm.entity_id
                """)
            else:
                # Legacy schema: entity_id and attributes directly in states
                cursor.execute("""
                    SELECT entity_id,
                           COUNT(*) AS row_count,
                           SUM(LENGTH(attributes)) AS size_bytes
                    FROM states
                    GROUP BY entity_id
                """)

            for row in cursor.fetchall():
                entity_id = row["entity_id"]
                row_count = row["row_count"]
                size_bytes = row["size_bytes"] or 0

                stats[entity_id] = {
                    "row_count": row_count,
                    "writes_per_minute": 0.0,
                    "size_bytes": size_bytes,
                }

            # Calculate actual writes per minute from the last 60 seconds
            if has_states_meta:
                one_minute_ago = time.time() - 60
                cursor.execute("""
                    SELECT sm.entity_id,
                           COUNT(s.state_id) as changes_last_minute
                    FROM states s
                    JOIN states_meta sm ON s.metadata_id = sm.metadata_id
                    WHERE s.last_updated_ts >= ?
                    GROUP BY sm.entity_id
                """, (one_minute_ago,))
                
                for row in cursor.fetchall():
                    entity_id = row["entity_id"]
                    changes = row["changes_last_minute"]
                    if entity_id in stats:
                        stats[entity_id]["writes_per_minute"] = float(changes)

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

        file_size_mb = round(float(file_size) / 1048576.0, 2)

        return {
            "file_size_bytes": file_size,
            "file_size_mb": file_size_mb,
            "total_rows": total_rows,
            "entity_count": entity_count,
            "entities": [
                {
                    "entity_id": eid,
                    "size_bytes": s.get("size_bytes", 0),
                    "writes_per_minute": round(s["writes_per_minute"], 4),
                }
                for eid, s in sorted(
                    stats.items(),
                    key=lambda x: x[1].get("size_bytes", 0),
                    reverse=True,
                )
            ],
        }

    async def get_entity_stats(self) -> dict:
        """Get per-entity statistics as a dict keyed by entity_id."""
        return await asyncio.to_thread(self._query_entity_stats)
