import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, statSync, chmodSync, symlinkSync, readdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { API_VERSION, RunnerError, RunStore, StripeTestClient, assertTestConfig, readConfiguration,
  sourceBindings, openPrivateDatabase, pollClock, cleanupOwned, main } from '../scripts/verify-stripe-lifecycle.mjs';
import { preparePlanChange, commitPlanChange, getPlanChange } from '../src/billing-lifecycle.js';

// Every transport below is an injected stand-in. These tests prove runner
// safety/source integration; they do not claim any real Stripe lifecycle passed.
const TEST_KEY = 'sk_test_fixture_only_12345678';
const ACCOUNT = 'acct_fixture123456';
const CONFIG = { key: TEST_KEY, account: ACCOUNT };
const BINDINGS = { 'fixture-only': 'immutable-source-binding' };
const reply = (value, status = 200) => new Response(JSON.stringify(value), { status });
const failure = code => error => error instanceof RunnerError && error.code === code;
function temporary(t) {
  const directory = mkdtempSync(join(tmpdir(), 'oraclebot-stripe-runner-'));
  t.after(() => rmSync(directory, { recursive: true, force: true })); return directory;
}
function storeFor(t, { bindings = BINDINGS, now = Date.now } = {}) {
  const directory = join(temporary(t), 'run');
  const store = new RunStore(directory, { account: ACCOUNT, bindings, now });
  t.after(() => store.close()); return store;
}
function transport(handler) {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, method: options.method, headers: options.headers, fields: new URLSearchParams(options.body) });
    return handler(new URL(url), options, calls);
  };
  return { calls, fetchImpl };
}
async function verified(t, handler, options = {}) {
  const store = options.store || storeFor(t, options);
  const wire = transport((url, request, calls) => url.pathname === '/v1/account' ? reply({ id: ACCOUNT, object: 'account' }) : handler(url, request, calls));
  const client = new StripeTestClient(CONFIG, store, { fetchImpl: wire.fetchImpl, ...(options.now ? { now: options.now } : {}) });
  await client.verifyMerchant(); return { store, client, ...wire };
}

test('plan mode does not read credentials, create state or issue HTTP', async t => {
  const directory = join(temporary(t), 'must-not-exist'); let calls = 0; const outputs = [];
  const env = new Proxy({}, { get() { throw new Error('Plan must not read credentials'); } });
  const result = await main(['--plan', '--run-dir', directory, '--env-file', '/does/not/exist'], {
    env, fetchImpl: async () => { calls++; throw new Error('Unexpected HTTP'); }, output: value => outputs.push(value),
  });
  assert.equal(result.mode, 'PLAN_ONLY'); assert.equal(calls, 0); assert.equal(outputs.length, 1);
  assert.deepEqual(readdirSync(join(directory, '..')), []);
  assert.ok(result.separateUnverifiedGates.some(value => /webhook/.test(value)));
});

test('missing, publishable, malformed and live secrets fail before any HTTP', async () => {
  for (const key of [undefined, '', 'pk_test_fixture1234', 'sk_live_fixture1234', 'rk_live_fixture1234', 'sk_test_short', `${TEST_KEY}\n`, `${TEST_KEY} `]) {
    let calls = 0;
    await assert.rejects(main(['--execute', '--run-dir', '/nonexistent'], {
      env: { STRIPE_ORACLEBOT_TEST_SEC_KEY: key, STRIPE_ORACLEBOT_ACCTNUM: ACCOUNT },
      fetchImpl: async () => { calls++; return reply({}); }, output() {},
    }), failure('test_secret_required'));
    assert.equal(calls, 0);
  }
});

