import { ARCHIVE_PRESETS } from './archive-presets.js';

/** Prior-study candidates. Presets retain the published cadence and signal parameters. */
export const PRESETS = Object.freeze([
  { id: 'zec-mean', name: 'ZEC · RSI + Z-score + Bollinger', assets: ['ZEC'], step: 300, kind: 'mean',
    source: 'Native Coinbase study, 697f3b1dd4526147f43ca3d4; +2.49% spot test at 10+2 bps',
    details: 'RSI 14/30/50 · z-score 20/−2/0 · Bollinger 20/2' },
  { id: 'zec-zscore', name: 'ZEC · Z-score reversion', assets: ['ZEC'], step: 300, kind: 'zscore',
    source: 'Native Coinbase study, 4aee6542900bfaad23c1c74f; +3.92% spot test, four sells',
    details: '20 closes · enter at −2 · exit at 0' },
  { id: 'zec-bands', name: 'ZEC · Bollinger reversion', assets: ['ZEC'], step: 300, kind: 'bands',
    source: 'Native Coinbase study, b7d879144b7c11147d802536; +3.42% spot test, four sells',
    details: '20 closes · 2 population standard deviations' },
  { id: 'sol-volty', name: 'SOL · Volty stop breakout', assets: ['SOL'], step: 3600, kind: 'volty',
    length: 4, factor: 0.75, source: 'Native Coinbase study, validation-leading worst-path Volty; +2.69% worst-path test',
    details: '4-bar SMA of true range · 0.75× · opposite stop reverses' },
  { id: 'eth-volty', name: 'ETH · Volty stop breakout', assets: ['ETH'], step: 3600, kind: 'volty',
    length: 5, factor: 0.75, source: 'Native Coinbase study, validation-leading worst-path Volty; +0.43% worst-path test',
    details: '5-bar SMA of true range · 0.75× · opposite stop reverses' },
  ...ARCHIVE_PRESETS,
]);

export const marketPresets = asset => PRESETS.filter(preset => preset.assets.includes(asset) || preset.kind !== 'archive');

export const INTERVALS = Object.freeze({ 60: '1m', 300: '5m', 600: '10m', 3600: '1h' });
export const RISK_PRESETS = Object.freeze({
  original: { tp: 0, sl: 0 },
  tight: { tp: 0.5, sl: 0.3 },
  wide: { tp: 1.5, sl: 0.8 },
});

/** Only complete, epoch-aligned windows can drive the strategy. */
export function aggregateMinutes(rows, step) {
  const result = [];
  const needed = step / 60;
  if (!Number.isSafeInteger(needed) || needed < 1) throw new Error('Invalid candle cadence.');
  let current = null;
  let count = 0;
  for (const row of rows) {
    if (row.closed === false) continue;
    const start = Math.floor(row.time / step) * step;
    if (start !== current?.time) {
      current = row.time === start ? { ...row, time: start } : null;
      count = current ? 1 : 0;
    } else if (row.time === start + count * 60) {
      current.high = Math.max(current.high, row.high);
      current.low = Math.min(current.low, row.low);
      current.close = row.close;
      count += 1;
    } else {
      current = null;
      count = 0;
    }
    if (count === needed && current) result.push(current);
  }
  return result;
}

const RSI = { strategy: 'rsi', params: { period: 14, oversold: 30, exit_level: 50 } };
const ZSCORE = { strategy: 'zscore', params: { window: 20, entry_z: -2, exit_z: 0 } };
const BANDS = { strategy: 'bb_reversion', params: { window: 20, num_std: 2 } };

function memberState(spec) {
  const params = spec.params;
  const rsi = spec.strategy === 'rsi';
  const warmup = rsi ? params.period + 1 : params.window;
  let age = 0;
  let previous = null;
  let gain = 0;
  let loss = 0;
  let held = false;
  const closes = [];
  return {
    reset() {
      age = 0;
      previous = null;
      gain = loss = 0;
      held = false;
      closes.length = 0;
    },
    update(close) {
      age += 1;
      if (rsi) {
        if (previous !== null) {
          const delta = close - previous;
          const rise = Math.max(delta, 0);
          const fall = Math.max(-delta, 0);
          const period = params.period;
          gain = (gain * (age <= period + 1 ? period : period - 1) + rise) / period;
          loss = (loss * (age <= period + 1 ? period : period - 1) + fall) / period;
        }
        previous = close;
        if (age <= warmup) return null;
        const value = loss <= 1e-15 ? (gain > 0 ? 100 : 50) : 100 - 100 / (1 + gain / loss);
        if (!held && value < params.oversold) held = true;
        else if (held && value > params.exit_level) held = false;
      } else {
        closes.push(close);
        if (closes.length > params.window) closes.shift();
        if (age <= warmup) return null;
        const mean = closes.reduce((sum, n) => sum + n, 0) / params.window;
        const squares = closes.reduce((sum, n) => sum + (n - mean) ** 2, 0);
        if (spec.strategy === 'zscore') {
          const z = squares > 0 ? (close - mean) / Math.sqrt(squares / (params.window - 1)) : 0;
          if (!held && z <= params.entry_z) held = true;
          else if (held && z >= params.exit_z) held = false;
        } else {
          if (!held && close < mean - params.num_std * Math.sqrt(squares / params.window)) held = true;
          else if (held && close > mean) held = false;
        }
      }
      return Number(held);
    },
  };
}

export function practiceSignals(bars, preset) {
  const rules = preset.members ?? { mean: [RSI, ZSCORE, BANDS], zscore: [ZSCORE], bands: [BANDS] }[preset.kind] ?? [];
  const members = rules.map(memberState);
  let previous = null;
  const ranges = [];
  return bars.map(bar => {
    if (previous && bar.time !== previous.time + preset.step) {
      previous = null;
      ranges.length = 0;
      for (const member of members) member.reset();
    }
    if (preset.kind === 'volty') {
      if (previous) {
        ranges.push(Math.max(bar.high - bar.low, Math.abs(bar.high - previous.close), Math.abs(bar.low - previous.close)));
        if (ranges.length > preset.length) ranges.shift();
      }
      previous = bar;
      if (ranges.length < preset.length) return null;
      const offset = preset.factor * ranges.reduce((sum, n) => sum + n, 0) / preset.length;
      return offset > 0 ? { upper: bar.close + offset, lower: bar.close - offset } : null;
    }
    previous = bar;
    const votes = members.map(member => member.update(bar.close));
    return !votes.length || votes.includes(null) ? null
      : { weight: votes.reduce((sum, vote) => sum + (vote ?? 0), 0) / votes.length };
  });
}

/** Decisions become available only after the complete signal bar closes. */
export function signalMap(minutes, preset) {
  const bars = aggregateMinutes(minutes, preset.step);
  const signals = practiceSignals(bars, preset);
  return new Map(bars.map((bar, i) => [bar.time + preset.step, signals[i]]));
}

export function breakout(bar, signal, direction = 0) {
  const long = direction !== 1 && bar.high >= signal.upper;
  const short = direction !== -1 && bar.low <= signal.lower;
  if (long === short) return null;
  return long
    ? { direction: 1, price: Math.max(bar.open, signal.upper) }
    : { direction: -1, price: Math.min(bar.open, signal.lower) };
}
