/**
 * The 1s scalp read-out: sixteen trend tiles, their net vote, a 30 second cone
 * and a running score of the vote against what price then did.
 *
 * The tile set, thresholds and measured hit rates come from
 * research/scripts/scalp_1s_study.py (recorded Jupiter oracle ticks). They
 * describe a lean, not a forecast that pays: research/papers/SCALP-1S-STUDY.md
 * has the numbers. Pure; no clock, network or storage.
 */
import * as ind from './scalp-indicators.js';
import { SCALP_MODEL } from './scalp-model-data.js';

export { SCALP_MODEL };
export const HORIZON_S = SCALP_MODEL.horizon_s;

const READERS = {
  roc_2: bars => ind.rocBps(bars, 2),
  roc_5: bars => ind.rocBps(bars, 5),
  roc_60: bars => ind.rocBps(bars, 60),
  brk_20: bars => ind.breakout(bars, 20),
  brk_60: bars => ind.breakout(bars, 60),
  ha: bars => ind.heikinAshiStreak(bars),
  bop_5: bars => ind.bopSma(bars, 5),
  zzdir_1: bars => ind.zigzagDirection(bars, 1),
  don_60: bars => ind.donchianPosition(bars, 60),
  er_60: bars => ind.efficiencyRatio(bars, 60),
  slope_60: bars => ind.slopeT(bars, 60),
  rsi_7: bars => ind.rsiCentered(bars, 7),
  z_20: bars => ind.zScore(bars, 20),
  macdh_1: bars => ind.macdHistogramBps(bars),
  psar: bars => ind.psarDirection(bars),
  super_10: bars => ind.supertrendDirection(bars, 10),
};
// Bars before a tile is shown. Path-dependent tiles (SAR, Supertrend, ZigZag,
// Heikin-Ashi, RSI) are computed from the window start and need time to settle.
const NEED = { roc_2: 3, roc_5: 6, roc_60: 61, brk_20: 21, brk_60: 61, ha: 60, bop_5: 5, zzdir_1: 60,
  don_60: 60, er_60: 61, slope_60: 60, rsi_7: 60, z_20: 20, macdh_1: 78, psar: 60, super_10: 60 };
const DETAIL = {
  roc_2: ['bp', 'Price change over the last 2 seconds.'],
  roc_5: ['bp', 'Price change over the last 5 seconds.'],
  roc_60: ['bp', 'Price change over the last 60 seconds.'],
  brk_20: ['', 'Close beyond the high or low of the previous 20 seconds.'],
  brk_60: ['', 'Close beyond the high or low of the previous 60 seconds. The strongest single reading in the study.'],
  ha: ['bars', 'Consecutive Heikin-Ashi bars of one colour.'],
  bop_5: ['', 'Average of (close − open) / (high − low) over 5 seconds.'],
  zzdir_1: ['', 'Direction of the current swing after a 1 basis point reversal.'],
  don_60: ['', 'Where price sits in the last 60 seconds’ range: +0.5 top, −0.5 bottom.'],
  er_60: ['', 'Net move divided by distance travelled over 60 seconds: ±1 is a straight line.'],
  slope_60: ['t', 't-statistic of the straight-line fit through the last 60 closes.'],
  rsi_7: ['', 'Wilder RSI over 7 seconds, centred: +1 only gains, −1 only losses.'],
  z_20: ['σ', 'Close against the mean of the last 20 seconds, in standard deviations.'],
  macdh_1: ['bp', 'MACD(12,26,9) histogram on 1s closes, in basis points of price.'],
  psar: ['', 'Parabolic SAR side: +1 while the stop trails below price.'],
  super_10: ['', 'Supertrend side from a 10 second mean true range.'],
};

export const TILES = Object.freeze(SCALP_MODEL.tiles.map(tile => {
  if (!READERS[tile.feature]) throw new Error(`No reader for scalp tile ${tile.feature}`);
  return Object.freeze({ ...tile, need: NEED[tile.feature], unit: DETAIL[tile.feature][0],
    describe: DETAIL[tile.feature][1], read: READERS[tile.feature] });
}));
export const WARMUP_BARS = Math.max(...TILES.map(tile => tile.need));

