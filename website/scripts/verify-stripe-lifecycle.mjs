#!/usr/bin/env node
/**
 * Real-provider, test-mode-only acceptance of the production billing module.
 * Default: print the plan without reading credentials or contacting Stripe.
 *
 * Execute with --execute --run-dir /absolute/private/directory. Use --resume
 * with the same directory after interruption, or --cleanup to remove only its
 * owned test fixtures. The test secret must be STRIPE_ORACLEBOT_TEST_SEC_KEY.
 * No live-secret fallback, Connect impersonation, webhook fabrication or local
 * entitlement projection exists in this runner.
 */
import { createHash, randomUUID } from 'node:crypto';
import { constants, closeSync, existsSync, fsyncSync, lstatSync, mkdirSync, openSync,
  readFileSync, readdirSync, renameSync, statSync, unlinkSync, writeFileSync } from 'node:fs';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { parseEnv } from 'node:util';
import { createD1 } from '../test/helpers/d1.js';
import { preparePlanChange, commitPlanChange, getPlanChange, cancelPlanChange,
  setPeriodEndCancellation } from '../src/billing-lifecycle.js';

export const API_VERSION = '2026-10-28.endive';
const DAY = 86400;
const PRIVATE_MODE = 0o600;
const ROOT = fileURLToPath(new URL('../', import.meta.url));
const MIGRATIONS = join(ROOT, 'migrations');
const digest = value => createHash('sha256').update(typeof value === 'string' ? value : JSON.stringify(value)).digest('hex');
const ref = value => typeof value === 'string' ? value : value?.id;
const id = value => typeof value === 'string' && /^[A-Za-z0-9_]{3,128}$/.test(value);
const sleep = milliseconds => new Promise(done => setTimeout(done, milliseconds));
const stableFields = fields => Object.fromEntries(Object.entries(fields || {}).sort(([a], [b]) => a.localeCompare(b)));
const check = (condition, code) => { if (!condition) throw new RunnerError(code); };

export class RunnerError extends Error {
  constructor(code, status = null) {
    super(`Stripe lifecycle verification stopped: ${code}.`);
    this.name = 'RunnerError'; this.code = code; this.status = status;
  }
}

export function assertTestConfig(env) {
  // This check runs before even GET /account. Never fall back to the live key.
  const key = env.STRIPE_ORACLEBOT_TEST_SEC_KEY;
  check(typeof key === 'string' && /^(?:sk|rk)_test_[A-Za-z0-9_]{8,512}$/.test(key), 'test_secret_required');
  const account = env.STRIPE_ORACLEBOT_TEST_ACCTNUM || env.STRIPE_ORACLEBOT_ACCTNUM;
  check(typeof account === 'string' && /^acct_[A-Za-z0-9]{3,100}$/.test(account), 'expected_test_merchant_required');
  return Object.freeze({ key, account });
}

export function readConfiguration(env, envFile) {
  if (!envFile) return assertTestConfig(env);
  check(isAbsolute(envFile), 'env_file_requires_absolute_path');
  privateFile(envFile);
  check(statSync(envFile).size <= 131072, 'env_file_too_large');
  let parsed;
  try { parsed = parseEnv(readFileSync(envFile, 'utf8')); } catch { throw new RunnerError('env_file_invalid'); }
  // An explicitly supplied process value wins. Other environment variables in
  // the file are never installed into the runner's environment.
  const selected = {};
  for (const name of ['STRIPE_ORACLEBOT_TEST_SEC_KEY', 'STRIPE_ORACLEBOT_TEST_ACCTNUM', 'STRIPE_ORACLEBOT_ACCTNUM']) {
    selected[name] = env[name] || parsed[name];
  }
  return assertTestConfig(selected);
}

function privateFile(path) {
  const stat = lstatSync(path);
  check(stat.isFile() && !stat.isSymbolicLink() && stat.uid === process.getuid() && (stat.mode & 0o077) === 0,
    'private_file_permissions');
}

export function sourceBindings() {
  const paths = ['scripts/verify-stripe-lifecycle.mjs', 'src/billing-lifecycle.js', 'test/helpers/d1.js',
    ...readdirSync(MIGRATIONS).filter(name => /^\d{4}_.*\.sql$/.test(name)).sort().map(name => `migrations/${name}`)];
  return Object.fromEntries(paths.map(path => [path, digest(readFileSync(join(ROOT, path), 'utf8'))]));
}

