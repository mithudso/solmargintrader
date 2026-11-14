import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { once } from 'node:events';
import worker from '../src/worker.js';
import executionService from '../execution/worker.js';
import { Coinbase } from '../execution/coinbase.js';
import { reconcileCustomerTrade } from '../src/trades.js';
import { environment, seedUser, request, ORIGIN, at } from './helpers/d1.js';

const NativeRequest = globalThis.Request;
const nativeFetch = globalThis.fetch;
const PORTFOLIO = 'c753d452-5138-45a9-868a-a86c980e30f0';
const permissions = { can_view: true, can_trade: true, can_transfer: false, portfolio_uuid: PORTFOLIO, portfolio_type: 'DEFAULT' };
const billing = {
  STRIPE_SECRET_KEY: 'sk_test_workers_transport_fixture', STRIPE_WEBHOOK_SECRET: 'whsec_workers_transport_fixture',
  STRIPE_STARTER_PRICE_ID: 'price_workers_starter', STRIPE_ADVANCED_PRICE_ID: 'price_workers_advanced',
  STRIPE_UNLIMITED_PRICE_ID: 'price_workers_unlimited', STRIPE_PORTAL_CONFIGURATION_ID: 'bpc_workersfixture',
  BILLING_LAUNCH_ENABLED: 'true',
};

// Node accepts redirect:error. Workers throws before sending it, so ordinary
// Node fetch stubs cannot catch this production-only failure.
class WorkersRequest extends NativeRequest {
  constructor(input, init) {
    const redirect = init?.redirect ?? (input instanceof NativeRequest ? input.redirect : 'follow');
    if (!['follow', 'manual'].includes(redirect)) throw new TypeError('Unsupported redirect mode. Must be one of: follow, manual');
    super(input, init);
  }
}
function workersBoundary(t) {
  globalThis.Request = WorkersRequest;
  t.after(() => { globalThis.Request = NativeRequest; });
}
function json(response, body, status = 200, headers = {}) {
  response.writeHead(status, { 'Content-Type': 'application/json', ...headers });
  response.end(JSON.stringify(body));
}
async function fixture(t, respond, receiverBody = {}) {
  const calls = []; const receiver = []; const failures = [];
  const server = createServer(async (incoming, response) => {
    try {
      let body = ''; for await (const chunk of incoming) body += chunk;
      const entry = { method: incoming.method, path: incoming.url, headers: incoming.headers, body };
      // The same-origin receiver would retain Authorization if fetch followed.
      if (incoming.url === '/redirect-receiver') { receiver.push(entry); return json(response, receiverBody); }
      calls.push(entry); await respond(entry, response);
    } catch (error) { failures.push(error); if (!response.headersSent) json(response, { error: 'fixture_failed' }, 500); else response.end(); }
  });
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  t.after(async () => {
    await new Promise((resolve, reject) => { server.close(error => error ? reject(error) : resolve()); server.closeAllConnections(); });
    assert.deepEqual(failures, []);
  });
  return { origin: `http://127.0.0.1:${server.address().port}`, calls, receiver };
}
function transport(origin, upstream, observed = []) {
  return async (input, init) => {
    const outgoing = new Request(input, init);
    const url = new URL(outgoing.url);
    assert.equal(url.origin, origin, 'tests may only rewrite the expected production origin');
    assert.equal(outgoing.redirect, 'manual', 'credentialed requests must explicitly refuse redirects');
    observed.push({ path: url.pathname, redirect: outgoing.redirect });
    // Preserve the product request's redirect mode; forcing one here would hide
    // a regression in the Worker or Coinbase client.
    return nativeFetch(new URL(url.pathname + url.search, upstream.origin), {
      method: outgoing.method, headers: outgoing.headers, body: outgoing.body,
      signal: outgoing.signal, redirect: outgoing.redirect, duplex: 'half',
    });
  };
}
async function call(env, path, options) {
  const response = await worker.fetch(request(path, options), env);
  return { response, data: await response.json() };
}

