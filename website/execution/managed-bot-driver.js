/** Managed automation core. Repositories and signal sources are trusted private
 * adapters; a saved paper definition, browser payload or MCP grant is not one. */
import { at, cents, digest, exact, opaque, uuid } from './common.js';
import { decimal, decimalText } from './coinbase.js';
import { validPolicyScope } from '../src/policy-scope.js';
import { requestTrade, submitTrade, reconcileCustomerTrade } from '../src/trades.js';

const HASH = /^[a-f0-9]{64}$/;
const WALLET = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;
const TERMINAL = new Set(['filled', 'canceled', 'failed', 'expired']);
const CONFIG_KEYS = ['version', 'venue', 'asset', 'product', 'leverage', 'strategyId', 'strategyRevision', 'intervalSeconds', 'budgetUsd'];
export class ManagedBotError extends Error {
  constructor(code) { super(code); this.code = code; this.name = 'ManagedBotError'; }
}
const deny = code => { throw new ManagedBotError(code); };
function canonicalConfig(config) {
  if (!exact(config, CONFIG_KEYS) || config.version !== 1 || config.venue !== 'coinbase' || config.product !== 'spot' || config.leverage !== 1 ||
      !['SOL', 'BTC', 'ETH', 'ZEC'].includes(config.asset) || !opaque(config.strategyId) || !opaque(config.strategyRevision) ||
      !Number.isSafeInteger(config.intervalSeconds) || config.intervalSeconds < 60 || config.intervalSeconds > 86400) deny('managed_config_invalid');
  cents(config.budgetUsd);
  return Object.fromEntries(CONFIG_KEYS.map(key => [key, config[key]]));
}
export const managedConfigHash = config => digest(canonicalConfig(config));
export function managedBindingHash(snapshot) {
  return digest({ version: 1, botId: snapshot.botId, configHash: snapshot.configHash,
    userId: snapshot.principal?.user?.id, wallet: snapshot.principal?.user?.wallet,
    clientId: snapshot.principal?.client?.id, grantId: snapshot.principal?.grant?.id,
    policyHash: snapshot.principal?.grant?.policy_hash, connectionId: snapshot.connectionId });
}
export function managedSignalId(signal) {
  return digest({ version: 1, asset: signal.asset, strategyId: signal.strategyId, strategyRevision: signal.strategyRevision,
    intervalSeconds: signal.intervalSeconds, barClosedAt: signal.barClosedAt });
}
async function validateSnapshot(snapshot, botId) {
  const principal = snapshot?.principal;
  if (!snapshot || snapshot.botId !== botId || !uuid(botId) || typeof snapshot.enabled !== 'boolean' ||
      !uuid(principal?.user?.id) || !WALLET.test(principal.user.wallet || '') ||
      !/^[A-Za-z0-9_-]{43}$/.test(principal?.client?.id || '') || principal.client.kind !== 'managed-bot' || !uuid(principal?.grant?.id) ||
      !HASH.test(principal.grant.policy_hash || '') || !uuid(snapshot.connectionId) ||
      !HASH.test(snapshot.configHash || '') || await managedConfigHash(snapshot.config) !== snapshot.configHash ||
      !HASH.test(snapshot.bindingHash || '') || await managedBindingHash(snapshot) !== snapshot.bindingHash ||
      (snapshot.pendingIntentId !== null && !uuid(snapshot.pendingIntentId))) deny('managed_binding_invalid');
  const allocation = decimal(snapshot.allocation?.quantity);
  if (decimalText(allocation) !== snapshot.allocation.quantity) deny('managed_allocation_invalid');
  return snapshot;
}
function context(snapshot, extra = {}) {
  return { botId: snapshot.botId, bindingHash: snapshot.bindingHash, configHash: snapshot.configHash,
    userId: snapshot.principal.user.id, wallet: snapshot.principal.user.wallet,
    clientId: snapshot.principal.client.id, grantId: snapshot.principal.grant.id,
    policyHash: snapshot.principal.grant.policy_hash, connectionId: snapshot.connectionId, ...extra };
}
async function activeAuthority(snapshot, time) {
  const { grant } = snapshot.principal;
  if (!(snapshot.principal.scopes instanceof Set) || !['trade:prepare', 'trade:submit'].every(scope => snapshot.principal.scopes.has(scope)) ||
      grant.revoked_at !== null || !Number.isSafeInteger(grant.expires_at) || grant.expires_at <= time) return false;
  let policy; try { policy = JSON.parse(grant.policy_json); } catch { return false; }
  return validPolicyScope(policy) && Number.isSafeInteger(policy.expiresAt) && policy.expiresAt > time &&
    policy.expiresAt <= grant.expires_at && await digest(grant.policy_json) === grant.policy_hash;
}
function intentBound(intent, snapshot, expectedTrade = null) {
  const trade = intent?.trade;
  if (!uuid(intent?.id) || intent.wallet !== snapshot.principal.user.wallet ||
      intent.connection?.id !== snapshot.connectionId || intent.connection.wallet !== snapshot.principal.user.wallet ||
      intent.connection.venue !== 'coinbase' || intent.connection.verified !== true ||
      trade?.venue !== snapshot.config.venue || trade.asset !== snapshot.config.asset || trade.product !== 'spot' || trade.leverage !== 1 ||
      !['buy', 'sell'].includes(trade.side) || (expectedTrade && ['venue', 'asset', 'side', 'product', 'leverage', 'budgetUsd', 'reduceOnly', 'maxBaseQuantity'].some(key => trade[key] !== expectedTrade[key]))) deny('managed_intent_binding_invalid');
  if (trade.side === 'sell' && (trade.reduceOnly !== true || typeof trade.maxBaseQuantity !== 'string')) deny('managed_allocation_invalid');
  return intent;
}
function settlement(intent, snapshot) {
  const allocation = decimal(snapshot.allocation.quantity); const quantity = decimal(intent.filled?.quantity || '0');
  if (intent.state === 'filled' && quantity === 0n) deny('managed_settlement_invalid');
  if (intent.filled) {
    decimal(intent.filled.valueUsd); decimal(intent.filled.feesUsd);
    if (!Number.isSafeInteger(intent.filled.asOf) || intent.filled.asOf <= 0) deny('managed_settlement_invalid');
  }
  if (intent.trade.side === 'sell' && (quantity > allocation || quantity > decimal(intent.trade.maxBaseQuantity, true))) deny('managed_allocation_invalid');
  if (intent.trade.side === 'buy' && allocation !== 0n) deny('managed_allocation_invalid');
  return { intentId: intent.id, state: intent.state, side: intent.trade.side, filledQuantity: decimalText(quantity),
    allocationBefore: snapshot.allocation.quantity, allocationAfter: decimalText(intent.trade.side === 'buy' ? allocation + quantity : allocation - quantity),
    consumedBudgetUsd: intent.consumedBudgetUsd, fill: intent.filled || null };
}
export function sharedManagedExecution(env, services) {
  return { prepare: (principal, trade) => requestTrade(env, principal, trade, services),
    submit: (principal, intentId) => submitTrade(env, principal, { intentId }, services),
    reconcile: (user, intentId) => reconcileCustomerTrade(env, user, intentId) };
}

