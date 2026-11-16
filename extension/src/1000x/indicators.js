/**
 * Pure, causal chart indicators. Inputs are one ordered, continuous candle segment.
 * The feed owns gap detection and closed/developing status; callers compute those
 * segments separately. No indicator here reads a clock, network, storage or venue.
 */

// The feed derives its seed/retention floor from this accepted period limit.
export const MAX_INDICATOR_LENGTH = 500;

export const DEFAULT_INDICATORS = Object.freeze({
  zigzag: Object.freeze({ enabled: true, reversalPercent: 0.5 }),
  rsi: Object.freeze({ enabled: true, length: 14, oversold: 30, overbought: 70 }),
  bop: Object.freeze({ enabled: true, smoothing: 1 }),
  volty: Object.freeze({ enabled: true, length: 5, multiplier: 0.75 }),
  psar: Object.freeze({ enabled: true, start: 0.02, step: 0.02, max: 0.2 }),
  ema: Object.freeze({ enabled: true }),
  macd: Object.freeze({ enabled: true }),
});

function record(value, label) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)
      || ![Object.prototype, null].includes(Object.getPrototypeOf(value))) {
    throw new TypeError(`${label} must be an object`);
  }
}

function number(value, label, minimum, maximum, integer = false) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new TypeError(`${label} must be finite numeric data`);
  }
  if ((integer && !Number.isInteger(value)) || value < minimum || value > maximum) {
    throw new RangeError(`${label} must be ${integer ? 'an integer ' : ''}in [${minimum}, ${maximum}]`);
  }
}

/** Return a fresh normalized config; unknown fields and malformed values fail closed. */
export function validateIndicatorConfig(input = {}) {
  record(input, 'indicator config');
  for (const name of Object.keys(input)) {
    if (!Object.hasOwn(DEFAULT_INDICATORS, name)) throw new TypeError(`Unknown indicator ${name}`);
  }
  const config = {};
  for (const [name, defaults] of Object.entries(DEFAULT_INDICATORS)) {
    const supplied = Object.hasOwn(input, name) ? input[name] : {};
    record(supplied, name);
    for (const key of Object.keys(supplied)) {
      if (!Object.hasOwn(defaults, key)) throw new TypeError(`Unknown ${name} option ${key}`);
    }
    config[name] = { ...defaults, ...supplied };
    if (typeof config[name].enabled !== 'boolean') throw new TypeError(`${name}.enabled must be boolean`);
  }
  number(config.zigzag.reversalPercent, 'zigzag.reversalPercent', 0.01, 50);
  number(config.rsi.length, 'rsi.length', 2, MAX_INDICATOR_LENGTH, true);
  number(config.rsi.oversold, 'rsi.oversold', 0, 100);
  number(config.rsi.overbought, 'rsi.overbought', 0, 100);
  if (config.rsi.oversold >= config.rsi.overbought) {
    throw new RangeError('rsi.oversold must be below rsi.overbought');
  }
  number(config.bop.smoothing, 'bop.smoothing', 1, MAX_INDICATOR_LENGTH, true);
  number(config.volty.length, 'volty.length', 1, MAX_INDICATOR_LENGTH, true);
  number(config.volty.multiplier, 'volty.multiplier', 0.01, 100);
  for (const field of ['start', 'step', 'max']) number(config.psar[field], `psar.${field}`, 0.0001, 1);
  if (config.psar.start > config.psar.max || config.psar.step > config.psar.max) {
    throw new RangeError('psar.start and psar.step must not exceed psar.max');
  }
  return config;
}

export function validateCandles(candles) {
  if (!Array.isArray(candles)) throw new TypeError('candles must be an array');
  let previous = -1;
  for (const candle of candles) {
    record(candle, 'candle');
    // The calendar limit also rejects contemporary millisecond epochs passed as seconds.
    number(candle.time, 'candle.time (UTC seconds)', 0, 253402300799, true);
    if (candle.time <= previous) throw new RangeError('candle times must be unique and increasing');
    previous = candle.time;
    for (const key of ['open', 'high', 'low', 'close']) {
      number(candle[key], `candle.${key}`, Number.MIN_VALUE, Number.MAX_VALUE);
    }
    if (candle.high < Math.max(candle.open, candle.close)
        || candle.low > Math.min(candle.open, candle.close) || candle.high < candle.low) {
      throw new RangeError('invalid candle OHLC envelope');
    }
    if (Object.hasOwn(candle, 'volume')) number(candle.volume, 'candle.volume', 0, Number.MAX_VALUE);
  }
}

