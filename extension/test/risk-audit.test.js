import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluate, admitBatch, normaliseLimits, DEFAULT_LIMITS } from '../src/core/risk.js';

const state = {
  openNotionalUsd: 0, openOrderCount: 0, realizedPnlUsdToday: 0, leverage: 1,
};
const order = { notionalUsd: 25, slippageBps: 100 };

test('unusable required account state refuses both individual and batch admission', () => {
  for (const key of Object.keys(state)) {
    for (const value of [undefined, null, NaN, Infinity, -Infinity, '0']) {
      const bad = { ...state, [key]: value };
      const single = evaluate({ order, state: bad });
      assert.equal(single.verdict, 'block', `${key}=${value}`);
      assert.ok(single.blockedBy.includes('unusable-state'));
      const batch = admitBatch({ intents: [{ ...order }], state: bad, slippageBps: 100 });
      assert.equal(batch.admitted.length, 0, `batch ${key}=${value}`);
      assert.ok(batch.rejected[0].blockedBy.includes('unusable-state'));
    }
  }
});

test('negative exposure and fractional account counts cannot create admission headroom', () => {
  for (const bad of [{ openNotionalUsd: -100 }, { openOrderCount: -1 }, { openOrderCount: 0.5 }, { leverage: -1 }]) {
    assert.equal(evaluate({ order, state: { ...state, ...bad } }).verdict, 'block');
  }
});

test('order notional must be positive and slippage cannot be negative', () => {
  for (const bad of [{ notionalUsd: -25 }, { notionalUsd: 0 }, { slippageBps: -1 }]) {
    const r = evaluate({ order: { ...order, ...bad }, state });
    assert.equal(r.verdict, 'block');
    assert.ok(r.blockedBy.includes('unusable-order'));
  }
});

test('count rails normalize fractional limits to finite integer defaults', () => {
  for (const key of ['maxConcurrentOrders', 'maxOrdersPerTick']) {
    for (const value of [0.5, Number.MAX_SAFE_INTEGER + 1]) {
      const result = normaliseLimits({ [key]: value });
      assert.equal(result[key], DEFAULT_LIMITS[key]);
      assert.ok(result.problems.some((p) => p.includes(key)));
    }
  }
});
