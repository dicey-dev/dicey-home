# Native Dicey Home implementation plan

## Goal

Turn the approved `mockups/home/` design into a native presentation of
Dicey Home. Dicey Home fills the entire display and covers the Omarchy bar,
shares the stock app/search engine, follows global theme tokens, and
remembers the chosen layout. The compact launcher remains available through
Ctrl+Shift+F and the visible layout control.

**Status:** first native iteration implemented, installed, and verified against
Omarchy 4.0.4-1. Native service checks use a silent MPRIS fixture, and live layout
checks cover keyboard switching, search, compact dialogs, and shell restart.

## Architecture

- Mount `Home.qml` inside the existing menu's layer surface. Keep one
  menu lifecycle and one keyboard-exclusive surface, rather than another shell.
- Use the existing menu for search ranking, calculator/web rows, app launching,
  routes, and selection/input dialogs. Dicey Home applies to root/Apps; other
  routes use the existing compact menu.
- Split reusable tiles, controls, native service bindings, and activity sampling
  into local components. Bind colors/fonts/spacing/borders to `qs.Commons`.
- Persist layout and hidden tiles outside plugin source; migrate the existing
  fullscreen preference. Keep Python helpers bytecode-free so data collection
  cannot trigger plugin hot-reload.
- Render lightweight terminal-like activity data in tiles. Activating the btop
  tile launches the real TUI in the user's terminal. Embedded PTY rendering is a
  separate extension, not a prerequisite for this first native iteration.

## Delivery stages

### 1. Native start surface

- [x] Replace the fullscreen result list with the four approved tile groups.
- [x] Add compact/Dicey Home toggling and the new name in UI/IPC.
- [x] Share search, calculator, browser-default web search, and app library.
- [x] Provide keyboard navigation, search focus, Escape, and visible controls.
- [x] Preserve portrait and existing menu routes/dialogs; cover bar zones in Dicey Home.

### 2. Real widgets

- [x] Sample CPU/core usage, memory, bandwidth, temperature, and disk space.
- [x] Launch real btop from its tile, using the configured terminal.
- [x] Bind media metadata, artwork, playback, track switching, and seeking to MPRIS.
- [x] Bind output volume/mute to the current physical output, including DSP routing.
- [x] Implement an actual 25-minute focus timer that continues while closed.
- [x] Connect clock, notification quiet mode, network, appearance, and lock actions.

### 3. Preferences and resilience

- [x] Remember Dicey Home versus compact layout across opens/restarts.
- [x] Persist tile visibility and provide edit/restore controls.
- [x] Handle no player, no audio output, no network, and unavailable telemetry.
- [x] Poll only while the home is visible; stop/reap helpers when hidden.
- [x] Adapt to monitor geometry, scale, font size, and theme changes.

### 4. Verification and installation

- [x] Validate manifests and run parser/sampler/preference regression tests.
- [x] Verify native rendering, keyboard toggle, search, and real service data.
- [x] Verify layout/tile persistence across shell restart.
- [x] Check compact menus and selection/input dialogs remain functional.
- [x] Install through the project's backup-aware helper and update documentation.

### Responsiveness/fullscreen follow-up (pre-alpha iteration 1)

- [x] Remove per-row result-grid rebuilding and detach the hidden compact view.
- [x] Virtualize and recycle result tiles; create edit controls only while editing.
- [x] Decouple text echo from filtering, with immediate keyboard-action flushing.
- [x] Resolve result actions by stable IDs rather than obsolete row indices.
- [x] Bind both home dimensions to the usable display and size tiles vertically.
- [x] Add a live typing/publication/delegate-count/fullscreen regression check.

### Full-display coverage update (pre-alpha iteration 2)

- [x] Use the overlay layer across the entire display, ignoring bar exclusion zones.
- [x] Verify the compositor surface starts at the monitor origin and spans its full size.
- [x] Reveal the existing bar on close without modifying its configuration.

## Verification commands

```bash
tests/run.sh
tests/run.sh --compat
omarchy plugin validate .
python3 -B tests/verify_home.py
python3 -B tests/verify_launcher_layout.py
```

The last two checks need an idle graphical session and restart the shell. The
native check uses `wtype`, `python-dbus`, and `python-gobject` for its silent
fixture; these are test dependencies rather than runtime plugin dependencies.

## Follow-up polish after the first native iteration

Custom app pinning/reordering, richer calendar integration, more widget types,
and an optional real embedded terminal surface can follow once the core native
layout and service bindings are stable. Marketplace-ready standalone packaging,
upstream licensing notices, and broader Omarchy-version compatibility remain the
separate publishing work identified in the repository audit.
