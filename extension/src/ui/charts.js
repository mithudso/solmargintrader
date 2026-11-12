/**
 * Charts drawn with TradingView Lightweight Charts, the one vendored runtime
 * library (extension/vendor/lightweight-charts/, Apache-2.0, pinned 5.2.1).
 *
 * The library is imported lazily, on first draw, so node tests and the service
 * worker never load it, and a missing or broken copy degrades to the caller's
 * SVG fallback instead of a blank panel. MV3 forbids remotely hosted code, so
 * the file is local and is never fetched from a CDN.
 *
 * The attribution logo stays on: the library's licence requires the
 * TradingView notice and a link, and `attributionLogo` provides the link.
 */

const LIB_PATH = '../../vendor/lightweight-charts/lightweight-charts.standalone.production.mjs';

let libPromise = null;

function loadLibrary() {
  // A failed import is not cached: a transient load error should not disable
  // charts until the page reloads.
  libPromise ??= import(LIB_PATH).catch((err) => {
    libPromise = null;
    throw err;
  });
  return libPromise;
}

/**
 * Equity points ({tsMs, equityUsd}) → Lightweight Charts line data.
 *
 * The library needs strictly ascending integer-second times. Several round
 * trips can close within one second, and the curve's meaning at that second is
 * the last equity reached, so later points replace earlier ones. Non-finite
 * values are dropped rather than drawn as zero, which would invent a crash.
 */
export function toLineData(points) {
  const bySecond = new Map();
  for (const p of points ?? []) {
    // typeof first: Number(null) and Number('') are 0, which would plot a fake
    // 1970 point or a fake $0 equity.
    if (typeof p?.tsMs !== 'number' || typeof p?.equityUsd !== 'number') continue;
    if (!Number.isFinite(p.tsMs) || !Number.isFinite(p.equityUsd)) continue;
    bySecond.set(Math.floor(p.tsMs / 1000), p.equityUsd);
  }
  return [...bySecond.entries()].sort((a, b) => a[0] - b[0]).map(([time, value]) => ({ time, value }));
}

const charts = new WeakMap();
// Every render or dispose bumps the element's token. A draw that awaited the
// library checks it afterwards, so a slower, older draw never overwrites a
// newer render (renderPnl runs on every refresh and does not await).
const tokens = new WeakMap();
const bump = (el) => {
  const next = (tokens.get(el) ?? 0) + 1;
  tokens.set(el, next);
  return next;
};

/** Remove a chart drawn into `el`, if any, before its content is replaced. */
export function disposeChart(el) {
  if (!el) return;
  bump(el);
  const entry = charts.get(el);
  if (!entry) return;
  try {
    entry.chart.remove();
  } catch {
    // Already detached with the element; nothing left to release.
  }
  charts.delete(el);
}

/**
 * Draw (or update) an equity line in `el`. Returns 'lightweight-charts' when
 * the library drew it, 'fallback' when `fallbackHtml()` was used instead, and
 * 'stale' when a newer render or dispose superseded this one mid-load.
 * `loadLib` exists so node tests can stand in for the browser-only library.
 *
 * `label` becomes the element's accessible name and a visible caption, so the
 * numbers stay reachable without reading the canvas.
 */
export async function renderEquityChart(el, points, { label, fallbackHtml, loadLib = loadLibrary }) {
  const data = toLineData(points);
  if (data.length < 2) {
    disposeChart(el);
    el.innerHTML = fallbackHtml();
    return 'fallback';
  }
  const token = bump(el);
  let lib;
  try {
    lib = await loadLib();
  } catch {
    if (tokens.get(el) !== token) return 'stale';
    disposeChart(el);
    el.innerHTML = fallbackHtml();
    return 'fallback';
  }
  if (tokens.get(el) !== token) return 'stale';
  const rising = data.at(-1).value >= data[0].value;
  const color = rising ? '#15803d' : '#b91c1c';

  let entry = charts.get(el);
  if (!entry) {
    el.innerHTML = '';
    const host = document.createElement('div');
    host.style.height = '200px';
    host.style.width = '100%';
    const caption = document.createElement('p');
    caption.className = 'note';
    el.append(host, caption);
    const chart = lib.createChart(host, {
      autoSize: true,
      layout: { attributionLogo: true },
      rightPriceScale: { borderVisible: false },
      timeScale: { timeVisible: true, secondsVisible: false, borderVisible: false },
      localization: { priceFormatter: (v) => `${v < 0 ? '−' : ''}$${Math.abs(v).toFixed(2)}` },
    });
    const series = chart.addSeries(lib.LineSeries, { lineWidth: 2, priceLineVisible: false });
    entry = { chart, series, caption };
    charts.set(el, entry);
  }
  entry.series.applyOptions({ color });
  entry.series.setData(data);
  entry.chart.timeScale().fitContent();
  el.setAttribute('role', 'img');
  el.setAttribute('aria-label', label);
  entry.caption.textContent = label;
  return 'lightweight-charts';
}

