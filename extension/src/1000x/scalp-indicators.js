/**
 * Pure, causal readings on one-second oracle bars.
 *
 * Every function reads closed bars oldest-first and returns the reading at the
 * last bar, or null while it warms up. Nothing here reads a clock, the network
 * or storage. The definitions are a port of research/scripts/scalp_1s_features.py;
 * test/1000x-scalp.test.js compares them with values that script wrote from
 * recorded Jupiter oracle ticks.
 *
 * A positive reading always means "price has been rising".
 */

// A silence longer than this starts a new segment: no reading spans seconds the
// oracle never published.
export const MAX_GAP_S = 3;
export const RETAIN_BARS = 900;
// Below this magnitude a reading casts no vote, so summation order cannot turn
// an exact tie into a direction.
export const VOTE_EPSILON = 1e-9;

const finitePrice = value => typeof value === 'number' && Number.isFinite(value) && value > 0;

/** Aggregates quotes into closed 1s bars. A bar closes when a later second trades. */
export class SecondBars {
  #bars = [];
  #current = null;
  #segment = 0;

  /** Returns how many bars this quote closed; -1 when it started a new segment. */
  push(quote) {
    const price = quote?.price, ms = quote?.exchangeMs;
    if (!finitePrice(price) || typeof ms !== 'number' || !Number.isFinite(ms) || ms <= 0) return 0;
    const time = Math.floor(ms / 1000);
    const current = this.#current;
    if (!current) {
      this.#current = { time, open: price, high: price, low: price, close: price };
      return 0;
    }
    if (time < current.time) return 0;
    if (time === current.time) {
      current.high = Math.max(current.high, price);
      current.low = Math.min(current.low, price);
      current.close = price;
      return 0;
    }
    const missing = time - current.time - 1;
    if (missing > MAX_GAP_S) {
      this.reset();
      this.#current = { time, open: price, high: price, low: price, close: price };
      return -1;
    }
    this.#bars.push(current);
    // The oracle published nothing in these seconds; its last price still stood.
    for (let i = 1; i <= missing; i++) {
      const c = current.close;
      this.#bars.push({ time: current.time + i, open: c, high: c, low: c, close: c, filled: true });
    }
    if (this.#bars.length > RETAIN_BARS) this.#bars.splice(0, this.#bars.length - RETAIN_BARS);
    this.#current = { time, open: price, high: price, low: price, close: price };
    return missing + 1;
  }

  reset() {
    this.#bars = [];
    this.#current = null;
    this.#segment += 1;
  }

  /** Closed bars, oldest first. The developing second is never included. */
  get bars() { return this.#bars; }
  get developing() { return this.#current ? { ...this.#current } : null; }
  /** Increments whenever history was discarded; callers drop pending state with it. */
  get segment() { return this.#segment; }
}

const closes = bars => bars.map(bar => bar.close);

function rawEma(values, span) {
  const alpha = 2 / (span + 1), out = new Array(values.length);
  let previous = values[0];
  for (let i = 0; i < values.length; i++) {
    previous = i === 0 ? values[0] : alpha * values[i] + (1 - alpha) * previous;
    out[i] = previous;
  }
  return out;
}

function trueRanges(bars) {
  return bars.map((bar, i) => {
    const previous = i ? bars[i - 1].close : bar.close;
    return Math.max(bar.high - bar.low, Math.abs(bar.high - previous), Math.abs(bar.low - previous));
  });
}

/** Percent change over n seconds, in basis points. */
export function rocBps(bars, n) {
  if (bars.length <= n) return null;
  return (bars.at(-1).close / bars.at(-1 - n).close - 1) * 1e4;
}

/** +1 when the last close exceeds the prior window's high, -1 below its low, else 0. */
export function breakout(bars, window) {
  if (bars.length <= window) return null;
  let high = -Infinity, low = Infinity;
  for (let i = bars.length - 1 - window; i < bars.length - 1; i++) {
    high = Math.max(high, bars[i].high);
    low = Math.min(low, bars[i].low);
  }
  const close = bars.at(-1).close;
  return close > high ? 1 : close < low ? -1 : 0;
}

/** Signed run length of same-colour Heikin-Ashi bars, capped at 20. */
export function heikinAshiStreak(bars, cap = 20) {
  if (!bars.length) return null;
  let haOpen = (bars[0].open + bars[0].close) / 2, previousClose = 0, run = 0;
  for (let i = 0; i < bars.length; i++) {
    const { open, high, low, close } = bars[i];
    const haClose = (open + high + low + close) / 4;
    if (i) haOpen = (haOpen + previousClose) / 2;
    const colour = haClose > haOpen ? 1 : haClose < haOpen ? -1 : 0;
    run = colour === 0 ? 0 : run * colour > 0 ? run + colour : colour;
    run = Math.max(-cap, Math.min(cap, run));
    previousClose = haClose;
  }
  return run;
}

/** Mean of (close-open)/(high-low) over n bars; a zero-range bar counts as 0. */
export function bopSma(bars, n) {
  if (bars.length < n) return null;
  let sum = 0;
  for (let i = bars.length - n; i < bars.length; i++) {
    const range = bars[i].high - bars[i].low;
    sum += range > 0 ? (bars[i].close - bars[i].open) / range : 0;
  }
  return sum / n;
}

/** Direction of the current close-only ZigZag leg: +1 after a confirmed low. */
export function zigzagDirection(bars, thresholdBps) {
  if (!bars.length) return null;
  const fraction = thresholdBps / 1e4;
  let state = 0, high = bars[0].close, low = bars[0].close;
  for (const { close } of bars) {
    if (state === 0) {
      if (close > high) high = close;
      if (close < low) low = close;
      if (close >= low * (1 + fraction)) { state = 1; high = close; }
      else if (close <= high * (1 - fraction)) { state = -1; low = close; }
    } else if (state === 1) {
      if (close > high) high = close;
      else if (close <= high * (1 - fraction)) { state = -1; low = close; }
    } else if (close < low) low = close;
    else if (close >= low * (1 + fraction)) { state = 1; high = close; }
  }
  return state === 0 ? null : state;
}

/** Position of the close in the window's high-low range, in [-0.5, 0.5]. */
export function donchianPosition(bars, window) {
  if (bars.length < window) return null;
  let high = -Infinity, low = Infinity;
  for (let i = bars.length - window; i < bars.length; i++) {
    high = Math.max(high, bars[i].high);
    low = Math.min(low, bars[i].low);
  }
  return high > low ? (bars.at(-1).close - low) / (high - low) - 0.5 : 0;
}

/** Kaufman efficiency ratio times the direction of the window's net change. */
export function efficiencyRatio(bars, window) {
  if (bars.length <= window) return null;
  let path = 0;
  for (let i = bars.length - window; i < bars.length; i++) path += Math.abs(bars[i].close - bars[i - 1].close);
  return path > 0 ? (bars.at(-1).close - bars.at(-1 - window).close) / path : 0;
}

/** t-statistic of the least-squares slope of close on time over the window. */
export function slopeT(bars, window) {
  if (bars.length < window) return null;
  const values = closes(bars.slice(-window));
  const mean = values.reduce((sum, value) => sum + value, 0) / window;
  let sxx = 0, sxy = 0, scale = 0;
  for (let i = 0; i < window; i++) {
    const x = i - (window - 1) / 2;
    sxx += x * x;
    sxy += x * (values[i] - mean);
    scale = Math.max(scale, Math.abs(values[i]));
  }
  const slope = sxy / sxx;
  let sse = 0;
  for (let i = 0; i < window; i++) {
    const residual = values[i] - mean - slope * (i - (window - 1) / 2);
    sse += residual * residual;
  }
  const se = Math.sqrt(sse / (window - 2) / sxx);
  return se > scale * 1e-12 ? Math.max(-50, Math.min(50, slope / se)) : 0;
}

/** Least-squares slope of close on time over the window, in basis points of price per second. */
export function slopeBps(bars, window) {
  if (bars.length < window) return null;
  const from = bars.length - window;
  let mean = 0;
  for (let i = 0; i < window; i++) mean += bars[from + i].close;
  mean /= window;
  let sxx = 0, sxy = 0;
  for (let i = 0; i < window; i++) {
    const x = i - (window - 1) / 2;
    sxx += x * x;
    sxy += x * (bars[from + i].close - mean);
  }
  return sxy / sxx / bars.at(-1).close * 1e4;
}

/**
 * Second derivative of a least-squares parabola through the window, in basis
 * points per second squared. Positive means the slope is increasing. With time
 * centred on the window the quadratic term is orthogonal to the linear one.
 */
export function curvatureBps(bars, window) {
  if (bars.length < window) return null;
  const from = bars.length - window;
  let mean = 0, meanSquare = 0;
  for (let i = 0; i < window; i++) {
    const x = i - (window - 1) / 2;
    mean += bars[from + i].close;
    meanSquare += x * x;
  }
  mean /= window;
  meanSquare /= window;
  let sqq = 0, sqy = 0;
  for (let i = 0; i < window; i++) {
    const x = i - (window - 1) / 2, q = x * x - meanSquare;
    sqq += q * q;
    sqy += q * (bars[from + i].close - mean);
  }
  return 2 * sqy / sqq / bars.at(-1).close * 1e4;
}

/** Wilder RSI with an SMA seed, mapped to [-1, 1]; a flat window reads 0. */
export function rsiCentered(bars, n) {
  if (bars.length <= n) return null;
  let gain = 0, loss = 0;
  for (let i = 1; i <= n; i++) {
    const delta = bars[i].close - bars[i - 1].close;
    gain += Math.max(delta, 0) / n;
    loss += Math.max(-delta, 0) / n;
  }
  for (let i = n + 1; i < bars.length; i++) {
    const delta = bars[i].close - bars[i - 1].close;
    gain = (gain * (n - 1) + Math.max(delta, 0)) / n;
    loss = (loss * (n - 1) + Math.max(-delta, 0)) / n;
  }
  return gain + loss > 0 ? (gain - loss) / (gain + loss) : 0;
}

/** Close minus the window mean, in sample standard deviations. */
export function zScore(bars, window) {
  if (bars.length < window) return null;
  const values = closes(bars.slice(-window));
  const mean = values.reduce((sum, value) => sum + value, 0) / window;
  const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (window - 1);
  const sd = Math.sqrt(variance), close = values.at(-1);
  return sd > close * 1e-12 ? (close - mean) / sd : 0;
}

/** MACD(12,26,9) histogram in basis points of price; EMAs seeded with the first close. */
export function macdHistogramBps(bars) {
  if (bars.length < 78) return null;
  const values = closes(bars);
  const fast = rawEma(values, 12), slow = rawEma(values, 26);
  const line = fast.map((value, i) => value - slow[i]);
  const signal = rawEma(line, 9);
  return (line.at(-1) - signal.at(-1)) / values.at(-1) * 1e4;
}

/** Parabolic SAR state: +1 while the stop is below price. Start/step 0.02, cap 0.2. */
export function psarDirection(bars, start = 0.02, step = 0.02, cap = 0.2) {
  if (bars.length < 2) return null;
  let up = bars[1].close >= bars[0].close;
  let sar = up ? bars[0].low : bars[0].high;
  let extreme = up ? Math.max(bars[0].high, bars[1].high) : Math.min(bars[0].low, bars[1].low);
  let af = start;
  for (let i = 2; i < bars.length; i++) {
    sar += af * (extreme - sar);
    if (up) {
      sar = Math.min(sar, bars[i - 1].low, bars[i - 2].low);
      if (bars[i].low < sar) { up = false; sar = extreme; extreme = bars[i].low; af = start; }
      else if (bars[i].high > extreme) { extreme = bars[i].high; af = Math.min(cap, af + step); }
    } else {
      sar = Math.max(sar, bars[i - 1].high, bars[i - 2].high);
      if (bars[i].high > sar) { up = true; sar = extreme; extreme = bars[i].high; af = start; }
      else if (bars[i].low < extreme) { extreme = bars[i].low; af = Math.min(cap, af + step); }
    }
  }
  return up ? 1 : -1;
}

/** Supertrend direction from an n-bar mean true range. */
export function supertrendDirection(bars, n = 10, multiplier = 3) {
  if (bars.length < n) return null;
  const tr = trueRanges(bars);
  let upper = NaN, lower = NaN, direction = 1;
  for (let i = n - 1; i < bars.length; i++) {
    // Sum the window itself so long runs cannot accumulate drift.
    let atr = 0;
    for (let j = i - n + 1; j <= i; j++) atr += tr[j];
    atr /= n;
    const mid = (bars[i].high + bars[i].low) / 2;
    const basicUpper = mid + multiplier * atr, basicLower = mid - multiplier * atr;
    if (Number.isNaN(upper)) { upper = basicUpper; lower = basicLower; continue; }
    const previousClose = bars[i - 1].close;
    upper = basicUpper < upper || previousClose > upper ? basicUpper : upper;
    lower = basicLower > lower || previousClose < lower ? basicLower : lower;
    if (direction < 0 && bars[i].close > upper) direction = 1;
    else if (direction > 0 && bars[i].close < lower) direction = -1;
  }
  return direction;
}

/** Sample standard deviation of 1s log returns over the window, in basis points. */
export function realizedVolBps(bars, window) {
  if (bars.length <= window) return null;
  const returns = [];
  for (let i = bars.length - window; i < bars.length; i++) returns.push(Math.log(bars[i].close / bars[i - 1].close) * 1e4);
  const mean = returns.reduce((sum, value) => sum + value, 0) / window;
  return Math.sqrt(returns.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (window - 1));
}

/** +1, -1 or 0; null stays null. */
export function vote(value) {
  if (value === null || !Number.isFinite(value)) return null;
  return value > VOTE_EPSILON ? 1 : value < -VOTE_EPSILON ? -1 : 0;
}
