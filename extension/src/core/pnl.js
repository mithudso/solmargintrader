/**
 * P&L accounting.
 *
 * Realized P&L uses FIFO lot matching: a sell fill is matched against the
 * oldest unmatched buy lots, which is both the IRS default for property and
 * the convention every crypto tax tool expects, so the CSV export lines up
 * with whatever you reconcile against later.
 *
 * Costs are never optional. Every fill carries its fee, and any carry cost
 * (perps borrow, lend interest) is passed in explicitly rather than assumed —
 * venues differ, and a hardcoded funding rate is a silent lie in the numbers.
 */

/**
 * @typedef {object} Fill
 * @property {string} id
 * @property {string} gridId
 * @property {string} side            'buy' | 'sell'
 * @property {number} baseQty         base units filled (e.g. SOL)
 * @property {number} priceUsd        realized execution price, not the trigger price
 * @property {number} feeUsd          all execution costs for this fill
 * @property {number} tsMs
 * @property {number} [level]         the rung this fill belongs to
 */

/** Sum of carry cost entries, e.g. perps borrow or lend interest accrued. */
export function totalCarryUsd(carryEntries = []) {
  return carryEntries.reduce((acc, c) => acc + (c.costUsd || 0), 0);
}

/**
 * FIFO-match fills into closed round trips.
 *
 * @returns {{
 *   roundTrips: Array<{openTsMs:number, closeTsMs:number, baseQty:number,
 *     entryUsd:number, exitUsd:number, feeUsd:number, grossUsd:number, netUsd:number}>,
 *   openLots: Array<{baseQty:number, priceUsd:number, feeUsd:number, tsMs:number}>,
 *   realizedGrossUsd:number, realizedFeeUsd:number, realizedNetUsd:number,
 *   unmatchedSellQty:number
 * }}
 */
export function matchFifo(fills) {
  const ordered = [...fills].sort((a, b) => a.tsMs - b.tsMs || a.id.localeCompare(b.id));
  /** @type {Array<{baseQty:number, priceUsd:number, feeUsd:number, tsMs:number}>} */
  const openLots = [];
  const roundTrips = [];
  let realizedGrossUsd = 0;
  let realizedFeeUsd = 0;
  let unmatchedSellQty = 0;

  for (const fill of ordered) {
    if (fill.side === 'buy') {
      openLots.push({
        baseQty: fill.baseQty,
        priceUsd: fill.priceUsd,
        // Carry the entry fee on the lot so a partial close only realizes its
        // proportional share of it.
        feeUsd: fill.feeUsd || 0,
        tsMs: fill.tsMs,
      });
      continue;
    }

    let remaining = fill.baseQty;
    const sellFeeRate = fill.baseQty > 0 ? (fill.feeUsd || 0) / fill.baseQty : 0;

    while (remaining > 1e-12 && openLots.length > 0) {
      const lot = openLots[0];
      const qty = Math.min(remaining, lot.baseQty);
      const lotFeeShare = lot.baseQty > 0 ? (lot.feeUsd * qty) / lot.baseQty : 0;
      const sellFeeShare = sellFeeRate * qty;

      const entryUsd = qty * lot.priceUsd;
      const exitUsd = qty * fill.priceUsd;
      const feeUsd = lotFeeShare + sellFeeShare;
      const grossUsd = exitUsd - entryUsd;

      roundTrips.push({
        openTsMs: lot.tsMs,
        closeTsMs: fill.tsMs,
        baseQty: qty,
        entryUsd,
        exitUsd,
        feeUsd,
        grossUsd,
        netUsd: grossUsd - feeUsd,
      });

      realizedGrossUsd += grossUsd;
      realizedFeeUsd += feeUsd;

      lot.baseQty -= qty;
      lot.feeUsd -= lotFeeShare;
      remaining -= qty;
      if (lot.baseQty <= 1e-12) openLots.shift();
    }

    // A sell with no lot behind it means the grid went short, or the fill log
    // is missing a buy. Surfaced rather than silently dropped.
    if (remaining > 1e-12) unmatchedSellQty += remaining;
  }

  return {
    roundTrips,
    openLots,
    realizedGrossUsd,
    realizedFeeUsd,
    realizedNetUsd: realizedGrossUsd - realizedFeeUsd,
    unmatchedSellQty,
  };
}

