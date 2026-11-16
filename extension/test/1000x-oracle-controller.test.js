import test from 'node:test';
import assert from 'node:assert/strict';
import { OracleController } from '../src/1000x/oracle-controller.js';
import { TIMEFRAMES } from '../src/1000x/feed.js';

const base = 1_800_000_000;
const rows = Array.from({ length: 1400 }, (_, i) => ({ time: base + i * 60, open: 100 + i / 100,
  high: 100.02 + i / 100, low: 99.99 + i / 100, close: 100.01 + i / 100, closed: true }));
const snapshot = nowMs => ({ symbol: 'SOL', sourceIdentity: { symbol: 'SOL', feedId: 6,
  marketAddress: 'Ew8sRjpuBttpmhSUeaAn4dLAegWnz55AuafVcGuojCPS', stream: 'fixed_rate@200ms', kind: 'oracle-ohlc' },
  status: 'live', minuteStatus: 'ready', minuteCandles: rows, quote: { price: 110, exchangeMs: nowMs, receivedMs: nowMs } });
const settle = async () => { for (let i = 0; i < 30; i++) await Promise.resolve(); };

// This fixture tests controller interleaving, not IndexedDB's implementation.
// The real browser gate exercises native transaction serialization separately.
function atomicFixture() {
  const states = new Map(); let queue = Promise.resolve(), reads = 0;
  return { states, get reads() { return reads; }, client: () => ({
    update(key, reduce) {
      const action = queue.then(() => { reads++; const result = reduce(structuredClone(states.get(key) || null));
        if (result.changed) states.set(key, structuredClone(result.state)); return structuredClone(result); });
      queue = action.catch(() => {}); return action;
    }, close() {},
  }) };
}

test('two controller instances reuse the atomically stored same-cutoff forecast and resolve it once', async () => {
  const db = atomicFixture(), views = [[], []]; let now = (base + 1000 * 60) * 1000 + 2000;
  const controllers = views.map(on => new OracleController({ store: db.client(), clock: () => now, onChange: view => on.push(view) }));
  for (const c of controllers) c.observe(snapshot(now)); await settle();
  assert.equal(db.states.size, 6); for (const stored of db.states.values()) assert.equal(stored.issued, 1);
  for (const t of TIMEFRAMES) assert.deepEqual(views[0].at(-1).horizons[t.seconds].state.pending[0], views[1].at(-1).horizons[t.seconds].state.pending[0]);
  now += 600_000;
  for (const c of controllers) c.observe(snapshot(now)); await settle();
  for (const state of db.states.values()) {
    // Shorter targets arrived after their90s grace, so those labels are unknown.
    const horizon = JSON.parse(state.key)[4], n = horizon === 600 ? 1 : 0;
    assert.equal(state.model.n, n); assert.equal(state.totals.n, n);
    assert.equal(state.expired, horizon < 600 ? 1 : 0);
  }
  controllers.forEach(c => c.stop());
});

test('reload restores the prior partition and immutable probabilities instead of a new learner', async () => {
  const db = atomicFixture(), views = []; let now = (base + 1000 * 60) * 1000 + 2000;
  let c = new OracleController({ store: db.client(), clock: () => now, onChange: view => views.push(view) });
  c.observe(snapshot(now)); await settle(); const first = structuredClone(views.at(-1).state.pending[0]); c.stop();
  c = new OracleController({ store: db.client(), clock: () => now, onChange: view => views.push(view) });
  c.observe(snapshot(now)); await settle(); assert.equal(views.at(-1).state.issued, 1);
  assert.deepEqual(views.at(-1).state.pending[0], first); c.stop();
});

test('rapid quote callbacks are coalesced and cannot issue multiple forecasts in one minute', async () => {
  const db = atomicFixture(); let now = (base + 1000 * 60) * 1000 + 2000;
  const c = new OracleController({ store: db.client(), clock: () => now });
  for (let i = 0; i < 20; i++) c.observe(snapshot(now)); await settle();
  assert.equal(db.reads, 6); for (const state of db.states.values()) assert.equal(state.issued, 1);
  now += 1000; c.observe(snapshot(now)); await settle();
  assert.equal(db.reads, 12); for (const state of db.states.values()) assert.equal(state.issued, 1); c.stop();
});

