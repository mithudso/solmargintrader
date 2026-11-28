import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { SecondBars, MAX_GAP_S, RETAIN_BARS, vote, VOTE_EPSILON, breakout, realizedVolBps, slopeBps, curvatureBps } from '../src/1000x/scalp-indicators.js';
import { TILES, WARMUP_BARS, SCALP_MODEL, HORIZON_S, readTiles, readSlopes, SlopeHistory, scalpCall, cone, likelyMoveBps, ScoreBook,
  quotePosition, payoutPercent, bustFraction } from '../src/1000x/scalp-model.js';

const fixture = JSON.parse(readFileSync(new URL('./fixtures/1000x-scalp-parity.json', import.meta.url), 'utf8'));
const bars = fixture.bars.map(([time, open, high, low, close]) => ({ time, open, high, low, close }));
const near = (actual, expected, label) => {
  const tolerance = 1e-7 * Math.max(1, Math.abs(expected));
  assert.ok(Math.abs(actual - expected) <= tolerance, `${label}: ${actual} != ${expected}`);
};

test('the generated model constants are the ones the study wrote', () => {
  const { sha256, ...model } = SCALP_MODEL;
  assert.equal(sha256, fixture.model_sha256);
  assert.deepEqual(JSON.parse(JSON.stringify(model)), fixture.model);
  assert.equal(TILES.length, 16);
  assert.equal(HORIZON_S, 30);
  assert.ok(SCALP_MODEL.lean < SCALP_MODEL.strong && SCALP_MODEL.strong <= TILES.length);
});

test('every tile matches the Python reference on recorded oracle bars', () => {
  const first = bars.length - fixture.tail;
  let compared = 0;
  for (let i = first; i < bars.length; i++) {
    const prefix = bars.slice(0, i + 1);
    const tiles = readTiles(prefix);
    for (const [index, tile] of TILES.entries()) {
      const expected = fixture.expected[tile.feature][i - first];
      assert.notEqual(expected, null, `${tile.feature} has a reference value`);
      assert.equal(tiles[index].ready, true, tile.feature);
      near(tiles[index].value, expected, `${tile.feature}@${i}`);
      compared++;
    }
    assert.equal(scalpCall(tiles).net, fixture.net[i - first], `net vote @${i}`);
    near(realizedVolBps(prefix, 30), fixture.expected.rv_30[i - first], `rv_30@${i}`);
  }
  assert.equal(compared, fixture.tail * 16);
});

test('the slope ladder and its second derivative match the Python reference', () => {
  const first = bars.length - fixture.tail;
  assert.deepEqual(SCALP_MODEL.slopes.map(row => row.window_s), [5, 10, 20, 30, 60, 300]);
  for (let i = first; i < bars.length; i += 7) {
    const prefix = bars.slice(0, i + 1);
    const rows = readSlopes(prefix);
    for (const row of rows) {
      assert.equal(row.ready, true, `${row.window}s`);
      near(row.slope, fixture.expected[`lsl_${row.window}`][i - first], `slope ${row.window}s @${i}`);
      near(row.change, fixture.expected[`acc_${row.window}`][i - first], `curvature ${row.window}s @${i}`);
    }
  }
  // A straight line has a slope and no curvature; a parabola opening upward has rising slope.
  const line = Array.from({ length: 30 }, (_, i) => ({ time: i, open: 100 + i, high: 100 + i, low: 100 + i, close: 100 + i }));
  near(slopeBps(line, 20), 1 / 129 * 1e4, 'line slope');
  assert.ok(Math.abs(curvatureBps(line, 20)) < 1e-9);
  const bowl = Array.from({ length: 30 }, (_, i) => ({ time: i, open: 1, high: 1, low: 1, close: 1000 + (i - 15) ** 2 }));
  near(curvatureBps(bowl, 20) * bowl.at(-1).close / 1e4, 2, 'second derivative of x squared');
  const up = readSlopes(bowl).find(row => row.window === 10);
  assert.deepEqual([up.slopeVote, up.changeVote, up.state], [1, 1, 'accelerating']);
  const cap = bowl.map(bar => ({ ...bar, close: 2000 - (bar.close - 1000) })).slice(0, 14);
  assert.equal(readSlopes(cap).find(row => row.window === 10).state, 'fading', 'rising but flattening');
  const short = readSlopes(bars.slice(0, 100));
  assert.deepEqual(short.map(row => row.ready), [true, true, true, true, true, false]);
  assert.deepEqual([short.at(-1).state, short.at(-1).slope, short.at(-1).have], ['warming', null, 100]);
  assert.equal(readSlopes(line).find(row => row.window === 5).state, 'steady');
});

