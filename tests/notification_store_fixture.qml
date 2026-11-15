pragma Singleton
import QtQuick
import Quickshell
import "NotificationModel.js" as Model

// TEST ONLY: copied over the singleton in a temporary .dev source snapshot.
// No IPC, host state access, persistence, notification server or subprocess.
Singleton {
  id: fixture
  property var fixtureRows: []
  property var removedKeys: ({})
  property var dnd: false
  property string lastCommand: ""
  readonly property bool ready: true
  readonly property bool hostAvailable: true
  readonly property bool commandPending: false
  readonly property string commandError: ""
  readonly property var snapshot: ({ready: true, rows: fixtureRows, warning: false, error: ""})
  readonly property var arranged: Model.arrange(Model.visible(fixtureRows, removedKeys))
  readonly property var rows: arranged.rows
  readonly property var groups: arranged.groups
  function remove(keys) { removedKeys = Model.remove(removedKeys, keys, Date.now()); return "ok" }
  function removeOne(key) { return rows.some(function(row) { return row.key === key }) ? remove([key]) : "unavailable" }
  function removeGroup(id) { return groups[id] ? remove(groups[id].keys) : "unavailable" }
  function removeAll() { return rows.length ? remove(rows.map(function(row) { return row.key })) : "unavailable" }
  function entry(key, minutes, app, source, extra) {
    var browser = /^(Chromium|Firefox)$/.test(app) ? app : ""
    var site = browser && source ? source : ""
    var group = site === "web.whatsapp.com" ? "webapp:" + site : site ? "site:" + site : "app:" + app.toLowerCase().replace(/[^a-z0-9]+/g, "-")
    return Object.assign({key: key, timestamp: Date.now() - minutes * 60000, app: app, summary: "Synthetic update " + key,
      body: "Synthetic message for grouping, scroll and removal testing.", urgency: 1, live: false, group: group,
      groupLabel: site === "web.whatsapp.com" ? "WhatsApp" : site || app, groupKind: group.split(":")[0], browser: browser}, extra || {})
  }
  function run(action) {
    if (!Model.command(action)) return "unavailable"
    lastCommand = action
    dnd = action === "dndOn"
    if (action === "dndOn") {
      // Fixture-only arrival in a new group above everything else, plus a
      // live-to-history transition, to prove the feed keeps its position.
      var updated = fixtureRows.map(function(row) { return Object.assign({}, row) })
      updated[0].live = false
      updated.unshift(entry("synthetic-new", -1, "Synthetic arrival"))
      fixtureRows = updated
    }
    return "ok"
  }
  function inspect() { return {ready: true, count: rows.length, total: fixtureRows.length, removed: Object.keys(removedKeys).length,
    groups: arranged.order, dnd: dnd, pending: false, lastCommand: lastCommand, keys: rows.map(function(row) { return row.key }),
    liveCount: rows.filter(function(row) { return row.live }).length, error: ""} }
  Component.onCompleted: {
    var values = [entry("synthetic-0", 0, "Synthetic mail", "", {urgency: 2, live: true, summary: "A synthetic urgent notification",
      body: "Only fixture data. <b>This is plain text.</b>\nA long message wraps within the feed, without links, images or executable content."})]
    for (var i = 1; i < 60; i++) {
      var kind = i % 4
      values.push(kind === 0 ? entry("synthetic-" + i, i, "Synthetic mail")
        : kind === 1 ? entry("synthetic-" + i, i, "Chromium", "news.example.com")
        : kind === 2 ? entry("synthetic-" + i, i, "Firefox", "web.whatsapp.com")
        : entry("synthetic-" + i, i, "Synthetic chat " + (i % 3)))
    }
    fixtureRows = values
  }
}