test('test configuration never borrows live key and requires an explicit expected merchant', () => {
  assert.throws(() => assertTestConfig({ STRIPE_ORACLEBOT_SEC_KEY: TEST_KEY, STRIPE_ORACLEBOT_ACCTNUM: ACCOUNT }), failure('test_secret_required'));
  assert.throws(() => assertTestConfig({ STRIPE_ORACLEBOT_TEST_SEC_KEY: TEST_KEY }), failure('expected_test_merchant_required'));
  assert.throws(() => assertTestConfig({ STRIPE_ORACLEBOT_TEST_SEC_KEY: TEST_KEY, STRIPE_ORACLEBOT_ACCTNUM: 'not-an-account' }), failure('expected_test_merchant_required'));
  assert.equal(assertTestConfig({ STRIPE_ORACLEBOT_TEST_SEC_KEY: 'rk_test_fixture_only_12345678', STRIPE_ORACLEBOT_ACCTNUM: ACCOUNT }).account, ACCOUNT);
  assert.equal(assertTestConfig({ STRIPE_ORACLEBOT_TEST_SEC_KEY: TEST_KEY, STRIPE_ORACLEBOT_TEST_ACCTNUM: 'acct_sandbox123', STRIPE_ORACLEBOT_ACCTNUM: ACCOUNT }).account, 'acct_sandbox123');
});

test('env file must be a private owned regular file and is parsed without executing shell text', t => {
  const directory = temporary(t); const file = join(directory, 'test.env');
  writeFileSync(file, `STRIPE_ORACLEBOT_TEST_SEC_KEY=${TEST_KEY}\nSTRIPE_ORACLEBOT_ACCTNUM=${ACCOUNT}\nUNRELATED=$(do-not-run)\n`, { mode: 0o600 });
  assert.deepEqual(readConfiguration({}, file), CONFIG);
  const link = join(directory, 'link.env'); symlinkSync(file, link);
  assert.throws(() => readConfiguration({}, link), failure('private_file_permissions'));
  chmodSync(file, 0o644); assert.throws(() => readConfiguration({}, file), failure('private_file_permissions'));
  assert.throws(() => readConfiguration({}, 'relative.env'), failure('env_file_requires_absolute_path'));
});

test('unverified client refuses object requests; account mismatch cannot create objects', async t => {
  const store = storeFor(t); const wire = transport(() => reply({ id: 'acct_someoneelse' }));
  const client = new StripeTestClient(CONFIG, store, { fetchImpl: wire.fetchImpl });
  await assert.rejects(client.request('GET', 'products/prod_foreign'), failure('merchant_not_verified'));
  await assert.rejects(client.verifyMerchant(), failure('test_merchant_mismatch'));
  await assert.rejects(client.fixture('products', { name: 'unused' }, 'unused'), failure('merchant_not_verified'));
  assert.equal(wire.calls.length, 1); assert.equal(wire.calls[0].method, 'GET');
});

test('verified transport pins Stripe origin/version, disables redirects, and never selects a Connect account', async t => {
  let received;
  const { client, store } = await verified(t, (_url, options) => { received = options; return reply({ id: 'prod_owned', object: 'product', livemode: false }); });
  const product = await client.fixture('products', { name: 'Synthetic test product', 'metadata[oraclebot_lifecycle_run]': store.data.runId }, 'owned-product');
  assert.equal(product.id, 'prod_owned'); assert.equal(received.headers['Stripe-Version'], API_VERSION);
  assert.equal(received.headers['Stripe-Account'], undefined); assert.equal(received.redirect, 'error');
  assert.equal(received.headers.Authorization, `Bearer ${TEST_KEY}`);
  assert.ok(received.headers['Idempotency-Key'].startsWith(store.data.runId));
  assert.equal(store.owned(product.id).kind, 'product');
});

test('arbitrary paths, unsupported methods, unbounded lists and raw card fields fail without HTTP', async t => {
  const { client, store, calls } = await verified(t, () => { throw new Error('Forbidden HTTP'); });
  store.resource('payment_method', 'pm_owned');
  const before = calls.length;
  for (const path of ['https://evil.example/v1/products', '../account', 'products/%2e%2e/account', 'products/prod_owned#x', 'subscriptions/sub_owned/cancel', 'customers?limit=100']) {
    await assert.rejects(client.request('GET', path), RunnerError);
  }
  await assert.rejects(client.request('GET', 'customers'), failure('unbounded_list_rejected'));
  await assert.rejects(client.request('PATCH', 'payment_methods/pm_owned', {}), failure('stripe_method_rejected'));
  await assert.rejects(client.fixture('payment_methods', { type: 'card', 'card[number]': '4242424242424242', 'metadata[oraclebot_lifecycle_run]': store.data.runId }, 'raw-card'), failure('stripe_fields_rejected'));
  await assert.rejects(client.fixture('payment_methods', { type: 'card', 'card[token]': 'tok_chargeDeclined', 'metadata[oraclebot_lifecycle_run]': store.data.runId }, 'wrong-token'), failure('official_test_token_required'));
  assert.equal(calls.length, before);
});

