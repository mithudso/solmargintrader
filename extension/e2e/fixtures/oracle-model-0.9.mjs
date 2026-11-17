/** Prospective binary price-direction learner. No orders, hindsight forecasts or
 * historical label warm-start. Everything here is pure and clock-explicit. */
import { aggregateMinutes, reversalContext } from '../../src/1000x/reversal.js';
import { computeIndicators } from '../../src/1000x/indicators.js';

export const ORACLE = Object.freeze({ schema: 1, model: 'projected-logit-l2-v1', features: 'fixed-price-context-v1',
  target: 'closed-price-up-vs-nonup-v1', horizon: 600, cadence: 60, issueGraceMs: 15_000,
  labelGraceMs: 90_000, minTrained: 20, recent: 128, maxPending: 32, maxPartitions: 16,
  eta: 0.05, l2: 0.001, coefficientBound: 8, scoreEpsilon: 1e-9, driftMin: 30 });
export const FEATURE_NAMES = Object.freeze(['return1', 'return5', 'return10', 'emaGap', 'macdHistogram', 'bopSma3',
  'rsi', 'body', 'volatility10', 'reversalPair', ...[5, 10, 15, 20].flatMap(m => [`shape${m}`, `known${m}`, `position${m}`])]);
const finite = x => typeof x === 'number' && Number.isFinite(x);
const clip = (x, bound = 1) => Math.max(-bound, Math.min(bound, x));
const fail = () => { throw new Error('invalid_oracle_state'); };

export function probability(model, x) {
  if (!Array.isArray(x) || x.length !== FEATURE_NAMES.length || x.some(v => !finite(v) || Math.abs(v) > 1)
    || !Array.isArray(model.weights) || model.weights.length !== x.length || model.weights.some(v => !finite(v) || Math.abs(v) > ORACLE.coefficientBound)
    || !finite(model.bias) || Math.abs(model.bias) > ORACLE.coefficientBound) fail();
  const z = model.weights.reduce((sum, w, i) => sum + w * x[i], model.bias);
  return z >= 0 ? 1 / (1 + Math.exp(-z)) : Math.exp(z) / (1 + Math.exp(z));
}

/** Delayed SGD uses CURRENT weights, not the forecast's earlier probability. */
export function learn(model, x, y) {
  if ((y !== 0 && y !== 1) || !Number.isSafeInteger(model.n) || model.n < 0 || model.n >= Number.MAX_SAFE_INTEGER) fail();
  const error = probability(model, x) - y;
  return { weights: model.weights.map((w, i) => clip(w - ORACLE.eta * (error * x[i] + ORACLE.l2 * w), ORACLE.coefficientBound)),
    bias: clip(model.bias - ORACLE.eta * error, ORACLE.coefficientBound), n: model.n + 1 };
}

export function score(p, y) {
  if (!finite(p) || p < 0 || p > 1 || (y !== 0 && y !== 1)) fail();
  const bounded = Math.max(ORACLE.scoreEpsilon, Math.min(1 - ORACLE.scoreEpsilon, p));
  return { hit: Number((p > 0.5 ? 1 : 0) === y), brier: (p - y) ** 2,
    logLoss: -(y * Math.log(bounded) + (1 - y) * Math.log(1 - bounded)) };
}

