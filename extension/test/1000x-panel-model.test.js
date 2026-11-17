import test from 'node:test';
import assert from 'node:assert/strict';
import { panelModel } from '../src/1000x/panel-model.js';

const base = 1_800_000_000;
const bar = (i, extra = {}) => ({ time: base + i * 60, open: 100 + i, high: 102 + i, low: 99 + i, close: 101 + i, closed: true, ...extra });
const now = (base + 5 * 60 + 10) * 1000;
const snapshot = extra => ({ symbol: 'SOL', intervalSec: 60, status: 'live', quote: { price: 106, exchangeMs: now, receivedMs: now }, candles: Array.from({ length: 6 }, (_, i) => bar(i, { closed: i < 5 })), ...extra });

test('only complete candles inform signal readouts; developing chart values stay separate', () => {
  const model = panelModel(snapshot(), {}, now);
  assert.equal(model.signalEligible, true);
  assert.equal(model.closedCount, 5);
  assert.equal(model.closedThrough, base + 4 * 60);
  assert.equal(model.candles.length, 6);
  assert.equal(model.completed.bop.series.length, 5);
  assert.equal(model.developing.bop.series.length, 6);
});

test('a delayed callback independently invalidates old quotes even if feed status still says live', () => {
  const model = panelModel(snapshot(), {}, now + 3001);
  assert.equal(model.signalEligible, false);
  assert.match(model.reason, /stale/);
  assert.equal(model.closedCount, 5);
});

test('future, invalid, missing and stale receipt timestamps cannot establish freshness', () => {
  for (const quote of [null, { price: 106, exchangeMs: now + 251, receivedMs: now }, { price: 106, exchangeMs: now, receivedMs: NaN }, { price: 106, exchangeMs: now, receivedMs: now - 3001 }, { price: NaN, exchangeMs: now, receivedMs: now }]) {
    assert.equal(panelModel(snapshot({ quote }), {}, now).signalEligible, false);
  }
});

test('a fresh quote cannot revive old candle-derived explanations', () => {
  const model = panelModel(snapshot({ candles: [bar(0), bar(1), bar(2)] }), {}, now);
  assert.equal(model.signalEligible, false);
  assert.match(model.reason, /latest complete candle/);
});

test('disconnected and backfilling snapshots with fresh quotes withhold signals', () => {
  for (const status of ['stale', 'error', 'unsupported', 'connecting', 'backfilling']) {
    assert.equal(panelModel(snapshot({ status }), {}, now).signalEligible, false);
  }
});

test('missing time buckets reset the mathematical history at the gap', () => {
  const model = panelModel(snapshot({ candles: [bar(0), bar(1), bar(3), bar(4), bar(5, { closed: false })] }), {}, now);
  assert.equal(model.gapTrimmed, true);
  assert.deepEqual(model.candles.map(c => c.time), [base + 180, base + 240, base + 300]);
  assert.equal(model.closedCount, 2);
  assert.equal(model.completed.rsi.latest, null);
});

test('a past partial candle splits completed history and cannot warm up an indicator', () => {
  const model = panelModel(snapshot({ candles: [bar(0), bar(1, { partial: true, closed: false }), bar(2), bar(3), bar(4), bar(5, { closed: false })] }), {}, now);
  assert.equal(model.closedCount, 3);
  assert.equal(model.completed.bop.series[0].time, base + 120);
  assert.equal(model.developing.bop.series[0].time, base + 120);
});

test('future complete flags never make a developing bucket complete', () => {
  const model = panelModel(snapshot({ candles: [bar(5)] }), {}, now);
  assert.equal(model.closedCount, 0);
  assert.equal(model.signalEligible, false);
});

test('malformed intervals and candle prices fail visibly without a numeric substitute', () => {
  assert.throws(() => panelModel(snapshot({ intervalSec: 0 }), {}, now));
  assert.throws(() => panelModel(snapshot({ candles: [bar(1, { close: NaN })] }), {}, now));
});

test('an intrabar ZigZag reversal is never drawn as a solid confirmed pivot', () => {
  const candles = [100, 110, 112, 111, 110, 100].map((value, i) => ({ ...bar(i), open: value, high: value + 1, low: value - 1, close: value, closed: i < 5 }));
  const model = panelModel(snapshot({ candles }), { zigzag: { reversalPercent: 10 } }, now);
  assert.ok(model.developing.zigzag.confirmed.length > model.confirmedPivots.length);
  const retreat = candles.map((c, i) => i === 5 ? { ...c, open: 110, high: 111, low: 109, close: 110 } : c);
  assert.deepEqual(panelModel(snapshot({ candles: retreat }), { zigzag: { reversalPercent: 10 } }, now).confirmedPivots, model.confirmedPivots);
});
