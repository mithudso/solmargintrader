import { JupiterFeed, TIMEFRAMES } from './feed.js';
import { DEFAULT_INDICATORS, validateIndicatorConfig } from './indicators.js';
import { panelModel } from './panel-model.js';
import { POWERED_BY } from '../jupiter/attribution.js';
import { createChart, CandlestickSeries, LineSeries, HistogramSeries, LineStyle } from '../../vendor/lightweight-charts/lightweight-charts.standalone.production.mjs';

const $ = id => document.getElementById(id);
$('api-attribution').textContent = `${POWERED_BY} — 1000x public catalog; Pyth oracle history and stream.`;
const SYMBOL = new URLSearchParams(location.hash.slice(1)).get('market') || '';
const STORAGE = 'jupiter1000xIndicatorView';
const NAMES = { zigzag: 'ZigZag', rsi: 'RSI', bop: 'Balance of Power', volty: 'Volty Expan Close', psar: 'Parabolic SAR' };
const fields = [
  ['zigzag', 'reversalPercent', 'ZigZag reversal %', '0.1'],
  ['rsi', 'length', 'RSI length', '1'], ['rsi', 'oversold', 'RSI oversold', '1'], ['rsi', 'overbought', 'RSI overbought', '1'],
  ['bop', 'smoothing', 'BOP SMA length', '1'],
  ['volty', 'length', 'Volty SMA(TR) length', '1'], ['volty', 'multiplier', 'Volty multiplier', '0.05'],
  ['psar', 'start', 'SAR initial AF', '0.01'], ['psar', 'step', 'SAR AF step', '0.01'], ['psar', 'max', 'SAR AF cap', '0.01'],
];
let config = validateIndicatorConfig(DEFAULT_INDICATORS), intervalSec = 60;
let feed, latest, model, viewIdentity, disposed = false, drawQueued = false;
let settingsError = '';
const chart = createChart($('chart'), {
  autoSize: true,
  layout: { background: { color: '#101723' }, textColor: '#b2bfd4', attributionLogo: true },
  grid: { vertLines: { color: '#202c40' }, horzLines: { color: '#202c40' } },
  timeScale: { timeVisible: true, secondsVisible: true, borderColor: '#46536c' },
  rightPriceScale: { borderColor: '#46536c' },
});
const candles = chart.addSeries(CandlestickSeries, { upColor: '#61dbac', downColor: '#f69b9b', borderVisible: false, wickUpColor: '#61dbac', wickDownColor: '#f69b9b' }, 0);
const lines = {
  zigzag: chart.addSeries(LineSeries, { color: '#5ed9ed', lineWidth: 2, priceLineVisible: false, lastValueVisible: false }, 0),
  provisional: chart.addSeries(LineSeries, { color: '#b1becf', lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false }, 0),
  psar: chart.addSeries(LineSeries, { color: '#f8d274', lineVisible: false, pointMarkersVisible: true, pointMarkersRadius: 2, priceLineVisible: false, lastValueVisible: false }, 0),
  upper: chart.addSeries(LineSeries, { color: '#d5a1ff', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }, 0),
  lower: chart.addSeries(LineSeries, { color: '#d5a1ff', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }, 0),
  rsi: chart.addSeries(LineSeries, { color: '#75c8ff', lineWidth: 1, priceLineVisible: false, title: 'RSI' }, 1),
  bop: chart.addSeries(HistogramSeries, { color: '#61dbac', priceLineVisible: false, title: 'BOP' }, 2),
};
const rsiLower = lines.rsi.createPriceLine({ price: config.rsi.oversold, color: '#67768f', lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true });
const rsiUpper = lines.rsi.createPriceLine({ price: config.rsi.overbought, color: '#67768f', lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true });
lines.bop.createPriceLine({ price: 0, color: '#67768f', lineWidth: 1, axisLabelVisible: true });
const numeric = value => typeof value === 'number' && Number.isFinite(value);
const fmt = value => numeric(value) ? value.toLocaleString(undefined, { maximumFractionDigits: 5 }) : 'Warming up';
const stamp = time => numeric(time) ? new Date(time).toISOString().slice(11, 23) + ' UTC' : 'unavailable';
const data = series => series.map(p => numeric(p.value) ? { time: p.time, value: p.value } : { time: p.time });

