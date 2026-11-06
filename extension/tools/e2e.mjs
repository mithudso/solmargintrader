#!/usr/bin/env node
/**
 * Real-browser end-to-end check.
 *
 * Loads the unpacked extension into Chrome for Testing, drives the real service
 * worker, popup and dashboard over the DevTools pipe, and asserts what a human
 * would otherwise have to click through at chrome://extensions.
 *
 *   node tools/e2e.mjs                       newest Chrome for Testing in ~/.cache/puppeteer
 *   CHROME=/path/to/chrome node tools/e2e.mjs
 *   E2E_NO_SANDBOX=1 node tools/e2e.mjs      containers and CI runners without user namespaces
 *
 * Scope, stated plainly: this verifies LOADING and DRY-RUN behaviour. It never
 * arms the extension, never signs, never sends a message that can change mode,
 * limits or keys (see e2e/lib/guard.mjs), and it blocks every network request
 * except a stubbed Jupiter price read. It proves nothing about live orders.
 *
 * Exit codes: 0 all checks passed, 1 a check failed, 2 no usable browser.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { findChromeForTesting, launch } from '../e2e/lib/cdp.mjs';
import { assertAllowedMessage, assertDisarmed } from '../e2e/lib/guard.mjs';

const EXT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SOL = 'So11111111111111111111111111111111111111112';
const USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
const STUB_PRICE = 75;
const CANARY = 'e2e-canary-api-key-7d1f0c9a52b84e63';

/* ----------------------------------------------------------------- reporting -- */

