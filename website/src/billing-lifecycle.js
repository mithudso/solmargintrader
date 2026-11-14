/** Durable, tenant-bound subscription changes. No function grants entitlement. */

const PLAN_AMOUNTS = Object.freeze({ starter: 999, advanced: 2999, unlimited: 4999 });
const QUOTE_SECONDS = 300;
const LEASE_SECONDS = 120;
const TERMINAL = new Set(['canceled', 'incomplete_expired']);
const CHANGEABLE = new Set(['active', 'trialing']);
const CANCELABLE = new Set(['active', 'trialing', 'past_due', 'unpaid']);
const text = value => typeof value === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(value);
const opaque = value => typeof value === 'string' && /^[A-Za-z0-9_-]{8,128}$/.test(value);
const integer = value => Number.isSafeInteger(value) && value >= 0;
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value) &&
  Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const ref = value => typeof value === 'string' ? value : value?.id;

export class BillingLifecycleError extends Error {
  constructor(code, status = 409, message = 'The billing operation could not be verified. Refresh your subscription before trying again.') {
    super(message); this.name = 'BillingLifecycleError'; this.code = code; this.status = status;
  }
}
const fail = (code, status, message) => { throw new BillingLifecycleError(code, status, message); };
const db = (env, sql, ...args) => {
  if (!env.DB) fail('storage_unavailable', 503);
  return env.DB.prepare(sql).bind(...args);
};
const digest = async value => [...new Uint8Array(await crypto.subtle.digest('SHA-256',
  new TextEncoder().encode(typeof value === 'string' ? value : JSON.stringify(value))))]
  .map(byte => byte.toString(16).padStart(2, '0')).join('');

function context(env, services) {
  if (typeof services?.stripe !== 'function') fail('billing_unavailable', 503);
  const prices = { starter: env.STRIPE_STARTER_PRICE_ID, advanced: env.STRIPE_ADVANCED_PRICE_ID, unlimited: env.STRIPE_UNLIMITED_PRICE_ID };
  if (Object.values(prices).some(value => !/^price_[A-Za-z0-9_]+$/.test(value || '')) || new Set(Object.values(prices)).size !== 3) fail('billing_unavailable', 503);
  return { stripe: services.stripe, now: services.now || (() => Math.floor(Date.now() / 1000)), uuid: services.uuid || (() => crypto.randomUUID()), prices };
}
function planForPrice(ctx, price) { return Object.keys(ctx.prices).find(plan => ctx.prices[plan] === ref(price)) || null; }
function checkedPrice(price, plan, { requireActive = false } = {}) {
  if (!price || price.currency !== 'usd' || price.unit_amount !== PLAN_AMOUNTS[plan] ||
      price.type !== 'recurring' || price.recurring?.interval !== 'month' || price.recurring?.interval_count !== 1 ||
      (requireActive && price.active !== true) || price.recurring?.usage_type === 'metered') fail('price_mismatch', 503);
}
function taxSettings(value, managed = false) {
  if (value == null) return { enabled: false, liability: null };
  if (typeof value.enabled !== 'boolean' || value.disabled_reason != null) fail('subscription_settings_unsupported', 409);
  const liability = value.liability == null ? null : { type: value.liability.type };
  if (value.liability && (Object.keys(value.liability).some(key => key !== 'type') ||
      !['self', 'stripe'].includes(value.liability.type))) fail('subscription_settings_unsupported', 409);
  if ((value.enabled && (!liability || liability.type !== (managed ? 'stripe' : 'self'))) ||
      (!value.enabled && liability)) fail('subscription_settings_unsupported', 409);
  return { enabled: value.enabled, liability };
}
function billingSettings(subscription) {
  const managed = subscription.managed_payments?.enabled ?? false;
  if (typeof managed !== 'boolean') fail('subscription_settings_unsupported', 409);
  const automaticTax = taxSettings(subscription.automatic_tax, managed);
  if (managed && !automaticTax.enabled) fail('subscription_settings_unsupported', 409);
  const type = subscription.billing_mode?.type || 'classic';
  if (!['classic', 'flexible'].includes(type)) fail('subscription_settings_unsupported', 409);
  const discounts = type === 'flexible' ? subscription.billing_mode?.flexible?.proration_discounts : null;
  if (type === 'flexible' && !['included', 'itemized'].includes(discounts)) fail('subscription_settings_unsupported', 409);
  return { automaticTax, managedPayments: managed, billingMode: { type, prorationDiscounts: discounts } };
}
const sorted = value => Array.isArray(value) ? value.map(sorted) : value && typeof value === 'object' ?
  Object.fromEntries(Object.keys(value).sort().map(key => [key, sorted(value[key])])) : value;
