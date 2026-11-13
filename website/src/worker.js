import { base58Decode, bytesToBase64 } from '../../extension/src/wallet/solana.js';
import { authenticateAgent, cleanupAgentAccess, handleOAuth, OAuthError } from './oauth.js';
import { handleMcp, MCP_PROTOCOL_VERSION } from './mcp.js';
import { executionAvailable } from './trades.js';
import { BacktestJobError, createBacktestJob, getBacktestJob, listBacktestJobs, reconcileBacktestJobs } from './backtest-jobs.js';
import { BillingLifecycleError, preparePlanChange, commitPlanChange, getPlanChange, listPlanChanges, cancelPlanChange, setPeriodEndCancellation } from './billing-lifecycle.js';
import { AccountLifecycleError, markExecutionInitialized, beginAccountDeletion, cleanupAccountExecution, deletionFencePredicate } from './account-lifecycle.js';
import { ManagedBotError, prepareManagedBot, activateManagedBot, managedBotStatus, pauseManagedBot, tickManagedBots } from './managed-bots.js';

export const COINS = ['SOL', 'BTC', 'ETH', 'ZEC'];
// Null removes a subscription count cap. Resource and risk bounds remain separate.
export const PLANS = Object.freeze({
  starter: Object.freeze({ id: 'starter', name: 'Starter', monthlyUsd: 9.99, botLimit: 3, backtestsPerDay: 10 }),
  advanced: Object.freeze({ id: 'advanced', name: 'Advanced', monthlyUsd: 29.99, botLimit: 10, backtestsPerDay: null }),
  unlimited: Object.freeze({ id: 'unlimited', name: 'Unlimited', monthlyUsd: 49.99, botLimit: null, backtestsPerDay: null }),
});
const BACKTEST_CONCURRENCY = 1;
const RESERVATION_SECONDS = 300;
const WEBHOOK_LEASE_SECONDS = 30;
const utcDay = (at = now()) => new Date(at * 1000).toISOString().slice(0, 10);
const enc = new TextEncoder();
const SESSION_SECONDS = 86400;
// Match the Stripe session's expiration. An ambiguous create stays locked until
// that session cannot accept payment, preventing two payable checkout sessions.
const CHECKOUT_SECONDS = 2100;
const MAX_BODY = 16384;
const BLOCKED = 'Live execution requires a separately verified, per-user venue connection. This configuration does not run or place orders.';
const securityHeaders = {
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self' https://checkout.stripe.com https://billing.stripe.com",
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
};

class ApiError extends Error {
  constructor(status, code, message = code) { super(message); this.status = status; this.code = code; }
}
const now = () => Math.floor(Date.now() / 1000);
const json = (value, status = 200, headers = {}) => Response.json(value, { status, headers: { 'Cache-Control': 'no-store', ...headers } });
const fail = (status, code, message) => { throw new ApiError(status, code, message); };
const requireDB = env => { if (!env.DB) fail(503, 'storage_unavailable', 'Account storage is not configured.'); return env.DB; };
const query = (env, sql, ...args) => requireDB(env).prepare(sql).bind(...args);
const hash = async value => [...new Uint8Array(await crypto.subtle.digest('SHA-256', enc.encode(value)))].map(x => x.toString(16).padStart(2, '0')).join('');

