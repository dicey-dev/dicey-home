import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Commons as Commons
import "HomeModel.js" as Model
import ".." as Plugin

FocusScope {
  id: home
  readonly property var paneOwner: home
  property var menu: null
  property var controller: null
  property bool editing: false
  property var tiles: []
  property var focusedTile: null
  property int iconRevision: 0
  readonly property bool active: visible && menu && menu.opened
  readonly property string query: search.text
  readonly property bool allApps: menu && menu.activeMenu === "apps"
  readonly property bool resultsMode: query.trim().length > 0 || allApps
  readonly property var results: menu ? menu.diceyControlSnapshot : []
  readonly property var metrics: services.metrics
  readonly property real gap: Style.space(10)
  readonly property real unit: Math.max(Style.space(90), (viewport.height - board.y - Style.space(48) - gap * 3) / 4.3)
  readonly property int columns: width >= Style.space(1250) ? 4 : width >= Style.space(780) ? 2 : 1
  readonly property color muted: Qt.tint(Color.menu.background, Util.alpha(Color.menu.text, 0.82))
  readonly property color onAccent: Model.ink(Commons.Color.accent)
  focus: active
  onActiveChanged: {
    if (active) { syncFilter(); portrait.refresh(); services.refreshWorkspaceIcons(); Qt.callLater(focusSearch) }
    else { if (applyFilter) applyFilter.stop(); editing = false }
  }
  onMenuChanged: Qt.callLater(syncFilter)
  function syncFilter() {
    if (!menu) return
    applyFilter.stop()
    if (search.text !== menu.filterText) search.text = menu.filterText
  }
  function flushFilter() {
    applyFilter.stop()
    if (!menu) return
    if (menu.filterText !== search.text) menu.setFilter(search.text)
    menu.diceyPublishControlRows()
  }
  function activateResult(id) {
    flushFilter()
    return menu ? menu.diceyActivateControlRow(id, true) : false
  }
  function resultDelegateCount() {
    var children = resultGrid.contentItem ? resultGrid.contentItem.children : [], count = 0
    for (var i = 0; i < children.length; i++) if (children[i].rowIndex !== undefined && children[i].visible) count++
    return count
  }
  function resolveIcon(icon) {
    return iconRevision >= 0 && icon && menu && menu.appLibrary ? String(menu.appLibrary.iconSource(icon)) : ""
  }
  function workspaceIcon(id) {
    var entry = services.workspaceIcons[id]
    return resolveIcon(entry ? entry.icon : "")
  }
  function loadedIcons() {
    var result = []
    for (var i = 0; i < tiles.length; i++) {
      var tile = tiles[i]
      if (tile && tile.visible && tile.iconSource) result.push({id: tile.tileId || tile.resultId, label: tile.title, source: tile.iconSource, ready: tile.iconReady})
    }
    return result
  }
  function focusSearch() { if (active) search.forceActiveFocus() }
  function isPinned(id) { return !controller || controller.hiddenTiles.indexOf(id) < 0 }
  function shows(id) { return editing || isPinned(id) }
  function groupVisible(ids) { return editing || ids.some(function(id) { return home.isPinned(id) }) }
  function groupWidth(index) {
    var available = board.width - board.spacing * (columns - 1)
    if (columns === 4) return available * [1, 1.36, 1.12, 0.84][index] / 4.32
    return available / columns
  }
  function registerTile(tile) { var next = tiles.slice(); next.push(tile); tiles = next }
  function unregisterTile(tile) {
    tiles = tiles.filter(function(item) { return item && item !== tile })
    if (focusedTile === tile) focusedTile = null
  }
  function tileFocused(tile) {
    focusedTile = tile
    if (menu && tile.rowIndex >= 0) {
      menu.selectedIndex = tile.rowIndex; menu.cursorActive = true
      resultGrid.currentIndex = tile.rowIndex
    }
  }
  function visibleTiles() {
    return tiles.filter(function(tile) {
      if (!tile || !tile.visible || !tile.enabled || tile.width <= 0 || tile.height <= 0) return false
      if (home.resultsMode) return tile.rowIndex >= 0 && tile.y + tile.height > resultGrid.contentY && tile.y < resultGrid.contentY + resultGrid.height
      return tile.rowIndex < 0
    }).sort(function(a, b) {
      var left = a.mapToItem(content, 0, 0), right = b.mapToItem(content, 0, 0)
      return Math.abs(left.y - right.y) > Style.space(8) ? left.y - right.y : left.x - right.x
    })
  }
  function navigate(dx, dy) {
    if (resultsMode) {
      flushFilter()
      if (!results.length) return
      var step = dy ? dy * resultGrid.tileColumns : dx
      var index = !focusedTile || focusedTile.rowIndex < 0 ? 0 : Math.max(0, Math.min(results.length - 1, resultGrid.currentIndex + step))
      resultGrid.currentIndex = index
      resultGrid.positionViewAtIndex(index, GridView.Contain)
      resultGrid.forceLayout()
      Qt.callLater(function() { if (home.active && resultGrid.currentItem) resultGrid.currentItem.forceActiveFocus() })
      return
    }
    var current = focusedTile, values = visibleTiles()
    if (!current || !current.visible) { if (values.length) values[0].forceActiveFocus(); return }
    var origin = current.mapToItem(home, current.width / 2, current.height / 2)
    var candidates = values.filter(function(tile) { return tile !== current }).map(function(tile) {
      var center = tile.mapToItem(home, tile.width / 2, tile.height / 2)
      return {tile: tile, x: center.x, y: center.y}
    })
    var next = Model.nearest(origin, candidates, dx, dy)
    if (next) {
      next.tile.forceActiveFocus()
      var point = next.tile.mapToItem(content, 0, 0)
      if (point.y < viewport.contentY) viewport.contentY = point.y
      else if (point.y + next.tile.height > viewport.contentY + viewport.height) viewport.contentY = Math.min(viewport.contentHeight - viewport.height, point.y + next.tile.height - viewport.height)
    }
  }
  function handleKey(event) {
    if (event.key === Qt.Key_F && event.modifiers === (Qt.ControlModifier | Qt.ShiftModifier)) {
      if (!event.isAutoRepeat && controller) { flushFilter(); controller.toggleHome() }
      event.accepted = true
    } else if (event.key === Qt.Key_Escape) {
      if (editing) editing = false
      else if (query) { applyFilter.stop(); search.text = ""; menu.setFilter("") }
      else if (allApps) menu.setActiveMenu("root", false)
      else menu.cancel()
      event.accepted = true
    } else if (event.key === Qt.Key_Slash && !search.activeFocus) { focusSearch(); event.accepted = true }
    else if (event.key === Qt.Key_Delete && focusedTile && focusedTile.rowIndex >= 0) {
      var id = focusedTile.resultId
      flushFilter()
      var index = menu.diceyControlIndex(id)
      if (index >= 0) { menu.selectedIndex = index; menu.cursorActive = true; menu.requestDeleteSelected() }
      event.accepted = true
    } else if (!search.activeFocus && [Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down].indexOf(event.key) >= 0) {
      navigate(event.key === Qt.Key_Left ? -1 : event.key === Qt.Key_Right ? 1 : 0, event.key === Qt.Key_Up ? -1 : event.key === Qt.Key_Down ? 1 : 0)
      event.accepted = true
    } else if (!search.activeFocus && event.text && event.text.length === 1 && event.text !== " " && event.modifiers === Qt.NoModifier) {
      search.text = query + event.text; applyFilter.restart(); focusSearch(); event.accepted = true
    }
  }
  Keys.onPressed: function(event) { home.handleKey(event) }
  function launch(command) { Quickshell.execDetached(command); menu.cancel(); return "ok" }
  function runAction(action) {
    if (action === "editor") return launch(["bash", "-c", 'omarchy launch editor "$(omarchy-cmd-terminal-cwd)"'])
    if (action === "terminal") return launch(["omarchy", "launch", "terminal"])
    if (action === "browser") return launch(["omarchy", "launch", "browser"])
    if (action === "files") return launch(["uwsm-app", "--", "xdg-open", Quickshell.env("HOME")])
    if (action === "notes") return launch(["uwsm-app", "--", "obsidian"])
    if (action === "activity") return launch(["omarchy", "launch", "tui", "btop"])
    if (action === "storage") return metrics.tools && metrics.tools.ncdu ? launch(["omarchy", "launch", "tui", "ncdu", Quickshell.env("HOME")]) : runAction("files")
    if (action === "network") { menu.openRoute("setup.network"); return "ok" }
    if (action === "appearance") { menu.openRoute("style.theme"); return "ok" }
    if (action === "lock") { menu.openRoute("system.lock"); return "ok" }
    if (action === "quiet") { Quickshell.execDetached(["omarchy", "toggle", "notification", "silencing"]); return "ok" }
    if (action === "wifi" && metrics.wifi !== null && metrics.wifi !== undefined) { Quickshell.execDetached(["nmcli", "radio", "wifi", metrics.wifi ? "off" : "on"]); return "ok" }
    if (action === "focus") return controller.focusControl("toggle")
    if (action === "focus:reset") return controller.focusControl("reset")
    if (action === "media:cycle") return services.cyclePlayer() ? "ok" : "unavailable"
    if (action.indexOf("player:") === 0) { services.selectedPlayer = action.slice(7); return "ok" }
    if (/^media:seek:\d+(\.\d+)?$/.test(action)) return services.seek(Number(action.slice(11))) ? "ok" : "unavailable"
    if (action.indexOf("media:") === 0) return services.media(action.slice(6)) ? "ok" : "unavailable"
    if (action === "mute" && metrics.audio && metrics.audio.available) { services.mute(); return "ok" }
    return "unavailable"
  }
  function inspect() {
    return {active: active, native: true, sampling: services.active, ready: !!metrics.memory,
      pinnedCount: Model.tileIds.length - (controller ? controller.hiddenTiles.length : 0), editing: editing,
      metrics: metrics, player: services.player ? {name: services.player.identity, dbusName: services.player.dbusName,
        title: services.player.trackTitle, artist: services.player.trackArtist, playing: services.player.isPlaying,
        canSeek: services.player.canSeek, canPlayPause: services.player.canTogglePlaying,
        position: services.player.position, length: services.player.length} : null,
      playerCount: services.players.length, resultsCount: results.length, navigationCount: visibleTiles().length,
      focusedTile: focusedTile ? focusedTile.tileId || "result:" + focusedTile.rowIndex : "",
      input: search.text, appliedQuery: menu ? menu.filterText : "", inputPending: applyFilter.running,
      resultPublications: menu ? menu.diceyControlPublishCount : 0,
      liveResultDelegates: resultDelegateCount(),
      appIcons: loadedIcons(),
      geometry: {width: width, height: height, viewportHeight: viewport.height, dashboardHeight: board.height, tileUnit: unit}}
  }

  Timer { id: applyFilter; interval: 35; onTriggered: home.flushFilter() }
  Connections {
    target: home.menu
    function onFilterTextChanged() { home.syncFilter() }
  }
  Connections {
    target: home.menu ? home.menu.appLibrary : null
    function onAppsChanged() { home.iconRevision++ }
  }
  HomeServices { id: services; active: home.active && !home.resultsMode }
  SystemClock { id: clock; precision: SystemClock.Seconds }
  component Heading: Column {
    property string title
    property string subtitle
    spacing: Style.space(3)
    Text { text: parent.title; color: Color.menu.text; font.family: Style.font.menuFamily; font.pixelSize: Style.font.heading }
    Text { text: parent.subtitle; color: home.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption }
  }
  component Tile: HomeTile {
    home: paneOwner
    editing: home.editing
    pinned: home.isPinned(tileId)
    visible: home.shows(tileId)
    Layout.fillWidth: true
    Layout.preferredHeight: home.unit
    onPinRequested: if (home.controller) home.controller.toggleTile(tileId)
  }
  Rectangle { anchors.fill: parent; color: Color.menu.background; MouseArea { anchors.fill: parent; onClicked: home.focusSearch() } }
  Flickable {
    id: viewport
    anchors.fill: parent
    anchors.margins: Style.space(40)
    anchors.bottomMargin: Style.space(55)
    contentWidth: width
    contentHeight: content.height
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
    Column {
      id: content
      width: viewport.width
      spacing: Style.space(10)
      RowLayout {
        width: parent.width
        height: Style.space(32)
        Text { text: "DICEY / DESKTOP EXPERIENCE"; color: home.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption; Layout.fillWidth: true }
        HomeButton { text: home.allApps ? "Home tiles" : "All apps"; onClicked: home.menu.setActiveMenu(home.allApps ? "root" : "apps", false) }
        HomeButton { text: home.editing ? "Done" : "Edit tiles"; visible: !home.resultsMode; onClicked: home.editing = !home.editing }
        HomeButton { text: "Restore tiles"; visible: home.editing; onClicked: home.controller.restoreTiles() }
        HomeButton { text: "Launcher  Ctrl+Shift+F"; onClicked: { home.flushFilter(); home.controller.toggleHome() } }
      }
      RowLayout {
        width: parent.width
        height: Style.space(88)
        Column {
          Layout.fillWidth: true
          Text { text: Qt.formatDateTime(clock.date, "dddd, d MMMM").toUpperCase(); color: home.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption }
          Text { text: "Dicey Home."; color: Color.menu.text; font.family: Style.font.menuFamily; font.pixelSize: Style.font.displayLarge * 1.8; font.weight: Font.Light; font.letterSpacing: -Style.space(2) }
        }
        Plugin.Profile { id: portrait; width: implicitWidth; height: implicitHeight }
      }
      TextField {
        id: search
        width: parent.width
        height: Style.space(52)
        text: ""
        onTextEdited: applyFilter.restart()
        placeholderText: "Search apps, commands, web, or calculate…"
        color: Color.menu.text
        placeholderTextColor: home.muted
        font.family: Style.font.menuFamily
        font.pixelSize: Style.font.heading
        leftPadding: Style.space(20)
        rightPadding: Style.space(20)
        selectByMouse: true
        background: Rectangle { color: Util.alpha(Color.menu.text, 0.035); radius: Math.min(Style.cornerRadius, Style.space(4)); border.width: Style.spacing.hairline; border.color: search.activeFocus ? Commons.Color.accent : Util.alpha(Color.menu.text, 0.18) }
        Keys.onPressed: function(event) {
          if (event.key === Qt.Key_Down) { home.navigate(0, 1); event.accepted = true }
          else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            home.flushFilter()
            if (home.resultsMode && home.results.length) home.menu.diceyActivateControlRow(home.results[0].itemId, false)
            event.accepted = true
          }
          else if (event.key === Qt.Key_Escape || (event.key === Qt.Key_F && event.modifiers === (Qt.ControlModifier | Qt.ShiftModifier))) home.handleKey(event)
        }
      }
      Column {
        id: resultsColumn
        visible: home.resultsMode
        width: parent.width
        spacing: Style.space(14)
        Heading { id: resultsHeading; title: home.query ? "Matches" : "Applications"; subtitle: home.results.length + " results · Enter opens the first match" }
        GridView {
          id: resultGrid
          width: parent.width
          height: Math.max(Style.space(180), viewport.height - resultsColumn.y - resultsHeading.height - parent.spacing)
          readonly property int tileColumns: Math.max(1, Math.floor(width / Style.space(230)))
          cellWidth: width / tileColumns
          cellHeight: home.unit + home.gap
          model: home.resultsMode ? home.results : []
          reuseItems: true
          cacheBuffer: cellHeight
          clip: true
          boundsBehavior: Flickable.StopAtBounds
          ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
          delegate: HomeTile {
              required property var modelData
              property bool pooled: false
              width: resultGrid.cellWidth - home.gap
              height: home.unit
              visible: !pooled
              GridView.onPooled: pooled = true
              GridView.onReused: pooled = false
              home: paneOwner
              rowIndex: modelData.index
              resultId: modelData.itemId
              title: modelData.label
              caption: modelData.kind
              detail: modelData.detail
              glyph: modelData.kind === "calculator" ? modelData.label : modelData.kind === "app" ? "▣" : "↗"
              iconSource: modelData.kind === "app" ? home.resolveIcon(modelData.appIcon) : ""
              onActivated: home.activateResult(modelData.itemId)
          }
        }
        Text { visible: home.results.length === 0; text: "No matches. Try another query."; color: home.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.body }
      }
      Flow {
        id: board
        visible: !home.resultsMode
        width: parent.width
        spacing: Style.space(24)
        Column {
          width: home.groupWidth(0)
          spacing: Style.space(12)
          visible: home.groupVisible(["editor", "terminal", "browser", "files", "notes"])
          Heading { title: "Workspace"; subtitle: "01 / YOUR DAILY TOOLS" }
          GridLayout {
            width: parent.width; columns: 2; rowSpacing: home.gap; columnSpacing: home.gap
            Tile {
              id: editorTile
              tileId: "editor"; title: "Editor"; caption: "DEFAULT EDITOR"; Layout.columnSpan: 2
              iconSource: home.workspaceIcon("editor"); iconSize: Style.space(60)
              Layout.preferredHeight: home.unit * 2 + home.gap
              tileColor: Qt.tint(Color.menu.background, Util.alpha(Commons.Color.accent, 0.15))
              onActivated: home.runAction("editor")
              Column {
                anchors.fill: parent
                spacing: Style.space(10)
                Item {
                  width: parent.width; height: editorTile.iconSize
                  Text { visible: !editorTile.iconReady; text: "N"; color: Commons.Color.accent; font.family: Style.font.menuFamily; font.pixelSize: Style.font.displayLarge * 1.7 }
                }
                Text { text: "Pick up where\nyou left off."; color: Color.menu.text; font.family: Style.font.menuFamily; font.pixelSize: Style.font.heading; font.weight: Font.Light }
              }
            }
            Tile { tileId: "terminal"; title: "Terminal"; caption: "SHELL"; glyph: ">_"; iconSource: home.workspaceIcon("terminal"); onActivated: home.runAction("terminal") }
            Tile { tileId: "browser"; title: "Browser"; caption: "DEFAULT BROWSER"; glyph: "◎"; iconSource: home.workspaceIcon("browser"); onActivated: home.runAction("browser") }
            Tile { tileId: "files"; title: "Files"; caption: "HOME"; glyph: "▱"; iconSource: home.workspaceIcon("files"); onActivated: home.runAction("files") }
            Tile { tileId: "notes"; title: "Notes"; caption: "OBSIDIAN"; glyph: "▤"; iconSource: home.workspaceIcon("notes"); enabled: !!(home.metrics.tools && home.metrics.tools.obsidian); onActivated: home.runAction("notes") }
          }
        }
        Column {
          width: home.groupWidth(1)
          spacing: Style.space(12)
          visible: home.groupVisible(["activity", "network", "storage"])
          Heading { title: "The machine"; subtitle: "02 / A LITTLE PULSE" }
          GridLayout {
            width: parent.width; columns: 2; rowSpacing: home.gap; columnSpacing: home.gap
            Tile {
              id: activityTile
              tileId: "activity"; title: "Open btop ↗"; caption: "BTOP / LIVE ACTIVITY"; Layout.columnSpan: 2
              detail: home.metrics.processes ? home.metrics.processes + " processes" : "Sampling…"
              Layout.preferredHeight: home.unit * 2 + home.gap
              tileColor: Commons.Color.accent; foreground: home.onAccent
              enabled: !!(home.metrics.tools && home.metrics.tools.btop)
              onActivated: home.runAction("activity")
              Column {
                anchors.fill: parent
                spacing: Style.space(7)
                RowLayout {
                  width: parent.width
                  Text { text: home.metrics.cpu === null || home.metrics.cpu === undefined ? "—" : Math.round(home.metrics.cpu) + "%"; color: activityTile.foreground; font.family: Style.font.menuFamily; font.pixelSize: Style.font.displayLarge * 1.6; Layout.fillWidth: true }
                  Text { text: (home.metrics.cores ? home.metrics.cores.length + " THREADS" : "CPU") + "\n" + (home.metrics.temperature === null || home.metrics.temperature === undefined ? "—" : home.metrics.temperature + "°C"); color: activityTile.foreground; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption; horizontalAlignment: Text.AlignRight }
                }
                Canvas {
                  id: cpuChart
                  width: parent.width; height: Math.max(Style.space(24), activityTile.height * 0.18)
                  property var values: services.cpuHistory
                  property color lineColor: activityTile.foreground
                  onValuesChanged: requestPaint()
                  onLineColorChanged: requestPaint()
                  onWidthChanged: requestPaint()
                  onPaint: {
                    var ctx = getContext("2d"); ctx.reset()
                    if (values.length < 2) return
                    ctx.strokeStyle = lineColor; ctx.lineWidth = 1.5; ctx.beginPath()
                    for (var i = 0; i < values.length; i++) { var x = i * width / (values.length - 1), y = height - values[i] * height / 100; if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y) }
                    ctx.stroke()
                  }
                }
                Repeater {
                  model: 3
                  RowLayout {
                    required property int index
                    width: parent.width
                    readonly property real usage: index < 2 ? (home.metrics.cores && home.metrics.cores[index] !== null && isFinite(home.metrics.cores[index]) ? Number(home.metrics.cores[index]) : 0) : (home.metrics.memory && home.metrics.memory.total ? home.metrics.memory.used * 100 / home.metrics.memory.total : 0)
                    Text { text: index < 2 ? "CPU " + index : "MEM"; color: activityTile.foreground; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption; Layout.preferredWidth: Style.space(45) }
                    Row {
                      Layout.fillWidth: true
                      spacing: Style.space(2)
                      Repeater { model: 28; Rectangle { required property int index; width: Math.max(1, (parent.width - Style.space(2) * 27) / 28); height: Style.space(6); color: activityTile.foreground; opacity: index * 100 / 28 < parent.parent.usage ? 1 : 0.18 } }
                    }
                    Text { text: parent.index < 2 ? Math.round(parent.usage) + "%" : Model.bytes(home.metrics.memory ? home.metrics.memory.used : null); color: activityTile.foreground; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption; Layout.preferredWidth: Style.space(65); horizontalAlignment: Text.AlignRight }
                  }
                }
              }
            }
            Tile {
              tileId: "network"; title: home.metrics.network ? home.metrics.network.interface || "Offline" : "Network"; caption: "TRAFFIC"; Layout.preferredHeight: home.unit * 1.25
              onActivated: home.runAction("network")
              Column {
                anchors.fill: parent; spacing: Style.space(8)
                Text { text: "↓ " + Model.bytes(home.metrics.network ? home.metrics.network.rx : null, "/s"); color: Color.menu.text; font.family: Style.font.menuFamily; font.pixelSize: Style.font.subtitle }
                Text { text: "↑ " + Model.bytes(home.metrics.network ? home.metrics.network.tx : null, "/s"); color: home.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption }
              }
            }
            Tile {
              tileId: "storage"; title: "Home filesystem"; caption: "STORAGE"; Layout.preferredHeight: home.unit * 1.25
              tileColor: Color.menu.text; foreground: Color.menu.background
              onActivated: home.runAction("storage")
              Column {
                anchors.fill: parent; spacing: Style.space(10)
                Text { text: Model.bytes(home.metrics.storage ? home.metrics.storage.free : null); color: parent.parent.parent.foreground; font.family: Style.font.menuFamily; font.pixelSize: Style.font.heading }
                Text { text: "FREE"; color: Color.menu.background; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption }
              }
            }
          }
        }
        Column {
          width: home.groupWidth(2)
          spacing: Style.space(12)
          visible: home.groupVisible(["media", "volume", "focus"])
          Heading { title: "In the flow"; subtitle: "03 / SET THE PACE" }
          GridLayout {
            width: parent.width; columns: 2; rowSpacing: home.gap; columnSpacing: home.gap
            Tile {
              id: mediaTile
              tileId: "media"; title: services.player ? services.player.identity : "MPRIS"; caption: services.player && services.player.isPlaying ? "NOW PLAYING" : "MEDIA"
              Layout.columnSpan: 2; Layout.preferredHeight: home.unit * 3 + home.gap * 2
              interactive: false
              Column {
                anchors.fill: parent
                spacing: Style.space(6)
                Rectangle {
                  width: parent.width; height: Math.min(Style.space(125), parent.height * 0.4)
                  color: Qt.tint(Color.menu.background, Util.alpha(Commons.Color.accent, 0.07)); clip: true
                  Repeater { model: 4; Rectangle { required property int index; anchors.centerIn: parent; width: Style.space(42 + index * 34); height: width; radius: width / 2; color: "transparent"; border.width: Style.spacing.hairline; border.color: Util.alpha(Commons.Color.accent, 0.3 + index * 0.15) } }
                  Image { anchors.fill: parent; source: services.active && services.player ? services.player.trackArtUrl : ""; fillMode: Image.PreserveAspectCrop; asynchronous: true; visible: status === Image.Ready }
                }
                Text { width: parent.width; text: services.player ? services.player.trackTitle || "Untitled track" : "Nothing playing"; textFormat: Text.PlainText; color: Color.menu.text; font.family: Style.font.menuFamily; font.pixelSize: Style.font.heading; elide: Text.ElideRight }
                Text { width: parent.width; text: services.player ? services.player.trackArtist || services.player.identity : "Start a media player to connect."; textFormat: Text.PlainText; color: home.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption; elide: Text.ElideRight }
                Row {
                  anchors.horizontalCenter: parent.horizontalCenter
                  spacing: Style.space(10)
                  HomeButton { text: "|‹"; Accessible.name: "Previous track"; enabled: services.player && services.player.canGoPrevious; onClicked: services.media("previous") }
                  HomeButton { text: services.player && services.player.isPlaying ? "Ⅱ" : "▷"; Accessible.name: "Play or pause"; enabled: services.player && services.player.canTogglePlaying; onClicked: services.media("playPause") }
                  HomeButton { text: "›|"; Accessible.name: "Next track"; enabled: services.player && services.player.canGoNext; onClicked: services.media("next") }
                  HomeButton { text: "↻"; Accessible.name: "Cycle media source"; enabled: services.players.length > 1; onClicked: services.cyclePlayer() }
                }
                HomeSlider {
                  width: parent.width
                  from: 0; to: services.player && services.player.lengthSupported ? Math.max(1, services.player.length) : 1
                  value: services.player && services.player.positionSupported ? services.player.position : 0
                  enabled: services.player && services.player.canSeek && services.player.positionSupported && services.player.lengthSupported
                  Accessible.name: "Media position"
                  onMoved: services.seek(value)
                }
                Text { text: services.player ? Model.elapsed(services.player.position) + " / " + (services.player.lengthSupported ? Model.elapsed(services.player.length) : "—") : "— / —"; color: home.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption }
              }
            }
            Tile {
              tileId: "volume"; title: "Output volume"; caption: "AUDIO"; interactive: false; Layout.preferredHeight: home.unit * 1.3
              Column {
                anchors.fill: parent
                spacing: Style.space(5)
                RowLayout {
                  width: parent.width
                  Text { text: home.metrics.audio && home.metrics.audio.available ? home.metrics.audio.volume + "%" : "No output"; color: Color.menu.text; font.family: Style.font.menuFamily; font.pixelSize: Style.font.heading; Layout.fillWidth: true }
                  HomeButton { text: home.metrics.audio && home.metrics.audio.muted ? "Unmute" : "Mute"; enabled: !!(home.metrics.audio && home.metrics.audio.available); onClicked: services.mute() }
                }
                HomeSlider {
                  width: parent.width; from: 0; to: 100; stepSize: 1
                  value: home.metrics.audio ? Math.min(100, home.metrics.audio.volume) : 0
                  enabled: !!(home.metrics.audio && home.metrics.audio.available)
                  Accessible.name: "Output volume"
                  onPressedChanged: if (!pressed && enabled) services.volume(value)
                  Keys.onReleased: function(event) { if (event.key === Qt.Key_Left || event.key === Qt.Key_Right) services.volume(value) }
                }
              }
            }
            Tile {
              tileId: "focus"; title: "Focus session"; caption: "FOCUS"; interactive: false; Layout.preferredHeight: home.unit * 1.3
              tileColor: Qt.tint(Color.menu.background, Util.alpha(Commons.Color.accent, 0.12))
              Column {
                anchors.fill: parent; spacing: Style.space(6)
                Text { text: home.controller ? Model.elapsed(home.controller.focusRemaining) : "25:00"; color: Color.menu.text; font.family: Style.font.menuFamily; font.pixelSize: Style.font.display }
                Row {
                  spacing: Style.space(6)
                  HomeButton { text: home.controller && home.controller.focusDeadline > 0 ? "Pause" : "Start"; onClicked: home.runAction("focus") }
                  HomeButton { text: "↺"; Accessible.name: "Reset focus timer"; onClicked: home.runAction("focus:reset") }
                }
              }
            }
          }
        }
        Column {
          width: home.groupWidth(3)
          spacing: Style.space(12)
          visible: home.groupVisible(["clock", "quiet", "wifi", "appearance", "lock"])
          Heading { title: "Make space"; subtitle: "04 / YOUR SESSION" }
          GridLayout {
            width: parent.width; columns: 2; rowSpacing: home.gap; columnSpacing: home.gap
            Tile {
              tileId: "clock"; title: Qt.formatDateTime(clock.date, "d MMMM yyyy"); caption: Qt.formatDateTime(clock.date, "dddd"); interactive: false
              Layout.columnSpan: 2; Layout.preferredHeight: home.unit * 1.4
              Text { anchors.centerIn: parent; text: Qt.formatDateTime(clock.date, "HH:mm"); color: Color.menu.text; font.family: Style.font.menuFamily; font.pixelSize: Style.font.displayLarge * 1.2 }
            }
            Tile { tileId: "quiet"; title: "Quiet mode"; caption: home.metrics.quiet === undefined || home.metrics.quiet === null ? "UNKNOWN" : home.metrics.quiet ? "ON" : "OFF"; glyph: "☾"; enabled: home.metrics.quiet !== undefined && home.metrics.quiet !== null; onActivated: home.runAction("quiet") }
            Tile { tileId: "wifi"; title: "Wi-Fi"; caption: home.metrics.wifi === undefined || home.metrics.wifi === null ? "UNAVAILABLE" : home.metrics.wifi ? "ON" : "OFF"; glyph: "⌁"; enabled: home.metrics.wifi !== undefined && home.metrics.wifi !== null; onActivated: home.runAction("wifi") }
            Tile { tileId: "appearance"; title: "Appearance"; caption: "GLOBAL THEME"; glyph: "◧"; onActivated: home.runAction("appearance") }
            Tile { tileId: "lock"; title: "Lock session"; caption: "SESSION"; glyph: "▣"; onActivated: home.runAction("lock") }
          }
        }
      }
    }
  }
  RowLayout {
    anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
    anchors.margins: Style.space(18)
    Text { text: "↑↓←→ tiles   ↵ open   / search   esc close"; color: home.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption; Layout.fillWidth: true }
    Text { text: "CONTROL PANE / LIVE SERVICES"; color: home.muted; font.family: Style.font.menuFamily; font.pixelSize: Style.font.caption }
  }
}