const same = (one, two) => JSON.stringify(sorted(one)) === JSON.stringify(sorted(two));
function quoteBinding(quote) {
  try {
    const value = JSON.parse(quote.subscription_fingerprint);
    if (value.version === 2 && typeof value.hash === 'string' && value.billing) return value;
  } catch { /* Earlier quotes cannot prove the newer tax and cancellation binding. */ }
  return null;
}
function billingMatches(subscription, quote) {
  const binding = quoteBinding(quote);
  return !!binding && same(billingSettings(subscription), binding.billing);
}
const hasCancellation = sub => sub.raw.cancel_at_period_end || sub.cancelAt !== null;
const cancellationAt = sub => sub.cancelAt ?? (sub.raw.cancel_at_period_end ? sub.end : null);
const cancellationMatches = (sub, requested) => requested ? hasCancellation(sub) && cancellationAt(sub) === sub.end : !hasCancellation(sub);
function noComplexSettings(subscription) {
  // Checkout may enable Stripe-managed tax. Preserve its authority and mode;
  // manual tax, discounts and Connect settings still require billing support.
  billingSettings(subscription);
  if ((subscription.discounts?.length || 0) || subscription.discount || (subscription.default_tax_rates?.length || 0) ||
      subscription.pause_collection || subscription.transfer_data ||
      subscription.on_behalf_of || subscription.application_fee_percent != null || subscription.billing_thresholds ||
      subscription.invoice_settings?.issuer?.type === 'account' || (subscription.invoice_settings?.account_tax_ids?.length || 0) ||
      subscription.pending_invoice_item_interval || (subscription.collection_method && subscription.collection_method !== 'charge_automatically')) {
    fail('subscription_settings_unsupported', 409, 'This subscription has custom billing settings. Use billing support to change its plan safely.');
  }
}
function canonical(subscription, user, local, ctx) {
  const items = subscription?.items;
  if (!subscription || subscription.id !== local.stripe_subscription_id || ref(subscription.customer) !== user.stripe_customer_id ||
      subscription.metadata?.oraclebot_user !== user.id || !text(subscription.id) ||
      !Array.isArray(items?.data) || items.has_more || items.data.length !== 1 || items.data[0].quantity !== 1 ||
      !text(items.data[0].id)) fail('subscription_binding_mismatch', 502);
  const item = items.data[0]; const plan = planForPrice(ctx, item.price);
  if (!plan) fail('plan_mismatch', 409);
  checkedPrice(item.price, plan);
  if ((item.discounts?.length || 0) || (item.tax_rates?.length || 0) || item.billing_thresholds) fail('subscription_settings_unsupported', 409);
  const start = item.current_period_start ?? subscription.current_period_start;
  const end = item.current_period_end ?? subscription.current_period_end;
  const trialEnd = subscription.trial_end ?? null;
  const cancelAt = subscription.cancel_at ?? null;
  if (!integer(start) || !integer(end) || end <= start || (trialEnd !== null && !integer(trialEnd)) ||
      (cancelAt !== null && (!integer(cancelAt) || cancelAt === 0)) ||
      typeof subscription.status !== 'string' || typeof subscription.cancel_at_period_end !== 'boolean') fail('subscription_response_unverified', 502);
  return { raw: subscription, item, plan, start, end, trialEnd, cancelAt, schedule: ref(subscription.schedule) || null };
}
async function identity(env, inputUser) {
  if (!text(inputUser?.id)) fail('authentication_required', 401);
  const user = await db(env, 'SELECT id,stripe_customer_id FROM users WHERE id=?', inputUser.id).first();
  const local = await db(env, 'SELECT * FROM subscriptions WHERE user_id=?', inputUser.id).first();
  if (!user?.stripe_customer_id || !local || !/^sub_[A-Za-z0-9_]+$/.test(local.stripe_subscription_id)) fail('no_subscription', 409);
  return { user, local };
}
async function financialAdmission(env, user, kind = null) {
  const row = await db(env, 'SELECT deletion_token FROM users WHERE id=?', user.id).first();
  if (!row || (row.deletion_token !== null && kind !== 'cancel_subscription')) {
    fail('account_deleting', 409, 'Account deletion is in progress. Subscription cancellation and reconciliation remain available.');
  }
}
async function ownedSubscription(env, inputUser, ctx) {
  const owner = await identity(env, inputUser);
  const value = await ctx.stripe(`subscriptions/${owner.local.stripe_subscription_id}`);
  return { ...owner, sub: canonical(value, owner.user, owner.local, ctx) };
}
async function fingerprint(sub) {
  return digest({ id: sub.raw.id, customer: ref(sub.raw.customer), item: sub.item.id, price: ref(sub.item.price), quantity: sub.item.quantity,
    status: sub.raw.status, start: sub.start, end: sub.end, trialEnd: sub.trialEnd, schedule: sub.schedule,
    cancel: sub.raw.cancel_at_period_end, cancelAt: sub.cancelAt, billing: billingSettings(sub.raw), pending: sub.raw.pending_update || null });
}
function publicQuote(row) {
  const billing = quoteBinding(row)?.billing;
  return { quoteId: row.id, currentPlan: row.current_plan, targetPlan: row.target_plan, kind: row.kind,
    amountDueNowCents: row.amount_due_now_cents, renewalAmountCents: row.renewal_amount_cents, currency: 'usd',
    effectiveAt: row.effective_at, trialEnd: row.trial_end, expiresAt: row.expires_at,
    renewalAmountExcludesTax: billing?.automaticTax.enabled === true, automaticTaxEnabled: billing?.automaticTax.enabled === true,
    managedPaymentsEnabled: billing?.managedPayments === true };
}
function publicOperation(row) {
  return { changeId: row.id, status: row.state, kind: row.kind, currentPlan: row.current_plan,
    pendingPlan: ['applied', 'canceled', 'failed'].includes(row.state) ? null : row.target_plan,
    effectiveAt: row.effective_at, amountDueNowCents: row.amount_due_now_cents, currency: 'usd',
    cancelAtPeriodEnd: row.requested_cancel === null ? null : row.requested_cancel === 1,
    requiresPayment: row.state === 'pending_payment', error: row.last_error, createdAt: row.created_at, updatedAt: row.updated_at };
}
function previewFields(sub, targetPrice, at) {
  const trial = sub.raw.status === 'trialing' && sub.trialEnd > at;
  const fields = { customer: ref(sub.raw.customer), subscription: sub.raw.id,
    'subscription_details[items][0][id]': sub.item.id, 'subscription_details[items][0][price]': targetPrice,
    'subscription_details[items][0][quantity]': '1',
    'subscription_details[proration_behavior]': trial ? 'none' : 'always_invoice',
    'subscription_details[billing_cycle_anchor][type]': 'unchanged' };
  if (trial) fields['subscription_details[trial_end]'] = String(sub.trialEnd);
  else fields['subscription_details[proration_date]'] = String(at);
  return fields;
}
async function preview(ctx, sub, targetPrice, at) {
  const value = await ctx.stripe('invoices/create_preview', previewFields(sub, targetPrice, at));
  if (!value || ref(value.customer) !== ref(sub.raw.customer) || value.currency !== 'usd' ||
      !integer(value.amount_due)) fail('invoice_preview_unverified', 502);
  const settings = billingSettings(sub.raw);
  if (!same(taxSettings(value.automatic_tax, settings.managedPayments), settings.automaticTax) ||
      (settings.automaticTax.enabled && value.automatic_tax?.status !== 'complete') ||
      (value.managed_payments != null && value.managed_payments.enabled !== settings.managedPayments)) fail('invoice_tax_unverified', 502);
  // Keeping the exact original trial and using no proration charges zero now.
  // The provider preview can describe the first invoice at the future trial end.
  return sub.raw.status === 'trialing' && sub.trialEnd > ctx.now() ? 0 : value.amount_due;
}
async function quoteRate(env, user) {
  const accepted = await db(env, `INSERT INTO billing_quote_rate(user_id,window_start,requests)
    SELECT id,unixepoch(),1 FROM users WHERE id=? AND deletion_token IS NULL
    ON CONFLICT(user_id) DO UPDATE SET
      requests=CASE WHEN window_start<=unixepoch()-60 THEN 1 ELSE requests+1 END,
      window_start=CASE WHEN window_start<=unixepoch()-60 THEN unixepoch() ELSE window_start END
    WHERE (window_start<=unixepoch()-60 OR requests<12)
      AND EXISTS(SELECT 1 FROM users WHERE id=billing_quote_rate.user_id AND deletion_token IS NULL)
    RETURNING requests`, user.id).first();
  if (!accepted) {
    await financialAdmission(env, user);
    fail('billing_quote_rate_limited', 429, 'Too many plan previews. Wait one minute before trying again.');
  }
}

