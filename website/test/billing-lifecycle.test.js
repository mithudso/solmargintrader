import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { environment } from './helpers/d1.js';
import {
  BillingLifecycleError, preparePlanChange, commitPlanChange, getPlanChange,
  cancelPlanChange, setPeriodEndCancellation, listPlanChanges,
} from '../src/billing-lifecycle.js';

const AMOUNTS = { starter: 999, advanced: 2999, unlimited: 4999 };
const copy = value => structuredClone(value);
const price = plan => ({ id: `price_${plan}`, active: true, currency: 'usd', unit_amount: AMOUNTS[plan], type: 'recurring', recurring: { interval: 'month', interval_count: 1, usage_type: 'licensed' } });

async function fixture(t, { plan = 'starter', trial = false } = {}) {
  const storage = environment();
  const user = { id: crypto.randomUUID(), stripe_customer_id: 'cus_owner' };
  const clock = { at: 2_000_000_000 };
  storage.sqlite.prepare('INSERT INTO users (id,wallet,created_at,stripe_customer_id) VALUES (?,?,?,?)').run(user.id, 'fixture-wallet', clock.at, user.stripe_customer_id);
  storage.sqlite.prepare('INSERT INTO subscriptions (user_id,stripe_subscription_id,status,period_end,trial_end,updated_at,plan_id) VALUES (?,?,?,?,?,?,?)').run(user.id, 'sub_owner', trial ? 'trialing' : 'active', clock.at + 100_000, trial ? clock.at + 100_000 : 0, clock.at, plan);
  const state = {
    sub: { id: 'sub_owner', customer: 'cus_owner', metadata: { oraclebot_user: user.id }, status: trial ? 'trialing' : 'active',
      cancel_at_period_end: false, pending_update: null, schedule: null, collection_method: 'charge_automatically',
      trial_end: trial ? clock.at + 100_000 : null,
      items: { has_more: false, data: [{ id: 'si_owner', quantity: 1, price: price(plan), current_period_start: clock.at - 100_000, current_period_end: clock.at + 100_000 }] } },
    schedule: null, amountDue: 1234, pending: false, requests: [], before: null, after: null,
  };
  function apply(path, method, form) {
    if (path === '/v1/subscriptions/sub_owner' && method === 'GET') return copy(state.sub);
    if (/^\/v1\/prices\/price_(starter|advanced|unlimited)$/.test(path) && method === 'GET') return price(path.split('price_')[1]);
    if (path === '/v1/invoices/create_preview' && method === 'POST') {
      assert.equal(form['subscription_details[billing_cycle_anchor][type]'], 'unchanged');
      assert.equal(Object.hasOwn(form, 'subscription_details[billing_cycle_anchor]'), false);
      return { id: 'upcoming_fixture', customer: 'cus_owner', currency: 'usd', amount_due: state.amountDue };
    }
    if (path === '/v1/subscriptions/sub_owner' && method === 'POST') {
      const staged = {};
      for (const [key, value] of Object.entries(form)) {
        const metadata = /^metadata\[([^\]]+)\]$/.exec(key);
        if (metadata) staged[metadata[1]] = value;
      }
      if (form['items[0][price]']) {
        assert.equal(form['billing_cycle_anchor[type]'], 'unchanged');
        assert.equal(Object.hasOwn(form, 'billing_cycle_anchor'), false);
        if (state.pending) state.sub.pending_update = { expires_at: clock.at + 600, metadata: staged, subscription_items: [{ id: 'si_owner', price: form['items[0][price]'], quantity: 1 }] };
        else state.sub.items.data[0].price = price(form['items[0][price]'].split('price_')[1]);
      }
      if (!(form['items[0][price]'] && state.pending)) Object.assign(state.sub.metadata, staged);
      if (form.cancel_at_period_end !== undefined) state.sub.cancel_at_period_end = form.cancel_at_period_end === 'true';
      if (form.trial_end !== undefined) state.sub.trial_end = Number(form.trial_end);
      return copy(state.sub);
    }
    if (path === '/v1/subscription_schedules' && method === 'POST') {
      assert.deepEqual(Object.keys(form), ['from_subscription']);
      assert.equal(form.from_subscription, 'sub_owner');
      const item = state.sub.items.data[0];
      state.sub.schedule = 'sub_sched_fixture';
      state.schedule = { id: 'sub_sched_fixture', customer: 'cus_owner', subscription: 'sub_owner', status: 'active', metadata: {}, end_behavior: 'release',
        current_phase: { start_date: item.current_period_start, end_date: item.current_period_end },
        phases: [{ start_date: item.current_period_start, end_date: item.current_period_end,
          items: [{ price: copy(item.price), quantity: 1 }], trial_end: state.sub.status === 'trialing' ? state.sub.trial_end : null }] };
      return copy(state.schedule);
    }
    if (path === '/v1/subscription_schedules/sub_sched_fixture' && method === 'GET') return copy(state.schedule);
    if (path === '/v1/subscription_schedules/sub_sched_fixture' && method === 'POST') {
      state.schedule.metadata = { oraclebot_user: form['metadata[oraclebot_user]'], oraclebot_change_id: form['metadata[oraclebot_change_id]'] };
      state.schedule.phases = [0, 1].map(index => ({ start_date: Number(form[`phases[${index}][start_date]`]),
        end_date: index === 0 ? Number(form['phases[0][end_date]']) : Number(form['phases[1][start_date]']) + 31 * 86400,
        items: [{ price: form[`phases[${index}][items][0][price]`], quantity: Number(form[`phases[${index}][items][0][quantity]`]) }],
        trial_end: form[`phases[${index}][trial_end]`] === undefined ? null : Number(form[`phases[${index}][trial_end]`]) }));
      state.schedule.end_behavior = form.end_behavior;
      return copy(state.schedule);
    }
    if (path === '/v1/subscription_schedules/sub_sched_fixture/release' && method === 'POST') {
      state.schedule.status = 'released'; state.schedule.released_subscription = 'sub_owner'; state.schedule.subscription = null;
      state.sub.schedule = null;
      return copy(state.schedule);
    }
    return undefined;
  }
  const server = http.createServer(async (request, response) => {
    let raw = ''; for await (const chunk of request) raw += chunk;
    const entry = { method: request.method, path: request.url, form: Object.fromEntries(new URLSearchParams(raw)), key: request.headers['idempotency-key'] || null };
    state.requests.push(entry);
    try {
      const before = await state.before?.(entry);
      if (before === 'fail') { response.writeHead(503, { 'Content-Type': 'application/json' }); response.end('{"error":"fixture_unavailable"}'); return; }
      const value = apply(entry.path, entry.method, entry.form);
      if (value === undefined) { response.writeHead(501); response.end(); return; }
      if (await state.after?.(entry, value) === 'disconnect') { request.socket.destroy(); return; }
      response.writeHead(200, { 'Content-Type': 'application/json' }); response.end(JSON.stringify(value));
    } catch { response.writeHead(500); response.end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(async () => { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); storage.sqlite.close(); });
  const origin = `http://127.0.0.1:${server.address().port}/v1/`;
  const services = { now: () => clock.at, async stripe(path, fields = null, key = null) {
    const response = await fetch(new URL(path, origin), { method: fields === null ? 'GET' : 'POST',
      headers: { Authorization: 'Bearer controlled-http-fixture', ...(fields === null ? {} : { 'Content-Type': 'application/x-www-form-urlencoded' }), ...(key ? { 'Idempotency-Key': key } : {}) },
      body: fields === null ? undefined : new URLSearchParams(fields), redirect: 'error', signal: AbortSignal.timeout(1000) });
    if (!response.ok) throw Error('fixture_provider_unavailable');
    return response.json();
  } };
  const env = { DB: storage.DB, STRIPE_STARTER_PRICE_ID: 'price_starter', STRIPE_ADVANCED_PRICE_ID: 'price_advanced', STRIPE_UNLIMITED_PRICE_ID: 'price_unlimited' };
  return { ...storage, env, user, state, clock, services, mutations: () => state.requests.filter(entry => entry.method === 'POST' && entry.path !== '/v1/invoices/create_preview') };
}
async function rejectsCode(run, code, status) {
  await assert.rejects(run, error => error instanceof BillingLifecycleError && error.code === code && (!status || error.status === status));
}
const commit = (f, quote, key = 'change-request-0001') => commitPlanChange(f.env, f.user, { quoteId: quote.quoteId, idempotencyKey: key }, f.services);

test('active upgrade binds a canonical invoice preview and idempotent transport mutation without granting local entitlement', async t => {
  const f = await fixture(t);
  const quote = await preparePlanChange(f.env, { ...f.user, stripe_customer_id: 'cus_spoof' }, { plan: 'advanced' }, f.services);
  assert.equal(quote.amountDueNowCents, 1234); assert.equal(quote.renewalAmountCents, 2999);
  const result = await commit(f, quote);
  assert.equal(result.status, 'applied'); assert.equal(result.currentPlan, 'advanced'); assert.equal(result.pendingPlan, null);
  assert.equal(f.mutations().length, 1);
  const call = f.mutations()[0];
  assert.equal(call.form.payment_behavior, 'pending_if_incomplete'); assert.equal(call.form.proration_behavior, 'always_invoice');
  assert.equal(call.form.proration_date, String(quote.effectiveAt)); assert.equal(call.form['billing_cycle_anchor[type]'], 'unchanged');
  assert.equal(call.form['items[0][id]'], 'si_owner'); assert.equal(call.form['items[0][quantity]'], '1'); assert.match(call.key, /^oraclebot-billing-/);
  assert.deepEqual(await commit(f, quote), result); assert.equal(f.mutations().length, 1);
  assert.equal(f.sqlite.prepare('SELECT plan_id FROM subscriptions').get().plan_id, 'starter');
  const serialized = JSON.stringify({ quote, result });
  for (const secret of ['cus_owner', 'sub_owner', 'si_owner', 'price_advanced', 'oraclebot_user', 'controlled-http-fixture']) assert.equal(serialized.includes(secret), false);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 0);
});

