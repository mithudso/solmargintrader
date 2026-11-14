import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import worker, { hasEntitlement, validateBot, verifyStripeSignature } from '../src/worker.js';
import { base58Encode } from '../../extension/src/wallet/solana.js';

const ORIGINAL_DIAGNOSTIC_METHODS = { fetch: globalThis.fetch, info: console.info, warn: console.warn, error: console.error };
const ORIGIN = 'https://oraclebot.example';
const at = () => Math.floor(Date.now() / 1000);
function environment() {
  const sqlite = new DatabaseSync(':memory:');
  for (const migration of readdirSync(new URL('../migrations/', import.meta.url)).filter(name => /^\d{4}_.*\.sql$/.test(name)).sort()) sqlite.exec(readFileSync(new URL(`../migrations/${migration}`, import.meta.url), 'utf8'));
  const batches = [];
  const DB = {
    prepare(sql) {
      let args = [];
      return {
        bind(...values) { args = values; return this; },
        async first() { return sqlite.prepare(sql).get(...args) || null; },
        async all() { return { results: sqlite.prepare(sql).all(...args) }; },
        async run() {
          // D1 reports total changes, including trigger/foreign-key cascades.
          // RETURNING rows identify the direct mutation independently of that count.
          const before = sqlite.prepare('SELECT total_changes() AS n').get().n;
          const statement = sqlite.prepare(sql);
          const results = statement.columns().length ? statement.all(...args) : (statement.run(...args), []);
          return { results, meta: { changes: sqlite.prepare('SELECT total_changes() AS n').get().n - before } };
        },
      };
    },
    async batch(statements) {
      sqlite.exec('BEGIN');
      try { const result = []; for (const statement of statements) result.push(await statement.run()); sqlite.exec('COMMIT'); batches.push(result); return result; }
      catch (error) { sqlite.exec('ROLLBACK'); throw error; }
    },
  };
  return { DB, sqlite, batches, APP_ORIGIN: ORIGIN };
}
function request(path, { method = 'GET', body, cookie, origin = ORIGIN, headers = {} } = {}) {
  return new Request(`${ORIGIN}${path}`, { method, headers: { ...(method !== 'GET' ? { Origin: origin } : {}), ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...(cookie ? { Cookie: cookie } : {}), ...headers }, body: body === undefined ? undefined : JSON.stringify(body) });
}
async function call(env, path, options) {
  const response = await worker.fetch(request(path, options), env);
  return { response, data: await response.json() };
}
async function keypair() {
  const keys = await crypto.subtle.generateKey('Ed25519', true, ['sign', 'verify']);
  const wallet = base58Encode(new Uint8Array(await crypto.subtle.exportKey('raw', keys.publicKey)));
  return { keys, wallet };
}
async function login(env, identity = null) {
  const { keys, wallet } = identity || await keypair();
  const challenge = await call(env, '/api/auth/challenge', { method: 'POST', body: { wallet } });
  assert.equal(challenge.response.status, 200);
  const signature = Buffer.from(await crypto.subtle.sign('Ed25519', keys.privateKey, new TextEncoder().encode(challenge.data.message))).toString('base64');
  const verified = await call(env, '/api/auth/verify', { method: 'POST', body: { id: challenge.data.id, signature } });
  assert.equal(verified.response.status, 200);
  return { ...verified.data, wallet, cookie: verified.response.headers.get('Set-Cookie').split(';')[0], challenge: challenge.data, signature };
}
function grant(env, user, status = 'trialing', plan = 'starter') {
  env.sqlite.prepare('INSERT INTO subscriptions (user_id,stripe_subscription_id,status,period_end,trial_end,updated_at,plan_id) VALUES (?,?,?,?,?,?,?)').run(user.id, `sub_${user.id.replaceAll('-', '')}`, status, at() + 86400, at() + 86400, at(), plan);
}
const bot = { name: 'SOL momentum', coin: 'SOL', strategy: 'rsi', venue: 'coinbase', leverage: 1, budget: 100, mode: 'paper' };

test('health reports external integrations accurately without secrets', async () => {
  const { data } = await call({}, '/api/health');
  assert.equal(data.storage, false); assert.equal(data.billing, false); assert.equal(data.engine, false); assert.equal(data.liveExecution, false);
});
test('config and anonymous account work before external setup', async () => {
  const { data } = await call({}, '/api/config');
  assert.equal(data.trialDays, 7); assert.equal(data.billingConfigured, false);
  assert.equal((await call({}, '/api/me')).data.user, null);
});
test('all responses send restrictive security headers', async () => {
  const { response } = await call({}, '/api/health');
  assert.equal(response.headers.get('X-Content-Type-Options'), 'nosniff');
  assert.match(response.headers.get('Content-Security-Policy'), /frame-ancestors 'none'/);
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
});
test('cross-origin and unexpected hosts fail before database writes', async () => {
  const env = environment();
  assert.equal((await call(env, '/api/auth/challenge', { method: 'POST', origin: 'https://evil.example', body: {} })).response.status, 403);
  const response = await worker.fetch(new Request('https://evil.example/api/health'), env);
  assert.equal(response.status, 403);
});
test('wallet challenge binds domain and refuses malformed public keys', async () => {
  const env = environment();
  const bad = await call(env, '/api/auth/challenge', { method: 'POST', body: { wallet: '0'.repeat(32) } });
  assert.equal(bad.response.status, 400);
  const good = await call(env, '/api/auth/challenge', { method: 'POST', body: { wallet: (await keypair()).wallet } });
  assert.match(good.data.message, /oraclebot.example wants you to sign in/);
  assert.match(good.data.message, /does not authorize transactions/);
});
test('wallet signature establishes account with hashed HttpOnly session', async () => {
  const env = environment(); const logged = await login(env);
  const { data } = await call(env, '/api/me', { cookie: logged.cookie });
  assert.equal(data.user.wallet, logged.wallet); assert.equal(data.subscription, null);
  const session = env.sqlite.prepare('SELECT * FROM sessions').get();
  assert.equal(session.token_hash.length, 64); assert.notEqual(session.token_hash, logged.cookie.split('=')[1]);
});
test('wallet signature challenge cannot be replayed', async () => {
  const env = environment(); const logged = await login(env);
  const result = await call(env, '/api/auth/verify', { method: 'POST', body: { id: logged.challenge.id, signature: logged.signature } });
  assert.equal(result.response.status, 401); assert.equal(result.data.error, 'challenge_expired_or_used');
});
test('signature for another wallet fails and consumes the challenge', async () => {
  const env = environment(); const first = await keypair(); const other = await keypair();
  const challenge = (await call(env, '/api/auth/challenge', { method: 'POST', body: { wallet: first.wallet } })).data;
  const signature = Buffer.from(await crypto.subtle.sign('Ed25519', other.keys.privateKey, new TextEncoder().encode(challenge.message))).toString('base64');
  const result = await call(env, '/api/auth/verify', { method: 'POST', body: { id: challenge.id, signature } });
  assert.equal(result.data.error, 'invalid_signature');
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM sessions').get().n, 0);
  assert.equal((await call(env, '/api/auth/verify', { method: 'POST', body: { id: challenge.id, signature } })).data.error, 'challenge_expired_or_used');
});
test('expired challenges and sessions refuse access', async () => {
  const env = environment(); const logged = await login(env);
  env.sqlite.prepare('UPDATE sessions SET expires_at = 1').run();
  assert.equal((await call(env, '/api/bots', { cookie: logged.cookie })).response.status, 401);
  const challenge = (await call(env, '/api/auth/challenge', { method: 'POST', body: { wallet: logged.wallet } })).data;
  env.sqlite.prepare('UPDATE challenges SET expires_at = 1 WHERE id = ?').run(challenge.id);
  assert.equal((await call(env, '/api/auth/verify', { method: 'POST', body: { id: challenge.id, signature: logged.signature } })).response.status, 401);
});
test('consumed challenges still count toward per-IP rate limit', async () => {
  const env = environment(); const logged = await login(env);
  for (let i = 0; i < 19; i++) assert.equal((await call(env, '/api/auth/challenge', { method: 'POST', body: { wallet: logged.wallet } })).response.status, 200);
  assert.equal((await call(env, '/api/auth/challenge', { method: 'POST', body: { wallet: logged.wallet } })).response.status, 429);
});
test('logout revokes database session and clears secure cookie', async () => {
  const env = environment(); const logged = await login(env);
  const result = await call(env, '/api/auth/logout', { method: 'POST', cookie: logged.cookie });
  assert.match(result.response.headers.get('Set-Cookie'), /HttpOnly; Secure; SameSite=Lax; Max-Age=0/);
  assert.equal((await call(env, '/api/me', { cookie: logged.cookie })).data.user, null);
});
test('bot and backtest writes require authenticated paid or trial entitlement', async () => {
  const env = environment();
  assert.equal((await call(env, '/api/bots', { method: 'POST', body: bot })).response.status, 401);
  const logged = await login(env);
  assert.equal((await call(env, '/api/bots', { method: 'POST', cookie: logged.cookie, body: bot })).response.status, 402);
  assert.equal((await call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: {} })).response.status, 402);
});
test('trial entitlement expires and invalid billing status fails closed', () => {
  assert.equal(hasEntitlement({ status: 'trialing', trial_end: 100 }, 99), true);
  assert.equal(hasEntitlement({ status: 'trialing', trial_end: 100 }, 100), false);
  assert.equal(hasEntitlement({ status: 'past_due', period_end: 200 }, 99), false);
  assert.equal(hasEntitlement({ status: 'active', period_end: NaN }, 99), false);
});
test('bot configuration is tenant scoped and never claims live execution', async () => {
  const env = environment(); const alice = await login(env); const bob = await login(env); grant(env, alice.user); grant(env, bob.user);
  const created = await call(env, '/api/bots', { method: 'POST', cookie: alice.cookie, body: bot });
  assert.equal(created.response.status, 201); assert.equal(created.data.bot.status, 'configured'); assert.equal(created.data.bot.executionReady, false);
  assert.equal('user_id' in created.data.bot, false);
  assert.equal((await call(env, '/api/bots', { cookie: bob.cookie })).data.bots.length, 0);
  assert.equal((await call(env, `/api/bots/${created.data.bot.id}`, { method: 'PATCH', cookie: bob.cookie, body: { status: 'archived' } })).response.status, 404);
  assert.equal((await call(env, `/api/bots/${created.data.bot.id}`, { method: 'PATCH', cookie: alice.cookie, body: { status: 'paused' } })).data.bot.status, 'paused');
});
test('live mode, nonfinite risk values and Coinbase leverage are refused', () => {
  assert.throws(() => validateBot({ ...bot, mode: 'live' }), /Live execution/);
  assert.throws(() => validateBot({ ...bot, budget: NaN }), /invalid_number/);
  assert.throws(() => validateBot({ ...bot, leverage: 2 }), /invalid_number/);
  assert.throws(() => validateBot({ ...bot, venue: 'jupiter', leverage: 100 }), /invalid_number/);
});
test('billing stays disabled without complete configuration', async () => {
  const env = environment(); const logged = await login(env);
  const result = await call(env, '/api/billing/checkout', { method: 'POST', body: { plan: 'starter' }, cookie: logged.cookie });
  assert.equal(result.response.status, 503); assert.equal(result.data.error, 'billing_unavailable');
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM subscriptions').get().n, 0);
});
test('forged webhook cannot mutate subscriptions', async () => {
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_STARTER_PRICE_ID: 'price_server', STRIPE_ADVANCED_PRICE_ID: 'price_advanced', STRIPE_UNLIMITED_PRICE_ID: 'price_unlimited', STRIPE_PORTAL_CONFIGURATION_ID: 'bpc_test', BILLING_LAUNCH_ENABLED: 'true' };
  const response = await call(env, '/api/billing/webhook', { method: 'POST', body: { id: 'evt_bad', type: 'customer.subscription.created' }, headers: { 'Stripe-Signature': `t=${at()},v1=${'0'.repeat(64)}` } });
  assert.equal(response.response.status, 400); assert.equal(response.data.error, 'invalid_webhook_signature');
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM stripe_events').get().n, 0);
});
async function signedEvent(event, secret, timestamp = at()) {
  const raw = JSON.stringify(event);
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const signature = Buffer.from(await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(`${timestamp}.${raw}`))).toString('hex');
  return { raw, header: `t=${timestamp},v1=${signature}` };
}
test('Stripe HMAC requires exact raw body and fresh timestamp', async () => {
  const signed = await signedEvent({ id: 'evt_valid' }, 'secret');
  assert.equal(await verifyStripeSignature(signed.raw, signed.header, 'secret'), true);
  assert.equal(await verifyStripeSignature(`${signed.raw} `, signed.header, 'secret'), false);
  assert.equal(await verifyStripeSignature(signed.raw, signed.header, 'wrong'), false);
  assert.equal(await verifyStripeSignature(signed.raw, signed.header, 'secret', at() + 301), false);
});
test('missing engine and unsupported coins never produce made-up forecasts', async () => {
  const env = environment();
  assert.equal((await call(env, '/api/oracle?coin=SOL')).data.error, 'engine_unavailable');
  assert.equal((await call(env, '/api/oracle?coin=NOPE')).response.status, 400);
});
test('oversized JSON request is refused before parsing', async () => {
  const env = environment();
  assert.equal((await call(env, '/api/auth/challenge', { method: 'POST', body: { wallet: 'x'.repeat(17000) } })).response.status, 413);
});
test('scheduled cleanup removes expired state and retains recent consumed challenges', async () => {
  const env = environment(); await login(env);
  env.sqlite.prepare("INSERT INTO challenges VALUES ('old','wallet','message','origin','ip',1,0)").run();
  await worker.scheduled({}, env);
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM challenges').get().n, 1);
});

