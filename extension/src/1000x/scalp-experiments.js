/**
 * The Experiments side of the 1s scalp window.
 *
 * Every setting in the generated grid (scalp-experiments-data.js) is read on
 * each closed one-second bar and scored against the move over each of twelve
 * horizons. The running hit rates weight the grid's aggregate call, and a
 * setting with a higher hit rate than the one a tile uses takes its place. A
 * second aggregate, in which a reading under 50% votes the other way, is scored
 * beside the first.
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
  macd: p => bars => ind.macdHistogramBps(bars, p.fast, p.slow, p.signal),
  psar: p => bars => ind.psarDirection(bars, p.start, p.step, p.cap),
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
  macd: ['MACD', 'bp', 'MACD histogram on 1s closes, in basis points of price: the fast average less the slow one, less that line’s own signal average. The numbers are the fast, slow and signal spans in seconds.'],
  psar: ['Parabolic SAR', '', 'Parabolic SAR side: +1 while the stop trails below price. The numbers are the acceleration’s start, step and cap.'],
  supertrend: ['Supertrend', '', 'Supertrend side from a mean true range and a multiplier. The numbers are the range’s seconds and the multiplier.'],
  emacross: ['EMA cross', 'bp', 'Fast EMA minus slow EMA, in basis points of price. The numbers are the two spans in seconds.'],
};

export const VARIANTS = Object.freeze(SCALP_EXPERIMENTS.variants.map((variant, index) => {
  const make = READERS[variant.kind];
  if (!make) throw new Error(`No reader for experiment kind ${variant.kind}`);
  const [kindName, unit, describe] = KIND[variant.kind];
  return Object.freeze({ ...variant, index, kindName, unit, describe, read: make(variant.params) });
}));
const BY_ID = new Map(VARIANTS.map(variant => [variant.id, variant]));
// Ids a setting had in an earlier grid: a saved record or a saved choice follows it to its new name.
const ALIASES = new Map(Object.entries(SCALP_EXPERIMENTS.aliases ?? {}));
const resolve = id => BY_ID.get(ALIASES.get(id) ?? id) ?? null;
/** A setting by id. An id from an earlier grid leads to the setting it is now. */
export const variantById = id => resolve(id);
/** The kinds of reading in grid order, with how many settings of each are tested. */
export const KINDS = Object.freeze([...new Set(VARIANTS.map(variant => variant.kind))].map(kind => Object.freeze({ kind,
  name: KIND[kind][0], count: VARIANTS.filter(variant => variant.kind === kind).length })));
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

  /**
   * Restore saved counts. A record from this grid or the one before it is taken
   * setting by setting and interval by interval, so what was learned survives a
   * wider grid: settings and intervals this grid no longer has are dropped and new
   * ones start empty. Anything malformed is refused whole.
   */
  restore(saved) {
    const strings = array => Array.isArray(array) && array.length > 0 && array.every(value => typeof value === 'string');
    if (!saved || typeof saved !== 'object' || !RESTORABLE.has(saved.version) || !strings(saved.ids) || new Set(saved.ids).size !== saved.ids.length
        || !Array.isArray(saved.horizons) || !saved.horizons.length || !saved.horizons.every(Number.isSafeInteger)) return false;
    const width = saved.horizons.length, size = saved.ids.length * width;
    const numbers = array => Array.isArray(array) && array.length === size
      && array.every(value => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= MAX_COUNT);
    if (!numbers(saved.hit) || !numbers(saved.n) || saved.hit.some((value, i) => value > saved.n[i] + 1e-6)) return false;
    const columns = saved.horizons.map(horizon => HORIZONS.indexOf(horizon));
    const hit = new Float64Array(this.#hit.length), n = new Float64Array(this.#n.length);
    let kept = 0;
    for (const [row, id] of saved.ids.entries()) {
      const variant = resolve(id);
      if (!variant) continue;
      for (const [column, h] of columns.entries()) {
        if (h < 0) continue;
        hit[variant.index * HORIZONS.length + h] = saved.hit[row * width + column];
        n[variant.index * HORIZONS.length + h] = saved.n[row * width + column];
        kept += 1;
      }
    }
    if (!kept) return false;
    this.#hit.set(hit); this.#n.set(n);
    this.#seconds = Number.isSafeInteger(saved.seconds) && saved.seconds >= 0 && saved.seconds <= MAX_SECONDS ? saved.seconds : 0;
    return true;
  }
}