test('trial upgrade charges zero now, preserves the original trial boundary and publishes future renewal', async t => {
  const f = await fixture(t, { trial: true }); const originalTrial = f.state.sub.trial_end;
  const quote = await preparePlanChange(f.env, f.user, { plan: 'unlimited' }, f.services);
  assert.equal(quote.amountDueNowCents, 0); assert.equal(quote.trialEnd, originalTrial); assert.equal(quote.renewalAmountCents, 4999);
  assert.equal((await commit(f, quote)).status, 'applied');
  const call = f.mutations()[0]; assert.equal(call.form.trial_end, String(originalTrial)); assert.equal(call.form.proration_behavior, 'none');
  assert.equal(f.state.sub.trial_end, originalTrial); assert.equal(f.state.sub.status, 'trialing');
});

test('downgrade retains current item until the exact boundary and undo releases the owned schedule', async t => {
  const f = await fixture(t, { plan: 'unlimited' });
  const quote = await preparePlanChange(f.env, f.user, { plan: 'starter' }, f.services);
  const result = await commit(f, quote);
  assert.equal(result.status, 'scheduled'); assert.equal(result.currentPlan, 'unlimited'); assert.equal(result.pendingPlan, 'starter');
  assert.equal(result.effectiveAt, f.state.sub.items.data[0].current_period_end);
  assert.equal(f.state.sub.items.data[0].price.id, 'price_unlimited');
  const configure = f.mutations().find(entry => entry.path === '/v1/subscription_schedules/sub_sched_fixture');
  assert.equal(configure.form['phases[0][items][0][price]'], 'price_unlimited');
  assert.equal(configure.form['phases[1][items][0][price]'], 'price_starter');
  assert.equal(configure.form['phases[1][start_date]'], String(result.effectiveAt));
  assert.equal(configure.form['phases[1][duration][interval]'], 'month'); assert.equal(configure.form.end_behavior, 'release');
  const undone = await cancelPlanChange(f.env, f.user, { changeId: result.changeId, idempotencyKey: 'undo-request-0001' }, f.services);
  assert.equal(undone.status, 'applied'); assert.equal(f.state.sub.status, 'active'); assert.equal(f.state.sub.schedule, null);
  assert.equal((await getPlanChange(f.env, f.user, result.changeId, f.services)).status, 'canceled');
  assert.equal(f.mutations().filter(entry => entry.path.endsWith('/release')).length, 1);
  assert.equal(f.mutations().some(entry => entry.path.endsWith('/cancel')), false);
  await cancelPlanChange(f.env, f.user, { changeId: result.changeId, idempotencyKey: 'undo-request-0001' }, f.services);
  assert.equal(f.mutations().filter(entry => entry.path.endsWith('/release')).length, 1);
});

