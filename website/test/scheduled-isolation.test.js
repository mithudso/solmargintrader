import assert from 'node:assert/strict';
import test from 'node:test';
import worker from '../src/worker.js';

test('a failed backtest query does not skip managed-bot selection', async () => {
  const seen = [];
  const forbiddenFetch = async () => { throw new Error('unexpected provider request'); };
  const env = {
    ENGINE_TOKEN: 'fixture', ENGINE_SERVICE: { fetch: forbiddenFetch },
    LIVE_EXECUTION_ENABLED: 'true', USER_TRADE_EXECUTOR: { fetch: forbiddenFetch },
    DB: { prepare(sql) { seen.push(sql); return { bind() { return this; }, async all() {
      if (sql.includes('hosted_backtest_jobs')) throw new Error('fixture backtest failure');
      return { results: [] };
    } }; } },
  };
  await assert.rejects(worker.scheduled({ cron: '* * * * *' }, env));
  assert.ok(seen.some(sql => sql.includes('hosted_backtest_jobs')));
  assert.ok(seen.some(sql => sql.includes('managed_bots')));
});

test('independent scheduled failures are both retained for the caller', async () => {
  const env = {
    ENGINE_TOKEN: 'fixture', ENGINE_SERVICE: { fetch: async () => { throw new Error('unexpected fetch'); } },
    LIVE_EXECUTION_ENABLED: 'true', USER_TRADE_EXECUTOR: { fetch: async () => { throw new Error('unexpected fetch'); } },
    DB: { prepare(sql) { return { bind() { return this; }, async all() {
      throw new Error(sql.includes('hosted_backtest_jobs') ? 'backtest failed' : 'managed failed');
    } }; } },
  };
  await assert.rejects(worker.scheduled({ cron: '* * * * *' }, env), error => {
    assert.ok(error instanceof AggregateError);
    assert.deepEqual(error.errors.map(item => item.message), ['backtest failed', 'managed failed']);
    return true;
  });
});