test('www redirects to configured canonical origin with path and query intact', async () => {
  const response = await worker.fetch(new Request('https://www.oraclebot.example/research?topic=fees'), environment());
  assert.equal(response.status, 308);
  assert.equal(response.headers.get('Location'), 'https://oraclebot.example/research?topic=fees');
});
test('account deletion clears owned data and sessions, requiring cancellation first', async () => {
  const env = environment(); const logged = await login(env); grant(env, logged.user);
  const create = await call(env, '/api/bots', { method: 'POST', cookie: logged.cookie, body: bot });
  assert.equal(create.response.status, 201);
  assert.equal((await call(env, '/api/me', { method: 'DELETE', cookie: logged.cookie })).response.status, 409);
  env.sqlite.prepare("UPDATE subscriptions SET status='canceled'").run();
  env.sqlite.prepare('UPDATE users SET trial_used=1').run();
  const result = await call(env, '/api/me', { method: 'DELETE', cookie: logged.cookie });
  assert.equal(result.data.deleted, true);
  assert.ok(env.batches.at(-1)[1].meta.changes > 1, 'D1 change count includes cascaded sessions, bots and subscription');
  assert.equal(env.batches.at(-1)[1].results[0].id, logged.user.id);
  for (const table of ['users', 'sessions', 'bots', 'subscriptions']) assert.equal(env.sqlite.prepare(`SELECT COUNT(*) AS n FROM ${table}`).get().n, 0);
  const ledger = env.sqlite.prepare('SELECT * FROM trial_history').get();
  assert.equal(ledger.wallet_hash.length, 64); assert.notEqual(ledger.wallet_hash, logged.wallet);
});
test('webhook reconciles canonical subscription once and refuses out-of-order regressions', async t => {
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_STARTER_PRICE_ID: 'price_server', STRIPE_ADVANCED_PRICE_ID: 'price_advanced', STRIPE_UNLIMITED_PRICE_ID: 'price_unlimited', STRIPE_PORTAL_CONFIGURATION_ID: 'bpc_test', BILLING_LAUNCH_ENABLED: 'true' };
  const logged = await login(env);
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_test', logged.user.id);
  let calls = 0;
  let current = { id: 'sub_test', customer: 'cus_test', status: 'trialing', created: 50, trial_start: 80, trial_end: at() + 604800, current_period_end: at() + 604800, items: { data: [{ price: { id: 'price_server' }, quantity: 1 }] }, metadata: { oraclebot_user: logged.user.id } };
  t.mock.method(globalThis, 'fetch', async url => { calls++; assert.equal(url, 'https://api.stripe.com/v1/subscriptions/sub_test'); return Response.json(current); });
  async function deliver(id, created, status) {
    const signed = await signedEvent({ id, created, type: 'customer.subscription.updated', data: { object: { id: 'sub_test', status } } }, env.STRIPE_WEBHOOK_SECRET);
    return worker.fetch(new Request(`${ORIGIN}/api/billing/webhook`, { method: 'POST', headers: { 'Stripe-Signature': signed.header }, body: signed.raw }), env);
  }
  assert.equal((await deliver('evt_1', 100, 'active')).status, 200);
  let sub = env.sqlite.prepare('SELECT * FROM subscriptions').get();
  assert.equal(sub.status, 'trialing'); assert.equal(hasEntitlement(sub), true);
  assert.equal((await deliver('evt_1', 100, 'active')).status, 200); assert.equal(calls, 1);
  current = { ...current, status: 'canceled' };
  assert.equal((await deliver('evt_3', 300, 'trialing')).status, 200);
  sub = env.sqlite.prepare('SELECT * FROM subscriptions').get(); assert.equal(sub.status, 'canceled');
  // An earlier in-flight read must not overwrite a newer cancellation.
  current = { ...current, status: 'active' };
  assert.equal((await deliver('evt_2', 200, 'active')).status, 200);
  sub = env.sqlite.prepare('SELECT * FROM subscriptions').get(); assert.equal(sub.status, 'canceled'); assert.equal(hasEntitlement(sub), false);
  assert.equal(env.sqlite.prepare('SELECT trial_used FROM users').get().trial_used, 1);
});
test('webhook for an unknown Stripe customer never grants account access', async t => {
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_STARTER_PRICE_ID: 'price_server', STRIPE_ADVANCED_PRICE_ID: 'price_advanced', STRIPE_UNLIMITED_PRICE_ID: 'price_unlimited', STRIPE_PORTAL_CONFIGURATION_ID: 'bpc_test', BILLING_LAUNCH_ENABLED: 'true' };
  await login(env);
  t.mock.method(globalThis, 'fetch', async () => Response.json({ id: 'sub_unknown', customer: 'cus_unknown', status: 'active', metadata: {} }));
  const signed = await signedEvent({ id: 'evt_unknown', created: 100, type: 'customer.subscription.created', data: { object: { id: 'sub_unknown' } } }, env.STRIPE_WEBHOOK_SECRET);
  const response = await worker.fetch(new Request(`${ORIGIN}/api/billing/webhook`, { method: 'POST', headers: { 'Stripe-Signature': signed.header }, body: signed.raw }), env);
  assert.equal(response.status, 200); assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM subscriptions').get().n, 0);
});
test('Stripe checkout sends a server-owned price and a seven-day first trial', async t => {
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_STARTER_PRICE_ID: 'price_server', STRIPE_ADVANCED_PRICE_ID: 'price_advanced', STRIPE_UNLIMITED_PRICE_ID: 'price_unlimited', STRIPE_PORTAL_CONFIGURATION_ID: 'bpc_test', BILLING_LAUNCH_ENABLED: 'true' };
  const logged = await login(env); const paths = [];
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    paths.push(new URL(url).pathname);
    if (url.endsWith('/customers')) return Response.json({ id: 'cus_test' });
    if (url.includes('/subscriptions?')) return Response.json({ data: [], has_more: false });
    assert.equal(url, 'https://api.stripe.com/v1/checkout/sessions');
    const fields = options.body;
    assert.equal(fields.get('subscription_data[trial_period_days]'), '7');
    assert.equal(fields.get('line_items[0][price]'), 'price_server');
    const pendingAt = env.sqlite.prepare('SELECT checkout_pending_at FROM users WHERE id=?').get(logged.user.id).checkout_pending_at;
    assert.equal(Number(fields.get('expires_at')), pendingAt + 2100);
    assert.equal(fields.get('subscription_data[metadata][oraclebot_user]'), logged.user.id);
    return Response.json({ url: 'https://checkout.stripe.com/c/pay/session' });
  });
  assert.equal((await call(env, '/api/billing/checkout', { method: 'POST', cookie: logged.cookie, body: { plan: 'starter', price: 'price_attacker', trialDays: 900 } })).response.status, 400);
  const result = await call(env, '/api/billing/checkout', { method: 'POST', body: { plan: 'starter' }, cookie: logged.cookie });
  assert.equal(result.response.status, 200); assert.equal(result.data.trialDays, 7); assert.equal(paths.length, 3);
  assert.equal((await call(env, '/api/billing/checkout', { method: 'POST', body: { plan: 'starter' }, cookie: logged.cookie })).response.status, 409);
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM subscriptions').get().n, 0);
});
test('used trials cannot be renewed by another checkout request', async t => {
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_STARTER_PRICE_ID: 'price_server', STRIPE_ADVANCED_PRICE_ID: 'price_advanced', STRIPE_UNLIMITED_PRICE_ID: 'price_unlimited', STRIPE_PORTAL_CONFIGURATION_ID: 'bpc_test', BILLING_LAUNCH_ENABLED: 'true' };
  const logged = await login(env);
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=?,trial_used=1 WHERE id=?').run('cus_test', logged.user.id);
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    if (url.includes('/subscriptions?')) return Response.json({ data: [{ status: 'canceled', trial_start: 1 }], has_more: false });
    assert.equal(options.body.has('subscription_data[trial_period_days]'), false);
    return Response.json({ url: 'https://checkout.stripe.com/c/pay/session' });
  });
  const result = await call(env, '/api/billing/checkout', { method: 'POST', body: { plan: 'starter' }, cookie: logged.cookie });
  assert.equal(result.response.status, 200); assert.equal(result.data.trialDays, 0);
});
test('expired trial and billing provider failure never produce backtest access', async t => {
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_STARTER_PRICE_ID: 'price_server', STRIPE_ADVANCED_PRICE_ID: 'price_advanced', STRIPE_UNLIMITED_PRICE_ID: 'price_unlimited', STRIPE_PORTAL_CONFIGURATION_ID: 'bpc_test', BILLING_LAUNCH_ENABLED: 'true' };
  const logged = await login(env); grant(env, logged.user); env.sqlite.prepare('UPDATE subscriptions SET trial_end=1').run();
  assert.equal((await call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: {} })).response.status, 402);
  t.mock.method(globalThis, 'fetch', async () => new Response('failure', { status: 500 }));
  assert.equal((await call(env, '/api/billing/checkout', { method: 'POST', body: { plan: 'starter' }, cookie: logged.cookie })).response.status, 502);
  assert.equal((await call(env, '/api/me', { cookie: logged.cookie })).data.subscription.entitled, false);
});

