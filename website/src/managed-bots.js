/** Managed automation uses its own wallet-signed authority. Paper definitions,
 * subscription status and an external agent's grant never confer this authority. */
import { base58Decode } from '../../extension/src/wallet/solana.js';
import { validateAgentPolicy } from './oauth.js';
import { managedConfigHash, managedBindingHash, managedSignalId, runManagedBot, sharedManagedExecution } from '../execution/managed-bot-driver.js';
import { digest, base64url } from '../execution/common.js';

const at = () => Math.floor(Date.now() / 1000);
const q = (env, sql, ...args) => env.DB.prepare(sql).bind(...args);
const uuid = value => typeof value === 'string' && /^[a-f0-9-]{36}$/.test(value);
const exact = (value, keys) => value && !Array.isArray(value) && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
export class ManagedBotError extends Error {
  constructor(code, status = 409) { super(code); this.code = code; this.status = status; }
}
const deny = (code, status) => { throw new ManagedBotError(code, status); };
const intervalSeconds = { '1m': 60, '5m': 300, '15m': 900, '1h': 3600, '6h': 21600, '1d': 86400 };
const opaque = () => base64url(crypto.getRandomValues(new Uint8Array(32)));
function message(row, origin, name) {
  const config = JSON.parse(row.config_json); const policy = JSON.parse(row.policy_json);
  return [
    'Oraclebot managed bot trading preauthorization',
    'Purpose: run this exact bot without asking for each trade.',
    `Site: ${origin}`, `Wallet: ${row.wallet}`, `Bot: ${name}`, `Bot ID: ${row.bot_id}`,
    `Customer connection: ${row.connection_id}`, `Managed client: ${row.client_id}`, `Grant: ${row.grant_id}`,
    `Market: ${config.asset}/USD`, `Venue: ${config.venue}`, 'Product: spot; maximum leverage: 1x',
    `Strategy: ${config.strategyId}`, `Strategy revision: ${config.strategyRevision}`,
    `Closed bar interval: ${config.intervalSeconds} seconds`, `Bot trade budget: USD ${config.budgetUsd.toFixed(2)}`,
    `Maximum per trade, fee-inclusive notional: USD ${policy.maxTradeUsd.toFixed(2)}`,
    `Maximum cumulative trading, fee-inclusive notional: USD ${policy.maxTotalUsd.toFixed(2)}`,
    `Authorization expires: ${new Date(policy.expiresAt * 1000).toISOString()}`,
    `Configuration SHA-256: ${row.config_hash}`, `Policy SHA-256: ${row.policy_hash}`,
    `Nonce: ${row.id}`, `Issued: ${new Date(row.created_at * 1000).toISOString()}`,
    `Sign before: ${new Date(row.expires_at * 1000).toISOString()}`,
    'The bot sells only inventory recorded from its own verified fills.',
    'Pausing revokes trading authority. Pausing does not close positions.',
    'Expiry, revocation or exhausted cumulative authority can prevent an automated exit.',
  ].join('\n');
}

