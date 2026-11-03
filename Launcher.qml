import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.services as Services
import "Makeover.js" as Makeover
import "home/HomeModel.js" as HomeModel

// Adapt the installed menu rather than freeze a fork of its application engine,
// routing, providers, selection protocol, keyboard handling, and theme bindings.
Item {
  id: host
  property string omarchyPath: Quickshell.env("OMARCHY_PATH") || "/usr/share/omarchy"
  property var shell: null
  property var manifest: null
  property var menu: null
  property bool opened: menu ? menu.opened : false
  property bool enhanced: false
  property string compatibilityError: ""
  property string pendingPayload: ""
  property bool pendingOpen: false
  property bool fullscreen: false
  property bool layoutReady: false
  property bool layoutDirectoryReady: false
  property bool layoutDirty: false
  property var hiddenTiles: []
  property double focusDeadline: 0
  property int focusPaused: 1500
  property double focusNow: Date.now()
  readonly property int focusRemaining: HomeModel.focusRemaining(focusDeadline, focusPaused, focusNow)
  readonly property string layoutStateDirectory: (Quickshell.env("XDG_STATE_HOME") || Quickshell.env("HOME") + "/.local/state") + "/omarchy/dicey.home"
  readonly property string layoutStatePath: layoutStateDirectory + "/layout.json"
  readonly property var applicationApi: host.shell && host.shell.appLibrary ? host.shell.appLibrary : localApps.item
  readonly property var menuApi: ({appLibrary: host.applicationApi, launcherFullscreen: host.fullscreen,
    homeController: host, toggleLauncherLayout: function() { return host.toggleHome() }})

  onFullscreenChanged: {
    if (!layoutReady) return
    layoutDirty = true
    saveLayout()
  }

  function restoreLayout(raw) {
    // The initial read must finish before opening. Subsequent FileView load
    // notifications must not overwrite a preference changed in this session.
    if (layoutReady) return
    try {
      var saved = JSON.parse(raw || "{}")
      if (saved && typeof saved.fullscreen === "boolean") fullscreen = saved.fullscreen
      else if (saved && typeof saved.fullWidth === "boolean") fullscreen = saved.fullWidth
      hiddenTiles = HomeModel.normalizeHidden(saved && saved.hiddenTiles)
      if (saved && typeof saved.focusPaused === "number") focusPaused = Math.max(0, Math.min(1500, saved.focusPaused))
      if (saved && typeof saved.focusDeadline === "number" && saved.focusDeadline > Date.now()) focusDeadline = saved.focusDeadline
    } catch (error) {
      console.warn("Dicey Home: could not read saved layout:", String(error))
    }
    layoutReady = true
    Qt.callLater(host.drainOpen)
  }

  function saveLayout() {
    // A toggle during first-run directory creation is saved when mkdir exits.
    if (!layoutReady || !layoutDirectoryReady || !layoutDirty) return
    layoutStateFile.setText(JSON.stringify({version: 2, fullscreen: fullscreen, hiddenTiles: hiddenTiles,
      focusDeadline: focusDeadline, focusPaused: focusPaused}) + "\n")
    layoutDirty = false
  }

  function toggleHome() {
    if (!layoutReady) return "loading"
    if (menu && menu.opened && (menu.dmenuActive || menu.deleteConfirmOpen)) return "unavailable"
    if (enhanced && menu && menu.opened && !menu.diceySearchActive) {
      fullscreen = true
      menu.openRoute("root")
      return "home"
    }
    fullscreen = !fullscreen
    return fullscreen ? "home" : "normal"
  }
  function toggleFullscreen() { return toggleHome() }
  function toggleTile(id) {
    if (HomeModel.tileIds.indexOf(id) < 0) return "unknown"
    var next = hiddenTiles.slice(), index = next.indexOf(id)
    if (index < 0) next.push(id); else next.splice(index, 1)
    hiddenTiles = next
    layoutDirty = true; saveLayout()
    return "ok"
  }
  function restoreTiles() { hiddenTiles = []; layoutDirty = true; saveLayout(); return "ok" }
  function focusControl(action) {
    focusNow = Date.now()
    if (action === "reset") { focusDeadline = 0; focusPaused = 1500 }
    else if (action === "toggle") {
      if (focusDeadline > 0) { focusPaused = focusRemaining; focusDeadline = 0 }
      else focusDeadline = focusNow + (focusPaused || 1500) * 1000
    } else return "unknown"
    layoutDirty = true; saveLayout()
    return "ok"
  }
  function paneAction(action) { return enhanced && menu ? menu.diceyHomeAction(action) : "unavailable" }

  function mount(source) {
    var modelUrl = Util.fileUrl(host.omarchyPath + "/shell/plugins/menu/MenuModel.js")
    var original = source.replace('import "MenuModel.js" as MenuModel', 'import "' + modelUrl + '" as MenuModel')
    try {
      var decorated = Makeover.transform(original, String(Qt.resolvedUrl("Search.js")), String(Qt.resolvedUrl("web-results.py")))
      host.menu = Qt.createQmlObject(decorated, host, Qt.resolvedUrl("DiceyMenu.qml"))
      host.enhanced = true
    } catch (error) {
      host.compatibilityError = String(error)
      console.warn("Dicey Home: using the stock menu:", host.compatibilityError)
      host.menu = Qt.createQmlObject(original, host, Qt.resolvedUrl("StockMenu.qml"))
    }
    host.menu.omarchyPath = host.omarchyPath
    host.menu.shell = Qt.binding(function() { return host.menuApi })
    host.menu.manifest = host.manifest
    host.drainOpen()
  }

  function open(payload) {
    pendingPayload = payload || "{}"
    pendingOpen = true
    drainOpen()
  }
  function drainOpen() {
    // The stock keepLoaded menu is normally ready before its first summon.
    // Our lazily mounted instance must wait for its JSONC sources, otherwise
    // a first 'apps' or dmenu request is incorrectly resolved against 'root'.
    if (!pendingOpen || !layoutReady || !menu || !menu.rowsLoaded || !menu.defaultMenuItems.length || !applicationApi) return
    pendingOpen = false
    menu.open(pendingPayload)
  }
  function close() {
    pendingOpen = false
    if (menu) menu.close()
  }
  function ping() { return menu ? "ok" : "loading" }
  function refresh() { return menu ? menu.refresh() : "loading" }
  function search(query) {
    if (!menu || !opened) return "closed"
    menu.setFilter(query)
    return "ok"
  }
  function inspect() {
    var state = enhanced && menu ? menu.diceyState() : ({opened: opened})
    state.enhanced = enhanced
    state.compatibilityError = compatibilityError
    state.pendingOpen = pendingOpen
    state.hasShell = !!host.shell
    state.hasAppLibrary = !!(host.menu && host.menu.appLibrary)
    state.localAppLibrary = !!localApps.item
    state.savedFullscreen = fullscreen
    state.layoutReady = layoutReady
    state.layoutStatePath = layoutStatePath
    state.hiddenTiles = hiddenTiles
    state.focusTimer = {remaining: focusRemaining, running: focusDeadline > 0}
    state.appCount = host.menu && host.menu.appLibrary ? host.menu.appLibrary.sortedEntries("").length : 0
    return JSON.stringify(state)
  }

  Connections {
    target: host.menu
    function onDefaultMenuItemsChanged() { Qt.callLater(host.drainOpen) }
    function onRowsLoadedChanged() { Qt.callLater(host.drainOpen) }
  }

  // The host can also revoke the injected facade after shell-config changes.
  // A missing facade must activate the fallback, rather than leave pending
  // opens waiting forever. Reuse the installed AppLibrary type, including
  // hidden filters, icons, launch OSD, and uninstall behavior.
  Loader {
    id: localApps
    active: !host.shell || !host.shell.appLibrary
    sourceComponent: Services.AppLibrary { omarchyPath: host.omarchyPath }
    onLoaded: Qt.callLater(host.drainOpen)
  }

  FileView {
    id: layoutStateFile
    path: host.layoutStatePath
    watchChanges: false
    atomicWrites: true
    printErrors: false
    onLoaded: host.restoreLayout(text())
    onLoadFailed: host.restoreLayout("")
    onSaveFailed: console.warn("Dicey Home: could not save layout preference")
  }

  Process {
    command: ["mkdir", "-p", host.layoutStateDirectory]
    running: true
    onExited: function(code, status) {
      host.layoutDirectoryReady = code === 0 && status === 0
      if (host.layoutDirectoryReady) host.saveLayout()
      else console.warn("Dicey Home: could not create layout state directory")
    }
  }

  Timer {
    interval: 1000
    repeat: true
    running: host.focusDeadline > 0
    onTriggered: {
      host.focusNow = Date.now()
      if (host.focusRemaining <= 0) {
        host.focusDeadline = 0; host.focusPaused = 1500
        host.layoutDirty = true; host.saveLayout()
        Quickshell.execDetached(["notify-send", "Dicey Home", "Focus session complete. Time to take a break."])
      }
    }
  }

  FileView {
    path: host.omarchyPath + "/shell/plugins/menu/Menu.qml"
    onLoaded: host.mount(text())
    onLoadFailed: console.warn("Dicey Home: could not read installed Omarchy menu")
  }
}