const results = [];
async function check(name, fn) {
  try {
    await fn();
    results.push({ name, ok: true });
    console.log(`ok   - ${name}`);
  } catch (err) {
    results.push({ name, ok: false, err });
    console.log(`FAIL - ${name}\n         ${String(err?.message ?? err).split('\n')[0]}`);
  }
}
function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}
function eq(actual, expected, msg) {
  assert(JSON.stringify(actual) === JSON.stringify(expected), `${msg}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

/* -------------------------------------------------------------------- launch -- */

const chromePath = process.env.CHROME || findChromeForTesting();
if (!chromePath || !fs.existsSync(chromePath)) {
  console.error(
    'e2e: no Chrome for Testing found. Install one with\n' +
      '  npx @puppeteer/browsers install chrome@stable\n' +
      'or set CHROME to a Chrome for Testing / Chromium 126+ binary. Branded Chrome cannot load\n' +
      'an unpacked extension from the command line, so it cannot be used here.',
  );
  process.exit(2);
}

let browser;
try {
  browser = await launch({
    chrome: chromePath,
    extension: EXT,
    noSandbox: process.env.E2E_NO_SANDBOX === '1',
  });
} catch (err) {
  console.error(`e2e: could not launch ${chromePath}: ${err.message}`);
  process.exit(2);
}
console.log(`browser   ${browser.version}\nextension ${browser.extensionId}\n`);

const watchdog = setTimeout(async () => {
  console.error('e2e: global timeout');
  await browser.close().catch(() => {});
  process.exit(1);
}, 120_000);
watchdog.unref();

/* ----------------------------------------------------- network: stub and audit -- */

/** Every request any extension target made, so the checks can audit them. */
const requests = [];
const pageErrors = [];

const priceBody = JSON.stringify({
  [SOL]: { usdPrice: STUB_PRICE, decimals: 9 },
  [USDC]: { usdPrice: 1, decimals: 6 },
});

browser.on((m) => {
  if (m.method === 'Runtime.exceptionThrown') {
    const d = m.params.exceptionDetails;
    pageErrors.push(d.exception?.description || d.text);
  }
  if (m.method !== 'Fetch.requestPaused') return;
  const { requestId, request } = m.params;
  const url = new URL(request.url);
  requests.push({ method: request.method, url: `${url.origin}${url.pathname}` });
  // Only the keyless price read is allowed, and it is answered locally: nothing
  // leaves the machine, so no order endpoint is reachable even by mistake.
  const isPriceRead =
    request.method === 'GET' && url.origin === 'https://lite-api.jup.ag' && url.pathname === '/price/v3';
  const reply = isPriceRead
    ? browser.call('Fetch.fulfillRequest', {
        requestId,
        responseCode: 200,
        responseHeaders: [
          { name: 'content-type', value: 'application/json' },
          { name: 'access-control-allow-origin', value: '*' },
        ],
        body: Buffer.from(priceBody).toString('base64'),
      }, m.sessionId)
    : browser.call('Fetch.failRequest', { requestId, errorReason: 'BlockedByClient' }, m.sessionId);
  reply.catch(() => {});
});

/* --------------------------------------------------------------- target helpers -- */

const origin = `chrome-extension://${browser.extensionId}`;

async function findTarget(pred) {
  return browser.waitFor(async () => (await browser.targets()).find(pred), 10_000);
}

async function openPage(file) {
  const { targetId } = await browser.call('Target.createTarget', { url: `${origin}/${file}` });
  const sessionId = await browser.attach(targetId);
  await browser.call('Runtime.enable', {}, sessionId);
  await browser.call('Log.enable', {}, sessionId);
  return { targetId, sessionId, ev: (expr) => browser.evaluate(sessionId, expr) };
}

/** Send one allowlisted message to the real service worker from an extension page. */
function sender(page) {
  return async (type, args = {}) => {
    assertAllowedMessage(type);
    return page.ev(`chrome.runtime.sendMessage(${JSON.stringify({ type, ...args })})`);
  };
}

let failed = false;
try {
  /* ----------------------------------------------------------- service worker -- */

  let sw;
  await check('service worker starts from the manifest entry point', async () => {
    const t = await findTarget((x) => x.type === 'service_worker' && x.url === `${origin}/src/bg/service-worker.js`);
    assert(t, 'no service_worker target for src/bg/service-worker.js');
    const sessionId = await browser.attach(t.targetId);
    await browser.call('Runtime.enable', {}, sessionId);
    // On Linux the target is listed before the worker's global scope exists, so an
    // immediate evaluate sees no `chrome`. Wait until the extension API is there.
    const ready = await browser.waitFor(() =>
      browser.evaluate(sessionId, `typeof chrome !== 'undefined' && typeof chrome.runtime?.id === 'string'`).catch(() => false),
    );
    assert(ready, 'worker never exposed chrome.runtime');
    // Intercept at the browser, below the extension's own code, so the audit
    // cannot be fooled by anything the worker does to `fetch`.
    await browser.call('Fetch.enable', { patterns: [{ urlPattern: '*' }] }, sessionId);
    sw = { sessionId, ev: (expr) => browser.evaluate(sessionId, expr) };
  });
  if (!sw) throw new Error('cannot continue without the service worker');

  // The popup page doubles as the place to import modules: dynamic import() is
  // not allowed inside a service worker, but it is inside an extension page.
  const popup = await openPage('src/ui/popup.html');
  const send = sender(popup);

  await check('installs disarmed, kill switch clear, mode equals DEFAULT_CONFIG.mode (dry-run)', async () => {
    const stored = await sw.ev(`chrome.storage.local.get(['config','runtime'])`);
    const expected = await popup.ev(
      `import(chrome.runtime.getURL('src/storage/store.js')).then(m => m.DEFAULT_CONFIG.mode)`,
    );
    eq(expected, 'dry-run', 'DEFAULT_CONFIG.mode');
    eq(stored.config?.mode, expected, 'installed mode');
    eq(stored.runtime?.armed, false, 'runtime.armed');
    eq(stored.runtime?.killSwitch, false, 'runtime.killSwitch');
  });

  await check('onInstalled logged an install event and scheduled the tick alarm', async () => {
    const alarms = await sw.ev(`chrome.alarms.getAll()`);
    assert(alarms.some((a) => a.name === 'solmargintrader-tick'), `no tick alarm in ${JSON.stringify(alarms)}`);
    const data = await send('data');
    assert(data.ok, 'data command failed');
    const installed = data.events.find((e) => e.type === 'installed');
    assert(installed, `no "installed" event in ${JSON.stringify(data.events.map((e) => e.type))}`);
    eq([installed.armed, installed.mode, installed.reason], [false, 'dry-run', 'install'], 'install event');
  });

  /* ------------------------------------------------------------------ popup UI -- */

  await check('popup loads and says dry-run / disarmed', async () => {
    const banner = await browser.waitFor(
      () => popup.ev(`document.getElementById('banner')?.textContent || ''`).then((t) => t || null),
    );
    assert(banner, 'banner never rendered');
    assert(/Disarmed/.test(banner), `unexpected banner: ${banner}`);
    eq(await popup.ev(`document.getElementById('mode').textContent`), 'dry-run', 'mode pill');
  });

  /* ------------------------------------------------------------ dashboard UI -- */

  const dash = await openPage('src/ui/dashboard.html');
  await check('dashboard loads with dry-run selected and the disclaimer shown', async () => {
    const mode = await browser.waitFor(() =>
      dash.ev(`document.querySelector('#configForm select[name=mode]')?.value`),
    );
    eq(mode, 'dry-run', 'dashboard mode select');
    assert(await dash.ev(`/not financial advice/i.test(document.body.innerText)`), 'disclaimer missing');
  });

  /* ------------------------------------------------- registry parity (real SW) -- */

  await check('worker routes only the shared command registry (unknown message rejected with the registry list)', async () => {
    const names = await popup.ev(
      `import(chrome.runtime.getURL('src/core/commands.js')).then(m => m.COMMAND_NAMES)`,
    );
    // Sent raw on purpose: this probes the worker's refusal, so it bypasses the
    // allowlist that guards every message that could act.
    const res = await popup.ev(`chrome.runtime.sendMessage({ type: 'e2eNoSuchCommand' })`);
    eq(res.ok, false, 'unknown message ok flag');
    eq(res.known, names, 'worker command list vs src/core/commands.js');
  });

  /* ------------------------------------------------------ dry-run plan and tick -- */

  await check('plan comes from the real registry, priced by the stubbed read, and places nothing', async () => {
    const before = requests.length;
    const res = await send('plan');
    assert(res.ok, `plan failed: ${res.error}`);
    eq(res.price, STUB_PRICE, 'plan price');
    assert(Array.isArray(res.intents) && res.intents.length > 0, 'plan produced no intents');
    assert(res.intents.every((i) => i.side && Number.isFinite(i.level)), 'malformed intent');
    const made = requests.slice(before);
    assert(made.length > 0, 'plan made no price request: the stub was never exercised');
  });

  await check('a tick while disarmed is skipped as not-armed and journals no order', async () => {
    const res = await send('tick');
    assert(res.ok, `tick failed: ${res.error}`);
    assert(res.skipped?.some((s) => s.reason === 'not-armed'), `expected not-armed, got ${JSON.stringify(res.skipped)}`);
    eq(res.placed ?? [], [], 'placed orders');
    const data = await send('data');
    eq(data.intents, [], 'intent journal');
  });

  await check('status still reports disarmed dry-run after the tick', async () => {
    const res = await send('status');
    assert(res.ok, 'status failed');
    assertDisarmed(res.runtime, 'after tick');
    eq(res.config.mode, 'dry-run', 'mode');
  });

  /* ------------------------------------------------------------- risk rails -- */

  await check('risk rails fail closed on missing, NaN or malformed state and limits', async () => {
    const out = await popup.ev(`(async () => {
      const { evaluate, admitBatch } = await import(chrome.runtime.getURL('src/core/risk.js'));
      const order = { notionalUsd: 12, slippageBps: 50 };
      const good = { openNotionalUsd: 0, openOrderCount: 0, realizedPnlUsdToday: 0, leverage: 1 };
      const intent = { notionalUsd: 12, side: 'buy', level: 70, intentKey: 'k' };
      return {
        control: evaluate({ order, state: good }).verdict,
        missing: evaluate({ order, state: {} }),
        undef: evaluate({ order, state: undefined }).verdict,
        nan: evaluate({ order, state: { ...good, openNotionalUsd: NaN } }).verdict,
        negative: evaluate({ order, state: { ...good, openOrderCount: -1 } }).verdict,
        killString: evaluate({ order, state: good, limits: { killSwitch: 'yes' } }),
        nanLimit: evaluate({ order: { notionalUsd: 1000, slippageBps: 50 }, state: good, limits: { maxNotionalPerOrderUsd: NaN } }),
        badOrder: evaluate({ order: { notionalUsd: NaN, slippageBps: 50 }, state: good }).verdict,
        batch: admitBatch({ intents: [intent], state: {}, slippageBps: 50 }),
      };
    })()`);
    eq(out.control, 'allow', 'control: a complete, in-limit state must be allowed (else the block checks prove nothing)');
    eq(out.missing.verdict, 'block', 'missing state');
    assert(out.missing.blockedBy.includes('unusable-state'), 'missing state not attributed to unusable-state');
    eq(out.undef, 'block', 'undefined state');
    eq(out.nan, 'block', 'NaN state field');
    eq(out.negative, 'block', 'negative order count');
    assert(out.killString.blockedBy.includes('kill-switch'), 'a non-boolean killSwitch must engage the kill switch');
    assert(out.nanLimit.blockedBy.includes('per-order-notional'), 'a NaN limit must fall back to the default, not disable the rail');
    eq(out.badOrder, 'block', 'NaN order notional');
    eq([out.batch.admitted.length, out.batch.rejected.length], [0, 1], 'batch with missing state');
  });

  /* ------------------------------------------------------------------ secrets -- */

  await check('no secret material in the DOM, storage.sync or any command response', async () => {
    const stored = await send('setApiKey', { apiKey: CANARY });
    eq([stored.ok, stored.keyLength], [true, CANARY.length], 'setApiKey response');
    assert(!JSON.stringify(stored).includes(CANARY), 'setApiKey echoed the key');

    // Reload so every page re-renders after the secret exists.
    await popup.ev('location.reload()');
    await dash.ev('location.reload()');
    await browser.waitFor(() => popup.ev(`document.getElementById('banner')?.textContent`));
    await browser.waitFor(() => dash.ev(`document.querySelector('#configForm select[name=mode]')?.value`));

    const dom = async (p) =>
      p.ev(`document.documentElement.outerHTML + '\\n' +
        [...document.querySelectorAll('input,textarea,select')].map((e) => e.name + '=' + e.value).join('\\n')`);
    const surfaces = {
      popupDom: await dom(popup),
      dashboardDom: await dom(dash),
      sync: JSON.stringify(await sw.ev(`chrome.storage.sync.get(null)`)),
      local: JSON.stringify(await sw.ev(`chrome.storage.local.get(['config','runtime','limits','lastTick'])`)),
    };
    for (const cmd of ['status', 'getConfig', 'getLimits', 'data']) {
      surfaces[`response:${cmd}`] = JSON.stringify(await send(cmd));
    }
    for (const [where, text] of Object.entries(surfaces)) {
      assert(!text.includes(CANARY), `API key canary found in ${where}`);
      assert(!/-----BEGIN [A-Z ]*PRIVATE KEY/.test(text), `PEM private key marker in ${where}`);
      // A 64-byte Solana secret key is 86-88 base58 characters; pubkeys and mints are 32-44.
      assert(!/\b[1-9A-HJ-NP-Za-km-z]{85,90}\b/.test(text), `secret-key-shaped string in ${where}`);
    }
    eq(await sw.ev(`chrome.storage.sync.get(null)`), {}, 'chrome.storage.sync must stay empty');
    // The one allowed home for the key is chrome.storage.local under `secrets`.
    const secrets = await sw.ev(`chrome.storage.local.get('secrets')`);
    eq(secrets.secrets?.apiKey, CANARY, 'the key is stored locally, where the design says it lives');
  });

  /* ------------------------------------------------------------ network audit -- */

  await check('network: only keyless GET price reads were attempted; no order endpoint was touched', async () => {
    assert(requests.length > 0, 'no requests observed: the interception never ran');
    const bad = requests.filter(
      (r) => !(r.method === 'GET' && r.url === 'https://lite-api.jup.ag/price/v3'),
    );
    eq(bad, [], 'unexpected requests');
  });

  await check('still disarmed at the end of the run', async () => {
    const res = await send('status');
    assertDisarmed(res.runtime, 'end of run');
    eq(res.runtime.killSwitch, false, 'kill switch');
  });

  await check('no uncaught exceptions in the worker or either page', async () => {
    eq(pageErrors, [], 'uncaught exceptions');
  });
} finally {
  clearTimeout(watchdog);
  await browser.close();
}

const passed = results.filter((r) => r.ok).length;
console.log(`\n${passed}/${results.length} checks passed`);
failed = passed !== results.length;
process.exit(failed ? 1 : 0);
