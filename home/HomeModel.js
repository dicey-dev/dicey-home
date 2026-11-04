// Pure data helpers shared by the native tiles and regression checks.
var tileIds = ["activity", "network", "storage", "media", "volume", "focus", "clock", "quiet", "wifi", "appearance", "lock"]
function normalizeHidden(values) {
  if (!Array.isArray(values)) return []
  return values.filter(function(id, index) { return tileIds.indexOf(id) >= 0 && values.indexOf(id) === index })
}
function bytes(value, suffix) {
  if (value === null || value === undefined || !isFinite(value)) return "—"
  var units = ["B", "KiB", "MiB", "GiB", "TiB"]
  var number = Math.max(0, Number(value)), index = 0
  while (number >= 1024 && index < units.length - 1) { number /= 1024; index++ }
  return (number >= 100 ? number.toFixed(0) : number.toFixed(1)) + " " + units[index] + (suffix || "")
}
function elapsed(value) {
  var seconds = Math.max(0, Math.floor(Number(value) || 0))
  return Math.floor(seconds / 60) + ":" + (seconds % 60 < 10 ? "0" : "") + seconds % 60
}
function focusRemaining(deadline, paused, now) {
  return deadline > 0 ? Math.max(0, Math.ceil((deadline - now) / 1000)) : Math.max(0, Math.floor(paused))
}
function luminance(color) {
  function linear(value) { return value <= 0.04045 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4) }
  return linear(color.r) * 0.2126 + linear(color.g) * 0.7152 + linear(color.b) * 0.0722
}
function ink(color) { return luminance(color) > 0.18 ? "#080b06" : "#fafaf2" }
function nearest(origin, candidates, dx, dy) {
  var best = null, score = Infinity
  for (var i = 0; i < candidates.length; i++) {
    var item = candidates[i], x = item.x - origin.x, y = item.y - origin.y
    var along = x * dx + y * dy, across = Math.abs(x * dy + y * dx)
    if (along > 8 && along + across * 2.5 < score) { best = item; score = along + across * 2.5 }
  }
  return best
}
if (typeof module !== "undefined") module.exports = {tileIds: tileIds, normalizeHidden: normalizeHidden, bytes: bytes, elapsed: elapsed, focusRemaining: focusRemaining, ink: ink, nearest: nearest}