function failureOperation(request) {
  const path = new URL(request.url).pathname;
  const known = ['/api/health', '/api/config', '/api/auth/challenge', '/api/auth/verify', '/api/me', '/api/auth/logout', '/api/billing/webhook', '/api/oracle', '/api/strategies', '/api/billing/checkout', '/api/billing/portal', '/api/bots', '/api/backtests',
    '/mcp', '/oauth/register', '/oauth/authorize', '/oauth/token', '/oauth/revoke',
    '/.well-known/oauth-protected-resource', '/.well-known/oauth-protected-resource/mcp', '/.well-known/oauth-authorization-server',
    '/api/agent/authorization', '/api/agent/authorization/challenge', '/api/agent/grants', '/api/runtime', '/api/backtest-jobs'];
  const route = known.includes(path) ? path : /^\/api\/bots\/[a-f0-9-]{36}$/.test(path) ? '/api/bots/:id' :
    /^\/api\/agent\/grants\/[a-f0-9-]{36}\/revoke$/.test(path) ? '/api/agent/grants/:id/revoke' :
    /^\/api\/backtest-jobs\/[a-f0-9-]{36}$/.test(path) ? '/api/backtest-jobs/:id' : '/api/unknown';
  const method = ['GET', 'POST', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'].includes(request.method) ? request.method : 'OTHER';
  return `${method} ${route}`;
}
function reportFailure(request, response, code) {
  // Operation names and codes are fixed vocabulary; raw URLs, errors and account
  // data must never reach the runtime diagnostic sink.
  diagnostic(response.status >= 500 ? 'error' : 'warn', { event: 'oraclebot.request_failed', operation: failureOperation(request), code, status: response.status });
}
function diagnostic(level, value) {
  // A failed diagnostic sink must never change an account or provider operation.
  try { console[level](JSON.stringify(value)); } catch {}
}
async function observeUpstream(operation, run) {
  const started = Date.now(); let status = 0; let outcome = 'failure';
  diagnostic('info', { event: 'oraclebot.upstream', operation, phase: 'start' });
  try {
    const value = await run(responseStatus => { status = responseStatus; });
    outcome = 'success';
    return value;
  } finally {
    diagnostic(outcome === 'success' ? 'info' : 'warn', { event: 'oraclebot.upstream', operation, phase: 'outcome', outcome, status, durationMs: Math.max(0, Date.now() - started) });
  }
}
function stripeOperation(path) {
  if (path === 'customers') return 'stripe.customer_create';
  if (path.startsWith('subscriptions?')) return 'stripe.subscription_list';
  if (/^subscriptions\/sub_[A-Za-z0-9]+$/.test(path)) return 'stripe.subscription_get';
  if (path === 'checkout/sessions') return 'stripe.checkout_create';
  if (path === 'billing_portal/sessions') return 'stripe.portal_create';
  return 'stripe.other';
}
function engineOperation(path) {
  if (path.startsWith('/v1/oracle?')) return 'engine.oracle';
  if (path === '/v1/strategies') return 'engine.strategies';
  if (path === '/v1/backtests') return 'engine.backtests';
  if (path === '/v1/jobs') return 'engine.job_submit';
  if (/^\/v1\/jobs\/[a-f0-9-]{36}$/.test(path)) return 'engine.job_status';
  if (path === '/health') return 'engine.health';
  if (path === '/v1/signals') return 'engine.signal';
  return 'engine.other';
}

async function boundedText(request, limit = MAX_BODY) {
  if (Number(request.headers.get('Content-Length')) > limit) fail(413, 'request_too_large');
  const reader = request.body?.getReader();
  if (!reader) return '';
  let size = 0;
  const chunks = [];
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.length;
    if (size > limit) { await reader.cancel(); fail(413, 'request_too_large'); }
    chunks.push(value);
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return new TextDecoder().decode(bytes);
}
async function bodyJSON(request) {
  if (!request.headers.get('Content-Type')?.toLowerCase().startsWith('application/json')) fail(415, 'json_required');
  try {
    const value = JSON.parse(await boundedText(request));
    if (!value || Array.isArray(value) || typeof value !== 'object') fail(400, 'invalid_json');
    return value;
  } catch (error) { if (error instanceof ApiError) throw error; fail(400, 'invalid_json'); }
}
function originOf(request, env) {
  const origin = new URL(request.url).origin;
  if (env.APP_ORIGIN && origin !== new URL(env.APP_ORIGIN).origin) fail(403, 'unexpected_host');
  return origin;
}
function sameOrigin(request, env) {
  const origin = originOf(request, env);
  if (request.headers.get('Origin') !== origin) fail(403, 'origin_required');
  if (request.headers.get('Sec-Fetch-Site') === 'cross-site') fail(403, 'cross_site_request');
}
function cookie(token = '', seconds = SESSION_SECONDS) {
  return `__Host-oraclebot=${token}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${seconds}`;
}
function sessionToken(request) {
  return request.headers.get('Cookie')?.split(';').map(v => v.trim()).find(v => v.startsWith('__Host-oraclebot='))?.slice(17) || '';
}
async function account(request, env, required = true) {
  const token = sessionToken(request);
  let user = null;
  if (/^[A-Za-z0-9_-]{43}$/.test(token)) {
    user = await query(env, 'SELECT u.* FROM users u JOIN sessions s ON s.user_id = u.id WHERE s.token_hash = ? AND s.expires_at > ?', await hash(token), now()).first();
  }
  if (!user && required) fail(401, 'authentication_required', 'Connect and sign in with your wallet first.');
  const expected = request.headers.get('X-Oraclebot-Account');
  if (expected !== null && expected !== user?.id) fail(409, 'account_changed', 'Your signed-in account changed. Reload your account before continuing.');
  if (user?.deletion_token && !['GET', 'HEAD'].includes(request.method)) {
    const path = new URL(request.url).pathname;
    const recovery = path === '/api/me' && request.method === 'DELETE' || ['/api/auth/logout', '/api/billing/portal', '/api/billing/cancellation'].includes(path) ||
      /^\/api\/(?:connections\/[a-f0-9-]{36}|agent\/grants\/[a-f0-9-]{36})\/revoke$/.test(path);
    if (!recovery) fail(409, 'account_deleting', 'Deletion is in progress. Status and cleanup remain available; new account actions are disabled.');
  }
  return user;
}
function publicUser(user) { return user ? { id: user.id, wallet: user.wallet, createdAt: user.created_at, deletionPending: Boolean(user.deletion_token) } : null; }
export function hasEntitlement(sub, at = now()) {
  return Boolean(sub && ((sub.status === 'trialing' && sub.trial_end > at) || (sub.status === 'active' && sub.period_end > at)));
}
async function subscription(env, user) { return user ? query(env, 'SELECT * FROM subscriptions WHERE user_id = ?', user.id).first() : null; }
function publicSubscription(sub) { return sub ? { status: sub.status, trialEnd: sub.trial_end, periodEnd: sub.period_end, plan: PLANS[sub.plan_id] || null, entitled: Boolean(PLANS[sub.plan_id] && hasEntitlement(sub)) } : null; }
async function entitled(env, user) {
  const sub = await subscription(env, user);
  if (!hasEntitlement(sub) || !PLANS[sub.plan_id]) fail(402, 'subscription_required', 'Start your seven-day Stripe trial or renew your subscription.');
  return sub;
}
function coin(value = 'SOL') { if (!COINS.includes(value)) fail(400, 'unsupported_coin'); return value; }
function textField(value, max, pattern = null) {
  if (typeof value !== 'string' || !value.trim() || value.length > max || /[\u0000-\u001f]/.test(value) || (pattern && !pattern.test(value))) fail(400, 'invalid_field');
  return value.trim();
}
function numberField(value, min, max) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) fail(400, 'invalid_number');
  return value;
}
export function validateBot(input) {
  if (input.mode && input.mode !== 'paper') fail(409, 'live_execution_unavailable', BLOCKED);
  const venue = input.venue;
  if (!['coinbase', 'jupiter'].includes(venue)) fail(400, 'unsupported_venue');
  const leverage = numberField(input.leverage ?? 1, 1, venue === 'coinbase' ? 1 : 5);
  return { name: textField(input.name, 80), coin: coin(input.coin), strategy: textField(input.strategy, 100, /^[a-zA-Z0-9_-]+$/), venue, leverage, budget: numberField(input.budget, 1, 1000000), mode: 'paper' };
}
const OWNED_BOTS = `SELECT b.*,m.enabled AS managed_enabled,m.last_reason AS managed_reason,m.allocation_quantity AS managed_quantity,
  m.pending_intent_id AS managed_pending,g.expires_at AS managed_expiry,g.revoked_at AS managed_revoked
  FROM bots b LEFT JOIN managed_bots m ON m.bot_id=b.id AND m.user_id=b.user_id LEFT JOIN agent_grants g ON g.id=m.grant_id WHERE b.user_id=?`;
function publicBot(bot, env) {
  const { user_id,managed_enabled,managed_reason,managed_quantity,managed_pending,managed_expiry,managed_revoked,...definition }=bot;
  const enabled=managed_enabled===1&&managed_revoked===null&&managed_expiry>now();
  return { ...definition, executionReady:enabled&&executionAvailable(env, 'coinbase'),
    automation:managed_enabled===undefined||managed_enabled===null?null:{enabled,reason:managed_reason,allocationQuantity:managed_quantity,pendingIntentId:managed_pending,authorizationExpiresAt:managed_expiry},
    blockedReason:enabled?'Automation is authorized. Fresh signal, venue and inventory checks still apply.':BLOCKED };
}

