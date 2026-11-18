import { createChart, CandlestickSeries, LineSeries } from '../../vendor/lightweight-charts/lightweight-charts.standalone.production.mjs';
import { computeIndicators } from '../1000x/indicators.js';
import { readMinutes, readSnapshot } from './market.js';
import { liquidationPrice, MARKETS, planPosition, settle } from './model.js';
import { PAPER_CAPITAL } from './replay.js';
import { aggregateMinutes, INTERVALS, RISK_PRESETS, workbenchPresets } from './strategies.js';
import { beginPaper, closePaper, freshQuote, managePaper, observePaper, stopPaperEntries } from './workbench.js';
import { causalEntryFeatures, openWorkbenchStore, paperMarketKey } from './workbench-store.js';
import { mountVoltyStatus } from './volty-status.js';

const $ = id => document.getElementById(id);
const args = new URLSearchParams(location.hash.slice(1));
const asset = args.get('market') ?? '';
const market = Object.hasOwn(MARKETS, asset) ? MARKETS[asset] : null;
const presets = workbenchPresets(asset);
const formIds = ['preset', 'step', 'direction', 'sizing', 'amount', 'leverage', 'tp', 'sl', 'exit-preset', 'slippageBps', 'additiveBps', 'networkUsd'];
const numeric = id => $(id).valueAsNumber;
const selection = () => presets.find(preset => preset.id === $('preset').value);
const direction = () => Number($('direction').value);
const utc = time => new Date(time * 1000).toISOString().slice(11, 19) + ' UTC';
const usd = price => Number.isFinite(price) ? '$' + price.toLocaleString(undefined, { maximumFractionDigits: 4 }) : '—';
const decimal = value => Number.isFinite(value) ? value.toFixed(3) : '—';
const bracket = price => Number.isFinite(price) ? usd(price) : 'Off';
const now = () => Date.now() / 1000;
const makeId = () => crypto.randomUUID();
const marketKey = symbol => paperMarketKey(MARKETS[symbol].venue, symbol);
const settings = () => ({
  sizing: $('sizing').value, amount: numeric('amount'), leverage: numeric('leverage'), tp: numeric('tp'), sl: numeric('sl'),
  slippageBps: numeric('slippageBps'), additiveBps: numeric('additiveBps'), networkUsd: numeric('networkUsd'),
});

const accounts = new Map();
const feeds = new Map();
let store;
let storageIssue = '';
let actionIssue = '';
let busy = false;
let disposed = false;
let chartReady = false;
let pollTimer;
let voltyView;
let editing;
let learned = [];
let forecast = null;
let candleLearning = null;
let learningIssue = '';
let savedForm = '';
const lifetime = new AbortController();
const chart = createChart($('chart'), {
  autoSize: true, layout: { background: { color: '#101723' }, textColor: '#bac7db', attributionLogo: true },
  grid: { vertLines: { color: '#1b263b' }, horzLines: { color: '#1b263b' } },
  timeScale: { timeVisible: true },
});
const candles = chart.addSeries(CandlestickSeries, { upColor: '#61dbac', downColor: '#f69b9b', borderVisible: false });
const lines = {
  liquidation: candles.createPriceLine({ color: '#ff6b78', price: 0, title: 'Liquidation', lineVisible: false, axisLabelVisible: false }),
  stop: candles.createPriceLine({ color: '#ffcb83', price: 0, title: 'Stop', lineVisible: false, axisLabelVisible: false }),
  take: candles.createPriceLine({ color: '#61dbac', price: 0, title: 'Target', lineVisible: false, axisLabelVisible: false }),
};
const overlays = Object.fromEntries(Object.entries({
  emaFast: '#8bc6f6', emaSlow: '#b6a6f3', voltyUpper: '#42608c', voltyLower: '#42608c', zigzag: '#f4c47a', psar: '#71c6a9',
}).map(([name, color]) => [name, chart.addSeries(LineSeries, {
  color, lineWidth: 1, lineVisible: name !== 'psar', pointMarkersVisible: name === 'psar',
  priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
})]));