test('pending checkout prevents account deletion and its lock survives an ambiguous create', async t => {
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_STARTER_PRICE_ID: 'price_server', STRIPE_ADVANCED_PRICE_ID: 'price_advanced', STRIPE_UNLIMITED_PRICE_ID: 'price_unlimited', STRIPE_PORTAL_CONFIGURATION_ID: 'bpc_test', BILLING_LAUNCH_ENABLED: 'true' };
  const logged = await login(env);
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_test', logged.user.id);
  let creates = 0;
  t.mock.method(globalThis, 'fetch', async url => {
    if (url.includes('/subscriptions?')) return Response.json({ data: [], has_more: false });
    creates++;
    throw new DOMException('The operation timed out', 'TimeoutError');
  });
  assert.equal((await call(env, '/api/billing/checkout', { method: 'POST', body: { plan: 'starter' }, cookie: logged.cookie })).response.status, 504);
  assert.equal((await call(env, '/api/me', { method: 'DELETE', cookie: logged.cookie })).data.error, 'checkout_pending');
  assert.equal((await call(env, '/api/billing/checkout', { method: 'POST', body: { plan: 'starter' }, cookie: logged.cookie })).data.error, 'checkout_pending');
  assert.equal(creates, 1);
  // The old 30-minute timeout must not unlock a still-payable 35-minute session.
  env.sqlite.prepare('UPDATE users SET checkout_pending_at=?').run(at() - 1801);
  assert.equal((await call(env, '/api/billing/checkout', { method: 'POST', body: { plan: 'starter' }, cookie: logged.cookie })).data.error, 'checkout_pending');
});
test('account deletion loses an atomic race to a newly claimed checkout without deleting data', async () => {
  const env = environment(); const logged = await login(env);
  const prepare = env.DB.prepare.bind(env.DB);
  env.DB.prepare = sql => {
    const statement = prepare(sql);
    if (sql.startsWith('DELETE FROM users WHERE id = ? AND')) {
      const run = statement.run.bind(statement);
      statement.run = async () => {
        env.sqlite.prepare('UPDATE users SET checkout_pending_at=? WHERE id=?').run(at(), logged.user.id);
        return run();
      };
    }
    return statement;
  };
  const result = await call(env, '/api/me', { method: 'DELETE', cookie: logged.cookie });
  assert.equal(result.response.status, 409); assert.equal(result.data.error, 'checkout_pending');
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM users').get().n, 1);
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM sessions').get().n, 1);
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM challenges').get().n, 1);
});

test('a delayed old-subscription event cannot unlock a newer pending checkout', async t => {
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_STARTER_PRICE_ID: 'price_server', STRIPE_ADVANCED_PRICE_ID: 'price_advanced', STRIPE_UNLIMITED_PRICE_ID: 'price_unlimited', STRIPE_PORTAL_CONFIGURATION_ID: 'bpc_test', BILLING_LAUNCH_ENABLED: 'true' };
  const logged = await login(env); const pendingAt = at();
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=?,checkout_pending_at=? WHERE id=?').run('cus_test', pendingAt, logged.user.id);
  t.mock.method(globalThis, 'fetch', async () => Response.json({ id: 'sub_old', customer: 'cus_test', status: 'canceled', created: 1, trial_start: 1, trial_end: 2, metadata: { oraclebot_user: logged.user.id }, items: { data: [{ price: { id: 'price_server' }, quantity: 1 }] } }));
  const event = { id: 'evt_old', created: 100, type: 'checkout.session.completed', data: { object: { subscription: 'sub_old', customer: 'cus_test', expires_at: pendingAt - 100, metadata: { oraclebot_user: logged.user.id } } } };
  const signed = await signedEvent(event, env.STRIPE_WEBHOOK_SECRET);
  const response = await worker.fetch(new Request(`${ORIGIN}/api/billing/webhook`, { method: 'POST', headers: { 'Stripe-Signature': signed.header }, body: signed.raw }), env);
  assert.equal(response.status, 200);
  assert.equal(env.sqlite.prepare('SELECT checkout_pending_at FROM users').get().checkout_pending_at, pendingAt);
  assert.equal((await call(env, '/api/me', { method: 'DELETE', cookie: logged.cookie })).data.error, 'checkout_pending');
});

test('concurrent bot creates cannot exceed the Starter three-bot quota', async () => {
  const env = environment(); const logged = await login(env); grant(env, logged.user);
  for (let index = 0; index < 2; index++) {
    assert.equal((await call(env, '/api/bots', { method: 'POST', cookie: logged.cookie, body: { ...bot, name: `Existing ${index}` } })).response.status, 201);
  }
  // Model two remote D1 count reads completing before either request writes.
  const prepare = env.DB.prepare.bind(env.DB);
  let counted = 0; let release;
  const bothCounted = new Promise(resolve => { release = resolve; });
  env.DB.prepare = sql => {
    const statement = prepare(sql);
    if (sql.startsWith('SELECT COUNT(*) AS n FROM bots')) {
      const first = statement.first.bind(statement);
      statement.first = async () => {
        const result = await first();
        if (++counted === 2) release();
        await bothCounted;
        return result;
      };
    }
    return statement;
  };
  const results = await Promise.all([0, 1].map(index => call(env, '/api/bots', { method: 'POST', cookie: logged.cookie, body: { ...bot, name: `Concurrent ${index}` } })));
  assert.equal(env.sqlite.prepare("SELECT COUNT(*) AS n FROM bots WHERE status != 'archived'").get().n, 3);
  assert.deepEqual(results.map(result => result.response.status).sort(), [201, 409]);
  assert.equal(results.find(result => result.response.status === 409).data.error, 'bot_limit');
});

