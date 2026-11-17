import test from 'node:test';
import assert from 'node:assert/strict';
import { OracleDiskBackup, MirroredOracleStore } from '../src/1000x/oracle-disk.js';
import { nextCheckpoint, checkpointText } from '../src/1000x/oracle-checkpoint.js';
import { LiveOracleController } from '../src/1000x/oracle-live-controller.js';
import { transitionLive } from '../src/1000x/oracle-live-model.js';
import { oracleIdentity } from '../src/1000x/oracle-model.js';

const namespace = '11111111-1111-4111-8111-111111111111';
const lineage = '22222222-2222-4222-8222-222222222222';
const origin = 1800000000000;
const input = t => ({ symbol: 'SOL', sourceIdentity: { symbol: 'SOL', feedId: 6,
  marketAddress: 'Ew8sRjpuBttpmhSUeaAn4dLAegWnz55AuafVcGuojCPS', stream: 'fixed_rate@200ms', kind: 'oracle-ohlc' },
  quote: { price: 100 + (t - origin) / 100000, exchangeMs: t, receivedMs: t } });
const identity = oracleIdentity(input(origin));
function trained() {
  let state = null;
  for (let second = 0; second <= 100; second++) {
    const nowMs = origin + second * 1000;
    state = transitionLive(state, { identity, quote: input(nowMs).quote, nowMs }).state;
  }
  return state;
}
const state = trained(), key = state.key;
const sha = async text => [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text)))].map(v => v.toString(16).padStart(2, '0')).join('');
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise(resolve => setImmediate(resolve)); };
const waitFor = async ready => {
  const deadline = Date.now() + 3000;
  while (!ready()) {
    assert(Date.now() < deadline, 'expected asynchronous checkpoint milestone before deadline');
    await new Promise(resolve => setTimeout(resolve, 5));
  }
};
function timers() {
  const pending = new Map(); let sequence = 0;
  return { pending, schedule: (fn, ms) => { const id = ++sequence; pending.set(id, { fn, ms }); return id; }, cancel: id => pending.delete(id) };
}
// A serialized store tests orchestration and race consequences. Native browser
// transactions and disk transport have separate real-browser acceptance.
function localStore(initial = null) {
  let record = structuredClone(initial), tail = Promise.resolve(), closed = false;
  const run = operation => { const p = tail.then(() => { if (closed) throw new Error('closed'); return operation(); }); tail = p.catch(() => {}); return p; };
  return { get record() { return structuredClone(record); },
    loadCheckpoint: () => run(() => structuredClone(record)), load: () => run(() => structuredClone(record?.state ?? null)),
    update: (_key, reduce, { backupBase, deferLegacy } = {}) => run(() => { const result = reduce(structuredClone(record?.state ?? null));
      const legacy = record && !record.lineage;
      const metadata = legacy && deferLegacy ? null : result.changed || !record?.lineage
        ? nextCheckpoint(legacy && backupBase ? backupBase : record) : { lineage: record.lineage, revision: record.revision };
      if (result.changed || !record?.lineage) record = { state: structuredClone(result.state), ...metadata };
      return { ...result, checkpoint: metadata }; }),
    restoreIfAbsent: (_key, saved) => run(() => { if (!record) record = structuredClone(saved); return structuredClone(record); }),
    seed: saved => { record = structuredClone(saved); }, cancelPending() {}, close: () => { closed = true; },
  };
}
async function remote(checkpoint = { state, lineage, revision: 101 }) {
  checkpoint = structuredClone(checkpoint);
  let saved = checkpoint ? { ...checkpoint, text: JSON.stringify(checkpoint.state), digest: await sha(JSON.stringify(checkpoint.state)) } : null;
  const calls = [];
  return { calls, get saved() { return saved; }, call: async (command, params) => {
    calls.push({ command, params }); assert.equal(params.namespace, namespace); assert.equal(params.key, key); assert.equal(params.kind, 'live');
    if (command === 'oracle.learning.load') {
      if (!saved) return { found: false };
      if (params.digest && params.digest !== saved.digest) throw new Error('learning_checkpoint_changed_during_read');
      const size = Math.ceil(saved.text.length / 2), offset = params.offset || 0;
      return { found: true, lineage: saved.lineage, revision: saved.revision, digest: saved.digest,
        length: saved.text.length, text: saved.text.slice(offset, offset + size), offset, saved_at: origin / 1000 };
    }
    assert.equal(command, 'oracle.learning.save');
    const next = params.checkpoint;
    if (saved && saved.lineage !== next.lineage) throw new Error('learning_checkpoint_lineage_conflict');
    const nextDigest = await sha(next.text);
    if (saved?.revision === next.revision && saved.digest !== nextDigest) throw new Error('learning_checkpoint_revision_conflict');
    if (saved && saved.revision > next.revision) return { saved: saved.digest === nextDigest, status: 'disk_newer', revision: saved.revision, digest: saved.digest };
    saved = { ...next, state: JSON.parse(next.text), digest: await sha(next.text) };
    return { saved: true, revision: next.revision, digest: saved.digest };
  } };
}