export async function preparePlanChange(env, inputUser, input, services) {
  if (!exact(input, ['plan']) || !Object.hasOwn(PLAN_AMOUNTS, input.plan)) fail('invalid_plan', 400);
  const ctx = context(env, services); const { user } = await identity(env, inputUser);
  await quoteRate(env, user);
  const { sub } = await ownedSubscription(env, user, ctx);
  if (!CHANGEABLE.has(sub.raw.status) || sub.end <= ctx.now()) fail('subscription_not_changeable', 409);
  if (sub.start > ctx.now()) fail('billing_clock_mismatch', 503, 'The billing clock does not match this subscription period. Refresh billing before changing plans.');
  noComplexSettings(sub.raw);
  if (sub.plan === input.plan) fail('plan_unchanged', 409);
  if (sub.raw.pending_update || sub.schedule || hasCancellation(sub)) fail('subscription_change_pending', 409);
  if (await db(env, 'SELECT operation_id FROM billing_lifecycle_locks WHERE subscription_id=?', sub.raw.id).first()) fail('billing_operation_pending', 409);
  const targetPrice = await ctx.stripe(`prices/${ctx.prices[input.plan]}`);
  if (targetPrice?.id !== ctx.prices[input.plan]) fail('price_mismatch', 503);
  checkedPrice(targetPrice, input.plan, { requireActive: true });
  const at = ctx.now(); const kind = PLAN_AMOUNTS[input.plan] > PLAN_AMOUNTS[sub.plan] ? 'upgrade' : 'downgrade';
  const amount = kind === 'upgrade' ? await preview(ctx, sub, targetPrice.id, at) : 0;
  const quote = { id: ctx.uuid(), user_id: user.id, subscription_id: sub.raw.id, customer_id: user.stripe_customer_id,
    subscription_item_id: sub.item.id, current_plan: sub.plan, target_plan: input.plan, current_price_id: ref(sub.item.price),
    target_price_id: targetPrice.id, kind, subscription_fingerprint: JSON.stringify({ version: 2, hash: await fingerprint(sub), billing: billingSettings(sub.raw) }), period_start: sub.start,
    period_end: sub.end, trial_end: sub.trialEnd, proration_date: at, amount_due_now_cents: amount,
    renewal_amount_cents: PLAN_AMOUNTS[input.plan], effective_at: kind === 'upgrade' ? at : sub.end,
    created_at: at, expires_at: Math.min(at + QUOTE_SECONDS, sub.end) };
  const inserted = await db(env, `INSERT INTO billing_plan_quotes (${Object.keys(quote).join(',')})
    SELECT ${Object.keys(quote).map(() => '?').join(',')} FROM users WHERE id=? AND deletion_token IS NULL RETURNING id`, ...Object.values(quote), user.id).first();
  if (!inserted) fail('account_deleting', 409);
  return publicQuote(quote);
}

