/**
 * MV3 service worker — the extension surface of the command registry.
 *
 * There is no long-lived process here. The worker is woken by an alarm, runs one
 * tick, and is free to die. Nothing may be held in module scope that the next
 * tick depends on: everything durable lives in IndexedDB or
 * chrome.storage.local, and the tick rebuilds its world from those plus the
 * venue's live state.
 *
 * `setInterval` would be the obvious way to schedule this and would be wrong —
 * the worker is terminated after ~30s idle and the timer dies with it.
 *
 * All message handling delegates to src/core/commands.js, the same registry the
 * CLI and HTTP API use. This file owns only what is genuinely Chrome-specific:
 * alarm scheduling, the badge, and message plumbing.
 */

import { Store, ConfigStore } from '../storage/store.js';
import { buildVenue, MODE, leverageFeasibility } from '../venues/index.js';
import { runCommand, COMMANDS, CommandError } from '../core/commands.js';
import { withStoreLock, enginePending } from '../core/engine.js';
import { checkForUpdate } from '../core/autoreload.js';
import { isEnvelope } from '../core/soltui.js';
import { createNativeTransport } from './soltui-transport.js';
import { DEFAULT_LIMITS } from '../core/risk.js';
import { RequestBudget } from '../jupiter/http.js';
import { makeSigner } from '../wallet/signer.js';
import { restorePaperVenue } from './paper-venue.js';
import { createLiveWindows } from './live-windows.js';
import { digest } from '../core/bot-manager.js';

const ALARM = 'solmargintrader-tick';
const MANAGER_ALARM = 'solmargintrader-manager';
let loadedHash;
async function loadedSourceHash() {
  loadedHash ??= Promise.all(['src/bg/service-worker.js', 'src/core/commands.js', 'src/core/bot-manager.js'].map(async path => {
    const response = await platformFetch(chrome.runtime.getURL(path));
    if (!response.ok) throw new Error('loaded browser source unavailable');
    return `${path}\0${await response.text()}`;
  })).then(parts => digest(parts.join('\0')));
  return loadedHash;
}

// Asks the soltui host once a minute whether the code on disk changed.
const BUILD_ALARM = 'solmargintrader-soltui-build';

// Re-reads holdings, the Aero scout, Top 5 and pool leads, and notifies on a
// better pool or strategy (src/core/alerts.js). Separate from the grid tick: it
// places nothing and runs whether or not the grid is armed.
const ALERT_ALARM = 'solmargintrader-alerts';

// Chrome clamps alarm periods; 30s is the floor on current versions. The engine
// records the ACTUAL wake delta so a clamp shows up in the UI instead of
// silently changing strategy behaviour.
const MIN_PERIOD_MINUTES = 0.5;

const configStore = new ConfigStore();

// One wrapper for the worker's lifetime: a bare `fetch` called off its global
// throws "Illegal invocation", and a fresh closure per message would defeat the
// pool cache, which keys on this function (src/market/pools.js).
const platformFetch = (...a) => fetch(...a);
const budget = new RequestBudget({ maxPerWindow: 30, windowMs: 60_000 });
const nativeTransport = createNativeTransport();
const liveWindows = chrome.runtime.onConnect && chrome.windows && chrome.runtime.getURL
  ? createLiveWindows({ runtime: chrome.runtime, windows: chrome.windows,
    getURL: path => chrome.runtime.getURL(path) }) : null;
const browserUiStore = {};

/**
 * Dependencies for the command registry, Chrome flavour.
 *
 * `passphrase` is never persisted: a full-auto session key can only be unsealed
 * while the user is present to supply it, which is the point.
 */
export async function chromeDeps({ passphrase, openStore = () => Store.open(), soltui = nativeTransport } = {}) {
  const store = await openStore();
  return {
    store,
    configStore,
    budget,
    soltui,
    extensionVersion: chrome.runtime.getManifest?.().version,
    loadedSourceHash,
    fetch: platformFetch,
    async buildVenue() {
      const config = await configStore.getConfig();
      const secrets = await configStore.get('secrets', {});
      const signer = await makeSigner({ mode: config.mode, passphrase });
      const venue = buildVenue({ config, signer, apiKey: secrets.apiKey, budget });
      return config.mode === MODE.DRY_RUN ? restorePaperVenue(venue, config, configStore) : venue;
    },
    clock: () => Date.now(),
    log: (e) => console[e.level === 'error' ? 'error' : 'warn']('[smt]', e.msg, e),
  };
}

/* ------------------------------------------------------------------- ticking -- */

