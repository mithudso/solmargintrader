import { ORACLE } from './oracle-model.js';
import { TIMEFRAMES } from './timeframes.js';

const percent = value => typeof value === 'number' && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : '—';
const number = value => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(4) : '—';
const utc = seconds => new Date(seconds * 1000).toISOString().slice(11, 19) + ' UTC';

export function oracleView(root) {
  const node = (tag, text, className) => {
    const el = document.createElement(tag); if (text !== undefined) el.textContent = text;
    if (className) el.className = className; return el;
  };
  const heading = node('h2', 'Streaming Oracle · all six horizons');
  const overview = node('div', undefined, 'oracle-overview');
  const horizonTable = node('table'); horizonTable.id = 'oracle-horizons';
  const horizonCaption = node('caption', 'One shared minute feed · every horizon learns · counts: trained / resolved / pending · recent Brier: candidate / served / fixed0.5');
  const horizonHead = node('thead'), horizonHeadRow = node('tr');
  for (const text of ['Horizon', 'State', 'Served P(UP)', 'Evidence', 'Recent Brier ↓']) horizonHeadRow.append(node('th', text));
  horizonHead.append(horizonHeadRow); const horizonBody = node('tbody');
  horizonTable.append(horizonCaption, horizonHead, horizonBody); overview.append(horizonTable);
  const selected = node('h3', 'Selected rolling 10m detail'); selected.id = 'oracle-selected';
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
  const target = node('p', undefined, 'muted');
  const limits = node('p', 'Candidate P(UP) is an uncalibrated shadow estimate. Warm-up or recent underperformance serves fixed P(UP)=50% while candidate learning continues. Labels need every completed contiguous minute in their own horizon; unknown/expired labels are excluded. Chart selection changes detail only. Learning pauses when this window is hidden. No position, profit or trading instruction is produced.', 'muted');
  details.append(summary, table, target, limits);
  root.append(heading, overview, selected, status, prediction, counts, feedback, details);
  return view => {
    const horizon = view?.selectedHorizon || ORACLE.horizon, label = TIMEFRAMES.find(t => t.seconds === horizon)?.label || '10m';
    selected.textContent = `Selected rolling ${label} detail`; root.dataset.horizon = String(horizon);
    target.textContent = `UP means the completed close ${label} after the forecast cutoff is above its reference close. NON-UP includes DOWN and exact FLAT. Every horizon issues per minute; overlapping targets within and across models are not independent trials. This is separate from the DD/UU candle-pattern context.`;
    horizonBody.replaceChildren();
    for (const t of TIMEFRAMES) {
      const v = view?.horizons?.[t.seconds], saved = v?.sourceKey === v?.state?.key ? v?.state : undefined;
      const row = node('tr'); row.dataset.horizon = String(t.seconds); row.setAttribute('aria-current', String(t.seconds === horizon));
      row.dataset.state = v?.error ? 'error' : !v?.inputReady ? 'waiting' : v.mode;
      const last = saved?.pending.at(-1) ?? saved?.recent.at(-1), metric = v?.metrics?.recent;
      const stateLabel = v?.error ? `Unavailable · ${v.error.replaceAll('_', ' ')}` : view?.suspended ? 'Paused'
        : !saved ? 'Loading' : !v.inputReady ? 'Historical · feed unavailable' : !saved.issued ? 'Waiting for minute'
          : v.mode === 'active' ? 'Live candidate' : v.mode === 'baseline-performance' ? 'Fallback · shadow learns' : `Warm-up ${saved.model.n}/${ORACLE.minTrained}`;
      const probabilityLabel = last ? `${v.inputReady ? '' : 'Historical '}${percent(last.servedP)}` : '—';
      const evidence = saved ? `${saved.model.n} / ${saved.totals.n} / ${saved.pending.length}` : 'unavailable';
      const metricsLabel = metric ? ['candidate', 'served', 'baseline'].map(name => number(metric[name].brier)).join(' / ') : '—';
      if (saved) { row.dataset.trained = String(saved.model.n); row.dataset.resolved = String(saved.totals.n); row.dataset.pending = String(saved.pending.length); }
      for (const text of [t.label, stateLabel, probabilityLabel, evidence, metricsLabel]) row.append(node('td', text));
      horizonBody.append(row);
    }
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
