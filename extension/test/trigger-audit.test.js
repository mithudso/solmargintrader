import test from 'node:test';
import assert from 'node:assert/strict';
import { TriggerVenue, normaliseOrders } from '../src/venues/triggerVenue.js';
import { listOrders, initiateCancel, confirmCancel, resolveVault, validateOrderBody } from '../src/jupiter/trigger.js';

const BASE = 'BASE';
const QUOTE = 'QUOTE';
const order = { id: 'order-1', triggerCondition: 'below', triggerMint: BASE,
  triggerPriceUsd: 100, inputMint: QUOTE, outputMint: BASE };
function venue(fetchImpl) {
  const result = new TriggerVenue({ baseMint: BASE, quoteMint: QUOTE, userPubkey: 'USER',
    signer: { signVerifiedTriggerDeposit: async () => 'signed', signVerifiedTriggerCancellation: async () => 'signed' }, fetchImpl });
  result.jwt = 'unit-jwt'; result.jwtExpiresAtMs = Date.now() + 86_400_000; result.vault = {};
  return result;
}
const json = (value) => new Response(JSON.stringify(value));

test('CDO-0c6241b439 active execution quantities require reconciliation', async () => {
  for (const evidence of [{ filledBaseQty: .5 }, { inputUsed: '1' }, { outputAmount: '1' }]) {
    await assert.rejects(venue(async () => json({ orders: [{ ...order, ...evidence }], pagination: { total: 1, limit: 100, offset: 0 } })).getOpenOrders(), /execution/);
  }
});

test('CDO-561bf176f9 invalid trigger prices refuse before transport or verifier', async () => {
  for (const level of [-1, 0, NaN, Infinity, '100', true, undefined]) {
    let calls = 0;
    const v = venue(async () => { calls++; throw new Error('side effect forbidden'); });
    await assert.rejects(v.placeOrder({ intent: { side: 'buy', notionalUsd: 100, level }, slippageBps: 100, ttlMs: 60000 }), /price|level/i);
    assert.equal(calls, 0);
    assert.ok(validateOrderBody({ inputMint: 'a', outputMint: 'b', expiresAt: Date.now() + 60000, triggerPriceUsd: level }).some(x => /price|exactly one/i.test(x)));
  }
});

test('CDO-1306963477 unrelated vault lookup failures never register', async () => {
  const calls = [];
  await assert.rejects(resolveVault({ fetchImpl: async url => { calls.push(url); return new Response('', { status: 401 }); } }));
  assert.equal(calls.length, 1);
  assert.ok(!calls.some(url => url.endsWith('/register')));
});

test('missing mint decimals refuse order sizing instead of guessing SPL conventions', async () => {
  await assert.rejects(() => venue(async () => json({ [BASE]: { usdPrice: 100 } })).getDecimals(), /decimal/i);
});

test('a raw cryptographic signer cannot sign a remotely crafted transfer without semantic verification', async () => {
  let network = 0; let signed = 0;
  const v = new TriggerVenue({ baseMint: BASE, quoteMint: QUOTE, userPubkey: 'USER',
    signer: { signTransactionBase64: async () => { signed++; return 'signed-unrelated-transfer'; } },
    fetchImpl: async () => { network++; return json({ requestId: 'req', transaction: 'unrelated-transfer' }); } });
  await assert.rejects(() => v.placeOrder({ intent: { side: 'buy', notionalUsd: 12, level: 100 },
    slippageBps: 100, ttlMs: 60_000 }), /verif/i);
  assert.equal(network, 0);
  assert.equal(signed, 0);
  assert.equal(v.capabilities.canPlaceLive, false);
});