test('slope extremes and reversal timing match the Python reference', () => {
  const history = new SlopeHistory();
  for (let i = 0; i < bars.length; i++) history.observe(readSlopes(bars.slice(0, i + 1)));
  let runs = 0;
  for (const row of history.stats()) {
    const expected = fixture.slope_runs[row.window];
    assert.deepEqual(row.runs.list.map(run => [run.sign, run.seconds]), expected, `${row.window}s runs`);
    runs += expected.length;
    near(row.slope.min, fixture.slope_ranges[row.window].lsl[0], `${row.window}s slope min`);
    near(row.slope.max, fixture.slope_ranges[row.window].lsl[1], `${row.window}s slope max`);
    near(row.change.min, fixture.slope_ranges[row.window].acc[0], `${row.window}s change min`);
    near(row.change.max, fixture.slope_ranges[row.window].acc[1], `${row.window}s change max`);
    if (expected.length) near(row.runs.meanS, expected.reduce((sum, run) => sum + run[1], 0) / expected.length, `${row.window}s mean run`);
    assert.equal(row.samples, bars.length - row.window + 1);
  }
  assert.ok(runs > 100, 'the fixture exercises real reversals');
});

test('a reversal is timed only when both of its ends were seen', () => {
  const history = new SlopeHistory();
  const feed = votes => { for (const v of votes) history.observe([{ window: 5, ready: true, slope: v, change: 0, slopeVote: Math.sign(v) }]); };
  feed([1, 1, 1]);
  let row = history.stats().find(entry => entry.window === 5);
  assert.deepEqual([row.runs.count, row.current.sign, row.current.ageS, row.current.sinceFlip], [0, 1, 3, false]);
  feed([-1, -1, 0, -1]);
  row = history.stats().find(entry => entry.window === 5);
  assert.equal(row.runs.count, 0, 'the first run began before observation');
  assert.deepEqual([row.current.sign, row.current.ageS, row.current.sinceFlip], [-1, 4, true]);
  feed([2, 2]);
  row = history.stats().find(entry => entry.window === 5);
  assert.deepEqual(row.runs.list, [{ sign: -1, seconds: 4 }], 'a flat second does not end a run');
  assert.deepEqual([row.runs.down.meanS, row.runs.down.maxS, row.runs.up.count], [4, 4, 0]);
  assert.deepEqual([row.slope.min, row.slope.max], [-1, 2]);
  history.reset();
  feed([-3, 3, 3, -3]);
  row = history.stats().find(entry => entry.window === 5);
  assert.deepEqual(row.runs.list, [{ sign: -1, seconds: 4 }, { sign: 1, seconds: 2 }], 'the run cut by a feed gap is not timed');
  history.observe([{ window: 5, ready: false, slope: null, change: null, slopeVote: null }, { window: 7, ready: true, slope: 1, change: 1, slopeVote: 1 }]);
  assert.equal(history.stats().find(entry => entry.window === 5).samples, 13);
});

test('a reading never uses a bar after the one it is read at', () => {
  const at = 300;
  const before = readTiles(bars.slice(0, at)).map(tile => tile.value);
  const changed = bars.map((bar, i) => i < at ? bar : { ...bar, open: bar.open * 3, high: bar.high * 3, low: bar.low * 3, close: bar.close * 3 });
  assert.deepEqual(readTiles(changed.slice(0, at)).map(tile => tile.value), before);
  // The breakout window excludes the bar being tested: a new high is a breakout of the PRIOR range.
  const flat = Array.from({ length: 21 }, (_, i) => ({ time: i, open: 100, high: 100, low: 100, close: 100 }));
  assert.equal(breakout([...flat, { time: 21, open: 100, high: 101, low: 100, close: 101 }], 20), 1);
  assert.equal(breakout([...flat, { time: 21, open: 100, high: 100, low: 99, close: 99 }], 20), -1);
  assert.equal(breakout([...flat, { time: 21, open: 100, high: 100, low: 100, close: 100 }], 20), 0);
});