test('same-second webhook races cannot restore a canceled subscription', async t => {
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_STARTER_PRICE_ID: 'price_server', STRIPE_ADVANCED_PRICE_ID: 'price_advanced', STRIPE_UNLIMITED_PRICE_ID: 'price_unlimited', STRIPE_PORTAL_CONFIGURATION_ID: 'bpc_test', BILLING_LAUNCH_ENABLED: 'true' };
  const logged = await login(env);
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_test', logged.user.id);
  let releaseOld; let signalOldStarted;
  const oldStarted = new Promise(resolve => { signalOldStarted = resolve; });
  const release = new Promise(resolve => { releaseOld = resolve; });
  let calls = 0;
  const active = { id: 'sub_test', customer: 'cus_test', status: 'active', created: 50, trial_start: null, trial_end: null, current_period_end: at() + 604800, items: { data: [{ price: { id: 'price_server' }, quantity: 1 }] }, metadata: { oraclebot_user: logged.user.id } };
  let latest = { ...active, status: 'canceled' };
  t.mock.method(globalThis, 'fetch', async () => {
    if (++calls === 1) {
      signalOldStarted(); await release;
      return Response.json(active);
    }
    return Response.json(latest);
  });
  async function deliver(id, type, subscriptionId = 'sub_test') {
    const signed = await signedEvent({ id, created: 300, type, data: { object: { id: subscriptionId } } }, env.STRIPE_WEBHOOK_SECRET);
    return worker.fetch(new Request(`${ORIGIN}/api/billing/webhook`, { method: 'POST', headers: { 'Stripe-Signature': signed.header }, body: signed.raw }), env);
  }
  const olderInFlight = deliver('evt_active_race', 'customer.subscription.updated');
  await oldStarted;
  assert.equal((await deliver('evt_cancel_race', 'customer.subscription.deleted')).status, 200);
  assert.equal(env.sqlite.prepare('SELECT status FROM subscriptions').get().status, 'canceled');
  releaseOld(); assert.equal((await olderInFlight).status, 200);
  const subscription = env.sqlite.prepare('SELECT * FROM subscriptions').get();
  assert.equal(subscription.status, 'canceled');
  assert.equal(hasEntitlement(subscription), false);
  latest = { ...active, id: 'sub_replacement', created: 51 };
  assert.equal((await deliver('evt_replacement', 'customer.subscription.created', latest.id)).status, 200);
  const replacement = env.sqlite.prepare('SELECT * FROM subscriptions').get();
  assert.equal(replacement.stripe_subscription_id, latest.id);
  assert.equal(hasEntitlement(replacement), true);
  // A terminal cancellation remains terminal even if its price no longer matches.
  latest = { ...latest, status: 'canceled', items: { data: [{ price: { id: 'price_other' }, quantity: 1 }] } };
  assert.equal((await deliver('evt_replacement_cancel', 'customer.subscription.deleted', latest.id)).status, 200);
  assert.equal(env.sqlite.prepare('SELECT status FROM subscriptions').get().status, 'canceled');
  latest = { ...active, id: replacement.stripe_subscription_id, created: 51 };
  assert.equal((await deliver('evt_replacement_stale', 'customer.subscription.updated', latest.id)).status, 200);
  assert.equal(hasEntitlement(env.sqlite.prepare('SELECT * FROM subscriptions').get()), false);
});

test('active bot remains visible after more than one hundred newer archived bots', async () => {
  const env = environment(); const logged = await login(env);
  const insert = env.sqlite.prepare('INSERT INTO bots (id,user_id,name,coin,strategy,venue,leverage,budget,mode,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)');
  const activeId = crypto.randomUUID();
  insert.run(activeId, logged.user.id, 'Retained active bot', 'SOL', 'rsi', 'coinbase', 1, 100, 'paper', 'configured', 1, 1);
  for (let index = 0; index < 100; index++) insert.run(crypto.randomUUID(), logged.user.id, `Archived ${index}`, 'SOL', 'rsi', 'coinbase', 1, 100, 'paper', 'archived', index + 2, index + 2);
  const result = await call(env, '/api/bots', { cookie: logged.cookie });
  assert.equal(result.response.status, 200);
  assert.ok(result.data.bots.some(item => item.id === activeId), 'the active account configuration must remain discoverable');
});

test('unexpected API failures emit structured diagnostics without raw errors or secrets', async t => {
  const env = environment(); const logged = await login(env);
  const emitted = []; const levels = [];
  t.mock.method(console, 'error', (...args) => { levels.push('error'); emitted.push(args); });
  t.mock.method(console, 'warn', (...args) => { levels.push('warn'); emitted.push(args); });
  const canary = 'private-diagnostic-canary';
  env.DB.prepare = () => { throw new Error(`database failure ${canary} ${logged.wallet} ${logged.cookie}`); };
  const result = await call(env, `/api/me?token=${canary}`, { cookie: logged.cookie });
  assert.equal(result.response.status, 503);
  assert.equal((await call(env, `/api/${canary}?token=${canary}`, { cookie: logged.cookie })).response.status, 503);
  const structured = emitted.flat().map(value => {
    if (value && typeof value === 'object') return value;
    try { return JSON.parse(value); } catch { return null; }
  }).filter(value => value && typeof value === 'object');
  assert.deepEqual(structured.map(({ operation, code, status }) => ({ operation, code, status })), [
    { operation: 'GET /api/me', code: 'service_unavailable', status: 503 },
    { operation: 'GET /api/unknown', code: 'service_unavailable', status: 503 },
  ]);
  assert.deepEqual(levels, ['error', 'error']);
  const diagnosticText = JSON.stringify(emitted);
  for (const secret of [canary, logged.wallet, logged.cookie]) assert.equal(diagnosticText.includes(secret), false);
  assert.equal(JSON.stringify(result.data).includes(canary), false);
});

const billing = { STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_STARTER_PRICE_ID: 'price_server', STRIPE_ADVANCED_PRICE_ID: 'price_advanced', STRIPE_UNLIMITED_PRICE_ID: 'price_unlimited', STRIPE_PORTAL_CONFIGURATION_ID: 'bpc_test', BILLING_LAUNCH_ENABLED: 'true' };
const backtest = { coin: 'SOL', strategy: 'rsi', interval: '1h', capital: 1000, leverage: 1 };
const complete = () => Response.json({ status: 'complete', metrics: { total_return: 0.1 } });
function configuredEngine() { return { ENGINE_URL: 'https://engine.example', ENGINE_TOKEN: 'fake_engine_token' }; }
async function deliverSubscription(env, current, id = crypto.randomUUID().replaceAll('-', '')) {
  const signed = await signedEvent({ id: `evt_${id}`, created: at(), type: 'customer.subscription.updated', data: { object: { id: current.id, metadata: { plan: 'unlimited' } } } }, env.STRIPE_WEBHOOK_SECRET);
  return worker.fetch(new Request(`${ORIGIN}/api/billing/webhook`, { method: 'POST', headers: { 'Stripe-Signature': signed.header }, body: signed.raw }), env);
}

