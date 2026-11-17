import test from 'node:test';
import assert from 'node:assert/strict';
import { LiveOracleController, liveInput } from '../src/1000x/oracle-live-controller.js';

const origin = 1_800_000_000_000;
const markets = {
  BTC: [1, 'BXQQo2VTJV2upjdA6qFMGBY3uMyTMnRmaZjPCB5ZVmr7'],
  ZEC: [66, '4ohWGDrmqdiEHinL5Kf2BYzM9UVSe3RJ1bzoveHehiwj'],
};
function input(now, symbol = 'BTC') {
  const [feedId, marketAddress] = markets[symbol];
  return { symbol, sourceIdentity: { symbol, feedId, marketAddress,
    stream: 'fixed_rate@200ms', kind: 'oracle-ohlc' }, streamStatus: 'live',
  minuteStatus: 'loading', minuteCandles: [],
  quote: { price: 100 + (now - origin) / 100_000, exchangeMs: now, receivedMs: now } };
}
const settle = async () => { for (let i = 0; i < 80; i++) await Promise.resolve(); };
function fixture() {
  const states = new Map(); let reads = 0, queue = Promise.resolve();
  return { states, get reads() { return reads; },
    update(key, reduce) {
      const task = queue.then(() => { reads++; const result = reduce(structuredClone(states.get(key) || null));
        if (result.changed) states.set(key, structuredClone(result.state)); return result; });
      queue = task.catch(() => {}); return task;
    }, close() {}, cancelPending() {},
  };
}

test('live scores and all horizons need fresh quotes rather than completed minute history', async () => {
  const store = fixture(), views = [], packets = []; let now = origin;
  const c = new LiveOracleController({ store, clock: () => now, id: () => 'producer',
    onChange: view => views.push(view), call: async (command, params) => {
      if (command === 'oracle.signals.invalidate') return {};
      assert.equal(command, 'oracle.signals.publish'); packets.push(params.packet); return { asset: null };
    } });
  for (let second = 0; second <= 31; second++) { now = origin + second * 1000; c.observe(input(now)); await settle(); }
  const view = views.at(-1);
  assert.equal(view.status, 'ready'); assert.equal(view.asset, 'BTC');
  for (const h of [60, 300, 600, 900, 1200, 3600]) {
    assert.deepEqual(view.local.horizons[h].scores, { up: 1 / 3, down: 1 / 3, flat: 1 / 3 });
    assert.equal(view.local.horizons[h].samples, 0);
  }
  assert(packets.length > 0); assert(!JSON.stringify(packets).includes('weights'));
  assert(!JSON.stringify(packets).includes('"pending":['));
  assert.equal(store.states.size, 1); c.stop();
});

test('a stalled native relay neither queues unbounded sends nor blocks one-second learning observations', async () => {
  const store = fixture(), views = []; let now = origin, release, calls = 0;
  const c = new LiveOracleController({ store, clock: () => now, id: () => 'producer',
    onChange: view => views.push(view), call: command => { if (command === 'oracle.signals.invalidate') return Promise.resolve({});
      calls++; return new Promise(resolve => { release = resolve; }); } });
  c.observe(input(now)); await settle();
  for (let second = 1; second <= 4; second++) { now = origin + second * 1000; c.observe(input(now)); await settle(); }
  assert.equal(calls, 1); assert.equal(store.reads, 5);
  assert.equal(views.at(-1).local.asOfMs, now); assert.equal(views.at(-1).status, 'ready');
  const before = views.length; c.stop(); release({ asset: null }); await settle();
  assert.equal(calls, 1); assert.equal(views.length, before);
});

test('invalidating the source fences a slow transaction before persistence and publication', async () => {
  const views = []; let release, writes = 0, calls = 0;
  const store = { update: (key, reduce) => new Promise((resolve, reject) => { release = () => {
    try { const result = reduce(null); writes++; resolve(result); } catch (e) { reject(e); }
  }; }), close() {}, cancelPending() {} };
  const c = new LiveOracleController({ store, clock: () => origin, id: () => 'producer',
    onChange: view => views.push(view), call: async () => { calls++; return {}; } });
  c.observe(input(origin)); c.observe({ ...input(origin), sourceIdentity: null });
  release(); await settle();
  assert.equal(writes, 0); assert.equal(calls, 0);
  assert.equal(views.at(-1).status, 'source_changed'); assert.equal(views.at(-1).local, null); c.stop();
});

