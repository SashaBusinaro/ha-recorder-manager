# Home Assistant Add-on: Recorder Manager

## How to use

1. Install this add-on from the repository.
2. Start the add-on.
3. Click **OPEN WEB UI** or find **Recorder Manager** in the sidebar.
4. Browse your entities sorted by database usage or write frequency.
5. Use the **Filter Rules** panel to configure include/exclude rules.
6. Click **Apply & Restart** to save and activate your filters.

## First-time setup

Before the add-on can manage your recorder filters, you need to add one
line to your `configuration.yaml`:

```yaml
recorder:
  purge_keep_days: 10    # your existing settings
  !include recorder_filters.yaml
```

The add-on will create and manage `recorder_filters.yaml` automatically.
You only need to add the `!include` line once.

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

## Support

Got questions? Open an issue on
[GitHub](https://github.com/SashaBusinaro/Home-Assistant-Recorder-Manager).

## License

MIT License