test('normal connecting snapshots wait for catalog identity without a false source error or long retry delay', async () => {
  const db = atomicFixture(), views = []; let now = (base + 1000 * 60) * 1000 + 2000;
  const c = new OracleController({ store: db.client(), clock: () => now, onChange: view => views.push(view) });
  c.observe({ ...snapshot(now), status: 'connecting', sourceIdentity: null }); await settle();
  assert.equal(db.reads, 0); assert.equal(views.at(-1).error, undefined);
  assert.equal(views.at(-1).reason, 'awaiting_catalog_identity');
  now += 1000; c.observe(snapshot(now)); await settle();
  assert.equal(db.reads, 6); assert.equal(views.at(-1).inputReady, true); assert.equal(views.at(-1).state.model.n, 0);
  c.stop();
});

test('suspend or stop fences a pending storage callback from issuing a forecast or repainting an old session', async () => {
  for (const method of ['suspend', 'stop']) {
    let release, writes = 0; const views = [], now = (base + 1000 * 60) * 1000 + 2000;
    const store = { update: (key, reduce) => new Promise((resolve, reject) => { release = () => {
      try { const result = reduce(null); if (result.changed) writes++; resolve(result); } catch (error) { reject(error); }
    }; }), close() {} };
    const c = new OracleController({ store, clock: () => now, onChange: view => views.push(view) });
    c.observe(snapshot(now)); c[method](); const before = views.length; release(); await settle();
    assert.equal(writes, 0); assert.equal(views.length, before);
  }
});

test('missing source and a failed storage transaction visibly abstain without fabricated samples or a reset', async () => {
  const now = (base + 1000 * 60) * 1000 + 2000, views = [];
  let reads = 0;
  const c = new OracleController({ clock: () => now, store: { update: async () => { reads++; throw new Error('disk'); }, close() {} }, onChange: view => views.push(view) });
  c.observe({ ...snapshot(now), sourceIdentity: null }); await settle();
  assert.equal(reads, 0); assert.equal(views.at(-1).error, 'oracle_source_unavailable'); assert.equal(views.at(-1).state, undefined); c.stop();
  const broken = new OracleController({ clock: () => now, store: { update: async () => { throw new Error('invalid_oracle_state'); }, close() {} }, onChange: view => views.push(view) });
  broken.observe(snapshot(now)); await settle(); assert.equal(views.at(-1).error, 'invalid_oracle_state');
  assert.equal(views.at(-1).state, undefined); broken.stop();
});

test('a trained source never leaks predictions through unknown identity or a delayed failing catalog rebind', async () => {
  const db = atomicFixture(), views = [], client = db.client();
  let now = (base + 1000 * 60) * 1000 + 2000, oldKey; const rejectLoads = [];
  const store = { update: (key, reduce) => oldKey && JSON.parse(key)[6] !== JSON.parse(oldKey)[6] ? new Promise((resolve, reject) => { rejectLoads.push(reject); }) : client.update(key, reduce), close() {} };
  const c = new OracleController({ store, clock: () => now, onChange: view => views.push(view) });
  for (let minute = 1000; minute <= 1030; minute++) { now = (base + minute * 60) * 1000 + 2000; c.observe(snapshot(now)); await settle(); }
  assert.equal(views.at(-1).state.model.n, 21); oldKey = views.at(-1).state.key;
  now += 1000; c.observe({ ...snapshot(now), status: 'connecting', sourceIdentity: null }); await settle();
  assert.equal(views.at(-1).state, undefined, 'unknown catalog identity must clear a trained old state');
  assert.equal(views.at(-1).metrics, undefined);
  now += 1000; c.observe(snapshot(now)); await settle(); assert.equal(views.at(-1).state.model.n, 21);
  now += 1000;
  c.observe({ ...snapshot(now), sourceIdentity: { ...snapshot(now).sourceIdentity, feedId: 66 } }); await settle();
  assert.equal(rejectLoads.length, 6);
  assert.equal(views.at(-1).state, undefined, 'pending rebind must not render the previous source');
  assert.equal(views.at(-1).metrics, undefined);
  rejectLoads.forEach(reject => reject(new Error('fixture storage failure'))); await settle();
  assert.equal(views.at(-1).state, undefined, 'failed rebind must not restore the previous source');
  assert.equal(views.at(-1).metrics, undefined); assert.equal(views.at(-1).inputReady, false);
  assert.equal(db.states.get(oldKey).model.n, 21, 'display invalidation must preserve persisted evidence'); c.stop();
});

