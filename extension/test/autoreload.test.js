import test from 'node:test';
import assert from 'node:assert/strict';

import { checkForUpdate, OUTCOME, BUILD_STATE_KEY } from '../src/core/autoreload.js';
import { withStoreLock, enginePending } from '../src/core/engine.js';
import { SoltuiTransportError } from '../src/core/soltui.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { fakeHandle } from '../e2e/fixtures/fake-soltui-registry.js';

const H1 = '1'.repeat(64);
const H2 = '2'.repeat(64);

/** Everything the gate touches, faked. `host` is the hash the host reports, or an Error. */
function rig({ host = H1, saved, store = new MemoryStore() } = {}) {
  const state = new Map(saved ? [[BUILD_STATE_KEY, saved]] : []);
  const log = [];
  const reloads = [];
  const order = [];
  const rigState = {
    host,
    store,
    state,
    log,
    reloads,
    order,
    run: () => checkForUpdate({
      deps: {
        soltui: {
          async request(request) {
            if (rigState.host instanceof Error) throw new SoltuiTransportError('failed', 'down');
            return fakeHandle(request, { hash: rigState.host });
          },
        },
      },
      state: {
        get: async (key, fallback) => (state.has(key) ? state.get(key) : fallback),
        set: async (key, value) => { order.push('state'); state.set(key, value); },
      },
      pending: () => enginePending(store),
      withLock: (op) => withStoreLock(store, op),
      reload: () => { order.push('reload'); reloads.push(1); },
      logEvent: async (e) => { order.push(`log:${e.type}`); log.push(e); },
      describe: async () => ({ armed: false }),
      hold: async () => {},
    }),
  };
  return rigState;
}

test('the first observation only records the hash', async () => {
  const r = rig();
  assert.equal(await r.run(), OUTCOME.FIRST);
  assert.equal(r.reloads.length, 0);
  assert.deepEqual(r.state.get(BUILD_STATE_KEY), { hash: H1, hostDown: false });
  assert.deepEqual(r.log, []);
});

test('an unchanged hash does nothing', async () => {
  const r = rig({ saved: { hash: H1, hostDown: false } });
  assert.equal(await r.run(), OUTCOME.UNCHANGED);
  assert.equal(r.reloads.length, 0);
});

test('a changed hash on an idle engine reloads once, after the new hash and the log are written', async () => {
  const r = rig({ host: H2, saved: { hash: H1, hostDown: false } });
  assert.equal(await r.run(), OUTCOME.RELOADED);
  assert.equal(r.reloads.length, 1);
  assert.deepEqual(r.state.get(BUILD_STATE_KEY), { hash: H2, hostDown: false });
  // The hash is stored first: a reload that loses the write would reload forever.
  assert.deepEqual(r.order, ['state', 'log:auto-reload', 'reload']);
  assert.deepEqual(r.log[0], { type: 'auto-reload', from: H1.slice(0, 12), to: H2.slice(0, 12), armed: false });
});

test('the reload event holds no secret: only hash prefixes and flags', async () => {
  const r = rig({ host: H2, saved: { hash: H1 } });
  await r.run();
  assert.deepEqual(Object.keys(r.log[0]).sort(), ['armed', 'from', 'to', 'type']);
});

test('NO reload while a tick is in flight; the change is not forgotten', async () => {
  const r = rig({ host: H2, saved: { hash: H1, hostDown: false } });
  let finishTick;
  const tick = withStoreLock(r.store, () => new Promise((resolve) => { finishTick = resolve; }));
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(await r.run(), OUTCOME.DEFERRED);
  assert.equal(r.reloads.length, 0, 'must not reload mid-tick');
  assert.equal(r.state.get(BUILD_STATE_KEY).hash, H1, 'the new hash is NOT recorded, so the next minute retries');

  finishTick();
  await tick;
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(await r.run(), OUTCOME.RELOADED);
  assert.equal(r.reloads.length, 1);
});

test('NO reload when work is queued behind the lock between the idle check and the reload', async () => {
  const r = rig({ host: H2, saved: { hash: H1, hostDown: false } });
  // The gate sees an idle engine, then queues its own lock operation. A tick that
  // arrives in that window is queued too, so the gate defers instead of racing it.
  let queued;
  const original = r.run;
  const outcome = original();
  queued = withStoreLock(r.store, async () => {});
  assert.equal(await outcome, OUTCOME.DEFERRED);
  await queued;
  assert.equal(r.reloads.length, 0);
  assert.equal(r.state.get(BUILD_STATE_KEY).hash, H1);
});

