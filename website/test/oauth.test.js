import test from 'node:test';
import assert from 'node:assert/strict';
import { authenticateAgent, cleanupAgentAccess, handleOAuth, OAuthError, validateAgentPolicy } from '../src/oauth.js';
import { environment, ORIGIN, request, seedUser, at } from './helpers/d1.js';

const encoder = new TextEncoder();
const sha = async value => Buffer.from(await crypto.subtle.digest('SHA-256', encoder.encode(value))).toString('hex');
const s256 = async value => Buffer.from(await crypto.subtle.digest('SHA-256', encoder.encode(value))).toString('base64url');
const verifier = () => Buffer.from(crypto.getRandomValues(new Uint8Array(32))).toString('base64url');
const basePolicy = () => ({ venues: ['jupiter', 'coinbase'], assets: ['SOL', 'BTC'], maxTradeUsd: 20, maxTotalUsd: 100, expiresAt: at() + 3600 });

function securityEvents(t) {
  const events = [];
  for (const level of ['info', 'warn']) t.mock.method(console, level, line => events.push({ level, ...JSON.parse(line) }));
  return events;
}
const securityRecord = (operation, reason, outcome = 'succeeded', level = 'info') => ({ level, event: 'oraclebot.agent_security', operation, outcome, reason });
function assertRedacted(events, secrets) {
  for (const event of events) assert.deepEqual(Object.keys(event).sort(), ['event', 'level', 'operation', 'outcome', 'reason']);
  const serialized = JSON.stringify(events);
  for (const secret of secrets) assert.ok(!serialized.includes(secret), 'Security diagnostics must exclude account and credential data');
}

async function account(req, env) {
  const value = /(?:^|;\s*)__Host-oraclebot=([A-Za-z0-9_-]{43})(?:;|$)/.exec(req.headers.get('Cookie') || '')?.[1];
  if (!value) throw new OAuthError(401, 'authentication_required');
  const user = await env.DB.prepare(`SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id
    WHERE s.token_hash=? AND s.expires_at>?`).bind(await sha(value), at()).first();
  if (!user) throw new OAuthError(401, 'authentication_required');
  return user;
}
function sameOrigin(req, env) {
  if (req.headers.get('Origin') !== env.APP_ORIGIN || req.headers.get('Sec-Fetch-Site') === 'cross-site') throw new OAuthError(403, 'invalid_origin');
}
async function call(env, path, options) {
  let response;
  try { response = await handleOAuth(request(path, options), env, { account, sameOrigin }); }
  catch (error) {
    if (!(error instanceof OAuthError)) throw error;
    response = Response.json({ error: error.code }, { status: error.status, headers: error.headers });
  }
  const data = response && response.headers.get('Content-Type')?.includes('application/json') ? await response.json() : null;
  return { response, data };
}
async function register(env, changes = {}) {
  const result = await call(env, '/oauth/register', { method: 'POST', body: { client_name: 'Example agent', redirect_uris: ['https://agent.example/callback?app=oraclebot'], token_endpoint_auth_method: 'none', ...changes } });
  assert.equal(result.response.status, 201, JSON.stringify(result.data));
  return result.data;
}
async function authorization(env, registered, scopes = 'status:read', changes = {}) {
  const secret = verifier();
  const params = { client_id: registered.client_id, redirect_uri: registered.redirect_uris[0], response_type: 'code', resource: `${ORIGIN}/mcp`, scope: scopes, state: 'state-with-entropy', code_challenge: await s256(secret), code_challenge_method: 'S256', ...changes };
  const result = await call(env, `/oauth/authorize?${new URLSearchParams(params)}`);
  return { ...result, verifier: secret, params, requestId: result.response.status === 302 ? new URL(result.response.headers.get('Location')).searchParams.get('agent_request') : null };
}
async function sign(user, message) {
  return Buffer.from(await crypto.subtle.sign('Ed25519', user.keys.privateKey, encoder.encode(message))).toString('base64');
}
async function approve(env, user, auth, { policy, signer = user } = {}) {
  let proof = {};
  if (auth.params.scope.includes('trade:')) {
    const challenge = await call(env, '/api/agent/authorization/challenge', { method: 'POST', cookie: user.cookie, body: { requestId: auth.requestId, policy: policy || basePolicy() } });
    assert.equal(challenge.response.status, 200, JSON.stringify(challenge.data));
    proof = { challengeId: challenge.data.challengeId, signature: await sign(signer, challenge.data.message) };
  }
  const result = await call(env, '/api/agent/authorization', { method: 'POST', cookie: user.cookie, body: { requestId: auth.requestId, approve: true, ...proof } });
  return { ...result, code: result.data?.redirectTo ? new URL(result.data.redirectTo).searchParams.get('code') : null, proof };
}
async function exchange(env, registered, auth, code, changes = {}) {
  return call(env, '/oauth/token', { method: 'POST', form: { grant_type: 'authorization_code', client_id: registered.client_id, code, redirect_uri: registered.redirect_uris[0], resource: `${ORIGIN}/mcp`, code_verifier: auth.verifier, ...changes } });
}
async function session(env, { user, scopes = 'status:read', policy } = {}) {
  user ||= await seedUser(env);
  const registered = await register(env); const auth = await authorization(env, registered, scopes);
  assert.equal(auth.response.status, 302);
  const consent = await approve(env, user, auth, { policy }); assert.equal(consent.response.status, 200, JSON.stringify(consent.data));
  const tokens = await exchange(env, registered, auth, consent.code); assert.equal(tokens.response.status, 200, JSON.stringify(tokens.data));
  return { user, registered, auth, consent, tokens: tokens.data };
}
const bearer = token => request('/mcp', { headers: { Authorization: `Bearer ${token}` } });

