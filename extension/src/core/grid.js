/**
 * Pure grid-strategy engine.
 *
 * No I/O, no chrome.* APIs, no network. Everything here is a deterministic
 * function of (config, price, open state) so the whole strategy is unit
 * testable and a service-worker restart can recompute intent from scratch.
 */

export const SPACING = { ARITH: 'arith', GEOM: 'geom' };
export const SIDE = { BUY: 'buy', SELL: 'sell' };
export const DIRECTION = { LONG: 'long', SHORT: 'short', NEUTRAL: 'neutral' };

/**
 * Grid price levels, lowest first.
 *
 * Geometric spacing gives every rung the same percentage width, which is what
 * you want for an asset that moves in percentage terms; arithmetic spacing
 * gives every rung the same dollar width.
 */
export function gridLevels({ lower, upper, rungs, spacing = SPACING.GEOM }) {
  if (!(lower > 0)) throw new RangeError(`lower must be > 0, got ${lower}`);
  if (!(upper > lower)) throw new RangeError(`upper (${upper}) must exceed lower (${lower})`);
  if (!Number.isInteger(rungs) || rungs < 2) {
    throw new RangeError(`rungs must be an integer >= 2, got ${rungs}`);
  }

  const levels = [];
  if (spacing === SPACING.ARITH) {
    const step = (upper - lower) / (rungs - 1);
    for (let i = 0; i < rungs; i++) levels.push(lower + i * step);
  } else if (spacing === SPACING.GEOM) {
    const ratio = (upper / lower) ** (1 / (rungs - 1));
    for (let i = 0; i < rungs; i++) levels.push(lower * ratio ** i);
  } else {
    throw new RangeError(`unknown spacing "${spacing}"`);
  }

  // Pin the endpoints: float drift otherwise leaves the top rung a hair off
  // `upper`, which shows up as a phantom "level changed" diff every tick.
  levels[0] = lower;
  levels[levels.length - 1] = upper;
  return levels;
}

/** Average percentage width between adjacent rungs — the gross edge per round trip. */
export function rungWidthBps({ lower, upper, rungs, spacing = SPACING.GEOM }) {
  const levels = gridLevels({ lower, upper, rungs, spacing });
  let sum = 0;
  for (let i = 1; i < levels.length; i++) sum += (levels[i] / levels[i - 1] - 1) * 10_000;
  return sum / (levels.length - 1);
}

/**
 * Stable identity for a rung order.
 *
 * Solana/Jupiter has no client-order-ID primitive, so idempotency is our job:
 * this key is derived only from inputs that survive a restart, letting the
 * reconciler match a persisted intent against a live order.
 */
export function intentKey({ gridId, side, level }) {
  // 6 decimal places of USD price — finer than any trigger the API accepts.
  return `${gridId}:${side}:${Math.round(level * 1e6)}`;
}

/** Index of the grid level closest to `price`. */
export function nearestLevelIndex(levels, price) {
  let best = 0;
  let bestDist = Infinity;
  for (let i = 0; i < levels.length; i++) {
    const d = Math.abs(levels[i] - price);
    if (d < bestDist) {
      bestDist = d;
      best = i;
    }
  }
  return best;
}

/**
 * Where the exit for a lot bought at `entryPrice` belongs: ONE RUNG UP.
 *
 * This is the whole economic engine of a grid. Offering at the level you bought
 * at captures nothing and still pays two fees, so the exit has to sit at the
 * next level, making the captured spread equal the rung width.
 */
export function pairedExitLevel({ levels, entryPrice }) {
  const idx = nearestLevelIndex(levels, entryPrice);
  if (idx < levels.length - 1) return levels[idx + 1];
  // A lot bought at the top rung has no rung above it. Extrapolate one more
  // step at the same ratio rather than selling flat.
  const ratio = levels[levels.length - 1] / levels[levels.length - 2];
  return levels[levels.length - 1] * ratio;
}

/**
 * Which side a rung should rest on, considered in isolation.
 *
 * Only used for entries now: exits are derived from open lots by
 * `pairedExitLevel`, not from a level's position relative to the market.
 */
export function sideForLevel({ level, price, deadbandBps = 25 }) {
  const band = (price * deadbandBps) / 10_000;
  if (level < price - band) return SIDE.BUY;
  if (level > price + band) return SIDE.SELL;
  return null;
}

/**
 * The orders the grid *wants* to have resting right now.
 *
 * Two distinct sources, which is the correction that makes the strategy able to
 * earn its rung width:
 *
 *   EXITS   one per open (unmatched) lot, resting one rung ABOVE that lot's
 *           entry. Every sell is the paired exit of a specific buy.
 *   ENTRIES bids at levels below the market that do not already hold a lot.
 *
 * @param {Array<{baseQty:number, priceUsd:number}>} openLots unmatched buy lots,
 *   as produced by pnl.snapshot().openLots
 * @returns {{intents: Array, skipped: Array}}
 */
