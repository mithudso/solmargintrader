import { computeIndicators, momentum } from '../../src/1000x/indicators.js';
import { describeShape, SHAPE_WINDOW } from '../../src/1000x/reversal.js';
import { aggregateMinutes, marketPresets, practiceSignals } from '../../src/perps/strategies.js';

const RSI = { strategy: 'rsi', params: { period: 14, oversold: 30, exit_level: 50 } };
const ZSCORE = { strategy: 'zscore', params: { window: 20, entry_z: -2, exit_z: 0 } };
const BANDS = { strategy: 'bb_reversion', params: { window: 20, num_std: 2 } };
const ALIAS_MEMBERS = { mean: [RSI, ZSCORE, BANDS], zscore: [ZSCORE], bands: [BANDS] };
const FAMILY = { rsi: 'rsi', zscore: 'zscore', bb_reversion: 'bollinger' };

const REVERSAL_SHAPES = ['range', 'v_rebound', 'bowl'];
const TREND_SHAPES = ['trend_up', 'bowl'];
const VOLTY_LONG_SHAPES = ['compression', 'trend_up'];
const VOLTY_SHORT_SHAPES = ['compression', 'trend_down'];
const SHAPE_ENTRY = ['v_rebound', 'bowl'];
const SHAPE_EXIT = ['trend_down', 'cap', 'inverted_v'];
const BOP_WINDOWS = [3, 5, 10];

export const CADENCE_POLICY = Object.freeze({
  trainBars: 64, refitBars: 16, minimumCoverage: 0.95, minimumCycles: 4, minimumBarsPerCycle: 6,
});

function memberName({ strategy, params }) {
  switch (strategy) {
    case 'rsi':
      return `RSI(${params.period}) <${params.oversold} → >${params.exit_level}`;
    case 'zscore':
      return `Z-score(${params.window}, sample σ) ≤${params.entry_z} → ≥${params.exit_z}`;
    case 'bb_reversion':
      return `Bollinger(${params.window}, ${params.num_std} population σ) below lower → above mean`;
    default:
      throw new Error(`Unsupported focused ZEC archive rule: ${strategy}.`);
  }
}

function labelMembers(preset, members, origin) {
  const first = members[0];
  const family = members.length === 1 ? FAMILY[first.strategy] : 'ensemble';
  const details = members.map(memberName).join(' + ');
  return {
    ...preset, members, origin, family, params: members.length === 1 ? first.params : { members, weights: 'equal' },
    name: members.length === 1 ? details : `Equal weight: ${details}`,
    details: members.length === 1 && first.strategy === 'rsi' && first.params.exit_level === 100
      ? details + ' (signal exit unreachable)' : details,
  };
}

/** Frozen prior IDs stay available even if another candidate uses identical parameters. */
export function candidates(step) {
  if (step !== 300 && step !== 600) throw new Error('The focused ZEC suite supports 5m and 10m.');
  const suffix = `-${step / 60}m`;
  const prior = marketPresets('ZEC').filter(preset => preset.assets.includes('ZEC') && preset.step === step)
    .map(preset => labelMembers(preset, preset.members ?? ALIAS_MEMBERS[preset.kind],
      preset.kind === 'archive' ? 'archived' : 'named-prior'));
  const reversionRules = [
    RSI,
    { strategy: 'rsi', params: { period: 7, oversold: 30, exit_level: 55 } },
    { strategy: 'rsi', params: { period: 21, oversold: 35, exit_level: 55 } },
    ZSCORE, BANDS,
    { strategy: 'zscore', params: { window: 200 * 60 / step, entry_z: -2, exit_z: 0 } },
    { strategy: 'bb_reversion', params: { window: 200 * 60 / step, num_std: 2 } },
  ];
  const oldKeys = new Set(prior.map(candidate => candidate.details));
  const standalone = reversionRules.map((spec, i) => labelMembers(
    { id: 'focused-' + spec.strategy + '-' + (i + 1) + suffix, kind: 'archive', step },
    [spec], 'focused'));
  const newReversionRules = standalone.filter(candidate => {
    if (oldKeys.has(candidate.details)) return false;
    oldKeys.add(candidate.details);
    return true;
  });

  const extra = [
    ...BOP_WINDOWS.map(smoothing => ({
      id: `bop-${smoothing}`, kind: 'bop', name: `Balance of Power (SMA${smoothing}) >0 → ≤0`,
      params: { smoothing },
      details: 'SMA of (close − open) / (high − low); zero-range bars contribute 0.',
    })),
    ...['histogram', 'line'].map(series => ({
      id: `macd-${series}`, kind: 'macd', name: `MACD (12/26/9) ${series} >0 → ≤0`,
      params: { fast: 12, slow: 26, signal: 9, series, warmup: 78 },
      details: 'First-close EMA seed and a 78-contiguous-bar warmup.',
    })),
    ...[[4, 0.75], [5, 0.75], [5, 1.25], [10, 1.5]].map(([length, factor]) => ({
      id: `volty-${length}-${factor}`, kind: 'volty', name: `Volty (SMA TR ${length} × ${factor})`,
      length, factor, params: { length, factor },
      details: 'Next-band stops around prior close; opposite stop reverses if allowed.',
    })),
    {
      id: 'graph-shape-reversal', kind: 'shape', name: 'Graph shape (48 bars), V rebound or bowl',
      params: { window: SHAPE_WINDOW, entry: SHAPE_ENTRY, exit: SHAPE_EXIT, entryZone: 'exclude upper', exitZone: 'upper' },
      details: 'Enter on a V rebound or bowl outside the upper zone; exit at the upper zone or a downtrend, cap or inverted V.',
    },
    {
      id: 'spectral-cadence', kind: 'cadence', name: 'Spectral cadence (64-bar fit, 16-bar refit)',
      params: CADENCE_POLICY,
      details: 'Long on a positive next harmonic increment. Go flat on a nonpositive or unavailable increment.',
    },
  ].map(candidate => ({
    ...candidate, origin: 'focused', family: candidate.kind, step, id: candidate.id + suffix,
  }));
  return [...prior, ...newReversionRules, ...extra];
}

