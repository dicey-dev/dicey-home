# Dicey Home

## Design

The launcher becomes a wide command palette: a small accent-colored route
heading, a user-profile portrait, a large inset search field, spacious icon-led rows, an accent cursor
rail, labeled calculator/web sections, and a quiet keyboard-hint footer.
Its normal width is 720 logical pixels (the original is 300), clamped to the
display width. The list scrolls at approximately 430 logical pixels in height.
Caller-specified dmenu widths, selection dialogs, and input prompts retain
their compact layout.

All colors come from `Color.menu` and `Color.accent`; structural values use
`Style` and `Border`. There is no private palette or theme-set hook. Changes to
the global theme, font, border specifications, and rounding apply live.

## Dicey Home

Press **Ctrl+Shift+F** while the launcher is open, or use its visible layout
control, to switch between the compact launcher and **Dicey Home**. The native
tile surface fills the entire display, covering the bar as well as the workspace.
Colors, typography, spacing, and rounding follow the global theme.

The four groups are **Workspace**, **The machine**, **In the flow**, and **Make
space**. Workspace tiles use the configured editor, terminal, browser, and file
manager; Notes uses Obsidian when installed. **All apps** displays the stock
application library as tiles. Search uses the original ranking, routes,
calculator, and browser-default web search. Enter in search opens the first
match; Down enters the tile grid, arrows navigate spatially, and Enter opens a
tile or focuses a widget's controls. Delete on an application result uses the
stock uninstall confirmation.

Application tiles display their desktop-entry icons through the shared Omarchy
icon resolver. Workspace shortcut icons are resolved from the configured editor,
terminal, browser, and directory handler, with Obsidian's icon for Notes. Images
load asynchronously at the display's pixel density; missing or unreadable icons
retain the fallback glyph. Icon discovery runs once per open, not per keystroke.

The home explicitly tracks the overlay surface's full width **and height** and
ignores bar exclusion zones. Dashboard tile sizes use the remaining viewport height rather than a
fixed maximum, so the presentation fills the screen vertically as well.
Closing the launcher reveals the bar again; its configuration is not changed.

Typing updates the TextField immediately. Filtering runs after a short 35 ms
typing pause; Enter, Down, and layout switching flush pending input first.
Results publish once after a completed model rebuild, not once per appended
row. A recycled GridView renders only the visible result tiles, and the hidden
compact ListView is detached while Dicey Home is active. Click and Delete
actions resolve stable item IDs against the current model to avoid stale-index
selection during asynchronous updates.

Activity is real Linux CPU/core usage, memory, temperature, network throughput,
process count, and home-filesystem space. It refreshes roughly every 2.5 seconds
while the dashboard widgets are visible, and stops while closed or displaying
search/application results. Activating the activity tile opens real `btop` in
the default terminal. Storage opens `ncdu` when installed, otherwise the default
file manager. The tiles render lightweight metrics; they do not embed a PTY.

Media uses native MPRIS metadata/artwork, play/pause, next/previous, source
cycling, and seek. Controls honor the selected player's reported capabilities.
Output volume/mute use Omarchy's physical-output resolver and `pactl`, including
DSP routing; each action re-resolves the current sink. The focus timer is a real
25-minute timer that continues while the launcher is closed, persists its
deadline, and sends a completion notification. Quiet mode, Wi-Fi, appearance,
and lock tiles use the existing Omarchy/NetworkManager operations.

**Edit tiles** exposes hide/show controls; **Restore tiles** restores the default
set. Layout and hidden tiles are saved immediately and survive opens, shell
restarts, and plugin reinstalls. The existing fullscreen preference migrates to
Dicey Home. Root/Apps use Dicey Home when selected; other routes and
selection/input dialogs retain the compact stock presentation without changing
that preference. Escape clears search, exits editing, returns from All apps to
the home tiles, or closes the launcher. Ctrl+Shift+F changes the saved layout.