function feedFor(symbol) {
  if (!feeds.has(symbol)) feeds.set(symbol, { history: [], from: Infinity, lastHistory: 0, snapshot: null, issue: '', historyIssue: '' });
  return feeds.get(symbol);
}

function renderFields(id, fields) {
  $(id).replaceChildren(...fields.map(([name, value, tone]) => {
    const group = document.createElement('div');
    const dt = document.createElement('dt');
    const dd = document.createElement('dd');
    dt.textContent = name;
    dd.textContent = value;
    if (tone) dd.className = tone;
    group.append(dt, dd);
    return group;
  }));
}

const tone = value => value > 0 ? 'up' : value < 0 ? 'down' : '';
function refreshChart(fit = false) {
  const rows = aggregateMinutes(feedFor(asset).history, Number($('step').value)).slice(-240);
  candles.setData(rows);
  const result = computeIndicators(rows);
  const series = { emaFast: result.ema.fast, emaSlow: result.ema.slow, voltyUpper: result.volty.upper,
    voltyLower: result.volty.lower, zigzag: result.zigzag.confirmed, psar: result.psar.series };
  for (const [name, line] of Object.entries(overlays)) {
    line.setData(series[name].map(({ time, value }) => Number.isFinite(value) ? { time, value } : { time }));
  }
  const emaGap = result.ema.latest === null || result.ema.slowLatest === null ? null : result.ema.latest - result.ema.slowLatest;
  renderFields('indicators', [
    ['RSI 14', decimal(result.rsi.latest)],
    ['MACD histogram', decimal(result.macd.histogramLatest), tone(result.macd.histogramLatest)],
    ['EMA 9 / 21', decimal(result.ema.latest) + ' / ' + decimal(result.ema.slowLatest), tone(emaGap)],
    ['Balance of Power', decimal(result.bop.latest), tone(result.bop.latest)],
    ['Volty levels', usd(result.volty.latest?.lower) + ' / ' + usd(result.volty.latest?.upper)],
    ['Parabolic SAR', usd(result.psar.latest), result.psar.trend],
    ['ZigZag confirmed', usd(result.zigzag.latest?.value)],
  ]);
  if (rows.length && (fit || !chartReady)) {
    chart.timeScale().fitContent();
    chartReady = true;
  }
}

function renderPositions() {
  const rows = [...accounts].filter(([, account]) => account.broker.position).map(([key, account]) => {
    const { asset: symbol, broker: { position } } = account;
    return { key, symbol, id: position.id, direction: position.direction, entry: position.entry,
      size: position.size, stop: position.stop, take: position.take, signals: position.exitPolicy?.signals?.rules?.length ?? 0,
      fresh: Boolean(freshQuote(feedFor(symbol), now())) };
  });
  const signature = JSON.stringify(rows);
  if ($('positions').dataset.signature !== signature) {
    $('positions').dataset.signature = signature;
    $('positions').replaceChildren(...rows.map(row => {
      const li = document.createElement('li');
      li.className = 'position-row';
      const detail = document.createElement('div');
      const label = document.createElement('strong');
      const info = document.createElement('p');
      label.textContent = `${row.symbol} · ${row.direction === 1 ? 'Long' : 'Short'} · ${usd(row.size)} paper`;
      label.className = row.direction === 1 ? 'up' : 'down';
      info.className = 'muted';
      info.textContent = `Entry ${usd(row.entry)} · TP ${bracket(row.take)} · SL ${bracket(row.stop)}${row.signals ? ` · ${row.signals} signal rules` : ''}${row.fresh ? '' : ' · waiting for a fresh mark'}`;
      detail.append(label, info);
      const actions = document.createElement('div');
      actions.className = 'actions';
      const exit = document.createElement('button');
      exit.type = 'button';
      exit.textContent = 'TP / SL and signals';
      exit.addEventListener('click', () => openEditor(row.key, row.id));
      const close = document.createElement('button');
      close.type = 'button';
      close.textContent = 'Close paper';
      close.disabled = !row.fresh;
      close.addEventListener('click', () => void editAccount(row.key, current => closePaper(current, feedFor(row.symbol), row.id, now())));
      actions.append(exit, close);
      li.append(detail, actions);
      return li;
    }));
  }
  $('book-status').textContent = storageIssue || (store
    ? rows.length ? `${rows.length} open paper ${rows.length === 1 ? 'position' : 'positions'} across markets.` : 'No open paper positions.'
    : 'Loading paper accounts…');
  $('export-trades').disabled = !store || Boolean(storageIssue);
}

