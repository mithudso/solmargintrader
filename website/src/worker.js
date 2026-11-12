import { base58Decode, bytesToBase64 } from '../../extension/src/wallet/solana.js';

export const COINS = ['SOL', 'BTC', 'ETH', 'ZEC'];
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
  return user;
}
function publicUser(user) { return user ? { id: user.id, wallet: user.wallet, createdAt: user.created_at } : null; }
export function hasEntitlement(sub, at = now()) {
  return Boolean(sub && ((sub.status === 'trialing' && sub.trial_end > at) || (sub.status === 'active' && sub.period_end > at)));
}
async function subscription(env, user) { return user ? query(env, 'SELECT * FROM subscriptions WHERE user_id = ?', user.id).first() : null; }
function publicSubscription(sub) { return sub ? { status: sub.status, trialEnd: sub.trial_end, periodEnd: sub.period_end, entitled: hasEntitlement(sub) } : null; }
async function entitled(env, user) {
  const sub = await subscription(env, user);
  if (!hasEntitlement(sub)) fail(402, 'subscription_required', 'Start your seven-day Stripe trial or renew your subscription.');
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
function publicBot(bot) { return { ...bot, user_id: undefined, executionReady: false, blockedReason: BLOCKED }; }

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
  const trial = await query(env, 'SELECT wallet_hash FROM trial_history WHERE wallet_hash = ?', await hash(challenge.wallet)).first();
  await query(env, 'INSERT INTO users (id,wallet,created_at,trial_used) VALUES (?,?,?,?) ON CONFLICT(wallet) DO NOTHING', crypto.randomUUID(), challenge.wallet, now(), trial ? 1 : 0).run();
  const user = await query(env, 'SELECT * FROM users WHERE wallet = ?', challenge.wallet).first();
  const token = bytesToBase64(crypto.getRandomValues(new Uint8Array(32))).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
  await query(env, 'INSERT INTO sessions (token_hash,user_id,expires_at) VALUES (?,?,?)', await hash(token), user.id, now() + SESSION_SECONDS).run();
  return json({ user: publicUser(user), subscription: publicSubscription(await subscription(env, user)) }, 200, { 'Set-Cookie': cookie(token) });
}

