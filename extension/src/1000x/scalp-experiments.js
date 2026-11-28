/**
 * The Experiments side of the 1s scalp window.
 *
 * Every setting in the generated grid (scalp-experiments-data.js) is read on
 * each closed one-second bar and scored against the move over each of twelve
 * horizons. The running hit rates weight the grid's aggregate call, and a
 * setting that is clearly ahead of the one a tile uses can take its place.
 *
 * Pure: no clock, network or storage. The grid, the horizons and the recorded
 * starting rates come from research/scripts/scalp_1s_study.py.
 */
import * as ind from './scalp-indicators.js';
import { SCALP_EXPERIMENTS } from './scalp-experiments-data.js';

export { SCALP_EXPERIMENTS };
export const HORIZONS = Object.freeze([...SCALP_EXPERIMENTS.horizons]);
export const CALL_HORIZON = SCALP_EXPERIMENTS.call_horizon_s;

const READERS = {
  roc: p => bars => ind.rocBps(bars, p.n),
  breakout: p => bars => ind.breakout(bars, p.w),
  heikin: () => bars => ind.heikinAshiStreak(bars),
  bop: p => bars => ind.bopSma(bars, p.n),
  zigzag: p => bars => ind.zigzagDirection(bars, p.bps),
  donchian: p => bars => ind.donchianPosition(bars, p.w),
  efficiency: p => bars => ind.efficiencyRatio(bars, p.w),
  slope: p => bars => ind.slopeT(bars, p.w),
  rsi: p => bars => ind.rsiCentered(bars, p.n),
  zscore: p => bars => ind.zScore(bars, p.w),
  macd: p => bars => ind.macdHistogramBps(bars, p.scale),
  psar: p => bars => ind.psarDirection(bars, p.start, p.start, p.cap),
  supertrend: p => bars => ind.supertrendDirection(bars, p.n, p.mult),
  emacross: p => bars => ind.emaCrossBps(bars, p.fast, p.slow),
};
const KIND = {
  roc: ['Momentum', 'bp', 'Percent change over the window, in basis points.'],
  breakout: ['Breakout', '', 'Close beyond the high or low of the previous window.'],
  heikin: ['Heikin-Ashi', 'bars', 'Consecutive Heikin-Ashi bars of one colour.'],
  bop: ['Balance of power', '', 'Average of (close − open) / (high − low) over the window.'],
  zigzag: ['ZigZag', '', 'Direction of the current swing after a reversal of this size.'],
  donchian: ['Range position', '', 'Where price sits in the window’s range: +0.5 top, −0.5 bottom.'],
  efficiency: ['Efficiency', '', 'Net move divided by distance travelled over the window: ±1 is a straight line.'],
  slope: ['Slope', 't', 't-statistic of the straight-line fit through the window’s closes.'],
  rsi: ['RSI', '', 'Wilder RSI, centred: +1 only gains, −1 only losses. Read as trend.'],
  zscore: ['Z-score', 'σ', 'Close against the window’s mean, in standard deviations. Read as trend.'],
  macd: ['MACD', 'bp', 'MACD(12,26,9) histogram on 1s closes with every span multiplied, in basis points of price.'],
  psar: ['Parabolic SAR', '', 'Parabolic SAR side: +1 while the stop trails below price.'],
  supertrend: ['Supertrend', '', 'Supertrend side from a mean true range and a multiplier.'],
  emacross: ['EMA cross', 'bp', 'Fast EMA minus slow EMA, in basis points of price.'],
};

export const VARIANTS = Object.freeze(SCALP_EXPERIMENTS.variants.map((variant, index) => {
  const make = READERS[variant.kind];
  if (!make) throw new Error(`No reader for experiment kind ${variant.kind}`);
  const [kindName, unit, describe] = KIND[variant.kind];
  return Object.freeze({ ...variant, index, kindName, unit, describe, read: make(variant.params) });
}));
const BY_ID = new Map(VARIANTS.map(variant => [variant.id, variant]));
export const variantById = id => BY_ID.get(id) ?? null;
export const DEFAULT_ASSIGNMENTS = Object.freeze(Object.fromEntries(SCALP_EXPERIMENTS.slots.map(slot => [slot.key, slot.variant])));
const CALL_INDEX = HORIZONS.indexOf(CALL_HORIZON);

