const assert = require('node:assert/strict');
const model = require('../home/NotificationModel.js');
const now = 10 * 24 * 3600 * 1000;
const row = (key, timestamp, group, extra = {}) => ({key, timestamp, group, groupLabel: group.split(':')[1], groupKind: group.split(':')[0], browser: '', ...extra});

// Removal memory: validated, bounded and forgotten after the host's retention.
assert.deepEqual(model.removed(null, now), {});
assert.deepEqual(model.removed([], now), {});
const stored = {good: now - 1000, 'bad key': now, old: now - 49 * 3600 * 1000, held: now - 72 * 3600 * 1000, future: now + 3600000, nan: NaN, str: '1'};
// Before the first snapshot nothing expires; afterwards only keys the host no longer holds do.
assert.deepEqual(model.removed(stored, now, null), {good: now - 1000, old: now - 49 * 3600 * 1000, held: now - 72 * 3600 * 1000});
assert.deepEqual(model.removed(stored, now, ['held']), {held: now, good: now - 1000});
let removed = model.remove({}, ['a', 7, 'b'], now);
assert.deepEqual(removed, {a: now, b: now});
const many = {};
for (let i = 0; i < 1100; i++) many['k' + i] = now - i;
assert.equal(Object.keys(model.removed(many, now, [])).length, 1024);
assert.ok('k0' in model.removed(many, now, []) && !('k1099' in model.removed(many, now, [])));

// Visible rows exclude removed keys, and prototype keys are not special.
const rows = [row('a', 5, 'app:mail'), row('b', 9, 'site:example.com', {groupKind: 'site', browser: 'Chromium'}),
  row('c', 7, 'app:mail'), row('constructor', 1, 'app:term')];
assert.deepEqual(model.visible(rows, removed).map(r => r.key), ['c', 'constructor']);

// Groups ordered by newest entry; entries newest first and contiguous.
const arranged = model.arrange(rows);
assert.deepEqual(arranged.order, ['site:example.com', 'app:mail', 'app:term']);
assert.deepEqual(arranged.rows.map(r => r.key), ['b', 'c', 'a', 'constructor']);
assert.deepEqual(arranged.groups['app:mail'], {label: 'mail', kind: 'app', browsers: [], count: 2, keys: ['c', 'a']});
// One website seen from two browsers names both.
const mixed = model.arrange([row('x', 2, 'site:example.com', {browser: 'Firefox'}), row('y', 1, 'site:example.com', {browser: 'Chromium'})]);
assert.deepEqual(mixed.groups['site:example.com'].browsers, ['Chromium', 'Firefox']);
assert.equal(model.caption(Object.assign({id: 'site:example.com'}, mixed.groups['site:example.com'])), 'Chromium, Firefox');
assert.deepEqual(model.arrange([]), {rows: [], groups: {}, order: []});

assert.equal(model.caption({id: 'webapp:web.whatsapp.com', kind: 'webapp', browsers: ['Chromium']}), 'web.whatsapp.com · Chromium');
assert.equal(model.caption({id: 'site:example.com', kind: 'site', browsers: ['Firefox']}), 'Firefox');
assert.equal(model.caption({id: 'app:mail', kind: 'app', browsers: []}), '');
assert.equal(model.caption(null), '');

// Only DND reaches the host; nothing in Home invokes, dismisses or clears host state.
assert.deepEqual(model.command('dndOn'), ['setDnd', 'on']);
assert.deepEqual(model.command('dndOff'), ['setDnd', 'off']);
for (const name of ['clearHistory', 'dismissLatest', 'openLatest', 'replay', 'arbitrary-command', 'dismiss;rm', '__proto__', 'toString'])
  assert.equal(model.command(name), null);

// A stable model changes individual rows rather than clearing/replacing them.
const stable = {
  values: [], operations: [],
  get count() { return this.values.length; },
  get(i) { return this.values[i]; },
  insert(i, row) { this.operations.push('insert'); this.values.splice(i, 0, {...row}); },
  move(from, to) { this.operations.push('move'); this.values.splice(to, 0, this.values.splice(from, 1)[0]); },
  set(i, row) { this.operations.push('set'); Object.assign(this.values[i], row); },
  remove(i, count) { this.operations.push('remove'); this.values.splice(i, count); },
};
model.sync(stable, [{key: 'a', live: true}, {key: 'b', live: false}]);
const a = stable.get(0), b = stable.get(1);
stable.operations = [];
model.sync(stable, [{key: 'a', live: true}, {key: 'b', live: false}]);
assert.deepEqual(stable.operations, []);
model.sync(stable, [{key: 'new', live: true}, {key: 'a', live: false}, {key: 'b', live: false}]);
assert.equal(stable.get(1), a);
assert.equal(stable.get(2), b);
assert.equal(a.live, false);
assert.deepEqual(stable.operations, ['insert', 'set']);
model.sync(stable, [{key: 'b', live: false}, {key: 'a', live: false}]);
assert.equal(stable.get(0), b);
assert.equal(stable.get(1), a);
// Removing a middle row removes it in place: survivors keep their order and
// objects, so ListView's selection moves to the neighbour, not the list's end.
model.sync(stable, [{key: 'a'}, {key: 'b'}, {key: 'c'}, {key: 'd'}]);
const [ra, rc, rd] = [stable.get(0), stable.get(2), stable.get(3)];
stable.operations = [];
model.sync(stable, [{key: 'a'}, {key: 'c'}, {key: 'd'}]);
assert.deepEqual(stable.operations, ['remove']);
assert.equal(stable.get(0), ra); assert.equal(stable.get(1), rc); assert.equal(stable.get(2), rd);
model.sync(stable, []);
assert.equal(stable.count, 0);
console.log('Notification grouping/removal/identity and public command tests passed.');
