import test from 'node:test';
import assert from 'node:assert/strict';
import { tick, reconcile, ingestFills, summarise } from '../src/core/engine.js';
import { runCommand, CommandError } from '../src/core/commands.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { ConfigStore, INTENT_STATUS } from '../src/storage/store.js';
import { intentKey } from '../src/core/grid.js';

const now = Date.UTC(2026, 10, 6, 12);
const key = (level, side = 'buy') => intentKey({ gridId: 'g', side, level });
async function setup() {
  const store = new MemoryStore();
  const configStore = new ConfigStore(null);
  await configStore.setConfig({ gridId: 'g', lower: 100, upper: 200, rungs: 5, spacing: 'arith', notionalPerRungUsd: 25 });
  await configStore.setRuntime({ armed: true });
  const logs = [];
  const venue = {
    kind: 'spot', getPrice: async () => 150, getOpenOrders: async () => [], getFills: async () => [],
    placeOrder: async ({ intent }) => ({ venueOrderId: `v-${intent.intentKey}` }),
    cancelOrder: async () => ({ cancelled: true }),
  };
  const deps = { store, configStore, buildVenue: async () => venue, clock: () => now, log: e => logs.push(e) };
  return { store, configStore, venue, deps, logs };
}
const drive = ({ store, configStore, venue, deps }) => tick({ store, configStore, venue, clock: deps.clock, log: deps.log });

test('ambiguous submit and local post-submit persistence failures hold rungs without retry', async () => {
  for (const localFailure of [false, true]) {
    const ctx = await setup(); let submits = 0;
    ctx.venue.placeOrder = async () => { submits++; if (!localFailure) throw new Error('response lost after acceptance'); return { venueOrderId: `accepted-${submits}` }; };
    if (localFailure) {
      const update = ctx.store.updateIntent.bind(ctx.store);
      ctx.store.updateIntent = async (k, patch) => { if (patch.status === 'resting') throw new Error('local write failed'); return update(k, patch); };
    }
    await drive(ctx); await drive(ctx);
    assert.equal(submits, 2);
    assert.ok((await ctx.store.allIntents()).every(i => i.status === 'unknown'));
    assert.ok(ctx.logs.some(e => e.level === 'error'));
  }
});

test('reconcile preserves two exact-price orders and their rung occupation across ticks', async () => {
  const ctx = await setup();
  ctx.venue.getOpenOrders = async () => ['a', 'b'].map(venueOrderId => ({ venueOrderId, side: 'buy', triggerPriceUsd: 100, notionalUsd: 25 }));
  for (let n = 0; n < 2; n++) {
    const r = await reconcile({ ...ctx, config: await ctx.configStore.getConfig() });
    assert.equal(r.restingKeys.length, 2);
    assert.equal(new Set((await ctx.store.allIntents()).map(i => i.venueOrderId)).size, 2);
  }
  await ctx.configStore.set('limits', { maxConcurrentOrders: 2 });
  const r = await tick({ ...ctx, limits: { maxConcurrentOrders: 2 } });
  assert.equal(r.placed.length, 0);
});

test('risk exposure uses journaled notional after rung-size edits and refuses unknown adopted size', async () => {
  for (const known of [true, false]) {
    const ctx = await setup();
    if (known) await ctx.store.putIntent({ intentKey: key(100), side: 'buy', level: 100, notionalUsd: 400, status: 'resting', venueOrderId: 'old' });
    ctx.venue.getOpenOrders = async () => [{ venueOrderId: 'old', side: 'buy', triggerPriceUsd: 100 }];
    const r = await tick({ ...ctx, limits: { maxTotalNotionalUsd: 410 } });
    assert.equal(r.placed.length, 0);
    assert.ok(r.rejected.length || r.errors.length);
  }
});