export class RunStore {
  constructor(directory, { account, resume = false, bindings = sourceBindings(), now = Date.now } = {}) {
    check(isAbsolute(directory || ''), 'absolute_run_directory_required');
    this.directory = resolve(directory); this.now = now; this.closed = false;
    const parent = lstatSync(dirname(this.directory));
    check(parent.isDirectory() && !parent.isSymbolicLink() && parent.uid === process.getuid(), 'run_parent_ownership');
    if (!existsSync(this.directory)) {
      check(!resume, 'resume_manifest_missing'); mkdirSync(this.directory, { mode: 0o700 });
    }
    const stat = lstatSync(this.directory);
    check(stat.isDirectory() && !stat.isSymbolicLink() && stat.uid === process.getuid() && (stat.mode & 0o077) === 0,
      'private_directory_permissions');
    this.manifestPath = join(this.directory, 'manifest.json');
    if (existsSync(this.manifestPath)) {
      check(resume, 'existing_run_requires_resume'); privateFile(this.manifestPath);
      try { this.data = JSON.parse(readFileSync(this.manifestPath, 'utf8')); } catch { throw new RunnerError('manifest_invalid'); }
      check(this.data.schema === 1 && this.data.apiVersion === API_VERSION && /^obl_[a-f0-9]{32}$/.test(this.data.runId || ''), 'manifest_invalid');
      check(this.data.account === account, 'manifest_merchant_mismatch');
      check(JSON.stringify(this.data.sources) === JSON.stringify(bindings), 'source_changed_since_run');
    } else {
      check(!resume && readdirSync(this.directory).length === 0, 'run_directory_not_empty');
      this.data = { schema: 1, runId: `obl_${randomUUID().replaceAll('-', '')}`, apiVersion: API_VERSION,
        account, createdAt: Math.floor(now() / 1000), sources: bindings, status: 'prepared', resources: {},
        requests: {}, steps: {}, checks: [], gates: {
          sourceModuleProviderLifecycle: 'NOT_RUN', productionCheckoutBrowser: 'NOT_RUN',
          genuineProviderWebhookDelivery: 'NOT_RUN', productionEntitlementProjection: 'NOT_RUN',
        } };
    }
    this.lockPath = join(this.directory, '.runner.lock');
    if (existsSync(this.lockPath)) {
      check(resume, 'run_locked'); privateFile(this.lockPath);
      let prior; try { prior = JSON.parse(readFileSync(this.lockPath, 'utf8')); } catch { throw new RunnerError('run_lock_invalid'); }
      check(Number.isSafeInteger(prior.pid) && prior.pid > 0, 'run_lock_invalid');
      let stale = false;
      try { process.kill(prior.pid, 0); } catch (error) { stale = error.code === 'ESRCH'; }
      check(stale, 'run_locked'); unlinkSync(this.lockPath);
    }
    this.nonce = randomUUID();
    const fd = openSync(this.lockPath, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, PRIVATE_MODE);
    try { writeFileSync(fd, JSON.stringify({ pid: process.pid, nonce: this.nonce })); fsyncSync(fd); }
    finally { closeSync(fd); }
    this.save();
  }
  save() {
    check(!this.closed, 'run_closed');
    const temporary = join(this.directory, `.manifest-${randomUUID()}.tmp`);
    const fd = openSync(temporary, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, PRIVATE_MODE);
    try { writeFileSync(fd, `${JSON.stringify(this.data, null, 2)}\n`); fsyncSync(fd); }
    finally { closeSync(fd); }
    renameSync(temporary, this.manifestPath);
    const directoryFd = openSync(this.directory, constants.O_RDONLY);
    try { fsyncSync(directoryFd); } finally { closeSync(directoryFd); }
  }
  resource(kind, resourceId, details = {}) {
    check(id(resourceId), 'provider_object_id_invalid');
    const prior = this.data.resources[resourceId];
    check(!prior || prior.kind === kind, 'resource_binding_mismatch');
    this.data.resources[resourceId] = { ...prior, kind, ...details }; this.save();
    return resourceId;
  }
  owned(resourceId, kind) {
    const value = this.data.resources[resourceId];
    check(value && (!kind || value.kind === kind), 'unowned_object'); return value;
  }
  async step(name, perform) {
    if (this.data.steps[name]?.status === 'complete') return structuredClone(this.data.steps[name].value);
    this.data.steps[name] = { status: 'running', at: Math.floor(this.now() / 1000) }; this.save();
    try {
      const value = await perform();
      this.data.steps[name] = { status: 'complete', at: Math.floor(this.now() / 1000), value }; this.save();
      return value;
    } catch (error) {
      this.data.steps[name].status = 'blocked';
      this.data.steps[name].error = safeCode(error); this.save(); throw error;
    }
  }
  verify(name, condition, evidence) {
    check(condition, name);
    this.data.checks.push({ name, at: Math.floor(this.now() / 1000), source: 'actual_Stripe_API_and_production_billing_module', ...evidence });
    this.save();
  }
  close() {
    if (this.closed) return;
    if (existsSync(this.lockPath)) {
      privateFile(this.lockPath);
      const owner = JSON.parse(readFileSync(this.lockPath, 'utf8'));
      if (owner.nonce === this.nonce && owner.pid === process.pid) unlinkSync(this.lockPath);
    }
    this.closed = true;
  }
}

function safeCode(error) {
  return typeof error?.code === 'string' && /^[a-z][a-z0-9_]{1,80}$/.test(error.code) ? error.code : 'unclassified_failure';
}

const TYPES = Object.freeze({ products: 'product', prices: 'price', customers: 'customer', payment_methods: 'payment_method',
  subscriptions: 'subscription', subscription_schedules: 'subscription_schedule', invoices: 'invoice' });
function routeOf(path) {
  check(typeof path === 'string' && path.length < 1024 && !path.includes('..') && !path.includes('%') && !path.includes('#') && !path.includes('\\'), 'stripe_path_rejected');
  if (path === 'account') return { kind: 'account' };
  if (path === 'invoices/create_preview') return { kind: 'preview' };
  const match = /^(test_helpers\/test_clocks|products|prices|customers|payment_methods|subscriptions|subscription_schedules|invoices)(?:\/([A-Za-z0-9_]{3,128}))?(?:\/(advance|release|pay|detach|attach))?(\?.*)?$/.exec(path);
  check(match, 'stripe_path_rejected');
  const [, collection, resourceId, action, query] = match;
  const kind = collection === 'test_helpers/test_clocks' ? 'test_clock' : TYPES[collection];
  if (action) check((kind === 'test_clock' && action === 'advance') || (kind === 'subscription_schedule' && action === 'release') ||
    (kind === 'invoice' && action === 'pay') || (kind === 'payment_method' && ['attach', 'detach'].includes(action)), 'stripe_action_rejected');
  if (query) {
    check(collection === 'customers' && !resourceId && !action, 'stripe_query_rejected');
    const params = new URLSearchParams(query.slice(1));
    check([...params.keys()].every(name => ['test_clock', 'limit', 'starting_after'].includes(name)) && params.get('limit') === '100' && id(params.get('test_clock')), 'stripe_query_rejected');
  }
  return { collection, kind, resourceId, action, query };
}

function assertTestObject(value) {
  check(value && typeof value === 'object' && !Array.isArray(value), 'provider_response_invalid');
  const walk = item => {
    if (!item || typeof item !== 'object') return;
    check(item.livemode !== true, 'live_object_refused');
    for (const nested of Object.values(item)) if (nested && typeof nested === 'object') walk(nested);
  };
  walk(value);
  if (value.object === 'list') {
    check(Array.isArray(value.data) && typeof value.has_more === 'boolean', 'provider_list_invalid');
    for (const item of value.data) check(item.livemode === false, 'test_object_required');
  } else if (!value.deleted) check(value.livemode === false, 'test_object_required');
}

