import test from 'node:test';
import assert from 'node:assert/strict';
import { ConfigStore, RUNTIME_KEY } from '../src/storage/store.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { tick } from '../src/core/engine.js';
import { evaluate, admitBatch } from '../src/core/risk.js';

const state = { openNotionalUsd: 0, openOrderCount: 0, realizedPnlUsdToday: 0, leverage: 1 };
const order = { notionalUsd: 25, slippageBps: 100 };

test('invalid persisted numeric limits cannot authorize orders using a looser default', () => {
  for (const limits of [{ maxNotionalPerOrderUsd: null }, { maxTotalNotionalUsd: '10' }, { maxOrdersPerTick: 0.5 }]) {
    const single = evaluate({ order, state, limits });
    assert.equal(single.verdict, 'block');
    assert.ok(single.blockedBy.includes('unusable-limits'));
    const batch = admitBatch({ intents: [order], state, limits, slippageBps: 100 });
    assert.equal(batch.admitted.length, 0);
    assert.ok(batch.rejected[0].blockedBy.includes('unusable-limits'));
  }
});

test('an explicit invalid kill-switch value stays engaged in both admission paths', () => {
  for (const killSwitch of [null, undefined, 0, '', 'false', [], {}]) {
    const limits = { killSwitch };
    assert.equal(evaluate({ order, state, limits }).verdict, 'block');
    assert.equal(admitBatch({ intents: [order], state, limits, slippageBps: 100 }).admitted.length, 0);
  }
});

test('persisted runtime never treats a truthy non-boolean armed flag as consent', async () => {
  for (const armed of ['false', 'true', 1, [], {}]) {
    const configStore = new ConfigStore(null);
    await configStore.set(RUNTIME_KEY, { armed, killSwitch: false });
    const store = new MemoryStore();
    await configStore.setConfig({ lower: 100, upper: 200, rungs: 5, spacing: 'arith', notionalPerRungUsd: 25 });
    let submits = 0;
    const venue = { kind: 'spot', getPrice: async () => 150, getOpenOrders: async () => [], getFills: async () => [],
      placeOrder: async () => { submits++; return { venueOrderId: `fake-${submits}` }; } };
    await tick({ store, configStore, venue });
    assert.equal(submits, 0);
    assert.equal((await configStore.getRuntime()).armed, false);
  }
});

test('malformed runtime latches safe state while valid partial legacy state keeps defaults', async () => {
  const configStore = new ConfigStore(null);
  for (const malformed of [null, [], 'armed']) {
    await configStore.set(RUNTIME_KEY, malformed);
    const runtime = await configStore.getRuntime();
    assert.equal(runtime.armed, false);
    assert.equal(runtime.killSwitch, true);
  }
  for (const killSwitch of [null, 0, '', 'false']) {
    await configStore.set(RUNTIME_KEY, { armed: true, killSwitch });
    assert.equal((await configStore.getRuntime()).killSwitch, true);
  }
  await configStore.set(RUNTIME_KEY, { armed: true });
  assert.equal((await configStore.getRuntime()).armed, true);
  assert.equal((await configStore.getRuntime()).killSwitch, false);
});


test('malformed limit documents remain unusable through the command and engine boundary', async () => {
  const { runCommand } = await import('../src/core/commands.js');
  for (const limits of [null, [], 'caps']) {
    assert.equal(evaluate({ order, state, limits }).verdict, 'block');
    assert.equal(admitBatch({ intents: [order], state, limits, slippageBps: 100 }).admitted.length, 0);
    const configStore = new ConfigStore(null);
    await configStore.setConfig({ lower: 100, upper: 200, rungs: 5, spacing: 'arith', notionalPerRungUsd: 25 });
    await configStore.setRuntime({ armed: true });
    await configStore.set('limits', limits);
    let submits = 0;
    const venue = { kind: 'spot', getPrice: async () => 150, getOpenOrders: async () => [], getFills: async () => [],
      placeOrder: async () => { submits++; return { venueOrderId: `fake-${submits}` }; } };
    const result = await runCommand({ name: 'tick', deps: { store: new MemoryStore(), configStore, buildVenue: async () => venue } });
    assert.equal(submits, 0);
    assert.ok(result.rejected.every(x => x.blockedBy.includes('unusable-limits')));
  }
});


