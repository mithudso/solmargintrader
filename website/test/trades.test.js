import test from 'node:test';
import assert from 'node:assert/strict';
import { environment, seedUser, at, ORIGIN } from './helpers/d1.js';
import { requestTrade, submitTrade, getTradeStatus, listTradeIntents } from '../src/trades.js';

const services = { requireEntitlement: async () => {} };
const input = (key = 'trade-1', budgetUsd = 10) => ({ idempotencyKey: key, venue: 'jupiter', asset: 'SOL', side: 'buy', budgetUsd });
const digest = async value => Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))).toString('hex');
async function fixture(options = {}) {
  const env = environment(); const owner = await seedUser(env); const id = crypto.randomUUID(); const clientId = crypto.randomUUID();
  const policy = { venues: ['coinbase', 'jupiter'], assets: ['BTC', 'ETH', 'SOL', 'ZEC'], maxTradeUsd: options.maxTradeUsd || 20, maxTotalUsd: options.maxTotalUsd || 30, expiresAt: at() + 3600 };
  const json = JSON.stringify(policy); const policyHash = await digest(json); const scope = 'status:read trade:prepare trade:submit';
  env.sqlite.prepare('INSERT INTO agent_clients(id,name,redirect_uris,created_at) VALUES (?,?,?,?)').run(clientId, 'Test agent', '[]', at());
  env.sqlite.prepare('INSERT INTO agent_grants(id,user_id,client_id,resource,scope,policy_json,policy_hash,created_at,expires_at) VALUES (?,?,?,?,?,?,?,?,?)').run(id, owner.id, clientId, `${ORIGIN}/mcp`, scope, json, policyHash, at(), policy.expiresAt);
  env.sqlite.prepare("INSERT INTO subscriptions(user_id,stripe_subscription_id,status,period_end,updated_at,plan_id) VALUES (?,?,'active',?,?,'starter')").run(owner.id, `sub_test_${owner.id}`, at() + 3600, at());
  const principal = { user: owner.user, grant: { id, resource: `${ORIGIN}/mcp`, policy_hash: policyHash }, client: { id: clientId }, scopes: new Set(scope.split(' ')) };
  return { env, principal, policy };
}
function executor(env, changes = {}) {
  const calls = []; env.LIVE_EXECUTION_ENABLED = 'true';
  env.USER_TRADE_EXECUTOR = { async fetch(request) {
    assert.equal(request.headers.get('Authorization'), null);
    assert.equal(new URL(request.url).origin, 'https://customer-trade.internal');
    const body = await request.json(); const operation = new URL(request.url).pathname.split('/').at(-1); calls.push({ operation, body });
    if (changes[operation]) return changes[operation](body);
    const result = operation === 'prepare' ? {
      intentId: body.intentId, wallet: body.wallet, policyHash: body.policyHash, payloadHash: body.payloadHash,
      quote: { id: 'quote-1', priceUsd: 9, quantity: 1, feesUsd: 0.5, maxSpendUsd: 10, quotedAt: at(), expiresAt: Math.min(body.expiresAt, at() + 120) },
      delegation: { id: 'delegation-1', wallet: body.wallet, policyHash: body.policyHash, expiresAt: body.policy.expiresAt, verified: true },
      connection: { id: 'customer-1', wallet: body.wallet, venue: body.trade.venue, verified: true },
    } : {
      intentId: body.intentId, wallet: body.wallet, policyHash: body.policyHash, payloadHash: body.payloadHash,
      quoteId: body.preparation.quote.id, delegationId: body.preparation.delegation.id, status: 'submitted', orderId: 'order-1',
    };
    return Response.json(result);
  } };
  return calls;
}
function preparedResponse(body, change = {}) {
  return Response.json({ intentId: body.intentId, wallet: body.wallet, policyHash: body.policyHash, payloadHash: body.payloadHash,
    quote: { id: 'quote-1', priceUsd: 9, quantity: 1, feesUsd: 0.5, maxSpendUsd: 10, quotedAt: at(), expiresAt: at() + 90 },
    delegation: { id: 'delegation-1', wallet: body.wallet, policyHash: body.policyHash, expiresAt: body.policy.expiresAt, verified: true },
    connection: { id: 'customer-1', wallet: body.wallet, venue: body.trade.venue, verified: true }, ...change });
}
function captureEvents(t) {
  const events = [];
  for (const level of ['info', 'warn']) t.mock.method(console, level, message => {
    assert.equal(typeof message, 'string');
    const event = JSON.parse(message);
    assert.deepEqual(Object.keys(event).sort(), ['category', 'event', 'operation', 'outcome']);
    assert.equal(event.event, 'customer_trade_execution');
    assert.ok(['prepare', 'submit'].includes(event.operation));
    assert.ok(['started', 'prepared', 'submitted', 'refused', 'failed', 'unknown'].includes(event.outcome));
    assert.ok(['none', 'unavailable', 'timeout', 'response', 'binding', 'quote', 'delegation', 'connection', 'quote_hash', 'payload', 'receipt', 'authorization_changed', 'unknown'].includes(event.category));
    events.push({ level, ...event });
  });
  return events;
}

