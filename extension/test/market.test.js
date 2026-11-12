import test from 'node:test';
import assert from 'node:assert/strict';

import { words, intArray, signed, abiString, fromUnits, toUnits, word, intWord, addressOf, hexToBigInt, SELECTOR } from '../src/market/evm.js';
import { assertReadMethod, fetchOf, rpcBatch, MarketError } from '../src/market/net.js';
import { readBase, readSolana, finish, summarise } from '../src/market/holdings.js';
import { normalisePool, rankPools, newPoolIds } from '../src/market/pools.js';
import { swapWithinRange, activeRange, quoteBase, quoteSolana, quote } from '../src/market/quote.js';
import { BASE, findToken } from '../src/market/tokens.js';

/* ------------------------------------------------------------- fixtures -- */

const reply = (body, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  headers: { get: () => null },
  text: async () => (typeof body === 'string' ? body : JSON.stringify(body)),
});

/**
 * A fetch stub. `routes` maps a URL prefix to a function (url, parsedBody) => body.
 * Every request is recorded so tests can assert nothing but reads went out.
 */
function stubFetch(routes) {
  const calls = [];
  const fetch = async (url, init = {}) => {
    const body = init.body ? JSON.parse(init.body) : null;
    calls.push({ url, method: init.method ?? 'GET', body });
    const key = Object.keys(routes).find((k) => url.startsWith(k));
    if (!key) return reply({ error: 'no route' }, 404);
    const out = await routes[key](url, body);
    return out?.__status ? reply(out.body, out.__status) : reply(out);
  };
  return { fetch, calls };
}

const hex = (n) => `0x${BigInt(n).toString(16)}`;
const uintWord = (n) => `0x${BigInt(n).toString(16).padStart(64, '0')}`;
const OWNER = '0x901a89cEC0608eB5435A915f006b45bD46405314';
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const SOL_OWNER = 'EMTK62aecgScjEuZqbqeGquk8cBoQF9Z4DnxQZxn8myV';

/** A Base JSON-RPC batch handler: chain id, ETH balance and per-token balanceOf. */
function baseRpc({ chainId = BASE.chainIdHex, eth = 10n ** 17n, balances = {} } = {}) {
  return (_url, batch) => batch.map((req) => {
    if (req.method === 'eth_chainId') return { jsonrpc: '2.0', id: req.id, result: chainId };
    if (req.method === 'eth_getBalance') return { jsonrpc: '2.0', id: req.id, result: hex(eth) };
    if (req.method === 'eth_call') {
      const to = req.params[0].to.toLowerCase();
      const v = balances[to];
      return v === undefined ? { jsonrpc: '2.0', id: req.id, result: uintWord(0) } : v === 'error'
        ? { jsonrpc: '2.0', id: req.id, error: { code: -32000, message: 'execution reverted' } }
        : { jsonrpc: '2.0', id: req.id, result: uintWord(v) };
    }
    return { jsonrpc: '2.0', id: req.id, error: { message: 'unexpected' } };
  });
}

/* ------------------------------------------------------------------ evm -- */

test('ABI helpers decode words, signed ints, int arrays, strings and units', () => {
  assert.deepEqual(words('0x' + '0'.repeat(63) + '5' + '0'.repeat(63) + '7'), [5n, 7n]);
  assert.equal(signed((1n << 24n) - 1n, 24), -1n);
  assert.equal(intWord(-1), 'f'.repeat(64));
  // tickSpacings() as the live factory answered it on 2026-11-07.
  const live = '0x' + [0x20, 7, 1, 10, 50, 100, 150, 200, 250].map((n) => n.toString(16).padStart(64, '0')).join('');
  assert.deepEqual(intArray(live), [1, 10, 50, 100, 150, 200, 250]);
  const str = '0x' + (32).toString(16).padStart(64, '0') + (4).toString(16).padStart(64, '0') + Buffer.from('USDC').toString('hex').padEnd(64, '0');
  assert.equal(abiString(str), 'USDC');
  assert.equal(abiString('0x' + Buffer.from('MKR').toString('hex').padEnd(64, '0')), 'MKR');
  assert.equal(fromUnits('1.5', 6), 1_500_000n);
  assert.equal(fromUnits('2', 0), 2n);
  assert.throws(() => fromUnits('0.0000001', 6), /decimal places/);
  assert.throws(() => fromUnits('-1', 6), /plain positive decimal/);
  assert.throws(() => fromUnits('1e3', 6), /plain positive decimal/);
  assert.equal(toUnits(1_500_000n, 6), 1.5);
  assert.equal(word(USDC), USDC.slice(2).toLowerCase().padStart(64, '0'));
  assert.throws(() => word('0x123'), /not an EVM address/);
  assert.equal(addressOf(uintWord(0)), '0x0000000000000000000000000000000000000000');
  // Junk from an endpoint is "no answer", never a SyntaxError out of BigInt.
  assert.deepEqual(words('0xnot-hex'), []);
  assert.equal(hexToBigInt('0x1f'), 31n);
  assert.equal(hexToBigInt('nope'), null);
  assert.equal(hexToBigInt('0x'), null);
  assert.equal(hexToBigInt(42), null);
});

