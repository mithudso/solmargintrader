/** Display-only adapter for soltui/live_score.py; shared fixture tests bind the rules. */
const HORIZONS = [1, 5, 10, 30];
const DIRECTIONS = { UP: 1, DOWN: -1, FLAT: 0 };
const finite = (n) => typeof n === 'number' && Number.isFinite(n);

export function aggregatePredictions(rows, now = Date.now() / 1000, { min_accuracy = 60, min_resolved = 20 } = {}) {
  const validPolicy = finite(min_accuracy) && min_accuracy >= 0 && min_accuracy <= 100 && Number.isInteger(min_resolved) && min_resolved >= 1;
  const strategies = [];
  const seen = new Set();
  let votes = 0;
  for (const row of rows ?? []) {
    if (!row || typeof row !== 'object') continue;
    if (typeof row.label !== 'string' || !row.label || seen.has(row.label)) continue;
    seen.add(row.label);
    if (!validPolicy || !finite(row.accuracy) || (row.accuracy < min_accuracy || row.accuracy > 100) || !finite(row.resolved) || row.resolved < min_resolved) continue;
    const directions = [];
    for (const h of HORIZONS) {
      const direction = Object.hasOwn(DIRECTIONS, row[`pred_${h}m`]) ? DIRECTIONS[row[`pred_${h}m`]] : undefined;
      const issued = row[`issued_${h}m`], expires = row[`expires_${h}m`];
      const accuracy = row[`acc_${h}m`], resolved = row[`resolved_${h}m`];
      if (!finite(accuracy) || accuracy < min_accuracy || accuracy > 100 || !Number.isInteger(resolved) || resolved < min_resolved) continue;
      if (direction === undefined || !finite(issued) || !finite(expires) || !(issued <= now && now < expires && expires > issued)) continue;
      directions.push(direction);
    }
    if (directions.length) {
      strategies.push(directions.reduce((a, b) => a + b, 0) / directions.length);
      votes += directions.length;
    }
  }
  const score = strategies.length ? Math.round(1000 * strategies.reduce((a, b) => a + b, 0) / strategies.length) / 10 : null;
  const label = score !== null && score >= 60 ? 'Strong Buy' : score !== null && score >= 20 ? 'Buy'
    : score !== null && score <= -60 ? 'Strong Sell' : score !== null && score <= -20 ? 'Sell' : 'Flat';
  return { score, label, color: ['Strong Buy', 'Buy'].includes(label) ? 'green' : ['Strong Sell', 'Sell'].includes(label) ? 'red' : 'gray',
    available: strategies.length > 0, strategies: strategies.length, votes, min_accuracy, min_resolved };
}

/** Explain unavailable agreement without turning stale or unqualified forecasts into votes. */
export function agreementUnavailableReason(snapshot, now = Date.now() / 1000) {
  if (!snapshot || !Array.isArray(snapshot.rows)) return 'Prediction data unavailable; open the workspace to check the native host.';
  if (!snapshot.rows.length) return 'No prediction history for this coin.';
  const policy = snapshot.voting ?? {};
  const minAccuracy = policy.min_accuracy ?? 60, minResolved = policy.min_resolved ?? 20;
  if (!finite(minAccuracy) || minAccuracy < 0 || minAccuracy > 100 || !Number.isInteger(minResolved) || minResolved < 1)
    return 'The prediction evidence policy is unavailable or invalid.';
  const eligible = snapshot.rows.some((row) => row && typeof row.label === 'string' && row.label &&
    finite(row.accuracy) && row.accuracy >= minAccuracy && row.accuracy <= 100 &&
    finite(row.resolved) && row.resolved >= minResolved && HORIZONS.some((h) => {
      const issued = row[`issued_${h}m`], expires = row[`expires_${h}m`];
      return Object.hasOwn(DIRECTIONS, row[`pred_${h}m`]) &&
        finite(row[`acc_${h}m`]) && row[`acc_${h}m`] >= minAccuracy && row[`acc_${h}m`] <= 100 &&
        Number.isInteger(row[`resolved_${h}m`]) && row[`resolved_${h}m`] >= minResolved &&
        finite(issued) && finite(expires) && issued <= now && expires > issued && expires <= now;
    }));
  return eligible ? 'Qualifying predictions have expired; no current vote is available.'
    : 'No current predictions meet the evidence and freshness requirements.';
}

export function scoreText(aggregate) {
  const score = aggregate?.score;
  return finite(score) ? `${score >= 0 ? '+' : ''}${score.toFixed(1)}` : '—';
}

/** One immutable observation per new source timestamp; never backfill or reorder a tick. */
export function appendScoreTick(history, { at, price, aggregate }, limit = 600) {
  if (!finite(at) || !finite(price) || price <= 0 || (history.length && at <= history.at(-1).x)) return history;
  return [...history, { x: at, y: price, score: finite(aggregate?.score) ? aggregate.score : null,
    color: aggregate?.color ?? 'gray', rating: aggregate?.label ?? 'Flat' }].slice(-limit);
}

export function scoreTickLayout(points, width = 720, slot = 56) {
  const left = 28, right = width - 28;
  const count = Math.max(1, Math.floor((right - left) / slot) + 1);
  const visible = points.slice(-count);
  return visible.map((p, i) => ({ ...p, plotX: right - (visible.length - 1 - i) * slot }));
}

export function renderScoreChart(points, { width = 720 } = {}) {
  const node = (tag, attrs = {}) => {
    const n = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, value] of Object.entries(attrs)) n.setAttribute(key, String(value));
    return n;
  };
  const visible = scoreTickLayout(points, width);
  const svg = node('svg', { viewBox: `0 0 ${width} 230`, role: 'img', 'aria-label': 'Live price with the aggregate prediction score observed at each tick' });
  if (!visible.length) return svg;
  const prices = visible.map((p) => p.y);
  let lo = Math.min(...prices), hi = Math.max(...prices);
  if (lo === hi) { lo -= Math.max(0.000001, Math.abs(lo) * 0.001); hi += Math.max(0.000001, Math.abs(hi) * 0.001); }
  const sy = (price) => 164 - (price - lo) / (hi - lo) * 140;
  const path = visible.map((p, i) => `${i ? 'L' : 'M'}${p.plotX},${sy(p.y)}`).join(' ');
  svg.append(node('path', { d: path, fill: 'none', stroke: 'var(--accent)', 'stroke-width': 2 }));
  for (const [value, y] of [[hi, 14], [lo, 181]]) {
    const label = node('text', { x: 8, y, class: 'axis' });
    label.textContent = `$${value.toLocaleString(undefined, { maximumFractionDigits: 8 })}`;
    svg.append(label);
  }
  for (const p of visible) {
    const group = node('g', { 'data-tick-time': p.x, 'data-score': p.score ?? '' });
    const color = p.color === 'green' ? 'var(--pos)' : p.color === 'red' ? 'var(--neg)' : 'var(--muted)';
    const title = node('title');
    title.textContent = `${new Date(p.x).toISOString()} · price ${p.y} · score ${scoreText({ score: p.score })} · ${p.rating}`;
    const score = node('text', { x: p.plotX, y: 205, 'text-anchor': 'middle', fill: color, class: 'score-tick' });
    score.textContent = scoreText({ score: p.score });
    const time = node('text', { x: p.plotX, y: 224, 'text-anchor': 'middle', class: 'axis' });
    time.textContent = new Date(p.x).toISOString().slice(11, 19);
    group.append(title, node('circle', { cx: p.plotX, cy: sy(p.y), r: 2, fill: 'var(--accent)' }), score, time);
    svg.append(group);
  }
  return svg;
}