test('suspending an already trained invalid session clears its visible state and fresh recovery reloads evidence', async () => {
  const db = atomicFixture(), views = []; let now;
  const c = new OracleController({ store: db.client(), clock: () => now, onChange: view => views.push(view) });
  for (let minute = 1000; minute <= 1030; minute++) { now = (base + minute * 60) * 1000 + 2000; c.observe(snapshot(now)); await settle(); }
  const trained = structuredClone(views.at(-1).state); assert.equal(trained.model.n, 21);
  c.suspend();
  assert.equal(views.at(-1).state, undefined, 'invalidated analytics cannot retain an active prediction');
  assert.equal(views.at(-1).metrics, undefined); assert.equal(views.at(-1).inputReady, false);
  now += 1000; c.observe(snapshot(now)); await settle();
  assert.equal(views.at(-1).state.model.n, 21); assert.deepEqual(views.at(-1).state.pending, trained.pending);
  c.stop();
});

test('all six models learn while deselected; chart errors and selecting detail cannot change their ledgers', async () => {
  const db = atomicFixture(), views = []; let now;
  const c = new OracleController({ store: db.client(), clock: () => now, onChange: view => views.push(view) });
  for (let minute = 1000; minute <= 1081; minute++) {
    now = (base + minute * 60) * 1000 + 2000;
    c.observe({ ...snapshot(now), intervalSec: 600, status: minute % 2 ? 'error' : 'backfilling', streamStatus: 'live' }); await settle();
  }
  assert.equal(db.states.size, 6);
  for (const t of TIMEFRAMES) {
    const view = views.at(-1).horizons[t.seconds];
    assert.equal(view.state.model.n, 82 - t.seconds / 60);
    assert.equal(view.state.issued, 82); assert.equal(view.state.pending.length, t.seconds / 60);
    assert.equal(view.inputReady, true); assert.equal(view.state.historicalTrainingSamples, 0);
  }
  const before = structuredClone([...db.states.entries()]), reads = db.reads;
  c.selectHorizon(3600); assert.equal(views.at(-1).horizon, 3600); assert.equal(views.at(-1).state.model.n, 22);
  c.selectHorizon(60); assert.equal(views.at(-1).horizon, 60); assert.equal(views.at(-1).state.model.n, 81);
  assert.equal(db.reads, reads); assert.deepEqual([...db.states.entries()], before); c.stop();
});

test('one horizon capacity failure stays isolated while healthy models keep collecting genuine feedback', async () => {
  const db = atomicFixture(), client = db.client(), views = []; let now, blocked = true;
  const c = new OracleController({ clock: () => now, onChange: v => views.push(v), store: {
    update(key, reduce) { return blocked && JSON.parse(key)[4] === 3600 ? Promise.reject(new Error('oracle_partition_capacity')) : client.update(key, reduce); }, close() {},
  } });
  for (let minute = 1000; minute <= 1030; minute++) {
    now = (base + minute * 60) * 1000 + 2000; c.observe(snapshot(now)); await settle();
  }
  const view = views.at(-1);
  assert.equal(view.horizons[3600].error, 'oracle_partition_capacity'); assert.equal(view.horizons[3600].state, undefined);
  assert.equal(view.horizons[60].state.model.n, 30); assert.equal(view.horizons[600].state.model.n, 21);
  assert.equal(view.horizons[60].mode, 'active'); assert.equal(view.horizons[1200].mode, 'baseline-warmup');
  assert.equal(view.horizons[600].inputReady, true);
  blocked = false; now += 60_000; c.observe(snapshot(now)); await settle();
  assert.equal(views.at(-1).horizons[3600].state.model.n, 0);
  assert.equal(views.at(-1).horizons[3600].state.issued, 1, 'capacity recovery must not backfill forecasts');
  assert.equal(views.at(-1).horizons[600].state.model.n, 22); c.stop();
});

test('a stale snapshot arriving before reducers execute forbids issuance and learning across all six', async () => {
  const db = atomicFixture(), client = db.client(), views = [], release = []; let now = (base + 1000 * 60) * 1000 + 2000;
  const c = new OracleController({ clock: () => now, onChange: v => views.push(v), store: {
    update: (key, reduce) => new Promise((resolve, reject) => release.push(() => client.update(key, reduce).then(resolve, reject))), close() {},
  } });
  c.observe(snapshot(now)); assert.equal(release.length, 6);
  c.observe({ ...snapshot(now), status: 'stale' }); release.forEach(run => run()); await settle();
  assert.equal(db.states.size, 6);
  for (const state of db.states.values()) { assert.equal(state.issued, 0); assert.equal(state.model.n, 0); }
  for (const view of Object.values(views.at(-1).horizons)) assert.equal(view.inputReady, false);
  c.stop();
});
