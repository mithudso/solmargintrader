import test from 'node:test';
import assert from 'node:assert/strict';
import { commandBlock, comparisonKey, comparisonStatus, runFromEnvelope, handoffValues, percentText, eligibilityReason } from '../src/ui/desk-model.js';
const context = { schema: 1, id: 'ctx1', run_id: 'run1', asset: 'SOL', interval: '1h', start: '2025-01-01', end: '2025-02-01',
  capital: 1000, fill_delay: 1, data_sha256: 'data1', strategy_revision: 'code1', cpcv: { cpcv_groups: 8, cpcv_k: 2 },
  execution: { fee_bps: 6, min_confidence: 0.8, allow_short: false }, entries: [{ label: 'trend', name: 'ma_crossover', params: { fast: 10 } }] };
const env = { ok: true, command: 'backtest.run', result: { context, rows: [{ label: 'trend', median_return: -0.02 }], cancelled: false } };
test('comparison binds data, code, geometry, timing and costs, independent of strategy membership', () => {
  const other = structuredClone(context); other.id = 'ctx2'; other.entries = [];
  assert.equal(comparisonKey(context), comparisonKey(other));
  for (const [key, value] of [['data_sha256', 'other'], ['strategy_revision', 'code2'], ['capital', 2000], ['fill_delay', 0], ['execution', { fee_bps: 10 }], ['cpcv', { cpcv_groups: 6, cpcv_k: 3 }]]) {
    const changed = { ...other, [key]: value };
    assert.notEqual(comparisonKey(context), comparisonKey(changed), key);
    assert.match(comparisonStatus([{ context }, { context: changed }]), /Incompatible/);
  }
  assert.equal(comparisonKey({}), null);
  assert.match(comparisonStatus([{ context }, { context: other, cancelled: true }]), /Partial/);
});
test('saved run detaches evidence and never mistakes a different command for a sweep', () => {
  const run = runFromEnvelope(env);
  run.context.entries[0].params.fast = 99;
  assert.equal(context.entries[0].params.fast, 10);
  assert.equal(runFromEnvelope({ ...env, command: 'pnl.summary' }), null);
  assert.equal(runFromEnvelope({ ...env, result: { rows: env.result.rows } }), null);
  assert.equal(percentText(-0.02), '-2%');
  assert.equal(percentText(null), 'Unavailable');
});
test('handoff stages the exact snapshot without coins or execution overrides or confirmation', () => {
  const run = runFromEnvelope(env);
  const values = handoffValues(run, run.rows[0]);
  assert.deepEqual(JSON.parse(values.snapshot), context);
  assert.equal(values.source_label, 'trend');
  assert.equal(values.optimize, 'false');
  for (const key of ['confirm', 'skip_confirm', 'coins', 'allow_short', 'min_confidence']) assert.equal(Object.hasOwn(values, key), false);
  assert.equal(handoffValues({ ...run, cancelled: true }, run.rows[0]), null);
  assert.equal(handoffValues(run, { label: 'other' }), null);
});
test('archived mutators remain unavailable even in expert tool forms', () => {
  assert.match(commandBlock({ name: 'liquidity.resume', read_only: false }), /Archived/);
  assert.match(commandBlock({ name: 'liquidity.kill', read_only: false }), /Archived/);
  assert.equal(commandBlock({ name: 'liquidity.status', read_only: true }), null);
  assert.equal(commandBlock({ name: 'jupiter.order_submit', read_only: false }), null);
});

test('strategy evidence explains record floors and never treats expired or future votes as current', () => {
  const p = { min_accuracy: 60, min_resolved: 20 };
  const row = { label: 'A', accuracy: 65, resolved: 40, pred_5m: 'UP', acc_5m: 70, resolved_5m: 30, issued_5m: 100, expires_5m: 200 };
  assert.equal(eligibilityReason(row, p, 150), 'Included');
  assert.match(eligibilityReason({ ...row, accuracy: 58 }, p, 150), /accuracy below 60/);
  assert.match(eligibilityReason({ ...row, resolved: 8 }, p, 150), /below 20 resolved/);
  assert.match(eligibilityReason(row, p, 200), /no current horizon/);
  assert.match(eligibilityReason(row, p, 50), /no current horizon/);
  assert.match(eligibilityReason({ ...row, resolved_5m: 2 }, p, 150), /no current horizon/);
});
