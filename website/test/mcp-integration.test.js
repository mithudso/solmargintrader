import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';
import { environment, request, keypair, ORIGIN, at } from './helpers/d1.js';

const encoder = new TextEncoder();
const digest = async value => Buffer.from(await crypto.subtle.digest('SHA-256', encoder.encode(value))).toString('base64url');
async function call(env, path, options) {
  const response = await worker.fetch(request(path, options), env);
  const text = await response.text();
  return { response, data: response.headers.get('Content-Type')?.includes('application/json') && text ? JSON.parse(text) : text };
}
async function login(env) {
  const pair = await keypair();
  const challenge = await call(env, '/api/auth/challenge', { method: 'POST', body: { wallet: pair.wallet } });
  assert.equal(challenge.response.status, 200);
  const signature = Buffer.from(await crypto.subtle.sign('Ed25519', pair.keys.privateKey, encoder.encode(challenge.data.message))).toString('base64');
  const verified = await call(env, '/api/auth/verify', { method: 'POST', body: { id: challenge.data.id, signature } });
  assert.equal(verified.response.status, 200);
  return { ...pair, ...verified.data, cookie: verified.response.headers.get('Set-Cookie').split(';')[0] };
}
async function authorize(env, user, scope = 'status:read trade:prepare trade:submit') {
  const registered = await call(env, '/oauth/register', { method: 'POST', body: { client_name: 'My agent', redirect_uris: ['https://agent.example/callback?app=oraclebot'], token_endpoint_auth_method: 'none' } });
  assert.equal(registered.response.status, 201);
  const verifier = Buffer.from(crypto.getRandomValues(new Uint8Array(32))).toString('base64url');
  const params = { client_id: registered.data.client_id, redirect_uri: registered.data.redirect_uris[0], response_type: 'code', resource: `${ORIGIN}/mcp`, scope, state: 'random-client-state', code_challenge: await digest(verifier), code_challenge_method: 'S256' };
  const started = await call(env, `/oauth/authorize?${new URLSearchParams(params)}`);
  assert.equal(started.response.status, 302);
  const requestId = new URL(started.response.headers.get('Location')).searchParams.get('agent_request');
  const details = await call(env, `/api/agent/authorization?request_id=${requestId}`, { cookie: user.cookie });
  assert.equal(details.data.wallet, user.wallet);
  assert.equal(details.data.client.redirectUri, params.redirect_uri);
  let proof = {};
  if (scope.includes('trade:')) {
    const policy = { venues: ['jupiter'], assets: ['SOL'], maxTradeUsd: 10, maxTotalUsd: 30, expiresAt: at() + 3600 };
    const challenge = await call(env, '/api/agent/authorization/challenge', { method: 'POST', cookie: user.cookie, body: { requestId, policy } });
    assert.equal(challenge.response.status, 200);
    assert.match(challenge.data.message, /trading preauthorization/);
    const signature = Buffer.from(await crypto.subtle.sign('Ed25519', user.keys.privateKey, encoder.encode(challenge.data.message))).toString('base64');
    proof = { challengeId: challenge.data.challengeId, signature };
  }
  const consent = await call(env, '/api/agent/authorization', { method: 'POST', cookie: user.cookie, body: { requestId, approve: true, ...proof } });
  assert.equal(consent.response.status, 200);
  const callback = new URL(consent.data.redirectTo);
  assert.equal(callback.searchParams.get('state'), params.state);
  const tokens = await call(env, '/oauth/token', { method: 'POST', form: { grant_type: 'authorization_code', client_id: params.client_id, code: callback.searchParams.get('code'), code_verifier: verifier, resource: params.resource, redirect_uri: params.redirect_uri } });
  assert.equal(tokens.response.status, 200);
  return { token: tokens.data.access_token, requestId };
}
const rpc = (env, token, name, args = {}) => call(env, '/mcp', { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'MCP-Protocol-Version': '2025-11-25' }, body: { jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name, arguments: args } } });