async function operation(env, userId, id) {
  if (!opaque(id)) fail('invalid_change', 400);
  const row = await db(env, 'SELECT * FROM billing_lifecycle_operations WHERE id=? AND user_id=?', id, userId).first();
  if (!row) fail('change_not_found', 404);
  return row;
}
async function existing(env, userId, key, payloadHash) {
  if (!opaque(key)) fail('invalid_idempotency_key', 400);
  const row = await db(env, 'SELECT * FROM billing_lifecycle_operations WHERE user_id=? AND idempotency_key=?', userId, key).first();
  if (row && row.payload_hash !== payloadHash) fail('idempotency_conflict', 409);
  return row;
}
async function claim(env, user, input, ctx) {
  const at = ctx.now(); const id = ctx.uuid();
  const row = { id, user_id: user.id, quote_id: input.quoteId || null, parent_id: input.parentId || null, kind: input.kind,
    idempotency_key: input.key, payload_hash: input.payloadHash, subscription_id: input.subscriptionId,
    customer_id: user.stripe_customer_id, state: 'committing', stage: 'claimed', current_plan: input.currentPlan,
    target_plan: input.targetPlan || null, effective_at: input.effectiveAt ?? null, amount_due_now_cents: input.amount ?? null,
    provider_schedule_id: input.scheduleId || null, requested_cancel: input.cancel == null ? null : Number(input.cancel),
    created_at: at, updated_at: at };
  await env.DB.batch([
    db(env, `INSERT OR IGNORE INTO billing_lifecycle_operations (${Object.keys(row).join(',')})
      SELECT ${Object.keys(row).map(() => '?').join(',')} FROM users WHERE id=? AND (deletion_token IS NULL OR ?='cancel_subscription')`, ...Object.values(row), user.id, input.kind),
    db(env, `INSERT OR IGNORE INTO billing_lifecycle_locks (subscription_id,operation_id,expires_at)
      SELECT subscription_id,id,unixepoch()+? FROM billing_lifecycle_operations WHERE id=? AND user_id=?
        AND EXISTS(SELECT 1 FROM users WHERE id=billing_lifecycle_operations.user_id AND (deletion_token IS NULL OR billing_lifecycle_operations.kind='cancel_subscription'))`, LEASE_SECONDS, id, user.id),
  ]);
  const saved = await existing(env, user.id, input.key, input.payloadHash);
  if (!saved) {
    await financialAdmission(env, user, input.kind);
    fail('quote_already_committed', 409);
  }
  if (saved.id !== id) return { row: saved, won: false };
  const lock = await db(env, 'SELECT * FROM billing_lifecycle_locks WHERE subscription_id=?', saved.subscription_id).first();
  if (lock?.operation_id !== id) {
    await db(env, "UPDATE billing_lifecycle_operations SET state='failed',last_error='billing_operation_pending',revision=revision+1 WHERE id=? AND state='committing'", id).run();
    fail('billing_operation_pending', 409);
  }
  return { row: await operation(env, user.id, id), won: true };
}
async function advance(env, row, ctx, fields, { release = false } = {}) {
  const values = { ...fields, updated_at: ctx.now() };
  const result = await db(env, `UPDATE billing_lifecycle_operations SET ${Object.keys(values).map(key => `${key}=?`).join(',')},revision=revision+1
    WHERE id=? AND user_id=? AND revision=? RETURNING id`, ...Object.values(values), row.id, row.user_id, row.revision).run();
  const saved = await operation(env, row.user_id, row.id);
  if (release && result.results?.length === 1) await db(env, 'DELETE FROM billing_lifecycle_locks WHERE subscription_id=? AND operation_id=?', row.subscription_id, row.id).run();
  return saved;
}
async function beforeWrite(env, row, ctx) {
  // D1 evaluates its clock when the statement executes. A delayed application
  // timestamp cannot renew a lease after its actual expiry.
  const renewed = await db(env, `UPDATE billing_lifecycle_locks SET expires_at=unixepoch()+?
    WHERE subscription_id=? AND operation_id=? AND expires_at>unixepoch()
      AND EXISTS(SELECT 1 FROM billing_lifecycle_operations WHERE id=? AND user_id=? AND state='committing' AND revision=?)
      AND EXISTS(SELECT 1 FROM users WHERE id=? AND (deletion_token IS NULL OR ?='cancel_subscription'))
    RETURNING operation_id`, LEASE_SECONDS, row.subscription_id, row.id, row.id, row.user_id, row.revision, row.user_id, row.kind).first();
  if (!renewed || renewed.operation_id !== row.id) fail('billing_operation_fenced', 409);
}
async function providerWrite(env, row, ctx, path, fields, suffix) {
  await beforeWrite(env, row, ctx);
  return ctx.stripe(path, fields, `oraclebot-billing-${row.id}-${suffix}`);
}
async function unknown(env, row, ctx) {
  const current = await operation(env, row.user_id, row.id);
  if (current.state !== 'committing') return current;
  return advance(env, current, ctx, { state: 'unknown', last_error: 'provider_outcome_unknown' });
}
async function preconditionFailed(env, row, ctx, code) {
  const current = await operation(env, row.user_id, row.id);
  return advance(env, current, ctx, { state: 'failed', last_error: code }, { release: true });
}
function boundToOperation(owner, row) {
  if (owner.sub.raw.id !== row.subscription_id || owner.user.stripe_customer_id !== row.customer_id) fail('subscription_changed', 409);
}
function confirmUpgrade(sub, row, quote) {
  if (sub.trialEnd !== quote.trial_end || sub.end !== quote.period_end || sub.start !== quote.period_start ||
      !billingMatches(sub.raw, quote) || hasCancellation(sub)) fail('subscription_response_unverified', 502);
  if (sub.raw.pending_update) {
    if (sub.plan !== quote.current_plan || !pendingUpgradeMatches(sub, row, quote)) fail('subscription_response_unverified', 502);
    return { state: 'pending_payment', stage: 'subscription_updated', pending_expires_at: sub.raw.pending_update.expires_at };
  }
  if (sub.raw.metadata?.oraclebot_change_id !== row.id || sub.plan !== quote.target_plan || !CHANGEABLE.has(sub.raw.status)) fail('subscription_response_unverified', 502);
  return { state: 'applied', stage: 'reconciled', current_plan: sub.plan, last_error: null };
}
function pendingUpgradeMatches(sub, row, quote) {
  // Stripe stages metadata alongside the price; it merges into subscription
  // metadata only after payment applies the pending update (Dahlia 2026-05-27).
  const pending = sub.raw.pending_update;
  return pending?.metadata?.oraclebot_change_id === row.id && integer(pending.expires_at) &&
    Array.isArray(pending.subscription_items) && pending.subscription_items.length === 1 &&
    pending.subscription_items[0].id === quote.subscription_item_id &&
    ref(pending.subscription_items[0].price) === quote.target_price_id && pending.subscription_items[0].quantity === 1;
}
function scheduleIdentity(value, row, sub) {
  if (!value || !/^sub_sched_[A-Za-z0-9_]+$/.test(value.id || '') || ref(value.customer) !== row.customer_id ||
      ref(value.subscription) !== row.subscription_id || value.status !== 'active' ||
      !Array.isArray(value.phases) || value.phases.length < 1 || value.phases.length > 2 ||
      !integer(value.current_phase?.start_date) || !integer(value.current_phase?.end_date) ||
      value.current_phase.start_date !== sub.start || value.current_phase.end_date !== sub.end) fail('schedule_response_unverified', 502);
}
function scheduleTax(value, expected) {
  const defaults = taxSettings(value.default_settings?.automatic_tax, expected.managedPayments);
  if (!same(defaults, expected.automaticTax)) return false;
  if (value.managed_payments != null && value.managed_payments.enabled !== expected.managedPayments) return false;
  if (value.default_settings?.managed_payments != null && value.default_settings.managed_payments.enabled !== expected.managedPayments) return false;
  return value.phases.every(phase => {
    const tax = phase.automatic_tax == null ? defaults : taxSettings({ ...phase.automatic_tax,
      liability: phase.automatic_tax.enabled ? (phase.automatic_tax.liability ?? defaults.liability) : null }, expected.managedPayments);
    return same(tax, expected.automaticTax);
  });
}
function scheduleConfigured(value, row, quote) {
  if (value.id !== row.provider_schedule_id || value.metadata?.oraclebot_change_id !== row.id || value.metadata?.oraclebot_user !== row.user_id ||
      value.end_behavior !== 'release' || value.phases.length !== 2 || !quoteBinding(quote) ||
      !scheduleTax(value, quoteBinding(quote).billing)) return false;
  const [current, next] = value.phases;
  return current.start_date === quote.period_start && current.end_date === quote.period_end &&
    current.items?.length === 1 && ref(current.items[0].price) === quote.current_price_id && current.items[0].quantity === 1 &&
    next.start_date === quote.period_end && next.items?.length === 1 && ref(next.items[0].price) === quote.target_price_id && next.items[0].quantity === 1 &&
    (current.trial_end ?? null) === (quote.trial_end > quote.proration_date ? quote.trial_end : null);
}
function scheduleFields(created, row, quote) {
  const phase = created.phases[0];
  const expected = quoteBinding(quote)?.billing;
  if (!expected || !scheduleTax(created, expected)) fail('schedule_tax_unverified', 502);
  const defaults = created.default_settings;
  if (defaults && ((defaults.default_tax_rates?.length || 0) || (defaults.discounts?.length || 0) ||
      defaults.application_fee_percent != null || defaults.transfer_data || defaults.on_behalf_of || defaults.billing_thresholds ||
      (defaults.collection_method && defaults.collection_method !== 'charge_automatically') ||
      defaults.invoice_settings?.days_until_due != null || defaults.invoice_settings?.issuer?.type === 'account' ||
      (defaults.invoice_settings?.account_tax_ids?.length || 0))) fail('subscription_settings_unsupported', 409);
  if (phase.items?.length !== 1 || ref(phase.items[0].price) !== quote.current_price_id || phase.items[0].quantity !== 1 ||
      (phase.discounts?.length || 0) || (phase.default_tax_rates?.length || 0) || (phase.add_invoice_items?.length || 0) ||
      phase.application_fee_percent != null || phase.transfer_data || phase.on_behalf_of || phase.billing_thresholds ||
      (phase.collection_method && phase.collection_method !== 'charge_automatically') || phase.invoice_settings?.days_until_due != null ||
      (phase.invoice_settings?.account_tax_ids?.length || 0) ||
      (phase.items[0].discounts?.length || 0) || (phase.items[0].tax_rates?.length || 0)) fail('subscription_settings_unsupported', 409);
  const fields = { end_behavior: 'release', proration_behavior: 'none', 'metadata[oraclebot_change_id]': row.id,
    'metadata[oraclebot_user]': row.user_id, 'phases[0][start_date]': String(quote.period_start),
    'phases[0][end_date]': String(quote.period_end), 'phases[0][items][0][price]': quote.current_price_id,
    'phases[0][items][0][quantity]': '1', 'phases[0][proration_behavior]': 'none',
    'phases[1][start_date]': String(quote.period_end), 'phases[1][duration][interval]': 'month',
    'phases[1][duration][interval_count]': '1', 'phases[1][items][0][price]': quote.target_price_id,
    'phases[1][items][0][quantity]': '1', 'phases[1][proration_behavior]': 'none',
    'phases[1][metadata][oraclebot_user]': row.user_id, 'phases[1][metadata][oraclebot_change_id]': row.id };
  if (quote.trial_end > quote.proration_date) fields['phases[0][trial_end]'] = String(quote.trial_end);
  // Both phases inherit the already verified default liability. Stripe owns the
  // 'stripe' liability value for Managed Payments; never replace it with 'self'.
  if (expected.automaticTax.enabled) {
    fields['phases[0][automatic_tax][enabled]'] = 'true';
    fields['phases[1][automatic_tax][enabled]'] = 'true';
  }
  if (phase.default_payment_method) {
    if (!/^pm_[A-Za-z0-9_]+$/.test(ref(phase.default_payment_method) || '')) fail('subscription_settings_unsupported', 409);
    fields['phases[0][default_payment_method]'] = ref(phase.default_payment_method);
    fields['phases[1][default_payment_method]'] = ref(phase.default_payment_method);
  }
  if (phase.invoice_settings?.issuer != null && !same(phase.invoice_settings.issuer, created.default_settings?.invoice_settings?.issuer)) {
    fail('subscription_settings_unsupported', 409);
  }
  if (phase.metadata && typeof phase.metadata === 'object' && !Array.isArray(phase.metadata)) {
    for (const [key, value] of Object.entries(phase.metadata)) {
      if (!/^[A-Za-z0-9_-]{1,40}$/.test(key) || typeof value !== 'string' || value.length > 500) fail('subscription_settings_unsupported', 409);
      fields[`phases[0][metadata][${key}]`] = value;
    }
  }
  return fields;
}

