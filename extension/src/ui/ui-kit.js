/**
 * Shared helpers for the dashboard views: DOM building, number formatting,
 * tables, chips and a small SVG line chart.
 *
 * Every string that reaches the page goes through textContent or a DOM
 * attribute, never innerHTML. Token names, pool symbols, venue errors and
 * soltui output are third-party data, and these pages hold extension
 * privileges (KNOW-407): one missed escape would be XSS with real reach.
 */

export const send = (msg) => chrome.runtime.sendMessage(msg);

/**
 * Run an extension command and return its result, or throw with the
 * command's own error text. Commands answer `{ ok, result, ...result }`.
 */
export async function call(msg) {
  const res = await send(msg);
  if (!res?.ok) throw new Error(res?.error ?? 'the extension did not answer');
  return res.result;
}

/** Run one soltui command over the bridge; throws with soltui's message on refusal. */
export async function soltui(command, params = {}) {
  const res = await send({ type: 'soltuiCall', command, params });
  const env = res?.result;
  if (!res?.ok) throw new Error(res?.error ?? 'the extension did not answer');
  if (!env?.ok) throw new Error(env?.error?.message ?? 'soltui refused');
  return env.result;
}

/* ------------------------------------------------------------------ DOM -- */

// Element kinds are assigned (input.type = ...), never written as a `type:`
// key: test/surfaces.test.js scans UI scripts for that literal to find the
// messages they send.
export function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value == null || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = String(value);
    else if (key === 'dataset') Object.assign(node.dataset, value);
    else if (key.startsWith('on') && typeof value === 'function') node.addEventListener(key.slice(2), value);
    else if (key in node && key !== 'list') node[key] = value;
    else node.setAttribute(key, value === true ? '' : String(value));
  }
  for (const child of children.flat()) {
    if (child == null || child === false) continue;
    node.append(child instanceof Node ? child : String(child));
  }
  return node;
}

export const $ = (sel, root = document) => root.querySelector(sel);

/** Tell readers how to reach columns in a horizontally scrollable table. */
export function tableScrollHint() {
  return el('p', { class: 'note table-scroll-hint', text: 'Scroll horizontally to see all table columns and actions.' });
}

export function clear(node, ...children) {
  node.replaceChildren(...children.flat().filter((c) => c != null && c !== false));
  return node;
}

export const empty = (text) => el('p', { class: 'empty', text });
export const errorLine = (text) => el('p', { class: 'err', text });

/** An external link that cannot reach back into the extension page. */
export const extLink = (href, text) => (href && /^https:\/\//.test(href)
  ? el('a', { href, target: '_blank', rel: 'noopener noreferrer', text: text ?? '↗' })
  : null);

export function chip(text, kind = 'plain', title) {
  return el('span', { class: `chip ${kind}`, text, title });
}

export const SOURCE_CHIP = { modelled: 'modelled', backtest: 'backtest', quoted: 'quoted', live: 'live' };

/**
 * A table from column specs: { label, value(row) => string|Node, num?: true }.
 * An empty list renders the given sentence instead of a header with no rows.
 */
export function table(columns, rows, { emptyText = 'Nothing to show.', rowClass } = {}) {
  if (!rows?.length) return empty(emptyText);
  const head = el('tr', {}, columns.map((c) => el('th', { class: c.num ? 'num' : null, text: c.label })));
  const body = rows.map((r) => el('tr', { class: rowClass?.(r) ?? null }, columns.map((c) => {
    const v = c.value(r);
    return el('td', { class: c.num ? 'num' : null, ...(typeof c.sortValue === 'function' ? { dataset: { sortValue: String(c.sortValue(r)) } } : typeof v === 'number' ? { dataset: { sortValue: String(v) } } : {}) }, v instanceof Node ? v : (v == null || v === '' ? '—' : String(v)));
  })));
  return el('table', {}, el('thead', {}, head), el('tbody', {}, body));
}

