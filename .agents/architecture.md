# Architecture: Home Assistant Recorder Manager

## Overview

Single-process Python web application running inside a Home Assistant add-on
container. Serves an ingress-compatible web UI for database analytics and
recorder filter management.

```
┌──────────────────────────────────────────────────────────────┐
│                    HA Supervisor Container                    │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Python Process (aiohttp)                  │  │
│  │                                                        │  │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────────────┐    │  │
│  │  │ REST API │  │  Static  │  │  Filter Engine    │    │  │
│  │  │ routes   │  │  files   │  │  (HA eval rules)  │    │  │
│  │  └────┬─────┘  └──────────┘  └───────┬───────────┘    │  │
│  │       │                              │                │  │
│  │  ┌────▼──────────────┐  ┌────────────▼────────────┐   │  │
│  │  │  DB Reader        │  │  YAML Writer            │   │  │
│  │  │  (SQLite, r/o)    │  │  (recorder_filters.yaml)│   │  │
│  │  └────┬──────────────┘  └────────────┬────────────┘   │  │
│  │       │                              │                │  │
│  └───────┼──────────────────────────────┼────────────────┘  │
│          │                              │                    │
│    ┌─────▼────────┐             ┌───────▼──────────┐        │
│    │ /config/     │             │ /config/          │        │
│    │ home-        │ (read-only) │ recorder_filters  │(write) │
│    │ assistant_   │             │ .yaml             │        │
│    │ v2.db        │             │                   │        │
│    └──────────────┘             └───────────────────┘        │
│                                                              │
│    ┌───────────────────────────────────────────┐             │
│    │ Supervisor API (http://supervisor/)       │             │
│    │  POST /core/check                        │             │
│    │  POST /core/restart                      │             │
│    │  GET  /core/api/states                   │             │
│    └───────────────────────────────────────────┘             │
└──────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.14 | Base image provides it; ecosystem has sqlite3, aiohttp, PyYAML |
| Base image | `ghcr.io/home-assistant/base-python:3.14-alpine3.23` | Latest HA Python image; Alpine for IoT-friendly footprint |
| Web framework | aiohttp | Lightweight async HTTP server; no heavy deps; supports ingress path rewriting natively |
| Database access | Python `sqlite3` stdlib | Zero additional deps; read-only connection with `?mode=ro` URI |
| YAML generation | PyYAML | Standard Python YAML library; generates valid HA-compatible YAML |
| Frontend | Vanilla HTML/CSS/JS (SPA) | No build step; served as static files; ingress-compatible |
| Process manager | S6-overlay (from base image) | Standard HA add-on process supervision |

## Directory Structure (Add-on Source)

```
recorder-manager/                     ← add-on folder (replaces example/)
├── config.yaml                       ← add-on manifest
├── Dockerfile
├── build.yaml
├── apparmor.txt
├── CHANGELOG.md
├── DOCS.md
├── README.md
├── icon.png
├── logo.png
├── translations/
│   └── en.yaml
└── rootfs/
    └── usr/
        └── src/
            └── app/
                ├── server.py          ← aiohttp entry point
                ├── db_reader.py       ← SQLite read-only queries
                ├── entity_resolver.py ← HA API entity discovery
                ├── filter_engine.py   ← HA filter eval logic
                ├── yaml_writer.py     ← YAML fragment generator
                ├── supervisor_api.py  ← config check + restart
                └── static/
                    ├── index.html
                    ├── app.js
                    └── style.css
