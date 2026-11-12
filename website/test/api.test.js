import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';
import worker, { hasEntitlement, validateBot, verifyStripeSignature } from '../src/worker.js';
import { base58Encode } from '../../extension/src/wallet/solana.js';

const ORIGIN = 'https://oraclebot.example';
const at = () => Math.floor(Date.now() / 1000);
function environment() {
  const sqlite = new DatabaseSync(':memory:');
  sqlite.exec(readFileSync(new URL('../migrations/0001_accounts.sql', import.meta.url), 'utf8'));
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
async function login(env) {
  const { keys, wallet } = await keypair();
  const challenge = await call(env, '/api/auth/challenge', { method: 'POST', body: { wallet } });
  assert.equal(challenge.response.status, 200);
  const signature = Buffer.from(await crypto.subtle.sign('Ed25519', keys.privateKey, new TextEncoder().encode(challenge.data.message))).toString('base64');
  const verified = await call(env, '/api/auth/verify', { method: 'POST', body: { id: challenge.data.id, signature } });
  assert.equal(verified.response.status, 200);
  return { ...verified.data, wallet, cookie: verified.response.headers.get('Set-Cookie').split(';')[0], challenge: challenge.data, signature };
}
function grant(env, user, status = 'trialing') {
  env.sqlite.prepare('INSERT INTO subscriptions (user_id,stripe_subscription_id,status,period_end,trial_end,updated_at) VALUES (?,?,?,?,?,?)').run(user.id, `sub_${user.id.replaceAll('-', '')}`, status, at() + 86400, at() + 86400, at());
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
  const result = await call(env, '/api/billing/checkout', { method: 'POST', cookie: logged.cookie });
  assert.equal(result.response.status, 503); assert.equal(result.data.error, 'billing_unavailable');
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM subscriptions').get().n, 0);
});
test('forged webhook cannot mutate subscriptions', async () => {
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_PRICE_ID: 'price_server' };
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
  assert.ok(env.batches.at(-1)[0].meta.changes > 1, 'D1 change count includes cascaded sessions, bots and subscription');
  assert.equal(env.batches.at(-1)[0].results[0].id, logged.user.id);
  for (const table of ['users', 'sessions', 'bots', 'subscriptions']) assert.equal(env.sqlite.prepare(`SELECT COUNT(*) AS n FROM ${table}`).get().n, 0);
  const ledger = env.sqlite.prepare('SELECT * FROM trial_history').get();
  assert.equal(ledger.wallet_hash.length, 64); assert.notEqual(ledger.wallet_hash, logged.wallet);
});
test('webhook reconciles canonical subscription once and refuses out-of-order regressions', async t => {
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_PRICE_ID: 'price_server' };
  const logged = await login(env);
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_test', logged.user.id);
  let calls = 0;
  let current = { id: 'sub_test', customer: 'cus_test', status: 'trialing', created: 50, trial_start: 80, trial_end: at() + 604800, current_period_end: at() + 604800, items: { data: [{ price: { id: 'price_server' } }] }, metadata: { oraclebot_user: logged.user.id } };
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
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_PRICE_ID: 'price_server' };
  await login(env);
  t.mock.method(globalThis, 'fetch', async () => Response.json({ id: 'sub_unknown', customer: 'cus_unknown', status: 'active', metadata: {} }));
  const signed = await signedEvent({ id: 'evt_unknown', created: 100, type: 'customer.subscription.created', data: { object: { id: 'sub_unknown' } } }, env.STRIPE_WEBHOOK_SECRET);
  const response = await worker.fetch(new Request(`${ORIGIN}/api/billing/webhook`, { method: 'POST', headers: { 'Stripe-Signature': signed.header }, body: signed.raw }), env);
  assert.equal(response.status, 200); assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM subscriptions').get().n, 0);
});
test('Stripe checkout sends a server-owned price and a seven-day first trial', async t => {
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_PRICE_ID: 'price_server' };
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
  const result = await call(env, '/api/billing/checkout', { method: 'POST', cookie: logged.cookie, body: { price: 'price_attacker', trialDays: 900 } });
  assert.equal(result.response.status, 200); assert.equal(result.data.trialDays, 7); assert.equal(paths.length, 3);
  assert.equal((await call(env, '/api/billing/checkout', { method: 'POST', cookie: logged.cookie })).response.status, 409);
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM subscriptions').get().n, 0);
});
test('used trials cannot be renewed by another checkout request', async t => {
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_PRICE_ID: 'price_server' };
  const logged = await login(env);
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=?,trial_used=1 WHERE id=?').run('cus_test', logged.user.id);
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    if (url.includes('/subscriptions?')) return Response.json({ data: [{ status: 'canceled', trial_start: 1 }], has_more: false });
    assert.equal(options.body.has('subscription_data[trial_period_days]'), false);
    return Response.json({ url: 'https://checkout.stripe.com/c/pay/session' });
  });
  const result = await call(env, '/api/billing/checkout', { method: 'POST', cookie: logged.cookie });
  assert.equal(result.response.status, 200); assert.equal(result.data.trialDays, 0);
});
test('expired trial and billing provider failure never produce backtest access', async t => {
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_PRICE_ID: 'price_server' };
  const logged = await login(env); grant(env, logged.user); env.sqlite.prepare('UPDATE subscriptions SET trial_end=1').run();
  assert.equal((await call(env, '/api/backtests', { method: 'POST', cookie: logged.cookie, body: {} })).response.status, 402);
  t.mock.method(globalThis, 'fetch', async () => new Response('failure', { status: 500 }));
  assert.equal((await call(env, '/api/billing/checkout', { method: 'POST', cookie: logged.cookie })).response.status, 502);
  assert.equal((await call(env, '/api/me', { cookie: logged.cookie })).data.subscription.entitled, false);
});

