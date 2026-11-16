import { ORACLE } from './oracle-model.js';

const percent = value => typeof value === 'number' && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : '—';
const number = value => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(4) : '—';
const utc = seconds => new Date(seconds * 1000).toISOString().slice(11, 19) + ' UTC';

export function oracleView(root) {
  const node = (tag, text, className) => {
    const el = document.createElement(tag); if (text !== undefined) el.textContent = text;
    if (className) el.className = className; return el;
  };
  const heading = node('h2', 'Streaming Oracle · rolling 10m');
  const status = node('p', 'Waiting for a fresh completed one-minute cutoff'); status.id = 'oracle-status'; status.setAttribute('role', 'status');
  const prediction = node('p', 'P(UP) unavailable until a prospective forecast is stored'); prediction.id = 'oracle-prediction';
  const counts = node('p', 'Learner sample counts unavailable until local state loads'); counts.id = 'oracle-counts';
  const feedback = node('p', 'No labels resolved. Only genuine completed outcomes can teach the model.', 'muted'); feedback.id = 'oracle-feedback';
  const details = node('details');
  const summary = node('summary', 'Candidate, served and fixed-baseline metrics');
  const table = node('table'); table.id = 'oracle-metrics';
  const caption = node('caption', 'Prospective binary metrics · recent ≤128 / cumulative · no historical label training');
  const head = node('thead'), headRow = node('tr');
  for (const text of ['Cohort / predictor', 'n', 'Accuracy', 'Brier ↓', 'Log loss ↓']) headRow.append(node('th', text));
  head.append(headRow); const body = node('tbody'); table.append(caption, head, body);
  const target = node('p', 'UP means the completed close 10 minutes after the forecast cutoff is above its reference close. NON-UP includes DOWN and exact FLAT. Forecasts issue per minute; overlapping targets are not independent trials. This is separate from the DD/UU candle-pattern context.', 'muted');
  const limits = node('p', 'Candidate P(UP) is an uncalibrated shadow estimate. Warm-up or recent underperformance serves fixed P(UP)=50% while candidate learning continues. Labels need all ten completed contiguous minutes; unknown/expired labels are excluded. Learning pauses when this window is hidden. No position, profit or trading instruction is produced.', 'muted');
  details.append(summary, table, target, limits);
  root.append(heading, status, prediction, counts, feedback, details);
  return view => {
    // Historical evidence is visible only after this session has loaded and
    // verified the exact source partition. Unbound or invalid sessions clear it.
    const state = view?.sourceKey === view?.state?.key ? view?.state : undefined;
    root.dataset.state = view?.error ? 'error' : !view?.inputReady ? 'waiting' : view?.mode || 'waiting';
    const messages = { active: 'Online candidate active · shadow price-direction forecast', 'baseline-warmup': `Fixed baseline served · model warm-up (<${ORACLE.minTrained} resolved)`,
      'baseline-performance': 'Fixed baseline served · heuristic recent underperformance; shadow learning continues' };
    status.textContent = view?.error ? `Learning unavailable · ${view.error.replaceAll('_', ' ')}; chart remains read only`
      : view?.suspended ? view.reason === 'invalid_analytics' ? 'Learning paused · invalid candle or indicator data' : 'Learning paused · feed restarting or window hidden'
      : !view?.inputReady ? 'Learning waits for fresh public data and complete one-minute history'
      : view.feedback?.status === 'waiting-features' ? 'Feature warm-up · need 78 contiguous completed one-minute candles'
      : state?.issued === 0 ? 'Waiting for next fresh completed minute · untrained model; no issued forecast yet'
      : messages[view.mode] || 'Waiting for the next fresh completed minute';
    if (!state) {
      counts.textContent = 'Learner sample counts unavailable until local state loads';
      counts.removeAttribute('data-trained'); counts.removeAttribute('data-resolved');
      prediction.textContent = 'P(UP) unavailable until a prospective forecast is stored';
      feedback.textContent = 'Stored feedback is unavailable for this feed session. Learning waits for verified fresh input.';
      body.replaceChildren(); return;
    }
    const last = state.pending.at(-1) ?? state.recent.at(-1);
    prediction.textContent = last ? `${view.inputReady ? 'Stored' : 'Historical stored · current feed unavailable ·'} ${last.mode === 'active' ? 'candidate' : 'baseline'} P(UP) ${percent(last.servedP)} · shadow candidate ${percent(last.p)} · NON-UP ${percent(1 - last.servedP)} · cutoff ${utc(last.cutoff)} → ${utc(last.target)} · ${last.outcome ? `resolved ${last.outcome}` : last.target * 1000 > Date.now() ? 'pending outcome' : 'matured / waiting for validated label'}`
      : 'No issued forecast yet · waiting for a fresh minute boundary; no backfilled predictions';
    counts.textContent = `Trained ${state.model.n} · resolved ${state.totals.n} · pending ${state.pending.length} · expired ${state.expired} · UP ${state.totals.up} / DOWN ${state.totals.down} / FLAT ${state.totals.flat}`;
    counts.dataset.trained = String(state.model.n); counts.dataset.resolved = String(state.totals.n);
    feedback.textContent = state.updatedAtMs ? `Last genuine feedback ${utc(state.updatedAtMs / 1000)} · model updated on stored features; issued probabilities stay unchanged. Historical label training: 0.`
      : 'No genuine outcome resolved yet. Baseline and candidate forecasts collect labels together. Historical label training: 0.';
    body.replaceChildren();
    for (const cohort of ['recent', 'cumulative']) for (const name of ['candidate', 'served', 'baseline']) {
      const metric = view.metrics[cohort][name], row = node('tr'); row.dataset.cohort = cohort; row.dataset.predictor = name;
      for (const text of [`${cohort} / ${name === 'candidate' ? 'candidate shadow' : name === 'baseline' ? 'fixed 0.5' : 'actually served'}`, String(metric.n), percent(metric.accuracy), number(metric.brier), number(metric.logLoss)]) row.append(node('td', text));
      body.append(row);
    }
  };
}