/** A saved slot-to-setting map, kept only where each setting exists, is the slot's own kind and is used once. */
export function validAssignments(saved) {
  const out = {}, used = new Set();
  // Every usable saved choice is kept first, so one bad entry cannot cost the others.
  for (const [key, fallback] of Object.entries(DEFAULT_ASSIGNMENTS)) {
    const wanted = Object.hasOwn(saved ?? {}, key) && typeof saved[key] === 'string' ? resolve(saved[key]) : null;
    if (wanted && wanted.kind === BY_ID.get(fallback).kind && !used.has(wanted.id)) { out[key] = wanted.id; used.add(wanted.id); }
  }
  // A slot left without one starts on its own setting, or on the first free setting of its kind when another slot holds that.
  for (const [key, fallback] of Object.entries(DEFAULT_ASSIGNMENTS)) {
    if (out[key]) continue;
    const id = used.has(fallback) ? VARIANTS.find(variant => variant.kind === BY_ID.get(fallback).kind && !used.has(variant.id))?.id : fallback;
    if (!id) return { ...DEFAULT_ASSIGNMENTS };
    out[key] = id; used.add(id);
  }
  return Object.fromEntries(Object.keys(DEFAULT_ASSIGNMENTS).map(key => [key, out[key]]));
}

// The grid is ready once every starting setting has its bars. A switched-in setting never adds to that.
export const WARMUP_BARS = Math.max(...SCALP_EXPERIMENTS.slots.map(slot => BY_ID.get(slot.variant).need));

/**
 * The setting each tile reads now. A chosen setting that does not have its bars
 * yet (just after opening, or after a feed break) leaves its tile on the
 * starting setting until it does, so a switch can never lengthen the grid's
 * warm-up. If another tile is reading that starting setting, the waiting tile
 * takes the first free setting of its kind that has its bars instead: no
 * setting is ever counted twice in the call. The study's replay does the same.
 */
function settingsInEffect(assignments, barCount) {
  const slots = SCALP_EXPERIMENTS.slots, wanted = slots.map(slot => BY_ID.get(assignments[slot.key]) ?? BY_ID.get(slot.variant));
  const taken = new Set(wanted.filter(variant => barCount >= variant.need).map(variant => variant.id));
  return slots.map((slot, i) => {
    if (barCount >= wanted[i].need) return { wanted: wanted[i], variant: wanted[i] };
    const starting = BY_ID.get(slot.variant);
    const variant = !taken.has(starting.id) ? starting
      : VARIANTS.find(other => other.kind === starting.kind && !taken.has(other.id) && other.need <= barCount) ?? starting;
    taken.add(variant.id);
    return { wanted: wanted[i], variant };
  });
}

/** The grid's tiles from the settings currently assigned to its slots; `waiting` names a chosen setting still gathering its bars. */
export function readSlots(assignments, readings, barCount) {
  const effective = settingsInEffect(assignments, barCount);
  return SCALP_EXPERIMENTS.slots.map((slot, i) => {
    const starting = BY_ID.get(slot.variant), { wanted, variant } = effective[i];
    const reading = readings.get(variant.id) ?? { value: null, vote: null, ready: false }, tuned = variant !== starting;
    // A switched-in setting with its bars but no reading yet (a ZigZag before its first swing) is
    // neutral, not warming: a switch must never hold the whole call back.
    const ready = reading.ready || (tuned && barCount >= variant.need);
    return { key: slot.key, variant: variant.id, kind: variant.kind, label: variant.label, unit: variant.unit, describe: variant.describe,
      need: variant.need, have: Math.min(barCount, variant.need), ready, value: reading.value, vote: reading.ready ? reading.vote : ready ? 0 : null, tuned,
      waiting: wanted !== variant ? wanted.id : null };
  });
}