test('UTC-day loss includes a previous-day lot sold before first wake and excludes yesterday realization', async () => {
  const ctx = await setup();
  const midnight = Date.UTC(2026, 10, 6);
  await ctx.store.putFill({ id: 'old-buy', side: 'buy', priceUsd: 100, baseQty: 1, feeUsd: 0, tsMs: midnight - 100 });
  await ctx.store.putFill({ id: 'past-buy', side: 'buy', priceUsd: 100, baseQty: 1, feeUsd: 0, tsMs: midnight - 300 });
  await ctx.store.putFill({ id: 'past-sell', side: 'sell', priceUsd: 80, baseQty: 1, feeUsd: 0, tsMs: midnight - 200 });
  ctx.venue.getFills = async () => [{ venueOrderId: 'today-sell', side: 'sell', executedPriceUsd: 40, filledBaseQty: 1, feeUsd: 0, updatedAtMs: midnight + 100 }];
  const r = await drive(ctx);
  assert.equal(r.realizedPnlUsdToday, -60);
  assert.equal(r.placed.length, 0);
  assert.ok(r.rejected.every(x => x.blockedBy.includes('daily-loss-limit')));
});

test('unknown fee warning and stored tick summary persist on repeated history reads', async () => {
  const ctx = await setup();
  ctx.venue.getFills = async () => [{ venueOrderId: 'no-fee', side: 'buy', executedPriceUsd: 100, filledBaseQty: 0.25, feeUsd: null, updatedAtMs: now - 1 }];
  for (let n = 0; n < 2; n++) {
    const r = await drive(ctx);
    assert.equal(r.feeUnknownFills, 1);
    assert.equal(summarise(r).feeUnknownFills, 1);
  }
});

test('concurrent ticks serialize and failed ticks release the queue', async () => {
  const ctx = await setup(); let submits = 0;
  ctx.venue.placeOrder = async () => ({ venueOrderId: `v${++submits}` });
  await Promise.all([drive(ctx), drive(ctx)]);
  assert.equal(submits, 2);
  ctx.venue.getPrice = async () => { throw new Error('read failed'); };
  await drive(ctx);
  ctx.venue.getPrice = async () => 175;
  await drive(ctx);
  assert.equal(submits, 3);
});

test('kill interrupts the remaining admitted batch and reset waits before clearing the journal', async () => {
  for (const command of ['kill', 'reset']) {
    const ctx = await setup(); let stop; let submits = 0;
    ctx.venue.placeOrder = async ({ intent }) => {
      submits++;
      stop = runCommand({ name: command, args: command === 'reset' ? { confirm: true } : {}, deps: ctx.deps });
      return { venueOrderId: intent.intentKey };
    };
    await drive(ctx); await stop;
    assert.equal(submits, 1);
    assert.equal((await ctx.configStore.getRuntime()).armed, false);
    if (command === 'reset') assert.equal((await ctx.store.allIntents()).length, 0);
  }
});

test('mode changes disarm first, and a failed safety write preserves configuration', async () => {
  const ctx = await setup();
  await runCommand({ name: 'setConfig', args: { mode: 'full-auto' }, deps: ctx.deps });
  assert.equal((await ctx.configStore.getRuntime()).armed, false);
  await assert.rejects(() => runCommand({ name: 'arm', deps: ctx.deps }), CommandError);
  const other = await setup();
  other.configStore.setRuntime = async () => { throw new Error('write failed'); };
  await assert.rejects(() => runCommand({ name: 'setConfig', args: { mode: 'full-auto' }, deps: other.deps }));
  assert.equal((await other.configStore.getConfig()).mode, 'dry-run');
});

test('live confirmation is a literal boolean and registry enforces declared argument types', async () => {
  const ctx = await setup(); await ctx.configStore.setConfig({ mode: 'full-auto' });
  for (const confirmLive of ['false', 'true', 1, {}, []]) await assert.rejects(() => runCommand({ name: 'arm', args: { confirmLive }, deps: ctx.deps }), CommandError);
  const r = await runCommand({ name: 'arm', args: { confirmLive: true }, deps: ctx.deps });
  assert.equal(r.runtime.armed, true);
  await assert.rejects(() => runCommand({ name: 'tick', args: { count: '2' }, deps: ctx.deps }), CommandError);
});