async function challenge(request, env) {
  const input = await bodyJSON(request);
  const wallet = textField(input.wallet, 44, /^[1-9A-HJ-NP-Za-km-z]{32,44}$/);
  if (base58Decode(wallet).length !== 32) fail(400, 'invalid_wallet');
  const at = now();
  const ip = await hash(`${request.headers.get('CF-Connecting-IP') || 'local'}:${originOf(request, env)}`);
  // Count challenges even after use: consumed rows stay until cleanup to retain this rate limit.
  const id = crypto.randomUUID();
  const origin = originOf(request, env);
  const message = `${new URL(origin).host} wants you to sign in with your Solana account:\n${wallet}\n\nSign in to Oraclebot. This signature does not authorize transactions or access to funds.\n\nURI: ${origin}\nVersion: 1\nChain ID: solana:mainnet\nNonce: ${id.replaceAll('-', '')}\nIssued At: ${new Date(at * 1000).toISOString()}\nExpiration Time: ${new Date((at + 300) * 1000).toISOString()}`;
  const inserted = await query(env, 'INSERT INTO challenges (id,wallet,message,origin,ip_hash,created_at,expires_at) SELECT ?,?,?,?,?,?,? WHERE (SELECT COUNT(*) FROM challenges WHERE (ip_hash = ? OR wallet = ?) AND created_at > ?) < 20', id, wallet, message, origin, ip, at, at + 300, ip, wallet, at - 300).run();
  if (inserted.meta.changes !== 1) fail(429, 'rate_limited');
  return json({ id, message, expiresAt: at + 300 });
}
async function verify(request, env) {
  const input = await bodyJSON(request);
  const id = textField(input.id, 36, /^[a-f0-9-]{36}$/);
  const signature = textField(input.signature, 100, /^[A-Za-z0-9+/]+={0,2}$/);
  let bytes;
  try { bytes = Uint8Array.from(atob(signature), v => v.charCodeAt(0)); } catch { fail(400, 'invalid_signature'); }
  if (bytes.length !== 64) fail(400, 'invalid_signature');
  // The atomic update permits exactly one verifier, including concurrent requests.
  const challenge = await query(env, 'UPDATE challenges SET expires_at = 0 WHERE id = ? AND expires_at > ? AND origin = ? RETURNING *', id, now(), originOf(request, env)).first();
  if (!challenge) fail(401, 'challenge_expired_or_used');
  const key = await crypto.subtle.importKey('raw', base58Decode(challenge.wallet), { name: 'Ed25519' }, false, ['verify']);
  if (!await crypto.subtle.verify('Ed25519', key, bytes, enc.encode(challenge.message))) fail(401, 'invalid_signature');
  // Deletion can record a used trial while verification is in flight. Read that
  // history inside the insert and only ever raise an existing account's flag.
  await query(env, 'INSERT INTO users (id,wallet,created_at,trial_used) VALUES (?,?,?,EXISTS (SELECT 1 FROM trial_history WHERE wallet_hash = ?)) ON CONFLICT(wallet) DO UPDATE SET trial_used = MAX(users.trial_used,excluded.trial_used)', crypto.randomUUID(), challenge.wallet, now(), await hash(challenge.wallet)).run();
  const user = await query(env, 'SELECT * FROM users WHERE wallet = ?', challenge.wallet).first();
  const token = bytesToBase64(crypto.getRandomValues(new Uint8Array(32))).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
  await query(env, 'INSERT INTO sessions (token_hash,user_id,expires_at) VALUES (?,?,?)', await hash(token), user.id, now() + SESSION_SECONDS).run();
  return json({ user: publicUser(user), subscription: publicSubscription(await subscription(env, user)) }, 200, { 'Set-Cookie': cookie(token) });
}

