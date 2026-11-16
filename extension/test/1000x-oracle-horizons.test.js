import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { TIMEFRAMES } from '../src/1000x/feed.js';
import { ORACLE, oracleInput, makeFeatures, transitionOracle, validateOracleState } from '../src/1000x/oracle-model.js';

const base = 1_800_000_000;
const rows = Array.from({ length: 1500 }, (_, i) => ({ time: base + i * 60, open: 100 + i / 100,
  high: 100.02 + i / 100, low: 99.99 + i / 100, close: 100.01 + i / 100, closed: true }));
const snapshot = (now, candles = rows, extra = {}) => ({ symbol: 'SOL', sourceIdentity: { symbol: 'SOL', feedId: 6,
  marketAddress: 'Ew8sRjpuBttpmhSUeaAn4dLAegWnz55AuafVcGuojCPS', stream: 'fixed_rate@200ms', kind: 'oracle-ohlc' },
  status: 'live', minuteStatus: 'ready', minuteCandles: candles,
  quote: { price: 110, exchangeMs: now, receivedMs: now }, ...extra });
const input = (minute, horizon, candles = rows, lag = 2000, extra = {}) => {
  const now = (base + minute * 60) * 1000 + lag;
  return oracleInput(snapshot(now, candles, extra), now, horizon);
};

test('all supported horizon keys are distinct while default600 and causal feature coordinates stay compatible', () => {
  const inputs = TIMEFRAMES.map(t => input(1000, t.seconds));
  assert.equal(new Set(inputs.map(i => i.key)).size, 6);
  for (const [n, i] of inputs.entries()) {
    assert.equal(i.horizon, TIMEFRAMES[n].seconds);
    assert.equal(JSON.parse(i.key)[4], i.horizon);
    assert.deepEqual(makeFeatures(i.rows, i.cutoff), makeFeatures(inputs[0].rows, inputs[0].cutoff));
  }
  assert.equal(input(1000).key, input(1000, 600).key);
  for (const bad of [0, 30, 120, 1800, 7200, NaN, Infinity, '600']) assert.throws(() => input(1000, bad));
});

for (const { label, seconds } of TIMEFRAMES) {
  test(`${label} scores only its exact genuine rolling target, never an earlier or selected-chart close`, () => {
    const first = transitionOracle(null, input(1000, seconds)).state;
    assert.equal(first.pending[0].target, base + 1000 * 60 + seconds);
    const before = transitionOracle(first, input(999 + seconds / 60, seconds, rows, 59_999)).state;
    assert.equal(before.model.n, 0);
    const matured = transitionOracle(first, input(1000 + seconds / 60, seconds)).state;
    assert.equal(matured.model.n, 1); assert.equal(matured.totals.n, 1);
    assert.equal(matured.recent[0].close, rows[999 + seconds / 60].close);
    assert.equal(matured.recent[0].outcome, 'UP');
    assert.equal(matured.recent[0].p, first.pending[0].p);
    const duplicate = transitionOracle(structuredClone(matured), input(1000 + seconds / 60, seconds)).state;
    assert.deepEqual(duplicate, matured);
  });
  test(`${label} missing/partial target minutes remain unknown and expire outside all denominators`, () => {
    const first = transitionOracle(null, input(1000, seconds)).state;
    const missingAt = base + (1000 + Math.floor(seconds / 120)) * 60;
    for (const candles of [rows.filter(r => r.time !== missingAt), rows.map(r => r.time === missingAt ? { ...r, partial: true } : r)]) {
      const waiting = transitionOracle(first, input(1000 + seconds / 60, seconds, candles)).state;
      assert.equal(waiting.model.n, 0); assert.equal(waiting.totals.n, 0); assert.equal(waiting.expired, 0);
      const expired = transitionOracle(waiting, input(1000 + seconds / 60, seconds, candles, 90_001)).state;
      assert.equal(expired.model.n, 0); assert.equal(expired.totals.n, 0); assert.equal(expired.expired, 1);
    }
  });
}

test('one-hour issuance sustains60 pending forecasts and resolves prospectively beyond the former32 bound', () => {
  let state;
  for (let minute = 1000; minute < 1060; minute++) state = transitionOracle(state, input(minute, 3600)).state;
  assert.equal(state.issued, 60); assert.equal(state.pending.length, 60); assert.equal(state.model.n, 0);
  assert.ok(ORACLE.maxPending >= 63 && ORACLE.maxPending < 100);
  state = transitionOracle(state, input(1060, 3600)).state;
  assert.equal(state.issued, 61); assert.equal(state.pending.length, 60); assert.equal(state.model.n, 1);
  assert.equal(state.recent[0].cutoff, base + 1000 * 60);
});

test('genuine-format0.9 ten-minute trained state, immutable pending forecasts and metrics survive without a migration', () => {
  const fixture = JSON.parse(fs.readFileSync(new URL('./fixtures/oracle-0.9-10m-state.json', import.meta.url)));
  const legacy = fixture.state;
  assert.equal(legacy.model.n, 21); assert.equal(input(1030).key, legacy.key);
  assert.deepEqual(validateOracleState(structuredClone(legacy), legacy.key), legacy);
  const restored = transitionOracle(structuredClone(legacy), input(1030, 600));
  assert.equal(restored.changed, false); assert.deepEqual(restored.state, legacy);
  const learned = transitionOracle(restored.state, input(1031, 600)).state;
  assert.equal(learned.model.n, 22); assert.equal(learned.recent.at(-1).id, legacy.pending[0].id);
  assert.equal(learned.recent.at(-1).p, legacy.pending[0].p);
  for (const t of TIMEFRAMES.filter(t => t.seconds !== 600)) {
    const fresh = transitionOracle(null, input(1031, t.seconds)).state;
    assert.equal(fresh.model.n, 0); assert.equal(fresh.historicalTrainingSamples, 0);
    assert.notEqual(fresh.key, legacy.key);
  }
});

test('all six issued forecasts and outcomes are invariant to future rows and reject cross-horizon state reuse', () => {
  for (const t of TIMEFRAMES) {
    const initial = input(1000, t.seconds), prefix = rows.filter(r => r.time < initial.cutoff);
    const issued = transitionOracle(null, initial).state;
    assert.deepEqual(transitionOracle(null, input(1000, t.seconds, prefix)).state, issued);
    const targetMinute = 1000 + t.seconds / 60;
    const changedFuture = rows.map(r => r.time >= base + targetMinute * 60 ? { ...r, open: 999, high: 1000, low: 998, close: 999 } : r);
    assert.deepEqual(transitionOracle(issued, input(targetMinute, t.seconds, changedFuture)).state,
      transitionOracle(issued, input(targetMinute, t.seconds)).state);
    const other = TIMEFRAMES.find(x => x.seconds !== t.seconds);
    assert.throws(() => validateOracleState(issued, input(1000, other.seconds).key));
  }
});

test('invalid shared minute arithmetic withholds every horizon even after the cutoff was already issued', () => {
  const overflow = rows.map(r => ({ ...r, open: 1e308, high: 1.79e308, low: 1, close: 1.79e308 }));
  for (const t of TIMEFRAMES) {
    const state = transitionOracle(null, input(1000, t.seconds)).state;
    const invalid = input(1000 + t.seconds / 60, t.seconds, overflow);
    assert.equal(invalid.eligible, false); assert.equal(invalid.reason, 'oracle_features_unavailable');
    const abstained = transitionOracle(state, invalid).state;
    assert.equal(abstained.model.n, 0); assert.equal(abstained.totals.n, 0); assert.equal(abstained.issued, 1);
  }
});