test('config patch validates actual schema without echoing synthetic secret values', async () => {
  const ctx = await setup();
  for (const patch of [{ mode: '' }, { mode: null }, { mode: false }, { apiKey: 'SYNTHETIC_SECRET' }, { autoRecentre: 'false' }, { leverage: null }, { slippageBps: -1 }, { direction: 'bogus' }, { rungs: 2.5 }, []]) {
    await assert.rejects(() => runCommand({ name: 'setConfig', args: { patch }, deps: ctx.deps }), e => e instanceof CommandError && !e.message.includes('SYNTHETIC_SECRET'));
  }
  assert.equal((await ctx.configStore.getConfig()).mode, 'dry-run');
  await assert.rejects(() => runCommand({ name: 'setLimits', args: { maxOrdersPerTick: 0.5 }, deps: ctx.deps }), CommandError);
});

test('unconfirmed cancellations hold the rung, confirmed cancellations release it', async () => {
  for (const result of [{ cancelled: false }, {}, { pending: true }, { cancelled: true }]) {
    const ctx = await setup(); await ctx.store.putIntent({ intentKey: key(100), venueOrderId: 'v', side: 'buy', level: 100, notionalUsd: 25, status: 'resting' });
    ctx.venue.cancelOrder = async () => result;
    await runCommand({ name: 'cancelOrder', args: { venueOrderId: 'v' }, deps: ctx.deps });
    assert.equal((await ctx.store.getIntent(key(100))).status, result.cancelled === true ? 'cancelled' : 'unknown');
  }
});

test('multi-tick command reloads limits after a queued cap change', async () => {
  const ctx = await setup(); let reads = 0; let tightening;
  ctx.venue.getPrice = async () => ++reads === 1 ? 150 : 200;
  ctx.venue.placeOrder = async ({ intent }) => {
    if (!tightening) tightening = runCommand({ name: 'setLimits', args: { maxOrdersPerTick: 0 }, deps: ctx.deps });
    return { venueOrderId: intent.intentKey };
  };
  const r = await runCommand({ name: 'tick', args: { count: 2 }, deps: ctx.deps }); await tightening;
  assert.equal(r.ticks[0].placed.length, 2);
  assert.equal(r.ticks[1].placed.length, 0);
});

test('reset disarms before erasure and a failed safety write retains journal', async () => {
  const ctx = await setup(); await ctx.store.putIntent({ intentKey: 'pending', status: 'unknown' });
  ctx.configStore.setRuntime = async () => { throw new Error('simulated persistence failure'); };
  await assert.rejects(() => runCommand({ name: 'reset', args: { confirm: true }, deps: ctx.deps }));
  assert.equal((await ctx.store.allIntents()).length, 1);
});

test('plan preview holds UNKNOWN and SUBMITTING rungs without mutation', async () => {
  const ctx = await setup();
  for (const [level, status] of [[100, INTENT_STATUS.UNKNOWN], [125, INTENT_STATUS.SUBMITTING]]) await ctx.store.putIntent({ intentKey: key(level), side: 'buy', level, status, notionalUsd: 25 });
  const before = await ctx.store.allIntents();
  const r = await runCommand({ name: 'plan', args: { price: 150 }, deps: ctx.deps });
  assert.equal(r.intents.length, 0);
  assert.deepEqual(await ctx.store.allIntents(), before);
});

test('uncertain execution history blocks trading and never borrows planned price or quantity', async () => {
  for (const sparse of [{ filledBaseQty: 0.25 }, { executedPriceUsd: 101 }, { unusable: true, missingFields: ['execution'] }]) {
    const ctx = await setup();
    await ctx.store.putIntent({ intentKey: key(100), side: 'buy', level: 100, baseQty: 0.25, notionalUsd: 25, status: 'unknown', venueOrderId: 'ambiguous' });
    ctx.venue.getFills = async () => [{ venueOrderId: 'ambiguous', side: 'buy', triggerPriceUsd: 100, updatedAtMs: now, ...sparse }];
    const ingested = await ingestFills({ ...ctx, config: await ctx.configStore.getConfig() });
    assert.equal(ingested.blocked, true);
    assert.equal(ingested.added.length, 0);
    const r = await drive(ctx);
    assert.equal(r.placed.length, 0);
    assert.ok(r.skipped.some(s => s.reason === 'execution-history-needs-review'));
    assert.ok(ctx.logs.some(e => e.level === 'warn'));
    assert.equal((await ctx.store.allFills()).length, 0);
  }
});

