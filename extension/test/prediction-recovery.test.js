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

test('CDO-4833a8eec6 manual start survives an overlapping automatic health read', async () => {
  let release, held = false; const calls = [];
  const gate = new Promise(r => { release = r; });
  const recovery = predictionRecovery({ clock: () => 100000, ask: async (name, params) => {
    calls.push([name, params]);
    return env(name.endsWith('health') ? held ? await gate : { ...stopped, paused: true } : running);
  } });
  await recovery.update('SOL', expired);
  held = true; const automatic = recovery.update('SOL', expired), manual = recovery.start();
  release({ ...stopped, paused: true }); await Promise.all([automatic, manual]);
  assert.deepEqual(calls.filter(([name]) => name.endsWith('ensure')), [['forwardtest.ensure', { asset: 'SOL', manual: true }]]);
});

test('CDO-423a330b4b returning asset gets its own current-generation health', async () => {
  let release; const calls = [], states = [];
  const gate = new Promise(r => { release = r; });
  const recovery = predictionRecovery({ clock: () => 100000, changed: value => states.push(value), ask: async (name, params) => {
    calls.push([name, params]);
    return env(name.endsWith('health') ? calls.length === 1 ? await gate : stopped : running);
  } });
  const old = recovery.update('SOL', expired);
  await recovery.update('ETH', current);
  const returned = recovery.update('SOL', expired);
  release(stopped); await Promise.all([old, returned]);
  assert.equal(calls.filter(([name]) => name.endsWith('health')).length, 2);
  assert.equal(states.at(-1).asset, 'SOL'); assert.equal(states.at(-1).running, true);
});

test('CDO-0033742db8 disposal suppresses an already-entered ensure completion', async () => {
  let release, entered; const states = [];
  const gate = new Promise(r => { release = r; }), started = new Promise(r => { entered = r; });
  const recovery = predictionRecovery({ clock: () => 100000, changed: s => states.push(s), ask: async name => {
    if (name.endsWith('ensure')) { entered(); return gate; }
    return env(stopped);
  } });
  const update = recovery.update('SOL', expired); await started;
  recovery.dispose(); const count = states.length;
  release(env(running)); await update; assert.equal(states.length, count);
});
