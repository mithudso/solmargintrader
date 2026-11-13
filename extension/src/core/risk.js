/**
 * Risk rails.
 *
 * Every rail is enforced here, in code, as a gate the executor must pass
 * before anything is submitted. A rail that lives only in the README is not a
 * rail. `evaluate()` is pure so the dashboard can show exactly which rail
 * would block a grid before you arm it.
 */

export const VERDICT = { ALLOW: 'allow', BLOCK: 'block' };

export const DEFAULT_LIMITS = Object.freeze({
  killSwitch: false,
  maxTotalNotionalUsd: 500,
  maxNotionalPerOrderUsd: 100,
  maxConcurrentOrders: 12,
  maxLeverage: 1, // 1 = unleveraged. Raising this alone does NOT create leverage.
  dailyLossLimitUsd: 50,
  maxSlippageBps: 300,
  minLiquidationDistancePct: 25, // perps only; ignored by spot venues
  maxOrdersPerTick: 4, // rate-limit budget: keeps a cold start from firing 20 requests
});

/** A single named rail. `test` returns true when the rail is violated. */
const RAILS = [
  {
    id: 'kill-switch',
    test: ({ limits }) => limits.killSwitch === true,
    explain: () => 'kill switch is engaged',
  },
  {
    id: 'slippage-bound',
    test: ({ order, limits }) => order.slippageBps > limits.maxSlippageBps,
    explain: ({ order, limits }) =>
      `slippage ${order.slippageBps}bps exceeds max ${limits.maxSlippageBps}bps`,
  },
  {
    id: 'per-order-notional',
    test: ({ order, limits }) => order.notionalUsd > limits.maxNotionalPerOrderUsd,
    explain: ({ order, limits }) =>
      `order $${order.notionalUsd} exceeds per-order cap $${limits.maxNotionalPerOrderUsd}`,
  },
  {
    id: 'total-notional',
    test: ({ order, state, limits }) =>
      order.capitalIncreaseUsd > 0 && state.openNotionalUsd + order.capitalIncreaseUsd > limits.maxTotalNotionalUsd,
    explain: ({ order, state, limits }) =>
      `open $${state.openNotionalUsd} + $${order.notionalUsd} exceeds total cap $${limits.maxTotalNotionalUsd}`,
  },
  {
    id: 'concurrent-orders',
    test: ({ state, limits }) => state.openOrderCount >= limits.maxConcurrentOrders,
    explain: ({ state, limits }) =>
      `${state.openOrderCount} open orders at cap ${limits.maxConcurrentOrders}`,
  },
  {
    id: 'leverage-cap',
    test: ({ state, limits }) => (state.leverage ?? 1) > limits.maxLeverage,
    explain: ({ state, limits }) =>
      `leverage ${state.leverage} exceeds cap ${limits.maxLeverage}`,
  },
  {
    id: 'daily-loss-limit',
    test: ({ state, limits }) => state.realizedPnlUsdToday <= -Math.abs(limits.dailyLossLimitUsd),
    explain: ({ state, limits }) =>
      `today's realized P&L $${state.realizedPnlUsdToday} hit the daily loss limit $${-Math.abs(limits.dailyLossLimitUsd)}`,
  },
  {
    id: 'liquidation-distance',
    test: ({ state, limits }) =>
      state.liquidationDistancePct != null &&
      state.liquidationDistancePct < limits.minLiquidationDistancePct,
    explain: ({ state, limits }) =>
      `liquidation is ${state.liquidationDistancePct}% away, under the ${limits.minLiquidationDistancePct}% floor`,
  },
];

const quantityTolerance = (a, b) => 32 * Number.EPSILON * Math.max(Math.abs(a), Math.abs(b));

function inventoryPool(lots) {
  if (!Array.isArray(lots)) return null;
  const pool = new Map();
  for (const lot of lots) {
    if (!Number.isFinite(lot?.priceUsd) || lot.priceUsd <= 0 || !Number.isFinite(lot?.baseQty) || lot.baseQty <= 0) return null;
    pool.set(lot.priceUsd, (pool.get(lot.priceUsd) ?? 0) + lot.baseQty);
  }
  return pool;
}