function prices(env) {
  const configured = { starter: env.STRIPE_STARTER_PRICE_ID, advanced: env.STRIPE_ADVANCED_PRICE_ID, unlimited: env.STRIPE_UNLIMITED_PRICE_ID };
  const values = Object.values(configured);
  return values.every(value => typeof value === 'string' && /^price_[A-Za-z0-9_]+$/.test(value)) && new Set(values).size === 3 ? configured : null;
}
function billingConfigured(env) { return Boolean(env.STRIPE_SECRET_KEY && prices(env) && env.STRIPE_WEBHOOK_SECRET); }
function checkoutEnabled(env) { return env.BILLING_LAUNCH_ENABLED === 'true' && billingConfigured(env) && /^bpc_[A-Za-z0-9]+$/.test(env.STRIPE_PORTAL_CONFIGURATION_ID || ''); }
function requireEngine(env) {
  if (!engineConfigured(env)) fail(503, 'engine_unavailable', 'The canonical research engine has not been connected. No forecast or backtest result is fabricated.');
  if (typeof env.ENGINE_SERVICE?.fetch === 'function') return new URL('https://analysis.internal');
  let base;
  try { base = new URL(env.ENGINE_URL); } catch { fail(503, 'engine_unavailable'); }
  if (base.protocol !== 'https:' || base.username || base.password || base.search || base.hash) fail(503, 'engine_unavailable');
  return base;
}
function engineConfigured(env) { return Boolean(env.ENGINE_TOKEN && (typeof env.ENGINE_SERVICE?.fetch === 'function' || env.ENGINE_URL)); }
async function usage(env, user, sub) {
  if (!user) return null;
  const at = now(); const day = utcDay(at);
  const bots = await query(env, "SELECT COUNT(*) AS n FROM bots WHERE user_id = ? AND status NOT IN ('paused','archived')", user.id).first();
  const tests = await query(env, "SELECT COALESCE(SUM(CASE WHEN state = 'complete' AND day = ? THEN 1 ELSE 0 END),0) AS completed,COALESCE(SUM(CASE WHEN state = 'reserved' AND expires_at > ? THEN 1 ELSE 0 END),0) AS reserved FROM backtest_usage WHERE user_id = ?", day, at, user.id).first();
  return { day, resetsAt: (Math.floor(at / 86400) + 1) * 86400, bots: bots.n, backtests: tests.completed, reservedBacktests: tests.reserved, concurrentBacktests: BACKTEST_CONCURRENCY, policy: PLANS[sub?.plan_id] || null };
}
async function reserveBacktest(env, user, plan, durable = false) {
  const at = now(); const id = crypto.randomUUID(); const day = utcDay(at);
  // One conditional INSERT reserves both quota and compute capacity. A separate
  // read followed by a write would admit concurrent requests past the last slot.
  const inserted = await query(env, "INSERT INTO backtest_usage (id,user_id,day,state,created_at,expires_at) SELECT ?,?,?,'reserved',?,? WHERE (? IS NULL OR (SELECT COUNT(*) FROM backtest_usage WHERE user_id = ? AND day = ? AND (state = 'complete' OR (state = 'reserved' AND expires_at > ?))) < ?) AND (SELECT COUNT(*) FROM backtest_usage WHERE user_id = ? AND state = 'reserved' AND expires_at > ?) < ? AND EXISTS (SELECT 1 FROM users WHERE id=? AND deletion_token IS NULL) AND EXISTS (SELECT 1 FROM subscriptions WHERE user_id = ? AND plan_id = ? AND ((status = 'active' AND period_end > ?) OR (status = 'trialing' AND trial_end > ?)))", id, user.id, day, at, at + (durable ? 36500 * 86400 : RESERVATION_SECONDS), plan.backtestsPerDay, user.id, day, at, plan.backtestsPerDay, user.id, at, BACKTEST_CONCURRENCY, user.id, user.id, plan.id, at, at).run();
  if (inserted.meta.changes !== 1) {
    if ((await entitled(env, user)).plan_id !== plan.id) fail(409, 'subscription_changed', 'Your membership changed. Reload your account before trying again.');
    const current = await usage(env, user, { plan_id: plan.id });
    if (plan.backtestsPerDay !== null && current.backtests + current.reservedBacktests >= plan.backtestsPerDay) fail(429, 'backtest_daily_limit', 'Your daily backtest allowance is used. It resets at 00:00 UTC.');
    fail(429, 'backtest_in_progress', 'One backtest may run at a time per account. Wait for the current request to finish.');
  }
  return id;
}
async function stripe(env, path, fields = null, idempotencyKey = null) {
  if (!env.STRIPE_SECRET_KEY) fail(503, 'billing_unavailable', 'Stripe billing is not configured yet.');
  return observeUpstream(stripeOperation(path), async recordStatus => {
    const response = await fetch(`https://api.stripe.com/v1/${path}`, {
      method: fields ? 'POST' : 'GET',
      headers: { Authorization: `Bearer ${env.STRIPE_SECRET_KEY}`, 'Stripe-Version': '2026-10-28.endive', ...(fields ? { 'Content-Type': 'application/x-www-form-urlencoded' } : {}), ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}) },
      body: fields ? new URLSearchParams(fields) : undefined,
      signal: AbortSignal.timeout(10000),
      redirect: 'manual',
    });
    recordStatus(response.status);
    if (!response.ok) fail(502, 'billing_provider_error', 'Stripe could not complete this request. No access was granted.');
    try { return JSON.parse(await boundedText(response, 256000)); } catch (error) { if (error instanceof ApiError) throw error; fail(502, 'billing_provider_error'); }
  });
}
async function checkout(request, env, user) {
  if (!checkoutEnabled(env)) fail(503, 'billing_unavailable', 'Membership checkout is not available yet.');
  const input = await bodyJSON(request);
  if (typeof input.plan !== 'string' || !Object.hasOwn(PLANS, input.plan) || Object.keys(input).some(key => key !== 'plan')) fail(400, 'invalid_plan', 'Choose a supported membership plan.');
  const plan = PLANS[input.plan];
  if (hasEntitlement(await subscription(env, user))) fail(409, 'already_subscribed', 'Manage your existing subscription in the billing portal.');
  const claim = await query(env, 'UPDATE users SET checkout_pending_at = ? WHERE id = ? AND deletion_token IS NULL AND (checkout_pending_at IS NULL OR checkout_pending_at < ?) RETURNING id,checkout_pending_at', now(), user.id, now() - CHECKOUT_SECONDS).first();
  if (!claim) fail(409, 'checkout_pending', 'A Checkout session is already pending. Finish that session or wait until its 35-minute expiration.');
  let customer = user.stripe_customer_id;
  if (!customer) {
    const created = await stripe(env, 'customers', { 'metadata[oraclebot_user]': user.id }, `customer-${user.id}`);
    customer = created.id;
    await query(env, 'UPDATE users SET stripe_customer_id = ? WHERE id = ?', customer, user.id).run();
  }
  const prior = await stripe(env, `subscriptions?customer=${encodeURIComponent(customer)}&status=all&limit=100`);
  if (!Array.isArray(prior.data) || prior.has_more) fail(502, 'subscription_history_unavailable');
  if (prior.data.some(s => ['active', 'trialing', 'past_due', 'unpaid', 'incomplete', 'paused'].includes(s.status))) fail(409, 'existing_subscription', 'Manage your existing subscription in the billing portal.');
  const trialAllowed = !user.trial_used && !prior.data.some(s => s.trial_start || s.trial_end);
  const origin = originOf(request, env);
  const fields = { mode: 'subscription', customer, expires_at: String(claim.checkout_pending_at + CHECKOUT_SECONDS), 'line_items[0][price]': prices(env)[plan.id], 'line_items[0][quantity]': '1', success_url: `${origin}/?billing=success#settings`, cancel_url: `${origin}/?billing=cancelled#pricing`, client_reference_id: user.id, 'subscription_data[metadata][oraclebot_user]': user.id, 'metadata[oraclebot_user]': user.id };
  if (trialAllowed) fields['subscription_data[trial_period_days]'] = '7';
  const session = await stripe(env, 'checkout/sessions', fields, `checkout-${user.id}-${claim.checkout_pending_at}`);
  if (typeof session.url !== 'string' || new URL(session.url).origin !== 'https://checkout.stripe.com') fail(502, 'invalid_checkout_url');
  return json({ url: session.url, trialDays: trialAllowed ? 7 : 0, plan: plan.id });
}
export async function verifyStripeSignature(raw, header, secret, at = now()) {
  if (!secret || typeof header !== 'string') return false;
  const parts = header.split(',').map(p => p.split('='));
  const timestamp = parts.find(([key]) => key === 't')?.[1];
  if (!/^\d+$/.test(timestamp || '') || Math.abs(at - Number(timestamp)) > 300) return false;
  const key = await crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['verify']);
  for (const [name, hex] of parts) {
    if (name !== 'v1' || !/^[a-f0-9]{64}$/.test(hex || '')) continue;
    const bytes = Uint8Array.from(hex.match(/../g), value => parseInt(value, 16));
    if (await crypto.subtle.verify('HMAC', key, bytes, enc.encode(`${timestamp}.${raw}`))) return true;
  }
  return false;
}
async function acquireWebhookLease(env, subscriptionId) {
  const key = await hash(subscriptionId); const owner = crypto.randomUUID();
  // SQLite time is evaluated when D1 executes the statement. Request time may be
  // stale after network or scheduling delays and cannot safely fence a writer.
  const lease = await query(env, 'INSERT INTO subscription_webhook_leases (subscription_key,owner_token,expires_at) VALUES (?,?,unixepoch()+?) ON CONFLICT(subscription_key) DO UPDATE SET owner_token=excluded.owner_token,expires_at=excluded.expires_at WHERE subscription_webhook_leases.expires_at <= unixepoch() RETURNING owner_token', key, owner, WEBHOOK_LEASE_SECONDS).first();
  if (!lease || lease.owner_token !== owner) fail(503, 'webhook_busy');
  return { key, owner };
}
function webhookFence(lease) {
  return lease ? { sql: 'EXISTS (SELECT 1 FROM subscription_webhook_leases WHERE subscription_key = ? AND owner_token = ? AND expires_at > unixepoch())', args: [lease.key, lease.owner] } : { sql: '1', args: [] };
}
function webhookReceipt(env, event, fence) {
  return query(env, `INSERT OR IGNORE INTO stripe_events (id,handled_at) SELECT ?,? WHERE ${fence.sql} RETURNING id`, event.id, now(), ...fence.args);
}
async function webhook(request, env) {
  requireDB(env);
  if (!billingConfigured(env)) fail(503, 'billing_unavailable');
  const raw = await boundedText(request, 256000);
  if (!await verifyStripeSignature(raw, request.headers.get('Stripe-Signature'), env.STRIPE_WEBHOOK_SECRET)) fail(400, 'invalid_webhook_signature');
  let event;
  try { event = JSON.parse(raw); } catch { fail(400, 'invalid_json'); }
  if (!event.id || typeof event.type !== 'string') fail(400, 'invalid_webhook');
  if (await query(env, 'SELECT id FROM stripe_events WHERE id = ?', event.id).first()) return json({ received: true, duplicate: true });
  const object = event.data?.object;
  const subscriptionId = event.type.startsWith('customer.subscription.') ? object?.id : event.type === 'checkout.session.completed' ? object?.subscription : null;
  if (typeof subscriptionId === 'string' && /^sub_[A-Za-z0-9]+$/.test(subscriptionId)) {
    // Cancellation can pass an in-flight plan update. The terminal-state guard
    // below prevents that older update from restoring canceled access.
    const lease = event.type === 'customer.subscription.deleted' ? null : await acquireWebhookLease(env, subscriptionId);
    try {
      const fence = webhookFence(lease);
      const current = await stripe(env, `subscriptions/${encodeURIComponent(subscriptionId)}`);
      if (current?.id !== subscriptionId) fail(502, 'billing_provider_error');
      const user = await query(env, 'SELECT * FROM users WHERE stripe_customer_id = ?', current.customer).first();
      if (user && current.metadata?.oraclebot_user === user.id) {
        const planId = current.items?.data?.length === 1 && current.items.has_more !== true && current.items.data[0].quantity === 1 ? Object.entries(prices(env)).find(([, price]) => price === current.items.data[0].price?.id)?.[0] || null : null;
        const planMatches = Boolean(planId);
        const terminal = ['canceled', 'incomplete_expired'].includes(current.status);
        const status = terminal || planMatches ? String(current.status) : 'plan_mismatch';
        const periodEnd = Number(current.items?.data?.[0]?.current_period_end ?? current.current_period_end ?? 0);
        const trialEnd = Number(current.trial_end || 0);
        const written = await requireDB(env).batch([
          query(env, `INSERT INTO subscriptions (user_id,stripe_subscription_id,status,period_end,trial_end,stripe_created,event_created,updated_at,plan_id) SELECT ?,?,?,?,?,?,?,?,? WHERE ${fence.sql} ON CONFLICT(user_id) DO UPDATE SET stripe_subscription_id=excluded.stripe_subscription_id,status=excluded.status,plan_id=excluded.plan_id,period_end=excluded.period_end,trial_end=excluded.trial_end,stripe_created=excluded.stripe_created,event_created=excluded.event_created,updated_at=excluded.updated_at WHERE (excluded.stripe_created > subscriptions.stripe_created OR (excluded.stripe_subscription_id = subscriptions.stripe_subscription_id AND excluded.event_created >= subscriptions.event_created)) AND NOT (excluded.stripe_subscription_id = subscriptions.stripe_subscription_id AND subscriptions.status IN (\'canceled\',\'incomplete_expired\') AND excluded.status NOT IN (\'canceled\',\'incomplete_expired\'))`, user.id, current.id, status, periodEnd, trialEnd, Number(current.created || 0), Number(event.created || 0), now(), planId, ...fence.args),
          // Only completion of this exact checkout unlocks it. A delayed event
          // about an earlier subscription must not unlock a newer payable session.
          query(env, `UPDATE users SET trial_used = MAX(trial_used, ?), checkout_pending_at = CASE WHEN ? = checkout_pending_at + ? THEN NULL ELSE checkout_pending_at END WHERE id = ? AND ${fence.sql}`, current.trial_start || current.trial_end ? 1 : 0, event.type === 'checkout.session.completed' && object.customer === current.customer && object.metadata?.oraclebot_user === user.id ? Number(object.expires_at || 0) : -1, CHECKOUT_SECONDS, user.id, ...fence.args),
          webhookReceipt(env, event, fence),
        ]);
        if (lease && written.at(-1).results?.length !== 1) fail(503, 'webhook_lease_lost');
        return json({ received: true });
      }
      const receipt = await webhookReceipt(env, event, fence).run();
      if (lease && receipt.results?.length !== 1) fail(503, 'webhook_lease_lost');
      return json({ received: true });
    } finally {
      if (lease) await query(env, 'DELETE FROM subscription_webhook_leases WHERE subscription_key = ? AND owner_token = ?', lease.key, lease.owner).run();
    }
  }
  await webhookReceipt(env, event, webhookFence(null)).run();
  return json({ received: true });
}

