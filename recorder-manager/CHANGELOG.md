# Changelog

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
