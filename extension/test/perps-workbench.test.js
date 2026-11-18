import assert from 'node:assert/strict';
import test from 'node:test';
import { beginPaper, closePaper, managePaper, observePaper, stopPaperEntries } from '../src/perps/workbench.js';

const terms = {
  venue: 'GUM', max: 50, baseBps: 3.5, maintenanceBps: 100, liquidationBps: 75, carryBps: 0,
  firstTierCap: 100000, maxOrder: 10000, minOrder: 1, maxQty: 500, stepSize: 0.001,
};
const settings = { sizing: 'notional', amount: 250, leverage: 25, tp: 0, sl: 0.8, slippageBps: 2, additiveBps: 0, networkUsd: 0.01 };
const rows = Array.from({ length: 100 }, (_, index) => ({
  time: index * 60, open: 100, high: 101, low: 99, close: 100, closed: true,
}));
const feed = (time, price, history = rows) => {
  const mark = { time, price };
  return { history, snapshot: { mark, points: [mark], long: terms, short: terms }, issue: '' };
};
const spec = (overrides = {}) => ({
  asset: 'ZEC', settings, direction: -1, strategy: 'zec-volty-10-1.5', step: 300,
  now: 6000, makeId: () => 'position-1', ...overrides,
});

test('the frozen Volty preset admits a short entry and emits a trainable managed take-profit settlement', () => {
  let result = beginPaper(null, feed(6000, 100), spec());
  assert.equal(result.account.running, true);
  assert.equal(stopPaperEntries(result.account, 'older-run'), null);
  assert.equal(stopPaperEntries(result.account, result.account.runId).account.running, false);
  result = observePaper(result.account, feed(6005, 96), 6005, () => 'position-1');
  assert.equal(result.account.broker.position.id, 'position-1');
  assert.equal(result.account.broker.position.direction, -1);
  result = managePaper(result.account, 'position-1', { tp: 1, sl: 0.8, armedAt: 6006, signals: null });
  result = observePaper(result.account, feed(6010, 94), 6010, () => 'unexpected');
  assert.equal(result.account.broker.position, null);
  assert.equal(result.account.exits, 1);
  assert.equal(result.trades[0].id, 'position-1');
  assert.equal(result.trades[0].reason, 'take');
  assert.equal(result.trades[0].strategy, 'zec-volty-10-1.5');
  assert.equal(result.trades[0].step, 300);
  assert.equal(result.trades[0].features.length, 22);
  assert.ok(result.trades[0].units > 0 && result.trades[0].size > 0);
  assert.ok(result.trades[0].pnl > 0);
  assert.equal(observePaper(result.account, feed(6010, 94), 6010, () => 'unexpected'), null);
});

test('entry refuses incomplete learning history and directions absent in the chosen strategy', () => {
  assert.throws(() => beginPaper(null, feed(6000, 100, rows.slice(25)), spec()), /contiguous closed/);
  assert.throws(() => beginPaper(null, feed(6000, 100), spec({ strategy: 'zec-mean' })), /only supplies long/);
  assert.throws(() => beginPaper(null, feed(6000, 100), spec({ strategy: null, direction: 0 })), /single direction/);
});

test('a stale mark or stale position identity cannot close a restored account', () => {
  const { account } = beginPaper(null, feed(6000, 100), spec({ strategy: null, direction: 1 }));
  assert.throws(() => closePaper(account, feed(6000, 101), 'position-1', 6030), /fresh market mark/);
  assert.throws(() => closePaper(account, feed(6005, 101), 'different-position', 6005), /position has changed/);
  const result = closePaper(account, feed(6005, 101), 'position-1', 6005);
  assert.equal(result.trades[0].reason, 'manual');
  assert.equal(result.account.broker.position, null);

  const managed = managePaper(account, 'position-1', { tp: 0, sl: 1, armedAt: 6004 });
  const buffered = feed(6012, 100);
  buffered.snapshot.points.unshift({ time: 6007, price: 98 });
  const stopped = closePaper(managed.account, buffered, 'position-1', 6012);
  assert.equal(stopped.trades[0].reason, 'stop');
  assert.equal(stopped.trades[0].time, 6007);
});
