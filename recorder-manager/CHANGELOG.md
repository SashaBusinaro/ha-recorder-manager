# Changelog

## [1.2.0] - 2026-04-27

### Added
- **Light/dark/auto theme toggle**: Toolbar button cycles through Light, Dark, and Auto (system) themes. Preference is persisted in `localStorage`. Auto mode follows the OS color scheme via `prefers-color-scheme`.
- **Entity display count**: Toolbar now shows "N of M" entities after filtering, giving immediate feedback on how many entities match the current search/domain/status filter.
- **Clear filter button**: Each entity row now shows a "Clear" action button when the entity is already in an include or exclude rule, allowing one-click removal from the rule without opening the filter panel.
- **Improved empty states**: Contextual empty-state messages explain why the table is empty (e.g., no results for a search term, no entities in a domain, no included/excluded entities).
- **Rule chip**: The "Reason" column is replaced by a compact chip in the Status cell showing the matched rule kind (entity, glob, domain, or no filter) with a tooltip for the full reason.

### Changed
- **Full light theme**: The UI now defaults to a light color scheme. Dark mode activates via system preference or the manual toggle.
- **Status column**: Merged the former "Reason" column into the Status cell as a hoverable rule chip; table is now 6 columns wide.
- **Sort highlight**: The active sort column header is now highlighted in the primary color.
- **Info icon on Size header**: The Size column header shows an inline info icon to indicate the tooltip.

## [1.1.1] - 2026-04-25

### Changed
- **Entity limit selector**: Refactored to apply filtering client-side instead of
  server-side. The `GET /api/entities` endpoint no longer accepts a `limit`
  query parameter and always returns the complete entity list. Changing the
  limit selector now triggers a local re-render instead of a server reload,
  improving responsiveness and reducing network overhead.

### Optimized
- **Screenshot images**: Recompressed all screenshots (main.png, chattiness.png,
  setup-wizard.png) for reduced file size.

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
