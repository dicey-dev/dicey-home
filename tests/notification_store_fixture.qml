pragma Singleton
import QtQuick
import Quickshell
import "NotificationModel.js" as Model

// TEST ONLY: copied over the singleton in a temporary .dev source snapshot.
// No IPC, host snapshot access, persistence, notification server or subprocess.
Singleton {
  id: fixture
  property var fixtureRows: []
  property var readCursor: ({timestamp: 0, keys: []})
  property bool dnd: false
  property string lastCommand: ""
  readonly property bool ready: true
  readonly property bool hostAvailable: true
  readonly property bool commandPending: false
  readonly property string commandError: ""
  readonly property var rows: fixtureRows
  readonly property var snapshot: ({ready: true, rows: rows, dnd: dnd, warning: false, error: ""})
  readonly property int unreadCount: Model.count(rows, readCursor)
  readonly property string badge: Model.badge(unreadCount)
  readonly property bool urgent: rows.some(function(row) { return row.urgency === 2 && fixture.isUnread(row) })
  function isUnread(row) { return Model.unread(row, readCursor) }
  function markRead() { readCursor = Model.markRead(rows, readCursor); return "ok" }
  function run(action) {
    if (!Model.command(action)) return "unavailable"
    lastCommand = action
    if (action === "dndOn") dnd = true
    if (action === "dndOff") dnd = false
    if (action === "replay") {
      var updated = rows.map(function(row) { return Object.assign({}, row) })
      updated[0].live = false  // An ordinary live-to-history transition.
      updated.unshift({key: "synthetic-new", timestamp: Date.now(), app: "Synthetic app",
        summary: "Synthetic arrival while reading", body: "Only fixture data.", live: false, urgency: 1})
      fixtureRows = updated
    }
    if (action === "clearHistory") fixtureRows = rows.filter(function(row) { return row.live })
    return "ok"
  }
  function inspect() { return {ready: true, count: rows.length, unread: unreadCount, badge: badge,
    urgent: urgent, dnd: dnd, pending: false, lastCommand: lastCommand,
    liveCount: rows.filter(function(row) { return row.live }).length, error: ""} }
  Component.onCompleted: {
    var values = []
    for (var i = 0; i < 105; i++) values.push({key: "synthetic-" + i,
      timestamp: Date.now() - i * 60000, app: "Synthetic app " + i,
      summary: i === 0 ? "A synthetic urgent notification" : "Synthetic update " + i,
      body: i === 0 ? "Only fixture data. <b>This is plain text.</b>\nA long message wraps within the feed, without links, images or executable content." : "Synthetic message for scroll and count testing.",
      live: i === 0 || i === 104, urgency: i === 0 ? 2 : 1})
    fixtureRows = values
  }
}
