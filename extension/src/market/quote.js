/**
 * Swap quotes. Quote only: nothing here builds, signs or sends a transaction.
 *
 * The extension's signer has no semantic transaction verifier, so live signing
 * stays blocked (CLAUDE.md, "Known-unverified areas"). A quote is handed to the
 * venue's own page, where the owner reviews and signs in their wallet. See
 * Stele KNOW-837.
 *
 * Solana: Jupiter's keyless quote API (lite-api.jup.ag/swap/v1/quote), which
 * routes across every Solana venue Jupiter knows.
 *
 * Base: Aero Slipstream pools read on chain. For each enabled tick spacing the
 * CLFactory gives the pool; slot0, liquidity and fee give its state. Inside the
 * current tick-spacing range liquidity is constant (initialized ticks sit only
 * on multiples of the spacing), so the output there is exact concentrated-
 * liquidity math (Uniswap v3 SwapMath). A swap that would cross that range is
 * REFUSED: liquidity past the boundary was not read, and a number past it would
 * be a guess (non-negotiable 3). Small swaps in deep pools fit easily.
 */

// A bad request (unknown token, wrong chain, bad slippage) is a RangeError, which
// the registry maps to 400; a venue or RPC that cannot answer is a MarketError (502).
import { rpcBatch, getJson, MarketError } from './net.js';
import { SELECTOR, word, intWord, uint, words, signed, intArray, addressOf, ZERO_ADDRESS, toUnits, fromUnits } from './evm.js';
import { BASE, ENDPOINTS, findToken } from './tokens.js';

const Q96 = 1n << 96n;

/* ------------------------------------------------------------- CL math -- */

/** sqrt(1.0001^tick) as a float; used only for range checks, never for amounts. */
export const sqrtPriceAtTick = (tick) => Math.sqrt(1.0001 ** tick);

/** The tick a Q64.96 sqrt price sits at, as a float. */
export function tickAtSqrtX96(sqrtX96) {
  const s = Number(sqrtX96) / 2 ** 96;
  return (2 * Math.log(s)) / Math.log(1.0001);
}

/** The [lower, upper) tick range in which the current liquidity is constant. */
export function activeRange(tick, tickSpacing) {
  const lower = Math.floor(tick / tickSpacing) * tickSpacing;
  return { lower, upper: lower + tickSpacing };
}

/**
 * Exact-input output inside the active range. Pure, BigInt.
 *
 * @param {object} p
 * @param {bigint} p.amountIn       raw input amount
 * @param {bigint} p.sqrtPriceX96
 * @param {bigint} p.liquidity
 * @param {number} p.feePips        fee in hundredths of a bp (500 = 0.05%)
 * @param {boolean} p.zeroForOne    true when token0 is the input
 * @param {number} p.tick           current tick
 * @param {number} p.tickSpacing
 * @param {number} [p.edgeTicks]    refuse within this many ticks of the boundary (float safety)
 * @returns {{ok: true, amountOut: bigint, sqrtNextX96: bigint} | {ok: false, reason: string}}
 */
export function swapWithinRange({ amountIn, sqrtPriceX96, liquidity, feePips, zeroForOne, tick, tickSpacing, edgeTicks = 1 }) {
  if (amountIn <= 0n) return { ok: false, reason: 'amount must be positive' };
  if (liquidity <= 0n) return { ok: false, reason: 'pool has no liquidity in range' };
  if (!(feePips >= 0 && feePips < 1_000_000)) return { ok: false, reason: 'pool fee is unreadable' };
  const net = (amountIn * BigInt(1_000_000 - feePips)) / 1_000_000n;
  let next;
  let out;
  if (zeroForOne) {
    const num = liquidity << 96n;
    next = (num * sqrtPriceX96) / (num + net * sqrtPriceX96);
    out = (liquidity * (sqrtPriceX96 - next)) / Q96;
  } else {
    next = sqrtPriceX96 + (net * Q96) / liquidity;
    out = ((liquidity << 96n) * (next - sqrtPriceX96)) / next / sqrtPriceX96;
  }
  const { lower, upper } = activeRange(tick, tickSpacing);
  const at = tickAtSqrtX96(next);
  if (!Number.isFinite(at) || (zeroForOne ? at <= lower + edgeTicks : at >= upper - edgeTicks)) {
    return { ok: false, reason: 'swap would leave the active liquidity range; liquidity beyond it was not read' };
  }
  return { ok: true, amountOut: out, sqrtNextX96: next };
}

