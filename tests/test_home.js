const assert = require('node:assert/strict');
const model = require('../HomeModel.js');

assert.deepEqual(model.normalizeHidden(['media', 'media', '../../file', 'browser', 42]), ['media', 'browser']);
assert.deepEqual(model.normalizeHidden(null), []);
assert.equal(model.focusRemaining(1025000, 1500, 1000000), 25);
assert.equal(model.focusRemaining(990000, 1500, 1000000), 0);
assert.equal(model.focusRemaining(0, 742, 1000000), 742);
assert.equal(model.elapsed(1500), '25:00');
assert.equal(model.elapsed(-1), '0:00');
assert.equal(model.bytes(1024), '1.0 KiB');
assert.equal(model.bytes(null), '—');
const right = {x: 90, y: 0, name: 'right'};
assert.equal(model.nearest({x: 0, y: 0}, [{x: -20, y: 0}, {x: 20, y: 100}, right], 1, 0), right);
assert.equal(model.nearest({x: 0, y: 0}, [right], -1, 0), null);
assert.equal(model.ink({r: 120 / 255, g: 130 / 255, b: 75 / 255}), '#080b06');
console.log('Dicey Home preference filtering, deadline arithmetic, formatting, navigation, and contrast helpers passed.');