/** Every tile's reading and vote at the last closed bar. */
export function readTiles(bars) {
  return TILES.map(tile => {
    const ready = bars.length >= tile.need;
    const value = ready ? tile.read(bars) : null;
    return { key: tile.key, label: tile.label, unit: tile.unit, describe: tile.describe, need: tile.need,
      have: Math.min(bars.length, tile.need), ready: ready && value !== null, value, vote: ready ? ind.vote(value) : null };
  });
}

/** Net vote and the tier it falls in. Not ready until every tile has a reading. */
export function scalpCall(tiles) {
  const total = tiles.length;
  const up = tiles.filter(tile => tile.vote === 1).length, down = tiles.filter(tile => tile.vote === -1).length;
  const ready = tiles.every(tile => tile.ready);
  const net = up - down, size = Math.abs(net);
  const tier = !ready ? 'warming' : size >= SCALP_MODEL.strong ? 'strong' : size >= SCALP_MODEL.lean ? 'lean' : 'mixed';
  const direction = !ready || tier === 'mixed' || net === 0 ? 'flat' : net > 0 ? 'up' : 'down';
  return { ready, total, up, down, flat: total - up - down, net, tier, direction,
    measured: ready ? SCALP_MODEL.measured[tier] ?? null : null };
}

/**
 * The slope ladder: for each window the fitted slope, the slope's own rate of
 * change, and whether the move is accelerating (both signs agree) or fading.
 * Not part of the vote; `measured` is what following each reading returned in
 * the study.
 */
export function readSlopes(bars) {
  return SCALP_MODEL.slopes.map(row => {
    const window = row.window_s, ready = bars.length >= window;
    const slope = ready ? ind.slopeBps(bars, window) : null, change = ready ? ind.curvatureBps(bars, window) : null;
    const slopeVote = ind.vote(slope), changeVote = ind.vote(change);
    const state = !ready ? 'warming' : !slopeVote ? 'flat' : !changeVote ? 'steady' : slopeVote === changeVote ? 'accelerating' : 'fading';
    return { window, ready, have: Math.min(bars.length, window), slope, change, slopeVote, changeVote, state,
      strength: ready ? Math.min(1, Math.abs(ind.slopeT(bars, Math.max(window, 4)) ?? 0) / 4) : 0, measured: row };
  });
}

/**
 * Per-window history of the slope ladder: the range the slope and its second
 * derivative have moved in, and how long a slope kept one sign before it
 * reversed. Only whole runs are timed: the run in progress when observation
 * began, or when the feed broke, has no known start and is left out.
 */
export class SlopeHistory {
  #state = new Map();
  #retain;
  #tick = 0;

  constructor(retainSeconds = 3600) {
    this.#retain = retainSeconds;
    for (const row of SCALP_MODEL.slopes) {
      this.#state.set(row.window_s, { slopes: [], changes: [], runs: [], sign: 0, start: 0, whole: false });
    }
  }

  /** One call per closed bar, with that bar's readSlopes() rows. */
  observe(rows) {
    const tick = this.#tick++;
    for (const row of rows) {
      const state = this.#state.get(row.window);
      if (!state || !row.ready || row.slope === null || row.change === null) continue;
      state.slopes.push(row.slope);
      state.changes.push(row.change);
      if (state.slopes.length > this.#retain) { state.slopes.shift(); state.changes.shift(); }
      const sign = row.slopeVote;
      if (!sign || sign === state.sign) continue;
      if (state.sign !== 0) {
        if (state.whole) state.runs.push({ sign: state.sign, seconds: tick - state.start });
        if (state.runs.length > 500) state.runs.shift();
        state.whole = true;
      }
      state.sign = sign;
      state.start = tick;
    }
  }

  /** The feed lost continuity: the open run can no longer be timed. */
  reset() {
    for (const state of this.#state.values()) Object.assign(state, { sign: 0, start: 0, whole: false });
  }

  stats() {
    const summary = runs => runs.length ? { count: runs.length,
      meanS: runs.reduce((sum, run) => sum + run.seconds, 0) / runs.length,
      maxS: Math.max(...runs.map(run => run.seconds)) } : { count: 0, meanS: null, maxS: null };
    const range = values => values.length ? { min: Math.min(...values), max: Math.max(...values) } : { min: null, max: null };
    return [...this.#state].map(([window, state]) => ({
      window, samples: state.slopes.length, slope: range(state.slopes), change: range(state.changes),
      runs: { ...summary(state.runs), up: summary(state.runs.filter(run => run.sign > 0)), down: summary(state.runs.filter(run => run.sign < 0)),
        list: state.runs.map(run => ({ ...run })) },
      // ageS counts from the flip that started this run; without one seen it is a lower bound.
      current: { sign: state.sign, ageS: state.sign ? this.#tick - state.start : null, sinceFlip: state.whole },
      recent: state.slopes.slice(-120),
    }));
  }
}

/**
 * Running accuracy of each ladder window: every second's slope sign is scored
 * against the move over the following 30 seconds, like the grid's own calls.
 * A flat slope makes no call. Seconds overlap, so n is not independent trials.
 */
export class SlopeScore {
  #entries = new Map();
  #retain;