test('OAuth discovery advertises exact MCP audience and only public PKCE code flow', async () => {
  const env = environment();
  const protectedResource = await call(env, '/.well-known/oauth-protected-resource/mcp');
  assert.equal(protectedResource.data.resource, `${ORIGIN}/mcp`);
  assert.deepEqual(protectedResource.data.authorization_servers, [ORIGIN]);
  assert.equal((await call(env, '/.well-known/oauth-protected-resource')).data.resource, `${ORIGIN}/mcp`);
  const metadata = await call(env, '/.well-known/oauth-authorization-server');
  assert.deepEqual(metadata.data.code_challenge_methods_supported, ['S256']);
  assert.deepEqual(metadata.data.token_endpoint_auth_methods_supported, ['none']);
  assert.equal(metadata.data.client_id_metadata_document_supported, undefined);
  assert.equal(metadata.response.headers.get('Access-Control-Allow-Origin'), '*');
  assert.equal(metadata.response.headers.get('Cache-Control'), 'no-store');
  const preflight = await call(env, '/oauth/token', { method: 'OPTIONS' });
  assert.equal(preflight.response.status, 204);
  assert.equal(await handleOAuth(request('/api/health'), env, {}), null);
});

test('registration bounds metadata, uses no secret, and never fetches client URLs', async () => {
  const env = environment();
  const original = globalThis.fetch; let fetches = 0;
  globalThis.fetch = async () => { fetches++; throw Error('network forbidden'); };
  try {
    const registered = await register(env, { client_uri: 'https://169.254.169.254/latest/meta-data', jwks_uri: 'https://internal.example/keys' });
    assert.equal(registered.client_secret, undefined); assert.equal(fetches, 0);
    assert.equal((await call(env, '/oauth/register', { method: 'POST', body: { redirect_uris: ['http://attacker.example/cb'] } })).response.status, 400);
    assert.equal((await call(env, '/oauth/register', { method: 'POST', body: { redirect_uris: ['https://a.example/cb#fragment'] } })).response.status, 400);
    assert.equal((await call(env, '/oauth/register', { method: 'POST', body: { redirect_uris: ['https://user:pass@a.example/cb'] } })).response.status, 400);
    assert.equal((await call(env, '/oauth/register', { method: 'POST', body: { redirect_uris: Array(11).fill('https://a.example/cb') } })).response.status, 400);
    assert.equal((await call(env, '/oauth/register', { method: 'POST', body: { redirect_uris: ['https://a.example/cb'], token_endpoint_auth_method: 'client_secret_basic' } })).response.status, 400);
    const local = await register(env, { redirect_uris: ['http://127.0.0.1:12345/callback'] });
    assert.equal(local.redirect_uris[0], 'http://127.0.0.1:12345/callback');
  } finally { globalThis.fetch = original; }
});

test('authorization rejects mismatched redirects, scope, resource and weak PKCE before redirecting', async () => {
  const env = environment(); const registered = await register(env);
  for (const change of [
    { redirect_uri: 'https://agent.example/other' },
    { redirect_uri: 'https://agent.example/callback?app=oraclebot&other=1' },
    { resource: 'https://evil.example/mcp' }, { resource: ORIGIN },
    { code_challenge_method: 'plain' }, { code_challenge: 'short' },
    { scope: 'admin' }, { scope: 'status:read status:read' },
    { response_type: 'token' }, { wallet: 'attacker-wallet' },
  ]) {
    const result = await authorization(env, registered, 'status:read', change);
    assert.equal(result.response.status, 400, JSON.stringify(change));
    assert.equal(result.response.headers.get('Location'), null);
  }
  const valid = await authorization(env, registered);
  const duplicated = await call(env, `/oauth/authorize?${new URLSearchParams(valid.params)}&resource=${encodeURIComponent(`${ORIGIN}/mcp`)}`);
  assert.equal(duplicated.response.status, 400);
});

