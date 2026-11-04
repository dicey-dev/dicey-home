# Dicey Home

A 720-logical-pixel command palette for Omarchy's existing application/menu
launcher. Source, design, installation, and behavior are documented in
[`docs/dicey-home.md`](docs/dicey-home.md).

Dicey Home brings notifications, application launching, search, and desktop controls together.
The plugin ID is **`dicey.home`**.
This is an independent repository; no other Dicey checkout, installer, or
synchronization service is required.

Press **Ctrl+Shift+F** inside the launcher to toggle **Dicey Home**: a native
tile dashboard covering the entire display and bar, with real activity monitoring, MPRIS media
controls, output volume/mute, a focus timer, and session actions. Layout and tile
visibility are remembered across opens and shell restarts.

The existing Home bar icon shows an unread count (up to **99+**), urgency and DND
status. Click it to open Home at **Notifications**. Read the newest live/recent
entries, filter unread, explicitly mark all read, toggle DND, or use the host's
latest-toast/replay controls. Clearing shared history requires confirmation;
opening Home never marks or deletes notifications. See [notification behavior
and host limitations](docs/notifications.md).

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
and `ncdu` controls honor availability. Colors, fonts, borders, spacing, and rounding follow the live
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

## Compatibility, updates and privacy

Tested on **Omarchy 4.0.6 / Quattro, Qt 6.12 and Quickshell 0.3.2**. The installed
menu is adapted with checked anchors; an unsupported upstream menu falls back
to its stock implementation instead of applying a partial transformation.
Other Omarchy releases are not yet a tested compatibility promise.

```bash
omarchy plugin update dicey.home
```

Omarchy fetches `origin HEAD` (the remote default branch) and fast-forwards the
installed checkout, even when detached; it does not choose a tag based on SemVer.
See [Releases and marketplace checklist](docs/publishing.md) for releases, rollback limitations
and migrating a manually copied install. The clone-source metadata deliberately
keeps existing `omarchy.menu` shortcuts and stock-menu restoration working.

No build, privilege elevation, background installer, additional daemon or remote
build is required. Omarchy normally supplies the runtime tools; optional tiles
are unavailable when their applications are absent. `pactl` comes from
`libpulse`, `nmcli` from `networkmanager`, `wl-copy` from `wl-clipboard`, and
`notify-send` from `libnotify`. XDG helpers and a configured default browser are
needed for browser/file actions. See [Security boundaries](docs/security-review.md):
search queries may go to your configured engine while typing, browser search
preferences are read-only, and avatars/media artwork come from your session.
Notification text is read locally from Omarchy's existing snapshot files; it is
not sent over the network or duplicated into another history database. One
shell-owned Python helper watches those files while Home is loaded. Only a read
watermark is stored in Home's own preferences. Notification content renders as
plain text; sender images, URLs and stored commands are not loaded or executed
by the feed. Explicit toast actions are delegated to the host via public IPC.

## Rollback and removal

Restore the stock menu with `omarchy plugin enable omarchy.menu`, then use
`omarchy plugin remove dicey.home`. Preferences live outside the checkout
under `$XDG_STATE_HOME/omarchy/dicey.home` (default `~/.local/state/omarchy/dicey.home`)
and are intentionally preserved.

Dicey code is Apache-2.0; adapted Omarchy portions remain MIT. Preserve
[`LICENSE`](LICENSE) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
Marketplace approval is separate from local validation and is not a security audit.