/** Sort existing rows without rebuilding their buttons or losing event handlers. */
const tableSorts = new Map();
export function sortableTable(node) {
  if (node.dataset.sortable === 'true' || node.dataset.sortable === 'false') return;
  const headers = [...node.querySelectorAll('thead tr:first-child th')];
  if (!headers.length) return;
  node.dataset.sortable = 'true';
  const key = `${node.closest('[id]')?.id ?? ''}:${headers.map((h) => h.textContent).join('|')}`;
  const value = (cell) => {
    if (cell?.dataset.sortValue !== undefined) { const raw = Number(cell.dataset.sortValue); return cell.dataset.sortValue.trim() !== '' && Number.isFinite(raw) ? raw : null; }
    const text = (cell?.textContent ?? '').trim();
    if (!text || ['—', 'Unavailable', 'N/A'].includes(text)) return null;
    const normalized = text.replace(/−/g, '-').replace(/[+$€£]/g, '');
    const decimal = new Intl.NumberFormat().formatToParts(1.1).find(p => p.type === 'decimal')?.value ?? '.';
    const grouped = decimal === ',' ? normalized.replace(/\./g, '').replace(',', '.') : normalized.replace(/,/g, '');
    const numeric = grouped.match(/^(-?\d+(?:\.\d+)?)(%|[kKmMbB])?(?:$|\s| ·)/);
    if (numeric) return Number(numeric[1]) * ({ k: 1e3, m: 1e6, b: 1e9 }[numeric[2]?.toLowerCase()] ?? 1);
    return text;
  };
  function sort(index, direction) {
    const body = node.tBodies[0];
    if (!body) return;
    const rows = [...body.rows].map((row, position) => ({ row, position, v: value(row.cells[index]) }));
    rows.sort((a, b) => a.v === null ? (b.v === null ? a.position - b.position : 1) : b.v === null ? -1 :
      direction * (typeof a.v === 'number' && typeof b.v === 'number' ? a.v - b.v : String(a.v).localeCompare(String(b.v), undefined, { numeric: true })) || a.position - b.position);
    body.append(...rows.map((r) => r.row));
    headers.forEach((h, i) => h.setAttribute('aria-sort', i === index ? (direction === 1 ? 'ascending' : 'descending') : 'none'));
    tableSorts.set(key, { index, direction });
  }
  headers.forEach((header, index) => {
    const button = el('button', { class: 'column-sort', text: header.textContent, title: `Sort by ${header.textContent}` });
    button.type = 'button';
    button.onclick = () => { const previous = tableSorts.get(key); sort(index, previous?.index === index ? -previous.direction : 1); };
    header.replaceChildren(button);
  });
  const previous = tableSorts.get(key);
  if (previous) sort(previous.index, previous.direction);
}

export function observeSortableTables(root = document) {
  const scan = () => root.querySelectorAll('table').forEach(sortableTable);
  scan();
  const observer = new MutationObserver(scan);
  observer.observe(root, { childList: true, subtree: true });
  return () => observer.disconnect();
}

/* ------------------------------------------------------------- formats -- */

const finite = (n) => typeof n === 'number' && Number.isFinite(n);

export function usd(n, { sign = false, compact = false } = {}) {
  if (!finite(n)) return '—';
  const abs = Math.abs(n);
  let body;
  if (compact && abs >= 1e9) body = `${(abs / 1e9).toFixed(2)}B`;
  else if (compact && abs >= 1e6) body = `${(abs / 1e6).toFixed(2)}M`;
  else if (compact && abs >= 1e4) body = `${(abs / 1e3).toFixed(1)}k`;
  else body = abs.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: abs < 1 ? 4 : 2 });
  const s = n < 0 ? '−' : sign && n > 0 ? '+' : '';
  return `${s}$${body}`;
}

/** A number already in percent units (12.3 means 12.3%). */
export function pct(n, { sign = true, places = 1 } = {}) {
  if (!finite(n)) return '—';
  // A tiny non-zero figure would round to "−0.0%"; show enough digits to be honest.
  const digits = n !== 0 && Math.abs(n) < 0.5 * 10 ** -places ? Math.min(6, places + 3) : places;
  return `${n < 0 ? '−' : sign && n > 0 ? '+' : ''}${Math.abs(n).toFixed(digits)}%`;
}