/** Same adjust=False, first-close seed as oracle_leverage.exit50.minute_features.
 * The research context waits for 78 observations before exposing a reading.
 */
export function momentum(candles) {
  const ema = length => {
    const alpha = 2 / (length + 1);
    let previous = null;
    return candles.map(({ close }) => (previous = previous === null ? close : finite(alpha * close + (1 - alpha) * previous)));
  };
  const fast = ema(9), slow = ema(21), e12 = ema(12), e26 = ema(26);
  const line = e12.map((value, i) => finite(value - e26[i]));
  let seed = null;
  const signal = line.map(value => (seed = seed === null ? value : finite(0.2 * value + 0.8 * seed)));
  const histogram = line.map((value, i) => finite(value - signal[i]));
  const warm = values => values.map((value, i) => i < 77 ? null : value);
  return { fast: warm(fast), slow: warm(slow), line: warm(line), signal: warm(signal), histogram: warm(histogram) };
}

function finite(value) {
  if (!Number.isFinite(value)) throw new RangeError('indicator arithmetic is not finite');
  return value;
}

const aligned = (candles, values) => candles.map(({ time }, i) => ({ time, value: values[i] ?? null }));
const blank = candles => candles.map(() => null);
const last = values => values.length ? values.at(-1) : null;

function sma(values, length) {
  const result = values.map(() => null);
  let mean = 0;
  let count = 0;
  for (let i = 0; i < values.length; i++) {
    if (values[i] === null) {
      mean = 0;
      count = 0;
      continue;
    }
    // Accumulate scaled terms so a representable average need not overflow its sum.
    if (count >= length) mean -= values[i - length] / length;
    mean += values[i] / length;
    count++;
    if (count >= length) result[i] = finite(mean);
  }
  return result;
}

function zigzag(candles, options) {
  const confirmed = [];
  let provisional = null;
  if (options.enabled && candles.length) {
    const percent = options.reversalPercent / 100;
    let direction = null;
    let high = { time: candles[0].time, value: candles[0].close };
    let low = { ...high };
    let extreme = { ...high };
    for (const { time, close: value } of candles) {
      if (direction === null) {
        if (value > high.value) high = { time, value };
        if (value < low.value) low = { time, value };
        if (value >= low.value * (1 + percent)) {
          confirmed.push({ ...low, kind: 'low', confirmedAt: time });
          direction = 'up';
          extreme = { time, value };
        } else if (value <= high.value * (1 - percent)) {
          confirmed.push({ ...high, kind: 'high', confirmedAt: time });
          direction = 'down';
          extreme = { time, value };
        } else {
          extreme = { time, value };
        }
      } else if (direction === 'up') {
        if (value > extreme.value) extreme = { time, value };
        else if (value <= extreme.value * (1 - percent)) {
          confirmed.push({ ...extreme, kind: 'high', confirmedAt: time });
          direction = 'down';
          extreme = { time, value };
        }
      } else {
        if (value < extreme.value) extreme = { time, value };
        else if (value >= extreme.value * (1 + percent)) {
          confirmed.push({ ...extreme, kind: 'low', confirmedAt: time });
          direction = 'up';
          extreme = { time, value };
        }
      }
    }
    provisional = { ...extreme, kind: direction === null ? 'undetermined' : direction === 'up' ? 'high' : 'low' };
  }
  return {
    confirmed, provisional, latest: last(confirmed),
    signal: !options.enabled ? 'Disabled.' : confirmed.length
      ? 'Pivots are known only at their confirmation time; the provisional endpoint can move.'
      : 'No percentage reversal confirmed; the provisional endpoint can move.',
  };
}