test('historical trial end is not reapplied to a later active schedule phase', async t => {
  const f = await fixture(t, { plan: 'unlimited' });
  f.state.sub.trial_end = f.state.sub.items.data[0].current_period_start - 100;
  const quote = await preparePlanChange(f.env, f.user, { plan: 'starter' }, f.services);
  assert.equal((await commit(f, quote)).status, 'scheduled');
  const configure = f.mutations().find(entry => entry.path === '/v1/subscription_schedules/sub_sched_fixture');
  assert.equal(Object.hasOwn(configure.form, 'phases[0][trial_end]'), false);
});

test('input, foreign tenant, expiry and conflicting idempotency checks occur before financial writes', async t => {
  const f = await fixture(t);
  await rejectsCode(() => preparePlanChange(f.env, f.user, { plan: 'advanced', price: 'price_unlimited' }, f.services), 'invalid_plan', 400);
  const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  f.clock.at = quote.expiresAt;
  await rejectsCode(() => commit(f, quote), 'quote_expired'); assert.equal(f.mutations().length, 0);
  f.clock.at -= 10;
  const result = await commit(f, quote);
  await rejectsCode(() => commitPlanChange(f.env, f.user, { quoteId: crypto.randomUUID(), idempotencyKey: 'change-request-0001' }, f.services), 'idempotency_conflict');
  const foreign = { id: crypto.randomUUID(), stripe_customer_id: 'cus_other' };
  f.sqlite.prepare('INSERT INTO users(id,wallet,stripe_customer_id,created_at) VALUES (?,?,?,?)').run(foreign.id, 'other-wallet', foreign.stripe_customer_id, f.clock.at);
  f.sqlite.prepare("INSERT INTO subscriptions(user_id,stripe_subscription_id,status,period_end,updated_at,plan_id) VALUES (?,?,'active',?,?,'starter')").run(foreign.id, 'sub_other', f.clock.at + 1000, f.clock.at);
  const calls = f.state.requests.length;
  await rejectsCode(() => getPlanChange(f.env, foreign, result.changeId, f.services), 'change_not_found', 404);
  assert.equal(f.state.requests.length, calls); assert.equal(f.mutations().length, 1);
});

