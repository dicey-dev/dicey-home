// A bounded recursive-descent calculator. User input is never executable code.
function calculate(raw) {
  var input = String(raw || "").trim().replace(/^=\s*/, "").replace(/×/g, "*").replace(/÷/g, "/").replace(/π/g, "pi")
  if (!input || input.length > 256) return null
  // A plain number is usually an app/search query; '=' explicitly calculates it.
  if (!/^=/.test(String(raw).trim()) && !/[+*/%^()-]|\b(?:pi|sqrt|abs|round|floor|ceil|pow|min|max|sin|cos|tan|log|ln|log10)\b/i.test(input)) return null
  var tokens = input.match(/(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?|[a-z][a-z0-9]*|\*\*|[+*/%^(),-]/gi) || []
  if (tokens.length > 128 || tokens.join("").toLowerCase() !== input.replace(/\s+/g, "").toLowerCase()) return null
  var index = 0
  var depth = 0
  var functions = {sqrt: Math.sqrt, abs: Math.abs, round: Math.round, floor: Math.floor, ceil: Math.ceil,
    sin: Math.sin, cos: Math.cos, tan: Math.tan, ln: Math.log, log: Math.log10, log10: Math.log10}
  function atom() {
    if (++depth > 32) throw new Error("Too deeply nested")
    var token = tokens[index++]
    var value
    if (token === "(") {
      value = sum()
      if (tokens[index++] !== ")") throw new Error("Missing parenthesis")
    } else if (token && /^(?:\d|\.)/.test(token)) {
      value = Number(token)
    } else if (token) {
      token = token.toLowerCase()
      if (token === "pi") value = Math.PI
      else if (token === "e") value = Math.E
      else {
        if (tokens[index++] !== "(") throw new Error("Expected a function")
        var args = [sum()]
        while (tokens[index] === ",") { index++; args.push(sum()) }
        if (tokens[index++] !== ")") throw new Error("Missing parenthesis")
        if (functions[token] && args.length === 1) value = functions[token](args[0])
        else if (token === "pow" && args.length === 2) value = Math.pow(args[0], args[1])
        else if (token === "min") value = Math.min.apply(null, args)
        else if (token === "max") value = Math.max.apply(null, args)
        else throw new Error("Unknown function or argument count")
      }
    } else throw new Error("Incomplete expression")
    depth--
    return value
  }
  function power() {
    var value = atom()
    if (tokens[index] === "^" || tokens[index] === "**") { index++; value = Math.pow(value, unary()) }
    return value
  }
  function unary() {
    if (tokens[index] === "+") { index++; return unary() }
    if (tokens[index] === "-") { index++; return -unary() }
    return power()
  }
  function product() {
    var value = unary()
    while (["*", "/", "%"].indexOf(tokens[index]) >= 0) {
      var op = tokens[index++]
      var next = unary()
      value = op === "*" ? value * next : op === "/" ? value / next : value % next
    }
    return value
  }
  function sum() {
    var value = product()
    while (tokens[index] === "+" || tokens[index] === "-") {
      var op = tokens[index++]
      var next = product()
      value = op === "+" ? value + next : value - next
    }
    return value
  }
  try {
    var answer = sum()
    if (index !== tokens.length || !isFinite(answer)) return null
    return String(Number(answer.toPrecision(12)))
  } catch (error) { return null }
}

function isArithmetic(raw) {
  var text = String(raw || "").trim()
  return /^=/.test(text) || (/^[\d\s.e+*/%^(),×÷-]+$/i.test(text) && /[+*/%^(),×÷-]/.test(text))
    || /^(?:sqrt|abs|round|floor|ceil|pow|min|max|sin|cos|tan|log|ln|log10)\s*\(/i.test(text) || calculate(text) !== null
}

function row(kind, label, detail, action, section) {
  return {itemId: "dicey." + kind + "." + label, kind: kind, label: label, detail: detail,
    icon: kind === "calculator" ? "=" : "↗", iconFont: "", appIcon: "", appId: "",
    target: "", path: "", childCount: 0, action: action || "", provider: "", score: 0, section: section || ""}
}

function searchQuery(query) {
  return String(query || "").trim().replace(/^\?\s*/, "")
}

function safeUrl(url) {
  return /^https?:\/\/[^\s]+$/i.test(String(url || ""))
}

if (typeof module !== "undefined") module.exports = {calculate: calculate, isArithmetic: isArithmetic, row: row, searchQuery: searchQuery, safeUrl: safeUrl}