export async function prepareManagedBot(env, user, botId, input, services) {
  if (!exact(input, ['connectionId', 'interval', 'policy']) || !uuid(input.connectionId) || !intervalSeconds[input.interval]) deny('invalid_managed_bot', 400);
  await services.requireEntitlement(user);
  const bot = await q(env, 'SELECT * FROM bots WHERE id=? AND user_id=?', botId, user.id).first();
  if (!bot || bot.status === 'archived') deny('bot_not_found', 404);
  if (bot.venue !== 'coinbase' || bot.leverage !== 1) deny('managed_venue_unavailable', 503);
  const policy = validateAgentPolicy(input.policy);
  if (policy.version !== 2 || JSON.stringify(policy.venues) !== '["coinbase"]' || JSON.stringify(policy.assets) !== JSON.stringify([bot.coin]) ||
      JSON.stringify(policy.products) !== '["spot"]' || policy.maxLeverage !== 1 || policy.maxTradeUsd < bot.budget) deny('managed_policy_mismatch', 400);
  const connection = await q(env, `SELECT id FROM customer_execution_connections WHERE id=? AND user_id=? AND wallet=? AND venue='coinbase' AND revoked_at IS NULL`, input.connectionId, user.id, user.wallet).first();
  if (!connection) deny('customer_connection_required', 409);
  const strategies = await services.strategies();
  const strategy = strategies?.strategies?.find(item => item.id === bot.strategy);
  if (!strategy || !/^[a-f0-9]{64}$/.test(strategy.strategyRevision || '')) deny('strategy_revision_unavailable', 503);
  const config = { version: 1, venue: 'coinbase', asset: bot.coin, product: 'spot', leverage: 1,
    strategyId: bot.strategy, strategyRevision: strategy.strategyRevision, intervalSeconds: intervalSeconds[input.interval], budgetUsd: bot.budget };
  const time = at(); const id = crypto.randomUUID(); const clientId = opaque();
  const row = { id, bot_id: botId, user_id: user.id, wallet: user.wallet, connection_id: connection.id,
    client_id: clientId, grant_id: crypto.randomUUID(), config_json: JSON.stringify(config), config_hash: await managedConfigHash(config),
    policy_json: JSON.stringify(policy), policy_hash: await digest(JSON.stringify(policy)), created_at: time, expires_at: time + 180 };
  row.message = message(row, services.origin, bot.name);
  const batch = await env.DB.batch([
    q(env, `INSERT INTO agent_clients(id,name,redirect_uris,created_at) SELECT ?,?,'[]',? WHERE EXISTS (SELECT 1 FROM users WHERE id=? AND deletion_token IS NULL) AND (SELECT COUNT(*) FROM managed_bot_challenges WHERE user_id=? AND created_at>?)<10 RETURNING id`, clientId, `Oraclebot managed bot ${bot.name}`.slice(0, 80), time, user.id, user.id, time - 300),
    q(env, `INSERT INTO managed_bot_challenges(id,bot_id,user_id,wallet,connection_id,client_id,grant_id,config_json,config_hash,policy_json,policy_hash,message,created_at,expires_at)
      SELECT ?,?,?,?,?,?,?,?,?,?,?,?,?,? WHERE EXISTS (SELECT 1 FROM agent_clients WHERE id=?) RETURNING id`, ...[row.id,row.bot_id,row.user_id,row.wallet,row.connection_id,row.client_id,row.grant_id,row.config_json,row.config_hash,row.policy_json,row.policy_hash,row.message,row.created_at,row.expires_at], clientId),
  ]);
  if (batch.some(value => value.results.length !== 1)) deny('managed_consent_rate_limited', 429);
  return { challengeId: id, message: row.message, config, policy, expiresAt: row.expires_at };
}

