import test from 'node:test';
import assert from 'node:assert/strict';
import { LIVE_ORACLE, VOLTY_TICK_IDENTITY, admitLiveProbe, liveIdentity, liveProbabilities, transitionLive } from '../src/1000x/oracle-live-model.js';

const identity = { market: 'BTC', source: 'test:btc:feed-a' };
const quote = (t, price = 100) => ({ price, exchangeMs: t, receivedMs: t });
const step = (state, t, price = 100, extra = {}) => transitionLive(state, { identity, quote: quote(t, price), nowMs: t, ...extra });
function warm() { let s = null; for (let t = 0; t <= 30000; t += 1000) s = step(s, t).state; return s; }

test('causal warmup issues independent six-horizon frozen probes with uniform cold start', () => {
  const s = warm(); assert.deepEqual(s.pending.map(p => p.horizon), LIVE_ORACLE.horizons);
  assert.equal(new Set(s.pending.map(p => p.id)).size, 6);
  assert.ok(s.pending.every(p => p.targetMs === 30000 + p.horizon * 1000 && p.p.every(v => v === 1 / 3)));
  assert.equal(step(s, 31000, 101).state.pending[0].reference, 100);
  assert.deepEqual(step(s, 31000, 101).state.pending[0].x, s.pending[0].x);
  let next = s; for (let t = 31000; t < 35000; t += 1000) next = step(next, t, 101).state;
  assert.equal(step(next, 35000, 101).issued, 6);
  const publicView = step(s, 31000).snapshot; assert.equal(JSON.stringify(publicView).includes('weights'), false);
  assert.equal(publicView.horizons[60].direction, 'FLAT');

  const volty = (state, t, price = 100) => step(state, t, price, { identity: VOLTY_TICK_IDENTITY });
  let ticks = null;
  for (let t = 0; t <= 34000; t += 2000) ticks = volty(ticks, t).state;
  assert.equal(ticks.metrics[60].issued, 3);
  assert.equal(ticks.models[60].n, 0);
  assert.equal(volty(ticks, 34000).changed, false);
  const settled = volty(ticks, 93000, 101).state;
  assert.equal(settled.models[60].n, 2);
  assert.equal(settled.metrics[60].counts[0], 2);
  assert.equal(volty(settled, 93000, 101).state.models[60].n, 2);
});

test('endpoint DOWN differs from FLAT, scoring uses frozen probabilities and labels train once', () => {
  let s = warm(); const first = structuredClone(s.pending[0]);
  s = step(s, 90000, 99).state;
  assert.equal(s.metrics[60].counts[1], 1); assert.equal(s.models[60].n, 1);
  assert.ok(Math.abs(s.metrics[60].candidate.brier - 2 / 3) < 1e-12); assert.deepEqual(s.metrics[60].recent[0].p, first.p);
  assert.equal(step(s, 90000, 99).state.models[60].n, 1);
  let flat = warm(); flat = step(flat, 90000, 100).state;
  assert.equal(flat.metrics[60].counts[2], 1); assert.equal(flat.metrics[60].candidate.hits, 1);
  assert.deepEqual(liveProbabilities(flat.models[60], first.x).length, 3);
});

test('gap resets features but valid endpoint still resolves; late or pre-target observations cannot label', () => {
  let s = warm(); s = step(s, 89999, 98).state;
  assert.equal(s.models[60].n, 0); assert.equal(s.history.length, 1);
  s = step(s, 90000, 98).state; assert.equal(s.models[60].n, 1);
  let late = warm(); late = step(late, 92001, 100).state;
  assert.equal(late.models[60].n, 0); assert.equal(late.metrics[60].expired, 1);
  let boundary = warm(); boundary = step(boundary, 92000, 101).state; assert.equal(boundary.models[60].n, 1);
});

