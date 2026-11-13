import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';
import { environment, seedUser, request, at } from './helpers/d1.js';

const input = () => ({ idempotencyKey: crypto.randomUUID(), request: { coin: 'SOL', strategy: 'rsi', interval: '1h', capital: 10000, leverage: 1 } });
async function hash(value) { return Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(value)))).toString('hex'); }
async function fixture() {
  const env = environment(); const owner = await seedUser(env); const other = await seedUser(env);
  for (const user of [owner, other]) env.sqlite.prepare("INSERT INTO subscriptions(user_id,stripe_subscription_id,status,period_end,updated_at,plan_id) VALUES (?,?,'active',?,?,'starter')").run(user.id, `sub_${user.id.replaceAll('-', '')}`, at() + 86400, at());
  const jobs = new Map(); const calls = []; let loseResponse = false; let wrongReceipt = false; let malformedResult = false;
  env.ENGINE_TOKEN = 'fixture-analysis-token-with-at-least32bytes';
  env.ENGINE_SERVICE = { async fetch(req) {
    calls.push({ method: req.method, url: req.url });
    assert.equal(req.headers.get('Authorization'), `Bearer ${env.ENGINE_TOKEN}`);
    const path = new URL(req.url).pathname; let row;
    if (req.method === 'POST') {
      const body = await req.json(); assert.deepEqual(Object.keys(body).sort(), ['id', 'request']);
      const requestHash = await hash(body.request);
      if (!jobs.has(body.id)) jobs.set(body.id, { id: body.id, requestHash, request: body.request, status: 'queued', createdAt: at(), updatedAt: at() });
      row = jobs.get(body.id); assert.equal(row.requestHash, requestHash);
      if (loseResponse) { loseResponse = false; throw new DOMException('fixture transport closed after acceptance', 'TimeoutError'); }
    } else row = jobs.get(path.split('/').at(-1));
    if (!row) return Response.json({ error: 'job_not_found' }, { status: 404 });
    const result = row.status === 'complete' ? { status: 'complete', ...row.request, metrics: { netReturnPct: 1 }, equity: [] } : undefined;
    if (malformedResult && result) result.coin = 'ETH';
    return Response.json({ id: wrongReceipt ? crypto.randomUUID() : row.id, requestHash: row.requestHash, status: row.status, createdAt: row.createdAt, updatedAt: row.updatedAt, ...(result ? { result } : {}), ...(row.error ? { error: row.error } : {}) });
  } };
  const call = async (user, path, options = {}) => {
    const response = await worker.fetch(request(path, { cookie: user.cookie, ...options }), env);
    return { response, data: await response.json() };
  };
  return { env, owner, other, jobs, calls, call, lose: () => { loseResponse = true; }, wrong: () => { wrongReceipt = true; }, malformed: () => { malformedResult = true; } };
}
test('durable jobs are tenant-owned, deduplicate requests and retain one quota slot', async () => {
  const f = await fixture(); const body = input();
  const first = await f.call(f.owner, '/api/backtest-jobs', { method: 'POST', body });
  assert.equal(first.response.status, 202); assert.equal(first.data.status, 'queued');
  const again = await f.call(f.owner, '/api/backtest-jobs', { method: 'POST', body });
  assert.equal(again.data.id, first.data.id); assert.equal(f.jobs.size, 1);
  assert.equal(f.env.sqlite.prepare('SELECT COUNT(*) AS n FROM backtest_usage').get().n, 1);
  assert.equal((await f.call(f.other, `/api/backtest-jobs/${first.data.id}`)).response.status, 404);
  assert.deepEqual((await f.call(f.other, '/api/backtest-jobs')).data, { jobs: [] });
  const conflict = await f.call(f.owner, '/api/backtest-jobs', { method: 'POST', body: { ...body, request: { ...body.request, capital: 20000 } } });
  assert.equal(conflict.response.status, 409); assert.equal(conflict.data.error, 'idempotency_conflict');
  const busy = await f.call(f.owner, '/api/backtest-jobs', { method: 'POST', body: input() });
  assert.equal(busy.response.status, 429); assert.equal(busy.data.error, 'backtest_in_progress');
});
test('lost submission response and daily cleanup preserve the durable reservation and allow safe replay', async () => {
  const f = await fixture(); f.lose(); const body = input();
  const started = await f.call(f.owner, '/api/backtest-jobs', { method: 'POST', body });
  assert.equal(started.response.status, 202); assert.equal(started.data.pendingReason, 'runtime_unavailable');
  assert.equal(f.jobs.size, 1);
  f.env.sqlite.prepare("UPDATE backtest_usage SET day='2020-01-01',created_at=?").run(at() - 200000);
  await worker.scheduled({}, f.env);
  assert.equal(f.env.sqlite.prepare("SELECT COUNT(*) AS n FROM backtest_usage WHERE state='reserved'").get().n, 1);
  assert.equal((await f.call(f.owner, '/api/backtest-jobs', { method: 'POST', body })).data.id, started.data.id);
  assert.equal(f.jobs.size, 1);
  f.jobs.get(started.data.id).status = 'complete';
  const done = await f.call(f.owner, `/api/backtest-jobs/${started.data.id}`);
  assert.equal(done.data.status, 'complete'); assert.equal(done.data.result.coin, 'SOL');
  assert.equal(f.env.sqlite.prepare("SELECT COUNT(*) AS n FROM backtest_usage WHERE state='complete'").get().n, 1);
});
test('only a verified terminal result consumes or releases quota', async () => {
  const f = await fixture(); const first = await f.call(f.owner, '/api/backtest-jobs', { method: 'POST', body: input() });
  f.jobs.get(first.data.id).status = 'running';
  assert.equal((await f.call(f.owner, `/api/backtest-jobs/${first.data.id}`)).data.status, 'running');
  f.jobs.get(first.data.id).status = 'complete'; f.malformed();
  const bad = await f.call(f.owner, `/api/backtest-jobs/${first.data.id}`);
  assert.equal(bad.response.status, 502); assert.equal(bad.data.error, 'job_result_unverified');
  assert.equal(f.env.sqlite.prepare('SELECT state FROM backtest_usage').get().state, 'reserved');
  const g = await fixture(); const second = await g.call(g.owner, '/api/backtest-jobs', { method: 'POST', body: input() });
  Object.assign(g.jobs.get(second.data.id), { status: 'failed', error: '/private/provider/secret traceback' });
  const failed = await g.call(g.owner, `/api/backtest-jobs/${second.data.id}`);
  assert.equal(failed.data.status, 'failed'); assert.equal(failed.data.error, 'calculation_failed');
  assert.equal(g.env.sqlite.prepare('SELECT COUNT(*) AS n FROM backtest_usage').get().n, 0);
  assert.equal(JSON.stringify(failed.data).includes('/private'), false);
});
test('minute reconciliation consumes completed work and account reads survive entitlement expiry', async () => {
  const f = await fixture(); const started = await f.call(f.owner, '/api/backtest-jobs', { method: 'POST', body: input() });
  f.env.sqlite.prepare("UPDATE subscriptions SET status='canceled' WHERE user_id=?").run(f.owner.id);
  f.jobs.get(started.data.id).status = 'complete';
  await worker.scheduled({ cron: '* * * * *' }, f.env);
  const done = await f.call(f.owner, `/api/backtest-jobs/${started.data.id}`);
  assert.equal(done.response.status, 200); assert.equal(done.data.status, 'complete');
  assert.equal(f.env.sqlite.prepare('SELECT state FROM backtest_usage').get().state, 'complete');
  const refused = await f.call(f.owner, '/api/backtest-jobs', { method: 'POST', body: input() });
  assert.equal(refused.response.status, 402); assert.equal(refused.data.error, 'subscription_required');
});
test('concurrent duplicate submission cannot reserve or create two jobs', async () => {
  const f = await fixture(); const body = input();
  const results = await Promise.all([f.call(f.owner, '/api/backtest-jobs', { method: 'POST', body }), f.call(f.owner, '/api/backtest-jobs', { method: 'POST', body })]);
  assert.ok(results.some(r => r.response.status === 202));
  assert.ok(results.every(r => [202, 429].includes(r.response.status)));
  assert.equal(f.jobs.size, 1);
  assert.equal(f.env.sqlite.prepare('SELECT COUNT(*) AS n FROM hosted_backtest_jobs').get().n, 1);
  assert.equal(f.env.sqlite.prepare('SELECT COUNT(*) AS n FROM backtest_usage').get().n, 1);
  assert.equal((await f.call(f.owner, '/api/backtest-jobs', { method: 'POST', body })).data.id, [...f.jobs.keys()][0]);
});
test('a completed quota receipt cannot regress when the runtime returns stale state', async () => {
  const f = await fixture(); const started = await f.call(f.owner, '/api/backtest-jobs', { method: 'POST', body: input() });
  f.jobs.get(started.data.id).status = 'complete';
  assert.equal((await f.call(f.owner, `/api/backtest-jobs/${started.data.id}`)).data.status, 'complete');
  f.jobs.get(started.data.id).status = 'queued';
  const stale = await f.call(f.owner, `/api/backtest-jobs/${started.data.id}`);
  assert.equal(stale.response.status, 502); assert.equal(stale.data.error, 'job_receipt_unverified');
  assert.equal(f.env.sqlite.prepare('SELECT state FROM backtest_usage').get().state, 'complete');
  assert.equal(f.env.sqlite.prepare('SELECT state FROM hosted_backtest_jobs').get().state, 'complete');
});
test('wrong runtime receipts and untrusted request fields do not mutate quota or ownership', async () => {
  const f = await fixture(); const body = input(); body.request.wallet = f.other.wallet;
  assert.equal((await f.call(f.owner, '/api/backtest-jobs', { method: 'POST', body })).response.status, 400);
  assert.equal(f.env.sqlite.prepare('SELECT COUNT(*) AS n FROM backtest_usage').get().n, 0);
  f.wrong(); const started = await f.call(f.owner, '/api/backtest-jobs', { method: 'POST', body: input() });
  assert.equal(started.response.status, 502); assert.equal(started.data.error, 'job_receipt_unverified');
  assert.equal(f.env.sqlite.prepare('SELECT state FROM backtest_usage').get().state, 'reserved');
});