// Coverage must match separately supplied owned lots. A side='sell' or a flag
// on an order cannot establish ownership, especially for a perp short entry.
function reserveCoveredExit(intent, pool) {
  if (!pool || intent.side !== 'sell' || !Number.isFinite(intent.baseQty) || intent.baseQty <= 0
      || !Array.isArray(intent.lots) || intent.lots.length === 0) return false;
  const requested = inventoryPool(intent.lots);
  if (!requested) return false;
  const total = [...requested.values()].reduce((sum, qty) => sum + qty, 0);
  if (!Number.isFinite(total) || Math.abs(total - intent.baseQty) > quantityTolerance(total, intent.baseQty)) return false;
  for (const [price, qty] of requested) {
    const available = pool.get(price) ?? 0;
    if (qty - available > quantityTolerance(qty, available)) return false;
  }
  for (const [price, qty] of requested) pool.set(price, Math.max(0, pool.get(price) - qty));
  return true;
}

const remainingLots = (pool) => pool ? [...pool].filter(([, qty]) => qty > 0)
  .map(([priceUsd, baseQty]) => ({ priceUsd, baseQty })) : [];

/** Owned inventory at mark plus commitments which add capital at risk. */
export function capitalExposure({ openLots, outstanding, markPriceUsd }) {
  const pool = inventoryPool(openLots);
  const inventoryKnown = pool && Number.isFinite(markPriceUsd) && markPriceUsd > 0;
  let notional = inventoryKnown
    ? openLots.reduce((sum, lot) => sum + lot.baseQty * markPriceUsd, 0) : NaN;
  for (const intent of outstanding) {
    if (!reserveCoveredExit(intent, pool)) {
      // Missing size is uncertainty, not available headroom. A covered sell
      // reserves owned units but does not add a second copy of their value.
      notional += Number.isFinite(intent.notionalUsd) && intent.notionalUsd > 0 ? intent.notionalUsd : NaN;
    }
  }
  return { openNotionalUsd: notional, openOrderCount: outstanding.length, unreservedLots: remainingLots(pool) };
}

/**
 * Account state with every numeric field guaranteed present and finite.
 *
 * Every rail is a comparison, and a comparison against `undefined` or `NaN` is
 * false — which means a missing field silently DISABLES its rail. For a system
 * whose entire job is refusing bad orders, failing open is the worst possible
 * default, so unusable numbers become 0 and are reported.
 */
export function normaliseState(state = {}) {
  if (!state || typeof state !== 'object' || Array.isArray(state)) state = {};
  const problems = [];
  const num = (key, fallback = 0) => {
    const v = state[key];
    if (v == null) {
      problems.push(`${key} was missing; treated as ${fallback}`);
      return fallback;
    }
    if (!Number.isFinite(v)) {
      problems.push(`${key} was ${v}; treated as ${fallback}`);
      return fallback;
    }
    if ((key !== 'realizedPnlUsdToday' && v < 0) ||
        (key === 'openOrderCount' && !Number.isSafeInteger(v))) {
      problems.push(`${key} was outside its valid domain; treated as ${fallback}`);
      return fallback;
    }
    return v;
  };

  if (state.liquidationDistancePct != null && !Number.isFinite(state.liquidationDistancePct)) {
    problems.push('liquidationDistancePct was non-finite');
  }
  return {
    openNotionalUsd: num('openNotionalUsd'),
    openOrderCount: num('openOrderCount'),
    realizedPnlUsdToday: num('realizedPnlUsdToday'),
    leverage: num('leverage', 1),
    // Genuinely optional: spot venues have no liquidation price, and null here
    // means "not applicable", not "missing".
    liquidationDistancePct:
      state.liquidationDistancePct == null || !Number.isFinite(state.liquidationDistancePct)
        ? null
        : state.liquidationDistancePct,
    problems,
  };
}

/**
 * Limits with every numeric cap guaranteed finite and non-negative.
 *
 * The mirror of `normaliseState`: every rail compares against a limit, and a
 * comparison against NaN, undefined or a string is false, so a bad limit would
 * silently switch its rail off. An unusable value falls back to the DEFAULT_LIMITS
 * value for diagnostics (never to Infinity) and is reported. Admission blocks
 * while a stored limit is invalid. An unclear kill switch means ENGAGED.
 *
 * Does not tighten or loosen anything for valid input.
 */
