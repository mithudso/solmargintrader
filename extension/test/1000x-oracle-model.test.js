import test from 'node:test';
import assert from 'node:assert/strict';
import { ORACLE, FEATURE_NAMES, probability, learn, score, oracleInput, makeFeatures, newOracleState,
  validateOracleState, transitionOracle, oracleMetrics, oracleMode } from '../src/1000x/oracle-model.js';

const base = 1_800_000_000;
const identity = { symbol: 'SOL', feedId: 6, marketAddress: 'Ew8sRjpuBttpmhSUeaAn4dLAegWnz55AuafVcGuojCPS', stream: 'fixed_rate@200ms', kind: 'oracle-ohlc' };
const bars = (count = 1500, slope = 0.01) => Array.from({ length: count }, (_, i) => {
  const open = 100 + i * slope, close = open + slope / 2;
  return { time: base + i * 60, open, high: Math.max(open, close) + 0.01, low: Math.min(open, close) - 0.01, close, closed: true };
});
const at = minute => base + minute * 60;
function input(minute = 1000, rows = bars(), lagMs = 2000, extra = {}) {
  const nowMs = at(minute) * 1000 + lagMs;
  return oracleInput({ symbol: 'SOL', sourceIdentity: identity, status: 'live', minuteStatus: 'ready', minuteCandles: rows,
    quote: { price: 110, exchangeMs: nowMs, receivedMs: nowMs }, ...extra }, nowMs);
}
const near = (a, b, tolerance = 1e-12) => assert.ok(Math.abs(a - b) <= tolerance, `${a} != ${b}`);
const zero = () => ({ weights: FEATURE_NAMES.map(() => 0), bias: 0, n: 0 });

test('sigmoid and L2 gradient match analytical binary logistic values, with an unregularized intercept', () => {
  const x = FEATURE_NAMES.map((_, i) => i === 0 ? 1 : 0), model = zero();
  model.weights[0] = 0.2; model.weights[1] = 0.4; model.bias = -0.1;
  const p = 1 / (1 + Math.exp(-0.1)); near(probability(model, x), p);
  const next = learn(model, x, 1);
  near(next.weights[0], 0.2 - 0.05 * ((p - 1) + 0.001 * 0.2));
  near(next.weights[1], 0.4 - 0.05 * 0.001 * 0.4);
  near(next.bias, -0.1 - 0.05 * (p - 1)); assert.equal(next.n, 1);
  assert.equal(model.n, 0); assert.equal(model.weights[0], 0.2);
});

test('finite bounds and zero/one scoring fail closed on malformed values and never return NaN', () => {
  const model = { weights: FEATURE_NAMES.map(() => 8), bias: 8, n: 2 }, x = FEATURE_NAMES.map(() => 1);
  assert.equal(probability(model, x), 1);
  const next = learn(model, x, 0); assert.ok(next.weights.every(w => Math.abs(w) <= 8));
  for (const p of [0, 0.5, 1]) for (const y of [0, 1]) assert.ok(Object.values(score(p, y)).every(Number.isFinite));
  assert.throws(() => probability(model, [NaN])); assert.throws(() => score(0.5, null));
  assert.throws(() => score(Infinity, 1)); assert.throws(() => learn({ ...model, n: NaN }, x, 1));
});

test('Brier, log loss and binary0.5 tie policy have hand-computed paired values', () => {
  assert.deepEqual(score(0.5, 0), { hit: 1, brier: 0.25, logLoss: Math.log(2) });
  near(score(0.8, 1).brier, 0.04); near(score(0.8, 1).logLoss, -Math.log(0.8));
  assert.equal(score(0.5, 1).hit, 0);
});

test('cold start issues a genuine labeled baseline/shadow forecast and does not learn historical labels', () => {
  const i = input(), result = transitionOracle(null, i), f = result.state.pending[0];
  assert.equal(f.p, 0.5); assert.equal(f.servedP, 0.5); assert.equal(f.mode, 'baseline-warmup');
  assert.equal(f.cutoff, at(1000)); assert.equal(f.target, at(1010)); assert.equal(f.x.length, FEATURE_NAMES.length);
  assert.equal(result.state.model.n, 0); assert.equal(result.state.historicalTrainingSamples, 0);
  assert.equal(oracleMetrics(result.state).cumulative.candidate.accuracy, null);
  assert.equal(result.state.totals.n, 0); assert.ok(result.feedback.issued);
});