The preference is stored outside the plugin at
`~/.local/state/omarchy/dicey.home/layout.json` (or under `$XDG_STATE_HOME`
when set). For automation:

```bash
omarchy-shell shell call dicey.home toggleHome ''
omarchy-shell shell call dicey.home toggleTile 'network'
omarchy-shell shell call dicey.home focusControl 'toggle'
```

`toggleFullscreen` remains a compatibility alias. The implementation plan and
follow-up work are in [home-plan.md](home-plan.md).

## Activation

```bash
omarchy plugin add https://github.com/dicey-dev/dicey-home.git
omarchy plugin enable dicey.home
```

The `omarchy.clonedFrom: omarchy.menu` manifest metadata makes Omarchy route
existing menu calls to this plugin and replaces the menu widget in its current
bar position. Standard shortcuts remain:

- `Super+Space`: command palette/root menu.
- `Super+Alt+Space`: applications.
- Existing theme/background/menu shortcuts retain their routes.
- Arrow keys, Page Up/Down, Enter/Right, Escape, Backspace/Left, mouse selection,
  paste, app uninstall via Delete, and dmenu selection/input retain stock behavior.
- Right-clicking the bar menu icon opens the default terminal.

Return to the packaged menu with:

```bash
omarchy plugin enable omarchy.menu
```

## Search

Apps and menu actions retain their original ranking. Root and Apps searches
also show:

- **Calculator:** `24 * 7`, `(12 + 8) / 5`, `2^10`, `sqrt(144)`, `18 % 5`.
  An answer is shown first; selecting it copies the answer to the clipboard.
  `=42` explicitly evaluates a plain number. Supported functions: `sqrt`, `abs`,
  `round`, `floor`, `ceil`, `pow`, `min`, `max`, `sin`, `cos`, `tan`, `ln`, and
  `log`/`log10`. Trigonometry uses radians; `pi`/`π` and `e` are constants.
  `%` means modulo. Invalid, incomplete, or non-finite expressions do not
  produce an answer. Expressions are parsed locally without `eval`.
- **Web:** a search action using the **default search engine of the default
  browser**, plus up to four best-effort preview titles and domains from that
  engine. Prefixing a query with `?` makes a web-only search (for example
  `? hyprland documentation`). The row shows the detected engine and browser.
  Requests start after 450 ms without typing, for queries of at least three
  characters. Only the configured engine receives preview queries; arithmetic
  and other submenus do not make requests. Results are cached in memory for
  five minutes, with at most thirty queries, keyed by browser/profile/engine.
  Nothing is written to a search-history file.

Search actions re-read the browser and engine settings at activation, build the
engine's configured URL, and use `omarchy launch browser`. Result links also open
in the current global default browser. Network previews do not launch a browser.
Late results cannot change the currently selected app/action.

Browser detection follows Omarchy: `xdg-settings get default-web-browser` with
`BROWSER` unset, then the HTTPS `xdg-mime` association. Chrome, Chromium, Brave,
Vivaldi, and Edge use their last-used profile's saved search preferences, with a
read-only Web Data database lookup when needed. No history, cookies, or browser
settings are modified. The selected engine is refreshed each time the launcher
opens; changing the browser or engine invalidates the corresponding cache key.
Custom URL engines such as Unduck and their bang syntax are preserved.

Firefox, LibreWolf, Floorp, and Zen delegate searches to their native `--search`
command, so the browser itself selects its configured engine. These browsers
do not fetch launcher previews. Chromium-family engines use best-effort HTML
previews; Bing RSS is used only when Bing is the configured engine. Engines
that require JavaScript, block automated requests, or do not return recognizable
results show **Preview unavailable**, while Enter still searches in the browser.
There is no substitute provider. Unsupported browsers, POST-only search engines,
and profiles whose settings cannot be resolved report that limitation instead
of silently using a different engine. Custom wrapper/profile-directory flags
are not resolved; profile selection follows Omarchy's normal browser invocation.

## User profile

