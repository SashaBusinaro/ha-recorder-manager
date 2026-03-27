# ADR-004: homeassistant_config:rw mapping for filter file output

**decision**: Map `homeassistant_config:rw` to give the add-on access to the
HA `/config/` directory with write permission, and write the generated filter
file to `/config/recorder_filters.yaml`.

**rationale**: The filter YAML must be `!include`d from the user's
`configuration.yaml`, which means it must live in the same `/config/` directory
that HA reads at startup. The `homeassistant_config` map type is the correct
way to access this directory per HA documentation. Write permission is required
to create/update the filter file. The database is also in `/config/`, but is
opened read-only at the application level via `?mode=ro`.

Using `addon_config` was considered but rejected because that maps to
`/addon_configs/{REPO}_{slug}/`, which is a separate directory that HA Core
does not read during config loading — making `!include` from
`configuration.yaml` impossible.

**rejected alternatives**:
- `addon_config:rw`: correct for addon-private config, but the generated file
  must be in HA's `/config/` for `!include` to work. This mapping points to
  the wrong directory.
- `homeassistant_config` (read-only, default): would prevent writing the
  filter file. The DB-only read-only guarantee is enforced at the SQLite
  connection level instead.
- `share:rw`: the share directory is not where HA loads configuration from.

**revisit if**: HA adds support for `!include` from `addon_configs/` paths,
or if a Supervisor API for injecting recorder config is introduced.
