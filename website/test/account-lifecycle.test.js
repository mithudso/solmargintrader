import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { environment, seedUser, at, ORIGIN, request } from './helpers/d1.js';
import service, { CustomerExecutor } from '../execution/worker.js';
import publicWorker from '../src/worker.js';
import { base64url, digest } from '../execution/common.js';
import { seal } from '../execution/credential-vault.js';
import { AccountLifecycleError, beginAccountDeletion, cleanupAccountExecution, deletionFencePredicate, markExecutionInitialized } from '../src/account-lifecycle.js';

const PORTFOLIO = 'c753d452-5138-45a9-868a-a86c980e30f0';
class Storage {
  constructor() { this.values = new Map(); }
  async get(key) { return structuredClone(this.values.get(key)); }
  async put(key, value) { this.values.set(key, structuredClone(value)); }
  async delete(key) { this.values.delete(key); }
  async deleteAll() { this.values.clear(); }
  async list({ prefix = '', limit = 1000 } = {}) { return new Map([...this.values].filter(([key]) => key.startsWith(prefix)).slice(0, limit).map(([key, value]) => [key, structuredClone(value)])); }
}
function rejects(status, code) {
  return error => error instanceof AccountLifecycleError && error.status === status && error.code === code;
}
function current(env, user) { return env.sqlite.prepare('SELECT * FROM users WHERE id=?').get(user.id); }
async function account() { const env = environment(); const user = await seedUser(env); return { env, user }; }
async function credentials() {
  const pair = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
  const pem = Buffer.from(await crypto.subtle.exportKey('pkcs8', pair.privateKey)).toString('base64');
  return { apiKeyName: 'organizations/test-org/apiKeys/test-key', privateKey: `-----BEGIN PRIVATE KEY-----\n${pem}\n-----END PRIVATE KEY-----\n` };
}
// These tests exercise the real private owner, encryption and SQLite admissions.
// Coinbase permission responses are deterministic; no external provider is called.
async function execution(options = {}) {
  const { env, user } = await account(); const stores = new Map(); const instances = new Map();
  Object.assign(env, { EXECUTOR_TOKEN: base64url(crypto.getRandomValues(new Uint8Array(32))), EXECUTOR_VAULT_KEY: base64url(crypto.getRandomValues(new Uint8Array(32))) });
  env.CUSTOMER_EXECUTORS = { getByName(name) {
    if (!stores.has(name)) stores.set(name, new Storage());
    if (!instances.has(name)) {
      const instance = new CustomerExecutor({ storage: stores.get(name) }, env);
      instance.client = () => ({ permissions: async () => { if (options.permissions) await options.permissions(); return PORTFOLIO; }, accounts: async () => [] });
      instances.set(name, instance);
    }
    return instances.get(name);
  } };
  env.USER_TRADE_EXECUTOR = { fetch: value => service.fetch(value, env) };
  const call = async (path, body) => {
    const response = await service.fetch(new Request(`https://private.internal${path}`, { method: 'POST', headers: { Authorization: `Bearer ${env.EXECUTOR_TOKEN}`, 'Content-Type': 'application/json' }, body: JSON.stringify(body) }), env);
    return { status: response.status, data: await response.json() };
  };
  const owner = { userId: user.id, wallet: user.wallet };
  const secret = await credentials();
  const connect = () => call('/v1/connections', { ...owner, input: { venue: 'coinbase', ...secret, portfolioId: PORTFOLIO, idempotencyKey: 'deletion-test-import' } });
  const cleanup = { configured: true, revokeAll: async () => {
    const result = await call('/v1/connections/revoke-all', owner);
    if (result.status !== 200) throw new Error('private cleanup unavailable');
    return result.data;
  } };
  const storage = async () => stores.get(await digest(user.id));
  return { env, user, call, owner, secret, connect, cleanup, storage };
}
function intent(env, user, state = 'unknown') {
  const id = crypto.randomUUID(); const now = at();
  env.sqlite.prepare(`INSERT INTO agent_trade_intents(id,user_id,wallet,resource,policy_hash,idempotency_key,payload_hash,payload_json,state,reservation_cents,expires_at,created_at,updated_at)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)`).run(id, user.id, user.wallet, `${ORIGIN}/mcp`, 'a'.repeat(64), id, 'b'.repeat(64), '{}', state, 100, now + 60, now, now);
  return id;
}
function billing(env, user, state = 'unknown') {
  const id = crypto.randomUUID(); const now = at();
  env.sqlite.prepare(`INSERT INTO billing_lifecycle_operations(id,user_id,kind,idempotency_key,payload_hash,subscription_id,customer_id,state,stage,created_at,updated_at)
    VALUES (?,?,'plan_change',?,?,?,?,?,'mutation',?,?)`).run(id, user.id, id, 'c'.repeat(64), 'sub_fixture', 'cus_fixture', state, now, now);
  return id;
}
// The HTTP owner adds this exact token predicate to its independently guarded
// final cascade. Repeat all financial guards here to test the last SQLite gate.
async function cascade(env, user, fence) {
  const predicate = deletionFencePredicate(fence);
  return env.DB.prepare(`DELETE FROM users WHERE id=? AND wallet=? AND ${predicate.sql}
    AND (checkout_pending_at IS NULL OR checkout_pending_at<?)
    AND NOT EXISTS(SELECT 1 FROM subscriptions WHERE user_id=users.id AND COALESCE(status,'unknown') NOT IN ('canceled','incomplete_expired'))
    AND NOT EXISTS(SELECT 1 FROM agent_trade_intents WHERE user_id=users.id AND state IN ('submitting','submitted','unknown'))
    AND NOT EXISTS(SELECT 1 FROM billing_lifecycle_operations WHERE user_id=users.id AND state IN ('committing','unknown','pending_payment'))
    RETURNING id`).bind(user.id, user.wallet, ...predicate.args, at() - 2100).first();
}

