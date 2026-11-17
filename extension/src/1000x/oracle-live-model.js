/** Causal, prospective advisory only. No execution or historical warm start. */
export const LIVE_ORACLE = Object.freeze({ schema: 1, model: 'live-softmax-l2-v1', target: 'endpoint-exact-price-v1',
  horizons: Object.freeze([60, 300, 600, 900, 1200, 3600]), cadenceMs: 5000, graceMs: 2000,
  maxPending: 1500, maxHistory: 120, recent: 128, maxBytes: 2 * 1024 * 1024, eta: 0.025, l2: 0.001, bound: 8 });
const CLASSES = ['UP', 'DOWN', 'FLAT'];
const finite = x => typeof x === 'number' && Number.isFinite(x);
const clip = (x, n = 1) => Math.max(-n, Math.min(n, x));
const fail = () => { throw new Error('invalid_live_oracle_state'); };
const empty = () => ({ issued: 0, resolved: 0, expired: 0, capacityDrops: 0, counts: [0, 0, 0],
  candidate: { brier: 0, hits: 0 }, uniform: { brier: 0, hits: 0 }, frequency: { brier: 0, hits: 0 }, recent: [] });
const model = () => ({ weights: Array.from({ length: 3 }, () => Array(5).fill(0)), bias: [0, 0, 0], n: 0 });
/** Return false and count a rejected candidate without issuing or labelling it. */
export function admitLiveProbe(pendingCount, metrics) {
  if (!Number.isSafeInteger(pendingCount) || pendingCount < 0 || !metrics
    || !Number.isSafeInteger(metrics.capacityDrops) || metrics.capacityDrops < 0) fail();
  if (pendingCount >= LIVE_ORACLE.maxPending) { metrics.capacityDrops++; return false; }
  return true;
}