/** The replayed record of the aggregate these choices produce: by switch rule, and with or without inverse votes. */
export function measuredFor({ rule = 'off', inverse = false } = {}) {
  if (inverse) return SCALP_EXPERIMENTS.measured_inverse?.[rule === 'best' ? 'best' : 'off'] ?? {};
  return (rule === 'off' ? SCALP_EXPERIMENTS.measured : SCALP_EXPERIMENTS.measured_rules?.[rule]) ?? {};
}

/**
 * The aggregate call, each tile weighted by how far its blended hit rate sits
 * from a coin flip. Normally a tile at or below 50% has no say. With `inverse`
 * such a tile votes the other way, weighted by how far below 50% it is: the
 * inverse-vote experiment. With no tile carrying an edge the vote is unweighted.
 * `measured` is the replayed record to quote for the result (`measuredFor`).
 */
export function weightedCall(tiles, book, { inverse = false, measured = SCALP_EXPERIMENTS.measured } = {}) {
  const total = tiles.length, ready = tiles.every(tile => tile.ready);
  const up = tiles.filter(tile => tile.vote === 1).length, down = tiles.filter(tile => tile.vote === -1).length;
  const raw = tiles.map(tile => book.blended(tile.variant) - 0.5);
  const edges = raw.map(edge => inverse ? Math.abs(edge) : Math.max(0, edge));
  const sum = edges.reduce((a, b) => a + b, 0);
  const weights = edges.map(edge => sum > 0 ? edge / sum : 1 / total);
  const inverted = raw.map(edge => inverse && sum > 0 && edge < 0);
  const score = ready ? tiles.reduce((acc, tile, i) => acc + weights[i] * (inverted[i] ? -1 : 1) * (tile.vote ?? 0), 0) : 0;
  const size = Math.abs(score);
  const tier = !ready ? 'warming' : size >= SCALP_EXPERIMENTS.strong ? 'strong' : size >= SCALP_EXPERIMENTS.lean ? 'lean' : 'mixed';
  const direction = !ready || tier === 'mixed' || score === 0 ? 'flat' : score > 0 ? 'up' : 'down';
  return { ready, total, up, down, flat: total - up - down, net: up - down, score, weights, inverse, inverted, tier, direction,
    measured: ready ? measured?.[tier] ?? null : null };
}

/**
 * When a setting takes a slot. Two rules, and `off`.
 *
 * `best` (the default, the owner's rule): the unused setting of the slot's kind
 * with the highest current estimate takes it when that estimate is at least
 * `bestMargin` above the estimate of the setting in use. Both settings need
 * `bestMinEff` independent-equivalent calls first, and a slot that changed keeps
 * its setting for `bestLockS`. The estimate is `blended`: the live hit rate at
 * the call horizon, pulled toward the recorded one. Without those three limits
 * the rule changed a tile about five times an hour on the recording, for no
 * gain; with them, about once in seven hours.
 *
 * `clear` (cautious): both settings need `minEff` independent-equivalent calls
 * at the call horizon (calls / horizon); the challenger's cautious (Wilson
 * lower, `z`) estimate must beat the incumbent's plain rate and be at least
 * `minRate`; the recording must not say the opposite (`priorSlack`); and a slot
 * that just changed is left alone for `lockS`.
 *
 * The study replays both rules.
 */
const rule = SCALP_EXPERIMENTS.promotion;
export const RULES = Object.freeze(['best', 'clear', 'off']);
export const PROMOTION = Object.freeze({ rule: rule.rule, minEff: rule.min_eff, z: rule.z, minRate: rule.min_rate, priorSlack: rule.prior_slack,
  lockS: rule.lock_s, everyS: rule.every_s, bestMinEff: rule.best_min_eff, bestLockS: rule.best_lock_s, bestMargin: rule.best_margin });