async function runTick(reason) {
  const deps = await chromeDeps();
  const config = await configStore.getConfig();
  const manager = await configStore.get('browserManager', null);
  if (manager?.last_sequence > 0 && !manager.running && config.mode === MODE.DRY_RUN && !(await configStore.getRuntime()).armed) {
    return { errors: [], skipped: [{ reason: 'browser-paper-owner-stopped' }] };
  }

  // Refuse a config that claims leverage the venue cannot deliver, rather than
  // quietly trading unleveraged while the UI says 3x.
  const venue = await deps.buildVenue();
  const feasible = leverageFeasibility({
    venue,
    leverage: config.leverage,
    marginSource: config.marginSource,
  });
  if (!feasible.ok) {
    await deps.store.logEvent({ type: 'blocked', reason: feasible.reason });
    await setBadge('!', '#b91c1c');
    return { errors: [{ error: feasible.reason }] };
  }

  const result = await runCommand({ name: 'tick', args: {}, deps });
  await configStore.set('lastTick', { ...result, reason });
  await paintBadge(result);
  return result;
}

/** Alerts not yet acknowledged that are worth a look (modelled or backtest, not quoted leads). */
async function openAlertCount() {
  const [scan, acks] = await Promise.all([configStore.get('scan', null), configStore.get('alertAcks', [])]);
  const acked = new Set(Array.isArray(acks) ? acks : []);
  return (scan?.alerts ?? []).filter((a) => !acked.has(a.id) && a.severity !== 'info').length;
}

async function paintBadge(result) {
  if (result.errors?.length) return setBadge('!', '#b91c1c');
  // Called after lifecycle commands and scans with no tick in hand: an armed
  // grid's badge keeps showing the last tick's P&L, not a placeholder.
  if (result.pnl === undefined) result = { ...result, pnl: (await configStore.get('lastTick', null))?.pnl };
  const runtime = await configStore.getRuntime();
  if (runtime.killSwitch) return setBadge('OFF', '#b91c1c');
  if (!runtime.armed) {
    // The grid is not the point of the extension any more; with it idle, the
    // badge shows what needs the owner's attention instead.
    const open = await openAlertCount().catch(() => 0);
    return open ? setBadge(String(open), '#b45309') : setBadge('', '#6b7280');
  }
  const net = result.pnl?.totalNetUsd;
  if (net == null) return setBadge('•', '#2563eb');
  return setBadge(net >= 0 ? `+${net.toFixed(0)}` : net.toFixed(0), net >= 0 ? '#15803d' : '#b91c1c');
}

async function setBadge(text, color) {
  try {
    await chrome.action.setBadgeText({ text: String(text).slice(0, 4) });
    await chrome.action.setBadgeBackgroundColor({ color });
  } catch {
    /* the action API is unavailable in some contexts; the badge is cosmetic */
  }
}

async function rescheduleAlarm() {
  const config = await configStore.getConfig();
  const periodInMinutes = Math.max(MIN_PERIOD_MINUTES, (config.tickSeconds ?? 60) / 60);
  await chrome.alarms.clear(ALARM);
  await chrome.alarms.create(ALARM, { periodInMinutes });
  return periodInMinutes;
}

/** The alert scan follows prefs: its own interval, and no alarm at all when disabled. */
async function scheduleAlertAlarm({ soon = false } = {}) {
  const prefs = { alertsEnabled: true, alertIntervalMinutes: 60, ...(await configStore.get('prefs', {})) };
  await chrome.alarms.clear(ALERT_ALARM);
  if (prefs.alertsEnabled !== true) return null;
  const periodInMinutes = Math.min(1440, Math.max(15, Number(prefs.alertIntervalMinutes) || 60));
  await chrome.alarms.create(ALERT_ALARM, { periodInMinutes, delayInMinutes: soon ? 1 : periodInMinutes });
  return periodInMinutes;
}

/**
 * One alert scan. Notifies only for alerts that are new and unacknowledged, and
 * only for modelled or backtest alerts unless the owner asked for quoted leads.
 * The message is the alert's own title: it holds no address or balance detail
 * beyond what the dashboard shows.
 */
export async function runAlertScan({ notify = (alert) => showNotification(alert) } = {}) {
  const deps = await chromeDeps();
  const out = await runCommand({ name: 'scanAlerts', args: {}, deps });
  for (const alert of out.notify ?? []) {
    try { await notify(alert); } catch (err) { console.warn('[smt] notification failed', String(err?.message ?? err)); }
  }
  await paintBadge({ errors: [] });
  return out;
}

async function showNotification(alert) {
  if (!chrome.notifications?.create) return;
  await chrome.notifications.create(`smt-alert:${alert.id}`.slice(0, 500), {
    type: 'basic',
    iconUrl: chrome.runtime.getURL('icons/icon-128.png'),
    title: alert.severity === 'action' ? 'Better pool found' : alert.kind === 'strategy' ? 'Strategy alert' : 'Pool lead',
    message: String(alert.title).slice(0, 250),
    contextMessage: alert.source === 'modelled' ? 'Modelled by the Aero scout' : alert.source === 'backtest' ? 'Backtest evidence' : 'Quoted by DefiLlama',
    priority: alert.severity === 'action' ? 2 : 0,
  });
}