test('read-only consent binds current wallet and stores only hashed protocol credentials', async () => {
  const env = environment(); const first = await seedUser(env); const second = await seedUser(env);
  const registered = await register(env); const auth = await authorization(env, registered);
  assert.equal((await call(env, `/api/agent/authorization?request_id=${auth.requestId}`)).response.status, 401);
  const consentView = await call(env, `/api/agent/authorization?request_id=${auth.requestId}`, { cookie: first.cookie });
  assert.equal(consentView.data.wallet, first.wallet); assert.equal(consentView.data.requiresPolicyProof, false);
  assert.equal((await call(env, `/api/agent/authorization?request_id=${auth.requestId}`, { cookie: second.cookie })).response.status, 404);
  assert.equal((await approve(env, second, auth)).response.status, 404);
  const consent = await approve(env, first, auth); assert.equal(consent.response.status, 200);
  const redirect = new URL(consent.data.redirectTo);
  assert.equal(redirect.searchParams.get('state'), 'state-with-entropy'); assert.equal(redirect.searchParams.get('app'), 'oraclebot');
  const tokens = await exchange(env, registered, auth, consent.code);
  assert.equal(tokens.response.status, 200); assert.equal(tokens.data.expires_in, 900);
  const principal = await authenticateAgent(bearer(tokens.data.access_token), env);
  assert.equal(principal.user.id, first.id); assert.equal(principal.user.wallet, first.wallet);
  assert.deepEqual([...principal.scopes], ['status:read']); assert.equal(principal.grant.policy_json, null);
  for (const [table, raw] of [['agent_codes', consent.code], ['agent_access_tokens', tokens.data.access_token], ['agent_refresh_tokens', tokens.data.refresh_token]]) {
    const stored = env.sqlite.prepare(`SELECT token_hash FROM ${table}`).get().token_hash;
    assert.equal(stored, await sha(raw)); assert.notEqual(stored, raw);
  }
  assert.equal((await approve(env, first, auth)).response.status, 404);
});

test('trade consent needs explicit finite signed preauthorization separate from login', async t => {
  const events = securityEvents(t);
  const env = environment(); const user = await seedUser(env); const registered = await register(env);
  const auth = await authorization(env, registered, 'status:read trade:prepare trade:submit');
  assert.equal((await call(env, '/api/agent/authorization', { method: 'POST', cookie: user.cookie, body: { requestId: auth.requestId, approve: true } })).data.error, 'wallet_authorization_required');
  const challenge = await call(env, '/api/agent/authorization/challenge', { method: 'POST', cookie: user.cookie, body: { requestId: auth.requestId, policy: basePolicy() } });
  assert.equal(challenge.response.status, 200);
  assert.match(challenge.data.message, /without asking for each trade/);
  assert.match(challenge.data.message, /separate from signing in/);
  assert.ok(challenge.data.message.includes(user.wallet)); assert.ok(challenge.data.message.includes(registered.client_id));
  assert.match(challenge.data.message, /Maximum per trade: USD 20\.00/); assert.match(challenge.data.message, /Maximum total: USD 100\.00/);
  const loginOnly = await sign(user, 'Sign in to Oraclebot. This signature does not authorize transactions or access to funds.');
  const invalid = await call(env, '/api/agent/authorization', { method: 'POST', cookie: user.cookie, body: { requestId: auth.requestId, approve: true, challengeId: challenge.data.challengeId, signature: loginOnly } });
  assert.equal(invalid.data.error, 'invalid_wallet_authorization');
  const replay = await call(env, '/api/agent/authorization', { method: 'POST', cookie: user.cookie, body: { requestId: auth.requestId, approve: true, challengeId: challenge.data.challengeId, signature: await sign(user, challenge.data.message) } });
  assert.equal(replay.data.error, 'wallet_authorization_required');
  const approved = await approve(env, user, auth);
  assert.equal(approved.response.status, 200);
  const token = await exchange(env, registered, auth, approved.code);
  const principal = await authenticateAgent(bearer(token.data.access_token), env);
  assert.deepEqual([...principal.scopes], ['status:read', 'trade:prepare', 'trade:submit']);
  const policy = JSON.parse(principal.grant.policy_json);
  assert.deepEqual(policy.venues, ['coinbase', 'jupiter']); assert.deepEqual(policy.assets, ['BTC', 'SOL']);
  assert.equal(principal.grant.policy_hash, await sha(principal.grant.policy_json));
  assert.equal(principal.grant.expires_at, policy.expiresAt);
  assert.throws(() => env.sqlite.prepare('UPDATE agent_grants SET policy_json=? WHERE id=?').run(JSON.stringify({ ...policy, maxTotalUsd: 100000 }), principal.grant.id), /immutable/);
  assert.deepEqual(events, [securityRecord('grant_issued', 'owner_consent')]);
  assertRedacted(events, [user.id, user.wallet, user.cookie, registered.client_id, registered.client_name, auth.requestId, auth.verifier, approved.code, approved.proof.signature, token.data.access_token, token.data.refresh_token, principal.grant.id, principal.grant.policy_hash, principal.grant.policy_json, challenge.data.message, await sha(approved.code)]);
});