// A live count can never exceed the sum of the decay series; anything larger in storage is not ours.
const MAX_COUNT = 1.01 / (1 - Math.exp(-Math.LN2 / SCALP_EXPERIMENTS.half_life_s));
// Records of the grid before this one are carried over by setting id.
const RESTORABLE = new Set([2, SCALP_EXPERIMENTS.version]);
// Seconds of ticks scored: ten years is more than any record of ours can hold.
const MAX_SECONDS = 10 * 365 * 86_400;

/**
 * The changes a rule makes now: at most one per slot, same kind only, and one
 * setting never fills two slots. Slots are visited in grid order.
 */
export function findPromotions({ assignments, book, locks = {}, nowS, rule: chosen = PROMOTION.rule }) {
  const used = new Set(Object.values(assignments)), changes = [];
  if (chosen === 'off') return changes;
  if (chosen !== 'best' && chosen !== 'clear') throw new RangeError(`Unknown switch rule ${chosen}`);
  for (const slot of SCALP_EXPERIMENTS.slots) {
    const incumbent = BY_ID.get(assignments[slot.key]);
    if (chosen === 'best') {
      if (nowS - (locks[slot.key] ?? -Infinity) < PROMOTION.bestLockS || book.stats(incumbent.id).eff < PROMOTION.bestMinEff) continue;
      const mine = book.blended(incumbent.id);
      let best = null;
      // Strictly above: of equal estimates the earlier setting in the grid wins, as in the study.
      for (const variant of VARIANTS) {
        if (variant.kind !== incumbent.kind || used.has(variant.id) || book.stats(variant.id).eff < PROMOTION.bestMinEff) continue;
        const estimate = book.blended(variant.id);
        if (!best || estimate > best.estimate) best = { variant, estimate };
      }
      if (!best || !(best.estimate > mine + PROMOTION.bestMargin)) continue;
      changes.push({ slot: slot.key, from: incumbent.id, to: best.variant.id, rate: best.estimate, incumbentRate: mine, rule: chosen });
      used.delete(incumbent.id); used.add(best.variant.id);
      continue;
    }
    if (nowS - (locks[slot.key] ?? -Infinity) < PROMOTION.lockS) continue;
    const mine = book.stats(incumbent.id);
    if (mine.eff < PROMOTION.minEff || mine.rate === null) continue;
    let best = null;
    for (const variant of VARIANTS) {
      if (variant.kind !== incumbent.kind || used.has(variant.id)) continue;
      const theirs = book.stats(variant.id);
      if (theirs.eff < PROMOTION.minEff || theirs.rate === null || theirs.rate < PROMOTION.minRate) continue;
      if (theirs.prior !== null && mine.prior !== null && theirs.prior < mine.prior - PROMOTION.priorSlack) continue;
      const lower = wilsonLower(theirs.rate, theirs.eff, PROMOTION.z);
      if (lower > mine.rate && (!best || lower > best.lower)) best = { variant, lower, rate: theirs.rate };
    }
    if (best) {
      changes.push({ slot: slot.key, from: incumbent.id, to: best.variant.id, rate: best.rate, lower: best.lower, incumbentRate: mine.rate, rule: chosen });
      used.delete(incumbent.id); used.add(best.variant.id);
    }
  }
  return changes;
}

/**
 * The leaderboard at one horizon: every setting with its live and recorded
 * record, best current estimate first. With nothing live that is the recorded
 * order; live results take over as calls settle. `lower` is the cautious live
 * estimate the `clear` rule uses.
 */
export function leaderboard(book, horizon = CALL_HORIZON) {
  return VARIANTS.map(variant => {
    const stats = book.stats(variant.id, horizon);
    return { id: variant.id, label: variant.label, kind: variant.kind, ...stats, blended: book.blended(variant.id, horizon),
      lower: stats.rate === null ? 0 : wilsonLower(stats.rate, stats.eff, PROMOTION.z) };
  }).sort((a, b) => b.blended - a.blended || a.id.localeCompare(b.id));
}

export const AGGREGATES = Object.freeze(['sitout', 'inverse']);
const TALLY_TIERS = Object.freeze(['strong', 'lean', 'mixed']);