test('tiles stay unavailable until their own warm-up and the call waits for all of them', () => {
  assert.equal(WARMUP_BARS, 78);
  const early = readTiles(bars.slice(0, 30));
  assert.equal(early.find(tile => tile.key === 'impulse').ready, true);
  assert.equal(early.find(tile => tile.key === 'macd').ready, false);
  assert.equal(early.find(tile => tile.key === 'macd').vote, null);
  assert.deepEqual({ ready: scalpCall(early).ready, tier: scalpCall(early).tier, direction: scalpCall(early).direction },
    { ready: false, tier: 'warming', direction: 'flat' });
  assert.equal(scalpCall(readTiles(bars.slice(0, 78))).ready, true);
  assert.equal(scalpCall(readTiles([])).ready, false);
});

test('the call tiers follow the study thresholds', () => {
  const make = (up, down) => TILES.map((tile, i) => ({ ready: true, vote: i < up ? 1 : i < up + down ? -1 : 0 }));
  assert.deepEqual(['tier', 'direction', 'net'].map(key => scalpCall(make(14, 2))[key]), ['strong', 'up', 12]);
  assert.deepEqual(['tier', 'direction', 'net'].map(key => scalpCall(make(2, 14))[key]), ['strong', 'down', -12]);
  assert.deepEqual(['tier', 'direction'].map(key => scalpCall(make(11, 5))[key]), ['lean', 'up']);
  assert.deepEqual(['tier', 'direction'].map(key => scalpCall(make(8, 8))[key]), ['mixed', 'flat']);
  assert.deepEqual(['tier', 'direction'].map(key => scalpCall(make(10, 5))[key]), ['mixed', 'flat']);
  assert.equal(scalpCall(make(14, 2)).measured, SCALP_MODEL.measured.strong);
  assert.equal(vote(VOTE_EPSILON / 2), 0);
  assert.equal(vote(-1), -1);
  assert.equal(vote(null), null);
  assert.equal(vote(NaN), null);
});

test('second bars close on the next second, fill short silences and reset after long ones', () => {
  const feed = new SecondBars();
  const tick = (ms, price) => feed.push({ price, exchangeMs: ms });
  assert.equal(tick(10_200, 100), 0);
  assert.equal(tick(10_800, 101), 0);
  assert.equal(feed.bars.length, 0);
  assert.equal(tick(11_100, 99), 1);
  assert.deepEqual(feed.bars[0], { time: 10, open: 100, high: 101, low: 100, close: 101 });
  // Seconds 12 and 13 had no update: the last price stood.
  assert.equal(tick(14_000, 98), 3);
  assert.deepEqual(feed.bars.slice(1).map(bar => [bar.time, bar.close, bar.filled === true]), [[11, 99, false], [12, 99, true], [13, 99, true]]);
  assert.equal(tick(13_500, 50), 0, 'an older quote is ignored');
  const segment = feed.segment;
  assert.equal(tick((14 + MAX_GAP_S + 2) * 1000, 97), -1);
  assert.equal(feed.bars.length, 0);
  assert.equal(feed.segment, segment + 1);
  for (const bad of [null, {}, { price: NaN, exchangeMs: 1 }, { price: -1, exchangeMs: 1 }, { price: 1, exchangeMs: 0 }]) assert.equal(feed.push(bad), 0);
  const long = new SecondBars();
  for (let s = 1; s <= RETAIN_BARS + 50; s++) long.push({ price: 100 + s / 1000, exchangeMs: s * 1000 });
  assert.equal(long.bars.length, RETAIN_BARS);
  assert.equal(long.developing.time, RETAIN_BARS + 50);
});

test('the cone widens with the square root of time and leans with the call', () => {
  const flat = cone({ price: 100, sigmaBps: 1, direction: 'flat', tier: 'mixed' });
  assert.equal(flat.length, 30);
  assert.equal(flat.at(-1).mid, 100);
  near((flat.at(-1).innerHigh / 100 - 1) * 1e4, SCALP_MODEL.cone.p68 * Math.sqrt(30), 'inner band');
  near((flat.at(-1).outerHigh / 100 - 1) * 1e4, SCALP_MODEL.cone.p90 * Math.sqrt(30), 'outer band');
  assert.ok(flat.every((step, i) => !i || step.outerHigh > flat[i - 1].outerHigh));
  const up = cone({ price: 100, sigmaBps: 1, direction: 'up', tier: 'strong' });
  // The most likely line follows the recorded average path: most of the move early, then level.
  const path = SCALP_MODEL.measured.strong.path_bps;
  assert.deepEqual(path.map(point => point[0]), [5, 10, 15, 20, 25, 30]);
  near((up.at(-1).mid / 100 - 1) * 1e4, path.at(-1)[1], 'likely price at 30 s');
  near((up[4].mid / 100 - 1) * 1e4, path[0][1], 'likely price at 5 s');
  near(likelyMoveBps('strong', 2.5), path[0][1] / 2, 'interpolated from zero');
  near(likelyMoveBps('strong', 7.5), (path[0][1] + path[1][1]) / 2, 'interpolated between steps');
  assert.equal(likelyMoveBps('strong', 0), 0);
  assert.equal(likelyMoveBps('strong', 99), path.at(-1)[1]);
  assert.equal(likelyMoveBps('warming', 10), 0);
  assert.ok(path[0][1] > path.at(-1)[1] / 2, 'more than half of the average move arrives in the first five seconds');
  const lean = cone({ price: 100, sigmaBps: 1, direction: 'down', tier: 'lean' });
  near((lean.at(-1).mid / 100 - 1) * 1e4, -SCALP_MODEL.measured.lean.path_bps.at(-1)[1], 'a down call leans the line down');
  assert.ok(cone({ price: 100, sigmaBps: 1, direction: 'down', tier: 'strong' }).at(-1).mid < 100);
  assert.deepEqual(cone({ price: 0, sigmaBps: 1 }), []);
  assert.deepEqual(cone({ price: 100, sigmaBps: NaN }), []);
});

