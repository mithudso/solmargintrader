/**
 * Popup: holdings and alerts at a glance, shortcuts into the dashboard, and the
 * grid's arm / disarm / kill controls (collapsed: the grid is experimental).
 *
 * All state comes from the service worker over messages. The popup holds no
 * strategy logic — it can be closed mid-tick without consequence, and it must
 * never be the thing that decides whether an order is placed. It paints from
 * the stored scan (overview) so it opens instantly, without waiting on RPC.
 */

import { aggregatePredictions, agreementUnavailableReason, scoreText } from './live-score.js';
import { attributionLine } from '../jupiter/attribution.js';
import { predictionRecovery, renderPredictionRecovery } from './prediction-recovery.js';

const $ = (id) => document.getElementById(id);
const send = (msg) => chrome.runtime.sendMessage(msg);

const usd = (n) =>
  n == null ? '—' : `${n < 0 ? '−' : ''}$${Math.abs(n).toFixed(2)}`;

function paintPnl(el, value) {
  el.textContent = usd(value);
  el.classList.toggle('pos', value > 0);
  el.classList.toggle('neg', value < 0);
}

async function refresh() {
  const res = await send({ type: 'status' });
  if (!res?.ok) return showError(res?.error ?? 'service worker did not respond');

  const { config, runtime, lastTick } = res;

  $('mode').textContent = config.mode;
  $('mode').className = `pill ${config.mode === 'dry-run' ? 'safe' : 'live'}`;

  const banner = $('banner');
  if (runtime.killSwitch) {
    banner.textContent = 'Kill switch engaged — no orders will be placed.';
    banner.className = 'banner danger';
  } else if (config.mode !== 'dry-run') {
    banner.textContent = `LIVE (${config.mode}) — real orders, real funds.`;
    banner.className = 'banner warn';
  } else if (!runtime.armed) {
    banner.textContent = 'Disarmed. The grid is in dry run; nothing is being placed.';
    banner.className = 'banner';
  } else {
    banner.textContent = 'Dry run armed — simulating fills, placing nothing.';
    banner.className = 'banner ok';
  }
  banner.classList.remove('hidden');

  // Licence-required attribution, from the one module that knows which Jupiter
  // APIs this extension actually calls.
  $('attribution').textContent = attributionLine();

  $('price').textContent = lastTick?.price ? `$${lastTick.price.toFixed(4)}` : '—';
  paintPnl($('net'), lastTick?.pnl?.totalNetUsd);
  paintPnl($('realized'), lastTick?.pnl?.realizedNetUsd);
  paintPnl($('unrealized'), lastTick?.pnl?.unrealizedNetUsd);
  // A trailing "?" when some fill's fee was never reported by the venue: the
  // total is a floor, not the real figure, and a bare number would claim
  // otherwise.
  $('fees').textContent =
    usd(lastTick?.pnl?.feeTotalUsd) + (lastTick?.feeUnknownFills > 0 ? '?' : '');
  $('trips').textContent =
    lastTick?.pnl?.roundTripCount != null
      ? `${lastTick.pnl.roundTripCount} (${(lastTick.pnl.winRate * 100).toFixed(0)}% win)`
      : '—';
  $('resting').textContent = lastTick?.placed != null ? String(lastTick.placed) : '—';

  $('lastTick').textContent = runtime.lastTickMs
    ? `${Math.round((Date.now() - runtime.lastTickMs) / 1000)}s ago` +
      (runtime.lastTickDeltaMs ? ` (every ${Math.round(runtime.lastTickDeltaMs / 1000)}s)` : '')
    : 'never';

  $('arm').disabled = runtime.armed || runtime.killSwitch;
  $('disarm').disabled = !runtime.armed;
  $('clearKill').classList.toggle('hidden', !runtime.killSwitch);

  if (lastTick?.errors?.length) showError(lastTick.errors[0].error);
  else $('err').classList.add('hidden');
}

function showError(text) {
  const el = $('err');
  el.textContent = text;
  el.classList.remove('hidden');
}

async function act(msg) {
  const res = await send(msg);
  if (!res?.ok) showError(res?.error ?? 'action failed');
  await refresh();
}

