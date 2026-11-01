# Dicey Home

**Alpha software (0.x).** Expect rough edges and compatibility changes.

A 720-logical-pixel command palette for Omarchy's existing application/menu
launcher. Source, design, installation, and behavior are documented in
[`docs/dicey-home.md`](docs/dicey-home.md).

Dicey Home brings application launching, search, and desktop controls together.
Notification-center and expanded quick-action features are planned.
The plugin ID is **`dicey.home`**.

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

Uses the installed Omarchy menu, Quickshell/MPRIS, `wl-copy`, `/usr/bin/python3`
(standard library only), `pactl`, `nmcli`, XDG tools, and `notify-send`. `btop`,
`ncdu`, and Obsidian tiles honor availability. Colors, fonts, borders, spacing, and rounding follow the live
global Omarchy theme. Existing menu IPC and shortcuts route to this clone.

## Development and hot reload

Edit this checkout, not the installed copy. Configure the local watcher to map
`~/projects/dicey-home` to `~/.config/omarchy/plugins/dicey.home`. It stages and
validates copies before deployment, preserves backups outside the plugin scan
directory, and excludes Git metadata, docs, tests, mockups, and Python bytecode.
Omarchy handles code hot-reload; this is not a second Quickshell process.

```bash
omarchy plugin validate .
node tests/test_launcher.js
node tests/test_home.js
/usr/bin/python3 -B -m unittest discover -s tests -p 'test_*.py'
```

The menu-compatibility test uses the installed Omarchy menu source. The separate
`tests/verify_*.py` checks operate the real desktop and may restart the shell;
run them only deliberately in an idle graphical session.

Manage the transitional watcher with
`~/dicey-kustomarchy/scripts/manage-watcher {status|stop|restart}`. Use `restart`
after adding runtime directories. See [the development-environment plan](docs/development.md)
for the recommended independent project setup and official references.

## Rollback and removal

Stop the watcher before removal so it cannot reinstall the plugin. Restore the
stock menu with `omarchy plugin enable omarchy.menu`, then use
`omarchy plugin remove dicey.home`. Preferences live outside the checkout
under `$XDG_STATE_HOME/omarchy/dicey.home` (default `~/.local/state/omarchy/dicey.home`)
and are intentionally preserved.

`LICENSE` was copied unchanged from the parent repository (Apache-2.0).
Upstream attribution/license review and broader compatibility testing remain
publishing tasks; this migration does not claim marketplace readiness.