export async function activateManagedBot(env, user, botId, input, services) {
  if (!exact(input, ['challengeId', 'signature']) || !uuid(input.challengeId) || typeof input.signature !== 'string' || !/^[A-Za-z0-9+/]{86}==$/.test(input.signature)) deny('wallet_authorization_required', 400);
  const sub = await services.requireEntitlement(user); const time = at();
  const row = await q(env, `SELECT c.*,b.name,b.coin,b.strategy,b.venue,b.leverage,b.budget,b.status FROM managed_bot_challenges c JOIN bots b ON b.id=c.bot_id
    WHERE c.id=? AND c.bot_id=? AND c.user_id=? AND c.wallet=? AND c.used_at IS NULL AND c.expires_at>?`, input.challengeId, botId, user.id, user.wallet, time).first();
  if (!row) deny('managed_consent_expired', 400);
  let policy; let config; let verified = false;
  try {
    policy = validateAgentPolicy(JSON.parse(row.policy_json)); config = JSON.parse(row.config_json);
    const key = await crypto.subtle.importKey('raw', base58Decode(user.wallet), 'Ed25519', false, ['verify']);
    verified = await crypto.subtle.verify('Ed25519', key, Uint8Array.from(atob(input.signature), c => c.charCodeAt(0)), new TextEncoder().encode(row.message));
  } catch { deny('invalid_wallet_authorization', 400); }
  if (!verified || await managedConfigHash(config) !== row.config_hash || JSON.stringify(policy) !== row.policy_json || await digest(row.policy_json) !== row.policy_hash ||
      message(row, services.origin, row.name) !== row.message || row.status === 'archived' || row.venue !== config.venue || row.coin !== config.asset || row.strategy !== config.strategyId || row.leverage !== config.leverage || row.budget !== config.budgetUsd) deny('invalid_wallet_authorization', 400);
  const strategies = await services.strategies();
  if (!strategies?.strategies?.some(item => item.id === config.strategyId && item.strategyRevision === config.strategyRevision)) deny('strategy_revision_changed');
  const previous = await q(env, 'SELECT * FROM managed_bots WHERE bot_id=? AND user_id=?', botId, user.id).first();
  if (previous && (previous.pending_intent_id || (previous.allocation_quantity !== '0' && (previous.config_hash !== row.config_hash || previous.connection_id !== row.connection_id)))) deny('managed_position_requires_reconciliation');
  const bindingHash = await managedBindingHash({ botId, configHash: row.config_hash, connectionId: row.connection_id,
    principal: { user, client: { id: row.client_id }, grant: { id: row.grant_id, policy_hash: row.policy_hash } } });
  const resource = `${services.origin}/mcp`; const limit = services.botLimit(sub);
  // Claim and all following changes share one D1 transaction. The final predicate
  // rechecks subscription, owner, connection, allocation, grant and slot capacity.
  const batch = await env.DB.batch([
    q(env, `UPDATE managed_bot_challenges SET used_at=? WHERE id=? AND used_at IS NULL AND expires_at>?
      AND EXISTS (SELECT 1 FROM users WHERE id=? AND wallet=? AND deletion_token IS NULL)
      AND EXISTS (SELECT 1 FROM customer_execution_connections WHERE id=? AND user_id=? AND wallet=? AND revoked_at IS NULL)
      AND EXISTS (SELECT 1 FROM subscriptions WHERE user_id=? AND plan_id=? AND ((status='active' AND period_end>?) OR (status='trialing' AND trial_end>?)))
      AND EXISTS (SELECT 1 FROM bots WHERE id=? AND user_id=? AND coin=? AND strategy=? AND venue=? AND leverage=? AND budget=? AND status<>'archived')
      AND NOT EXISTS (SELECT 1 FROM managed_bots WHERE bot_id=? AND (pending_intent_id IS NOT NULL OR (allocation_quantity<>'0' AND (config_hash<>? OR connection_id<>?))))
      AND (? IS NULL OR (SELECT COUNT(*) FROM bots WHERE user_id=? AND status NOT IN ('paused','archived') AND id<>?)<?) RETURNING id`,
      time, row.id, time, user.id, user.wallet, row.connection_id, user.id, user.wallet, user.id, sub.plan_id, time, time, botId,user.id,config.asset,config.strategyId,config.venue,config.leverage,config.budgetUsd, botId, row.config_hash, row.connection_id, limit, user.id, botId, limit),
    q(env, `UPDATE agent_grants SET revoked_at=COALESCE(revoked_at,?) WHERE id IN (SELECT grant_id FROM managed_bots WHERE bot_id=?) AND EXISTS (SELECT 1 FROM managed_bot_challenges WHERE id=? AND used_at=?)`, time, botId, row.id, time),
    q(env, `INSERT INTO agent_grants(id,user_id,client_id,resource,scope,policy_json,policy_hash,created_at,expires_at)
      SELECT ?,?,?,?,'status:read trade:prepare trade:submit',?,?,?,? WHERE EXISTS (SELECT 1 FROM managed_bot_challenges WHERE id=? AND used_at=?) RETURNING id`, row.grant_id,user.id,row.client_id,resource,row.policy_json,row.policy_hash,time,policy.expiresAt,row.id,time),
    q(env, `INSERT INTO managed_bots(bot_id,user_id,wallet,connection_id,client_id,grant_id,config_json,config_hash,binding_hash,enabled,created_at,updated_at)
      SELECT ?,?,?,?,?,?,?,?,?,1,?,? WHERE EXISTS (SELECT 1 FROM agent_grants WHERE id=?)
      ON CONFLICT(bot_id) DO UPDATE SET connection_id=excluded.connection_id,client_id=excluded.client_id,grant_id=excluded.grant_id,config_json=excluded.config_json,config_hash=excluded.config_hash,binding_hash=excluded.binding_hash,enabled=1,lease_token=NULL,lease_until=NULL,last_reason='awaiting_signal',updated_at=excluded.updated_at RETURNING bot_id`, botId,user.id,user.wallet,row.connection_id,row.client_id,row.grant_id,row.config_json,row.config_hash,bindingHash,time,time,row.grant_id),
    q(env, `UPDATE bots SET status='configured',updated_at=? WHERE id=? AND user_id=? AND EXISTS (SELECT 1 FROM managed_bots WHERE bot_id=? AND grant_id=?)`, time,botId,user.id,botId,row.grant_id),
  ]);
  if (batch[0].results.length !== 1 || batch[2].results.length !== 1 || batch[3].results.length !== 1) deny('managed_activation_changed');
  return managedBotStatus(env, user, botId);
}

