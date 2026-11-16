import { JupiterFeed, TIMEFRAMES } from './feed.js';
import { DEFAULT_INDICATORS, validateIndicatorConfig } from './indicators.js';
import { panelModel } from './panel-model.js';
import { OracleController } from './oracle-controller.js';
import { oracleView } from './oracle-view.js';
import { POWERED_BY } from '../jupiter/attribution.js';
import { createChart, CandlestickSeries, LineSeries, HistogramSeries, LineStyle } from '../../vendor/lightweight-charts/lightweight-charts.standalone.production.mjs';

const $ = id => document.getElementById(id);
const renderOracle = oracleView($('streaming-oracle'));
const oracle = new OracleController({ onChange: renderOracle });
$('api-attribution').textContent = `${POWERED_BY} — 1000x public catalog; Pyth oracle history and stream.`;
const SYMBOL = new URLSearchParams(location.hash.slice(1)).get('market') || '';
const STORAGE = 'jupiter1000xIndicatorView';
const NAMES = { zigzag: 'ZigZag', rsi: 'RSI', bop: 'Balance of Power', volty: 'Volty Expan Close', psar: 'Parabolic SAR', ema: 'EMA9 / EMA21', macd: 'MACD12 / 26 / 9' };
const fields = [
  ['zigzag', 'reversalPercent', 'ZigZag reversal %', '0.1'],
  ['rsi', 'length', 'RSI length', '1'], ['rsi', 'oversold', 'RSI oversold', '1'], ['rsi', 'overbought', 'RSI overbought', '1'],
  ['bop', 'smoothing', 'BOP SMA length', '1'],
  ['volty', 'length', 'Volty SMA(TR) length', '1'], ['volty', 'multiplier', 'Volty multiplier', '0.05'],
  ['psar', 'start', 'SAR initial AF', '0.01'], ['psar', 'step', 'SAR AF step', '0.01'], ['psar', 'max', 'SAR AF cap', '0.01'],
];
let config = validateIndicatorConfig(DEFAULT_INDICATORS), intervalSec = 600;
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
  ema9: chart.addSeries(LineSeries, { color: '#ffcd75', lineWidth: 1, priceLineVisible: false, title: 'EMA9' }, 0),
  ema21: chart.addSeries(LineSeries, { color: '#b3b1ff', lineWidth: 1, priceLineVisible: false, title: 'EMA21' }, 0),
  macd: chart.addSeries(LineSeries, { color: '#75c8ff', lineWidth: 1, priceLineVisible: false, title: 'MACD' }, 3),
  macdSignal: chart.addSeries(LineSeries, { color: '#ffcd75', lineWidth: 1, priceLineVisible: false, title: 'Signal' }, 3),
  macdHistogram: chart.addSeries(HistogramSeries, { color: '#61dbac', priceLineVisible: false, title: 'Histogram' }, 3),
};
const rsiLower = lines.rsi.createPriceLine({ price: config.rsi.oversold, color: '#67768f', lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true });
const rsiUpper = lines.rsi.createPriceLine({ price: config.rsi.overbought, color: '#67768f', lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true });
lines.bop.createPriceLine({ price: 0, color: '#67768f', lineWidth: 1, axisLabelVisible: true });
lines.macd.createPriceLine({ price: 0, color: '#67768f', lineWidth: 1, axisLabelVisible: true });
const numeric = value => typeof value === 'number' && Number.isFinite(value);
const fmt = value => numeric(value) ? value.toLocaleString(undefined, { maximumFractionDigits: 5 }) : 'Warming up';
const stamp = time => numeric(time) ? new Date(time).toISOString().slice(11, 23) + ' UTC' : 'unavailable';
const data = series => series.map(p => numeric(p.value) ? { time: p.time, value: p.value } : { time: p.time });
const histogramData = series => data(series).map(p => numeric(p.value) ? { ...p, color: p.value >= 0 ? '#61dbac' : '#f69b9b' } : p);
const utc = seconds => numeric(seconds) ? new Date(seconds * 1000).toISOString().slice(11, 16) + ' UTC' : 'unavailable';
const shapeNames = { unknown: 'Warming up', range: 'Range', trend_up: 'Rising trend', trend_down: 'Falling trend',
  v_rebound: 'V rebound', inverted_v: 'Inverted V', bowl: 'Bowl', cap: 'Cap', compression: 'Compression' };