test('readBase survives a junk balance from the endpoint, and readHoldings keeps the other chain', async () => {
  const { fetch } = stubFetch({
    'https://rpc': (_u, batch) => batch.map((req) => ({ jsonrpc: '2.0', id: req.id,
      result: req.method === 'eth_chainId' ? BASE.chainIdHex : req.method === 'eth_getBalance' ? 'garbage' : '0xzz' })),
  });
  const r = await readBase({ fetch }, OWNER, { rpcs: ['https://rpc'] });
  assert.equal(r.holdings.length, 0);
  assert.ok(r.notes.some((n) => /no answer for ETH/.test(n)));
});

/* ------------------------------------------------------------------ net -- */

test('market reads refuse any non-read RPC method and a surface without fetch', async () => {
  for (const m of ['eth_sendRawTransaction', 'eth_sendTransaction', 'sendTransaction', 'eth_sign', 'personal_sign']) {
    assert.throws(() => assertReadMethod(m), /refusing non-read method/);
  }
  for (const m of ['eth_call', 'eth_chainId', 'eth_getBalance', 'getBalance', 'getTokenAccountsByOwner']) assertReadMethod(m);
  assert.throws(() => fetchOf({}), MarketError);
  await assert.rejects(() => rpcBatch({ fetch: async () => reply([]) }, ['https://x'], [['eth_sendRawTransaction', []]]), /non-read/);
});

test('rpcBatch falls through to the next endpoint and maps per-call errors to null', async () => {
  const { fetch, calls } = stubFetch({
    'https://down': () => ({ __status: 503, body: 'no' }),
    'https://up': (_u, batch) => batch.map((r) => (r.id === 0 ? { id: 0, result: '0x1' } : { id: 1, error: { message: 'bad' } })),
  });
  const out = await rpcBatch({ fetch }, ['https://down', 'https://up'], [['eth_chainId', []], ['eth_call', [{}, 'latest']]]);
  assert.deepEqual(out, ['0x1', null]);
  assert.deepEqual(calls.map((c) => c.url), ['https://down', 'https://up']);
});

/* ------------------------------------------------------------- holdings -- */

test('readBase values ETH and tokens, skips low-confidence prices and never calls a write', async () => {
  const { fetch, calls } = stubFetch({
    'https://rpc': baseRpc({ balances: { [USDC.toLowerCase()]: 25_000_000n, '0x3f5bf3edac59d650d8fdf9657a71f2f904a3a4ee': 10n ** 18n } }),
    'https://coins.llama.fi': () => ({ coins: {
      'coingecko:ethereum': { price: 2000, confidence: 0.99 },
      [`base:${USDC}`]: { price: 1, confidence: 0.99 },
      'base:0x3f5bF3EdAc59d650D8fDf9657a71F2f904A3a4Ee': { price: 0.6, confidence: 0.2 },
    } }),
  });
  const r = await readBase({ fetch }, OWNER, { rpcs: ['https://rpc'] });
  assert.equal(r.status, 'ok');
  const by = Object.fromEntries(r.holdings.map((h) => [h.symbol, h]));
  assert.equal(by.ETH.usd, 200);
  assert.equal(by.USDC.usd, 25);
  assert.equal(by.AERO.priceUsd, null, 'a 0.2-confidence price is not used');
  assert.equal(r.totalUsd, 225);
  assert.equal(r.usdComplete, false, 'an unpriced holding leaves the total incomplete');
  for (const c of calls.filter((x) => x.body)) for (const req of c.body) assert.match(req.method, /^eth_(chainId|getBalance|call)$/);
});