test('every plan uses its allowlisted server Price and never a browser amount', async t => {
  let selected;
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    if (url.endsWith('/customers')) return Response.json({ id: `cus_${selected}` });
    if (url.includes('/subscriptions?')) return Response.json({ data: [], has_more: false });
    assert.equal(options.body.get('line_items[0][price]'), billing[`STRIPE_${selected.toUpperCase()}_PRICE_ID`]);
    assert.equal(options.body.get('subscription_data[trial_period_days]'), '7');
    return Response.json({ url: 'https://checkout.stripe.com/c/pay/fixture' });
  });
  for (selected of ['starter', 'advanced', 'unlimited']) {
    const env = { ...environment(), ...billing }; const logged = await login(env);
    const result = await call(env, '/api/billing/checkout', { method: 'POST', cookie: logged.cookie, body: { plan: selected } });
    assert.equal(result.response.status, 200); assert.equal(result.data.plan, selected);
  }
});
test('invalid and spoofed plans fail before a checkout lock or provider request', async t => {
  const env = { ...environment(), ...billing }; const logged = await login(env);
  t.mock.method(globalThis, 'fetch', () => { assert.fail('invalid plan must not reach Stripe'); });
  for (const body of [{}, { plan: 'enterprise' }, { plan: '__proto__' }, { plan: 'toString' }, { plan: 'starter', price: 'price_unlimited' }, { plan: 'starter', amount: 1 }, { plan: ['starter'] }]) {
    assert.equal((await call(env, '/api/billing/checkout', { method: 'POST', cookie: logged.cookie, body })).data.error, 'invalid_plan');
  }
  assert.equal(env.sqlite.prepare('SELECT checkout_pending_at FROM users').get().checkout_pending_at, null);
});
test('Checkout needs an explicit launch flag; portal cancellation works while Checkout is hidden', async t => {
  const env = { ...environment(), ...billing, BILLING_LAUNCH_ENABLED: 'false' }; const logged = await login(env);
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_existing', logged.user.id);
  let calls = 0;
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls++; assert.equal(url, 'https://api.stripe.com/v1/billing_portal/sessions');
    assert.equal(options.body.get('configuration'), 'bpc_test'); assert.equal(options.body.get('customer'), 'cus_existing');
    return Response.json({ url: 'https://billing.stripe.com/p/session/test' });
  });
  for (const flag of [undefined, false, true, 'false', 'TRUE', 1]) {
    env.BILLING_LAUNCH_ENABLED = flag;
    assert.equal((await call(env, '/api/config')).data.billingConfigured, false);
    assert.equal((await call(env, '/api/billing/checkout', { method: 'POST', cookie: logged.cookie, body: { plan: 'starter' } })).response.status, 503);
  }
  assert.equal((await call(env, '/api/me', { cookie: logged.cookie })).data.portalAvailable, true);
  assert.equal((await call(env, '/api/billing/portal', { method: 'POST', cookie: logged.cookie })).response.status, 200);
  assert.equal(calls, 1);
  delete env.STRIPE_PORTAL_CONFIGURATION_ID;
  env.BILLING_LAUNCH_ENABLED = 'true';
  assert.equal((await call(env, '/api/config')).data.billingConfigured, false);
  assert.equal((await call(env, '/api/billing/portal', { method: 'POST', cookie: logged.cookie })).response.status, 503);
  assert.equal(calls, 1);
});
test('missing or duplicated price bindings disable Checkout and unknown canonical Prices grant no entitlement', async t => {
  const env = { ...environment(), ...billing }; const logged = await login(env);
  env.STRIPE_ADVANCED_PRICE_ID = env.STRIPE_STARTER_PRICE_ID;
  assert.equal((await call(env, '/api/config')).data.billingConfigured, false);
  env.STRIPE_ADVANCED_PRICE_ID = 'price_advanced';
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_known', logged.user.id);
  t.mock.method(globalThis, 'fetch', async () => Response.json({ id: 'sub_known', created: 1, customer: 'cus_known', status: 'active', current_period_end: at() + 86400, metadata: { oraclebot_user: logged.user.id, plan: 'unlimited' }, items: { data: [{ price: { id: 'price_attacker' }, quantity: 1 }] } }));
  assert.equal((await deliverSubscription(env, { id: 'sub_known' })).status, 200);
  const me = (await call(env, '/api/me', { cookie: logged.cookie })).data;
  assert.equal(me.subscription.status, 'plan_mismatch'); assert.equal(me.subscription.entitled, false); assert.equal(me.subscription.plan, null);
});
test('canonical webhook plan changes preserve first-trial history and ignore event/browser plan hints', async t => {
  const env = { ...environment(), ...billing }; const logged = await login(env);
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_known', logged.user.id);
  let current = { id: 'sub_known', created: 1, customer: 'cus_known', status: 'trialing', trial_start: 1, trial_end: at() + 86400, current_period_end: at() + 86400, metadata: { oraclebot_user: logged.user.id, plan: 'unlimited' }, items: { data: [{ price: { id: 'price_server' }, quantity: 1 }] } };
  t.mock.method(globalThis, 'fetch', async () => Response.json(current));
  for (const [plan, price] of [['starter', 'price_server'], ['advanced', 'price_advanced'], ['unlimited', 'price_unlimited']]) {
    current = { ...current, items: { data: [{ price: { id: price }, quantity: 1 }] } };
    assert.equal((await deliverSubscription(env, current)).status, 200);
    const me = (await call(env, '/api/me', { cookie: logged.cookie })).data;
    assert.equal(me.subscription.plan.id, plan); assert.equal(me.subscription.entitled, true);
    assert.equal(env.sqlite.prepare('SELECT trial_used FROM users').get().trial_used, 1);
  }
  current = { ...current, trial_start: null, trial_end: null, status: 'active' };
  assert.equal((await deliverSubscription(env, current)).status, 200);
  assert.equal(env.sqlite.prepare('SELECT trial_used FROM users').get().trial_used, 1);
  current = { ...current, items: { data: [current.items.data[0], current.items.data[0]] } };
  assert.equal((await deliverSubscription(env, current)).status, 200);
  assert.equal((await call(env, '/api/me', { cookie: logged.cookie })).data.subscription.entitled, false);
});
test('Starter allows ten daily backtests, refuses eleven and resets at midnight UTC', async t => {
  const original = Date.now(); let clock = Math.floor(original / 86400000) * 86400000 + 86340000;
  t.mock.method(Date, 'now', () => clock);
  const env = { ...environment(), ...configuredEngine() }; const logged = await login(env); grant(env, logged.user);
  t.mock.method(globalThis, 'fetch', complete);
  for (let index = 0; index < 10; index++) assert.equal((await call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: backtest })).response.status, 200);
  const refused = await call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: { ...backtest, plan: 'unlimited', backtestsPerDay: null } });
  assert.equal(refused.response.status, 429); assert.equal(refused.data.error, 'backtest_daily_limit');
  const before = (await call(env, '/api/me', { cookie: logged.cookie })).data.usage;
  assert.equal(before.backtests, 10); assert.equal(before.reservedBacktests, 0);
  clock += 120000;
  assert.equal((await call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: backtest })).response.status, 200);
  const after = (await call(env, '/api/me', { cookie: logged.cookie })).data.usage;
  assert.notEqual(after.day, before.day); assert.equal(after.backtests, 1);
});
test('validation, entitlement, absent or failed engines consume no backtest credits', async t => {
  const env = environment(); const logged = await login(env);
  assert.equal((await call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: backtest })).response.status, 402);
  grant(env, logged.user);
  assert.equal((await call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: backtest })).data.error, 'engine_unavailable');
  Object.assign(env, configuredEngine());
  assert.equal((await call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: { ...backtest, capital: -1 } })).response.status, 400);
  let respond = () => new Response('{}', { status: 503 });
  t.mock.method(globalThis, 'fetch', () => respond());
  for (respond of [() => new Response('{}', { status: 503 }), () => Response.json({ status: 'unavailable' }), () => new Response('not json'), () => { throw new DOMException('timed out', 'TimeoutError'); }]) {
    const result = await call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: backtest });
    assert.ok(result.response.status >= 500);
    assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM backtest_usage').get().n, 0);
  }
  respond = complete;
  assert.equal((await call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: backtest })).response.status, 200);
  assert.equal((await call(env, '/api/me', { cookie: logged.cookie })).data.usage.backtests, 1);
});
test('an atomic reservation admits one concurrent backtest and releases capacity after completion', async t => {
  const env = { ...environment(), ...configuredEngine() }; const logged = await login(env); grant(env, logged.user);
  let release; let started;
  const gate = new Promise(resolve => { release = resolve; }); const entered = new Promise(resolve => { started = resolve; });
  t.mock.method(globalThis, 'fetch', async () => { started(); await gate; return complete(); });
  const first = call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: backtest });
  await entered;
  const other = await call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: backtest });
  assert.equal(other.response.status, 429); assert.equal(other.data.error, 'backtest_in_progress');
  assert.equal(env.sqlite.prepare("SELECT COUNT(*) AS n FROM backtest_usage WHERE state='reserved'").get().n, 1);
  release(); assert.equal((await first).response.status, 200);
  assert.equal((await call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: backtest })).response.status, 200);
  assert.equal((await call(env, '/api/me', { cookie: logged.cookie })).data.usage.backtests, 2);
});
test('the final daily credit is reserved atomically and unused stale reservations expire', async t => {
  const env = { ...environment(), ...configuredEngine() }; const logged = await login(env); grant(env, logged.user);
  t.mock.method(globalThis, 'fetch', complete);
  for (let index = 0; index < 9; index++) await call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: backtest });
  const results = await Promise.all([0, 1].map(() => call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: backtest })));
  assert.deepEqual(results.map(result => result.response.status).sort(), [200, 429]);
  assert.equal(env.sqlite.prepare("SELECT COUNT(*) AS n FROM backtest_usage WHERE state='complete'").get().n, 10);
  const other = await login(env); grant(env, other.user);
  env.sqlite.prepare("INSERT INTO backtest_usage(id,user_id,day,state,created_at,expires_at) VALUES (?, ?, ?, 'reserved', ?, ?)").run(crypto.randomUUID(), other.user.id, new Date().toISOString().slice(0, 10), at() - 400, at() - 1);
  assert.equal((await call(env, '/api/backtests', { method: 'POST', cookie: other.cookie, body: backtest })).response.status, 200);
});
test('Advanced and Unlimited have unlimited backtest counts with bounded concurrent capacity', async t => {
  t.mock.method(globalThis, 'fetch', complete);
  for (const plan of ['advanced', 'unlimited']) {
    const env = { ...environment(), ...configuredEngine() }; const logged = await login(env); grant(env, logged.user, 'active', plan);
    for (let index = 0; index < 12; index++) assert.equal((await call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: backtest })).response.status, 200);
    const usage = (await call(env, '/api/me', { cookie: logged.cookie })).data.usage;
    assert.equal(usage.backtests, 12); assert.equal(usage.policy.backtestsPerDay, null); assert.equal(usage.concurrentBacktests, 1);
    assert.equal((await call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: { ...backtest, leverage: 1000 } })).response.status, 400);
  }
});
test('bot slots enforce each tier, paused and archived free slots, and tenant counts remain isolated', async () => {
  for (const [plan, limit] of [['starter', 3], ['advanced', 10], ['unlimited', 25]]) {
    const env = environment(); const logged = await login(env); grant(env, logged.user, 'active', plan);
    const other = await login(env); grant(env, other.user);
    const ids = [];
    for (let index = 0; index < limit; index++) { const result = await call(env, '/api/bots', { method: 'POST', cookie: logged.cookie, body: { ...bot, status: 'paused', plan: 'unlimited' } }); assert.equal(result.response.status, 201); assert.equal(result.data.bot.status, 'configured'); ids.push(result.data.bot.id); }
    assert.equal((await call(env, '/api/bots', { method: 'POST', cookie: other.cookie, body: bot })).response.status, 201);
    assert.equal((await call(env, '/api/bots', { method: 'POST', cookie: logged.cookie, body: bot })).response.status, plan === 'unlimited' ? 201 : 409);
    for (const [index, status] of ['paused', 'archived'].entries()) {
      assert.equal((await call(env, `/api/bots/${ids[index]}`, { method: 'PATCH', cookie: logged.cookie, body: { status } })).response.status, 200);
      assert.equal((await call(env, '/api/bots', { method: 'POST', cookie: logged.cookie, body: bot })).response.status, 201);
    }
    assert.equal((await call(env, `/api/bots/${ids[0]}`, { method: 'PATCH', cookie: logged.cookie, body: { status: 'configured' } })).response.status, 400);
  }
});
test('downgrades preserve over-limit records and safe pause/archive access; unknown statuses cannot avoid slots', async () => {
  const env = environment(); const logged = await login(env); grant(env, logged.user, 'active', 'advanced');
  for (let index = 0; index < 4; index++) await call(env, '/api/bots', { method: 'POST', cookie: logged.cookie, body: bot });
  env.sqlite.prepare("UPDATE subscriptions SET plan_id='starter'").run();
  const bots = (await call(env, '/api/bots', { cookie: logged.cookie })).data.bots;
  assert.equal(bots.length, 4); assert.equal((await call(env, '/api/bots', { method: 'POST', cookie: logged.cookie, body: bot })).data.error, 'bot_limit');
  // A future/invalid stored status fails conservatively instead of bypassing capacity.
  env.sqlite.exec('PRAGMA ignore_check_constraints = ON'); env.sqlite.prepare("UPDATE bots SET status='unknown' WHERE id=?").run(bots[0].id);
  assert.equal((await call(env, '/api/me', { cookie: logged.cookie })).data.usage.bots, 4);
  env.sqlite.prepare("UPDATE subscriptions SET status='canceled'").run();
  for (const [index, status] of ['paused', 'archived'].entries()) assert.equal((await call(env, `/api/bots/${bots[index].id}`, { method: 'PATCH', cookie: logged.cookie, body: { status } })).response.status, 200);
  assert.equal((await call(env, '/api/bots', { cookie: logged.cookie })).data.bots.length, 4);
});