export function amount(n) {
  if (!finite(n)) return '—';
  const abs = Math.abs(n);
  const digits = abs >= 1000 ? 2 : abs >= 1 ? 4 : abs >= 0.0001 ? 6 : 10;
  return n.toLocaleString(undefined, { maximumFractionDigits: digits });
}

export function ago(ms) {
  if (!finite(ms)) return 'never';
  const s = Math.round((Date.now() - ms) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}

export const signClass = (n) => (finite(n) ? (n > 0 ? 'pos' : n < 0 ? 'neg' : '') : '');

/** Write a USD figure into a node and colour it by sign. */
export function paint(node, n, opts) {
  node.textContent = usd(n, opts);
  node.classList.remove('pos', 'neg');
  const c = signClass(n);
  if (opts?.sign && c) node.classList.add(c);
}

/* ---------------------------------------------------------------- chart -- */

const SVG = 'http://www.w3.org/2000/svg';
const svgEl = (tag, attrs = {}) => {
  const n = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, String(v));
  return n;
};

/**
 * A line chart from [{x, y}] (x numeric, e.g. ms). Built with createElementNS,
 * so no string of it is ever parsed as markup. Carries a text alternative.
 */
export function lineChart(points, { width = 720, height = 180, label = 'chart', format = (v) => usd(v) } = {}) {
  const pts = points.filter((p) => finite(p.x) && finite(p.y));
  if (pts.length < 2) return empty('Not enough points to draw yet.');
  const pad = { l: 8, r: 8, t: 16, b: 16 };
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const p of pts) { x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y); }
  // Preserve source rows for tables/CSV. Only SVG complexity is reduced; each
  // bucket retains both extrema and original order, plus the global endpoints.
  let plotted = pts;
  if (pts.length > 2000) {
    const indices = new Set([0, pts.length - 1]), size = Math.ceil(pts.length / 500);
    for (let begin = 0; begin < pts.length; begin += size) {
      let lo = begin, hi = begin;
      for (let i = begin + 1; i < Math.min(pts.length, begin + size); i++) {
        if (pts[i].y < pts[lo].y) lo = i;
        if (pts[i].y > pts[hi].y) hi = i;
      }
      indices.add(lo); indices.add(hi);
    }
    plotted = [...indices].sort((a, b) => a - b).map(i => pts[i]);
  }
  if (y0 === y1) { y0 -= 1; y1 += 1; }
  const sx = (x) => pad.l + ((x - x0) / (x1 - x0 || 1)) * (width - pad.l - pad.r);
  const sy = (y) => height - pad.b - ((y - y0) / (y1 - y0)) * (height - pad.t - pad.b);
  const up = pts.at(-1).y >= pts[0].y;
  const svg = svgEl('svg', { viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-label': `${label}: ${pts.length} points, from ${format(pts[0].y)} to ${format(pts.at(-1).y)}` });
  if (y0 < 0 && y1 > 0) svg.append(svgEl('line', { x1: pad.l, x2: width - pad.r, y1: sy(0), y2: sy(0), class: 'grid-line', 'stroke-dasharray': '3 3' }));
  const d = plotted.map((p, i) => `${i ? 'L' : 'M'}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(' ');
  svg.append(svgEl('path', { d, fill: 'none', 'stroke-width': 2, stroke: up ? 'var(--pos)' : 'var(--neg)' }));
  const top = svgEl('text', { x: pad.l, y: 11, class: 'axis' });
  top.textContent = format(y1);
  const bottom = svgEl('text', { x: pad.l, y: height - 3, class: 'axis' });
  bottom.textContent = format(y0);
  svg.append(top, bottom);
  return el('div', { class: 'chart' }, svg);
}

/** Run an async view loader, showing its error in `target` instead of failing silently. */
export async function guard(target, fn) {
  try {
    return await fn();
  } catch (err) {
    if (target) clear(target, errorLine(err?.message ?? String(err)));
    return null;
  }
}