test('the compatibility boundary rejects redirect:error before transport', () => {
  assert.throws(() => new WorkersRequest('https://fixture.example', { redirect: 'error' }), /Unsupported redirect mode/);
  assert.throws(() => new WorkersRequest(new NativeRequest('https://fixture.example', { redirect: 'error' })), /Unsupported redirect mode/);
  assert.equal(new WorkersRequest('https://fixture.example', { redirect: 'manual' }).redirect, 'manual');
});

test('Stripe Checkout succeeds through a Workers-compatible local fetch boundary', async t => {
  workersBoundary(t);
  const env = { ...environment(), ...billing }; const user = await seedUser(env);
  const upstream = await fixture(t, (entry, response) => {
    assert.equal(entry.headers.authorization, `Bearer ${billing.STRIPE_SECRET_KEY}`);
    assert.equal(entry.headers['stripe-version'], '2026-10-28.endive');
    if (entry.path === '/v1/customers') {
      assert.equal(entry.method, 'POST');
      assert.equal(new URLSearchParams(entry.body).get('metadata[oraclebot_user]'), user.id);
      return json(response, { id: 'cus_workers_fixture' });
    }
    if (entry.path.startsWith('/v1/subscriptions?')) { assert.equal(entry.method, 'GET'); return json(response, { data: [], has_more: false }); }
    assert.equal(entry.path, '/v1/checkout/sessions'); assert.equal(entry.method, 'POST');
    const fields = new URLSearchParams(entry.body);
    assert.equal(fields.get('line_items[0][price]'), billing.STRIPE_STARTER_PRICE_ID);
    assert.equal(fields.get('subscription_data[trial_period_days]'), '7');
    json(response, { url: 'https://checkout.stripe.com/c/pay/workers-fixture' });
  });
  t.mock.method(globalThis, 'fetch', transport('https://api.stripe.com', upstream));
  const result = await call(env, '/api/billing/checkout', { method: 'POST', cookie: user.cookie, body: { plan: 'starter' } });
  assert.equal(result.response.status, 200); assert.equal(result.data.url, 'https://checkout.stripe.com/c/pay/workers-fixture');
  assert.equal(result.data.trialDays, 7); assert.equal(upstream.calls.length, 3);
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM subscriptions').get().n, 0);
});

test('Stripe rejects a real HTTP redirect without following or granting membership', async t => {
  workersBoundary(t);
  const env = { ...environment(), ...billing }; const user = await seedUser(env);
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_workers_fixture', user.id);
  const upstream = await fixture(t, (entry, response) => {
    assert.equal(entry.headers.authorization, `Bearer ${billing.STRIPE_SECRET_KEY}`);
    if (entry.path.startsWith('/v1/subscriptions?')) return json(response, { data: [], has_more: false });
    assert.equal(entry.path, '/v1/checkout/sessions');
    json(response, {}, 302, { Location: '/redirect-receiver' });
  }, { url: 'https://checkout.stripe.com/c/pay/redirect-must-not-succeed' });
  t.mock.method(globalThis, 'fetch', transport('https://api.stripe.com', upstream));
  const result = await call(env, '/api/billing/checkout', { method: 'POST', cookie: user.cookie, body: { plan: 'starter' } });
  assert.equal(result.response.status, 502); assert.equal(result.data.error, 'billing_provider_error');
  assert.equal(upstream.calls.length, 2); assert.deepEqual(upstream.receiver, []);
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM subscriptions').get().n, 0);
  assert.ok(env.sqlite.prepare('SELECT checkout_pending_at FROM users WHERE id=?').get(user.id).checkout_pending_at);
});