  constructor(retainSeconds = 600) {
    this.#retain = retainSeconds;
    for (const row of SCALP_MODEL.slopes) this.#entries.set(row.window_s, []);
  }

  /** One call per closed bar, with that bar and its readSlopes() rows. */
  observe(bar, rows) {
    if (!bar || !Number.isSafeInteger(bar.time) || !(bar.close > 0)) return;
    for (const row of rows) {
      const list = this.#entries.get(row.window);
      if (!list || (list.length && bar.time <= list.at(-1).time)) continue;
      for (const entry of list) {
        if (entry.outcome !== null) continue;
        if (entry.time + HORIZON_S === bar.time) entry.outcome = bar.close === entry.price ? 'flat' : (bar.close > entry.price) === (entry.vote > 0) ? 'hit' : 'miss';
        else if (entry.time + HORIZON_S < bar.time) entry.outcome = 'unknown';
      }
      if (row.ready && row.slopeVote) list.push({ time: bar.time, price: bar.close, vote: row.slopeVote, outcome: null });
      while (list.length && list[0].time < bar.time - this.#retain) list.shift();
    }
  }

  /** The feed lost continuity: calls still waiting can no longer be settled. */
  reset() {
    for (const list of this.#entries.values()) for (const entry of list) if (entry.outcome === null) entry.outcome = 'unknown';
  }

  stats() {
    return new Map([...this.#entries].map(([window, list]) => {
      const hit = list.filter(entry => entry.outcome === 'hit').length, miss = list.filter(entry => entry.outcome === 'miss').length;
      return [window, { hit, miss, n: hit + miss, rate: hit + miss ? hit / (hit + miss) : null }];
    }));
  }
}

/**
 * Price bands for each of the next 30 seconds. sigmaBps is the standard
 * deviation of recent 1s returns; the multipliers are the recorded 68% and 90%
 * quantiles of |30s move| / (sigma * sqrt(30)). The centre drifts by the tier's
 * measured mean move, which is a fraction of a basis point.
 */
export function cone({ price, sigmaBps, direction = 'flat', tier = 'mixed' }) {
  if (!(price > 0) || !(sigmaBps >= 0) || !Number.isFinite(sigmaBps)) return [];
  const drift = direction === 'flat' ? 0 : (direction === 'up' ? 1 : -1) * (SCALP_MODEL.measured[tier]?.mean_follow_bps ?? 0);
  const at = bps => price * (1 + bps / 1e4);
  return Array.from({ length: HORIZON_S }, (_, i) => {
    const seconds = i + 1, sigma = sigmaBps * Math.sqrt(seconds), centre = drift * seconds / HORIZON_S;
    return { seconds, mid: at(centre),
      innerLow: at(centre - SCALP_MODEL.cone.p68 * sigma), innerHigh: at(centre + SCALP_MODEL.cone.p68 * sigma),
      outerLow: at(centre - SCALP_MODEL.cone.p90 * sigma), outerHigh: at(centre + SCALP_MODEL.cone.p90 * sigma) };
  });
}

/**
 * Scores each second's call against the close 30 seconds later. Calls made in a
 * segment that was later discarded are dropped, never guessed.
 */
export class ScoreBook {
  #entries = [];
  #retain;