test('full six-horizon SOL checkpoint restores from pinned chunks into an absent local partition', async () => {
  const rpc = await remote(), local = localStore(), events = [], clock = timers();
  const disk = new OracleDiskBackup({ call: rpc.call, profile: async () => namespace, onChange: e => events.push(e), ...clock });
  const store = new MirroredOracleStore(local, disk, 'live');
  assert.deepEqual(await store.load(key), state);
  assert.equal(local.record.lineage, lineage); assert.equal(local.record.revision, 101);
  assert.equal(local.record.state.models[60].n, 3); assert.equal(local.record.state.models[600].n, 0);
  assert(rpc.calls.length >= 2); assert(rpc.calls.every(c => c.command === 'oracle.learning.load'));
  assert.equal(events.at(-1).status, 'verified'); store.close(); disk.close(); assert.equal(clock.pending.size, 0);
});

test('existing browser data is authoritative and never overwritten by a disk restore', async () => {
  const rpc = await remote(), local = localStore({ state, lineage, revision: 102 }), clock = timers();
  const disk = new OracleDiskBackup({ call: rpc.call, profile: async () => namespace, ...clock });
  const store = new MirroredOracleStore(local, disk, 'live');
  assert.deepEqual(await store.load(key), state); await waitFor(() => rpc.saved?.revision === 102);
  assert(!rpc.calls.some(c => c.command === 'oracle.learning.load'));
  assert.equal(local.record.revision, 102); assert.equal(rpc.saved.revision, 102);
  store.close(); disk.close();
});

test('digest corruption and invalid model state refuse recovery without creating an empty local model', async () => {
  for (const bad of ['digest', 'model']) {
    const rpc = await remote(), local = localStore(), clock = timers();
    if (bad === 'model') { rpc.saved.state.models[60].weights = [['invalid']]; rpc.saved.text = JSON.stringify(rpc.saved.state); rpc.saved.digest = await sha(rpc.saved.text); }
    const disk = new OracleDiskBackup({ call: async (...args) => {
      const response = await rpc.call(...args); return bad === 'digest' && args[1].offset ? { ...response, digest: 'f'.repeat(64) } : response;
    }, profile: async () => namespace, ...clock });
    const store = new MirroredOracleStore(local, disk, 'live');
    await assert.rejects(store.load(key), /oracle_backup_(invalid|digest)/);
    assert.equal(local.record, null); assert(!rpc.calls.some(c => c.command === 'oracle.learning.save'));
    store.close(); disk.close();
  }
});

test('a chunk revision race is refused and preserves the disk and local histories', async () => {
  const rpc = await remote(), local = localStore(), clock = timers();
  const disk = new OracleDiskBackup({ call: async (command, params) => {
    if (params.offset) throw new Error('learning_checkpoint_changed_during_read'); return rpc.call(command, params);
  }, profile: async () => namespace, ...clock });
  const store = new MirroredOracleStore(local, disk, 'live');
  await assert.rejects(store.load(key), /changed_during_read/);
  assert.equal(local.record, null); assert.equal(rpc.saved.revision, 101); store.close(); disk.close();
});

test('concurrent local restoration wins atomically; a different lineage never overwrites the disk copy', async () => {
  const rpc = await remote(), local = localStore(), events = [], clock = timers();
  const other = { state, lineage: '33333333-3333-4333-8333-333333333333', revision: 1 };
  const restore = local.restoreIfAbsent;
  local.restoreIfAbsent = (...args) => { local.seed(other); return restore(...args); };
  const disk = new OracleDiskBackup({ call: rpc.call, profile: async () => namespace, onChange: e => events.push(e), ...clock });
  const store = new MirroredOracleStore(local, disk, 'live');
  await store.load(key); await store.update(key, old => ({ state: old, changed: false }));
  await waitFor(() => events.at(-1)?.status === 'conflict');
  assert.equal(local.record.lineage, other.lineage); assert.equal(rpc.saved.lineage, lineage);
  assert.equal(events.at(-1).status, 'conflict'); store.close(); disk.close();
});