export class StripeTestClient {
  constructor(config, store, { fetchImpl = fetch, now = Date.now } = {}) {
    this.config = assertTestConfig({ STRIPE_ORACLEBOT_TEST_SEC_KEY: config?.key, STRIPE_ORACLEBOT_TEST_ACCTNUM: config?.account });
    this.store = store; this.fetchImpl = fetchImpl; this.now = now; this.verified = false;
  }
  async verifyMerchant() {
    const value = await this.#send('GET', 'account', null, null);
    check(value?.id === this.config.account, 'test_merchant_mismatch');
    this.verified = true; this.store.data.merchantVerifiedAt = Math.floor(this.now() / 1000); this.store.save();
    return value.id;
  }
  async #send(method, path, fields, key) {
    let response;
    try {
      response = await this.fetchImpl(`https://api.stripe.com/v1/${path}`, { method,
        headers: { Authorization: `Bearer ${this.config.key}`, 'Stripe-Version': API_VERSION,
          ...(fields ? { 'Content-Type': 'application/x-www-form-urlencoded' } : {}), ...(key ? { 'Idempotency-Key': key } : {}) },
        ...(fields ? { body: new URLSearchParams(stableFields(fields)).toString() } : {}), signal: AbortSignal.timeout(30000), redirect: 'error' });
    } catch { throw new RunnerError('provider_transport_unknown'); }
    let value;
    try {
      const body = await response.text(); check(body.length <= 2_000_000, 'provider_response_too_large'); value = JSON.parse(body);
    } catch { throw new RunnerError('provider_response_invalid', response.status); }
    // Stripe error messages can contain submitted data. They never leave this boundary.
    if (!response.ok) throw new RunnerError(response.status === 404 ? 'provider_object_missing' : 'provider_http_error', response.status);
    return value;
  }
  authorize(method, route, fields) {
    check(this.verified, 'merchant_not_verified');
    check(['GET', 'POST', 'DELETE'].includes(method) && route.kind !== 'account', 'stripe_method_rejected');
    if (route.resourceId) this.store.owned(route.resourceId, route.kind);
    if (route.query) this.store.owned(new URLSearchParams(route.query.slice(1)).get('test_clock'), 'test_clock');
    if (method === 'GET') {
      check(route.resourceId || route.query, 'unbounded_list_rejected'); check(!route.action, 'stripe_method_rejected'); return;
    }
    if (method === 'DELETE') { check(route.kind === 'test_clock' && route.resourceId && !route.action && !route.query, 'stripe_delete_rejected'); return; }
    check(!route.query && fields && typeof fields === 'object' && !Array.isArray(fields), 'stripe_fields_rejected');
    for (const [name, value] of Object.entries(fields)) {
      check(typeof value === 'string' && value.length <= 1000 && !/number|cvc|api.?key|secret|password/i.test(name), 'stripe_fields_rejected');
      check(!/(?:sk|rk)_(?:test|live)_/.test(value), 'stripe_fields_rejected');
    }
    if (route.kind === 'preview') {
      this.store.owned(fields.customer, 'customer'); this.store.owned(fields.subscription, 'subscription'); return;
    }
    if (route.kind === 'payment_method' && route.action === 'attach') this.store.owned(fields.customer, 'customer');
    if (!route.resourceId) {
      if (route.kind === 'test_clock') check(fields.name?.startsWith(`${this.store.data.runId}:`), 'fixture_ownership_required');
      else if (route.kind === 'subscription_schedule') this.store.owned(fields.from_subscription, 'subscription');
      else check(fields['metadata[oraclebot_lifecycle_run]'] === this.store.data.runId, 'fixture_ownership_required');
      if (route.kind === 'price') this.store.owned(fields.product, 'product');
      if (route.kind === 'customer') {
        this.store.owned(fields.test_clock, 'test_clock'); this.store.owned(fields.payment_method, 'payment_method');
        check(fields['metadata[oraclebot_user]'] && fields.email?.endsWith('@example.invalid'), 'synthetic_customer_required');
      }
      if (route.kind === 'subscription') {
        const owner = this.store.owned(fields.customer, 'customer');
        check(fields['metadata[oraclebot_user]'] === owner.userId, 'fixture_ownership_required');
      }
      if (route.kind === 'payment_method') check(fields.type === 'card' && ['tok_visa', 'tok_chargeCustomerFail'].includes(fields['card[token]']), 'official_test_token_required');
      check(route.kind !== 'invoice', 'fixture_creation_rejected');
    }
    for (const [name, value] of Object.entries(fields)) {
      if (/(?:^|\[)price\]?$/.test(name)) this.store.owned(value, 'price');
      if (['payment_method', 'default_payment_method', 'invoice_settings[default_payment_method]'].includes(name)) this.store.owned(value, 'payment_method');
    }
  }
  async request(method, path, fields = null, { key, purpose, scenario, userId, source = false } = {}) {
    const route = routeOf(path); this.authorize(method, route, fields);
    const mutation = method !== 'GET' && route.kind !== 'preview';
    let journal;
    if (mutation) {
      check(typeof key === 'string' && /^[A-Za-z0-9_-]{8,200}$/.test(key), 'idempotency_key_required');
      const hash = digest({ method, path, fields: stableFields(fields) }); journal = this.store.data.requests[key];
      check(!journal || journal.hash === hash, 'idempotency_payload_changed');
      if (journal?.state === 'complete') {
        check(journal.resultId && journal.resultPath, 'completed_request_unreadable');
        if (method === 'DELETE') return { id: journal.resultId, deleted: true };
        return this.request('GET', journal.resultPath);
      }
      if (journal) {
        check(!source && !journal.source, 'source_mutation_requires_canonical_reconciliation');
        check(this.now() - journal.startedAt < 23 * 3600000, 'idempotency_window_expired');
      } else {
        journal = { hash, state: 'intent', source, purpose, startedAt: this.now() };
        this.store.data.requests[key] = journal; this.store.save();
      }
    }
    const value = await this.#send(method, path, fields, key);
    assertTestObject(value);
    if (route.resourceId) check(value.id === route.resourceId, 'provider_object_binding_mismatch');
    if (mutation) {
      check(id(value.id), 'provider_object_id_invalid');
      if (!route.resourceId) {
        this.store.resource(route.kind, value.id, { scenario: scenario || null, userId: userId || null, purpose: purpose || 'source_module' });
      }
      journal.state = 'complete'; journal.resultId = value.id;
      journal.resultPath = route.resourceId ? `${route.collection}/${route.resourceId}` : `${route.collection}/${value.id}`;
      journal.completedAt = this.now(); this.store.save();
    }
    return value;
  }
  fixture(path, fields, purpose, details = {}) {
    return this.request('POST', path, fields, { key: `${this.store.data.runId}-${purpose}`, purpose, ...details });
  }
  stripe() {
    return (path, fields = null, key = null) => this.request(fields ? 'POST' : 'GET', path, fields,
      { key: key || undefined, purpose: 'production_module', source: true });
  }
}