/** Required repository ABI:
 * load(botId) -> current immutable snapshot (see validateSnapshot).
 * claimSignal(context + signalId/decisionHash/leaseToken) -> {status:'claimed'|'busy'|'complete'}.
 * recordPrepared(context + signalId/leaseToken/intentId/trade) -> true only after durable binding.
 * recordSubmitted(context + signalId/leaseToken/intentId/state) -> true only after durable pending state.
 * applySettlement(context + settlement) -> {applied:boolean}; the repository MUST
 * fence pending intent, binding and allocationBefore, and deduplicate intentId.
 * hold(context + reason/complete?/signalId?/leaseToken?) -> durable fenced result.
 * All writes must compare the binding/config/grant/connection and current lease.
 * The same atomic claim must compare the allocation and pending intent from load;
 * a per-bot lease serializes every signal, not just duplicate copies of one bar.
 */
export async function runManagedBot({ repository, signals, execution, clock = at }, botId) {
  for (const method of ['load', 'claimSignal', 'recordPrepared', 'recordSubmitted', 'applySettlement', 'hold']) if (typeof repository?.[method] !== 'function') deny('managed_repository_unavailable');
  if (typeof signals?.closedBar !== 'function' || !['prepare', 'submit', 'reconcile'].every(method => typeof execution?.[method] === 'function')) deny('managed_source_unavailable');
  let snapshot = await validateSnapshot(await repository.load(botId), botId);
  const hold = async (reason, extra = {}) => { await repository.hold(context(snapshot, { reason, ...extra })); return { botId, status: 'held', reason }; };
  if (snapshot.pendingIntentId) {
    let reconciled;
    try { reconciled = await execution.reconcile(snapshot.principal.user, snapshot.pendingIntentId); }
    catch { return hold('reconciliation_unavailable', { intentId: snapshot.pendingIntentId }); }
    const intent = intentBound(reconciled, snapshot);
    if (intent.id !== snapshot.pendingIntentId) deny('managed_intent_binding_invalid');
    if (!TERMINAL.has(intent.state)) return hold('pending_order_unresolved', { intentId: intent.id });
    const result = await repository.applySettlement(context(snapshot, settlement(intent, snapshot)));
    if (typeof result?.applied !== 'boolean') deny('managed_ledger_unconfirmed');
    const previous = snapshot; snapshot = await validateSnapshot(await repository.load(botId), botId);
    if (snapshot.bindingHash !== previous.bindingHash || snapshot.pendingIntentId !== null) return hold('managed_binding_changed');
  }
  if (!snapshot.enabled) return hold('managed_bot_paused');
  if (!await activeAuthority(snapshot, clock())) return hold('wallet_authorization_inactive');
  const signal = await signals.closedBar(canonicalConfig(snapshot.config)); const time = clock();
  if (!signal || signal.asset !== snapshot.config.asset || signal.strategyId !== snapshot.config.strategyId ||
      signal.strategyRevision !== snapshot.config.strategyRevision || signal.intervalSeconds !== snapshot.config.intervalSeconds ||
      ![0, 1].includes(signal.desiredExposure) || !Number.isSafeInteger(signal.barClosedAt) ||
      signal.barClosedAt > time || signal.barClosedAt < time - snapshot.config.intervalSeconds - 60 ||
      !Number.isSafeInteger(signal.asOf) || signal.asOf < time - 60 || signal.asOf > time + 5 || signal.asOf < signal.barClosedAt ||
      !Number.isSafeInteger(signal.expiresAt) || signal.expiresAt <= time || signal.expiresAt > signal.asOf + 120 ||
      signal.id !== await managedSignalId(signal)) return hold('strategy_signal_unverified');
  const signalId = signal.id; const leaseToken = crypto.randomUUID();
  const claim = await repository.claimSignal(context(snapshot, { signalId, decisionHash: await digest({ signalId, desiredExposure: signal.desiredExposure }),
    leaseToken, allocationBefore: snapshot.allocation.quantity, pendingIntentId: null }));
  if (claim?.status === 'complete') return { botId, status: 'idle', reason: 'signal_already_processed' };
  if (claim?.status !== 'claimed') return { botId, status: 'held', reason: 'managed_bot_busy' };
  const lease = { signalId, leaseToken };
  const held = decimal(snapshot.allocation.quantity) > 0n;
  if ((signal.desiredExposure === 1) === held) return hold('already_at_target', { ...lease, complete: true });
  const trade = { idempotencyKey: `bot:${botId}:${signalId}`, venue: 'coinbase', asset: snapshot.config.asset,
    side: signal.desiredExposure === 1 ? 'buy' : 'sell', budgetUsd: snapshot.config.budgetUsd, product: 'spot', leverage: 1,
    ...(signal.desiredExposure === 0 ? { reduceOnly: true, maxBaseQuantity: snapshot.allocation.quantity } : {}) };
  let preparation;
  try { preparation = await execution.prepare(snapshot.principal, trade); }
  catch { return hold('trade_preparation_refused', lease); }
  const prepared = intentBound(preparation, snapshot, trade);
  if (prepared.state !== 'prepared') return hold('intent_not_prepared', { ...lease, intentId: prepared.id });
  if (await repository.recordPrepared(context(snapshot, { ...lease, intentId: prepared.id, trade })) !== true) return hold('managed_binding_changed', lease);
  const fresh = await validateSnapshot(await repository.load(botId), botId);
  if (fresh.bindingHash !== snapshot.bindingHash || !fresh.enabled || fresh.pendingIntentId !== prepared.id ||
      fresh.allocation.quantity !== snapshot.allocation.quantity || !await activeAuthority(fresh, clock()) ||
      signal.expiresAt <= clock() || signal.asOf < clock() - 60) return hold('managed_binding_changed', { ...lease, intentId: prepared.id });
  let submission;
  try { submission = await execution.submit(snapshot.principal, prepared.id); }
  catch { return hold('submission_unverified', { ...lease, intentId: prepared.id }); }
  const submitted = intentBound(submission, snapshot, trade);
  if (submitted.id !== prepared.id || !['submitting', 'submitted', 'unknown', 'filled', 'canceled', 'failed'].includes(submitted.state)) return hold('submission_unverified', { ...lease, intentId: prepared.id });
  if (await repository.recordSubmitted(context(snapshot, { ...lease, intentId: prepared.id, state: submitted.state })) !== true) deny('managed_journal_unconfirmed');
  return { botId, status: submitted.state === 'submitted' ? 'submitted' : 'held', reason: submitted.state, intentId: prepared.id };
}
