import test from 'node:test';
import assert from 'node:assert/strict';
import { environment, seedUser, keypair, at, ORIGIN } from './helpers/d1.js';
import { digest } from '../execution/common.js';
import { managedSignalId, runManagedBot } from '../execution/managed-bot-driver.js';
import { prepareManagedBot, activateManagedBot, pauseManagedBot, managedBotStatus, managedRepository } from '../src/managed-bots.js';

const REVISION = 'a'.repeat(64);
const reject = code => error => error.code === code;
const one = (f, table) => f.env.sqlite.prepare(`SELECT * FROM ${table}`).get();
const count = (f, table) => f.env.sqlite.prepare(`SELECT COUNT(*) AS n FROM ${table}`).get().n;
async function fixture() {
  const env = environment(); const seeded = await seedUser(env); const user = seeded.user;
  const botId = crypto.randomUUID(); const connectionId = crypto.randomUUID(); const time = at();
  env.sqlite.prepare(`INSERT INTO bots(id,user_id,name,coin,strategy,venue,leverage,budget,mode,status,created_at,updated_at)
    VALUES (?,?,'Signed managed bot','SOL','rsi','coinbase',1,10,'paper','configured',?,?)`).run(botId, user.id, time, time);
  env.sqlite.prepare(`INSERT INTO customer_execution_connections(id,user_id,wallet,venue,credential_fingerprint,portfolio_id,created_at,verified_at)
    VALUES (?,?,?,'coinbase',?,?,?,?)`).run(connectionId, user.id, user.wallet, 'b'.repeat(64), crypto.randomUUID(), time, time);
  env.sqlite.prepare(`INSERT INTO subscriptions(user_id,stripe_subscription_id,status,period_end,trial_end,updated_at,plan_id)
    VALUES (?,'sub_managed_fixture','active',?,0,?,'starter')`).run(user.id, time + 86400, time);
  const services = { origin: ORIGIN,
    async requireEntitlement(owner) {
      const sub = env.sqlite.prepare('SELECT * FROM subscriptions WHERE user_id=?').get(owner.id);
      if (!sub || !((sub.status === 'active' && sub.period_end > at()) || (sub.status === 'trialing' && sub.trial_end > at()))) throw Error('subscription_required');
      return sub;
    },
    strategies: async () => ({ strategies: [{ id: 'rsi', strategyRevision: REVISION }] }),
    botLimit: sub => sub.plan_id === 'unlimited' ? null : sub.plan_id === 'advanced' ? 10 : 3,
  };
  const input = () => ({ connectionId, interval: '1m', policy: { version: 2, venues: ['coinbase'], assets: ['SOL'], products: ['spot'], maxLeverage: 1, maxTradeUsd: 10, maxTotalUsd: 100, expiresAt: at() + 3600 } });
  const f = { env, user, seeded, botId, connectionId, services, input };
  f.prepare = change => prepareManagedBot(env, user, botId, { ...input(), ...change }, services);
  f.sign = async (challenge, keys = seeded.keys) => ({ challengeId: challenge.challengeId, signature: Buffer.from(await crypto.subtle.sign('Ed25519', keys.privateKey, new TextEncoder().encode(challenge.message))).toString('base64') });
  f.activate = async challenge => activateManagedBot(env, user, botId, await f.sign(challenge), services);
  f.active = async () => { const challenge = await f.prepare(); await f.activate(challenge); return challenge; };
  return f;
}
function context(snapshot, extra = {}) {
  return { botId: snapshot.botId, bindingHash: snapshot.bindingHash, configHash: snapshot.configHash, userId: snapshot.principal.user.id,
    wallet: snapshot.principal.user.wallet, clientId: snapshot.principal.client.id, grantId: snapshot.principal.grant.id,
    policyHash: snapshot.principal.grant.policy_hash, connectionId: snapshot.connectionId, ...extra };
}
function insertIntent(f, state = 'prepared', trade = {}) {
  const row = one(f, 'managed_bots'); const id = crypto.randomUUID(); const now = at();
  f.env.sqlite.prepare(`INSERT INTO agent_trade_intents(id,user_id,wallet,grant_id,resource,policy_hash,idempotency_key,payload_hash,payload_json,state,reservation_cents,expires_at,created_at,updated_at)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).run(id, f.user.id, f.user.wallet, row.grant_id, `${ORIGIN}/mcp`, one(f, 'agent_grants').policy_hash, id, 'c'.repeat(64), JSON.stringify(trade), state, 1000, now + 60, now, now);
  return id;
}
async function engine(f, { quantity = '0', target = 1 } = {}) {
  await f.active();
  f.env.sqlite.prepare('UPDATE managed_bots SET allocation_quantity=? WHERE bot_id=?').run(quantity, f.botId);
  const repository = managedRepository(f.env); const calls = []; const intents = new Map();
  const time = at();
  const signal = { asset: 'SOL', strategyId: 'rsi', strategyRevision: REVISION, intervalSeconds: 60,
    barClosedAt: time - 20, asOf: time - 5, expiresAt: time + 55, desiredExposure: target };
  signal.id = await managedSignalId(signal);
  const execution = {
    async prepare(principal, trade) {
      calls.push({ op: 'prepare', trade: structuredClone(trade), principal });
      const id = insertIntent(f, 'prepared', trade);
      const intent = { id, state: 'prepared', wallet: f.user.wallet, trade: structuredClone(trade),
        connection: { id: f.connectionId, wallet: f.user.wallet, venue: 'coinbase', verified: true } };
      intents.set(id, intent); return structuredClone(intent);
    },
    async submit(principal, id) {
      calls.push({ op: 'submit', id, principal }); const value = intents.get(id); value.state = 'submitted';
      f.env.sqlite.prepare("UPDATE agent_trade_intents SET state='submitted' WHERE id=?").run(id);
      return structuredClone(value);
    },
    async reconcile(user, id) { calls.push({ op: 'reconcile', id, user }); return structuredClone(intents.get(id)); },
  };
  const dependencies = { repository, execution, signals: { closedBar: async () => structuredClone(signal) }, clock: () => time };
  return { repository, execution, dependencies, calls, intents, signal, time, run: () => runManagedBot(dependencies, f.botId) };
}

test('wallet Ed25519 activation binds the exact bot config, connection, policy and dedicated managed grant', async () => {
  const f = await fixture(); const challenge = await f.prepare();
  assert.equal(count(f, 'managed_bots'), 0); assert.equal(count(f, 'agent_grants'), 0);
  assert.equal(challenge.config.strategyRevision, REVISION); assert.equal(challenge.config.budgetUsd, 10);
  for (const text of [f.user.wallet, f.botId, f.connectionId, REVISION, 'maximum leverage: 1x', 'USD 100.00', 'Pausing does not close positions']) assert.ok(challenge.message.includes(text), text);
  const result = await f.activate(challenge); const saved = one(f, 'managed_bots'); const grant = one(f, 'agent_grants');
  assert.equal(result.enabled, true); assert.equal(saved.connection_id, f.connectionId); assert.equal(saved.wallet, f.user.wallet);
  assert.deepEqual(JSON.parse(saved.config_json), challenge.config); assert.deepEqual(JSON.parse(grant.policy_json), challenge.policy);
  assert.equal(saved.grant_id, grant.id); assert.equal(saved.client_id, grant.client_id); assert.equal(grant.resource, `${ORIGIN}/mcp`);
  assert.equal(grant.policy_hash, await digest(grant.policy_json)); assert.equal(grant.revoked_at, null);
  assert.equal(grant.scope, 'status:read trade:prepare trade:submit'); assert.equal(saved.allocation_quantity, '0');
  assert.equal(one(f, 'bots').mode, 'paper'); assert.ok(one(f, 'managed_bot_challenges').used_at);
});

test('a foreign wallet or signature cannot activate another user consent and a used challenge cannot replay', async () => {
  const f = await fixture(); const challenge = await f.prepare(); const other = await keypair();
  await assert.rejects(activateManagedBot(f.env, f.user, f.botId, await f.sign(challenge, other.keys), f.services), reject('invalid_wallet_authorization'));
  await assert.rejects(activateManagedBot(f.env, { ...f.user, wallet: other.wallet }, f.botId, await f.sign(challenge), f.services), reject('managed_consent_expired'));
  assert.equal(count(f, 'agent_grants'), 0); assert.equal(count(f, 'managed_bots'), 0);
  await f.activate(challenge);
  await assert.rejects(f.activate(challenge), reject('managed_consent_expired'));
  assert.equal(count(f, 'agent_grants'), 1); assert.equal(count(f, 'managed_bots'), 1);
});

test('altered bot configuration, signed message or strategy revision cannot acquire authority', async () => {
  for (const kind of ['config', 'message', 'revision']) {
    const f = await fixture(); const challenge = await f.prepare();
    if (kind === 'config') f.env.sqlite.prepare('UPDATE bots SET budget=11 WHERE id=?').run(f.botId);
    if (kind === 'message') f.env.sqlite.prepare("UPDATE managed_bot_challenges SET message=message||' changed' WHERE id=?").run(challenge.challengeId);
    if (kind === 'revision') f.services.strategies = async () => ({ strategies: [{ id: 'rsi', strategyRevision: 'd'.repeat(64) }] });
    await assert.rejects(f.activate(challenge), reject(kind === 'revision' ? 'strategy_revision_changed' : 'invalid_wallet_authorization'));
    assert.equal(count(f, 'agent_grants'), 0); assert.equal(count(f, 'managed_bots'), 0);
  }
});

test('consent preparation requires the active customer connection and exact spot budget scope', async () => {
  const f = await fixture(); const other = await seedUser(f.env);
  await assert.rejects(prepareManagedBot(f.env, other.user, f.botId, f.input(), f.services));
  await assert.rejects(f.prepare({ connectionId: crypto.randomUUID() }), reject('customer_connection_required'));
  f.env.sqlite.prepare('UPDATE customer_execution_connections SET revoked_at=? WHERE id=?').run(at(), f.connectionId);
  await assert.rejects(f.prepare(), reject('customer_connection_required'));
  f.env.sqlite.prepare('UPDATE customer_execution_connections SET revoked_at=NULL WHERE id=?').run(f.connectionId);
  for (const patch of [{ assets: ['BTC'] }, { venues: ['jupiter'] }, { products: ['perpetual'] }, { maxLeverage: 2 }, { maxTradeUsd: 9 }]) {
    await assert.rejects(f.prepare({ policy: { ...f.input().policy, ...patch } }), reject('managed_policy_mismatch'));
  }
  assert.equal(count(f, 'agent_grants'), 0);
});

test('activation atomically refuses a customer connection revoked after signature verification', async () => {
  const f = await fixture(); const challenge = await f.prepare();
  f.services.strategies = async () => {
    f.env.sqlite.prepare('UPDATE customer_execution_connections SET revoked_at=? WHERE id=?').run(at(), f.connectionId);
    return { strategies: [{ id: 'rsi', strategyRevision: REVISION }] };
  };
  await assert.rejects(f.activate(challenge), reject('managed_activation_changed'));
  assert.equal(count(f, 'agent_grants'), 0); assert.equal(count(f, 'managed_bots'), 0);
  assert.equal(one(f, 'managed_bot_challenges').used_at, null);
});

test('activation atomically refuses a bot edited after its signature was verified', async () => {
  const f = await fixture(); const challenge = await f.prepare();
  f.services.strategies = async () => {
    f.env.sqlite.prepare('UPDATE bots SET budget=11 WHERE id=?').run(f.botId);
    return { strategies: [{ id: 'rsi', strategyRevision: REVISION }] };
  };
  await assert.rejects(f.activate(challenge), reject('managed_activation_changed'));
  assert.equal(count(f, 'agent_grants'), 0); assert.equal(count(f, 'managed_bots'), 0);
  assert.equal(one(f, 'managed_bot_challenges').used_at, null);
});

test('a per-bot SQLite lease serializes different closed bars and compares observed inventory', async () => {
  const f = await fixture(); await f.active(); const repository = managedRepository(f.env); const snapshot = await repository.load(f.botId);
  const first = context(snapshot, { signalId: 'bar-one', decisionHash: '1'.repeat(64), leaseToken: crypto.randomUUID(), allocationBefore: '0' });
  const second = context(snapshot, { signalId: 'bar-two', decisionHash: '2'.repeat(64), leaseToken: crypto.randomUUID(), allocationBefore: '0' });
  const results = await Promise.all([repository.claimSignal(first), repository.claimSignal(second)]);
  assert.deepEqual(results.map(value => value.status).sort(), ['busy', 'claimed']);
  assert.equal(count(f, 'managed_bot_signals'), 1);
  const winner = results[0].status === 'claimed' ? first : second;
  await repository.hold({ ...winner, reason: 'test release' });
  f.env.sqlite.prepare("UPDATE managed_bots SET allocation_quantity='0.1' WHERE bot_id=?").run(f.botId);
  assert.equal((await repository.claimSignal({ ...second, signalId: 'bar-three', leaseToken: crypto.randomUUID() })).status, 'busy');
  assert.equal(one(f, 'managed_bots').allocation_quantity, '0.1');
  assert.equal(one(f, 'managed_bots').lease_token, null);
});

test('simultaneous driver ticks against real SQLite prepare and submit exactly one order', async () => {
  const f = await fixture(); const e = await engine(f); let n = 0;
  e.dependencies.signals.closedBar = async () => {
    const signal = { ...e.signal, barClosedAt: e.signal.barClosedAt - n++ };
    return { ...signal, id: await managedSignalId(signal) };
  };
  const results = await Promise.all([e.run(), e.run()]);
  assert.equal(results.filter(value => value.status === 'submitted').length, 1);
  assert.equal(e.calls.filter(value => value.op === 'prepare').length, 1); assert.equal(e.calls.filter(value => value.op === 'submit').length, 1);
  assert.equal(count(f, 'agent_trade_intents'), 1); assert.ok(one(f, 'managed_bots').pending_intent_id);
  assert.equal((await e.run()).reason, 'pending_order_unresolved'); assert.equal(e.calls.filter(value => value.op === 'submit').length, 1);
});

test('a terminal verified fill settles the SQLite allocation once and cannot resubmit the same bar', async () => {
  const f = await fixture(); const e = await engine(f); await e.run(); const id = one(f, 'managed_bots').pending_intent_id;
  const intent = e.intents.get(id); intent.state = 'filled'; intent.filled = { quantity: '0.0988', valueUsd: '9.88', feesUsd: '0.1', asOf: e.time }; intent.consumedBudgetUsd = 10;
  f.env.sqlite.prepare("UPDATE agent_trade_intents SET state='filled' WHERE id=?").run(id);
  await Promise.all([e.run(), e.run()]); await e.run();
  assert.equal(one(f, 'managed_bots').allocation_quantity, '0.0988'); assert.equal(one(f, 'managed_bots').pending_intent_id, null);
  assert.equal(count(f, 'managed_bot_settlements'), 1); assert.equal(one(f, 'managed_bot_signals').state, 'complete');
  assert.equal(e.calls.filter(value => value.op === 'submit').length, 1);
  const snapshot = await e.repository.load(f.botId);
  const replay = await e.repository.applySettlement(context(snapshot, { intentId: id, allocationBefore: '0', allocationAfter: '0.0988' }));
  assert.equal(replay.applied, false); assert.equal(one(f, 'managed_bots').allocation_quantity, '0.0988');
});

test('a sell carries only its recorded bot inventory and partial settlement preserves the remainder', async () => {
  const f = await fixture(); const e = await engine(f, { quantity: '0.01', target: 0 }); await e.run();
  const trade = e.calls.find(value => value.op === 'prepare').trade;
  assert.equal(trade.side, 'sell'); assert.equal(trade.reduceOnly, true); assert.equal(trade.maxBaseQuantity, '0.01');
  const id = one(f, 'managed_bots').pending_intent_id; const intent = e.intents.get(id);
  intent.state = 'canceled'; intent.filled = { quantity: '0.005', valueUsd: '0.5', feesUsd: '0.01', asOf: e.time }; intent.consumedBudgetUsd = 10;
  await e.run();
  assert.equal(one(f, 'managed_bots').allocation_quantity, '0.005'); assert.equal(count(f, 'managed_bot_settlements'), 1);
  assert.equal(e.calls.filter(value => value.op === 'submit').length, 1);
});

test('pause or grant revocation after durable preparation prevents the final send and retains pending recovery', async () => {
  for (const change of ['pause', 'revoke']) {
    const f = await fixture(); const e = await engine(f); const record = e.repository.recordPrepared;
    e.repository.recordPrepared = async value => {
      const accepted = await record(value);
      if (change === 'pause') await pauseManagedBot(f.env, f.user, f.botId);
      else f.env.sqlite.prepare('UPDATE agent_grants SET revoked_at=? WHERE id=?').run(at(), value.grantId);
      return accepted;
    };
    assert.equal((await e.run()).reason, 'managed_binding_changed');
    assert.equal(e.calls.filter(value => value.op === 'submit').length, 0);
    assert.ok(one(f, 'managed_bots').pending_intent_id); assert.equal(one(f, 'agent_trade_intents').state, 'prepared');
    assert.equal((await managedBotStatus(f.env, f.user, f.botId)).enabled, false);
  }
});

test('renewal with a pending intent fails and preserves its old grant and allocation', async () => {
  const f = await fixture(); await f.active(); const old = one(f, 'managed_bots'); const id = insertIntent(f);
  f.env.sqlite.prepare("UPDATE managed_bots SET pending_intent_id=?,allocation_quantity='0.01' WHERE bot_id=?").run(id, f.botId);
  const challenge = await f.prepare();
  await assert.rejects(f.activate(challenge), reject('managed_position_requires_reconciliation'));
  const saved = one(f, 'managed_bots'); assert.equal(saved.pending_intent_id, id); assert.equal(saved.grant_id, old.grant_id); assert.equal(saved.allocation_quantity, '0.01');
  assert.equal(f.env.sqlite.prepare('SELECT revoked_at FROM agent_grants WHERE id=?').get(old.grant_id).revoked_at, null);
});

test('same-config renewal preserves held inventory and revokes the previous managed grant', async () => {
  const f = await fixture(); await f.active(); const old = one(f, 'managed_bots');
  f.env.sqlite.prepare("UPDATE managed_bots SET allocation_quantity='0.01' WHERE bot_id=?").run(f.botId);
  const challenge = await f.prepare(); await f.activate(challenge); const saved = one(f, 'managed_bots');
  assert.equal(saved.allocation_quantity, '0.01'); assert.notEqual(saved.grant_id, old.grant_id); assert.equal(saved.config_hash, old.config_hash);
  assert.equal(saved.connection_id, old.connection_id); assert.ok(f.env.sqlite.prepare('SELECT revoked_at FROM agent_grants WHERE id=?').get(old.grant_id).revoked_at);
  assert.equal((await managedBotStatus(f.env, f.user, f.botId)).enabled, true);
});

test('held inventory prevents renewal onto a changed config or different customer connection', async () => {
  for (const change of ['config', 'connection']) {
    const f = await fixture(); await f.active(); const old = one(f, 'managed_bots');
    f.env.sqlite.prepare("UPDATE managed_bots SET allocation_quantity='0.01' WHERE bot_id=?").run(f.botId);
    let input;
    if (change === 'config') { f.env.sqlite.prepare('UPDATE bots SET budget=9 WHERE id=?').run(f.botId); input = {}; }
    else {
      const id = crypto.randomUUID();
      f.env.sqlite.prepare('UPDATE customer_execution_connections SET revoked_at=? WHERE id=?').run(at(), f.connectionId);
      f.env.sqlite.prepare(`INSERT INTO customer_execution_connections(id,user_id,wallet,venue,credential_fingerprint,portfolio_id,created_at,verified_at)
        VALUES (?,?,?,'coinbase',?,?,?,?)`).run(id, f.user.id, f.user.wallet, 'e'.repeat(64), crypto.randomUUID(), at(), at());
      input = { connectionId: id };
    }
    const challenge = await f.prepare(input);
    await assert.rejects(f.activate(challenge), reject('managed_position_requires_reconciliation'));
    assert.equal(one(f, 'managed_bots').grant_id, old.grant_id); assert.equal(one(f, 'managed_bots').allocation_quantity, '0.01');
  }
});
