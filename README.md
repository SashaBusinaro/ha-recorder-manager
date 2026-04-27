# Home Assistant Recorder Manager

[![Open your Home Assistant instance and show the add add-on repository dialog](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FSashaBusinaro%2Fha-recorder-manager)

## Add-on

This repository contains the following add-on:

### [Recorder Manager](./recorder-manager)

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]

Visual database analytics and recorder filter manager for Home Assistant.
See which entities consume the most space and writes, then build
include/exclude filters with a click.

> **Note:** Currently, this add-on only supports the default SQLite database engine.

## Screenshots

**Main Dashboard**
Shows database size by entity and allows managing include/exclude filters.

<p>
  <img src="images/main-light.png#gh-light-mode-only" alt="Main Dashboard">
  <img src="images/main-dark.png#gh-dark-mode-only" alt="Main Dashboard">
</p>

**Chattiness Analysis**
Real-time analysis of the most talkative entities.

<p>
  <img src="images/chattiness-light.png#gh-light-mode-only" alt="Chattiness Analysis">
  <img src="images/chattiness-dark.png#gh-dark-mode-only" alt="Chattiness Analysis">
</p>

**Setup Wizard**
Guides you through initial configuration and migration of existing filters.

<p>
  <img src="images/setup-light.png#gh-light-mode-only" alt="Setup Wizard">
  <img src="images/setup-dark.png#gh-dark-mode-only" alt="Setup Wizard">
</p>

## Installation

1. Click the button above to add this repository to your Home Assistant.
2. Find **Recorder Manager** in the add-on store and install it.
3. Start the add-on and open the web UI.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg

---

## 🤖 AI-Assisted Development

> [!NOTE]
> **Transparency Notice:** This integration was developed with assistance from AI coding agents (GitHub Copilot, Claude, and others). If you encounter unexpected behavior, please [open an issue](../../issues) on GitHub.
