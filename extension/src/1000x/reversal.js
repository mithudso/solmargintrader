/** Causal display context. No forecasts, position inference or execution. */
import { computeIndicators, validateCandles } from './indicators.js';

export const SHAPE_WINDOW = 48;
export const SHAPE_MINUTES = Object.freeze([5, 10, 15, 20]);
const color = bar => !bar ? null : bar.close > bar.open ? 'UP' : bar.close < bar.open ? 'DOWN' : 'FLAT';
const pairFor = bars => bars.length < 2 ? null : bars.slice(-2).map(bar => ({ UP: 'U', DOWN: 'D', FLAT: 'F' })[color(bar)]).join('');
const mean = values => values.reduce((sum, v) => sum + v / values.length, 0);

/** Epoch-aligned buckets require every completed minute. Oracle volume is not
 * executed volume; the TUI's require_volume=False aggregation is intentional.
 */
export function aggregateMinutes(rows, minutes, atSec) {
  if (!Number.isInteger(minutes) || minutes < 1 || !Number.isFinite(atSec)) throw new TypeError('invalid aggregation clock or interval');
  validateCandles(rows);
  const step = minutes * 60, buckets = new Map();
  for (const row of rows) {
    if (row.time % 60 !== 0) throw new RangeError('minute candle is not epoch aligned');
    if (row.closed !== true || row.partial === true || row.time + 60 > atSec) continue;
    const stamp = Math.floor(row.time / step) * step;
    if (!buckets.has(stamp)) buckets.set(stamp, []);
    buckets.get(stamp).push(row);
  }
  return [...buckets].flatMap(([time, chunk]) => chunk.length !== minutes || time + step > atSec
    || chunk.some((row, i) => row.time !== time + i * 60 || (i > 0 && row.gapBefore)) ? [] : [{
      time, open: chunk[0].open, high: Math.max(...chunk.map(row => row.high)),
      low: Math.min(...chunk.map(row => row.low)), close: chunk.at(-1).close, closed: true,
    }]);
}

/** Fixed symmetric-design least squares is the same trailing fit as
 * research.shape_study._fit. Center prices before sums to limit cancellation.
 */
function fit(values, degree) {
  const n = values.length, center = mean(values), y = values.map(value => value - center);
  const x = values.map((_, i) => -1 + 2 * i / (n - 1));
  const x2 = x.map(value => value * value);
  const sum = values => values.reduce((a, b) => a + b, 0);
  const sx2 = sum(x2);
  const b = sum(x.map((value, i) => value * y[i])) / sx2;
  const a = degree === 2 ? sum(x2.map((value, i) => (value - sx2 / n) * y[i])) / (sum(x2.map(value => value * value)) - sx2 * sx2 / n) : 0;
  const c = center - a * sx2 / n;
  const residual = sum(values.map((value, i) => (value - (a * x2[i] + b * x[i] + c)) ** 2));
  const total = sum(y.map(value => value * value));
  return { a, b, c, variance: total, r2: Math.max(0, Math.min(1, 1 - residual / Math.max(total, 1e-12))) };
}

/** Latest observable geometry from research.shape_study.detect_shapes. Reset at
 * gaps; the 48-return sample deviation includes the preceding close if present.
 */
export function describeShape(bars, minutes, atSec) {
  const step = minutes * 60;
  const closed = bars.filter(bar => bar.closed === true && bar.partial !== true && bar.time + step <= atSec);
  let from = 0;
  for (let i = 1; i < closed.length; i++) if (closed[i].time - closed[i - 1].time !== step || closed[i].gapBefore) from = i;
  const tail = closed.slice(from), last = tail.at(-1), closedAt = last ? last.time + step : null;
  const base = { minutes, shape: 'unknown', closedAt, count: tail.length, pair: pairFor(tail), zone: null,
    rangePosition: null, efficiency: null, fitR2: null };
  if (!last || atSec >= closedAt + step || tail.length < SHAPE_WINDOW) return base;
  const window = tail.slice(-SHAPE_WINDOW), p = window.map(bar => Math.log(bar.close));
  const q = fit(p, 2), hp = fit(window.map(bar => Math.log(bar.high)), 1), lp = fit(window.map(bar => Math.log(bar.low)), 1);
  const low = Math.min(...window.map(bar => bar.low)), high = Math.max(...window.map(bar => bar.high));
  const position = high === low ? 0.5 : Math.max(0, Math.min(1, (last.close - low) / (high - low)));
  const net = p.at(-1) - p[0];
  const changes = p.slice(1).map((value, i) => value - p[i]);
  const path = changes.reduce((sum, value) => sum + Math.abs(value), 0), efficiency = path ? Math.abs(net) / path : 0;
  const previous = tail.length > SHAPE_WINDOW ? Math.log(tail.at(-SHAPE_WINDOW - 1).close) : p[0];
  const returns = [p[0] - previous, ...changes], average = mean(returns);
  const rv = Math.sqrt(returns.reduce((sum, value) => sum + (value - average) ** 2, 0) / (SHAPE_WINDOW - 1));
  const bend = Math.abs(q.a) / Math.max(rv * Math.sqrt(SHAPE_WINDOW), 1e-12);
  const vertex = Math.abs(2 * q.a) > 1e-12 ? -q.b / (2 * q.a) : NaN;
  const startWidth = (hp.c - hp.b) - (lp.c - lp.b), endWidth = (hp.c + hp.b) - (lp.c + lp.b);
  const contraction = endWidth / Math.max(startWidth, 1e-12);
  const left = p[SHAPE_WINDOW - 1 - Math.floor(SHAPE_WINDOW / 2)] - p[0];
  const right = p.at(-1) - p[SHAPE_WINDOW - 1 - Math.floor(SHAPE_WINDOW / 2)];
  let shape = efficiency < 0.25 ? 'range' : net > 0 ? 'trend_up' : net < 0 ? 'trend_down' : 'unknown';
  if (left < -2 * rv && right > 2 * rv && position > 0.35) shape = 'v_rebound';
  if (left > 2 * rv && right < -2 * rv && position < 0.65) shape = 'inverted_v';
  if (q.a > 0 && q.r2 >= 0.8 && bend >= 0.15 && vertex > -0.8 && vertex < 0.8) shape = 'bowl';
  if (q.a < 0 && q.r2 >= 0.8 && bend >= 0.15 && vertex > -0.8 && vertex < 0.8) shape = 'cap';
  if (hp.b < 0 && lp.b > 0 && endWidth > 0 && contraction < 0.65 && contraction > 0.1) shape = 'compression';
  return { ...base, shape, zone: position < 1 / 3 ? 'lower' : position > 2 / 3 ? 'upper' : 'middle',
    // A constant path has no fit-quality statistic. The Python uncentered sum
    // loses precision there; do not expose its cancellation residue as quality.
    rangePosition: position, efficiency, fitR2: q.variance > 1e-12 ? q.r2 : null };
}

