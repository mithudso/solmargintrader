/**
 * Dashboard shell: hash routing between views, the top bar, the stored scan,
 * and Settings.
 *
 * Views load on first visit and on their own Refresh buttons; Overview paints
 * from the stored scan first so the page is useful before any network answers.
 * Every action goes through a registry command (src/core/commands.js) — this
 * page holds no trading or alert logic of its own.
 */

import { attributionLine, attributionDetail } from '../jupiter/attribution.js';
import { mountSoltuiPanel } from './soltui-panel.js';
import { mountWalletPubkeyButton } from './wallet-pubkey.js';
import { call, soltui, $, ago, observeSortableTables } from './ui-kit.js';
import { renderOverview, renderAlerts, mountAlertPrefs } from './view-overview.js';
import { renderHoldings, refreshHoldings, mountHoldings, refreshPnl, mountPnl, refreshScout, refreshPools, mountDiscover } from './view-markets.js';
import { refreshStrategies, mountStrategies, refreshSwap, mountSwap } from './view-trade.js';
import { refreshGrid, mountGrid } from './view-grid.js';

observeSortableTables(document);

const send = (msg) => chrome.runtime.sendMessage(msg);

// The version is the only visible sign that a reload picked up new code.
document.getElementById('version').textContent = `v${chrome.runtime.getManifest().version}`;

const state = { overview: null, holdings: null, loaded: new Set() };

/* --------------------------------------------------------------- shared -- */

async function loadOverview() {
  state.overview = await call({ type: 'overview' });
  const scan = state.overview?.scan;
  $('#scanInfo').textContent = scan ? `Last scan ${ago(scan.scannedAtMs)}` : 'No scan yet';
  const open = (scan?.alerts ?? []).filter((a) => !a.acked && a.severity !== 'info').length;
  $('#navAlertCount').hidden = open === 0;
  $('#navAlertCount').textContent = String(open);
}

async function ack(id) {
  await call({ type: 'ackAlerts', id });
  await loadOverview();
  repaint();
}

const onAck = (id) => ack(id).catch((err) => { $('#scanInfo').textContent = `Could not acknowledge: ${err.message}`; });

/* --------------------------------------------------------------- routing -- */

// Old links (popup's "SolTUI console", bookmarks) land on the view holding them.
const ALIASES = {};
const VIEWS = {
  soltui: { load: () => {} },
  overview: { load: () => renderOverview(state, { onAck }) },
  holdings: { load: () => refreshHoldings(state) },
  pnl: { load: refreshPnl },
  discover: { load: () => Promise.all([refreshScout(), refreshPools()]) },
  strategies: { load: () => refreshStrategies(state) },
  swap: { load: () => refreshSwap(state) },
  alerts: { load: () => renderAlerts(state, { onAck }) },
  settings: { load: loadSettings },
  grid: { load: refreshGrid },
};

function current() {
  const raw = location.hash.slice(1).split('/')[0] || 'soltui';
  const name = ALIASES[raw] ?? raw;
  return Object.hasOwn(VIEWS, name) ? name : 'overview';
}

function show() {
  const name = current();
  for (const section of document.querySelectorAll('[data-view]')) section.hidden = section.dataset.view !== name;
  for (const link of document.querySelectorAll('.nav-link')) {
    if (link.getAttribute('href') === location.hash || (link.getAttribute('href') === '#soltui/signal' && (!location.hash || location.hash === '#soltui'))) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }

  // Overview and Alerts repaint every visit (they are cheap); the rest load once.
  if (!state.loaded.has(name) || name === 'overview' || name === 'alerts') {
    state.loaded.add(name);
    Promise.resolve(VIEWS[name].load()).catch((err) => console.warn('[smt] view failed', name, err));
  }
}

function repaint() {
  const name = current();
  if (name === 'overview') renderOverview(state, { onAck });
  if (name === 'alerts') renderAlerts(state, { onAck });
  if (name === 'holdings') renderHoldings(state);
}

