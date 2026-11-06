import test from 'node:test';
import assert from 'node:assert/strict';
import { runCommand, CommandError } from '../src/core/commands.js';
import { tick } from '../src/core/engine.js';
import { evaluate, admitBatch } from '../src/core/risk.js';
import { ConfigStore } from '../src/storage/store.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { intentKey } from '../src/core/grid.js';

const now = Date.UTC(2026, 10, 6, 12);
async function setup({ price = 150, config = {}, fill = { baseQty: 0.25, priceUsd: 100 } } = {}) {
  const store = new MemoryStore(), configStore = new ConfigStore(null), orders = [];
  await configStore.setConfig({ lower: 100, upper: 200, rungs: 5, spacing: 'arith', ...config });
  await configStore.setRuntime({ armed: true });
  if (fill) await store.putFill({ id: 'prior-buy', side: 'buy', feeUsd: 0, tsMs: now, ...fill });
  const venue = { kind: 'spot', getPrice: async () => price, getOpenOrders: async () => [], getFills: async () => [],
    placeOrder: async ({ intent }) => { orders.push(intent); return { venueOrderId: `v${orders.length}` }; } };
  const deps = { store, configStore, buildVenue: async () => venue, clock: () => now };
  return { store, configStore, venue, orders, deps, clock: deps.clock };
}

test('financial records forbid execution-context changes and remain available for review', async () => {
  for (const patch of [{ mode: 'full-auto' }, { baseMint: 'DIFFERENT_BASE' }, { quoteMint: 'DIFFERENT_QUOTE' }, { userPubkey: 'DIFFERENT_WALLET' }, { venue: 'perps' }, { gridId: 'other-grid' }]) {
    const c = await setup();
    const config = await c.configStore.getConfig(), fills = await c.store.allFills();
    await assert.rejects(() => runCommand({ name: 'setConfig', args: { patch }, deps: c.deps }), e => e instanceof CommandError && e.status === 409);
    assert.deepEqual(await c.configStore.getConfig(), config);
    assert.deepEqual(await c.store.allFills(), fills);
    assert.equal((await c.configStore.getRuntime()).armed, false);
  }
  for (const kind of ['intent', 'carry']) {
    const c = await setup({ fill: null });
    if (kind === 'intent') await c.store.putIntent({ intentKey: 'history', status: 'filled' });
    else await c.store.putCarry({ id: 'cost', costUsd: 1, tsMs: now });
    await assert.rejects(() => runCommand({ name: 'setConfig', args: { mode: 'full-auto' }, deps: c.deps }), CommandError);
  }
});

test('explicit reset allows an empty new context and historical inventory never becomes its sell', async () => {
  const c = await setup();
  await runCommand({ name: 'reset', args: { confirm: true }, deps: c.deps });
  await runCommand({ name: 'setConfig', args: { patch: { mode: 'full-auto', baseMint: 'DIFFERENT_BASE', userPubkey: 'DIFFERENT_WALLET' } }, deps: c.deps });
  await runCommand({ name: 'arm', args: { confirmLive: true }, deps: c.deps });
  await runCommand({ name: 'tick', deps: c.deps });
  assert.ok(!c.orders.some(i => i.side === 'sell'));
});

test('near-cap filled inventory blocks new buys when its exit is unavailable', async () => {
  const c = await setup({ price: 100, config: { lower: 50, upper: 150, notionalPerRungUsd: 100 }, fill: { baseQty: 4.9, priceUsd: 100 } });
  const r = await tick(c);
  assert.equal(c.orders.filter(i => i.side === 'buy').length, 0);
  assert.ok(r.rejected.some(x => x.intent.side === 'sell' && x.blockedBy.includes('per-order-notional')));
  assert.ok(r.rejected.filter(x => x.intent.side === 'buy').every(x => x.blockedBy.includes('total-notional')));
});

