# Notification center (unreleased alpha work)

This is work in progress on `main`, not part of the **v0.1.0** pre-notification
release. No later release/tag is currently authorized.

## Flow and design

Home's first column is a notification center: recent notifications grouped by
where they came from. It only *shows and tidies* notifications. Pop-ups remain
Omarchy's (or, separately, a bar plugin's) job; Home never shows, invokes,
dismisses or replays toasts.

- Click the Home bar icon to open the dashboard at Notifications with keyboard
  focus in the list. The bar icon shows the DND pause marker (`Ⅱ`) and `!` when
  the reader or host service is not ready. There is no count badge.
- **Grouping.** Each application is one group. A browser notification
  (Chromium, Chrome, Brave, Edge, Vivaldi, Opera, Helium, Firefox, Zen,
  LibreWolf) is grouped by **website**, with the browser named under the group
  title. If an Omarchy web app (`omarchy-launch-webapp <url>` desktop entry)
  exists for that exact hostname, the group takes the web app's name, e.g.
  "WhatsApp · web.whatsapp.com · Chromium"; `www.` and the bare hostname are
  one site. When one website's group has entries from several browsers, each
  entry names its browser. The browser cannot tell Home whether
  a notification came from the web app window or an ordinary tab, so both land
  in the same group. A browser notification without a recognizable origin stays
  in the browser's own group.
- Groups are ordered by their newest entry; entries are newest first. The
  current group's header stays pinned while scrolling a long group.
- **Removing.** × (or Delete on the selected entry) removes one entry. A group's
  **Clear** (or Shift+Delete) removes that group; **Clear all** empties the list.
  Removal only hides entries in Home and persists across restarts. A removal is
  kept while the host still holds the entry (e.g. a critical toast left on
  screen) and otherwise forgotten after 48 hours, pruned hourly while the shell
  runs; at most 1024 removals are remembered. Selection moves to
  the neighbouring entry. There is no read/unread state.
- App name, summary, body text, local time, urgency and "on screen" (still a
  live toast) are plain text. The host's small markup subset is reduced to text;
  sender images, icons and links are not fetched.
- **DND** changes the host's global setting via public IPC. Omarchy decides
  which alerts bypass it and which silenced messages enter history.

Tab/Shift+Tab reach labelled controls with visible focus rings; arrows select
entries, PgUp/PgDn scroll. New arrivals and live-to-history updates preserve the
visible entry and scroll position while reading older entries.

## Host boundary and limitations

Supported host: Omarchy 4.5 (`omarchy.notifications` 2.0.0). Its third-party
shell facade does not provide a notification model or per-entry action API.
Home does not traverse private service objects, start another notification
server, D-Bus owner, Quickshell process or daemon.

One shared QML singleton owns one shell-lifetime `python3 notifications.py
--watch` subprocess. It reads the host's `live.json` and `history.json` under
`~/.local/state/omarchy/notifications/` once a second and rescans web app
desktop entries every 30 seconds. This HOME-based path and file format match the
tested host; they are a compatibility dependency, not a promised upstream API.
Public `omarchy-shell notifications isDnd`, polled every five seconds, both
detects the service and reports DND. Commands have bounded timeouts; reader
failure is visible and retried.

The host keeps history for 24 hours (at most 100 entries) plus current toasts,
and never persists notifications sent with the `transient` hint. It prunes
`history.json` only when it writes it, so Home applies the same 24-hour and
100-entry rule by each entry's `closed_ts` rather than extending retention.
Entries are identified by the host's row key; a replayed duplicate shows its
newest copy. An unreadable applications directory only disables web app names.

Reads reject symlinks, non-regular and oversized files, and malformed rows;
control/bidi-override characters are removed. At most 256 entries are shown,
with a warning if anything is skipped or truncated. Files can change during
reads; the next refresh converges without writing or locking the host's files.
This is not a sandbox.

Only `notifications-removed.json` (host keys and removal times, no content) is
written under `$XDG_STATE_HOME/omarchy/dicey.home/`. Development scopes it to
`dicey.home.dev`. The singleton stops its subprocess when unloaded.

## Verification

- `tests/run.sh`: reader parsing/grouping/web app mapping, model grouping and
  removal, release notes.
- `tests/verify_notification_fixtures.py` (no dev session active): isolated
  fixture data in the real shell; grouping, pinned headers, scroll
  preservation, Delete/Shift+Delete, per-entry/group/all removal, DND, empty state.
- `DICEY_PLUGIN_ID=dicey.home.dev tests/verify_notifications.py` (dev session
  active): uniquely prefixed synthetic notifications through the real host,
  app and Chromium-site grouping, removal persisting across a shell restart,
  real history entries unchanged. Synthetic entries stay in host history until
  its 24-hour retention drops them. If `notify-send` fails with a symbol lookup
  error, unset an inherited `LD_LIBRARY_PATH` (e.g. from an AppImage terminal).