export function oracleInput(snapshot, nowMs) {
  if (!Number.isSafeInteger(nowMs) || nowMs < 0) throw new Error('invalid_oracle_clock');
  const identity = snapshot?.sourceIdentity;
  if (!identity || snapshot.symbol !== identity.symbol || !/^[A-Z][A-Z0-9]{0,11}$/.test(identity.symbol)
    || !Number.isSafeInteger(identity.feedId) || identity.feedId <= 0
    || !/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(identity.marketAddress)
    || identity.stream !== 'fixed_rate@200ms' || identity.kind !== 'oracle-ohlc') throw new Error('oracle_source_unavailable');
  const source = `${identity.stream}:${identity.feedId}:${identity.marketAddress}:${identity.kind}`;
  const key = JSON.stringify([ORACLE.schema, ORACLE.model, ORACLE.features, ORACLE.target, ORACLE.horizon, identity.symbol, source]);
  const cutoff = Math.floor(nowMs / 60_000) * 60;
  const rows = aggregateMinutes(snapshot.minuteCandles ?? [], 1, cutoff);
  const quote = snapshot.quote;
  const fresh = finite(quote?.price) && quote.price > 0 && [quote.exchangeMs, quote.receivedMs].every(stamp =>
    finite(stamp) && nowMs - stamp >= -250 && nowMs - stamp <= 3000);
  const eligible = snapshot.status === 'live' && snapshot.minuteStatus === 'ready' && fresh && rows.at(-1)?.time + 60 === cutoff;
  return { key, source, market: identity.symbol, cutoff, rows, nowMs, eligible,
    reason: !fresh ? 'stale_oracle_quote' : snapshot.status !== 'live' ? 'feed_unavailable' : 'complete_minute_history_unavailable' };
}

/** Fixed, bounded transforms are frozen with each forecast; no scaler is fitted
 * to future samples. Price-return/gap scales are1% and are not tuned claims. */
export function makeFeatures(rows, cutoff) {
  const closed = aggregateMinutes(rows, 1, cutoff);
  let from = 0;
  for (let i = 1; i < closed.length; i++) if (closed[i].time - closed[i - 1].time !== 60) from = i;
  const tail = closed.slice(from);
  if (tail.length < 78 || tail.at(-1)?.time + 60 !== cutoff) return null;
  const m = computeIndicators(tail, { bop: { smoothing: 3 } }), last = tail.at(-1), price = last.close;
  const ret = lag => clip(Math.log(price / tail.at(-1 - lag).close) * 100);
  const context = reversalContext(tail, cutoff * 1000, true);
  const vol = tail.slice(-10).reduce((sum, row, i, chunk) => i ? sum + Math.abs(Math.log(row.close / chunk[i - 1].close)) * 100 / 9 : sum, 0);
  const x = [ret(1), ret(5), ret(10), clip((m.ema.latest - m.ema.slowLatest) / price * 100),
    clip(m.macd.histogramLatest / price * 100), clip(m.bop.latest), clip(m.rsi.latest / 50 - 1),
    last.high === last.low ? 0 : clip((last.close - last.open) / (last.high - last.low)), clip(vol),
    context.pair === 'DD' ? 1 : context.pair === 'UU' ? -1 : 0];
  for (const minutes of [5, 10, 15, 20]) {
    const f = context.frames[minutes], known = f.shape !== 'unknown';
    const sign = ['trend_up', 'bowl', 'v_rebound'].includes(f.shape) ? 1 : ['trend_down', 'cap', 'inverted_v'].includes(f.shape) ? -1 : 0;
    x.push(sign, Number(known), known ? clip(f.rangePosition * 2 - 1) : 0);
  }
  if (x.some(v => !finite(v))) throw new Error('invalid_oracle_features');
  return x;
}

const emptyScore = () => ({ hits: 0, brier: 0, logLoss: 0 });
export function newOracleState(input) {
  return { schema: ORACLE.schema, key: input.key, market: input.market, source: input.source,
    model: { weights: FEATURE_NAMES.map(() => 0), bias: 0, n: 0 }, pending: [], recent: [],
    totals: { n: 0, up: 0, down: 0, flat: 0, candidate: emptyScore(), baseline: emptyScore(), served: emptyScore() },
    issued: 0, expired: 0, lastIssuedCutoff: 0, lastClosedTarget: 0, updatedAtMs: null, historicalTrainingSamples: 0 };
}

