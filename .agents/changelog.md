# Changelog

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
- Added `gcc`, `musl-dev`, `python3-dev` build deps for aiohttp wheel compilation on Alpine
- Fixed API fetch URLs to use ingress base path (`data-ingress-path` on body)
