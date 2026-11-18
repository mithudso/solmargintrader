import { createChart, CandlestickSeries } from '../../vendor/lightweight-charts/lightweight-charts.standalone.production.mjs';
import { readMinutes, readSnapshot } from './market.js';
import { MARKETS, planPosition } from './model.js';
import { PaperBroker, PAPER_CAPITAL } from './replay.js';
import { aggregateMinutes, INTERVALS, marketPresets, RISK_PRESETS, signalMap } from './strategies.js';

const $ = id => document.getElementById(id);
const args = new URLSearchParams(location.hash.slice(1));
const asset = args.get('market') ?? '';
const market = Object.hasOwn(MARKETS, asset) ? MARKETS[asset] : null;
const presets = marketPresets(asset);
const formIds = ['preset', 'step', 'direction', 'sizing', 'amount', 'leverage', 'tp', 'sl', 'exit-preset', 'slippageBps', 'additiveBps', 'networkUsd'];
const numeric = id => $(id).valueAsNumber;
const selection = () => presets.find(preset => preset.id === $('preset').value);
const direction = () => Number($('direction').value);
const utc = time => new Date(time * 1000).toISOString().slice(11, 19) + ' UTC';
const usd = price => Number.isFinite(price) ? '$' + price.toLocaleString(undefined, { maximumFractionDigits: 5 }) : '—';
const bracket = price => Number.isFinite(price) ? usd(price) : 'Off';
const now = () => Date.now() / 1000;
const settings = () => ({
  sizing: $('sizing').value, amount: numeric('amount'), leverage: numeric('leverage'), tp: numeric('tp'), sl: numeric('sl'),
  slippageBps: numeric('slippageBps'), additiveBps: numeric('additiveBps'), networkUsd: numeric('networkUsd'),
});

let history = [];
let snapshot = null;
let feedIssue = '';
let historyIssue = '';
let broker = null;
let running = false;
let active = null;
let lastPoint = 0;
let lastDecision = 0;
let gap = '';
let disposed = false;
let lastHistory = 0;
let chartReady = false;
let pollTimer;
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

function refreshChart(fit = false) {
  const rows = aggregateMinutes(history, Number($('step').value)).slice(-180);
  candles.setData(rows);
  if (rows.length && (fit || !chartReady)) {
    chart.timeScale().fitContent();
    chartReady = true;
  }
}

function fresh() {
  return snapshot && !feedIssue && now() - snapshot.mark.time <= 20;
}

function render() {
  const preset = selection();
  const quote = fresh() ? snapshot.mark : null;
  const terms = snapshot ? (direction() === 1 ? snapshot.long : snapshot.short) : null;
  const held = broker?.position;
  const locked = running || !!held;
  for (const id of formIds) $(id).disabled = locked;
  if (!locked && preset) $('step').disabled = true;
  $('status').textContent = [quote ? `${usd(quote.price)} · ${utc(quote.time)}` : feedIssue || 'Waiting for market data…', historyIssue]
    .filter(Boolean).join(' · ');
  $('preset-info').textContent = preset ? `${INTERVALS[preset.step]} · ${preset.details} · ${preset.source}${preset.assets.includes(asset) ? '' : ' · Cross-market transfer'}` : '';
  if (terms) {
    $('leverage').max = String(terms.max);
    $('fees').textContent = terms.venue === 'JLP'
      ? `${terms.baseBps} bps open and close + rounded linear and scenario impact. Current ${terms.carryBps.toFixed(3)} bps/hour borrow. 20 bps maintenance.`
      : `${terms.baseBps} bps taker · ${terms.makerBps} bps maker · ${terms.liquidationBps} bps liquidation. Current ${terms.carryBps.toFixed(3)} bps/hour funding. First tier only. TP/SL run in this paper window.`;
  }
  let position = null;
  let warning = gap || broker?.note || '';
  const view = quote && broker ? broker.view(quote.price) : null;
  if (view?.position) position = view.position;
  else if (quote && !held && terms) {
    try {
      position = planPosition(settings(), terms, quote.price, direction());
      if (position.deposit > (broker?.equity ?? PAPER_CAPITAL)) throw new Error('Paper account has insufficient remaining capital.');
    } catch (error) {
      warning = error.message;
      position = null;
    }
  }
  if (position?.stop && position.direction * (position.stop - position.liquidation) <= 0) {
    warning = 'This stop is at or beyond estimated liquidation. Liquidation can occur first.';
  }
  for (const [key, line] of Object.entries(lines)) {
    const price = position?.[key];
    const visible = Number.isFinite(price) && price > 0;
    line.applyOptions({ price: visible ? price : 0, lineVisible: visible, axisLabelVisible: visible });
  }
  const fields = [
    ['Size', usd(position?.size)], ['Collateral', usd(position?.deposit)],
    ['Entry', usd(position?.entry)], ['Est. liquidation', usd(position?.liquidation)],
    ['Liq. distance', position ? `${(100 * Math.abs(1 - position.liquidation / position.entry)).toFixed(3)}%` : '—'],
    ['Take profit', bracket(position?.take)], ['Stop loss', bracket(position?.stop)], ['Open cost', usd(position?.openCost)],
  ];
  $('risk').replaceChildren(...fields.map(([name, value]) => {
    const group = document.createElement('div');
    const dt = document.createElement('dt');
    const dd = document.createElement('dd');
    dt.textContent = name; dd.textContent = value; group.append(dt, dd); return group;
  }));
  $('warning').textContent = warning;
  $('open').disabled = !position || locked;
  $('auto').disabled = !running && (!position || !preset || !history.length || !!held);
  $('auto').textContent = running ? 'Pause entries' : 'Start strategy';
  $('close').disabled = !held || !quote;
  $('performance').textContent = `${running ? 'Strategy active' : held ? 'Position open' : 'Paper idle'} · Equity ${usd(view?.equity ?? broker?.equity ?? PAPER_CAPITAL)} · Realized ${usd((broker?.equity ?? PAPER_CAPITAL) - PAPER_CAPITAL)} · ${broker?.ledger.length ?? 0} exits`;
  $('ledger').replaceChildren(...(broker?.ledger ?? []).slice(-5).reverse().map(row => {
    const item = document.createElement('li');
    item.textContent = `${utc(row.time)} · ${row.reason} · ${usd(row.pnl)}`;
    return item;
  }));
}