test('positive proof of no execution can be ignored without blocking otherwise safe trading', async () => {
  const ctx = await setup();
  ctx.venue.getFills = async () => [{ venueOrderId: 'never-filled', status: 'cancelled', executionAbsent: true, filledBaseQty: 0 }];
  const r = await drive(ctx);
  assert.equal(r.placed.length, 2);
  assert.equal((await ctx.store.allFills()).length, 0);
});

test('legacy unknown configuration fields never reach getConfig or status', async () => {
  const ctx = await setup();
  await ctx.configStore.set('config', { apiKey: 'LEGACY_SYNTHETIC_SECRET', sessionKeyVault: { secret: 'LEGACY_SYNTHETIC_SECRET' } });
  const config = await runCommand({ name: 'getConfig', deps: ctx.deps });
  const status = await runCommand({ name: 'status', deps: ctx.deps });
  assert.ok(!JSON.stringify({ config, status }).includes('LEGACY_SYNTHETIC_SECRET'));
});

test('a different known venue identity cannot consume an unresolved intent at the same rung', async () => {
  const ctx = await setup();
  await ctx.store.putIntent({ intentKey: key(100), side: 'buy', level: 100, status: 'unknown', venueOrderId: 'old-ambiguous', notionalUsd: 400 });
  ctx.venue.getOpenOrders = async () => [{ venueOrderId: 'different-live', side: 'buy', triggerPriceUsd: 100, notionalUsd: 25 }];
  const r = await tick({ ...ctx, limits: { maxTotalNotionalUsd: 430 } });
  assert.equal((await ctx.store.getIntent(key(100))).status, 'unknown');
  assert.equal((await ctx.store.allIntents()).filter(i => i.level === 100).length, 2);
  assert.equal(r.placed.length, 0);
});

test('an old fill cannot mark a different live order at the same rung filled', async () => {
  const ctx = await setup();
  await ctx.store.putIntent({ intentKey: key(100), side: 'buy', level: 100, status: 'resting', venueOrderId: 'new-live', notionalUsd: 25 });
  ctx.venue.getFills = async () => [{ venueOrderId: 'old-filled', side: 'buy', triggerPriceUsd: 100, executedPriceUsd: 100, filledBaseQty: 0.25, feeUsd: 0 }];
  await ingestFills({ ...ctx, config: await ctx.configStore.getConfig() });
  assert.equal((await ctx.store.getIntent(key(100))).status, 'resting');
});

test('an earlier queued arm cannot revoke a later immediate kill request', async () => {
  const ctx = await setup();
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  ctx.venue.getPrice = async () => { await gate; return 150; };
  let submits = 0;
  ctx.venue.placeOrder = async () => ({ venueOrderId: `v-${++submits}` });
  const active = drive(ctx);
  const earlierArm = runCommand({ name: 'arm', deps: ctx.deps });
  const queuedTick = drive(ctx);
  const laterKill = runCommand({ name: 'kill', deps: ctx.deps });
  release();
  const outcomes = await Promise.allSettled([active, earlierArm, queuedTick, laterKill]);
  assert.equal(outcomes[0].status, 'fulfilled');
  assert.equal(outcomes[1].status, 'rejected', 'the obsolete arm must report its refusal');
  assert.ok(outcomes[1].reason.status === 409 || outcomes[1].reason.code === 'RUNTIME_STOP_CHANGED');
  assert.equal(outcomes[2].status, 'fulfilled');
  assert.equal(outcomes[3].status, 'fulfilled');
  assert.equal(submits, 0);
  assert.equal((await ctx.configStore.getRuntime()).killSwitch, true);
});