export async function managedBotStatus(env, user, botId) {
  const row = await q(env, `SELECT m.*,g.expires_at,g.revoked_at FROM managed_bots m JOIN agent_grants g ON g.id=m.grant_id WHERE m.bot_id=? AND m.user_id=?`, botId, user.id).first();
  if (!row) return { botId, enabled: false, configured: false, reason: 'wallet_authorization_required' };
  return { botId, configured: true, enabled: row.enabled === 1 && row.revoked_at === null && row.expires_at > at(),
    connectionId: row.connection_id, config: JSON.parse(row.config_json), configHash: row.config_hash,
    allocationQuantity: row.allocation_quantity, pendingIntentId: row.pending_intent_id, reason: row.last_reason, authorizationExpiresAt: row.expires_at, updatedAt: row.updated_at };
}
export async function pauseManagedBot(env, user, botId) {
  return env.DB.batch([
    q(env, `UPDATE agent_grants SET revoked_at=COALESCE(revoked_at,?) WHERE user_id=? AND id IN (SELECT grant_id FROM managed_bots WHERE bot_id=? AND user_id=?)`, at(),user.id,botId,user.id),
    q(env, `UPDATE managed_bots SET enabled=0,last_reason='managed_bot_paused',updated_at=? WHERE bot_id=? AND user_id=?`,at(),botId,user.id),
  ]);
}

