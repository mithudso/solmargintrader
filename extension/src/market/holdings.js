/**
 * Live holdings: what the owner's public Base and Solana addresses hold, in USD.
 *
 * Read-only. No key, no signature, no transaction: Base is read with
 * eth_getBalance and ERC-20 balanceOf through one JSON-RPC batch, Solana with
 * getBalance and getTokenAccountsByOwner, prices from DefiLlama (Base) and the
 * keyless Jupiter price API (Solana).
 *
 * Honesty rules, shared with soltui/wallet.py:
 * - A source that fails makes the chain `partial` with the error named. It is
 *   never an exception and never a silently smaller total.
 * - A holding with no price is listed with usd null and leaves the chain total
 *   marked incomplete; it is never valued at zero.
 * - A price DefiLlama itself rates below 0.5 confidence is not used.
 * - A Solana token Jupiter does not list as verified, and that has no price,
 *   is flagged `unverified` and left out of totals: unsolicited airdrop tokens
 *   look exactly like that. Its contract is never called beyond the standard
 *   reads.
 */

import { rpcBatch, rpcCall, getJson, MarketError } from './net.js';
import { SELECTOR, word, uint, toUnits, isAddress, hexToBigInt } from './evm.js';
import { BASE, SOLANA, BASE_TOKENS, ENDPOINTS, isSolanaAddress } from './tokens.js';

/** Balances worth less than this are counted, not listed. */
export const DUST_USD = 0.01;

/** An unknown token whose market is thinner than this is not counted (soltui/wallet.py). */
export const MIN_LIQUIDITY_USD = 5_000;

function balanceNumber(value) {
  if (!['number', 'string'].includes(typeof value) || (typeof value === 'string' && !value.trim())) return null;
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : null;
}

function chainResult(chain, address) {
  return { chain, address, status: 'ok', holdings: [], errors: [], notes: [], totalUsd: 0, usdComplete: true };
}

function fail(result, err) {
  result.errors.push(err instanceof MarketError ? err.message : `${result.chain}: ${err?.message ?? 'read failed'}`);
}

/* -------------------------------------------------------------------- Base -- */

export async function readBase(deps, address, { rpcs = BASE.rpcs } = {}) {
  const result = chainResult('base', address);
  if (!isAddress(address)) {
    result.status = 'skipped';
    result.notes.push('no Base address set');
    return result;
  }

  const tokens = BASE_TOKENS.filter((t) => !t.native);
  const calls = [
    ['eth_chainId', []],
    ['eth_getBalance', [address, 'latest']],
    ...tokens.map((t) => ['eth_call', [{ to: t.address, data: SELECTOR.balanceOf + word(address) }, 'latest']]),
  ];
  let out;
  try {
    out = await rpcBatch(deps, rpcs, calls, { source: 'base rpc' });
  } catch (err) {
    fail(result, err);
    result.status = 'failed';
    result.usdComplete = false;
    return result;
  }
  // A misconfigured endpoint pointing at another chain would report real-looking
  // balances for the wrong network. Refuse the whole read instead.
  if (out[0] !== BASE.chainIdHex) {
    result.status = 'failed';
    result.usdComplete = false;
    result.errors.push(`base rpc: endpoint reports chain ${out[0] ?? 'unknown'}, expected ${BASE.chainIdHex} (8453)`);
    return result;
  }

  const raw = [{ token: BASE_TOKENS[0], value: hexToBigInt(out[1]) }];
  tokens.forEach((t, i) => raw.push({ token: t, value: uint(out[i + 2]) }));
  const missing = raw.filter((r) => r.value === null).map((r) => r.token.symbol);
  if (missing.length) {
    result.notes.push(`no answer for ${missing.join(', ')}; not listed`);
    result.errors.push('base rpc: some known balances are unavailable');
  }

  const held = raw.filter((r) => r.value !== null && r.value > 0n);
  let prices = {};
  if (held.length) {
    const keys = held.map((r) => (r.token.native ? 'coingecko:ethereum' : `base:${r.token.address}`));
    try {
      const reply = await getJson(deps, ENDPOINTS.llamaPrices + keys.join(','), { source: 'defillama prices' });
      prices = Object.fromEntries(keys.map((k) => {
        const c = reply?.coins?.[k];
        const ok = c && Number.isFinite(c.price) && c.price > 0 && (c.confidence ?? 0) >= 0.5;
        return [k, ok ? c.price : null];
      }));
    } catch (err) {
      fail(result, err);
    }
  }

  for (const r of held) {
    const key = r.token.native ? 'coingecko:ethereum' : `base:${r.token.address}`;
    const amount = toUnits(r.value, r.token.decimals);
    const priceUsd = prices[key] ?? null;
    result.holdings.push({
      symbol: r.token.symbol,
      address: r.token.address,
      amount,
      priceUsd,
      usd: priceUsd == null ? null : amount * priceUsd,
      stable: r.token.stable,
      included: true,
      link: r.token.native ? `${BASE.explorer}/address/${address}` : `${BASE.explorer}/token/${r.token.address}`,
    });
  }
  result.notes.push(`checked native ETH and ${tokens.length} known tokens; use the soltui deep scan for anything else`);
  return finish(result);
}