test('same-source staleness cannot retain a live shared window or serve a late relay response', async () => {
  const store = fixture(), views = []; let now = origin, release;
  const c = new LiveOracleController({ store, clock: () => now, id: () => 'producer',
    onChange: view => views.push(view), call: command => command === 'oracle.signals.invalidate'
      ? Promise.resolve({}) : new Promise(resolve => { release = resolve; }) });
  c.observe(input(now)); await settle();
  now += 3000; c.observe(input(origin));
  release({ asset: { fresh: true, horizons: { 60: { window: { side: 'UP' } } } } }); await settle();
  assert.equal(views.at(-1).status, 'stale'); assert.equal(views.at(-1).shared, null); c.stop();
});

test('local committed information remains visible when the native relay is missing', async () => {
  const store = fixture(), views = []; let now = origin;
  const c = new LiveOracleController({ store, clock: () => now, id: () => 'producer',
    onChange: view => views.push(view), call: async () => { throw new Error('private transport details'); } });
  c.observe(input(now)); await settle(); now += 1000; c.observe(input(now)); await settle();
  assert.equal(views.at(-1).status, 'ready'); assert.equal(views.at(-1).local.asOfMs, now);
  assert.equal(views.at(-1).error, 'signal_sharing_unavailable');
  assert(!JSON.stringify(views).includes('private transport details')); c.stop();
});

test('sampling throttles bursts, preserves fractional stamps and changes only displayed horizon', async () => {
  const store = fixture(), views = []; let now = origin + 0.5, publishes = 0;
  const snapshot = input(now); snapshot.quote.exchangeMs += 100;
  assert.equal(liveInput(snapshot, now).valid, true);
  const c = new LiveOracleController({ store, clock: () => now, id: () => 'producer',
    onChange: view => views.push(view), call: async command => { if (command === 'oracle.signals.publish') publishes++; return { asset: null }; } });
  // The model clock uses integer epoch milliseconds; quote stamps may be fractional.
  now = Math.ceil(now); snapshot.quote.receivedMs = now - 0.5;
  for (let n = 0; n < 20; n++) c.observe(snapshot);
  await settle(); assert.equal(store.reads, 1);
  now += 1000; c.observe(snapshot); await settle();
  assert.equal(store.reads, 2); assert.equal(publishes, 1);
  c.selectHorizon(3600); assert.equal(views.at(-1).selectedHorizon, 3600);
  assert.equal(store.states.size, 1); c.stop();
});

test('hung publish and status requests expire so a recovered relay receives the latest committed score', async () => {
  const store = fixture(), views = [], timers = new Map(); let timerId = 0, now = origin, healthy = false, late;
  let publishes = 0, statuses = 0;
  const c = new LiveOracleController({ store, clock: () => now, id: () => 'producer',
    schedule: callback => { timers.set(++timerId, callback); return timerId; }, cancelTimer: id => timers.delete(id),
    onChange: view => views.push(view), call: (command, params) => {
      if (command === 'oracle.signals.invalidate') return Promise.resolve({});
      if (command === 'oracle.signals.status') { statuses++; return new Promise(() => {}); }
      publishes++;
      if (!healthy) return new Promise(resolve => { late = resolve; });
      return Promise.resolve({ asset: { source: params.packet.snapshot.source, sequence: params.packet.sequence } });
    } });
  c.observe(input(now)); await settle();
  for (let second = 1; second <= 4; second++) { now = origin + second * 1000; c.observe(input(now)); await settle(); }
  assert.equal(publishes, 1); assert.equal(store.reads, 5);
  for (const callback of [...timers.values()]) callback(); await settle();
  assert.equal(statuses, 1);
  healthy = true; for (const callback of [...timers.values()]) callback(); await settle();
  assert.equal(publishes, 2); assert(views.at(-1).shared.sequence > 1);
  const latest = structuredClone(views.at(-1).shared);
  late({ asset: { source: 'wrong late response', sequence: -1 } }); await settle();
  assert.deepEqual(views.at(-1).shared, latest); c.stop();
});

test('suspension sends a later sequence fence than an already-sent publication', async () => {
  const store = fixture(), calls = []; const c = new LiveOracleController({ store, clock: () => origin,
    id: () => 'producer', call: (command, params) => { calls.push({ command, params });
      return command === 'oracle.signals.publish' ? new Promise(() => {}) : Promise.resolve({}); } });
  c.observe(input(origin)); await settle(); c.suspend('feed_unavailable'); await settle();
  const publication = calls.find(v => v.command === 'oracle.signals.publish').params.packet;
  const revoke = calls.find(v => v.command === 'oracle.signals.invalidate').params.event;
  assert.equal(revoke.publisher_id, publication.publisher_id); assert.equal(revoke.asset, publication.asset);
  assert(revoke.sequence > publication.sequence); assert.equal(revoke.reason, 'feed_unavailable'); c.stop();
});