test('readBase refuses an endpoint on the wrong chain and fails cleanly when every RPC is down', async () => {
  const wrong = stubFetch({ 'https://rpc': baseRpc({ chainId: '0x1' }) });
  const r1 = await readBase({ fetch: wrong.fetch }, OWNER, { rpcs: ['https://rpc'] });
  assert.equal(r1.status, 'failed');
  assert.match(r1.errors[0], /expected 0x2105/);
  assert.equal(r1.holdings.length, 0);

  const down = stubFetch({ 'https://rpc': () => ({ __status: 500, body: 'x' }) });
  const r2 = await readBase({ fetch: down.fetch }, OWNER, { rpcs: ['https://rpc'] });
  assert.equal(r2.status, 'failed');
  assert.equal(r2.usdComplete, false);

  const skipped = await readBase({ fetch: down.fetch }, null);
  assert.equal(skipped.status, 'skipped');
});

test('readSolana counts priced tokens and lists, but does not count, an unknown unpriced mint', async () => {
  const unknownMint = 'AirDrop1111111111111111111111111111111111111';
  const { fetch } = stubFetch({
    'https://sol': (_u, req) => {
      if (req.method === 'getBalance') return { id: 1, result: { value: 2_000_000_000 } };
      const program = req.params[1].programId;
      const accounts = program.startsWith('Tokenkeg') ? [
        { account: { data: { parsed: { info: { mint: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', tokenAmount: { uiAmountString: '10' } } } } } },
        { account: { data: { parsed: { info: { mint: unknownMint, tokenAmount: { uiAmountString: '1000000' } } } } } },
        { account: { data: { parsed: { info: { mint: 'Thin111111111111111111111111111111111111111', tokenAmount: { uiAmountString: '100' } } } } } },
        { account: { data: { parsed: { info: { mint: 'bad&ids=x', tokenAmount: { uiAmountString: '1' } } } } } },
        { account: { data: { parsed: { info: { mint: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', tokenAmount: { uiAmountString: '0' } } } } } },
      ] : [];
      return { id: 1, result: { value: accounts } };
    },
    'https://lite-api.jup.ag/price': () => ({
      So11111111111111111111111111111111111111112: { usdPrice: 100 },
      EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v: { usdPrice: 1 },
      // Priced, unknown, and too thin to sell into: listed, not counted.
      Thin111111111111111111111111111111111111111: { usdPrice: 5, liquidity: 900 },
    }),
  });
  const r = await readSolana({ fetch }, SOL_OWNER, { rpcs: ['https://sol'] });
  const by = Object.fromEntries(r.holdings.map((h) => [h.symbol, h]));
  assert.equal(by.SOL.usd, 200);
  assert.equal(by.USDC.usd, 10);
  const airdrop = r.holdings.find((h) => h.address === unknownMint);
  assert.equal(airdrop.included, false);
  assert.equal(airdrop.unverified, true);
  const thin = r.holdings.find((h) => h.address === 'Thin111111111111111111111111111111111111111');
  assert.equal(thin.included, false, 'a priced token with a $900 market is not counted');
  assert.ok(!r.holdings.some((h) => h.address === 'bad&ids=x'), 'a non-base58 mint never reaches a query string');
  assert.equal(r.totalUsd, 210);
  assert.equal(r.usdComplete, true, 'an excluded airdrop does not make the total incomplete');
  assert.ok(r.notes.some((n) => /empty token account/.test(n)));
});

test('finish drops dust and marks errors partial; summarise reports completeness across chains', () => {
  const chain = finish({ chain: 'base', status: 'ok', errors: ['defillama prices: HTTP 500'], notes: [], holdings: [
    { symbol: 'A', usd: 0.001, included: true }, { symbol: 'B', usd: 5, included: true, stable: true },
  ] });
  assert.equal(chain.status, 'partial');
  assert.equal(chain.holdings.length, 1);
  assert.equal(chain.usdComplete, false);
  const s = summarise([chain, { chain: 'solana', status: 'skipped', holdings: [], errors: [], totalUsd: 0, usdComplete: true }], { atMs: 1 });
  assert.equal(s.totalUsd, 5.001);
  assert.equal(s.stableUsd, 5);
  assert.equal(s.complete, false);
});

/* ---------------------------------------------------------------- pools -- */

const rawPool = (over = {}) => ({
  chain: 'Base', project: 'aerodrome-slipstream', symbol: 'WETH-USDC', pool: 'p1', tvlUsd: 5e6,
  apy: 20, apyBase: 12, apyReward: 8, apyMean30d: 18, apyPct7D: -1, stablecoin: false, ilRisk: 'yes',
  exposure: 'multi', outlier: false, poolMeta: null, ...over,
});

test('normalisePool keeps Base and Solana rows only and marks every row quoted', () => {
  assert.equal(normalisePool(rawPool({ chain: 'Ethereum' })), null);
  assert.equal(normalisePool(rawPool({ apy: 'x' })), null);
  assert.equal(normalisePool(rawPool({ apy: null })), null, 'a missing APY is not a 0% APY');
  assert.equal(normalisePool(rawPool({ tvlUsd: null })), null);
  assert.equal(normalisePool(rawPool({ apyMean30d: null })).apyMean30d, null);
  const p = normalisePool(rawPool());
  assert.equal(p.chain, 'base');
  assert.equal(p.quoted, true);
  assert.match(p.link, /defillama\.com\/yields\/pool\/p1$/);
});

test('rankPools filters by chain, TVL, stable, outlier and search, and ranks by 30-day mean', () => {
  const pools = [
    rawPool({ pool: 'a', apy: 90, apyMean30d: 10 }),
    rawPool({ pool: 'b', apy: 15, apyMean30d: 30 }),
    rawPool({ pool: 'c', tvlUsd: 1000 }),
    rawPool({ pool: 'd', outlier: true, apyMean30d: 500 }),
    rawPool({ pool: 'e', chain: 'Solana', project: 'orca-dex', stablecoin: true }),
  ].map(normalisePool);
  assert.deepEqual(rankPools(pools).map((p) => p.id), ['b', 'e', 'a']);
  assert.deepEqual(rankPools(pools, { includeOutliers: true }).map((p) => p.id)[0], 'd');
  assert.deepEqual(rankPools(pools, { chain: 'solana' }).map((p) => p.id), ['e']);
  assert.deepEqual(rankPools(pools, { stableOnly: true }).map((p) => p.id), ['e']);
  assert.deepEqual(rankPools(pools, { search: 'ORCA' }).map((p) => p.id), ['e']);
  assert.deepEqual(rankPools(pools, { sort: 'apy' }).map((p) => p.id)[0], 'a');
  assert.deepEqual(newPoolIds([], pools), [], 'the first scan reports nothing as new');
  assert.deepEqual(newPoolIds(['a', 'b', 'c', 'd'], pools), ['e']);
});

/* ---------------------------------------------------------------- quote -- */

// A pool sitting mid-range at tick 50 of a 100-spacing range: price 1.0001^50.
const MID = BigInt(Math.floor(Math.sqrt(1.0001 ** 50) * 2 ** 96));
const PRICE_MID = 1.0001 ** 50;
// Tick 75 sits inside both a 50-spacing range [50, 100) and a 100-spacing range [0, 100).
const MID75 = BigInt(Math.floor(Math.sqrt(1.0001 ** 75) * 2 ** 96));

test('swapWithinRange: a tiny swap returns spot less the fee, in both directions', () => {
  const base = { sqrtPriceX96: MID, liquidity: 10n ** 24n, feePips: 500, tick: 50, tickSpacing: 100 };
  const a = swapWithinRange({ ...base, amountIn: 10n ** 6n, zeroForOne: true });
  const b = swapWithinRange({ ...base, amountIn: 10n ** 6n, zeroForOne: false });
  assert.equal(a.ok, true);
  assert.equal(b.ok, true);
  // 0.05% fee, negligible impact at this depth; integer math rounds down by at most 1.
  const wantA = 1e6 * PRICE_MID * 0.9995;
  const wantB = (1e6 / PRICE_MID) * 0.9995;
  assert.ok(Math.abs(Number(a.amountOut) - wantA) <= 1, `${a.amountOut} vs ${wantA}`);
  assert.ok(Math.abs(Number(b.amountOut) - wantB) <= 1, `${b.amountOut} vs ${wantB}`);
  assert.ok(a.sqrtNextX96 < MID && b.sqrtNextX96 > MID, 'price moves the right way');
});

test('swapWithinRange refuses at the exact range edge, where the next tick may hold different liquidity', () => {
  const r = swapWithinRange({ amountIn: 10n ** 6n, sqrtPriceX96: 1n << 96n, liquidity: 10n ** 24n, feePips: 500, zeroForOne: true, tick: 0, tickSpacing: 100 });
  assert.equal(r.ok, false);
});

test('swapWithinRange refuses a swap that would leave the active range instead of guessing', () => {
  const r = swapWithinRange({ amountIn: 10n ** 30n, sqrtPriceX96: 1n << 96n, liquidity: 10n ** 18n, feePips: 500, zeroForOne: true, tick: 0, tickSpacing: 100 });
  assert.equal(r.ok, false);
  assert.match(r.reason, /active liquidity range/);
  assert.equal(swapWithinRange({ amountIn: 1n, sqrtPriceX96: 1n << 96n, liquidity: 0n, feePips: 500, zeroForOne: true, tick: 0, tickSpacing: 1 }).ok, false);
  assert.deepEqual(activeRange(-1, 100), { lower: -100, upper: 0 });
  assert.deepEqual(activeRange(150, 100), { lower: 100, upper: 200 });
});

function slipstreamRpc({ pools }) {
  // pools: { [tickSpacing]: { address, sqrtPriceX96, tick, liquidity, fee } }
  const byAddress = Object.fromEntries(Object.values(pools).map((p) => [p.address.toLowerCase(), p]));
  return (_url, batch) => batch.map((req) => {
    const r = (result) => ({ jsonrpc: '2.0', id: req.id, result });
    if (req.method === 'eth_chainId') return r(BASE.chainIdHex);
    if (req.method === 'eth_blockNumber') return r('0x2a');
    const { to, data } = req.params[0];
    if (to === BASE.clFactory && data === SELECTOR.tickSpacings) {
      const spacings = [1, 50, 100];
      return r('0x' + [0x20, spacings.length, ...spacings].map((n) => n.toString(16).padStart(64, '0')).join(''));
    }
    if (to === BASE.clFactory && data.startsWith(SELECTOR.getPool)) {
      const ts = Number(BigInt(`0x${data.slice(-64)}`));
      return r(uintWord(BigInt(pools[ts]?.address ?? '0x0')));
    }
    const p = byAddress[to.toLowerCase()];
    if (data === SELECTOR.slot0) return r(`0x${p.sqrtPriceX96.toString(16).padStart(64, '0')}${BigInt.asUintN(256, BigInt(p.tick)).toString(16).padStart(64, '0')}${'0'.repeat(64 * 4)}`);
    if (data === SELECTOR.liquidity) return r(uintWord(p.liquidity));
    if (data === SELECTOR.fee) return r(uintWord(p.fee));
    return r('0x');
  });
}

test('CDO-27afd5b542 quoteBase picks the pool with the best output and hands off to the venue to sign', async () => {
  const { fetch, calls } = stubFetch({
    'https://': slipstreamRpc({ pools: {
      50: { address: '0x00000000000000000000000000000000000000a1', sqrtPriceX96: MID75, tick: 75, liquidity: 10n ** 24n, fee: 500 },
      100: { address: '0x00000000000000000000000000000000000000a2', sqrtPriceX96: MID75, tick: 75, liquidity: 10n ** 24n, fee: 3000 },
    } }),
  });
  const q = await quoteBase({ fetch }, { from: 'WETH', to: 'USDC', amount: '0.000001', slippageBps: 100 });
  assert.equal(q.venue, 'Aero Slipstream');
  assert.match(q.route[0], /spacing 50/, 'the lower-fee pool wins');
  assert.ok(q.minOut < q.to.amount);
  assert.match(q.handoffUrl, /^https:\/\/aerodrome\.finance\/swap\?from=0x4200/);
  assert.equal(q.poolsChecked.length, 2);
  for (const c of calls) for (const req of c.body) {
    assert.match(req.method, /^eth_(chainId|blockNumber|call)$/);
    if (req.method === 'eth_call') assert.equal(req.params[1], '0x2a');
  }
});

test('quoteBase refuses when no pool can fill inside its active range, and rejects unknown tokens', async () => {
  const { fetch } = stubFetch({ 'https://': slipstreamRpc({ pools: {
    100: { address: '0x00000000000000000000000000000000000000a2', sqrtPriceX96: MID, tick: 50, liquidity: 10n, fee: 500 },
  } }) });
  await assert.rejects(() => quoteBase({ fetch }, { from: 'WETH', to: 'USDC', amount: '10' }), /inside its active range/);
  await assert.rejects(() => quoteBase({ fetch }, { from: 'PEPE', to: 'USDC', amount: '1' }), /unknown Base token/);
  await assert.rejects(() => quoteBase({ fetch }, { from: 'ETH', to: 'WETH', amount: '1' }), /same token/);
  await assert.rejects(() => quote({ fetch }, { chain: 'eth', from: 'a', to: 'b', amount: '1' }), /chain must be/);
  await assert.rejects(() => quote({ fetch }, { chain: 'base', from: 'a', to: 'b', amount: '1', slippageBps: 5000 }), /slippageBps/);
});

test('quoteSolana reads Jupiter and refuses a reply that does not match the request', async () => {
  const sol = findToken('solana', 'SOL').address;
  const usdc = findToken('solana', 'usdc').address;
  const good = stubFetch({ 'https://lite-api.jup.ag/swap/v1/quote': (url) => {
    assert.match(url, /amount=500000000&slippageBps=50/);
    return { inputMint: sol, outputMint: usdc, inAmount: '500000000', swapMode: 'ExactIn', outAmount: '44751706', otherAmountThreshold: '44527948', priceImpactPct: '0.00002', routePlan: [{ swapInfo: { label: 'Orca' }, percent: 100 }] };
  } });
  const q = await quoteSolana({ fetch: good.fetch }, { from: 'SOL', to: 'USDC', amount: '0.5', slippageBps: 50 });
  assert.equal(q.to.amount, 44.751706);
  assert.equal(q.minOut, 44.527948);
  assert.deepEqual(q.route, ['Orca 100%']);
  assert.equal(q.handoffUrl, `https://jup.ag/swap/${sol}-${usdc}`);

  const bad = stubFetch({ 'https://lite-api.jup.ag/swap/v1/quote': () => ({ inputMint: usdc, outputMint: sol, outAmount: '1' }) });
  await assert.rejects(() => quoteSolana({ fetch: bad.fetch }, { from: 'SOL', to: 'USDC', amount: '0.5' }), /did not match/);
});

test('readSolana reads Jupiter holdings first (the public RPC refuses extension origins) and falls back to RPC', async () => {
  const usdcMint = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
  const rpcHits = [];
  const routes = {
    'https://lite-api.jup.ag/ultra/v1/holdings/': () => ({
      amount: '2000000000', uiAmountString: '2',
      tokens: { [usdcMint]: [{ uiAmountString: '7.5' }, { uiAmountString: '2.5' }], ['1'.repeat(32)]: [{ uiAmountString: '0' }] },
    }),
    'https://sol': (_u, req) => { rpcHits.push(req.method); return { id: 1, result: { value: 0 } }; },
    'https://lite-api.jup.ag/price': () => ({ So11111111111111111111111111111111111111112: { usdPrice: 100 }, [usdcMint]: { usdPrice: 1 } }),
  };
  const { fetch, calls } = stubFetch(routes);
  const r = await readSolana({ fetch }, SOL_OWNER, { rpcs: ['https://sol'] });
  assert.equal(r.totalUsd, 210);
  assert.deepEqual(rpcHits, [], 'RPC is not touched when Jupiter answers');
  assert.ok(r.notes.some((n) => /Jupiter holdings/.test(n)));
  assert.ok(r.notes.some((n) => /1 empty token account/.test(n)));
  assert.ok(calls.every((c) => c.method === 'GET'), 'the holdings path is GET reads only');

  // Jupiter down: the same balances come from RPC, and the switch is noted.
  delete routes['https://lite-api.jup.ag/ultra/v1/holdings/'];
  routes['https://sol'] = (_u, req) => (req.method === 'getBalance'
    ? { id: 1, result: { value: 2_000_000_000 } }
    : { id: 1, result: { value: [] } });
  const r2 = await readSolana({ fetch: stubFetch(routes).fetch }, SOL_OWNER, { rpcs: ['https://sol'] });
  assert.equal(r2.totalUsd, 200);
  assert.ok(r2.notes.some((n) => /jupiter holdings unavailable/.test(n)));
  assert.ok(r2.notes.some((n) => /Solana JSON-RPC/.test(n)));
});
