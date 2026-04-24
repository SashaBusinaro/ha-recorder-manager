# Changelog

## [1.1.0] - 2026-04-25

### Added
- **Entity limit selector**: Toolbar dropdown ("Top 25 / 100 / 250 / 500 / All") limits
  the number of entities fetched from the server. The default is **Top 100**, which
  dramatically speeds up initial load on large HA installations. Entities are
  sorted by database size descending before slicing, so the most impactful
  entities always appear first.

### Changed
- **Writes/min metric**: Replaced the 60-second sliding window (which showed
  `0.00` for most entities at page-load time) with a lifetime average computed
  across the entity's full history in the database. The value is now stable and
  meaningful even immediately after startup.
- **Size column tooltip**: The "Size" column header now shows a tooltip
  explaining that the value is an estimated/proportional metric due to Home
  Assistant's shared attribute deduplication, not exact on-disk bytes.

### Fixed
- `GET /api/entities`: `total` field in the response now reflects the full
  entity count before the limit is applied (was incorrectly returning the
  sliced count).
- `POST /api/filters` and `POST /api/apply`: Added input validation — malformed
  payloads (wrong types for entities/domains/entity_globs) now return HTTP 400
  instead of crashing the YAML writer.
- SQLite connection is now always closed via `try/finally`, preventing a
  resource leak when a query raised an exception.
- Filter YAML writes are now atomic: content is written to a `.tmp` file and
  renamed in place (`os.replace`), preventing partially written files on crash.
- `asyncio.create_task` result from the reboot handler is now held in a strong
  reference set, preventing premature garbage collection before the task
  completes.
- Domain filter dropdown now XSS-escapes domain names.
- `formatNumber` and `formatBytes` in the UI are now guarded against
  `null`/`undefined` values from unexpected server responses.

## [1.0.0] - 2026-04-23

### Added
- **Setup Wizard**: Unified wizard handling both first-time setup and migration
  from existing inline `recorder:` filter blocks; appears as a dismissible
  notification banner on every page load until setup is complete
- **Migration Wizard**: Detects existing inline `include:`/`exclude:` sub-keys
  inside the `recorder:` block, automatically copies the filter definitions to
  `recorder_include.yaml` and `recorder_exclude.yaml`, then guides the user
  through replacing those sub-keys with `!include` pointers
- **Fresh-Setup Wizard**: For users with no existing `include:`/`exclude:`
  filter blocks; creates both managed files and shows the two-line snippet the
  user must add to their `recorder:` block
- **Config check & reboot flow**: Client-orchestrated — validate first, show
  result, then trigger reboot on success so users see confirmation before the
  add-on becomes temporarily unresponsive
- New API endpoints: `GET /api/setup/status`, `POST /api/setup/check`,
  `POST /api/setup/reboot`, `POST /api/setup/init-default`,
  `POST /api/migration/apply`
- New backend module `config_reader.py` for safe regex-based parsing of
  `configuration.yaml` (handles HA-specific `!include` tags that PyYAML cannot
  parse)

### Changed
- **Architecture**: The add-on now manages only the filter sub-key files
  (`recorder_include.yaml` and `recorder_exclude.yaml`), not the entire
  `recorder:` block. Users retain full control of all other recorder settings
  (`purge_keep_days`, `db_url`, `commit_interval`, etc.) in
  `configuration.yaml`.
- Setup requires adding two lines inside an existing `recorder:` block instead
  of replacing the entire block with a single `!include` directive
- Updated `DOCS.md` to document both migration and fresh-setup flows, banner
  behaviour, and the new two-file setup syntax

### Fixed
- **File encoding**: all file opens now explicitly use `encoding="utf-8"`
  (`server.py`, `yaml_writer.py`)
- **Refresh button**: `refresh()` uses `try/finally` so the button is always
  re-enabled, even when a sub-load throws
- **Migration wizard**: copy-error state shows a dynamically inserted Close
  button so the user is not permanently stuck in the wizard
- **Apply confirmation**: success toast falls back to a safe default message if
  the server response body is absent or unexpected

## [0.1.2] - 2026-03-28

### Changed
- Chore: removed redundant configuration keys to follow linter best practices.

## [0.1.1] - 2026-03-27

### Changed
- Replaced row count metric with actual database space occupied (bytes)
- Replaced average `writes_per_minute` metric with a live sliding window
  capturing changes in the last 60 seconds
- Improved filter tag UX to automatically add typed text when clicking
  elsewhere on the page
- Downgraded base image to Python 3.13 (alpine3.21) to fix `aiohttp` builder
  issues instead of using `gcc` dependencies

## [0.1.0] - 2026-03-20

### Added
- Database overview dashboard (file size, total rows, entity count)
- Per-entity row count and writes-per-minute metrics
- Sortable entity table with search and domain/status filtering
- Visual filter editor with tag-based input for entities, domains, and globs
- Filter transparency showing which rule causes each entity's status
- Live filter preview
- YAML filter file generator (`recorder_include.yaml` / `recorder_exclude.yaml`)
- Configuration validation via Supervisor API before restart
- Automatic HA Core restart after successful validation
- Dark mode UI with responsive layout