test('a downgrade that races a create cannot reserve capacity from an obsolete plan', async () => {
  for (const path of ['/api/bots', '/api/backtests']) {
    const env = { ...environment(), ...configuredEngine() }; const logged = await login(env); grant(env, logged.user, 'active', 'unlimited');
    const prepare = env.DB.prepare.bind(env.DB); let raced = false;
    env.DB.prepare = sql => {
      const statement = prepare(sql);
      if (sql.startsWith(path === '/api/bots' ? 'INSERT INTO bots' : 'INSERT INTO backtest_usage')) {
        const run = statement.run.bind(statement);
        statement.run = async () => { if (!raced) { raced = true; env.sqlite.prepare("UPDATE subscriptions SET plan_id='starter'").run(); } return run(); };
      }
      return statement;
    };
    const result = await call(env, path, { method: 'POST', cookie: logged.cookie, body: path === '/api/bots' ? bot : backtest });
    assert.equal(result.response.status, 409); assert.equal(result.data.error, 'subscription_changed');
    assert.equal(env.sqlite.prepare(`SELECT COUNT(*) AS n FROM ${path === '/api/bots' ? 'bots' : 'backtest_usage'}`).get().n, 0);
  }
});
test('Unlimited records beyond a hundred stay accessible through tenant-scoped bounded pages', async () => {
  const env = environment(); const logged = await login(env); const other = await login(env);
  const insert = env.sqlite.prepare('INSERT INTO bots (id,user_id,name,coin,strategy,venue,leverage,budget,mode,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)');
  for (let index = 0; index < 105; index++) insert.run(crypto.randomUUID(), logged.user.id, `Bot ${index}`, 'SOL', 'rsi', 'coinbase', 1, 100, 'paper', 'configured', index, index);
  insert.run(crypto.randomUUID(), other.user.id, 'Private other account bot', 'SOL', 'rsi', 'coinbase', 1, 100, 'paper', 'configured', 999, 999);
  const first = (await call(env, '/api/bots', { cookie: logged.cookie })).data;
  const second = (await call(env, `/api/bots?page=${first.nextPage}`, { cookie: logged.cookie })).data;
  assert.equal(first.bots.length, 100); assert.equal(first.nextPage, 1); assert.equal(second.bots.length, 5); assert.equal(second.nextPage, null);
  assert.equal(new Set([...first.bots, ...second.bots].map(bot => bot.id)).size, 105);
  assert.equal([...first.bots, ...second.bots].some(bot => bot.name === 'Private other account bot'), false);
  assert.equal((await call(env, '/api/bots?page=-1', { cookie: logged.cookie })).response.status, 400);
});

test('same-second plan webhook races cannot restore an older Unlimited plan after a downgrade', async t => {
  const env = { ...environment(), ...billing }; const logged = await login(env);
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_planrace', logged.user.id);
  const base = { id: 'sub_planrace', customer: 'cus_planrace', status: 'active', created: 50, current_period_end: at() + 86400, metadata: { oraclebot_user: logged.user.id } };
  let started; let release;
  const entered = new Promise(resolve => { started = resolve; }); const held = new Promise(resolve => { release = resolve; });
  let calls = 0;
  t.mock.method(globalThis, 'fetch', async () => {
    const sequence = ++calls;
    if (sequence === 1) { started(); await held; }
    return Response.json({ ...base, items: { data: [{ price: { id: sequence === 1 ? 'price_unlimited' : 'price_server' }, quantity: 1 }] } });
  });
  async function deliver(id) {
    const signed = await signedEvent({ id, created: 300, type: 'customer.subscription.updated', data: { object: { id: base.id } } }, env.STRIPE_WEBHOOK_SECRET);
    return worker.fetch(new Request(`${ORIGIN}/api/billing/webhook`, { method: 'POST', headers: { 'Stripe-Signature': signed.header }, body: signed.raw }), env);
  }
  const older = deliver('evt_older_plan'); await entered;
  const contended = await deliver('evt_newer_plan');
  const earlyReceipt = env.sqlite.prepare('SELECT id FROM stripe_events WHERE id=?').get('evt_newer_plan');
  release(); assert.equal((await older).status, 200);
  assert.equal((await deliver('evt_newer_plan')).status, 200);
  assert.equal(env.sqlite.prepare('SELECT plan_id FROM subscriptions').get().plan_id, 'starter', 'a late old fetch must not restore Unlimited after the same-second downgrade');
  assert.equal(contended.status, 503);
  assert.equal(earlyReceipt, undefined, 'contention must remain retryable, without a handled-event receipt');
  assert.equal(calls, 2, 'the contending request must not fetch canonical state before its retry');
  assert.equal((await deliver('evt_newer_plan')).status, 200); assert.equal(calls, 2, 'completed replay must deduplicate');
});