function rsi(candles, options) {
  const values = blank(candles);
  if (options.enabled && candles.length > options.length) {
    let gain = 0;
    let loss = 0;
    const value = () => {
      if (gain === 0 && loss === 0) return 50;
      // Both ratios stay at most one, including extreme but valid price scales.
      return gain >= loss ? 100 / (1 + loss / gain) : 100 * (gain / loss) / (1 + gain / loss);
    };
    for (let i = 1; i <= options.length; i++) {
      const change = candles[i].close - candles[i - 1].close;
      gain += Math.max(change, 0) / options.length;
      loss += Math.max(-change, 0) / options.length;
    }
    values[options.length] = finite(value());
    for (let i = options.length + 1; i < candles.length; i++) {
      const change = candles[i].close - candles[i - 1].close;
      gain += (Math.max(change, 0) - gain) / options.length;
      loss += (Math.max(-change, 0) - loss) / options.length;
      values[i] = finite(value());
    }
  }
  const latest = last(values);
  return {
    series: aligned(candles, values), latest,
    signal: !options.enabled ? 'Disabled.' : latest === null
      ? `Warming up: ${options.length + 1} candles required for the SMA seed.`
      : latest >= options.overbought ? `RSI is at or above ${options.overbought}; a momentum description.`
        : latest <= options.oversold ? `RSI is at or below ${options.oversold}; a momentum description.`
          : `RSI is between ${options.oversold} and ${options.overbought}.`,
  };
}

function bop(candles, options) {
  const values = options.enabled ? sma(candles.map(candle => candle.high === candle.low ? 0
    : (candle.close - candle.open) / (candle.high - candle.low)), options.smoothing) : blank(candles);
  const latest = last(values);
  return {
    series: aligned(candles, values), latest,
    signal: !options.enabled ? 'Disabled.' : latest === null ? 'Warming up the candle-pressure average.'
      : latest > 0 ? 'Positive average (close - open) / (high - low).'
        : latest < 0 ? 'Negative average (close - open) / (high - low).'
          : 'Zero average candle pressure; zero-range candles contribute zero.',
  };
}

function volty(candles, options) {
  const upper = blank(candles);
  const lower = blank(candles);
  let next = null;
  if (options.enabled) {
    const ranges = candles.map((candle, i) => i === 0 ? null : Math.max(candle.high - candle.low,
      Math.abs(candle.high - candles[i - 1].close), Math.abs(candle.low - candles[i - 1].close)));
    const averages = sma(ranges, options.length);
    for (let i = 0; i < candles.length; i++) {
      // Exact stop_levels timing: a level formed at this close is active next bar.
      if (i && averages[i - 1] !== null) {
        const width = finite(averages[i - 1] * options.multiplier);
        upper[i] = finite(candles[i - 1].close + width);
        lower[i] = finite(candles[i - 1].close - width);
      }
    }
    if (candles.length && last(averages) !== null) {
      const width = finite(last(averages) * options.multiplier);
      next = { upper: finite(candles.at(-1).close + width), lower: finite(candles.at(-1).close - width),
        basedOn: candles.at(-1).time };
    }
  }
  const latest = last(upper) === null ? null : { upper: last(upper), lower: last(lower) };
  const close = candles.length ? candles.at(-1).close : null;
  return {
    upper: aligned(candles, upper), lower: aligned(candles, lower), latest, next,
    signal: !options.enabled ? 'Disabled.' : latest === null
      ? `Active levels warming up: ${options.length + 2} candles required.`
      : close >= latest.upper ? 'Close is at or above the envelope formed before this candle.'
        : close <= latest.lower ? 'Close is at or below the envelope formed before this candle.'
          : 'Close is inside the envelope formed before this candle.',
  };
}

