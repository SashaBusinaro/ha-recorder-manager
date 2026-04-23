# Changelog

## 2026-04-23 — Phase 3: v1.0.0 — Filter-Only Split-File Architecture

- decision: Switched from single-file full-recorder-block takeover (`recorder: !include recorder_filters.yaml`) to filter-only delegation using two files (`recorder_include.yaml`, `recorder_exclude.yaml`) as sub-key values inside the user's `recorder:` block
- implemented: T1 — Rewrote `config_reader.py`: per-key detection (`inc_managed`, `exc_managed`, `inc_inline`, `exc_inline`); removed full-block extraction and `_parse_full_recorder_as_dict`
- implemented: T2 — Rewrote `yaml_writer.py`: two-file `__init__`, `read_filters`, `write_filters`, `create_defaults`, atomic `backup`/`restore_backup`; removed `write_full_recorder` and `import copy`
- implemented: T3 — Rewrote `server.py`: replaced `FILTER_FILE` with `INCLUDE_FILE`/`EXCLUDE_FILE`; updated `handle_setup_status` scenario logic; rewrote `handle_setup_check`, `handle_setup_init_default`, `handle_migration_apply`; kept all audit fixes
- implemented: T4 — Updated `app.js`: kept all audit fixes (try/finally refresh, message fallback, close button on copy error)
- implemented: T5 — Updated `index.html`: migration step 1 note, step 1 description, step 2 copy-done snippet and warning, step 2 spinner text, fresh-setup step 1 snippet and note
- verified: T6 — `.wizard-snippet` CSS uses `overflow-x: auto` + `white-space: pre` — multi-line snippet renders correctly, no CSS changes needed
- implemented: T7 — Rewrote `DOCS.md`: two-line setup, split migration/fresh-setup sections, updated read-only table, new note about user-retained settings
- implemented: T8 — Replaced uncommitted 2.0.0 CHANGELOG entry with clean 1.0.0 entry; removed intermediate 0.2.0/0.3.0 entries (never released)
- implemented: T9 — Bumped `config.yaml` version to 1.0.0
- implemented: T11 — Updated ADR-004 to reference two new filter files
- discovered: `write_full_recorder` (most dangerous operation — could accidentally overwrite non-filter settings) is now completely eliminated from the codebase



- implemented: `config_reader.detect_setup_status()` — detects three scenarios (complete/!include present, migration/recorder block exists, fresh-setup/no recorder config); robust against false-positive from `recorder: !include` being matched by `_extract_recorder_block`
- implemented: `GET /api/setup/status` — unified scenario detection replacing old `/api/migration/check`; returns `{setup_complete, scenario}` 
- implemented: `POST /api/setup/check` — standalone config validation via Supervisor API; returns `{status: ok}` or HTTP 400 with message
- implemented: `POST /api/setup/reboot` — fire-and-forget HA Core restart using `asyncio.create_task`; returns immediately so client receives response before addon goes unresponsive
- implemented: `POST /api/setup/init-default` — creates empty `recorder_filters.yaml` (comment-only) for fresh-setup scenario; no-op if file exists
- implemented: Removed server-side `_migration_dismissed` flag and `POST /api/migration/dismiss` endpoint; banner is now stateless (reappears on each page load)
- implemented: Unified setup wizard HTML — single `#setup-overlay` modal handles both migration (3 steps) and fresh-setup (2 steps) flows; wizard becomes non-closable after Step 1 via `wizLock()`
- implemented: Client-orchestrated check-then-reboot flow — JS calls `/api/setup/check`, shows result, then calls `/api/setup/reboot` only on success
- implemented: Setup notification banner — dismissible, stateless, shows on every page load when `setup_complete === false`; two variants (migration vs fresh-setup)
- implemented: Success screen with green checkmark circle, reboot notice, and Close button
- implemented: `DOCS.md` rewritten to cover both migration and fresh-setup flows, banner behavior, and correct `!include` syntax
- discovered: `_extract_recorder_block` returns empty string (not None) for `recorder: !include ...` lines, requiring explicit `.strip() != ""` guard in `detect_setup_status`
- discovered: `asyncio.ensure_future` is deprecated in Python 3.10+; replaced with `asyncio.create_task`

