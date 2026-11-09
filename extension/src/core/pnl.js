import { csvCell } from './csv.js';

/**
 * P&L accounting.
 *
 * Two lot-matching modes, because two consumers want different answers:
 *
 *   PAIRED (default)  A sell fill that records the lots its intent was paired
 *     with (`closesLots`) closes THOSE lots. Grid exits are placed one rung above a
 *     specific buy, so when rung B's exit fills before rung A's, the inventory still
 *     held is A's, and strict FIFO would instead consume A and leave B behind. The
 *     planner derives exits from the residual, so a wrong residual re-points a
 *     lot's exit one rung too low: a sell at the level that lot was bought at,
 *     zero spread and two fees. The daily-loss rail reads realized P&L from the
 *     same pass, so it needs the lot that was actually sold too.
 *   FIFO (`{ linkage: false }`)  Ignores `closesLots`; oldest lot first. This is
 *     the IRS default for property and what a tax-style export expects. Nothing
 *     in the live strategy path uses it.
 *
 * Fills stored before linkage existed carry no `closesLots`, so they take the
 * FIFO path in either mode.
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
 * @property {Array<{priceUsd:number, baseQty:number}>} [closesLots]
 *   sells only: the entry lots the originating intent was paired with
 */

const EPS = 1e-12;

/** Entry prices come from the same buy fills, so equality is exact; tolerance is for JSON round trips. */
const samePrice = (a, b) => Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a), Math.abs(b));

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
export function matchFifo(fills, { linkage = true } = {}) {
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

    const closeLot = (idx, want) => {
      const lot = openLots[idx];
      const qty = Math.min(want, lot.baseQty);
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
      if (lot.baseQty <= EPS) openLots.splice(idx, 1);
    };

    // Linked closes first: the lots this sell's intent was paired with, oldest
    // matching lot per entry. Anything the link cannot cover (lot already gone,
    // fill larger than the linked qty) falls through to FIFO below rather than
    // being dropped.
    if (linkage && Array.isArray(fill.closesLots)) {
      for (const link of fill.closesLots) {
        let want = Math.min(remaining, link.baseQty);
        while (want > EPS) {
          const idx = openLots.findIndex((l) => samePrice(l.priceUsd, link.priceUsd));
          if (idx < 0) break;
          const before = remaining;
          closeLot(idx, want);
          want -= before - remaining;
        }
      }
    }

    while (remaining > EPS && openLots.length > 0) closeLot(0, remaining);

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
 * @param {boolean} [arg.linkage]    false for strict FIFO (tax-style); default pairs sells to their lots
 * @param {Array<{costUsd:number}>} [arg.carryEntries] borrow/funding costs
 */
export function snapshot({ fills, markPriceUsd, carryEntries = [], linkage = true }) {
  const m = matchFifo(fills, { linkage });
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
    worstUsd = Math.max(worstUsd, ddUsd);
    // Dollar and proportional maxima need not belong to the same drawdown.
    // A zero/nonpositive peak cannot define a meaningful percentage.
    if (peak > 0) worstPct = Math.max(worstPct, (ddUsd / peak) * 100);
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
    ].map(csvCell).join(','),
  );
  return [header, ...rows].join('\n');
}