export async function commitPlanChange(env, inputUser, input, services) {
  if (!exact(input, ['quoteId', 'idempotencyKey']) || !opaque(input.quoteId) || !opaque(input.idempotencyKey)) fail('invalid_plan_change', 400);
  const ctx = context(env, services); const { user } = await identity(env, inputUser);
  const payloadHash = await digest({ kind: 'plan_change', quoteId: input.quoteId });
  const prior = await existing(env, user.id, input.idempotencyKey, payloadHash);
  if (prior) return getPlanChange(env, user, prior.id, services);
  const quote = await db(env, 'SELECT * FROM billing_plan_quotes WHERE id=? AND user_id=?', input.quoteId, user.id).first();
  if (!quote) fail('quote_not_found', 404);
  if (quote.expires_at <= ctx.now()) fail('quote_expired', 409);
  const claimed = await claim(env, user, { quoteId: quote.id, kind: 'plan_change', key: input.idempotencyKey, payloadHash,
    subscriptionId: quote.subscription_id, currentPlan: quote.current_plan, targetPlan: quote.target_plan,
    effectiveAt: quote.effective_at, amount: quote.amount_due_now_cents }, ctx);
  if (!claimed.won) return getPlanChange(env, user, claimed.row.id, services);
  let row = claimed.row; let mutationStarted = false;
  try {
    const owner = await ownedSubscription(env, user, ctx); boundToOperation(owner, row);
    noComplexSettings(owner.sub.raw);
    if (quote.expires_at <= ctx.now() || await fingerprint(owner.sub) !== quoteBinding(quote)?.hash) fail('subscription_changed', 409);
    if (quote.kind === 'upgrade') {
      if (await preview(ctx, owner.sub, quote.target_price_id, quote.proration_date) !== quote.amount_due_now_cents) fail('invoice_preview_changed', 409);
      if (quote.expires_at <= ctx.now()) fail('quote_expired', 409);
      const trial = owner.sub.raw.status === 'trialing' && quote.trial_end > ctx.now();
      const fields = { 'items[0][id]': quote.subscription_item_id, 'items[0][price]': quote.target_price_id, 'items[0][quantity]': '1',
        payment_behavior: 'pending_if_incomplete', proration_behavior: trial ? 'none' : 'always_invoice',
        'billing_cycle_anchor[type]': 'unchanged', 'metadata[oraclebot_change_id]': row.id };
      if (trial) fields.trial_end = String(quote.trial_end);
      else fields.proration_date = String(quote.proration_date);
      mutationStarted = true;
      const value = await providerWrite(env, row, ctx, `subscriptions/${row.subscription_id}`, fields, 'upgrade');
      const updated = canonical(value, user, owner.local, ctx);
      const result = confirmUpgrade(updated, row, quote);
      // A known pending update remains in the audit ledger and cannot grant the
      // higher plan. It need not block cancellation: new plan writes independently
      // reject its canonical pending_update, including already-quoted races.
      row = await advance(env, row, ctx, result, { release: ['applied', 'pending_payment'].includes(result.state) });
    } else {
      if (quote.expires_at <= ctx.now()) fail('quote_expired', 409);
      mutationStarted = true;
      const created = await providerWrite(env, row, ctx, 'subscription_schedules', { from_subscription: row.subscription_id }, 'schedule-create');
      scheduleIdentity(created, row, owner.sub);
      row = await advance(env, row, ctx, { stage: 'schedule_created', provider_schedule_id: created.id });
      const fields = scheduleFields(created, row, quote);
      if (quote.expires_at <= ctx.now()) fail('quote_expired', 409);
      const configured = await providerWrite(env, row, ctx, `subscription_schedules/${created.id}`, fields, 'schedule-configure');
      scheduleIdentity(configured, row, owner.sub);
      if (!scheduleConfigured(configured, row, quote) || !same(configured.default_settings, created.default_settings)) fail('schedule_response_unverified', 502);
      const after = await ownedSubscription(env, user, ctx);
      if (!billingMatches(after.sub.raw, quote) || hasCancellation(after.sub) || after.sub.plan !== quote.current_plan ||
          after.sub.schedule !== created.id || after.sub.start !== quote.period_start || after.sub.end !== quote.period_end ||
          after.sub.trialEnd !== quote.trial_end) fail('subscription_response_unverified', 502);
      row = await advance(env, row, ctx, { state: 'scheduled', stage: 'reconciled', last_error: null }, { release: true });
    }
  } catch (error) {
    if (mutationStarted) row = await unknown(env, row, ctx);
    else {
      await preconditionFailed(env, row, ctx, error instanceof BillingLifecycleError ? error.code : 'provider_unavailable');
      if (error instanceof BillingLifecycleError) throw error;
      fail('billing_provider_unavailable', 503);
    }
  }
  return publicOperation(row);
}