/* ------------------------------------------------------------------ Solana -- */

/**
 * Token balances by mint from Jupiter's holdings read. Null when it cannot answer.
 * The extension tries this first: api.mainnet-beta.solana.com answers 403 to a
 * request with a chrome-extension Origin, while this endpoint accepts it.
 */
async function solanaFromJupiter(deps, address, result) {
  try {
    const body = await getJson(deps, ENDPOINTS.jupiterHoldings + address, { source: 'jupiter holdings' });
    const sol = balanceNumber(body?.uiAmountString ?? body?.uiAmount);
    if (sol === null || !body?.tokens || typeof body.tokens !== 'object' || Array.isArray(body.tokens)) {
      result.notes.push('jupiter holdings answered in an unexpected shape; read Solana RPC instead');
      return null;
    }
    const mints = new Map();
    let empty = 0;
    for (const [mint, accounts] of Object.entries(body.tokens)) {
      // Mints go into a price query string and an explorer link: base58 only.
      if (!isSolanaAddress(mint) || !Array.isArray(accounts)) continue;
      const amount = accounts.reduce((sum, account) => {
        const quantity = balanceNumber(account?.uiAmountString ?? account?.uiAmount);
        if (quantity === null || !Number.isFinite(sum + quantity)) throw new MarketError('jupiter holdings', 'token balance unavailable');
        return sum + quantity;
      }, 0);
      if (amount === 0) { empty += accounts.length; continue; }
      mints.set(mint, { mint, amount });
    }
    return { sol, mints, empty, via: 'Jupiter holdings (lite-api.jup.ag/ultra/v1/holdings)' };
  } catch (err) {
    result.notes.push(`jupiter holdings unavailable (${err?.message ?? 'failed'}); read Solana RPC instead`);
    return null;
  }
}

async function solanaFromRpc(deps, address, rpcs, result) {
  const mints = new Map();
  let sol = null;
  try {
    const bal = await rpcCall(deps, rpcs, 'getBalance', [address], { source: 'solana getBalance' });
    const lamports = balanceNumber(bal?.value ?? bal);
    if (lamports === null) throw new MarketError('solana getBalance', 'native balance unavailable');
    sol = lamports / 1e9;
  } catch (err) {
    fail(result, err);
  }
  let empty = 0;
  for (const program of [SOLANA.tokenProgram, SOLANA.token2022Program]) {
    try {
      const reply = await rpcCall(deps, rpcs, 'getTokenAccountsByOwner',
        [address, { programId: program }, { encoding: 'jsonParsed' }], { source: 'solana token accounts' });
      if (!Array.isArray(reply?.value)) throw new MarketError('solana token accounts', 'token account list unavailable');
      for (const item of reply.value) {
        const info = item?.account?.data?.parsed?.info;
        const amt = info?.tokenAmount;
        if (!isSolanaAddress(info?.mint)) continue;
        const ui = balanceNumber(amt?.uiAmountString ?? amt?.uiAmount);
        if (ui === null) throw new MarketError('solana token accounts', 'token balance unavailable');
        if (ui === 0) { empty += 1; continue; }
        const row = mints.get(info.mint) ?? { mint: info.mint, amount: 0 };
        row.amount += ui;
        mints.set(info.mint, row);
      }
    } catch (err) {
      fail(result, err);
    }
  }
  return { sol, mints, empty, via: 'Solana JSON-RPC' };
}