/* -------------------------------------------------------------- settings -- */

async function loadSettings() {
  const prefs = state.overview?.prefs ?? (await call({ type: 'getPrefs' }));
  const f = $('#walletForm').elements;
  f.baseAddress.value = prefs.baseAddress ?? '';
  f.solanaAddress.value = prefs.solanaAddress ?? '';
}

function mountSettings() {
  $('#walletForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = e.target.elements;
    const patch = {
      baseAddress: f.baseAddress.value.trim() || null,
      solanaAddress: f.solanaAddress.value.trim() || null,
    };
    try {
      await call({ type: 'setPrefs', patch });
      $('#walletStatus').textContent = 'Saved. Holdings now read these addresses.';
      state.holdings = null;
      await loadOverview();
    } catch (err) {
      $('#walletStatus').textContent = `Not saved: ${err.message}`;
    }
  });
  $('#walletFromSoltui').addEventListener('click', async () => {
    try {
      const r = await soltui('wallet.addresses');
      const f = $('#walletForm').elements;
      if (r.base_address) f.baseAddress.value = r.base_address;
      if (r.solana_address) f.solanaAddress.value = r.solana_address;
      $('#walletStatus').textContent = 'Filled from soltui. Check them, then Save.';
    } catch (err) {
      $('#walletStatus').textContent = `soltui: ${err.message}`;
    }
  });
  $('#keyForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = $('#keyForm input[name="apiKey"]');
    await send({ type: 'setApiKey', apiKey: input.value });
    input.value = ''; // do not leave the key sitting in the DOM
  });
}

/* ------------------------------------------------------------------ boot -- */

$('#scanNow').addEventListener('click', async () => {
  const button = $('#scanNow');
  button.disabled = true;
  $('#scanInfo').textContent = 'Scanning holdings, the Aero scout, Top 5 and pools…';
  try {
    const r = await call({ type: 'scanAlerts' });
    state.holdings = r.scan.holdings ? { ...r.scan.holdings, addressSource: state.holdings?.addressSource } : state.holdings;
    await loadOverview();
    repaint();
  } catch (err) {
    $('#scanInfo').textContent = `Scan failed: ${err.message}`;
  } finally {
    button.disabled = false;
  }
});

$('#ackAll').addEventListener('click', async () => {
  await call({ type: 'ackAlerts', all: true }).catch(() => null);
  await loadOverview();
  repaint();
});

// Licence-required attribution (agreement 8.4 and 2.3), rendered from the
// module that imports the real base URLs so it cannot drift from what we call.
$('#attribution').textContent = attributionLine();
$('#attributionDetail').textContent = attributionDetail();

mountGrid();
mountSettings();
mountHoldings(state);
mountPnl();
mountDiscover();
mountStrategies(state);
mountSwap(state);
mountAlertPrefs(async () => { await loadOverview(); repaint(); });

// Fills the grid's Wallet pubkey field from soltui; the owner still clicks Save.
mountWalletPubkeyButton(document, send);

// Independent of everything else: a missing soltui host must not stop the
// rest of the dashboard from loading.
mountSoltuiPanel().catch((err) => {
  $('#soltuiStatus').textContent = `SolTUI panel failed to load: ${err.message}`;
});

// The grid's status feeds the mode pill and the Grid tab's forms.
refreshGrid().then(async () => {
  const status = await send({ type: 'status' });
  if (status?.ok) $('#gridModePill').textContent = `${status.config.mode}${status.runtime.armed ? ' · armed' : ''}${status.runtime.killSwitch ? ' · KILLED' : ''}`;
}).catch((err) => {
  $('#banner').textContent = `Grid failed to load: ${err.message}`;
  $('#banner').className = 'banner danger';
});

window.addEventListener('hashchange', () => { show(); const heading = document.querySelector('[data-view]:not([hidden]) h1'); if (heading) { heading.tabIndex = -1; heading.focus({ preventScroll: true }); } });
loadOverview().catch(() => null).finally(show);