test('positive sub-cent and overprecision budgets refuse before reservation or customer execution', async () => {
  const { env, principal } = await fixture(); const calls = executor(env);
  for (const budgetUsd of [1e-9, 0.001, 1.000000001, 0.29000000000000004]) {
    await assert.rejects(requestTrade(env, principal, input('invalid-cent', budgetUsd), services), { code: 'invalid_trade' });
    assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM agent_trade_intents').get().n, 0);
    assert.equal(calls.length, 0);
  }
});
test('decimal cent budgets and policies preserve exact reservations and explicit zero fees', async () => {
  for (const [budgetUsd, expectedCents] of [[0.29, 29], [0.57, 57]]) {
    const { env, principal } = await fixture({ maxTradeUsd: budgetUsd, maxTotalUsd: budgetUsd });
    const calls = executor(env, { prepare: body => preparedResponse(body, {
      quote: { id: 'cent-quote', priceUsd: budgetUsd, quantity: 1, feesUsd: 0, maxSpendUsd: budgetUsd, quotedAt: at(), expiresAt: at() + 60 },
    }) });
    const intent = await requestTrade(env, principal, input('exact-cent', budgetUsd), services);
    assert.equal(intent.state, 'prepared'); assert.equal(intent.trade.budgetUsd, budgetUsd);
    assert.equal(intent.quote.feesUsd, 0); assert.equal(intent.budgetCommittedUsd, budgetUsd);
    assert.equal(env.sqlite.prepare('SELECT reservation_cents FROM agent_trade_intents WHERE id=?').get(intent.id).reservation_cents, expectedCents);
    assert.equal(calls.length, 1); assert.equal(calls[0].body.trade.budgetUsd, budgetUsd);
  }
});
test('signed policy monetary limits refuse sub-cent and overprecision values', async () => {
  for (const options of [{ maxTradeUsd: 1e-9 }, { maxTradeUsd: 1.000000001 }, { maxTradeUsd: 1, maxTotalUsd: 1.000000001 }]) {
    const { env, principal } = await fixture(options); const calls = executor(env);
    await assert.rejects(requestTrade(env, principal, input('invalid-policy', 0.01), services), { code: 'policy_required' });
    assert.equal(calls.length, 0); assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM agent_trade_intents').get().n, 0);
  }
});
test('execution events report unavailable and successful transitions without account data', async t => {
  const events = captureEvents(t); const { env, principal } = await fixture();
  await assert.rejects(requestTrade(env, principal, input(), services), { code: 'execution_unavailable' });
  const calls = executor(env); const intent = await requestTrade(env, principal, input(), services);
  const submitted = await submitTrade(env, principal, { intentId: intent.id }, services);
  assert.equal(submitted.state, 'submitted'); assert.equal(submitted.filled, null);
  assert.deepEqual(events.map(({ level, operation, outcome, category }) => [level, operation, outcome, category]), [
    ['warn', 'prepare', 'refused', 'unavailable'], ['info', 'prepare', 'started', 'none'], ['info', 'prepare', 'prepared', 'none'],
    ['info', 'submit', 'started', 'none'], ['info', 'submit', 'submitted', 'none'],
  ]);
  const serialized = JSON.stringify(events);
  for (const secret of [principal.user.id, principal.user.wallet, principal.grant.id, principal.grant.policy_hash, principal.client.id, intent.id, 'quote-1', 'order-1', 'delegation-1', 'customer-1']) assert.ok(!serialized.includes(secret));
  assert.equal(calls.length, 2);
});
test('preparation failures emit only fixed categories and never raw provider errors or bodies', async t => {
  const events = captureEvents(t); const secret = 'SECRET_EXECUTION_PAYLOAD';
  const cases = [
    ['timeout', () => { throw new DOMException(secret, 'TimeoutError'); }],
    ['unavailable', () => { throw new Error(secret); }],
    ['response', () => new Response(secret, { status: 503, headers: { 'Content-Type': 'application/json' } })],
    ['response', () => new Response(secret, { headers: { 'Content-Type': 'application/json' } })],
    ['binding', body => preparedResponse(body, { wallet: secret })],
    ['quote', body => preparedResponse(body, { quote: { secret } })],
    ['quote', body => preparedResponse(body, { quote: { id: 'q', priceUsd: 9, quantity: 1, feesUsd: 1e-9, maxSpendUsd: 10, quotedAt: at(), expiresAt: at() + 60 } })],
    ['delegation', body => preparedResponse(body, { delegation: { secret } })],
    ['connection', body => preparedResponse(body, { connection: { secret } })],
    ['authorization_changed', (body, env) => {
      env.sqlite.prepare('UPDATE agent_grants SET revoked_at=? WHERE id=?').run(at(), body.grantId);
      return preparedResponse(body);
    }],
  ];
  for (const [category, prepare] of cases) {
    const { env, principal } = await fixture(); executor(env, { prepare: body => prepare(body, env) });
    await assert.rejects(requestTrade(env, principal, input(), services), { code: 'preparation_unverified' });
    assert.deepEqual(events.slice(-2).map(({ operation, outcome, category }) => [operation, outcome, category]), [['prepare', 'started', 'none'], ['prepare', 'failed', category]]);
    assert.equal(env.sqlite.prepare('SELECT state FROM agent_trade_intents').get().state, 'failed');
    assert.ok(!JSON.stringify(events).includes(principal.user.wallet));
  }
  assert.ok(!JSON.stringify(events).includes(secret));
});
test('submission failure events retain ambiguous commitments and redact provider exceptions', async t => {
  const events = captureEvents(t); const secret = 'SECRET_SUBMISSION_PAYLOAD';
  for (const [category, submit] of [
    ['timeout', () => { throw new DOMException(secret, 'TimeoutError'); }],
    ['unavailable', () => { throw new Error(secret); }],
    ['receipt', () => Response.json({ secret })],
  ]) {
    const { env, principal } = await fixture({ maxTradeUsd: 10, maxTotalUsd: 10 }); const calls = executor(env, { submit });
    const intent = await requestTrade(env, principal, input(), services);
    const result = await submitTrade(env, principal, { intentId: intent.id }, services);
    assert.equal(result.state, 'unknown'); assert.equal(result.filled, null);
    assert.deepEqual(events.slice(-2).map(({ operation, outcome, category }) => [operation, outcome, category]), [['submit', 'started', 'none'], ['submit', 'unknown', category]]);
    env.sqlite.prepare('UPDATE agent_trade_intents SET expires_at=? WHERE id=?').run(at() - 10, intent.id);
    assert.equal((await submitTrade(env, principal, { intentId: intent.id }, services)).state, 'unknown');
    await assert.rejects(requestTrade(env, principal, input('second'), services), { code: 'policy_limit' });
    assert.equal(calls.length, 2); assert.ok(!JSON.stringify(events).includes(intent.id));
  }
  assert.ok(!JSON.stringify(events).includes(secret));
});
test('stored preparation refusals identify quote, hash and payload verification without an adapter retry', async t => {
  const events = captureEvents(t);
  for (const [category, corrupt] of [
    ['quote', (env, id) => env.sqlite.prepare('UPDATE agent_trade_intents SET quote_json=? WHERE id=?').run('[SECRET_STORED_QUOTE', id)],
    ['quote_hash', (env, id) => env.sqlite.prepare('UPDATE agent_trade_intents SET quote_hash=? WHERE id=?').run('SECRET_STORED_HASH', id)],
    ['payload', (env, id) => {
      const payload = JSON.parse(env.sqlite.prepare('SELECT payload_json FROM agent_trade_intents WHERE id=?').get(id).payload_json);
      env.sqlite.prepare('UPDATE agent_trade_intents SET payload_json=? WHERE id=?').run(JSON.stringify({ ...payload, budgetUsd: 9 }), id);
    }],
  ]) {
    const { env, principal } = await fixture(); const calls = executor(env);
    const intent = await requestTrade(env, principal, input(), services); corrupt(env, intent.id);
    await assert.rejects(submitTrade(env, principal, { intentId: intent.id }, services), { code: 'preparation_unverified' });
    assert.deepEqual(events.at(-1), { level: 'warn', event: 'customer_trade_execution', operation: 'submit', outcome: 'refused', category });
    assert.equal(calls.length, 1); assert.equal(env.sqlite.prepare('SELECT state FROM agent_trade_intents WHERE id=?').get(intent.id).state, 'prepared');
  }
  assert.doesNotMatch(JSON.stringify(events), /SECRET_STORED/);
});
test('an unexpected receipt-storage failure emits unknown and keeps the submitted commitment reserved', async t => {
  const events = captureEvents(t); const { env, principal } = await fixture({ maxTradeUsd: 10, maxTotalUsd: 10 }); const calls = executor(env);
  const intent = await requestTrade(env, principal, input(), services);
  const prepare = env.DB.prepare.bind(env.DB);
  t.mock.method(env.DB, 'prepare', sql => {
    const statement = prepare(sql);
    if (sql.includes("SET state='submitted'")) statement.run = async () => { throw new Error('SECRET_STORAGE_FAILURE'); };
    return statement;
  });
  const result = await submitTrade(env, principal, { intentId: intent.id }, services);
  assert.equal(result.state, 'unknown'); assert.equal(result.orderId, null); assert.equal(result.filled, null);
  assert.deepEqual(events.at(-1), { level: 'warn', event: 'customer_trade_execution', operation: 'submit', outcome: 'unknown', category: 'unknown' });
  env.sqlite.prepare('UPDATE agent_trade_intents SET expires_at=? WHERE id=?').run(at() - 10, intent.id);
  assert.equal((await submitTrade(env, principal, { intentId: intent.id }, services)).state, 'unknown');
  await assert.rejects(requestTrade(env, principal, input('second'), services), { code: 'policy_limit' });
  assert.equal(calls.length, 2); assert.doesNotMatch(JSON.stringify(events), /SECRET_STORAGE_FAILURE/);
});