/** Creating an alarm with an existing name replaces it, so this is idempotent. */
async function scheduleBuildAlarm() {
  await chrome.alarms.create(BUILD_ALARM, { periodInMinutes: 1, delayInMinutes: 1 });
}

/**
 * One pass of the auto-reload gate. See src/core/autoreload.js for the rules;
 * this only wires them to Chrome: the engine lock, the event log and
 * chrome.runtime.reload. Nothing in the log or the state is a secret: a hash
 * prefix, the mode and the armed flag.
 */
export async function runBuildCheck({
  soltui = nativeTransport, store, reload = () => chrome.runtime.reload(), hold,
} = {}) {
  const target = store ?? (await Store.open());
  return checkForUpdate({
    deps: { soltui },
    state: configStore,
    // A dashboard holds replay/job state and unsaved forms. Reload only after it closes.
    pending: () => enginePending(target) + (soltui.busy?.() ? 2 : 0),
    withLock: (operation) => withStoreLock(target, operation),
    reload,
    ...(hold ? { hold } : {}),
    logEvent: async (event) => {
      try { await target.logEvent(event); } catch (err) {
        console.warn('[smt] could not log', event.type, String(err?.message ?? err));
      }
    },
    describe: async () => {
      const runtime = await configStore.getRuntime();
      return { armed: runtime.armed === true, killSwitch: runtime.killSwitch === true };
    },
  });
}

async function scheduleManagerAlarm() {
  if (!(await chrome.alarms.get?.(MANAGER_ALARM))) {
    await chrome.alarms.create(MANAGER_ALARM, { periodInMinutes: 0.5, delayInMinutes: 0.5 });
  }
}

export async function runManagerPoll() {
  return runCommand({ name: 'browserManagerPoll', args: {}, deps: await chromeDeps() });
}

// Listener registration stays synchronous. Re-create missing alarms after every
// worker activation, because Chrome does not guarantee alarm persistence.
scheduleManagerAlarm().catch(() => {});

/* ----------------------------------------------------------------- lifecycle -- */

/**
 * Chrome fires onInstalled for 'install', 'update' and 'chrome_update', so the
 * reason decides what may be reset.
 *
 * - install: fresh-install defaults. Explicitly disarmed, dry-run, kill switch
 *   clear. An extension that started trading the moment it was installed would
 *   be indefensible.
 * - anything else (an extension or browser update): the operator's state is
 *   theirs. The kill switch is a latched hard stop and an update must NEVER
 *   clear it; the stored mode is kept. The one thing an update changes is
 *   `armed`, forced to false: the new code has not been watched trading yet, so
 *   the operator re-arms on purpose. Keeping `mode` is safe because nothing
 *   trades while disarmed, and rewriting it would silently discard a deliberate
 *   semi-auto/full-auto choice without making anything safer.
 *
 * `store` is injectable for tests. The event log is best-effort and must never
 * stop the safety writes above it from landing.
 */
export async function handleInstalled(details = {}, { store } = {}) {
  const reason = details.reason ?? 'unknown';
  const fresh = reason === 'install';

  if (fresh) {
    await configStore.setRuntime({ armed: false, killSwitch: false });
    await configStore.setConfig({ mode: MODE.DRY_RUN });
  } else {
    await configStore.setRuntime({ armed: false });
  }
  const managed = await configStore.get('browserManager', null);
  if (managed?.running) await configStore.set('browserManager', { ...managed, running: false, generation: managed.generation + 1 });
  await configStore.set('limits', { ...DEFAULT_LIMITS, ...(await configStore.get('limits', {})) });
  await rescheduleAlarm();
  await scheduleBuildAlarm();
  await scheduleManagerAlarm();
  await scheduleAlertAlarm({ soon: true });

  const runtime = await configStore.getRuntime();
  const config = await configStore.getConfig();
  runManagerPoll().catch(() => {});
  if (fresh) await setBadge('—', '#6b7280');
  else await paintBadge({ errors: [] });

  try {
    const target = store ?? (await Store.open());
    await target.logEvent({
      type: fresh ? 'installed' : 'updated',
      reason,
      previousVersion: details.previousVersion ?? null,
      armed: false,
      killSwitch: runtime.killSwitch === true,
      mode: config.mode,
    });
  } catch (err) {
    console.warn('[smt] could not log lifecycle event', String(err?.message ?? err));
  }
}

chrome.runtime.onInstalled.addListener((details) => {
  handleInstalled(details).catch((err) => console.error('[smt] onInstalled threw', err));
});