// Arming a live mode spends real money, so it takes a typed confirmation.
// Deliberately NOT window.prompt(): Chrome suppresses modal dialogs in an
// extension popup, which would either no-op or close the popup outright.
$('arm').addEventListener('click', async () => {
  const { config } = await send({ type: 'status' });
  if (config.mode !== 'dry-run') {
    $('confirmRow').classList.remove('hidden');
    $('confirmText').value = '';
    $('confirmText').focus();
    return;
  }
  return act({ type: 'arm' });
});

$('confirmArm').addEventListener('click', async () => {
  if ($('confirmText').value.trim() !== 'ARM') {
    showError('type ARM exactly to confirm live trading');
    return;
  }
  $('confirmRow').classList.add('hidden');
  await act({ type: 'arm', confirmLive: true });
});

$('cancelArm').addEventListener('click', () => {
  $('confirmRow').classList.add('hidden');
});

$('disarm').addEventListener('click', () => act({ type: 'disarm' }));
$('kill').addEventListener('click', () => act({ type: 'kill' }));
$('clearKill').addEventListener('click', () => act({ type: 'clearKill' }));
$('tickNow').addEventListener('click', () => act({ type: 'tickNow' }));
$('openDashboard').addEventListener('click', () => chrome.runtime.openOptionsPage());
const openView = (view) => chrome.tabs.create({ url: chrome.runtime.getURL(`src/ui/dashboard.html#${view}`) });
for (const tile of document.querySelectorAll('[data-view], [data-extra-view]')) {
  tile.addEventListener('click', () => openView(tile.dataset.view ?? tile.dataset.extraView));
}
$('openAlerts').addEventListener('click', () => openView('alerts'));
$('openGrid').addEventListener('click', () => openView('grid'));
// The SolTUI panel lives on the dashboard; the anchor scrolls straight to it.
$('openSoltui').addEventListener('click', () =>
  chrome.tabs.create({ url: chrome.runtime.getURL('src/ui/dashboard.html#soltui/signal') }));
// The version is the only visible sign that a reload picked up new code.
$('version').textContent = `v${chrome.runtime.getManifest().version}`;

/* ------------------------------------------------------- holdings + alerts -- */

const ago = (ms) => {
  if (!Number.isFinite(ms)) return '';
  const m = Math.round((Date.now() - ms) / 60000);
  return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : `${Math.round(m / 60)} h ago`;
};

function paintHoldings(h) {
  if (!h) return;
  $('total').textContent = (h.complete ? '' : '≥ ') + usd(h.totalUsd);
  const chain = (name) => h.chains?.find((c) => c.chain === name);
  const line = (name, label) => {
    const c = chain(name);
    if (!c || c.status === 'skipped') return `${label} —`;
    return c.status === 'failed' ? `${label} read failed` : `${label} ${usd(c.totalUsd)}`;
  };
  $('baseTotal').textContent = line('base', 'Base');
  $('solTotal').textContent = line('solana', 'Solana');
  $('scanAge').textContent = ago(h.atMs);
}

// Built with DOM calls only: alert titles carry pool and token names from
// third-party feeds, and this page holds extension privileges.
function paintAlerts(scan) {
  const box = $('alerts');
  const open = (scan?.alerts ?? []).filter((a) => !a.acked);
  if (!open.length) {
    const p = document.createElement('p');
    p.className = 'note';
    p.textContent = scan ? 'Nothing needs attention.' : 'No scan yet — press Scan.';
    box.replaceChildren(p);
    return;
  }
  box.replaceChildren(...open.slice(0, 3).map((a) => {
    const row = document.createElement('div');
    row.className = `alert ${a.severity}`;
    const bar = document.createElement('div');
    bar.className = 'bar';
    const text = document.createElement('div');
    const title = document.createElement('div');
    title.className = 'title';
    title.textContent = a.title;
    const meta = document.createElement('div');
    meta.className = 'meta';
    meta.textContent = a.source === 'modelled' ? 'modelled (Aero scout)' : a.source === 'backtest' ? 'backtest' : 'quoted lead';
    text.append(title, meta);
    row.append(bar, text, document.createElement('div'));
    return row;
  }));
}

async function refreshOverview() {
  const res = await send({ type: 'overview' });
  if (!res?.ok) return;
  paintHoldings(res.scan?.holdings);
  paintAlerts(res.scan);
  // A scan older than an hour is refreshed in the background; the popup has
  // already painted the stored one.
  if (!res.scan || Date.now() - res.scan.scannedAtMs > 60 * 60_000) scan();
}

