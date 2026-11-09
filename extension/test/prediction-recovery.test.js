import test from 'node:test';
import assert from 'node:assert/strict';
import { predictionRecovery, hasCurrentPrediction } from '../src/ui/prediction-recovery.js';

const row = { label: 'rsi', accuracy: 90, resolved: 40, pred_1m: 'UP', acc_1m: 90,
  resolved_1m: 40, issued_1m: 10, expires_1m: 70 };
const expired = { rows: [row] };
const current = { rows: [{ ...row, issued_1m: 90, expires_1m: 150 }] };
const stopped = { state: 'stopped', running: false, can_start: true };
const running = { state: 'running', running: true, can_start: false };
const env = (result) => ({ ok: true, result });

test('expired votes start recovery once and subsequent polls respect cooldown', async () => {
  const calls = []; let at = 100_000;
  const recovery = predictionRecovery({ clock: () => at, ask: async (name, params) => {
    calls.push([name, params]); return env(name.endsWith('health') ? stopped : running);
  } });
  await recovery.update('SOL', expired);
  await recovery.update('SOL', expired);
  assert.deepEqual(calls.filter(([n]) => n.endsWith('ensure')), [['forwardtest.ensure', { asset: 'SOL', manual: false }]]);
  at += 31_000;
  await recovery.update('SOL', expired);
  assert.equal(calls.filter(([n]) => n.endsWith('ensure')).length, 2);
});

test('current eligible votes never start a producer', async () => {
  const calls = [];
  const recovery = predictionRecovery({ clock: () => 100_000, ask: async (...a) => { calls.push(a); return env(stopped); } });
  await recovery.update('SOL', current);
  assert.deepEqual(calls, []);
  assert.equal(hasCurrentPrediction(current, 100), true);
  assert.equal(hasCurrentPrediction(expired, 100), false);
});

test('fresh forecasts below quality floors do not restart an existing producer', async () => {
  const calls = [];
  const recovery = predictionRecovery({ clock: () => 100_000, ask: async (name) => { calls.push(name); return env(running); } });
  await recovery.update('SOL', { rows: [{ ...current.rows[0], accuracy: 40 }] });
  assert.deepEqual(calls, ['forwardtest.health']);
});

test('explicit Stop remains paused until Start predictions resumes it', async () => {
  const calls = [], states = [];
  const recovery = predictionRecovery({ clock: () => 100_000, changed: (s) => states.push(s), ask: async (name, params) => {
    calls.push([name, params]); return env(name.endsWith('health') ? { ...stopped, state: 'paused', paused: true } : running);
  } });
  await recovery.update('SOL', expired);
  assert.equal(calls.length, 1);
  assert.equal(states.at(-1).can_start, true);
  await recovery.start();
  assert.deepEqual(calls.at(-1), ['forwardtest.ensure', { asset: 'SOL', manual: true }]);
  assert.equal(states.at(-1).running, true);
});

test('overlapping reads share one recovery; obsolete coin results cannot start it', async () => {
  let release; const hold = new Promise((resolve) => { release = resolve; });
  const calls = [], states = [];
  const recovery = predictionRecovery({ clock: () => 100_000, changed: (s) => states.push(s), ask: async (name, params) => {
    calls.push([name, params]);
    if (params.asset === 'SOL') return hold;
    return env(running);
  } });
  const first = recovery.update('SOL', expired);
  const duplicate = recovery.update('SOL', expired);
  assert.equal(first, duplicate);
  await recovery.update('ETH', current);
  release(env(stopped)); await first;
  assert.equal(calls.length, 1);
  assert.equal(states.at(-1).asset, 'ETH');
  assert.equal(states.at(-1).needed, false);
});

test('start failures remain actionable and disposed views suppress late updates', async () => {
  const states = [];
  const recovery = predictionRecovery({ clock: () => 100_000, changed: (s) => states.push(s), ask: async (name) =>
    name.endsWith('health') ? env(stopped) : { ok: false, error: { message: 'fixture spawn failure' } } });
  await recovery.update('SOL', expired);
  assert.match(states.at(-1).message, /fixture spawn failure/);
  assert.equal(states.at(-1).can_start, true);
  const count = states.length; recovery.dispose();
  await recovery.start(); await recovery.update('ETH', expired);
  assert.equal(states.length, count);
});
