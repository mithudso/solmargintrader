/**
 * Alerts: "there is a more profitable pool or strategy than what you have now".
 *
 * Pure. No I/O, no chrome.*, no clock of its own: the scan in commands.js reads
 * the inputs, and this file decides. Every alert says where its number came
 * from, because the three sources differ in how far they can be trusted:
 *
 *   modelled  the Aero scout's net APR: a model built from MEASURED fee growth
 *             and gauge share minus loss-versus-rebalancing, backtested on
 *             recent bars. soltui labels it "modelled estimates ... not
 *             results", and so does this file. It is the evidence the liquidity
 *             daemon itself deploys on, and the only source that may say "act" -
 *             and only when it is fresh, positive in backtest, medium or high
 *             confidence, unflagged, and above its break-even deposit.
 *   backtest  soltui's Top 5 / CPCV evidence. Says "review": a backtest is not a
 *             live return.
 *   quoted    DefiLlama's advertised APY. Says "info" only. liquidity/CLAUDE.md
 *             forbids treating a quoted APR as income (Stele KNOW-838).
 *
 * Alert ids are stable, so a re-scan updates an alert instead of re-raising it,
 * and an acknowledged alert stays quiet until its id changes.
 */

export const SEVERITY = Object.freeze({ ACTION: 'action', REVIEW: 'review', INFO: 'info' });

export const DEFAULT_PREFS = Object.freeze({
  baseAddress: null,
  solanaAddress: null,
  alertsEnabled: true,
  alertIntervalMinutes: 60,
  // A pool must beat the current position by this many APR percentage points.
  minAprGainPct: 5,
  // Idle capital worth mentioning, and the modelled net APR worth moving it for.
  minIdleUsd: 25,
  minNetAprPct: 5,
  // Quoted leads: only large, sustained pools. Off for notifications by default.
  leadMinTvlUsd: 1_000_000,
  leadMinApyPct: 15,
  notifyLeads: false,
  // The strategy the owner runs, by Top 5 label; null means "compare leaders only".
  activeStrategy: null,
  minSharpeGain: 0.25,
  // Scout output older than this cannot say "act": pools move.
  maxScoutAgeHours: 48,
});

const PREF_TYPES = {
  baseAddress: 'address', solanaAddress: 'address', alertsEnabled: 'boolean', alertIntervalMinutes: 'minutes',
  minAprGainPct: 'number', minIdleUsd: 'number', minNetAprPct: 'number', leadMinTvlUsd: 'number',
  leadMinApyPct: 'number', notifyLeads: 'boolean', activeStrategy: 'label', minSharpeGain: 'number',
  maxScoutAgeHours: 'number',
};

/**
 * Validate a prefs patch. Returns an error sentence, or null. Pure.
 * A threshold that is NaN or negative would silently disable or flood alerts,
 * so it is refused here rather than clamped.
 */
export function prefsProblem(patch) {
  for (const [key, value] of Object.entries(patch)) {
    const kind = PREF_TYPES[key];
    if (!kind) return `unknown preference "${key}"`;
    if (kind === 'boolean' && typeof value !== 'boolean') return `${key} must be true or false`;
    if (kind === 'number' && !(typeof value === 'number' && Number.isFinite(value) && value >= 0)) return `${key} must be a finite non-negative number`;
    if (kind === 'minutes' && !(Number.isFinite(value) && value >= 15 && value <= 24 * 60)) return `${key} must be 15 to 1440 minutes`;
    if ((kind === 'address' || kind === 'label') && !(value === null || (typeof value === 'string' && value.trim().length > 0 && value.length <= 200))) {
      return `${key} must be a non-empty string or null`;
    }
  }
  return null;
}

const finite = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : null);
const pct = (v, places = 1) => `${v >= 0 ? '+' : ''}${v.toFixed(places)}%`;
const usd = (v) => `$${v.toFixed(v >= 100 ? 0 : 2)}`;

/**
 * Scout pools that may justify moving money. Every condition must hold; a
 * missing field fails it (the daemon's allocator also reads a missing
 * confidence as low):
 * - modelled net APR at or above the bar, and positive in backtest over at
 *   least a day of bars;
 * - confidence medium or high;
 * - no scout flag (each one is a reason the scout itself doubts the number);
 * - an active gauge, since the scout's AERO income assumes one.
 */
export function viableScoutPools(scoutPools, { minNetAprPct }) {
  return (scoutPools ?? [])
    .filter((p) => finite(p?.expected_net_apr) !== null && p.expected_net_apr >= minNetAprPct)
    .filter((p) => finite(p.backtest_net_apr) !== null && p.backtest_net_apr > 0)
    .filter((p) => finite(p.backtest_days) !== null && p.backtest_days >= 1)
    .filter((p) => p.confidence === 'high' || p.confidence === 'medium')
    .filter((p) => Array.isArray(p.flags) && p.flags.length === 0)
    .filter((p) => p.gauge_active === true)
    .filter((p) => finite(p.break_even_deposit_usd) !== null && p.break_even_deposit_usd >= 0)
    .sort((a, b) => b.expected_net_apr - a.expected_net_apr);
}