// Every write binds immutable authority and the observed inventory. A per-bot
// lease serializes different bar IDs as well as repeated requests for one bar.
export function managedRepository(env) {
  const bound = context => [context.botId,context.bindingHash,context.userId,context.wallet,context.clientId,context.grantId,context.configHash,context.connectionId];
  const match = 'bot_id=? AND binding_hash=? AND user_id=? AND wallet=? AND client_id=? AND grant_id=? AND config_hash=? AND connection_id=?';
  return {
    async load(botId) {
      const row = await q(env, `SELECT m.*,g.resource,g.scope,g.policy_json,g.policy_hash,g.expires_at,g.revoked_at,g.created_at AS grant_created_at FROM managed_bots m JOIN agent_grants g ON g.id=m.grant_id WHERE m.bot_id=?`,botId).first();
      if (!row) deny('managed_bot_not_found',404);
      return { botId,enabled:row.enabled===1,config:JSON.parse(row.config_json),configHash:row.config_hash,bindingHash:row.binding_hash,connectionId:row.connection_id,
        principal:{user:{id:row.user_id,wallet:row.wallet},client:{id:row.client_id,kind:'managed-bot'},grant:{id:row.grant_id,user_id:row.user_id,client_id:row.client_id,resource:row.resource,scope:row.scope,policy_json:row.policy_json,policy_hash:row.policy_hash,expires_at:row.expires_at,revoked_at:row.revoked_at,created_at:row.grant_created_at},scopes:new Set(row.scope.split(' '))},
        allocation:{quantity:row.allocation_quantity},pendingIntentId:row.pending_intent_id };
    },
    async claimSignal(c) {
      const existing = await q(env,'SELECT state,decision_hash FROM managed_bot_signals WHERE bot_id=? AND binding_hash=? AND signal_id=?',c.botId,c.bindingHash,c.signalId).first();
      if (existing && existing.decision_hash !== c.decisionHash) return {status:'busy'};
      if (existing?.state==='complete') return {status:'complete'};
      const time=at();
      const batch=await env.DB.batch([
        q(env,`UPDATE managed_bots SET lease_token=?,lease_until=?,updated_at=?,next_tick_at=? WHERE ${match} AND enabled=1 AND pending_intent_id IS NULL AND allocation_quantity=? AND (lease_token IS NULL OR lease_until<?)
          AND EXISTS (SELECT 1 FROM users WHERE id=managed_bots.user_id AND wallet=managed_bots.wallet AND deletion_token IS NULL)
          AND EXISTS (SELECT 1 FROM agent_grants WHERE id=managed_bots.grant_id AND revoked_at IS NULL AND expires_at>?) RETURNING bot_id`,c.leaseToken,time+90,time,time+60,...bound(c),c.allocationBefore,time,time),
        q(env,`INSERT INTO managed_bot_signals(bot_id,binding_hash,signal_id,decision_hash,state,created_at,updated_at) SELECT ?,?,?,?,'claimed',?,? WHERE EXISTS (SELECT 1 FROM managed_bots WHERE ${match} AND lease_token=?) ON CONFLICT(bot_id,binding_hash,signal_id) DO UPDATE SET state='claimed',updated_at=excluded.updated_at WHERE managed_bot_signals.decision_hash=excluded.decision_hash AND managed_bot_signals.state IN ('claimed','held') RETURNING signal_id`,c.botId,c.bindingHash,c.signalId,c.decisionHash,time,time,...bound(c),c.leaseToken),
      ]);
      return {status:batch.every(value=>value.results.length===1)?'claimed':'busy'};
    },
    async recordPrepared(c) {
      const batch=await env.DB.batch([
        q(env,`UPDATE managed_bots SET pending_intent_id=?,updated_at=? WHERE ${match} AND enabled=1 AND lease_token=? AND lease_until>=? AND pending_intent_id IS NULL
          AND EXISTS (SELECT 1 FROM agent_trade_intents WHERE id=? AND user_id=managed_bots.user_id AND grant_id=managed_bots.grant_id AND state='prepared') RETURNING bot_id`,c.intentId,at(),...bound(c),c.leaseToken,at(),c.intentId),
        q(env,`UPDATE managed_bot_signals SET state='prepared',intent_id=?,updated_at=? WHERE bot_id=? AND binding_hash=? AND signal_id=? AND EXISTS (SELECT 1 FROM managed_bots WHERE ${match} AND lease_token=? AND pending_intent_id=?) RETURNING signal_id`,c.intentId,at(),c.botId,c.bindingHash,c.signalId,...bound(c),c.leaseToken,c.intentId),
      ]); return batch.every(value=>value.results.length===1);
    },
    async recordSubmitted(c) {
      const row=await q(env,`UPDATE managed_bot_signals SET state='submitted',updated_at=? WHERE bot_id=? AND binding_hash=? AND signal_id=? AND intent_id=? AND EXISTS (SELECT 1 FROM managed_bots WHERE ${match} AND lease_token=? AND pending_intent_id=?) RETURNING signal_id`,at(),c.botId,c.bindingHash,c.signalId,c.intentId,...bound(c),c.leaseToken,c.intentId).first();
      return Boolean(row);
    },
    async applySettlement(c) {
      const time=at();
      const batch=await env.DB.batch([
        q(env,`INSERT INTO managed_bot_settlements(intent_id,bot_id,binding_hash,allocation_before,allocation_after,receipt_json,settled_at) SELECT ?,?,?,?,?,?,? WHERE EXISTS (SELECT 1 FROM managed_bots WHERE ${match} AND pending_intent_id=? AND allocation_quantity=?) ON CONFLICT(intent_id) DO NOTHING RETURNING intent_id`,c.intentId,c.botId,c.bindingHash,c.allocationBefore,c.allocationAfter,JSON.stringify(c),time,...bound(c),c.intentId,c.allocationBefore),
        q(env,`UPDATE managed_bots SET allocation_quantity=?,pending_intent_id=NULL,lease_token=NULL,lease_until=NULL,last_reason='settled',updated_at=? WHERE ${match} AND pending_intent_id=? AND allocation_quantity=? AND EXISTS (SELECT 1 FROM managed_bot_settlements WHERE intent_id=? AND bot_id=? AND binding_hash=? AND allocation_before=? AND allocation_after=?) RETURNING bot_id`,c.allocationAfter,time,...bound(c),c.intentId,c.allocationBefore,c.intentId,c.botId,c.bindingHash,c.allocationBefore,c.allocationAfter),
        q(env,`UPDATE managed_bot_signals SET state='complete',updated_at=? WHERE bot_id=? AND binding_hash=? AND intent_id=? AND EXISTS (SELECT 1 FROM managed_bot_settlements WHERE intent_id=?)`,time,c.botId,c.bindingHash,c.intentId,c.intentId),
      ]); return {applied:batch[0].results.length===1&&batch[1].results.length===1};
    },
    async hold(c) {
      const time=at(); const lease=c.leaseToken? ' AND lease_token=?':'';
      const statements=[q(env,`UPDATE managed_bots SET last_reason=?,updated_at=?,next_tick_at=? WHERE ${match}${lease}`,c.reason,time,time+60,...bound(c),...(c.leaseToken?[c.leaseToken]:[]))];
      if(c.signalId&&c.leaseToken) statements.push(q(env,`UPDATE managed_bot_signals SET state=?,updated_at=? WHERE bot_id=? AND binding_hash=? AND signal_id=? AND intent_id IS NULL AND EXISTS (SELECT 1 FROM managed_bots WHERE ${match} AND lease_token=?)`,c.complete?'complete':'held',time,c.botId,c.bindingHash,c.signalId,...bound(c),c.leaseToken));
      if(c.leaseToken) statements.push(q(env,`UPDATE managed_bots SET lease_token=NULL,lease_until=NULL WHERE ${match} AND lease_token=? AND pending_intent_id IS NULL`,...bound(c),c.leaseToken));
      await env.DB.batch(statements);
    },
  };
}