function clearChart() {
  candles.setData([]);
  Object.values(lines).forEach(series => series.setData([]));
}
function visibility() {
  rsiLower.applyOptions({ price: config.rsi.oversold });
  rsiUpper.applyOptions({ price: config.rsi.overbought });
  for (const key of ['zigzag', 'psar', 'rsi', 'bop']) lines[key].applyOptions({ visible: config[key].enabled });
  lines.provisional.applyOptions({ visible: config.zigzag.enabled });
  lines.upper.applyOptions({ visible: config.volty.enabled });
  lines.lower.applyOptions({ visible: config.volty.enabled });
}
function draw() {
  drawQueued = false;
  if (disposed || !latest) return;
  try { model = panelModel(latest, config); }
  catch {
    model = null; clearChart();
    $('status').textContent = 'Invalid candle or indicator data — signals unavailable';
    $('status').dataset.state = 'error';
    document.querySelectorAll('[data-value]').forEach(el => { el.textContent = 'Unavailable'; });
    document.querySelectorAll('[data-signal]').forEach(el => { el.textContent = 'Invalid input'; });
    return;
  }
  const metrics = model.developing;
  candles.setData(model.candles.map(({ time, open, high, low, close }) => ({ time, open, high, low, close })));
  const pivots = model.confirmedPivots.map(({ time, value }) => ({ time, value }));
  lines.zigzag.setData(pivots);
  const last = pivots.at(-1), provisional = metrics.zigzag.provisional;
  lines.provisional.setData(last && provisional && provisional.time > last.time ? [last, { time: provisional.time, value: provisional.value }] : []);
  lines.psar.setData(data(metrics.psar.series));
  lines.upper.setData(data(metrics.volty.upper)); lines.lower.setData(data(metrics.volty.lower));
  lines.rsi.setData(data(metrics.rsi.series));
  lines.bop.setData(data(metrics.bop.series).map(p => numeric(p.value) ? { ...p, color: p.value >= 0 ? '#61dbac' : '#f69b9b' } : p));
  visibility();
  const identity = `${latest.symbol}:${latest.intervalSec}`;
  if (viewIdentity !== identity && model.candles.length) {
    chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, model.candles.length - 100), to: model.candles.length + 3 });
    chart.panes()[0]?.setHeight(190); chart.panes()[1]?.setHeight(65); chart.panes()[2]?.setHeight(65);
    viewIdentity = identity;
  }
  const price = latest.quote?.price;
  $('market').textContent = `${SYMBOL || 'Select market'}${numeric(price) ? ' · $' + fmt(price) : ''}`;
  $('status').dataset.state = model.signalEligible ? 'live' : latest.status === 'live' ? 'stale' : latest.status;
  $('status').textContent = settingsError || (model.signalEligible ? 'Live oracle · completed-candle explanations' : `${model.reason}${latest.error ? ' · ' + latest.error : ''}`);
  $('timing').textContent = `Exchange ${stamp(latest.quote?.exchangeMs)} · received ${stamp(latest.quote?.receivedMs)} · age ${model.ageMs === null ? 'unavailable' : (model.ageMs / 1000).toFixed(2) + 's'}`;
  for (const key of Object.keys(NAMES)) {
    const metric = model.completed[key];
    const row = document.querySelector(`[data-indicator="${key}"]`);
    let value = metric.latest;
    if (key === 'volty') value = metric.next ? `${fmt(metric.next.lower)} / ${fmt(metric.next.upper)}` : 'Warming up';
    if (key === 'zigzag') value = metric.confirmed.at(-1)?.value ?? null;
    row.querySelector('[data-value]').textContent = typeof value === 'string' ? value : fmt(value);
    row.querySelector('[data-signal]').textContent = !config[key].enabled ? 'Hidden' : model.signalEligible ? (metric.signal || 'Waiting for confirmation') : 'Unavailable until feed is fresh';
  }
  $('candle-note').textContent = `${model.closedCount} contiguous completed candles · last completed open ${model.closedThrough === null ? 'unavailable' : stamp(model.closedThrough * 1000)} · latest chart candle may be developing${model.gapTrimmed ? ' · earlier gap excluded; indicators restart after it' : ''}. Volty readout is the next-bar lower / upper level.`;
}
function queueDraw() {
  if (drawQueued || disposed) return;
  drawQueued = true;
  requestAnimationFrame(draw);
}
async function save() {
  try { await chrome.storage.local.set({ [STORAGE]: { config, intervalSec } }); }
  catch { settingsError = 'View settings could not be saved locally'; }
}
function readoutRows() {
  for (const [key, name] of Object.entries(NAMES)) {
    const tr = document.createElement('tr'); tr.dataset.indicator = key;
    const toggle = document.createElement('input'); toggle.type = 'checkbox'; toggle.checked = config[key].enabled;
    toggle.setAttribute('aria-label', `Show ${name}`);
    toggle.addEventListener('change', () => { config = validateIndicatorConfig({ ...config, [key]: { ...config[key], enabled: toggle.checked } }); save(); queueDraw(); });
    const cell = document.createElement('td'); cell.append(toggle); tr.append(cell);
    for (const [attr, value] of [['name', name], ['value', 'Warming up'], ['signal', 'Waiting for live data']]) {
      const td = document.createElement('td'); td.dataset[attr] = ''; td.textContent = value; tr.append(td);
    }
    $('readouts').append(tr);
  }
}
function parameterForm() {
  const form = $('config-form'); form.replaceChildren();
  for (const [group, name, label, step] of fields) {
    const el = document.createElement('label'); el.textContent = label;
    const input = document.createElement('input'); input.type = 'number'; input.step = step;
    input.name = `${group}.${name}`; input.value = config[group][name]; input.required = true; el.append(input); form.append(el);
  }
  const error = document.createElement('p'); error.id = 'config-error'; error.setAttribute('role', 'alert'); form.append(error);
  const actions = document.createElement('div'); actions.className = 'actions';
  const apply = document.createElement('button'); apply.type = 'submit'; apply.textContent = 'Apply';
  const reset = document.createElement('button'); reset.type = 'button'; reset.textContent = 'Reset defaults';
  reset.addEventListener('click', () => { config = validateIndicatorConfig(DEFAULT_INDICATORS); parameterForm(); syncToggles(); save(); queueDraw(); });
  actions.append(apply, reset); form.append(actions);
}
function syncToggles() {
  for (const key of Object.keys(NAMES)) document.querySelector(`[data-indicator="${key}"] input`).checked = config[key].enabled;
}
$('config-form').addEventListener('submit', event => {
  event.preventDefault();
  const candidate = structuredClone(config);
  for (const [group, name] of fields) {
    const input = $('config-form').elements.namedItem(`${group}.${name}`);
    if (!input.value.trim()) { $('config-error').textContent = 'Every parameter needs a number'; return; }
    candidate[group][name] = Number(input.value);
  }
  try { config = validateIndicatorConfig(candidate); }
  catch (error) { $('config-error').textContent = error.message; return; }
  settingsError = ''; save(); queueDraw(); $('parameters').open = false;
});
async function restart() {
  feed?.stop(); latest = null; model = null; viewIdentity = null; clearChart();
  $('status').textContent = 'Connecting to Jupiter…'; $('status').dataset.state = 'connecting';
  document.querySelectorAll('[data-value]').forEach(el => { el.textContent = 'Warming up'; });
  document.querySelectorAll('[data-signal]').forEach(el => { el.textContent = 'Waiting for live data'; });
  feed = new JupiterFeed({ symbol: SYMBOL, intervalSec, onUpdate: snapshot => { latest = snapshot; queueDraw(); } });
  try { await feed.start(); } catch { $('status').textContent = 'Jupiter data unavailable — no signal'; $('status').dataset.state = 'error'; }
}
for (const entry of TIMEFRAMES) {
  const option = document.createElement('option'); option.value = entry.seconds; option.textContent = entry.label; $('timeframe').append(option);
}
try {
  const saved = (await chrome.storage.local.get(STORAGE))[STORAGE];
  if (saved) { config = validateIndicatorConfig(saved.config); if (TIMEFRAMES.some(t => t.seconds === saved.intervalSec)) intervalSec = saved.intervalSec; }
} catch { settingsError = 'Saved settings invalid or unavailable; using defaults'; }
$('timeframe').value = intervalSec;
$('timeframe').addEventListener('change', () => { intervalSec = Number($('timeframe').value); save(); restart(); });
$('refresh').addEventListener('click', () => restart());
readoutRows(); parameterForm(); visibility();
const staleClock = setInterval(queueDraw, 1000);
window.addEventListener('pagehide', () => { disposed = true; clearInterval(staleClock); feed?.stop(); chart.remove(); }, { once: true });
await restart();
