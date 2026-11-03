import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Mpris

Item {
  id: services
  property bool active: false
  property var metrics: ({})
  property var cpuHistory: []
  property string selectedPlayer: ""
  property var workspaceIcons: ({})
  function refreshWorkspaceIcons() {
    if (!workspaceLookup.running) workspaceLookup.running = true
  }
  readonly property string helper: decodeURIComponent(String(Qt.resolvedUrl("../activity.py")).slice(7))
  readonly property var players: Mpris.players ? Mpris.players.values : []
  readonly property var player: {
    var fallback = null
    for (var i = 0; i < players.length; i++) {
      var current = players[i]
      if (!current) continue
      if (selectedPlayer && current.dbusName === selectedPlayer) return current
      if (!fallback || (!fallback.isPlaying && current.isPlaying)) fallback = current
    }
    return fallback
  }
  function cyclePlayer() {
    if (!players.length) return false
    var index = players.indexOf(player)
    selectedPlayer = players[(index + 1) % players.length].dbusName
    return true
  }
  function media(action) {
    if (!player) return false
    if (action === "playPause" && player.canTogglePlaying) player.togglePlaying()
    else if (action === "next" && player.canGoNext) player.next()
    else if (action === "previous" && player.canGoPrevious) player.previous()
    else return false
    return true
  }
  function seek(value) {
    if (!player || !player.canSeek || !player.positionSupported) return false
    player.position = Math.max(0, Math.min(value, player.length))
    return true
  }
  function volume(value) { Quickshell.execDetached(["python3", "-B", helper, "--volume", String(Math.round(Math.max(0, Math.min(100, value))))]) }
  function mute() { Quickshell.execDetached(["python3", "-B", helper, "--mute"]) }
  Process {
    id: workspaceLookup
    command: ["python3", "-B", decodeURIComponent(String(Qt.resolvedUrl("../workspace_icons.py")).slice(7))]
    stdout: StdioCollector { id: workspaceOutput; waitForEnd: true }
    onExited: function(code) {
      if (code !== 0) return
      try { services.workspaceIcons = JSON.parse(workspaceOutput.text) } catch (error) {}
    }
  }
  Process {
    id: sampler
    command: ["python3", "-B", services.helper, "--watch"]
    running: services.active
    stdout: SplitParser {
      onRead: function(line) {
        var snapshot
        try { snapshot = JSON.parse(line) } catch (error) { return }
        services.metrics = snapshot
        if (snapshot.cpu !== null) {
          var history = services.cpuHistory.slice(-39)
          history.push(snapshot.cpu)
          services.cpuHistory = history
        }
      }
    }
  }
  Timer {
    interval: 1000
    repeat: true
    running: services.active && services.player && services.player.isPlaying
    onTriggered: if (services.player) services.player.positionChanged()
  }
}