test('order identifiers and numeric financial fields reject coercion', () => {
  for (const id of ['', ' ', true, {}, [], 5]) {
    assert.throws(() => normaliseOrders([{ ...order, id }]), /venueOrderId/);
  }
  for (const triggerPriceUsd of [true, [100], {}]) {
    assert.throws(() => normaliseOrders([{ ...order, triggerPriceUsd }]), /triggerPriceUsd/);
  }
  for (const feeUsd of ['', ' ', false, true, [], -1]) {
    const [result] = normaliseOrders([{ ...order, feeUsd }]);
    assert.equal(result.feeUsd, null);
    assert.equal(result.feeUnknown, true);
  }
  const [sell] = normaliseOrders([{ ...order, triggerCondition: 'above', filledOutputAmount: 400 }]);
  assert.equal(sell.filledBaseQty, null, 'output units cannot be assumed to be base units');
});

test('wallet-wide history is isolated to the configured directed mint pair', async () => {
  const v = venue(async () => json({ orders: [order, { ...order, id: 'foreign', inputMint: 'OTHER' }],
    pagination: { total: 2, limit: 100, offset: 0 } }));
  assert.deepEqual((await v.getOpenOrders()).map((x) => x.venueOrderId), ['order-1']);
  assert.deepEqual((await v.getFills()).map((x) => x.venueOrderId), ['order-1']);
  await assert.rejects(() => venue(async () => json({ orders: [{ ...order, inputMint: undefined }],
    pagination: { total: 1, limit: 100, offset: 0 } })).getOpenOrders(), /mint/i);
});

test('buy deposit and order use measured quote USD conversion consistently', async () => {
  const bodies = [];
  const v = venue(async (url, init) => {
    if (url.includes('/price/v3')) return json({ [BASE]: { decimals: 9, usdPrice: 100 }, [QUOTE]: { decimals: 6, usdPrice: 2 } });
    const body = JSON.parse(init.body); bodies.push(body);
    return json(url.endsWith('/deposit/craft') ? { requestId: 'req', transaction: 'unsigned' } : { id: 'order-1' });
  });
  await v.placeOrder({ intent: { side: 'buy', notionalUsd: 100, baseQty: 1, level: 100 }, slippageBps: 100, ttlMs: 60_000 });
  assert.equal(bodies[0].amount, '50000000');
  assert.equal(bodies[1].inputAmount, bodies[0].amount);
});

test('deposit errors never echo untrusted response values', async () => {
  const v = venue(async (url) => url.includes('/price/v3')
    ? json({ [BASE]: { decimals: 9, usdPrice: 100 }, [QUOTE]: { decimals: 6, usdPrice: 1 } })
    : json({ token: 'TEST_PRIVATE_VALUE' }));
  await assert.rejects(() => v.placeOrder({ intent: { side: 'buy', notionalUsd: 100, level: 100 }, slippageBps: 100, ttlMs: 60_000 }),
    (err) => /requestId/.test(err.message) && !err.message.includes('TEST_PRIVATE_VALUE'));
});

test('history client follows every validated page using documented state parameter', async () => {
  const seen = [];
  const result = await listOrders({ status: 'active', fetchImpl: async (url) => {
    const u = new URL(url); seen.push(u);
    const offset = Number(u.searchParams.get('offset'));
    return json({ orders: [{ ...order, id: `order-${offset}` }], pagination: { total: 2, limit: 1, offset } });
  } });
  assert.equal(seen.length, 2);
  assert.equal(seen[0].pathname, '/trigger/v2/orders/history');
  assert.equal(seen[0].searchParams.get('state'), 'active');
  assert.equal(result.orders.length, 2);
});

test('cancel client uses documented routes and includes the cancellation request ID', async () => {
  const seen = [];
  const fetchImpl = async (url, init) => { seen.push({ url, init }); return json({ id: 'o' }); };
  await initiateCancel({ orderId: 'o', fetchImpl });
  await confirmCancel({ orderId: 'o', signedTx: 'signed', cancelRequestId: 'cancel-req', fetchImpl });
  assert.ok(seen[0].url.endsWith('/orders/price/cancel/o'));
  assert.ok(seen[1].url.endsWith('/orders/price/confirm-cancel/o'));
  assert.deepEqual(JSON.parse(seen[1].init.body), { signedTransaction: 'signed', cancelRequestId: 'cancel-req' });
});