async function expireOwner(env, row, ctx) {
  if (row.state !== 'committing') return row;
  const expired = await db(env, 'SELECT operation_id FROM billing_lifecycle_locks WHERE subscription_id=? AND operation_id=? AND expires_at<=unixepoch()', row.subscription_id, row.id).first();
  if (expired) return unknown(env, row, ctx);
  return row;
}
async function reconcile(env, user, row, ctx) {
  row = await expireOwner(env, row, ctx);
  if (['applied', 'failed', 'canceled', 'scheduled', 'pending_payment'].includes(row.state)) {
    // Recover a crash after a definitive outcome was saved but before its lock
    // deletion. A known pending payment still denies new plan changes but allows
    // cancellation. Never release a committing or unknown operation this way.
    await db(env, 'DELETE FROM billing_lifecycle_locks WHERE subscription_id=? AND operation_id=?', row.subscription_id, row.id).run();
  }
  if (!['unknown', 'pending_payment', 'scheduled'].includes(row.state)) return row;
  const owner = await ownedSubscription(env, user, ctx); boundToOperation(owner, row);
  const sub = owner.sub;
  if (row.kind === 'plan_change') {
    const quote = await db(env, 'SELECT * FROM billing_plan_quotes WHERE id=? AND user_id=?', row.quote_id, user.id).first();
    if (!quote) return row;
    if (quote.kind === 'upgrade') {
      if (sub.plan === quote.current_plan && billingMatches(sub.raw, quote) && pendingUpgradeMatches(sub, row, quote)) {
        return advance(env, row, ctx, { state: 'pending_payment', stage: 'subscription_updated', pending_expires_at: sub.raw.pending_update.expires_at, last_error: null }, { release: true });
      }
      if (row.state === 'pending_payment' && row.pending_expires_at <= ctx.now() && !sub.raw.pending_update && sub.plan === quote.current_plan) {
        return advance(env, row, ctx, { state: 'failed', stage: 'reconciled', last_error: 'upgrade_payment_expired' }, { release: true });
      }
      if (sub.raw.metadata?.oraclebot_change_id !== row.id) return row;
      // The operation can have applied before a later cancellation or delinquent
      // renewal. Its historical outcome never grants present entitlement.
      if (sub.plan === quote.target_plan && !sub.raw.pending_update && sub.trialEnd === quote.trial_end && billingMatches(sub.raw, quote)) {
        return advance(env, row, ctx, { state: 'applied', stage: 'reconciled', current_plan: sub.plan, last_error: null }, { release: true });
      }
    } else if (row.provider_schedule_id) {
      const schedule = await ctx.stripe(`subscription_schedules/${row.provider_schedule_id}`);
      if (schedule.id !== row.provider_schedule_id || schedule.metadata?.oraclebot_change_id !== row.id || schedule.metadata?.oraclebot_user !== user.id ||
          ref(schedule.customer) !== row.customer_id || ![ref(schedule.subscription), ref(schedule.released_subscription)].includes(row.subscription_id)) return row;
      if (sub.plan === quote.target_plan && ctx.now() >= quote.period_end && !sub.raw.pending_update && billingMatches(sub.raw, quote)) {
        return advance(env, row, ctx, { state: 'applied', stage: 'reconciled', current_plan: sub.plan, last_error: null }, { release: true });
      }
      if (schedule.status === 'released' && ref(schedule.released_subscription) === row.subscription_id) {
        return advance(env, row, ctx, { state: 'canceled', stage: 'reconciled', target_plan: null, last_error: null }, { release: true });
      }
      if (schedule.status === 'active' && ref(schedule.subscription) === row.subscription_id && sub.schedule === schedule.id &&
          billingMatches(sub.raw, quote) && scheduleConfigured(schedule, row, quote)) {
        return advance(env, row, ctx, { state: 'scheduled', stage: 'reconciled', last_error: null }, { release: true });
      }
    }
  } else if (row.kind === 'undo_plan_change') {
    const schedule = await ctx.stripe(`subscription_schedules/${row.provider_schedule_id}`);
    const parent = await operation(env, user.id, row.parent_id);
    if (schedule.id === row.provider_schedule_id && schedule.metadata?.oraclebot_change_id === parent.id && schedule.metadata?.oraclebot_user === user.id &&
        ref(schedule.customer) === row.customer_id && schedule.status === 'released' && ref(schedule.released_subscription) === row.subscription_id && !sub.schedule) {
      await advance(env, parent, ctx, { state: 'canceled', stage: 'reconciled', target_plan: null, last_error: null });
      return advance(env, row, ctx, { state: 'applied', stage: 'reconciled', target_plan: null, last_error: null }, { release: true });
    }
  } else if (sub.raw.metadata?.oraclebot_cancel_id === row.id &&
      ((row.requested_cancel === 1 && (cancellationMatches(sub, true) || TERMINAL.has(sub.raw.status))) ||
       (row.requested_cancel === 0 && cancellationMatches(sub, false) && !TERMINAL.has(sub.raw.status) && sub.end > ctx.now()))) {
    return advance(env, row, ctx, { state: 'applied', stage: 'reconciled', last_error: null }, { release: true });
  }
  return row;
}