The top-right corner displays your username and a circular profile photo. With
no photo configured, it shows a theme-colored initials badge. The portrait is
center-cropped, so rectangular images also fit cleanly; unreadable images use
the initials fallback.

The launcher checks these locations in order each time it opens:

1. `~/.config/omarchy/launcher-avatar` — a launcher-specific image.
2. `~/.face` — your standard user-profile image.
3. `~/.face.icon` — an alternate standard user-profile image.
4. `/var/lib/AccountsService/icons/$USER` — the system account image, if available.

To set a launcher-specific photo, copy a PNG, JPEG, or WebP image to the first
location (the file does not need an extension):

```bash
cp "/path/to/your-photo.png" ~/.config/omarchy/launcher-avatar
```

Reopen the launcher to load it. Replacing the same image file also refreshes on
the next open. Profile images stay outside this repository. The profile border,
initials, username, and session label follow the global theme; compact selection
and input dialogs omit the profile area.

## Implementation and updates

`Launcher.qml` reads the installed `Menu.qml` and mounts a decorated instance
inside the existing shell. `Makeover.js` applies a small set of exact, unique
source adaptations for the visual layout and extra result rows. The installed
`MenuModel.js` and stock application library remain the source of truth;
application icons, hidden-entry rules, launch feedback, user JSONC extensions,
menu providers, guards, navigation, uninstall flow, and selection-file protocol
continue to use Omarchy's implementation. On builds where the injected menu
facade lacks `appLibrary` or is revoked following a shell-configuration change,
a local instance of the installed `AppLibrary.qml` provides the same operations.
This keeps launcher shortcuts working after changing bar/widget settings.
Calculator copying uses the installed `wl-copy`
so the answer remains available after the palette closes.

This approach avoids maintaining a frozen copy of the full menu engine. Each
new instance reads the installed source, so upstream features are inherited.
If an upstream update changes an adaptation anchor or fails QML compilation,
the plugin opens the original menu and records the reason in `inspect()` and
the Quickshell log. The plugin does not edit packaged Omarchy files.

The menu is mounted lazily and reads the installed source when mounted. Plugin
changes request a shell rescan. If the running Quickshell retains its component
cache, run `omarchy restart shell` after installing an update. Activation itself
does not require Hyprland edits.

## Verification

```bash
omarchy plugin validate .
node tests/test_launcher.js
/usr/bin/python3 -B -m unittest discover -s tests -p 'test_launcher_web.py'
/usr/bin/python3 -B -m unittest discover -s tests -p 'test_launcher_browser.py'
omarchy-menu toggle apps
omarchy-shell shell call dicey.home inspect ''
omarchy-shell shell call dicey.home search '24 * 7'
omarchy-shell shell call dicey.home inspect ''
```

`inspect` reports enhancement/fallback state, dimensions, current/saved layout,
state-file path, theme colors, route, result types, selection, search engine, and network status.
`search` edits the open palette's filter through the same stock filter function
used by the keyboard.

On an idle desktop, run the live layout regression check:

```bash
/usr/bin/python3 -B tests/verify_launcher_layout.py
```

It requires `wtype`, opens the launcher, exercises the actual keyboard shortcut,
checks query/selection preservation and compact dialogs, and restarts the shell
once to verify persistent layout restoration. It restores the original layout
preference and closes the launcher afterward.

The native dashboard regression check additionally verifies real telemetry,
spatial keyboard navigation, focus continuation, saved tiles, and MPRIS controls
using a silent test-only player:

```bash
node tests/test_home.js
/usr/bin/python3 -B -m unittest discover -s tests -p 'test_control_activity.py'
/usr/bin/python3 -B tests/verify_home.py
```

The live check requires `wtype`, `python-dbus`, and `python-gobject`, restarts the
shell once, and restores layout/tile choices. It does not change real playback,
audio settings, Wi-Fi, notification mode, or session locking.

For input latency, batched publications, virtualized delegate counts, and full
screen geometry on an idle desktop:

```bash
/usr/bin/python3 -B tests/verify_launcher_performance.py
```