test('execution intent is persisted before forwarding and cannot reopen a fenced account', async () => {
  const { env, user } = await account(); const now = at();
  assert.deepEqual(await markExecutionInitialized(env, user.user, { now: () => now }), { initialized: true });
  assert.equal(current(env, user).execution_initialized_at, now);
  await markExecutionInitialized(env, user.user, { now: () => now + 5 });
  assert.equal(current(env, user).execution_initialized_at, now);
  const fence = await beginAccountDeletion(env, user.user);
  await assert.rejects(markExecutionInitialized(env, user.user), rejects(409, 'account_deleting'));
  assert.equal(current(env, user).deletion_token, fence.token);
});

test('migration marks preexisting connection owners even when the registry row was revoked', async () => {
  const directory = new URL('../migrations/', import.meta.url);
  const env = environment({ migrations: readdirSync(directory).filter(name => /^\d{4}_.*\.sql$/.test(name) && name < '0009').sort() });
  const user = await seedUser(env); const now = at();
  env.sqlite.prepare(`INSERT INTO customer_execution_connections(id,user_id,wallet,venue,credential_fingerprint,portfolio_id,created_at,verified_at,revoked_at)
    VALUES (?,?,?,'coinbase',?,?,?,?,?)`).run(crypto.randomUUID(), user.id, user.wallet, 'd'.repeat(64), PORTFOLIO, now - 100, now - 100, now);
  env.sqlite.exec(readFileSync(new URL('../migrations/0009_account_lifecycle.sql', import.meta.url), 'utf8'));
  assert.equal(current(env, user).execution_initialized_at, now - 100);
  assert.equal(current(env, user).deletion_token, null);
  const fence = await beginAccountDeletion(env, user.user);
  await assert.rejects(cleanupAccountExecution(env, user.user, fence, { configured: false }), rejects(503, 'execution_cleanup_unavailable'));
});

test('repeated deletion resumes the same server fence and original request time', async () => {
  const { env, user } = await account(); const now = at();
  const first = await beginAccountDeletion(env, user.user, { now: () => now });
  const repeated = await beginAccountDeletion(env, user.user, { now: () => now + 60 });
  assert.deepEqual(repeated, first);
  assert.match(first.token, /^[a-f0-9-]{36}$/);
  assert.equal(first.requestedAt, now);
  await assert.rejects(beginAccountDeletion(env, { ...user.user, wallet: 'foreign-wallet' }), rejects(404, 'account_not_found'));
  await assert.rejects(cleanupAccountExecution(env, user.user, { token: crypto.randomUUID() }), rejects(409, 'deletion_fence_unverified'));
});