export function planGrid({ config, price, openIntentKeys = [], openLots = [] }) {
  if (!(price > 0)) throw new RangeError(`price must be > 0, got ${price}`);

  const {
    gridId,
    lower,
    upper,
    rungs,
    spacing = SPACING.GEOM,
    notionalPerRungUsd,
    direction = DIRECTION.NEUTRAL,
    deadbandBps = 25,
    minOrderUsd = 10, // Jupiter Trigger V2 hard minimum
  } = config;

  const levels = gridLevels({ lower, upper, rungs, spacing });
  const open = new Set(openIntentKeys);
  const intents = [];
  const skipped = [];

  // --- exits: one per open lot, one rung above its entry ------------------
  //
  // Lots are AGGREGATED by exit level first. Two lots on the same rung (a
  // partial fill, or a rung that filled twice) both map to the same exit level
  // and therefore the same intentKey — emitting them separately would put two
  // identical keys in one batch, and the executor would submit the rung twice
  // while the journal kept only one record of it.
  const lotLevelIndexes = new Set();
  const exitBuckets = new Map(); // exitLevel -> {baseQty, entries: number[]}

  for (const lot of openLots) {
    if (!(lot.baseQty > 0)) continue;
    lotLevelIndexes.add(nearestLevelIndex(levels, lot.priceUsd));

    if (direction === DIRECTION.SHORT) {
      skipped.push({ level: lot.priceUsd, side: SIDE.SELL, reason: 'short-direction-holds-no-exits' });
      continue;
    }

    const exitLevel = pairedExitLevel({ levels, entryPrice: lot.priceUsd });
    const bucket = exitBuckets.get(exitLevel) ?? { baseQty: 0, entries: [] };
    bucket.baseQty += lot.baseQty;
    bucket.entries.push(lot.priceUsd);
    exitBuckets.set(exitLevel, bucket);
  }

  for (const [exitLevel, bucket] of exitBuckets) {
    const notionalUsd = bucket.baseQty * exitLevel;
    if (notionalUsd < minOrderUsd) {
      skipped.push({ level: exitLevel, side: SIDE.SELL, reason: `below-venue-minimum-${minOrderUsd}usd` });
      continue;
    }

    const key = intentKey({ gridId, side: SIDE.SELL, level: exitLevel });
    if (open.has(key)) {
      skipped.push({ level: exitLevel, side: SIDE.SELL, reason: 'already-resting' });
      continue;
    }

    intents.push({
      intentKey: key,
      gridId,
      side: SIDE.SELL,
      level: exitLevel,
      notionalUsd,
      baseQty: bucket.baseQty,
      entryPriceUsd: bucket.entries.length === 1 ? bucket.entries[0] : null,
      lotCount: bucket.entries.length,
      priceAtPlan: price,
    });
  }

  // --- entries: bids below the market on levels not already holding a lot --
  for (let i = 0; i < levels.length; i++) {
    const level = levels[i];
    const side = sideForLevel({ level, price, deadbandBps });

    if (side !== SIDE.BUY) {
      skipped.push({ level, reason: side === null ? 'inside-deadband' : 'above-market-entry-not-taken' });
      continue;
    }
    if (direction === DIRECTION.SHORT) {
      skipped.push({ level, side, reason: 'short-direction-takes-no-bids' });
      continue;
    }
    if (lotLevelIndexes.has(i)) {
      // Already holding inventory bought here; a second bid would double up.
      skipped.push({ level, side, reason: 'lot-already-held-at-level' });
      continue;
    }
    if (notionalPerRungUsd < minOrderUsd) {
      skipped.push({ level, side, reason: `below-venue-minimum-${minOrderUsd}usd` });
      continue;
    }

    const key = intentKey({ gridId, side: SIDE.BUY, level });
    if (open.has(key)) {
      skipped.push({ level, side, reason: 'already-resting' });
      continue;
    }

    intents.push({
      intentKey: key,
      gridId,
      side: SIDE.BUY,
      level,
      notionalUsd: notionalPerRungUsd,
      baseQty: notionalPerRungUsd / level,
      priceAtPlan: price,
    });
  }

  return { intents, skipped };
}

/**
 * Capital a grid needs before it can run.
 *
 * Only the bids need funding up front: each one becomes the inventory that
 * backs its own paired exit, so no base balance is required to start.
 */
export function capitalRequirement({ config, price }) {
  const { intents } = planGrid({ config, price });
  let quoteUsd = 0;
  let baseQty = 0;
  for (const i of intents) {
    if (i.side === SIDE.BUY) {
      quoteUsd += i.notionalUsd;
      baseQty += i.baseQty; // acquired if the bid fills, then offered one rung up
    }
  }
  return {
    quoteUsd,
    baseQty,
    baseValueUsd: baseQty * price,
    totalUsd: quoteUsd,
  };
}

/** Gross spread a single round trip captures at `level`, before fees. */
export function expectedRoundTripUsd({ config, level }) {
  const levels = gridLevels(config);
  const exit = pairedExitLevel({ levels, entryPrice: level });
  const baseQty = config.notionalPerRungUsd / level;
  return baseQty * (exit - level);
}