test('a queued lifecycle change reads the latest paper-manager generation under the engine lease', async () => {
  const { runCommand } = await import('../src/core/commands.js');
  const { withStoreLock } = await import('../src/core/engine.js');
  const { MANAGER_KEY } = await import('../src/core/bot-manager.js');
  const configStore = new ConfigStore(null), store = new MemoryStore();
  await configStore.set(MANAGER_KEY, { running: true, generation: 1 });
  let release, entered;
  const gate = new Promise(resolve => { release = resolve; });
  const started = new Promise(resolve => { entered = resolve; });
  const owner = withStoreLock(store, async () => {
    entered(); await gate;
    await configStore.set(MANAGER_KEY, { running: true, generation: 2 });
  });
  await started;
  const stopped = runCommand({ name: 'disarm', deps: { store, configStore } });
  await new Promise(resolve => setImmediate(resolve));
  release(); await owner; await stopped;
  assert.equal((await configStore.get(MANAGER_KEY)).running, false);
  assert.equal((await configStore.get(MANAGER_KEY)).generation, 3);
});


test('disk-backed null limits stay invalid and corrupt intents retain their original evidence', async t => {
  const { mkdtemp, rm } = await import('node:fs/promises');
  const { tmpdir } = await import('node:os');
  const { join } = await import('node:path');
  const { FileStore, createFileArea } = await import('../src/storage/fileStore.js');
  const { runCommand } = await import('../src/core/commands.js');
  const home = await mkdtemp(join(tmpdir(), 'smt-persisted-boundary-'));
  t.after(() => rm(home, { recursive: true, force: true }));
  const configStore = new ConfigStore(createFileArea(join(home, 'config.json')));
  const store = await FileStore.open(join(home, 'journal.json'));
  await configStore.setRuntime({ armed: true });
  await configStore.set('limits', null);
  let calls = 0;
  const venue = { kind: 'spot', getPrice: async () => 75, getOpenOrders: async () => [], getFills: async () => [],
    placeOrder: async () => { calls++; return { venueOrderId: 'must-not-submit' }; } };
  const deps = { store, configStore, buildVenue: async () => venue };
  const nullLimit = await runCommand({ name: 'tick', deps });
  assert.equal(await configStore.get('limits', {}), null);
  assert.equal(calls, 0); assert.ok(nullLimit.rejected.every(row => row.blockedBy.includes('unusable-limits')));
  await configStore.set('limits', {});
  const record = { intentKey: 'grid-1:buy:60000000', side: 'buy', level: 60, notionalUsd: 12,
    status: 'CORRUPT_STATUS', txSignature: 'synthetic-unresolved-evidence' };
  await store.putIntent(record);
  const held = await runCommand({ name: 'tick', deps });
  assert.equal(calls, 0);
  assert.ok(held.skipped.some(row => row.reason === 'journal-evidence-needs-review'));
  assert.deepEqual(await store.getIntent(record.intentKey), record);
});

test('stale arm and clear snapshots lose to a later kill, including malformed stop generations', async () => {
  const configStore = new ConfigStore(null);
  const earlier = (await configStore.getRuntime()).stopGeneration;
  await configStore.killRuntime();
  for (const patch of [{ armed: true }, { killSwitch: false }]) {
    await assert.rejects(configStore.setRuntime(patch, { expectedStopGeneration: earlier }), error => error.code === 'RUNTIME_STOP_CHANGED');
  }
  await configStore.setRuntime({ armed: false, killSwitch: false, lastTickMs: 123 });
  assert.equal((await configStore.getRuntime()).killSwitch, true, 'an initialization writer cannot erase the latch');
  for (const stopGeneration of [null, -1, 0.5, true, '1', Number.MAX_SAFE_INTEGER + 1]) {
    await configStore.set(RUNTIME_KEY, { armed: true, killSwitch: false, stopGeneration });
    const runtime = await configStore.getRuntime();
    assert.equal(runtime.armed, false); assert.equal(runtime.killSwitch, true);
    await assert.rejects(configStore.setRuntime({ killSwitch: false }, { expectedStopGeneration: stopGeneration }),
      error => error.code === 'RUNTIME_STOP_CHANGED');
  }
});
