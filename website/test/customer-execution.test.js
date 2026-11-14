import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { environment, seedUser, at, ORIGIN } from './helpers/d1.js';
import service, { CustomerExecutor } from '../execution/worker.js';
import { Coinbase, decimal, decimalText, importSigningKey, jwt } from '../execution/coinbase.js';
import { seal, open } from '../execution/credential-vault.js';
import { base64url, digest } from '../execution/common.js';
import { requestTrade, submitTrade, getTradeStatus, reconcileCustomerTrade } from '../src/trades.js';
import { managedConfigHash, managedBindingHash } from '../execution/managed-bot-driver.js';

const PORTFOLIO = 'c753d452-5138-45a9-868a-a86c980e30f0';
const NAME = 'organizations/test-org/apiKeys/test-key';
const SCALE = 10n ** 18n;
const CENT = SCALE / 100n;
const permission = { can_view: true, can_trade: true, can_transfer: false, portfolio_uuid: PORTFOLIO, portfolio_type: 'DEFAULT' };
class Storage {
  constructor() { this.values = new Map(); }
  async get(key) { return structuredClone(this.values.get(key)); }
  async put(key, value) { this.values.set(key, structuredClone(value)); }
  async delete(key) { this.values.delete(key); }
  async deleteAll() { this.values.clear(); }
  async list({ prefix = '', limit = 1000 } = {}) { return new Map([...this.values].filter(([key]) => key.startsWith(prefix)).slice(0, limit).map(([key, value]) => [key, structuredClone(value)])); }
}
async function signing() {
  const pair = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
  const der = new Uint8Array(await crypto.subtle.exportKey('pkcs8', pair.privateKey));
  const pem = `-----BEGIN PRIVATE KEY-----\n${Buffer.from(der).toString('base64')}\n-----END PRIVATE KEY-----\n`;
  return { pair, credentials: { apiKeyName: NAME, privateKey: pem } };
}
async function provider(t, pair, change = {}) {
  const calls = []; const orders = []; const tokens = new Set();
  const server = createServer(async (request, response) => {
    try {
      let raw = ''; for await (const chunk of request) raw += chunk;
      const body = raw ? JSON.parse(raw) : null; const url = new URL(request.url, 'https://api.coinbase.com');
      const token = request.headers.authorization?.slice(7); const parts = token?.split('.'); assert.equal(parts?.length, 3);
      const header = JSON.parse(Buffer.from(parts[0], 'base64url')); const payload = JSON.parse(Buffer.from(parts[1], 'base64url'));
      assert.equal(header.alg, 'ES256'); assert.equal(header.kid, NAME); assert.match(header.nonce, /^[a-f0-9]{32}$/);
      assert.equal(payload.uri, `${request.method} api.coinbase.com${url.pathname}`); assert.equal(payload.iss, 'cdp'); assert.equal(payload.sub, NAME);
      assert.ok(payload.nbf <= at() + 1 && payload.exp === payload.nbf + 120); assert.ok(!tokens.has(token)); tokens.add(token);
      assert.equal(await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, pair.publicKey, Buffer.from(parts[2], 'base64url'), new TextEncoder().encode(`${parts[0]}.${parts[1]}`)), true);
      calls.push({ method: request.method, path: url.pathname, query: url.search, body });
      if (change.onRequest) await change.onRequest({ request, response, body, url, orders, calls });
      if (response.destroyed || response.writableEnded) return;
      let result;
      if (url.pathname.endsWith('/key_permissions')) result = change.permissions || permission;
      else if (url.pathname.endsWith('/accounts')) result = { accounts: ['USD', 'SOL'].map(currency => ({ currency, retail_portfolio_id: PORTFOLIO, active: true, ready: true, available_balance: { value: '10000', currency } })), has_next: false, cursor: '' };
      else if (url.pathname.endsWith('/orders/historical/batch')) result = { orders, has_next: false, cursor: '' };
      else if (/\/orders\/historical\//.test(url.pathname)) result = { order: orders.find(order => order.order_id === url.pathname.split('/').at(-1)) };
      else if (url.pathname.endsWith('/products/SOL-USD')) result = { product_id: 'SOL-USD', base_currency_id: 'SOL', quote_currency_id: 'USD', product_type: 'SPOT', base_increment: '0.0001', quote_increment: '0.01', base_min_size: '0.001', quote_min_size: '1', trading_disabled: false, cancel_only: false, limit_only: false, post_only: false, auction_mode: false };
      else if (url.pathname.endsWith('/best_bid_ask')) result = { pricebooks: [{ product_id: 'SOL-USD', time: new Date((at() - (change.bookAge || 0)) * 1000).toISOString(), bids: [{ price: '100', size: '100' }], asks: [{ price: '100', size: '100' }] }] };
      else if (url.pathname.endsWith('/transaction_summary')) result = { fee_tier: { taker_fee_rate: '0.01' } };
      else if (url.pathname.endsWith('/orders/preview')) {
        const config = body.order_configuration.sor_limit_ioc; const gross = decimal(config.base_size) * decimal(config.limit_price) / SCALE;
        const fee = (gross / 100n + CENT - 1n) / CENT * CENT;
        result = { preview_id: crypto.randomUUID(), errs: [], warning: [], base_size: config.base_size, quote_size: decimalText(gross), order_total: decimalText(gross + fee), commission_total: decimalText(fee), best_bid: '100', best_ask: '100' };
      } else if (url.pathname.endsWith('/orders') && request.method === 'POST') {
        const config = body.order_configuration.sor_limit_ioc;
        const gross = decimal(config.base_size) * decimal(config.limit_price) / SCALE;
        const order = { order_id: crypto.randomUUID(), client_order_id: body.client_order_id, retail_portfolio_id: PORTFOLIO, product_id: body.product_id, side: body.side,
          order_configuration: body.order_configuration, status: 'FILLED', filled_size: config.base_size, filled_value: decimalText(gross), total_fees: '0.1' };
        orders.push(order);
        if (change.loseSubmission) { response.destroy(); return; }
        result = { success: true, success_response: { order_id: order.order_id, client_order_id: order.client_order_id } };
      } else { response.writeHead(501, { 'Content-Type': 'application/json' }); response.end(JSON.stringify({ error: 'unmodeled_endpoint' })); return; }
      response.writeHead(200, { 'Content-Type': 'application/json' }); response.end(JSON.stringify(result));
    } catch (error) {
      response.writeHead(500, { 'Content-Type': 'application/json' }); response.end(JSON.stringify({ error: 'provider_fixture_assertion' }));
      change.fixtureError = error;
    }
  });
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  t.after(async () => { server.closeAllConnections(); server.close(); await once(server, 'close'); if (change.fixtureError) throw change.fixtureError; });
  const transport = request => {
    const target = new URL(request.url); target.protocol = 'http:'; target.hostname = '127.0.0.1'; target.port = String(server.address().port);
    return fetch(target, { method: request.method, headers: request.headers, body: request.body, duplex: 'half', signal: request.signal, redirect: 'error' });
  };
  return { calls, orders, transport };
}
async function setup(t, options = {}) {
  const { credentials, pair } = await signing(); const upstream = await provider(t, pair, options.provider || {});
  const env = environment(); const user = await seedUser(env); const stores = new Map(); const instances = new Map();
  Object.assign(env, { EXECUTOR_TOKEN: base64url(crypto.getRandomValues(new Uint8Array(32))), EXECUTOR_VAULT_KEY: base64url(crypto.getRandomValues(new Uint8Array(32))),
    COINBASE_EXECUTION_ENABLED: 'true', LIVE_EXECUTION_ENABLED: 'true', EXECUTOR_AVAILABLE_VENUES: '["coinbase"]', EXECUTOR_RECONCILIATION_ENABLED: 'true' });
  env.CUSTOMER_EXECUTORS = { getByName(name) {
    if (!stores.has(name)) stores.set(name, new Storage());
    if (!instances.has(name)) { const instance = new CustomerExecutor({ storage: stores.get(name) }, env); instance.client = value => new Coinbase(value, upstream.transport); instances.set(name, instance); }
    return instances.get(name);
  } };
  env.USER_TRADE_EXECUTOR = { fetch: request => service.fetch(request, env) };
  const clientId = base64url(crypto.getRandomValues(new Uint8Array(32))); const grantId = crypto.randomUUID(); const policy = { venues: ['coinbase'], assets: ['SOL'], maxTradeUsd: 10, maxTotalUsd: options.maxTotalUsd || 10, expiresAt: at() + 3600 };
  const policyJson = JSON.stringify(policy); const policyHash = await digest(policyJson); const scope = 'status:read trade:prepare trade:submit';
  env.sqlite.prepare('INSERT INTO agent_clients(id,name,redirect_uris,created_at) VALUES (?,?,?,?)').run(clientId, 'Execution fixture', '[]', at());
  env.sqlite.prepare('INSERT INTO agent_grants(id,user_id,client_id,resource,scope,policy_json,policy_hash,created_at,expires_at) VALUES (?,?,?,?,?,?,?,?,?)').run(grantId, user.id, clientId, `${ORIGIN}/mcp`, scope, policyJson, policyHash, at(), policy.expiresAt);
  env.sqlite.prepare("INSERT INTO subscriptions(user_id,stripe_subscription_id,status,period_end,updated_at,plan_id) VALUES (?,?,'active',?,?,'starter')").run(user.id, 'sub_execution_fixture', at() + 3600, at());
  const principal = { user: user.user, grant: { id: grantId, resource: `${ORIGIN}/mcp`, policy_hash: policyHash }, client: { id: clientId }, scopes: new Set(scope.split(' ')) };
  const call = async (path, body, headers = {}) => { const response = await service.fetch(new Request(`https://private.internal${path}`, { method: 'POST', headers: { Authorization: `Bearer ${env.EXECUTOR_TOKEN}`, 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(body) }), env); return { response, data: await response.json() }; };
  const connectionInput = { venue: 'coinbase', ...credentials, portfolioId: PORTFOLIO, idempotencyKey: 'connection-one' };
  const connect = () => call('/v1/connections', { userId: user.id, wallet: user.wallet, input: connectionInput });
  return { env, user, stores, instances, upstream, credentials, principal, call, connect, connectionInput };
}
const trade = key => ({ idempotencyKey: key, venue: 'coinbase', asset: 'SOL', side: 'buy', budgetUsd: 10 });
const entitled = { requireEntitlement: async () => {} };
async function managed(f, connectionId, { quantity = '0.01', other = false, paused = false } = {}) {
  const botId = crypto.randomUUID(); const original = f.env.sqlite.prepare('SELECT * FROM agent_grants WHERE id=?').get(f.principal.grant.id);
  const clientId = other ? base64url(crypto.getRandomValues(new Uint8Array(32))) : f.principal.client.id;
  const grantId = other ? crypto.randomUUID() : f.principal.grant.id;
  if (other) {
    f.env.sqlite.prepare('INSERT INTO agent_clients(id,name,redirect_uris,created_at) VALUES (?,?,?,?)').run(clientId, 'Other managed fixture', '[]', at());
    f.env.sqlite.prepare('INSERT INTO agent_grants(id,user_id,client_id,resource,scope,policy_json,policy_hash,created_at,expires_at,revoked_at) VALUES (?,?,?,?,?,?,?,?,?,?)').run(grantId, f.user.id, clientId, original.resource, original.scope, original.policy_json, original.policy_hash, original.created_at, original.expires_at, paused ? at() : null);
  }
  const config = { version: 1, venue: 'coinbase', asset: 'SOL', product: 'spot', leverage: 1, strategyId: 'rsi', strategyRevision: 'r1', intervalSeconds: 60, budgetUsd: 10 };
  const configHash = await managedConfigHash(config);
  const bindingHash = await managedBindingHash({ botId, configHash, connectionId, principal: { user: f.user.user, client: { id: clientId }, grant: { id: grantId, policy_hash: original.policy_hash } } });
  f.env.sqlite.prepare("INSERT INTO bots(id,user_id,name,coin,strategy,venue,leverage,budget,mode,status,created_at,updated_at) VALUES (?,?,?,'SOL','rsi','coinbase',1,10,'paper',?,?,?)").run(botId, f.user.id, 'Managed provider fixture', paused ? 'paused' : 'configured', at(), at());
  f.env.sqlite.prepare('INSERT INTO managed_bots(bot_id,user_id,wallet,connection_id,client_id,grant_id,config_json,config_hash,binding_hash,enabled,allocation_quantity,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)').run(botId,f.user.id,f.user.wallet,connectionId,clientId,grantId,JSON.stringify(config),configHash,bindingHash,paused?0:1,quantity,at(),at());
  return { botId, grantId, async pending() {
    const id = crypto.randomUUID(); const payload = { venue: 'coinbase', asset: 'SOL', side: 'buy', budgetUsd: 10, product: 'spot', leverage: 1 };
    f.env.sqlite.prepare("INSERT INTO agent_trade_intents(id,user_id,wallet,grant_id,resource,policy_hash,idempotency_key,payload_hash,payload_json,state,reservation_cents,consumed_cents,expires_at,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,'filled',1000,1000,?,?,?)").run(id,f.user.id,f.user.wallet,grantId,original.resource,original.policy_hash,id,await digest(payload),JSON.stringify(payload),at()+300,at(),at());
    f.env.sqlite.prepare('UPDATE managed_bots SET pending_intent_id=? WHERE bot_id=?').run(id,botId); return id;
  } };
}
function paperBots(f, n) {
  for (let i = 0; i < n; i++) f.env.sqlite.prepare("INSERT INTO bots(id,user_id,name,coin,strategy,venue,leverage,budget,mode,status,created_at,updated_at) VALUES (?,?,'Other definition','SOL','rsi','coinbase',1,10,'paper','configured',?,?)").run(crypto.randomUUID(), f.user.id, at(), at());
}

test('ES256 JWT is method/path-bound; only P-256 credentials import', async () => {
  const { credentials, pair } = await signing(); const token = await jwt(credentials, 'GET', '/api/v3/brokerage/accounts');
  const [header, payload, signature] = token.split('.');
  assert.equal(await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, pair.publicKey, Buffer.from(signature, 'base64url'), new TextEncoder().encode(`${header}.${payload}`)), true);
  assert.equal(JSON.parse(Buffer.from(payload, 'base64url')).uri, 'GET api.coinbase.com/api/v3/brokerage/accounts');
  await assert.rejects(importSigningKey('not a key'), { code: 'invalid_credential' });
  const ed = await crypto.subtle.generateKey('Ed25519', true, ['sign', 'verify']); const encoded = Buffer.from(await crypto.subtle.exportKey('pkcs8', ed.privateKey)).toString('base64');
  await assert.rejects(importSigningKey(`-----BEGIN PRIVATE KEY-----\n${encoded}\n-----END PRIVATE KEY-----`), { code: 'invalid_credential' });
});
test('credential encryption binds user wallet connection and key version, never plaintext', async () => {
  const env = { EXECUTOR_VAULT_KEY: base64url(crypto.getRandomValues(new Uint8Array(32))) }; const owner = { userId: 'u', wallet: 'wallet-a' }; const secret = { apiKeyName: NAME, privateKey: 'sensitive-fixture' };
  const encrypted = await seal(env, owner, 'connection', secret); assert.equal(JSON.stringify(encrypted).includes('sensitive-fixture'), false);
  assert.deepEqual(await open(env, owner, 'connection', encrypted), secret);
  await assert.rejects(open(env, { ...owner, wallet: 'wallet-b' }, 'connection', encrypted), { code: 'credential_vault_unavailable' });
  await assert.rejects(open(env, owner, 'other-connection', encrypted), { code: 'credential_vault_unavailable' });
});
test('real HTTP connection proof requires view+trade/no-transfer and binds portfolio', async t => {
  const f = await setup(t); const result = await f.connect(); assert.equal(result.response.status, 201); assert.equal(result.data.connection.portfolioId, PORTFOLIO);
  const serialized = JSON.stringify([...f.stores.values()].flatMap(store => [...store.values.values()]));
  assert.equal(serialized.includes(f.credentials.privateKey), false); assert.equal(JSON.stringify(result.data).includes(NAME), false);
  assert.equal((await f.connect()).data.connection.id, result.data.connection.id);
  const before = f.upstream.calls.length; const wrong = await f.call('/v1/connections/list', { userId: f.user.id, wallet: '11111111111111111111111111111111' });
  assert.equal(wrong.response.status, 403); assert.equal(f.upstream.calls.length, before);
});
test('broader transfer permission and wrong portfolio refuse before credential persistence', async t => {
  for (const permissions of [{ ...permission, can_transfer: true }, { ...permission, portfolio_uuid: crypto.randomUUID() }, { ...permission, can_trade: false }]) {
    const f = await setup(t, { provider: { permissions } }); const result = await f.connect(); assert.equal(result.response.status, 403);
    assert.equal(f.env.sqlite.prepare('SELECT COUNT(*) AS n FROM customer_execution_connections').get().n, 0);
    assert.ok([...f.stores.values()].every(store => ![...store.values.keys()].some(key => key.startsWith('credential:'))));
  }
});
test('private service refuses missing bearer and browser Origin', async t => {
  const f = await setup(t);
  const missing = await service.fetch(new Request('https://private.internal/health'), f.env); assert.equal(missing.status, 401);
  const browser = await f.call('/v1/connections/list', { userId: f.user.id, wallet: f.user.wallet }, { Origin: ORIGIN }); assert.equal(browser.response.status, 403);
  assert.equal(f.upstream.calls.length, 0);
});
test('health refuses malformed encryption keys and reports per-venue capability', async t => {
  const f = await setup(t);
  const health = () => service.fetch(new Request('https://private.internal/health', { headers: { Authorization: `Bearer ${f.env.EXECUTOR_TOKEN}` } }), f.env).then(response => response.json());
  assert.equal((await health()).status, 'ready');
  for (const value of ['', 'malformed', base64url(new Uint8Array(31)), base64url(new Uint8Array(33))]) {
    f.env.EXECUTOR_VAULT_KEY = value; const result = await health();
    assert.equal(result.status, 'unconfigured'); assert.equal(result.venues.jupiter.enabled, false);
  }
});
test('deletion fence blocks late credential imports and preserves read-only cleanup', async t => {
  let fixture;
  const f = await setup(t, { provider: { async onRequest({ url }) {
    if (url.pathname.endsWith('/accounts')) fixture.env.sqlite.prepare('UPDATE users SET deletion_token=?,deletion_requested_at=? WHERE id=?').run(crypto.randomUUID(), at(), fixture.user.id);
  } } }); fixture = f;
  const refused = await f.connect(); assert.equal(refused.response.status, 409); assert.equal(refused.data.error, 'account_deleting');
  assert.equal(f.env.sqlite.prepare('SELECT COUNT(*) AS n FROM customer_execution_connections').get().n, 0);
  assert.ok([...f.stores.values()].every(store => ![...store.values.keys()].some(key => key.startsWith('credential:'))));
  const cleanup = await f.call('/v1/connections/revoke-all', { userId: f.user.id, wallet: f.user.wallet });
  assert.equal(cleanup.data.credentialsDeleted, true);
  const retry = await f.connect(); assert.equal(retry.response.status, 409);
  assert.ok([...f.stores.values()].every(store => store.values.size === 0));
});
test('deletion fence appearing at final preview prevents signer admission and allows reconciliation', async t => {
  let fixture; let previews = 0;
  const f = await setup(t, { provider: { async onRequest({ url }) {
    if (url.pathname.endsWith('/orders/preview') && ++previews === 2) fixture.env.sqlite.prepare('UPDATE users SET deletion_token=?,deletion_requested_at=? WHERE id=?').run(crypto.randomUUID(), at(), fixture.user.id);
  } } }); fixture = f; await f.connect();
  const prepared = await requestTrade(f.env, f.principal, trade('deleting-race'), entitled);
  assert.equal((await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled)).state, 'unknown');
  assert.equal(f.upstream.orders.length, 0);
  assert.equal(f.env.sqlite.prepare('SELECT executor_admission_id FROM agent_trade_intents WHERE id=?').get(prepared.id).executor_admission_id, null);
  assert.equal((await reconcileCustomerTrade(f.env, f.user.user, prepared.id)).state, 'failed');
  assert.equal((await f.call('/v1/connections/revoke-all', { userId: f.user.id, wallet: f.user.wallet })).data.credentialsDeleted, true);
});
test('actual edge/service/HTTP path sends once, reconciles fill and retains cumulative consumption', async t => {
  const f = await setup(t); assert.equal((await f.connect()).response.status, 201);
  const prepared = await requestTrade(f.env, f.principal, trade('one-order'), entitled); assert.equal(prepared.state, 'prepared');
  assert.ok(prepared.quote.maxSpendUsd <= 10); assert.ok(prepared.quote.feesUsd > 0);
  const attempts = await Promise.all([submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled), submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled)]);
  assert.ok(attempts.some(row => row.state === 'submitted')); assert.equal(f.upstream.calls.filter(row => row.path.endsWith('/orders') && row.method === 'POST').length, 1);
  const filled = await getTradeStatus(f.env, f.principal, { intentId: prepared.id }); assert.equal(filled.state, 'filled'); assert.equal(filled.consumedBudgetUsd, 10); assert.ok(Number(filled.filled.quantity) > 0);
  await assert.rejects(requestTrade(f.env, f.principal, trade('next-order'), entitled), { code: 'policy_limit' });
});
test('lost response remains unknown and reconciliation discovers original order without retry', async t => {
  const f = await setup(t, { provider: { loseSubmission: true } }); await f.connect();
  const prepared = await requestTrade(f.env, f.principal, trade('lost-order'), entitled);
  const unknown = await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled); assert.equal(unknown.state, 'unknown');
  await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled);
  assert.equal(f.upstream.calls.filter(row => row.path.endsWith('/orders') && row.method === 'POST').length, 1);
  const result = await getTradeStatus(f.env, f.principal, { intentId: prepared.id }); assert.equal(result.state, 'filled'); assert.equal(result.consumedBudgetUsd, 10);
  assert.equal(f.upstream.calls.filter(row => row.path.endsWith('/orders') && row.method === 'POST').length, 1);
});
test('grant revocation, plan loss and connection revocation during preview stop the send', async t => {
  for (const kind of ['grant', 'plan', 'connection']) {
    let fixture; let previews = 0;
    const f = await setup(t, { provider: { async onRequest({ url }) {
      if (!url.pathname.endsWith('/orders/preview') || ++previews !== 2) return;
      if (kind === 'grant') fixture.env.sqlite.prepare('UPDATE agent_grants SET revoked_at=? WHERE id=?').run(at(), fixture.principal.grant.id);
      if (kind === 'plan') fixture.env.sqlite.prepare("UPDATE subscriptions SET status='canceled' WHERE user_id=?").run(fixture.user.id);
      if (kind === 'connection') fixture.env.sqlite.prepare('UPDATE customer_execution_connections SET revoked_at=? WHERE user_id=?').run(at(), fixture.user.id);
    } } }); fixture = f;
    await f.connect(); const prepared = await requestTrade(f.env, f.principal, trade(`revoke-${kind}`), entitled);
    const result = await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled); assert.equal(result.state, 'unknown');
    assert.equal(f.upstream.calls.filter(row => row.path.endsWith('/orders') && row.method === 'POST').length, 0);
    const settled = await reconcileCustomerTrade(f.env, f.user.user, prepared.id); assert.equal(settled.state, 'failed'); assert.equal(settled.consumedBudgetUsd, 0);
  }
});
test('status reconciliation works after subscription loss while new risk refuses independently', async t => {
  const f = await setup(t); await f.connect(); const prepared = await requestTrade(f.env, f.principal, trade('paid-order'), entitled);
  await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled);
  f.env.sqlite.prepare("UPDATE subscriptions SET status='canceled' WHERE user_id=?").run(f.user.id);
  const result = await getTradeStatus(f.env, f.principal, { intentId: prepared.id }); assert.equal(result.state, 'filled');
  await assert.rejects(requestTrade(f.env, f.principal, trade('unpaid-order'), entitled), { code: 'policy_limit' });
});
test('expired membership permits only explicitly reduced owned Coinbase spot inventory', async t => {
  const f = await setup(t); await f.connect();
  f.env.sqlite.prepare("UPDATE subscriptions SET status='canceled' WHERE user_id=?").run(f.user.id);
  const unpaid = { requireEntitlement: async () => { throw Object.assign(new Error('subscription_required'), { code: 'subscription_required' }); } };
  for (const input of [trade('unpaid-buy'), { ...trade('unpaid-sell'), side: 'sell' }]) {
    await assert.rejects(requestTrade(f.env, f.principal, input, unpaid), { code: 'subscription_required' });
  }
  const prepared = await requestTrade(f.env, f.principal, { ...trade('protective-sale'), side: 'sell', reduceOnly: true }, unpaid);
  assert.equal(prepared.state, 'prepared'); assert.equal(prepared.trade.reduceOnly, true);
  const submitted = await submitTrade(f.env, f.principal, { intentId: prepared.id }, unpaid); assert.equal(submitted.state, 'submitted');
  assert.equal(f.upstream.orders.length, 1); assert.equal(f.upstream.orders[0].side, 'SELL');
  assert.ok(decimal(f.upstream.orders[0].order_configuration.sor_limit_ioc.base_size) <= decimal('10000'));
  const filled = await getTradeStatus(f.env, f.principal, { intentId: prepared.id }); assert.equal(filled.state, 'filled');
  await assert.rejects(requestTrade(f.env, f.principal, { ...trade('cannot-evade-cap'), side: 'sell', reduceOnly: true }, unpaid), { code: 'policy_limit' });
});
test('reduce-only does not widen products, leverage, venue or order direction', async t => {
  const f = await setup(t); await f.connect();
  for (const changed of [{ side: 'buy' }, { venue: 'jupiter' }, { product: 'perpetual', side: 'short' }, { leverage: 2 }, { reduceOnly: 'true' }, { reduceOnly: null }, { product: null }]) {
    await assert.rejects(requestTrade(f.env, f.principal, { ...trade('invalid-reduce-only'), side: 'sell', reduceOnly: true, ...changed }, entitled), { code: 'invalid_trade' });
  }
  assert.equal(f.env.sqlite.prepare('SELECT COUNT(*) AS n FROM agent_trade_intents').get().n, 0); assert.equal(f.upstream.orders.length, 0);
});
test('a managed allocation cap floors native sell size and never consumes the other available inventory', async t => {
  const f = await setup(t); await f.connect();
  const prepared = await requestTrade(f.env, f.principal, { ...trade('allocated-sale'), side: 'sell', reduceOnly: true, maxBaseQuantity: '0.0100900' }, entitled);
  assert.equal(prepared.trade.maxBaseQuantity, '0.01009'); assert.equal(prepared.quote.quantity, 0.01); assert.ok(prepared.quote.maxSpendUsd < 10);
  assert.equal((await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled)).state, 'submitted');
  assert.equal(f.upstream.orders[0].order_configuration.sor_limit_ioc.base_size, '0.01');
  const filled = await getTradeStatus(f.env, f.principal, { intentId: prepared.id }); assert.equal(filled.filled.quantity, '0.01');
});
test('quantity caps require strictly positive ordinary decimals and explicit reduced spot inventory', async t => {
  const f = await setup(t); await f.connect();
  for (const changed of [{ maxBaseQuantity: '0' }, { maxBaseQuantity: '-1' }, { maxBaseQuantity: '1e-3' }, { maxBaseQuantity: '0.0000000000000000001' }, { maxBaseQuantity: 1 }, { maxBaseQuantity: null }, { reduceOnly: false }, { side: 'buy' }]) {
    await assert.rejects(requestTrade(f.env, f.principal, { ...trade('invalid-cap'), side: 'sell', reduceOnly: true, maxBaseQuantity: '0.01', ...changed }, entitled), { code: 'invalid_trade' });
  }
  await assert.rejects(requestTrade(f.env, f.principal, { ...trade('below-step-cap'), side: 'sell', reduceOnly: true, maxBaseQuantity: '0.00001' }, entitled), { code: 'preparation_unverified' });
  assert.equal(f.upstream.orders.length, 0);
});
test('managed sales protect every allocation including paused bots after external inventory depletion', async t => {
  for (const failureAt of [2, 3]) {
    let reads = 0;
    const f = await setup(t, { provider: { async onRequest({ url, response }) {
      if (!url.pathname.endsWith('/accounts') || ++reads !== failureAt) return;
      response.writeHead(200, { 'Content-Type': 'application/json' }); response.end(JSON.stringify({ accounts: [{ currency: 'SOL', retail_portfolio_id: PORTFOLIO, active: true, ready: true, available_balance: { value: '0.015', currency: 'SOL' } }], has_next: false }));
    } } }); const connection = (await f.connect()).data.connection;
    const own = await managed(f, connection.id); await managed(f, connection.id, { other: true, paused: true });
    const input = { ...trade(`aggregate-${failureAt}`), side: 'sell', reduceOnly: true, maxBaseQuantity: '0.01' };
    if (failureAt === 2) await assert.rejects(requestTrade(f.env, f.principal, input, entitled), { code: 'preparation_unverified' });
    else {
      const prepared = await requestTrade(f.env, f.principal, input, entitled);
      f.env.sqlite.prepare('UPDATE managed_bots SET pending_intent_id=? WHERE bot_id=?').run(prepared.id, own.botId);
      assert.equal((await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled)).state, 'unknown');
      assert.equal((await reconcileCustomerTrade(f.env, f.user.user, prepared.id)).state, 'failed');
    }
    assert.equal(f.upstream.orders.length, 0);
  }
});
test('covered managed inventory passes the final atomic snapshot fence and sends only its own allocation', async t => {
  const f = await setup(t); const connection = (await f.connect()).data.connection;
  const own = await managed(f, connection.id); await managed(f, connection.id, { other: true, paused: true });
  const prepared = await requestTrade(f.env, f.principal, { ...trade('covered-managed-sale'), side: 'sell', reduceOnly: true, maxBaseQuantity: '0.01' }, entitled);
  f.env.sqlite.prepare('UPDATE managed_bots SET pending_intent_id=? WHERE bot_id=?').run(prepared.id, own.botId);
  assert.equal((await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled)).state, 'submitted');
  assert.equal(f.upstream.orders.length, 1); assert.equal(f.upstream.orders[0].order_configuration.sor_limit_ioc.base_size, '0.01');
});
test('aggregate managed inventory uses exact decimal arithmetic rather than floating-point sums', async t => {
  let reads = 0;
  const f = await setup(t, { provider: { async onRequest({ url, response }) {
    if (!url.pathname.endsWith('/accounts') || ++reads !== 2) return;
    response.writeHead(200, { 'Content-Type': 'application/json' }); response.end(JSON.stringify({ accounts: [{ currency: 'SOL', retail_portfolio_id: PORTFOLIO, active: true, ready: true, available_balance: { value: '0.020000000000000002', currency: 'SOL' } }], has_next: false }));
  } } }); const connection = (await f.connect()).data.connection;
  await managed(f, connection.id, { quantity: '0.010000000000000001' }); await managed(f, connection.id, { other: true, paused: true, quantity: '0.010000000000000002' });
  await assert.rejects(requestTrade(f.env, f.principal, { ...trade('one-atto-short'), side: 'sell', reduceOnly: true, maxBaseQuantity: '0.01' }, entitled), { code: 'preparation_unverified' });
  assert.equal(f.upstream.orders.length, 0);
});
test('another bot with an already filled but unapplied order holds managed preparation', async t => {
  const f = await setup(t); const connection = (await f.connect()).data.connection;
  await managed(f, connection.id); const other = await managed(f, connection.id, { other: true }); await other.pending();
  const before = f.upstream.calls.length;
  await assert.rejects(requestTrade(f.env, f.principal, { ...trade('other-unapplied'), side: 'sell', reduceOnly: true, maxBaseQuantity: '0.01' }, entitled), { code: 'preparation_unverified' });
  assert.equal(f.upstream.calls.length, before); assert.equal(f.upstream.orders.length, 0);
});
test('final managed admission detects an unapplied other-bot fill arriving after the last balance proof', async t => {
  const f = await setup(t); const connection = (await f.connect()).data.connection;
  const own = await managed(f, connection.id); const other = await managed(f, connection.id, { other: true, paused: true });
  const prepared = await requestTrade(f.env, f.principal, { ...trade('other-fill-race'), side: 'sell', reduceOnly: true, maxBaseQuantity: '0.01' }, entitled);
  f.env.sqlite.prepare('UPDATE managed_bots SET pending_intent_id=? WHERE bot_id=?').run(prepared.id, own.botId);
  const original = f.env.DB.prepare.bind(f.env.DB); let raced = false;
  f.env.DB.prepare = sql => {
    const statement = original(sql);
    if (sql.includes('SET executor_admission_id=')) { const run = statement.run.bind(statement); statement.run = async () => { raced = true; await other.pending(); return run(); }; }
    return statement;
  };
  assert.equal((await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled)).state, 'unknown'); assert.equal(raced, true);
  assert.equal(f.upstream.orders.length, 0); assert.equal((await reconcileCustomerTrade(f.env, f.user.user, prepared.id)).state, 'failed');
});
test('managed ledger caps and enabled state are enforced privately while explicit manual sells stay available', async t => {
  const f = await setup(t); const connection = (await f.connect()).data.connection;
  const own = await managed(f, connection.id);
  await assert.rejects(requestTrade(f.env, f.principal, { ...trade('over-ledger'), side: 'sell', reduceOnly: true, maxBaseQuantity: '0.02' }, entitled), { code: 'preparation_unverified' });
  f.env.sqlite.prepare('UPDATE managed_bots SET enabled=0 WHERE bot_id=?').run(own.botId);
  await assert.rejects(requestTrade(f.env, f.principal, { ...trade('paused-private'), side: 'sell', reduceOnly: true, maxBaseQuantity: '0.01' }, entitled), { code: 'preparation_unverified' });
  const manual = await setup(t); const manualConnection = (await manual.connect()).data.connection;
  await managed(manual, manualConnection.id, { other: true, paused: true, quantity: '100000' });
  const prepared = await requestTrade(manual.env, manual.principal, { ...trade('explicit-manual'), side: 'sell', reduceOnly: true, maxBaseQuantity: '0.01' }, entitled);
  assert.equal((await submitTrade(manual.env, manual.principal, { intentId: prepared.id }, entitled)).state, 'submitted'); assert.equal(manual.upstream.orders.length, 1);
});
test('managed buy admission applies the current canonical plan slot limit and holds a downgrade race', async t => {
  for (const [plan, count, allowed] of [['advanced', 10, true], ['starter', 10, false], ['unlimited', 11, true]]) {
    let fixture; let previews = 0;
    const f = await setup(t, { provider: { async onRequest({ url }) {
      if (url.pathname.endsWith('/orders/preview') && ++previews === 2) fixture.env.sqlite.prepare('UPDATE subscriptions SET plan_id=? WHERE user_id=?').run(plan, fixture.user.id);
    } } }); fixture = f; const connection = (await f.connect()).data.connection;
    const own = await managed(f, connection.id, { quantity: '0' }); paperBots(f, count - 1);
    f.env.sqlite.prepare("UPDATE subscriptions SET plan_id='advanced' WHERE user_id=?").run(f.user.id);
    const prepared = await requestTrade(f.env, f.principal, trade(`slot-race-${plan}`), entitled);
    f.env.sqlite.prepare('UPDATE managed_bots SET pending_intent_id=? WHERE bot_id=?').run(prepared.id, own.botId);
    const result = await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled);
    assert.equal(result.state, allowed ? 'submitted' : 'unknown'); assert.equal(f.upstream.orders.length, allowed ? 1 : 0);
    if (!allowed) assert.equal((await reconcileCustomerTrade(f.env, f.user.user, prepared.id)).state, 'failed');
  }
});
test('over-capacity plans preserve managed protective exits and explicit manual new-risk authority', async t => {
  const f = await setup(t); const connection = (await f.connect()).data.connection; const own = await managed(f, connection.id); paperBots(f, 9);
  f.env.sqlite.prepare("UPDATE subscriptions SET status='canceled',plan_id='starter' WHERE user_id=?").run(f.user.id);
  const prepared = await requestTrade(f.env, f.principal, { ...trade('over-capacity-exit'), side: 'sell', reduceOnly: true, maxBaseQuantity: '0.01' }, entitled);
  f.env.sqlite.prepare('UPDATE managed_bots SET pending_intent_id=? WHERE bot_id=?').run(prepared.id, own.botId);
  assert.equal((await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled)).state, 'submitted');
  const manual = await setup(t); await manual.connect(); paperBots(manual, 10);
  const explicit = await requestTrade(manual.env, manual.principal, trade('manual-after-downgrade'), entitled);
  assert.equal((await submitTrade(manual.env, manual.principal, { intentId: explicit.id }, entitled)).state, 'submitted');
});
test('protective sell refuses insufficient owned balance both before quoting and immediately before send', async t => {
  for (const failureAt of [2, 3]) {
    let accountReads = 0;
    const f = await setup(t, { provider: { async onRequest({ url, response }) {
      if (!url.pathname.endsWith('/accounts') || ++accountReads !== failureAt) return;
      response.writeHead(200, { 'Content-Type': 'application/json' });
      response.end(JSON.stringify({ accounts: [{ currency: 'SOL', retail_portfolio_id: PORTFOLIO, active: true, ready: true, available_balance: { value: '0.00001', currency: 'SOL' } }], has_next: false }));
    } } }); await f.connect();
    f.env.sqlite.prepare("UPDATE subscriptions SET status='canceled' WHERE user_id=?").run(f.user.id);
    const input = { ...trade(`low-inventory-${failureAt}`), side: 'sell', reduceOnly: true };
    if (failureAt === 2) await assert.rejects(requestTrade(f.env, f.principal, input, entitled), { code: 'preparation_unverified' });
    else {
      const prepared = await requestTrade(f.env, f.principal, input, entitled);
      assert.equal((await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled)).state, 'unknown');
      assert.equal((await reconcileCustomerTrade(f.env, f.user.user, prepared.id)).state, 'failed');
    }
    assert.equal(f.upstream.orders.length, 0);
  }
});
test('protective sells still require unexpired wallet authority and current connection', async t => {
  for (const kind of ['expired', 'revoked', 'connection']) {
    const f = await setup(t); await f.connect();
    const prepared = await requestTrade(f.env, f.principal, { ...trade(`protective-${kind}`), side: 'sell', reduceOnly: true }, entitled);
    f.env.sqlite.prepare("UPDATE subscriptions SET status='canceled' WHERE user_id=?").run(f.user.id);
    if (kind === 'expired') { const future = Date.now() + 3601_000; t.mock.method(Date, 'now', () => future); }
    if (kind === 'revoked') f.env.sqlite.prepare('UPDATE agent_grants SET revoked_at=? WHERE id=?').run(at(), f.principal.grant.id);
    if (kind === 'connection') f.env.sqlite.prepare('UPDATE customer_execution_connections SET revoked_at=? WHERE user_id=?').run(at(), f.user.id);
    if (kind === 'connection') assert.equal((await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled)).state, 'unknown');
    else await assert.rejects(submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled), { code: 'authorization_expired' });
    assert.equal(f.upstream.orders.length, 0);
    if (kind === 'expired') t.mock.restoreAll();
  }
});
test('stale market data and unqualified Jupiter refuse without an order', async t => {
  const f = await setup(t, { provider: { bookAge: 60 } }); await f.connect();
  await assert.rejects(requestTrade(f.env, f.principal, trade('stale-order'), entitled), { code: 'preparation_unverified' });
  assert.equal(f.upstream.calls.filter(row => row.path.endsWith('/orders') && row.method === 'POST').length, 0);
  const before = f.env.sqlite.prepare('SELECT COUNT(*) AS n FROM agent_trade_intents').get().n;
  await assert.rejects(requestTrade(f.env, f.principal, { ...trade('jupiter-order'), venue: 'jupiter', product: 'perpetual', side: 'long', leverage: 2 }, entitled), { code: 'policy_limit' });
  assert.equal(f.env.sqlite.prepare('SELECT COUNT(*) AS n FROM agent_trade_intents').get().n, before);
});
test('partial cancellation retains observed fills and cumulative commitment', async t => {
  const f = await setup(t); await f.connect(); const prepared = await requestTrade(f.env, f.principal, trade('partial'), entitled);
  await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled);
  Object.assign(f.upstream.orders[0], { status: 'CANCELLED', filled_size: '0.04', filled_value: '4', total_fees: '0.04' });
  const result = await getTradeStatus(f.env, f.principal, { intentId: prepared.id });
  assert.equal(result.state, 'canceled'); assert.equal(result.filled.venueStatus, 'CANCELLED'); assert.equal(result.filled.quantity, '0.04'); assert.equal(result.consumedBudgetUsd, 10);
  await assert.rejects(requestTrade(f.env, f.principal, trade('after-partial'), entitled), { code: 'policy_limit' });
});
test('authoritative cost overrun is recorded and never releases additional policy budget', async t => {
  const f = await setup(t); await f.connect(); const prepared = await requestTrade(f.env, f.principal, trade('overrun'), entitled);
  await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled);
  f.upstream.orders[0].total_fees = '1';
  const expected = Number(f.upstream.orders[0].filled_value) + 1;
  const result = await getTradeStatus(f.env, f.principal, { intentId: prepared.id });
  assert.equal(result.state, 'filled'); assert.equal(result.budgetExceeded, true); assert.equal(result.error, 'execution_cost_exceeded'); assert.equal(result.consumedBudgetUsd, expected);
  await assert.rejects(requestTrade(f.env, f.principal, trade('after-overrun'), entitled), { code: 'policy_limit' });
});
test('unresolved own submissions block a new venue preparation even with spare budget', async t => {
  const f = await setup(t, { maxTotalUsd: 30 }); await f.connect(); const prepared = await requestTrade(f.env, f.principal, trade('unresolved'), entitled);
  await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled);
  const before = f.upstream.calls.length;
  await assert.rejects(requestTrade(f.env, f.principal, trade('before-reconcile'), entitled), { code: 'preparation_unverified' });
  assert.equal(f.upstream.calls.length, before);
  await getTradeStatus(f.env, f.principal, { intentId: prepared.id });
  assert.equal((await requestTrade(f.env, f.principal, trade('after-reconcile'), entitled)).state, 'prepared');
});
test('atomic signer admission fences a grant revoked after its earlier read', async t => {
  const f = await setup(t); await f.connect(); const prepared = await requestTrade(f.env, f.principal, trade('admission-race'), entitled);
  const original = f.env.DB.prepare.bind(f.env.DB); let changed = false;
  f.env.DB.prepare = sql => {
    const statement = original(sql);
    if (sql.includes('SET executor_admission_id=')) {
      const run = statement.run.bind(statement); statement.run = async () => {
        changed = true; f.env.sqlite.prepare('UPDATE agent_grants SET revoked_at=? WHERE id=?').run(at(), f.principal.grant.id); return run();
      };
    }
    return statement;
  };
  assert.equal((await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled)).state, 'unknown'); assert.equal(changed, true);
  assert.equal(f.upstream.calls.filter(row => row.path.endsWith('/orders') && row.method === 'POST').length, 0);
  assert.equal((await reconcileCustomerTrade(f.env, f.user.user, prepared.id)).state, 'failed');
});
test('an existing admission survives a stale local prepared journal without a resend', async t => {
  const f = await setup(t); await f.connect(); const prepared = await requestTrade(f.env, f.principal, trade('old-admission'), entitled);
  f.env.sqlite.prepare('UPDATE agent_trade_intents SET executor_admission_id=?,executor_admitted_at=? WHERE id=?').run(crypto.randomUUID(), at(), prepared.id);
  assert.equal((await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled)).state, 'unknown');
  assert.equal((await reconcileCustomerTrade(f.env, f.user.user, prepared.id)).state, 'unknown');
  assert.equal(f.upstream.calls.filter(row => row.path.endsWith('/orders') && row.method === 'POST').length, 0);
  assert.equal(f.env.sqlite.prepare('SELECT reservation_cents FROM agent_trade_intents WHERE id=?').get(prepared.id).reservation_cents, 1000);
});
test('revoke-all erases all credential and orphan blobs only when sends are resolved', async t => {
  const f = await setup(t); await f.connect(); const prepared = await requestTrade(f.env, f.principal, trade('erase'), entitled);
  await submitTrade(f.env, f.principal, { intentId: prepared.id }, entitled);
  const blocked = await f.call('/v1/connections/revoke-all', { userId: f.user.id, wallet: f.user.wallet });
  assert.deepEqual(blocked.data, { revoked: true, credentialsDeleted: false, pendingReconciliation: true });
  const store = [...f.stores.values()][0]; assert.equal((await store.list({ prefix: 'credential:' })).size, 1);
  // Revocation stops writes but retains the scoped key for read-only settlement.
  assert.equal((await getTradeStatus(f.env, f.principal, { intentId: prepared.id })).state, 'filled');
  await store.put('credential:orphan-fixture', { encrypted: true });
  const cleared = await f.call('/v1/connections/revoke-all', { userId: f.user.id, wallet: f.user.wallet });
  assert.deepEqual(cleared.data, { revoked: true, credentialsDeleted: true, pendingReconciliation: false }); assert.equal(store.values.size, 0);
  assert.deepEqual((await f.call('/v1/connections/revoke-all', { userId: f.user.id, wallet: f.user.wallet })).data, cleared.data);
});
test('unknown retained encrypted authorities remain bounded before provider calls', async t => {
  const f = await setup(t);
  await f.call('/v1/connections/list', { userId: f.user.id, wallet: f.user.wallet }); const store = [...f.stores.values()][0];
  for (let i = 0; i < 16; i++) await store.put(`credential:${crypto.randomUUID()}`, { encrypted: true });
  const result = await f.connect(); assert.equal(result.response.status, 409); assert.equal(result.data.error, 'connection_limit'); assert.equal(f.upstream.calls.length, 0);
});
test('credential rotations never hit a lifetime lock and historical pages keep active authority reachable', async t => {
  const f = await setup(t); let clock = Date.now(); const beginning = clock; t.mock.method(Date, 'now', () => clock);
  const ids = [];
  for (let i = 0; i < 32; i++) {
    clock = beginning + Math.floor(i / 7) * 86401_000; f.connectionInput.idempotencyKey = `rotation-${i}`;
    const created = await f.connect(); assert.equal(created.response.status, 201); ids.push(created.data.connection.id);
    if (i < 31) assert.equal((await f.call('/v1/connections/revoke', { userId: f.user.id, wallet: f.user.wallet, id: created.data.connection.id })).response.status, 200);
  }
  const store = [...f.stores.values()][0]; assert.equal((await store.list({ prefix: 'credential:' })).size, 1);
  assert.equal(f.env.sqlite.prepare('SELECT COUNT(*) AS n FROM customer_execution_connections').get().n, 32);
  const first = await f.call('/v1/connections/list', { userId: f.user.id, wallet: f.user.wallet }); assert.equal(first.data.connections.length, 26);
  assert.equal(first.data.connections[0].id, ids.at(-1)); assert.ok(first.data.nextCursor);
  const second = await f.call('/v1/connections/list', { userId: f.user.id, wallet: f.user.wallet, cursor: first.data.nextCursor });
  assert.equal(second.data.connections[0].id, ids.at(-1)); assert.equal(second.data.nextCursor, null);
  assert.equal(new Set([...first.data.connections, ...second.data.connections].map(row => row.id)).size, 32);
  const before = f.upstream.calls.length; f.connectionInput.idempotencyKey = 'rotation-0'; const duplicate = await f.connect();
  assert.equal(duplicate.data.connection.id, ids[0]); assert.equal(duplicate.data.connection.status, 'revoked'); assert.equal(f.upstream.calls.length, before);
  for (const cursor of ['not-a-valid-cursor', base64url(new TextEncoder().encode(JSON.stringify({ createdAt: 1, id: 'bad' })))]) {
    assert.equal((await f.call('/v1/connections/list', { userId: f.user.id, wallet: f.user.wallet, cursor })).response.status, 400);
  }
  const cleanup = await f.call('/v1/connections/revoke-all', { userId: f.user.id, wallet: f.user.wallet }); assert.equal(cleanup.data.credentialsDeleted, true); assert.equal(store.values.size, 0);
});
test('rolling import attempts are bounded across failures and recover after 24 hours', async t => {
  const f = await setup(t, { provider: { permissions: { ...permission, can_trade: false } } });
  for (let i = 0; i < 8; i++) { f.connectionInput.idempotencyKey = `failed-attempt-${i}`; assert.equal((await f.connect()).response.status, 403); }
  const before = f.upstream.calls.length; assert.equal((await f.connect()).data.error, 'connection_rate_limit'); assert.equal(f.upstream.calls.length, before);
  const future = Date.now() + 86401_000; t.mock.method(Date, 'now', () => future);
  assert.equal((await f.connect()).response.status, 403); assert.ok(f.upstream.calls.length > before);
});