test('warmup collects real labels while candidate/shadow, actually-served and fixed-baseline policies stay separate', () => {
  let state;
  for (let minute = 1000; minute <= 1032; minute++) state = transitionOracle(state, input(minute)).state;
  assert.equal(state.model.n, 23); assert.equal(oracleMode(state), 'active');
  const shadow = state.recent.find(f => f.p > 0.5 && f.mode === 'baseline-warmup');
  assert.ok(shadow); assert.equal(shadow.servedP, 0.5); assert.equal(shadow.baselineP, 0.5);
  near(shadow.scores.served.brier, 0.25); assert.notEqual(shadow.scores.candidate.brier, 0.25);
  assert.equal(state.totals.candidate.hits > state.totals.baseline.hits, true);
  assert.equal(state.pending.at(-1).mode, 'active');
});

test('delayed outcomes score issued probabilities but gradients use current weights after an intervening update', () => {
  let state = transitionOracle(null, input(1000)).state;
  state = transitionOracle(state, input(1001)).state;
  const [first, second] = structuredClone(state.pending), starting = structuredClone(state.model);
  state = transitionOracle(state, input(1010)).state;
  const afterFirst = learn(starting, first.x, 1);
  assert.deepEqual(state.model, afterFirst);
  state = transitionOracle(state, input(1011)).state;
  assert.deepEqual(state.model, learn(afterFirst, second.x, 1));
  assert.equal(state.recent[1].p, second.p); near(state.recent[1].scores.candidate.brier, 0.25);
  assert.notEqual(state.model.bias, 0.05, 'stale0.5 gradients would incorrectly produce bias0.05');
});

test('duplicate issue/feedback after reload reuses the stored issued record and never updates twice', () => {
  const issued = transitionOracle(null, input(1000)), original = structuredClone(issued.state.pending[0]);
  const restored = structuredClone(issued.state);
  // A second writer must use the stored forecast for ANY valid current weights,
  // including weights that differ from those at issuance.
  restored.model.bias = 0.4;
  assert.notEqual(probability(restored.model, original.x), original.p);
  const duplicate = transitionOracle(restored, input(1000));
  assert.deepEqual(duplicate.state.pending[0], original); assert.equal(duplicate.changed, false);
  const resolved = transitionOracle(duplicate.state, input(1010));
  const replay = transitionOracle(structuredClone(resolved.state), input(1010));
  assert.deepEqual(replay.state, resolved.state); assert.equal(replay.state.model.n, 1);
  assert.deepEqual(replay.state.recent[0].x, original.x); assert.equal(replay.state.recent[0].p, original.p);
});

test('older pending outcomes survive newer resolution and accept a complete gap fill inside90s', () => {
  let state = transitionOracle(null, input(1000)).state;
  state = transitionOracle(state, input(1001)).state;
  const first = structuredClone(state.pending[0]);
  const missing = bars().filter(row => row.time !== at(1000));
  state = transitionOracle(state, input(1011, missing)).state;
  assert.equal(state.model.n, 1); assert.equal(state.recent[0].cutoff, at(1001));
  assert.ok(state.pending.some(f => f.id === first.id)); assert.equal(state.lastClosedTarget, at(1011));
  const model = structuredClone(state.model);
  const filled = transitionOracle(state, input(1011, bars(), 15_000)).state;
  assert.equal(filled.model.n, 2); assert.equal(filled.recent.at(-1).id, first.id);
  assert.deepEqual(filled.model, learn(model, first.x, 1)); assert.equal(filled.lastClosedTarget, at(1011));
  const alreadyIssued = structuredClone(filled.pending.find(f => f.cutoff === at(1011)));
  const secondWindow = transitionOracle(structuredClone(filled), input(1011, bars(), 15_000)).state;
  assert.deepEqual(secondWindow.pending.find(f => f.id === alreadyIssued.id), alreadyIssued, 'same-cutoff second window must reuse stored probability');
});

test('flat labels are NON-UP and counted explicitly; unknown, gapped and late labels never train', () => {
  let state = transitionOracle(null, input(1000, bars(1500, 0))).state;
  state = transitionOracle(state, input(1010, bars(1500, 0))).state;
  assert.equal(state.recent[0].outcome, 'FLAT'); assert.equal(state.recent[0].y, 0);
  assert.equal(state.totals.flat, 1); assert.equal(state.totals.n, 1); assert.equal(state.totals.baseline.hits, 1);
  const first = transitionOracle(null, input(1000)).state;
  const missing = bars().filter(row => row.time !== at(1005));
  const waiting = transitionOracle(first, input(1010, missing)).state;
  assert.equal(waiting.model.n, 0); assert.equal(waiting.expired, 0);
  const expired = transitionOracle(waiting, input(1012, missing)).state;
  assert.equal(expired.model.n, 0); assert.equal(expired.totals.n, 0); assert.equal(expired.expired, 1);
});

