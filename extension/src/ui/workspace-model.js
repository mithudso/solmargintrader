import { spreadsheetText } from '../core/csv.js';

/** Registry-derived navigation and result adapters shared by the dashboard and tests. */
export const WORKSPACES = [
  { id: 'now', title: 'Now', detail: 'Processes, prices, current recommendations and saved results.', tools: ['prices.status', 'backtest.status', 'queue.progress', 'forwardtest.state', 'compound.autopilot_status', 'bots.schedule_status', 'portfolio.last'] },
  { id: 'signal', title: 'Live signals', detail: 'Compound metrics, live predictions, forward testing and unattended training.', tools: ['signals.check', 'prices.quote'], prefixes: ['compound'] },
  { id: 'forward', title: 'Forward testing', detail: 'Prospective paper trials, frozen costs, resolved evidence and session controls.', prefixes: ['forwardtest'] },
  { id: 'research', title: 'Backtesting', detail: 'Strategies, roster, CPCV backtests, sweep queue, cumulative results, analysis and replay.', prefixes: ['strategies', 'roster', 'backtest', 'queue', 'top5', 'analyze', 'cumulative', 'paper', 'live', 'signals', 'research', 'batch', 'paperexperiment'] },
  { id: 'bots', title: 'Bot monitor', detail: 'Grid, DCA, triangle simulations, coin suitability, optimization and the price recorder.', prefixes: ['bots', 'prices'] },
  { id: 'experiments', title: 'Experiments', detail: 'Search specifications, preview, worker controls, candidates, heatmaps, CSV import and comparisons.', prefixes: ['experiments'] },
  { id: 'money', title: 'Money', detail: 'Wallets, P&L, Coinbase and Jupiter. Manual order commands can spend real funds.', prefixes: ['portfolio', 'wallet', 'pnl', 'coinbase', 'jupiter'] },
  { id: 'library', title: 'Library', detail: 'Search, read and edit catalogued documents. Research evidence stays protected.', prefixes: ['docs'] },
  { id: 'settings', title: 'TUI settings', detail: 'Shared research settings, dates, fees and public wallet addresses.', prefixes: ['settings'] },
  { id: 'archive', title: 'Archive', detail: 'Historical Aero LP records. The discontinued service stays disabled.', prefixes: ['liquidity'] },
  { id: 'all', title: 'All tools', detail: 'Every command in the installed SolTUI registry, including newly added tools.' },
];

export function workspaceFor(name) {
  const prefix = name.split('.')[0];
  return WORKSPACES.find((w) => w.prefixes?.includes(prefix))?.id ?? 'all';
}

export function filterCommands(commands, workspace = 'all', query = '') {
  const spec = WORKSPACES.find((w) => w.id === workspace);
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return commands.filter((c) => (workspace === 'all' || workspaceFor(c.name) === workspace || spec?.tools?.includes(c.name))
    && words.every((q) => `${c.name} ${c.describe}`.toLowerCase().includes(q)));
}

export function cellText(value) {
  if (value === null || value === undefined) return '';
  return typeof value === 'object' ? JSON.stringify(value) : String(value);
}

export function columnsFor(rows) {
  return [...new Set(rows.flatMap((r) => Object.keys(r)))];
}

export function rowsToCsv(rows) {
  const columns = columnsFor(rows);
  const quote = (v) => {
    const s = spreadsheetText(typeof v === 'object' ? cellText(v) : v);
    return `"${s.replaceAll('"', '""')}"`;
  };
  return [columns.map(quote).join(','), ...rows.map((r) => columns.map((c) => quote(r[c])).join(','))].join('\r\n');
}

/** Find structured tables without conflating paper and real-money sources. */
export function resultTables(value, path = 'result', depth = 0) {
  if (depth > 8 || value === null || typeof value !== 'object') return [];
  if (Array.isArray(value)) {
    if (!value.length) return [];
    const rows = value.map((r) => r !== null && typeof r === 'object' && !Array.isArray(r) ? r : { value: r });
    const nested = value.flatMap((r, i) => resultTables(r, `${path}[${i}]`, depth + 1));
    return [{ path, rows }, ...nested];
  }
  const entries = Object.entries(value);
  const mapped = entries.length && entries.every(([, v]) => v !== null && typeof v === 'object' && !Array.isArray(v))
    ? [{ path, rows: entries.map(([key, v]) => {
      if (!Object.hasOwn(v, 'key')) return { key, ...v };
      let identity = 'dictionaryKey';
      while (Object.hasOwn(v, identity)) identity = '_' + identity;
      return { [identity]: key, ...v };
    }) }] : [];
  return [...mapped, ...entries.flatMap(([k, v]) => resultTables(v, `${path}.${k}`, depth + 1))];
}

/** Only registry-declared fields can be copied; confirmation is always a new decision. */
export function valuesFromRow(command, row) {
  return Object.fromEntries((command.params ?? []).filter((p) => p.name !== 'confirm' && p.name !== 'skip_confirm'
    && Object.hasOwn(row, p.name)).map((p) => [p.name, p.type === 'json' ? JSON.stringify(row[p.name], null, 2) : row[p.name]]));
}

/** Explicit source times only: never turn a missing price or time into a zero. */
export function seriesFromRows(rows) {
  const timeKeys = ['tsMs', 'timestamp', 'ts', 'time', 'date', 't'];
  const valueKeys = ['equityUsd', 'equity', 'close', 'price', 'mid', 'net_pct'];
  const points = [];
  for (const row of rows) {
    const tk = timeKeys.find((k) => row[k] != null);
    const vk = valueKeys.find((k) => typeof row[k] === 'number' && Number.isFinite(row[k]));
    if (!tk || !vk) continue;
    const t = row[tk];
    const x = typeof t === 'number' ? (tk === 'tsMs' || t > 1e12 ? t : t * 1000) : Date.parse(t);
    if (Number.isFinite(x)) points.push({ x, y: row[vk] });
  }
  return [...new Map(points.map((p) => [p.x, p])).values()].sort((a, b) => a.x - b.x);
}