test('fresh checkout and every nonterminal or unknown subscription block the atomic deletion fence', async () => {
  const { env, user } = await account(); const now = at();
  env.sqlite.prepare('UPDATE users SET checkout_pending_at=? WHERE id=?').run(now, user.id);
  await assert.rejects(beginAccountDeletion(env, user.user), rejects(409, 'checkout_pending'));
  assert.equal(current(env, user).deletion_token, null);
  env.sqlite.prepare('UPDATE users SET checkout_pending_at=? WHERE id=?').run(now - 2101, user.id);
  for (const state of ['active', 'trialing', 'past_due', 'incomplete', 'paused', 'unpaid', 'unknown']) {
    env.sqlite.prepare('INSERT OR REPLACE INTO subscriptions(user_id,stripe_subscription_id,status,updated_at) VALUES (?,?,?,?)').run(user.id, 'sub_fixture', state, now);
    await assert.rejects(beginAccountDeletion(env, user.user), rejects(409, 'cancel_subscription_first'));
    assert.equal(current(env, user).deletion_token, null, state);
  }
  env.sqlite.prepare("UPDATE subscriptions SET status='canceled' WHERE user_id=?").run(user.id);
  assert.ok((await beginAccountDeletion(env, user.user)).token);
});

test('submitting, submitted and unknown trades preserve the account and its reconciliation records', async () => {
  for (const state of ['submitting', 'submitted', 'unknown']) {
    const { env, user } = await account(); const id = intent(env, user, state);
    await assert.rejects(beginAccountDeletion(env, user.user), rejects(409, 'trade_reconciliation_required'));
    assert.equal(current(env, user).deletion_token, null);
    assert.equal(env.sqlite.prepare('SELECT state FROM agent_trade_intents WHERE id=?').get(id).state, state);
  }
});

test('unresolved billing operations block deletion without discarding provider recovery', async () => {
  for (const state of ['committing', 'unknown', 'pending_payment']) {
    const { env, user } = await account(); const id = billing(env, user, state);
    await assert.rejects(beginAccountDeletion(env, user.user), rejects(409, 'billing_reconciliation_required'));
    assert.equal(current(env, user).deletion_token, null);
    assert.equal(env.sqlite.prepare('SELECT state FROM billing_lifecycle_operations WHERE id=?').get(id).state, state);
  }
});

test('actual private import is erased and verified before the token-bound SQLite cascade', async () => {
  const fixture = await execution(); const { env, user } = fixture;
  await markExecutionInitialized(env, user.user);
  const connected = await fixture.connect(); assert.equal(connected.status, 201);
  const storage = await fixture.storage(); assert.equal((await storage.list({ prefix: 'credential:' })).size, 1);
  const fence = await beginAccountDeletion(env, user.user);
  assert.deepEqual(await cleanupAccountExecution(env, user.user, fence, fixture.cleanup), { credentialsDeleted: true, executionNeverInitialized: false });
  assert.equal(storage.values.size, 0);
  assert.equal(env.sqlite.prepare('SELECT revoked_at FROM customer_execution_connections WHERE user_id=?').get(user.id).revoked_at !== null, true);
  assert.equal((await cascade(env, user, fence)).id, user.id);
  assert.equal(current(env, user), undefined);
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM customer_execution_connections').get().n, 0);
  assert.equal(storage.values.size, 0);
});

test('configured cleanup always crosses the private barrier even with no registry and an interrupted import', async () => {
  const fixture = await execution(); const { env, user } = fixture;
  await markExecutionInitialized(env, user.user);
  const instance = env.CUSTOMER_EXECUTORS.getByName(await digest(user.id));
  const id = crypto.randomUUID();
  await instance.ctx.storage.put(`credential:${id}`, await seal(env, fixture.owner, id, fixture.secret));
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM customer_execution_connections').get().n, 0);
  const fence = await beginAccountDeletion(env, user.user);
  await cleanupAccountExecution(env, user.user, fence, fixture.cleanup);
  assert.equal((await fixture.storage()).values.size, 0);
});

test('unavailable private service retains the fence whenever import intent was recorded', async () => {
  const { env, user } = await account(); await markExecutionInitialized(env, user.user);
  const fence = await beginAccountDeletion(env, user.user);
  await assert.rejects(cleanupAccountExecution(env, user.user, fence, { configured: false }), rejects(503, 'execution_cleanup_unavailable'));
  assert.equal(current(env, user).deletion_token, fence.token);
  assert.deepEqual(await beginAccountDeletion(env, user.user), fence);
  await assert.rejects(markExecutionInitialized(env, user.user), rejects(409, 'account_deleting'));
});

test('an existing registry also requires verified private cleanup when its import marker is absent', async () => {
  const fixture = await execution(); const { env, user } = fixture;
  assert.equal((await fixture.connect()).status, 201);
  assert.equal(current(env, user).execution_initialized_at, null);
  const fence = await beginAccountDeletion(env, user.user);
  await assert.rejects(cleanupAccountExecution(env, user.user, fence, { configured: false }), rejects(503, 'execution_cleanup_unavailable'));
  assert.equal(current(env, user).deletion_token, fence.token);
  assert.equal((await (await fixture.storage()).list({ prefix: 'credential:' })).size, 1);
});