test('wrong wallet cannot sign policy and challenge/request/policy substitution fails', async () => {
  const env = environment(); const user = await seedUser(env); const attacker = await seedUser(env); const registered = await register(env);
  const auth = await authorization(env, registered, 'trade:prepare trade:submit');
  const bad = await approve(env, user, auth, { signer: attacker }); assert.equal(bad.data.error, 'invalid_wallet_authorization');
  const challenge = await call(env, '/api/agent/authorization/challenge', { method: 'POST', cookie: user.cookie, body: { requestId: auth.requestId, policy: basePolicy() } });
  const other = await authorization(env, registered, 'trade:prepare trade:submit');
  const substituted = await call(env, '/api/agent/authorization', { method: 'POST', cookie: user.cookie, body: { requestId: other.requestId, approve: true, challengeId: challenge.data.challengeId, signature: await sign(user, challenge.data.message) } });
  assert.equal(substituted.data.error, 'wallet_authorization_required');
  const tampered = { ...basePolicy(), maxTotalUsd: 999 };
  env.sqlite.prepare('UPDATE agent_consent_challenges SET policy_json=?,policy_hash=? WHERE id=?').run(JSON.stringify(tampered), await sha(JSON.stringify(tampered)), challenge.data.challengeId);
  const changed = await call(env, '/api/agent/authorization', { method: 'POST', cookie: user.cookie, body: { requestId: auth.requestId, approve: true, challengeId: challenge.data.challengeId, signature: await sign(user, challenge.data.message) } });
  assert.equal(changed.data.error, 'invalid_wallet_authorization');
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM agent_grants').get().n, 0);
});

test('policy rejects implicit, nonfinite, fractional-cent, unbounded and unsupported authority', () => {
  for (const change of [
    { maxTradeUsd: NaN }, { maxTradeUsd: Infinity }, { maxTradeUsd: -1 }, { maxTradeUsd: 0 },
    { maxTradeUsd: '20' }, { maxTradeUsd: 0.001 }, { maxTradeUsd: 200 },
    { maxTotalUsd: 1000001 }, { expiresAt: null }, { expiresAt: at() + 31 * 86400 },
    { expiresAt: at() }, { venues: [] }, { venues: ['owner-wallet'] },
    { assets: ['SOL', 'SOL'] }, { assets: ['UNKNOWN'] }, { wallet: 'override' },
  ]) assert.throws(() => validateAgentPolicy({ ...basePolicy(), ...change }), error => error.code === 'invalid_policy', JSON.stringify(change));
  assert.equal(validateAgentPolicy({ ...basePolicy(), maxTradeUsd: 0.29 }).maxTradeUsd, 0.29);
  assert.equal(validateAgentPolicy({ ...basePolicy(), maxTradeUsd: 0.57 }).maxTradeUsd, 0.57);
  assert.throws(() => validateAgentPolicy({}), error => error.code === 'invalid_policy');
});

test('stolen code needs exact client, resource, redirect and PKCE, without consuming valid code', async t => {
  const events = securityEvents(t);
  const env = environment(); const user = await seedUser(env); const registered = await register(env); const attacker = await register(env);
  const auth = await authorization(env, registered); const approved = await approve(env, user, auth);
  assert.deepEqual(events, [securityRecord('grant_issued', 'owner_consent')]); events.length = 0;
  for (const change of [
    { client_id: attacker.client_id }, { redirect_uri: 'https://evil.example/callback' },
    { resource: 'https://evil.example/mcp' }, { resource: `${ORIGIN}/mcp/` }, { code_verifier: verifier() }, { code: verifier() },
  ]) assert.equal((await exchange(env, registered, auth, approved.code, change)).response.status, 400, JSON.stringify(change));
  assert.deepEqual(events, [], 'Mismatched or unknown credentials are not evidence of replay');
  const tokens = await exchange(env, registered, auth, approved.code); assert.equal(tokens.response.status, 200);
  await authenticateAgent(bearer(tokens.data.access_token), env);
  const replay = await exchange(env, registered, auth, approved.code);
  assert.equal(replay.data.error, 'invalid_grant');
  await assert.rejects(authenticateAgent(bearer(tokens.data.access_token), env), error => error.status === 401);
  assert.deepEqual(events, [securityRecord('code_replay', 'already_used', 'detected', 'warn'), securityRecord('grant_revoked', 'code_replay')]);
  assertRedacted(events, [user.id, user.wallet, registered.client_id, auth.verifier, approved.code, tokens.data.access_token, tokens.data.refresh_token, await sha(approved.code)]);
});

