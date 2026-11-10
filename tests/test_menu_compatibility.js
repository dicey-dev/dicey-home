const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
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
assert.equal((output.match(/onFilterTextChanged:/g) || []).length, 1);
if (stock.includes('id: filterInput')) {
  assert.equal((output.match(/id: filterInput/g) || []).length, 1);
  assert.match(output, /onFilterTextChanged: \{ if \(filterInput.text !== filterText\).*diceyQueueWeb\(\)/);
  assert.match(output, /else filterInput.forceActiveFocus\(\)/);
  assert.match(output, /target: filterInput/);
  assert.match(output, /visible: !root.filterText && !filterInput.preeditText/);
  assert.match(output, /readOnly: root.deleteConfirmOpen/);
}
if (stock.includes('Commons.I18n.rightToLeft ? "‹" : "›"'))
  assert.ok(output.includes('Commons.I18n.rightToLeft ? "‹" : "›"'));
// Route-specific stock widths may change, but duplicate/removed properties
// must still reject the entire transformation rather than partially adapt it.
const width = stock.match(/^  property int cardWidth: .*$/m)[0];
assert.match(makeover.transform(stock.replace(width, width.replace(/root.activeMenu === "[^"]+"/, 'root.activeMenu === "new.route"')), 'Search.js', 'web.py'), /Style\.space\(720\)/);
assert.throws(() => makeover.transform(stock.replace(width, ''), 'Search.js', 'web.py'), /Unsupported Omarchy menu anchor: cardWidth/);
assert.throws(() => makeover.transform(stock.replace(width, width + '\n' + width), 'Search.js', 'web.py'), /Unsupported Omarchy menu anchor: cardWidth/);
for (const method of ['openDmenu', 'finishRequest', 'requestDeleteSelected', 'confirmDelete', 'evaluateGuards', 'resolveRoute', 'loadProviderForMenu', 'runAction']) {
  const start = stock.indexOf('  function ' + method + '(');
  assert.notEqual(start, -1, method + ' exists upstream');
  const end = stock.indexOf('\n  }', start + 1) + '\n  }'.length;
  // Preserve complete function bodies, including dmenu completion, uninstall,
  // guards and route resolution, rather than testing a synthetic menu fixture.
  assert.ok(output.includes(stock.slice(start, end).trimEnd()), method + ' is retained');
}
assert.throws(() => makeover.transform(stock.replace('  property string filterText: ""', '  property string filterText: "changed"'), 'Search.js', 'web.py'), /Unsupported Omarchy menu anchor/);
// The stock fallback's runAction also uses the injected shell facade. It must
// forward summons, or return false so the stock command fallback can run.
const launcher = fs.readFileSync(path.join(__dirname, '../Launcher.qml'), 'utf8');
const facade = launcher.match(/readonly property var menuApi: (\(\{[\s\S]*?\}\))/)[1];
const calls = [];
const host = {applicationApi: {}, fullscreen: false, shell: {summon: (...args) => { calls.push(args); return true; }}};
const api = vm.runInNewContext(facade, {host});
assert.equal(api.appLibrary, host.applicationApi);
assert.equal(api.summon('omarchy.menu', '{"menu":"apps"}'), true);
assert.deepEqual(calls, [['omarchy.menu', '{"menu":"apps"}']]);
host.shell.summon = () => false;
assert.equal(api.summon('missing.plugin', '{}'), false);
host.shell = {};
assert.equal(api.summon('omarchy.menu', '{}'), false);
host.shell = null;
assert.equal(api.summon('omarchy.menu', '{}'), false);
console.log('Installed-menu compatibility passed.');
