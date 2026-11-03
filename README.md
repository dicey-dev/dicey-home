# Dicey Home

**Alpha software (0.x).** Expect rough edges and compatibility changes.

A 720-logical-pixel command palette for Omarchy's existing application/menu
launcher. Source, design, installation, and behavior are documented in
[`docs/dicey-home.md`](docs/dicey-home.md).

Dicey Home brings application launching, search, and desktop controls together.
Notification-center and expanded quick-action features are planned.
The plugin ID is **`dicey.home`**.
This is an independent repository; no other Dicey checkout, installer, or
synchronization service is required.

Press **Ctrl+Shift+F** inside the launcher to toggle **Dicey Home**: a native
tile dashboard covering the entire display and bar, with real activity monitoring, MPRIS media
controls, output volume/mute, a focus timer, and session actions. Layout and tile
visibility are remembered across opens and shell restarts.

Web searches use the default browser's configured search engine, including
custom URL engines such as Unduck. Preview results come only from that engine;
providers without usable previews still open through the browser. Chromium-family
settings are read-only; Firefox-family searches use native browser search.

The header includes your username and a circular portrait. It uses
`~/.config/omarchy/launcher-avatar` or your standard user-profile image, with a
theme-colored initials badge when no photo is available.

```bash
omarchy plugin add https://github.com/dicey-dev/dicey-home.git
omarchy plugin enable dicey.home
```

Uses the installed Omarchy menu, Quickshell/MPRIS, `wl-copy`, Python 3
(standard library only), `pactl`, `nmcli`, XDG tools, and `notify-send`. `btop`,
`ncdu`, and Obsidian tiles honor availability. Colors, fonts, borders, spacing, and rounding follow the live
global Omarchy theme. Existing menu IPC and shortcuts route to this clone.

## Development and hot reload

From any checkout (not the installed production folder):

```bash
tests/run.sh
tests/run.sh --compat
omarchy plugin validate .
scripts/dev.py start
# Ctrl+C stops watching and restores the previously enabled menu.
```

Tests use `python3` and `node` from `PATH`, with no npm/pip dependencies or
hardcoded interpreter paths in the test runner. Node is test-only. Installed
Python helpers remain a separate runtime dependency. Internal dashboard
components live in `home/`, following the feature-folder organization used by
[Omaplug](https://github.com/fross100/omaplug).

`tests/run.sh --compat` uses the installed Omarchy menu source. The separate
`tests/verify_*.py` checks operate the real desktop and may restart the shell;
run them only deliberately in an idle graphical session.

Development runs as `dicey.home.dev`, with separate preferences and without
modifying installed `dicey.home` files. No background watcher is installed.
See [Development](docs/development.md) for hot reload, recovery and production updates.

## Rollback and removal

Restore the stock menu with `omarchy plugin enable omarchy.menu`, then use
`omarchy plugin remove dicey.home`. Preferences live outside the checkout
under `$XDG_STATE_HOME/omarchy/dicey.home` (default `~/.local/state/omarchy/dicey.home`)
and are intentionally preserved.

`LICENSE` is Apache-2.0.
Upstream attribution/license review and broader compatibility testing remain
publishing tasks; passing development checks does not claim marketplace readiness.