test('concurrent authorization approvals and code exchanges issue at most one grant and token family', async t => {
  const events = securityEvents(t);
  const env = environment(); const user = await seedUser(env); const registered = await register(env);
  const auth = await authorization(env, registered);
  const approvals = await Promise.all([approve(env, user, auth), approve(env, user, auth)]);
  assert.equal(approvals.filter(result => result.response.status === 200).length, 1);
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM agent_grants').get().n, 1);
  assert.deepEqual(events, [securityRecord('grant_issued', 'owner_consent')]); events.length = 0;
  const code = approvals.find(result => result.code).code;
  const exchanges = await Promise.all([exchange(env, registered, auth, code), exchange(env, registered, auth, code)]);
  assert.ok(exchanges.filter(result => result.response.status === 200).length <= 1);
  // Reuse revokes the family, including a successful racing exchange.
  for (const result of exchanges.filter(result => result.data?.access_token)) await assert.rejects(authenticateAgent(bearer(result.data.access_token), env), error => error.status === 401);
  assert.equal(events.filter(event => event.level === 'warn' && ['code_replay', 'code_claim_conflict'].includes(event.operation)).length, 1);
  assert.equal(events.filter(event => event.operation === 'grant_revoked').length, 1);
});

test('refresh rotates credentials, narrows scopes, and reuse revokes all tokens immediately', async t => {
  const events = securityEvents(t);
  const env = environment(); const current = await session(env, { scopes: 'status:read trade:prepare trade:submit' });
  events.length = 0;
  const form = { grant_type: 'refresh_token', client_id: current.registered.client_id, resource: `${ORIGIN}/mcp`, refresh_token: current.tokens.refresh_token };
  const rotated = await call(env, '/oauth/token', { method: 'POST', form: { ...form, scope: 'status:read' } });
  assert.equal(rotated.response.status, 200); assert.notEqual(rotated.data.refresh_token, current.tokens.refresh_token);
  assert.deepEqual([...(await authenticateAgent(bearer(rotated.data.access_token), env)).scopes], ['status:read']);
  const wider = await call(env, '/oauth/token', { method: 'POST', form: { ...form, refresh_token: rotated.data.refresh_token, scope: 'status:read trade:submit' } });
  assert.equal(wider.data.error, 'invalid_scope');
  const replay = await call(env, '/oauth/token', { method: 'POST', form }); assert.equal(replay.data.error, 'invalid_grant');
  for (const token of [current.tokens.access_token, rotated.data.access_token]) await assert.rejects(authenticateAgent(bearer(token), env), error => error.status === 401);
  const revokedRefresh = await call(env, '/oauth/token', { method: 'POST', form: { ...form, refresh_token: rotated.data.refresh_token } });
  assert.equal(revokedRefresh.data.error, 'invalid_grant');
  assert.deepEqual(events, [securityRecord('refresh_replay', 'already_used', 'detected', 'warn'), securityRecord('grant_revoked', 'refresh_replay')]);
  assertRedacted(events, [current.user.id, current.user.wallet, current.registered.client_id, current.tokens.access_token, current.tokens.refresh_token, rotated.data.access_token, rotated.data.refresh_token, await sha(current.tokens.refresh_token)]);
});

test('concurrent refresh reuse cannot create two usable token families', async t => {
  const events = securityEvents(t);
  const env = environment(); const current = await session(env);
  events.length = 0;
  const form = { grant_type: 'refresh_token', client_id: current.registered.client_id, resource: `${ORIGIN}/mcp`, refresh_token: current.tokens.refresh_token };
  const results = await Promise.all([call(env, '/oauth/token', { method: 'POST', form }), call(env, '/oauth/token', { method: 'POST', form })]);
  assert.ok(results.filter(result => result.response.status === 200).length <= 1);
  for (const token of [current.tokens.access_token, ...results.map(result => result.data?.access_token).filter(Boolean)]) await assert.rejects(authenticateAgent(bearer(token), env), error => error.status === 401);
  assert.equal(events.filter(event => event.level === 'warn' && ['refresh_replay', 'refresh_claim_conflict'].includes(event.operation)).length, 1);
  assert.equal(events.filter(event => event.operation === 'grant_revoked').length, 1);
});

