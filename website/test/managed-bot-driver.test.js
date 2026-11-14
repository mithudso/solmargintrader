import test from 'node:test';
import assert from 'node:assert/strict';
import { base64url, digest } from '../execution/common.js';
import { managedConfigHash, managedBindingHash, managedSignalId, runManagedBot } from '../execution/managed-bot-driver.js';

const TIME = 1_800_000_000;
async function fixture(options = {}) {
  const user = { id: crypto.randomUUID(), wallet: '11111111111111111111111111111111' };
  const policy = { venues: ['coinbase'], assets: ['SOL'], maxTradeUsd: 10, maxTotalUsd: 100, expiresAt: TIME + 3600 };
  const policyJson = JSON.stringify(policy);
  const config = { version: 1, venue: 'coinbase', asset: 'SOL', product: 'spot', leverage: 1, strategyId: 'rsi', strategyRevision: 'r1', intervalSeconds: 60, budgetUsd: 10 };
  let state = { botId: crypto.randomUUID(), enabled: true, config, configHash: await managedConfigHash(config), connectionId: crypto.randomUUID(),
    principal: { user, client: { id: base64url(crypto.getRandomValues(new Uint8Array(32))), kind: 'managed-bot' }, grant: { id: crypto.randomUUID(), resource: 'https://oraclebot.io/mcp', policy_hash: await digest(policyJson), policy_json: policyJson, expires_at: TIME + 3600, revoked_at: null }, scopes: new Set(['trade:prepare', 'trade:submit']) },
    allocation: { quantity: options.quantity || '0' }, pendingIntentId: null };
  state.bindingHash = await managedBindingHash(state);
  let signal = { asset: 'SOL', strategyId: 'rsi', strategyRevision: 'r1', intervalSeconds: 60, barClosedAt: TIME - 20, asOf: TIME - 10, expiresAt: TIME + 30, desiredExposure: options.target ?? 1 };
  signal.id = await managedSignalId(signal);
  const claims = new Map(); const settled = new Set(); const calls = []; const holds = []; let lease = null; let currentIntent = null; let applied = 0;
  const bound = c => c.bindingHash === state.bindingHash && c.connectionId === state.connectionId && c.userId === user.id && c.wallet === user.wallet && c.configHash === state.configHash;
  const repository = {
    async load() { return structuredClone(state); },
    async claimSignal(c) {
      if (!bound(c) || c.allocationBefore !== state.allocation.quantity || state.pendingIntentId || lease) return { status: 'busy' };
      if (claims.has(c.signalId)) return { status: 'complete' }; lease = c.leaseToken; return { status: 'claimed' };
    },
    async recordPrepared(c) {
      if (!bound(c) || c.leaseToken !== lease || state.pendingIntentId) return false;
      state.pendingIntentId = c.intentId;
      if (options.afterPrepared) await options.afterPrepared(state);
      return true;
    },
    async recordSubmitted(c) { if (!bound(c) || c.leaseToken !== lease || state.pendingIntentId !== c.intentId) return false; claims.set(c.signalId, true); lease = null; return true; },
    async applySettlement(c) {
      if (settled.has(c.intentId)) return { applied: false };
      assert.ok(bound(c)); assert.equal(c.intentId, state.pendingIntentId); assert.equal(c.allocationBefore, state.allocation.quantity);
      state.allocation.quantity = c.allocationAfter; state.pendingIntentId = null; settled.add(c.intentId); applied++; lease = null; return { applied: true };
    },
    async hold(c) { holds.push(c); if (c.leaseToken === lease) lease = null; if (c.complete) claims.set(c.signalId, true); },
  };
  const connection = () => ({ id: state.connectionId, wallet: user.wallet, venue: 'coinbase', verified: true });
  const execution = {
    async prepare(principal, trade) { calls.push({ op: 'prepare', trade, principal }); currentIntent = { id: crypto.randomUUID(), wallet: user.wallet, connection: connection(), trade: structuredClone(trade), state: 'prepared' }; return structuredClone(currentIntent); },
    async submit(principal, id) { calls.push({ op: 'submit', id, principal }); currentIntent.state = 'submitted'; return structuredClone(currentIntent); },
    async reconcile(owner, id) { calls.push({ op: 'reconcile', owner, id }); return structuredClone(currentIntent); },
  };
  const dependencies = { repository, signals: { closedBar: async () => structuredClone(signal) }, execution, clock: () => TIME };
  return { dependencies, calls, holds, get state() { return state; }, get intent() { return currentIntent; }, get applied() { return applied; }, get signal() { return signal; }, set signal(value) { signal = value; }, run: () => runManagedBot(dependencies, state.botId) };
}
test('a managed bot claims each closed-bar signal once and unresolved submissions hold exposure', async () => {
  const f = await fixture(); const results = await Promise.all([f.run(), f.run()]);
  assert.equal(results.filter(r => r.status === 'submitted').length, 1); assert.equal(f.calls.filter(c => c.op === 'submit').length, 1);
  const held = await f.run(); assert.equal(held.reason, 'pending_order_unresolved'); assert.equal(f.calls.filter(c => c.op === 'submit').length, 1);
  f.intent.state = 'filled'; f.intent.filled = { quantity: '0.0988', valueUsd: '9.88', feesUsd: '0.1', asOf: TIME }; f.intent.consumedBudgetUsd = 10;
  await f.run(); await f.run(); assert.equal(f.applied, 1); assert.equal(f.state.allocation.quantity, '0.0988'); assert.equal(f.calls.filter(c => c.op === 'prepare').length, 1);
});
test('a sell can reduce only the exact bot allocation and always carries reduce-only protection', async () => {
  const f = await fixture({ quantity: '0.01', target: 0 }); assert.equal((await f.run()).status, 'submitted');
  const trade = f.calls.find(c => c.op === 'prepare').trade; assert.equal(trade.side, 'sell'); assert.equal(trade.reduceOnly, true); assert.equal(trade.maxBaseQuantity, '0.01');
  f.intent.state = 'canceled'; f.intent.filled = { quantity: '0.005', valueUsd: '0.5', feesUsd: '0.01', asOf: TIME }; f.intent.consumedBudgetUsd = 10;
  await f.run(); assert.equal(f.state.allocation.quantity, '0.005'); assert.equal(f.applied, 1);
});
test('fractional, stale, open-bar and altered-revision signals never reach execution', async () => {
  for (const patch of [{ desiredExposure: 0.5 }, { asOf: TIME - 61 }, { barClosedAt: TIME + 1 }, { strategyRevision: 'changed' }, { expiresAt: TIME - 1 }]) {
    const f = await fixture(); f.signal = { ...f.signal, ...patch }; f.signal.id = await managedSignalId(f.signal);
    assert.equal((await f.run()).reason, 'strategy_signal_unverified'); assert.equal(f.calls.length, 0);
  }
});
test('external MCP authority, changed immutable config and revoked or expired grants cannot drive a bot', async () => {
  for (const kind of ['external', 'config', 'revoked', 'expired']) {
    const f = await fixture({ quantity: '0.01', target: 0 });
    if (kind === 'external') f.state.principal.client.kind = 'external';
    if (kind === 'config') f.state.config.asset = 'ETH';
    if (kind === 'revoked') f.state.principal.grant.revoked_at = TIME - 1;
    if (kind === 'expired') f.state.principal.grant.expires_at = TIME - 1;
    if (['external', 'config'].includes(kind)) await assert.rejects(f.run(), { code: 'managed_binding_invalid' });
    else assert.equal((await f.run()).reason, 'wallet_authorization_inactive');
    assert.equal(f.calls.length, 0);
  }
});
test('pausing after durable preparation prevents submission and preserves the pending intent', async () => {
  const f = await fixture({ afterPrepared: state => { state.enabled = false; } });
  assert.equal((await f.run()).reason, 'managed_binding_changed'); assert.equal(f.calls.filter(c => c.op === 'submit').length, 0); assert.ok(f.state.pendingIntentId);
});
test('a strategy signal that expires during preparation never reaches submit', async () => {
  let time = TIME;
  const f = await fixture({ afterPrepared: () => { time = TIME + 31; } }); f.dependencies.clock = () => time;
  assert.equal((await f.run()).reason, 'managed_binding_changed'); assert.equal(f.calls.filter(c => c.op === 'submit').length, 0); assert.ok(f.state.pendingIntentId);
});
test('a substituted connection never reaches submit', async () => {
  const f = await fixture(); const original = f.dependencies.execution.prepare;
  f.dependencies.execution.prepare = async (...args) => { const result = await original(...args); result.connection.id = crypto.randomUUID(); return result; };
  await assert.rejects(f.run(), { code: 'managed_intent_binding_invalid' }); assert.equal(f.calls.filter(c => c.op === 'submit').length, 0);
});
test('authoritative settlement cannot sell another bot or manual allocation', async () => {
  const f = await fixture({ quantity: '0.01', target: 0 }); await f.run(); f.intent.state = 'filled';
  f.intent.filled = { quantity: '0.02', valueUsd: '2', feesUsd: '0.02', asOf: TIME }; f.intent.consumedBudgetUsd = 10;
  await assert.rejects(f.run(), { code: 'managed_allocation_invalid' }); assert.equal(f.applied, 0); assert.equal(f.state.allocation.quantity, '0.01');
});
