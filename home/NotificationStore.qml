pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "NotificationModel.js" as Model

Singleton {
  id: store
  property var snapshot: ({ready: false, rows: [], warning: false, error: ""})
  property var removedKeys: ({})
  property bool removedReady: false
  property bool directoryReady: false
  property bool removedDirty: false
  property bool commandPending: false
  property bool hostAvailable: false
  property var dnd: null
  property string commandError: ""
  readonly property bool ready: snapshot.ready && removedReady && hostAvailable
  readonly property var arranged: Model.arrange(Model.visible(snapshot.rows, removedKeys))
  readonly property var rows: arranged.rows
  readonly property var groups: arranged.groups
  readonly property string directory: (Quickshell.env("XDG_STATE_HOME") || Quickshell.env("HOME") + "/.local/state") + "/omarchy/dicey.home"
  // Removing only hides an entry in Home: Omarchy's history and live toasts are untouched.
  function remove(keys) {
    if (!ready) return "loading"
    removedKeys = Model.remove(removedKeys, keys, Date.now())
    removedDirty = true
    saveRemoved()
    return "ok"
  }
  function removeOne(key) { return rows.some(function(row) { return row.key === key }) ? remove([key]) : "unavailable" }
  function removeGroup(id) { return Object.prototype.hasOwnProperty.call(groups, id) ? remove(groups[id].keys) : "unavailable" }
  function removeAll() { return rows.length ? remove(rows.map(function(row) { return row.key })) : "unavailable" }
  function saveRemoved() {
    if (removedReady && directoryReady && removedDirty) {
      removedFile.setText(JSON.stringify(removedKeys) + "\n")
      removedDirty = false
    }
  }
  function loadRemoved(raw) {
    if (removedReady) return
    try { removedKeys = Model.removed(JSON.parse(raw || "{}"), Date.now(), null) } catch (error) { removedKeys = ({}) }
    removedReady = true
  }
  function run(action) {
    var args = Model.command(action)
    if (!ready || !args || commandPending) return "unavailable"
    commandError = ""
    commandPending = true
    ipc.command = ["omarchy-shell", "notifications"].concat(args)
    ipc.running = true
    return "ok"
  }
  function inspect() {
    // Same-user diagnostics, deliberately excludes private notification text.
    return {ready: ready, count: rows.length, total: snapshot.rows.length, removed: Object.keys(removedKeys).length,
      groups: arranged.order, dnd: dnd, warning: snapshot.warning,
      error: snapshot.error || commandError || (!hostAvailable ? "Notification service unavailable." : ""),
      pending: commandPending, keys: rows.map(function(row) { return row.key }),
      liveCount: rows.filter(function(row) { return row.live }).length}
  }
  Process {
    id: reader
    command: ["python3", "-B", decodeURIComponent(String(Qt.resolvedUrl("../notifications.py")).slice(7)), "--watch"]
    running: true
    stdout: SplitParser {
      onRead: function(line) {
        try { store.snapshot = JSON.parse(line) } catch (error) { store.snapshot = {ready: false, rows: [], warning: false, error: "Invalid notification snapshot."} }
      }
    }
    onExited: {
      store.snapshot = {ready: false, rows: [], warning: false, error: "Notification reader stopped. Reopen after restarting the shell."}
      retry.restart()
    }
  }
  Timer { id: retry; interval: 5000; onTriggered: reader.running = true }
  Process {
    id: ipc
    stdout: StdioCollector { id: response; waitForEnd: true }
    onExited: function(code) {
      commandTimeout.stop()
      store.commandPending = false
      var reply = response.text.trim()
      if (code === 0 && (reply === "on" || reply === "off")) store.dnd = reply === "on"
      else store.commandError = "The notification service did not accept the command. Try again."
    }
    onRunningChanged: if (running) commandTimeout.restart()
  }
  Timer { id: commandTimeout; interval: 10000; onTriggered: { ipc.signal(15); store.commandError = "Notification command timed out." } }
  // Public IPC both proves the host service is up and reports Do Not Disturb.
  Process {
    id: probe
    command: ["omarchy-shell", "notifications", "isDnd"]
    running: true
    stdout: StdioCollector { id: probeOutput; waitForEnd: true }
    onExited: function(code) {
      probeTimeout.stop()
      var reply = probeOutput.text.trim()
      store.hostAvailable = code === 0 && (reply === "on" || reply === "off")
      if (store.hostAvailable && !store.commandPending) store.dnd = reply === "on"
    }
    onRunningChanged: if (running) probeTimeout.restart()
  }
  Timer { id: probeTimeout; interval: 4000; onTriggered: { probe.signal(15); store.hostAvailable = false } }
  Timer { interval: 5000; repeat: true; running: true; onTriggered: if (!probe.running) probe.running = true }
  // Forget removals the host no longer holds, so the file stays small; keys it
  // still holds (e.g. a critical toast left on screen) are kept.
  Timer {
    interval: 3600000; repeat: true; running: store.removedReady && store.snapshot.ready
    onTriggered: {
      store.removedKeys = Model.removed(store.removedKeys, Date.now(), store.snapshot.rows.map(function(row) { return row.key }))
      store.removedDirty = true
      store.saveRemoved()
    }
  }
  Process {
    command: ["mkdir", "-p", store.directory]
    running: true
    onExited: function(code) { store.directoryReady = code === 0; store.saveRemoved() }
  }
  FileView {
    id: removedFile
    path: store.directory + "/notifications-removed.json"
    atomicWrites: true
    printErrors: false
    onLoaded: store.loadRemoved(text())
    onLoadFailed: store.loadRemoved("")
    onSaveFailed: { store.removedDirty = true; store.commandError = "Could not save removed notifications. They may reappear after a restart." }
  }
}