export async function pollClock(client, clockId, target, { attempts = 60, interval = 1000, pause = sleep } = {}) {
  for (let attempt = 0; attempt < attempts; attempt++) {
    const clock = await client.request('GET', `test_helpers/test_clocks/${clockId}`);
    check(['advancing', 'ready'].includes(clock.status), 'clock_status_unexpected');
    if (clock.status === 'ready') {
      check(Number.isSafeInteger(clock.frozen_time) && (target === undefined || clock.frozen_time === target), 'clock_time_unverified'); return clock;
    }
    if (attempt + 1 < attempts) await pause(interval);
  }
  throw new RunnerError('clock_not_ready');
}

async function advanceClock(client, scenario, target, purpose) {
  const { clockId } = scenario;
  return client.store.step(purpose, async () => {
    const current = await pollClock(client, clockId);
    check(Number.isSafeInteger(target) && target >= current.frozen_time, 'clock_cannot_reverse');
    if (target !== current.frozen_time) await client.fixture(`test_helpers/test_clocks/${clockId}/advance`, { frozen_time: String(target) }, purpose);
    const ready = await pollClock(client, clockId, target);
    return { frozenTime: ready.frozen_time, clockId };
  });
}

export function openPrivateDatabase(store) {
  const databasePath = join(store.directory, 'state.sqlite3');
  if (existsSync(databasePath)) privateFile(databasePath);
  else {
    const fd = openSync(databasePath, constants.O_CREAT | constants.O_EXCL | constants.O_WRONLY | constants.O_NOFOLLOW, PRIVATE_MODE); closeSync(fd);
  }
  const sqlite = new DatabaseSync(databasePath);
  sqlite.exec('PRAGMA journal_mode=DELETE; PRAGMA foreign_keys=ON; CREATE TABLE IF NOT EXISTS verification_migrations(name TEXT PRIMARY KEY,sha256 TEXT NOT NULL)');
  for (const name of readdirSync(MIGRATIONS).filter(name => /^\d{4}_.*\.sql$/.test(name)).sort()) {
    const sql = readFileSync(join(MIGRATIONS, name), 'utf8'); const hash = digest(sql);
    const prior = sqlite.prepare('SELECT sha256 FROM verification_migrations WHERE name=?').get(name);
    if (prior) check(prior.sha256 === hash, 'database_migration_changed');
    else {
      sqlite.exec('BEGIN');
      try { sqlite.exec(sql); sqlite.prepare('INSERT INTO verification_migrations(name,sha256) VALUES(?,?)').run(name, hash); sqlite.exec('COMMIT'); }
      catch (error) { sqlite.exec('ROLLBACK'); sqlite.close(); throw error; }
    }
  }
  return { ...createD1(sqlite), APP_ORIGIN: 'https://oraclebot-verification.example.invalid' };
}

const RUN_METADATA = store => ({ 'metadata[oraclebot_lifecycle_run]': store.data.runId });
async function catalog(client) {
  const prices = {};
  for (const [plan, cents] of Object.entries({ starter: 999, advanced: 2999, unlimited: 4999 })) {
    const productId = await client.store.step(`catalog-${plan}-product`, async () => {
      const product = await client.fixture('products', { name: `Oraclebot lifecycle verification ${plan}`, ...RUN_METADATA(client.store) }, `catalog-${plan}-product`);
      return product.id;
    });
    prices[plan] = await client.store.step(`catalog-${plan}-price`, async () => {
      const price = await client.fixture('prices', { product: productId, currency: 'usd', unit_amount: String(cents),
        'recurring[interval]': 'month', ...RUN_METADATA(client.store) }, `catalog-${plan}-price`);
      return price.id;
    });
  }
  return prices;
}

async function fixtureScenario(client, env, prices, name) {
  const userId = `${client.store.data.runId}_${name}`;
  const clockId = await client.store.step(`${name}-clock`, async () => {
    const clock = await client.fixture('test_helpers/test_clocks', { frozen_time: String(client.store.data.createdAt),
      name: `${client.store.data.runId}:${name}` }, `${name}-clock`, { scenario: name });
    check(clock.status === 'ready', 'new_clock_not_ready'); return clock.id;
  });
  const visaId = await client.store.step(`${name}-visa`, async () => {
    const value = await client.fixture('payment_methods', { type: 'card', 'card[token]': 'tok_visa', ...RUN_METADATA(client.store) }, `${name}-visa`, { scenario: name });
    return value.id;
  });
  const customerId = await client.store.step(`${name}-customer`, async () => {
    const customer = await client.fixture('customers', { email: `${client.store.data.runId}.${name}@example.invalid`, test_clock: clockId,
      payment_method: visaId, 'invoice_settings[default_payment_method]': visaId,
      'metadata[oraclebot_user]': userId, ...RUN_METADATA(client.store) }, `${name}-customer`, { scenario: name, userId });
    check(ref(customer.test_clock) === clockId, 'customer_clock_unverified'); return customer.id;
  });
  const subscriptionId = await client.store.step(`${name}-subscription`, async () => {
    const value = await client.fixture('subscriptions', { customer: customerId, 'items[0][price]': prices.starter, 'items[0][quantity]': '1',
      trial_period_days: '7', default_payment_method: visaId, payment_behavior: 'default_incomplete',
      'metadata[oraclebot_user]': userId, ...RUN_METADATA(client.store) }, `${name}-subscription`, { scenario: name, userId });
    check(value.status === 'trialing' && value.trial_end === value.trial_start + 7 * DAY, 'seven_day_trial_unverified');
    return value.id;
  });
  env.sqlite.prepare('INSERT INTO users(id,wallet,created_at,stripe_customer_id) VALUES(?,?,?,?) ON CONFLICT(id) DO NOTHING')
    .run(userId, `verification_${userId}`, client.store.data.createdAt, customerId);
  // Identity only. No invented webhook or successful subscription is projected.
  env.sqlite.prepare("INSERT INTO subscriptions(user_id,stripe_subscription_id,status,updated_at) VALUES(?,?,'verification_only',?) ON CONFLICT(user_id) DO NOTHING")
    .run(userId, subscriptionId, client.store.data.createdAt);
  const local = env.sqlite.prepare('SELECT * FROM subscriptions WHERE user_id=?').get(userId);
  check(local.stripe_subscription_id === subscriptionId && local.status === 'verification_only' && local.plan_id === null && local.period_end === 0 && local.trial_end === 0, 'local_entitlement_must_remain_unverified');
  const clock = await pollClock(client, clockId);
  return { name, user: { id: userId }, clockId, visaId, customerId, subscriptionId, time: clock.frozen_time,
    services: { stripe: client.stripe(), now: () => scenarioTime(client, clockId) } };
}

