# Development and production

## Structure and the Omarchy contract

This repository follows [Omaplug](https://github.com/fross100/omaplug): root
manifest/public QML entry points and runtime helpers, feature components in
`home/`, one `tests/run.sh` entry point, README and license. `scripts/` and
`docs/` are development tooling. `mockups/` is design material, not the runtime.
Omaplug itself has no dedicated dev-mode command; our opt-in tool adds that
separation while keeping normal Omarchy production installation.

`manifest.json` declares the `menu` and `bar-widget` kinds, loading `Launcher.qml`
and `BarWidget.qml`. These are two real shell entry points, unlike an internal
detail panel that does not need its own manifest kind. `home/` contains the
dashboard's internal QML components and pure JS model; shared `Profile.qml`,
launcher transformation/search code and Python helpers remain at the root.

QML is Qt's declarative UI language. Quickshell exposes desktop services;
Omarchy supplies theme, components and lifecycle. JavaScript executes in Qt,
not Node. Python helpers use the standard library for browser metadata, search
and activity; see [security boundaries](security-review.md). Plugins run
unsandboxed inside the existing shell, not a web server or second Quickshell.

## Tests and validation

Install Python 3 and Node. Tests have no third-party pip/npm dependencies. Like
Omaplug, `tests/run.sh` uses global `python3`/`node` resolved through `PATH`, not
hardcoded interpreter paths. Check `command -v python3` / `command -v node` when
using activated environments. This setup is deliberately not version-pinned or
hermetic. Node is test-only; installed helper processes still require Python.

```bash
tests/run.sh
# Requires the actual installed Omarchy menu source:
tests/run.sh --compat
omarchy plugin validate .
qmllint -I "${OMARCHY_PATH:-/usr/share/omarchy}/shell" ./*.qml home/*.qml
```

The runner works from any directory. The default suite tests Python helpers,
JS arithmetic/models and development deployment/recovery without desktop IPC.
`--compat` tests `Makeover.js` against the actual installed `Menu.qml`, rejecting
unsupported adaptation anchors. It is separate so ordinary unit tests work
without an Omarchy installation. QML lint uses the installed shell imports;
choose the Qt tools matching Omarchy rather than an unrelated Conda installation.
Existing warnings are not suppressed. Static-file lint cannot prove dynamically
generated menu QML or native desktop interactions.

## Opt-in development mode

From a source checkout outside the installed production folder:

```bash
scripts/dev.py start
```

The foreground command stages and validates real runtime files in
`~/.config/omarchy/plugins/dicey.home.dev`, saves the currently enabled menu ID,
then switches to the development plugin. Installed `dicey.home` files are never
written. Literal plugin IDs are scoped in the development copy, so its layout
preferences use `dicey.home.dev` state rather than production preferences.

Every half second, content changes/new directories/deletions are detected.
Each update is validated before replacing the last valid development copy;
Omarchy handles hot reload. Tooling, docs, tests, hidden directories and mockups
are not copied; symlinks are rejected. Runtime file selection currently covers
QML/JS/Python/JSON and license files; extend it deliberately for new asset formats.

Ctrl+C/SIGTERM restores the previously enabled menu and removes the development
copy. No background service is installed, and a per-plugin lock prevents two
development sessions from competing. Do not manually switch menus or perform
plugin updates/removal during a development session. After an interrupted
session or failed restoration, recover with:

```bash
scripts/dev.py restore
```

Imported JS and QML dependencies can remain cached by the running engine. If a
rescan appears to keep old behavior, deliberately run `omarchy restart shell`;
always include a fresh-shell check before a release. Successful file copying
is not by itself proof that cached code was replaced. Restart is not automatic
on each save.

The recovery journal lives under `$XDG_STATE_HOME/omarchy/development`
(default `~/.local/state/omarchy/development`) and is kept until restoration
succeeds. Unmanaged folders using the development ID are never overwritten.
Stop/disable pre-existing external auto-deployers before adopting this workflow.
Neither this tool nor the plugin requires another source repository.

This is not a sandbox: development uses your current shell process and can
affect its shared configuration, browser reads, network and desktop services.
Production **files** and Home preferences are separate, but bar layout and other
global configuration are not isolated. Use a VM/separate graphical session for
risky changes. Never edit packaged Omarchy files or symlink a plugin folder.

## Native tests and production lifecycle

`tests/verify_*.py` deliberately operate the desktop and may restart the shell;
run them only in an idle graphical test session, never on every save:

```bash
python3 -B tests/verify_launcher_layout.py
python3 -B tests/verify_launcher_performance.py
python3 -B tests/verify_home.py
```

These require `wtype`; the media fixture additionally needs `python-dbus` and
`python-gobject` matching the selected Python. The fixture inherits that same
interpreter through `sys.executable`. Do not globally pip-install native system
bindings. Native scripts target production by default; set `DICEY_PLUGIN_ID` to
`dicey.home.dev` to inspect a development session.

Production is installed and updated deliberately, independently of source edits:

```bash
omarchy plugin add https://github.com/dicey-dev/dicey-home.git
omarchy plugin enable dicey.home
omarchy plugin update dicey.home
# Restore stock before removing:
omarchy plugin enable omarchy.menu
omarchy plugin remove dicey.home
```

`add` is for a fresh install; `update` requires a Git-managed installed copy.
Manually copied existing installs need explicit migration, not silent overwrites.
Preserve `$XDG_STATE_HOME/omarchy/dicey.home` preferences on removal. See
[Releases and marketplace checklist](publishing.md) for upstream notices,
SemVer, supported compatibility, verification and submission values. Repeat
native takeover/dmenu, click/Escape, summon/hide, fallback and lifecycle checks
for behavior changes. Clone metadata deliberately supports replacement routing.
Marketplace validation is not a security audit. Never commit browser databases or tokens.
