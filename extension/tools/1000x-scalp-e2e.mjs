#!/usr/bin/env node
/**
 * Real-browser gate for the 1s scalp window and its take-profit / stop-loss guard.
 *
 * Loads the unpacked extension into Chrome for Testing and serves a local
 * stand-in for https://jup.ag/1000x whose positions table copies the markup of
 * the public bundle. Oracle quotes come from a loopback WebSocket that the test
 * steers. It proves, in a real browser: the window opens from the overlay, reads
 * the listed position, arms only on a trusted click, alerts without pressing in
 * alert mode, presses the row's own Close exactly once in close mode (after the
 * minimum-hold lock clears), never presses "Close all", and reports an armed
 * guard as unprotected when the price goes stale.
 *
 * It never visits the real site, connects no wallet and can place no order.
 * --full also waits out the 78 second warm-up and checks the call and the cone.
 * Exit: 0 pass, 1 failed check, 2 no usable browser.
 */
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { createHash } from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const option = (name, fallback) => args.includes(name) ? args[args.indexOf(name) + 1] : fallback;
const EXT = path.resolve(option('--extension', path.resolve(here, '..')));
const FULL = args.includes('--full');
const OUT = option('--evidence', null);
const { launch, findChromeForTesting, sleep } = await import(pathToFileURL(path.join(EXT, 'e2e/lib/cdp.mjs')));
const CATALOG = 'https://yolo-api.jup.ag/markets';
const HISTORY = 'https://perps-api.jup.ag/v1/pyth/fixed_rate%40200ms/history';
const STREAM = 'wss://perps-api.jup.ag/v1/pyth/stream';
const PORTAL = 'https://jup.ag/1000x?market=SOL&mode=classic';
const manifest = JSON.parse(fs.readFileSync(path.join(EXT, 'manifest.json'), 'utf8'));
const checks = [];
const assert = (value, message) => { if (!value) throw new Error(message); };
async function check(name, fn) {
  try { const detail = await fn(); checks.push({ name, ok: true, detail }); console.log(`ok - ${name}`); }
  catch (error) { checks.push({ name, ok: false, error: error.message }); console.log(`FAIL - ${name}: ${error.message}`); }
}

/** The positions table as the public bundle renders it; buttons count their own clicks. */
const portalHtml = `<!doctype html><html><head><meta charset="utf-8"><title>1000x fixture</title><style>body{margin:0;background:#080c14;color:#fff;font:14px system-ui}table{margin:120px 20px;border-collapse:collapse}td,th{padding:8px 12px;border-bottom:1px solid #333}</style></head><body>
<button id="close-all" type="button" onclick="window.__clicks.all++">Close all</button>
<button id="positions-tab" type="button">Positions (1)</button>
<table><thead><tr><th>Position</th><th>Value / PnL</th><th>Entry / Mark price</th><th>Bust price</th><th>Size</th><th>Collateral</th><th>Held</th><th>Status</th></tr></thead><tbody id="rows"></tbody></table>
<script>
window.__clicks = { close: 0, all: 0, share: 0 };
window.__addRow = (label = 'Close in 3s', disabled = true) => {
  document.getElementById('rows').innerHTML = '<tr><td><button type="button" data-row-action aria-label="Focus SOL position on chart"><span><strong>SOL<span> #1</span></strong><span class="text-success">1,000× Long</span> <span>Classic</span></span></button></td>'
    + '<td><span>$10.00</span><span>+$0.00</span></td><td>$100.0000 / <span>$100.0000</span></td><td>$99.9020</td><td>$10,000.00</td><td><span>$10.00</span><span>JupUSD</span></td><td>12s</td>'
    + '<td><div><button type="button" id="share" onclick="window.__clicks.share++"></button><button type="button" id="row-close"></button></div></td></tr>';
  const button = document.getElementById('row-close');
  button.textContent = label; button.disabled = disabled;
  button.addEventListener('click', () => { window.__clicks.close++; button.textContent = 'Closing…'; button.disabled = true; setTimeout(() => { document.getElementById('rows').innerHTML = ''; }, 1200); });
};
window.__unlock = () => { const button = document.getElementById('row-close'); button.textContent = 'Close'; button.disabled = false; };
window.__addRow();
</script></body></html>`;

