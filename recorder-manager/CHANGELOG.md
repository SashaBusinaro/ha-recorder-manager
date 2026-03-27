# Changelog

## 0.1.1

### Changed
- Replaced row count metric with actual database space occupied (bytes)
- Replaced average `writes_per_minute` metric with a live sliding window capturing changes in the last 60 seconds
- Improved filter tag UX to automatically add typed text when clicking elsewhere on the page
- Downgraded base image to Python 3.13 (alpine3.21) to fix `aiohttp` builder issues instead of using `gcc` dependencies

## 0.1.0

### Added
- Database overview dashboard (file size, total rows, entity count)
- Per-entity row count and writes-per-minute metrics
- Sortable entity table with search and domain/status filtering
- Visual filter editor with tag-based input for entities, domains, and globs
- Filter transparency showing which rule causes each entity's status
- Live filter preview
- YAML fragment generator (`recorder_filters.yaml`)
- Configuration validation via Supervisor API before restart
- Automatic HA Core restart after successful validation
- Dark mode UI with responsive layout
