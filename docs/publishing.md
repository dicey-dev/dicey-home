# Releases and marketplace checklist

## Versioning

This is the **v0.1.0 alpha baseline**, before notification-hub development.
A 0.x version is not a stability or marketplace-approval claim.

`manifest.json` is the single version source of truth. Use alpha `0.x.y`
`MAJOR.MINOR.PATCH`: major for breaking behavior/configuration, minor for
compatible features, patch for compatible fixes. The permanent plugin ID is
`dicey.home`; it does not change for new releases.

```bash
python3 scripts/version.py check
python3 scripts/version.py patch "Describe the compatible fix."
# Choose minor for a new compatible feature, or major for a breaking change.
tests/run.sh
tests/run.sh --compat
```

The bump command updates the manifest and dated changelog together; it does not
commit/tag/publish or touch production. Review and merge the release PR, then
tag its exact tested main commit `vX.Y.Z` and publish matching GitHub release
notes. Never move/reuse an existing release tag.

## Install/update semantics

The README's standard Omarchy install needs no build, custom installer or dev
tooling. `omarchy plugin update dicey.home` fetches `origin HEAD` (the remote
default branch), shows changes and fast-forwards to `FETCH_HEAD`, regardless of
the local tracking branch. **It is not a SemVer resolver.**

For a rollback snapshot, review and switch the installed checkout to a release:

```bash
PLUGIN_DIR="$HOME/.config/omarchy/plugins/dicey.home"
git -C "$PLUGIN_DIR" fetch --tags origin
git -C "$PLUGIN_DIR" switch --detach v0.1.0
omarchy-shell shell rescanPlugins
```

Detaching is **not an update-resistant pin**: both
`omarchy plugin update dicey.home` and the all-plugin `omarchy plugin update`
can advance this checkout to the remote default HEAD. There is no pin/exclusion
option in this Omarchy version; avoid both updater forms to hold the snapshot.
Switching back to `main` is optional for updates, not a protection mechanism.
Never discard local edits to force an update. Service changes may require an explicit
`omarchy restart shell`; normal QML edits use the shell's native reload.

For an existing manually copied install: stop development, enable `omarchy.menu`,
back up the existing directory outside the scan root, use Omarchy removal, then
perform a fresh standard install. Removing a non-Git copy backs it up. Preferences
under XDG state are preserved. These are deliberate production actions, not
something a source edit or test runner performs automatically.

## Guide compliance and release evidence

References: [development guide](https://plugins.omarchy.org/develop.html),
[runtime contract](https://github.com/omacom/omarchy/blob/quattro/shell/README.md),
[publishing guide](https://plugins.omarchy.org/publish.html).

- Public single-plugin repository; root manifest, README and both license notices.
- Permanent namespaced ID, safe existing relative entry points, real files and
  no symlinks. `menu` and `bar-widget` are intentionally separate shell entry
  points, not an incorrectly declared nested details panel.
- `Launcher.qml` exposes the menu's opened/open/close lifecycle. The bar widget
  uses the plugin's own ID. `clonedFrom` is deliberately retained to route stock
  menu shortcuts to Home and restore the built-in on disable/removal, as the
  shell's clone contract documents. It is not a temporary author/ID placeholder.
- All runtime helpers, dependencies, browser/network reads, state writes,
  privilege boundaries and user-triggered actions are disclosed. No privileged
  setup, background installer, remote build or bundled executable is required.
- Manifest validation, system `qmllint`, unit tests and actual installed-menu
  transformation checks run before release. Qt 6.12 accent bindings are qualified
  explicitly through `Commons.Color`, rather than the ambiguous global name.
- `python3 -B tests/verify_install.py` uses the official add/update/remove tools
  with temporary HOME/local Git and **stubbed desktop IPC**. This is filesystem
  packaging proof, not a claim of isolated native UI coverage.
- Native `.dev` checks exercise menu/dashboard loading, arithmetic, state
  separation, invalid updates, edited-source deployment and activation restore.
  Live layout tests cover Escape/open/close and restart persistence. Supported
  host: Omarchy 4.0.6, Qt 6.12, Quickshell 0.3.2. Other versions are not promised.

No private preview is required; the marketplace can use its fallback image.
Marketplace validation and a static baseline are not a security certification.
Browser configuration remains read-only, but typed search queries can reach the
configured provider; users should read the privacy disclosure before enabling.

## Form values (owner submits)

- Repository: `https://github.com/dicey-dev/dicey-home`
- Category: `Productivity`
- Tags: `launcher`, `quickshell`, `system`
- Notes: Native command palette and dashboard; standard Omarchy install, no
  build. Requires the tested Quattro menu contract; unsupported anchors fall
  back to the stock menu. See README privacy and dependency disclosures.

Use the [submission form](https://github.com/omacom/omarchy-plugin-marketplace/issues/new?template=submit-plugin.yml).
The owner confirms ownership/permission and the checklist; this project does
not submit on their behalf. Maintainers still review/approve the listing and any
declared capabilities. Do not claim publication merely because local checks pass.