test('the reload holds the engine lock so a tick queued afterwards cannot run first', async () => {
  const store = new MemoryStore();
  const reloads = [];
  const ran = [];
  let outcome;
  const state = new Map([[BUILD_STATE_KEY, { hash: H1 }]]);
  const attempt = checkForUpdate({
    deps: { soltui: { request: async (request) => fakeHandle(request, { hash: H2 }) } },
    state: { get: async (k, f) => state.get(k) ?? f, set: async (k, v) => state.set(k, v) },
    pending: () => enginePending(store),
    withLock: (op) => withStoreLock(store, op),
    reload: () => { reloads.push(1); setImmediate(() => { withStoreLock(store, async () => { ran.push('tick'); }); }); },
    logEvent: async () => {},
    // default hold: never settles, like the worker dying
  }).then((o) => { outcome = o; });
  await new Promise((resolve) => setTimeout(resolve, 50));
  assert.equal(reloads.length, 1);
  assert.deepEqual(ran, [], 'nothing queued after the reload may run');
  assert.equal(outcome, undefined, 'the lock is held until the worker is torn down');
  void attempt;
});

test('a host that cannot be reached never reloads and is logged once', async () => {
  const r = rig({ host: new Error('down'), saved: { hash: H1, hostDown: false } });
  assert.equal(await r.run(), OUTCOME.UNREACHABLE);
  assert.equal(await r.run(), OUTCOME.UNREACHABLE);
  assert.equal(await r.run(), OUTCOME.UNREACHABLE);
  assert.equal(r.reloads.length, 0);
  assert.deepEqual(r.log.map((e) => e.type), ['soltui-host-unreachable']);
  assert.equal(r.state.get(BUILD_STATE_KEY).hash, H1, 'the known hash survives an outage');
});

test('an unreachable host on the very first run never reloads either', async () => {
  const r = rig({ host: new Error('down') });
  assert.equal(await r.run(), OUTCOME.UNREACHABLE);
  assert.equal(r.reloads.length, 0);
});

test('recovery is logged, a later outage logs again, and recovery with a new hash still reloads once', async () => {
  const r = rig({ host: new Error('down'), saved: { hash: H1, hostDown: false } });
  await r.run();
  r.host = H2;
  assert.equal(await r.run(), OUTCOME.RELOADED);
  assert.deepEqual(r.log.map((e) => e.type), ['soltui-host-unreachable', 'soltui-host-reachable', 'auto-reload']);
  assert.equal(r.reloads.length, 1);
  r.host = new Error('down');
  await r.run();
  assert.deepEqual(r.log.map((e) => e.type).slice(-1), ['soltui-host-unreachable']);
});

test('recovery with an unchanged hash clears the outage flag', async () => {
  const r = rig({ host: H1, saved: { hash: H1, hostDown: true } });
  assert.equal(await r.run(), OUTCOME.UNCHANGED);
  assert.equal(r.state.get(BUILD_STATE_KEY).hostDown, false);
});

test('a malformed hash is ignored: it never reloads and never overwrites the stored one', async () => {
  for (const bad of ['xyz', 'A'.repeat(64), '1'.repeat(63)]) {
    const r = rig({ host: bad, saved: { hash: H1, hostDown: false } });
    const outcome = await r.run();
    assert.equal(outcome, OUTCOME.BAD_HASH, JSON.stringify(bad));
    assert.equal(r.reloads.length, 0);
    assert.equal(r.state.get(BUILD_STATE_KEY).hash, H1);
  }
});

test('if chrome.runtime.reload throws, the old hash is restored so the next minute retries', async () => {
  const store = new MemoryStore();
  const state = new Map([[BUILD_STATE_KEY, { hash: H1, hostDown: false }]]);
  const events = [];
  const outcome = await checkForUpdate({
    deps: { soltui: { request: async (request) => fakeHandle(request, { hash: H2 }) } },
    state: { get: async (k, f) => state.get(k) ?? f, set: async (k, v) => state.set(k, v) },
    pending: () => enginePending(store),
    withLock: (op) => withStoreLock(store, op),
    reload: () => { throw new Error('nope'); },
    logEvent: async (e) => events.push(e.type),
    hold: async () => {},
  });
  assert.equal(outcome, OUTCOME.DEFERRED);
  assert.equal(state.get(BUILD_STATE_KEY).hash, H1);
  assert.deepEqual(events, ['auto-reload', 'auto-reload-failed']);
});