async function engineValue(env, path, payload = null) {
  const base = requireEngine(env);
  return observeUpstream(engineOperation(path), async recordStatus => {
    const options = { method: payload ? 'POST' : 'GET', headers: { Authorization: `Bearer ${env.ENGINE_TOKEN}`, ...(payload ? { 'Content-Type': 'application/json' } : {}) }, body: payload ? JSON.stringify(payload) : undefined, signal: AbortSignal.timeout(20000), redirect: 'manual' };
    const response = typeof env.ENGINE_SERVICE?.fetch === 'function'
      ? await env.ENGINE_SERVICE.fetch(new Request(new URL(path, base), options)) : await fetch(new URL(path, base), options);
    recordStatus(response.status);
    let value;
    try { value = JSON.parse(await boundedText(response, 2000000)); } catch (error) { if (error instanceof ApiError) throw error; fail(502, 'engine_invalid_response'); }
    if (!response.ok) fail(response.status === 400 ? 400 : 503, 'engine_unavailable', 'The research engine could not complete this request.');
    if (!value || typeof value !== 'object' || Array.isArray(value)) fail(502, 'engine_invalid_response');
    if (path === '/v1/backtests' && (value.status !== 'complete' || !value.metrics || typeof value.metrics !== 'object' || Array.isArray(value.metrics))) fail(502, 'engine_invalid_response');
    return value;
  });
}
async function engine(env, path, payload = null) { return json(await engineValue(env, path, payload)); }
function normalizeBacktest(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input) || Object.keys(input).some(k => !['coin', 'strategy', 'interval', 'capital', 'leverage'].includes(k))) fail(400, 'invalid_backtest_request');
  const payload = { coin: coin(input.coin), strategy: textField(input.strategy, 100, /^[a-zA-Z0-9_-]+$/), interval: input.interval || '1h', capital: numberField(input.capital ?? 10000, 1, 1000000), leverage: numberField(input.leverage ?? 1, 1, 5) };
  if (!['1m', '5m', '15m', '1h', '6h', '1d'].includes(payload.interval)) fail(400, 'unsupported_interval');
  return payload;
}
function jobServices(env) {
  return { normalize: normalizeBacktest, entitled: user => entitled(env, user),
    reserve: (user, sub, durable) => reserveBacktest(env, user, PLANS[sub.plan_id], durable),
    engine: (path, payload) => engineValue(env, path, payload) };
}
async function billingServices(env) {
  const service = { stripe: (path, fields = null, key = null) => stripe(env, path, fields, key) };
  if (env.BILLING_TEST_CLOCK_ID) {
    // Provider clock time is available only on an explicitly isolated sandbox.
    // Browser input never controls a production clock or a proration date.
    if (env.BILLING_TEST_MODE !== 'true' || !/^(sk|rk)_test_/.test(env.STRIPE_SECRET_KEY || '') ||
        !/^clock_[A-Za-z0-9]+$/.test(env.BILLING_TEST_CLOCK_ID) || !env.APP_ORIGIN || ['oraclebot.io', 'www.oraclebot.io'].includes(new URL(env.APP_ORIGIN).hostname)) fail(503, 'test_clock_configuration_invalid');
    const clock = await stripe(env, `test_helpers/test_clocks/${env.BILLING_TEST_CLOCK_ID}`);
    if (clock.id !== env.BILLING_TEST_CLOCK_ID || clock.status !== 'ready' || !Number.isSafeInteger(clock.frozen_time) || clock.frozen_time <= 0 || clock.livemode === true) fail(503, 'test_clock_not_ready');
    service.now = () => clock.frozen_time;
  }
  return service;
}
function connectionsConfigured(env) { return typeof env.USER_TRADE_EXECUTOR?.fetch === 'function' && typeof env.EXECUTOR_TOKEN === 'string' && env.EXECUTOR_TOKEN.length >= 32; }
async function executionRequest(env, path, user, input = null) {
  if (!connectionsConfigured(env)) fail(503, 'execution_unavailable', 'Customer account connections are not configured.');
  const payload = path === '/health' ? null : { userId: user.id, wallet: user.wallet, ...input };
  const response = await env.USER_TRADE_EXECUTOR.fetch(new Request(`https://customer-trade.internal${path}`, {
    method: payload ? 'POST' : 'GET', headers: { Authorization: `Bearer ${env.EXECUTOR_TOKEN}`, ...(payload ? { 'Content-Type': 'application/json' } : {}) },
    body: payload ? JSON.stringify(payload) : undefined, signal: AbortSignal.timeout(15000), redirect: 'manual',
  }));
  let value;
  try { value = JSON.parse(await boundedText(response, 65536)); } catch { fail(502, 'execution_response_unverified'); }
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(502, 'execution_response_unverified');
  if (!response.ok) fail([400, 401, 403, 404, 409, 429, 503].includes(response.status) ? response.status : 503,
    typeof value.error === 'string' && /^[a-z0-9_]{1,80}$/.test(value.error) ? value.error : 'execution_unavailable', 'The customer connection could not complete this request. No execution is assumed.');
  return value;
}
async function agentStatus(env, user) {
  const sub = await subscription(env, user);
  const rows = await query(env, `${OWNED_BOTS} ORDER BY b.created_at DESC,b.id DESC LIMIT 101`, user.id).all();
  return { user: publicUser(user), subscription: publicSubscription(sub), usage: await usage(env, user, sub),
    bots: rows.results.slice(0, 100).map(row=>publicBot(row,env)), moreBotsAvailable: rows.results.length > 100,
    engineConfigured: engineConfigured(env), configurationsExecute:rows.results.some(row=>publicBot(row,env).executionReady) };
}
function managedServices(request, env) {
  return { origin: request ? originOf(request, env) : env.APP_ORIGIN,
    requireEntitlement: user => entitled(env, user), botLimit: sub => PLANS[sub.plan_id].botLimit,
    strategies: () => engineValue(env, '/v1/strategies'), signal: input => engineValue(env, '/v1/signals', input) };
}
async function route(request, env) {
  const url = new URL(request.url);
  if (env.APP_ORIGIN) {
    const canonical = new URL(env.APP_ORIGIN);
    if (url.hostname === `www.${canonical.hostname}`) {
      canonical.pathname = url.pathname; canonical.search = url.search;
      return Response.redirect(canonical.toString(), 308);
    }
  }
  const path = url.pathname;
  // Protocol routes must run before the single-page asset fallback. They use
  // bearer/PKCE authority, while cookie-based consent keeps its own CSRF gate.
  if (path === '/mcp' || path.startsWith('/oauth/') || path.startsWith('/.well-known/') || path.startsWith('/api/agent/')) {
    originOf(request, env);
    const oauth = await handleOAuth(request, env, { account, json, bodyJSON, fail, sameOrigin });
    if (oauth) return oauth;
    if (path === '/mcp') return handleMcp(request, env, { authenticateAgent, getStatus: user => agentStatus(env, user), requireEntitlement: user => entitled(env, user) });
    fail(404, 'endpoint_not_found');
  }
  if (!path.startsWith('/api/')) return env.ASSETS ? env.ASSETS.fetch(request) : new Response('Not found', { status: 404 });
  originOf(request, env);
  if (request.method !== 'GET' && request.method !== 'HEAD' && path !== '/api/billing/webhook') sameOrigin(request, env);
  if (path === '/api/health' && request.method === 'GET') return json({ status: env.DB ? 'ok' : 'setup_required', version: env.APP_VERSION || '1.0.0', storage: Boolean(env.DB), engine: engineConfigured(env), billing: checkoutEnabled(env), liveExecution: executionAvailable(env), mcp: { protocolVersion: MCP_PROTOCOL_VERSION, authentication: 'oauth-pkce', executionAdapterConfigured: executionAvailable(env) } });
  if (path === '/api/config' && request.method === 'GET') return json({ coins: COINS, trialDays: 7, billingConfigured: checkoutEnabled(env), plans: Object.values(PLANS), botSlotStatuses: ['configured'], concurrentBacktests: BACKTEST_CONCURRENCY, engineConfigured: engineConfigured(env), durableBacktests: Boolean(typeof env.ENGINE_SERVICE?.fetch === 'function'), customerConnectionsConfigured: connectionsConfigured(env), managedAutomationConfigured: executionAvailable(env, 'coinbase') && engineConfigured(env), billingPlanChanges: billingConfigured(env), liveExecution: executionAvailable(env), walletNetwork: 'solana:mainnet', mcp: { endpoint: `${originOf(request, env)}/mcp`, protocolVersion: MCP_PROTOCOL_VERSION, authorizationMode: 'preauthorized', executionAdapterConfigured: executionAvailable(env) } });
  if (path === '/api/auth/challenge' && request.method === 'POST') return challenge(request, env);
  if (path === '/api/auth/verify' && request.method === 'POST') return verify(request, env);
  if (path === '/api/me' && request.method === 'GET') {
    const user = env.DB ? await account(request, env, false) : null;
    const sub = await subscription(env, user);
    return json({ user: publicUser(user), subscription: publicSubscription(sub), usage: await usage(env, user, sub), portalAvailable: Boolean(user?.stripe_customer_id && env.STRIPE_SECRET_KEY && /^bpc_[A-Za-z0-9]+$/.test(env.STRIPE_PORTAL_CONFIGURATION_ID || '')) });
  }
  if (path === '/api/auth/logout' && request.method === 'POST') {
    if (request.headers.has('X-Oraclebot-Account')) await account(request, env);
    const token = sessionToken(request);
    if (token) await query(env, 'DELETE FROM sessions WHERE token_hash = ?', await hash(token)).run();
    return json({ ok: true }, 200, { 'Set-Cookie': cookie('', 0) });
  }
  if (path === '/api/billing/webhook' && request.method === 'POST') return webhook(request, env);
  if (path === '/api/oracle' && request.method === 'GET') return engine(env, `/v1/oracle?coin=${coin(url.searchParams.get('coin') || 'SOL')}`);
  if (path === '/api/strategies' && request.method === 'GET') return engine(env, '/v1/strategies');
  if (path === '/api/runtime' && request.method === 'GET') return engine(env, '/health');
  const user = await account(request, env);
  if (path === '/api/execution' && request.method === 'GET') return json(await executionRequest(env, '/health', user));
  if (path === '/api/connections' && request.method === 'GET') {
    const cursor = url.searchParams.get('cursor');
    if (cursor !== null && (cursor.length > 4096 || !/^[A-Za-z0-9_-]+$/.test(cursor))) fail(400, 'invalid_cursor');
    return json(await executionRequest(env, '/v1/connections/list', user, cursor ? { cursor } : null));
  }
  if (path === '/api/connections' && request.method === 'POST') {
    const input = await bodyJSON(request);
    if (Object.keys(input).some(key => !['venue', 'apiKeyName', 'privateKey', 'portfolioId', 'idempotencyKey'].includes(key))) fail(400, 'invalid_connection');
    if (!connectionsConfigured(env)) fail(503, 'execution_unavailable');
    await markExecutionInitialized(env, user);
    return json(await executionRequest(env, '/v1/connections', user, { input }), 201);
  }
  if (/^\/api\/connections\/[a-f0-9-]{36}\/revoke$/.test(path) && request.method === 'POST') {
    if (Object.keys(await bodyJSON(request)).length) fail(400, 'invalid_connection_action');
    return json(await executionRequest(env, '/v1/connections/revoke', user, { id: path.split('/').at(-2) }));
  }
  if (path === '/api/me' && request.method === 'DELETE') {
    if (await query(env, "SELECT id FROM billing_lifecycle_operations WHERE user_id=? AND state IN ('committing','unknown','pending_payment') LIMIT 1", user.id).first()) fail(409, 'billing_reconciliation_required', 'A billing change is unresolved. Reconcile it before deleting your account.');
    if (await query(env, "SELECT id FROM agent_trade_intents WHERE user_id = ? AND state IN ('submitting','submitted','unknown') LIMIT 1", user.id).first()) fail(409, 'trade_reconciliation_required', 'A submitted or unresolved trade must be reconciled before account deletion.');
    if (user.checkout_pending_at && user.checkout_pending_at >= now() - CHECKOUT_SECONDS) fail(409, 'checkout_pending', 'Finish the pending Checkout session or wait until its 35-minute expiration before deleting your account.');
    const sub = await subscription(env, user);
    let usedTrial = Boolean(user.trial_used);
    if (sub && !['canceled', 'incomplete_expired'].includes(sub.status)) fail(409, 'cancel_subscription_first', 'Cancel your subscription in the billing portal before deleting your account. Deletion is available after cancellation takes effect.');
    if (user.stripe_customer_id) {
      const prior = await stripe(env, `subscriptions?customer=${encodeURIComponent(user.stripe_customer_id)}&status=all&limit=100`);
      if (!Array.isArray(prior.data) || prior.has_more) fail(502, 'subscription_history_unavailable');
      if (prior.data.some(s => !['canceled', 'incomplete_expired'].includes(s.status))) fail(409, 'cancel_subscription_first');
      usedTrial ||= prior.data.some(s => s.trial_start || s.trial_end);
    }
    const deletion = await beginAccountDeletion(env, user, { checkoutSeconds: CHECKOUT_SECONDS });
    await cleanupAccountExecution(env, user, deletion, { configured: connectionsConfigured(env), revokeAll: owner => executionRequest(env, '/v1/connections/revoke-all', owner) });
    const fence = deletionFencePredicate(deletion);
    const deleted = await requireDB(env).batch([
      // Capture current trial use before a cascade removes the account. Retaining
      // this fact is safe even when a concurrent subscription blocks deletion.
      query(env, 'INSERT OR IGNORE INTO trial_history (wallet_hash,used_at) SELECT ?,? WHERE ? = 1 OR EXISTS (SELECT 1 FROM users WHERE id = ? AND trial_used = 1)', await hash(user.wallet), now(), usedTrial ? 1 : 0, user.id),
      query(env, `DELETE FROM users WHERE id = ? AND ${fence.sql} AND (checkout_pending_at IS NULL OR checkout_pending_at < ?) AND NOT EXISTS (SELECT 1 FROM billing_lifecycle_operations WHERE user_id=users.id AND state IN ('committing','unknown','pending_payment')) AND NOT EXISTS (SELECT 1 FROM agent_trade_intents WHERE user_id = users.id AND state IN ('submitting','submitted','unknown')) AND NOT EXISTS (SELECT 1 FROM subscriptions WHERE user_id = users.id AND COALESCE(status,'unknown') NOT IN ('canceled','incomplete_expired')) RETURNING id`, user.id, ...fence.args, now() - CHECKOUT_SECONDS),
      query(env, 'DELETE FROM challenges WHERE wallet = ? AND NOT EXISTS (SELECT id FROM users WHERE id = ?)', user.wallet, user.id),
    ]);
    if (deleted[1].results?.length !== 1 || deleted[1].results[0].id !== user.id) {
      if (await query(env, "SELECT id FROM billing_lifecycle_operations WHERE user_id=? AND state IN ('committing','unknown','pending_payment') LIMIT 1", user.id).first()) fail(409, 'billing_reconciliation_required', 'A billing operation began while deletion was being checked. Reconcile it first.');
      if (await query(env, "SELECT id FROM agent_trade_intents WHERE user_id = ? AND state IN ('submitting','submitted','unknown') LIMIT 1", user.id).first()) fail(409, 'trade_reconciliation_required', 'A trade began while deletion was being checked. Reconcile it before deleting your account.');
      const currentSub = await subscription(env, user);
      if (currentSub && !['canceled', 'incomplete_expired'].includes(currentSub.status)) fail(409, 'cancel_subscription_first', 'Your subscription changed while deletion was being checked. Cancel it before deleting your account.');
      fail(409, 'checkout_pending', 'A Checkout session began while deletion was being checked. Finish it or wait until its expiration.');
    }
    diagnostic('info', { event: 'oraclebot.account_deleted' });
    return json({ deleted: true }, 200, { 'Set-Cookie': cookie('', 0) });
  }
  if (path === '/api/billing/checkout' && request.method === 'POST') return checkout(request, env, user);
  if (path === '/api/billing/plan-change/quote' && request.method === 'POST') return json(await preparePlanChange(env, user, await bodyJSON(request), await billingServices(env)));
  if (path === '/api/billing/plan-change/commit' && request.method === 'POST') return json(await commitPlanChange(env, user, await bodyJSON(request), await billingServices(env)));
  if (path === '/api/billing/plan-changes' && request.method === 'GET') return json(await listPlanChanges(env, user));
  if (/^\/api\/billing\/plan-changes\/[a-f0-9-]{36}$/.test(path) && request.method === 'GET') return json(await getPlanChange(env, user, path.split('/').at(-1), await billingServices(env)));
  if (/^\/api\/billing\/plan-changes\/[a-f0-9-]{36}\/cancel$/.test(path) && request.method === 'POST') {
    const input = await bodyJSON(request);
    if (Object.keys(input).some(key => key !== 'idempotencyKey')) fail(400, 'invalid_plan_change');
    return json(await cancelPlanChange(env, user, { changeId: path.split('/').at(-2), idempotencyKey: input.idempotencyKey }, await billingServices(env)));
  }
  if (path === '/api/billing/cancellation' && request.method === 'POST') return json(await setPeriodEndCancellation(env, user, await bodyJSON(request), await billingServices(env)));
  if (path === '/api/billing/portal' && request.method === 'POST') {
    if (!user.stripe_customer_id) fail(409, 'no_subscription');
    if (!/^bpc_[A-Za-z0-9]+$/.test(env.STRIPE_PORTAL_CONFIGURATION_ID || '')) fail(503, 'billing_unavailable', 'The billing portal is not configured.');
    const portal = await stripe(env, 'billing_portal/sessions', { customer: user.stripe_customer_id, configuration: env.STRIPE_PORTAL_CONFIGURATION_ID, return_url: `${originOf(request, env)}/#settings` });
    if (typeof portal.url !== 'string' || new URL(portal.url).origin !== 'https://billing.stripe.com') fail(502, 'invalid_portal_url');
    return json({ url: portal.url });
  }
  if (path === '/api/bots' && request.method === 'GET') {
    // Active and paused configurations remain discoverable before archived history.
    const page = Number(url.searchParams.get('page') || 0);
    if (!Number.isSafeInteger(page) || page < 0 || !Number.isSafeInteger(page * 100)) fail(400, 'invalid_page');
    const rows = await query(env, `${OWNED_BOTS} ORDER BY CASE WHEN b.status='archived' THEN 1 ELSE 0 END,b.created_at DESC,b.id DESC LIMIT 101 OFFSET ?`, user.id, page * 100).all();
    return json({ bots: rows.results.slice(0, 100).map(row=>publicBot(row,env)), nextPage: rows.results.length > 100 ? page + 1 : null });
  }
  if (path === '/api/bots' && request.method === 'POST') {
    const sub = await entitled(env, user);
    const plan = PLANS[sub.plan_id];
    const bot = validateBot(await bodyJSON(request));
    const id = crypto.randomUUID();
    // The quota and insertion share one D1 statement so concurrent requests cannot
    // both reserve the final available slot.
    const inserted = await query(env, "INSERT INTO bots (id,user_id,name,coin,strategy,venue,leverage,budget,mode,status,created_at,updated_at) SELECT ?,?,?,?,?,?,?,?,?,?,?,? WHERE (? IS NULL OR (SELECT COUNT(*) FROM bots WHERE user_id = ? AND status NOT IN ('paused','archived')) < ?) AND EXISTS (SELECT 1 FROM users WHERE id=? AND deletion_token IS NULL) AND EXISTS (SELECT 1 FROM subscriptions WHERE user_id = ? AND plan_id = ? AND ((status = 'active' AND period_end > ?) OR (status = 'trialing' AND trial_end > ?)))", id, user.id, bot.name, bot.coin, bot.strategy, bot.venue, bot.leverage, bot.budget, 'paper', 'configured', now(), now(), plan.botLimit, user.id, plan.botLimit, user.id, user.id, plan.id, now(), now()).run();
    if (inserted.meta.changes !== 1) {
      if ((await entitled(env, user)).plan_id !== plan.id) fail(409, 'subscription_changed', 'Your membership changed. Reload your account before trying again.');
      fail(409, 'bot_limit');
    }
    return json({ bot: publicBot(await query(env, 'SELECT * FROM bots WHERE id = ?', id).first(),env) }, 201);
  }
  if (/^\/api\/bots\/[a-f0-9-]{36}\/automation(?:\/challenge)?$/.test(path)) {
    const botId = path.split('/')[3];
    if (!await query(env, 'SELECT id FROM bots WHERE id=? AND user_id=?', botId, user.id).first()) fail(404, 'bot_not_found');
    if (request.method === 'GET' && path.endsWith('/automation')) return json(await managedBotStatus(env, user, botId));
    if (request.method === 'POST') {
      if (!executionAvailable(env, 'coinbase') || !engineConfigured(env)) fail(503, 'managed_execution_unavailable', 'Automated trading is not available until the hosted services complete launch verification.');
      const input = await bodyJSON(request);
      return json(path.endsWith('/challenge') ? await prepareManagedBot(env, user, botId, input, managedServices(request, env)) : await activateManagedBot(env, user, botId, input, managedServices(request, env)));
    }
    fail(405, 'method_not_allowed');
  }
  if (/^\/api\/bots\/[a-f0-9-]{36}$/.test(path) && request.method === 'PATCH') {
    const input = await bodyJSON(request);
    if (!['paused', 'archived'].includes(input.status) || Object.keys(input).some(k => k !== 'status')) fail(400, 'invalid_bot_action');
    const botId = path.split('/').at(-1);
    // Revoke and pause before exposing a stopped definition. Both writes share
    // a transaction; the private signer rereads grant revocation at admission.
    await pauseManagedBot(env, user, botId);
    const bot = await query(env, 'UPDATE bots SET status = ?,updated_at = ? WHERE id = ? AND user_id = ? RETURNING *', input.status, now(), botId, user.id).first();
    if (!bot) fail(404, 'bot_not_found');
    return json({ bot: publicBot(bot,env) });
  }
  if (path === '/api/backtest-jobs' && request.method === 'POST') {
    requireEngine(env);
    return json(await createBacktestJob(env, user, await bodyJSON(request), jobServices(env)), 202);
  }
  if (path === '/api/backtest-jobs' && request.method === 'GET') return json(await listBacktestJobs(env, user));
  if (/^\/api\/backtest-jobs\/[a-f0-9-]{36}$/.test(path) && request.method === 'GET') {
    return json(await getBacktestJob(env, user, path.split('/').at(-1), jobServices(env)));
  }
  if (path === '/api/backtests' && request.method === 'POST') {
    const sub = await entitled(env, user);
    const input = await bodyJSON(request);
    const payload = { coin: coin(input.coin), strategy: textField(input.strategy, 100, /^[a-zA-Z0-9_-]+$/), interval: input.interval || '1h', capital: numberField(input.capital ?? 10000, 1, 1000000), leverage: numberField(input.leverage ?? 1, 1, 5) };
    if (!['1m', '1h', '1d'].includes(payload.interval)) fail(400, 'unsupported_interval');
    requireEngine(env);
    const reservation = await reserveBacktest(env, user, PLANS[sub.plan_id]);
    try {
      const result = await engine(env, '/v1/backtests', payload);
      await query(env, "UPDATE backtest_usage SET state = 'complete' WHERE id = ? AND user_id = ?", reservation, user.id).run();
      return result;
    } catch (error) {
      // Validation and unavailable/failed engines never consume a daily credit.
      await query(env, "DELETE FROM backtest_usage WHERE id = ? AND user_id = ? AND state = 'reserved'", reservation, user.id).run();
      throw error;
    }
  }
  fail(404, 'endpoint_not_found');
}