for (const binding of [false, true]) {
  for (const redirect of [false, true]) {
    test(`${binding ? 'bound' : 'legacy URL'} analysis ${redirect ? 'rejects an HTTP redirect' : 'succeeds'} at the Workers fetch boundary`, async t => {
      workersBoundary(t);
      const env = { ENGINE_URL: 'https://analysis.example', ENGINE_TOKEN: 'analysis-workers-fixture-token' };
      const value = { strategies: [{ id: 'rsi', name: 'Local fixture strategy' }] };
      const upstream = await fixture(t, (entry, response) => {
        assert.equal(entry.path, '/v1/strategies'); assert.equal(entry.method, 'GET');
        assert.equal(entry.headers.authorization, `Bearer ${env.ENGINE_TOKEN}`);
        json(response, value, redirect ? 302 : 200, redirect ? { Location: '/redirect-receiver' } : {});
      }, value);
      const fetch = transport(binding ? 'https://analysis.internal' : env.ENGINE_URL, upstream);
      if (binding) env.ENGINE_SERVICE = { fetch }; else t.mock.method(globalThis, 'fetch', fetch);
      const result = await call(env, '/api/strategies');
      assert.equal(result.response.status, redirect ? 503 : 200);
      if (redirect) assert.equal(result.data.error, 'engine_unavailable'); else assert.deepEqual(result.data, value);
      assert.equal(upstream.calls.length, 1); assert.deepEqual(upstream.receiver, []);
    });
  }
}

for (const redirect of [false, true]) {
  test(`private connection service ${redirect ? 'rejects an HTTP redirect' : 'and owner dispatch use Workers-compatible requests'}`, async t => {
    workersBoundary(t);
    const env = { ...environment(), EXECUTOR_TOKEN: 'execution-workers-fixture-token-32-characters' };
    const user = await seedUser(env); const observed = [];
    const value = { connections: [], nextCursor: null };
    const upstream = await fixture(t, (entry, response) => {
      assert.equal(entry.path, '/v1/connections/list'); assert.equal(entry.method, 'POST');
      assert.deepEqual(JSON.parse(entry.body), { userId: user.id, wallet: user.wallet });
      if (redirect) assert.equal(entry.headers.authorization, `Bearer ${env.EXECUTOR_TOKEN}`);
      json(response, value, redirect ? 302 : 200, redirect ? { Location: '/redirect-receiver' } : {});
    }, value);
    if (redirect) {
      env.USER_TRADE_EXECUTOR = { fetch: transport('https://customer-trade.internal', upstream, observed) };
    } else {
      env.CUSTOMER_EXECUTORS = { getByName() { return { fetch: transport('https://executor-owner.internal', upstream, observed) }; } };
      env.USER_TRADE_EXECUTOR = { async fetch(outgoing) {
        const checked = new Request(outgoing); assert.equal(checked.redirect, 'manual');
        assert.equal(checked.headers.get('Authorization'), `Bearer ${env.EXECUTOR_TOKEN}`);
        return executionService.fetch(checked, env);
      } };
    }
    const result = await call(env, '/api/connections', { cookie: user.cookie });
    assert.equal(result.response.status, redirect ? 503 : 200);
    if (redirect) assert.equal(result.data.error, 'execution_unavailable'); else assert.deepEqual(result.data, value);
    assert.equal(observed.length, 1); assert.equal(upstream.calls.length, 1); assert.deepEqual(upstream.receiver, []);
  });
}