test('failed code and refresh claims distinguish conflicts from proven replay', async t => {
  const events = securityEvents(t);
  for (const credential of ['code', 'refresh']) for (const cause of ['used_at', 'expires_at']) {
    const env = environment();
    let current;
    if (credential === 'code') {
      const user = await seedUser(env); const registered = await register(env); const auth = await authorization(env, registered);
      current = { user, registered, auth, consent: await approve(env, user, auth) };
    } else current = await session(env);
    const table = credential === 'code' ? 'agent_codes' : 'agent_refresh_tokens';
    const raw = credential === 'code' ? current.consent.code : current.tokens.refresh_token;
    events.length = 0;
    const prepare = env.DB.prepare;
    env.DB.prepare = sql => {
      const statement = prepare(sql);
      if (sql.startsWith(`UPDATE ${table} SET used_at=?`)) {
        const first = statement.first;
        statement.first = async () => {
          // A competing claim or expiry wins after the caller reads the token.
          env.sqlite.prepare(`UPDATE ${table} SET ${cause}=? WHERE token_hash=?`).run(at() - 1, await sha(raw));
          return first();
        };
      }
      return statement;
    };
    let result;
    try {
      result = credential === 'code' ? await exchange(env, current.registered, current.auth, raw) : await call(env, '/oauth/token', {
        method: 'POST', form: { grant_type: 'refresh_token', client_id: current.registered.client_id, resource: `${ORIGIN}/mcp`, refresh_token: raw },
      });
    } finally { env.DB.prepare = prepare; }
    assert.equal(result.data.error, 'invalid_grant');
    assert.deepEqual(events, [securityRecord(`${credential}_claim_conflict`, 'claim_unavailable', 'denied', 'warn'), securityRecord('grant_revoked', `${credential}_claim_conflict`)]);
    assert.notEqual(env.sqlite.prepare('SELECT revoked_at FROM agent_grants WHERE user_id=?').get(current.user.id).revoked_at, null);
    if (credential === 'refresh') await assert.rejects(authenticateAgent(bearer(current.tokens.access_token), env), error => error.status === 401);
    assertRedacted(events, [current.user.id, current.user.wallet, raw, await sha(raw)]);
  }
});

test('an unavailable diagnostic sink cannot interrupt issuance or replay revocation', async t => {
  for (const level of ['info', 'warn']) t.mock.method(console, level, () => { throw Error('diagnostic sink unavailable'); });
  const env = environment(); const current = await session(env);
  const form = { grant_type: 'refresh_token', client_id: current.registered.client_id, resource: `${ORIGIN}/mcp`, refresh_token: current.tokens.refresh_token };
  const rotated = await call(env, '/oauth/token', { method: 'POST', form });
  assert.equal(rotated.response.status, 200);
  assert.equal((await call(env, '/oauth/token', { method: 'POST', form })).data.error, 'invalid_grant');
  for (const token of [current.tokens.access_token, rotated.data.access_token]) await assert.rejects(authenticateAgent(bearer(token), env), error => error.status === 401);
});

test('refresh client/resource mismatch cannot revoke or consume another client token', async t => {
  const events = securityEvents(t);
  const env = environment(); const current = await session(env); const attacker = await register(env);
  events.length = 0;
  const form = { grant_type: 'refresh_token', client_id: current.registered.client_id, resource: `${ORIGIN}/mcp`, refresh_token: current.tokens.refresh_token };
  for (const change of [{ client_id: attacker.client_id }, { resource: 'https://evil.example/mcp' }, { refresh_token: verifier() }]) assert.equal((await call(env, '/oauth/token', { method: 'POST', form: { ...form, ...change } })).response.status, 400);
  assert.deepEqual(events, [], 'Mismatched or unknown credentials are not evidence of replay');
  await authenticateAgent(bearer(current.tokens.access_token), env);
  assert.equal((await call(env, '/oauth/token', { method: 'POST', form })).response.status, 200);
});

