# project: Home Assistant Recorder Manager

## problem

Managing which entities are included in or excluded from the Home Assistant
recorder is cumbersome. The only native method requires manually editing YAML
filter blocks in `configuration.yaml`. Users who want to understand which
entities are consuming the most database space or causing the most write
operations must resort to running raw SQL queries via the SQLite Web add-on —
a workflow that is diagnostic only and offers no actionable path to controlling
future recording behaviour.

This is particularly painful on Raspberry Pi / SD-card setups, where excessive
write operations shorten the lifespan of the storage medium and inflate backup
sizes unnecessarily.

## solution

A Home Assistant add-on with an ingress-based web UI that provides:

1. **Database analytics** — a dashboard showing total database size,
   per-entity row counts (space consumed), and per-entity write frequency
   (operations over time), sortable in ascending or descending order.

2. **Visual filter editor** — a graphical interface for building recorder
   include/exclude filters using Home Assistant's native filter model:
   individual entities, entire domains, and entity glob patterns.

3. **Recorder filter files** — the add-on manages two standalone YAML
   files (`recorder_include.yaml` and `recorder_exclude.yaml`) in
   `/config/`. Each file contains only the filter definitions for its
   direction (entities, domains, entity_globs). The user adds two
   `!include` sub-keys inside their existing `recorder:` block:
   ```yaml
   recorder:
     include: !include recorder_include.yaml
     exclude: !include recorder_exclude.yaml
   ```
   All other recorder settings (`purge_keep_days`, `commit_interval`,
   etc.) remain under user control in `configuration.yaml`. The add-on
   **never** modifies `configuration.yaml` or the database directly;
   it only influences future recording behaviour.

The user installs the add-on, configures their filters visually, and applies
the generated YAML with a one-time edit to `configuration.yaml` adding the
two `!include` lines above.

## user and context

- **Primary user:** Home Assistant enthusiasts and self-hosters running HA OS
  or Supervised installations — from hobbyists to power users.
- **Key persona:** Raspberry Pi users on SD cards who need to minimise
  unnecessary database writes to extend storage lifespan.
- **Access method:** HA Ingress panel (sidebar integration). Authentication
  is handled by Home Assistant — no separate login required.
- **Experience level:** Comfortable installing community add-ons and editing
  `configuration.yaml`, but not necessarily comfortable running SQL queries.
- **Distribution:** Published as a community add-on repository on GitHub,
  shared with the Home Assistant open-source community.

## core functionality

### F1 — Database overview
- Display total database file size (bytes/MB).
- List all entities present in the `states` table.
- For each entity show: row count (space metric) and write count over a
  configurable recent period (operations metric).
- Sort ascending/descending by either metric.
- Data is read-only — obtained by querying `home-assistant_v2.db` directly
  (SQLite, mapped read-only into the container).

### F2 — Filter editor
- Visual UI to build recorder filters using HA's native model:
  - **Include:** entities, domains, entity_globs
  - **Exclude:** entities, domains, entity_globs
- The filter editor must respect HA's documented evaluation priority rules:
  1. Exact entity match (include/exclude)
  2. Glob pattern match
  3. Domain match
  4. Default fallback (include-all or exclude-all depending on config shape)
- **Filter transparency:** for every entity in the list, the UI must show
  its current recording status (included / excluded) **and** the specific
  rule causing that status. Example: if `sensor.sun*` is in exclude globs
  and `sensor.sun_today` is in include entities, then:
  - `sensor.sun_today` → ✅ included (by entity include rule)
  - `sensor.sun_tomorrow` → ❌ excluded (by glob `sensor.sun*`)
- Show entities that have zero DB rows (already fully excluded) so users
  can re-include them if desired.
- Show a live preview of which entities would be recorded vs. dropped based
  on the current filter configuration.

### F3 — Recorder filter files
- Generate two standalone YAML files containing the include/exclude filter
  definitions: `recorder_include.yaml` and `recorder_exclude.yaml`.
- Each file contains only the filter dict for its direction (entities,
  domains, entity_globs) — no wrapping key.
- The user adds two `!include` sub-keys inside their `recorder:` block:
  ```yaml
  recorder:
    include: !include recorder_include.yaml
    exclude: !include recorder_exclude.yaml
  ```
- All other recorder settings (`purge_keep_days`, `commit_interval`,
  etc.) remain under user control in `configuration.yaml`.
- Write the files to `/config/recorder_include.yaml` and
  `/config/recorder_exclude.yaml`.
- The add-on manages these files exclusively; the user never hand-edits them.

### F4 — Ingress web UI
- Single-page web interface served via HA Ingress (port 8099 by default).
- Accept connections only from 172.30.32.2 (HA Ingress proxy).
- Responsive design suitable for desktop and tablet.

### F5 — Configuration verification & restart
- After the user confirms their filter changes, the add-on:
  1. Writes the updated `recorder_filters.yaml` to `/config/`.
  2. Calls `POST http://supervisor/core/check` to validate the
     configuration. Auth via `Authorization: Bearer $SUPERVISOR_TOKEN`.
  3. If validation succeeds → calls `POST http://supervisor/core/restart`
     to apply the new filters.
  4. If validation fails → reports the error to the user and does **not**
     restart. The previous filter file is preserved (or restored).
- Requires `config.yaml` keys:
  - `hassio_api: true`
  - `hassio_role: homeassistant`
  - `homeassistant_api: true`

## out of scope

- **No `configuration.yaml` modification** — the add-on never writes to or
  reads from the user's main configuration file.
- **No database writes** — no purge, repack, or any mutation of the database.
- **No MariaDB / MySQL / PostgreSQL support** — v1 is SQLite-only. The
  architecture should allow this to be added later without a rewrite.
- **No multi-user / role-based access** — HA Ingress handles authentication.
- **No event_type filtering** — v1 focuses on entity/domain/glob filters only.

## hard constraints

| Constraint | Value |
|---|---|
| Platform | Home Assistant add-on (Supervisor managed) |
| Architectures | amd64, aarch64 (multi-arch) |
| Base image | `ghcr.io/home-assistant/base-python:3.13-alpine3.21` |
| UI delivery | HA Ingress (`ingress: true`, port 8099) |
| DB access | Read-only map of `/config/` to access `home-assistant_v2.db` |
| Generated file locations | `/config/recorder_include.yaml`, `/config/recorder_exclude.yaml` |
| Supervisor API | `hassio_api: true`, `hassio_role: homeassistant`, `homeassistant_api: true` |
| Auth | `SUPERVISOR_TOKEN` env var (auto-injected by Supervisor) |
| Security | Custom `apparmor.txt` profile; no host network; read-only mappings where possible |
| License | Open source (current repo uses MIT) |

## definition of done

A user can:
1. Install the add-on from a custom repository.
2. Open the Ingress panel and see the current database file size.
3. Sort entities in ascending or descending order by **space consumed**
   (row count) or by **write frequency** (writes per minute).
4. Configure include/exclude filters for individual entities, domains,
   and entity globs using the graphical UI.
5. See which rule is causing each entity to be included or excluded
   (filter transparency).
6. The add-on generates a valid `recorder_filters.yaml` in `/config/`.
7. The add-on verifies the configuration via the Supervisor API; if
   valid, it restarts HA Core to apply the new filters.
8. After restart, the filters take effect on future recordings.

## open questions

*All resolved during ideation — none remaining.*