test('unowned objects and missing metadata/idempotency are rejected before HTTP', async t => {
  const { client, store, calls } = await verified(t, () => { throw new Error('Forbidden HTTP'); });
  const before = calls.length;
  await assert.rejects(client.request('GET', 'products/prod_foreign'), failure('unowned_object'));
  await assert.rejects(client.fixture('products', { name: 'Unmarked' }, 'unmarked'), failure('fixture_ownership_required'));
  await assert.rejects(client.request('POST', 'products', { name: 'Marked', 'metadata[oraclebot_lifecycle_run]': store.data.runId }), failure('idempotency_key_required'));
  store.resource('subscription_schedule', 'sub_sched_owned');
  await assert.rejects(client.request('DELETE', 'subscription_schedules/sub_sched_owned', null, { key: 'must-not-cancel' }), failure('stripe_delete_rejected'));
  assert.equal(calls.length, before);
});

test('live objects, nested live prices and substituted IDs fail closed', async t => {
  let value = { id: 'prod_owned', object: 'product', livemode: true };
  const { client, store } = await verified(t, () => reply(value)); store.resource('product', 'prod_owned');
  await assert.rejects(client.request('GET', 'products/prod_owned'), failure('live_object_refused'));
  value = { id: 'prod_owned', object: 'product', livemode: false, default_price: { id: 'price_live', livemode: true } };
  await assert.rejects(client.request('GET', 'products/prod_owned'), failure('live_object_refused'));
  value = { id: 'prod_different', object: 'product', livemode: false };
  await assert.rejects(client.request('GET', 'products/prod_owned'), failure('provider_object_binding_mismatch'));
  value = { id: 'prod_owned', object: 'product' };
  await assert.rejects(client.request('GET', 'products/prod_owned'), failure('test_object_required'));
});

test('completed fixture requests are recovered by canonical GET; completed steps do not duplicate creation', async t => {
  const { client, store, calls } = await verified(t, () => reply({ id: 'prod_owned', object: 'product', livemode: false }));
  const fields = { name: 'Synthetic', 'metadata[oraclebot_lifecycle_run]': store.data.runId };
  await client.fixture('products', fields, 'fixture-product');
  await client.fixture('products', fields, 'fixture-product');
  let performed = 0;
  await store.step('completed', async () => { performed++; return { id: 'prod_owned' }; });
  await store.step('completed', async () => { performed++; return { id: 'bad' }; });
  assert.equal(performed, 1); assert.equal(calls.filter(call => call.method === 'POST').length, 1);
  assert.equal(calls.at(-1).method, 'GET');
  assert.equal(statSync(store.manifestPath).mode & 0o777, 0o600);
  assert.equal(statSync(store.directory).mode & 0o777, 0o700);
  const manifest = readFileSync(store.manifestPath, 'utf8');
  assert.ok(!manifest.includes(TEST_KEY)); assert.ok(!manifest.includes('Authorization'));
  assert.equal(store.data.gates.sourceModuleProviderLifecycle, 'NOT_RUN');
});

test('fixture crash recovery preserves one idempotency key and rejects payload changes or expired replay', async t => {
  let time = 1000; let fail = true;
  const { client, store, calls } = await verified(t, () => {
    if (fail) throw new Error('network failed after send');
    return reply({ id: 'prod_owned', object: 'product', livemode: false });
  }, { now: () => time });
  const fields = { name: 'Synthetic', 'metadata[oraclebot_lifecycle_run]': store.data.runId };
  await assert.rejects(client.fixture('products', fields, 'unknown-fixture'), failure('provider_transport_unknown'));
  assert.equal(store.data.requests[`${store.data.runId}-unknown-fixture`].state, 'intent');
  const before = calls.length;
  await assert.rejects(client.fixture('products', { ...fields, name: 'Changed' }, 'unknown-fixture'), failure('idempotency_payload_changed'));
  assert.equal(calls.length, before);
  fail = false; await client.fixture('products', fields, 'unknown-fixture');
  const sends = calls.filter(call => call.method === 'POST');
  assert.equal(sends[0].headers['Idempotency-Key'], sends[1].headers['Idempotency-Key']);
  fail = true;
  await assert.rejects(client.fixture('products', fields, 'expired-fixture'), failure('provider_transport_unknown'));
  time += 23 * 3600000;
  const expiredBefore = calls.length;
  await assert.rejects(client.fixture('products', fields, 'expired-fixture'), failure('idempotency_window_expired'));
  assert.equal(calls.length, expiredBefore);
});