chrome.runtime.onStartup.addListener(() => {
  scheduleManagerAlarm().catch(() => {});
  runManagerPoll().catch(() => {});
  rescheduleAlarm().catch((err) => console.error('[smt] reschedule threw', err));
  scheduleBuildAlarm().catch((err) => console.error('[smt] build alarm threw', err));
  scheduleAlertAlarm({ soon: true }).catch((err) => console.error('[smt] alert alarm threw', err));
});

// A notification opens the dashboard on the Alerts tab.
chrome.notifications?.onClicked?.addListener((id) => {
  if (!String(id).startsWith('smt-alert:')) return;
  chrome.tabs.create({ url: chrome.runtime.getURL('src/ui/dashboard.html#alerts') }).catch(() => {});
  chrome.notifications.clear(id).catch?.(() => {});
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === MANAGER_ALARM) { runManagerPoll().catch(() => {}); return; }
  if (alarm.name === BUILD_ALARM) {
    runBuildCheck().catch((err) => console.error('[smt] build check threw', String(err?.message ?? err)));
    return;
  }
  if (alarm.name === ALERT_ALARM) {
    runAlertScan().catch((err) => console.error('[smt] alert scan threw', String(err?.message ?? err)));
    return;
  }
  if (alarm.name !== ALARM) return;
  // Errors are swallowed here on purpose: an unhandled rejection in an alarm
  // handler tears down the worker before the journal is flushed.
  runTick('alarm').catch((err) => console.error('[smt] tick threw', err));
});

/* ------------------------------------------------------------------ messages -- */

/**
 * Legacy message names kept for the bundled UI. New callers should use the
 * registry name directly.
 */
const ALIASES = { tickNow: 'tick' };

chrome.runtime.onMessage.addListener((msg, sender, respond) => {
  if (['browserManagerPoll', 'browserManagerSnapshot'].includes(msg?.type)) {
    const origin = chrome.runtime.getURL('').replace(/\/$/, '');
    if (sender?.origin !== origin && !String(sender?.url ?? '').startsWith(`${origin}/`)) {
      respond({ ok: false, error: 'browser owner messages require an extension origin' });
      return false;
    }
  }
  handleMessage(msg)
    .then(respond)
    .catch((err) => respond({ ok: false, error: String(err?.message ?? err) }));
  return true; // keep the channel open for the async reply
});

export async function handleMessage(msg, { openStore, soltui } = {}) {
  const requested = msg?.type;
  const name = ALIASES[requested] ?? requested;

  if (!name || !COMMANDS[name]) {
    return {
      ok: false,
      error: `unknown message type "${requested}"`,
      known: Object.keys(COMMANDS),
    };
  }

  const { type, passphrase, ...args } = msg;
  // The passphrase also unlocks the session key inside the chrome deps, but a
  // command that DECLARES it (createSessionKey) needs it in its own args too:
  // runCommand rejects a missing required param. A command that does not
  // declare it must not receive it, or runCommand rejects it as unknown.
  if (passphrase !== undefined && COMMANDS[name].params.some((p) => p.name === 'passphrase')) {
    args.passphrase = passphrase;
  }
  // The PiP gesture crosses the synchronous message→Port relay. Opening the
  // order store first would discard it; UI commands never receive trading deps.
  const deps = COMMANDS[name].browserUi ? { store: browserUiStore, liveWindows }
    : await chromeDeps({ passphrase, openStore, ...(soltui ? { soltui } : {}) });

  try {
    const result = await runCommand({ name, args, deps });

    // A config or tick change can alter the tick period, so reschedule after
    // anything that writes.
    if (name === 'setConfig') await rescheduleAlarm();
    if (name === 'arm') await rescheduleAlarm();
    if (name === 'kill' || name === 'disarm') await paintBadge({ errors: [] });
    if (name === 'setPrefs') await scheduleAlertAlarm();
    if (name === 'scanAlerts') {
      // A scan from the popup or dashboard stores its fresh alerts as seen, so
      // the alarm scan would never notify them: deliver here as well.
      for (const alert of result.notify ?? []) {
        try { await showNotification(alert); } catch (err) { console.warn('[smt] notification failed', String(err?.message ?? err)); }
      }
    }
    if (name === 'scanAlerts' || name === 'ackAlerts') await paintBadge({ errors: [] });

    // Spread for the UI's existing field access (res.config, res.runtime, ...)
    // and expose `result` for generic callers. A soltui envelope has its own
    // ok/error, which spreading would overwrite or leak into the top level, so
    // it is returned only as `result`, byte-for-byte what the CLI and API give.
    return { ok: true, ...(isEnvelope(result) ? {} : result), result };
  } catch (err) {
    if (err instanceof CommandError) return { ok: false, error: err.message, status: err.status };
    throw err;
  }
}