/** Age of the scout in hours, or null when it carries no usable timestamp. Pure. */
export function scoutAgeHours(liquidity, nowMs) {
  const at = finite(liquidity?.scout?.generated_at);
  return at === null || !finite(nowMs) ? null : (nowMs / 1000 - at) / 3600;
}

/**
 * @param {object} input
 * @param {object} [input.holdings]   summarise() output from src/market/holdings.js
 * @param {object} [input.liquidity]  soltui liquidity.data result, or null when soltui is unavailable
 * @param {Array}  [input.leads]      quoted pools that newly qualify (src/market/pools.js shape)
 * @param {object} [input.top5]       soltui top5.list result, or null
 * @param {string} [input.previousLeader] the Top 5 rank-1 label at the last scan
 * @param {object} input.prefs        merged prefs
 * @param {number} [input.nowMs]      the scan's clock; without it the scout counts as stale
 * @returns {Array<object>} alerts, most severe first
 */
export function computeAlerts({ holdings, liquidity, leads = [], top5, previousLeader = null, prefs, nowMs }) {
  const p = { ...DEFAULT_PREFS, ...prefs };
  const out = [];
  const age = scoutAgeHours(liquidity, nowMs);
  const fresh = age !== null && age >= 0 && age <= p.maxScoutAgeHours;
  const viable = fresh ? viableScoutPools(liquidity?.scout?.pools, p) : [];
  const best = viable[0];

  // 1. A modelled pool beats an open position.
  for (const pos of liquidity?.positions ?? []) {
    const current = finite(pos.apr_realized);
    if (current === null || !best || best.pool === pos.pool) continue;
    const capital = finite(pos.value_usd) ?? finite(pos.deposited_usd);
    const required = finite(best.break_even_deposit_usd);
    if (capital === null || capital <= 0 || required === null || required <= 0 || capital < required) continue;
    const gain = best.expected_net_apr - current;
    if (gain < p.minAprGainPct) continue;
    out.push({
      id: `lp-better:${pos.slot ?? pos.pool}:${best.pool}`,
      kind: 'pool',
      severity: SEVERITY.ACTION,
      source: 'modelled',
      title: `${best.pair} models ${pct(best.expected_net_apr)} net vs your ${pos.pair ?? 'position'} realizing ${pct(current)}`,
      detail: `Aero scout (modelled, ${age.toFixed(0)} h old), tick spacing ${best.tick_spacing}: expected ${pct(best.expected_net_apr)}, `
        + `backtest ${pct(best.backtest_net_apr)} over ${best.backtest_days.toFixed(1)} days, confidence ${best.confidence}. `
        + `Gain ${pct(gain)} APR versus the position's realized rate.`,
      evidence: { pool: best.pool, expectedNetAprPct: best.expected_net_apr, positionAprPct: current },
      link: `https://basescan.org/address/${best.pool}`,
    });
  }

  // 2. Idle capital that a modelled pool would put to work.
  // Base only: scout pools are Aero pools on Base, and Solana stablecoins would
  // need a bridge first. The daemon's own idle figure wins when it is larger.
  const baseStableUsd = (holdings?.chains ?? []).filter((c) => c.chain === 'base').flatMap((c) => c.holdings ?? [])
    .filter((h) => h.included && h.stable && finite(h.usd) !== null).reduce((s, h) => s + h.usd, 0);
  const idleUsd = Math.max(baseStableUsd, finite(liquidity?.wallet?.idle_usd) ?? 0);
  // Below its break-even deposit a position loses to its own rebalancing gas.
  const breakEven = finite(best?.break_even_deposit_usd);
  if (best && idleUsd >= p.minIdleUsd && (breakEven !== null && breakEven > 0 && breakEven <= idleUsd)) {
    const deposit = finite(liquidity?.scout?.deposit_usd);
    out.push({
      id: `idle:${best.pool}`,
      kind: 'pool',
      severity: SEVERITY.ACTION,
      source: 'modelled',
      title: `${usd(idleUsd)} idle on Base; ${best.pair} models ${pct(best.expected_net_apr)} net`,
      detail: `Aero scout (modelled, ${age.toFixed(0)} h old) for a ${deposit === null ? 'deposit of unknown size' : `${usd(deposit)} deposit`}: `
        + `expected ${pct(best.expected_net_apr)}, backtest ${pct(best.backtest_net_apr)} over ${best.backtest_days.toFixed(1)} days`
        + `${breakEven === null ? '' : `, break-even deposit ${usd(breakEven)}`}. A different deposit size changes the result. `
        + 'The liquidity daemon deploys within its own caps; nothing is changed from here.',
      evidence: { pool: best.pool, idleUsd, expectedNetAprPct: best.expected_net_apr, scoutDepositUsd: deposit },
      link: `https://basescan.org/address/${best.pool}`,
    });
  }

  // 3. Top 5 leadership changed, or a Top 5 config beats the strategy in use.
  const configs = Array.isArray(top5?.configs) ? top5.configs : [];
  const sharpe = (c) => finite(c?.home?.median_sharpe);
  const leader = configs.find((c) => c.rank === 1) ?? null;
  if (leader && previousLeader && leader.label !== previousLeader) {
    out.push({
      id: `strategy-leader:${leader.label}`,
      kind: 'strategy',
      severity: SEVERITY.REVIEW,
      source: 'backtest',
      title: `New top strategy: ${leader.label}`,
      detail: `Replaces ${previousLeader}. ${leader.home?.net_pct_text ?? ''}, median Sharpe ${sharpe(leader)?.toFixed(2) ?? '?'}, `
        + `${Math.round((finite(leader.home?.frac_positive) ?? 0) * 100)}% of CPCV paths positive. Backtest, not a live result.`,
      evidence: { label: leader.label, medianSharpe: sharpe(leader) },
      link: null,
    });
  }
  // Only against a strategy with its own Top 5 record: comparing with a made-up
  // zero baseline would call any positive config "better" on no evidence.
  const active = p.activeStrategy ? configs.find((c) => c.label === p.activeStrategy) : null;
  const activeSharpe = sharpe(active);
  if (active && activeSharpe !== null) {
    const better = configs.filter((c) => c.label !== p.activeStrategy && sharpe(c) !== null && sharpe(c) - activeSharpe >= p.minSharpeGain)
      .sort((a, b) => sharpe(b) - sharpe(a))[0];
    if (better) {
      out.push({
        id: `strategy-better:${p.activeStrategy}:${better.label}`,
        kind: 'strategy',
        severity: SEVERITY.REVIEW,
        source: 'backtest',
        title: `${better.label} backtests better than ${p.activeStrategy}`,
        detail: `Median Sharpe ${sharpe(better).toFixed(2)} vs ${activeSharpe.toFixed(2)} `
          + `(${better.home?.net_pct_text ?? 'no net figure'}). Backtest, not a live result.`,
        evidence: { label: better.label, medianSharpe: sharpe(better), activeSharpe },
        link: null,
      });
    }
  }

  // 4. Quoted leads: large pools that newly cross the APY bar. Information only.
  for (const pool of leads) {
    out.push({
      id: `lead:${pool.id}`,
      kind: 'lead',
      severity: SEVERITY.INFO,
      source: 'quoted',
      title: `${pool.project} ${pool.symbol} (${pool.chain}) quotes ${pct(pool.apyMean30d ?? pool.apy)} 30-day mean APY`,
      detail: `TVL ${usd(pool.tvlUsd)}. Quoted by DefiLlama, not measured: includes reward emissions and can fall. `
        + 'Measure before moving money.',
      evidence: { poolId: pool.id, apy: pool.apy, apyMean30d: pool.apyMean30d, tvlUsd: pool.tvlUsd },
      link: pool.link,
    });
  }

  const rank = { action: 0, review: 1, info: 2 };
  return out.sort((a, b) => rank[a.severity] - rank[b.severity]);
}

