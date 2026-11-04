pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "NotificationModel.js" as Model

Singleton {
  id: store
  property var snapshot: ({ready: false, rows: [], dnd: null, warning: false, error: ""})
  property var readCursor: ({timestamp: 0, keys: []})
  property bool readReady: false
  property bool directoryReady: false
  property bool readDirty: false
  property bool commandPending: false
  property bool hostAvailable: false
  property string commandError: ""
  readonly property var rows: snapshot.rows
  readonly property bool ready: snapshot.ready && readReady && hostAvailable
  readonly property int unreadCount: ready ? Model.count(rows, readCursor) : 0
  readonly property string badge: Model.badge(unreadCount)
  readonly property bool urgent: ready && rows.some(function(row) { return row.urgency === 2 && Model.unread(row, store.readCursor) })
  readonly property string directory: (Quickshell.env("XDG_STATE_HOME") || Quickshell.env("HOME") + "/.local/state") + "/omarchy/dicey.home"
  function isUnread(row) { return Model.unread(row, readCursor) }
  function markRead() {
    if (!ready) return "loading"
    readCursor = Model.markRead(rows, readCursor)
    readDirty = true
    saveRead()
    return "ok"
  }
  function saveRead() {
    if (readReady && directoryReady && readDirty) {
      readFile.setText(JSON.stringify(readCursor) + "\n")
      readDirty = false
    }
  }
  function loadRead(raw) {
    if (readReady) return
    try { readCursor = Model.cursor(JSON.parse(raw || "{}")) } catch (error) { readCursor = Model.cursor(null) }
    readReady = true
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
    return {ready: ready, count: rows.length, unread: unreadCount, badge: badge, urgent: urgent,
      dnd: snapshot.dnd, warning: snapshot.warning, error: snapshot.error || commandError || (!hostAvailable ? "Notification service unavailable." : ""),
      pending: commandPending, keys: rows.map(function(row) { return row.key }),
      liveCount: rows.filter(function(row) { return row.live }).length}
  }
  Process {
    id: reader
    command: ["python3", "-B", decodeURIComponent(String(Qt.resolvedUrl("../notifications.py")).slice(7)), "--watch"]
    running: true
    stdout: SplitParser {
      onRead: function(line) {
        try { store.snapshot = JSON.parse(line) } catch (error) { store.snapshot = {ready: false, rows: [], dnd: null, warning: false, error: "Invalid notification snapshot."} }
      }
    }
    onExited: {
      store.snapshot = {ready: false, rows: [], dnd: null, warning: false, error: "Notification reader stopped. Reopen after restarting the shell."}
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
      if (code !== 0 || ["ok", "on", "off", "none"].indexOf(response.text.trim()) < 0)
        store.commandError = "The notification service did not accept the command. Try again."
    }
    onRunningChanged: if (running) commandTimeout.restart()
  }
  Timer { id: commandTimeout; interval: 10000; onTriggered: { ipc.signal(15); store.commandError = "Notification command timed out." } }
  Process {
    id: probe
    command: ["omarchy-shell", "notifications", "ping"]
    running: true
    stdout: StdioCollector { id: probeOutput; waitForEnd: true }
    onExited: function(code) { probeTimeout.stop(); store.hostAvailable = code === 0 && probeOutput.text.trim() === "ok" }
    onRunningChanged: if (running) probeTimeout.restart()
  }
  Timer { id: probeTimeout; interval: 4000; onTriggered: { probe.signal(15); store.hostAvailable = false } }
  Timer { interval: 5000; repeat: true; running: true; onTriggered: if (!probe.running) probe.running = true }
  Process {
    command: ["mkdir", "-p", store.directory]
    running: true
    onExited: function(code) { store.directoryReady = code === 0; store.saveRead() }
  }
  FileView {
    id: readFile
    path: store.directory + "/notifications-read.json"
    atomicWrites: true
    printErrors: false
    onLoaded: store.loadRead(text())
    onLoadFailed: store.loadRead("")
    onSaveFailed: { store.readDirty = true; store.commandError = "Could not save read status. It may reset after a restart." }
  }
}
