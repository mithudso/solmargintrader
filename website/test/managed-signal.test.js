import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';
import { prepareManagedBot, activateManagedBot } from '../src/managed-bots.js';
import { environment, seedUser, at, ORIGIN } from './helpers/d1.js';

const REVISION = 'a'.repeat(64);

async function fixture(t) {
  const env = environment();
  t.after(() => env.sqlite.close());
  const seeded = await seedUser(env);
  const user = seeded.user;
  const botId = crypto.randomUUID();
  const connectionId = crypto.randomUUID();
  const time = at();
  env.sqlite.prepare(`INSERT INTO bots(id,user_id,name,coin,strategy,venue,leverage,budget,mode,status,created_at,updated_at)
    VALUES (?,?,'Signal adapter fixture','SOL','rsi','coinbase',1,10,'paper','configured',?,?)`).run(botId, user.id, time, time);
  env.sqlite.prepare(`INSERT INTO customer_execution_connections(id,user_id,wallet,venue,credential_fingerprint,portfolio_id,created_at,verified_at)
    VALUES (?,?,?,'coinbase',?,?,?,?)`).run(connectionId, user.id, user.wallet, 'b'.repeat(64), crypto.randomUUID(), time, time);
  env.sqlite.prepare(`INSERT INTO subscriptions(user_id,stripe_subscription_id,status,period_end,updated_at,plan_id)
    VALUES (?,'sub_signal_fixture','active',?,?,'starter')`).run(user.id, time + 86400, time);
  const services = {
    origin: ORIGIN,
    async requireEntitlement(owner) {
      const sub = env.sqlite.prepare('SELECT * FROM subscriptions WHERE user_id=?').get(owner.id);
      if (sub?.status !== 'active' || sub.period_end <= at()) throw Error('subscription_required');
      return sub;
    },
    strategies: async () => ({ strategies: [{ id: 'rsi', strategyRevision: REVISION }] }),
    botLimit: () => 3,
  };
  const challenge = await prepareManagedBot(env, user, botId, {
    connectionId,
    interval: '1m',
    policy: { version: 2, venues: ['coinbase'], assets: ['SOL'], products: ['spot'], maxLeverage: 1,
      maxTradeUsd: 10, maxTotalUsd: 100, expiresAt: time + 3600 },
  }, services);
  const signature = Buffer.from(await crypto.subtle.sign('Ed25519', seeded.keys.privateKey,
    new TextEncoder().encode(challenge.message))).toString('base64');
  await activateManagedBot(env, user, botId, { challengeId: challenge.challengeId, signature }, services);

  Object.assign(env, {
    ENGINE_TOKEN: 'signal-fixture-engine-token-thirty-two-characters',
    EXECUTOR_TOKEN: 'signal-fixture-executor-token-thirty-two-characters',
    LIVE_EXECUTION_ENABLED: 'true',
    EXECUTOR_AVAILABLE_VENUES: '["coinbase"]',
  });
  const engineCalls = [];
  const executorCalls = [];
  const signal = {
    status: 'available', mode: 'spot', coin: 'SOL', strategy: 'rsi', interval: '1m', strategyRevision: REVISION,
    executionQuote: false, fillDelay: 1, inputHash: 'd'.repeat(64), sourceHash: 'e'.repeat(64),
    sourceIdentity: { sha256: 'b'.repeat(64) }, barEnd: time - 20,
    asOf: time - 5.25, expiresAt: time + 55.75, desiredExposure: 1,
  };
  env.ENGINE_SERVICE = { async fetch(request) {
    engineCalls.push({ path: new URL(request.url).pathname, method: request.method, body: await request.json() });
    return Response.json(signal);
  } };
  // The fixture stops at preparation. It implements no signing or order endpoint.
  env.USER_TRADE_EXECUTOR = { async fetch(request) {
    executorCalls.push({ path: new URL(request.url).pathname, body: await request.json() });
    return Response.json({ error: 'fixture_stop_before_signing' }, { status: 503 });
  } };
  return { env, user, botId, time, signal, engineCalls, executorCalls };
}

const cases = [
  { name: 'accepts fresh floating timestamps and structured source provenance', patch: () => ({}), prepares: true },
  { name: 'refuses a stale floating observation timestamp', patch: time => ({ asOf: time - 61.25 }) },
  { name: 'refuses a string in place of structured source provenance', patch: () => ({ sourceIdentity: 'b'.repeat(64) }) },
  { name: 'refuses a future bar', patch: time => ({ barEnd: time + 20 }) },
  { name: 'refuses fractional target exposure', patch: () => ({ desiredExposure: 0.5 }) },
  { name: 'refuses an execution quote in place of a research signal', patch: () => ({ executionQuote: true }) },
  { name: 'refuses a strategy revision different from the wallet authorization', patch: () => ({ strategyRevision: 'c'.repeat(64) }) },
  { name: 'refuses an expired floating expiry timestamp', patch: time => ({ expiresAt: time - 0.25 }) },
];

for (const scenario of cases) {
  test(`root managed signal adapter ${scenario.name}`, async t => {
    const f = await fixture(t);
    Object.assign(f.signal, scenario.patch(f.time));
    await worker.scheduled({ cron: '* * * * *' }, f.env);

    assert.deepEqual(f.engineCalls, [{ path: '/v1/signals', method: 'POST',
      body: { coin: 'SOL', strategy: 'rsi', interval: '1m' } }]);
    const saved = f.env.sqlite.prepare('SELECT last_reason,pending_intent_id FROM managed_bots WHERE bot_id=?').get(f.botId);
    const intents = f.env.sqlite.prepare('SELECT COUNT(*) AS n FROM agent_trade_intents WHERE user_id=?').get(f.user.id).n;
    assert.equal(saved.pending_intent_id, null);
    if (scenario.prepares) {
      assert.equal(f.executorCalls.length, 1);
      const call = f.executorCalls[0];
      assert.equal(call.path, '/v1/trades/prepare');
      assert.equal(call.body.userId, f.user.id);
      assert.equal(call.body.wallet, f.user.wallet);
      assert.deepEqual(call.body.trade, { venue: 'coinbase', asset: 'SOL', side: 'buy', budgetUsd: 10, product: 'spot', leverage: 1 });
      assert.equal(intents, 1);
      assert.equal(saved.last_reason, 'trade_preparation_refused');
    } else {
      assert.equal(f.executorCalls.length, 0);
      assert.equal(intents, 0);
      assert.equal(saved.last_reason, 'strategy_signal_unverified');
    }
  });
}
