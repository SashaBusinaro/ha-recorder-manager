# ADR-005: Supervisor API for config validation and restart

**decision**: Use the Supervisor API endpoints `POST /core/check` and
`POST /core/restart` (via `http://supervisor/`) to validate configuration
and restart HA Core after filter changes.

**rationale**: The add-on writes a YAML fragment that HA loads at startup.
To apply changes, HA must restart. Rather than asking the user to manually
restart, the add-on automates this with a safety net: config validation
first, restart only on success, rollback on failure. The Supervisor API is
the official mechanism for add-ons to interact with HA Core lifecycle.
The `homeassistant` role is the minimum role that grants access to these
Core endpoints.

**rejected alternatives**:
- Manual user restart: poor UX; users may forget or make mistakes.
- `admin` role: overly permissive; grants access to all API endpoints
  including protection mode toggle. `homeassistant` role is sufficient
  and more secure.
- Direct `ha core restart` CLI: not available inside add-on containers;
  the Supervisor API is the sanctioned approach.

**revisit if**: HA introduces a recorder-specific reload mechanism that
doesn't require a full core restart (currently no such API exists).