  constructor(retainSeconds = 600) { this.#retain = retainSeconds; }

  /** Record the call made at this closed bar and settle calls that are now 30 s old. */
  observe(bar, call) {
    if (!bar || !Number.isSafeInteger(bar.time) || !(bar.close > 0)) return;
    const last = this.#entries.at(-1);
    if (last && bar.time <= last.time) return;
    for (const entry of this.#entries) {
      if (entry.outcome === null && entry.time + HORIZON_S === bar.time) {
        entry.move = (bar.close / entry.price - 1) * 1e4;
        entry.outcome = entry.direction === 'flat' ? 'none'
          : entry.move === 0 ? 'flat' : (entry.move > 0) === (entry.direction === 'up') ? 'hit' : 'miss';
      } else if (entry.outcome === null && entry.time + HORIZON_S < bar.time) entry.outcome = 'unknown';
    }
    this.#entries.push({ time: bar.time, price: bar.close, direction: call?.ready ? call.direction : 'flat',
      tier: call?.ready ? call.tier : 'warming', net: call?.ready ? call.net : 0, outcome: null, move: null });
    while (this.#entries.length && this.#entries[0].time < bar.time - this.#retain) this.#entries.shift();
  }

  reset() { this.#entries = []; }

  /** The last `seconds` entries, oldest first, for the ribbon. */
  recent(seconds = 120) { return this.#entries.slice(-seconds).map(entry => ({ ...entry })); }

  /** Hit counts over the retained window. Seconds overlap, so n is not independent trials. */
  stats() {
    const out = { all: { hit: 0, miss: 0 }, strong: { hit: 0, miss: 0 }, lean: { hit: 0, miss: 0 } };
    for (const entry of this.#entries) {
      if (entry.outcome !== 'hit' && entry.outcome !== 'miss') continue;
      out.all[entry.outcome] += 1;
      if (out[entry.tier]) out[entry.tier][entry.outcome] += 1;
    }
    for (const row of Object.values(out)) {
      row.n = row.hit + row.miss;
      row.rate = row.n ? row.hit / row.n : null;
    }
    return out;
  }
}

/* ------------------------------------------------------------------ payout -- */

const D = 1_000_000n, A = 50_000n, B = 7_259_685_000n, K = 1_983_979n;
const PRICE_SCALE = 1e8;

/**
 * The saved Jupiter frontend's integer payout arithmetic (a port of
 * oracle_leverage/exit50.py:quote_position). An estimate of the page's own
 * figure, not on-chain settlement or a fill.
 */
export function quotePosition({ margin, notional, entry, mark, side, closeFeePpm = 20n, winFeePpm = 30_000n, maxWinMultiple = 25n }) {
  for (const value of [margin, notional, entry, mark]) {
    if (typeof value !== 'bigint' || value <= 0n) throw new RangeError('margin, notional and prices must be positive integers');
  }
  if (side !== 'long' && side !== 'short') throw new RangeError('side must be long or short');
  const fee = notional * closeFeePpm / D < margin ? notional * closeFeePpm / D : margin;
  const available = margin - fee;
  const delta = side === 'long' ? mark - entry : entry - mark;
  let loss = 0n, winNet = 0n, liquidatable = false;
  if (delta < 0n) {
    const adverse = -delta;
    liquidatable = notional * adverse >= available * entry;
    loss = liquidatable ? available : (notional * adverse + entry - 1n) / entry;
  } else if (delta > 0n) {
    const u = A * delta - entry;
    if (u > 0n) {
      const d = A * entry, f = B * u + K * d;
      const gross = notional * 9n * u * u * B / (10n * d * f);
      const cap = margin * maxWinMultiple;
      const adjusted = gross < cap ? gross : cap;
      winNet = adjusted - adjusted * winFeePpm / D;
    }
  }
  return { fee, available, loss, winNet, payout: available - loss + winNet, liquidatable };
}

/** Estimated net result at a mark price, as a percentage of collateral. Null on unusable input. */
export function payoutPercent({ entry, mark, side, leverage }) {
  if (![entry, mark, leverage].every(value => typeof value === 'number' && Number.isFinite(value) && value > 0)
      || !Number.isInteger(leverage) || (side !== 'long' && side !== 'short')) return null;
  const margin = 10_000_000n;
  const quote = quotePosition({ margin, notional: margin * BigInt(leverage),
    entry: BigInt(Math.round(entry * PRICE_SCALE)), mark: BigInt(Math.round(mark * PRICE_SCALE)), side });
  return { percent: Number(quote.payout - margin) / Number(margin) * 100, liquidated: quote.liquidatable };
}

/** Adverse move, as a fraction of entry, at which the saved arithmetic liquidates. */
export function bustFraction(leverage, closeFeePpm = 20) {
  if (!Number.isInteger(leverage) || leverage <= 0) return null;
  return Math.max(0, 1 / leverage - closeFeePpm / 1e6);
}