async function scan() {
  $('scanNow').disabled = true;
  $('scanAge').textContent = 'scanning…';
  try {
    const res = await send({ type: 'scanAlerts' });
    if (res?.ok) {
      paintHoldings(res.scan?.holdings);
      paintAlerts(res.scan);
    } else {
      $('scanAge').textContent = `scan failed: ${res?.error ?? 'no answer'}`;
    }
  } finally {
    $('scanNow').disabled = false;
  }
}

$('scanNow').addEventListener('click', scan);

refresh().catch((err) => showError(String(err.message ?? err)));
refreshOverview().catch(() => {});


// A transient popup reads status once; it owns no recorder, trainer or session lease.
let glanceCommands = [], glanceBusy = false;
const glanceRecovery = predictionRecovery({
  supports: (name) => glanceCommands.some((c) => c.name === name),
  ask: async (command, params) => {
    const res = await send({ type: 'soltuiCall', command, params });
    if (!res?.ok) throw new Error(res?.error ?? 'Native host unavailable');
    return res.result;
  },
  changed: (state) => renderPredictionRecovery($('glanceRecovery'), state, {
    start: () => glanceRecovery.start(), href: chrome.runtime.getURL('src/ui/dashboard.html#soltui/forward'), newTab: true,
  }),
});
async function refreshGlance() {
  if (glanceBusy) return;
  glanceBusy = true;
  try {
  const saved = await chrome.storage.local.get('signalDesk.v1');
  const value = saved?.['signalDesk.v1']?.asset;
  const asset = typeof value === 'string' && /^[A-Z0-9]{1,20}$/.test(value) ? value : 'SOL';
  $('glanceAsset').textContent = `${asset} / USD`;
  const listing = await send({ type: 'soltuiCommands' });
  const commands = listing?.result?.result;
  if (!listing?.ok || !listing.result?.ok || !Array.isArray(commands)) throw new Error('Native host unavailable. Open the workspace to reconnect.');
  glanceCommands = commands;
  const read = async (command, params = {}) => {
    if (!commands.some((c) => c.name === command && c.read_only && !c.requires_confirm && !c.long_running)) return null;
    const res = await send({ type: 'soltuiCall', command, params });
    return res?.ok && res.result?.ok ? res.result.result : null;
  };
  const [prices, predictions, forward, trainer] = await Promise.all([
    read('prices.status'), read('forwardtest.predictions', { asset }),
    read('forwardtest.state'), read('compound.unattended_status', { asset }),
  ]);
  const aggregate = aggregatePredictions(predictions?.rows ?? [], Date.now() / 1000, predictions?.voting);
  $('glanceScore').textContent = aggregate.available ? `${scoreText(aggregate)} · ${aggregate.label}` : 'Agreement unavailable';
  $('glanceScore').className = `glance-value signal-score-${aggregate.available ? aggregate.color : 'gray'}`;
  const q = prices?.prices?.[`${asset}-USD`];
  const price = q?.mid ?? q?.last;
  const usable = typeof price === 'number' && Number.isFinite(price) && price > 0;
  $('glancePrice').textContent = usable ? `$${price.toLocaleString()} · ${q.quote_age_s ?? 'unknown'}s old at capture · ${prices.live ? 'recorder fresh' : 'last known / stale'}` : 'No usable recorder quote. Opening this popup starts no recorder.';
  $('glanceAge').textContent = `Read ${new Date().toISOString().slice(11, 19)} UTC · ${aggregate.available ? 'agreement is not success probability' : agreementUnavailableReason(predictions)}`;
  const running = (v) => typeof v === 'boolean' ? (v ? 'running' : 'stopped') : 'unavailable';
  $('glanceProcesses').textContent = `Recorder ${running(prices?.running)} · prediction checks ${running(forward?.running)} · ${asset} detached trainer ${running(trainer?.running)}`;
  await glanceRecovery.update(asset, predictions);
  } finally { glanceBusy = false; }
}
const readGlance = () => refreshGlance().catch((e) => {
  $('glancePrice').textContent = e.message; $('glanceAge').textContent = 'Prediction data unavailable.';
  renderPredictionRecovery($('glanceRecovery'), { needed: true, message: 'Open Forward testing to reconnect.', can_start: false });
});
readGlance();
const glanceTimer = setInterval(readGlance, 10_000);
window.addEventListener('pagehide', () => { clearInterval(glanceTimer); glanceRecovery.dispose(); }, { once: true });
