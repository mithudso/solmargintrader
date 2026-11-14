/** Customer-only execution boundary. A configured binding must implement the
 * verified adapter contract; this module does not implement a venue or signer. */
import { validPolicyScope, tradeWithinPolicyScope } from './policy-scope.js';
const ASSETS = new Set(['SOL', 'BTC', 'ETH', 'ZEC']);
const VENUES = new Set(['coinbase', 'jupiter']);
const MAX_USD = 1_000_000;
const EVENT_CATEGORIES = new Set(['none', 'unavailable', 'timeout', 'response', 'binding', 'quote', 'delegation', 'connection', 'quote_hash', 'payload', 'receipt', 'authorization_changed', 'unknown']);
const now = () => Math.floor(Date.now() / 1000);
const db = (env, sql, ...args) => {
  if (!env.DB) throw new TradeError('storage_unavailable', 'Account storage is unavailable.');
  return env.DB.prepare(sql).bind(...args);
};
export class TradeError extends Error {
  constructor(code, message, status = 400) { super(message); this.name = 'TradeError'; this.code = code; this.status = status; }
}
class ExecutionFailure extends Error {
  constructor(category) { super('Customer execution could not be verified.'); this.category = category; }
}
function failureCategory(error) {
  return error instanceof ExecutionFailure && EVENT_CATEGORIES.has(error.category) ? error.category : 'unknown';
}
function executionEvent(operation, outcome, category = 'none') {
  // Only fixed vocabulary reaches telemetry. Logger failure must not change order state.
  const level = ['refused', 'failed', 'unknown'].includes(outcome) ? 'warn' : 'info';
  try {
    console[level](JSON.stringify({ event: 'customer_trade_execution', operation, outcome,
      category: EVENT_CATEGORIES.has(category) ? category : 'unknown' }));
  } catch {}
}
function transportFailure(error) {
  return new ExecutionFailure(['TimeoutError', 'AbortError'].includes(error?.name) ? 'timeout' : 'unavailable');
}
const reject = (code, message, status) => { throw new TradeError(code, message, status); };
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
function exact(value, keys) {
  return object(value) && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
}
function only(value, keys) { return object(value) && Object.keys(value).every(key => keys.includes(key)); }
const opaque = value => typeof value === 'string' && /^[A-Za-z0-9_.:-]{1,128}$/.test(value);
const positive = value => typeof value === 'number' && Number.isFinite(value) && value > 0;
function cents(value, allowZero = false) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || (!allowZero && value === 0) || value > MAX_USD) return null;
  // Parse decimal digits so binary multiplication neither rejects 0.29 nor rounds sub-cents.
  const decimal = /^(\d+)(?:\.(\d{1,2}))?$/.exec(String(value));
  if (!decimal) return null;
  const amount = Number(decimal[1]) * 100 + Number((decimal[2] || '').padEnd(2, '0'));
  return Number.isSafeInteger(amount) && (allowZero || amount > 0) ? amount : null;
}
async function hash(value) {
  const bytes = new TextEncoder().encode(typeof value === 'string' ? value : JSON.stringify(value));
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), n => n.toString(16).padStart(2, '0')).join('');
}
function normalizeInput(input) {
  if (!only(input, ['idempotencyKey', 'venue', 'asset', 'side', 'budgetUsd', 'product', 'leverage', 'reduceOnly', 'maxBaseQuantity']) ||
      !opaque(input.idempotencyKey) || !VENUES.has(input.venue) || !ASSETS.has(input.asset) || cents(input.budgetUsd) === null) {
    reject('invalid_trade', 'Supply an idempotency key, supported venue and asset, and a positive USD budget with at most two decimal places.');
  }
  const product = input.product === undefined ? 'spot' : input.product;
  const leverage = input.leverage === undefined ? 1 : input.leverage;
  if (!['spot', 'perpetual'].includes(product) || !Number.isInteger(leverage) || leverage < 1 || leverage > 5 ||
      (product === 'spot' && (leverage !== 1 || !['buy', 'sell'].includes(input.side))) ||
      (product === 'perpetual' && (input.venue !== 'jupiter' || !['SOL', 'BTC', 'ETH'].includes(input.asset) || !['long', 'short'].includes(input.side)))) {
    reject('invalid_trade', 'Spot trades use buy or sell at 1x. Jupiter perpetual trades use long or short at 1x to 5x.');
  }
  if ((input.reduceOnly !== undefined && typeof input.reduceOnly !== 'boolean') ||
      (input.reduceOnly === true && !(input.venue === 'coinbase' && product === 'spot' && leverage === 1 && input.side === 'sell'))) {
    reject('invalid_trade', 'Reduce-only trades require a Coinbase spot sell at 1x against owned available inventory.');
  }
  let maxBaseQuantity;
  if (input.maxBaseQuantity !== undefined) {
    if (input.reduceOnly !== true || typeof input.maxBaseQuantity !== 'string' || input.maxBaseQuantity.length > 40 ||
        !/^\d{1,18}(?:\.\d{1,18})?$/.test(input.maxBaseQuantity)) reject('invalid_trade', 'A base quantity cap requires a positive decimal string on a reduce-only Coinbase spot sell.');
    const [whole, fraction = ''] = input.maxBaseQuantity.split('.');
    if (BigInt(whole) === 0n && !/[1-9]/.test(fraction)) reject('invalid_trade', 'The base quantity cap must be positive.');
    maxBaseQuantity = `${BigInt(whole)}${fraction.replace(/0+$/, '') ? `.${fraction.replace(/0+$/, '')}` : ''}`;
  }
  // Omit absent/false so existing signed payload hashes remain unchanged.
  return { venue: input.venue, asset: input.asset, side: input.side, budgetUsd: cents(input.budgetUsd) / 100, product, leverage,
    ...(input.reduceOnly === true ? { reduceOnly: true } : {}), ...(maxBaseQuantity ? { maxBaseQuantity } : {}) };
}
function protectiveExit(trade) {
  return trade?.reduceOnly === true && trade.venue === 'coinbase' && trade.product === 'spot' && trade.leverage === 1 && trade.side === 'sell';
}
function requirePrincipal(principal, scope) {
  if (!principal?.user?.id || !principal.user.wallet || !principal.grant?.id || !(principal.scopes instanceof Set) || !principal.scopes.has(scope)) {
    reject('insufficient_scope', 'The agent does not have the required permission.', 403);
  }
}
async function currentPolicy(env, principal, scope) {
  requirePrincipal(principal, scope);
  const grant = await db(env, `SELECT g.*, u.wallet FROM agent_grants g JOIN users u ON u.id=g.user_id
    WHERE g.id=? AND g.user_id=?`, principal.grant.id, principal.user.id).first();
  if (!grant || grant.wallet !== principal.user.wallet || grant.client_id !== principal.client.id ||
      grant.resource !== principal.grant.resource || grant.revoked_at !== null || grant.expires_at <= now() ||
      !grant.scope.split(' ').includes(scope) || grant.policy_hash !== principal.grant.policy_hash) {
    reject('authorization_expired', 'The wallet authorization has expired or was revoked.', 403);
  }
  let policy;
  try { policy = JSON.parse(grant.policy_json); } catch { reject('policy_required', 'An explicit trading policy is required.', 403); }
  if (!validPolicyScope(policy) ||
      !Array.isArray(policy.venues) || !policy.venues.length || policy.venues.some(v => !VENUES.has(v)) ||
      !Array.isArray(policy.assets) || !policy.assets.length || policy.assets.some(a => !ASSETS.has(a)) ||
      cents(policy.maxTradeUsd) === null || cents(policy.maxTotalUsd) === null || policy.maxTradeUsd > policy.maxTotalUsd ||
      !Number.isSafeInteger(policy.expiresAt) || policy.expiresAt <= now() || policy.expiresAt > grant.expires_at || policy.expiresAt > grant.created_at + 30 * 86400 ||
      await hash(grant.policy_json) !== grant.policy_hash) {
    reject('policy_required', 'A current, valid trading policy is required.', 403);
  }
  return { grant, policy };
}
async function entitled(services, user) {
  if (typeof services?.requireEntitlement !== 'function') reject('subscription_required', 'A current subscription is required.', 403);
  await services.requireEntitlement(user);
}
export function executionAvailable(env, venue = null) {
  if (env.LIVE_EXECUTION_ENABLED !== 'true' || typeof env.USER_TRADE_EXECUTOR?.fetch !== 'function') return false;
  if (env.EXECUTOR_AVAILABLE_VENUES !== undefined) {
    let venues;
    try { venues = JSON.parse(env.EXECUTOR_AVAILABLE_VENUES); } catch { return false; }
    if (!Array.isArray(venues) || !venues.length || venues.some(item => !VENUES.has(item))) return false;
    if (venue && !venues.includes(venue)) return false;
  }
  return true;
}
function requireExecutor(env, operation, venue = null) {
  if (!executionAvailable(env, venue)) {
    executionEvent(operation, 'refused', 'unavailable');
    reject('execution_unavailable', 'Customer wallet execution is not connected. No trade was placed.', 503);
  }
}
async function adapter(env, operation, payload) {
  executionEvent(operation, 'started');
  let response;
  try {
    response = await env.USER_TRADE_EXECUTOR.fetch(new Request(`https://customer-trade.internal/v1/trades/${operation}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', ...(typeof env.EXECUTOR_TOKEN === 'string' ? { Authorization: `Bearer ${env.EXECUTOR_TOKEN}` } : {}) }, body: JSON.stringify(payload), signal: AbortSignal.timeout(10_000), redirect: 'manual',
    }));
  } catch (error) { throw transportFailure(error); }
  if (!response.ok || !response.headers.get('Content-Type')?.toLowerCase().startsWith('application/json')) throw new ExecutionFailure('response');
  const reader = response.body?.getReader();
  if (!reader) throw new ExecutionFailure('response');
  const chunks = []; let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read(); if (done) break;
      size += value.length; if (size > 32_768) throw new ExecutionFailure('response'); chunks.push(value);
    }
  } catch (error) {
    if (error instanceof ExecutionFailure) throw error;
    throw transportFailure(error);
  } finally { await reader.cancel().catch(() => {}); }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  try { return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)); }
  catch { throw new ExecutionFailure('response'); }
}
function verifyPreparation(value, intent, policy) {
  if (!exact(value, ['intentId', 'wallet', 'policyHash', 'payloadHash', 'quote', 'delegation', 'connection']) ||
      value.intentId !== intent.id || value.wallet !== intent.wallet || value.policyHash !== intent.policy_hash || value.payloadHash !== intent.payload_hash) throw new ExecutionFailure('binding');
  const { quote, delegation, connection } = value;
  if (!exact(quote, ['id', 'priceUsd', 'quantity', 'feesUsd', 'maxSpendUsd', 'quotedAt', 'expiresAt']) || !opaque(quote.id) ||
      !positive(quote.priceUsd) || !positive(quote.quantity) || cents(quote.feesUsd, true) === null || cents(quote.maxSpendUsd) === null ||
      cents(quote.maxSpendUsd) > intent.reservation_cents || cents(quote.maxSpendUsd) > cents(policy.maxTradeUsd) ||
      quote.priceUsd * quote.quantity + quote.feesUsd > quote.maxSpendUsd + 0.000001 ||
      !Number.isSafeInteger(quote.quotedAt) || quote.quotedAt > now() + 5 || quote.quotedAt < now() - 60 ||
      !Number.isSafeInteger(quote.expiresAt) || quote.expiresAt <= now() || quote.expiresAt > intent.expires_at || quote.expiresAt > quote.quotedAt + 300) throw new ExecutionFailure('quote');
  if (!exact(delegation, ['id', 'wallet', 'policyHash', 'expiresAt', 'verified']) || !opaque(delegation.id) ||
      delegation.wallet !== intent.wallet || delegation.policyHash !== intent.policy_hash || delegation.verified !== true ||
      !Number.isSafeInteger(delegation.expiresAt) || delegation.expiresAt < quote.expiresAt || delegation.expiresAt > policy.expiresAt) throw new ExecutionFailure('delegation');
  let payload;
  try { payload = JSON.parse(intent.payload_json); } catch { throw new ExecutionFailure('payload'); }
  if (payload.maxBaseQuantity !== undefined && quote.quantity > Number(payload.maxBaseQuantity)) throw new ExecutionFailure('quote');
  if (!exact(connection, ['id', 'wallet', 'venue', 'verified']) || !opaque(connection.id) || connection.wallet !== intent.wallet ||
      connection.venue !== payload.venue || connection.verified !== true) throw new ExecutionFailure('connection');
  return value;
}
function publicIntent(row) {
  let payload; let prepared;
  try { payload = JSON.parse(row.payload_json); prepared = row.quote_json ? JSON.parse(row.quote_json) : null; } catch { reject('intent_unavailable', 'The stored intent is unavailable.', 503); }
  return {
    id: row.id, wallet: row.wallet, state: ['preparing', 'prepared'].includes(row.state) && row.expires_at <= now() ? 'expired' : row.state,
    trade: { venue: payload.venue, asset: payload.asset, side: payload.side, budgetUsd: payload.budgetUsd, product: payload.product, leverage: payload.leverage,
      ...(payload.reduceOnly === true ? { reduceOnly: true } : {}), ...(payload.maxBaseQuantity ? { maxBaseQuantity: payload.maxBaseQuantity } : {}) },
    connection: prepared ? prepared.connection : null,
    budgetCommittedUsd: row.reservation_cents / 100, createdAt: row.created_at, expiresAt: row.expires_at,
    quote: prepared ? { id: prepared.quote.id, priceUsd: prepared.quote.priceUsd, quantity: prepared.quote.quantity,
      feesUsd: prepared.quote.feesUsd, maxSpendUsd: prepared.quote.maxSpendUsd, quotedAt: prepared.quote.quotedAt, expiresAt: prepared.quote.expiresAt } : null,
    orderId: row.backend_order_id || null, error: ['preparation_unverified', 'submission_unknown', 'reconciliation_unavailable', 'execution_cost_exceeded'].includes(row.last_error) ? row.last_error : null,
    requiresWalletApproval: false,
    submissionReceiptVerified: ['submitted', 'filled', 'canceled'].includes(row.state),
    consumedBudgetUsd: (row.consumed_cents || 0) / 100,
    budgetExceeded: (row.consumed_cents || 0) > row.reservation_cents,
    filled: row.fill_json ? JSON.parse(row.fill_json) : null,
    reconciledAt: row.reconciled_at || null,
  };
}
async function owned(env, principal, id) {
  if (!opaque(id)) reject('invalid_intent', 'Supply a valid intent ID.');
  const row = await db(env, 'SELECT * FROM agent_trade_intents WHERE id=? AND user_id=? AND wallet=?', id, principal.user.id, principal.user.wallet).first();
  if (!row) reject('intent_not_found', 'The trade intent was not found.', 404);
  return row;
}
export async function getTradeStatus(env, principal, input) {
  requirePrincipal(principal, 'status:read');
  if (!exact(input, ['intentId'])) reject('invalid_arguments', 'Supply only the intent ID.');
  let intent = await owned(env, principal, input.intentId);
  if (env.EXECUTOR_RECONCILIATION_ENABLED === 'true' && ['submitting', 'submitted', 'unknown'].includes(intent.state)) {
    await reconcileIntent(env, principal.user, intent);
    intent = await owned(env, principal, input.intentId);
  }
  return publicIntent(intent);
}
export async function reconcileCustomerTrade(env, user, id) {
  if (!opaque(id) || !user?.id || !user.wallet) reject('invalid_intent', 'Supply a valid owned intent ID.');
  const row = await db(env, 'SELECT * FROM agent_trade_intents WHERE id=? AND user_id=? AND wallet=?', id, user.id, user.wallet).first();
  if (!row) reject('intent_not_found', 'The trade intent was not found.', 404);
  if (env.EXECUTOR_RECONCILIATION_ENABLED === 'true' && ['submitting', 'submitted', 'unknown'].includes(row.state)) await reconcileIntent(env, user, row);
  return publicIntent(await db(env, 'SELECT * FROM agent_trade_intents WHERE id=? AND user_id=? AND wallet=?', id, user.id, user.wallet).first());
}
async function reconcileIntent(env, user, intent) {
  // Reads remain available after subscription loss. This path never submits,
  // widens authority or frees an unknown commitment because a request timed out.
  try {
    const receipt = await adapter(env, 'reconcile', { intentId: intent.id, userId: user.id, wallet: user.wallet,
      resource: intent.resource, policyHash: intent.policy_hash, payloadHash: intent.payload_hash });
    if (!exact(receipt, ['intentId', 'wallet', 'policyHash', 'payloadHash', 'connectionId', 'orderId', 'status', 'consumedCents', 'filled', 'reconciledAt']) ||
        receipt.intentId !== intent.id || receipt.wallet !== intent.wallet || receipt.policyHash !== intent.policy_hash || receipt.payloadHash !== intent.payload_hash ||
        !['unknown', 'submitted', 'filled', 'canceled', 'failed'].includes(receipt.status) || !Number.isSafeInteger(receipt.consumedCents) || receipt.consumedCents < 0 ||
        !Number.isSafeInteger(receipt.reconciledAt) || receipt.reconciledAt < now() - 60 || receipt.reconciledAt > now() + 5 ||
        (receipt.orderId !== null && !opaque(receipt.orderId)) || (intent.backend_order_id && receipt.orderId !== intent.backend_order_id)) throw new ExecutionFailure('receipt');
    if (receipt.status === 'unknown') return;
    let prepared; try { prepared = JSON.parse(intent.quote_json); } catch { throw new ExecutionFailure('quote'); }
    if (!opaque(receipt.connectionId) || receipt.connectionId !== prepared.connection.id) throw new ExecutionFailure('connection');
    if (receipt.status === 'submitted') {
      if (!opaque(receipt.orderId) || receipt.filled !== null || receipt.consumedCents !== 0) throw new ExecutionFailure('receipt');
    } else if (receipt.filled === null) {
      // Only an executor's durably proven no-send failure can lack an order.
      if (receipt.status !== 'failed' || receipt.orderId !== null || receipt.consumedCents !== 0) throw new ExecutionFailure('receipt');
    } else {
      if (!opaque(receipt.orderId) || !exact(receipt.filled, ['quantity', 'valueUsd', 'feesUsd', 'venueStatus', 'asOf']) ||
          ['quantity', 'valueUsd', 'feesUsd'].some(key => typeof receipt.filled[key] !== 'string' || !/^\d{1,18}(?:\.\d{1,18})?$/.test(receipt.filled[key]) || !Number.isFinite(Number(receipt.filled[key]))) ||
          !Number.isSafeInteger(receipt.filled.asOf) || receipt.filled.asOf < intent.created_at || receipt.filled.asOf > receipt.reconciledAt) throw new ExecutionFailure('receipt');
      const quantity = Number(receipt.filled.quantity); const value = Number(receipt.filled.valueUsd); const fee = Number(receipt.filled.feesUsd);
      const native = receipt.filled.venueStatus;
      if ((quantity === 0) !== (value === 0) || quantity > prepared.quote.quantity + 0.000000001 ||
          (receipt.status === 'filled' && (native !== 'FILLED' || quantity <= 0)) ||
          (receipt.status === 'canceled' && !['CANCELLED', 'EXPIRED'].includes(native)) ||
          (receipt.status === 'failed' && native !== 'FAILED') ||
          (quantity > 0 || fee > 0 ? receipt.consumedCents < intent.reservation_cents : receipt.consumedCents !== 0)) throw new ExecutionFailure('receipt');
      const scaled = value => { const [whole, fraction = ''] = value.split('.'); return BigInt(whole) * 10n ** 18n + BigInt(fraction.padEnd(18, '0')); };
      const actual = (scaled(receipt.filled.valueUsd) + scaled(receipt.filled.feesUsd) + 10n ** 16n - 1n) / 10n ** 16n;
      if (actual > BigInt(Number.MAX_SAFE_INTEGER) || receipt.consumedCents !== (quantity > 0 || fee > 0 ? Math.max(intent.reservation_cents, Number(actual)) : 0)) throw new ExecutionFailure('receipt');
    }
    await db(env, `UPDATE agent_trade_intents SET state=?,backend_order_id=COALESCE(backend_order_id,?),consumed_cents=?,fill_json=?,reconciled_at=?,updated_at=?,last_error=?
      WHERE id=? AND user_id=? AND wallet=? AND state IN ('submitting','submitted','unknown') AND policy_hash=? AND payload_hash=? AND quote_hash=?`,
    receipt.status, receipt.orderId, receipt.consumedCents, receipt.filled ? JSON.stringify(receipt.filled) : null, receipt.reconciledAt, now(), receipt.consumedCents > intent.reservation_cents ? 'execution_cost_exceeded' : null, intent.id, user.id, user.wallet, intent.policy_hash, intent.payload_hash, intent.quote_hash).run();
  } catch {
    await db(env, "UPDATE agent_trade_intents SET last_error='reconciliation_unavailable' WHERE id=? AND user_id=? AND wallet=? AND state IN ('submitting','submitted','unknown')", intent.id, user.id, user.wallet).run();
  }
}
export async function listTradeIntents(env, principal) {
  requirePrincipal(principal, 'status:read');
  const result = await db(env, 'SELECT * FROM agent_trade_intents WHERE user_id=? AND wallet=? ORDER BY created_at DESC, id DESC LIMIT 50', principal.user.id, principal.user.wallet).all();
  return result.results.map(publicIntent);
}
async function existing(env, principal, key, payloadHash) {
  const row = await db(env, 'SELECT * FROM agent_trade_intents WHERE user_id=? AND idempotency_key=?', principal.user.id, key).first();
  if (!row) return null;
  if (row.payload_hash !== payloadHash || row.wallet !== principal.user.wallet || row.grant_id !== principal.grant.id) reject('idempotency_conflict', 'That idempotency key already belongs to a different trade or authorization.', 409);
  return row;
}
export async function requestTrade(env, principal, input, services) {
  const payload = normalizeInput(input);
  const { grant, policy } = await currentPolicy(env, principal, 'trade:prepare');
  if (!protectiveExit(payload)) await entitled(services, principal.user);
  if (!tradeWithinPolicyScope(policy, payload) || cents(payload.budgetUsd) > cents(policy.maxTradeUsd)) reject('policy_limit', 'The trade exceeds the approved wallet policy.', 403);
  const payloadHash = await hash(payload);
  const duplicate = await existing(env, principal, input.idempotencyKey, payloadHash);
  if (duplicate) return publicIntent(duplicate);
  requireExecutor(env, 'prepare', payload.venue);
  const at = now(); const id = crypto.randomUUID(); const expiry = Math.min(grant.expires_at, policy.expiresAt, at + 300);
  const result = await db(env, `INSERT INTO agent_trade_intents
    (id,user_id,wallet,grant_id,resource,policy_hash,idempotency_key,payload_hash,payload_json,state,reservation_cents,expires_at,created_at,updated_at)
    SELECT ?,g.user_id,u.wallet,g.id,g.resource,g.policy_hash,?,?,?,'preparing',?,?,?,?
    FROM agent_grants g JOIN users u ON u.id=g.user_id
    WHERE g.id=? AND g.user_id=? AND u.wallet=? AND g.resource=? AND g.policy_hash=? AND g.policy_json=?
      AND g.revoked_at IS NULL AND g.expires_at>? AND instr(' '||g.scope||' ',' trade:prepare ')>0
      AND (?=1 OR EXISTS(SELECT 1 FROM subscriptions s WHERE s.user_id=g.user_id
        AND s.plan_id IN ('starter','advanced','unlimited')
        AND ((s.status='active' AND s.period_end>?) OR (s.status='trialing' AND s.trial_end>?))))
      AND COALESCE((SELECT SUM(CASE WHEN t.state IN ('filled','canceled','failed') THEN t.consumed_cents
        WHEN t.state IN ('submitting','submitted','unknown') OR (t.state IN ('preparing','prepared') AND t.expires_at>?) THEN t.reservation_cents ELSE 0 END)
        FROM agent_trade_intents t WHERE t.grant_id=g.id),0)+?<=?
    ON CONFLICT(user_id,idempotency_key) DO NOTHING RETURNING id`,
  id, input.idempotencyKey, payloadHash, JSON.stringify(payload), cents(payload.budgetUsd), expiry, at, at,
  grant.id, principal.user.id, principal.user.wallet, grant.resource, grant.policy_hash, grant.policy_json, at, Number(protectiveExit(payload)), at, at, at, cents(payload.budgetUsd), cents(policy.maxTotalUsd)).run();
  if (!result.results?.length) {
    const raced = await existing(env, principal, input.idempotencyKey, payloadHash);
    if (raced) return publicIntent(raced);
    reject('policy_limit', 'The remaining wallet policy budget is insufficient or the authorization changed.', 403);
  }
  const intent = await owned(env, principal, id);
  try {
    const prepared = verifyPreparation(await adapter(env, 'prepare', {
      intentId: id, idempotencyKey: id, userId: principal.user.id, wallet: principal.user.wallet,
      grantId: grant.id, resource: grant.resource, policyHash: grant.policy_hash, payloadHash,
      policy, trade: payload, expiresAt: expiry,
    }), intent, policy);
    const quoteHash = await hash(prepared); const fresh = now();
    const update = await db(env, `UPDATE agent_trade_intents SET state='prepared',quote_id=?,quote_json=?,quote_hash=?,quote_expires_at=?,expires_at=?,updated_at=?
      WHERE id=? AND user_id=? AND state='preparing' AND expires_at>?
      AND EXISTS(SELECT 1 FROM agent_grants g JOIN users u ON u.id=g.user_id WHERE g.id=agent_trade_intents.grant_id
        AND g.user_id=? AND u.wallet=? AND g.resource=? AND g.policy_hash=? AND g.policy_json=? AND g.revoked_at IS NULL AND g.expires_at>?) RETURNING id`,
    prepared.quote.id, JSON.stringify(prepared), quoteHash, prepared.quote.expiresAt, prepared.quote.expiresAt, fresh,
    id, principal.user.id, fresh, principal.user.id, principal.user.wallet, grant.resource, grant.policy_hash, grant.policy_json, fresh).run();
    if (!update.results?.length) throw new ExecutionFailure('authorization_changed');
    executionEvent('prepare', 'prepared');
  } catch (error) {
    executionEvent('prepare', 'failed', failureCategory(error));
    await db(env, "UPDATE agent_trade_intents SET state='failed',last_error='preparation_unverified',updated_at=? WHERE id=? AND user_id=? AND state='preparing'", now(), id, principal.user.id).run();
    reject('preparation_unverified', 'The customer connection, delegated authority or quote could not be verified. No order was submitted.', 503);
  }
  return publicIntent(await owned(env, principal, id));
}
export async function submitTrade(env, principal, input, services) {
  requirePrincipal(principal, 'trade:submit');
  if (!exact(input, ['intentId'])) reject('invalid_arguments', 'Supply only the intent ID.');
  const intent = await owned(env, principal, input.intentId);
  const { grant, policy } = await currentPolicy(env, principal, 'trade:submit');
  if (intent.grant_id !== grant.id || intent.policy_hash !== grant.policy_hash || intent.resource !== grant.resource) reject('authorization_changed', 'The intent belongs to a different wallet authorization.', 403);
  if (['submitting', 'submitted', 'unknown', 'failed', 'expired', 'filled', 'canceled'].includes(intent.state)) return publicIntent(intent);
  requireExecutor(env, 'submit');
  if (intent.state !== 'prepared' || intent.expires_at <= now() || intent.quote_expires_at <= now()) reject('intent_not_ready', 'The intent is not prepared or its quote has expired.', 409);
  let prepared; let payload;
  try {
    try { prepared = JSON.parse(intent.quote_json); } catch { throw new ExecutionFailure('quote'); }
    prepared = verifyPreparation(prepared, intent, policy);
    if (await hash(prepared) !== intent.quote_hash) throw new ExecutionFailure('quote_hash');
    try { payload = normalizeInput({ ...JSON.parse(intent.payload_json), idempotencyKey: 'validate' }); }
    catch { throw new ExecutionFailure('payload'); }
    if (await hash(payload) !== intent.payload_hash || !tradeWithinPolicyScope(policy, payload) || intent.reservation_cents > cents(policy.maxTradeUsd)) throw new ExecutionFailure('payload');
  } catch (error) {
    executionEvent('submit', 'refused', failureCategory(error));
    reject('preparation_unverified', 'The stored quote or delegated authority could not be verified.', 409);
  }
  if (!protectiveExit(payload)) await entitled(services, principal.user);
  const at = now();
  const won = await db(env, `UPDATE agent_trade_intents SET state='submitting',updated_at=?
    WHERE id=? AND user_id=? AND wallet=? AND grant_id=? AND resource=? AND state='prepared' AND expires_at>? AND quote_expires_at>?
      AND quote_hash=? AND quote_json=? AND payload_hash=? AND payload_json=? AND policy_hash=?
    AND EXISTS(SELECT 1 FROM agent_grants g JOIN users u ON u.id=g.user_id WHERE g.id=agent_trade_intents.grant_id
      AND g.user_id=? AND u.wallet=? AND g.resource=? AND g.policy_hash=? AND g.policy_json=? AND g.revoked_at IS NULL
      AND g.expires_at>? AND instr(' '||g.scope||' ',' trade:submit ')>0
      AND (?=1 OR EXISTS(SELECT 1 FROM subscriptions s WHERE s.user_id=g.user_id
        AND s.plan_id IN ('starter','advanced','unlimited')
        AND ((s.status='active' AND s.period_end>?) OR (s.status='trialing' AND s.trial_end>?))))) RETURNING id`,
  at, intent.id, principal.user.id, principal.user.wallet, grant.id, grant.resource, at, at,
  intent.quote_hash, intent.quote_json, intent.payload_hash, intent.payload_json, grant.policy_hash,
  principal.user.id, principal.user.wallet, grant.resource, grant.policy_hash, grant.policy_json, at, Number(protectiveExit(payload)), at, at).run();
  if (!won.results?.length) {
    const current = await owned(env, principal, intent.id);
    if (['submitting', 'submitted', 'unknown'].includes(current.state)) return publicIntent(current);
    executionEvent('submit', 'refused', 'authorization_changed');
    reject('intent_not_ready', 'The intent or authorization changed before submission.', 409);
  }
  try {
    const receipt = await adapter(env, 'submit', {
      intentId: intent.id, idempotencyKey: intent.id, userId: principal.user.id, wallet: principal.user.wallet,
      grantId: grant.id, resource: grant.resource, policyHash: grant.policy_hash, payloadHash: intent.payload_hash,
      policy, trade: JSON.parse(intent.payload_json), preparation: prepared, preparationHash: intent.quote_hash,
    });
    if (!exact(receipt, ['intentId', 'wallet', 'policyHash', 'payloadHash', 'quoteId', 'delegationId', 'status', 'orderId']) ||
        receipt.intentId !== intent.id || receipt.wallet !== intent.wallet || receipt.policyHash !== intent.policy_hash || receipt.payloadHash !== intent.payload_hash ||
        receipt.quoteId !== intent.quote_id || receipt.delegationId !== prepared.delegation.id || receipt.status !== 'submitted' || !opaque(receipt.orderId)) throw new ExecutionFailure('receipt');
    await db(env, "UPDATE agent_trade_intents SET state='submitted',backend_order_id=?,submitted_at=?,updated_at=? WHERE id=? AND user_id=? AND state='submitting'", receipt.orderId, now(), now(), intent.id, principal.user.id).run();
    executionEvent('submit', 'submitted');
  } catch (error) {
    executionEvent('submit', 'unknown', failureCategory(error));
    await db(env, "UPDATE agent_trade_intents SET state='unknown',last_error='submission_unknown',updated_at=? WHERE id=? AND user_id=? AND state='submitting'", now(), intent.id, principal.user.id).run();
  }
  return publicIntent(await owned(env, principal, intent.id));
}
