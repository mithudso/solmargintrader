import { computeIndicators, validateIndicatorConfig } from './indicators.js';

/** A second eligibility check keeps a delayed UI callback from showing a live signal. */
export function panelModel(snapshot, config, nowMs = Date.now()) {
  const normalized = validateIndicatorConfig(config);
  const rows = snapshot?.candles ?? [];
  const interval = snapshot?.intervalSec;
  if (!Number.isInteger(interval) || interval <= 0 || !Array.isArray(rows)) throw new Error('invalid_snapshot');
  let from = 0;
  for (let i = 0; i < rows.length; i++) {
    if (rows[i].gapBefore || (i && rows[i].time - rows[i - 1].time !== interval)) from = i;
  }
  const candles = rows.slice(from);
  const complete = c => c.closed === true && c.partial !== true && (c.time + interval) * 1000 <= nowMs;
  const end = candles.findLastIndex(complete);
  let start = end;
  while (start >= 0 && complete(candles[start])) start--;
  const closed = candles.slice(start + 1, end + 1);
  // A missed first tick cannot establish a candle's true opening price. Do not
  // seed recursive indicator state from that partial bar after its bucket ends.
  let metricFrom = 0;
  for (let i = 0; i < candles.length; i++) {
    if (candles[i].partial === true && (candles[i].time + interval) * 1000 <= nowMs) metricFrom = i + 1;
  }
  const quote = snapshot?.quote;
  const age = quote ? nowMs - quote.exchangeMs : Infinity;
  const receiptAge = quote ? nowMs - quote.receivedMs : Infinity;
  const fresh = typeof quote?.price === 'number' && Number.isFinite(quote.price) && quote.price > 0 &&
    [age, receiptAge].every(v => Number.isFinite(v) && v >= -250 && v <= 3000);
  const currentOpen = Math.floor(nowMs / 1000 / interval) * interval;
  const currentHistory = closed.at(-1)?.time + interval === currentOpen;
  const eligible = snapshot?.status === 'live' && fresh && currentHistory;
  const completed = computeIndicators(closed, normalized);
  return {
    candles,
    developing: computeIndicators(candles.slice(metricFrom), normalized),
    completed,
    confirmedPivots: completed.zigzag.confirmed,
    closedThrough: closed.at(-1)?.time ?? null,
    closedCount: closed.length,
    gapTrimmed: from > 0,
    signalEligible: eligible,
    ageMs: Number.isFinite(age) ? Math.max(0, age) : null,
    reason: eligible ? null : (!fresh ? 'Oracle quote is unavailable or stale' :
      snapshot?.status !== 'live' ? `Feed ${snapshot?.status || 'unavailable'}` : 'Waiting for the latest complete candle'),
  };
}
