/** Private service binding only. No browser route, operator account or fallback signer. */
import { Coinbase, credentialShape, decimal, decimalText, importSigningKey } from './coinbase.js';
import { open, seal, vaultReady } from './credential-vault.js';
import { at, base64url, boundedJSON, cents, decode64, digest, exact, ExecutionError, json, opaque, only, query, refuse, uuid } from './common.js';
import { validPolicyScope, tradeWithinPolicyScope } from '../src/policy-scope.js';
import { managedConfigHash, managedBindingHash } from './managed-bot-driver.js';

const WALLET = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;
const UNRESOLVED_CONNECTION = "EXISTS(SELECT 1 FROM agent_trade_intents t WHERE t.user_id=c.user_id AND t.wallet=c.wallet AND t.state IN ('submitting','submitted','unknown') AND json_extract(t.quote_json,'$.connection.id')=c.id)";
const MANAGED_FIELDS = ['bot_id', 'grant_id', 'client_id', 'connection_id', 'config_json', 'config_hash', 'binding_hash', 'enabled', 'allocation_quantity', 'pending_intent_id'];
const MANAGED_ROWS = `SELECT ${MANAGED_FIELDS.join(',')} FROM managed_bots WHERE user_id=? AND wallet=? AND (grant_id=? OR (connection_id=? AND json_extract(config_json,'$.asset')=?)) ORDER BY bot_id`;
function protectiveExit(trade) {
  return trade?.reduceOnly === true && trade.venue === 'coinbase' && trade.product === 'spot' && trade.leverage === 1 && trade.side === 'sell';
}
function publicConnection(row) {
  return { id: row.id, venue: row.venue, wallet: row.wallet, portfolioId: row.portfolio_id,
    status: row.revoked_at === null ? 'verified' : 'revoked', canTrade: row.revoked_at === null,
    canTransfer: false, createdAt: row.created_at, verifiedAt: row.verified_at, revokedAt: row.revoked_at };
}
async function owner(env, body, allowDeletion = false) {
  if (!uuid(body?.userId) || typeof body.wallet !== 'string' || !WALLET.test(body.wallet)) refuse('invalid_owner');
  const row = await query(env, 'SELECT id,wallet,deletion_token FROM users WHERE id=?', body.userId).first();
  if (!row || row.wallet !== body.wallet) refuse('owner_binding_invalid', 403);
  if (!allowDeletion && row.deletion_token !== null) refuse('account_deleting', 409);
  return { userId: row.id, wallet: row.wallet };
}
function publicError(error) {
  return json({ error: error instanceof ExecutionError ? error.code : 'executor_unavailable' }, error instanceof ExecutionError ? error.status : 503);
}
async function serviceAuthorized(request, env) {
  if (typeof env.EXECUTOR_TOKEN !== 'string' || env.EXECUTOR_TOKEN.length < 32 || env.EXECUTOR_TOKEN.length > 256) refuse('executor_unconfigured', 503);
  const supplied = request.headers.get('Authorization');
  if (typeof supplied !== 'string' || supplied.length > 300 || await digest(supplied) !== await digest(`Bearer ${env.EXECUTOR_TOKEN}`)) refuse('service_authentication_required', 401);
  if (request.headers.has('Origin')) refuse('browser_access_refused', 403);
}
export default {
  async fetch(request, env) {
    try {
      await serviceAuthorized(request, env);
      const path = new URL(request.url).pathname;
      if (path === '/health' && request.method === 'GET') return json({ status: env.DB && env.CUSTOMER_EXECUTORS && vaultReady(env) ? 'ready' : 'unconfigured',
        version: '0.1.0', venues: { coinbase: { implemented: true, enabled: env.COINBASE_EXECUTION_ENABLED === 'true', products: ['spot'], assets: ['SOL', 'BTC', 'ETH', 'ZEC'], connectionRequired: true },
          jupiter: { implemented: false, enabled: false, reason: 'delegated_perps_qualification_required', assets: ['SOL', 'BTC', 'ETH'] } },
        budgetSemantics: 'fee-inclusive quote-time notional; any filled order conservatively consumes its full reserved maximum', primaryWalletKeysAccepted: false });
      if (request.method !== 'POST' || !['/v1/connections', '/v1/connections/list', '/v1/connections/revoke', '/v1/connections/revoke-all', '/v1/trades/prepare', '/v1/trades/submit', '/v1/trades/reconcile'].includes(path)) refuse('endpoint_not_found', 404);
      const body = await boundedJSON(request, 32768); const principal = await owner(env, body, !['/v1/connections', '/v1/trades/prepare', '/v1/trades/submit'].includes(path));
      if (!env.CUSTOMER_EXECUTORS?.getByName) refuse('executor_unconfigured', 503);
      // One persistent owner per authenticated account serializes admission and revocation.
      const instance = env.CUSTOMER_EXECUTORS.getByName(await digest(principal.userId));
      return instance.fetch(new Request(`https://executor-owner.internal${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), redirect: 'manual' }));
    } catch (error) { return publicError(error); }
  },
};

export class CustomerExecutor {
  constructor(ctx, env) { this.ctx = ctx; this.env = env; this.tail = Promise.resolve(); }
  async fetch(request) {
    const run = this.tail.then(() => this.operation(request)); this.tail = run.catch(() => {});
    try { return await run; } catch (error) { return publicError(error); }
  }
  async operation(request) {
    const path = new URL(request.url).pathname;
    const body = await boundedJSON(request, 32768); const principal = await owner(this.env, body, !['/v1/connections', '/v1/trades/prepare', '/v1/trades/submit'].includes(path));
    const bound = await this.ctx.storage.get('owner');
    if (bound && (bound.userId !== principal.userId || bound.wallet !== principal.wallet)) refuse('owner_binding_invalid', 403);
    if (!bound) await this.ctx.storage.put('owner', principal);
    if (path === '/v1/connections') return json({ connection: await this.connect(principal, body.input) }, 201);
    if (path === '/v1/connections/list') {
      if (!only(body, ['userId', 'wallet', 'cursor'])) refuse('invalid_connection_request');
      let cursor = null;
      if (body.cursor !== undefined) {
        try { if (typeof body.cursor !== 'string' || body.cursor.length > 256) throw Error(); cursor = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(decode64(body.cursor))); } catch { refuse('invalid_connection_cursor'); }
        if (!exact(cursor, ['createdAt', 'id']) || !Number.isSafeInteger(cursor.createdAt) || cursor.createdAt < 0 || !uuid(cursor.id)) refuse('invalid_connection_cursor');
      }
      const priority = await query(this.env, `SELECT c.* FROM customer_execution_connections c WHERE c.user_id=? AND c.wallet=?
        AND (c.revoked_at IS NULL OR ${UNRESOLVED_CONNECTION}) ORDER BY (c.revoked_at IS NULL) DESC,c.created_at DESC,c.id DESC LIMIT 17`, principal.userId, principal.wallet).all();
      if (priority.results.length > 16) refuse('connection_inventory_unavailable', 503);
      const rows = await query(this.env, `SELECT c.* FROM customer_execution_connections c WHERE c.user_id=? AND c.wallet=? AND c.revoked_at IS NOT NULL
        AND NOT ${UNRESOLVED_CONNECTION} AND (? IS NULL OR c.created_at<? OR (c.created_at=? AND c.id<?))
        ORDER BY c.created_at DESC,c.id DESC LIMIT 26`, principal.userId, principal.wallet, cursor?.createdAt ?? null, cursor?.createdAt ?? 0, cursor?.createdAt ?? 0, cursor?.id ?? '').all();
      const more = rows.results.length > 25; const history = rows.results.slice(0, 25); const last = history.at(-1);
      return json({ connections: [...priority.results, ...history].map(publicConnection), nextCursor: more ? base64url(new TextEncoder().encode(JSON.stringify({ createdAt: last.created_at, id: last.id }))) : null });
    }
    if (path === '/v1/connections/revoke') {
      if (!exact(body, ['userId', 'wallet', 'id']) || !uuid(body.id)) refuse('invalid_connection_request');
      const row = await query(this.env, 'UPDATE customer_execution_connections SET revoked_at=COALESCE(revoked_at,?) WHERE id=? AND user_id=? AND wallet=? RETURNING *', at(), body.id, principal.userId, principal.wallet).first();
      if (!row) refuse('connection_not_found', 404);
      const pending = await query(this.env, "SELECT id FROM agent_trade_intents WHERE user_id=? AND wallet=? AND state IN ('submitting','submitted','unknown') AND json_extract(quote_json,'$.connection.id')=? LIMIT 1", principal.userId, principal.wallet, row.id).first();
      // Keep ciphertext only when an already admitted order needs read-only recovery.
      if (!pending) await this.ctx.storage.delete(`credential:${row.id}`);
      return json({ connection: publicConnection(row), pendingOrdersRetained: Boolean(pending) });
    }
    if (path === '/v1/connections/revoke-all') {
      if (!exact(body, ['userId', 'wallet'])) refuse('invalid_connection_request');
      await query(this.env, 'UPDATE customer_execution_connections SET revoked_at=COALESCE(revoked_at,?) WHERE user_id=? AND wallet=?', at(), principal.userId, principal.wallet).run();
      const pending = await query(this.env, "SELECT id FROM agent_trade_intents WHERE user_id=? AND wallet=? AND state IN ('submitting','submitted','unknown') LIMIT 1", principal.userId, principal.wallet).first();
      if (pending) return json({ revoked: true, credentialsDeleted: false, pendingReconciliation: true });
      await query(this.env, "UPDATE agent_trade_intents SET state='expired',updated_at=? WHERE user_id=? AND wallet=? AND state IN ('preparing','prepared')", at(), principal.userId, principal.wallet).run();
      // No admitted send remains. Erase ciphertext, orphaned connection attempts,
      // terminal journals and private owner metadata before account cascade.
      await this.ctx.storage.deleteAll();
      const retained = await this.ctx.storage.list({ prefix: 'credential:', limit: 1 });
      if (retained.size) refuse('credential_cleanup_unconfirmed', 503);
      return json({ revoked: true, credentialsDeleted: true, pendingReconciliation: false });
    }
    if (path === '/v1/trades/prepare') return json(await this.prepare(principal, body));
    if (path === '/v1/trades/submit') return json(await this.submit(principal, body));
    if (path === '/v1/trades/reconcile') return json(await this.reconcile(principal, body));
    refuse('endpoint_not_found', 404);
  }
  client(credentials) { return new Coinbase(credentials); }
  async connect(principal, input) {
    if (!only(input, ['venue', 'apiKeyName', 'privateKey', 'portfolioId', 'idempotencyKey']) || input.venue !== 'coinbase' || !opaque(input.idempotencyKey) || (input.portfolioId !== undefined && !uuid(input.portfolioId))) refuse('invalid_connection_request');
    const credentials = credentialShape(input); await importSigningKey(credentials.privateKey);
    const requestHash = await digest({ ...credentials, portfolioId: input.portfolioId || null });
    const requestKeyHash = await digest(input.idempotencyKey);
    const previous = await query(this.env, 'SELECT * FROM customer_execution_connections WHERE user_id=? AND wallet=? AND request_key_hash=?', principal.userId, principal.wallet, requestKeyHash).first();
    if (previous) {
      if (previous.request_hash !== requestHash) refuse('idempotency_conflict', 409);
      return publicConnection(previous);
    }
    const stored = await this.ctx.storage.list({ prefix: 'credential:', limit: 17 });
    for (const key of stored.keys()) {
      const id = key.slice('credential:'.length);
      const retired = await query(this.env, `SELECT c.id FROM customer_execution_connections c WHERE c.id=? AND c.user_id=? AND c.wallet=?
        AND c.revoked_at IS NOT NULL AND NOT ${UNRESOLVED_CONNECTION}`, id, principal.userId, principal.wallet).first();
      if (retired) { await this.ctx.storage.delete(key); stored.delete(key); }
    }
    if (stored.size >= 16) refuse('connection_limit', 409);
    const previousAttempts = await this.ctx.storage.get('connection-attempts');
    const attempts = Array.isArray(previousAttempts) ? previousAttempts.filter(time => Number.isSafeInteger(time) && time > at() - 86400) : [];
    if (attempts.length >= 8) refuse('connection_rate_limit', 429);
    await this.ctx.storage.put('connection-attempts', [...attempts, at()]);
    const client = this.client(credentials); const portfolio = await client.permissions(input.portfolioId || null);
    await client.accounts(portfolio);
    await owner(this.env, principal);
    const id = crypto.randomUUID(); const encrypted = await seal(this.env, principal, id, credentials);
    await this.ctx.storage.put(`credential:${id}`, encrypted);
    try {
      const result = await query(this.env, `INSERT INTO customer_execution_connections
        (id,user_id,wallet,venue,credential_fingerprint,portfolio_id,request_key_hash,request_hash,created_at,verified_at)
        SELECT ?,u.id,u.wallet,'coinbase',?,?,?,?,?,? FROM users u WHERE u.id=? AND u.wallet=? AND u.deletion_token IS NULL
          AND (SELECT COUNT(*) FROM customer_execution_connections c WHERE c.user_id=u.id AND (c.revoked_at IS NULL OR ${UNRESOLVED_CONNECTION}))<16 RETURNING *`,
      id, await digest(credentials.apiKeyName), portfolio, requestKeyHash, requestHash, at(), at(), principal.userId, principal.wallet).run();
      if (result.results?.length !== 1) refuse('owner_binding_invalid', 403);
      return publicConnection(result.results[0]);
    } catch (error) {
      const saved = await query(this.env, 'SELECT id FROM customer_execution_connections WHERE id=? AND user_id=?', id, principal.userId).first();
      if (!saved) await this.ctx.storage.delete(`credential:${id}`);
      if (error instanceof ExecutionError) throw error;
      refuse('connection_conflict', 409);
    }
  }
  async connection(principal, id = null, trading = true) {
    const row = id ? await query(this.env, 'SELECT * FROM customer_execution_connections WHERE id=? AND user_id=? AND wallet=?', id, principal.userId, principal.wallet).first() :
      await query(this.env, "SELECT * FROM customer_execution_connections WHERE user_id=? AND wallet=? AND venue='coinbase' AND revoked_at IS NULL", principal.userId, principal.wallet).first();
    if (!row || (trading && row.revoked_at !== null)) refuse('connection_unavailable', 409);
    const credentials = await open(this.env, principal, row.id, await this.ctx.storage.get(`credential:${row.id}`));
    return { row, client: this.client(credentials) };
  }
  async authorization(principal, body, scope = null) {
    if (!uuid(body.intentId) || !/^[a-f0-9]{64}$/.test(body.policyHash || '') || !/^[a-f0-9]{64}$/.test(body.payloadHash || '')) refuse('invalid_intent');
    const intent = await query(this.env, 'SELECT * FROM agent_trade_intents WHERE id=? AND user_id=? AND wallet=?', body.intentId, principal.userId, principal.wallet).first();
    if (!intent || intent.policy_hash !== body.policyHash || intent.payload_hash !== body.payloadHash || intent.resource !== body.resource) refuse('intent_binding_invalid', 403);
    if (!scope) return intent;
    await owner(this.env, principal);
    if (this.env.COINBASE_EXECUTION_ENABLED !== 'true') refuse('venue_unavailable', 503);
    const grant = await query(this.env, 'SELECT * FROM agent_grants WHERE id=? AND user_id=?', intent.grant_id, principal.userId).first();
    if (!grant || grant.id !== body.grantId || grant.policy_hash !== intent.policy_hash || grant.resource !== intent.resource || grant.revoked_at !== null || grant.expires_at <= at() || !grant.scope.split(' ').includes(scope)) refuse('authorization_expired', 403);
    let policy; let trade; try { policy = JSON.parse(grant.policy_json); trade = JSON.parse(intent.payload_json); } catch { refuse('intent_binding_invalid', 403); }
    if (!only(trade, ['venue', 'asset', 'side', 'budgetUsd', 'product', 'leverage', 'reduceOnly', 'maxBaseQuantity']) ||
        (trade.reduceOnly !== undefined && (trade.reduceOnly !== true || !protectiveExit(trade))) ||
        (trade.maxBaseQuantity !== undefined && (!protectiveExit(trade) || typeof trade.maxBaseQuantity !== 'string' || trade.maxBaseQuantity.length > 40 || decimal(trade.maxBaseQuantity, true) <= 0n)) ||
        !validPolicyScope(policy) || !tradeWithinPolicyScope(policy, trade) || await digest(grant.policy_json) !== grant.policy_hash || JSON.stringify(policy) !== JSON.stringify(body.policy) || await digest(trade) !== intent.payload_hash || JSON.stringify(trade) !== JSON.stringify(body.trade) || trade.venue !== 'coinbase' || trade.product !== 'spot' || trade.leverage !== 1 || !['buy', 'sell'].includes(trade.side) || !['SOL', 'BTC', 'ETH', 'ZEC'].includes(trade.asset) || !Number.isSafeInteger(policy.expiresAt) || policy.expiresAt <= at() || policy.expiresAt > grant.expires_at || policy.expiresAt > grant.created_at + 30 * 86400 || cents(policy.maxTradeUsd) > cents(policy.maxTotalUsd) || intent.reservation_cents !== cents(trade.budgetUsd) || intent.reservation_cents > cents(policy.maxTradeUsd)) refuse('policy_limit', 403);
    const sub = await query(this.env, "SELECT user_id FROM subscriptions WHERE user_id=? AND plan_id IN ('starter','advanced','unlimited') AND ((status='active' AND period_end>?) OR (status='trialing' AND trial_end>?))", principal.userId, at(), at()).first();
    // Subscription loss must not lock owned spot inventory. The provider proves
    // the exact sell quantity is owned and available at prepare and before send.
    if (!sub && !protectiveExit(trade)) refuse('subscription_required', 403);
    const budget = await query(this.env, `SELECT COALESCE(SUM(CASE WHEN state IN ('filled','canceled','failed') THEN consumed_cents
      WHEN state IN ('submitting','submitted','unknown') OR (state IN ('preparing','prepared') AND expires_at>?) THEN reservation_cents ELSE 0 END),0) AS committed
      FROM agent_trade_intents WHERE grant_id=?`, at(), grant.id).first();
    if (!budget || budget.committed > cents(policy.maxTotalUsd)) refuse('policy_limit', 403);
    if ((scope === 'trade:prepare' && intent.state !== 'preparing') || (scope === 'trade:submit' && intent.state !== 'submitting')) refuse('intent_not_ready', 409);
    return intent;
  }
  async managedRisk(principal, intent, trade, connectionId, submitting = false, quantity = null) {
    // D1 determines whether this is a managed grant. Caller-supplied client kind
    // never confers managed authority or exemption from aggregate inventory.
    const rows = await query(this.env, MANAGED_ROWS, principal.userId, principal.wallet, intent.grant_id, connectionId, trade.asset).all();
    const own = rows.results.find(row => row.grant_id === intent.grant_id);
    if (!own) return null;
    let config; try { config = JSON.parse(own.config_json); } catch { refuse('managed_binding_invalid', 403); }
    if (own.enabled !== 1 || own.connection_id !== connectionId || await managedConfigHash(config) !== own.config_hash ||
        await managedBindingHash({ botId: own.bot_id, configHash: own.config_hash, connectionId, principal: {
          user: { id: principal.userId, wallet: principal.wallet }, client: { id: own.client_id }, grant: { id: intent.grant_id, policy_hash: intent.policy_hash },
        } }) !== own.binding_hash || config.venue !== trade.venue || config.asset !== trade.asset || config.product !== trade.product || config.leverage !== trade.leverage ||
        config.budgetUsd !== trade.budgetUsd || (submitting ? own.pending_intent_id !== intent.id : own.pending_intent_id !== null)) refuse('managed_binding_invalid', 403);
    const allocation = decimal(own.allocation_quantity);
    if (trade.side === 'buy' && allocation !== 0n) refuse('managed_allocation_invalid', 409);
    let total = 0n;
    for (const row of rows.results) {
      const amount = decimal(row.allocation_quantity);
      if (decimalText(amount) !== row.allocation_quantity) refuse('managed_allocation_invalid', 409);
      if (row.connection_id === connectionId) {
        total += amount;
        if (row.bot_id !== own.bot_id && row.pending_intent_id !== null) refuse('managed_reconciliation_required', 409);
      }
    }
    if (trade.side === 'sell' && (!protectiveExit(trade) || trade.maxBaseQuantity === undefined || allocation === 0n ||
        decimal(trade.maxBaseQuantity, true) > allocation || (quantity !== null && decimal(quantity, true) > allocation))) refuse('managed_allocation_invalid', 409);
    return { own, minimumBaseBalance: trade.side === 'sell' ? decimalText(total) : null,
      snapshot: JSON.stringify(rows.results.map(row => MANAGED_FIELDS.map(field => row[field]))) };
  }
  async prepare(principal, body) {
    if (!exact(body, ['intentId', 'idempotencyKey', 'userId', 'wallet', 'grantId', 'resource', 'policyHash', 'payloadHash', 'policy', 'trade', 'expiresAt']) || body.idempotencyKey !== body.intentId) refuse('invalid_intent');
    const intent = await this.authorization(principal, body, 'trade:prepare');
    if (intent.expires_at !== body.expiresAt || intent.expires_at <= at()) refuse('intent_not_ready', 409);
    const prior = await this.ctx.storage.get(`intent:${intent.id}`);
    if (prior) {
      if (prior.payloadHash !== intent.payload_hash || prior.policyHash !== intent.policy_hash || prior.status !== 'prepared' || prior.prepared.quote.expiresAt <= at()) refuse('intent_not_ready', 409);
      return prior.prepared;
    }
    const outstanding = await query(this.env, "SELECT id FROM agent_trade_intents WHERE user_id=? AND wallet=? AND id<>? AND state IN ('submitting','submitted','unknown') LIMIT 1", principal.userId, principal.wallet, intent.id).first();
    if (outstanding) refuse('reconciliation_required', 409);
    const { row, client } = await this.connection(principal);
    const managed = await this.managedRisk(principal, intent, body.trade, row.id);
    const plan = await client.prepare(body.trade, row.portfolio_id, managed?.minimumBaseBalance ?? null);
    plan.quote.expiresAt = Math.min(plan.quote.expiresAt, intent.expires_at, body.policy.expiresAt);
    if (plan.quote.expiresAt <= at()) refuse('stale_quote', 409);
    const prepared = { intentId: intent.id, wallet: principal.wallet, policyHash: intent.policy_hash, payloadHash: intent.payload_hash,
      quote: plan.quote, delegation: { id: row.id, wallet: principal.wallet, policyHash: intent.policy_hash, expiresAt: body.policy.expiresAt, verified: true },
      connection: { id: row.id, wallet: principal.wallet, venue: 'coinbase', verified: true } };
    await this.authorization(principal, body, 'trade:prepare');
    const latestManaged = await this.managedRisk(principal, intent, body.trade, row.id);
    if (latestManaged?.snapshot !== managed?.snapshot) refuse('managed_inventory_changed', 409);
    await query(this.env, 'UPDATE customer_execution_connections SET verified_at=? WHERE id=? AND revoked_at IS NULL', at(), row.id).run();
    await this.ctx.storage.put(`intent:${intent.id}`, { status: 'prepared', connectionId: row.id, payloadHash: intent.payload_hash, policyHash: intent.policy_hash, prepared, plan, createdAt: at() });
    return prepared;
  }
  async admit(principal, body, saved, admissionId, managed) {
    const time = at();
    const result = await query(this.env, `UPDATE agent_trade_intents SET executor_admission_id=?,executor_admitted_at=?
      WHERE id=? AND user_id=? AND wallet=? AND state='submitting' AND executor_admission_id IS NULL
        AND policy_hash=? AND payload_hash=? AND payload_json=? AND quote_hash=? AND quote_json=? AND expires_at>? AND quote_expires_at>?
        AND EXISTS(SELECT 1 FROM users u WHERE u.id=agent_trade_intents.user_id AND u.wallet=agent_trade_intents.wallet AND u.deletion_token IS NULL)
        AND EXISTS(SELECT 1 FROM agent_grants g WHERE g.id=agent_trade_intents.grant_id AND g.id=? AND g.user_id=?
          AND g.resource=? AND g.policy_hash=? AND g.policy_json=? AND g.revoked_at IS NULL AND g.expires_at>?
          AND instr(' '||g.scope||' ',' trade:submit ')>0
          AND (?=1 OR EXISTS(SELECT 1 FROM subscriptions s WHERE s.user_id=g.user_id AND s.plan_id IN ('starter','advanced','unlimited')
            AND ((s.status='active' AND s.period_end>?) OR (s.status='trialing' AND s.trial_end>?))
            AND (?=0 OR s.plan_id='unlimited' OR (SELECT COUNT(*) FROM bots b WHERE b.user_id=g.user_id AND b.status NOT IN ('paused','archived'))
              <=CASE s.plan_id WHEN 'starter' THEN 3 WHEN 'advanced' THEN 10 ELSE 0 END))))
        AND EXISTS(SELECT 1 FROM customer_execution_connections c WHERE c.id=? AND c.user_id=? AND c.wallet=? AND c.revoked_at IS NULL)
        AND (? IS NULL OR ?=(SELECT json_group_array(json_array(${MANAGED_FIELDS.join(',')})) FROM (${MANAGED_ROWS})))
        AND COALESCE((SELECT SUM(CASE WHEN t.state IN ('filled','canceled','failed') THEN t.consumed_cents
          WHEN t.state IN ('submitting','submitted','unknown') OR (t.state IN ('preparing','prepared') AND t.expires_at>?) THEN t.reservation_cents ELSE 0 END)
          FROM agent_trade_intents t WHERE t.grant_id=agent_trade_intents.grant_id),0)<=?
        RETURNING id`, admissionId, time, body.intentId, principal.userId, principal.wallet,
    body.policyHash, body.payloadHash, JSON.stringify(body.trade), body.preparationHash, JSON.stringify(saved.prepared), time, time,
    body.grantId, principal.userId, body.resource, body.policyHash, JSON.stringify(body.policy), time, Number(protectiveExit(body.trade)), time, time, Number(Boolean(managed) && body.trade.side === 'buy'),
    saved.connectionId, principal.userId, principal.wallet,
    managed?.snapshot ?? null, managed?.snapshot ?? null, principal.userId, principal.wallet, body.grantId, saved.connectionId, body.trade.asset,
    time, cents(body.policy.maxTotalUsd)).run();
    if (result.results?.length !== 1) {
      const previous = await query(this.env, 'SELECT executor_admission_id FROM agent_trade_intents WHERE id=? AND user_id=? AND wallet=?', body.intentId, principal.userId, principal.wallet).first();
      if (previous?.executor_admission_id) refuse('submission_outcome_unknown', 409);
      refuse('submission_admission_changed', 409);
    }
  }
  async submit(principal, body) {
    if (!exact(body, ['intentId', 'idempotencyKey', 'userId', 'wallet', 'grantId', 'resource', 'policyHash', 'payloadHash', 'policy', 'trade', 'preparation', 'preparationHash']) || body.idempotencyKey !== body.intentId) refuse('invalid_intent');
    const intent = await this.authorization(principal, body, 'trade:submit');
    const key = `intent:${intent.id}`; const saved = await this.ctx.storage.get(key);
    if (!saved || saved.policyHash !== intent.policy_hash || saved.payloadHash !== intent.payload_hash || await digest(saved.prepared) !== body.preparationHash || body.preparationHash !== intent.quote_hash || JSON.stringify(saved.prepared) !== JSON.stringify(body.preparation) || JSON.stringify(saved.prepared) !== intent.quote_json) refuse('preparation_unverified', 409);
    if (saved.status === 'submitted' && saved.orderId) return this.submittedReceipt(intent, saved);
    if (intent.executor_admission_id && saved.status === 'prepared') {
      saved.status = 'unknown'; saved.admissionId = intent.executor_admission_id; await this.ctx.storage.put(key, saved);
      refuse('submission_requires_reconciliation', 409);
    }
    if (saved.status !== 'prepared' || saved.prepared.quote.expiresAt <= at() || intent.quote_expires_at <= at()) refuse('submission_requires_reconciliation', 409);
    const { row, client } = await this.connection(principal, saved.connectionId);
    const quantity = saved.plan.order.order_configuration.sor_limit_ioc.base_size;
    const managed = await this.managedRisk(principal, intent, body.trade, row.id, true, quantity);
    const request = await client.submitRequest(saved.plan, row.portfolio_id, intent.id, managed?.minimumBaseBalance ?? null);
    const latestManaged = await this.managedRisk(principal, intent, body.trade, row.id, true, quantity);
    if (latestManaged?.snapshot !== managed?.snapshot) refuse('managed_inventory_changed', 409);
    saved.status = 'submitting'; saved.admittedAt = at(); saved.admissionId = crypto.randomUUID(); await this.ctx.storage.put(key, saved);
    let started = false;
    try {
      // The signature/request and durable send marker already exist. Recheck the
      // shared grant/plan and connection immediately before the single HTTP send.
      await this.admit(principal, body, saved, saved.admissionId, managed);
      started = true;
      saved.orderId = await client.send(request, intent.id);
      saved.status = 'submitted'; saved.submittedAt = at(); await this.ctx.storage.put(key, saved);
      return this.submittedReceipt(intent, saved);
    } catch (error) {
      const uncertain = started || error?.code !== 'submission_admission_changed';
      saved.status = uncertain ? 'unknown' : 'failed'; saved.noSend = !uncertain;
      await this.ctx.storage.put(key, saved);
      throw error;
    }
  }
  submittedReceipt(intent, saved) {
    return { intentId: intent.id, wallet: intent.wallet, policyHash: intent.policy_hash, payloadHash: intent.payload_hash,
      quoteId: saved.prepared.quote.id, delegationId: saved.prepared.delegation.id, status: 'submitted', orderId: saved.orderId };
  }
  async reconcile(principal, body) {
    if (!exact(body, ['intentId', 'userId', 'wallet', 'resource', 'policyHash', 'payloadHash'])) refuse('invalid_intent');
    const intent = await this.authorization(principal, body);
    const key = `intent:${intent.id}`; const saved = await this.ctx.storage.get(key);
    const base = { intentId: intent.id, wallet: intent.wallet, policyHash: intent.policy_hash, payloadHash: intent.payload_hash,
      connectionId: saved?.connectionId || null, orderId: saved?.orderId || null, status: 'unknown', consumedCents: 0, filled: null, reconciledAt: at() };
    if (!saved || saved.policyHash !== intent.policy_hash || saved.payloadHash !== intent.payload_hash) return base;
    if (saved.status === 'failed' && saved.noSend) return { ...base, status: 'failed' };
    if (saved.settlement) return { ...base, ...saved.settlement, reconciledAt: at() };
    if (saved.status === 'prepared' && !intent.executor_admission_id) {
      // A send is impossible without a prior durable admission marker. The DO's
      // serialized operation queue has already finished any admitted submit.
      saved.status = 'failed'; saved.noSend = true; await this.ctx.storage.put(key, saved);
      return { ...base, status: 'failed' };
    }
    const { row, client } = await this.connection(principal, saved.connectionId, false);
    const settled = await client.reconcile(saved.plan, row.portfolio_id, intent.id, saved.orderId || null);
    const spent = settled.filled && (Number(settled.filled.quantity) > 0 || Number(settled.filled.feesUsd) > 0);
    const cent = 10n ** 16n;
    const actual = settled.filled ? (decimal(settled.filled.valueUsd) + decimal(settled.filled.feesUsd) + cent - 1n) / cent : 0n;
    if (actual > BigInt(Number.MAX_SAFE_INTEGER)) refuse('reconciliation_economics_invalid', 503);
    const result = { ...base, ...settled, consumedCents: spent ? Math.max(intent.reservation_cents, Number(actual)) : 0, reconciledAt: at() };
    if (['filled', 'canceled', 'failed'].includes(result.status)) {
      saved.settlement = result; saved.status = result.status; await this.ctx.storage.put(key, saved);
    } else if (result.orderId) { saved.orderId = result.orderId; await this.ctx.storage.put(key, saved); }
    return result;
  }
}
