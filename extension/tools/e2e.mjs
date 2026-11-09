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
 * The soltui bridge is exercised end to end: the real extension talks to the
 * soltui native messaging host (the production one when soltui is installed, a
 * protocol-identical fixture otherwise; the run says which) and its replies are
 * compared with what the extension's CLI and, with the real host, `soltui` print.
 * Only commands soltui lists as read_only are ever called (e2e/lib/guard.mjs).
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
import { execFile } from 'node:child_process';
import { assertAllowedMessage, assertDisarmed, assertSoltuiCallAllowed } from '../e2e/lib/guard.mjs';
import { installHost } from '../e2e/lib/soltui-host.mjs';
import { verifyDashboardWorkflows } from '../e2e/lib/dashboard-workspace.mjs';
import { verifySignalDesk } from '../e2e/lib/signal-desk.mjs';

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
console.log(`browser   ${browser.version}\nextension ${browser.extensionId}`);

let host;
try {
  host = await installHost({ profile: browser.profile, extensionId: browser.extensionId });
} catch (err) {
  console.error(`e2e: ${err.message}`);
  await browser.close();
  process.exit(2);
}
console.log(`soltui    ${host.kind} native host\n`);

const watchdog = setTimeout(async () => {
  console.error('e2e: global timeout');
  await browser.close().catch(() => {});
  process.exit(1);
}, 120_000);
watchdog.unref();

/* ----------------------------------------------------- network: stub and audit -- */

/** Every request any extension target made, so the checks can audit them. */
const requests = [];

/** The JSON-RPC method names in a POST body (one call or a batch); null when it is not JSON-RPC. */
function rpcMethodsOf(postData) {
  if (!postData) return null;
  try {
    const body = JSON.parse(postData);
    const calls = Array.isArray(body) ? body : [body];
    return calls.every((c) => typeof c?.method === 'string') ? calls.map((c) => c.method) : null;
  } catch {
    return null;
  }
}