test('a never-initialized account may cascade without an unavailable execution binding', async () => {
  const { env, user } = await account(); const fence = await beginAccountDeletion(env, user.user);
  assert.deepEqual(await cleanupAccountExecution(env, user.user, fence, { configured: false }), { credentialsDeleted: true, executionNeverInitialized: true });
  assert.equal((await cascade(env, user, fence)).id, user.id);
});

test('lost cleanup response retains the same fence and retry safely confirms erasure', async () => {
  const fixture = await execution(); const { env, user } = fixture;
  await markExecutionInitialized(env, user.user); assert.equal((await fixture.connect()).status, 201);
  const fence = await beginAccountDeletion(env, user.user);
  await assert.rejects(cleanupAccountExecution(env, user.user, fence, { configured: true, revokeAll: async () => { await fixture.cleanup.revokeAll(); throw new Error('response lost'); } }), rejects(503, 'execution_cleanup_unconfirmed'));
  assert.equal((await fixture.storage()).values.size, 0);
  assert.equal(current(env, user).deletion_token, fence.token);
  assert.equal((await fixture.connect()).data.error, 'account_deleting');
  const resumed = await beginAccountDeletion(env, user.user); assert.deepEqual(resumed, fence);
  await cleanupAccountExecution(env, user.user, resumed, fixture.cleanup);
  assert.equal((await fixture.storage()).values.size, 0);
  assert.equal((await cascade(env, user, resumed)).id, user.id);
});

test('a pending order discovered by private cleanup retains credentials and returns 409', async () => {
  const fixture = await execution(); const { env, user } = fixture;
  await markExecutionInitialized(env, user.user); assert.equal((await fixture.connect()).status, 201);
  const fence = await beginAccountDeletion(env, user.user); const id = intent(env, user);
  await assert.rejects(cleanupAccountExecution(env, user.user, fence, fixture.cleanup), rejects(409, 'trade_reconciliation_required'));
  assert.equal((await (await fixture.storage()).list({ prefix: 'credential:' })).size, 1);
  assert.equal(current(env, user).deletion_token, fence.token);
  assert.equal(env.sqlite.prepare('SELECT state FROM agent_trade_intents WHERE id=?').get(id).state, 'unknown');
  assert.equal(await cascade(env, user, fence), null);
});

test('an import already awaiting its provider cannot persist a credential after deletion is fenced', async () => {
  let release; let entered;
  const started = new Promise(resolve => { entered = resolve; });
  const waiting = new Promise(resolve => { release = resolve; });
  const fixture = await execution({ permissions: async () => { entered(); await waiting; } }); const { env, user } = fixture;
  await markExecutionInitialized(env, user.user);
  const importing = fixture.connect(); await started;
  const fence = await beginAccountDeletion(env, user.user);
  const cleaning = cleanupAccountExecution(env, user.user, fence, fixture.cleanup);
  release();
  const rejected = await importing; assert.equal(rejected.status, 409); assert.equal(rejected.data.error, 'account_deleting');
  await cleaning;
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM customer_execution_connections').get().n, 0);
  assert.equal((await fixture.storage()).values.size, 0);
  assert.equal((await fixture.connect()).data.error, 'account_deleting');
  assert.equal((await fixture.storage()).values.size, 0);
});

test('cleanup rejects unknown or malformed success and never resets the durable fence', async () => {
  const { env, user } = await account(); const fence = await beginAccountDeletion(env, user.user);
  for (const reply of [undefined, {}, { revoked: true }, { revoked: true, credentialsDeleted: false, pendingReconciliation: false }, { revoked: true, credentialsDeleted: true, pendingReconciliation: false, unknown: true }]) {
    await assert.rejects(cleanupAccountExecution(env, user.user, fence, { configured: true, revokeAll: async () => reply }), rejects(503, 'execution_cleanup_unconfirmed'));
    assert.equal(current(env, user).deletion_token, fence.token);
  }
  const second = await seedUser(env);
  await assert.rejects(cleanupAccountExecution(env, second.user, fence, { configured: true, revokeAll: async () => assert.fail('must not reach another owner') }), rejects(409, 'deletion_fence_unverified'));
});

