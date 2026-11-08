/**
 * Pool discovery from DefiLlama yields (keyless, https://yields.llama.fi/pools).
 *
 * Every APY here is QUOTED by DefiLlama, not measured by this project. It
 * includes reward emissions and can be a short-window spike. liquidity/CLAUDE.md
 * forbids using a quoted APR as an income figure, so these rows are a list of
 * leads: the UI labels them "quoted", and the alert scan never tells the owner
 * to move money on a quoted number alone (src/core/alerts.js). The modelled
 * figures come from the Aero scout over the soltui bridge.
 *
 * The full feed is ~11 MB for ~16k pools; it is filtered to the chains we hold
 * funds on as soon as it is parsed.
 */

import { getJson } from './net.js';
import { ENDPOINTS } from './tokens.js';

const CHAIN_NAMES = { Base: 'base', Solana: 'solana' };

/** One raw DefiLlama row to the shape the UI and alerts use. Null for unusable rows. Pure. */
export function normalisePool(raw) {
  const chain = CHAIN_NAMES[raw?.chain];
  // Number(null) is 0: a missing APY would rank as a real 0%. Missing is missing.
  const num = (v) => (v === null || v === undefined || v === '' ? null : Number.isFinite(Number(v)) ? Number(v) : null);
  const apy = num(raw?.apy);
  const tvlUsd = num(raw?.tvlUsd);
  if (!chain || typeof raw.pool !== 'string' || apy === null || tvlUsd === null) return null;
  return {
    id: raw.pool,
    chain,
    project: String(raw.project ?? ''),
    symbol: String(raw.symbol ?? ''),
    meta: raw.poolMeta == null ? null : String(raw.poolMeta),
    tvlUsd,
    apy,
    apyBase: num(raw.apyBase),
    apyReward: num(raw.apyReward),
    apyMean30d: num(raw.apyMean30d),
    apyChange7d: num(raw.apyPct7D),
    volumeUsd1d: num(raw.volumeUsd1d),
    stablecoin: raw.stablecoin === true,
    ilRisk: raw.ilRisk === 'yes',
    exposure: raw.exposure === 'single' ? 'single' : 'multi',
    outlier: raw.outlier === true,
    quoted: true,
    link: `https://defillama.com/yields/pool/${encodeURIComponent(raw.pool)}`,
  };
}

/**
 * Filter and rank. Pure.
 *
 * The default rank is the 30-day mean APY, not today's: a pool whose APY spiked
 * for a day is the commonest way a yield list misleads. DefiLlama's own
 * `outlier` flag removes a row unless `includeOutliers` is set.
 */
export function rankPools(pools, {
  chain = 'all', minTvlUsd = 250_000, stableOnly = false, singleOnly = false, search = '',
  includeOutliers = false, sort = 'apyMean30d', limit = 50,
} = {}) {
  const q = String(search ?? '').trim().toLowerCase();
  const key = ['apy', 'apyMean30d', 'apyBase', 'tvlUsd'].includes(sort) ? sort : 'apyMean30d';
  return pools
    .filter((p) => p && (chain === 'all' || p.chain === chain))
    .filter((p) => p.tvlUsd >= minTvlUsd)
    .filter((p) => !stableOnly || p.stablecoin)
    .filter((p) => !singleOnly || p.exposure === 'single')
    .filter((p) => includeOutliers || !p.outlier)
    .filter((p) => !q || `${p.project} ${p.symbol} ${p.meta ?? ''}`.toLowerCase().includes(q))
    .sort((a, b) => (b[key] ?? b.apy ?? -Infinity) - (a[key] ?? a.apy ?? -Infinity))
    .slice(0, Math.max(1, Math.min(500, limit)));
}

/** Ids in `current` that were not in `previousIds`. Pure. The first scan reports none. */
export function newPoolIds(previousIds, current) {
  if (!Array.isArray(previousIds) || !previousIds.length) return [];
  const seen = new Set(previousIds);
  return current.filter((p) => !seen.has(p.id)).map((p) => p.id);
}

/** Fetch the feed and normalise the Base and Solana rows. */
export async function fetchPools(deps) {
  const body = await getJson(deps, ENDPOINTS.llamaYields, { source: 'defillama yields', timeoutMs: 30_000, maxAttempts: 2 });
  const rows = Array.isArray(body?.data) ? body.data : [];
  return rows.map(normalisePool).filter(Boolean);
}

// DefiLlama refreshes yields about hourly; re-downloading 11 MB per filter
// change would only burn their bandwidth and the worker's memory. This is a
// cache, not state: losing it when the worker sleeps costs one refetch.
const POOL_CACHE_MS = 10 * 60_000;
let poolCache = null;

export async function fetchPoolsCached(deps, { maxAgeMs = POOL_CACHE_MS } = {}) {
  const now = deps.clock?.() ?? Date.now();
  if (poolCache && poolCache.fetchImpl === deps.fetch && now - poolCache.atMs < maxAgeMs) return poolCache;
  const pools = await fetchPools(deps);
  poolCache = { atMs: now, pools, fetchImpl: deps.fetch };
  return poolCache;
}