function psar(candles, options) {
  const values = blank(candles);
  const trends = blank(candles);
  if (options.enabled && candles.length >= 2) {
    // Seeding needs two candles. Ties seed up; bar zero remains unavailable.
    let direction = candles[1].close >= candles[0].close ? 'up' : 'down';
    let sar = direction === 'up' ? Math.min(candles[0].low, candles[1].low)
      : Math.max(candles[0].high, candles[1].high);
    let extreme = direction === 'up' ? Math.max(candles[0].high, candles[1].high)
      : Math.min(candles[0].low, candles[1].low);
    let acceleration = options.start;
    values[1] = sar;
    trends[1] = direction;
    for (let i = 2; i < candles.length; i++) {
      let candidate = finite(sar + acceleration * (extreme - sar));
      if (direction === 'up') {
        candidate = Math.min(candidate, candles[i - 1].low, candles[i - 2].low);
        if (candles[i].low < candidate) {
          direction = 'down';
          sar = extreme;
          extreme = candles[i].low;
          acceleration = options.start;
        } else {
          sar = candidate;
          if (candles[i].high > extreme) {
            extreme = candles[i].high;
            acceleration = Math.min(options.max, acceleration + options.step);
          }
        }
      } else {
        candidate = Math.max(candidate, candles[i - 1].high, candles[i - 2].high);
        if (candles[i].high > candidate) {
          direction = 'up';
          sar = extreme;
          extreme = candles[i].high;
          acceleration = options.start;
        } else {
          sar = candidate;
          if (candles[i].low < extreme) {
            extreme = candles[i].low;
            acceleration = Math.min(options.max, acceleration + options.step);
          }
        }
      }
      values[i] = finite(sar);
      trends[i] = direction;
    }
  }
  const latest = last(values);
  const trend = last(trends);
  return {
    series: aligned(candles, values),
    points: candles.flatMap(({ time }, i) => values[i] === null ? [] : [{ time, value: values[i], trend: trends[i] }]),
    latest, trend,
    signal: !options.enabled ? 'Disabled.' : latest === null ? 'Warming up: two candles required to seed SAR.'
      : `SAR is in its ${trend === 'up' ? 'upward' : 'downward'} recurrence state; a trend description.`,
  };
}

/**
 * Every numeric series is candle-aligned {time,value}; unavailable values are null.
 * ZigZag is sparse: pivot.time is historical, pivot.confirmedAt is availability.
 * Its provisional endpoint may move. Volty.next contains levels for the next bar,
 * based on the last input candle; no future timestamp or candle is fabricated.
 * On developing inputs, every indicator's latest value may change with that bar.
 */
export function computeIndicators(candles, input = {}) {
  const config = validateIndicatorConfig(input);
  validateCandles(candles);
  const m = momentum(candles);
  const emaFast = config.ema.enabled ? m.fast : blank(candles);
  const emaSlow = config.ema.enabled ? m.slow : blank(candles);
  const macdLine = config.macd.enabled ? m.line : blank(candles);
  const macdSignal = config.macd.enabled ? m.signal : blank(candles);
  const macdHistogram = config.macd.enabled ? m.histogram : blank(candles);
  const emaReady = last(emaFast) !== null && last(emaSlow) !== null;
  const macdReady = last(macdLine) !== null && last(macdSignal) !== null;
  return {
    config,
    zigzag: zigzag(candles, config.zigzag),
    rsi: rsi(candles, config.rsi),
    bop: bop(candles, config.bop),
    volty: volty(candles, config.volty),
    psar: psar(candles, config.psar),
    ema: { fast: aligned(candles, emaFast), slow: aligned(candles, emaSlow), latest: last(emaFast), slowLatest: last(emaSlow),
      signal: !config.ema.enabled ? 'Disabled.' : !emaReady ? 'Warming up: 78 contiguous candles required.' : `EMA9 ${last(emaFast) > last(emaSlow) ? 'above' : last(emaFast) < last(emaSlow) ? 'below' : 'equals'} EMA21; trend context.` },
    macd: { series: aligned(candles, macdLine), signalSeries: aligned(candles, macdSignal), histogram: aligned(candles, macdHistogram),
      latest: last(macdLine), signalLatest: last(macdSignal), histogramLatest: last(macdHistogram),
      signal: !config.macd.enabled ? 'Disabled.' : !macdReady ? 'Warming up: 78 contiguous candles required.' : `MACD ${last(macdHistogram) > 0 ? 'above' : last(macdHistogram) < 0 ? 'below' : 'equals'} its signal; momentum context.` },
  };
}
