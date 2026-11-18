import test from 'node:test';
import assert from 'node:assert/strict';
import { PaperBroker } from '../src/perps/replay.js';
import { closedPerpsBars, evaluateExitSignals, validateExitSignals } from '../src/perps/managed-exits.js';
import { jlpTerms } from '../src/perps/market.js';

const sol = jlpTerms('SOL', { openFeePercent: '0.06', maxPriceImpactFeePercent: '0.44', longBorrowRatePercent: '0.0015' }, 1);
const risk = { sizing: 'collateral', amount: 25, leverage: 10, tp: 0, sl: 0, slippageBps: 0, additiveBps: 0, networkUsd: 0 };
const bar = (time, open, low = open, high = open) => ({ time, open, low, high, close: open, closed: true });
const markets = { long: sol, short: sol };
const manual = { ...markets, decisionKind: 'manual' };
const observeVolty = (broker, time, mark) =>
  broker.observe(bar(time, mark), { ...markets, decisionKind: 'volty', decision: { upper: 102, lower: 98 } });
const history = Array.from({ length: 95 }, (_, i) => bar(i * 60, i < 80 ? 110 - i * 0.1 : 114));
const crossAt = 81 * 60;
const rsiUp = { indicator: 'rsi', cross: 'up', level: 60 };
const macdUp = { indicator: 'macd', cross: 'up' };
const rules = validateExitSignals({ step: 60, mode: 'all', rules: [macdUp, rsiUp] });

function tracked(direction = 1, time = 0) {
  const entryFeatures = [0.2, 0.3];
  const broker = new PaperBroker(risk, { onEntry: () => ({ id: 'book-1', entryFeatures }) });
  broker.open(time, 100, direction, sol, 1);
  return broker;
}

test('Volty direction admission preserves opposite exits and the one net position', () => {
  for (const [policy, first, second] of [[1, 103, 97], [-1, 97, 103], [0, 103, 97]]) {
    const broker = new PaperBroker(risk, { entryDirection: policy });
    observeVolty(broker, 60, first);
    assert.equal(broker.position?.direction, first > 100 ? 1 : -1);
    observeVolty(broker, 120, second);
    assert.equal(broker.ledger[0].reason, 'signal');
    assert.equal(broker.position?.direction ?? null, policy === 0 ? -1 : null);
  }
});

test('short-only strategy settings never reinterpret a legacy long admission as a short', () => {
  const broker = new PaperBroker(risk, { entryDirection: -1 });
  broker.observe(bar(60, 100), { ...markets, decisionKind: 'mean', decision: { weight: 1 } });
  assert.equal(broker.position, null);
  assert.equal(broker.ledger.length, 0);
});

test('checkpoint preserves the open position, carry, identity and policy without including fills', () => {
  const features = [0.1, 0.3];
  const broker = new PaperBroker(risk, { entryDirection: -1, onEntry: () => ({ id: 'unique-entry', entryFeatures: features }) });
  broker.open(3500, 100, -1, sol, 1);
  features[0] = 42;
  broker.managePosition('unique-entry', { tp: 6, sl: 2, armedAt: 3550, signals: rules });
  broker.observe(bar(3600, 100), manual);
  broker.signal = { upper: Infinity, lower: 98 };
  const state = broker.checkpoint();
  assert.ok(state.position.carry > 0);
  assert.equal(state.position.take, 94);
  assert.equal(state.position.stop, 102);
  assert.equal('ledger' in state, false);
  const restored = PaperBroker.fromCheckpoint(state);
  assert.deepEqual(restored.checkpoint(), state);
  assert.throws(() => { restored.position.id = 'replacement'; }, TypeError);
  assert.throws(() => { restored.position.entryFeatures[0] = 0; }, TypeError);
  restored.close(3610, { reason: 'manual', price: 99 });
  assert.equal(restored.ledger[0].id, 'unique-entry');
  assert.deepEqual(restored.ledger[0].features, [0.1, 0.3]);
  assert.equal(restored.ledger[0].carry, state.position.carry);
});

test('a stale ID or invalid managed rule cannot modify an open position', () => {
  const broker = tracked(-1);
  assert.throws(() => broker.managePosition('old-id', { tp: 1, sl: 1, armedAt: 10 }), /no longer open/);
  assert.throws(() => broker.managePosition('book-1', { tp: -1, sl: 1, armedAt: 10 }), /valid price/);
  assert.throws(() => broker.managePosition('book-1', { tp: 1, sl: 1, armedAt: -1 }), /current observation/);
  assert.throws(() => broker.managePosition('book-1', {
    tp: 1, sl: 1, armedAt: 10, signals: { ...rules, rules: [macdUp, macdUp] },
  }), /duplicate/i);
  assert.equal(broker.position.stop, null);
  assert.equal(broker.position.take, null);
  broker.managePosition('book-1', { tp: 1, sl: 1.5, armedAt: 10 });
  broker.observe(bar(9, 102), manual);
  assert.ok(broker.position, 'Late observations must not trigger a bracket edited later.');
  assert.throws(() => broker.managePosition('book-1', { tp: 0, sl: 5, armedAt: 12 }), /pending exit edit/);
  broker.observe(bar(11, 102), manual);
  assert.equal(broker.ledger[0].reason, 'stop');
});

test('managed MACD and RSI edges use the same closed candle without reading future bars', () => {
  const mixed = validateExitSignals({ step: 60, mode: 'all', rules: [macdUp, { ...rsiUp, cross: 'down' }] });
  assert.equal(evaluateExitSignals(history, rules, crossAt - 1).matched, false);
  assert.equal(evaluateExitSignals(history, rules, crossAt).matched, true);
  assert.equal(evaluateExitSignals(history, mixed, crossAt).matched, false);
  assert.equal(evaluateExitSignals(history, { ...mixed, mode: 'any' }, crossAt).matched, true);
  assert.equal(evaluateExitSignals(history, rules, crossAt + 60).matched, false);
  assert.deepEqual(evaluateExitSignals(history.filter((_, i) => i !== 79), rules, crossAt), { available: false, matched: false });
  assert.deepEqual(closedPerpsBars(history.map((row, i) => i === 80 ? { ...row, closed: false } : row), 60, crossAt), []);
});

test('signals require an edge strictly after arming and cannot outrank observed liquidation', () => {
  const hold = tracked(1, crossAt - 90);
  hold.managePosition('book-1', { tp: 0, sl: 0, armedAt: crossAt - 10, signals: rules });
  hold.observe(bar(crossAt - 1, 100), { ...manual, exitMinutes: history });
  assert.ok(hold.position);
  hold.observe(bar(crossAt, 100), { ...manual, exitMinutes: history });
  assert.equal(hold.ledger[0].reason, 'managed-signal');

  const armedAtCross = tracked(1, crossAt - 90);
  armedAtCross.managePosition('book-1', { tp: 0, sl: 0, armedAt: crossAt, signals: rules });
  armedAtCross.observe(bar(crossAt, 100), { ...manual, exitMinutes: history });
  armedAtCross.observe(bar(crossAt + 60, 100), { ...manual, exitMinutes: history });
  assert.ok(armedAtCross.position);

  const adverse = tracked(1, crossAt - 90);
  adverse.managePosition('book-1', { tp: 0, sl: 0, armedAt: crossAt - 10, signals: rules });
  adverse.observe(bar(crossAt, 100, 89), { ...manual, exitMinutes: history });
  assert.equal(adverse.ledger[0].reason, 'liquidation');
});
