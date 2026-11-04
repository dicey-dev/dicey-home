// Read state only: notification content/history remains owned by Omarchy.
function cursor(value) {
  if (!value || typeof value.timestamp !== "number" || !isFinite(value.timestamp) || value.timestamp < 0) return {timestamp: 0, keys: []}
  return {timestamp: value.timestamp, keys: Array.isArray(value.keys) ? value.keys.filter(function(key) { return typeof key === "string" }).slice(0, 256) : []}
}
function unread(row, read) {
  return row.timestamp > read.timestamp || (row.timestamp === read.timestamp && read.keys.indexOf(row.key) < 0)
}
function markRead(rows, previous) {
  var timestamp = previous.timestamp
  rows.forEach(function(row) { timestamp = Math.max(timestamp, row.timestamp) })
  var keys = timestamp === previous.timestamp ? previous.keys.slice() : []
  rows.forEach(function(row) { if (row.timestamp === timestamp && keys.indexOf(row.key) < 0) keys.push(row.key) })
  return {timestamp: timestamp, keys: keys.slice(-256)}
}
function count(rows, read) { return rows.filter(function(row) { return unread(row, read) }).length }
function badge(count) { return count > 99 ? "99+" : count > 0 ? String(count) : "" }
function sync(model, rows) {
  // Keep the ListModel and surviving rows alive: replacing an array model
  // resets ListView's scroll/current item on every notification refresh.
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
  var commands = {dndOn: ["setDnd", "on"], dndOff: ["setDnd", "off"], replay: ["showHistory"],
    dismissLatest: ["dismissOne"], openLatest: ["invokeLast"], clearHistory: ["clear"]}
  return Object.prototype.hasOwnProperty.call(commands, action) ? commands[action] : null
}
if (typeof module !== "undefined") module.exports = {cursor: cursor, unread: unread, markRead: markRead, count: count, badge: badge, sync: sync, command: command}