/**
 * The inverse-vote experiment's live record. Each second both aggregates make
 * their call from the same tiles: `sitout` (a reading at or under 50% has no
 * say, the call the window shows by default) and `inverse` (it votes the other
 * way). Each call is scored against the close one call horizon later, by tier,
 * with the same decay as the settings' own records. A score under the lean
 * threshold is scored by its sign under `mixed`, as in the study; the window
 * shows no direction for it. Counts survive a feed break and can be saved.
 */
export class CallTally {
  #hit = new Float64Array(AGGREGATES.length * TALLY_TIERS.length);
  #n = new Float64Array(AGGREGATES.length * TALLY_TIERS.length);
  #history = new Map();
  #decay = Math.exp(-Math.LN2 / SCALP_EXPERIMENTS.half_life_s);
  #lastTime = null;

  /** One call per closed bar, with that bar and `{ sitout, inverse }` from weightedCall. */
  observe(bar, calls) {
    if (!bar || !Number.isSafeInteger(bar.time) || !(bar.close > 0) || (this.#lastTime !== null && bar.time <= this.#lastTime)) return;
    this.#lastTime = bar.time;
    for (let i = 0; i < this.#hit.length; i++) { this.#hit[i] *= this.#decay; this.#n[i] *= this.#decay; }
    const past = this.#history.get(bar.time - CALL_HORIZON);
    if (past && past.close !== bar.close) {
      const up = bar.close > past.close;
      for (const [a, entry] of past.entries.entries()) {
        if (!entry) continue;
        const index = a * TALLY_TIERS.length + entry.tier;
        this.#n[index] += 1;
        if ((entry.sign > 0) === up) this.#hit[index] += 1;
      }
    }
    const entries = AGGREGATES.map(name => {
      const call = calls?.[name], tier = TALLY_TIERS.indexOf(call?.tier);
      return call?.ready && tier >= 0 && call.score !== 0 ? { tier, sign: Math.sign(call.score) } : null;
    });
    this.#history.set(bar.time, { close: bar.close, entries });
    const oldest = bar.time - CALL_HORIZON;
    for (const time of this.#history.keys()) { if (time >= oldest) break; this.#history.delete(time); }
  }

  /** The feed lost continuity: calls still waiting can no longer be settled. Counts are kept. */
  reset() { this.#history.clear(); this.#lastTime = null; }

  clear() { this.#hit.fill(0); this.#n.fill(0); this.reset(); }

  /** Per aggregate: each tier and `called` (strong and lean together), as { hit, n, rate, eff }. */
  stats() {
    const row = (hit, n) => ({ hit, n, rate: n > 0.5 ? hit / n : null, eff: n / CALL_HORIZON });
    return Object.fromEntries(AGGREGATES.map((name, a) => {
      const at = tier => a * TALLY_TIERS.length + TALLY_TIERS.indexOf(tier);
      const tiers = Object.fromEntries(TALLY_TIERS.map(tier => [tier, row(this.#hit[at(tier)], this.#n[at(tier)])]));
      return [name, { ...tiers, called: row(tiers.strong.hit + tiers.lean.hit, tiers.strong.n + tiers.lean.n) }];
    }));
  }

  toJSON() {
    const round = array => Array.from(array, value => Math.round(value * 1000) / 1000);
    return { version: 1, aggregates: [...AGGREGATES], tiers: [...TALLY_TIERS], hit: round(this.#hit), n: round(this.#n) };
  }

  /** Restore saved counts. Anything that does not match exactly is ignored. */
  restore(saved) {
    const numbers = array => Array.isArray(array) && array.length === this.#hit.length
      && array.every(value => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= MAX_COUNT);
    if (!saved || saved.version !== 1 || JSON.stringify(saved.aggregates) !== JSON.stringify(AGGREGATES) || JSON.stringify(saved.tiers) !== JSON.stringify(TALLY_TIERS)
        || !numbers(saved.hit) || !numbers(saved.n) || saved.hit.some((value, i) => value > saved.n[i] + 1e-6)) return false;
    this.#hit.set(saved.hit); this.#n.set(saved.n);
    return true;
  }
}