test('default refuses before reservation and cannot use an owner key or a truthy flag', async () => {
  const { env, principal } = await fixture();
  env.OWNER_PRIVATE_KEY = 'unused-test-marker';
  for (const flag of [undefined, 'false', true, '1']) {
    env.LIVE_EXECUTION_ENABLED = flag;
    let called = 0; env.USER_TRADE_EXECUTOR = { fetch() { called++; throw new Error(); } };
    await assert.rejects(requestTrade(env, principal, input(), services), { code: 'execution_unavailable' }); assert.equal(called, 0);
  }
  assert.equal(env.sqlite.prepare('SELECT COUNT(*) AS n FROM agent_trade_intents').get().n, 0);
});
test('only the token wallet owns prepared intents and customer execution requests', async () => {
  const { env, principal } = await fixture(); const calls = executor(env);
  const intent = await requestTrade(env, principal, input(), services);
  assert.equal(intent.wallet, principal.user.wallet); assert.equal(intent.state, 'prepared'); assert.equal(intent.requiresWalletApproval, false);
  assert.equal(calls[0].body.wallet, principal.user.wallet); assert.equal(calls[0].body.userId, principal.user.id);
  const other = await seedUser(env); const attacker = { ...principal, user: other.user };
  await assert.rejects(getTradeStatus(env, attacker, { intentId: intent.id }), { code: 'intent_not_found' });
  await assert.rejects(submitTrade(env, attacker, { intentId: intent.id }, services), { code: 'intent_not_found' });
  assert.deepEqual(await listTradeIntents(env, attacker), []);
  for (const field of ['wallet', 'userId', 'account', 'signer', 'url', '__proto__']) {
    const malicious = JSON.parse(JSON.stringify(input())); Object.defineProperty(malicious, field, { value: 'override', enumerable: true });
    await assert.rejects(requestTrade(env, principal, malicious, services), { code: 'invalid_trade' });
  }
  assert.equal(calls.length, 1);
});
test('concurrent requests reserve only the final available policy slot', async () => {
  const { env, principal } = await fixture({ maxTradeUsd: 10, maxTotalUsd: 10 }); const calls = executor(env);
  const results = await Promise.allSettled([requestTrade(env, principal, input('a'), services), requestTrade(env, principal, input('b'), services)]);
  assert.equal(results.filter(result => result.status === 'fulfilled').length, 1);
  assert.equal(results.find(result => result.status === 'rejected').reason.code, 'policy_limit'); assert.equal(calls.length, 1);
  assert.equal(env.sqlite.prepare('SELECT SUM(reservation_cents) AS n FROM agent_trade_intents').get().n, 1000);
});
test('concurrent idempotency returns the original intent and changed payloads refuse', async () => {
  const { env, principal } = await fixture(); const calls = executor(env);
  const results = await Promise.all([requestTrade(env, principal, input(), services), requestTrade(env, principal, input(), services)]);
  assert.equal(results[0].id, results[1].id); assert.equal(calls.length, 1);
  assert.equal((await requestTrade(env, principal, input(), services)).id, results[0].id);
  await assert.rejects(requestTrade(env, principal, { ...input(), side: 'sell' }, services), { code: 'idempotency_conflict' });
  assert.equal(calls.length, 1);
});
test('valid mock delegation submits once without a repeated wallet prompt and never claims a fill', async () => {
  const { env, principal } = await fixture(); const calls = executor(env);
  const intent = await requestTrade(env, principal, input(), services);
  const result = await Promise.all([submitTrade(env, principal, { intentId: intent.id }, services), submitTrade(env, principal, { intentId: intent.id }, services)]);
  assert.ok(result.every(value => ['submitting', 'submitted'].includes(value.state)));
  const final = await getTradeStatus(env, principal, { intentId: intent.id });
  assert.equal(final.state, 'submitted'); assert.equal(final.orderId, 'order-1'); assert.equal(final.filled, null);
  assert.equal(calls.filter(call => call.operation === 'submit').length, 1);
  const submit = calls.find(call => call.operation === 'submit').body;
  assert.equal(submit.idempotencyKey, intent.id); assert.equal(submit.preparation.wallet, principal.user.wallet); assert.match(submit.preparationHash, /^[a-f0-9]{64}$/);
  await submitTrade(env, principal, { intentId: intent.id }, services); assert.equal(calls.length, 2);
});
test('ambiguous submission retains the budget after quote expiry and cannot resubmit', async () => {
  const { env, principal } = await fixture({ maxTradeUsd: 10, maxTotalUsd: 10 });
  const calls = executor(env, { submit() { throw new Error('ambiguous transport failure with private provider data'); } });
  const intent = await requestTrade(env, principal, input(), services);
  const result = await submitTrade(env, principal, { intentId: intent.id }, services);
  assert.equal(result.state, 'unknown'); assert.equal(result.error, 'submission_unknown');
  env.sqlite.prepare('UPDATE agent_trade_intents SET expires_at=? WHERE id=?').run(at() - 10, intent.id);
  assert.equal((await submitTrade(env, principal, { intentId: intent.id }, services)).state, 'unknown');
  await assert.rejects(requestTrade(env, principal, input('another'), services), { code: 'policy_limit' });
  assert.equal(calls.length, 2); assert.doesNotMatch(JSON.stringify(result), /private provider/);
});
test('unverified receipts become unknown and strict output never exposes provider extras', async () => {
  for (const change of [{ wallet: 'another-wallet' }, { quoteId: 'wrong' }, { policyHash: 'wrong' }, { payloadHash: 'wrong' }, { intentId: 'wrong' }, { delegationId: 'wrong' }, { secret: 'private-test' }]) {
    const { env, principal } = await fixture();
    executor(env, { submit: body => Response.json({ intentId: body.intentId, wallet: body.wallet, policyHash: body.policyHash, payloadHash: body.payloadHash, quoteId: body.preparation.quote.id, delegationId: body.preparation.delegation.id, status: 'submitted', orderId: 'order-1', ...change }) });
    const intent = await requestTrade(env, principal, input(), services);
    const result = await submitTrade(env, principal, { intentId: intent.id }, services);
    assert.equal(result.state, 'unknown'); assert.equal(result.orderId, null); assert.doesNotMatch(JSON.stringify(result), /private-test/);
  }
});
test('wrong wallet, stale or incomplete quote, missing fees and expired delegated authority refuse before submit', async () => {
  const cases = [
    body => ({ wallet: 'wrong-wallet' }),
    body => ({ payloadHash: 'wrong' }),
    body => ({ quote: { id: 'q', priceUsd: 9, quantity: 1, feesUsd: 0.5, maxSpendUsd: 10, quotedAt: at(), expiresAt: at() - 1 } }),
    body => ({ quote: { id: 'q', priceUsd: 9, quantity: 1, feesUsd: 0.5, maxSpendUsd: 10, quotedAt: at() - 61, expiresAt: at() + 60 } }),
    body => ({ quote: { id: 'q', priceUsd: 9, quantity: 1, maxSpendUsd: 10, quotedAt: at(), expiresAt: at() + 60 } }),
    body => ({ quote: { id: 'q', priceUsd: 9, quantity: 1, feesUsd: 2, maxSpendUsd: 11, quotedAt: at(), expiresAt: at() + 60 } }),
    body => ({ quote: { id: 'q', priceUsd: 11, quantity: 1, feesUsd: 0, maxSpendUsd: 10, quotedAt: at(), expiresAt: at() + 60 } }),
    body => ({ delegation: { id: 'd', wallet: body.wallet, policyHash: body.policyHash, expiresAt: at() - 1, verified: true } }),
    body => ({ delegation: { id: 'd', wallet: 'wrong', policyHash: body.policyHash, expiresAt: body.policy.expiresAt, verified: true } }),
    body => ({ connection: { id: 'c', wallet: body.wallet, venue: 'coinbase', verified: true } }),
  ];
  for (const change of cases) {
    const { env, principal } = await fixture(); const calls = executor(env, { prepare: body => preparedResponse(body, change(body)) });
    await assert.rejects(requestTrade(env, principal, input(), services), { code: 'preparation_unverified' });
    assert.equal(calls.length, 1); assert.equal(env.sqlite.prepare('SELECT state FROM agent_trade_intents').get().state, 'failed');
  }
});
test('revocation, current subscription expiry and tampered quotes prevent submission', async () => {
  for (const scenario of ['revoked', 'subscription', 'quote']) {
    const { env, principal } = await fixture(); const calls = executor(env);
    const intent = await requestTrade(env, principal, input(), services);
    if (scenario === 'revoked') env.sqlite.prepare('UPDATE agent_grants SET revoked_at=? WHERE id=?').run(at(), principal.grant.id);
    if (scenario === 'subscription') env.sqlite.prepare('UPDATE subscriptions SET period_end=? WHERE user_id=?').run(at() - 1, principal.user.id);
    if (scenario === 'quote') env.sqlite.prepare("UPDATE agent_trade_intents SET quote_json='{}' WHERE id=?").run(intent.id);
    await assert.rejects(submitTrade(env, principal, { intentId: intent.id }, services)); assert.equal(calls.length, 1);
  }
});
test('revocation while preparing cannot resurrect an expired or revoked reservation', async () => {
  const { env, principal } = await fixture(); const calls = executor(env, { prepare: body => {
    env.sqlite.prepare('UPDATE agent_grants SET revoked_at=? WHERE id=?').run(at(), principal.grant.id);
    return preparedResponse(body);
  } });
  await assert.rejects(requestTrade(env, principal, input(), services), { code: 'preparation_unverified' });
  assert.equal(calls.length, 1); assert.equal(env.sqlite.prepare('SELECT state FROM agent_trade_intents').get().state, 'failed');
});
test('policy and USD validation fail before contacting customer execution', async () => {
  const { env, principal } = await fixture(); const calls = executor(env);
  for (const args of [{ ...input(), budgetUsd: 1.001 }, { ...input(), budgetUsd: 0 }, { ...input(), budgetUsd: '10' }, { ...input(), leverage: 2 }, { ...input(), side: 'long' }, { ...input(), product: 'perpetual', side: 'long', venue: 'coinbase' }, { ...input(), product: 'perpetual', side: 'long', asset: 'ZEC' }]) {
    await assert.rejects(requestTrade(env, principal, args, services), { code: 'invalid_trade' });
  }
  await assert.rejects(requestTrade(env, principal, input('over-limit', 21), services), { code: 'policy_limit' });
  const noScope = { ...principal, scopes: new Set(['status:read']) };
  await assert.rejects(requestTrade(env, noScope, input(), services), { code: 'insufficient_scope' });
  await assert.rejects(requestTrade(env, principal, input(), { requireEntitlement: async () => { throw new Error('subscription expired'); } }));
  assert.equal(calls.length, 0);
});