test('stalled native writes do not block learning, queue only the newest state, and close retires timers', async () => {
  const local = localStore({ state, lineage, revision: 101 }), clock = timers(), events = []; let calls = 0;
  const disk = new OracleDiskBackup({ call: () => { calls++; return new Promise(() => {}); }, profile: async () => namespace,
    onChange: e => events.push(e), ...clock });
  const store = new MirroredOracleStore(local, disk, 'live');
  for (let second = 101; second <= 105; second++) {
    const nowMs = origin + second * 1000;
    await store.update(key, old => transitionLive(old, { identity, quote: input(nowMs).quote, nowMs }));
  }
  await settle(); assert.equal(calls, 1); assert.equal(local.record.revision, 106);
  assert.equal(local.record.state.lastQuote.receivedMs, origin + 105000);
  assert.equal([...clock.pending.values()].filter(v => v.ms === 2000).length, 1);
  for (const timer of [...clock.pending.values()]) if (timer.ms === 2000) timer.fn();
  await settle(); assert(events.some(e => e.status === 'unavailable'));
  store.close(); disk.close(); assert.equal(clock.pending.size, 0);
});

test('an acknowledged unchanged checkpoint does not cause repeated disk writes', async () => {
  const rpc = await remote(null), clock = timers(), events = [];
  const disk = new OracleDiskBackup({ call: rpc.call, profile: async () => namespace, onChange: event => events.push(event), ...clock });
  const checkpoint = { state, lineage, revision: 101 };
  disk.queue('live', key, checkpoint); await waitFor(() => events.at(-1)?.status === 'saved');
  disk.queue('live', key, checkpoint); await settle();
  assert.equal(rpc.calls.length, 1); disk.close(); assert.equal(clock.pending.size, 0);
});

test('a recovered helper restores saved SOL during an ongoing stale feed without a page reload', async () => {
  const rpc = await remote(), local = localStore(), clock = timers(), views = []; let available = false, now = origin + 103000;
  const disk = new OracleDiskBackup({ call: (...args) => { if (!available) throw new Error('helper absent'); return rpc.call(...args); },
    profile: async () => namespace, ...clock });
  const store = new MirroredOracleStore(local, disk, 'live');
  const load = store.load.bind(store); let loadsCompleted = 0;
  store.load = async (...args) => { try { return await load(...args); } finally { loadsCompleted++; } };
  const controller = new LiveOracleController({ store, clock: () => now, onChange: view => views.push(view), call: async () => { throw new Error('stale data cannot publish'); } });
  const stale = { ...input(origin + 100000), streamStatus: 'live', minuteStatus: 'loading', minuteCandles: [] };
  controller.observe(stale); await waitFor(() => loadsCompleted === 1); await settle();
  assert.equal(local.record, null); assert.equal(views.at(-1).local, null);
  available = true; now += 5000; controller.observe(stale); await waitFor(() => views.at(-1)?.local !== null);
  assert.equal(views.at(-1).status, 'stale'); assert.equal(views.at(-1).local.horizons[60].samples, 3);
  assert.equal(views.at(-1).local.horizons[60].scores, null); controller.stop(); disk.close();
});

test('valid legacy browser data gets checkpoint metadata and a disk copy without another quote or label', async () => {
  const rpc = await remote(null), local = localStore({ state }), clock = timers();
  const disk = new OracleDiskBackup({ call: rpc.call, profile: async () => namespace, ...clock });
  const store = new MirroredOracleStore(local, disk, 'live');
  assert.deepEqual(await store.load(key), state); await waitFor(() => rpc.saved?.revision === 1);
  assert.equal(local.record.revision, 1); assert(local.record.lineage);
  assert.deepEqual(rpc.saved.state, state); assert.equal(rpc.saved.revision, 1);
  store.close(); disk.close();
});

test('a Live learner with missing browser metadata keeps learning offline and rejoins its verified disk checkpoint', async () => {
  const rpc = await remote(), local = localStore({ state }), clock = timers(), events = [];
  let now = origin + 101000, available = false, rejectedReads = 0;
  const disk = new OracleDiskBackup({ call: async (...args) => {
    if (!available) { rejectedReads++; throw new Error('helper unavailable'); }
    return rpc.call(...args);
  }, profile: async () => namespace, clock: () => now, onChange: event => events.push(event), ...clock });
  const store = new MirroredOracleStore(local, disk, 'live', { clock: () => now });
  const observe = previous => transitionLive(previous, { identity, quote: input(now).quote, nowMs: now });
  await store.update(key, observe);
  now += 1000;
  const advanced = await store.update(key, observe);
  assert.equal(rejectedReads, 1, 'unavailable disk is retried on a bounded schedule');
  assert.equal(local.record.lineage, undefined);
  assert(advanced.state.revision > state.revision);
  assert.equal(rpc.saved.revision, 101);
  available = true;
  now += 5000;
  assert.deepEqual(await store.load(key), advanced.state, 'the newer local model stays authoritative');
  await waitFor(() => events.at(-1)?.status === 'saved');
  assert.equal(local.record.lineage, lineage);
  assert.equal(local.record.revision, 102);
  assert.equal(rpc.saved.lineage, lineage);
  assert.equal(rpc.saved.revision, 102);
  assert.deepEqual(rpc.saved.state, advanced.state);
  store.close(); disk.close();
});

