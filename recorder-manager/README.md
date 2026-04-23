# Home Assistant Add-on: Recorder Manager

Visual database analytics and recorder filter manager for Home Assistant.

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]

## About

This add-on provides a graphical interface for managing which entities are
recorded by the Home Assistant Recorder integration. It helps you:

- **See which entities consume the most database space** (by DB space)
- **Identify the most chatty entities** (by writes per minute, live sliding window)
- **Build include/exclude filters visually** — no YAML editing required
- **Apply filters safely** — with config validation before restart
- **Migrate existing filters** — guided wizard copies your current `recorder:` rules automatically

The add-on is **read-only** for both the database and `configuration.yaml`.
It only writes to its dedicated `recorder_include.yaml` and `recorder_exclude.yaml` files.

Particularly useful for Raspberry Pi / SD card setups where minimizing
database writes extends storage lifespan.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