test('the final SQLite cascade rechecks the token and newly appeared financial blockers', async () => {
  const { env, user } = await account(); const fence = await beginAccountDeletion(env, user.user);
  assert.equal(await cascade(env, user, { token: crypto.randomUUID() }), null);
  const id = billing(env, user, 'unknown');
  assert.equal(await cascade(env, user, fence), null);
  assert.equal(current(env, user).deletion_token, fence.token);
  env.sqlite.prepare("UPDATE billing_lifecycle_operations SET state='failed' WHERE id=?").run(id);
  assert.equal((await cascade(env, user, fence)).id, user.id);
});

test('public DELETE crosses the private cleanup barrier for registry-empty encrypted import residue', async () => {
  const f = await execution(); await markExecutionInitialized(f.env, f.user.user);
  const instance = f.env.CUSTOMER_EXECUTORS.getByName(await digest(f.user.id)); const id = crypto.randomUUID();
  await instance.ctx.storage.put(`credential:${id}`, await seal(f.env, f.owner, id, f.secret));
  assert.equal(f.env.sqlite.prepare('SELECT COUNT(*) AS n FROM customer_execution_connections').get().n, 0);
  const response = await publicWorker.fetch(request('/api/me', { method: 'DELETE', cookie: f.user.cookie }), f.env);
  assert.equal(response.status, 200); assert.deepEqual(await response.json(), { deleted: true });
  assert.equal((await f.storage()).values.size, 0);
  assert.equal(current(f.env, f.user), undefined);
  assert.equal(f.env.sqlite.prepare('SELECT COUNT(*) AS n FROM sessions').get().n, 0);
});

test('public DELETE retains account authorization after a lost cleanup reply and resumes the identical fence', async () => {
  const f = await execution(); const forwarding = f.env.USER_TRADE_EXECUTOR.fetch;
  let markedBeforeForward = false;
  f.env.USER_TRADE_EXECUTOR.fetch = value => {
    if (new URL(value.url).pathname === '/v1/connections') {
      markedBeforeForward = current(f.env, f.user).execution_initialized_at !== null;
      assert.equal(f.env.sqlite.prepare('SELECT COUNT(*) AS n FROM customer_execution_connections').get().n, 0);
    }
    return forwarding(value);
  };
  const imported = await publicWorker.fetch(request('/api/connections', { method: 'POST', cookie: f.user.cookie,
    body: { venue: 'coinbase', ...f.secret, portfolioId: PORTFOLIO, idempotencyKey: 'public-import-before-deletion' } }), f.env);
  assert.equal(imported.status, 201); assert.equal(markedBeforeForward, true);
  const before = current(f.env, f.user); const sessions = f.env.sqlite.prepare('SELECT * FROM sessions').all();
  const fetchPrivate = f.env.USER_TRADE_EXECUTOR.fetch; const observed = []; let loseReply = true;
  f.env.USER_TRADE_EXECUTOR.fetch = async value => {
    if (new URL(value.url).pathname === '/v1/connections/revoke-all') {
      observed.push(current(f.env, f.user).deletion_token);
      const result = await fetchPrivate(value);
      if (loseReply) { loseReply = false; throw Error('cleanup reply lost'); }
      return result;
    }
    return fetchPrivate(value);
  };
  const first = await publicWorker.fetch(request('/api/me', { method: 'DELETE', cookie: f.user.cookie }), f.env);
  assert.equal(first.status, 503); assert.equal((await first.json()).error, 'execution_cleanup_unconfirmed');
  const saved = current(f.env, f.user);
  assert.match(saved.deletion_token, /^[a-f0-9-]{36}$/); assert.ok(saved.deletion_requested_at >= before.created_at);
  assert.deepEqual({ ...saved, deletion_token: null, deletion_requested_at: null }, { ...before });
  assert.deepEqual(f.env.sqlite.prepare('SELECT * FROM sessions').all(), sessions);
  assert.equal((await f.storage()).values.size, 0);
  const blocked = await publicWorker.fetch(request('/api/connections', { method: 'POST', cookie: f.user.cookie, body: {} }), f.env);
  assert.equal(blocked.status, 409); assert.equal((await blocked.json()).error, 'account_deleting');
  const second = await publicWorker.fetch(request('/api/me', { method: 'DELETE', cookie: f.user.cookie }), f.env);
  assert.equal(second.status, 200); assert.deepEqual(await second.json(), { deleted: true });
  assert.deepEqual(observed, [saved.deletion_token, saved.deletion_token]);
  assert.equal((await f.storage()).values.size, 0); assert.equal(current(f.env, f.user), undefined);
});