function scenarioTime(client, clockId) {
  const value = client.store.data.resources[clockId]?.frozenTime;
  check(Number.isSafeInteger(value), 'canonical_clock_required'); return value;
}
async function synchronizeClock(client, scenario) {
  const clock = await pollClock(client, scenario.clockId);
  client.store.resource('test_clock', scenario.clockId, { frozenTime: clock.frozen_time }); scenario.time = clock.frozen_time;
}
async function subscription(client, scenario) {
  const value = await client.request('GET', `subscriptions/${scenario.subscriptionId}`);
  check(ref(value.customer) === scenario.customerId && value.metadata?.oraclebot_user === scenario.user.id && value.metadata?.oraclebot_lifecycle_run === client.store.data.runId,
    'canonical_subscription_ownership');
  check(value.items?.data?.length === 1 && value.items.has_more === false, 'subscription_item_unverified'); return value;
}
const priceOf = sub => ref(sub.items.data[0].price);
const periodEnd = sub => sub.items.data[0].current_period_end ?? sub.current_period_end;
const periodStart = sub => sub.items.data[0].current_period_start ?? sub.current_period_start;
async function invoice(client, scenario, sub) {
  const invoiceId = ref(sub.latest_invoice); check(id(invoiceId), 'subscription_invoice_missing');
  client.store.resource('invoice', invoiceId, { scenario: scenario.name, userId: scenario.user.id });
  const value = await client.request('GET', `invoices/${invoiceId}`);
  const invoiceSubscription = ref(value.parent?.subscription_details?.subscription) || ref(value.subscription);
  check(ref(value.customer) === scenario.customerId && invoiceSubscription === scenario.subscriptionId && value.currency === 'usd', 'canonical_invoice_binding');
  return value;
}
function invoiceEvidence(value) {
  return { invoiceId: value.id, invoiceStatus: value.status, amountDueCents: value.amount_due, amountPaidCents: value.amount_paid };
}
async function paid(client, scenario, cents, name) {
  let sub; let bill;
  for (let attempt = 0; attempt < 12; attempt++) {
    sub = await subscription(client, scenario); bill = await invoice(client, scenario, sub);
    if (bill.status === 'paid' && sub.status === 'active') break;
    if (attempt < 11) await sleep(1000);
  }
  client.store.verify(name, sub.status === 'active' && bill.status === 'paid' && bill.amount_due === cents && bill.amount_paid === cents,
    { subscriptionId: sub.id, ...invoiceEvidence(bill) }); return sub;
}

async function sourceOperation(client, env, scenario, label, perform) {
  return client.store.step(label, async () => {
    await synchronizeClock(client, scenario);
    const key = `${client.store.data.runId}-${label}`;
    const prior = env.sqlite.prepare('SELECT id FROM billing_lifecycle_operations WHERE user_id=? AND idempotency_key=?').get(scenario.user.id, key);
    // Production mutation recovery is read-only. Never replay an ambiguous write.
    const result = prior ? await getPlanChange(env, scenario.user, prior.id, scenario.services) : await perform(key);
    check(!['unknown', 'committing', 'failed'].includes(result.status), 'source_operation_requires_reconciliation');
    return result;
  });
}
async function changePlan(client, env, scenario, plan, label) {
  const quote = await client.store.step(`${label}-quote`, async () => {
    await synchronizeClock(client, scenario);
    return preparePlanChange(env, scenario.user, { plan }, scenario.services);
  });
  const result = await sourceOperation(client, env, scenario, label, key =>
    commitPlanChange(env, scenario.user, { quoteId: quote.quoteId, idempotencyKey: key }, scenario.services));
  return { quote, result };
}
async function cancelFlag(client, env, scenario, value, label) {
  const result = await sourceOperation(client, env, scenario, label, key => setPeriodEndCancellation(env, scenario.user,
    { cancelAtPeriodEnd: value, idempotencyKey: key }, scenario.services));
  check(result.status === 'applied', 'cancellation_not_applied'); return result;
}

