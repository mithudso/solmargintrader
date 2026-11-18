import { SHAPE_WINDOW } from '../../src/1000x/reversal.js';
import { practiceSignals } from '../../src/perps/strategies.js';
import { CADENCE_POLICY, buildContext, buildDecisions } from './zec-perps-signals.mjs';

const STEP = 300;
const BOP_SMOOTHING = [3, 5, 10];
const SHAPE_GATE = ['trend_up', 'bowl'];

function candidate(id, name, family, params, details, kind = 'signal') {
  return { id, name, family, kind, step: STEP, params, details };
}

function zscore(window, entry_z, exit_z = 0) {
  return candidate(`zscore-${window}-${entry_z}-${exit_z}`,
    `Z-score(${window}) ≤ ${entry_z} → ≥ ${exit_z}`, 'zscore', { window, entry_z, exit_z },
    'Use the rolling sample standard deviation of closed prices. Enter at or below the first threshold and go flat at or above the second.');
}

function rsi(period, oversold, exit_level) {
  return candidate(`rsi-${period}-${oversold}-${exit_level}`,
    `RSI(${period}) < ${oversold} → > ${exit_level}`, 'rsi', { period, oversold, exit_level },
    'Use the existing Wilder-style RSI. Enter strictly below the first threshold and go flat strictly above the second.');
}

function bop(smoothing, entry = 0, exit = 0) {
  const name = `Balance of Power SMA(${smoothing}) > ${entry} → ≤ ${exit}`;
  return candidate(`bop-${smoothing}-${entry}-${exit}`, name, 'bop', { smoothing, entry, exit },
    'Smooth (close − open) / (high − low), using zero for zero-range bars. Enter strictly above the first threshold and exit at or below the second.');
}

function volty(length, factor) {
  return candidate(`volty-${length}-${factor}`, `Volty(${length} × ${factor})`, 'volty',
    { length, factor },
    'From the next five-minute bar, stage stops at the prior close ± multiplier × SMA of true range. An eligible opposite stop reverses the position.',
    'volty');
}

const spec = ({ id, family, params }) => ({ id, family, params });

function vote(members, mode) {
  const label = { all: 'All agree', any: 'Any active', majority: 'Two of three', confirm: 'Entry confirmation' }[mode];
  const behavior = {
    all: 'Hold long only while all members are active.',
    any: 'Hold long while at least one member is active.',
    majority: 'Hold long while at least two of the three members are active.',
    confirm: 'Enter when reversion and pressure agree. Exit when the reversion member turns off.' +
      ' A later change in pressure does not close an existing position.',
  }[mode];
  return candidate(
    `${mode}--${members.map(member => member.id).join('--')}`,
    `${label} · ${members.map(member => member.name).join(' + ')}`, 'vote',
    { mode, members: members.map(spec) }, behavior);
}

function filteredVolty(breakoutRule, filters) {
  return candidate(
    `gate--${breakoutRule.id}--${filters.map(filter => filter.id).join('--')}`,
    `${breakoutRule.name} gated by ${filters.map(filter => filter.name).join(' + ')}`, 'volty',
    { ...breakoutRule.params, filters: filters.map(spec) },
    'Keep the original Volty stops. Enable a side only while all filters agree. For shorts, apply the same indicator rules to reflected OHLC prices. A blocked opposite stop leaves the position open.', 'volty');
}

function priorBop(cadence) {
  const filter = cadence ? 'shape + cadence' : 'shape';
  return candidate(
    cadence ? 'bop-5-prior-shape-cadence' : 'bop-5-prior-shape',
    `Balance of Power SMA(5) · ${filter}`, 'bop',
    { smoothing: 5, entry: 0, exit: 0, shape: SHAPE_GATE, shapeWindow: SHAPE_WINDOW,
      cadence, cadencePolicy: cadence ? CADENCE_POLICY : null },
    'Prior sweep baseline. Admit a new positive-pressure cycle only when the graph shape is a rising trend or bowl.'
      + (cadence ? ' Also require a positive next spectral increment.' : '')
      + ' Exit when pressure turns nonpositive.');
}