export function normaliseLimits(limits = {}) {
  const problems = [];
  if (!limits || typeof limits !== 'object' || Array.isArray(limits)) {
    problems.push('limits must be an object; admission refused');
    limits = {};
  }
  const merged = { ...DEFAULT_LIMITS, ...limits };
  for (const key of Object.keys(DEFAULT_LIMITS)) {
    if (key === 'killSwitch') continue;
    const v = merged[key];
    if (typeof v !== 'number' || !Number.isFinite(v) || v < 0 ||
        (['maxConcurrentOrders', 'maxOrdersPerTick'].includes(key) && !Number.isSafeInteger(v))) {
      problems.push(`${key} was invalid; diagnostic default ${DEFAULT_LIMITS[key]} applied`);
      merged[key] = DEFAULT_LIMITS[key];
    }
  }
  if (typeof merged.killSwitch !== 'boolean') {
    problems.push('killSwitch was invalid; treated as engaged');
    merged.killSwitch = true;
  }
  return { ...merged, problems };
}

/**
 * @param {object} arg
 * @param {{notionalUsd:number, slippageBps:number}} arg.order  candidate order
 * @param {object} arg.state  live account state
 * @param {object} arg.limits configured limits
 * @returns {{verdict:string, blockedBy:string[], reasons:string[]}}
 */
export function evaluate({ order, state, limits = DEFAULT_LIMITS, openLots = [] }) {
  const { problems: limitProblems, ...merged } = normaliseLimits(limits);
  const safeState = normaliseState(state);
  const blockedBy = [];
  const reasons = [];

  if (limitProblems.length) {
    blockedBy.push('unusable-limits');
    reasons.push(...limitProblems);
  }

  // An order whose own numbers are unusable cannot be risk-checked at all.
  if (!Number.isFinite(order?.notionalUsd) || order.notionalUsd <= 0 ||
      !Number.isFinite(order?.slippageBps) || order.slippageBps < 0) {
    return {
      verdict: VERDICT.BLOCK,
      blockedBy: ['unusable-order'],
      reasons: ['order requires finite positive notionalUsd and finite nonnegative slippageBps'],
    };
  }

  if (safeState.problems.length) {
    blockedBy.push('unusable-state');
    reasons.push(...safeState.problems);
  }

  const coveredExit = reserveCoveredExit(order, inventoryPool(openLots));
  const capitalIncreaseUsd = coveredExit ? 0 : order.notionalUsd;
  const ctx = { order: { ...order, capitalIncreaseUsd }, state: safeState, limits: merged };
  for (const rail of RAILS) {
    if (rail.test(ctx)) {
      blockedBy.push(rail.id);
      reasons.push(rail.explain(ctx));
    }
  }

  return {
    verdict: blockedBy.length ? VERDICT.BLOCK : VERDICT.ALLOW,
    blockedBy,
    reasons,
    stateProblems: safeState.problems,
    limitProblems,
    capitalIncreaseUsd,
  };
}

/**
 * Filter a planned batch down to what the rails permit, applying state
 * incrementally so a batch cannot collectively breach a cap that each member
 * passes individually.
 */
export function admitBatch({ intents, state, limits = DEFAULT_LIMITS, slippageBps, openLots = [] }) {
  const { problems: limitProblems, ...merged } = normaliseLimits(limits);
  const admitted = [];
  const rejected = [];
  const running = normaliseState(state);
  const unreserved = inventoryPool(openLots);

  for (const intent of intents) {
    if (admitted.length >= merged.maxOrdersPerTick) {
      rejected.push({ intent, blockedBy: ['tick-budget'], reasons: ['per-tick order budget reached'] });
      continue;
    }

    const order = { ...intent, slippageBps };
    // Keep the original invalid fields visible to evaluate; normalization alone
    // cannot turn missing exposure or P&L into proof that an order is safe.
    const result = evaluate({ order, state: running.problems.length ? state : running, limits, openLots: remainingLots(unreserved) });
    if (result.verdict === VERDICT.ALLOW) {
      admitted.push(intent);
      running.openNotionalUsd += result.capitalIncreaseUsd;
      if (result.capitalIncreaseUsd === 0) reserveCoveredExit(intent, unreserved);
      // A resting exit has not sold anything yet, so it cannot fund a new buy.
      running.openOrderCount += 1;
    } else {
      rejected.push({ intent, blockedBy: result.blockedBy, reasons: result.reasons });
    }
  }

  return { admitted, rejected, limitProblems };
}

/** Rolling UTC-day key, used to reset the daily loss counter. */
export function dayKey(nowMs = Date.now()) {
  return new Date(nowMs).toISOString().slice(0, 10);
}