test('grant listing, CSRF protection, owner-only revoke, and protocol revocation isolate wallets', async t => {
  const events = securityEvents(t);
  const env = environment(); const first = await session(env); const second = await session(env);
  events.length = 0;
  const principal = await authenticateAgent(bearer(first.tokens.access_token), env);
  const firstGrants = await call(env, '/api/agent/grants', { cookie: first.user.cookie });
  assert.equal(firstGrants.data.grants.length, 1); assert.equal(firstGrants.data.grants[0].id, principal.grant.id);
  assert.ok(!JSON.stringify(firstGrants.data).includes(first.tokens.access_token));
  assert.equal((await call(env, `/api/agent/grants/${principal.grant.id}/revoke`, { method: 'POST', cookie: second.user.cookie })).response.status, 404);
  assert.equal((await call(env, `/api/agent/grants/${principal.grant.id}/revoke`, { method: 'POST', cookie: first.user.cookie, origin: 'https://evil.example' })).response.status, 403);
  assert.equal((await call(env, '/oauth/revoke', { method: 'POST', form: { client_id: second.registered.client_id, token: first.tokens.access_token } })).response.status, 200);
  assert.deepEqual(events, [], 'An unrelated client cannot emit a successful revocation event');
  await authenticateAgent(bearer(first.tokens.access_token), env);
  assert.equal((await call(env, `/api/agent/grants/${principal.grant.id}/revoke`, { method: 'POST', cookie: first.user.cookie })).response.status, 200);
  await assert.rejects(authenticateAgent(bearer(first.tokens.access_token), env), error => error.status === 401);
  await authenticateAgent(bearer(second.tokens.access_token), env);
  await call(env, '/oauth/revoke', { method: 'POST', form: { client_id: second.registered.client_id, token: second.tokens.refresh_token } });
  await assert.rejects(authenticateAgent(bearer(second.tokens.access_token), env), error => error.status === 401);
  assert.deepEqual(events, [securityRecord('grant_revoked', 'owner_revocation'), securityRecord('grant_revoked', 'oauth_revocation')]);
  assertRedacted(events, [first.user.id, first.user.wallet, principal.grant.id, first.tokens.access_token, second.tokens.refresh_token]);
});

test('token expiry, audience, current user existence and bearer-only authentication fail closed', async () => {
  const env = environment(); const current = await session(env);
  await assert.rejects(authenticateAgent(request('/mcp', { cookie: current.user.cookie }), env), error => error.status === 401 && error.headers['WWW-Authenticate'].includes('/.well-known/oauth-protected-resource/mcp'));
  await assert.rejects(authenticateAgent(new Request('https://evil.example/mcp', { headers: { Authorization: `Bearer ${current.tokens.access_token}` } }), env), error => error.status === 403);
  env.sqlite.prepare('UPDATE agent_access_tokens SET expires_at=?').run(at() - 1);
  await assert.rejects(authenticateAgent(bearer(current.tokens.access_token), env), error => error.status === 401);
  const refreshed = await call(env, '/oauth/token', { method: 'POST', form: { grant_type: 'refresh_token', client_id: current.registered.client_id, resource: `${ORIGIN}/mcp`, refresh_token: current.tokens.refresh_token } });
  assert.equal(refreshed.response.status, 200);
  env.sqlite.prepare('DELETE FROM users WHERE id=?').run(current.user.id);
  await assert.rejects(authenticateAgent(bearer(refreshed.data.access_token), env), error => error.status === 401);
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM agent_grants').get().n, 0);
});

test('denial consumes request and returns only the exact registered redirect and state', async t => {
  const events = securityEvents(t);
  const env = environment(); const user = await seedUser(env); const registered = await register(env); const auth = await authorization(env, registered);
  const denied = await call(env, '/api/agent/authorization', { method: 'POST', cookie: user.cookie, body: { requestId: auth.requestId, approve: false } });
  const redirect = new URL(denied.data.redirectTo);
  assert.equal(redirect.origin, 'https://agent.example'); assert.equal(redirect.pathname, '/callback');
  assert.equal(redirect.searchParams.get('error'), 'access_denied'); assert.equal(redirect.searchParams.get('state'), auth.params.state);
  assert.equal((await approve(env, user, auth)).response.status, 404);
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM agent_grants').get().n, 0);
  assert.deepEqual(events, [securityRecord('grant_denied', 'owner_denied', 'denied')]);
  assertRedacted(events, [user.id, user.wallet, registered.client_id, auth.requestId, auth.params.state, registered.redirect_uris[0]]);
});

