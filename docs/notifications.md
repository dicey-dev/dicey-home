# Notification hub (unreleased alpha work)

This is work in progress on `main`, not part of the **v0.1.0** pre-notification
release. Native test coverage below does not imply finished UX or release
approval. No later release/tag is currently authorized.

## Flow and design

Home's first column is now a readable, newest-first notification feed, not a
second collection of app shortcuts. The wider column, quiet borders, urgency
rail and explicit unread dot use the current Omarchy theme. The other three
groups, application search, stock routes and compact dmenu remain intact.

- Click the existing Home bar icon to open the dashboard at Notifications,
  clearing any launcher query and moving keyboard focus to the feed controls.
  The stock compact menu's backdrop can consume the first outside click to
  close itself; click the exposed icon to open the feed. Use Escape or the usual
  shortcut to close Home.
  The horizontal icon shows unread count (`99+` at 100), urgent color, and a
  separate DND pause marker. A vertical bar uses a small status dot and the
  tooltip reports the count/DND. `!` means the reader/service is not ready.
- App identity, exact local date/time, live/recent status, urgency, summary and
  body are plain text. Sender markup is displayed literally, never rendered.
  Sender images/icons/links are not fetched. Long content is bounded; the feed
  scrolls independently and the dashboard itself scrolls on smaller screens.
  New arrivals and live-to-history updates preserve the visible entry/scroll
  position while reading older messages; the top stays live when already there.
- **Unread only** filters the feed. **Mark all read** acknowledges the current
  snapshot without dismissing anything. Opening, Escape, filtering, dismissing
  a toast or replaying history does not implicitly mark notifications read.
  Read status is local to Home, not a sender receipt. Timestamp + ID distinguish
  entries, including ID reuse after shell restart. In-place sender replacements
  retain their original read status. First use treats retained entries as unread.
- **DND** changes the host's global setting. Omarchy decides which alerts bypass
  it and which silenced messages enter history; Home does not override that policy.
- **Open latest toast** delegates the newest visible toast's default action (or
  host app-focus fallback); **Dismiss latest toast** archives that toast. They
  are deliberately *not* row actions. An intervening notification changes the
  latest target. With no visible toast the host safely returns `none`.
- **Replay recent** asks the host to replay its recent history as toasts, retaining
  the host's existing behavior (including replacing current toasts).
- **Clear history…** first shows a warning that this deletes the host's **shared**
  history permanently, with Cancel focused by default. Escape cancels this step;
  another Escape closes Home. Confirmation invokes public `notifications clear`.
  Live toasts are not cleared, and can subsequently archive into history.

Tab/Shift+Tab reach labelled controls with visible focus rings. Escape retains
the normal query/edit/menu behavior. The notification view cannot be hidden by
tile editing; obsolete Workspace tile IDs are dropped from saved preferences.

## Host boundary and limitations

Supported host: Omarchy 4.0.6-1, Qt 6.12, Quickshell 0.3.2. Its third-party shell
facade does not provide a notification model or per-entry action API. Home does
not traverse private service objects or authentication services. It does not
start another notification server, D-Bus owner, Quickshell process, or daemon.

One shared QML singleton owns one shell-lifetime `python3 notifications.py
--watch` subprocess. It reads existing host snapshots under
`~/.local/state/omarchy/notifications/` and `history/`, and the host DND setting
from `~/.local/state/omarchy/notifications.json`. This HOME-based path deliberately
matches the tested host; the snapshot format is a compatibility dependency,
not a promised upstream API. Public `omarchy-shell notifications ping` detects
service availability; commands use only its documented IPC methods. Polling is
one second for files and five seconds for service availability. IPC has bounded
timeouts; reader failure is visible and retried.

The host retains only ten archived entries, plus current popup files; Home does
not extend retention. DND can release sender objects, and archived/restarted
notifications usually have no live sender actions. Therefore there are **no**
fake per-history-row action/dismiss buttons, arbitrary sender-action enumeration,
or independently editable history. Stored `execArgv` is never read by Home;
explicit latest-toast invocation remains the host's responsibility.

Reads reject symlinks, FIFOs, oversized/malformed files and inconsistent
identities; control/bidi-override characters are removed. Each directory scan
and file read is bounded, with at most 256 merged entries displayed and a warning
if anything is skipped/truncated. Files can move during reads; the next refresh
converges without writing or locking the host's files. This is not a sandbox.

Only `notifications-read.json` (timestamp and boundary IDs, no content) is
written under `$XDG_STATE_HOME/omarchy/dicey.home/`. Development scopes it to
`dicey.home.dev`. The singleton stops its subprocesses when unloaded; shell
restart reloads the host history and Home read watermark. Production deployment
remains explicit; a source edit does not upgrade a manually copied install.