async function successfulLifecycle(client, env, prices) {
  const scenario = await fixtureScenario(client, env, prices, 'success');
  await client.store.step('trial-and-upgrade-proof', async () => {
    const before = await subscription(client, scenario); const first = await invoice(client, scenario, before);
    client.store.verify('trial_original_seven_days', before.status === 'trialing' && before.trial_end - before.trial_start === 7 * DAY && first.amount_paid === 0,
      { subscriptionId: before.id, trialEnd: before.trial_end, ...invoiceEvidence(first) });
    const { quote, result } = await changePlan(client, env, scenario, 'advanced', 'trial-upgrade');
    const after = await subscription(client, scenario);
    client.store.verify('trial_upgrade_retains_original_end', quote.amountDueNowCents === 0 && result.status === 'applied' && after.trial_end === before.trial_end &&
      after.status === 'trialing' && priceOf(after) === prices.advanced, { changeId: result.changeId, trialEnd: after.trial_end, subscriptionId: after.id });
    return { trialEnd: after.trial_end };
  });
  const trialEnd = client.store.data.steps['trial-and-upgrade-proof'].value.trialEnd;
  await advanceClock(client, scenario, trialEnd + 3601, 'success-trial-end');
  await client.store.step('first-paid-invoice', async () => {
    const sub = await paid(client, scenario, 2999, 'trial_conversion_actual_payment');
    return { start: periodStart(sub), end: periodEnd(sub), originalTrialEnd: sub.trial_end };
  });
  const firstPeriod = client.store.data.steps['first-paid-invoice'].value;
  await advanceClock(client, scenario, Math.floor((firstPeriod.start + firstPeriod.end) / 2), 'success-mid-period');
  await client.store.step('paid-proration-proof', async () => {
    const { quote, result } = await changePlan(client, env, scenario, 'unlimited', 'paid-upgrade');
    check(quote.amountDueNowCents > 0 && result.status === 'applied', 'upgrade_proration_missing');
    const sub = await paid(client, scenario, quote.amountDueNowCents, 'preview_matches_actual_proration');
    client.store.verify('paid_upgrade_preserves_trial_and_period', sub.trial_end === firstPeriod.originalTrialEnd && periodEnd(sub) === firstPeriod.end &&
      priceOf(sub) === prices.unlimited, { subscriptionId: sub.id, changeId: result.changeId, periodEnd: periodEnd(sub) }); return { changeId: result.changeId };
  });
  await client.store.step('downgrade-release-proof', async () => {
    const { result } = await changePlan(client, env, scenario, 'starter', 'first-downgrade');
    const before = await subscription(client, scenario);
    const released = await sourceOperation(client, env, scenario, 'release-downgrade', key => cancelPlanChange(env, scenario.user,
      { changeId: result.changeId, idempotencyKey: key }, scenario.services));
    const after = await subscription(client, scenario);
    client.store.verify('downgrade_undo_releases_keeps_subscription', result.status === 'scheduled' && released.status === 'applied' &&
      before.status === 'active' && after.status === 'active' && !ref(after.schedule) && priceOf(after) === prices.unlimited,
    { subscriptionId: after.id, releasedChangeId: released.changeId }); return { releasedChangeId: released.changeId };
  });
  await client.store.step('scheduled-downgrade-proof', async () => {
    const { quote, result } = await changePlan(client, env, scenario, 'starter', 'second-downgrade');
    const sub = await subscription(client, scenario); const scheduleId = ref(sub.schedule);
    client.store.owned(scheduleId, 'subscription_schedule');
    const schedule = await client.request('GET', `subscription_schedules/${scheduleId}`);
    client.store.verify('downgrade_preserves_current_plan_until_boundary', result.status === 'scheduled' && priceOf(sub) === prices.unlimited &&
      quote.effectiveAt === periodEnd(sub) && schedule.end_behavior === 'release' && schedule.phases.length === 2 &&
      ref(schedule.phases[0].items[0].price) === prices.unlimited && schedule.phases[0].end_date === quote.effectiveAt &&
      ref(schedule.phases[1].items[0].price) === prices.starter && schedule.phases[1].start_date === quote.effectiveAt,
    { subscriptionId: sub.id, scheduleId, effectiveAt: quote.effectiveAt }); return { at: quote.effectiveAt, changeId: result.changeId };
  });
  const downgrade = client.store.data.steps['scheduled-downgrade-proof'].value;
  await advanceClock(client, scenario, downgrade.at + 3601, 'success-downgrade-boundary');
  await client.store.step('downgrade-boundary-proof', async () => {
    await synchronizeClock(client, scenario);
    const sub = await paid(client, scenario, 999, 'downgrade_boundary_actual_payment');
    const operation = await getPlanChange(env, scenario.user, downgrade.changeId, scenario.services);
    client.store.verify('source_reconciles_executed_downgrade', priceOf(sub) === prices.starter && operation.status === 'applied',
      { changeId: operation.changeId, subscriptionId: sub.id }); return { next: periodEnd(sub), invoiceId: ref(sub.latest_invoice) };
  });
  const boundary = client.store.data.steps['downgrade-boundary-proof'].value;
  await advanceClock(client, scenario, boundary.next + 3601, 'success-next-renewal');
  await client.store.step('renewal-and-cancel-undo-proof', async () => {
    const sub = await paid(client, scenario, 999, 'recurring_renewal_actual_payment');
    check(ref(sub.latest_invoice) !== boundary.invoiceId, 'renewal_must_have_new_invoice');
    await cancelFlag(client, env, scenario, true, 'cancel-first');
    const scheduled = await subscription(client, scenario);
    check((scheduled.cancel_at_period_end === true || scheduled.cancel_at === periodEnd(scheduled)) &&
      (scheduled.cancel_at == null || scheduled.cancel_at === periodEnd(scheduled)), 'cancellation_schedule_missing');
    await cancelFlag(client, env, scenario, false, 'undo-cancel');
    const undone = await subscription(client, scenario);
    client.store.verify('cancel_undo_before_boundary', undone.status === 'active' && undone.cancel_at_period_end === false && undone.cancel_at === null,
      { subscriptionId: undone.id });
    await client.fixture(`subscriptions/${scenario.subscriptionId}`, { cancel_at: String(periodEnd(undone)), proration_behavior: 'none' }, 'set-explicit-date-cancel');
    const dated = await subscription(client, scenario);
    check(dated.cancel_at === periodEnd(undone) && dated.cancel_at_period_end === false, 'explicit_cancellation_fixture_unverified');
    await cancelFlag(client, env, scenario, false, 'undo-explicit-date-cancel');
    const reactivated = await subscription(client, scenario);
    client.store.verify('explicit_cancellation_date_undo_clears_both_fields', reactivated.status === 'active' &&
      reactivated.cancel_at === null && reactivated.cancel_at_period_end === false && reactivated.trial_end === undone.trial_end,
    { subscriptionId: reactivated.id });
    await cancelFlag(client, env, scenario, true, 'cancel-final');
    return { end: periodEnd(undone), lastInvoiceId: ref(undone.latest_invoice) };
  });
  const cancellation = client.store.data.steps['renewal-and-cancel-undo-proof'].value;
  await advanceClock(client, scenario, cancellation.end + 3601, 'success-cancel-boundary');
  await client.store.step('terminal-no-resurrection-proof', async () => {
    await synchronizeClock(client, scenario);
    const sub = await subscription(client, scenario); const before = Object.keys(client.store.data.requests).length;
    let code;
    try { await setPeriodEndCancellation(env, scenario.user, { cancelAtPeriodEnd: false,
      idempotencyKey: `${client.store.data.runId}-undo-terminal` }, scenario.services); } catch (error) { code = safeCode(error); }
    const finalInvoice = ref(sub.latest_invoice) !== cancellation.lastInvoiceId ? await invoice(client, scenario, sub) : null;
    client.store.verify('terminal_subscription_cannot_resurrect', sub.status === 'canceled' && code === 'subscription_terminal' &&
      Object.keys(client.store.data.requests).length === before && (!finalInvoice || (finalInvoice.amount_due === 0 && finalInvoice.amount_paid === 0)),
    { subscriptionId: sub.id, status: sub.status, lastInvoiceId: ref(sub.latest_invoice) }); return { status: sub.status };
  });
}