export async function getPlanChange(env, inputUser, changeId, services) {
  const ctx = context(env, services); const { user } = await identity(env, inputUser);
  const row = await operation(env, user.id, changeId);
  try { return publicOperation(await reconcile(env, user, row, ctx)); }
  catch { return publicOperation(await operation(env, user.id, row.id)); }
}

export async function listPlanChanges(env, inputUser) {
  if (!text(inputUser?.id) || !await db(env, 'SELECT id FROM users WHERE id=?', inputUser.id).first()) fail('authentication_required', 401);
  const rows = await db(env, `SELECT * FROM billing_lifecycle_operations WHERE user_id=?
    ORDER BY CASE WHEN state IN ('committing','unknown','pending_payment','scheduled') THEN 0 ELSE 1 END,
      created_at DESC,id DESC LIMIT 51`, inputUser.id).all();
  return { changes: rows.results.slice(0, 50).map(publicOperation), moreAvailable: rows.results.length > 50 };
}

async function ownedSchedule(env, user, parent, owner, ctx) {
  if (!parent.provider_schedule_id || owner.sub.schedule !== parent.provider_schedule_id || ctx.now() >= parent.effective_at) fail('scheduled_change_not_cancelable', 409);
  const value = await ctx.stripe(`subscription_schedules/${parent.provider_schedule_id}`);
  if (value.id !== parent.provider_schedule_id || value.metadata?.oraclebot_change_id !== parent.id || value.metadata?.oraclebot_user !== user.id ||
      ref(value.customer) !== user.stripe_customer_id || ref(value.subscription) !== parent.subscription_id || value.status !== 'active') fail('schedule_ownership_unverified', 409);
  return value;
}
async function releaseSchedule(env, user, row, parent, owner, ctx) {
  await ownedSchedule(env, user, parent, owner, ctx);
  const before = billingSettings(owner.sub.raw);
  const released = await providerWrite(env, row, ctx, `subscription_schedules/${parent.provider_schedule_id}/release`, {}, 'schedule-release');
  if (released?.id !== parent.provider_schedule_id || released.status !== 'released' || ref(released.customer) !== user.stripe_customer_id ||
      ref(released.released_subscription) !== row.subscription_id || released.metadata?.oraclebot_change_id !== parent.id ||
      released.metadata?.oraclebot_user !== user.id) fail('schedule_release_unverified', 502);
  const after = await ownedSubscription(env, user, ctx);
  if (after.sub.schedule || !same(billingSettings(after.sub.raw), before)) fail('schedule_release_unverified', 502);
  await advance(env, parent, ctx, { state: 'canceled', stage: 'reconciled', target_plan: null, last_error: null });
  return advance(env, row, ctx, { stage: 'schedule_released' });
}