test('old or out-of-order quotes never change history, issue, or train; source partition is bound', () => {
  const s = warm(); const out = step(s, 31000, 99, { quote: { price: 99, exchangeMs: 29000, receivedMs: 31000 } });
  assert.deepEqual(out.state, s);
  assert.throws(() => step(s, 31000, 100, { identity: { market: 'BTC', source: 'other' } }), /invalid_live_oracle_state/);
  assert.notEqual(liveIdentity(identity), liveIdentity({ market: 'BTC', source: 'other' }));
});

test('continuous observations keep pending, history, and accounting bounded', () => {
  let s = warm();
  for (let t = 31000; t <= 1_600_000; t += 1000) s = step(s, t).state;
  assert.ok(s.pending.length <= LIVE_ORACLE.maxPending); assert.ok(s.history.length <= LIVE_ORACLE.maxHistory);
  assert.ok(Object.values(s.metrics).every(m => m.issued === m.resolved + m.expired + s.pending.filter(p => p.horizon === Number(Object.keys(s.metrics).find(k => s.metrics[k] === m))).length));
  assert.ok(Object.values(s.metrics).some(m => m.resolved > 0));
});

test('issuance uses processing cutoff, never backdates a delayed accepted quote', () => {
  const s = warm(), t = 35000; let q = s;
  for (let now = 31000; now < 34000; now += 1000) q = step(q, now).state;
  const result = step(q, t, 101, { quote: quote(34000, 101) });
  assert.equal(result.issued, 6); assert.equal(result.state.pending.at(-1).issuedAtMs, t);
  assert.equal(result.state.pending.at(-1).targetMs, t + 3_600_000);
  let shifted = null; for (let now = 900; now <= 30900; now += 1000) shifted = step(shifted, now).state;
  for (let now = 31900; now <= 34900; now += 1000) shifted = step(shifted, now).state;
  assert.equal(step(shifted, 35000).issued, 0);
});

test('frequency baseline freezes past outcomes and oversized recovered state is rejected', () => {
  let s = warm(); const old = structuredClone(s.pending.find(p => p.horizon === 300));
  s = step(s, 90000, 101).state;
  for (let t = 91000; t <= 120000; t += 1000) s = step(s, t, 101).state;
  const next = step(s, 121000, 101).state;
  assert.deepEqual(next.pending.find(p => p.id === old.id).baseline, [1 / 3, 1 / 3, 1 / 3]);
  assert.deepEqual(next.pending.filter(p => p.horizon === 60).at(-1).baseline, [1, 0, 0]);
  const broken = structuredClone(next); broken.pending = Array(LIVE_ORACLE.maxPending + 1).fill(broken.pending[0]);
  assert.throws(() => step(broken, 122000), /invalid_live_oracle_state/);
});

test('capacity denial increments drops without issuing or resolving', () => {
  const metrics = { capacityDrops: 0, issued: 7, resolved: 3, expired: 1 };
  assert.equal(admitLiveProbe(LIVE_ORACLE.maxPending - 1, metrics), true);
  assert.equal(admitLiveProbe(LIVE_ORACLE.maxPending, metrics), false);
  assert.deepEqual(metrics, { capacityDrops: 1, issued: 7, resolved: 3, expired: 1 });
});

test('fractional source time and bounded provider skew work while missing or corrupt times fail', () => {
  const s = warm();
  assert.equal(step(s, 31000, 100, { quote: { price: 100, exchangeMs: 31125.25, receivedMs: 31000 } }).changed, true);
  assert.equal(step(s, 31000, 100, { quote: { price: 100, exchangeMs: 31251, receivedMs: 31000 } }).changed, false);
  assert.equal(step(s, 31000, 100, { quote: { price: 100, exchangeMs: undefined, receivedMs: 31000 } }).changed, false);
  const broken = structuredClone(s); broken.lastQuote.exchangeMs = NaN;
  assert.throws(() => step(broken, 31000), /invalid_live_oracle_state/);
  assert.throws(() => step(s, 29000), /invalid_live_oracle_state/);
  const scored = step(s, 90000, 99).state; scored.metrics[60].recent = [];
  assert.throws(() => step(scored, 91000), /invalid_live_oracle_state/);
});