function render() {
  if (disposed || !market) return;
  const account = accounts.get(marketKey(asset));
  const broker = account?.broker;
  const held = broker?.position;
  const running = account?.running;
  if (running || held) restoreForm(account);
  else savedForm = '';
  const feed = feedFor(asset);
  const preset = selection();
  const quote = freshQuote(feed, now());
  const locked = running || !!held;
  for (const id of formIds) $(id).disabled = locked;
  if (!locked && preset) $('step').disabled = true;
  $('direction').options[1].disabled = Boolean(preset && preset.kind !== 'volty');
  $('direction').options[2].disabled = preset?.kind !== 'volty';
  $('status').textContent = [quote ? `${usd(quote.price)} · ${utc(quote.time)}` : feed.issue || 'Waiting for fresh market data…',
    feed.historyIssue].filter(Boolean).join(' · ');
  $('preset-info').textContent = preset ? `${INTERVALS[preset.step]} · ${preset.details} · ${preset.source}${preset.assets.includes(asset) ? '' : ' · Cross-market transfer'}` : '';

  let position = held ? { ...held, liquidation: liquidationPrice(held, held.carry) } : null;
  let warning = actionIssue || storageIssue || account?.notice || broker?.note || '';
  const side = direction() === -1 ? -1 : 1;
  const terms = feed.snapshot && (side === 1 ? feed.snapshot.long : feed.snapshot.short);
  if (terms) {
    $('leverage').max = String(terms.max);
    $('fees').textContent = terms.venue === 'JLP'
      ? `${terms.baseBps} bps open and close + modeled impact. Current ${terms.carryBps.toFixed(3)} bps/hour borrow.`
      : `${terms.baseBps} bps taker · ${terms.liquidationBps} bps liquidation. Current ${terms.carryBps.toFixed(3)} bps/hour funding. First tier.`;
  }
  if (!held && terms && quote) {
    try {
      position = planPosition(settings(), terms, quote.price, side);
      if (position.deposit > (broker?.equity ?? PAPER_CAPITAL)) throw new Error('Paper account has insufficient remaining capital.');
    } catch (error) {
      warning ||= error.message;
      position = null;
    }
  }
  if (position?.stop && position.direction * (position.stop - position.liquidation) <= 0) {
    warning ||= 'This stop is at or beyond estimated liquidation.';
  }
  for (const [key, line] of Object.entries(lines)) {
    const price = position?.[key];
    const visible = Number.isFinite(price) && price > 0;
    line.applyOptions({ price: visible ? price : 0, lineVisible: visible, axisLabelVisible: visible });
  }
  renderFields('risk', [
    ['Size', usd(position?.size)], ['Collateral', usd(position?.deposit)], ['Entry', usd(position?.entry)],
    ['Est. liquidation', usd(position?.liquidation)], ['Take profit', bracket(position?.take)],
    ['Stop loss', bracket(position?.stop)], ['Open cost', usd(position?.openCost)],
  ]);
  const entryReady = quote && causalEntryFeatures(feed.history, quote.time);
  if (quote && !entryReady && !held) warning ||= 'Entries need contiguous closed one-minute bars for learning.';
  $('warning').textContent = warning;
  const unavailable = busy || !store || Boolean(storageIssue);
  $('open').disabled = unavailable || !entryReady || !position || locked || direction() === 0;
  $('auto').disabled = unavailable || (!running && (!entryReady || !position || !preset || !!held));
  $('auto').textContent = running ? 'Pause entries' : 'Start strategy';
  $('auto').dataset.action = running ? 'pause' : 'start';
  $('auto').dataset.runId = running ? account.runId ?? '' : '';
  $('close').disabled = unavailable || !held || !quote;
  const equity = (broker?.equity ?? PAPER_CAPITAL) + (held && quote
    ? settle(held, { reason: 'mark', price: quote.price }, held.carry).pnl : 0);
  $('performance').textContent = `${running ? 'Strategy active' : held ? 'Position open' : 'Paper idle'} · Equity ${usd(equity)} · Realized ${usd((broker?.equity ?? PAPER_CAPITAL) - PAPER_CAPITAL)} · ${account?.exits ?? 0} exits`;
  $('ledger').replaceChildren(...(account?.recent ?? []).slice().reverse().map(row => {
    const item = document.createElement('li');
    item.textContent = `${utc(row.time)} · ${row.direction === 1 ? 'Long' : 'Short'} · ${row.reason} · ${usd(row.pnl)}`;
    return item;
  }));
  const longSamples = learned.filter(row => row.direction === 1).reduce((sum, row) => sum + row.samples, 0);
  const shortSamples = learned.filter(row => row.direction === -1).reduce((sum, row) => sum + row.samples, 0);
  const mature = learned.filter(row => row.samples >= (row.minimumSamples ?? 20)).length;
  const scope = learningScope();
  const estimates = forecast?.key === scope.key
    ? forecast.estimates.filter(row => Number.isFinite(row.result.probability))
      .map(row => `${row.direction === 1 ? 'Long' : 'Short'} ${(row.result.probability * 100).toFixed(1)}% estimated profitable`)
    : [];
  $('learning').textContent = [
    `After-cost trade model · ${longSamples} long and ${shortSamples} short closes learned · ${mature} ready models`,
    ...estimates,
  ].join(' · ');
  renderFields('candle-learning', (candleLearning?.horizons ?? []).map(row => {
    const probability = row.issue?.mode === 'active' && row.issue?.probability;
    return [`${row.seconds / 60}m higher close`,
      Number.isFinite(probability) ? `${(100 * probability).toFixed(1)}% · ${row.samples} labels` : `${row.samples} labels`,
      Number.isFinite(probability) ? tone(probability - 0.5) : ''];
  }));
  $('learning-error').textContent = learningIssue;
  renderPositions();
}