export default {
  async fetch(request, env) {
    let response;
    try { response = await route(request, env); }
    catch (error) {
      const code = error instanceof ApiError || error instanceof OAuthError || error instanceof BacktestJobError || error instanceof BillingLifecycleError || error instanceof AccountLifecycleError || error instanceof ManagedBotError ? error.code : error?.name === 'TimeoutError' || error?.name === 'AbortError' ? 'upstream_timeout' : 'service_unavailable';
      if (error instanceof OAuthError) response = json({ error: error.code }, error.status, error.headers);
      else if (error instanceof ApiError || error instanceof BacktestJobError || error instanceof BillingLifecycleError || error instanceof AccountLifecycleError || error instanceof ManagedBotError) response = json({ error: error.code, message: error.message }, error.status);
      else if (code === 'upstream_timeout') response = json({ error: code, message: 'The upstream service timed out. No result or execution is assumed.' }, 504);
      else response = json({ error: code, message: 'This service is temporarily unavailable.' }, 503);
      reportFailure(request, response, code);
    }
    const result = new Response(response.body, response);
    for (const [name, value] of Object.entries(securityHeaders)) result.headers.set(name, value);
    return result;
  },
  async scheduled(event, env) {
    if (!env.DB) return;
    if (event.cron === '* * * * *') {
      if (engineConfigured(env)) await reconcileBacktestJobs(env, jobServices(env));
      if (engineConfigured(env) && executionAvailable(env, 'coinbase')) await tickManagedBots(env, managedServices(null, env));
      return;
    }
    await env.DB.batch([
      query(env, 'DELETE FROM challenges WHERE created_at < ?', now() - 3600),
      query(env, 'DELETE FROM sessions WHERE expires_at < ?', now()),
      query(env, 'DELETE FROM stripe_events WHERE handled_at < ?', now() - 90 * 86400),
      query(env, "DELETE FROM backtest_usage WHERE (job_id IS NULL AND state = 'reserved' AND expires_at < ?) OR (state = 'complete' AND day < ?) OR (job_id IS NULL AND day < ?)", now(), utcDay(now() - 86400), utcDay(now() - 86400)),
      query(env, 'DELETE FROM subscription_webhook_leases WHERE expires_at <= unixepoch()'),
      query(env, "UPDATE agent_trade_intents SET state = 'expired',updated_at = ? WHERE state IN ('preparing','prepared') AND expires_at <= ?", now(), now()),
    ]);
    await cleanupAgentAccess(env);
  },
};