test('pending checkout prevents account deletion and its lock survives an ambiguous create', async t => {
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_PRICE_ID: 'price_server' };
  const logged = await login(env);
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=? WHERE id=?').run('cus_test', logged.user.id);
  let creates = 0;
  t.mock.method(globalThis, 'fetch', async url => {
    if (url.includes('/subscriptions?')) return Response.json({ data: [], has_more: false });
    creates++;
    throw new DOMException('The operation timed out', 'TimeoutError');
  });
  assert.equal((await call(env, '/api/billing/checkout', { method: 'POST', cookie: logged.cookie })).response.status, 504);
  assert.equal((await call(env, '/api/me', { method: 'DELETE', cookie: logged.cookie })).data.error, 'checkout_pending');
  assert.equal((await call(env, '/api/billing/checkout', { method: 'POST', cookie: logged.cookie })).data.error, 'checkout_pending');
  assert.equal(creates, 1);
  // The old 30-minute timeout must not unlock a still-payable 35-minute session.
  env.sqlite.prepare('UPDATE users SET checkout_pending_at=?').run(at() - 1801);
  assert.equal((await call(env, '/api/billing/checkout', { method: 'POST', cookie: logged.cookie })).data.error, 'checkout_pending');
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
  const env = { ...environment(), STRIPE_WEBHOOK_SECRET: 'test_webhook', STRIPE_SECRET_KEY: 'test_secret', STRIPE_PRICE_ID: 'price_server' };
  const logged = await login(env); const pendingAt = at();
  env.sqlite.prepare('UPDATE users SET stripe_customer_id=?,checkout_pending_at=? WHERE id=?').run('cus_test', pendingAt, logged.user.id);
  t.mock.method(globalThis, 'fetch', async () => Response.json({ id: 'sub_old', customer: 'cus_test', status: 'canceled', created: 1, trial_start: 1, trial_end: 2, metadata: { oraclebot_user: logged.user.id }, items: { data: [{ price: { id: 'price_server' } }] } }));
  const event = { id: 'evt_old', created: 100, type: 'checkout.session.completed', data: { object: { subscription: 'sub_old', customer: 'cus_test', expires_at: pendingAt - 100, metadata: { oraclebot_user: logged.user.id } } } };
  const signed = await signedEvent(event, env.STRIPE_WEBHOOK_SECRET);
  const response = await worker.fetch(new Request(`${ORIGIN}/api/billing/webhook`, { method: 'POST', headers: { 'Stripe-Signature': signed.header }, body: signed.raw }), env);
  assert.equal(response.status, 200);
  assert.equal(env.sqlite.prepare('SELECT checkout_pending_at FROM users').get().checkout_pending_at, pendingAt);
  assert.equal((await call(env, '/api/me', { method: 'DELETE', cookie: logged.cookie })).data.error, 'checkout_pending');
});