function restoreForm(account) {
  const { strategy, step, broker } = account;
  const signature = JSON.stringify([strategy, step, broker.entryDirection, broker.settings]);
  if (signature === savedForm) return;
  savedForm = signature;
  $('preset').value = strategy ?? '';
  $('step').value = String(step);
  $('direction').value = String(broker.entryDirection);
  for (const [key, value] of Object.entries(broker.settings)) {
    if (formIds.includes(key)) $(key).value = String(value);
  }
  $('exit-preset').value = 'custom';
  refreshChart();
}

function learningScope() {
  const strategy = selection()?.id ?? 'manual';
  const step = Number($('step').value);
  return { key: JSON.stringify([strategy, step]), strategy, step };
}

async function refreshLearning() {
  const key = marketKey(asset);
  const scope = learningScope();
  const feed = feedFor(asset);
  const quote = freshQuote(feed, now());
  const features = quote ? causalEntryFeatures(feed.history, quote.time) : null;
  try {
    const estimates = features ? await Promise.all([1, -1].map(async direction => ({ direction,
      result: await store.predict(key, { strategy: scope.strategy, step: scope.step, direction, features }),
    }))) : [];
    learned = await store.metrics(key);
    forecast = { key: scope.key, estimates };
    candleLearning = await store.advanceCandleModel(key, feed.history, quote, Date.now());
    learningIssue = '';
  } catch (error) {
    forecast = null;
    candleLearning = null;
    learningIssue = `Learning metrics unavailable. ${error.message}`;
  }
}

