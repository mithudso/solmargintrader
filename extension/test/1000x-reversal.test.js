import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { aggregateMinutes, describeShape, reversalContext } from '../src/1000x/reversal.js';
import { computeIndicators } from '../src/1000x/indicators.js';

const base = 1_800_000_000;
const objectBars = rows => rows.map(([time, open, high, low, close]) => ({ time, open, high, low, close, closed: true }));
const minuteBars = (count, direction = 'DOWN') => Array.from({ length: count }, (_, i) => ({
  time: base + i * 60, open: 100, high: 102, low: 98, close: direction === 'DOWN' ? 99 : 101, closed: true,
}));
const fixture = JSON.parse(fs.readFileSync(new URL('./fixtures/1000x-python-parity.json', import.meta.url)));
const near = (actual, expected, tolerance = 1e-9) => assert.ok(Number.isFinite(actual) && Math.abs(actual - expected) <= tolerance, `${actual} != ${expected}`);

test('frozen numerical vectors bind the independent Python sources exactly', () => {
  for (const [file, expected] of Object.entries(fixture.source_sha256)) {
    const bytes = fs.readFileSync(new URL(`../../${file}`, import.meta.url));
    assert.equal(createHash('sha256').update(bytes).digest('hex'), expected, `${file}: regenerate independent vectors after reviewing a changed formula`);
  }
});

test('EMA9/21, MACD12/26/9 and BOP SMA3 match independent Python first-close seeds and 78-bar warmup', () => {
  for (const example of fixture.momentum) {
    const rows = objectBars(example.rows), result = computeIndicators(rows, { bop: { smoothing: 3 } });
    assert.ok(result.ema.fast.slice(0, 77).every(point => point.value === null));
    assert.ok(result.macd.series.slice(0, 77).every(point => point.value === null));
    for (const [index, expected] of Object.entries(example.expected)) {
      const i = Number(index);
      near(result.ema.fast[i].value, expected.ema9);
      near(result.ema.slow[i].value, expected.ema21);
      near(result.macd.series[i].value, expected.macd);
      near(result.macd.signalSeries[i].value, expected.macd_signal);
      near(result.bop.series[i].value, expected.bop_sma3);
    }
  }
});

test('all nine shape paths match independent NumPy/pandas trailing fits at three prefixes', () => {
  const seen = new Set();
  for (const example of fixture.shapes) {
    const bars = objectBars(example.rows);
    for (const expected of example.expected) {
      const rows = bars.slice(0, expected.count), at = rows.at(-1).time + 300;
      const actual = describeShape(rows, 5, at);
      assert.equal(actual.shape, expected.shape, `${example.name} prefix ${expected.count}`);
      assert.equal(actual.zone, expected.zone);
      near(actual.rangePosition, expected.range_position);
      near(actual.efficiency, expected.efficiency);
      if (rows.every(row => row.close === rows[0].close)) assert.equal(actual.fitR2, null, 'constant paths have no fit quality');
      else near(actual.fitR2, expected.r2, 1e-5);
      seen.add(actual.shape);
    }
  }
  for (const shape of ['range', 'trend_up', 'trend_down', 'bowl', 'cap', 'v_rebound', 'inverted_v', 'compression']) assert.ok(seen.has(shape), `missing independent ${shape} example`);
});

test('epoch aggregation requires every closed minute, accepts zero oracle volume and never fills gaps', () => {
  const rows = minuteBars(31).map(row => ({ ...row, volume: 0 }));
  assert.equal(aggregateMinutes(rows, 10, base + 30 * 60).length, 3);
  const gapped = rows.filter((_, i) => i !== 14);
  assert.deepEqual(aggregateMinutes(gapped, 10, base + 30 * 60).map(bar => bar.time), [base, base + 1200]);
  const partial = rows.map((row, i) => i === 14 ? { ...row, partial: true } : row);
  assert.equal(aggregateMinutes(partial, 10, base + 30 * 60).length, 2);
  assert.equal(aggregateMinutes(rows, 10, base + 29 * 60).length, 2);
  assert.throws(() => aggregateMinutes([{ ...rows[0], time: base + 1 }], 10, base + 60), /aligned/);
});