test('concurrent competing commits share a durable subscription lock and issue one upgrade', async t => {
  const f = await fixture(t);
  const one = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  const two = await preparePlanChange(f.env, f.user, { plan: 'unlimited' }, f.services);
  f.state.before = async entry => { if (entry.method === 'POST' && entry.path === '/v1/subscriptions/sub_owner') await new Promise(resolve => setTimeout(resolve, 30)); };
  const results = await Promise.allSettled([commit(f, one, 'concurrent-one-01'), commit(f, two, 'concurrent-two-02')]);
  assert.equal(results.filter(result => result.status === 'fulfilled').length, 1);
  assert.equal(results.find(result => result.status === 'rejected').reason.code, 'billing_operation_pending');
  assert.equal(f.mutations().length, 1);
});

test('one quote cannot be committed under two different keys', async t => {
  const f = await fixture(t); const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  const results = await Promise.allSettled([commit(f, quote, 'quote-key-one-01'), commit(f, quote, 'quote-key-two-02')]);
  assert.equal(results.filter(result => result.status === 'fulfilled').length, 1);
  assert.equal(results.find(result => result.status === 'rejected').reason.code, 'quote_already_committed');
  assert.equal(f.mutations().length, 1);
});

test('pending payment retains old entitlement and audit until canonical settlement', async t => {
  const f = await fixture(t); f.state.pending = true;
  const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services); const result = await commit(f, quote);
  assert.equal(result.status, 'pending_payment'); assert.equal(result.requiresPayment, true); assert.equal(result.currentPlan, 'starter');
  assert.equal(f.state.sub.items.data[0].price.id, 'price_starter'); assert.equal(f.sqlite.prepare('SELECT plan_id FROM subscriptions').get().plan_id, 'starter');
  assert.equal(f.state.sub.metadata.oraclebot_change_id, undefined);
  assert.equal(f.state.sub.pending_update.metadata.oraclebot_change_id, result.changeId);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 0);
  assert.equal((await getPlanChange(f.env, f.user, result.changeId, f.services)).status, 'pending_payment');
  Object.assign(f.state.sub.metadata, f.state.sub.pending_update.metadata);
  f.state.sub.pending_update = null; f.state.sub.items.data[0].price = price('advanced');
  assert.equal((await getPlanChange(f.env, f.user, result.changeId, f.services)).status, 'applied');
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 0); assert.equal(f.mutations().length, 1);
});

test('expired unpaid pending update releases its lock only after canonical rollback', async t => {
  const f = await fixture(t); f.state.pending = true;
  const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services); const result = await commit(f, quote);
  f.clock.at += 601; f.state.sub.pending_update = null;
  const failed = await getPlanChange(f.env, f.user, result.changeId, f.services);
  assert.equal(failed.status, 'failed'); assert.equal(failed.error, 'upgrade_payment_expired');
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 0);
});

test('lost upgrade response remains unknown and read-only canonical proof resolves it without resubmission', async t => {
  const f = await fixture(t); const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  f.state.after = entry => entry.method === 'POST' && entry.path === '/v1/subscriptions/sub_owner' ? 'disconnect' : null;
  const result = await commit(f, quote); assert.equal(result.status, 'unknown');
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 1);
  const reconciled = await getPlanChange(f.env, f.user, result.changeId, f.services);
  assert.equal(reconciled.status, 'applied'); assert.equal(f.mutations().length, 1);
  assert.equal((await commit(f, quote)).status, 'applied'); assert.equal(f.mutations().length, 1);
});

