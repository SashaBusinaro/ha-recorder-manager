# ADR-006: HA REST API for entity discovery

**decision**: Use `GET http://supervisor/core/api/states` to discover all
entities currently registered in Home Assistant, then merge with database
entities to produce a unified view.

**rationale**: The SQLite database only contains entities that have been
recorded. Entities that are already excluded by existing filters have zero
rows and are invisible to DB queries. To show these entities (so users can
re-include them), we need an external source of truth for "all entities
that exist in HA." The Core REST API `GET /api/states` returns every active
entity with its current state. Accessed via the Supervisor internal proxy,
this requires only `homeassistant_api: true` (already needed for F5).

**rejected alternatives**:
- WebSocket API `config/entity_registry/list_for_display`: lighter response
  but requires maintaining a WebSocket connection; overkill for a one-shot
  entity list fetch.
- Parsing `configuration.yaml` for entity definitions: not feasible;
  entities come from integrations, automations, templates, etc. — not from
  a single config file.
- Relying on DB only: would miss excluded entities entirely, violating the
  requirement to show zero-row entities for re-inclusion.

**revisit if**: the entity list becomes too large for a single REST call
(unlikely for typical HA installations, but possible for very large setups
with 5000+ entities).
