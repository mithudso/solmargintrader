import test from 'node:test';
import assert from 'node:assert/strict';
import { gridLevels, intentKey } from '../src/core/grid.js';

test('a ladder whose actual generated rung keys collide is refused', () => {
  assert.throws(() => gridLevels({ lower: 100, upper: 100.0000018, rungs: 4, spacing: 'arith' }), RangeError);
});

test('positive half-microdollar key rounds up, matching the Python grid simulator', () => {
  assert.equal(intentKey({ gridId: 'g', side: 'buy', level: 100.0000005 }), 'g:buy:100000001');
});