test('unknown schedule creation never adopts an unmarked schedule or repeats its mutation', async t => {
  const f = await fixture(t, { plan: 'unlimited' }); const quote = await preparePlanChange(f.env, f.user, { plan: 'starter' }, f.services);
  f.state.after = entry => entry.path === '/v1/subscription_schedules' && entry.method === 'POST' ? 'disconnect' : null;
  const result = await commit(f, quote); assert.equal(result.status, 'unknown');
  assert.equal((await getPlanChange(f.env, f.user, result.changeId, f.services)).status, 'unknown');
  assert.equal((await commit(f, quote)).status, 'unknown'); assert.equal(f.mutations().length, 1);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 1);
});

test('lost schedule configuration is resolved by its exact owned phase and metadata evidence', async t => {
  const f = await fixture(t, { plan: 'unlimited' }); const quote = await preparePlanChange(f.env, f.user, { plan: 'starter' }, f.services);
  f.state.after = entry => entry.path === '/v1/subscription_schedules/sub_sched_fixture' && entry.method === 'POST' ? 'disconnect' : null;
  const result = await commit(f, quote); assert.equal(result.status, 'unknown');
  assert.equal((await getPlanChange(f.env, f.user, result.changeId, f.services)).status, 'scheduled');
  assert.equal(f.mutations().length, 2); assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 0);
});

test('fresh preview or canonical-subscription drift refuses before an upgrade mutation', async t => {
  const f = await fixture(t); const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  f.state.amountDue += 1;
  await rejectsCode(() => commit(f, quote), 'invoice_preview_changed'); assert.equal(f.mutations().length, 0);
  assert.equal(f.sqlite.prepare('SELECT state FROM billing_lifecycle_operations').get().state, 'failed');
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 0);
  const second = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  f.state.sub.items.data[0].current_period_end += 1;
  await rejectsCode(() => commit(f, second, 'second-request-01'), 'subscription_changed'); assert.equal(f.mutations().length, 0);
});

test('provider read outage before mutation releases the no-write claim but retains failure audit', async t => {
  const f = await fixture(t); const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  f.state.before = entry => entry.method === 'GET' && entry.path === '/v1/subscriptions/sub_owner' ? 'fail' : null;
  await rejectsCode(() => commit(f, quote), 'billing_provider_unavailable', 503);
  assert.equal(f.mutations().length, 0); assert.equal(f.sqlite.prepare('SELECT state FROM billing_lifecycle_operations').get().state, 'failed');
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 0);
});

test('subscription cancellation releases only its owned downgrade and undo never creates a subscription', async t => {
  const f = await fixture(t, { plan: 'unlimited' }); const quote = await preparePlanChange(f.env, f.user, { plan: 'starter' }, f.services);
  const scheduled = await commit(f, quote);
  const canceled = await setPeriodEndCancellation(f.env, f.user, { cancelAtPeriodEnd: true, idempotencyKey: 'cancel-request-01' }, f.services);
  assert.equal(canceled.status, 'applied'); assert.equal(canceled.cancelAtPeriodEnd, true);
  assert.equal(f.state.sub.schedule, null); assert.equal(f.state.sub.cancel_at_period_end, true); assert.equal(f.state.sub.status, 'active');
  assert.equal((await getPlanChange(f.env, f.user, scheduled.changeId, f.services)).status, 'canceled');
  const actions = f.mutations().slice(-2).map(entry => entry.path);
  assert.deepEqual(actions, ['/v1/subscription_schedules/sub_sched_fixture/release', '/v1/subscriptions/sub_owner']);
  const undone = await setPeriodEndCancellation(f.env, f.user, { cancelAtPeriodEnd: false, idempotencyKey: 'uncancel-request-01' }, f.services);
  assert.equal(undone.status, 'applied'); assert.equal(f.state.sub.cancel_at_period_end, false);
  await rejectsCode(() => setPeriodEndCancellation(f.env, f.user, { cancelAtPeriodEnd: false, idempotencyKey: 'cancel-request-01' }, f.services), 'idempotency_conflict');
  assert.equal(f.mutations().some(entry => entry.path === '/v1/subscriptions'), false);
});

test('foreign schedule or terminal subscription cannot be released or resurrected', async t => {
  const f = await fixture(t);
  f.state.sub.schedule = 'sub_sched_foreign';
  await rejectsCode(() => setPeriodEndCancellation(f.env, f.user, { cancelAtPeriodEnd: true, idempotencyKey: 'foreign-cancel-01' }, f.services), 'schedule_ownership_unverified');
  assert.equal(f.mutations().length, 0);
  f.state.sub.schedule = null; f.state.sub.status = 'canceled';
  await rejectsCode(() => setPeriodEndCancellation(f.env, f.user, { cancelAtPeriodEnd: false, idempotencyKey: 'terminal-undo-01' }, f.services), 'subscription_terminal');
  assert.equal(f.mutations().length, 0);
});