test('Worker routes protocol before assets and retains bearer challenge and security headers', async () => {
  const env = environment(); let assets = 0;
  env.ASSETS = { fetch() { assets++; return new Response('asset'); } };
  const metadata = await call(env, '/.well-known/oauth-protected-resource/mcp');
  assert.equal(metadata.data.resource, `${ORIGIN}/mcp`);
  assert.equal(metadata.response.headers.get('X-Content-Type-Options'), 'nosniff');
  const response = await call(env, '/mcp', { method: 'POST', body: { jsonrpc: '2.0', id: 1, method: 'ping' } });
  assert.equal(response.response.status, 401);
  assert.match(response.response.headers.get('WWW-Authenticate'), /resource_metadata/);
  assert.equal((await call(env, '/mcp')).response.status, 405);
  assert.equal((await call(env, '/oauth/token', { method: 'POST', form: {} })).response.status, 400);
  assert.equal(assets, 0);
  await call(env, '/'); assert.equal(assets, 1);
});

test('real wallet login and signed preauthorization produce only the bearer owner status', async () => {
  const env = environment(); const owner = await login(env); const other = await login(env);
  env.sqlite.prepare("INSERT INTO bots(id,user_id,name,coin,strategy,venue,leverage,budget,mode,status,created_at,updated_at) VALUES (?,?,?,'SOL','rsi','jupiter',1,10,'paper','configured',?,?)").run(crypto.randomUUID(), other.user.id, 'Other wallet private configuration', at(), at());
  const { token } = await authorize(env, owner);
  const result = await rpc(env, token, 'oraclebot_get_status');
  assert.equal(result.response.status, 200);
  const status = result.data.result.structuredContent;
  assert.equal(status.wallet, owner.wallet); assert.equal(status.account.user.id, owner.user.id);
  assert.deepEqual(status.account.bots, []); assert.equal(status.account.usage.bots, 0);
  assert.equal(status.execution.requiresWalletApprovalPerTrade, false);
  assert.equal(status.execution.mode, 'preauthorized'); assert.equal(status.execution.readiness, 'execution_unavailable');
  const serialized = JSON.stringify(result.data);
  for (const secret of [token, other.wallet, other.user.id, 'Other wallet private configuration']) assert.equal(serialized.includes(secret), false);
  assert.equal((await rpc(env, token, 'oraclebot_get_status', { wallet: other.wallet })).data.error.code, -32602);
  assert.equal((await call(env, '/mcp', { method: 'POST', cookie: owner.cookie, body: { jsonrpc: '2.0', id: 1, method: 'ping' } })).response.status, 401);
});

test('preauthorized trade refuses missing customer executor and grant revocation is immediate', async () => {
  const env = environment(); const owner = await login(env); const other = await login(env);
  env.sqlite.prepare("INSERT INTO subscriptions(user_id,stripe_subscription_id,status,period_end,updated_at,plan_id) VALUES (?,?,'active',?,?,'starter')").run(owner.user.id, 'sub_fixture', at() + 3600, at());
  const { token } = await authorize(env, owner);
  const trade = await rpc(env, token, 'oraclebot_request_trade', { idempotencyKey: 'one-request', venue: 'jupiter', asset: 'SOL', side: 'buy', budgetUsd: 10 });
  assert.equal(trade.data.result.isError, true);
  assert.equal(trade.data.result.structuredContent.code, 'execution_unavailable');
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM agent_trade_intents').get().n, 0);
  const grants = await call(env, '/api/agent/grants', { cookie: owner.cookie });
  assert.equal(grants.data.grants.length, 1);
  const id = grants.data.grants[0].id;
  const grantBeforeForeignRevoke = env.sqlite.prepare('SELECT * FROM agent_grants WHERE id=?').get(id);
  assert.equal((await call(env, `/api/agent/grants/${id}/revoke`, { method: 'POST', cookie: other.cookie, body: {} })).response.status, 404);
  assert.deepEqual(env.sqlite.prepare('SELECT * FROM agent_grants WHERE id=?').get(id), grantBeforeForeignRevoke);
  const stillAuthorized = await rpc(env, token, 'oraclebot_get_status');
  assert.equal(stillAuthorized.response.status, 200);
  assert.equal(stillAuthorized.data.result.structuredContent.wallet, owner.wallet);
  assert.equal((await call(env, `/api/agent/grants/${id}/revoke`, { method: 'POST', cookie: owner.cookie, body: {} })).response.status, 200);
  assert.equal((await rpc(env, token, 'oraclebot_get_status')).response.status, 401);
});