async function oracleFixture() {
  const sockets = new Set(), state = { quotes: true, price: 100, subscriptions: [] };
  const frame = text => { const data = Buffer.from(text); if (data.length < 126) return Buffer.concat([Buffer.from([0x81, data.length]), data]); const head = Buffer.alloc(4); head[0] = 0x81; head[1] = 126; head.writeUInt16BE(data.length, 2); return Buffer.concat([head, data]); };
  const server = http.createServer((request, response) => { response.writeHead(404); response.end(); });
  server.on('upgrade', (request, socket) => {
    const accept = createHash('sha1').update(request.headers['sec-websocket-key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
    socket.write(`HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ${accept}\r\n\r\n`);
    sockets.add(socket);
    let buffer = Buffer.alloc(0), feedId;
    const timer = setInterval(() => {
      if (!state.quotes || !feedId || socket.destroyed) return;
      const now = Date.now() - 25;
      // A small wobble keeps the bars from being flat without reaching any test level.
      const price = state.price + Math.sin(now / 900) * 0.004;
      socket.write(frame(JSON.stringify({ type: 'streamUpdated', subscriptionId: 1, parsed: { priceFeeds: [{ priceFeedId: feedId, price: String(Math.round(price * 1e8)), exponent: -8, feedUpdateTimestamp: now * 1000 }] } })));
    }, 200);
    socket.on('data', chunk => {
      buffer = Buffer.concat([buffer, chunk]);
      while (buffer.length >= 2) {
        const opcode = buffer[0] & 15; let length = buffer[1] & 127, offset = 2;
        if (length === 126) { if (buffer.length < 4) return; length = buffer.readUInt16BE(2); offset = 4; }
        if (length === 127 || !(buffer[1] & 128)) { socket.destroy(); return; }
        if (buffer.length < offset + 4 + length) return;
        const mask = buffer.subarray(offset, offset + 4); offset += 4;
        const body = Buffer.from(buffer.subarray(offset, offset + length));
        for (let i = 0; i < length; i++) body[i] ^= mask[i % 4];
        buffer = buffer.subarray(offset + length);
        if (opcode === 8) { socket.end(Buffer.from([0x88, 0])); return; }
        if (opcode === 1) try { const payload = JSON.parse(body); state.subscriptions.push(payload); feedId = payload.priceFeedIds?.[0]; } catch { socket.destroy(); }
      }
    });
    socket.once('close', () => { clearInterval(timer); sockets.delete(socket); });
    socket.on('error', () => {});
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const history = url => {
    const u = new URL(url), step = Number(u.searchParams.get('resolution')) * 60, first = Number(u.searchParams.get('from'));
    const current = Math.floor(Date.now() / 1000 / step) * step;
    const t = Array.from({ length: Math.floor((current - first) / step) + 1 }, (_, i) => first + i * step);
    return { s: 'ok', t, o: t.map(() => 100), h: t.map(() => 100.01), l: t.map(() => 99.99), c: t.map(() => 100) };
  };
  return { state, history, url: `ws://127.0.0.1:${server.address().port}/oracle`,
    catalog: { markets: [{ symbol: 'SOL', address: 'Ew8sRjpuBttpmhSUeaAn4dLAegWnz55AuafVcGuojCPS', feedId: 6, closed: false }] },
    close: async () => { for (const socket of sockets) socket.destroy(); await new Promise(resolve => server.close(resolve)); } };
}

let browser, fixture, fatal;
const targets = new Map(), ready = new Map(), requests = [], errors = [];
try {
  const chrome = process.env.CHROME || findChromeForTesting();
  assert(chrome, 'no Chrome for Testing binary');
  fixture = await oracleFixture();
  browser = await launch({ chrome, extension: EXT, noSandbox: process.env.E2E_NO_SANDBOX === '1' });
  const remap = `(() => { if (globalThis.__smtFixture) return; const Native = globalThis.WebSocket; globalThis.WebSocket = class extends Native { constructor(url, ...rest) { super(String(url) === ${JSON.stringify(STREAM)} ? ${JSON.stringify(fixture.url)} : url, ...rest); } }; globalThis.__smtFixture = true; })()`;
  async function setup(sessionId, info) {
    targets.set(info.targetId, { ...info, sessionId });
    await browser.call('Fetch.enable', { patterns: [{ urlPattern: 'http*', requestStage: 'Request' }] }, sessionId);
    if (info.type !== 'service_worker') {
      await browser.call('Runtime.enable', {}, sessionId);
      if (info.type === 'page' || info.type === 'iframe') {
        await browser.call('Page.enable', {}, sessionId);
        await browser.call('Page.addScriptToEvaluateOnNewDocument', { source: remap }, sessionId);
        await browser.evaluate(sessionId, remap).catch(() => {});
      }
      await browser.call('Target.setAutoAttach', { autoAttach: true, waitForDebuggerOnStart: true, flatten: true,
        filter: [{ type: 'service_worker', exclude: true }, {}] }, sessionId).catch(() => {});
    }
    await browser.call('Runtime.runIfWaitingForDebugger', {}, sessionId);
  }
  async function intercept(m) {
    const { requestId, request } = m.params;
    const record = { method: request.method, url: request.url, action: 'blocked' };
    requests.push(record);
    const fulfill = (body, type = 'application/json') => { record.action = 'fixture'; return browser.call('Fetch.fulfillRequest', { requestId, responseCode: 200,
      responseHeaders: [{ name: 'content-type', value: type }, { name: 'access-control-allow-origin', value: '*' }],
      body: Buffer.from(typeof body === 'string' ? body : JSON.stringify(body)).toString('base64') }, m.sessionId); };
    if (request.method === 'GET') {
      if (new URL(request.url).origin === 'https://jup.ag' && m.params.resourceType === 'Document') return fulfill(portalHtml, 'text/html');
      if (request.url === CATALOG) return fulfill(fixture.catalog);
      if (request.url.startsWith(HISTORY + '?')) return fulfill(fixture.history(request.url));
    }
    return browser.call('Fetch.failRequest', { requestId, errorReason: 'BlockedByClient' }, m.sessionId);
  }
  browser.on(m => {
    if (m.method === 'Target.targetInfoChanged' && targets.has(m.params.targetInfo.targetId)) Object.assign(targets.get(m.params.targetInfo.targetId), m.params.targetInfo);
    if (m.method === 'Target.attachedToTarget') ready.set(m.params.sessionId, setup(m.params.sessionId, m.params.targetInfo).catch(error => errors.push(error.message)));
    if (m.method === 'Fetch.requestPaused') void intercept(m).catch(() => {});
    if (m.method === 'Runtime.exceptionThrown') errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
  });
  await browser.call('Target.setAutoAttach', { autoAttach: true, waitForDebuggerOnStart: true, flatten: true });
  const ev = (page, expression) => browser.evaluate(page.sessionId, expression);
  const until = async (fn, what, ms = 15_000) => {
    let last; const result = await browser.waitFor(async () => { try { return await fn(); } catch (error) { last = error; return null; } }, ms, 100);
    assert(result, `timed out: ${what}${last ? ` (${last.message})` : ''}`); return result;
  };
  async function trustedClick(page, expression) {
    const point = await ev(page, `(() => { const el = ${expression}; if (!el) return null; el.scrollIntoView?.({ block: 'center' }); const box = el.getBoundingClientRect(); return box.width && box.height ? { x: box.left + box.width / 2, y: box.top + box.height / 2 } : null; })()`);
    assert(point, `no visible element: ${expression}`);
    await browser.call('Input.dispatchMouseEvent', { type: 'mousePressed', ...point, button: 'left', clickCount: 1 }, page.sessionId);
    await browser.call('Input.dispatchMouseEvent', { type: 'mouseReleased', ...point, button: 'left', clickCount: 1 }, page.sessionId);
  }
  const setInput = (page, id, value) => ev(page, `(() => { const el = document.getElementById(${JSON.stringify(id)}); el.value = ${JSON.stringify(value)}; el.dispatchEvent(new Event('input', { bubbles: true })); })()`);
  const text = (page, id) => ev(page, `document.getElementById(${JSON.stringify(id)}).textContent`);
  const guardState = page => ev(page, `document.getElementById('guard').dataset.state`);

  const { targetId } = await browser.call('Target.createTarget', { url: 'about:blank' });
  const portal = await until(() => targets.get(targetId), 'portal target'); await ready.get(portal.sessionId);
  await browser.call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false }, portal.sessionId);
  await browser.call('Page.navigate', { url: PORTAL }, portal.sessionId);
  const clicks = () => ev(portal, 'window.__clicks');
  const scalpUrl = `chrome-extension://${browser.extensionId}/src/1000x/scalp.html#market=SOL`;
  let scalp;

  await check('the overlay offers a 1s scalp button and a trusted click opens one window', async () => {
    const button = `document.querySelector('#smt-1000x-indicators')?.shadowRoot.querySelector('#smt-1000x-scalp')`;
    await until(() => ev(portal, `Boolean(${button}) && !${button}.hidden`), 'scalp button');
    await ev(portal, `${button}.click()`);
    await sleep(600);
    assert(!(await browser.targets()).some(target => target.url === scalpUrl), 'a scripted click opened the window');
    await trustedClick(portal, button);
    scalp = await until(async () => { const target = (await browser.targets()).find(item => item.type === 'page' && item.url === scalpUrl); return target && targets.get(target.targetId); }, 'scalp window');
    await ready.get(scalp.sessionId);
    await until(() => ev(scalp, `document.getElementById('version')?.textContent === ${JSON.stringify('v' + manifest.version)}`), 'version tag');
    await trustedClick(portal, button);
    await sleep(500);
    return { windows: (await browser.targets()).filter(target => target.url === scalpUrl).length };
  });
  assert(scalp, 'the scalp window did not open');

  await check('the window builds one-second bars from the live stream and fills readings as they warm up', async () => {
    await until(() => ev(scalp, `document.getElementById('feed').dataset.state === 'live'`), 'live feed', 20_000);
    await until(() => ev(scalp, `document.querySelector('.tile[data-vote]:not([data-vote=warming])') !== null && document.querySelector('#slopes tbody tr').dataset.state !== 'warming'`), 'first readings', 20_000);
    const state = await ev(scalp, `({ tiles: document.querySelectorAll('.tile').length, slopes: [...document.querySelectorAll('#slopes tbody tr')].map(tr => tr.dataset.state), call: document.getElementById('call-text').textContent, tier: document.getElementById('call').dataset.tier, canvas: document.querySelectorAll('#chart canvas').length, overflow: document.documentElement.scrollWidth > innerWidth })`);
    assert(state.tiles === 16 && state.slopes.length === 6, 'grid or ladder is incomplete');
    assert(state.slopes.at(-1) === 'warming' && /Warming up/.test(state.call) && state.tier === 'warming', 'a reading appeared before its warm-up');
    assert(state.canvas > 0 && !state.overflow, 'chart missing or page overflows sideways');
    return state;
  });

  await check('it reads the listed position from the page and installs disarmed in alert-only mode', async () => {
    try { await until(() => ev(scalp, `document.getElementById('guard-position').options.length === 1`), 'position option'); }
    catch (error) { throw new Error(`${error.message}: ${await text(scalp, 'guard-page')}`); }
    const state = await ev(scalp, `({ option: document.getElementById('guard-position').selectedOptions[0].textContent, page: document.getElementById('guard-page').textContent, detail: document.getElementById('guard-position-detail').textContent, mode: document.querySelector('input[name="guard-mode"]:checked').value, guard: document.getElementById('guard').dataset.state })`);
    assert(/SOL · 1,000× long · entry \$100\.0000/.test(state.option), `position not read: ${state.option}`);
    assert(/bust 99\.902/.test(state.detail) && /Close button: locked \(Close in 3s\)/.test(state.detail), `detail: ${state.detail}`);
    assert(state.mode === 'alert' && state.guard === 'idle', 'the guard did not start disarmed in alert-only mode');
    return state;
  });

  await check('arming needs a trusted click and valid levels', async () => {
    await setInput(scalp, 'guard-tp', '100.05');
    await ev(scalp, `document.getElementById('guard-arm').click()`);
    await sleep(300);
    assert(await guardState(scalp) === 'idle', 'a scripted click armed the guard');
    await setInput(scalp, 'guard-tp', '99.5');
    await trustedClick(scalp, `document.getElementById('guard-arm')`);
    await until(() => ev(scalp, `/above the current price/.test(document.getElementById('guard-errors').textContent)`), 'wrong-side error');
    await setInput(scalp, 'guard-sl', '99.80');
    await setInput(scalp, 'guard-tp', '');
    await trustedClick(scalp, `document.getElementById('guard-arm')`);
    await until(() => ev(scalp, `/beyond the bust price/.test(document.getElementById('guard-errors').textContent)`), 'beyond-bust error');
    assert(await guardState(scalp) === 'idle', 'an invalid level armed the guard');
    return { note: await text(scalp, 'guard-sl-note') };
  });

  await check('alert-only mode reports the level and presses nothing', async () => {
    await setInput(scalp, 'guard-sl', '');
    await setInput(scalp, 'guard-tp', '100.05');
    await trustedClick(scalp, `document.getElementById('guard-arm')`);
    await until(async () => await guardState(scalp) === 'armed', 'armed');
    fixture.state.price = 100.07;
    await until(async () => await guardState(scalp) === 'alerted', 'alerted');
    await sleep(1500);
    const counted = await clicks();
    assert(counted.close === 0 && counted.all === 0, `alert mode pressed a button: ${JSON.stringify(counted)}`);
    assert(/Alert only: nothing was pressed/.test(await text(scalp, 'guard-status')), 'status does not say nothing was pressed');
    fixture.state.price = 100;
    return counted;
  });

  await check('close mode waits out the minimum-hold lock, presses the row’s own Close once, and confirms when the row leaves', async () => {
    await sleep(1200);
    await trustedClick(scalp, `document.querySelector('input[name="guard-mode"][value="close"]')`);
    await setInput(scalp, 'guard-tp', '100.05');
    await setInput(scalp, 'guard-sl', '99.95');
    await trustedClick(scalp, `document.getElementById('guard-arm')`);
    await until(async () => await guardState(scalp) === 'armed', 'armed in close mode');
    assert(/will press Close/.test(await text(scalp, 'guard-badge')), 'badge does not show close mode');
    fixture.state.price = 100.07;
    await until(async () => await guardState(scalp) === 'triggered', 'triggered');
    await sleep(1500);
    assert((await clicks()).close === 0, 'pressed while the page still showed the hold countdown');
    await ev(portal, 'window.__unlock()');
    await until(async () => (await clicks()).close === 1, 'one press');
    await until(async () => await guardState(scalp) === 'closed', 'closed', 20_000);
    await sleep(2500);
    const counted = await clicks();
    assert(counted.close === 1 && counted.all === 0 && counted.share === 0, `unexpected presses: ${JSON.stringify(counted)}`);
    fixture.state.price = 100;
    return { counted, status: await text(scalp, 'guard-status') };
  });

  await check('an armed guard with a stale price says it is not protected and presses nothing', async () => {
    await ev(portal, `window.__addRow('Close', false)`);
    await sleep(1500);
    await until(() => ev(scalp, `document.getElementById('guard-position').options.length === 1 && !document.getElementById('guard-arm').hidden && !document.getElementById('guard-arm').disabled`), 'position listed again');
    await setInput(scalp, 'guard-tp', '');
    await setInput(scalp, 'guard-sl', '99.95');
    await trustedClick(scalp, `document.getElementById('guard-arm')`);
    await until(async () => await guardState(scalp) === 'armed', 'armed');
    fixture.state.quotes = false;
    fixture.state.price = 99.9;
    await until(() => ev(scalp, `document.getElementById('guard').hasAttribute('data-unprotected') && /NOT PROTECTED/.test(document.getElementById('guard-status').textContent)`), 'unprotected warning', 12_000);
    assert((await clicks()).close === 1, 'a stale price pressed Close');
    fixture.state.price = 100;
    fixture.state.quotes = true;
    await until(() => ev(scalp, `!document.getElementById('guard').hasAttribute('data-unprotected')`), 'protection restored', 30_000);
    await trustedClick(scalp, `document.getElementById('guard-disarm')`);
    await until(async () => await guardState(scalp) === 'idle', 'disarmed');
    return { clicks: await clicks() };
  });

  if (FULL) await check('after the warm-up the grid makes a call and draws the 30 second range', async () => {
    await until(() => ev(scalp, `document.getElementById('call').dataset.tier !== 'warming'`), 'call ready', 120_000);
    const state = await ev(scalp, `({ tier: document.getElementById('call').dataset.tier, direction: document.getElementById('call').dataset.direction, text: document.getElementById('call-text').textContent, detail: document.getElementById('call-detail').textContent, warm: document.querySelectorAll('.tile[data-vote=warming]').length, count: document.getElementById('tiles-count').textContent, title: document.title })`);
    assert(state.warm === 0 && ['strong', 'lean', 'mixed'].includes(state.tier), JSON.stringify(state));
    assert(/On the recording the grid was chosen from/.test(state.detail) && /separate short live check/.test(state.detail), 'the call does not state its measured hit rate and the untouched check');
    return state;
  });

  await check('only public GET reads left the browser and no page error occurred', async () => {
    const sent = requests.filter(request => request.action !== 'blocked');
    assert(requests.every(request => request.method === 'GET'), 'a non-GET request was attempted');
    assert(sent.every(request => request.url === CATALOG || request.url.startsWith(HISTORY + '?') || request.url.startsWith('https://jup.ag/')), 'an unexpected host was read');
    assert(fixture.state.subscriptions.every(payload => payload.type === 'subscribe' && String(payload.priceFeedIds) === '6'), 'unexpected stream message');
    assert(errors.length === 0, `page errors: ${errors.join(' | ')}`);
    return { requests: requests.length, blocked: requests.filter(request => request.action === 'blocked').map(request => request.url) };
  });

  if (OUT) {
    fs.mkdirSync(OUT, { recursive: true });
    const shot = await browser.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true }, scalp.sessionId);
    fs.writeFileSync(path.join(OUT, 'scalp.png'), Buffer.from(shot.data, 'base64'));
    fs.writeFileSync(path.join(OUT, 'receipt.json'), JSON.stringify({ runner: '1000x-scalp-browser-gate', observed_at: new Date().toISOString(),
      browser: browser.version, version: manifest.version, full: FULL, checks }, null, 2));
  }
} catch (error) {
  fatal = error;
  console.error(`e2e: ${error.message}`);
} finally {
  if (browser) await browser.close();
  if (fixture) await fixture.close();
}
process.exitCode = fatal ? 2 : checks.some(item => !item.ok) ? 1 : 0;
