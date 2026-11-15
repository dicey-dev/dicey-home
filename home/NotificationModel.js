// Notification content/history remains owned by Omarchy. Home only remembers
// which entries were removed from its own list (host key -> removal time).
var REMEMBER_MS = 48 * 3600 * 1000  // Host history keeps 24 hours.
var MAX_REMOVED = 1024
// present: keys the host still holds, refreshed so they never reappear; null
// skips age expiry (before the first snapshot).
function removed(value, now, present) {
  var times = {}
  if (!value || typeof value !== "object" || Array.isArray(value)) return times
  Object.keys(value).forEach(function(key) {
    var at = value[key]
    if (!/^[A-Za-z0-9_-]{1,120}$/.test(key) || typeof at !== "number" || !isFinite(at) || at > now + 60000) return
    if (present && present.indexOf(key) >= 0) times[key] = now
    else if (!present || at > now - REMEMBER_MS) times[key] = at
  })
  var out = {}
  Object.keys(times).sort(function(a, b) { return times[b] - times[a] }).slice(0, MAX_REMOVED)
    .forEach(function(key) { out[key] = times[key] })
  return out
}
function remove(previous, keys, now) {
  var out = Object.assign({}, previous)
  keys.forEach(function(key) { if (typeof key === "string") out[key] = now })
  return removed(out, now, null)
}
function visible(rows, removedKeys) {
  return rows.filter(function(row) { return !Object.prototype.hasOwnProperty.call(removedKeys, row.key) })
}
// Groups ordered by their newest entry, entries newest first, so a ListView
// section per group stays contiguous.
function arrange(rows) {
  var groups = {}, order = []
  rows.forEach(function(row) {
    var group = groups[row.group]
    if (!group) {
      group = groups[row.group] = {id: row.group, label: row.groupLabel, kind: row.groupKind, browsers: [], newest: row.timestamp, rows: []}
      order.push(group)
    }
    if (row.browser && group.browsers.indexOf(row.browser) < 0) group.browsers.push(row.browser)
    group.newest = Math.max(group.newest, row.timestamp)
    group.rows.push(row)
  })
  order.sort(function(a, b) { return b.newest - a.newest || (a.id < b.id ? -1 : 1) })
  var flat = [], info = {}
  order.forEach(function(group) {
    group.rows.sort(function(a, b) { return b.timestamp - a.timestamp || (a.key < b.key ? 1 : -1) })
    info[group.id] = {label: group.label, kind: group.kind, browsers: group.browsers.sort(), count: group.rows.length,
      keys: group.rows.map(function(row) { return row.key })}
    flat = flat.concat(group.rows)
  })
  return {rows: flat, groups: info, order: order.map(function(group) { return group.id })}
}
function caption(group) {
  if (!group) return ""
  var browsers = (group.browsers || []).join(", ")
  if (group.kind === "webapp") return group.id.slice(7) + " · " + browsers
  if (group.kind === "site") return browsers
  return ""
}
function sync(model, rows) {
  // Keep the ListModel and surviving rows alive: replacing an array model
  // resets ListView's scroll/current item on every notification refresh.
  // Remove departed rows in place first, so selection moves to a neighbour.
  var wanted = {}
  rows.forEach(function(row) { wanted[row.key] = true })
  for (var r = model.count - 1; r >= 0; r--)
    if (!Object.prototype.hasOwnProperty.call(wanted, model.get(r).key)) model.remove(r, 1)
  for (var i = 0; i < rows.length; i++) {
    var row = rows[i]
    if (i >= model.count || model.get(i).key !== row.key) {
      var found = -1
      for (var j = i + 1; j < model.count; j++) {
        if (model.get(j).key === row.key) { found = j; break }
      }
      if (found >= 0) model.move(found, i, 1)
      else model.insert(i, row)
    }
    var previous = model.get(i)
    if (Object.keys(row).some(function(key) { return previous[key] !== row[key] })) model.set(i, row)
  }
  if (model.count > rows.length) model.remove(rows.length, model.count - rows.length)
}
function command(action) {
  var commands = {dndOn: ["setDnd", "on"], dndOff: ["setDnd", "off"]}
  return Object.prototype.hasOwnProperty.call(commands, action) ? commands[action] : null
}
if (typeof module !== "undefined") module.exports = {removed: removed, remove: remove, visible: visible, arrange: arrange, caption: caption, sync: sync, command: command}