function developingBar(rows, time, nowSec) {
  const currentMinute = Math.floor(nowSec / 60) * 60;
  const chunk = rows.filter(row => row.time >= time && row.time <= currentMinute
    && (row.closed !== true || row.time + 60 <= nowSec));
  if (!chunk.length || chunk[0].time !== time || chunk.some((row, i) => row.time !== time + i * 60 || row.partial === true || (i && row.gapBefore))) return null;
  if (chunk.at(-1).time !== currentMinute) return null;
  return { time, open: chunk[0].open, close: chunk.at(-1).close,
    high: Math.max(...chunk.map(row => row.high)), low: Math.min(...chunk.map(row => row.low)), developing: true };
}

export function reversalContext(rows = [], nowMs, eligible = false) {
  const nowSec = nowMs / 1000;
  const at = Math.floor(nowSec / 600) * 600;
  const bars = aggregateMinutes(rows, 10, at);
  const byTime = new Map(bars.map(bar => [bar.time, bar]));
  const previous = [byTime.get(at - 1200) ?? null, byTime.get(at - 600) ?? null];
  const colors = previous.map(color);
  const pair = colors.every(value => value !== null) ? colors.map(value => ({ UP: 'U', DOWN: 'D', FLAT: 'F' })[value]).join('') : null;
  const direction = pair === 'DD' ? 'UP' : pair === 'UU' ? 'DOWN' : null;
  const older = color(byTime.get(at - 1800));
  const current = developingBar(rows, at, nowSec);
  const frames = Object.fromEntries(SHAPE_MINUTES.map(minutes => [String(minutes), describeShape(aggregateMinutes(rows, minutes, nowSec), minutes, nowSec)]));
  let start = 0;
  const closed = aggregateMinutes(rows, 1, nowSec);
  for (let i = 1; i < closed.length; i++) if (closed[i].time - closed[i - 1].time !== 60) start = i;
  const minute = closed.slice(start), indicators = computeIndicators(minute, { bop: { smoothing: 3 } });
  const momentumReady = minute.at(-1)?.time + 60 === Math.floor(nowSec / 60) * 60 && minute.length >= 78;
  const momentum = { ready: eligible && momentumReady, count: minute.length, closedAt: minute.at(-1)?.time + 60 || null,
    ema9: indicators.ema.latest, ema21: indicators.ema.slowLatest, macd: indicators.macd.latest,
    macdSignal: indicators.macd.signalLatest, macdHistogram: indicators.macd.histogramLatest,
    bopSma3: momentumReady ? indicators.bop.latest : null };
  const sign = direction === 'UP' ? 1 : -1;
  const alignment = direction && momentum.ready ? [momentum.ema9 - momentum.ema21, momentum.macdHistogram, momentum.bopSma3].filter(value => value * sign > 0).length : null;
  return {
    ready: eligible && previous.every(Boolean), pair, direction, previous, colors,
    newStreak: direction && older !== null ? older === (direction === 'UP' ? 'UP' : 'DOWN') : null,
    targetStart: at, targetEnd: at + 600, developing: current ? { ...current, color: color(current) } : null,
    frames, momentum, heuristic: alignment === null ? null : { agree: alignment, total: 3, kind: 'indicator alignment; not a probability' },
    empirical: { status: 'unavailable', probability: null, score: null, reason: 'No compatible model is bundled for this market, oracle source and pattern. UU evidence is not DD evidence.' },
    exit: { status: 'unavailable', roe: null, intent: null, reason: 'No typed position input. The +50% ROE / minimum 15s / 10s delay research policy is inactive.' },
  };
}
