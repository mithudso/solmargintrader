/**
 * Popup: status at a glance, plus arm / disarm / kill.
 *
 * All state comes from the service worker over messages. The popup holds no
 * strategy logic — it can be closed mid-tick without consequence, and it must
 * never be the thing that decides whether an order is placed.
 */

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
    banner.textContent = 'Disarmed. Dry run only; nothing is being placed.';
    banner.className = 'banner';
  } else {
    banner.textContent = 'Dry run armed — simulating fills, placing nothing.';
    banner.className = 'banner ok';
  }
  banner.classList.remove('hidden');

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

refresh().catch((err) => showError(String(err.message ?? err)));