test('custom tax, discount or ownership changes are refused rather than silently erased', async t => {
  const f = await fixture(t);
  f.state.sub.automatic_tax = { enabled: true };
  await rejectsCode(() => preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services), 'subscription_settings_unsupported');
  f.state.sub.automatic_tax.enabled = false; f.state.sub.metadata.oraclebot_user = 'other-user';
  await rejectsCode(() => preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services), 'subscription_binding_mismatch', 502);
  assert.equal(f.mutations().length, 0); assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_plan_quotes').get().n, 0);
});

test('expired request owner cannot issue a later stage or reacquire an unknown operation', async t => {
  const f = await fixture(t, { plan: 'unlimited' }); const quote = await preparePlanChange(f.env, f.user, { plan: 'starter' }, f.services);
  f.state.after = entry => {
    if (entry.path === '/v1/subscription_schedules' && entry.method === 'POST') {
      f.sqlite.prepare('UPDATE billing_lifecycle_locks SET expires_at=unixepoch()-1').run();
    }
  };
  const result = await commit(f, quote);
  assert.equal(result.status, 'unknown'); assert.equal(f.mutations().length, 1);
  assert.equal((await commit(f, quote)).status, 'unknown'); assert.equal(f.mutations().length, 1);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 1);
});

test('unknown cancellation is resolved by canonical operation marker without repeating a write', async t => {
  const f = await fixture(t);
  f.state.after = entry => entry.path === '/v1/subscriptions/sub_owner' && entry.method === 'POST' ? 'disconnect' : null;
  const result = await setPeriodEndCancellation(f.env, f.user, { cancelAtPeriodEnd: true, idempotencyKey: 'lost-cancel-01' }, f.services);
  assert.equal(result.status, 'unknown'); assert.equal(f.mutations().length, 1);
  assert.equal((await getPlanChange(f.env, f.user, result.changeId, f.services)).status, 'applied'); assert.equal(f.mutations().length, 1);
});

test('known pending payment denies another plan change but does not block cancellation', async t => {
  const f = await fixture(t); f.state.pending = true;
  const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  const upgrade = await commit(f, quote); assert.equal(upgrade.status, 'pending_payment');
  await rejectsCode(() => preparePlanChange(f.env, f.user, { plan: 'unlimited' }, f.services), 'subscription_change_pending');
  const canceled = await setPeriodEndCancellation(f.env, f.user, { cancelAtPeriodEnd: true, idempotencyKey: 'pending-cancel-01' }, f.services);
  assert.equal(canceled.status, 'applied'); assert.equal(f.state.sub.cancel_at_period_end, true);
  assert.equal((await getPlanChange(f.env, f.user, upgrade.changeId, f.services)).status, 'pending_payment');
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_operations').get().n, 2);
});

test('known finished operation recovers a crash before lock deletion', async t => {
  const f = await fixture(t);
  const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  const result = await commit(f, quote);
  f.sqlite.prepare('INSERT INTO billing_lifecycle_locks(subscription_id,operation_id,expires_at) VALUES (?,?,unixepoch()+120)').run('sub_owner', result.changeId);
  assert.equal((await getPlanChange(f.env, f.user, result.changeId, f.services)).status, 'applied');
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 0);
  assert.equal(f.mutations().length, 1);
});

test('quote expiry during a preview blocks the financial mutation even with a valid owner lease', async t => {
  const f = await fixture(t);
  const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  f.state.after = entry => { if (entry.path === '/v1/invoices/create_preview') f.clock.at = quote.expiresAt; };
  await rejectsCode(() => commit(f, quote), 'quote_expired'); assert.equal(f.mutations().length, 0);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 0);
});

test('foreign pending metadata or target cannot certify an unknown operation', async t => {
  const f = await fixture(t); f.state.pending = true;
  const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  f.state.after = entry => {
    if (entry.path === '/v1/subscriptions/sub_owner' && entry.method === 'POST') {
      f.state.sub.pending_update.metadata.oraclebot_change_id = crypto.randomUUID(); return 'disconnect';
    }
  };
  const result = await commit(f, quote); assert.equal(result.status, 'unknown');
  assert.equal((await getPlanChange(f.env, f.user, result.changeId, f.services)).status, 'unknown');
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 1);
  assert.equal(f.mutations().length, 1);
});