test('ambiguous production module writes cannot be replayed even with the same idempotency key', async t => {
  const { client, store, calls } = await verified(t, () => { throw new Error('timeout'); });
  store.resource('subscription', 'sub_owned');
  const stripe = client.stripe(); const fields = { cancel_at_period_end: 'true' };
  await assert.rejects(stripe('subscriptions/sub_owned', fields, 'oraclebot-source-operation'), failure('provider_transport_unknown'));
  const before = calls.length;
  await assert.rejects(stripe('subscriptions/sub_owned', fields, 'oraclebot-source-operation'), failure('source_mutation_requires_canonical_reconciliation'));
  assert.equal(calls.length, before);
});

test('provider error text, PII and key-like strings never escape safe errors or manifests', async t => {
  const confidential = 'sk_live_malicious_provider_text_123 someone@example.com';
  const { client, store } = await verified(t, () => reply({ error: { message: confidential } }, 402));
  store.resource('product', 'prod_owned');
  let caught;
  try { await client.request('GET', 'products/prod_owned'); } catch (error) { caught = error; }
  assert.equal(caught.code, 'provider_http_error'); assert.equal(caught.status, 402);
  assert.ok(!String(caught).includes(confidential)); assert.ok(!readFileSync(store.manifestPath, 'utf8').includes(confidential));
});

test('clock polling waits for actual ready time and has a finite bound', async t => {
  let count = 0; let pauseCount = 0;
  const { client, store } = await verified(t, () => reply({ id: 'clock_owned', object: 'test_helpers.test_clock', livemode: false,
    status: ++count < 3 ? 'advancing' : 'ready', frozen_time: 1234 }));
  store.resource('test_clock', 'clock_owned');
  assert.equal((await pollClock(client, 'clock_owned', 1234, { attempts: 3, pause: async () => { pauseCount++; } })).frozen_time, 1234);
  assert.equal(pauseCount, 2);
  await assert.rejects(pollClock(client, 'clock_owned', 1235, { attempts: 1 }), failure('clock_time_unverified'));
  count = -100;
  await assert.rejects(pollClock(client, 'clock_owned', 1234, { attempts: 2, pause: async () => {} }), failure('clock_not_ready'));
});

test('foreign customers on an owned clock prevent every cleanup mutation', async t => {
  let runId;
  const { client, store, calls } = await verified(t, url => {
    if (url.pathname.includes('/test_clocks/')) return reply({ id: 'clock_owned', livemode: false, status: 'ready', frozen_time: 123,
      name: `${runId}:success` });
    if (url.pathname === '/v1/customers') return reply({ object: 'list', has_more: false,
      data: [{ id: 'cus_foreign', object: 'customer', livemode: false, test_clock: 'clock_owned', metadata: {} }] });
    throw new Error('Unexpected path');
  });
  runId = store.data.runId; store.resource('test_clock', 'clock_owned', { scenario: 'success' });
  store.resource('customer', 'cus_expected', { scenario: 'success' });
  await assert.rejects(cleanupOwned(client), failure('unowned_object'));
  assert.equal(calls.filter(call => call.method !== 'GET').length, 0);
});

