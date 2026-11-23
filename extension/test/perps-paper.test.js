import test from 'node:test';
import assert from 'node:assert/strict';
import { formingChartCandle } from '../src/perps/chart-candles.js';
import { MARKETS, barrier, carryCost, planPosition, settle } from '../src/perps/model.js';
import { gumTerms, jlpTerms, parseGumMinutes, parseJlpPrices } from '../src/perps/market.js';
import { PaperBroker } from '../src/perps/replay.js';
import { aggregateMinutes, marketPresets, signalMap } from '../src/perps/strategies.js';

const sol = jlpTerms('SOL', { openFeePercent: '0.06', maxPriceImpactFeePercent: '0.44', longBorrowRatePercent: '0.0015' }, 1);
const gum = { ...MARKETS.ZEC, baseBps: 3.5, liquidationBps: 75, maintenanceBps: 100, carryBps: 2,
  firstTierCap: 10000, maxOrder: 20000, minOrder: 5, maxQty: 25, stepSize: 0.001 };
const risk = { sizing: 'collateral', amount: 25, leverage: 10, tp: 1.5, sl: 0.8, slippageBps: 0, additiveBps: 0, networkUsd: 0 };
const bar = (time, open, low = open, high = open) => ({ time, open, low, high, close: open });
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-8, `${a} != ${b}`);

test('JLP fees reduce initial liquidation buffer on both sides and accrue on size', () => {
  const long = planPosition(risk, sol, 100);
  const short = planPosition(risk, sol, 100, -1);
  near(long.size, 250);
  near(long.openCost, 0.175);
  near(long.liquidation, 90.34);
  near(short.liquidation, 109.66);
  near(carryCost(long, 0, 3600, 100), 0.00375);
  const large = planPosition({ ...risk, leverage: 250 }, sol, 100);
  near(large.liquidation, 99.94);
  assert.throws(() => planPosition({ ...risk, leverage: 250, additiveBps: 10 }, sol, 100), /exhaust/);
  near(settle(large, { reason: 'liquidation', price: 99.94 }, 0).pnl, -25);
});

test('sizing basis keeps the intended quantity fixed and does not apply JLP fees to GUM', () => {
  const a = planPosition({ ...risk, sizing: 'notional', amount: 250, leverage: 5 }, sol, 100);
  const b = planPosition({ ...risk, sizing: 'notional', amount: 250, leverage: 50 }, sol, 100);
  near(a.size, b.size);
  near(a.deposit, 50);
  near(b.deposit, 5);
  const g = planPosition(risk, gum, 100);
  near(g.openCost, 0.0875);
  const exposure = g.units * g.liquidation;
  near(g.collateral + g.units * (g.liquidation - g.entry), exposure * 178.5 / 10000);
  near(carryCost(g, 3599, 3600, 100), 0.05);
  near(carryCost({ ...g, direction: -1 }, 3599, 3600, 100), -0.05);
  assert.throws(() => planPosition({ ...risk, leverage: 250 }, gum, 100), /valid position/);
});

test('same-minute adverse path and gap through the stop use pessimistic accounting', () => {
  const p = planPosition(risk, sol, 100);
  assert.deepEqual(barrier(p, bar(60, 100, 95, 102), 0), { reason: 'stop', price: 99.2 });
  assert.deepEqual(barrier(p, bar(60, 98, 89, 102), 0), { reason: 'stop', price: 98 });
  assert.equal(barrier(p, bar(60, 100, 89, 102), 0).reason, 'liquidation');
});

test('a known next-open signal exit precedes the same minute low', () => {
  const paper = new PaperBroker(risk);
  const options = { decisionKind: 'mean', long: sol, short: sol };
  paper.observe(bar(60, 100), { ...options, decision: { weight: 1 } });
  paper.observe(bar(120, 100, 88), { ...options, decision: { weight: 0 } });
  assert.equal(paper.ledger.length, 1);
  assert.equal(paper.ledger[0].reason, 'signal');
  near(paper.ledger[0].pnl, -0.3500625);
});

test('Volty cannot reopen repeatedly beyond the same stop following liquidation', () => {
  const paper = new PaperBroker({ ...risk, leverage: 250, sl: 0, tp: 0 });
  const options = { decisionKind: 'volty', long: sol, short: sol };
  paper.observe(bar(60, 101, 100.5, 101.1), { ...options, decision: { upper: 100.5, lower: 98 } });
  paper.observe(bar(120, 101), options);
  assert.equal(paper.ledger.length, 1);
  assert.equal(paper.ledger[0].reason, 'liquidation');
  assert.equal(paper.position, null);
});

test('only complete chronological candles reach a strategy and future bars preserve its prefix', () => {
  assert.deepEqual(aggregateMinutes([bar(0, 100), bar(60, 100), bar(180, 100), bar(240, 100)], 300), []);
  const preset = marketPresets('ZEC').find(x => x.id === 'zec-mean');
  const history = Array.from({ length: 150 }, (_, i) => bar(60 * i, i < 124 ? 100 : 98));
  const before = signalMap(history, preset);
  assert.deepEqual([...signalMap([...history, bar(9000, 20)], preset)].slice(0, before.size), [...before]);
  assert.equal(before.has(7500), true);
  assert.equal(marketPresets('ZEC').filter(x => x.kind === 'archive').length, 62);
  assert.ok(marketPresets('ZEC').some(x => x.step === 60));

  const minutes = [bar(300, 100, 98, 104), bar(360, 105, 102, 108)];
  const forming = formingChartCandle(minutes, 300, 427);
  assert.equal(forming.through, 420);
  const { color, wickColor, ...ohlc } = forming.candle;
  assert.equal(color, wickColor);
  assert.deepEqual(ohlc, { time: 300, open: 100, high: 108, low: 98, close: 105 });
  assert.deepEqual(aggregateMinutes(minutes, 300), []);
  assert.equal(formingChartCandle([minutes[0], bar(420, 95)], 300, 480), null);
  assert.equal(formingChartCandle([minutes[0], { ...minutes[1], closed: false }], 300, 427), null);
  assert.equal(formingChartCandle(minutes, 300, 419), null);
  assert.equal(formingChartCandle(minutes, 300, 600), null);
  assert.equal(formingChartCandle(minutes, 60, 427), null);
});

test('GUM candles bind symbol and minute and Pyth prices bind the feed and clock', () => {
  const gumBar = { t: 60000, T: 120000, s: 'ZEC', i: '1m', o: 10, h: 11, l: 10, c: 11 };
  assert.equal(parseGumMinutes('ZEC', [gumBar])[0].close, 11);
  assert.throws(() => parseGumMinutes('HYPE', [gumBar]), /invalid/i);
  const point = { price_feed_id: 6, feed_update_timestamp: 99000000, price: 7500, exponent: -2 };
  assert.deepEqual(parseJlpPrices('SOL', { data: [point] }, 100), [{ time: 99, price: 75 }]);
  assert.throws(() => parseJlpPrices('SOL', { data: [point] }, 130), /stale/i);
  assert.throws(() => gumTerms('ZEC', [], {}, 100), /unavailable/i);
});