test('expired requests, wallet consent challenges and authorization codes cannot be reused', async () => {
  const env = environment(); const user = await seedUser(env); const registered = await register(env);
  const stale = await authorization(env, registered);
  env.sqlite.prepare('UPDATE agent_authorization_requests SET expires_at=? WHERE id=?').run(at() - 1, stale.requestId);
  assert.equal((await approve(env, user, stale)).response.status, 404);
  const trade = await authorization(env, registered, 'trade:submit');
  const challenge = await call(env, '/api/agent/authorization/challenge', { method: 'POST', cookie: user.cookie, body: { requestId: trade.requestId, policy: basePolicy() } });
  env.sqlite.prepare('UPDATE agent_consent_challenges SET expires_at=? WHERE id=?').run(at() - 1, challenge.data.challengeId);
  const approval = await call(env, '/api/agent/authorization', { method: 'POST', cookie: user.cookie, body: { requestId: trade.requestId, approve: true, challengeId: challenge.data.challengeId, signature: await sign(user, challenge.data.message) } });
  assert.equal(approval.data.error, 'wallet_authorization_required');
  const current = await authorization(env, registered, 'status:read', { state: '' });
  const approved = await approve(env, user, current);
  assert.equal(new URL(approved.data.redirectTo).searchParams.get('state'), '');
  env.sqlite.prepare('UPDATE agent_codes SET expires_at=? WHERE token_hash=?').run(at() - 1, await sha(approved.code));
  assert.equal((await exchange(env, registered, current, approved.code)).data.error, 'invalid_grant');
});

test('protocol parameter pollution and wrong media type fail with readable CORS errors', async () => {
  const env = environment();
  const req = new Request(`${ORIGIN}/oauth/token`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: `grant_type=refresh_token&resource=${encodeURIComponent(`${ORIGIN}/mcp`)}&resource=${encodeURIComponent('https://evil.example/mcp')}` });
  await assert.rejects(handleOAuth(req, env, {}), error => error.code === 'invalid_request' && error.headers['Access-Control-Allow-Origin'] === '*');
  const wrongType = await call(env, '/oauth/register', { method: 'POST', headers: { 'Content-Type': 'application/json-evil' }, body: {} });
  assert.equal(wrongType.response.status, 415);
  assert.equal(wrongType.response.headers.get('Access-Control-Allow-Origin'), '*');
});

test('bodies, rate limits and cleanup remain bounded while preserving replay detection', async () => {
  const env = environment();
  const oversized = await call(env, '/oauth/register', { method: 'POST', body: { client_name: 'x'.repeat(17000) } });
  assert.equal(oversized.response.status, 413);
  const duplicate = await call(env, '/oauth/token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, form: { resource: `${ORIGIN}/mcp` } });
  assert.equal(duplicate.response.status, 400);
  for (let index = 0; index < 9; index++) await register(env);
  const limited = await call(env, '/oauth/register', { method: 'POST', body: { redirect_uris: ['https://agent.example/callback'] } });
  assert.equal(limited.response.status, 429);
  const second = environment(); const current = await session(second);
  const rotated = await call(second, '/oauth/token', { method: 'POST', form: { grant_type: 'refresh_token', client_id: current.registered.client_id, resource: `${ORIGIN}/mcp`, refresh_token: current.tokens.refresh_token } });
  assert.equal(rotated.response.status, 200);
  await cleanupAgentAccess(second);
  assert.equal(second.sqlite.prepare('SELECT COUNT(*) AS n FROM agent_refresh_tokens WHERE used_at IS NOT NULL').get().n, 1);
  assert.equal((await call(second, '/oauth/token', { method: 'POST', form: { grant_type: 'refresh_token', client_id: current.registered.client_id, resource: `${ORIGIN}/mcp`, refresh_token: current.tokens.refresh_token } })).data.error, 'invalid_grant');
});

test('active grants remain visible and revocable behind newer inactive history', async () => {
  const env = environment(); const f = await session(env);
  const active = env.sqlite.prepare('SELECT * FROM agent_grants WHERE user_id=?').get(f.user.id);
  env.sqlite.prepare('UPDATE agent_grants SET created_at=? WHERE id=?').run(at()-100, active.id);
  for (let i=0;i<100;i++) {
    env.sqlite.prepare('INSERT INTO agent_grants(id,user_id,client_id,resource,scope,created_at,expires_at,revoked_at) VALUES (?,?,?,?,?,?,?,?)')
      .run(crypto.randomUUID(), f.user.id, active.client_id, active.resource, 'status:read', at()-50, i%2 ? at()+1000 : at()-1, i%2 ? at()-1 : null);
  }
  const listed = await call(env, '/api/agent/grants', { cookie: f.user.cookie });
  assert.equal(listed.data.grants.length,100);
  assert.equal(listed.data.grants[0].id, active.id);
  assert.equal((await call(env, `/api/agent/grants/${active.id}/revoke`, { method:'POST',cookie:f.user.cookie,body:{} })).response.status,200);
  await assert.rejects(authenticateAgent(bearer(f.tokens.access_token),env),error=>error.code==='invalid_token');
});