async function failureLifecycle(client, env, prices) {
  const scenario = await fixtureScenario(client, env, prices, 'failure');
  await client.store.step('failure-trial-proof', async () => {
    const sub = await subscription(client, scenario); check(sub.status === 'trialing', 'failure_trial_missing'); return { end: sub.trial_end };
  });
  await advanceClock(client, scenario, client.store.data.steps['failure-trial-proof'].value.end + 3601, 'failure-trial-end');
  await client.store.step('failure-first-payment', async () => {
    const sub = await paid(client, scenario, 999, 'failure_fixture_initial_payment'); return { start: periodStart(sub), end: periodEnd(sub) };
  });
  const first = client.store.data.steps['failure-first-payment'].value;
  await advanceClock(client, scenario, Math.floor((first.start + first.end) / 2), 'failure-mid-period');
  const declineId = await client.store.step('failure-decline-method', async () => {
    const pm = await client.fixture('payment_methods', { type: 'card', 'card[token]': 'tok_chargeCustomerFail', ...RUN_METADATA(client.store) }, 'failure-decline-method', { scenario: 'failure' });
    // This official token attaches successfully and declines later charges.
    await client.fixture(`payment_methods/${pm.id}/attach`, { customer: scenario.customerId }, 'failure-decline-attach'); return pm.id;
  });
  await client.store.step('pending-payment-protection-proof', async () => {
    await client.fixture(`subscriptions/${scenario.subscriptionId}`, { default_payment_method: declineId }, 'failure-set-decline');
    const { quote, result } = await changePlan(client, env, scenario, 'advanced', 'declined-upgrade');
    const sub = await subscription(client, scenario); const bill = await invoice(client, scenario, sub);
    client.store.verify('declined_upgrade_keeps_old_plan', result.status === 'pending_payment' && quote.amountDueNowCents > 0 &&
      priceOf(sub) === prices.starter && !!sub.pending_update && bill.status === 'open' && bill.amount_paid === 0 && bill.amount_due === quote.amountDueNowCents,
    { changeId: result.changeId, subscriptionId: sub.id, ...invoiceEvidence(bill) });
    return { changeId: result.changeId, invoiceId: bill.id, amount: quote.amountDueNowCents };
  });
  const pending = client.store.data.steps['pending-payment-protection-proof'].value;
  await client.store.step('pending-payment-recovery-proof', async () => {
    await client.fixture(`subscriptions/${scenario.subscriptionId}`, { default_payment_method: scenario.visaId }, 'failure-set-visa');
    await client.fixture(`invoices/${pending.invoiceId}/pay`, { payment_method: scenario.visaId }, 'failure-pay-pending');
    await synchronizeClock(client, scenario);
    const sub = await paid(client, scenario, pending.amount, 'pending_payment_actual_recovery');
    const result = await getPlanChange(env, scenario.user, pending.changeId, scenario.services);
    client.store.verify('source_applies_upgrade_only_after_payment', result.status === 'applied' && priceOf(sub) === prices.advanced && !sub.pending_update,
      { changeId: result.changeId, subscriptionId: sub.id }); return { end: periodEnd(sub) };
  });
  await client.store.step('renewal-failure-method', async () => {
    await client.fixture(`subscriptions/${scenario.subscriptionId}`, { default_payment_method: declineId }, 'renewal-set-decline'); return true;
  });
  await advanceClock(client, scenario, client.store.data.steps['pending-payment-recovery-proof'].value.end + 3601, 'failed-renewal-boundary');
  await client.store.step('renewal-failure-protection-proof', async () => {
    const sub = await subscription(client, scenario); const bill = await invoice(client, scenario, sub);
    await synchronizeClock(client, scenario); let code;
    try { await preparePlanChange(env, scenario.user, { plan: 'unlimited' }, scenario.services); } catch (error) { code = safeCode(error); }
    client.store.verify('failed_renewal_blocks_plan_change', ['past_due', 'unpaid'].includes(sub.status) && bill.status === 'open' &&
      bill.amount_due === 2999 && bill.amount_paid === 0 && code === 'subscription_not_changeable',
    { subscriptionId: sub.id, status: sub.status, ...invoiceEvidence(bill) }); return { invoiceId: bill.id };
  });
  await client.store.step('renewal-payment-recovery-proof', async () => {
    const billId = client.store.data.steps['renewal-failure-protection-proof'].value.invoiceId;
    await client.fixture(`subscriptions/${scenario.subscriptionId}`, { default_payment_method: scenario.visaId }, 'renewal-set-visa');
    await client.fixture(`invoices/${billId}/pay`, { payment_method: scenario.visaId }, 'renewal-pay-recovery');
    const sub = await paid(client, scenario, 2999, 'failed_renewal_actual_recovery'); return { status: sub.status, invoiceId: ref(sub.latest_invoice) };
  });
}

export async function runVerification(client, env) {
  check(client.verified, 'merchant_not_verified');
  const prices = await catalog(client);
  Object.assign(env, { STRIPE_STARTER_PRICE_ID: prices.starter, STRIPE_ADVANCED_PRICE_ID: prices.advanced, STRIPE_UNLIMITED_PRICE_ID: prices.unlimited });
  client.store.data.status = 'running'; client.store.save();
  await successfulLifecycle(client, env, prices);
  await failureLifecycle(client, env, prices);
  const inventedEvents = env.sqlite.prepare('SELECT count(*) AS n FROM stripe_events').get().n;
  const granted = env.sqlite.prepare("SELECT count(*) AS n FROM subscriptions WHERE status!='verification_only' OR plan_id IS NOT NULL OR period_end!=0 OR trial_end!=0").get().n;
  client.store.verify('no_synthetic_webhook_or_entitlement_claim', inventedEvents === 0 && granted === 0,
    { note: 'Private identity fixtures only; no webhook delivered and no entitlement granted.' });
  client.store.data.gates.sourceModuleProviderLifecycle = 'PASSED'; client.store.data.status = 'provider_lifecycle_passed'; client.store.save();
  return report(client.store);
}

async function allClockCustomers(client, clockId) {
  const customers = []; let cursor;
  for (let page = 0; page < 20; page++) {
    const query = new URLSearchParams({ test_clock: clockId, limit: '100', ...(cursor ? { starting_after: cursor } : {}) });
    const value = await client.request('GET', `customers?${query}`); customers.push(...value.data);
    if (!value.has_more) return customers;
    check(value.data.length > 0 && id(value.data.at(-1).id) && value.data.at(-1).id !== cursor, 'customer_pagination_invalid');
    cursor = value.data.at(-1).id;
  }
  throw new RunnerError('customer_pagination_bound_exceeded');
}