test('D1 evaluates lease expiry when a delayed renewal statement executes', async t => {
  const f = await fixture(t);
  const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  const prepare = f.env.DB.prepare;
  f.env.DB.prepare = sql => {
    const statement = prepare(sql);
    if (sql.startsWith('UPDATE billing_lifecycle_locks SET expires_at=unixepoch()')) {
      const first = statement.first;
      statement.first = async () => {
        f.sqlite.prepare('UPDATE billing_lifecycle_locks SET expires_at=unixepoch()-1').run();
        return first();
      };
    }
    return statement;
  };
  const result = await commit(f, quote);
  assert.equal(result.status, 'unknown'); assert.equal(f.mutations().length, 0);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 1);
});

test('a late read cannot demote an operation whose newer reconciliation already won', async t => {
  const f = await fixture(t); f.state.pending = true;
  const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services); const result = await commit(f, quote);
  let injected = false;
  f.state.after = entry => {
    if (!injected && entry.path === '/v1/subscriptions/sub_owner' && entry.method === 'GET') {
      injected = true;
      f.sqlite.prepare("UPDATE billing_lifecycle_operations SET state='applied',current_plan='advanced',revision=revision+1 WHERE id=?").run(result.changeId);
    }
  };
  const reconciled = await getPlanChange(f.env, f.user, result.changeId, f.services);
  assert.equal(reconciled.status, 'applied'); assert.equal(reconciled.currentPlan, 'advanced');
  assert.equal(f.mutations().length, 1);
});

test('current phase retains its genuine trial boundary when downgrading during trial', async t => {
  const f = await fixture(t, { trial: true, plan: 'unlimited' });
  const quote = await preparePlanChange(f.env, f.user, { plan: 'starter' }, f.services);
  const result = await commit(f, quote); assert.equal(result.status, 'scheduled');
  const configured = f.mutations().find(entry => entry.path === '/v1/subscription_schedules/sub_sched_fixture');
  assert.equal(configured.form['phases[0][trial_end]'], String(f.state.sub.trial_end));
  assert.equal(result.effectiveAt, f.state.sub.trial_end); assert.equal(f.state.sub.status, 'trialing');
});

test('historical applied operation can reconcile after later cancellation without granting entitlement', async t => {
  const f = await fixture(t);
  const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  f.state.after = entry => entry.path === '/v1/subscriptions/sub_owner' && entry.method === 'POST' ? 'disconnect' : null;
  const result = await commit(f, quote); assert.equal(result.status, 'unknown');
  f.state.sub.status = 'canceled';
  const reconciled = await getPlanChange(f.env, f.user, result.changeId, f.services);
  assert.equal(reconciled.status, 'applied'); assert.equal(f.state.sub.status, 'canceled');
  assert.equal(f.sqlite.prepare('SELECT plan_id FROM subscriptions').get().plan_id, 'starter');
  assert.equal(f.mutations().length, 1); assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 0);
});

test('lost response recovery list is bounded, tenant-owned and performs no provider calls', async t => {
  const f = await fixture(t);
  const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  f.state.after = entry => entry.path === '/v1/subscriptions/sub_owner' && entry.method === 'POST' ? 'disconnect' : null;
  const result = await commit(f, quote); const calls = f.state.requests.length;
  const rows = await listPlanChanges(f.env, f.user);
  assert.equal(rows.moreAvailable, false); assert.equal(rows.changes.length, 1); assert.equal(rows.changes[0].changeId, result.changeId);
  assert.equal(rows.changes[0].status, 'unknown'); assert.equal(f.state.requests.length, calls);
  const foreign = { id: crypto.randomUUID() };
  f.sqlite.prepare('INSERT INTO users(id,wallet,created_at) VALUES (?,?,?)').run(foreign.id, 'foreign-wallet', f.clock.at);
  assert.deepEqual(await listPlanChanges(f.env, foreign), { changes: [], moreAvailable: false });
  assert.equal(JSON.stringify(rows).includes('sub_owner'), false);
});

test('per-user quote rate is atomic and rejects before another provider request', async t => {
  const f = await fixture(t);
  for (let count = 0; count < 12; count += 1) await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  const calls = f.state.requests.length;
  await rejectsCode(() => preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services), 'billing_quote_rate_limited', 429);
  assert.equal(f.state.requests.length, calls);
  f.sqlite.prepare('UPDATE billing_quote_rate SET window_start=unixepoch()-61').run();
  await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  assert.equal(f.state.requests.length, calls + 3);
});

test('provider virtual clock must be bound by trusted services before previewing a future period', async t => {
  const f = await fixture(t);
  f.state.sub.items.data[0].current_period_start = f.clock.at + 100;
  f.state.sub.items.data[0].current_period_end = f.clock.at + 1000;
  await rejectsCode(() => preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services), 'billing_clock_mismatch', 503);
  assert.equal(f.state.requests.filter(entry => entry.path === '/v1/invoices/create_preview').length, 0);
  assert.equal(f.mutations().length, 0);
});