test('the score book settles a call exactly 30 seconds later and never guesses across a gap', () => {
  const book = new ScoreBook();
  const call = (direction, tier = 'strong') => ({ ready: true, direction, tier, net: direction === 'up' ? 14 : -14 });
  book.observe({ time: 100, close: 100 }, call('up'));
  book.observe({ time: 101, close: 100 }, call('down'));
  book.observe({ time: 102, close: 100 }, { ready: true, direction: 'flat', tier: 'mixed', net: 0 });
  for (let t = 103; t < 130; t++) book.observe({ time: t, close: 100 }, { ready: false });
  book.observe({ time: 130, close: 101 }, call('up'));
  book.observe({ time: 131, close: 101 }, call('up'));
  book.observe({ time: 132, close: 101 }, call('up'));
  const recent = book.recent(40);
  assert.deepEqual(recent.slice(0, 3).map(entry => entry.outcome), ['hit', 'miss', 'none']);
  assert.equal(recent[0].move > 99 && recent[0].move < 101, true);
  assert.deepEqual(book.stats().strong, { hit: 1, miss: 1, n: 2, rate: 0.5 });
  // A bar that skips the settlement second leaves the older call unknown.
  const gap = new ScoreBook();
  gap.observe({ time: 1, close: 100 }, call('up'));
  gap.observe({ time: 40, close: 200 }, call('up'));
  assert.equal(gap.recent()[0].outcome, 'unknown');
  assert.equal(gap.stats().all.n, 0);
  gap.observe({ time: 40, close: 1 }, call('down'));
  assert.equal(gap.recent().length, 2, 'a repeated second is ignored');
});

test('the payout port reproduces the saved frontend arithmetic', () => {
  for (const [move, expected] of Object.entries(fixture.payout_pct)) {
    const actual = payoutPercent({ entry: 1_000_000, mark: 1_000_000 * (1 + Number(move) / 1e4), side: 'long', leverage: 1000 });
    near(actual.percent, expected, `long ${move} bp`);
    const short = payoutPercent({ entry: 1_000_000, mark: 1_000_000 * (1 - Number(move) / 1e4), side: 'short', leverage: 1000 });
    near(short.percent, expected, `short ${move} bp`);
  }
  assert.equal(payoutPercent({ entry: 100, mark: 99.9, side: 'long', leverage: 1000 }).liquidated, true);
  assert.equal(payoutPercent({ entry: 100, mark: 99.95, side: 'long', leverage: 1000 }).liquidated, false);
  assert.equal(payoutPercent({ entry: 100, mark: NaN, side: 'long', leverage: 1000 }), null);
  assert.equal(payoutPercent({ entry: 100, mark: 101, side: 'up', leverage: 1000 }), null);
  assert.equal(payoutPercent({ entry: 100, mark: 101, side: 'long', leverage: 0 }), null);
  near(bustFraction(1000), 0.00098, 'bust distance');
  assert.equal(bustFraction(0), null);
  assert.throws(() => quotePosition({ margin: 1n, notional: 0n, entry: 1n, mark: 1n, side: 'long' }), RangeError);
  // A favourable move inside the dead zone pays nothing and still costs the close fee.
  assert.ok(payoutPercent({ entry: 100, mark: 100.0001, side: 'long', leverage: 1000 }).percent < 0);
});
