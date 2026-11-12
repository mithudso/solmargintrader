import { aggregatePredictions } from './live-score.js';
/** Pure presentation contracts. No market assumptions or execution decisions live here. */
export const DESK_PAGES = new Set(['signal', 'research', 'forward', 'bots']);
export const DESK_READS = {
  research: ['settings.get', 'roster.list', 'backtest.status', 'backtest.results', 'cumulative.summary'],
  forward: ['forwardtest.state', 'forwardtest.status'],
  bots: ['prices.status', 'bots.overview', 'backtest.status', 'forwardtest.state',
    'compound.unattended_status', 'compound.autopilot_status', 'bots.schedule_status'],
};
export function commandBlock(command) {
  return command?.name?.startsWith('liquidity.') && command.read_only !== true
    ? 'Archived by the owner. Liquidity controls remain unavailable.' : null;
}
export const finite = (n) => typeof n === 'number' && Number.isFinite(n);
export const numberText = (n, digits = 2) => finite(n) ? n.toLocaleString(undefined, { maximumFractionDigits: digits }) : 'Unavailable';
export const percentText = (fraction) => finite(fraction) ? `${numberText(100 * fraction)}%` : 'Unavailable';
export function comparisonKey(context) {
  if (!context || !['asset', 'interval', 'start', 'end'].every(k => typeof context[k] === 'string' && context[k].trim()) || !finite(context.capital) || context.capital <= 0 || !Number.isInteger(context.fill_delay) || context.fill_delay < 0 || !context.execution || typeof context.execution !== 'object' || !Object.keys(context.execution).length || !context.cpcv || !Number.isInteger(context.cpcv.cpcv_groups) || !Number.isInteger(context.cpcv.cpcv_k) || context.cpcv.cpcv_groups < 2 || context.cpcv.cpcv_k < 1 || context.cpcv.cpcv_k >= context.cpcv.cpcv_groups) return null;
  if (!context?.data_sha256 || !context?.strategy_revision || !context?.execution || !context?.cpcv) return null;
  // Strategy membership may differ: data, costs and the evaluation contract may not.
  const canonical = (v) => Array.isArray(v) ? v.map(canonical) : v && typeof v === 'object'
    ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, canonical(v[k])])) : v;
  return JSON.stringify(canonical(Object.fromEntries(['asset', 'interval', 'start', 'end', 'capital', 'fill_delay',
    'data_sha256', 'strategy_revision', 'execution', 'cpcv'].map((k) => [k, context[k]]))));
}
export function comparisonStatus(runs) {
  if (runs.length < 2) return 'Select at least two saved runs to compare.';
  const keys = runs.map((r) => comparisonKey(r.context));
  if (keys.some((k) => k === null) || new Set(keys).size !== 1) return 'Incompatible evidence: data, code, dates, costs or evaluation settings differ. Inspect separately; no combined ranking.';
  if (runs.some((r) => r.cancelled || r.error)) return 'Partial evidence: a selected run was canceled. Completed rows remain inspectable; no combined ranking.';
  return 'Matched dataset, code, interval, capital, CPCV geometry and cost scenario. Compare the recorded summaries below.';
}
export function runFromEnvelope(env) {
  if (!env?.ok || !['backtest.run', 'backtest.results'].includes(env.command)) return null;
  const val = env.result;
  if (val?.context?.schema !== 1 || typeof val.context.id !== 'string' || !Array.isArray(val.rows)) return null;
  const record = v => v && typeof v === 'object' && !Array.isArray(v);
  if (!val.rows.every(record) || (val.skipped !== undefined && (!Array.isArray(val.skipped) || !val.skipped.every(record)))) return null;
  const rowKeys = ['label', 'family', 'median_sharpe', 'iqr', 'frac_positive', 'median_return', 'trades', 'evaluable', 'reason'];
  return { id: val.context.id, context: structuredClone(val.context), cancelled: val.cancelled === true, error: val.error ?? null,
    rows: val.rows.slice(0, 1000).map((r) => Object.fromEntries(rowKeys.filter((k) => Object.hasOwn(r, k)).map((k) => [k, r[k]]))),
    skipped: (val.skipped ?? []).map((r) => ({ label: r.label, reason: r.reason })), message: val.message ?? '' };
}
export function handoffValues(run, row) {
  if (!run?.context?.entries?.some((e) => e.label === row?.label) || run.cancelled || run.error || !comparisonKey(run.context)) return null;
  return { snapshot: JSON.stringify(run.context, null, 2), source_label: row.label,
    horizons: '[5]', optimize: 'false' };
}
export function forwardColumns(row) {
  // Saved directional hits are separate from paper profits and the confidence gate.
  return { label: row.label ?? row.name ?? row.id ?? 'Unnamed trial',
    horizon: row.minutes ?? row.horizon ?? 'Unavailable', resolved: row.resolved ?? null,
    accuracy: row.accuracy ?? null, pending: row.pending ?? null, net: row.net_pct ?? null };
}

export function eligibilityReason(row, policy, now = Date.now() / 1000) {
  if (aggregatePredictions([row], now, policy).available) return 'Included';
  const floor = policy?.min_accuracy ?? 60, samples = policy?.min_resolved ?? 20;
  if (!finite(row?.accuracy) || row.accuracy > 100) return 'Excluded · strategy accuracy unavailable';
  if (row.accuracy < floor) return `Excluded · strategy accuracy below ${floor}%`;
  if (!finite(row.resolved) || row.resolved < samples) return `Excluded · strategy record below ${samples} resolved`;
  return 'Excluded · no current horizon meets expiry, accuracy and sample floors';
}
