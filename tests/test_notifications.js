const assert = require('node:assert/strict');
const model = require('../home/NotificationModel.js');
const rows = [{key: '100-1', timestamp: 100}, {key: '100-2', timestamp: 100}];
let read = model.cursor(null);
assert.equal(model.count(rows, read), 2);
read = model.markRead(rows, read);
assert.equal(model.count(rows, read), 0);
assert.equal(model.count([...rows, {key: '100-3', timestamp: 100}], read), 1);
assert.equal(model.count([...rows, {key: '101-1', timestamp: 101}], read), 1);
assert.deepEqual(model.markRead([], read), read);
assert.deepEqual(model.cursor({timestamp: NaN}), {timestamp: 0, keys: []});
assert.deepEqual(model.cursor({timestamp: -1}), {timestamp: 0, keys: []});
assert.equal(model.badge(0), '');
assert.equal(model.badge(99), '99');
assert.equal(model.badge(100), '99+');
assert.deepEqual(model.command('dismissLatest'), ['dismissOne']);
assert.deepEqual(model.command('openLatest'), ['invokeLast']);
assert.deepEqual(model.command('clearHistory'), ['clear']);
assert.deepEqual(model.command('dndOn'), ['setDnd', 'on']);
assert.equal(model.command('arbitrary-command'), null);
assert.equal(model.command('dismiss;rm'), null);
assert.equal(model.command('__proto__'), null);
assert.equal(model.command('toString'), null);
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
assert.deepEqual(stable.values.map(row => row.key), ['b', 'a']);
model.sync(stable, []);
assert.equal(stable.count, 0);
console.log('Notification read/count/identity and public command tests passed.');
