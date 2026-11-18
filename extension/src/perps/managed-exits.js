import { computeIndicators } from '../1000x/indicators.js';
import { aggregateMinutes, INTERVALS } from './strategies.js';

const closesAcross = (before, after, level, cross) =>
  (cross !== 'down' && before <= level && after > level)
  || (cross !== 'up' && before >= level && after < level);

/** Signal exits use the same closed bar for every rule in an all-of policy. */
export function validateExitSignals(signals) {
  if (signals === null) return null;
  if (!signals || !Number.isInteger(signals.step) || !Object.hasOwn(INTERVALS, signals.step)
      || !['any', 'all'].includes(signals.mode)
      || !Array.isArray(signals.rules) || !signals.rules.length || signals.rules.length > 8) {
    throw new Error('Choose a supported cadence and one or more exit signals.');
  }
  const rules = signals.rules.map(rule => {
    const { indicator, cross, level } = rule ?? {};
    if (indicator === 'macd' && ['up', 'down', 'either'].includes(cross) && level === undefined) {
      return { indicator, cross };
    }
    if (indicator === 'rsi' && ['up', 'down'].includes(cross)
        && Number.isFinite(level) && level > 0 && level < 100) {
      return { indicator, cross, level };
    }
    throw new Error('An exit rule needs a MACD cross or a directional RSI threshold between 0 and 100.');
  });
  const unique = new Set(rules.map(rule => JSON.stringify(rule)));
  if (unique.size !== rules.length) throw new Error('Remove duplicate exit rules.');
  return { step: signals.step, mode: signals.mode, rules };
}

const validMinute = row => row.closed === true && row.partial !== true && row.time >= 0
  && [row.open, row.high, row.low, row.close].every(value => Number.isFinite(value) && value > 0)
  && row.high >= Math.max(row.open, row.close) && row.low <= Math.min(row.open, row.close);

/** Return only the continuous suffix ending at the latest expected closed cadence boundary. */
export function closedPerpsBars(minutes, step, time) {
  if (!Array.isArray(minutes) || !Number.isFinite(time)
      || !Number.isInteger(step) || !Object.hasOwn(INTERVALS, step)) return [];
  const closedAt = Math.floor(time / step) * step;
  const suffix = [];
  let expected = closedAt - 60;
  let i = minutes.length - 1;
  while (i >= 0 && minutes[i]?.time >= closedAt) i -= 1;
  for (; i >= 0; i -= 1) {
    const row = minutes[i];
    if (row?.time !== expected || !validMinute(row)) break;
    suffix.push(row);
    expected -= 60;
  }
  return aggregateMinutes(suffix.reverse(), step);
}

/** Evaluate one completed edge. An unavailable leg cannot confirm an all-of rule. */
export function evaluateExitSignals(minutes, signals, time) {
  const bars = closedPerpsBars(minutes, signals.step, time);
  if (bars.length < 2) return { available: false, matched: false };
  const indicators = computeIndicators(bars);
  const readings = signals.rules.map(({ indicator, cross, level }) => {
    const series = indicator === 'macd' ? indicators.macd.histogram : indicators.rsi.series;
    const before = series.at(-2)?.value;
    const after = series.at(-1)?.value;
    if (!Number.isFinite(before) || !Number.isFinite(after)) return null;
    return closesAcross(before, after, indicator === 'macd' ? 0 : level, cross);
  });
  const all = signals.mode === 'all';
  return {
    available: all ? readings.every(value => value !== null) : readings.some(value => value !== null),
    matched: all ? readings.every(value => value === true) : readings.some(value => value === true),
  };
}