test('appreciated inventory over cap can still place a fully covered exit without funding new bids', async () => {
  const c = await setup({ price: 600, config: { lower: 100, upper: 400, rungs: 4 }, fill: { baseQty: 1, priceUsd: 100 } });
  await tick({ ...c, limits: { maxTotalNotionalUsd: 500, maxNotionalPerOrderUsd: 1000 } });
  assert.equal(c.orders.filter(i => i.side === 'buy').length, 0);
  assert.equal(c.orders.filter(i => i.side === 'sell' && i.baseQty === 1).length, 1);
});

test('resting covered exits reserve inventory without double-counting its notional', async () => {
  const c = await setup({ price: 100, config: { lower: 50, upper: 150, notionalPerRungUsd: 25 }, fill: { baseQty: 1, priceUsd: 100 } });
  const key = intentKey({ gridId: 'grid-1', side: 'sell', level: 125 });
  await c.store.putIntent({ intentKey: key, side: 'sell', level: 125, baseQty: 1, notionalUsd: 125, lots: [{ priceUsd: 100, baseQty: 1 }], status: 'resting', venueOrderId: 'covered' });
  c.venue.getOpenOrders = async () => [{ venueOrderId: 'covered', side: 'sell', triggerPriceUsd: 125 }];
  await tick({ ...c, limits: { maxTotalNotionalUsd: 150 } });
  assert.equal(c.orders.filter(i => i.side === 'buy').reduce((n, i) => n + i.notionalUsd, 0), 50);
});

test('sell labels and supplied exemption flags cannot bypass total cap, and covered lots cannot be reserved twice', () => {
  const state = { openNotionalUsd: 600, openOrderCount: 0, realizedPnlUsdToday: 0, leverage: 1 };
  const sell = { notionalUsd: 100, slippageBps: 100, side: 'sell', baseQty: 1, lots: [{ priceUsd: 100, baseQty: 1 }], capitalIncreaseUsd: 0, coveredExit: true };
  assert.ok(evaluate({ order: sell, state }).blockedBy.includes('total-notional'));
  const r = admitBatch({ intents: [{ ...sell, intentKey: 'first' }, { ...sell, intentKey: 'second' }], state,
    limits: { maxTotalNotionalUsd: 500 }, slippageBps: 100, openLots: [{ priceUsd: 100, baseQty: 1 }] });
  assert.deepEqual(r.admitted.map(i => i.intentKey), ['first']);
  assert.ok(r.rejected[0].blockedBy.includes('total-notional'));
  for (const [limits, rail] of [[{ maxNotionalPerOrderUsd: 50 }, 'per-order-notional'], [{ maxConcurrentOrders: 0 }, 'concurrent-orders']]) {
    const result = evaluate({ order: sell, state, limits, openLots: [{ priceUsd: 100, baseQty: 1 }] });
    assert.ok(result.blockedBy.includes(rail));
  }
});

test('manual ladder edits disarm and explicit rearm cannot emit an exit below actual entry', async () => {
  const c = await setup({ price: 30, fill: { baseQty: 1, priceUsd: 100 } });
  await runCommand({ name: 'setConfig', args: { lower: 10, upper: 20 }, deps: c.deps });
  assert.equal((await c.configStore.getRuntime()).armed, false);
  await runCommand({ name: 'arm', deps: c.deps });
  const r = await runCommand({ name: 'tick', deps: c.deps });
  assert.ok(!c.orders.some(i => i.side === 'sell' && i.level <= 100));
  assert.ok(r.skipped.some(s => s.reason === 'exit-not-above-entry'));
});

test('missing live transaction verification is surfaced before journaling an order', async () => {
  const c = await setup({ fill: null });
  c.venue.executionBlockedReason = 'live-transaction-verifier-required';
  const r = await tick(c);
  assert.ok(r.skipped.some(s => s.reason === 'live-transaction-verifier-required'));
  assert.equal(c.orders.length, 0);
  assert.equal((await c.store.allIntents()).length, 0);
});