/** Merge only real, agreeing candles. An unavailable feature stays unplotted. */
export function strategyChartData(explanations) {
  const candles = new Map(), conflicting = new Set(), series = [], markers = [], missing = [];
  for (const explanation of explanations ?? []) {
    const c = explanation?.chart;
    if (!c) continue;
    for (const p of c.candles ?? []) {
      if (!['time', 'open', 'high', 'low', 'close'].every(k => typeof p[k] === 'number' && Number.isFinite(p[k])) || p.low > Math.min(p.open, p.close) || p.high < Math.max(p.open, p.close)) continue;
      const prior = candles.get(p.time);
      if (prior && ['open', 'high', 'low', 'close'].some(k => prior[k] !== p[k])) conflicting.add(p.time);
      else candles.set(p.time, { time: p.time, open: p.open, high: p.high, low: p.low, close: p.close });
    }
    for (const s of c.series ?? []) series.push({ ...s, name: `${explanation.label} · ${s.name}` });
    for (const m of c.markers ?? []) markers.push({ ...m, text: `${explanation.label} · ${m.text}` });
    missing.push(...(c.missing ?? []).map(value => `${explanation.label}: ${value}`));
  }
  for (const time of conflicting) candles.delete(time);
  if (conflicting.size) missing.push('Conflicting saved candles were omitted.');
  const data = [...candles.values()].sort((a, b) => a.time - b.time);
  return { candles: data, series: series.map(s => ({ ...s, data: (s.data ?? []).filter(p => candles.has(p.time) && typeof p.value === 'number' && Number.isFinite(p.value)).sort((a, b) => a.time - b.time) })),
    markers: markers.filter(m => candles.has(m.time)).sort((a, b) => a.time - b.time), missing };
}

export async function renderStrategyChart(el, explanations, { asset, follow = true, loadLib = loadLibrary } = {}) {
  const data = strategyChartData(explanations), token = bump(el);
  if (!data.candles.length) { disposeChart(el); el.textContent = 'Original closed candles unavailable.'; return 'unavailable'; }
  const lib = await loadLib();
  if (tokens.get(el) !== token) return 'stale';
  const fingerprint = JSON.stringify(data);
  let entry = charts.get(el);
  if (entry?.fingerprint === fingerprint) { if (follow) entry.chart.timeScale().scrollToRealTime(); return 'lightweight-charts'; }
  const priorRange = !follow ? entry?.chart.timeScale().getVisibleRange() : null;
  if (entry) { entry.chart.remove(); charts.delete(el); }
  el.replaceChildren();
  const host = document.createElement('div'); host.style.height = '400px'; host.style.width = '100%';
  const caption = document.createElement('p'); caption.className = 'note';
  caption.textContent = `${asset} · saved Coinbase 1m candles · ${data.markers.length} forecast markers${data.missing.length ? ' · ' + data.missing.join(' · ') : ''}`;
  el.append(host, caption);
  const style = getComputedStyle(el);
  const chart = lib.createChart(host, { autoSize: true, layout: { attributionLogo: true,
    background: { color: style.getPropertyValue('--surface').trim() || '#ffffff' }, textColor: style.getPropertyValue('--fg').trim() || '#0f172a' },
    rightPriceScale: { borderVisible: false }, timeScale: { timeVisible: true, secondsVisible: false },
    localization: { timeFormatter: time => new Date(time * 1000).toISOString().slice(11, 16) + ' UTC' } });
  charts.set(el, { chart, caption, fingerprint: null });
  try {
  const candle = chart.addSeries(lib.CandlestickSeries, { upColor: '#239978', downColor: '#d05d63', borderVisible: false, wickUpColor: '#239978', wickDownColor: '#d05d63' });
  candle.setData(data.candles);
  const colors = ['#d8a43b', '#759bdf', '#ba89d2', '#e47d52'];
  data.series.forEach((s, i) => { const line = chart.addSeries(lib.LineSeries, { color: colors[i % colors.length], lineWidth: 2, title: s.name, priceLineVisible: false, lastValueVisible: false }); line.setData(s.data); });
  lib.createSeriesMarkers(candle, data.markers.map(m => ({ time: m.time, position: m.direction === 'UP' ? 'belowBar' : 'aboveBar',
    shape: m.direction === 'UP' ? 'arrowUp' : m.direction === 'DOWN' ? 'arrowDown' : 'circle', color: m.direction === 'UP' ? '#239978' : m.direction === 'DOWN' ? '#d05d63' : '#82998f', text: m.text })));
  if (priorRange) chart.timeScale().setVisibleRange(priorRange); else chart.timeScale().fitContent();
  } catch (error) { disposeChart(el); throw error; }
  charts.set(el, { chart, caption, fingerprint }); el.setAttribute('role', 'img'); el.setAttribute('aria-label', caption.textContent);
  return 'lightweight-charts';
}