function validForecast(f, key) {
  return f && f.id === `${key}:${f.cutoff}` && Number.isSafeInteger(f.cutoff) && f.cutoff % 60 === 0
    && f.target === f.cutoff + ORACLE.horizon && finite(f.reference) && f.reference > 0
    && Number.isSafeInteger(f.issuedAtMs) && f.issuedAtMs >= f.cutoff * 1000 && f.issuedAtMs <= f.cutoff * 1000 + ORACLE.issueGraceMs
    && Array.isArray(f.x) && f.x.length === FEATURE_NAMES.length && f.x.every(v => finite(v) && Math.abs(v) <= 1)
    && [f.p, f.servedP].every(p => finite(p) && p >= 0 && p <= 1) && f.baselineP === 0.5
    && ['active', 'baseline-warmup', 'baseline-performance'].includes(f.mode)
    && f.servedP === (f.mode === 'active' ? f.p : 0.5) && Number.isSafeInteger(f.modelSamples) && f.modelSamples >= 0;
}
export function validateOracleState(state, key) {
  if (!state || state.schema !== ORACLE.schema || state.key !== key || state.historicalTrainingSamples !== 0
    || !Array.isArray(state.pending) || state.pending.length > ORACLE.maxPending || !Array.isArray(state.recent) || state.recent.length > ORACLE.recent
    || ![state.model?.n, state.totals?.n, state.totals?.up, state.totals?.down, state.totals?.flat, state.issued, state.expired, state.lastIssuedCutoff, state.lastClosedTarget].every(n => Number.isSafeInteger(n) && n >= 0)
    || state.model.n !== state.totals.n || state.totals.up + state.totals.down + state.totals.flat !== state.totals.n
    || state.issued !== state.totals.n + state.expired + state.pending.length || state.recent.length !== Math.min(state.totals.n, ORACLE.recent)
    || (state.updatedAtMs !== null && (!Number.isSafeInteger(state.updatedAtMs) || state.updatedAtMs < 0))) fail();
  let binding;
  try { binding = JSON.parse(key); } catch { fail(); }
  if (!Array.isArray(binding) || binding.length !== 7 || binding[0] !== ORACLE.schema || binding[1] !== ORACLE.model
    || binding[2] !== ORACLE.features || binding[3] !== ORACLE.target || binding[4] !== ORACLE.horizon
    || binding[5] !== state.market || binding[6] !== state.source) fail();
  probability(state.model, FEATURE_NAMES.map(() => 0));
  for (const name of ['candidate', 'baseline', 'served']) {
    const s = state.totals[name];
    if (!s || !Number.isSafeInteger(s.hits) || s.hits < 0 || s.hits > state.totals.n || !finite(s.brier) || s.brier < 0
      || s.brier > state.totals.n + 1e-9 || !finite(s.logLoss) || s.logLoss < 0
      || s.logLoss > state.totals.n * (-Math.log(ORACLE.scoreEpsilon) + 1e-6) + 1e-9) fail();
  }
  const ids = new Set();
  for (const f of [...state.pending, ...state.recent]) {
    if (!validForecast(f, key) || ids.has(f.id) || f.cutoff > state.lastIssuedCutoff || f.modelSamples > state.model.n) fail();
    ids.add(f.id);
  }
  for (const f of state.recent) {
    if (!['UP', 'DOWN', 'FLAT'].includes(f.outcome) || f.y !== Number(f.outcome === 'UP') || !finite(f.close) || f.close <= 0
      || f.outcome !== (f.close > f.reference ? 'UP' : f.close < f.reference ? 'DOWN' : 'FLAT')
      || !Number.isSafeInteger(f.resolvedAtMs) || f.resolvedAtMs < f.target * 1000 || f.resolvedAtMs > f.target * 1000 + ORACLE.labelGraceMs) fail();
    for (const [name, p] of [['candidate', f.p], ['baseline', f.baselineP], ['served', f.servedP]]) {
      const actual = f.scores?.[name], expected = score(p, f.y);
      if (!actual || actual.hit !== expected.hit || actual.brier !== expected.brier || actual.logLoss !== expected.logLoss) fail();
    }
  }
  return state;
}

export function performanceFallback(state) {
  if (state.recent.length < ORACLE.driftMin) return false;
  const extra = state.recent.reduce((s, f) => ({ brier: s.brier + f.scores.candidate.brier - f.scores.baseline.brier,
    logLoss: s.logLoss + f.scores.candidate.logLoss - f.scores.baseline.logLoss }), { brier: 0, logLoss: 0 });
  return extra.brier / state.recent.length > 0.02 && extra.logLoss / state.recent.length > 0.05;
}
export function oracleMode(state) {
  return state.model.n < ORACLE.minTrained ? 'baseline-warmup' : performanceFallback(state) ? 'baseline-performance' : 'active';
}