/** Every candidate uses five-minute closed bars, including all members of a combination. */
export function fiveMinuteCandidates() {
  const zGrid = [12, 20, 40, 90].flatMap(window =>
    [-1.5, -2, -2.5].map(entry => zscore(window, entry)));
  const rsiGrid = [7, 14, 21, 28].flatMap(period =>
    [[25, 50], [30, 50], [30, 55], [35, 60]].map(([entry, exit]) => rsi(period, entry, exit)));
  const pressureGrid = BOP_SMOOTHING.flatMap(smoothing =>
    [[0, 0], [0.05, 0], [0.1, -0.05]].map(([entry, exit]) => bop(smoothing, entry, exit)));
  const breakoutGrid = [4, 5, 10, 14].flatMap(length => [0.75, 1.25, 1.5].map(factor => volty(length, factor)));

  const zBases = [zscore(12, -1.5), zscore(20, -2), zscore(40, -2)];
  const rsiBases = [rsi(7, 30, 55), rsi(14, 30, 50), rsi(21, 35, 60)];
  const pressureBases = [bop(3), bop(5)];
  const breakoutBases = [volty(4, 0.75), volty(5, 1.25), volty(10, 1.5)];

  const reversionVotes = zBases.flatMap((z, i) => ['all', 'any'].map(mode => vote([z, rsiBases[i]], mode)));
  const pressureVotes = [...zBases, ...rsiBases].flatMap(reversion =>
    pressureBases.flatMap(pressure => ['all', 'confirm'].map(mode => vote([reversion, pressure], mode))));
  const threeVotes = zBases.flatMap((z, i) =>
    ['all', 'majority'].map(mode => vote([z, rsiBases[i], bop(5)], mode)));
  const pressureBreakouts = breakoutBases.flatMap(rule =>
    BOP_SMOOTHING.map(smoothing => filteredVolty(rule, [bop(smoothing)])));
  const reversionBreakouts = breakoutBases.flatMap(rule =>
    [[zBases[1]], [rsiBases[1]], [zBases[1], rsiBases[1]]].map(filters => filteredVolty(rule, filters)));

  return [...zGrid, ...[-1.5, -2, -2.5].map(entry => zscore(20, entry, -0.5)),
    ...rsiGrid, ...pressureGrid, priorBop(false), priorBop(true), ...breakoutGrid,
    ...reversionVotes, ...pressureVotes, ...threeVotes, ...pressureBreakouts, ...reversionBreakouts];
}

export function fiveMinuteContext(minutes) {
  const features = buildContext(minutes, STEP);
  const reflected = features.bars.map(bar =>
    ({ ...bar, open: -bar.open, high: -bar.low, low: -bar.high, close: -bar.close }));
  return { features, reflected, cache: new Map() };
}

function pressureSignals(context, params, direction) {
  let held = false;
  return context.features.bop[params.smoothing].map(value => {
    if (value === null) {
      held = false;
      return null;
    }
    const pressure = direction * value;
    if (!held && pressure > params.entry) held = true;
    else if (held && pressure <= params.exit) held = false;
    return { weight: Number(held) };
  });
}

function memberSeries(context, member, direction = 1) {
  const key = direction + ':' + member.id;
  if (context.cache.has(key)) return context.cache.get(key);
  const { family, params } = member;
  let values;
  if (family === 'bop') {
    values = pressureSignals(context, params, direction);
  } else {
    if (!['rsi', 'zscore'].includes(family)) throw new Error('Unknown combination member ' + family);
    values = practiceSignals(direction === 1 ? context.features.bars : context.reflected,
      { step: STEP, members: [{ strategy: family, params }] });
  }
  context.cache.set(key, values);
  return values;
}

function combinedSignals(context, { mode, members }) {
  const votes = members.map(member => memberSeries(context, member));
  let held = false;
  return context.features.bars.map((_, i) => {
    const states = votes.map(series => series[i]);
    if (states.includes(null)) {
      held = false;
      return null;
    }
    const active = states.reduce((sum, state) => sum + state.weight, 0);
    if (mode === 'confirm') {
      held = held ? states[0].weight > 0 : active === members.length;
    } else {
      const target = { all: members.length, any: 1, majority: 2 }[mode];
      held = active >= target;
    }
    return { weight: Number(held) };
  });
}

function breakoutSignals(context, { length, factor, filters = [] }) {
  const stops = practiceSignals(context.features.bars, { kind: 'volty', step: STEP, length, factor });
  if (!filters.length) return stops;
  const longs = filters.map(filter => memberSeries(context, filter, 1));
  const shorts = filters.map(filter => memberSeries(context, filter, -1));
  return stops.map((stop, i) => {
    if (!stop) return null;
    const long = longs.every(series => series[i]?.weight === 1);
    const short = shorts.every(series => series[i]?.weight === 1);
    if (!(long || short)) return null;
    return { upper: long ? stop.upper : Infinity, lower: short ? stop.lower : -Infinity };
  });
}

/** Signals are available from the first minute after the complete signal bar. */
export function fiveMinuteDecisions(context, rule) {
  if (rule.step !== STEP) throw new Error('Expected a five-minute candidate.');
  const { family, params } = rule;
  if (family === 'bop' && params.shape) {
    return buildDecisions(context.features, { ...rule, kind: 'bop' }, true, params.cadence);
  }
  let signals;
  if (family === 'volty') signals = breakoutSignals(context, params);
  else if (family === 'vote') signals = combinedSignals(context, params);
  else signals = memberSeries(context, rule);
  return new Map(context.features.bars.map((bar, i) => [bar.time + STEP, signals[i]]));
}
