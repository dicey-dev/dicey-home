const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const makeover = require('../Makeover.js');

// This integration check deliberately requires a real Omarchy installation.
const root = process.env.OMARCHY_PATH || '/usr/share/omarchy';
const stock = fs.readFileSync(path.join(root, 'shell/plugins/menu/Menu.qml'), 'utf8');
const output = makeover.transform(stock, 'file:///tmp/Search.js', 'file:///tmp/web-results.py');
assert.match(output, /Style\.space\(720\)/);
assert.match(output, /diceyAppendSearch\(rows, query\)/);
assert.ok(output.includes('/home" as DiceyHome'));
assert.ok(output.includes('DiceyHome.Home {'));
assert.ok(output.includes('accent: String(Commons.Color.accent)'));
assert.doesNotMatch(output, /(?<!\.)\bColor\.accent/);
for (const method of ['openDmenu', 'finishRequest', 'requestDeleteSelected', 'confirmDelete', 'evaluateGuards', 'resolveRoute', 'loadProviderForMenu']) {
  const start = stock.indexOf('  function ' + method + '(');
  assert.notEqual(start, -1, method + ' exists upstream');
  const end = stock.indexOf('\n  }', start + 1) + '\n  }'.length;
  // Preserve complete function bodies, including dmenu completion, uninstall,
  // guards and route resolution, rather than testing a synthetic menu fixture.
  assert.ok(output.includes(stock.slice(start, end).trimEnd()), method + ' is retained');
}
assert.throws(() => makeover.transform(stock.replace('  property string filterText: ""', '  property string filterText: "changed"'), 'Search.js', 'web.py'), /Unsupported Omarchy menu anchor/);
console.log('Installed-menu compatibility passed.');