// A webhook can invalidate a plan after the initial entitlement read. The
// reservation and submit statement must each fence the current canonical plan.
test('atomic trade writes reject a plan removed after the entitlement read', async () => {
  for (const invalid of [null]) {
    const preparing = await fixture(); const preparedCalls = executor(preparing.env);
    const changed = { requireEntitlement: async user => {
      assert.equal(preparing.env.sqlite.prepare('SELECT plan_id FROM subscriptions WHERE user_id=?').get(user.id).plan_id, 'starter');
      preparing.env.sqlite.prepare('UPDATE subscriptions SET plan_id=? WHERE user_id=?').run(invalid, user.id);
    } };
    await assert.rejects(requestTrade(preparing.env, preparing.principal, input(), changed), error => error.code === 'policy_limit');
    assert.equal(preparedCalls.length, 0);
    assert.equal(preparing.env.sqlite.prepare('SELECT COUNT(*) AS n FROM agent_trade_intents').get().n, 0);

    const submitting = await fixture(); const calls = executor(submitting.env);
    const intent = await requestTrade(submitting.env, submitting.principal, input(), services);
    await assert.rejects(submitTrade(submitting.env, submitting.principal, { intentId: intent.id }, { requireEntitlement: async user => {
      assert.equal(submitting.env.sqlite.prepare('SELECT plan_id FROM subscriptions WHERE user_id=?').get(user.id).plan_id, 'starter');
      submitting.env.sqlite.prepare('UPDATE subscriptions SET plan_id=? WHERE user_id=?').run(invalid, user.id);
    } }), error => error.code === 'intent_not_ready');
    assert.equal(calls.filter(call => call.operation === 'submit').length, 0);
    assert.equal(submitting.env.sqlite.prepare('SELECT state FROM agent_trade_intents WHERE id=?').get(intent.id).state, 'prepared');
  }
});
