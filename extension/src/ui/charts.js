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
