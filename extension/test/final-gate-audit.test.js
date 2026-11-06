import test from 'node:test';
import assert from 'node:assert/strict';
import * as grid from '../src/core/grid.js';
import { tick } from '../src/core/engine.js';
import { runCommand } from '../src/core/commands.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { ConfigStore } from '../src/storage/store.js';
const { gridLevels, MAX_GRID_RUNGS } = grid;

async function context() {
  const store = new MemoryStore(); const configStore = new ConfigStore(null);
  await configStore.setConfig({ lower: 100, upper: 200, rungs: 5, spacing: 'arith' });
  await configStore.setRuntime({ armed: true });
  let placed = 0;
  const venue = { kind: 'spot', getPrice: async () => 150, getOpenOrders: async () => [], getFills: async () => [],
    placeOrder: async () => { placed++; return { venueOrderId: 'new' }; } };
  const deps = { store, configStore, buildVenue: async () => venue, log: () => {} };
  return { store, configStore, venue, deps, placed: () => placed };
}

test('kill requested during write-ahead persistence prevents the following venue submission', async () => {
  const ctx = await context(); const put = ctx.store.putIntent.bind(ctx.store); let stopping;
  ctx.store.putIntent = async (intent) => {
    await put(intent);
    stopping = runCommand({ name: 'kill', args: {}, deps: ctx.deps });
    await Promise.resolve();
  };
  const result = await tick(ctx);
  await stopping;
  assert.equal(ctx.placed(), 0);
  assert.ok(result.skipped.some((row) => row.reason === 'execution-stopped'));
  assert.ok((await ctx.store.allIntents()).every((row) => row.status !== 'resting'));
});

test('an unmatched historical sale holds new risk until its cost basis is established', async () => {
  const ctx = await context();
  await ctx.store.putFill({ id: 'unmatched', side: 'sell', baseQty: 10, priceUsd: 10,
    feeUsd: 0, feeUnknown: false, tsMs: 1 });
  const result = await tick(ctx);
  assert.equal(result.pnl.unmatchedSellQty, 10);
  assert.equal(ctx.placed(), 0);
  assert.ok(result.skipped.some((row) => row.reason === 'accounting-evidence-needs-review'));
});

test('rung allocation is bounded before any large loop or array allocation', () => {
  assert.equal(MAX_GRID_RUNGS, 10_000);
  for (const rungs of [10_001, Number.MAX_SAFE_INTEGER, Number.MAX_VALUE, Infinity]) {
    assert.throws(() => gridLevels({ lower: 100, upper: 200, rungs }), /rungs/i);
  }
  assert.equal(gridLevels({ lower: 100, upper: 200, rungs: MAX_GRID_RUNGS }).length, MAX_GRID_RUNGS);
});