async function refreshHistory(symbol, feed, step) {
  const boundary = Math.floor(now() / 60) * 60;
  const from = boundary - Math.max(86400, step * 96);
  const refreshFrom = feed.from > from ? from : Math.max(from, (feed.history.at(-1)?.time ?? from) - 120);
  const readRanges = [];
  for (let cursor = refreshFrom; cursor < boundary; cursor += 43200) {
    readRanges.push([cursor, Math.min(boundary, cursor + 43200)]);
  }
  const byTime = new Map(feed.history.filter(row => row.time >= from).map(row => [row.time, row]));
  for (let i = 0; i < readRanges.length; i += 4) {
    const chunks = await Promise.all(readRanges.slice(i, i + 4).map(([start, end]) => readMinutes(symbol, start, end, lifetime.signal)));
    for (const row of chunks.flat()) byTime.set(row.time, { ...row, closed: true });
  }
  if (disposed) return;
  feed.history = [...byTime.values()].sort((a, b) => a.time - b.time);
  feed.from = from;
  feed.lastHistory = now();
  feed.historyIssue = feed.history.length ? '' : 'Waiting for complete candles';
  if (symbol === asset) refreshChart();
}

async function refreshFeed(symbol, account) {
  const feed = feedFor(symbol);
  const step = Math.max(symbol === asset ? Number($('step').value) : 60, account?.step ?? 60);
  const quote = readSnapshot(symbol, lifetime.signal).then(value => {
    if (!disposed) feed.snapshot = value;
    feed.issue = '';
  }).catch(error => { feed.issue = error.message; });
  const history = now() - feed.lastHistory >= 12 ? refreshHistory(symbol, feed, step)
    .catch(() => { feed.historyIssue = 'Candle history unavailable'; }) : Promise.resolve();
  await Promise.all([quote, history]);
  if (!disposed && store && (account?.running || account?.broker.position)) {
    const result = await store.update(marketKey(symbol), current => observePaper(current, feed, now(), makeId));
    if (result.account) accounts.set(marketKey(symbol), result.account);
  }
}

async function poll() {
  if (disposed || !market) return;
  try {
    if (!store) store = await openWorkbenchStore(indexedDB);
    for (const { key, account } of await store.getAccounts()) accounts.set(key, account);
    const active = [...accounts.values()].filter(account => account.running || account.broker.position).map(account => account.asset);
    await Promise.all([...new Set([asset, ...active])].map(symbol => refreshFeed(symbol, accounts.get(marketKey(symbol)))));
    await refreshLearning();
    storageIssue = '';
  } catch (error) {
    storageIssue = `Paper storage unavailable. ${error.message}`;
  }
  if (!disposed) {
    render();
    pollTimer = setTimeout(poll, 5000);
  }
}

async function editAccount(key, reduce, inEditor = false) {
  if (!store || busy || storageIssue) return;
  busy = true;
  actionIssue = '';
  try {
    const result = await store.update(key, reduce);
    if (result.account) accounts.set(key, result.account);
    await refreshLearning();
    if (inEditor) $('exit-editor').close();
  } catch (error) {
    (inEditor ? $('exit-error') : $('warning')).textContent = error.message;
    if (!inEditor) actionIssue = error.message;
  } finally {
    busy = false;
    render();
  }
}

function openEditor(key, id) {
  const position = accounts.get(key)?.broker.position;
  if (position?.id !== id) return;
  editing = { key, id };
  const signals = position.exitPolicy?.signals;
  $('edit-tp').value = String(position.take === null ? 0 : 100 * Math.abs(position.take / position.entry - 1));
  $('edit-sl').value = String(position.stop === null ? 0 : 100 * Math.abs(position.stop / position.entry - 1));
  $('signal-step').value = String(signals?.step ?? 300);
  $('signal-mode').value = signals?.mode ?? 'any';
  $('signal-macd').value = signals?.rules.find(rule => rule.indicator === 'macd')?.cross ?? '';
  $('signal-rsi-low').value = signals?.rules.find(rule => rule.indicator === 'rsi' && rule.level === 30)?.cross ?? '';
  $('signal-rsi-high').value = signals?.rules.find(rule => rule.indicator === 'rsi' && rule.level === 60)?.cross ?? '';
  $('exit-error').textContent = '';
  $('exit-editor').showModal();
}