async function signing() {
  const pair = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
  const encoded = Buffer.from(await crypto.subtle.exportKey('pkcs8', pair.privateKey)).toString('base64');
  return { pair, credentials: { apiKeyName: 'organizations/workers-fixture/apiKeys/ephemeral-key', privateKey: `-----BEGIN PRIVATE KEY-----\n${encoded}\n-----END PRIVATE KEY-----\n` } };
}
for (const redirect of [false, true]) {
  test(`Coinbase signed read ${redirect ? 'rejects an HTTP redirect without forwarding its bearer' : 'succeeds with the actual request redirect mode'}`, async t => {
    workersBoundary(t);
    const { pair, credentials } = await signing();
    const upstream = await fixture(t, async (entry, response) => {
      assert.equal(entry.path, '/api/v3/brokerage/key_permissions'); assert.equal(entry.method, 'GET');
      const authorization = entry.headers.authorization; assert.match(authorization, /^Bearer /);
      const [header, payload, signature] = authorization.slice(7).split('.');
      assert.equal(JSON.parse(Buffer.from(payload, 'base64url')).uri, 'GET api.coinbase.com/api/v3/brokerage/key_permissions');
      assert.equal(await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, pair.publicKey,
        Buffer.from(signature, 'base64url'), new TextEncoder().encode(`${header}.${payload}`)), true);
      json(response, permissions, redirect ? 302 : 200, redirect ? { Location: '/redirect-receiver' } : {});
    }, permissions);
    const client = new Coinbase(credentials, transport('https://api.coinbase.com', upstream));
    if (redirect) await assert.rejects(client.permissions(PORTFOLIO), { code: 'provider_unavailable', status: 503 });
    else assert.equal(await client.permissions(PORTFOLIO), PORTFOLIO);
    assert.equal(upstream.calls.length, 1); assert.deepEqual(upstream.receiver, []);
  });
}

for (const redirect of [false, true]) {
  test(`read-only trade reconciliation ${redirect ? 'retains unknown state after an HTTP redirect' : 'uses a Workers-compatible private request'}`, async t => {
    workersBoundary(t);
    const env = { ...environment(), EXECUTOR_RECONCILIATION_ENABLED: 'true', EXECUTOR_TOKEN: 'reconcile-workers-fixture-token-32-characters' };
    const user = await seedUser(env); const id = crypto.randomUUID();
    const policyHash = 'a'.repeat(64); const payloadHash = 'b'.repeat(64);
    env.sqlite.prepare(`INSERT INTO agent_trade_intents
      (id,user_id,wallet,resource,policy_hash,idempotency_key,payload_hash,payload_json,state,reservation_cents,expires_at,created_at,updated_at)
      VALUES (?,?,?,?,?,?,?,?,'unknown',1000,?,?,?)`).run(id, user.id, user.wallet, `${ORIGIN}/mcp`, policyHash, id, payloadHash,
      JSON.stringify({ venue: 'coinbase', asset: 'SOL', side: 'buy', budgetUsd: 10, product: 'spot', leverage: 1 }), at() + 300, at(), at());
    const receipt = { intentId: id, wallet: user.wallet, policyHash, payloadHash, connectionId: null,
      orderId: null, status: 'unknown', consumedCents: 0, filled: null, reconciledAt: at() };
    const upstream = await fixture(t, (entry, response) => {
      assert.equal(entry.path, '/v1/trades/reconcile'); assert.equal(entry.method, 'POST');
      assert.equal(entry.headers.authorization, `Bearer ${env.EXECUTOR_TOKEN}`);
      assert.deepEqual(JSON.parse(entry.body), { intentId: id, userId: user.id, wallet: user.wallet, resource: `${ORIGIN}/mcp`, policyHash, payloadHash });
      json(response, receipt, redirect ? 302 : 200, redirect ? { Location: '/redirect-receiver' } : {});
    }, receipt);
    env.USER_TRADE_EXECUTOR = { fetch: transport('https://customer-trade.internal', upstream) };
    await reconcileCustomerTrade(env, user.user, id);
    const saved = env.sqlite.prepare('SELECT state,reservation_cents,last_error FROM agent_trade_intents WHERE id=?').get(id);
    assert.equal(saved.state, 'unknown'); assert.equal(saved.reservation_cents, 1000);
    assert.equal(saved.last_error, redirect ? 'reconciliation_unavailable' : null);
    assert.equal(upstream.calls.length, 1); assert.deepEqual(upstream.receiver, []);
  });
}