test('cleanup validates all catalog ownership before deleting a clock, then releases no subscriptions by cancel', async t => {
  let runId; let badMetadata = true;
  const { client, store, calls } = await verified(t, (url, options) => {
    const path = url.pathname;
    if (path.includes('/test_clocks/') && options.method === 'GET') return reply({ id: 'clock_owned', livemode: false, status: 'ready', frozen_time: 123, name: `${runId}:success` });
    if (path === '/v1/customers') return reply({ object: 'list', has_more: false,
      data: [{ id: 'cus_owned', object: 'customer', livemode: false, test_clock: 'clock_owned', metadata: { oraclebot_lifecycle_run: runId } }] });
    if (path === '/v1/prices/price_owned') return reply({ id: 'price_owned', object: 'price', livemode: false, active: options.method === 'POST' ? false : true,
      metadata: { oraclebot_lifecycle_run: badMetadata ? 'a-different-run' : runId } });
    if (path.includes('/test_clocks/') && options.method === 'DELETE') return reply({ id: 'clock_owned', deleted: true });
    throw new Error('Unexpected path');
  });
  runId = store.data.runId; store.resource('test_clock', 'clock_owned', { scenario: 'success' });
  store.resource('customer', 'cus_owned', { scenario: 'success' }); store.resource('price', 'price_owned');
  await assert.rejects(cleanupOwned(client), failure('cleanup_catalog_ownership'));
  assert.equal(calls.filter(call => call.method !== 'GET').length, 0);
  badMetadata = false; await cleanupOwned(client);
  assert.equal(calls.filter(call => call.method === 'DELETE').length, 1);
  assert.equal(calls.filter(call => call.method === 'POST').length, 1);
  assert.ok(calls.every(call => !/subscription_schedules.*cancel/.test(call.url)));
  const mutations = calls.filter(call => call.method !== 'GET').length;
  await cleanupOwned(client); assert.equal(calls.filter(call => call.method !== 'GET').length, mutations);
});

test('state refuses symlinks, open permissions, unrelated contents and a running lock', t => {
  const parent = temporary(t); const target = join(parent, 'actual'); mkdirSync(target, { mode: 0o700 });
  const link = join(parent, 'link'); symlinkSync(target, link);
  assert.throws(() => new RunStore(link, { account: ACCOUNT, bindings: BINDINGS }), failure('private_directory_permissions'));
  chmodSync(target, 0o755);
  assert.throws(() => new RunStore(target, { account: ACCOUNT, bindings: BINDINGS }), failure('private_directory_permissions'));
  chmodSync(target, 0o700); writeFileSync(join(target, 'unrelated'), 'Do not adopt me');
  assert.throws(() => new RunStore(target, { account: ACCOUNT, bindings: BINDINGS }), failure('run_directory_not_empty'));
  const store = storeFor(t);
  assert.throws(() => new RunStore(store.directory, { account: ACCOUNT, bindings: BINDINGS, resume: true }), failure('run_locked'));
});

test('resume binds exact merchant and source hashes before HTTP or state mutation', t => {
  const store = storeFor(t); const directory = store.directory; store.close();
  assert.throws(() => new RunStore(directory, { account: 'acct_different123', resume: true, bindings: BINDINGS }), failure('manifest_merchant_mismatch'));
  assert.throws(() => new RunStore(directory, { account: ACCOUNT, resume: true, bindings: { 'fixture-only': 'different' } }), failure('source_changed_since_run'));
  const resumed = new RunStore(directory, { account: ACCOUNT, resume: true, bindings: BINDINGS });
  assert.equal(resumed.data.runId, store.data.runId); resumed.close();
});

test('private SQLite executes all real migrations once, preserves evidence on resume and grants no entitlement', t => {
  const bindings = sourceBindings();
  assert.ok(bindings['src/billing-lifecycle.js']); assert.ok(bindings['test/helpers/d1.js']);
  assert.ok(Object.keys(bindings).some(name => /migrations\/0009_/.test(name)));
  const store = storeFor(t, { bindings }); const env = openPrivateDatabase(store);
  const count = env.sqlite.prepare('SELECT count(*) AS n FROM verification_migrations').get().n;
  assert.equal(count, Object.keys(bindings).filter(name => name.startsWith('migrations/')).length);
  assert.equal(env.sqlite.prepare('SELECT count(*) AS n FROM stripe_events').get().n, 0);
  const columns = env.sqlite.prepare('PRAGMA table_info(users)').all().map(row => row.name);
  assert.ok(columns.includes('deletion_token')); assert.ok(columns.includes('execution_initialized_at'));
  env.sqlite.close(); const reopened = openPrivateDatabase(store);
  assert.equal(reopened.sqlite.prepare('SELECT count(*) AS n FROM verification_migrations').get().n, count);
  reopened.sqlite.close(); assert.equal(statSync(join(store.directory, 'state.sqlite3')).mode & 0o777, 0o600);
});