const dot = (xs, ys) => xs.reduce((sum, x, i) => sum + x * ys[i], 0);
const average = xs => xs.reduce((sum, x) => sum + x, 0) / xs.length;

/** Residualize both the log price and each harmonic against intercept and slope. */
function fitCadence(bars, step) {
  const first = bars[0].time;
  const span = bars.at(-1).time - first + step;
  const { trainBars, minimumCoverage, minimumCycles, minimumBarsPerCycle } = CADENCE_POLICY;
  if (trainBars * step / span < minimumCoverage) return null;
  const time = bars.map(bar => bar.time - first);
  const center = average(time);
  const x = time.map(t => (t - center) / span);
  const xx = dot(x, x);
  const residualize = values => {
    const mean = average(values);
    const slope = dot(x, values) / xx;
    return values.map((value, i) => value - mean - slope * x[i]);
  };
  const y = residualize(bars.map(bar => Math.log(bar.close)));
  if (dot(y, y) <= 1e-24) return null;

  const maximum = Math.floor(span / (minimumBarsPerCycle * step));
  // Match Spectrum's rounded geometric search across counts, including the endpoints.
  const counts = Array.from({ length: maximum - minimumCycles + 1 }, (_, i) =>
    Math.round(minimumCycles * (maximum / minimumCycles) ** (i / (maximum - minimumCycles))));
  let best = null;
  for (const count of new Set(counts)) {
    const omega = 2 * Math.PI * count / span;
    const c = residualize(time.map(t => Math.cos(omega * t)));
    const s = residualize(time.map(t => Math.sin(omega * t)));
    const cc = dot(c, c), ss = dot(s, s), cs = dot(c, s);
    const cy = dot(c, y), sy = dot(s, y);
    const determinant = cc * ss - cs * cs;
    if (determinant < 1e-10) continue;
    const cosine = (ss * cy - cs * sy) / determinant;
    const sine = (cc * sy - cs * cy) / determinant;
    const score = cosine * cy + sine * sy;
    if (!best || score > best.score) {
      best = { first, trainedAt: bars.at(-1).time, omega, cosine, sine, score };
    }
  }
  return best;
}

function cadenceSeries(bars, step) {
  const { trainBars, refitBars } = CADENCE_POLICY;
  const start = bars[0]?.time;
  let fit = null;
  return bars.map((bar, i) => {
    const offset = (bar.time - start) / step;
    if (i >= trainBars - 1 && (offset - trainBars + 1) % refitBars === 0) {
      fit = fitCadence(bars.slice(i - trainBars + 1, i + 1), step);
    }
    if (!fit || bar.time - fit.trainedAt >= refitBars * step) return null;
    const now = (bar.time - fit.first) * fit.omega;
    const next = now + step * fit.omega;
    const increment = (Math.cos(next) - Math.cos(now)) * fit.cosine
      + (Math.sin(next) - Math.sin(now)) * fit.sine;
    return Math.abs(increment) > 1e-14 ? Math.sign(increment) : 0;
  });
}