function fenceAccount(f) {
  const token = crypto.randomUUID();
  f.sqlite.prepare('UPDATE users SET deletion_token=?,deletion_requested_at=? WHERE id=?').run(token, f.clock.at, f.user.id);
  return token;
}
test('a fenced account cannot preview a new plan or increment its quote rate', async t => {
  const f = await fixture(t); fenceAccount(f);
  await rejectsCode(() => preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services), 'account_deleting', 409);
  assert.equal(f.state.requests.length, 0);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_quote_rate').get().n, 0);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_plan_quotes').get().n, 0);
});

test('a quote preview already at the provider cannot insert a quote after deletion wins', async t => {
  const f = await fixture(t);
  f.state.after = entry => { if (entry.path === '/v1/invoices/create_preview') fenceAccount(f); };
  await rejectsCode(() => preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services), 'account_deleting', 409);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_plan_quotes').get().n, 0);
  assert.equal(f.mutations().length, 0);
});

test('the final quote-rate statement rechecks a deletion fence installed after its initial owner read', async t => {
  const f = await fixture(t); const prepare = f.env.DB.prepare;
  f.env.DB.prepare = sql => {
    const statement = prepare(sql);
    if (sql.startsWith('INSERT INTO billing_quote_rate')) {
      const first = statement.first;
      statement.first = async () => { fenceAccount(f); return first(); };
    }
    return statement;
  };
  await rejectsCode(() => preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services), 'account_deleting', 409);
  assert.equal(f.state.requests.length, 0);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_quote_rate').get().n, 0);
});

test('the atomic operation claim refuses an upgrade when deletion wins immediately before its batch', async t => {
  const f = await fixture(t); const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  const batch = f.env.DB.batch;
  f.env.DB.batch = async statements => { fenceAccount(f); return batch(statements); };
  await rejectsCode(() => commit(f, quote), 'account_deleting', 409);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_operations').get().n, 0);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 0);
  assert.equal(f.mutations().length, 0);
});

test('an already claimed upgrade rechecks deletion at its last financial-write admission', async t => {
  const f = await fixture(t); const quote = await preparePlanChange(f.env, f.user, { plan: 'advanced' }, f.services);
  const prepare = f.env.DB.prepare;
  f.env.DB.prepare = sql => {
    const statement = prepare(sql);
    if (sql.startsWith('UPDATE billing_lifecycle_locks SET expires_at=unixepoch()')) {
      const first = statement.first;
      statement.first = async () => { fenceAccount(f); return first(); };
    }
    return statement;
  };
  const result = await commit(f, quote);
  assert.equal(result.status, 'unknown'); assert.equal(f.mutations().length, 0);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 1);
});

test('deletion blocks cancellation undo and scheduled-plan undo while preserving read reconciliation', async t => {
  const f = await fixture(t, { plan: 'unlimited' });
  const quote = await preparePlanChange(f.env, f.user, { plan: 'starter' }, f.services);
  const changed = await commit(f, quote); const count = f.mutations().length;
  fenceAccount(f);
  await rejectsCode(() => cancelPlanChange(f.env, f.user, { changeId: changed.changeId, idempotencyKey: 'undo-fenced-plan' }, f.services), 'account_deleting', 409);
  await rejectsCode(() => setPeriodEndCancellation(f.env, f.user, { cancelAtPeriodEnd: false, idempotencyKey: 'undo-fenced-cancel' }, f.services), 'account_deleting', 409);
  assert.equal((await getPlanChange(f.env, f.user, changed.changeId, f.services)).status, 'scheduled');
  assert.equal((await listPlanChanges(f.env, f.user)).changes.length, 1);
  assert.equal(f.mutations().length, count);
});

test('explicit subscription cancellation remains admitted after a deletion fence', async t => {
  const f = await fixture(t, { plan: 'unlimited' });
  const quote = await preparePlanChange(f.env, f.user, { plan: 'starter' }, f.services);
  await commit(f, quote); fenceAccount(f);
  const result = await setPeriodEndCancellation(f.env, f.user, { cancelAtPeriodEnd: true, idempotencyKey: 'cancel-fenced-subscription' }, f.services);
  assert.equal(result.status, 'applied'); assert.equal(result.cancelAtPeriodEnd, true);
  assert.equal(f.state.sub.cancel_at_period_end, true); assert.equal(f.state.sub.schedule, null);
  assert.equal(f.mutations().filter(entry => entry.path.endsWith('/release')).length, 1);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM billing_lifecycle_locks').get().n, 0);
});