test('quota failure during optional legacy metadata capture preserves readable historical counts', async () => {
  const rpc = await remote(null), local = localStore({ state }), clock = timers(), events = [];
  local.update = async () => { throw new DOMException('fixture quota', 'QuotaExceededError'); };
  const disk = new OracleDiskBackup({ call: rpc.call, profile: async () => namespace, onChange: e => events.push(e), ...clock });
  const store = new MirroredOracleStore(local, disk, 'live');
  assert.deepEqual(await store.load(key), state); assert.equal(local.record.state.models[60].n, 3);
  assert.equal(events.at(-1).status, 'unavailable');
  assert.deepEqual(rpc.calls.map(x => x.command), ['oracle.learning.load']); store.close(); disk.close();
});

test('logical timeout keeps the physical save fenced across different queued partitions', async () => {
  const clock = timers(), calls = [], replies = [];
  const disk = new OracleDiskBackup({ profile: async () => namespace, ...clock,
    call: (_command, params) => { calls.push(params); return new Promise(resolve => replies.push(resolve)); } });
  disk.queue('live', key, { state, lineage, revision: 101 }); await waitFor(() => calls.length === 1);
  for (const timer of [...clock.pending.values()]) if (timer.ms === 2000) timer.fn(); await settle();
  const other = transitionLive(null, { identity: { market: 'BTC', source: identity.source }, quote: input(origin).quote, nowMs: origin }).state;
  disk.queue('live', other.key, { state: other, lineage, revision: 1 }, true); disk.flush(); await settle();
  assert.equal(calls.length, 1, 'a logical deadline cannot retire an unresolved physical native write');
  replies[0]({ saved: true, revision: 101, digest: await sha(calls[0].checkpoint.text) }); await waitFor(() => calls.length >= 2);
  assert.equal(calls.length, 2);
  replies[1]({ saved: true, revision: calls[1].checkpoint.revision, digest: await sha(calls[1].checkpoint.text) }); await settle();
  if (calls[1].key !== other.key) {
    await waitFor(() => calls.length >= 3); assert.equal(calls.length, 3); assert.equal(calls[2].key, other.key);
    replies[2]({ saved: true, revision: 1, digest: await sha(calls[2].checkpoint.text) }); await settle();
  }
  disk.close(); assert.equal(clock.pending.size, 0);
});

test('another tab newer disk revision retires obsolete queued states without retrying', async () => {
  const clock = timers(), events = []; let calls = 0, now = 0;
  const disk = new OracleDiskBackup({ profile: async () => namespace, clock: () => now, ...clock,
    onChange: e => events.push(e), call: async () => { calls++; return { saved: false, revision: 102, digest: 'a'.repeat(64), status: 'disk_newer' }; } });
  disk.queue('live', key, { state, lineage, revision: 101 }); await waitFor(() => events.at(-1)?.status === 'disk-newer');
  now += 31000; disk.queue('live', key, { state, lineage, revision: 101 }); disk.flush(); await settle();
  assert.equal(calls, 1); assert.equal(events.at(-1).status, 'disk-newer'); assert.equal(clock.pending.size, 0); disk.close();
});

test('reconstructed property order produces identical protocol bytes and no same-revision conflict', async () => {
  const rebuilt = { ...state }; delete rebuilt.metrics; delete rebuilt.pending;
  rebuilt.metrics = state.metrics; rebuilt.pending = state.pending;
  assert.notEqual(JSON.stringify(rebuilt), JSON.stringify(state)); assert.equal(checkpointText(rebuilt), checkpointText(state));
  const rpc = await remote(null), events = [];
  for (const saved of [state, rebuilt]) {
    const acknowledged = events.filter(event => event.status === 'saved').length;
    const clock = timers(), disk = new OracleDiskBackup({ call: rpc.call, profile: async () => namespace, onChange: e => events.push(e), ...clock });
    disk.queue('live', key, { state: saved, lineage, revision: 101 });
    await waitFor(() => events.filter(event => event.status === 'saved').length === acknowledged + 1); disk.close();
  }
  assert.equal(rpc.calls.length, 2); assert.equal(events.filter(e => e.status === 'saved').length, 2);
  assert(!events.some(e => e.status === 'conflict'));
});