function billingConfigured(env) { return Boolean(env.STRIPE_SECRET_KEY && env.STRIPE_PRICE_ID && env.STRIPE_WEBHOOK_SECRET); }
async function stripe(env, path, fields = null, idempotencyKey = null) {
  if (!env.STRIPE_SECRET_KEY) fail(503, 'billing_unavailable', 'Stripe billing is not configured yet.');
  const response = await fetch(`https://api.stripe.com/v1/${path}`, {
    method: fields ? 'POST' : 'GET',
    headers: { Authorization: `Bearer ${env.STRIPE_SECRET_KEY}`, ...(fields ? { 'Content-Type': 'application/x-www-form-urlencoded' } : {}), ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}) },
    body: fields ? new URLSearchParams(fields) : undefined,
    signal: AbortSignal.timeout(10000),
    redirect: 'error',
  });
  if (!response.ok) fail(502, 'billing_provider_error', 'Stripe could not complete this request. No access was granted.');
  try { return JSON.parse(await boundedText(response, 256000)); } catch (error) { if (error instanceof ApiError) throw error; fail(502, 'billing_provider_error'); }
}
async function checkout(request, env, user) {
  if (!billingConfigured(env)) fail(503, 'billing_unavailable', 'Stripe billing is not configured yet.');
  if (hasEntitlement(await subscription(env, user))) fail(409, 'already_subscribed', 'Manage your existing subscription in the billing portal.');
  const claim = await query(env, 'UPDATE users SET checkout_pending_at = ? WHERE id = ? AND (checkout_pending_at IS NULL OR checkout_pending_at < ?) RETURNING id,checkout_pending_at', now(), user.id, now() - CHECKOUT_SECONDS).first();
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
  const fields = { mode: 'subscription', customer, expires_at: String(claim.checkout_pending_at + CHECKOUT_SECONDS), 'line_items[0][price]': env.STRIPE_PRICE_ID, 'line_items[0][quantity]': '1', success_url: `${origin}/?billing=success#settings`, cancel_url: `${origin}/?billing=cancelled#pricing`, client_reference_id: user.id, 'subscription_data[metadata][oraclebot_user]': user.id, 'metadata[oraclebot_user]': user.id };
  if (trialAllowed) fields['subscription_data[trial_period_days]'] = '7';
  const session = await stripe(env, 'checkout/sessions', fields, `checkout-${user.id}-${claim.checkout_pending_at}`);
  if (typeof session.url !== 'string' || new URL(session.url).origin !== 'https://checkout.stripe.com') fail(502, 'invalid_checkout_url');
  return json({ url: session.url, trialDays: trialAllowed ? 7 : 0 });
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
    // Read current Stripe state. Delivery order cannot restore a cancelled entitlement.
    const current = await stripe(env, `subscriptions/${encodeURIComponent(subscriptionId)}`);
    const user = await query(env, 'SELECT * FROM users WHERE stripe_customer_id = ?', current.customer).first();
    if (user && current.metadata?.oraclebot_user === user.id) {
      const planMatches = current.items?.data?.length === 1 && current.items.data[0].price?.id === env.STRIPE_PRICE_ID;
      const status = planMatches ? String(current.status) : 'plan_mismatch';
      const periodEnd = Number(current.current_period_end || current.items?.data?.[0]?.current_period_end || 0);
      const trialEnd = Number(current.trial_end || 0);
      await requireDB(env).batch([
        query(env, 'INSERT INTO subscriptions (user_id,stripe_subscription_id,status,period_end,trial_end,stripe_created,event_created,updated_at) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET stripe_subscription_id=excluded.stripe_subscription_id,status=excluded.status,period_end=excluded.period_end,trial_end=excluded.trial_end,stripe_created=excluded.stripe_created,event_created=excluded.event_created,updated_at=excluded.updated_at WHERE excluded.stripe_created > subscriptions.stripe_created OR (excluded.stripe_subscription_id = subscriptions.stripe_subscription_id AND excluded.event_created >= subscriptions.event_created)', user.id, current.id, status, periodEnd, trialEnd, Number(current.created || 0), Number(event.created || 0), now()),
        // Only completion of this exact checkout unlocks it. A delayed event
        // about an earlier subscription must not unlock a newer payable session.
        query(env, 'UPDATE users SET trial_used = MAX(trial_used, ?), checkout_pending_at = CASE WHEN ? = checkout_pending_at + ? THEN NULL ELSE checkout_pending_at END WHERE id = ?', current.trial_start || current.trial_end ? 1 : 0, event.type === 'checkout.session.completed' && object.customer === current.customer && object.metadata?.oraclebot_user === user.id ? Number(object.expires_at || 0) : -1, CHECKOUT_SECONDS, user.id),
        query(env, 'INSERT OR IGNORE INTO stripe_events (id,handled_at) VALUES (?,?)', event.id, now()),
      ]);
      return json({ received: true });
    }
  }
  await query(env, 'INSERT OR IGNORE INTO stripe_events (id,handled_at) VALUES (?,?)', event.id, now()).run();
  return json({ received: true });
}