/* --------------------------------------------------------------- Base -- */

function baseToken(ref) {
  const t = findToken('base', ref);
  if (!t) throw new RangeError(`unknown Base token "${ref}"; use one of the listed symbols`);
  // Native ETH trades as WETH in every Slipstream pool.
  return t.native ? findToken('base', 'WETH') : t;
}

export async function quoteBase(deps, { from, to, amount, slippageBps = 50 }) {
  const tin = baseToken(from);
  const tout = baseToken(to);
  if (tin.address.toLowerCase() === tout.address.toLowerCase()) throw new RangeError('input and output are the same token');
  const amountIn = fromUnits(amount, tin.decimals);
  const zeroForOne = tin.address.toLowerCase() < tout.address.toLowerCase();

  const [chainId, spacingsHex] = await rpcBatch(deps, BASE.rpcs, [
    ['eth_chainId', []],
    ['eth_call', [{ to: BASE.clFactory, data: SELECTOR.tickSpacings }, 'latest']],
  ], { source: 'base rpc' });
  if (chainId !== BASE.chainIdHex) throw new MarketError('base rpc', `endpoint reports chain ${chainId}, expected ${BASE.chainIdHex}`);
  const spacings = intArray(spacingsHex);
  if (!spacings.length) throw new MarketError('quote', 'could not read Slipstream tick spacings');

  const poolsHex = await rpcBatch(deps, BASE.rpcs, spacings.map((ts) => ['eth_call', [{
    to: BASE.clFactory, data: SELECTOR.getPool + word(tin.address) + word(tout.address) + intWord(ts),
  }, 'latest']]), { source: 'base rpc' });
  const pools = spacings.map((ts, i) => ({ tickSpacing: ts, address: addressOf(poolsHex[i]) }))
    .filter((p) => p.address && p.address !== ZERO_ADDRESS);
  if (!pools.length) throw new MarketError('quote', `no Slipstream pool for ${tin.symbol}/${tout.symbol}`);

  const state = await rpcBatch(deps, BASE.rpcs, pools.flatMap((p) => [
    ['eth_call', [{ to: p.address, data: SELECTOR.slot0 }, 'latest']],
    ['eth_call', [{ to: p.address, data: SELECTOR.liquidity }, 'latest']],
    ['eth_call', [{ to: p.address, data: SELECTOR.fee }, 'latest']],
  ]), { source: 'base rpc' });

  const tried = pools.map((p, i) => {
    const s0 = words(state[3 * i]);
    const liquidity = uint(state[3 * i + 1]);
    const fee = uint(state[3 * i + 2]);
    if (s0.length < 2 || liquidity === null || fee === null) return { ...p, ok: false, reason: 'pool state unreadable' };
    const sqrtPriceX96 = s0[0];
    const tick = Number(signed(s0[1], 24));
    const feePips = Number(fee);
    const r = swapWithinRange({ amountIn, sqrtPriceX96, liquidity, feePips, zeroForOne, tick, tickSpacing: p.tickSpacing });
    // Spot output before fee and impact, for the impact figure.
    const price = (Number(sqrtPriceX96) / 2 ** 96) ** 2; // token1 per token0, raw units
    const spotOut = zeroForOne ? Number(amountIn) * price : Number(amountIn) / price;
    return { ...p, ...r, feePips, liquidity, spotOut };
  });
  const filled = tried.filter((t) => t.ok).sort((a, b) => (b.amountOut > a.amountOut ? 1 : b.amountOut < a.amountOut ? -1 : 0));
  if (!filled.length) {
    throw new MarketError('quote', `no Slipstream pool can fill this size inside its active range (${
      tried.map((t) => `spacing ${t.tickSpacing}: ${t.reason}`).join('; ')})`);
  }
  const best = filled[0];
  const outUnits = toUnits(best.amountOut, tout.decimals);
  const minOut = (best.amountOut * BigInt(10_000 - slippageBps)) / 10_000n;
  return {
    chain: 'base',
    venue: 'Aero Slipstream',
    from: { symbol: tin.symbol, address: tin.address, amount: Number(amount) },
    to: { symbol: tout.symbol, address: tout.address, amount: outUnits },
    minOut: toUnits(minOut, tout.decimals),
    slippageBps,
    feePct: best.feePips / 10_000,
    priceImpactPct: best.spotOut > 0 ? Math.max(0, (1 - Number(best.amountOut) / best.spotOut) * 100 - best.feePips / 10_000) : null,
    route: [`Slipstream ${tin.symbol}/${tout.symbol} spacing ${best.tickSpacing} (${best.address})`],
    poolsChecked: tried.map((t) => ({ tickSpacing: t.tickSpacing, pool: t.address, ok: t.ok, reason: t.reason ?? null,
      out: t.ok ? toUnits(t.amountOut, tout.decimals) : null })),
    caveats: [
      'Exact within the active tick range at the latest block; the price can move before you sign.',
      'Aero may add an MEV-tax fee on a high priority fee; the venue page shows the final amount.',
    ],
    handoffUrl: `https://aerodrome.finance/swap?from=${tin.address}&to=${tout.address}`,
  };
}

