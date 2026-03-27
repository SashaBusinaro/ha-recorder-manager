# ADR-002: Direct SQLite read-only access for database analytics

**decision**: Query `home-assistant_v2.db` directly via Python's `sqlite3`
module in read-only mode (`?mode=ro` URI).

**rationale**: The project requires per-entity row counts and write frequency
calculations — aggregate queries that are cheap in SQLite but impractical via
the HA REST API (which returns individual states, not aggregates). The `sqlite3`
module is in the Python stdlib, adding zero dependencies. Read-only mode
(`?mode=ro`) guarantees the add-on cannot corrupt the database, even though
the filesystem mapping is rw.

**rejected alternatives**:
- HA REST API (`GET /api/history/period`): returns raw state arrays, not
  aggregates; would require client-side counting of potentially millions of
  records; extremely slow and memory-intensive.
- HA WebSocket API: same problem — no aggregate query support.
- SQLAlchemy: unnecessary abstraction layer for read-only SELECT queries;
  adds a heavy dependency.

**revisit if**: v2 adds MariaDB/PostgreSQL support. At that point, introduce
an abstract `DbReader` interface with SQLite and SQLAlchemy-based
implementations selectable by the user's `db_url` configuration.