async function engine(env, path, payload = null) {
  if (!env.ENGINE_URL || !env.ENGINE_TOKEN) fail(503, 'engine_unavailable', 'The canonical research engine has not been connected. No forecast or backtest result is fabricated.');
  const base = new URL(env.ENGINE_URL);
  if (base.protocol !== 'https:' || base.username || base.password || base.search || base.hash) fail(503, 'engine_unavailable');
  const response = await fetch(new URL(path, base), { method: payload ? 'POST' : 'GET', headers: { Authorization: `Bearer ${env.ENGINE_TOKEN}`, ...(payload ? { 'Content-Type': 'application/json' } : {}) }, body: payload ? JSON.stringify(payload) : undefined, signal: AbortSignal.timeout(20000), redirect: 'error' });
  let value;
  try { value = JSON.parse(await boundedText(response, 2000000)); } catch (error) { if (error instanceof ApiError) throw error; fail(502, 'engine_invalid_response'); }
  if (!response.ok) fail(response.status === 400 ? 400 : 503, 'engine_unavailable', 'The research engine could not complete this request.');
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(502, 'engine_invalid_response');
  return json(value);
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
  if (!path.startsWith('/api/')) return env.ASSETS ? env.ASSETS.fetch(request) : new Response('Not found', { status: 404 });
  originOf(request, env);
  if (request.method !== 'GET' && request.method !== 'HEAD' && path !== '/api/billing/webhook') sameOrigin(request, env);
  if (path === '/api/health' && request.method === 'GET') return json({ status: env.DB ? 'ok' : 'setup_required', version: env.APP_VERSION || '1.0.0', storage: Boolean(env.DB), engine: Boolean(env.ENGINE_URL && env.ENGINE_TOKEN), billing: billingConfigured(env), liveExecution: false });
  if (path === '/api/config' && request.method === 'GET') return json({ coins: COINS, trialDays: 7, billingConfigured: billingConfigured(env), engineConfigured: Boolean(env.ENGINE_URL && env.ENGINE_TOKEN), liveExecution: false, walletNetwork: 'solana:mainnet', priceLabel: env.PRICE_LABEL || 'Pricing available at checkout' });
  if (path === '/api/auth/challenge' && request.method === 'POST') return challenge(request, env);
  if (path === '/api/auth/verify' && request.method === 'POST') return verify(request, env);
  if (path === '/api/me' && request.method === 'GET') {
    const user = env.DB ? await account(request, env, false) : null;
    const sub = await subscription(env, user);
    return json({ user: publicUser(user), subscription: publicSubscription(sub) });
  }
  if (path === '/api/auth/logout' && request.method === 'POST') {
    const token = sessionToken(request);
    if (token) await query(env, 'DELETE FROM sessions WHERE token_hash = ?', await hash(token)).run();
    return json({ ok: true }, 200, { 'Set-Cookie': cookie('', 0) });
  }
  if (path === '/api/billing/webhook' && request.method === 'POST') return webhook(request, env);
  if (path === '/api/oracle' && request.method === 'GET') return engine(env, `/v1/oracle?coin=${coin(url.searchParams.get('coin') || 'SOL')}`);
  if (path === '/api/strategies' && request.method === 'GET') return engine(env, '/v1/strategies');
  const user = await account(request, env);
  if (path === '/api/me' && request.method === 'DELETE') {
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
    const deleted = await requireDB(env).batch([
      query(env, 'DELETE FROM users WHERE id = ? AND (checkout_pending_at IS NULL OR checkout_pending_at < ?) RETURNING id', user.id, now() - CHECKOUT_SECONDS),
      ...(usedTrial ? [query(env, 'INSERT OR IGNORE INTO trial_history (wallet_hash,used_at) SELECT ?,? WHERE NOT EXISTS (SELECT id FROM users WHERE id = ?)', await hash(user.wallet), now(), user.id)] : []),
      query(env, 'DELETE FROM challenges WHERE wallet = ? AND NOT EXISTS (SELECT id FROM users WHERE id = ?)', user.wallet, user.id),
    ]);
    if (deleted[0].results?.length !== 1 || deleted[0].results[0].id !== user.id) fail(409, 'checkout_pending', 'A Checkout session began while deletion was being checked. Finish it or wait until its expiration.');
    return json({ deleted: true }, 200, { 'Set-Cookie': cookie('', 0) });
  }
  if (path === '/api/billing/checkout' && request.method === 'POST') return checkout(request, env, user);
  if (path === '/api/billing/portal' && request.method === 'POST') {
    if (!user.stripe_customer_id) fail(409, 'no_subscription');
    const portal = await stripe(env, 'billing_portal/sessions', { customer: user.stripe_customer_id, return_url: `${originOf(request, env)}/#settings` });
    if (typeof portal.url !== 'string' || new URL(portal.url).origin !== 'https://billing.stripe.com') fail(502, 'invalid_portal_url');
    return json({ url: portal.url });
  }
  if (path === '/api/bots' && request.method === 'GET') {
    const rows = await query(env, 'SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC LIMIT 100', user.id).all();
    return json({ bots: rows.results.map(publicBot) });
  }
  if (path === '/api/bots' && request.method === 'POST') {
    await entitled(env, user);
    const bot = validateBot(await bodyJSON(request));
    const count = await query(env, "SELECT COUNT(*) AS n FROM bots WHERE user_id = ? AND status != 'archived'", user.id).first();
    if (count.n >= 20) fail(409, 'bot_limit');
    const id = crypto.randomUUID();
    await query(env, 'INSERT INTO bots (id,user_id,name,coin,strategy,venue,leverage,budget,mode,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', id, user.id, bot.name, bot.coin, bot.strategy, bot.venue, bot.leverage, bot.budget, 'paper', 'configured', now(), now()).run();
    return json({ bot: publicBot(await query(env, 'SELECT * FROM bots WHERE id = ?', id).first()) }, 201);
  }
  if (/^\/api\/bots\/[a-f0-9-]{36}$/.test(path) && request.method === 'PATCH') {
    const input = await bodyJSON(request);
    if (!['paused', 'archived'].includes(input.status) || Object.keys(input).some(k => k !== 'status')) fail(400, 'invalid_bot_action');
    const bot = await query(env, 'UPDATE bots SET status = ?,updated_at = ? WHERE id = ? AND user_id = ? RETURNING *', input.status, now(), path.split('/').at(-1), user.id).first();
    if (!bot) fail(404, 'bot_not_found');
    return json({ bot: publicBot(bot) });
  }
  if (path === '/api/backtests' && request.method === 'POST') {
    await entitled(env, user);
    const input = await bodyJSON(request);
    const payload = { coin: coin(input.coin), strategy: textField(input.strategy, 100, /^[a-zA-Z0-9_-]+$/), interval: input.interval || '1h', capital: numberField(input.capital ?? 10000, 1, 1000000), leverage: numberField(input.leverage ?? 1, 1, 5) };
    if (!['1m', '1h', '1d'].includes(payload.interval)) fail(400, 'unsupported_interval');
    return engine(env, '/v1/backtests', payload);
  }
  fail(404, 'endpoint_not_found');
}

export default {
  async fetch(request, env) {
    let response;
    try { response = await route(request, env); }
    catch (error) {
      if (error instanceof ApiError) response = json({ error: error.code, message: error.message }, error.status);
      else if (error?.name === 'TimeoutError' || error?.name === 'AbortError') response = json({ error: 'upstream_timeout', message: 'The upstream service timed out. No result or execution is assumed.' }, 504);
      else response = json({ error: 'service_unavailable', message: 'This service is temporarily unavailable.' }, 503);
    }
    const result = new Response(response.body, response);
    for (const [name, value] of Object.entries(securityHeaders)) result.headers.set(name, value);
    return result;
  },
  async scheduled(_event, env) {
    if (!env.DB) return;
    await env.DB.batch([
      query(env, 'DELETE FROM challenges WHERE created_at < ?', now() - 3600),
      query(env, 'DELETE FROM sessions WHERE expires_at < ?', now()),
      query(env, 'DELETE FROM stripe_events WHERE handled_at < ?', now() - 90 * 86400),
    ]);
  },
};
