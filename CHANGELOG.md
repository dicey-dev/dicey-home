# Changelog

Versions follow [Semantic Versioning](https://semver.org/), with **0.x alpha**
versions while the project is under development. `manifest.json` records the
last released baseline; changes under Unreleased are not a new release.

## [Unreleased]

- Replace Workspace shortcuts with a **notification center** in Home's first column.
- Group notifications by application. Browser notifications are grouped by
  website and labelled with the browser; a website installed as an Omarchy web
  app shows that web app's name.
- Remove an entry (×, or Delete), clear a group (Clear, or Shift+Delete) or
  clear the whole list. Removal hides entries in Home only; Omarchy's history
  and on-screen toasts are untouched, and removals persist across restarts.
- Read Omarchy 4.5's `live.json`/`history.json` notification store; the old
  per-file snapshot reader showed an empty feed on Omarchy 4.5.
- No read/unread state, unread filter or count badge; the bar icon shows only
  DND and reader status. Latest-toast, replay and clear-shared-history controls
  are gone: Home never acts on the host's toasts or history, except DND.
- Release notes: every version now has `docs/releases/vX.Y.Z.md`, written by
  `scripts/version.py` and enforced by its `check`.

Not tagged or released.

## [0.1.0] - 2026-11-04

- Separate opt-in development copies from installed production files.
- Group dashboard internals under `home/`; retain portable test entry points.
- Fix the bar widget's own plugin identity and Qt theme-color qualification.
- Add upstream notices, release tooling and marketplace preparation docs.

## Pre-release development

- Native Home dashboard and browser-default search in the themed command palette.