/** Lower end of a Wilson interval for a rate seen over n independent trials. */
export function wilsonLower(rate, n, z = 1.64) {
  if (!(n > 0) || !(rate >= 0 && rate <= 1)) return 0;
  const z2 = z * z;
  return (rate + z2 / (2 * n) - z * Math.sqrt((rate * (1 - rate) + z2 / (4 * n)) / n)) / (1 + z2 / n);
}

/**
 * Running hit rates of every setting at every horizon. Counts decay with a
 * half-life so the rates follow the market that is trading now, and they can be
 * saved and restored, so testing carries on from one window to the next.
 */
export class ExperimentBook {
  #hit = new Float64Array(VARIANTS.length * HORIZONS.length);
  #n = new Float64Array(VARIANTS.length * HORIZONS.length);
  #history = new Map();
  #decay = Math.exp(-Math.LN2 / SCALP_EXPERIMENTS.half_life_s);
  #seconds = 0;
  #lastTime = null;

  /**
   * One call per closed bar, with all closed bars up to it. Settles the calls
   * made one horizon ago and returns each setting's reading at this bar.
   */
  observe(bars) {
    const bar = bars.at(-1);
    const readings = new Map();
    if (!bar || !Number.isSafeInteger(bar.time) || !(bar.close > 0) || (this.#lastTime !== null && bar.time <= this.#lastTime)) return readings;
    this.#lastTime = bar.time;
    this.#seconds += 1;
    for (let i = 0; i < this.#hit.length; i++) { this.#hit[i] *= this.#decay; this.#n[i] *= this.#decay; }
    for (const [h, horizon] of HORIZONS.entries()) {
      const past = this.#history.get(bar.time - horizon);
      if (!past || past.close === bar.close) continue;
      const up = bar.close > past.close;
      for (let v = 0; v < VARIANTS.length; v++) {
        const vote = past.votes[v];
        if (!vote) continue;
        const index = v * HORIZONS.length + h;
        this.#n[index] += 1;
        if ((vote > 0) === up) this.#hit[index] += 1;
      }
    }
    const votes = new Int8Array(VARIANTS.length);
    for (const variant of VARIANTS) {
      const ready = bars.length >= variant.need;
      const value = ready ? variant.read(bars) : null;
      const vote = ind.vote(value);
      votes[variant.index] = vote ?? 0;
      readings.set(variant.id, { value, vote, ready: ready && value !== null });
    }
    this.#history.set(bar.time, { close: bar.close, votes });
    const oldest = bar.time - HORIZONS.at(-1);
    for (const time of this.#history.keys()) { if (time >= oldest) break; this.#history.delete(time); }
    return readings;
  }

  /** The feed lost continuity: calls still waiting can no longer be settled. Counts are kept. */
  reset() { this.#history.clear(); this.#lastTime = null; }

  /** Clear everything learned, back to the recorded starting rates. */
  clear() { this.#hit.fill(0); this.#n.fill(0); this.#history.clear(); this.#lastTime = null; this.#seconds = 0; }

  /** Live record of one setting at one horizon. `eff` treats overlapping seconds as n / horizon trials. */
  stats(id, horizon = CALL_HORIZON) {
    const variant = BY_ID.get(id), h = HORIZONS.indexOf(horizon);
    if (!variant || h < 0) return { hit: 0, n: 0, rate: null, eff: 0, prior: null };
    const index = variant.index * HORIZONS.length + h, n = this.#n[index];
    return { hit: this.#hit[index], n, rate: n > 0.5 ? this.#hit[index] / n : null, eff: n / horizon, prior: variant.prior[h] ?? null };
  }

  /** Live rate pulled toward the recorded rate, which counts as a fixed number of calls: the best current estimate. */
  blended(id, horizon = CALL_HORIZON) {
    const { hit, n, prior } = this.stats(id, horizon), weight = SCALP_EXPERIMENTS.prior_seconds;
    return (hit + weight * (prior ?? 0.5)) / (n + weight);
  }

  get seconds() { return this.#seconds; }

  toJSON() {
    const round = array => Array.from(array, value => Math.round(value * 1000) / 1000);
    return { version: SCALP_EXPERIMENTS.version, ids: VARIANTS.map(variant => variant.id), horizons: [...HORIZONS], seconds: this.#seconds,
      hit: round(this.#hit), n: round(this.#n) };
  }

  /** Restore saved counts. Anything that does not match this grid exactly is ignored. */
  restore(saved) {
    const size = VARIANTS.length * HORIZONS.length;
    const numbers = array => Array.isArray(array) && array.length === size
      && array.every(value => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= MAX_COUNT);
    if (!saved || saved.version !== SCALP_EXPERIMENTS.version || JSON.stringify(saved.ids) !== JSON.stringify(VARIANTS.map(variant => variant.id))
        || JSON.stringify(saved.horizons) !== JSON.stringify(HORIZONS) || !numbers(saved.hit) || !numbers(saved.n)
        || saved.hit.some((value, i) => value > saved.n[i] + 1e-6)) return false;
    this.#hit.set(saved.hit); this.#n.set(saved.n);
    this.#seconds = Number.isSafeInteger(saved.seconds) && saved.seconds >= 0 ? saved.seconds : 0;
    return true;
  }
}

/** A saved slot-to-setting map, kept only where each setting exists, is the slot's own kind and is used once. */
export function validAssignments(saved) {
  const out = { ...DEFAULT_ASSIGNMENTS }, used = new Set();
  for (const [key, fallback] of Object.entries(DEFAULT_ASSIGNMENTS)) {
    const wanted = BY_ID.get(saved?.[key]);
    const id = wanted && wanted.kind === BY_ID.get(fallback).kind && !used.has(wanted.id) ? wanted.id : fallback;
    out[key] = used.has(id) ? fallback : id;
    used.add(out[key]);
  }
  return new Set(Object.values(out)).size === Object.keys(out).length ? out : { ...DEFAULT_ASSIGNMENTS };
}

/** The grid's tiles from the settings currently assigned to its slots. */
export function readSlots(assignments, readings, barCount) {
  return SCALP_EXPERIMENTS.slots.map(slot => {
    const variant = BY_ID.get(assignments[slot.key]) ?? BY_ID.get(slot.variant);
    const reading = readings.get(variant.id) ?? { value: null, vote: null, ready: false }, tuned = variant.id !== slot.variant;
    // A switched-in setting with its bars but no reading yet (a ZigZag before its first swing) is
    // neutral, not warming: a switch must never hold the whole call back.
    const ready = reading.ready || (tuned && barCount >= variant.need);
    return { key: slot.key, variant: variant.id, kind: variant.kind, label: variant.label, unit: variant.unit, describe: variant.describe,
      need: variant.need, have: Math.min(barCount, variant.need), ready, value: reading.value, vote: reading.ready ? reading.vote : ready ? 0 : null, tuned };
  });
}

/**
 * The aggregate call, each tile weighted by how far its blended hit rate sits
 * above a coin flip. A tile at or below 50% has no say. With no tile above 50%
 * the vote is unweighted.
 */
export function weightedCall(tiles, book) {
  const total = tiles.length, ready = tiles.every(tile => tile.ready);
  const up = tiles.filter(tile => tile.vote === 1).length, down = tiles.filter(tile => tile.vote === -1).length;
  const edges = tiles.map(tile => Math.max(0, book.blended(tile.variant) - 0.5));
  const sum = edges.reduce((a, b) => a + b, 0);
  const weights = edges.map(edge => sum > 0 ? edge / sum : 1 / total);
  const score = ready ? tiles.reduce((acc, tile, i) => acc + weights[i] * (tile.vote ?? 0), 0) : 0;
  const size = Math.abs(score);
  const tier = !ready ? 'warming' : size >= SCALP_EXPERIMENTS.strong ? 'strong' : size >= SCALP_EXPERIMENTS.lean ? 'lean' : 'mixed';
  const direction = !ready || tier === 'mixed' || score === 0 ? 'flat' : score > 0 ? 'up' : 'down';
  return { ready, total, up, down, flat: total - up - down, net: up - down, score, weights, tier, direction,
    measured: ready ? SCALP_EXPERIMENTS.measured[tier] ?? null : null };
}

/**
 * When a setting may take a slot. Both settings need `minEff` independent-equivalent
 * calls at the call horizon (calls / horizon); the challenger's cautious (Wilson
 * lower, `z`) estimate must beat the incumbent's plain rate and be at least
 * `minRate`; the recording must not say the opposite (`priorSlack`); a setting
 * that needs more than `maxNeed` bars is never switched in, so the grid's
 * warm-up cannot grow; and a slot that just changed is left alone for `lockS`.
 * The study replays the same rule.
 */
const rule = SCALP_EXPERIMENTS.promotion;
export const PROMOTION = Object.freeze({ minEff: rule.min_eff, z: rule.z, minRate: rule.min_rate, priorSlack: rule.prior_slack,
  lockS: rule.lock_s, everyS: rule.every_s, maxNeed: rule.max_need });
// A live count can never exceed the sum of the decay series; anything larger in storage is not ours.
const MAX_COUNT = 1.01 / (1 - Math.exp(-Math.LN2 / SCALP_EXPERIMENTS.half_life_s));

/**
 * Settings that are clearly ahead of the one a slot uses: same kind, not in use
 * elsewhere, with a cautious live estimate above the incumbent's live rate and
 * no contradiction from the recording. At most one change per slot.
 */
export function findPromotions({ assignments, book, locks = {}, nowS }) {
  const used = new Set(Object.values(assignments)), changes = [];
  for (const slot of SCALP_EXPERIMENTS.slots) {
    if (nowS - (locks[slot.key] ?? -Infinity) < PROMOTION.lockS) continue;
    const incumbent = BY_ID.get(assignments[slot.key]), mine = book.stats(incumbent.id);
    if (mine.eff < PROMOTION.minEff || mine.rate === null) continue;
    let best = null;
    for (const variant of VARIANTS) {
      if (variant.kind !== incumbent.kind || used.has(variant.id) || variant.need > PROMOTION.maxNeed) continue;
      const theirs = book.stats(variant.id);
      if (theirs.eff < PROMOTION.minEff || theirs.rate === null || theirs.rate < PROMOTION.minRate) continue;
      if (theirs.prior !== null && mine.prior !== null && theirs.prior < mine.prior - PROMOTION.priorSlack) continue;
      const lower = wilsonLower(theirs.rate, theirs.eff, PROMOTION.z);
      if (lower > mine.rate && (!best || lower > best.lower)) best = { variant, lower, rate: theirs.rate };
    }
    if (best) {
      changes.push({ slot: slot.key, from: incumbent.id, to: best.variant.id, rate: best.rate, lower: best.lower, incumbentRate: mine.rate });
      used.delete(incumbent.id); used.add(best.variant.id);
    }
  }
  return changes;
}

/**
 * The leaderboard at one horizon: every setting with its live and recorded
 * record, best current estimate first. With nothing live that is the recorded
 * order; live results take over as calls settle. `lower` is the cautious live
 * estimate the switch rule uses.
 */
export function leaderboard(book, horizon = CALL_HORIZON) {
  return VARIANTS.map(variant => {
    const stats = book.stats(variant.id, horizon);
    return { id: variant.id, label: variant.label, kind: variant.kind, ...stats, blended: book.blended(variant.id, horizon),
      lower: stats.rate === null ? 0 : wilsonLower(stats.rate, stats.eff, PROMOTION.z) };
  }).sort((a, b) => b.blended - a.blended || a.id.localeCompare(b.id));
}