function canonicalPlan(user, subscriptionId, customer, price = 'price_server') {
  return { id: subscriptionId, customer, status: 'active', created: 50, current_period_end: at() + 86400, metadata: { oraclebot_user: user.id }, items: { data: [{ price: { id: price }, quantity: 1 }] } };
}
test('webhook fetch failures release their owned lease and leave the event retryable', async t => {
  const env = { ...environment(), ...billing }; const logged = await login(env);
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_retry', logged.user.id);
  const current = canonicalPlan(logged.user, 'sub_retry', 'cus_retry');
  let outcome = 'http'; let calls = 0;
  t.mock.method(globalThis, 'fetch', async () => { calls++; if (outcome === 'http') return new Response('{}', { status: 500 }); if (outcome === 'timeout') throw new DOMException('timed out', 'TimeoutError'); if (outcome === 'identity') return Response.json({ ...current, id: 'sub_unexpected' }); return Response.json(current); });
  for (const [mode, status] of [['http', 502], ['timeout', 504], ['identity', 502]]) {
    outcome = mode;
    assert.equal((await deliverSubscription(env, current, 'fetch_retry')).status, status);
    assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM subscription_webhook_leases').get().n, 0);
    assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM stripe_events').get().n, 0);
    assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM subscriptions').get().n, 0);
  }
  outcome = 'success';
  assert.equal((await deliverSubscription(env, current, 'fetch_retry')).status, 200);
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM subscription_webhook_leases').get().n, 0);
  assert.equal((await deliverSubscription(env, current, 'fetch_retry')).status, 200); assert.equal(calls, 4);
});
test('an expired webhook lease cannot mutate subscription, trial history or receipt without a replacement', async t => {
  const env = { ...environment(), ...billing }; const logged = await login(env);
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_expired', logged.user.id);
  const current = { ...canonicalPlan(logged.user, 'sub_expired', 'cus_expired', 'price_unlimited'), trial_start: 1, trial_end: at() + 86400 };
  let entered; let release; const started = new Promise(resolve => { entered = resolve; }); const held = new Promise(resolve => { release = resolve; });
  t.mock.method(globalThis, 'fetch', async () => { entered(); await held; return Response.json(current); });
  const pending = deliverSubscription(env, current, 'expired'); await started;
  const lease = env.sqlite.prepare('SELECT * FROM subscription_webhook_leases').get();
  assert.match(lease.subscription_key, /^[a-f0-9]{64}$/);
  assert.ok(lease.expires_at > at() && lease.expires_at <= at() + 30);
  for (const identifier of [current.id, current.customer, logged.user.id, logged.wallet]) assert.equal(JSON.stringify(lease).includes(identifier), false);
  env.sqlite.prepare('UPDATE subscription_webhook_leases SET expires_at=unixepoch()-1').run();
  release(); const result = await pending;
  assert.equal(result.status, 503); assert.equal((await result.json()).error, 'webhook_lease_lost');
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM subscriptions').get().n, 0);
  assert.equal(env.sqlite.prepare('SELECT trial_used FROM users').get().trial_used, 0);
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM stripe_events').get().n, 0);
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM subscription_webhook_leases').get().n, 0);
});
test('expired webhook owners cannot overwrite replacements or release another owner’s lease', async t => {
  for (const replacementFirst of [false, true]) await t.test(replacementFirst ? 'replacement writes before late owner' : 'late owner returns while replacement is fetching', async t => {
    const env = { ...environment(), ...billing }; const logged = await login(env);
    env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_fence', logged.user.id);
    const base = canonicalPlan(logged.user, 'sub_fence', 'cus_fence');
    const signals = [0, 1].map(() => { let entered; let release; return { started: new Promise(resolve => { entered = resolve; }), held: new Promise(resolve => { release = resolve; }), enter: () => entered(), release: () => release() }; });
    let calls = 0;
    t.mock.method(globalThis, 'fetch', async () => {
      const index = calls++; signals[index].enter(); await signals[index].held;
      return Response.json({ ...base, items: { data: [{ price: { id: index === 0 ? 'price_unlimited' : 'price_server' }, quantity: 1 }] } });
    });
    const old = deliverSubscription(env, base, 'old_fence'); await signals[0].started;
    const original = env.sqlite.prepare('SELECT * FROM subscription_webhook_leases').get();
    env.sqlite.prepare('UPDATE subscription_webhook_leases SET expires_at=unixepoch()-1').run();
    const replacement = deliverSubscription(env, base, 'new_fence'); await signals[1].started;
    const newer = env.sqlite.prepare('SELECT * FROM subscription_webhook_leases').get(); assert.notEqual(newer.owner_token, original.owner_token);
    if (replacementFirst) { signals[1].release(); assert.equal((await replacement).status, 200); }
    signals[0].release(); const stale = await old; assert.equal(stale.status, 503); assert.equal((await stale.json()).error, 'webhook_lease_lost');
    assert.equal(env.sqlite.prepare('SELECT id FROM stripe_events WHERE id=?').get('evt_old_fence'), undefined);
    if (!replacementFirst) {
      assert.equal(env.sqlite.prepare('SELECT owner_token FROM subscription_webhook_leases').get().owner_token, newer.owner_token, 'old finally cleanup cannot delete the replacement lease');
      signals[1].release(); assert.equal((await replacement).status, 200);
    }
    assert.equal(env.sqlite.prepare('SELECT plan_id FROM subscriptions').get().plan_id, 'starter');
    assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM subscription_webhook_leases').get().n, 0);
    assert.equal(calls, 2);
  });
});
test('webhook leases serialize each subscription independently and cleanup only expired leases', async t => {
  const env = { ...environment(), ...billing }; const first = await login(env); const second = await login(env);
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_first', first.user.id);
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_second', second.user.id);
  const a = canonicalPlan(first.user, 'sub_first', 'cus_first'); const b = canonicalPlan(second.user, 'sub_second', 'cus_second', 'price_advanced');
  let entered; let release; const started = new Promise(resolve => { entered = resolve; }); const held = new Promise(resolve => { release = resolve; });
  t.mock.method(globalThis, 'fetch', async url => { if (url.endsWith(a.id)) { entered(); await held; return Response.json(a); } assert.ok(url.endsWith(b.id)); return Response.json(b); });
  const pending = deliverSubscription(env, a, 'first_independent'); await started;
  assert.equal((await deliverSubscription(env, b, 'second_independent')).status, 200);
  assert.equal(env.sqlite.prepare('SELECT plan_id FROM subscriptions WHERE user_id=?').get(second.user.id).plan_id, 'advanced');
  release(); assert.equal((await pending).status, 200);
  env.sqlite.prepare('INSERT INTO subscription_webhook_leases VALUES (?,?,unixepoch()-1)').run('expired-hash-fixture', 'expired-owner');
  env.sqlite.prepare('INSERT INTO subscription_webhook_leases VALUES (?,?,unixepoch()+30)').run('active-hash-fixture', 'active-owner');
  await worker.scheduled({}, env);
  assert.deepEqual(env.sqlite.prepare('SELECT subscription_key FROM subscription_webhook_leases').all().map(row => row.subscription_key), ['active-hash-fixture']);
});

test('OAuth diagnostics classify protocol routes without request text or credentials', async t => {
  const env = environment(); const emitted = []; const canary = 'private-oauth-diagnostic-marker';
  t.mock.method(console, 'warn', text => emitted.push(JSON.parse(text)));
  const result = await call(env, `/oauth/register?private=${canary}`, { method: 'POST', body: { client_name: canary, redirect_uris: [] } });
  assert.equal(result.response.status, 400);
  assert.deepEqual(emitted, [{ event: 'oraclebot.request_failed', operation: 'POST /oauth/register', code: 'invalid_redirect_uri', status: 400 }]);
  assert.equal(JSON.stringify(emitted).includes(canary), false);
});

test('login racing deletion reads trial history atomically before recreating the wallet account', async t => {
  const env = { ...environment(), ...billing }; const identity = await keypair();
  const old = await login(env, identity);
  env.sqlite.prepare('UPDATE users SET trial_used=1 WHERE id=?').run(old.user.id);
  const challenge = await call(env, '/api/auth/challenge', { method: 'POST', body: { wallet: identity.wallet } });
  const signature = Buffer.from(await crypto.subtle.sign('Ed25519', identity.keys.privateKey, new TextEncoder().encode(challenge.data.message))).toString('base64');
  let entered; let release;
  const started = new Promise(resolve => { entered = resolve; }); const held = new Promise(resolve => { release = resolve; });
  const prepare = env.DB.prepare.bind(env.DB);
  env.DB.prepare = sql => {
    const statement = prepare(sql);
    if (sql.startsWith('INSERT INTO users ')) {
      const run = statement.run.bind(statement);
      statement.run = async () => { entered(); await held; return run(); };
    }
    return statement;
  };
  const pending = call(env, '/api/auth/verify', { method: 'POST', body: { id: challenge.data.id, signature } });
  await started;
  assert.equal((await call(env, '/api/me', { method: 'DELETE', cookie: old.cookie })).response.status, 200);
  release(); const recreated = await pending;
  assert.equal(recreated.response.status, 200); assert.notEqual(recreated.data.user.id, old.user.id);
  assert.equal(env.sqlite.prepare('SELECT trial_used FROM users WHERE wallet=?').get(identity.wallet).trial_used, 1);
  let customers = 0;
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    if (url.endsWith('/customers')) { customers++; return Response.json({ id: 'cus_recreated' }); }
    if (url.includes('/subscriptions?')) return Response.json({ data: [], has_more: false });
    assert.equal(url, 'https://api.stripe.com/v1/checkout/sessions');
    assert.equal(options.body.has('subscription_data[trial_period_days]'), false);
    return Response.json({ url: 'https://checkout.stripe.com/c/pay/recreated' });
  });
  const cookie = recreated.response.headers.get('Set-Cookie').split(';')[0];
  const result = await call(env, '/api/billing/checkout', { method: 'POST', cookie, body: { plan: 'starter' } });
  assert.equal(result.response.status, 200); assert.equal(result.data.trialDays, 0); assert.equal(customers, 1);
});

test('login repairs a stale trial flag monotonically without replacing account identity or customer', async t => {
  const env = environment(); const identity = await keypair(); const original = await login(env, identity);
  const walletHash = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(identity.wallet))).toString('hex');
  env.sqlite.prepare('INSERT INTO trial_history VALUES (?,?)').run(walletHash, at());
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_preserved', original.user.id);
  const before = env.sqlite.prepare('SELECT * FROM users').get();
  let upstream = 0; t.mock.method(globalThis, 'fetch', async () => { upstream++; throw new Error('unexpected upstream'); });
  assert.equal((await login(env, identity)).user.id, original.user.id);
  assert.deepEqual({ ...env.sqlite.prepare('SELECT * FROM users').get() }, { ...before, trial_used: 1 });
  env.sqlite.prepare('DELETE FROM trial_history').run();
  assert.equal((await login(env, identity)).user.id, original.user.id);
  assert.equal(env.sqlite.prepare('SELECT trial_used FROM users').get().trial_used, 1); assert.equal(upstream, 0);
});

test('deletion captures a trial flag that changes after its initial account read', async t => {
  const env = environment(); const identity = await keypair(); const original = await login(env, identity);
  const batch = env.DB.batch.bind(env.DB);
  let entered; let release;
  const started = new Promise(resolve => { entered = resolve; }); const held = new Promise(resolve => { release = resolve; });
  env.DB.batch = async statements => { entered(); await held; return batch(statements); };
  let upstream = 0; t.mock.method(globalThis, 'fetch', async () => { upstream++; throw new Error('unexpected upstream'); });
  const pending = call(env, '/api/me', { method: 'DELETE', cookie: original.cookie });
  await started;
  env.sqlite.prepare('UPDATE users SET trial_used=1 WHERE id=?').run(original.user.id);
  release(); assert.equal((await pending).response.status, 200);
  const history = env.sqlite.prepare('SELECT * FROM trial_history').get(); assert.ok(history);
  assert.notEqual(history.wallet_hash, identity.wallet);
  assert.equal((await login(env, identity)).user.wallet, identity.wallet);
  assert.equal(env.sqlite.prepare('SELECT trial_used FROM users').get().trial_used, 1); assert.equal(upstream, 0);
});

