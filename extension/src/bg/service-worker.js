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
import { DEFAULT_LIMITS } from '../core/risk.js';
import { RequestBudget } from '../jupiter/http.js';
import { makeSigner } from '../wallet/signer.js';

const ALARM = 'solmargintrader-tick';

// Chrome clamps alarm periods; 30s is the floor on current versions. The engine
// records the ACTUAL wake delta so a clamp shows up in the UI instead of
// silently changing strategy behaviour.
const MIN_PERIOD_MINUTES = 0.5;

const configStore = new ConfigStore();
const budget = new RequestBudget({ maxPerWindow: 30, windowMs: 60_000 });

/**
 * Dependencies for the command registry, Chrome flavour.
 *
 * `passphrase` is never persisted: a full-auto session key can only be unsealed
 * while the user is present to supply it, which is the point.
 */
async function chromeDeps({ passphrase } = {}) {
  const store = await Store.open();
  return {
    store,
    configStore,
    budget,
    async buildVenue() {
      const config = await configStore.getConfig();
      const secrets = await configStore.get('secrets', {});
      const signer = await makeSigner({ mode: config.mode, passphrase });
      return buildVenue({ config, signer, apiKey: secrets.apiKey, budget });
    },
    clock: () => Date.now(),
    log: (e) => console[e.level === 'error' ? 'error' : 'warn']('[smt]', e.msg, e),
  };
}

/* ------------------------------------------------------------------- ticking -- */

async function runTick(reason) {
  const deps = await chromeDeps();
  const config = await configStore.getConfig();

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

async function paintBadge(result) {
  if (result.errors?.length) return setBadge('!', '#b91c1c');
  const runtime = await configStore.getRuntime();
  if (runtime.killSwitch) return setBadge('OFF', '#b91c1c');
  if (!runtime.armed) return setBadge('—', '#6b7280');
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

/* ----------------------------------------------------------------- lifecycle -- */

chrome.runtime.onInstalled.addListener(async () => {
  // Explicitly disarmed and dry-run on install. An extension that started
  // trading the moment it was installed would be indefensible.
  await configStore.setRuntime({ armed: false, killSwitch: false });
  await configStore.setConfig({ mode: MODE.DRY_RUN });
  await configStore.set('limits', { ...DEFAULT_LIMITS, ...(await configStore.get('limits', {})) });
  await rescheduleAlarm();
  await setBadge('—', '#6b7280');
});

chrome.runtime.onStartup.addListener(rescheduleAlarm);

chrome.alarms.onAlarm.addListener((alarm) => {
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

chrome.runtime.onMessage.addListener((msg, _sender, respond) => {
  handleMessage(msg)
    .then(respond)
    .catch((err) => respond({ ok: false, error: String(err?.message ?? err) }));
  return true; // keep the channel open for the async reply
});

export async function handleMessage(msg) {
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
  const deps = await chromeDeps({ passphrase });

  try {
    const result = await runCommand({ name, args, deps });

    // A config or tick change can alter the tick period, so reschedule after
    // anything that writes.
    if (name === 'setConfig') await rescheduleAlarm();
    if (name === 'arm') await rescheduleAlarm();
    if (name === 'kill' || name === 'disarm') await paintBadge({ errors: [] });

    // Spread for the UI's existing field access (res.config, res.runtime, ...)
    // and expose `result` for generic callers.
    return { ok: true, ...result, result };
  } catch (err) {
    if (err instanceof CommandError) return { ok: false, error: err.message, status: err.status };
    throw err;
  }
}
