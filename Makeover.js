// Small, checked adaptations of the installed menu. An upstream shape change
// rejects the entire makeover so Launcher.qml can still mount the stock menu.
// The wrapper resolves MenuModel's import first; every other dependency stays
// attached to the running shell's qs.Commons / qs.Ui module tree.
function transform(source, searchUrl, helperUrl) {
  function replace(before, after) {
    if (source.indexOf(before) < 0 || source.indexOf(before) !== source.lastIndexOf(before))
      throw new Error("Unsupported Omarchy menu anchor: " + before.slice(0, 100))
    source = source.replace(before, after)
  }
  var pluginDirectory = searchUrl.slice(0, searchUrl.lastIndexOf("/"))
  replace('import QtQuick', 'import QtQuick\nimport "' + searchUrl + '" as DiceySearch\nimport "' + pluginDirectory + '" as Dicey')
  replace('  function open(payloadJson) {', '  function open(payloadJson) {\n    diceyProfile.refresh()\n    root.diceyProbeEngine()')
  replace('  property string filterText: ""', `  property string filterText: ""
  onFilterTextChanged: root.diceyQueueWeb()
  readonly property bool diceySearchActive: !root.dmenuActive && (root.activeMenu === "root" || root.activeMenu === "apps")
  readonly property int diceyFooterHeight: root.dmenuActive ? 0 : Style.space(48)
  readonly property bool diceyFullscreen: !!(root.shell && root.shell.launcherFullscreen)
  readonly property bool diceyFullscreenActive: root.diceyFullscreen && !root.dmenuActive && root.diceySearchActive && !root.deleteConfirmOpen
  onDiceyFullscreenActiveChanged: {
    // A search pins the normal card's top edge. Recompute that geometry when
    // switching layouts rather than carrying a fullscreen top into normal mode.
    panel.cardTop = -1
    panel.maxRowsHeight = -1
    root.layoutSerial++
    Qt.callLater(function() {
      if (!root.opened) return
      if (root.diceyFullscreenActive) diceyHome.focusSearch()
      else keyCatcher.forceActiveFocus()
      root.revealCursor()
    })
  }
  property var diceyWebRows: []
  property var diceyCache: ({})
  property string diceyWebQuery: ""
  property string diceyWebStatus: ""
  property string diceyHelper: ${JSON.stringify(helperUrl)}
  property string diceyBrowserHelper: ${JSON.stringify(pluginDirectory + "/browser_search.py")}
  property var diceyEngine: ({name: "Browser default", browser: "Default browser", key: "", ready: false})
  property bool diceyEngineLoaded: false
  property var diceyControlSnapshot: []
  property var diceyPendingControlRows: []
  property string diceyControlSnapshotQuery: ""
  property string diceyPendingControlQuery: ""
  property bool diceyControlPublishQueued: false
  property int diceyControlPublishCount: 0

  function diceyQueueControlRows(rows, query) {
    root.diceyPendingControlRows = rows
    root.diceyPendingControlQuery = query
    if (root.diceyControlPublishQueued) return
    root.diceyControlPublishQueued = true
    Qt.callLater(root.diceyPublishControlRows)
  }
  function diceyPublishControlRows() {
    if (!root.diceyControlPublishQueued) return
    root.diceyControlPublishQueued = false
    var rows = []
    for (var i = 0; i < root.diceyPendingControlRows.length; i++) {
      var row = root.diceyPendingControlRows[i]
      rows.push({index: i, kind: row.kind, label: row.label, detail: row.detail, appId: row.appId, appIcon: row.appIcon || "", itemId: row.itemId})
    }
    root.diceyControlSnapshotQuery = root.diceyPendingControlQuery
    root.diceyControlSnapshot = rows
    root.diceyControlPublishCount++
  }
  function diceyControlRows() { return root.diceyControlSnapshot }
  function diceyControlIndex(id) {
    for (var i = 0; i < displayModel.count; i++) {
      if (displayModel.get(i).itemId === id) return i
    }
    return -1
  }
  function diceyActivateControlRow(id, fromPointer) {
    var index = root.diceyControlIndex(id)
    if (index < 0) return false
    root.activateIndex(index, fromPointer)
    return true
  }
  function diceyHomeAction(action) { return diceyHome.runAction(action) }

  function diceyProbeEngine() {
    root.diceyEngineLoaded = false
    root.diceyWebRows = []
    if (diceyEngineProc.running) diceyEngineProc.running = false
    diceyEngineProc.collected = ""
    diceyEngineProc.command = ["/usr/bin/python3", "-B", decodeURIComponent(root.diceyBrowserHelper.replace(/^file:\\/\\//, "")), "--describe"]
    diceyEngineProc.running = true
  }

  function diceyQueueWeb() {
    diceyDebounce.stop()
    // Terminating obsolete requests also prevents queued keystrokes from
    // consuming a subprocess each. Late output is checked again on exit.
    if (diceyWebProc.running) diceyWebProc.running = false
    root.diceyWebRows = []
    root.diceyWebQuery = root.filterText.trim().replace(/^\\?\\s*/, "")
    root.diceyWebStatus = ""
    if (!root.opened || !root.diceySearchActive || root.diceyWebQuery.length < 3 || DiceySearch.isArithmetic(root.filterText)) return
    if (!root.diceyEngineLoaded) { root.diceyWebStatus = "resolving"; return }
    if (!root.diceyEngine.ready) { root.diceyWebStatus = "unavailable"; return }
    if (root.diceyEngine.mode === "native") { root.diceyWebStatus = "native"; return }
    var cached = root.diceyCache[root.diceyEngine.key + ":" + root.diceyWebQuery]
    if (cached && Date.now() - cached.time < 300000) {
      root.diceyWebRows = cached.rows
      root.diceyWebStatus = cached.status
    } else {
      root.diceyWebStatus = "loading"
      diceyDebounce.restart()
    }
  }

  function diceyRefreshWeb() {
    // A network response must not move the keyboard cursor to a different row.
    var selectedId = displayModel.count > root.selectedIndex ? displayModel.get(root.selectedIndex).itemId : ""
    root.rebuildDisplay()
    for (var i = 0; i < displayModel.count; i++) {
      if (displayModel.get(i).itemId === selectedId) { root.selectedIndex = i; break }
    }
    root.revealCursor()
  }

  function diceyAppendSearch(rows, query) {
    if (!root.diceySearchActive || !query) return rows
    var answer = DiceySearch.calculate(query)
    if (answer !== null) rows.unshift(DiceySearch.row("calculator", answer, query + "  ·  Enter to copy answer", answer, "calculator"))
    if (!DiceySearch.isArithmetic(query)) {
      rows.push(DiceySearch.row("web-search", "Search the web for “" + query.replace(/^\\?\\s*/, "") + "”",
        !root.diceyEngineLoaded ? "Detecting your browser's search engine…" : !root.diceyEngine.ready ? "Search setting unavailable · Enter to retry" : root.diceyEngine.name + " · " + root.diceyEngine.browser + (root.diceyWebStatus === "unavailable" ? " · Preview unavailable" : ""),
        DiceySearch.searchQuery(query), "web"))
      for (var i = 0; i < root.diceyWebRows.length; i++) {
        var result = root.diceyWebRows[i]
        if (DiceySearch.safeUrl(result.url)) rows.push(DiceySearch.row("web-result", result.title, result.detail, result.url, "web"))
      }
    }
    return rows
  }

  function diceyState() {
    var rows = []
    for (var i = 0; i < Math.min(displayModel.count, 20); i++) {
      var row = displayModel.get(i)
      rows.push({id: row.itemId, kind: row.kind, label: row.label, detail: row.detail, action: row.action})
    }
    return {opened: root.opened, route: root.activeMenu, mode: root.mode, filter: root.filterText,
      width: root.cardWidth, height: root.cardHeight, screenWidth: panel.width, screenHeight: panel.height,
      screen: panel.screen ? panel.screen.name : "", cardTop: panel.effectiveCardTop,
      fullscreen: root.diceyFullscreen,
      layout: root.dmenuActive ? "compact" : root.diceyFullscreenActive ? "home" : "normal",
      home: diceyHome.inspect(),
      count: displayModel.count, rows: rows,
      selected: root.selectedIndex, webStatus: root.diceyWebStatus, webEngine: root.diceyEngine,
      background: String(root.background), foreground: String(root.foreground), accent: String(Color.accent),
      profile: {username: diceyProfile.username, initials: diceyProfile.initials, picture: diceyProfile.picturePath, ready: diceyProfile.pictureReady}}
  }

  Timer {
    id: diceyDebounce
    interval: 450
    onTriggered: {
      if (diceyWebProc.running) { restart(); return }
      diceyWebProc.query = root.diceyWebQuery
      diceyWebProc.collected = ""
      diceyWebProc.command = ["/usr/bin/python3", "-B", decodeURIComponent(root.diceyHelper.replace(/^file:\\/\\//, "")), diceyWebProc.query]
      diceyWebProc.running = true
    }
  }

  Process {
    id: diceyEngineProc
    property string collected: ""
    stdout: SplitParser { onRead: function(line) { diceyEngineProc.collected += line } }
    onExited: function(code, status) {
      if (status !== 0) return
      var engine
      try { engine = JSON.parse(diceyEngineProc.collected) } catch (error) { engine = {name: "Browser default", browser: "Default browser", key: "", ready: false} }
      root.diceyEngine = engine
      root.diceyEngineLoaded = true
      root.diceyQueueWeb()
      if (root.opened) root.diceyRefreshWeb()
    }
  }

  Process {
    id: diceyWebProc
    property string query: ""
    property string collected: ""
    stdout: SplitParser { onRead: function(line) { diceyWebProc.collected += line } }
    onExited: function(code, status) {
      if (!root.opened || !root.diceySearchActive || diceyWebProc.query !== root.diceyWebQuery || status !== 0) return
      var result
      try { result = JSON.parse(diceyWebProc.collected) } catch (error) { result = {rows: [], status: "unavailable"} }
      if (result.engine && result.engine.ready) root.diceyEngine = result.engine
      root.diceyWebRows = code === 0 && Array.isArray(result.rows) ? result.rows : []
      root.diceyWebStatus = code === 0 ? result.status : "unavailable"
      var cache = root.diceyCache
      if (Object.keys(cache).length >= 30) cache = ({})
      cache[root.diceyEngine.key + ":" + root.diceyWebQuery] = {time: Date.now(), rows: root.diceyWebRows, status: root.diceyWebStatus}
      root.diceyCache = cache
      root.diceyRefreshWeb()
    }
  }`)
  replace('  onOpenedChanged: if (!opened) { deleteConfirmOpen = false; deleteTarget = null }',
    '  onOpenedChanged: if (!opened) { deleteConfirmOpen = false; deleteTarget = null; diceyDebounce.stop(); diceyWebProc.running = false }')
  replace('  property int headerHeight: Math.max(Style.space(34), Style.font.title + Style.spacing.controlPaddingY * 2)',
    '  property int headerHeight: root.dmenuActive ? Math.max(Style.space(34), Style.font.title + Style.spacing.controlPaddingY * 2) : Style.space(104)')
  replace('  property int dividerHeight: Style.space(17)', '  property int dividerHeight: Style.space(28)')
  replace('  property int cardWidth: Math.min(root.dmenuActive ? Style.space(root.dmenuWidth) : ((root.activeMenu === "trigger.capture.screenrecord" || root.activeMenu === "style.font") ? Style.space(520) : Style.space(300)), panel.width - Style.gapsOut * 2)',
    '  property int cardWidth: root.diceyFullscreenActive ? panel.width : Math.min(root.dmenuActive ? Style.space(root.dmenuWidth) : Style.space(720), panel.width - Math.max(Style.gapsOut * 2, Style.space(32)))')
  replace('  property int visibleRowsHeight: root.dmenuActive ? dmenuRowListHeight(layoutSerial, displayModel.count, filterText) : rowListHeight(layoutSerial, displayModel.count, filterText, searchDivider)',
    '  property int visibleRowsHeight: root.diceyFullscreenActive ? Math.max(0, panel.height - card.contentTopInset - card.contentBottomInset - root.headerHeight - root.contentSpacing * 2 - root.diceyFooterHeight) : root.dmenuActive ? dmenuRowListHeight(layoutSerial, displayModel.count, filterText) : rowListHeight(layoutSerial, displayModel.count, filterText, searchDivider)')
  replace('  property int cardHeight: root.dmenuActive', '  property int cardHeight: root.diceyFullscreenActive ? panel.height : root.dmenuActive')
  // Keep the stock Overlay/Ignore layer: Dicey Home covers bar exclusion
  // zones as well as the workspace, without changing the bar configuration.
  replace('    readonly property int effectiveCardTop: cardTop >= 0 ? cardTop : centeredTop',
    '    readonly property int effectiveCardTop: root.diceyFullscreenActive ? 0 : cardTop >= 0 ? cardTop : centeredTop')
  replace('      height: Math.min(root.cardHeight, panel.height - Style.gapsOut - panel.effectiveCardTop)',
    '      height: root.diceyFullscreenActive ? panel.height : Math.min(root.cardHeight, panel.height - Style.gapsOut - panel.effectiveCardTop)')
  replace('      radius: root.cornerRadius\n      anchors.horizontalCenter: parent.horizontalCenter',
    '      radius: root.diceyFullscreenActive ? 0 : root.cornerRadius\n      anchors.horizontalCenter: parent.horizontalCenter')
  replace('    BorderSurface {\n      id: card', `    Dicey.Home {
      id: diceyHome
      x: 0; y: 0
      width: panel.width
      height: panel.height
      visible: root.diceyFullscreenActive
      menu: root
      controller: root.shell ? root.shell.homeController : null
    }
    Connections {
      target: keyCatcher
      function onActiveFocusChanged() {
        if (keyCatcher.activeFocus && root.diceyFullscreenActive) Qt.callLater(diceyHome.focusSearch)
      }
    }
    BorderSurface {
      id: card
      visible: !root.diceyFullscreenActive`)
  replace('          if (event.key === Qt.Key_Delete) {', `          if (!root.dmenuActive && event.key === Qt.Key_F && event.modifiers === (Qt.ControlModifier | Qt.ShiftModifier)) {
            if (!event.isAutoRepeat) root.shell.toggleLauncherLayout()
            event.accepted = true
          } else if (event.key === Qt.Key_Delete) {`)
  replace('    : Math.min(contentMargin * 2 + headerHeight + contentSpacing + visibleRowsHeight, panel.height - Style.gapsOut * 2)',
    '    : Math.min(contentMargin * 2 + headerHeight + contentSpacing * 2 + visibleRowsHeight + diceyFooterHeight, panel.height - Style.gapsOut * 2)')
  replace('var available = panel.height - top - Style.gapsOut - root.contentMargin * 2 - root.headerHeight - root.contentSpacing',
    'var available = panel.height - top - Style.gapsOut - root.contentMargin * 2 - root.headerHeight - root.contentSpacing * 2 - root.diceyFooterHeight')
  replace('return Math.min(available, Math.round(panel.height * 0.7))',
    'return Math.min(available, Math.round(panel.height * 0.7), root.dmenuActive ? panel.height : Style.space(430))')
  replace('if (row.section === "drilldown" && previousSection !== "drilldown") total += root.dividerHeight',
    'if (row.section && row.section !== previousSection) total += root.dividerHeight')
  replace('    for (var k = 0; k < rows.length; k++) displayModel.append(rows[k])',
    '    rows = root.diceyAppendSearch(rows, query)\n    for (var k = 0; k < rows.length; k++) displayModel.append(rows[k])\n    root.diceyQueueControlRows(rows, query)')
  replace('            model: displayModel\n            clip: true',
    '            model: root.diceyFullscreenActive ? null : displayModel\n            clip: true')
  replace('  function revealCursor() {', '  function revealCursor() {\n    if (root.diceyFullscreenActive) return')
  replace('    if (row.kind === "menu" || row.kind === "link") {', `    if (row.kind === "calculator") {
      Quickshell.execDetached(["bash", "-c", "printf %s " + Util.shellQuote(row.action) + " | wl-copy"])
      root.cancel()
    } else if (row.kind === "web-search") {
      Quickshell.execDetached(["/usr/bin/python3", "-B", decodeURIComponent(root.diceyBrowserHelper.replace(/^file:\\/\\//, "")), "--open", row.action])
      root.cancel()
    } else if (row.kind === "web-result") {
      if (DiceySearch.safeUrl(row.action)) Quickshell.execDetached(["omarchy", "launch", "browser", row.action])
      root.cancel()
    } else if (row.kind === "menu" || row.kind === "link") {`)
  replace(`          Text {
            textFormat: Text.PlainText
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            text: root.filterText || (root.dmenuActive ? (root.dmenuPrompt + "…") : ((root.item(root.activeMenu) ? (root.item(root.activeMenu).title || root.item(root.activeMenu).label) : "Go") + "…"))
            color: root.foreground
            opacity: root.filterText ? 1 : 0.58
            font.family: root.fontFamily
            font.pixelSize: Style.font.heading
            elide: Text.ElideRight
          }`, `          Text {
            visible: !root.dmenuActive
            anchors.left: parent.left
            anchors.verticalCenter: diceyProfile.verticalCenter
            text: "DICEY  /  " + (root.activeMenu === "root" ? "COMMAND PALETTE" : root.pathFor(root.activeMenu).toUpperCase())
            textFormat: Text.PlainText
            color: Color.accent
            font.family: root.fontFamily
            font.pixelSize: Style.font.caption
            font.weight: Font.DemiBold
            font.letterSpacing: Style.space(1)
            width: Math.max(0, parent.width - diceyProfile.width - Style.space(20))
            elide: Text.ElideRight
          }
          Dicey.Profile {
            id: diceyProfile
            visible: !root.dmenuActive
            anchors.right: parent.right
            anchors.top: parent.top
            width: Math.min(implicitWidth, parent.width * 0.42)
            height: implicitHeight
          }
          Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: root.dmenuActive ? parent.height : Style.space(64)
            radius: root.cornerRadius
            color: root.dmenuActive ? "transparent" : Util.alpha(root.foreground, 0.045)
            border.width: root.dmenuActive ? 0 : Style.spacing.hairline
            border.color: Util.alpha(Color.accent, 0.35)
            Text {
              id: diceySearchIcon
              visible: !root.dmenuActive
              anchors.left: parent.left
              anchors.leftMargin: Style.space(18)
              anchors.verticalCenter: parent.verticalCenter
              text: "⌕"
              font.family: root.fontFamily
              font.pixelSize: Style.font.displayLarge
              color: Color.accent
            }
            Text {
              textFormat: Text.PlainText
              anchors.left: root.dmenuActive ? parent.left : diceySearchIcon.right
              anchors.leftMargin: root.dmenuActive ? 0 : Style.space(14)
              anchors.right: parent.right
              anchors.rightMargin: root.dmenuActive ? 0 : Style.space(18)
              anchors.verticalCenter: parent.verticalCenter
              text: root.filterText || (root.dmenuActive ? root.dmenuPrompt + "…" : (root.diceySearchActive ? "Search apps, commands, web or calculate…" : "Search " + (root.item(root.activeMenu) ? root.item(root.activeMenu).label.toLowerCase() : "menu") + "…"))
              color: root.foreground
              opacity: root.filterText ? 1 : 0.58
              font.family: root.fontFamily
              font.pixelSize: Style.font.heading
              elide: Text.ElideRight
            }
          }`)
  replace('              height: section === "drilldown" ? root.dividerHeight : 0\n              visible: section === "drilldown"',
    '              height: section ? root.dividerHeight : 0\n              visible: !!section')
  replace('                color: Util.alpha(root.foreground, 0.2)\n              }\n            }', `                color: Util.alpha(root.foreground, 0.12)
              }
              Text {
                anchors.left: parent.left
                anchors.leftMargin: Style.space(12)
                anchors.verticalCenter: parent.verticalCenter
                text: section === "web" ? "WEB RESULTS" : section === "calculator" ? "CALCULATOR" : "MORE MATCHES"
                color: Color.accent
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
                font.letterSpacing: Style.space(1)
                Rectangle { anchors.fill: parent; anchors.margins: -Style.space(4); color: root.background; z: -1 }
              }
            }`)
  replace('                visible: false\n                width: Style.space(4)',
    '                visible: row.hasCursor && !root.dmenuActive\n                width: Style.space(3)')
  replace('                color: root.selectedBackground\n                anchors.left: parent.left',
    '                color: Color.accent\n                anchors.left: parent.left')
  replace('                  color: root.foreground\n                  opacity: 0.52',
    '                  color: row.hasCursor ? root.selectedText : root.foreground\n                  opacity: 0.65')
  replace('                width: Style.space(14)\n                anchors.right: parent.right',
    '                width: Style.space(26)\n                anchors.right: parent.right')
  replace('                  text: row.kind === "menu" || row.kind === "link" ? "›" : ""',
    '                  text: row.kind === "menu" || row.kind === "link" ? "›" : row.kind === "calculator" ? "⧉" : row.kind.indexOf("web-") === 0 ? "↗" : row.hasCursor ? "↵" : ""')
  replace('                  opacity: row.kind === "menu" || row.kind === "link" ? 0.36 : 0',
    '                  opacity: 0.55')
  replace(`        Item {
          width: parent.width
          height: 0
        }`, `        Item {
          width: parent.width
          height: root.diceyFooterHeight
          visible: !root.dmenuActive
          Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; height: Style.spacing.hairline; color: Util.alpha(root.foreground, 0.12) }
          Text {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.topMargin: Style.space(5)
            text: root.diceyWebStatus === "loading" ? "Searching the web…" : displayModel.count + " results  ·  " + (root.diceySearchActive ? "try 24 * 7 or ? a web search" : "Backspace to go back")
            color: root.foreground
            opacity: 0.55
            font.family: root.fontFamily
            font.pixelSize: Style.font.caption
            width: parent.width
            elide: Text.ElideRight
          }
          Text {
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            anchors.bottomMargin: Style.space(4)
            text: "↑↓ move    ↵ select    esc close"
            color: root.foreground
            opacity: 0.55
            font.family: root.fontFamily
            font.pixelSize: Style.font.caption
            width: Math.max(0, parent.width - diceyLayoutToggle.width - Style.space(12))
            elide: Text.ElideRight
          }
          Rectangle {
            id: diceyLayoutToggle
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            width: diceyLayoutLabel.implicitWidth + Style.space(16)
            height: Style.space(24)
            radius: Math.min(root.cornerRadius, Style.space(6))
            enabled: !root.deleteConfirmOpen
            opacity: enabled ? 1 : 0.45
            color: Util.alpha(Color.accent, diceyLayoutMouse.containsMouse ? 0.18 : 0.08)
            border.width: Style.spacing.hairline
            border.color: Util.alpha(Color.accent, 0.3)
            Text {
              id: diceyLayoutLabel
              anchors.centerIn: parent
              text: "Ctrl+Shift+F · Dicey Home"
              color: Color.accent
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
            }
            MouseArea {
              id: diceyLayoutMouse
              anchors.fill: parent
              hoverEnabled: true
              cursorShape: Qt.PointingHandCursor
              onClicked: root.shell.toggleLauncherLayout()
            }
          }
        }`)
  return source
}

if (typeof module !== "undefined") module.exports = {transform: transform}
