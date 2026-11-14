// Account ownership and quota live at the edge; the analysis service receives
// only an opaque job ID and a bounded public-market research request.
export class BacktestJobError extends Error {
  constructor(status, code, message = code) { super(message); this.status = status; this.code = code; }
}
const fail = (status, code, message) => { throw new BacktestJobError(status, code, message); };
const at = () => Math.floor(Date.now() / 1000);
const query = (env, sql, ...args) => env.DB.prepare(sql).bind(...args);
const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
const ACTIVE = new Set(['queued', 'running']);
const terminal = state => state === 'complete' || state === 'failed';
function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(k => [k, stable(value[k])]));
  return value;
}
async function digest(value) {
  const data = new TextEncoder().encode(typeof value === 'string' ? value : JSON.stringify(stable(value)));
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', data))].map(n => n.toString(16).padStart(2, '0')).join('');
}
function publicJob(row, result) {
  return { id: row.id, status: row.state, request: JSON.parse(row.request_json), createdAt: row.created_at,
    updatedAt: row.updated_at, ...(result ? { result } : {}),
    ...(row.state === 'failed' ? { error: row.error_code || 'calculation_failed' } : {}) };
}
function checkOwner(user) {
  if (!user?.id || !user.wallet) fail(401, 'authentication_required');
}
function checkedResult(value, request) {
  return value && typeof value === 'object' && !Array.isArray(value) && value.status === 'complete' &&
    value.coin === request.coin && value.strategy === request.strategy && value.interval === request.interval &&
    value.leverage === request.leverage && value.metrics && typeof value.metrics === 'object' && !Array.isArray(value.metrics);
}
async function snapshot(env, row, operation, services) {
  const payload = { id: row.id, request: JSON.parse(row.request_json) };
  const remote = await services.engine(operation === 'post' ? '/v1/jobs' : `/v1/jobs/${row.id}`, operation === 'post' ? payload : null);
  if (!remote || remote.id !== row.id || remote.requestHash !== row.request_hash ||
      !['queued', 'running', 'complete', 'failed'].includes(remote.status)) fail(502, 'job_receipt_unverified');
  // A completed quota receipt is immutable. A stale or incompatible provider
  // cannot resurrect it or quietly replace its saved input/result identity.
  if (terminal(row.state) && remote.status !== row.state) fail(502, 'job_receipt_unverified');
  if (remote.status === 'complete') {
    if (!checkedResult(remote.result, payload.request)) fail(502, 'job_result_unverified');
    const resultHash = await digest(remote.result);
    if (row.result_hash && row.result_hash !== resultHash) fail(502, 'job_result_unverified');
    await env.DB.batch([
      query(env, "UPDATE hosted_backtest_jobs SET state='complete',result_hash=?,error_code=NULL,updated_at=? WHERE id=? AND user_id=? AND request_hash=? AND state IN ('queued','running','complete') AND (result_hash IS NULL OR result_hash=?)", resultHash, at(), row.id, row.user_id, row.request_hash, resultHash),
      query(env, "UPDATE backtest_usage SET state='complete' WHERE id=? AND user_id=? AND job_id=? AND EXISTS(SELECT 1 FROM hosted_backtest_jobs WHERE id=? AND user_id=? AND state='complete' AND result_hash=?)", row.usage_id, row.user_id, row.id, row.id, row.user_id, resultHash),
    ]);
    const saved = await query(env, 'SELECT * FROM hosted_backtest_jobs WHERE id=? AND user_id=?', row.id, row.user_id).first();
    if (!saved || saved.state !== 'complete' || saved.result_hash !== resultHash) fail(502, 'job_result_unverified');
    return publicJob(saved, remote.result);
  }
  if (remote.status === 'failed') {
    // Return fixed error vocabulary, never a provider exception or path.
    const reason = ['invalid_request', 'cached_history_unavailable', 'history_or_strategy_not_usable', 'calculation_failed', 'input_snapshot_unavailable', 'job_timeout'].includes(remote.error) ? remote.error : 'calculation_failed';
    await env.DB.batch([
      query(env, "UPDATE hosted_backtest_jobs SET state='failed',error_code=?,updated_at=? WHERE id=? AND user_id=? AND request_hash=? AND state IN ('queued','running','failed')", reason, at(), row.id, row.user_id, row.request_hash),
      query(env, "DELETE FROM backtest_usage WHERE id=? AND user_id=? AND job_id=? AND state='reserved' AND EXISTS(SELECT 1 FROM hosted_backtest_jobs WHERE id=? AND user_id=? AND state='failed')", row.usage_id, row.user_id, row.id, row.id, row.user_id),
    ]);
  } else {
    // Never regress running to queued when a delayed POST/GET response arrives.
    await query(env, "UPDATE hosted_backtest_jobs SET state=CASE WHEN state='running' THEN 'running' ELSE ? END,updated_at=? WHERE id=? AND user_id=? AND state IN ('queued','running')", remote.status, at(), row.id, row.user_id).run();
  }
  const saved = await query(env, 'SELECT * FROM hosted_backtest_jobs WHERE id=? AND user_id=?', row.id, row.user_id).first();
  if (!saved) fail(404, 'job_not_found');
  if (terminal(saved.state) && saved.state !== remote.status) fail(502, 'job_receipt_unverified');
  return publicJob(saved);
}
export async function createBacktestJob(env, user, input, services) {
  checkOwner(user);
  if (!input || Object.keys(input).sort().join(',') !== 'idempotencyKey,request' ||
      typeof input.idempotencyKey !== 'string' || !/^[A-Za-z0-9_-]{16,128}$/.test(input.idempotencyKey)) fail(400, 'invalid_job_request');
  const request = services.normalize(input.request);
  const requestJSON = JSON.stringify(stable(request));
  const requestHash = await digest(requestJSON);
  const keyHash = await digest(input.idempotencyKey);
  const sub = await services.entitled(user);
  let row = await query(env, 'SELECT * FROM hosted_backtest_jobs WHERE user_id=? AND idempotency_hash=?', user.id, keyHash).first();
  if (row) {
    if (row.request_hash !== requestHash) fail(409, 'idempotency_conflict');
    return snapshot(env, row, ACTIVE.has(row.state) ? 'post' : 'get', services);
  }
  const id = crypto.randomUUID();
  const reservation = await services.reserve(user, sub, true);
  try {
    await env.DB.batch([
      query(env, "INSERT OR IGNORE INTO hosted_backtest_jobs(id,user_id,usage_id,idempotency_hash,request_hash,request_json,state,created_at,updated_at) SELECT ?,?,?,?,?,?,'queued',?,? WHERE EXISTS(SELECT 1 FROM backtest_usage WHERE id=? AND user_id=? AND state='reserved')", id, user.id, reservation, keyHash, requestHash, requestJSON, at(), at(), reservation, user.id),
      query(env, 'UPDATE backtest_usage SET job_id=? WHERE id=? AND user_id=? AND EXISTS(SELECT 1 FROM hosted_backtest_jobs WHERE id=? AND usage_id=?)', id, reservation, user.id, id, reservation),
      query(env, 'DELETE FROM backtest_usage WHERE id=? AND user_id=? AND NOT EXISTS(SELECT 1 FROM hosted_backtest_jobs WHERE usage_id=?)', reservation, user.id, reservation),
    ]);
  } catch (error) {
    await query(env, 'DELETE FROM backtest_usage WHERE id=? AND user_id=? AND job_id IS NULL', reservation, user.id).run();
    throw error;
  }
  row = await query(env, 'SELECT * FROM hosted_backtest_jobs WHERE user_id=? AND idempotency_hash=?', user.id, keyHash).first();
  if (!row || row.request_hash !== requestHash) fail(409, 'idempotency_conflict');
  // Keep a durable queued row across a transport failure. A replay uses the
  // same upstream ID; it cannot create a second calculation or release credit.
  try { return await snapshot(env, row, 'post', services); }
  catch (error) {
    if (error instanceof BacktestJobError) throw error;
    return { ...publicJob(row), pendingReason: 'runtime_unavailable' };
  }
}
export async function getBacktestJob(env, user, id, services) {
  checkOwner(user);
  if (!UUID.test(id)) fail(400, 'invalid_job_id');
  const row = await query(env, 'SELECT * FROM hosted_backtest_jobs WHERE id=? AND user_id=?', id, user.id).first();
  if (!row) fail(404, 'job_not_found');
  try { return await snapshot(env, row, 'get', services); }
  catch (error) {
    if (error instanceof BacktestJobError) throw error;
    if (row.state === 'complete') fail(503, 'job_result_unavailable');
    return { ...publicJob(row), pendingReason: 'runtime_unavailable' };
  }
}
export async function listBacktestJobs(env, user) {
  checkOwner(user);
  const rows = await query(env, 'SELECT * FROM hosted_backtest_jobs WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT 50', user.id).all();
  return { jobs: rows.results.map(row => publicJob(row)) };
}
export async function reconcileBacktestJobs(env, services) {
  const rows = await query(env, "SELECT * FROM hosted_backtest_jobs WHERE state IN ('queued','running') ORDER BY updated_at,id LIMIT 20").all();
  for (const row of rows.results) {
    try { await snapshot(env, row, 'post', services); }
    catch { await query(env, "UPDATE hosted_backtest_jobs SET updated_at=? WHERE id=? AND state IN ('queued','running')", at(), row.id).run(); }
  }
}
