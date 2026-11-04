# Initial-import security review

Reviewed before committing the standalone import. This is a focused source
review, not an independent security audit or a sandbox guarantee.

## Reviewed boundaries

- Calculator/parser bounds, dynamic QML transformation, search URL handling,
  subprocess arguments, browser preference/database access, telemetry helpers,
  media/system actions, preference writes, tests, and mockup scripting.
- Arithmetic uses a bounded parser, not `eval`. Query strings and URLs are
  passed as subprocess arguments, not interpolated into shell commands. The
  calculator clipboard pipeline uses the shell's quoting helper.
- QML transformation consumes the locally installed menu and trusted local
  plugin code; it does not evaluate fetched search-result content as code.
- Browser SQLite access uses `mode=ro` and parameterized queries. It reads the
  selected search-provider configuration, not browsing history or cookies.
- Preview requests are limited to 512 KiB per response with a five-second
  socket timeout. Search URLs/results are limited to HTTP(S); normal provider
  redirects still apply. Queries go to the configured engine while typing,
  and a configured HTTP endpoint is not transport-encrypted. This is an
  intentional privacy boundary, not anonymous or offline search.
- Result labels and media titles/artists use plain-text rendering. Artwork can
  load URLs supplied by MPRIS players. Trust the desktop session and players.
- System actions dispatch an explicit action set; volume is range-checked in
  both QML and Python. Layout preferences are written atomically to the plugin's
  XDG state location, not to browser configuration or the source checkout.
- Mockups simulate commands rather than executing them; clipboard access is a
  user action. Live verification scripts are separate from unit-test discovery
  because they type into the desktop and may restart the shell.

## Checks

Manifest validation, both Node test suites, and all 20 Python unit tests passed.
Every staged commit receives credential-pattern/file-mode/generated-file and
applicable syntax/whitespace checks in addition to manual boundary review.
Network/browser tests use mocks or temporary fixtures. No privileged installer,
download-to-shell pipeline, or embedded credential was identified.

## Release follow-up

The publication-readiness pass preserves the complete upstream MIT notice,
declares mixed Apache/MIT licensing, and adds SemVer/changelog checks and official
install/update/remove filesystem verification. Qt 6.12 accent references are
explicitly qualified. Native menu/dashboard, Escape/reopen, layout persistence
through shell restart and `.dev` restoration were tested on Omarchy 4.0.6 /
Qt 6.12 / Quickshell 0.3.2; broader versions and clean-VM certification are not
claimed. See [publishing evidence](publishing.md). Existing lint warnings are
not suppressed.

Clone metadata deliberately retains supported built-in menu routing/restoration;
it does not change the author or permanent plugin ID. The dev tool preserves
production files and uses a separate preference ID, but is not a sandbox. Version
tooling does not publish/install. The same-user diagnostic IPC exposes current
menu/search state; it is not a security boundary against other session processes.