test('deletion refuses a newly active subscription and retains newly observed trial history', async t => {
  const env = { ...environment(), ...billing }; const original = await login(env); grant(env, original.user, 'canceled');
  const before = env.sqlite.prepare('SELECT * FROM users').get();
  const batch = env.DB.batch.bind(env.DB);
  let entered; let release;
  const started = new Promise(resolve => { entered = resolve; }); const held = new Promise(resolve => { release = resolve; });
  env.DB.batch = async statements => { entered(); await held; return batch(statements); };
  const emitted = []; t.mock.method(console, 'info', text => emitted.push(JSON.parse(text)));
  let upstream = 0; t.mock.method(globalThis, 'fetch', async () => { upstream++; throw new Error('unexpected upstream'); });
  const pending = call(env, '/api/me', { method: 'DELETE', cookie: original.cookie });
  await started;
  env.sqlite.prepare("UPDATE subscriptions SET status='active'").run();
  env.sqlite.prepare('UPDATE users SET trial_used=1 WHERE id=?').run(original.user.id);
  release(); const result = await pending;
  assert.equal(result.response.status, 409); assert.equal(result.data.error, 'cancel_subscription_first');
  const after = env.sqlite.prepare('SELECT * FROM users').get();
  assert.match(after.deletion_token, /^[a-f0-9-]{36}$/); assert.ok(after.deletion_requested_at >= before.created_at);
  assert.deepEqual({ ...after, deletion_token: null, deletion_requested_at: null }, { ...before, trial_used: 1 });
  assert.equal(env.sqlite.prepare('SELECT status FROM subscriptions').get().status, 'active');
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM sessions').get().n, 1);
  const history = env.sqlite.prepare('SELECT * FROM trial_history').get(); assert.ok(history);
  assert.equal(emitted.some(row => row.event === 'oraclebot.account_deleted'), false);
  assert.equal((await call(env, '/api/billing/checkout', { method: 'POST', cookie: original.cookie, body: { plan: 'starter' } })).data.error, 'account_deleting');
  assert.deepEqual(env.sqlite.prepare('SELECT * FROM trial_history').get(), history); assert.equal(upstream, 0);
});

test('upstream diagnostics record static starts and outcomes without account or request data', async t => {
  const env = { ...environment(), ...billing, ...configuredEngine() }; const logged = await login(env);
  const emitted = []; const canary = 'private-upstream-diagnostic-marker';
  t.mock.method(console, 'info', text => emitted.push(JSON.parse(text)));
  t.mock.method(console, 'warn', text => emitted.push(JSON.parse(text)));
  t.mock.method(console, 'error', text => emitted.push(JSON.parse(text)));
  t.mock.method(globalThis, 'fetch', async url => {
    const endpoint = String(url);
    if (endpoint.endsWith('/customers')) return Response.json({ id: `cus_${canary}` });
    if (endpoint.includes('/subscriptions?')) return Response.json({ data: [], has_more: false });
    if (endpoint.endsWith('/checkout/sessions')) return Response.json({ url: `https://checkout.stripe.com/c/pay/${canary}` });
    return Response.json({ unavailable: canary }, { status: 503 });
  });
  assert.equal((await call(env, '/api/billing/checkout', { method: 'POST', cookie: logged.cookie, body: { plan: 'starter' } })).response.status, 200);
  assert.equal((await call(env, `/api/oracle?coin=SOL&private=${canary}`)).response.status, 503);
  globalThis.fetch.mock.mockImplementation(async () => { throw new Error(`${canary} ${logged.wallet} ${env.ENGINE_TOKEN}`); });
  assert.equal((await call(env, '/api/strategies')).response.status, 503);
  const upstream = emitted.filter(row => row.event === 'oraclebot.upstream');
  assert.deepEqual(upstream.map(({ operation, phase, outcome, status }) => ({ operation, phase, outcome, status })), [
    { operation: 'stripe.customer_create', phase: 'start', outcome: undefined, status: undefined },
    { operation: 'stripe.customer_create', phase: 'outcome', outcome: 'success', status: 200 },
    { operation: 'stripe.subscription_list', phase: 'start', outcome: undefined, status: undefined },
    { operation: 'stripe.subscription_list', phase: 'outcome', outcome: 'success', status: 200 },
    { operation: 'stripe.checkout_create', phase: 'start', outcome: undefined, status: undefined },
    { operation: 'stripe.checkout_create', phase: 'outcome', outcome: 'success', status: 200 },
    { operation: 'engine.oracle', phase: 'start', outcome: undefined, status: undefined },
    { operation: 'engine.oracle', phase: 'outcome', outcome: 'failure', status: 503 },
    { operation: 'engine.strategies', phase: 'start', outcome: undefined, status: undefined },
    { operation: 'engine.strategies', phase: 'outcome', outcome: 'failure', status: 0 },
  ]);
  for (const row of upstream) {
    assert.deepEqual(Object.keys(row).sort(), (row.phase === 'start' ? ['event', 'operation', 'phase'] : ['durationMs', 'event', 'operation', 'outcome', 'phase', 'status']).sort());
    if (row.phase === 'outcome') assert.ok(Number.isFinite(row.durationMs) && row.durationMs >= 0);
  }
  for (const secret of [canary, logged.wallet, logged.cookie, logged.user.id, env.STRIPE_SECRET_KEY, env.ENGINE_TOKEN]) assert.equal(JSON.stringify(emitted).includes(secret), false);
  t.mock.restoreAll();
  assert.equal(globalThis.fetch, ORIGINAL_DIAGNOSTIC_METHODS.fetch);
  for (const level of ['info', 'warn', 'error']) assert.equal(console[level], ORIGINAL_DIAGNOSTIC_METHODS[level]);
});

test('account deletion emits success only after deletion and diagnostic sink failures never change responses', async t => {
  const env = { ...environment(), ...configuredEngine() }; const logged = await login(env); const emitted = [];
  t.mock.method(console, 'info', text => {
    assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM users').get().n, 0);
    emitted.push(JSON.parse(text));
  });
  assert.equal((await call(env, '/api/me', { method: 'DELETE', cookie: logged.cookie })).response.status, 200);
  assert.deepEqual(emitted, [{ event: 'oraclebot.account_deleted' }]);
  const failedSink = () => { throw new Error('diagnostic sink failed'); };
  console.info.mock.mockImplementation(failedSink);
  for (const level of ['warn', 'error']) t.mock.method(console, level, failedSink);
  t.mock.method(globalThis, 'fetch', async () => Response.json({ strategies: [] }));
  assert.equal((await call(env, '/api/strategies')).response.status, 200);
  globalThis.fetch.mock.mockImplementation(async () => { throw new Error('private-network-error'); });
  assert.equal((await call(env, '/api/strategies')).response.status, 503);
  assert.equal((await call(env, '/api/me', { method: 'DELETE', cookie: logged.cookie })).response.status, 401);
  const another = await login(env);
  assert.equal((await call(env, '/api/me', { method: 'DELETE', cookie: another.cookie })).response.status, 200);
  t.mock.restoreAll();
  assert.equal(globalThis.fetch, ORIGINAL_DIAGNOSTIC_METHODS.fetch);
  for (const level of ['info', 'warn', 'error']) assert.equal(console[level], ORIGINAL_DIAGNOSTIC_METHODS[level]);
});

test('expected-account header rejects a changed cookie owner before reads or mutations', async t => {
  const env = { ...environment(), STRIPE_SECRET_KEY: 'sk_test_fixture', STRIPE_PORTAL_CONFIGURATION_ID: 'bpc_test' };
  const a = await login(env); const b = await login(env);
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_fixture', b.user.id);
  let upstream = 0;
  t.mock.method(globalThis, 'fetch', () => { upstream++; assert.fail('mismatched identity must not reach a provider'); });
  const headers = { 'X-Oraclebot-Account': a.user.id };
  for (const [path, method, body] of [
    ['/api/me', 'GET'], ['/api/bots', 'GET'], ['/api/agent/grants', 'GET'],
    ['/api/bots', 'POST', bot], ['/api/backtests', 'POST', { coin: 'SOL', strategy: 'rsi' }],
    ['/api/billing/checkout', 'POST', { plan: 'starter' }], ['/api/billing/portal', 'POST', {}],
    ['/api/me', 'DELETE', {}], ['/api/auth/logout', 'POST', {}],
  ]) {
    const result = await call(env, path, { method, body, cookie: b.cookie, headers });
    assert.equal(result.response.status, 409, path);
    assert.equal(result.data.error, 'account_changed', path);
  }
  assert.equal(upstream, 0);
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM bots').get().n, 0);
  assert.equal((await call(env, '/api/me', { cookie: b.cookie })).data.user.id, b.user.id);
  assert.equal((await call(env, '/api/me', { cookie: b.cookie, headers: { 'X-Oraclebot-Account': b.user.id } })).response.status, 200);
  assert.equal((await call(env, '/api/bots', { headers })).response.status, 401);
});
