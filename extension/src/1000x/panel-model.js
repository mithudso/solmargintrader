import { computeIndicators, validateIndicatorConfig } from './indicators.js';
import { reversalContext } from './reversal.js';

export const Z_SCORE_LENGTH = 20;
const MAX_QUOTE_AGE_MS = 3000;

function latestZScore(candles) {
  const window = candles.slice(-Z_SCORE_LENGTH);
  if (window.length < Z_SCORE_LENGTH) return null;
  const close = window.at(-1).close;
  // Center and scale first so the sample variance stays representable.
  const scale = Math.max(...window.map(candle => Math.abs(candle.close - close)));
  if (scale === 0) return 0;
  const deviations = window.map(candle => (candle.close - close) / scale);
  const mean = deviations.reduce((sum, value) => sum + value, 0) / window.length;
  const squared = deviations.reduce((sum, value) => sum + (value - mean) ** 2, 0);
  const sd = Math.sqrt(squared / (window.length - 1));
  return sd * scale <= 1e-15 ? 0 : -mean / sd;
}

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
    [age, receiptAge].every(v => Number.isFinite(v) && v >= -250 && v <= MAX_QUOTE_AGE_MS);
  const currentOpen = Math.floor(nowMs / 1000 / interval) * interval;
  const currentHistory = closed.at(-1)?.time + interval === currentOpen;
  const eligible = snapshot?.status === 'live' && fresh && currentHistory;
  const completed = computeIndicators(closed, normalized);
  const developingCandles = candles.slice(metricFrom);
  const developing = computeIndicators(developingCandles, normalized);
  const current = developingCandles.at(-1);
  const currentQuote = eligible && Math.floor(quote.exchangeMs / 1000 / interval) * interval === currentOpen;
  const currentTick = currentQuote && current?.closed === false && current.time === currentOpen && current.close === quote.price;
  const stale = snapshot?.status === 'stale' || Boolean(quote && (age > MAX_QUOTE_AGE_MS || receiptAge > MAX_QUOTE_AGE_MS));
  const immediate = {
    state: currentTick ? 'live' : stale ? 'stale' : 'unavailable',
    zScore: currentTick ? latestZScore(developingCandles) : null,
    rsi: currentTick ? developing.rsi.latest : null,
    // A partial candle can supply a close, but its open and range are unverified.
    bop: currentTick && !current.partial ? developing.bop.latest : null,
    bopPartial: currentTick && current.partial === true,
    macdHistogram: currentTick ? developing.macd.histogramLatest : null,
  };
  const minutes = snapshot?.minuteCandles ?? (interval === 60 ? candles : []);
  const minuteReady = (snapshot?.minuteStatus === 'ready' || (snapshot?.minuteStatus === undefined && interval === 60))
    && minutes.some(candle => candle.closed === true && candle.partial !== true
      && candle.time + 60 === Math.floor(nowMs / 60_000) * 60);
  return {
    candles,
    developing,
    completed,
    immediate,
    reversal: reversalContext(minutes, nowMs, eligible && minuteReady),
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