function latestDecision(preset, time, map) {
  if (!preset) return [0, undefined];
  const boundary = Math.floor(time / preset.step) * preset.step;
  return [boundary, time - boundary < 60 && map.has(boundary) ? map.get(boundary) : undefined];
}

function observe() {
  if (!broker || (!broker.position && !running)) return;
  const decisions = running && active ? signalMap(history, active) : null;
  for (const { time, price } of snapshot.points) {
    if (time <= lastPoint) continue;
    if (time - lastPoint > 25) {
      gap = 'Market observations were interrupted. Strategy entries are paused.';
      running = false;
      broker.signal = null;
    }
    const [boundary, planned] = latestDecision(running ? active : null, time, decisions);
    const decision = boundary > lastDecision ? planned : undefined;
    if (running && boundary > lastDecision && planned === undefined && time - boundary >= 45) {
      gap = 'The next closed signal candle is unavailable. Strategy entries are paused.';
      running = false;
      broker.signal = null;
    }
    if (running && decision !== undefined) lastDecision = boundary;
    broker.observe({ time, open: price, high: price, low: price, close: price }, {
      decision, decisionKind: running ? active.kind : 'manual', long: snapshot.long, short: snapshot.short,
    });
    lastPoint = time;
  }
}

async function refreshHistory() {
  const boundary = Math.floor(now() / 60) * 60;
  const from = history.length ? Math.max(boundary - 86400, (history.at(-1)?.time ?? boundary) - 120) : boundary - 86400;
  const reads = [];
  for (let cursor = from; cursor < boundary; cursor += 43200) {
    reads.push(readMinutes(asset, cursor, Math.min(boundary, cursor + 43200), lifetime.signal));
  }
  const byTime = new Map(history.filter(row => row.time >= boundary - 86400).map(row => [row.time, row]));
  for (const rows of await Promise.all(reads)) for (const row of rows) byTime.set(row.time, row);
  if (disposed) return;
  history = [...byTime.values()].sort((a, b) => a.time - b.time);
  refreshChart();
  lastHistory = now();
}

async function poll() {
  if (disposed || !market) return;
  const quote = readSnapshot(asset, lifetime.signal).then(value => {
    if (disposed) return;
    snapshot = value;
    feedIssue = '';
  }).catch(error => { feedIssue = error.message; });
  const chartRead = now() - lastHistory >= 12 ? refreshHistory().then(() => {
    historyIssue = history.length ? '' : 'Waiting for complete candles';
  }).catch(() => { historyIssue = 'Candle history unavailable'; }) : Promise.resolve();
  await Promise.all([quote, chartRead]);
  if (disposed) return;
  if (fresh()) observe();
  render();
  pollTimer = setTimeout(poll, 5000);
}

function newBroker() {
  const next = new PaperBroker(settings());
  if (broker) {
    next.equity = broker.equity;
    next.ledger = broker.ledger;
    next.peak = broker.peak;
    next.drawdown = broker.drawdown;
  }
  broker = next;
  gap = '';
  lastPoint = snapshot.mark.time;
}

if (market) {
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
    if (preset) {
      $('step').value = String(preset.step);
      if (preset.kind !== 'volty') $('direction').value = '1';
      $('exit-preset').value = 'original';
      $('tp').value = $('sl').value = '0';
    }
    refreshChart(true);
    render();
  });
  $('step').addEventListener('change', () => refreshChart(true));
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
  $('open').addEventListener('click', () => {
    if (!fresh() || running || broker?.position) return;
    newBroker();
    const side = direction();
    broker.open(lastPoint, snapshot.mark.price, side, side === 1 ? snapshot.long : snapshot.short, 1);
    render();
  });
  $('auto').addEventListener('click', () => {
    if (running) {
      running = false;
      broker.signal = null;
    } else if (fresh() && selection() && !broker?.position && history.length) {
      newBroker();
      active = selection();
      running = true;
      lastDecision = Math.floor(lastPoint / active.step) * active.step;
      if (active.kind === 'volty') broker.signal = signalMap(history, active).get(lastDecision) ?? null;
    }
    render();
  });
  $('close').addEventListener('click', () => {
    if (broker?.position && fresh()) {
      running = false;
      broker.close(snapshot.mark.time, { reason: 'manual', price: snapshot.mark.price });
      render();
    }
  });
  void poll();
} else $('status').textContent = 'Unsupported Perps market.';

window.addEventListener('pagehide', () => {
  disposed = true;
  clearTimeout(pollTimer);
  lifetime.abort();
  chart.remove();
}, { once: true });
