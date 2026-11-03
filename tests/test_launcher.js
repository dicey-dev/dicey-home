const assert = require('node:assert/strict');
const search = require('../Search.js');

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

console.log('Launcher arithmetic and URL handling passed.');