/* ------------------------------------------------------------- Solana -- */

export async function quoteSolana(deps, { from, to, amount, slippageBps = 50 }) {
  const tin = findToken('solana', from);
  const tout = findToken('solana', to);
  if (!tin || !tout) throw new RangeError('unknown Solana token; use one of the listed symbols');
  if (tin.address === tout.address) throw new RangeError('input and output are the same token');
  const raw = fromUnits(amount, tin.decimals);
  const url = `${ENDPOINTS.jupiterQuote}?inputMint=${tin.address}&outputMint=${tout.address}`
    + `&amount=${raw}&slippageBps=${slippageBps}&swapMode=ExactIn`;
  const q = await getJson(deps, url, { source: 'jupiter quote' });
  if (q?.inputMint !== tin.address || q?.outputMint !== tout.address || !/^\d+$/.test(String(q?.outAmount ?? ''))) {
    throw new MarketError('jupiter quote', 'response did not match the request');
  }
  const impact = Number(q.priceImpactPct);
  return {
    chain: 'solana',
    venue: 'Jupiter',
    from: { symbol: tin.symbol, address: tin.address, amount: Number(amount) },
    to: { symbol: tout.symbol, address: tout.address, amount: toUnits(BigInt(q.outAmount), tout.decimals) },
    minOut: /^\d+$/.test(String(q.otherAmountThreshold ?? '')) ? toUnits(BigInt(q.otherAmountThreshold), tout.decimals) : null,
    slippageBps,
    feePct: null,
    priceImpactPct: Number.isFinite(impact) ? impact * 100 : null,
    usdValue: Number.isFinite(Number(q.swapUsdValue)) ? Number(q.swapUsdValue) : null,
    route: (q.routePlan ?? []).map((r) => `${r?.swapInfo?.label ?? 'venue'} ${r?.percent ?? '?'}%`),
    caveats: ['Jupiter re-quotes when you open the swap; the page shows the final amount before you sign.'],
    handoffUrl: `https://jup.ag/swap/${tin.address}-${tout.address}`,
  };
}

export async function quote(deps, { chain, ...args }) {
  if (!Number.isSafeInteger(args.slippageBps ?? 50) || (args.slippageBps ?? 50) < 1 || (args.slippageBps ?? 50) > 1000) {
    throw new RangeError('slippageBps must be an integer from 1 to 1000');
  }
  if (chain === 'base') return quoteBase(deps, args);
  if (chain === 'solana') return quoteSolana(deps, args);
  throw new RangeError('chain must be base or solana');
}