test('actual billing module uses serialized HTTP transport and real D1 without projecting entitlement', async t => {
  const now = Math.floor(Date.now() / 1000); const userId = 'test_source_module_user';
  const store = storeFor(t); const env = openPrivateDatabase(store); t.after(() => env.sqlite.close());
  const makePrice = (priceId, amount) => ({ id: priceId, object: 'price', livemode: false, currency: 'usd', unit_amount: amount,
    active: true, type: 'recurring', recurring: { interval: 'month', interval_count: 1, usage_type: 'licensed' } });
  const starter = makePrice('price_starter', 999); const advanced = makePrice('price_advanced', 2999);
  let sub = { id: 'sub_owned', object: 'subscription', livemode: false, customer: 'cus_owned', status: 'active', trial_end: null,
    cancel_at_period_end: false, pending_update: null, schedule: null, metadata: { oraclebot_user: userId },
    items: { has_more: false, data: [{ id: 'si_owned', quantity: 1, current_period_start: now - 86400,
      current_period_end: now + 20 * 86400, price: starter }] } };
  let ambiguous = false;
  const wire = transport((url, options) => {
    if (url.pathname === '/v1/account') return reply({ id: ACCOUNT });
    if (url.pathname === '/v1/prices/price_advanced') return reply(advanced);
    if (url.pathname === '/v1/invoices/create_preview') return reply({ object: 'invoice', livemode: false, customer: 'cus_owned', currency: 'usd', amount_due: 1300 });
    if (url.pathname === '/v1/subscriptions/sub_owned') {
      if (options.method === 'POST') {
        const fields = new URLSearchParams(options.body);
        assert.equal(fields.get('payment_behavior'), 'pending_if_incomplete');
        assert.equal(fields.get('proration_behavior'), 'always_invoice');
        assert.equal(fields.get('billing_cycle_anchor[type]'), 'unchanged');
        assert.equal(fields.get('proration_date'), String(now));
        sub = { ...sub, metadata: { ...sub.metadata, oraclebot_change_id: fields.get('metadata[oraclebot_change_id]') },
          items: { ...sub.items, data: [{ ...sub.items.data[0], price: advanced }] } };
        if (ambiguous) throw new Error('Response lost after successful provider mutation');
      }
      return reply(sub);
    }
    throw new Error('Unexpected path');
  });
  const client = new StripeTestClient(CONFIG, store, { fetchImpl: wire.fetchImpl }); await client.verifyMerchant();
  for (const [kind, resourceId] of [['subscription', 'sub_owned'], ['customer', 'cus_owned'], ['price', 'price_starter'], ['price', 'price_advanced'], ['price', 'price_unlimited']]) store.resource(kind, resourceId);
  env.sqlite.prepare('INSERT INTO users(id,wallet,created_at,stripe_customer_id) VALUES(?,?,?,?)').run(userId, 'synthetic_wallet', now, 'cus_owned');
  env.sqlite.prepare("INSERT INTO subscriptions(user_id,stripe_subscription_id,status,updated_at) VALUES(?,?,'verification_only',?)").run(userId, 'sub_owned', now);
  Object.assign(env, { STRIPE_STARTER_PRICE_ID: 'price_starter', STRIPE_ADVANCED_PRICE_ID: 'price_advanced', STRIPE_UNLIMITED_PRICE_ID: 'price_unlimited' });
  const user = { id: userId }; const services = { stripe: client.stripe(), now: () => now };
  const quote = await preparePlanChange(env, user, { plan: 'advanced' }, services);
  assert.equal(quote.amountDueNowCents, 1300); ambiguous = true;
  const result = await commitPlanChange(env, user, { quoteId: quote.quoteId, idempotencyKey: 'actual-source-http-operation' }, services);
  assert.equal(result.status, 'unknown');
  const reconciled = await getPlanChange(env, user, result.changeId, services);
  assert.equal(reconciled.status, 'applied');
  assert.equal(wire.calls.filter(call => call.method === 'POST' && call.url.endsWith('/subscriptions/sub_owned')).length, 1);
  const local = env.sqlite.prepare('SELECT * FROM subscriptions WHERE user_id=?').get(userId);
  assert.equal(local.status, 'verification_only'); assert.equal(local.plan_id, null); assert.equal(local.period_end, 0);
  assert.equal(env.sqlite.prepare('SELECT count(*) AS n FROM stripe_events').get().n, 0);
});