function resetContext() {
  $('pattern').textContent = 'Reversal context unavailable until fresh complete history arrives';
  $('pattern').dataset.state = 'unavailable';
  for (const [i, id] of ['previous-first', 'previous-second'].entries()) {
    const card = $(id); card.dataset.color = 'unknown'; card.style.removeProperty('--strength');
    card.querySelector('strong').textContent = `Previous ${2 - i} · unavailable`;
    card.querySelector('span').textContent = 'Completed 10m candle';
  }
  $('developing-context').textContent = 'Developing target: unavailable';
  $('shapes').replaceChildren();
  $('momentum-context').textContent = 'Closed 1m momentum: unavailable';
  $('heuristic').textContent = 'Heuristic alignment unavailable · not a probability';
}

function drawContext(context) {
  for (const [i, id] of ['previous-first', 'previous-second'].entries()) {
    const bar = context.previous[i], card = $(id), color = context.colors[i];
    card.dataset.color = color || 'unknown';
    const strength = bar && bar.high > bar.low ? Math.min(1, Math.abs(bar.close - bar.open) / (bar.high - bar.low)) : 0;
    card.style.setProperty('--strength', String(0.15 + strength * 0.55));
    card.querySelector('strong').textContent = `Previous ${2 - i} · ${color || 'unavailable'}`;
    card.querySelector('span').textContent = bar ? `${utc(bar.time)}–${utc(bar.time + 600)} · ${fmt(bar.open)} → ${fmt(bar.close)}` : 'Waiting for a complete 10m candle';
  }
  $('pattern').dataset.state = context.ready ? context.direction === 'UP' ? 'up' : context.direction === 'DOWN' ? 'down' : 'neutral' : 'unavailable';
  $('pattern').textContent = !context.ready ? 'Reversal context unavailable until feed and complete 1m history are fresh'
    : context.direction ? `${context.pair} → watch ${context.direction} · ${context.direction === 'UP' ? 'long' : 'short'} context · ${context.newStreak === true ? 'new pair after opposite color' : context.newStreak === false ? 'rolling pair' : 'preceding color unknown'}`
    : 'No reversal setup · flat or mixed previous candles';
  const developing = context.developing;
  $('developing-context').textContent = `Developing target ${utc(context.targetStart)}–${utc(context.targetEnd)}: ${context.ready && developing ? `${developing.color} · ${fmt(developing.open)} → ${fmt(developing.close)} · can change before close` : 'partial or unavailable; no confirmed target direction'}`;
  $('shapes').replaceChildren(...Object.values(context.frames).map(frame => {
    const card = document.createElement('div'); card.className = 'shape-card'; card.dataset.minutes = frame.minutes;
    const title = document.createElement('strong'); title.textContent = `${frame.minutes}m · ${context.ready ? shapeNames[frame.shape] : 'Unavailable'}`;
    const detail = document.createElement('span');
    detail.textContent = !context.ready ? 'Feed / history not ready' : frame.shape === 'unknown' ? `${Math.min(frame.count, 48)}/48 completed bars · gaps reset warmup`
      : `Closed ${utc(frame.closedAt)} · ${frame.zone} third of observed range`;
    card.append(title, detail); return card;
  }));
  const m = context.momentum;
  $('momentum-context').textContent = m.ready ? `Closed 1m momentum · ${utc(m.closedAt)} · EMA9 ${fmt(m.ema9)} / EMA21 ${fmt(m.ema21)} · MACD ${fmt(m.macd)} / signal ${fmt(m.macdSignal)} / hist ${fmt(m.macdHistogram)} · BOP SMA3 ${fmt(m.bopSma3)} (OHLC price proxy)`
    : `Closed 1m momentum: ${context.ready ? `warming up ${Math.min(m.count, 78)}/78 contiguous candles` : 'unavailable until feed and history are fresh'}`;
  $('heuristic').textContent = context.ready && context.heuristic ? `Heuristic alignment: ${context.heuristic.agree}/${context.heuristic.total} · EMA trend, MACD histogram and BOP agree with ${context.direction}. Not a probability or a trade instruction.`
    : 'Heuristic alignment unavailable · needs a same-color pair and 78 fresh completed 1m candles · not a probability';
  $('empirical').textContent = `Empirical probability / model score unavailable: ${context.empirical.reason}`;
  $('exit-context').textContent = `Position / ROE / exit context unavailable: ${context.exit.reason}`;
}

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
  lines.ema9.applyOptions({ visible: config.ema.enabled }); lines.ema21.applyOptions({ visible: config.ema.enabled });
  for (const key of ['macd', 'macdSignal', 'macdHistogram']) lines[key].applyOptions({ visible: config.macd.enabled });
}
function draw() {
  drawQueued = false;
  if (disposed || !latest) return;
  try { model = panelModel(latest, config); }
  catch {
    // Chart arithmetic is independent of the shared minute learner. Its own
    // causal input/feature validation withholds every model on invalid minutes.
    model = null; clearChart(); resetContext();
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
  lines.bop.setData(histogramData(metrics.bop.series));
  lines.ema9.setData(data(metrics.ema.fast)); lines.ema21.setData(data(metrics.ema.slow));
  lines.macd.setData(data(metrics.macd.series)); lines.macdSignal.setData(data(metrics.macd.signalSeries));
  lines.macdHistogram.setData(histogramData(metrics.macd.histogram));
  visibility();
  const identity = `${latest.symbol}:${latest.intervalSec}`;
  if (viewIdentity !== identity && model.candles.length) {
    chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, model.candles.length - 100), to: model.candles.length + 3 });
    chart.panes()[0]?.setHeight(190); chart.panes()[1]?.setHeight(60); chart.panes()[2]?.setHeight(55); chart.panes()[3]?.setHeight(65);
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
    if (key === 'ema') value = numeric(metric.latest) ? `${fmt(metric.latest)} / ${fmt(metric.slowLatest)}` : null;
    if (key === 'macd') value = numeric(metric.latest) ? `${fmt(metric.latest)} / ${fmt(metric.signalLatest)}` : null;
    row.querySelector('[data-value]').textContent = typeof value === 'string' ? value : fmt(value);
    row.querySelector('[data-signal]').textContent = !config[key].enabled ? 'Hidden' : model.signalEligible ? (metric.signal || 'Waiting for confirmation') : 'Unavailable until feed is fresh';
  }
  drawContext(model.reversal);
  $('readout-caption').textContent = `Completed ${TIMEFRAMES.find(entry => entry.seconds === intervalSec)?.label} chart-candle readings · 1m momentum is separate above`;
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
  oracle.suspend();
  feed?.stop(); latest = null; model = null; viewIdentity = null; clearChart(); resetContext();
  $('status').textContent = 'Connecting to Jupiter…'; $('status').dataset.state = 'connecting';
  document.querySelectorAll('[data-value]').forEach(el => { el.textContent = 'Warming up'; });
  document.querySelectorAll('[data-signal]').forEach(el => { el.textContent = 'Waiting for live data'; });
  feed = new JupiterFeed({ symbol: SYMBOL, intervalSec, withReversalContext: true, onUpdate: snapshot => {
    latest = snapshot;
    if (!document.hidden) oracle.observe(snapshot);
    queueDraw();
  } });
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
oracle.selectHorizon(intervalSec);
$('timeframe').addEventListener('change', () => {
  intervalSec = Number($('timeframe').value); oracle.selectHorizon(intervalSec); save();
  model = null; viewIdentity = null; clearChart(); resetContext();
  void feed.setInterval(intervalSec);
});
$('refresh').addEventListener('click', () => restart());
readoutRows(); parameterForm(); visibility();
const staleClock = setInterval(() => { if (!document.hidden && latest) oracle.observe(latest); queueDraw(); }, 1000);
document.addEventListener('visibilitychange', () => {
  if (document.hidden) oracle.suspend();
  else { if (latest) oracle.observe(latest); queueDraw(); }
});
window.addEventListener('pagehide', () => { disposed = true; clearInterval(staleClock); feed?.stop(); oracle.stop(); chart.remove(); }, { once: true });
await restart();