```

## Component Design

### C1 — Web Server (`server.py`)

- **Framework:** aiohttp
- **Bind:** `0.0.0.0:8099` (ingress default port)
- **Ingress path handling:** Read `X-Ingress-Path` header from each request;
  inject as `base_path` into HTML template so all asset/API URLs are relative
  to the ingress prefix.
- **IP restriction:** Middleware checks `request.remote == "172.30.32.2"`,
  returns 403 otherwise.
- **Routes:**

| Method | Path | Description |
|---|---|---|
| GET | `/` | Serve `index.html` with injected `base_path` |
| GET | `/static/*` | Serve static assets (JS, CSS) |
| GET | `/api/db/overview` | DB file size + entity stats |
| GET | `/api/entities` | All HA entities (from API + DB merge) |
| GET | `/api/filters` | Current filter config (read from YAML) |
| POST | `/api/filters` | Save new filter config → write YAML |
| POST | `/api/filters/preview` | Dry-run: evaluate filters, return per-entity status |
| POST | `/api/apply` | Write YAML + config check + restart |

### C2 — DB Reader (`db_reader.py`)

- Opens `home-assistant_v2.db` in **read-only** mode via URI:
  `sqlite3.connect("file:/config/home-assistant_v2.db?mode=ro", uri=True)`
- **Queries (modern normalized schema):**

  **Row count per entity (space metric):**
  ```sql
  SELECT sm.entity_id, COUNT(*) AS row_count
  FROM states s
  JOIN states_meta sm ON s.metadata_id = sm.metadata_id
  GROUP BY sm.entity_id
  ORDER BY row_count DESC;
  ```

  **Writes per minute (operations metric):**
  ```sql
  SELECT sm.entity_id,
         COUNT(*) / ((MAX(s.last_updated_ts) - MIN(s.last_updated_ts)) / 60.0)
           AS writes_per_minute
  FROM states s
  JOIN states_meta sm ON s.metadata_id = sm.metadata_id
  GROUP BY sm.entity_id
  HAVING COUNT(*) > 1
  ORDER BY writes_per_minute DESC;
  ```

  **Database file size:**
  ```python
  os.path.getsize("/config/home-assistant_v2.db")
  ```

- All queries run on a background thread (via `asyncio.to_thread`) to avoid
  blocking the event loop.

### C3 — Entity Resolver (`entity_resolver.py`)

- Calls `GET http://supervisor/core/api/states` with
  `Authorization: Bearer $SUPERVISOR_TOKEN` header.
- Extracts `entity_id` from every state object → set of all live entities.
- Merges with DB entities to produce a unified list including:
  - Entities that exist in HA but have zero DB rows (already excluded)
  - Entities that exist in DB but may no longer be in HA (stale)
- Extracts domain from `entity_id` (everything before first `.`).

### C4 — Filter Engine (`filter_engine.py`)

Implements HA's documented filter evaluation priority exactly:

```python
def evaluate(entity_id, include, exclude) -> (status, reason):
    """
    Returns ("included"|"excluded", "reason string")

    Evaluation order depends on which filter categories are present:

    Case 1: No filters → all included
    Case 2: Only includes → entity/glob/domain include, else exclude
    Case 3: Only excludes → entity/glob/domain exclude, else include
    Case 4: Domain/glob includes + any excludes →
            entity include > entity exclude > glob include >
            glob exclude > domain include > default exclude
    Case 5: Domain/glob excludes only (no domain/glob includes) →
            entity include > entity exclude > glob exclude >
            domain exclude > default include
    Case 6: Entity-level only → entity include, else exclude
    """
```

- Glob matching uses `fnmatch.fnmatch` (same as HA internally).
- Returns both the status AND the rule that caused it (e.g.,
  `("excluded", "glob exclude: sensor.sun*")`).

### C5 — YAML Writer (`yaml_writer.py`)

- Generates YAML fragment with only `include:` and `exclude:` sub-keys.
- Output example:
  ```yaml
  include:
    entities:
      - sensor.sun_today
  exclude:
    entity_globs:
      - sensor.sun*
  ```
- Writes to `/config/recorder_filters.yaml`.
- Before overwriting, backs up the current file to
  `/config/recorder_filters.yaml.bak` for rollback.

### C6 — Supervisor API Client (`supervisor_api.py`)

- **Config check:** `POST http://supervisor/core/check`
  - Auth: `Authorization: Bearer $SUPERVISOR_TOKEN`
  - Returns success/failure with error details.
- **Restart:** `POST http://supervisor/core/restart`
  - Only called after successful config check.
- **Entity states:** `GET http://supervisor/core/api/states`
  - Used by Entity Resolver.
- Uses `aiohttp.ClientSession` for all HTTP calls.

## Data Flow

### Filter Apply Workflow

```
User clicks "Apply Filters"
        │
        ▼
┌─────────────────────┐
│ POST /api/apply      │
│ 1. Backup current    │
│    YAML file         │
│ 2. Write new YAML    │
│ 3. POST /core/check  │──── Fail ──► Restore backup,
│                      │              return error to UI
│ 4. POST /core/restart│
│ 5. Return success    │
└─────────────────────┘
```

### Entity List Assembly

```
GET /api/entities
        │
        ├──► DB Reader: entities + row_count + writes/min
        │
        ├──► Entity Resolver: all live HA entities
        │
        ├──► Merge: unified list
        │    - present in both = active entity with stats
        │    - in HA only = excluded entity (0 rows)
        │    - in DB only = stale entity (flagged)
        │
        ├──► Filter Engine: evaluate current filters for each
        │    - status: included / excluded
        │    - reason: "entity include", "glob exclude: sensor.sun*", etc.
        │
        └──► Return JSON response
```

## Add-on Configuration (`config.yaml`)

```yaml
name: Recorder Manager
version: "0.1.0"
slug: recorder-manager
description: >-
  Visual database analytics and recorder filter manager.
  See which entities consume the most space and writes,
  then build include/exclude filters with a click.
url: "https://github.com/SashaBusinaro/Home-Assistant-Recorder-Manager"
arch:
  - aarch64
  - amd64
startup: application
boot: auto
ingress: true
ingress_port: 8099
panel_icon: mdi:database-cog
panel_title: Recorder Manager
panel_admin: true
hassio_api: true
hassio_role: homeassistant
homeassistant_api: true
map:
  - homeassistant_config:rw
init: false
options: {}
schema: {}
```

### Key configuration choices:
- **`map: homeassistant_config:rw`** — maps `/config/` (HA config dir) into
  the container. Read-write is needed because the add-on writes
  `recorder_filters.yaml` there. The DB file is read-only at the
  application level (opened with `?mode=ro`).
- **`hassio_role: homeassistant`** — grants access to `/core/check` and
  `/core/restart` Supervisor endpoints.
- **`ingress: true`** — enables HA sidebar integration.
- **`startup: application`** — starts after HA Core is up (needed for API access).
- **`init: false`** — we use S6-overlay from the base image directly.

## Security Considerations

- **DB read-only at app level:** SQLite opened with `?mode=ro` URI param;
  even though the filesystem map is rw, the application cannot write to the DB.
- **No host network:** Add-on uses the default Docker network.
- **Custom AppArmor profile:** Restricts filesystem access to only required paths.
- **Ingress-only access:** Web server rejects connections not from 172.30.32.2.
- **SUPERVISOR_TOKEN:** Never exposed to the frontend; all Supervisor API
  calls happen server-side only.

## Future Extensibility

- **Multi-DB support:** `db_reader.py` is the only component that touches
  SQLite. To add MariaDB/PostgreSQL, create alternative reader implementations
  with the same interface and select based on the user's `db_url` config.
- **Event type filtering:** The filter engine can be extended with an
  `event_types` key in the exclude config without changing the architecture.