test('DD and UU use their own candle bodies, are mirrored contexts, and never manufacture model probability', () => {
  for (const [direction, pair, watch] of [['DOWN', 'DD', 'UP'], ['UP', 'UU', 'DOWN']]) {
    const rows = minuteBars(1200, direction), now = (base + 1200 * 60 + 10) * 1000;
    const result = reversalContext(rows, now, true);
    assert.equal(result.ready, true); assert.equal(result.pair, pair); assert.equal(result.direction, watch);
    assert.equal(result.empirical.probability, null); assert.equal(result.empirical.score, null);
    assert.equal(result.exit.roe, null); assert.equal(result.exit.intent, null);
    assert.equal(result.heuristic.total, 3);
    assert.equal(result.previous.length, 2);
    for (const minutes of [5, 10, 15, 20]) assert.notEqual(result.frames[minutes].shape, 'unknown');
  }
});

test('mixed/flat pairs and an absent closed minute do not establish a setup', () => {
  const at = base + 1200 * 60;
  const rows = minuteBars(1200);
  const flat = rows.map((row, i) => i === 1199 ? { ...row, close: row.open } : row);
  assert.equal(reversalContext(flat, at * 1000, true).direction, null);
  const mixed = rows.map((row, i) => i === 1199 ? { ...row, close: 101 } : row);
  assert.equal(reversalContext(mixed, at * 1000, true).direction, null);
  const missing = rows.filter((_, i) => i !== 1190);
  assert.equal(reversalContext(missing, at * 1000, true).ready, false);
});

test('the developing target can turn without changing the completed pair, shapes, momentum or heuristic', () => {
  const rows = minuteBars(1201), at = base + 1200 * 60 + 20;
  rows.at(-1).closed = false;
  const first = reversalContext(rows, at * 1000, true);
  const changed = rows.map((row, i) => i === 1200 ? { ...row, close: 101 } : row);
  const second = reversalContext(changed, at * 1000, true);
  assert.equal(first.developing.color, 'DOWN'); assert.equal(second.developing.color, 'UP');
  for (const key of ['pair', 'direction', 'previous', 'frames', 'momentum', 'heuristic', 'empirical']) assert.deepEqual(second[key], first[key], key);
});

test('future candle mutations cannot alter a context evaluated at an earlier clock', () => {
  const rows = minuteBars(1350), at = base + 1200 * 60;
  const prefix = reversalContext(rows.slice(0, 1200), at * 1000, true);
  const mutated = rows.map((row, i) => i >= 1200 ? { ...row, open: 1, high: 9000, low: 1, close: 8000 } : row);
  assert.deepEqual(reversalContext(mutated, at * 1000, true), prefix);
});

test('a partially observed target opening never receives an invented developing direction', () => {
  const rows = minuteBars(1201), now = (base + 1200 * 60 + 10) * 1000;
  Object.assign(rows.at(-1), { closed: false, partial: true });
  const result = reversalContext(rows, now, true);
  assert.equal(result.ready, true);
  assert.equal(result.pair, 'DD');
  assert.equal(result.developing, null);
});

test('gaps restart every shape warmup and stale feeds withhold directional alignment', () => {
  const rows = minuteBars(1200).filter((_, i) => i !== 1180), at = base + 1200 * 60;
  const result = reversalContext(rows, at * 1000, false);
  assert.equal(result.ready, false); assert.equal(result.momentum.ready, false); assert.equal(result.heuristic, null);
  for (const frame of Object.values(result.frames)) assert.equal(frame.shape, 'unknown');
  const oldBars = aggregateMinutes(minuteBars(1200), 20, at);
  assert.equal(describeShape(oldBars, 20, at + 1200).shape, 'unknown');
});

test('EMA and MACD numerical outputs are prefix invariant and disabled series stay unavailable', () => {
  const rows = objectBars(fixture.momentum[0].rows), full = computeIndicators(rows);
  for (const count of [77, 78, 90, 120]) {
    const prefix = computeIndicators(rows.slice(0, count));
    for (const key of ['fast', 'slow']) assert.deepEqual(prefix.ema[key], full.ema[key].slice(0, count));
    for (const key of ['series', 'signalSeries', 'histogram']) assert.deepEqual(prefix.macd[key], full.macd[key].slice(0, count));
  }
  const disabled = computeIndicators(rows, { ema: { enabled: false }, macd: { enabled: false } });
  assert.equal(disabled.ema.latest, null); assert.equal(disabled.macd.latest, null);
  assert.ok(disabled.macd.histogram.every(point => point.value === null));
});
