import test from 'node:test';
import assert from 'node:assert/strict';
import { LiveOracleStore, LIVE_ORACLE_DB } from '../src/1000x/oracle-live-store.js';
import { newLiveState, transitionLive } from '../src/1000x/oracle-live-model.js';

// Simulates atomic serialized transactions; native IndexedDB needs a browser gate.
function fakeIndexedDB() {
  const maps = new Map(); let tail = Promise.resolve(), fail = false, opened, writes = [];
  const db = { createObjectStore(name) { maps.set(name, new Map()); return { createIndex() {} }; }, close() {}, transaction(_names, mode) {
    const tasks = [], staged = [], tx = { aborted: false, abort() { this.aborted = true; }, objectStore(name) { const map = maps.get(name); return {
      get(key) { const r = {}; tasks.push(() => { r.result = structuredClone(map.get(key)); r.onsuccess?.(); }); return r; },
      index() { return { getAll(key) { const r = {}; tasks.push(() => { r.result = [...map.values()].filter(v => v.key === key).map(v => structuredClone(v)); r.onsuccess?.(); }); return r; } }; },
      count() { const r = {}; tasks.push(() => { r.result = map.size; r.onsuccess?.(); }); return r; },
      put(row) { tasks.push(() => staged.push({ name, key: name === 'partitions' ? row.key : row.id, row: structuredClone(row) })); },
      delete(key) { tasks.push(() => staged.push({ name, key, remove: true })); },
    }; } };
    const run = async () => { await Promise.resolve(); while (tasks.length && !tx.aborted) tasks.shift()();
      if (fail && mode === 'readwrite') { fail = false; tx.aborted = true; }
      if (tx.aborted) tx.onabort?.(); else { writes = staged; for (const op of staged) op.remove ? maps.get(op.name).delete(op.key) : maps.get(op.name).set(op.key, op.row); tx.oncomplete?.(); } };
    tail = tail.then(run); return tx;
  } };
  return { failNext() { fail = true; }, get writes() { return writes; }, get opened() { return opened; }, open(name) { opened = name; const r = {};
    queueMicrotask(() => { r.result = db; if (!maps.size) r.onupgradeneeded?.(); r.onsuccess?.(); }); return r; } };
}
const identity = { market: 'BTC', source: 'test' };
test('separate database serializes concurrent reducers and reloads committed revisions', async () => {
  const fake = fakeIndexedDB(), a = new LiveOracleStore(fake), b = new LiveOracleStore(fake), initial = newLiveState(identity), key = initial.key;
  const reduce = old => { const state = old ?? initial; state.revision++; return { changed: true, state }; };
  await Promise.all([a.update(key, reduce), b.update(key, reduce)]);
  assert.equal(fake.opened, LIVE_ORACLE_DB); assert.equal((await b.load(key)).revision, 2);
  a.close(); b.close();
});
test('aborted storage and asynchronous reducer preserve prior committed state', async () => {
  const fake = fakeIndexedDB(), s = new LiveOracleStore(fake), initial = newLiveState(identity), key = initial.key;
  await s.update(key, () => ({ changed: true, state: { ...initial, revision: 1 } }));
  fake.failNext(); await assert.rejects(s.update(key, state => ({ changed: true, state: { ...state, revision: 2 } })), /transaction_failed/);
  await assert.rejects(s.update(key, async () => ({})), /async_transaction/);
  assert.equal((await s.load(key)).revision, 1); s.close();
});
test('ordinary state update does not rewrite unchanged pending or metric records', async () => {
  const fake = fakeIndexedDB(), s = new LiveOracleStore(fake), state = newLiveState(identity), key = state.key;
  state.pending.push({ id: 'one', issuedAtMs: 1, horizon: 60 });
  await s.update(key, () => ({ changed: true, state }));
  await s.update(key, prior => { prior.revision++; return { changed: true, state: prior }; });
  assert.deepEqual(fake.writes.map(v => v.name), ['partitions']);
  assert.equal((await s.load(key)).pending[0].id, 'one'); s.close();
});
test('peak six-horizon queue reconstructs and writes only changed records', async () => {
  let state = null; const observe = (previous, nowMs) => transitionLive(previous, { identity,
    quote: { price: 100 + Math.sin(nowMs / 60000) / 10, exchangeMs: nowMs, receivedMs: nowMs }, nowMs });
  for (let t = 0; t <= 3_660_000; t += 1000) state = observe(state, t).state;
  assert.equal(state.pending.length, 1332);
  const fake = fakeIndexedDB(), store = new LiveOracleStore(fake), key = state.key;
  await store.update(key, () => ({ changed: true, state }));
  assert.deepEqual(await store.load(key), state);
  let maxBytes = 0, maxWrites = 0;
  for (let t = 3_661_000; t <= 3_665_000; t += 1000) {
    const expected = observe(state, t); const result = await store.update(key, prior => observe(prior, t));
    state = expected.state; assert.deepEqual(result.state, state);
    const bytes = Buffer.byteLength(JSON.stringify(fake.writes)); maxBytes = Math.max(maxBytes, bytes); maxWrites = Math.max(maxWrites, fake.writes.length);
  }
  assert.deepEqual(await store.load(key), state); assert.ok(maxBytes < 40000);
  console.log(`peak incremental transaction: ${maxBytes} UTF-8 bytes, ${maxWrites} changed records`);
  store.close();
});