/** Atomic-store reducer. Stored forecasts are scored first; current-weight SGD
 * then learns from exactly their frozen features and a genuine observed label. */
export function transitionOracle(previous, input) {
  const state = structuredClone(previous ? validateOracleState(previous, input.key) : newOracleState(input));
  let changed = !previous, resolved = 0, expired = 0, issued = false;
  const byTime = new Map(input.rows.map(row => [row.time, row]));
  const pending = [];
  for (const f of state.pending) {
    if (input.nowMs < f.target * 1000) { pending.push(f); continue; }
    if (input.nowMs > f.target * 1000 + ORACLE.labelGraceMs) {
      state.expired++; expired++; state.lastClosedTarget = Math.max(state.lastClosedTarget, f.target); changed = true; continue;
    }
    const observed = Array.from({ length: 10 }, (_, i) => byTime.get(f.cutoff + i * 60));
    if (!input.eligible || observed.some(row => !row)) { pending.push(f); continue; }
    const close = observed.at(-1).close, outcome = close > f.reference ? 'UP' : close < f.reference ? 'DOWN' : 'FLAT', y = outcome === 'UP' ? 1 : 0;
    const scores = { candidate: score(f.p, y), baseline: score(f.baselineP, y), served: score(f.servedP, y) };
    state.totals.n++; state.totals[outcome.toLowerCase()]++;
    for (const name of Object.keys(scores)) {
      const s = scores[name], total = state.totals[name]; total.hits += s.hit; total.brier += s.brier; total.logLoss += s.logLoss;
    }
    state.model = learn(state.model, f.x, y);
    state.recent.push({ ...f, outcome, y, close, scores, resolvedAtMs: input.nowMs });
    state.recent = state.recent.slice(-ORACLE.recent);
    state.lastClosedTarget = Math.max(state.lastClosedTarget, f.target); state.updatedAtMs = input.nowMs; resolved++; changed = true;
  }
  state.pending = pending;
  let status = input.eligible ? 'waiting-next-minute' : 'waiting-input';
  if (input.eligible && input.cutoff > state.lastIssuedCutoff && input.nowMs - input.cutoff * 1000 <= ORACLE.issueGraceMs
    && state.pending.length < ORACLE.maxPending) {
    const x = makeFeatures(input.rows, input.cutoff);
    if (x) {
      const p = probability(state.model, x), mode = oracleMode(state);
      state.pending.push({ id: `${input.key}:${input.cutoff}`, cutoff: input.cutoff, target: input.cutoff + ORACLE.horizon,
        issuedAtMs: input.nowMs, reference: byTime.get(input.cutoff - 60).close, x, p, baselineP: 0.5,
        servedP: mode === 'active' ? p : 0.5, mode, modelSamples: state.model.n });
      state.lastIssuedCutoff = input.cutoff; state.issued++; changed = true; issued = true;
    } else status = 'waiting-features';
  }
  validateOracleState(state, input.key);
  return { state, changed, feedback: { issued, resolved, expired, status } };
}

export function oracleMetrics(state) {
  const summarize = (totals, n) => Object.fromEntries(['candidate', 'baseline', 'served'].map(name => [name,
    { n, accuracy: n ? totals[name].hits / n : null, brier: n ? totals[name].brier / n : null, logLoss: n ? totals[name].logLoss / n : null }]));
  const recent = { candidate: emptyScore(), baseline: emptyScore(), served: emptyScore() };
  for (const f of state.recent) for (const name of Object.keys(recent)) {
    recent[name].hits += f.scores[name].hit; recent[name].brier += f.scores[name].brier; recent[name].logLoss += f.scores[name].logLoss;
  }
  return { cumulative: summarize(state.totals, state.totals.n), recent: summarize(recent, state.recent.length) };
}
