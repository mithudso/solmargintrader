/** Isolated paper positions. All prices are USD and all percentages are price distances. */
export const MARKETS = Object.freeze({
  SOL: { venue: 'JLP', max: 250, feed: 6, mint: 'So11111111111111111111111111111111111111112', impactStep: 375000 },
  ETH: { venue: 'JLP', max: 250, feed: 2, mint: '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs', impactStep: 1500000 },
  BTC: { venue: 'JLP', max: 250, feed: 1, mint: '3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh', impactStep: 2400000 },
  ZEC: { venue: 'GUM', max: 50 },
  HYPE: { venue: 'GUM', max: 25 },
});

const positive = value => Number.isFinite(value) && value > 0;
const nonnegative = value => Number.isFinite(value) && value >= 0;
const bps = 10000;

export function planPosition(settings, market, price, direction = 1, weight = 1) {
  const { sizing, amount, leverage, tp, sl, slippageBps, additiveBps, networkUsd } = settings;
  if (!market || !positive(price) || ![1, -1].includes(direction) || !positive(weight) || weight > 1
      || !['collateral', 'notional'].includes(sizing) || !positive(amount)
      || !Number.isFinite(leverage) || leverage < 1.1 || leverage > market.max
      || ![tp, sl].every(v => nonnegative(v) && v < 100)
      || ![slippageBps, additiveBps, networkUsd, market.baseBps, market.maintenanceBps].every(nonnegative)
      || slippageBps >= bps || !Number.isFinite(market.carryBps)
      || (market.venue === 'JLP' && (market.carryBps < 0 || !positive(market.impactStep)
        || !nonnegative(market.maxImpactBps)))
      || (market.venue === 'GUM' && (!positive(market.firstTierCap) || !positive(market.maxOrder)
        || !positive(market.maxQty) || !positive(market.minOrder) || !positive(market.stepSize)
        || !nonnegative(market.liquidationBps)))) throw new Error('Enter valid position settings and wait for venue terms.');
  const entry = price * (1 + direction * slippageBps / bps);
  const requested = (sizing === 'collateral' ? amount * leverage : amount) * weight;
  const units = market.venue === 'GUM' ? Math.floor((requested / entry) / market.stepSize) * market.stepSize : requested / entry;
  const size = units * entry;
  if (!positive(size) || (market.venue === 'GUM' && (size < market.minOrder || requested >= market.firstTierCap
      || size > market.maxOrder || units > market.maxQty))) {
    throw new Error('Size must fit the modeled first maintenance tier and the market-order limits.');
  }
  const deposit = size / leverage;
  const linearBps = market.venue === 'JLP' ? Math.min(market.maxImpactBps, Math.ceil(size / market.impactStep)) : 0;
  const impactBps = market.venue === 'JLP' ? Math.min(market.maxImpactBps, linearBps + additiveBps) : 0;
  const feeBps = market.baseBps + impactBps;
  const openCost = size * feeBps / bps + networkUsd;
  const position = {
    venue: market.venue, entry, direction, size, units, deposit, openCost, feeBps, linearBps,
    collateral: deposit - openCost,
    stop: sl ? entry * (1 - direction * sl / 100) : null,
    take: tp ? entry * (1 + direction * tp / 100) : null,
    market, slippageBps, networkUsd,
  };
  const liquidation = liquidationPrice(position, 0);
  if (market.venue === 'GUM' && units * liquidation >= market.firstTierCap) {
    throw new Error('Liquidation crosses the modeled first maintenance tier.');
  }
  if (direction * (price - liquidation) <= 0 || deposit <= openCost) {
    throw new Error('The assumed opening costs and slippage exhaust the liquidation buffer.');
  }
  return { ...position, liquidation };
}

export function liquidationPrice(position, carry) {
  const { market, venue, collateral, direction, entry, size, units, linearBps } = position;
  if (!Number.isFinite(carry)) throw new Error('Carry is unavailable.');
  if (venue === 'JLP') {
    const reserve = (market.maintenanceBps + market.baseBps + linearBps) * size / bps;
    return Math.max(0, entry - direction * (collateral - carry - reserve) / units);
  }
  const reserveRate = (market.maintenanceBps + market.baseBps + market.liquidationBps) / bps;
  return Math.max(0, (direction * entry - (collateral - carry) / units) / (direction - reserveRate));
}

export function carryCost(position, from, to, mark) {
  const { venue, market, direction, units, size } = position;
  if (!positive(mark) || !Number.isFinite(from) || !Number.isFinite(to) || to < from) {
    throw new Error('Carry interval is unavailable.');
  }
  if (venue === 'JLP') return size * market.carryBps / bps * (to - from) / 3600;
  const hours = Math.floor(to / 3600) - Math.floor(from / 3600);
  return direction * units * mark * market.carryBps / bps * hours;
}

/** A gap through a stop fills at the opening price. If hit order is unknown, prefer the adverse exit. */
export function barrier(position, bar, carry) {
  const { direction, take, stop } = position;
  const liq = liquidationPrice(position, carry);
  const adverse = direction === 1 ? bar.low : bar.high;
  const favorable = direction === 1 ? bar.high : bar.low;
  const passed = (value, level) => direction * (value - level) <= 0;
  if (passed(bar.open, liq)) return { reason: 'liquidation', price: bar.open };
  if (stop !== null && passed(bar.open, stop)) return { reason: 'stop', price: bar.open };
  if (take !== null && direction * (bar.open - take) >= 0) return { reason: 'take', price: take };
  if (passed(adverse, liq)) return { reason: 'liquidation', price: liq };
  if (stop !== null && passed(adverse, stop)) return { reason: 'stop', price: stop };
  if (take !== null && direction * (favorable - take) >= 0) return { reason: 'take', price: take };
  return null;
}

export function settle(position, exit, carry) {
  const { venue, market, direction, entry, units, deposit, size, openCost, feeBps, slippageBps, networkUsd } = position;
  const price = exit.price * (1 - direction * slippageBps / bps);
  const gross = direction * units * (price - entry);
  const closeNotional = venue === 'JLP' ? size : price * units;
  const fee = exit.reason === 'liquidation'
    ? (venue === 'JLP' ? 0 : market.baseBps + market.liquidationBps) : feeBps;
  const closeCost = closeNotional * fee / bps + networkUsd;
  const pnl = exit.reason === 'liquidation' && venue === 'JLP'
    ? -deposit : Math.max(-deposit, gross - openCost - closeCost - carry);
  return { ...exit, price, pnl, deposit, carry, openCost, closeCost };
}
