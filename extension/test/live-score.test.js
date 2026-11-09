import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { aggregatePredictions, appendScoreTick, scoreTickLayout } from '../src/ui/live-score.js';

test('browser votes match the shared Python policy vectors', async () => {
  const cases = JSON.parse(await readFile(new URL('../../soltui/tests/fixtures/live-score.json', import.meta.url), 'utf8'));
  for (const c of cases) {
    const actual = aggregatePredictions(c.rows, c.now, c.policy);
    assert.deepEqual(Object.fromEntries(Object.keys(c.expected).map((key) => [key, actual[key]])), c.expected, c.name);
  }
});

test('a tick score is immutable, keyed by source time and slides left on the next tick', () => {
  const a = { at: 1000, price: 100, aggregate: { score: 80, label: 'Strong Buy', color: 'green' } };
  const first = appendScoreTick([], a);
  const duplicate = appendScoreTick(first, { ...a, aggregate: { score: -100 } });
  assert.equal(duplicate, first);
  const second = appendScoreTick(first, { at: 2000, price: 101, aggregate: { score: -40, label: 'Sell', color: 'red' } });
  assert.equal(second[0].score, 80);
  assert.equal(scoreTickLayout(first)[0].plotX - scoreTickLayout(second)[0].plotX, 56);
  assert.equal(scoreTickLayout(second).at(-1).plotX, scoreTickLayout(first)[0].plotX);
  assert.equal(appendScoreTick(second, { at: 500, price: 90 }), second);
  assert.equal(appendScoreTick(second, { at: 3000, price: NaN }), second);
});

test('unknown tick scores remain unavailable and the rolling window is bounded', () => {
  let history = [];
  for (let i = 1; i <= 4; i++) history = appendScoreTick(history, { at: i, price: 100 }, 3);
  assert.deepEqual(history.map((p) => p.x), [2, 3, 4]);
  assert.equal(history[0].score, null);
  assert.equal(history[0].color, 'gray');
});