// The read-only market reads the redesigned pages make (src/market). They are
// blocked like everything else; the audit proves they were reads.
const MARKET_GETS = [
  (u) => u === 'https://lite-api.jup.ag/price/v3',
  (u) => u === 'https://lite-api.jup.ag/swap/v1/quote',
  // Ultra's holdings READ only; /ultra/v1/order and /execute stay unexpected.
  (u) => /^https:\/\/lite-api\.jup\.ag\/ultra\/v1\/holdings\/[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(u),
  (u) => u.startsWith('https://coins.llama.fi/prices/current/'),
  (u) => u === 'https://yields.llama.fi/pools',
];
const RPC_ORIGINS = ['https://base-rpc.publicnode.com', 'https://mainnet.base.org', 'https://api.mainnet-beta.solana.com'];
const READ_RPC = /^(eth_(call|chainId|getBalance|blockNumber)|get[A-Z][A-Za-z]*)$/;
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
  requests.push({ method: request.method, url: `${url.origin}${url.pathname}`, rpcMethods: rpcMethodsOf(request.postData) });
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

  /* --------------------------------------------------------- equity chart -- */

  // The vendored Lightweight Charts must load under the extension CSP and draw
  // in a real MV3 page; a node test cannot see either (no DOM, no CSP).
  await check('equity chart draws with the vendored Lightweight Charts under the extension CSP', async () => {
    const out = await dash.ev(`(async () => {
      const { renderEquityChart, disposeChart } = await import(chrome.runtime.getURL('src/ui/charts.js'));
      const el = document.createElement('div');
      el.style.width = '600px';
      document.body.append(el);
      const points = [
        { tsMs: Date.UTC(2026, 10, 1), equityUsd: 100 },
        { tsMs: Date.UTC(2026, 10, 2), equityUsd: 103.5 },
        { tsMs: Date.UTC(2026, 10, 3), equityUsd: 101.25 },
      ];
      const drawnBy = await renderEquityChart(el, points, { label: 'e2e equity', fallbackHtml: () => '<p>fallback</p>' });
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      const res = {
        drawnBy,
        canvases: el.querySelectorAll('canvas').length,
        attribution: !!el.querySelector('a[href*="tradingview.com"]'),
        ariaLabel: el.getAttribute('aria-label'),
      };
      disposeChart(el);
      el.remove();
      return res;
    })()`);
    eq(out.drawnBy, 'lightweight-charts', 'chart renderer (fallback means the vendored library did not load)');
    assert(out.canvases > 0, 'no canvas drawn');
    assert(out.attribution, 'TradingView attribution link missing (licence requires it)');
    eq(out.ariaLabel, 'e2e equity', 'accessible label');
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

  /* ------------------------------------------------------------ soltui bridge -- */

  const runCli = (args, env = host.env) =>
    new Promise((resolve) => {
      execFile(process.execPath, [path.join(EXT, 'tools', 'cli.js'), ...args, '--json', '--ephemeral'],
        { cwd: EXT, env, timeout: 60_000 },
        (err, stdout, stderr) => resolve({ code: err?.code ?? 0, stdout, stderr }));
    });
  const same = (a, b, msg) => assert(JSON.stringify(a) === JSON.stringify(b), `${msg}\n  extension: ${JSON.stringify(a).slice(0, 300)}\n  other:     ${JSON.stringify(b).slice(0, 300)}`);

  let listing;
  await check('soltuiCommands through the real extension returns the same envelope as the extension CLI', async () => {
    const res = await send('soltuiCommands');
    assert(res.ok, `message failed: ${res.error}`);
    assert(res.result.ok === true, `soltui list failed: ${JSON.stringify(res.result.error)}`);
    listing = res.result.result;
    assert(Array.isArray(listing) && listing.length > 0, 'soltui listed no commands');
    assert(listing.every((c) => c.name && 'read_only' in c && 'long_running' in c && 'requires_confirm' in c && Array.isArray(c.params)), 'list entry missing a contract field');
    const cli = await runCli(['soltuiCommands']);
    assert(cli.code === 0, `CLI failed: ${cli.stderr}`);
    same(res.result, JSON.parse(cli.stdout), 'extension and CLI list envelopes differ');
  });
  if (!listing) throw new Error('cannot continue without the soltui command list');

  // A command that cannot change anything (read_only, no confirm, nothing required)
  // and whose answer is stable across two calls, so a comparison is not a race.
  let probe;
  const candidates = listing.filter((c) => c.read_only === true && c.requires_confirm !== true && c.long_running !== true
    && !(c.params ?? []).some((p) => p.required));
  for (const c of candidates.slice(0, 8)) {
    assertSoltuiCallAllowed(c.name, {}, listing);
    const a = await send('soltuiCall', { command: c.name, params: {} });
    const b = await send('soltuiCall', { command: c.name, params: {} });
    if (a.ok && JSON.stringify(a.result) === JSON.stringify(b.result)) { probe = c; break; }
  }

  await check('a read-only soltuiCall through the real extension returns the same envelope as the extension CLI', async () => {
    assert(probe, 'soltui lists no stable read-only command that needs no parameters');
    assertSoltuiCallAllowed(probe.name, {}, listing);
    const res = await send('soltuiCall', { command: probe.name, params: {} });
    assert(res.ok, `message failed: ${res.error}`);
    assert(res.result.command === probe.name, `envelope names ${res.result.command}`);
    const cli = await runCli(['soltuiCall', '--command', probe.name]);
    assert(cli.code === 0 || res.result.ok === false, `CLI failed: ${cli.stderr}`);
    same(res.result, JSON.parse(cli.stdout), `${probe.name} envelopes differ between the extension and its CLI`);
    console.log(`         compared ${probe.name}: ok=${res.result.ok}`);
  });

  if (host.cli) {
    await check('the real extension returns the same envelope as `soltui list` and `soltui call` (the soltui CLI)', async () => {
      const listed = await host.cli(['list']);
      same((await send('soltuiCommands')).result, JSON.parse(listed.stdout), 'extension vs `soltui list`');
      const called = await host.cli(['call', probe.name]);
      const res = await send('soltuiCall', { command: probe.name, params: {} });
      same(res.result, JSON.parse(called.stdout), `extension vs \`soltui call ${probe.name}\``);
      // Byte-level: the CLI prints one line of JSON, and the extension's reply re-serialises to the same text.
      eq(JSON.stringify(res.result), called.stdout.trim(), 'serialised envelope vs CLI line');
      console.log(`         compared \`soltui call ${probe.name}\`: byte-identical`);
    });
  }

  await check('an unknown soltui command is a clean refusal envelope, identical on the extension and its CLI', async () => {
    // Sent raw on purpose, like the unknown-message probe above: it is a name soltui
    // does not have, so it can only come back as unknown_command and runs nothing.
    const res = await popup.ev(`chrome.runtime.sendMessage({ type: 'soltuiCall', command: 'e2e.no_such_command', params: {} })`);
    assert(res.ok === true && res.result.ok === false, `unexpected: ${JSON.stringify(res)}`);
    eq(res.result.error.code, 'unknown_command', 'error code');
    const cli = await runCli(['soltuiCall', '--command', 'e2e.no_such_command']);
    same(res.result, JSON.parse(cli.stdout), 'unknown-command envelopes differ');
  });

  await check('the dashboard SolTUI panel lists the registry commands, renders the result with textContent, and gates confirm', async () => {
    const options = await browser.waitFor(() =>
      dash.ev(`[...document.querySelectorAll('#soltuiCommand option')].map((o) => o.value)`).then((v) => (v.length ? v : null)));
    assert(options, 'the panel never listed commands');
    eq(options, listing.map((c) => c.name), 'panel options vs soltuiCommands');
    // Run the read-only probe from the form and compare with the envelope.
    await dash.ev(`(() => { const s = document.querySelector('#soltuiCommand'); s.value = ${JSON.stringify(probe.name)}; s.dispatchEvent(new Event('change')); })()`);
    await dash.ev(`document.querySelector('#soltuiForm').requestSubmit()`);
    const shown = await browser.waitFor(() =>
      dash.ev(`document.querySelector('#soltuiResult').textContent`).then((t) => (t && t !== 'Running…' ? t : null)));
    assert(shown, 'the panel showed no result');
    const expected = (await send('soltuiCall', { command: probe.name, params: {} })).result;
    eq(JSON.parse(shown), expected, 'panel result vs envelope');
    assert(await dash.ev(`document.querySelector('#soltuiResult').children.length === 0`), 'result must be text, not markup');
    // A requires_confirm command: Run is disabled until the box is ticked (never clicked here).
    const gated = listing.find((c) => c.requires_confirm === true);
    if (gated) {
      await dash.ev(`(() => { const s = document.querySelector('#soltuiCommand'); s.value = ${JSON.stringify(gated.name)}; s.dispatchEvent(new Event('change')); })()`);
      eq(await dash.ev(`document.querySelector('#soltuiForm button[type=submit]').disabled`), true, 'Run disabled before confirm');
    }
  });

  await check('dashboard workspaces expose the registry, filter tools and render sortable exportable results', async () => {
    await dash.ev(`location.hash = '#soltui/research'`);
    const workspace = await browser.waitFor(() => dash.ev(`document.querySelector('#soltuiWorkspace').value`).then((v) => v === 'research' ? v : null));
    assert(workspace, 'Research navigation did not select its workspace');
    const spec = listing.find((c) => c.name === 'strategies.list') ?? probe;
    assertSoltuiCallAllowed(spec.name, {}, listing);
    await dash.ev(`(() => { const s = document.querySelector('#soltuiCommand'); s.value = ${JSON.stringify(spec.name)}; s.dispatchEvent(new Event('change')); document.querySelector('#soltuiForm').requestSubmit(); })()`);
    const response = await browser.waitFor(() => dash.ev(`document.querySelector('#soltuiResult').textContent`).then((t) => {
      try { return JSON.parse(t).command === spec.name ? JSON.parse(t) : null; } catch { return null; }
    }));
    assert(response?.ok, 'read-only result did not render');
    if (spec.name === 'strategies.list') {
      assert(await dash.ev(`document.querySelectorAll('#soltuiTables tbody tr').length > 0`), 'structured rows missing');
      assert(await dash.ev(`[...document.querySelectorAll('#soltuiTables button')].some((b) => b.textContent === 'Export CSV')`), 'CSV export missing');
      await dash.ev(`document.querySelector('#soltuiTables th button').click()`);
      assert(await dash.ev(`document.querySelector('#soltuiTables th').getAttribute('aria-sort') === 'ascending'`), 'column sort did not apply');
      await dash.ev(`(() => { const f = document.querySelector('#soltuiTables input'); f.value = 'no-match-9bd53a'; f.dispatchEvent(new Event('input')); })()`);
      eq(await dash.ev(`document.querySelectorAll('#soltuiTables tbody tr').length`), 0, 'filter rows');
    }
    await dash.ev(`(() => { const f = document.querySelector('#soltuiSearch'); f.value = 'no-match-9bd53a'; f.dispatchEvent(new Event('input')); })()`);
    eq(await dash.ev(`document.querySelectorAll('#soltuiTools button').length`), 0, 'filter tools');
    await dash.ev(`(() => { const f = document.querySelector('#soltuiSearch'); f.value = ''; f.dispatchEvent(new Event('input')); location.hash = '#soltui/signal'; })()`);
    assert(await browser.waitFor(() => dash.ev(`!document.querySelector('#soltuiLive').hidden`)), 'Signal live view missing');
    const falseCommand = listing.find((c) => c.params.some((p) => p.type === 'bool' && p.name !== 'confirm'));
    if (falseCommand) {
      await dash.ev(`(() => { const s = document.querySelector('#soltuiCommand'); s.value = ${JSON.stringify(falseCommand.name)}; s.dispatchEvent(new Event('change')); })()`);
      assert(await dash.ev(`[...document.querySelectorAll('#soltuiForm select option')].some((o) => o.value === 'false')`), 'false boolean value is not available');
    }
    // Inspect forms only: no write or live-money tool is run by this check.
  });

  await check('dashboard order handoff, confirmation, explicit clear and editor regression scenarios (mock writes)', async () => {
    await verifyDashboardWorkflows(dash, browser);
  });

  await check('Signal Desk source identity, workflows, pinned paper setup, search, archive policy and responsive layout (memory-only native fixture)', async () => {
    await verifySignalDesk(dash, browser);
  });

  await check('the 1-minute soltui build probe alarm is scheduled', async () => {
    const alarms = await sw.ev(`chrome.alarms.getAll()`);
    const build = alarms.find((a) => a.name === 'solmargintrader-soltui-build');
    assert(build, `no build alarm in ${JSON.stringify(alarms)}`);
    eq(build.periodInMinutes, 1, 'build alarm period');
  });

  await check('with the native host missing, the extension returns a clean failed envelope, not an exception', async () => {
    // Close the dashboard lease first; a retained live host can outlast its manifest.
    await send('soltuiSession', { session: await dash.ev(`document.querySelector('#soltui').dataset.session`), active: false });
    await browser.call('Target.closeTarget', { targetId: dash.targetId });
    host.remove();
    try {
      const res = await send('soltuiCommands');
      assert(res.ok === true, `message failed: ${res.error}`);
      eq(res.result.ok, false, 'envelope ok');
      eq(res.result.error.code, 'failed', 'error code');
      assert(/not available|could not be started/.test(res.result.error.message), `unhelpful message: ${res.result.error.message}`);
      assert(/native_host_install/.test(res.result.error.message), 'message does not say how to install the host');
    } finally {
      host.restore();
    }
    const back = await send('soltuiCommands');
    assert(back.result.ok === true, 'host did not come back after the manifest was restored');
  });

  /* ------------------------------------------------------------ network audit -- */

  await check('network: only keyless reads were attempted (prices, quotes, yields, read-only JSON-RPC); no order endpoint was touched', async () => {
    assert(requests.length > 0, 'no requests observed: the interception never ran');
    const bad = requests.filter((r) => {
      if (r.method === 'GET') return !MARKET_GETS.some((ok) => ok(r.url));
      if (r.method === 'POST' && RPC_ORIGINS.some((o) => r.url === o || r.url === `${o}/`)) {
        return !(r.rpcMethods?.length && r.rpcMethods.every((name) => READ_RPC.test(name)));
      }
      return true;
    });
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