export async function cancelPlanChange(env, inputUser, input, services) {
  if (!exact(input, ['changeId', 'idempotencyKey']) || !opaque(input.changeId) || !opaque(input.idempotencyKey)) fail('invalid_plan_change', 400);
  const ctx = context(env, services); const { user } = await identity(env, inputUser);
  const payloadHash = await digest({ kind: 'undo_plan_change', changeId: input.changeId });
  const prior = await existing(env, user.id, input.idempotencyKey, payloadHash);
  if (prior) return getPlanChange(env, user, prior.id, services);
  const parent = await operation(env, user.id, input.changeId);
  if (parent.kind !== 'plan_change' || parent.state !== 'scheduled') fail('scheduled_change_not_cancelable', 409);
  const claimed = await claim(env, user, { parentId: parent.id, kind: 'undo_plan_change', key: input.idempotencyKey, payloadHash,
    subscriptionId: parent.subscription_id, currentPlan: parent.current_plan, targetPlan: null,
    effectiveAt: ctx.now(), scheduleId: parent.provider_schedule_id }, ctx);
  if (!claimed.won) return getPlanChange(env, user, claimed.row.id, services);
  let row = claimed.row; let mutationStarted = false;
  try {
    const owner = await ownedSubscription(env, user, ctx); boundToOperation(owner, row);
    if (TERMINAL.has(owner.sub.raw.status)) fail('subscription_terminal', 409);
    await ownedSchedule(env, user, parent, owner, ctx);
    mutationStarted = true;
    row = await releaseSchedule(env, user, row, parent, owner, ctx);
    row = await advance(env, row, ctx, { state: 'applied', stage: 'reconciled', last_error: null }, { release: true });
  } catch (error) {
    if (mutationStarted) row = await unknown(env, row, ctx);
    else { await preconditionFailed(env, row, ctx, error instanceof BillingLifecycleError ? error.code : 'provider_unavailable'); throw error; }
  }
  return publicOperation(row);
}

export async function setPeriodEndCancellation(env, inputUser, input, services) {
  if (!exact(input, ['cancelAtPeriodEnd', 'idempotencyKey']) || typeof input.cancelAtPeriodEnd !== 'boolean' || !opaque(input.idempotencyKey)) fail('invalid_cancellation', 400);
  const ctx = context(env, services); const { user } = await identity(env, inputUser);
  const kind = input.cancelAtPeriodEnd ? 'cancel_subscription' : 'undo_subscription_cancel';
  const payloadHash = await digest({ kind, cancelAtPeriodEnd: input.cancelAtPeriodEnd });
  const prior = await existing(env, user.id, input.idempotencyKey, payloadHash);
  if (prior) return getPlanChange(env, user, prior.id, services);
  const initial = await ownedSubscription(env, user, ctx);
  if (!CANCELABLE.has(initial.sub.raw.status) || initial.sub.end <= ctx.now()) fail('subscription_terminal', 409);
  const claimed = await claim(env, user, { kind, key: input.idempotencyKey, payloadHash, subscriptionId: initial.sub.raw.id,
    currentPlan: initial.sub.plan, effectiveAt: input.cancelAtPeriodEnd ? initial.sub.end : ctx.now(), cancel: input.cancelAtPeriodEnd }, ctx);
  if (!claimed.won) return getPlanChange(env, user, claimed.row.id, services);
  let row = claimed.row; let mutationStarted = false;
  try {
    let owner = await ownedSubscription(env, user, ctx); boundToOperation(owner, row);
    if (!CANCELABLE.has(owner.sub.raw.status) || owner.sub.end <= ctx.now()) fail('subscription_terminal', 409);
    if (owner.sub.schedule) {
      const parent = await db(env, "SELECT * FROM billing_lifecycle_operations WHERE user_id=? AND subscription_id=? AND provider_schedule_id=? AND kind='plan_change' AND state='scheduled'", user.id, row.subscription_id, owner.sub.schedule).first();
      if (!parent) fail('schedule_ownership_unverified', 409);
      await ownedSchedule(env, user, parent, owner, ctx);
      mutationStarted = true;
      row = await advance(env, row, ctx, { provider_schedule_id: parent.provider_schedule_id, parent_id: parent.id });
      row = await releaseSchedule(env, user, row, parent, owner, ctx);
      owner = await ownedSubscription(env, user, ctx); boundToOperation(owner, row);
      if (TERMINAL.has(owner.sub.raw.status) || owner.sub.end <= ctx.now() || owner.sub.schedule) fail('subscription_changed', 409);
    }
    if (input.cancelAtPeriodEnd && owner.sub.cancelAt !== null && owner.sub.cancelAt !== owner.sub.end) {
      fail('subscription_cancellation_date_unsupported', 409);
    }
    if (cancellationMatches(owner.sub, input.cancelAtPeriodEnd)) {
      row = await advance(env, row, ctx, { state: 'applied', stage: 'reconciled',
        effective_at: input.cancelAtPeriodEnd ? cancellationAt(owner.sub) : ctx.now(), last_error: null }, { release: true });
    } else {
      const fields = { 'metadata[oraclebot_cancel_id]': row.id };
      if (!input.cancelAtPeriodEnd) {
        // A flexible-mode portal cancellation has cancel_at set while the flag
        // is already false. Stripe rejects sending both cancellation parameters.
        // Clear the active representation, then verify both canonical fields.
        if (owner.sub.cancelAt !== null && !owner.sub.raw.cancel_at_period_end) fields.cancel_at = '';
        else fields.cancel_at_period_end = 'false';
      } else if (owner.sub.raw.billing_mode?.type === 'flexible') fields.cancel_at = String(owner.sub.end);
      else fields.cancel_at_period_end = 'true';
      mutationStarted = true;
      const value = await providerWrite(env, row, ctx, `subscriptions/${row.subscription_id}`, fields, 'cancel-flag');
      const sub = canonical(value, user, owner.local, ctx);
      if (TERMINAL.has(sub.raw.status) || sub.end <= ctx.now() || sub.raw.metadata?.oraclebot_cancel_id !== row.id ||
          !cancellationMatches(sub, input.cancelAtPeriodEnd)) fail('cancellation_response_unverified', 502);
      row = await advance(env, row, ctx, { state: 'applied', stage: 'reconciled',
        effective_at: input.cancelAtPeriodEnd ? cancellationAt(sub) : ctx.now(), last_error: null }, { release: true });
    }
  } catch (error) {
    if (mutationStarted) row = await unknown(env, row, ctx);
    else { await preconditionFailed(env, row, ctx, error instanceof BillingLifecycleError ? error.code : 'provider_unavailable'); throw error; }
  }
  return publicOperation(row);
}
