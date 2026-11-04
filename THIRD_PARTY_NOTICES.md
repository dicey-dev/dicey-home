# Third-party notices

Dicey-specific code is distributed under the Apache License 2.0 in `LICENSE`.
This does not replace the following upstream notice.

## Omarchy — MIT

The bar widget and menu-adaptation code include or adapt Omarchy plugin
patterns and menu fragments. `Launcher.qml` loads the installed Omarchy
`Menu.qml`/`MenuModel.js` at runtime rather than bundling a frozen menu engine.
Preserve this notice when redistributing derived portions.

- Upstream: https://github.com/omacom/omarchy
- Runtime/source reference: Omarchy 4.0.6; upstream `quattro` reference inspected
  at `5eb922f137422ff32a90869a9ba47525a428792d` (not a claim that every adapted
  fragment originated at that exact revision).
- Upstream license: https://github.com/omacom/omarchy/blob/quattro/LICENSE

Copyright (c) David Heinemeier Hansson

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Qt, Quickshell, Omarchy and system commands are separately installed runtime
dependencies. User avatars, browser databases, MPRIS artwork, app icons and
theme fonts are read from the host, not distributed as repository assets.
The HTML mockup is original illustrative code and is not a shipped web runtime.