function exitRule() {
  const rules = [
    { indicator: 'macd', cross: $('signal-macd').value },
    { indicator: 'rsi', cross: $('signal-rsi-low').value, level: 30 },
    { indicator: 'rsi', cross: $('signal-rsi-high').value, level: 60 },
  ].filter(rule => rule.cross);
  return { tp: numeric('edit-tp'), sl: numeric('edit-sl'),
    signals: rules.length ? { step: Number($('signal-step').value), mode: $('signal-mode').value, rules } : null };
}

function requestEntry(allowStrategy) {
  const feed = { ...feedFor(asset) };
  const request = { asset, settings: settings(), direction: direction(),
    strategy: allowStrategy ? selection()?.id ?? null : null,
    step: Number($('step').value), makeId };
  return current => beginPaper(current, feed, { ...request, now: now() });
}

if (market) {
  if (asset === 'ZEC') voltyView = mountVoltyStatus($('volty'));
  $('market').textContent = `${asset}/USD · ${market.venue === 'JLP' ? 'JLP · JupUSD input' : 'GUM Beta · USDC'}`;
  $('source').textContent = market.venue === 'JLP' ? 'Jupiter Pyth oracle candles and prices' : 'GUM trade candles · GUM sampled mark';
  $('impact-field').hidden = market.venue !== 'JLP';
  $('direction').value = args.get('side') === 'short' ? '-1' : '1';
  for (const preset of presets) {
    const option = document.createElement('option');
    option.value = preset.id;
    option.textContent = preset.name + (preset.assets.includes(asset) ? '' : ' · transfer');
    $('preset').append(option);
  }
  $('preset').addEventListener('change', () => {
    const preset = selection();
    if (preset) $('step').value = String(preset.step);
    if (preset?.kind !== 'volty' && (direction() === 0 || preset && direction() === -1)) $('direction').value = '1';
    $('exit-preset').value = preset?.bracket ? 'custom' : 'original';
    $('tp').value = String(preset?.bracket?.tp ?? 0);
    $('sl').value = String(preset?.bracket?.sl ?? 0);
    feedFor(asset).lastHistory = 0;
    refreshChart(true);
    render();
  });
  $('step').addEventListener('change', () => {
    feedFor(asset).lastHistory = 0;
    refreshChart(true);
  });
  $('exit-preset').addEventListener('change', () => {
    const rule = RISK_PRESETS[$('exit-preset').value];
    if (rule) {
      $('tp').value = String(rule.tp);
      $('sl').value = String(rule.sl);
    }
    render();
  });
  for (const id of ['tp', 'sl']) $(id).addEventListener('input', () => { $('exit-preset').value = 'custom'; });
  for (const id of formIds) $(id).addEventListener('input', render);
  $('open').addEventListener('click', () => void editAccount(marketKey(asset), requestEntry(false)));
  $('auto').addEventListener('click', () => {
    const key = marketKey(asset);
    const { runId, action } = $('auto').dataset;
    const operation = action === 'pause' ? current => stopPaperEntries(current, runId) : requestEntry(true);
    void editAccount(key, operation);
  });
  $('close').addEventListener('click', () => {
    const key = marketKey(asset);
    const id = accounts.get(key)?.broker.position?.id;
    if (id) void editAccount(key, current => closePaper(current, feedFor(asset), id, now()));
  });
  $('exit-form').addEventListener('submit', event => {
    event.preventDefault();
    if (!editing) return;
    const { key, id } = editing;
    const rule = exitRule();
    void editAccount(key, current => managePaper(current, id, { ...rule, armedAt: now() }), true);
  });
  $('exit-cancel').addEventListener('click', () => $('exit-editor').close());
  $('export-trades').addEventListener('click', async () => {
    try {
      const data = await store.exportTrades();
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2) + '\n'], { type: 'application/json' }));
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'perps-paper-trades.json';
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      actionIssue = error.message;
      render();
    }
  });
  void poll();
} else $('status').textContent = 'Unsupported Perps market.';

window.addEventListener('pagehide', () => {
  disposed = true;
  clearTimeout(pollTimer);
  voltyView?.close();
  lifetime.abort();
  chart.remove();
}, { once: true });
