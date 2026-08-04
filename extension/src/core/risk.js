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
      state.openNotionalUsd + order.notionalUsd > limits.maxTotalNotionalUsd,
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

/**
 * Account state with every numeric field guaranteed present and finite.
 *
 * Every rail is a comparison, and a comparison against `undefined` or `NaN` is
 * false — which means a missing field silently DISABLES its rail. For a system
 * whose entire job is refusing bad orders, failing open is the worst possible
 * default, so unusable numbers become 0 and are reported.
 */
export function normaliseState(state = {}) {
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
    return v;
  };

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
 * @param {object} arg
 * @param {{notionalUsd:number, slippageBps:number}} arg.order  candidate order
 * @param {object} arg.state  live account state
 * @param {object} arg.limits configured limits
 * @returns {{verdict:string, blockedBy:string[], reasons:string[]}}
 */
export function evaluate({ order, state, limits = DEFAULT_LIMITS }) {
  const merged = { ...DEFAULT_LIMITS, ...limits };
  const safeState = normaliseState(state);
  const blockedBy = [];
  const reasons = [];

  // An order whose own numbers are unusable cannot be risk-checked at all.
  if (!Number.isFinite(order?.notionalUsd) || !Number.isFinite(order?.slippageBps)) {
    return {
      verdict: VERDICT.BLOCK,
      blockedBy: ['unusable-order'],
      reasons: [`order has non-finite notionalUsd or slippageBps: ${JSON.stringify(order)}`],
    };
  }

  const ctx = { order, state: safeState, limits: merged };
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
  };
}

/**
 * Filter a planned batch down to what the rails permit, applying state
 * incrementally so a batch cannot collectively breach a cap that each member
 * passes individually.
 */
export function admitBatch({ intents, state, limits = DEFAULT_LIMITS, slippageBps }) {
  const merged = { ...DEFAULT_LIMITS, ...limits };
  const admitted = [];
  const rejected = [];
  const running = normaliseState(state);

  for (const intent of intents) {
    if (admitted.length >= merged.maxOrdersPerTick) {
      rejected.push({ intent, blockedBy: ['tick-budget'], reasons: ['per-tick order budget reached'] });
      continue;
    }

    const order = { notionalUsd: intent.notionalUsd, slippageBps };
    const result = evaluate({ order, state: running, limits: merged });
    if (result.verdict === VERDICT.ALLOW) {
      admitted.push(intent);
      running.openNotionalUsd += intent.notionalUsd;
      running.openOrderCount += 1;
    } else {
      rejected.push({ intent, blockedBy: result.blockedBy, reasons: result.reasons });
    }
  }

  return { admitted, rejected };
}

/** Rolling UTC-day key, used to reset the daily loss counter. */
export function dayKey(nowMs = Date.now()) {
  return new Date(nowMs).toISOString().slice(0, 10);
}