export function liveIdentity(identity) {
  if (!identity || typeof identity.market !== 'string' || !identity.market || identity.market.length > 128
    || typeof identity.source !== 'string' || !identity.source || identity.source.length > 512) throw new Error('live_oracle_source_unavailable');
  return JSON.stringify([LIVE_ORACLE.schema, LIVE_ORACLE.model, LIVE_ORACLE.target, identity.market, identity.source]);
}
export function newLiveState(identity) {
  return { schema: LIVE_ORACLE.schema, key: liveIdentity(identity), market: identity.market, source: identity.source,
    models: Object.fromEntries(LIVE_ORACLE.horizons.map(h => [h, model()])),
    metrics: Object.fromEntries(LIVE_ORACLE.horizons.map(h => [h, empty()])), pending: [], history: [],
    lastQuote: null, lastProbeBucket: null, lastProbeAtMs: null, revision: 0 };
}
function validVector(x) { return Array.isArray(x) && x.length === 5 && x.every(v => finite(v) && Math.abs(v) <= 1); }
export function liveProbabilities(m, x) {
  if (!validVector(x) || !Array.isArray(m?.weights) || m.weights.length !== 3 || !Array.isArray(m.bias) || m.bias.length !== 3
    || m.weights.some(row => !Array.isArray(row) || row.length !== 5 || row.some(v => !finite(v) || Math.abs(v) > LIVE_ORACLE.bound))
    || m.bias.some(v => !finite(v) || Math.abs(v) > LIVE_ORACLE.bound)) fail();
  const z = m.weights.map((w, c) => w.reduce((s, v, i) => s + v * x[i], m.bias[c]));
  const top = Math.max(...z), e = z.map(v => Math.exp(v - top)), sum = e.reduce((a, b) => a + b, 0);
  return e.map(v => v / sum);
}
function direction(p) { const max = Math.max(...p); return p.filter(v => v === max).length === 1 ? CLASSES[p.indexOf(max)] : 'FLAT'; }
function score(p, y) { return { brier: p.reduce((s, v, i) => s + (v - Number(i === y)) ** 2, 0), hit: Number(direction(p) === CLASSES[y]) }; }
function learn(m, x, y) {
  const p = liveProbabilities(m, x);
  return { weights: m.weights.map((row, c) => row.map((w, i) => clip(w - LIVE_ORACLE.eta * ((p[c] - Number(c === y)) * x[i] + LIVE_ORACLE.l2 * w), LIVE_ORACLE.bound))),
    bias: m.bias.map((b, c) => clip(b - LIVE_ORACLE.eta * (p[c] - Number(c === y)), LIVE_ORACLE.bound)), n: m.n + 1 };
}
function features(history) {
  const last = history.at(-1); if (!last || last.t - history[0].t < 30000) return null;
  const get = seconds => { for (let i = history.length - 1; i >= 0; i--) if (history[i].t <= last.t - seconds * 1000) return history[i]; return null; };
  const past = [5, 15, 30].map(get); if (past.some(v => !v)) return null;
  const prices = history.filter(v => v.t >= last.t - 30000).map(v => v.price), low = Math.min(...prices), high = Math.max(...prices);
  const volatility = prices.slice(1).reduce((s, p, i) => s + Math.abs(Math.log(p / prices[i])), 0);
  const x = [...past.map(v => clip(Math.log(last.price / v.price) * 100)), clip(volatility * 100), high === low ? 0 : clip(2 * (last.price - low) / (high - low) - 1)];
  return validVector(x) ? x : null;
}
function validate(state, key) {
  if (!state || state.key !== key || state.key !== liveIdentity({ market: state.market, source: state.source }) || state.schema !== LIVE_ORACLE.schema || !Array.isArray(state.pending)
    || state.pending.length > LIVE_ORACLE.maxPending || !Array.isArray(state.history) || state.history.length > LIVE_ORACLE.maxHistory
    || !Number.isSafeInteger(state.revision) || state.revision < 0
    || (state.lastProbeAtMs !== null && (!Number.isSafeInteger(state.lastProbeAtMs) || state.lastProbeAtMs < 0))) fail();
  const isProb = p => Array.isArray(p) && p.length === 3 && p.every(v => finite(v) && v >= 0 && v <= 1)
    && Math.abs(p.reduce((a, b) => a + b, 0) - 1) < 1e-9;
  const ids = new Set();
  const q = state.lastQuote;
  if ((q !== null && (!q || !finite(q.price) || q.price <= 0 || !finite(q.exchangeMs) || !finite(q.receivedMs)
    || q.exchangeMs < 0 || q.receivedMs < 0 || q.exchangeMs > q.receivedMs + 250))
    || (q === null && state.history.length !== 0)) fail();
  for (const f of state.pending) {
    if (!f || !LIVE_ORACLE.horizons.includes(f.horizon) || !Number.isSafeInteger(f.issuedAtMs)
      || f.issuedAtMs < 0 || f.targetMs !== f.issuedAtMs + f.horizon * 1000 || !finite(f.reference) || f.reference <= 0
      || f.id !== `${f.horizon}:${Math.floor(f.issuedAtMs / LIVE_ORACLE.cadenceMs)}` || ids.has(f.id)
      || !validVector(f.x) || !isProb(f.p) || !isProb(f.baseline)) fail();
    ids.add(f.id);
  }
  for (const [i, q] of state.history.entries()) if (!Number.isSafeInteger(q.t) || q.t < 0 || !finite(q.price) || q.price <= 0
    || (i && (q.t <= state.history[i - 1].t || q.t - state.history[i - 1].t > LIVE_ORACLE.graceMs))) fail();
  if (q && (!state.history.length || state.history.at(-1).t !== Math.floor(q.receivedMs / 1000) * 1000
    || state.history.at(-1).price !== q.price)) fail();
  for (const h of LIVE_ORACLE.horizons) {
    const m = state.models?.[h], s = state.metrics?.[h]; liveProbabilities(m, [0, 0, 0, 0, 0]);
    if (!Number.isSafeInteger(m.n) || m.n < 0 || !s || !Array.isArray(s.counts) || s.counts.length !== 3 || !Array.isArray(s.recent)
      || s.recent.length !== Math.min(s.resolved, LIVE_ORACLE.recent)
      || ![s.issued, s.resolved, s.expired, s.capacityDrops, ...s.counts].every(v => Number.isSafeInteger(v) && v >= 0)
      || s.resolved !== m.n || s.counts.reduce((a, b) => a + b, 0) !== s.resolved
      || s.issued !== s.resolved + s.expired + state.pending.filter(p => p.horizon === h).length) fail();
    for (const name of ['candidate', 'uniform', 'frequency']) if (!s[name] || !finite(s[name].brier) || s[name].brier < 0
      || !Number.isSafeInteger(s[name].hits) || s[name].hits < 0 || s[name].hits > s.resolved) fail();
    for (let i = 0; i < s.recent.length; i++) { const r = s.recent[i];
      if (!r || typeof r.id !== 'string' || !Number.isSafeInteger(r.ordinal) || r.ordinal !== s.resolved - s.recent.length + i + 1
        || (i && s.recent[i - 1].ordinal >= r.ordinal) || !Number.isSafeInteger(r.y) || r.y < 0 || r.y > 2
        || !isProb(r.p) || !isProb(r.baseline)) fail(); }
  }
  if (JSON.stringify(state).length * 2 > LIVE_ORACLE.maxBytes) fail();
  return state;
}
export function liveSnapshot(state, nowMs) {
  validate(state, state.key); const q = state.lastQuote;
  const fresh = q && nowMs >= q.receivedMs && nowMs - q.receivedMs <= LIVE_ORACLE.graceMs
    && nowMs - q.exchangeMs >= -250 && nowMs - q.exchangeMs <= LIVE_ORACLE.graceMs;
  const x = fresh ? features(state.history) : null;
  return { key: state.key, market: state.market, source: state.source, model: LIVE_ORACLE.model, target: LIVE_ORACLE.target,
    asOfMs: q?.receivedMs ?? null, status: !fresh ? 'stale' : !x ? 'warming' : 'learning',
    horizons: Object.fromEntries(LIVE_ORACLE.horizons.map(h => { const m = state.models[h], s = state.metrics[h], p = x ? liveProbabilities(m, x) : null;
      return [h, { scores: p ? { up: p[0], down: p[1], flat: p[2] } : null, direction: p ? direction(p) : 'FLAT',
        samples: m.n, issued: s.issued, resolved: s.resolved, expired: s.expired, capacityDrops: s.capacityDrops,
        pending: state.pending.filter(f => f.horizon === h).length, candidate: { ...s.candidate }, uniform: { ...s.uniform }, frequency: { ...s.frequency } }]; })) };
}
/** Only committed return values should be published. Unknown outcomes never train. */
export function transitionLive(previous, { identity, quote, nowMs }) {
  if (!Number.isSafeInteger(nowMs) || nowMs < 0) fail(); const key = liveIdentity(identity);
  const state = structuredClone(previous ? validate(previous, key) : newLiveState(identity));
  if (state.lastQuote && nowMs < state.lastQuote.receivedMs) fail();
  const valid = quote && finite(quote.price) && quote.price > 0 && finite(quote.exchangeMs) && finite(quote.receivedMs)
    && quote.exchangeMs >= 0 && quote.receivedMs >= 0 && quote.exchangeMs <= quote.receivedMs + 250 && quote.receivedMs <= nowMs
    && nowMs - quote.receivedMs <= LIVE_ORACLE.graceMs && nowMs - quote.exchangeMs >= -250
    && nowMs - quote.exchangeMs <= LIVE_ORACLE.graceMs && (!state.lastQuote || (quote.exchangeMs > state.lastQuote.exchangeMs && quote.receivedMs > state.lastQuote.receivedMs));
  let resolved = 0, expired = 0, issued = 0, changed = !previous; const pending = [];
  for (const f of state.pending) {
    const metric = state.metrics[f.horizon];
    if (valid && nowMs <= f.targetMs + LIVE_ORACLE.graceMs && quote.exchangeMs >= f.targetMs && quote.receivedMs >= f.targetMs && quote.exchangeMs <= f.targetMs + LIVE_ORACLE.graceMs && quote.receivedMs <= f.targetMs + LIVE_ORACLE.graceMs) {
      const y = quote.price > f.reference ? 0 : quote.price < f.reference ? 1 : 2;
      for (const [name, p] of [['candidate', f.p], ['uniform', [1 / 3, 1 / 3, 1 / 3]], ['frequency', f.baseline]]) {
        const s = score(p, y); metric[name].brier += s.brier; metric[name].hits += s.hit;
      }
      metric.resolved++; metric.counts[y]++; metric.recent.push({ id: f.id, ordinal: metric.resolved, y, p: f.p, baseline: f.baseline });
      metric.recent = metric.recent.slice(-LIVE_ORACLE.recent); state.models[f.horizon] = learn(state.models[f.horizon], f.x, y);
      resolved++; changed = true;
    } else if (nowMs > f.targetMs + LIVE_ORACLE.graceMs) { metric.expired++; expired++; changed = true; }
    else pending.push(f);
  }
  state.pending = pending;
  if (valid) {
    if (state.lastQuote && (quote.receivedMs - state.lastQuote.receivedMs > LIVE_ORACLE.graceMs || quote.exchangeMs - state.lastQuote.exchangeMs > LIVE_ORACLE.graceMs)) state.history = [];
    const t = Math.floor(quote.receivedMs / 1000) * 1000, row = { t, price: quote.price };
    if (state.history.at(-1)?.t === t) state.history[state.history.length - 1] = row; else state.history.push(row);
    state.history = state.history.slice(-LIVE_ORACLE.maxHistory);
    state.lastQuote = { price: quote.price, exchangeMs: quote.exchangeMs, receivedMs: quote.receivedMs }; changed = true;
    const x = features(state.history), bucket = Math.floor(nowMs / LIVE_ORACLE.cadenceMs);
    if (x && bucket !== state.lastProbeBucket && (state.lastProbeAtMs === null || nowMs - state.lastProbeAtMs >= LIVE_ORACLE.cadenceMs)) {
      state.lastProbeBucket = bucket; state.lastProbeAtMs = nowMs;
      for (const h of LIVE_ORACLE.horizons) {
        const metric = state.metrics[h]; if (!admitLiveProbe(state.pending.length, metric)) continue;
        const n = metric.resolved, baseline = n ? metric.counts.map(v => v / n) : [1 / 3, 1 / 3, 1 / 3];
        state.pending.push({ id: `${h}:${bucket}`, horizon: h, issuedAtMs: nowMs, targetMs: nowMs + h * 1000,
          reference: quote.price, x: [...x], p: liveProbabilities(state.models[h], x), baseline }); metric.issued++; issued++;
      }
    }
  }
  if (changed) state.revision++;
  validate(state, key); return { state, changed, snapshot: liveSnapshot(state, nowMs), resolved, expired, issued };
}