- implemented: `config_reader.py` — regex-based parser for `configuration.yaml` that handles HA-specific `!include` tags safely; detects and extracts recorder include/exclude blocks
- implemented: 3 new API routes (`GET /api/migration/check`, `POST /api/migration/apply`, `POST /api/migration/dismiss`) with in-session dismiss state
- implemented: 5-step migration wizard UI (modal) in index.html + app.js + style.css — detection, copy, manual-edit snippet, validate & restart, with dismiss/retry paths
- implemented: Updated DOCS.md with read-only access table, migration wizard docs, and manual edit instructions
- verified: End-to-end test via CLI — `/api/migration/check` returns correct filters and snippet from live `configuration.yaml`; `/api/migration/apply` writes correct `recorder_filters.yaml`
- verified: Rebuilt container and confirmed server starts cleanly with new `config_reader` module
- discovered: PyYAML cannot parse HA YAML (`!include` tags raise ConstructorError); solved using regex/text-based parsing approach
- discovered: HA YAML doesn't allow !include as a sub-key inside a block — only as a value on the key itself

## 2026-03-28 — Phase 3: v0.1.2 Maintenance
- implemented: Cleaned up redundant default keys in `config.yaml` to address linter errors (`boot`, `ingress_port`, `options`, `panel_admin`, `schema`, `startup`)

## 2026-03-27 — Phase 3: v0.1.1 Updates
- implemented: Converted raw database row count metric to true DB size bytes (`SUM(LENGTH(shared_attrs))`) to resolve visual parity bugs
- implemented: UX improvements allowing filter tagging via blur events
- implemented: Migrated the average `writes_per_minute` stat over lifetime to an exact sliding window measuring changes in the last 60 seconds (`last_updated_ts >= time.time() - 60`)

## 2026-03-25 — Phase 3: Initial Implementation (T1–T8)

### Add-on Scaffold (T1)
- Created `recorder-manager/` directory with HA add-on structure
- `config.yaml`: Ingress on port 8099, Supervisor API access, `homeassistant_config:rw` mapping
- `Dockerfile`: Python 3.14 Alpine base image with build deps for aiohttp
- `build.yaml`: aarch64 + amd64 architectures
- `apparmor.txt`: Custom profile with read-only DB access, write to filter file only
- S6 service scripts (`run`, `finish`)

### Repository Config (T2)
- Updated `repository.yaml` and root `README.md`

### Python Backend (T3–T6)
- `server.py`: aiohttp server with ingress middleware, IP restriction, REST API routes
- `db_reader.py`: SQLite read-only queries (modern + legacy schema support)
- `entity_resolver.py`: HA API entity discovery via Supervisor proxy
- `filter_engine.py`: Full HA filter evaluation (all 6 cases) with transparency
- `yaml_writer.py`: YAML fragment generator with backup/restore
- `supervisor_api.py`: Config check + restart via Supervisor API

### Frontend (T7)
- `index.html`: Stats header, search/filter toolbar, filter rules panel, entity table, modal
- `style.css`: Dark mode design system, responsive layout
- `app.js`: Data loading, sortable table, tag inputs, live preview, apply workflow

### Add-on Presentation (T8)
- `README.md`, `DOCS.md`, `CHANGELOG.md` for store listing

### Bug Fixes
- Fixed `homeassistant_config` mount path: `/homeassistant` not `/homeassistant_config`
- Downgraded base image to Python 3.13 (alpine3.21) to fix aiohttp wheel compilation issues
- Fixed API fetch URLs to use ingress base path (`data-ingress-path` on body)