function insertIntent(env, owner, state) {
  const grant = env.sqlite.prepare('SELECT * FROM agent_grants WHERE user_id=?').get(owner.user.id);
  const id = crypto.randomUUID();
  env.sqlite.prepare('INSERT INTO agent_trade_intents(id,user_id,wallet,grant_id,resource,policy_hash,idempotency_key,payload_hash,payload_json,state,reservation_cents,expires_at,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)').run(id, owner.user.id, owner.wallet, grant.id, grant.resource, grant.policy_hash, id, 'fixture-hash', '{}', state, 1000, at() - 1, at() - 60, at() - 60);
  return id;
}
function accountAuthorizationRows(env, userId) {
  return {
    users: env.sqlite.prepare('SELECT * FROM users WHERE id=?').all(userId),
    sessions: env.sqlite.prepare('SELECT * FROM sessions WHERE user_id=? ORDER BY token_hash').all(userId),
    grants: env.sqlite.prepare('SELECT * FROM agent_grants WHERE user_id=? ORDER BY id').all(userId),
  };
}
test('cleanup expires only unsubmitted intents and deletion preserves unresolved submissions', async () => {
  const env = environment(); const owner = await login(env); await authorize(env, owner);
  const prepared = insertIntent(env, owner, 'prepared'); const unknown = insertIntent(env, owner, 'unknown');
  await worker.scheduled({}, env);
  assert.equal(env.sqlite.prepare('SELECT state FROM agent_trade_intents WHERE id=?').get(prepared).state, 'expired');
  assert.equal(env.sqlite.prepare('SELECT state FROM agent_trade_intents WHERE id=?').get(unknown).state, 'unknown');
  const authorizationBeforeDeletion = accountAuthorizationRows(env, owner.user.id);
  assert.equal(authorizationBeforeDeletion.users.length, 1);
  assert.equal(authorizationBeforeDeletion.sessions.length, 1);
  assert.equal(authorizationBeforeDeletion.grants.length, 1);
  const deleted = await call(env, '/api/me', { method: 'DELETE', cookie: owner.cookie, body: {} });
  assert.equal(deleted.response.status, 409); assert.equal(deleted.data.error, 'trade_reconciliation_required');
  assert.deepEqual(accountAuthorizationRows(env, owner.user.id), authorizationBeforeDeletion);
});
test('deletion transaction rejects a submit that wins after its initial check', async () => {
  const env = environment(); const owner = await login(env); await authorize(env, owner);
  const intent = insertIntent(env, owner, 'prepared'); const batch = env.DB.batch;
  const authorizationBeforeDeletion = accountAuthorizationRows(env, owner.user.id);
  assert.equal(authorizationBeforeDeletion.users.length, 1);
  assert.equal(authorizationBeforeDeletion.sessions.length, 1);
  assert.equal(authorizationBeforeDeletion.grants.length, 1);
  env.DB.batch = async statements => {
    env.sqlite.prepare("UPDATE agent_trade_intents SET state='submitting' WHERE id=?").run(intent);
    return batch(statements);
  };
  const deleted = await call(env, '/api/me', { method: 'DELETE', cookie: owner.cookie, body: {} });
  assert.equal(deleted.response.status, 409); assert.equal(deleted.data.error, 'trade_reconciliation_required');
  assert.equal(env.sqlite.prepare('SELECT state FROM agent_trade_intents WHERE id=?').get(intent).state, 'submitting');
  assert.deepEqual(accountAuthorizationRows(env, owner.user.id), authorizationBeforeDeletion);
});