export async function tickManagedBots(env, services) {
  const rows=await q(env,'SELECT bot_id FROM managed_bots WHERE (enabled=1 OR pending_intent_id IS NOT NULL) AND next_tick_at<=? ORDER BY next_tick_at,bot_id LIMIT 20',at()).all();
  const repository=managedRepository(env);
  const signals={async closedBar(config){
    const interval=Object.keys(intervalSeconds).find(key=>intervalSeconds[key]===config.intervalSeconds);
    const value=await services.signal({coin:config.asset,strategy:config.strategyId,interval});
    if(value?.status!=='available'||value.mode!=='spot'||value.coin!==config.asset||value.strategy!==config.strategyId||value.interval!==interval||value.strategyRevision!==config.strategyRevision||value.executionQuote!==false||value.fillDelay!==1||!['inputHash','sourceHash'].every(key=>/^[a-f0-9]{64}$/.test(value[key]||''))||!/^[a-f0-9]{64}$/.test(value.sourceIdentity?.sha256||'')||!Number.isFinite(value.asOf)||!Number.isFinite(value.expiresAt))return null;
    const signal={asset:config.asset,strategyId:config.strategyId,strategyRevision:value.strategyRevision,intervalSeconds:config.intervalSeconds,barClosedAt:value.barEnd,asOf:Math.floor(value.asOf),expiresAt:Math.floor(value.expiresAt),desiredExposure:value.desiredExposure};
    return {...signal,id:await managedSignalId(signal)};
  }};
  const execution=sharedManagedExecution(env,{requireEntitlement:services.requireEntitlement});
  const results=[];
  for(const row of rows.results){
    try { results.push(await runManagedBot({repository,signals,execution},row.bot_id)); }
    catch { await q(env,"UPDATE managed_bots SET last_reason='managed_tick_unavailable',next_tick_at=?,updated_at=? WHERE bot_id=?",at()+60,at(),row.bot_id).run(); results.push({botId:row.bot_id,status:'held',reason:'managed_tick_unavailable'}); }
  }
  return results;
}
