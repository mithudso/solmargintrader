import test from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_INDICATORS, validateIndicatorConfig, computeIndicators } from '../src/1000x/indicators.js';

const epoch = 1_700_000_000;
const prices = closes => closes.map((close, i) => ({ time: epoch + i * 60,
  open: close, high: close + 1, low: close - 1, close }));
const bars = rows => rows.map(([open, high, low, close], i) => ({ time: epoch + i * 60, open, high, low, close }));
const values = series => series.map(point => point.value);
function near(actual, expected, tolerance = 1e-10) {
  assert.equal(typeof actual, 'number');
  assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} differs from ${expected}`);
}
function nearSeries(actual, expected) {
  assert.equal(actual.length, expected.length);
  actual.forEach((value, i) => expected[i] === null ? assert.equal(value, null) : near(value, expected[i]));
}

test('config normalizes partial options without changing input or frozen defaults', () => {
  const input = { rsi: { length: 3 }, bop: { enabled: false } };
  const before = structuredClone(input);
  const config = validateIndicatorConfig(input);
  assert.equal(config.rsi.length, 3);
  assert.equal(config.rsi.oversold, 30);
  assert.equal(config.bop.enabled, false);
  assert.equal(config.zigzag.reversalPercent, 0.5);
  assert.deepEqual(input, before);
  config.rsi.length = 7;
  assert.equal(DEFAULT_INDICATORS.rsi.length, 14);
  assert.ok(Object.isFrozen(DEFAULT_INDICATORS));
  for (const item of Object.values(DEFAULT_INDICATORS)) assert.ok(Object.isFrozen(item));
});

test('config rejects typo fields, coerced numbers, invalid bounds and inconsistent thresholds', () => {
  for (const input of [null, [], 1, { sar: {} }, { rsi: null }, { rsi: { period: 14 } },
    { rsi: { length: '14' } }, { rsi: { length: 1 } }, { rsi: { length: 2.5 } },
    { rsi: { length: 501 } }, { rsi: { enabled: 1 } },
    { rsi: { oversold: 70, overbought: 30 } }, { rsi: { overbought: NaN } },
    { zigzag: { reversalPercent: 0 } }, { zigzag: { reversalPercent: 51 } },
    { bop: { smoothing: 0 } }, { volty: { length: 0 } }, { volty: { multiplier: Infinity } },
    { volty: { multiplier: 0 } }, { psar: { start: 0 } }, { psar: { max: 1.1 } },
    { psar: { start: 0.3, max: 0.2 } }, { psar: { step: 0.3, max: 0.2 } }]) {
    assert.throws(() => validateIndicatorConfig(input), { name: /^(TypeError|RangeError)$/ });
  }
});

test('empty and short histories keep warmups unavailable instead of fabricating values', () => {
  const empty = computeIndicators([]);
  assert.deepEqual(empty.rsi.series, []);
  assert.equal(empty.rsi.latest, null);
  assert.equal(empty.bop.latest, null);
  assert.equal(empty.psar.latest, null);
  assert.equal(empty.volty.latest, null);
  assert.equal(empty.volty.next, null);
  assert.deepEqual(empty.zigzag.confirmed, []);
  assert.equal(empty.zigzag.provisional, null);
  const single = computeIndicators(prices([10]));
  assert.deepEqual(values(single.rsi.series), [null]);
  assert.deepEqual(values(single.psar.series), [null]);
  assert.deepEqual(values(single.volty.upper), [null]);
  assert.equal(single.bop.latest, 0);
  assert.equal(single.zigzag.provisional.kind, 'undetermined');
});

test('disabled indicators remain candle-aligned and report no latest value', () => {
  const candles = prices([10, 11, 9, 12, 10]);
  const input = Object.fromEntries(Object.keys(DEFAULT_INDICATORS).map(name => [name, { enabled: false }]));
  const result = computeIndicators(candles, input);
  for (const name of ['rsi', 'bop', 'psar']) {
    assert.deepEqual(values(result[name].series), [null, null, null, null, null]);
    assert.equal(result[name].latest, null);
    assert.equal(result[name].signal, 'Disabled.');
  }
  assert.deepEqual(values(result.volty.upper), [null, null, null, null, null]);
  assert.deepEqual(values(result.volty.lower), [null, null, null, null, null]);
  assert.equal(result.volty.next, null);
  assert.deepEqual(result.psar.points, []);
  assert.deepEqual(result.zigzag.confirmed, []);
  assert.equal(result.zigzag.provisional, null);
});

test('malformed OHLC, volume and timestamps fail closed without mutating the candles', () => {
  const source = prices([10, 11]);
  const before = structuredClone(source);
  computeIndicators(source);
  assert.deepEqual(source, before);
  assert.throws(() => computeIndicators(null));
  assert.throws(() => computeIndicators([null]));
  for (const patch of [{ open: NaN }, { high: Infinity }, { low: 0 }, { close: '10' },
    { open: -1 }, { high: 9 }, { low: 11 }, { close: 12 },
    { volume: -1 }, { volume: undefined }, { volume: NaN },
    { time: epoch + 0.5 }, { time: epoch * 1000 }, { time: -1 }, { time: '1700000000' }]) {
    assert.throws(() => computeIndicators([{ ...source[0], ...patch }]));
  }
  assert.throws(() => computeIndicators([source[0], source[0]]), /unique and increasing/);
  assert.throws(() => computeIndicators([source[1], source[0]]), /unique and increasing/);
  assert.doesNotThrow(() => computeIndicators([{ ...source[0], volume: 0 }]));
});

test('RSI matches the classic 14-change Wilder worksheet with an SMA seed', () => {
  // Independent published worksheet values (rounded here only after 8 decimals):
  // https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi
  const closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08,
    45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64, 46.21];
  const result = values(computeIndicators(prices(closes)).rsi.series);
  assert.deepEqual(result.slice(0, 14), Array(14).fill(null));
  const expected = [70.46413502, 66.24961855, 66.48094183, 69.34685316, 66.29471266, 57.91502067, 62.88071831];
  expected.forEach((value, i) => near(result[i + 14], value, 1e-8));
});

test('RSI handles flat, only-gain and only-loss sequences after the complete seed', () => {
  for (const [closes, expected] of [[[10, 10, 10, 10, 10], 50], [[10, 11, 12, 13, 14], 100],
    [[14, 13, 12, 11, 10], 0]]) {
    const result = values(computeIndicators(prices(closes), { rsi: { length: 3 } }).rsi.series);
    assert.deepEqual(result.slice(0, 3), [null, null, null]);
    near(result[3], expected);
    near(result[4], expected);
  }
});

test('Balance of Power matches hand ratios, zero-range behavior and SMA warmup', () => {
  const candles = bars([[10, 14, 8, 12], [12, 14, 10, 11], [11, 11, 11, 11]]);
  nearSeries(values(computeIndicators(candles).bop.series), [1 / 3, -1 / 4, 0]);
  nearSeries(values(computeIndicators(candles, { bop: { smoothing: 2 } }).bop.series), [null, 1 / 24, -1 / 8]);
});

test('Volty matches hand SMA(true range) levels with the exact local stop_levels shift', () => {
  const candles = prices([10, 12, 11, 15, 14, 16, 13]);
  // TR[0] unavailable, then 3, 2, 5, 2, 3, 4. With length3 and multiplier1/2,
  // widths at bars3..6 are 5/3, 3/2, 5/3, 3/2; active levels use prior close/width.
  const result = computeIndicators(candles, { volty: { length: 3, multiplier: 0.5 } }).volty;
  nearSeries(values(result.upper), [null, null, null, null, 15 + 5 / 3, 15.5, 16 + 5 / 3]);
  nearSeries(values(result.lower), [null, null, null, null, 15 - 5 / 3, 12.5, 16 - 5 / 3]);
  near(result.next.upper, 14.5);
  near(result.next.lower, 11.5);
  assert.equal(result.next.basedOn, candles[6].time);
  const short = computeIndicators(candles.slice(0, 4), { volty: { length: 3, multiplier: 0.5 } }).volty;
  assert.equal(short.latest, null);
  near(short.next.upper, 15 + 5 / 3);
  const defaults = computeIndicators(candles).volty;
  nearSeries(values(defaults.upper), [null, null, null, null, null, null, 18.25]);
  near(defaults.next.upper, 15.4);
  near(defaults.next.lower, 10.6);
});

test('Volty active levels exclude every value from the current bar', () => {
  const candles = prices([10, 12, 11, 15, 14, 16, 13]);
  const changed = structuredClone(candles);
  changed[6] = { ...changed[6], open: 19, high: 25, low: 2, close: 20 };
  const a = computeIndicators(candles).volty;
  const b = computeIndicators(changed).volty;
  assert.deepEqual(a.upper, b.upper);
  assert.deepEqual(a.lower, b.lower);
  assert.notDeepEqual(a.next, b.next);
});

test('ZigZag fixes close-based pivot origins and records their later confirmation times', () => {
  const candles = prices([100, 101, 103, 102, 101, 100, 102, 104, 103, 101]);
  const result = computeIndicators(candles, { zigzag: { reversalPercent: 2 } }).zigzag;
  assert.deepEqual(result.confirmed, [
    { time: candles[0].time, value: 100, kind: 'low', confirmedAt: candles[2].time },
    { time: candles[2].time, value: 103, kind: 'high', confirmedAt: candles[5].time },
    { time: candles[5].time, value: 100, kind: 'low', confirmedAt: candles[6].time },
    { time: candles[7].time, value: 104, kind: 'high', confirmedAt: candles[9].time },
  ]);
  assert.deepEqual(result.provisional, { time: candles[9].time, value: 101, kind: 'low' });
  const beforeConfirmation = computeIndicators(candles.slice(0, 2), { zigzag: { reversalPercent: 2 } }).zigzag;
  assert.deepEqual(beforeConfirmation.confirmed, []);
  const falling = computeIndicators(prices([100, 99.5, 98, 99, 100]), { zigzag: { reversalPercent: 2 } }).zigzag;
  assert.deepEqual(falling.confirmed.map(point => point.kind), ['high', 'low']);
  assert.deepEqual(falling.confirmed.map(point => point.value), [100, 98]);
});

test('Parabolic SAR matches hand recurrence, two-bar clamps and both reversal directions', () => {
  const candles = bars([[9.5, 10, 9, 9.5], [10.5, 11, 10, 10.5], [11, 12, 10.5, 11.5],
    [12, 13, 11, 12.5], [12, 12.5, 9, 9.5], [9, 10, 8, 8.5], [10, 14, 9, 13.5], [13, 15, 12, 14]]);
  const result = computeIndicators(candles).psar;
  nearSeries(values(result.series), [null, 9, 9, 9.12, 13, 13, 8, 8]);
  assert.deepEqual(result.points.map(point => point.trend), ['up', 'up', 'up', 'down', 'down', 'up', 'up']);
  assert.equal(result.points[0].time, candles[1].time);
});

test('Parabolic SAR uses documented down/tie seeds, strict crossings and an AF cap', () => {
  const down = computeIndicators(bars([[12, 13, 11, 12], [11, 12, 10, 11], [10, 13, 9, 10]])).psar;
  nearSeries(values(down.series), [null, 13, 13]);
  assert.equal(down.trend, 'down', 'a high equal to SAR does not reverse');
  const tie = computeIndicators(bars([[10, 11, 9, 10], [10, 12, 8, 10], [10, 13, 8, 11]])).psar;
  assert.equal(tie.points[0].trend, 'up');
  assert.equal(tie.trend, 'up', 'a low equal to SAR does not reverse');
  const capped = computeIndicators(bars([[5, 10, 1, 5], [6, 11, 2, 6], [18, 20, 15, 18],
    [20, 21, 16, 20], [21, 22, 17, 21], [22, 23, 18, 22]]),
  { psar: { start: 0.1, step: 0.2, max: 0.3 } }).psar;
  nearSeries(values(capped.series), [null, 1, 1, 2, 7.7, 11.99]);
});

test('every numeric series is prefix-invariant, and confirmed ZigZag pivots never repaint', () => {
  const candles = prices([100, 101, 103, 102, 101, 100, 102, 104, 103, 101, 98, 100,
    103, 107, 106, 105, 103, 108, 109, 107, 105, 104, 110, 112]);
  const config = { zigzag: { reversalPercent: 2 }, rsi: { length: 3 }, bop: { smoothing: 3 },
    volty: { length: 3 } };
  const full = computeIndicators(candles, config);
  for (let end = 1; end <= candles.length; end++) {
    const prefix = computeIndicators(candles.slice(0, end), config);
    for (const name of ['rsi', 'bop', 'psar']) assert.deepEqual(prefix[name].series, full[name].series.slice(0, end));
    for (const name of ['upper', 'lower']) assert.deepEqual(prefix.volty[name], full.volty[name].slice(0, end));
    assert.deepEqual(prefix.zigzag.confirmed, full.zigzag.confirmed.filter(point => point.confirmedAt <= candles[end - 1].time));
    if (end < candles.length && prefix.volty.next) {
      near(prefix.volty.next.upper, full.volty.upper[end].value);
      near(prefix.volty.next.lower, full.volty.lower[end].value);
    }
  }
});

test('unrepresentable derived levels throw instead of returning Infinity or a made-up fallback', () => {
  const candles = bars([[1e307, 1.7e308, 1, 1e307], [1e308, 1.7e308, 1, 1e308], [1e308, 1.7e308, 1, 1e308]]);
  assert.throws(() => computeIndicators(candles, { volty: { length: 1, multiplier: 100 } }), /not finite/);
});
