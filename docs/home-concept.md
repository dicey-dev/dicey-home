# Dicey Home — concept 01

An interactive HTML study for evolving the launcher's fullscreen mode into a
Windows 8–inspired start surface. Open `mockups/home/index.html` locally:

```bash
omarchy launch browser "file://$PWD/mockups/home/index.html"
```

## Direction: Metro, after midnight

The signature is a grouped, asymmetrical tile canvas rather than a larger result
list. Large activity and media surfaces sit beside small application tiles.
Charcoal, fine borders, monospace type, one accent, and restrained transitions
keep it visually connected to Omarchy. The bar remains visible above the home.

The HTML study retains the original bar-visible design. The native implementation
now uses full-display coverage, including the bar, following the updated requirement.

The starting Miasma palette is taken from the current machine's global theme:
background `#222222`, foreground `#c2c2b0`, accent `#78824b`. The selector offers
Tokyo Night, Catppuccin, Everforest, and a light-mode study to test the same
geometry with other palettes. In the native implementation these variables map
to `Color`, `Style`, and `Border`; the prototype does not watch system themes.
The media artwork is original CSS geometry; there are no remote fonts or assets.

## The four groups

1. **Workspace:** an oversized Editor tile, then Terminal, Browser, Files, Notes.
2. **The machine:** a btop-inspired terminal tile with CPU history and segmented
   core/memory rails; supporting bandwidth and storage tiles.
3. **In the flow:** artwork, track metadata, playback/seek controls, output volume,
   and a focus timer.
4. **Make space:** clock/calendar, quiet mode, Wi-Fi, appearance, and session lock.

Large surfaces are useful at a glance; selecting an activity tile opens a deeper
terminal-style preview. The layout becomes two columns on tablets and grouped
vertical tiles on narrow screens. Desktop layouts preserve the Win8 feeling of
distinct clusters and mixed-size tiles without requiring horizontal scrolling.

## Try the prototype

- **Ctrl+Shift+F:** Dicey Home ↔ compact launcher. The last view is remembered.
- **/** focuses search; tiles filter by app names, tools, and capabilities.
- **Arrow keys** navigate spatially between focused tiles; **Enter** opens them.
- **Escape** clears search, closes a detail dialog, or returns to the launcher.
- **24 * 7** and other arithmetic use the launcher's existing safe calculator.
- **Media:** play/pause, next/previous, seek, volume, mute.
- **Focus:** start/pause/resume/reset a 25-minute timer.
- **Edit tiles:** hide or restore tiles; choices persist in browser local storage.
- **Theme selector:** recolors every surface, graph, and control.
- **Demo running:** pause simulated telemetry and playback progress.

This is a design prototype. Telemetry, media metadata, connectivity, and agenda
are simulated. Application tiles show command previews rather than execute
commands. No system settings, browser search settings, or native launcher
preferences are changed. Prototype view/theme/pinning preferences live only in
browser local storage under `dicey-home-concept-v1`.

## Native implementation shape

Keep the stock application engine and compact launcher. Dicey Home would be
an alternate presentation sharing search, routing, and persisted layout state.
Render individual tiles as replaceable QML widgets, using the existing service
facades where available:

- App tiles → the shared app library and default-app commands.
- Activity → read-only CPU/memory/network sampling; select to open a real TUI.
- Media → existing MPRIS/PipeWire services or appropriate scoped interfaces.
- Session → existing Omarchy lifecycle and configuration operations.
- Theme → live `Color`, `Style`, `Border` bindings, without a separate palette.

The btop artwork suggests a TUI tile; the HTML does not embed a real PTY.
Whether to embed a terminal surface or render lightweight terminal-like metrics
is an implementation decision to make after reviewing the design.