function indicatorsBySegment(bars, step) {
  const histogram = [], line = [];
  const bop = Object.fromEntries(BOP_WINDOWS.map(smoothing => [smoothing, []]));
  const readSegment = segment => {
    const macd = momentum(segment);
    histogram.push(...macd.histogram);
    line.push(...macd.line);
    for (const smoothing of BOP_WINDOWS) {
      const indicators = computeIndicators(segment, {
        bop: { smoothing }, zigzag: { enabled: false }, rsi: { enabled: false }, volty: { enabled: false },
        psar: { enabled: false }, ema: { enabled: false }, macd: { enabled: false },
      });
      bop[smoothing].push(...indicators.bop.series.map(row => row.value));
    }
  };
  let from = 0;
  bars.forEach((bar, i) => {
    if (i && bar.time !== bars[i - 1].time + step) {
      readSegment(bars.slice(from, i));
      from = i;
    }
  });
  readSegment(bars.slice(from));
  return { histogram, line, bop };
}

/** Public historical GUM rows omit the closed flag; explicit partial rows never enter a feature. */
export function buildContext(minutes, step) {
  const bars = aggregateMinutes(minutes.filter(row => row.partial !== true), step)
    .map(bar => ({ ...bar, closed: true }));
  const shape = bars.map((bar, i) =>
    describeShape(bars.slice(Math.max(0, i - SHAPE_WINDOW), i + 1), step / 60, bar.time + step));
  return { bars, step, shape, cadence: cadenceSeries(bars, step), ...indicatorsBySegment(bars, step) };
}

function shapeSignal(context) {
  let held = false;
  return context.shape.map(({ shape, zone }) => {
    if (shape === 'unknown') {
      held = false;
      return null;
    }
    if (zone === 'upper' || SHAPE_EXIT.includes(shape)) held = false;
    else if (SHAPE_ENTRY.includes(shape)) held = true;
    return { weight: Number(held) };
  });
}

function baseSignals(context, candidate) {
  let series;
  switch (candidate.kind) {
    case 'shape': return shapeSignal(context);
    case 'cadence': series = context.cadence; break;
    case 'bop': series = context.bop[candidate.params.smoothing]; break;
    case 'macd': series = context[candidate.params.series]; break;
    default: return practiceSignals(context.bars, candidate);
  }
  return series.map(value => value === null ? null : { weight: Number(value > 0) });
}

/** Gate original entry transitions. A disappearing gate never flattens a held long.
 * Volty's opposite-stop action is atomic in PaperBroker, so its gate can defer reversal.
 */
export function buildDecisions(context, candidate, shapeEnabled = false, cadenceEnabled = false) {
  if (candidate.step !== context.step) throw new Error('Candidate and context cadence mismatch.');
  const { bars, step, shape, cadence } = context;
  const signals = baseSignals(context, candidate);
  const longShapes = candidate.kind === 'volty' ? VOLTY_LONG_SHAPES
    : candidate.kind === 'bop' || candidate.kind === 'macd' ? TREND_SHAPES : REVERSAL_SHAPES;
  let previous = 0;
  let accepted = 0;
  return new Map(bars.map((bar, i) => {
    const signal = signals[i];
    const time = bar.time + step;
    if (!signal || !(shapeEnabled || cadenceEnabled)) {
      if (!signal) previous = accepted = 0;
      return [time, signal];
    }
    const long = (!shapeEnabled || longShapes.includes(shape[i].shape))
      && (!cadenceEnabled || cadence[i] === 1);
    if (candidate.kind === 'volty') {
      const short = (!shapeEnabled || VOLTY_SHORT_SHAPES.includes(shape[i].shape))
        && (!cadenceEnabled || cadence[i] === -1);
      return [time, { upper: long ? signal.upper : Infinity, lower: short ? signal.lower : -Infinity }];
    }
    const { weight } = signal;
    // A rejected increase is skipped even if the gate opens later at the same raw weight.
    if (weight > previous) {
      if (long) accepted = weight;
    } else {
      accepted = Math.min(accepted, weight);
    }
    previous = weight;
    return [time, { weight: accepted }];
  }));
}
