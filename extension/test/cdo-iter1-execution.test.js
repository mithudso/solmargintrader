import test from 'node:test';
import assert from 'node:assert/strict';
import { ingestFills } from '../src/core/engine.js';
import { snapshot } from '../src/core/pnl.js';
import { recentreDecision } from '../src/core/grid.js';
import { computeAlerts, DEFAULT_PREFS } from '../src/core/alerts.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { DryRunVenue } from '../src/venues/index.js';
import { swapWithinRange, quoteSolana } from '../src/market/quote.js';
import { finish, summarise } from '../src/market/holdings.js';

test('CDO-44940d545a persisted execution repairs only its exact original intent', async () => {
  const store = new MemoryStore();
  await store.putIntent({ intentKey: 'original', gridId: 'g', venueOrderId: 'executed', status: 'unknown' });
  await store.putIntent({ intentKey: 'reused', gridId: 'g', venueOrderId: 'later', status: 'unknown' });
  await store.putFill({ id: 'executed', side: 'buy', gridId: 'g', baseQty: 1, priceUsd: 100, feeUsd: 0, tsMs: 1 });
  await ingestFills({ venue: { getFills: async () => [{ venueOrderId: 'executed' }] }, store, config: { gridId: 'g' } });
  assert.equal((await store.getIntent('original')).status, 'filled');
  assert.equal((await store.getIntent('reused')).status, 'unknown');
  assert.equal((await store.allFills()).length, 1);
});

test('CDO-fceab8682a unknown fees never become authoritative net results', () => {
  const fills = [{ id: 'b', side: 'buy', baseQty: 1, priceUsd: 100, feeUsd: 0, feeUnknown: true, tsMs: 1 },
    { id: 's', side: 'sell', baseQty: 1, priceUsd: 110, feeUsd: 1, tsMs: 2 }];
  const p = snapshot({ fills, markPriceUsd: 110 });
  assert.equal(p.accountingComplete, false);
  assert.equal(p.realizedNetUsd, null);
  assert.equal(p.totalNetUsd, null);
  assert.equal(p.realizedGrossUsd, 10);
  assert.equal(snapshot({ fills: fills.map(f => ({ ...f, feeUnknown: false })), markPriceUsd: 110 }).realizedNetUsd, 9);
});

test('CDO-c39f24e8c7 known unmatched execution fees are conserved', () => {
  const p = snapshot({ fills: [{ id: 's', side: 'sell', baseQty: 2, priceUsd: 100, feeUsd: 4, tsMs: 1 }], markPriceUsd: 100 });
  assert.equal(p.feeTotalUsd, 4);
  assert.equal(p.unmatchedSellQty, 2);
  assert.equal(p.accountingComplete, false);
  assert.equal(p.totalNetUsd, null);
});

test('CDO-87b9a8c064 simulated expiration is enforced before crossing', async () => {
  let now = 1000;
  const v = new DryRunVenue({ inner: { id: 'fixture', kind: 'spot', capabilities: {} }, clock: () => now });
  await v.placeOrder({ intent: { intentKey: 'i', side: 'buy', level: 100, baseQty: 1 }, slippageBps: 0, ttlMs: 1000 });
  now = 2000;
  assert.deepEqual(v.markPrice(99), []);
  assert.deepEqual(await v.getOpenOrders(), []);
});

test('CDO-ace05a8f34 tiny exact input cannot gain optimistic sqrt rounding', () => {
  const Q96 = 1n << 96n, MID = BigInt(Math.floor(Math.sqrt(1.0001 ** 50) * Number(Q96)));
  const r = swapWithinRange({ amountIn: 2n, sqrtPriceX96: MID, liquidity: 100n * Q96, feePips: 500, zeroForOne: true, tick: 50, tickSpacing: 100 });
  assert.equal(r.ok, true);
  assert.equal(r.sqrtNextX96, MID);
  assert.equal(r.amountOut, 0n);
});

test('CDO-925327e83b Solana quote binds raw amount and ExactIn mode', async () => {
  await assert.rejects(quoteSolana({ fetch: async url => { const q = new URL(url); return new Response(JSON.stringify({ inputMint: q.searchParams.get('inputMint'), outputMint: q.searchParams.get('outputMint'), inAmount: '1000000000', outAmount: '100', otherAmountThreshold: '200', swapMode: 'ExactOut', routePlan: [] })); } }, { from: 'SOL', to: 'USDC', amount: '0.5' }), /match|amount|quote/);
});

test('CDO-96de1d6a8e dust contributes to measured totals without display rows', () => {
  const chain = finish({ chain: 'base', status: 'ok', holdings: [{ included: true, stable: true, usd: .005 }], notes: [], errors: [] });
  assert.equal(chain.holdings.length, 0);
  assert.equal(chain.totalUsd, .005);
  assert.equal(summarise([chain]).stableUsd, .005);
});

test('CDO-b038862030 quantization refusal preserves valid existing ladder', () => {
  const r = recentreDecision({ config: { lower: .0002, upper: .0004, autoRecentre: true }, price: .0001 });
  assert.equal(r.allowed, false);
  assert.match(r.reason, /precision|quantiz/);
});