/**
 * Full P&L snapshot.
 *
 * @param {object} arg
 * @param {Fill[]} arg.fills
 * @param {number} arg.markPriceUsd  current mark for open inventory
 * @param {Array<{costUsd:number}>} [arg.carryEntries] borrow/funding costs
 */
export function snapshot({ fills, markPriceUsd, carryEntries = [] }) {
  const m = matchFifo(fills);
  const carryUsd = totalCarryUsd(carryEntries);

  const openBaseQty = m.openLots.reduce((a, l) => a + l.baseQty, 0);
  const openCostUsd = m.openLots.reduce((a, l) => a + l.baseQty * l.priceUsd, 0);
  const openFeeUsd = m.openLots.reduce((a, l) => a + l.feeUsd, 0);
  const openMarketUsd = openBaseQty * markPriceUsd;

  // Unrealized is net of the entry fees still sitting on those open lots.
  const unrealizedNetUsd = openMarketUsd - openCostUsd - openFeeUsd;
  const realizedNetUsd = m.realizedNetUsd - carryUsd;

  return {
    realizedGrossUsd: m.realizedGrossUsd,
    realizedFeeUsd: m.realizedFeeUsd,
    carryUsd,
    realizedNetUsd,
    openBaseQty,
    openCostUsd,
    openMarketUsd,
    avgEntryUsd: openBaseQty > 0 ? openCostUsd / openBaseQty : 0,
    unrealizedNetUsd,
    totalNetUsd: realizedNetUsd + unrealizedNetUsd,
    roundTripCount: m.roundTrips.length,
    winRate: winRate(m.roundTrips),
    feeTotalUsd: m.realizedFeeUsd + openFeeUsd + carryUsd,
    unmatchedSellQty: m.unmatchedSellQty,
    roundTrips: m.roundTrips,
    openLots: m.openLots,
  };
}

export function winRate(roundTrips) {
  if (roundTrips.length === 0) return 0;
  return roundTrips.filter((r) => r.netUsd > 0).length / roundTrips.length;
}

/**
 * Equity curve from closed round trips, marked at close time.
 * Carry entries are folded in at their own timestamps when supplied.
 */
export function equityCurve({ roundTrips, carryEntries = [], startEquityUsd = 0 }) {
  const events = [
    ...roundTrips.map((r) => ({ tsMs: r.closeTsMs, deltaUsd: r.netUsd })),
    ...carryEntries.map((c) => ({ tsMs: c.tsMs, deltaUsd: -(c.costUsd || 0) })),
  ].sort((a, b) => a.tsMs - b.tsMs);

  let equity = startEquityUsd;
  const points = [{ tsMs: events[0]?.tsMs ?? Date.now(), equityUsd: equity }];
  for (const e of events) {
    equity += e.deltaUsd;
    points.push({ tsMs: e.tsMs, equityUsd: equity });
  }
  return points;
}

/** Peak-to-trough drawdown of an equity curve, in dollars and percent of peak. */
export function maxDrawdown(points) {
  let peak = -Infinity;
  let worstUsd = 0;
  let worstPct = 0;
  for (const p of points) {
    if (p.equityUsd > peak) peak = p.equityUsd;
    const ddUsd = peak - p.equityUsd;
    if (ddUsd > worstUsd) {
      worstUsd = ddUsd;
      // Percent is only meaningful against a positive peak; a curve starting
      // at zero equity would otherwise divide by zero.
      worstPct = peak > 0 ? (ddUsd / peak) * 100 : 0;
    }
  }
  return { drawdownUsd: worstUsd, drawdownPct: worstPct };
}

/** Fill log as CSV. */
export function fillsToCsv(fills) {
  const header = 'id,gridId,tsIso,side,baseQty,priceUsd,notionalUsd,feeUsd,level';
  const rows = fills.map((f) =>
    [
      f.id,
      f.gridId,
      new Date(f.tsMs).toISOString(),
      f.side,
      f.baseQty,
      f.priceUsd,
      (f.baseQty * f.priceUsd).toFixed(6),
      f.feeUsd ?? 0,
      f.level ?? '',
    ].join(','),
  );
  return [header, ...rows].join('\n');
}