/** Quoted pools that qualify as a lead under prefs. Pure. */
export function qualifyingLeads(pools, prefs) {
  const p = { ...DEFAULT_PREFS, ...prefs };
  return (pools ?? []).filter((x) => !x.outlier && x.tvlUsd >= p.leadMinTvlUsd
    && (x.apyMean30d ?? x.apy) >= p.leadMinApyPct);
}

/**
 * Merge a fresh scan into the stored alert list. Pure.
 * Keeps each alert's first-seen time; drops alerts the scan no longer produces.
 * Acknowledgements live in their own list (`ackedIds`) so an ack written while a
 * scan is running is never overwritten by that scan. `fresh` lists the ids that are new AND unacknowledged,
 * which is what a notification should be raised for.
 */
export function mergeAlerts(previous, current, nowMs, ackedIds = []) {
  const before = new Map((previous ?? []).map((a) => [a.id, a]));
  const acked = new Set(ackedIds);
  const merged = current.map((a) => {
    const old = before.get(a.id);
    return { ...a, firstSeenMs: old?.firstSeenMs ?? nowMs, lastSeenMs: nowMs, acked: acked.has(a.id) };
  });
  const fresh = merged.filter((a) => !before.has(a.id) && !a.acked).map((a) => a.id);
  return { alerts: merged, fresh };
}

/** Which fresh alerts deserve a system notification. Pure. */
export function notifiable(alerts, freshIds, prefs) {
  const p = { ...DEFAULT_PREFS, ...prefs };
  const ids = new Set(freshIds);
  return alerts.filter((a) => ids.has(a.id) && (a.severity !== SEVERITY.INFO || p.notifyLeads));
}