test('features and issued predictions are invariant to future mutation, incomplete current bars and full-history suffixes', () => {
  const all = bars(), cutoff = at(1000), prefix = all.filter(row => row.time < cutoff);
  const mutated = all.map(row => row.time >= cutoff ? { ...row, open: 1, high: 9000, low: 1, close: 8000 } : row);
  assert.deepEqual(makeFeatures(mutated, cutoff), makeFeatures(prefix, cutoff));
  assert.deepEqual(transitionOracle(null, input(1000, mutated)).state.pending, transitionOracle(null, input(1000, prefix)).state.pending);
  assert.equal(makeFeatures(prefix.slice(-77), cutoff), null);
  assert.equal(makeFeatures(prefix.map((row, i) => i === prefix.length - 10 ? { ...row, partial: true } : row), cutoff), null);
});

test('stale/disconnected inputs abstain, late starts do not fabricate old forecasts, and market/source changes isolate state', () => {
  for (const extra of [{ status: 'stale' }, { minuteStatus: 'unavailable' }, { quote: null }]) {
    const result = transitionOracle(null, input(1000, bars(), 2000, extra)); assert.equal(result.state.pending.length, 0);
  }
  assert.equal(transitionOracle(null, input(1000, bars(), 15001)).state.issued, 0);
  const sol = input(), btc = input(1000, bars(), 2000, { symbol: 'BTC', sourceIdentity: { ...identity, symbol: 'BTC', feedId: 1 } });
  assert.notEqual(sol.key, btc.key);
  assert.throws(() => transitionOracle(transitionOracle(null, sol).state, btc), /invalid_oracle_state/);
  const changed = input(1000, bars(), 2000, { sourceIdentity: { ...identity, feedId: 66 } }); assert.notEqual(changed.key, sol.key);
  assert.throws(() => input(1000, bars(), 2000, { sourceIdentity: null }), /source_unavailable/);
});

test('recent ledger stays bounded while cumulative pairing and old duplicate watermarks survive pruning', () => {
  let state;
  for (let minute = 1000; minute <= 1145; minute++) state = transitionOracle(state, input(minute)).state;
  assert.equal(state.recent.length, ORACLE.recent); assert.equal(state.model.n, 136);
  assert.equal(state.totals.n, 136); assert.equal(oracleMetrics(state).cumulative.baseline.n, 136);
  assert.equal(oracleMetrics(state).recent.candidate.n, 128);
  assert.ok(state.pending.length <= ORACLE.maxPending);
  const replay = transitionOracle(structuredClone(state), input(1000)); assert.equal(replay.state.issued, state.issued);
  assert.equal(replay.state.model.n, state.model.n);
});

test('recent-underperformance fallback continues actual shadow learning and retains each issued serving policy', () => {
  let state = newOracleState(input(1000, bars(1500, 0))); state.model.bias = 8;
  for (let minute = 1000; minute <= 1042; minute++) state = transitionOracle(state, input(minute, bars(1500, 0))).state;
  assert.equal(oracleMode(state), 'baseline-performance');
  const before = structuredClone(state.model), pending = structuredClone(state.pending.at(-1));
  assert.equal(pending.mode, 'baseline-performance'); assert.equal(pending.servedP, 0.5); assert.ok(pending.p > 0.5);
  state = transitionOracle(state, input(1043, bars(1500, 0))).state;
  assert.equal(state.model.n, before.n + 1); assert.ok(state.model.bias < before.bias);
  assert.ok(state.recent.some(f => f.mode === 'baseline-warmup' && f.servedP === 0.5));
});

test('corrupt persisted weights, counters, records and nonfinite metrics are refused without resetting evidence', () => {
  const initial = transitionOracle(null, input()).state;
  for (const mutate of [s => { s.model.weights[0] = NaN; }, s => { s.pending[0].p = Infinity; },
    s => { s.model.n = -1; }, s => { s.totals.n = 99; }, s => { s.totals.flat = -1; },
    s => { s.totals.baseline.logLoss = NaN; }, s => { s.pending[0].x[0] = 2; },
    s => { s.market = 'BTC'; }, s => { s.pending[0].servedP = 0.7; }, s => { s.pending[0].modelSamples = Infinity; }]) {
    const corrupted = structuredClone(initial); mutate(corrupted);
    assert.throws(() => validateOracleState(corrupted, initial.key), /invalid_oracle_state/);
  }
});
