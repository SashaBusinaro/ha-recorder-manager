# Home Assistant Add-on: Recorder Manager

## How to use

1. Install this add-on from the repository.
2. Start the add-on.
3. Click **OPEN WEB UI** or find **Recorder Manager** in the sidebar.
4. Complete the one-time setup (see below).
5. Browse your entities sorted by database usage or write frequency.
6. Use the **Filter Rules** panel to configure include/exclude rules.
7. Click **Apply & Restart** to save and activate your filters.

## First-time setup

Before the add-on can manage your recorder filters, add these two lines inside
your `recorder:` block in `configuration.yaml`:

```yaml
recorder:
  include: !include recorder_include.yaml
  exclude: !include recorder_exclude.yaml
```

If you don't have a `recorder:` block yet, add the entire snippet above.
If you already have one, just insert the two `!include` lines inside it —
your existing settings (e.g. `purge_keep_days`) stay exactly as they are.

The add-on creates and manages `recorder_include.yaml` and
`recorder_exclude.yaml` automatically. These files contain only the filter
rules; all other recorder settings remain under your control in
`configuration.yaml`.

> **Important:** This add-on will never modify `configuration.yaml` or the
> Home Assistant database. Only `recorder_include.yaml` and
> `recorder_exclude.yaml` are written by the add-on.

### Setup notification

Each time you open the add-on interface, a **notification banner** appears at
the top of the page if setup is not yet complete. You can dismiss it to
browse database information, but it will reappear on the next page load until
setup is finished.

---

## If you already have inline include/exclude filters (Migration Wizard)

If your `configuration.yaml` has inline `include:` or `exclude:` sub-keys
inside the `recorder:` block, the **Migration Wizard** guides you through
the transition:

1. **Detection** — The add-on detects your existing inline filter definitions
   and offers to copy them.
2. **Copy** — Your existing `include`/`exclude` rules are automatically written
   to `recorder_include.yaml` and `recorder_exclude.yaml`. Your
   `configuration.yaml` is not touched.
3. **Manual edit** — Replace the inline `include:`/`exclude:` blocks inside
   your `recorder:` section with:
   ```yaml
   include: !include recorder_include.yaml
   exclude: !include recorder_exclude.yaml
   ```
   Your other recorder settings (e.g. `purge_keep_days`) stay as they are.
4. **Check & Reboot** — Click **"Edited, check and reboot to apply changes"**.
   The add-on validates your configuration and, if valid, reboots Home
   Assistant to apply the new setup.

> The wizard becomes non-closable once migration starts (after "Start
> Migration" is clicked), to prevent accidental partial completion.

---

## If you have no existing recorder filters (Fresh Setup)

If your `configuration.yaml` has no `include:`/`exclude:` filter blocks,
the **First-Time Setup** wizard appears:

1. Add the two `!include` lines to your `recorder:` block (or add the full
   block if you don't have one):
   ```yaml
   recorder:
     include: !include recorder_include.yaml
     exclude: !include recorder_exclude.yaml
   ```
2. Click **"Edited, check and reboot to apply changes"**.
3. The add-on validates your configuration and reboots Home Assistant.

The add-on creates empty `recorder_include.yaml` and `recorder_exclude.yaml`
for you, letting Home Assistant use its built-in defaults until you configure
filters.

---

## Filter rules

The add-on supports all of Home Assistant's native recorder filter types:

- **Entity include/exclude** — specific entity IDs
- **Domain include/exclude** — entire domains (e.g., `sensor`, `automation`)
- **Entity glob include/exclude** — wildcard patterns (e.g., `sensor.sun*`)

The filter evaluation follows HA's documented priority:
1. Exact entity match
2. Glob pattern match
3. Domain match
4. Default (based on whether includes or excludes are configured)

## Read-only access

The add-on operates with the following access model:

| Resource | Access |
|---|---|
| `home-assistant_v2.db` | Read-only (analytics only) |
| `configuration.yaml` | Read-only (never modified) |
| `recorder_include.yaml` | Read-write (managed by this add-on) |
| `recorder_exclude.yaml` | Read-write (managed by this add-on) |

## Support

Got questions? Open an issue on
[GitHub](https://github.com/SashaBusinaro/Home-Assistant-Recorder-Manager).

## License

MIT License
