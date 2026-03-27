# Changelog

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