export async function cleanupOwned(client) {
  check(client.verified, 'merchant_not_verified');
  const runId = client.store.data.runId;
  const resources = Object.entries(client.store.data.resources);
  for (const [resourceId, value] of resources) {
    if (value.kind === 'test_clock' && client.store.data.requests[`${runId}-cleanup-${resourceId}`]?.state === 'complete') {
      await client.store.step(`cleanup-${resourceId}`, async () => ({ deleted: true }));
    }
  }
  const clocks = resources.filter(([resourceId, value]) => value.kind === 'test_clock' && client.store.data.steps[`cleanup-${resourceId}`]?.status !== 'complete');
  // Preflight the complete deletion set before any destructive provider call.
  for (const [clockId, details] of clocks) {
    const clock = await pollClock(client, clockId);
    check(clock.name === `${runId}:${details.scenario}`, 'cleanup_clock_ownership');
    const customers = await allClockCustomers(client, clockId);
    for (const customer of customers) {
      client.store.owned(customer.id, 'customer');
      check(customer.metadata?.oraclebot_lifecycle_run === runId && ref(customer.test_clock) === clockId, 'cleanup_customer_ownership');
    }
    const expected = resources.filter(([, value]) => value.kind === 'customer' && value.scenario === details.scenario).map(([resourceId]) => resourceId);
    check(expected.every(customerId => customers.some(customer => customer.id === customerId)), 'cleanup_clock_customer_census');
  }
  for (const [resourceId, details] of resources.filter(([, value]) => ['price', 'product', 'payment_method'].includes(value.kind))) {
    if (client.store.data.steps[`cleanup-${resourceId}`]?.status === 'complete') continue;
    const collection = Object.keys(TYPES).find(key => TYPES[key] === details.kind);
    const value = await client.request('GET', `${collection}/${resourceId}`);
    check(value.metadata?.oraclebot_lifecycle_run === runId, 'cleanup_catalog_ownership');
    if (details.kind === 'payment_method' && value.customer) client.store.owned(ref(value.customer), 'customer');
  }
  for (const [clockId] of clocks) await client.store.step(`cleanup-${clockId}`, async () => {
    const value = await client.request('DELETE', `test_helpers/test_clocks/${clockId}`, null,
      { key: `${runId}-cleanup-${clockId}`, purpose: `cleanup-${clockId}` });
    check(value.deleted === true, 'clock_deletion_unverified'); return { deleted: true };
  });
  // Stripe does not delete Prices. Archive the run's catalog and detach any
  // surviving owned test PM; detached PMs remain identified in the manifest.
  for (const kind of ['price', 'product', 'payment_method']) {
    for (const [resourceId, details] of resources.filter(([, value]) => value.kind === kind)) {
      await client.store.step(`cleanup-${resourceId}`, async () => {
        const collection = Object.keys(TYPES).find(key => TYPES[key] === details.kind);
        const current = await client.request('GET', `${collection}/${resourceId}`);
        check(current.metadata?.oraclebot_lifecycle_run === runId, 'cleanup_catalog_ownership');
        if (kind === 'payment_method') {
          if (current.customer) {
            client.store.owned(ref(current.customer), 'customer');
            const detached = await client.fixture(`${collection}/${resourceId}/detach`, {}, `cleanup-${resourceId}`);
            check(!detached.customer, 'payment_method_detach_unverified');
          }
          return { detached: true, retainedByProvider: true };
        }
        if (current.active) {
          const archived = await client.fixture(`${collection}/${resourceId}`, { active: 'false' }, `cleanup-${resourceId}`);
          check(archived.active === false, 'catalog_archive_unverified');
        }
        return { archived: true };
      });
    }
  }
  client.store.data.cleanup = 'completed'; client.store.save(); return report(client.store);
}

function report(store) {
  return { runId: store.data.runId, status: store.data.status, apiVersion: API_VERSION,
    checksPassed: store.data.checks.length, gates: store.data.gates, cleanup: store.data.cleanup || 'NOT_RUN', manifest: store.manifestPath };
}

export const PLAN = Object.freeze({ mode: 'PLAN_ONLY', apiVersion: API_VERSION,
  execution: '--execute --run-dir /absolute/private/run-directory --env-file /Users/mitch/.env',
  resume: '--execute --resume --run-dir /same/private/run-directory --env-file /Users/mitch/.env',
  cleanup: '--execute --cleanup --run-dir /same/private/run-directory --env-file /Users/mitch/.env',
  requiredSecret: 'STRIPE_ORACLEBOT_TEST_SEC_KEY (sk_test_ or rk_test_ only)',
  expectedMerchant: 'STRIPE_ORACLEBOT_TEST_ACCTNUM, otherwise STRIPE_ORACLEBOT_ACCTNUM',
  checks: ['Actual production billing module and real SQLite migrations', 'Seven-day trial and original-end retention',
    'Preview versus charged proration', 'Pending payment keeps the original plan; actual payment recovery',
    'Downgrade boundary, schedule release and unchanged current plan', 'Actual renewal charge and failed-renewal recovery',
    'Cancel, undo before boundary and terminal no-resurrection'],
  separateUnverifiedGates: ['Production authenticated Checkout browser path', 'Genuine Stripe-to-Worker webhook delivery',
    'Production entitlement projection from genuine provider events'],
  providerCallsMade: 0 });

export async function main(argv = process.argv.slice(2), { env = process.env, fetchImpl = fetch, output = value => process.stdout.write(`${JSON.stringify(value, null, 2)}\n`) } = {}) {
  let execute = false; let resume = false; let cleanup = false; let directory; let envFile;
  for (let index = 0; index < argv.length; index++) {
    const arg = argv[index];
    if (arg === '--execute') execute = true;
    else if (arg === '--plan') { /* default */ }
    else if (arg === '--resume') resume = true;
    else if (arg === '--cleanup') { cleanup = true; resume = true; }
    else if (arg === '--run-dir') directory = argv[++index];
    else if (arg === '--env-file') envFile = argv[++index];
    else throw new RunnerError('unknown_argument');
  }
  if (!execute) { output(PLAN); return PLAN; }
  const config = readConfiguration(env, envFile);
  const store = new RunStore(directory, { account: config.account, resume }); let database;
  try {
    const client = new StripeTestClient(config, store, { fetchImpl });
    await client.verifyMerchant();
    if (!cleanup) database = openPrivateDatabase(store);
    const result = cleanup ? await cleanupOwned(client) : await runVerification(client, database);
    output(result); return result;
  } catch (error) {
    store.data.status = 'blocked'; store.data.lastError = safeCode(error); store.save();
    throw new RunnerError(safeCode(error), error instanceof RunnerError ? error.status : null);
  } finally { database?.sqlite.close(); store.close(); }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch(error => { process.stderr.write(`${JSON.stringify({ error: safeCode(error), providerLifecycleVerified: false })}\n`); process.exitCode = 1; });
}