export async function readSolana(deps, address, { rpcs = SOLANA.rpcs } = {}) {
  const result = chainResult('solana', address);
  if (!isSolanaAddress(address)) {
    result.status = 'skipped';
    result.notes.push('no Solana address set');
    return result;
  }

  const read = (await solanaFromJupiter(deps, address, result)) ?? (await solanaFromRpc(deps, address, rpcs, result));
  const { sol, mints, empty } = read;
  result.notes.push(`balances from ${read.via}`);
  if (empty) result.notes.push(`${empty} empty token account(s) hold rent only`);

  const ids = [SOLANA.wsol, ...mints.keys()];
  const table = {};
  for (let i = 0; i < ids.length; i += 50) {
    const chunk = ids.slice(i, i + 50);
    try {
      Object.assign(table, await getJson(deps, `${ENDPOINTS.jupiterPrice}?ids=${chunk.join(',')}`, { source: 'jupiter price' }) ?? {});
    } catch (err) {
      fail(result, err);
      break;
    }
  }
  const priceOf = (mint) => {
    const p = Number(table?.[mint]?.usdPrice);
    return Number.isFinite(p) && p > 0 ? p : null;
  };
  const liquidityOf = (mint) => {
    const l = table?.[mint]?.liquidity;
    return l == null ? null : Number.isFinite(Number(l)) ? Number(l) : null;
  };

  if (sol !== null && sol > 0) {
    const priceUsd = priceOf(SOLANA.wsol);
    result.holdings.push({
      symbol: 'SOL', address: null, amount: sol, priceUsd, usd: priceUsd == null ? null : sol * priceUsd,
      stable: false, included: true, link: `${SOLANA.explorer}/account/${address}`,
    });
  }
  for (const { mint, amount } of mints.values()) {
    const priceUsd = priceOf(mint);
    const listed = SOLANA_KNOWN.get(mint);
    // Unknown and unpriced, or unknown with a pool too thin to sell into: an
    // airdrop looks exactly like this. List it, do not count it. Same rule and
    // threshold as soltui/wallet.py airdrop_reasons (MIN_LIQUIDITY_USD).
    const liquidity = liquidityOf(mint);
    const thin = liquidity !== null && liquidity < MIN_LIQUIDITY_USD;
    const included = Boolean(listed) || (priceUsd !== null && !thin);
    result.holdings.push({
      symbol: listed ?? `${mint.slice(0, 4)}…`, address: mint, amount, priceUsd,
      usd: priceUsd == null ? null : amount * priceUsd, stable: STABLE_MINTS.has(mint), included,
      unverified: !included, link: `${SOLANA.explorer}/token/${mint}`,
    });
  }
  return finish(result);
}

const SOLANA_KNOWN = new Map([
  ['EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'USDC'],
  ['Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB', 'USDT'],
  ['J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn', 'JitoSOL'],
  ['mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So', 'mSOL'],
  ['jupSoLaHXQiZZTSfEWMTRRgpnyFm8f6sZdosWBjx93v', 'JupSOL'],
  ['JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN', 'JUP'],
  ['So11111111111111111111111111111111111111112', 'wSOL'],
]);
const STABLE_MINTS = new Set(['EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB']);

/* ------------------------------------------------------------------ totals -- */

/**
 * Status, dust filter and totals for one chain. Pure.
 * A chain with any error is `partial`; with no holdings and an error, `failed`.
 */
export function finish(result) {
  let dust = 0;
  result.holdings = result.holdings.filter((h) => {
    if (h.usd != null && (!Number.isFinite(h.usd) || h.usd < 0)) h.usd = null;
    if (h.usd != null && h.usd < DUST_USD) { dust += 1; return false; }
    return true;
  });
  if (dust) result.notes.push(`${dust} balance(s) under $${DUST_USD} not listed`);
  result.holdings.sort((a, b) => (b.usd ?? -1) - (a.usd ?? -1));
  let total = 0;
  let complete = true;
  for (const h of result.holdings) {
    if (!h.included) continue;
    if (h.usd == null) complete = false;
    else total += h.usd;
  }
  result.totalUsd = total;
  result.usdComplete = complete && result.errors.length === 0;
  if (result.errors.length) result.status = result.holdings.length ? 'partial' : 'failed';
  return result;
}

/**
 * Totals across chains. Pure. `complete` is false when any chain is partial,
 * failed or has an unpriced holding, so a UI can show "at least $X".
 */
export function summarise(chains, { atMs = Date.now() } = {}) {
  const read = chains.filter((c) => c.status !== 'skipped');
  const stableUsd = read.flatMap((c) => c.holdings).filter((h) => h.included && h.stable && h.usd != null)
    .reduce((s, h) => s + h.usd, 0);
  return {
    atMs,
    chains,
    totalUsd: read.reduce((s, c) => s + c.totalUsd, 0),
    stableUsd,
    complete: read.length > 0 && read.every((c) => c.usdComplete),
    errors: read.flatMap((c) => c.errors),
  };
}

/** Read every configured address. Each chain fails on its own; one never sinks the other. */
export async function readHoldings(deps, { baseAddress, solanaAddress, chain = 'all' } = {}) {
  const jobs = [];
  if (chain === 'all' || chain === 'base') jobs.push(readBase(deps, baseAddress));
  if (chain === 'all' || chain === 'solana') jobs.push(readSolana(deps, solanaAddress));
  return summarise(await Promise.all(jobs), { atMs: deps.clock?.() ?? Date.now() });
}
