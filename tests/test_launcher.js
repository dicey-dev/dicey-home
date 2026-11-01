const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const search = require('../Search.js');
const makeover = require('../Makeover.js');

for (const [expression, answer] of [
  ['24 * 7', '168'], ['(12 + 8) / 5', '4'], ['0.1 + 0.2', '0.3'],
  ['2^3^2', '512'], ['-2^2', '-4'], ['2^-3', '0.125'], ['=42', '42'],
  ['sqrt(144) + abs(-3)', '15'], ['max(1, 7, 3) * min(2, 9)', '14'],
  ['pow(2, 8)', '256'], ['1e3 / 4', '250'], ['18 % 5', '3'],
  ['2 × 8 ÷ 4', '4'], ['sin(pi / 2)', '1'], ['log(100)', '2'],
]) assert.equal(search.calculate(expression), answer, expression);

for (const expression of ['Firefox', '42', '1 / 0', 'sqrt(-1)', '2 +',
  'process.exit()', '1; globalThis.pwned = true', 'sqrt(4, 9)', '2 ** ** 3',
  '('.repeat(33) + '1' + ')'.repeat(33)]) {
  assert.equal(search.calculate(expression), null, expression);
}
assert.equal(search.isArithmetic('sqrt(-1)'), true);
assert.equal(search.isArithmetic('=2 +'), true);
assert.equal(search.isArithmetic('42'), false);
assert.equal(search.safeUrl('javascript:alert(1)'), false);
assert.equal(search.safeUrl('https://example.com/hello'), true);
assert.equal(search.searchQuery('? cats & dogs'), 'cats & dogs');

// Exercise compatibility against the installed source; reject an upstream
// change instead of partially rewriting the launcher and breaking its menus.
const root = process.env.OMARCHY_PATH || '/usr/share/omarchy';
const stock = fs.readFileSync(path.join(root, 'shell/plugins/menu/Menu.qml'), 'utf8');
const output = makeover.transform(stock, 'file:///tmp/Search.js', 'file:///tmp/web-results.py');
assert.match(output, /Style\.space\(720\)/);
assert.match(output, /diceyAppendSearch\(rows, query\)/);
for (const method of ['openDmenu', 'finishRequest', 'requestDeleteSelected', 'confirmDelete', 'evaluateGuards', 'resolveRoute', 'loadProviderForMenu']) {
  const start = stock.indexOf('  function ' + method + '(');
  const end = stock.indexOf('\n  }', start + 1) + '\n  }'.length;
  // Whole original function bodies, including the dmenu completion protocol,
  // uninstall flow, guard engine, and route resolution, survive the makeover.
  const body = stock.slice(start, end).trimEnd();
  assert.ok(output.includes(body), method + ' is retained');
}
assert.throws(() => makeover.transform(stock.replace('  property string filterText: ""', '  property string filterText: "changed"'), 'Search.js', 'web.py'), /Unsupported Omarchy menu anchor/);
console.log('Launcher arithmetic, URL handling, and installed-menu compatibility passed.');
