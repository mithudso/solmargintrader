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
 * guard as unprotected when the price goes stale. For entries it proves that
 * Long and Short stay locked until unlocked, need a confirming second press,
 * press the page's own size and side buttons once, and arm the levels from the
 * new position's real entry.
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
if (OUT) fs.mkdirSync(OUT, { recursive: true });
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

/** The positions table and order form as the public bundle renders them; buttons count their own clicks. */
const portalHtml = `<!doctype html><html><head><meta charset="utf-8"><title>1000x fixture</title><style>body{margin:0;background:#080c14;color:#fff;font:14px system-ui}table{margin:20px;border-collapse:collapse}td,th{padding:8px 12px;border-bottom:1px solid #333}form{margin:90px 20px 0;display:flex;gap:8px;align-items:center}</style></head><body>
<nav aria-label="Trading mode"><a id="mode" aria-current="page">Classic</a><a>Double or Nothing</a></nav>
<form aria-label="Degen market order" onsubmit="return false">
  <label for="degen-amount">You're paying</label>
  <button type="button" id="quick-25">25%</button><button type="button" id="quick-half">Half</button><button type="button" id="quick-max">Max</button>
  <button type="button" aria-label="Available balance: 15.80352 JupUSD" title="Available balance: 15.80352 JupUSD"><span>15.80352</span></button>
  <input id="degen-amount" name="amount" placeholder="0.00" aria-label="Collateral amount"><span id="degen-amount-hint"></span>
  <button type="button" class="lev" aria-pressed="false">500×</button><button type="button" class="lev" aria-pressed="true">1,000×</button>
  <button type="button" data-side="long">Long</button><button type="button" data-side="short">Short</button>
</form>
<button id="close-all" type="button" onclick="window.__clicks.all++">Close all</button>
<button id="positions-tab" type="button">Positions (1)</button>
<table><thead><tr><th>Position</th><th>Value / PnL</th><th>Entry / Mark price</th><th>Bust price</th><th>Size</th><th>Collateral</th><th>Held</th><th>Status</th></tr></thead><tbody id="rows"></tbody></table>
<script>
window.__clicks = { close: 0, all: 0, share: 0, long: 0, short: 0, quick: [], amounts: [], leverage: [] };
const pressedLeverage = () => document.querySelector('.lev[aria-pressed="true"]').textContent;
for (const preset of document.querySelectorAll('.lev')) preset.addEventListener('click', () => {
  window.__clicks.leverage.push(preset.textContent);
  setTimeout(() => { for (const other of document.querySelectorAll('.lev')) other.setAttribute('aria-pressed', String(other === preset)); }, 40);
});
const rowHtml = (side, entry, bust) => '<tr><td><button type="button" data-row-action aria-label="Focus SOL position on chart"><span><strong>SOL<span> #1</span></strong><span class="text-success">' + pressedLeverage() + ' ' + side + '</span> <span>Classic</span></span></button></td>'
    + '<td><span>$10.00</span><span>+$0.00</span></td><td>' + entry + ' / <span>' + entry + '</span></td><td>' + bust + '</td><td>$10,000.00</td><td><span>$10.00</span><span>JupUSD</span></td><td>12s</td>'
    + '<td><div><button type="button" class="share" onclick="window.__clicks.share++"></button><button type="button" class="row-close"></button></div></td></tr>';
const wire = (label, disabled) => {
  const button = document.querySelector('#rows .row-close');
  button.textContent = label; button.disabled = disabled;
  button.addEventListener('click', () => { window.__clicks.close++; button.textContent = 'Closing…'; button.disabled = true; setTimeout(() => { document.getElementById('rows').innerHTML = ''; }, 1200); });
};
window.__addRow = (label = 'Close in 3s', disabled = true) => { document.getElementById('rows').innerHTML = rowHtml('Long', '$100.0000', '$99.9020'); wire(label, disabled); };
window.__unlock = () => { const button = document.querySelector('#rows .row-close'); button.textContent = 'Close'; button.disabled = false; };
// The order form: quick sizes fill the amount a moment later, and a side press lists the position after an "opening" row.
const amount = document.getElementById('degen-amount'), hint = document.getElementById('degen-amount-hint');
// The line under the amount is drawn from the page's own state, as on the real page.
amount.addEventListener('input', () => { hint.textContent = amount.value ? '≈ $' + amount.value : ''; });
for (const [id, value] of [['quick-25', '3.95088'], ['quick-half', '7.90176'], ['quick-max', '15.80352']]) {
  document.getElementById(id).addEventListener('click', () => { window.__clicks.quick.push(id); setTimeout(() => { amount.value = value; hint.textContent = '≈ $' + value; }, 40); });
}
for (const button of document.querySelectorAll('[data-side]')) button.addEventListener('click', () => {
  const side = button.dataset.side;
  window.__clicks[side]++; window.__clicks.amounts.push(amount.value);
  document.getElementById('rows').innerHTML = '<tr aria-busy="true"><td>SOL opening</td><td></td><td>Pending / $100.01</td><td></td><td></td><td></td><td></td><td><button type="button" disabled>Opening</button></td></tr>';
  setTimeout(() => {
    document.getElementById('rows').innerHTML = rowHtml(side === 'long' ? 'Long' : 'Short', '$100.0100', side === 'long' ? '$99.9120' : '$100.1080');
    wire('Close in 2s', true);
    setTimeout(window.__unlock, 1500);
  }, 800);
});
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
    catalog: { markets: [{ symbol: 'SOL', address: 'Ew8sRjpuBttpmhSUeaAn4dLAegWnz55AuafVcGuojCPS', feedId: 6, closed: false },
      { symbol: 'BTC', address: 'Ew8sRjpuBttpmhSUeaAn4dLAegWnz55AuafVcGuojCPS', feedId: 1, closed: false },
      { symbol: 'ZEC', address: 'Ew8sRjpuBttpmhSUeaAn4dLAegWnz55AuafVcGuojCPS', feedId: 66, closed: false }] },
    close: async () => { for (const socket of sockets) socket.destroy(); await new Promise(resolve => server.close(resolve)); } };
}

/**
 * A Perps beta market as the live order form (read 2026-11-28) and the page's own code render it: side radios,
 * Market and Limit tabs, a balance button, HALF and MAX, a labelled amount input, a leverage slider with presets
 * and a submit button; a position row of eight cells with a "Quick close" button; and the close question.
 */
const perpsHtml = `<!doctype html><html><head><meta charset="utf-8"><title>Perps fixture</title><style>body{margin:0;background:#080c14;color:#fff;font:14px system-ui}.perps-position-table-row{display:grid;grid-template-columns:repeat(8,1fr);gap:8px;padding:8px 12px}#form{margin:20px;display:flex;flex-wrap:wrap;gap:8px;max-width:520px}[role=dialog]{position:fixed;top:120px;left:120px;padding:20px;background:#223;border:1px solid #889}</style></head><body>
<div><button role="tab" aria-selected="true" id="positions-tab">Positions</button><button role="tab" aria-selected="false">Open Orders</button><button type="button" id="close-all">Close All</button></div>
<div id="list"><p id="empty">No positions</p></div>
<div id="form">
  <button type="button" role="radio" aria-label="Long" data-checked="">Long/Buy</button><input type="radio" value="long" hidden>
  <button type="button" role="radio" aria-label="Short">Short/Sell</button><input type="radio" value="short" hidden>
  <button type="button" role="tab" aria-selected="true">Market</button><button type="button" role="tab" aria-selected="false">Limit</button>
  <button type="button" id="balance">40 USDC</button><button type="button" id="half">HALF</button><button type="button" id="max">MAX</button>
  <input type="text" aria-label="Collateral amount" inputmode="decimal" placeholder="0.00" id="amount">
  <input type="range" aria-label="Leverage" min="1.1" max="50" step="0.1" value="10" id="leverage">
  <button type="button" aria-label="Set leverage to 10x" class="preset">10x</button><button type="button" aria-label="Set leverage to 25x" class="preset">25x</button><button type="button" aria-label="Set leverage to 50x" class="preset">50x</button>
  <button type="button" id="submit" disabled>Long/Buy</button>
</div>
<script>
window.__perps = { submit: 0, quick: 0, confirm: 0, dismiss: 0, all: 0, typed: 0, side: null, leverage: null, amount: null };
const $ = id => document.getElementById(id), amount = $('amount'), submit = $('submit'), lever = $('leverage');
const radios = [...document.querySelectorAll('[role=radio]')];
for (const radio of radios) radio.addEventListener('click', () => setTimeout(() => {
  for (const other of radios) other.toggleAttribute('data-checked', other === radio);
  submit.textContent = radio.getAttribute('aria-label') === 'Long' ? 'Long/Buy' : 'Short/Sell';
}, 40));
for (const preset of document.querySelectorAll('.preset')) preset.addEventListener('click', () => setTimeout(() => { lever.value = preset.textContent.replace('x', ''); }, 40));
$('half').addEventListener('click', () => setTimeout(() => { amount.value = '20.0000'; submit.disabled = false; }, 40));
$('max').addEventListener('click', () => setTimeout(() => { amount.value = '39.9200'; submit.disabled = false; }, 40));
amount.addEventListener('input', () => { window.__perps.typed += 1; });
$('close-all').addEventListener('click', () => { window.__perps.all += 1; });
submit.addEventListener('click', () => {
  const side = radios.find(radio => radio.hasAttribute('data-checked')).getAttribute('aria-label');
  Object.assign(window.__perps, { submit: window.__perps.submit + 1, side, leverage: lever.value, amount: amount.value });
  submit.disabled = true;
  setTimeout(() => {
    $('empty').remove();
    const row = document.createElement('div');
    row.className = 'grid perps-position-table-row h-[62px]';
    row.innerHTML = '<div><button type="button">ZEC</button><span>' + side + ' ' + lever.value + 'x</span></div><div><span>$20.10</span><span>(+$0.10)</span></div>'
      + '<div><span>$100.0100<span>/</span></span><span>$100.0200</span></div><div><span>' + (side === 'Long' ? '$97.10' : '$102.90') + '</span></div>'
      + '<div><span>$500.00</span><span>5 ZEC</span></div><div><span>$20.00</span></div><div><span>-- / --</span></div>'
      + '<div><button type="button" aria-label="Share ZEC">s</button><button type="button" aria-label="Quick close ZEC">x</button><button type="button">Close</button></div>';
    row.querySelector('[aria-label="Quick close ZEC"]').addEventListener('click', () => {
      window.__perps.quick += 1;
      setTimeout(() => {
        const dialog = document.createElement('div');
        dialog.setAttribute('role', 'dialog');
        dialog.innerHTML = '<h2>Close Entire Position?</h2><p>This will send an order to close your ZEC position.</p><button type="button">Confirm</button><button type="button">Dismiss</button>';
        const [confirm, dismiss] = dialog.querySelectorAll('button');
        confirm.addEventListener('click', () => { window.__perps.confirm += 1; dialog.remove(); setTimeout(() => { row.remove(); $('positions-tab').textContent = 'Positions'; const empty = document.createElement('p'); empty.id = 'empty'; empty.textContent = 'No positions'; $('list').append(empty); }, 300); });
        dismiss.addEventListener('click', () => { window.__perps.dismiss += 1; dialog.remove(); });
        document.body.append(dialog);
      }, 150);
    });
    $('list').append(row);
    // With a position listed the tab carries a count.
    $('positions-tab').textContent = 'Positions (1)';
  }, 400);
});
</script></body></html>`;

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
      if (new URL(request.url).origin === 'https://jup.ag' && m.params.resourceType === 'Document') return fulfill(new URL(request.url).pathname.startsWith('/perps/') ? perpsHtml : portalHtml, 'text/html');
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

  const state = expression => ev(scalp, expression);
  const setSelect = (id, value) => ev(scalp, `(() => { const el = document.getElementById(${JSON.stringify(id)}); el.value = ${JSON.stringify(value)}; el.dispatchEvent(new Event('change', { bubbles: true })); })()`);

  await check('the order form sits to the right of the chart, and help lives in hover text, not in paragraphs', async () => {
    if (await state('innerWidth') < 900) await browser.call('Emulation.setDeviceMetricsOverride', { width: 980, height: 940, deviceScaleFactor: 1, mobile: false }, scalp.sessionId);
    const layout = await until(() => state(`(() => { const chart = document.getElementById('chart').getBoundingClientRect(), order = document.getElementById('guard').getBoundingClientRect();
      return order.left >= chart.right - 1 && Math.abs(order.top - document.getElementById('call').getBoundingClientRect().top) < 40 ? { chartRight: Math.round(chart.right), orderLeft: Math.round(order.left), overflow: document.documentElement.scrollWidth > innerWidth } : null; })()`), 'two-column layout');
    assert(!layout.overflow, 'the page overflows sideways');
    const help = await state(`({ tiles: [...document.querySelectorAll('.tile')].map(tile => tile.title.length), heads: [...document.querySelectorAll('#slopes thead th')].map(th => th.title.length),
      rows: [...document.querySelectorAll('#slopes tbody th')].map(th => th.title.length), prose: document.querySelectorAll('.legend, #slopes-note, #guard-help, #call-detail').length,
      labelled: [...document.querySelectorAll('#guard legend, #guard label[title], #guard button[title], #guard fieldset[title]')].length, tile: document.querySelector('.tile').title })`);
    assert(help.tiles.length === 16 && help.tiles.every(length => length > 120), 'a tile lacks a detailed description');
    assert(help.heads.length === 8 && help.heads.every(length => length > 60), 'a ladder column title lacks a description');
    assert(help.rows.length === 6 && help.rows.every(length => length > 60), 'a ladder row lacks its baseline');
    assert(help.prose === 0, 'explanatory paragraphs are still in the window');
    assert(/On the recording, following it over the next 30 seconds was right \d+\.\d% of the time/.test(help.tile), 'a tile does not state its own record');
    return { layout, labelled: help.labelled };
  });

  await check('it reads the listed position and the order form, and installs disarmed, alert-only, with entries locked', async () => {
    try { await until(() => state(`document.getElementById('guard-position').options.length === 1`), 'position option'); }
    catch (error) { throw new Error(`${error.message}: ${await text(scalp, 'guard-page')}`); }
    const seen = await state(`({ option: document.getElementById('guard-position').selectedOptions[0].textContent, page: document.getElementById('guard-page').textContent, detail: document.getElementById('guard-position-detail').textContent,
      mode: document.querySelector('input[name="guard-mode"]:checked').value, guard: document.getElementById('guard').dataset.state, unit: document.getElementById('guard-unit').value,
      unlocked: document.getElementById('entry-unlock').checked, confirm: document.getElementById('entry-confirm').checked, long: document.getElementById('entry-long').disabled, short: document.getElementById('entry-short').disabled,
      why: document.getElementById('entry-status').textContent, badge: document.getElementById('guard-badge').textContent, watch: document.getElementById('guard-status').textContent })`);
    assert(/SOL · 1,000× long · entry \$100\.0000/.test(seen.option), `position not read: ${seen.option}`);
    assert(/bust 99\.902/.test(seen.detail) && /Close button: locked \(Close in 3s\)/.test(seen.detail), `detail: ${seen.detail}`);
    assert(/Available 15\.80352 JupUSD · page leverage 1,000× · Classic/.test(seen.page), `order form not read: ${seen.page}`);
    assert(seen.mode === 'alert' && seen.guard === 'idle' && seen.unit === 'bp', 'the guard did not start disarmed, alert-only, in bp');
    assert(!seen.unlocked && seen.confirm && seen.long && seen.short, 'entries did not start locked and confirmed');
    // The reason the buttons are off is on screen, and the take profit and stop loss state does not read as a block on entries.
    assert(/^Long and Short are off: Tick Unlock/.test(seen.why), `the window does not say how to enable entries: ${seen.why}`);
    assert(seen.badge === 'TP/SL off' && /does not block Long or Short/.test(seen.watch), `guard wording: ${seen.badge} | ${seen.watch}`);
    return seen;
  });

  await check('the window’s one sound has a mute button, and the choice is kept', async () => {
    const before = await state(`({ text: document.getElementById('mute').textContent, pressed: document.getElementById('mute').getAttribute('aria-pressed'), title: document.getElementById('mute').title.length })`);
    assert(before.text === 'Sound on' && before.pressed === 'false' && before.title > 120, JSON.stringify(before));
    await trustedClick(scalp, `document.getElementById('mute')`);
    await until(() => state(`document.getElementById('mute').getAttribute('aria-pressed') === 'true' && document.getElementById('mute').textContent === 'Muted'`), 'muted');
    await until(async () => (await state(`chrome.storage.local.get('jupiter1000xScalp').then(stored => stored.jupiter1000xScalp?.muted === true)`)) === true, 'mute saved');
    await trustedClick(scalp, `document.getElementById('mute')`);
    await until(async () => (await state(`chrome.storage.local.get('jupiter1000xScalp').then(stored => stored.jupiter1000xScalp?.muted === false && document.getElementById('mute').textContent === 'Sound on')`)) === true, 'unmuted and saved');
    return before;
  });

  await check('arming needs a trusted click and valid levels, in price or in basis points', async () => {
    await setInput(scalp, 'guard-tp', '5');
    await ev(scalp, `document.getElementById('guard-arm').click()`);
    await sleep(300);
    assert(await guardState(scalp) === 'idle', 'a scripted click armed the guard');
    assert(/at 100\.0500/.test(await text(scalp, 'guard-tp-note')), `bp level not priced: ${await text(scalp, 'guard-tp-note')}`);
    await setInput(scalp, 'guard-tp', '');
    await setInput(scalp, 'guard-sl', '12');
    await trustedClick(scalp, `document.getElementById('guard-arm')`);
    await until(() => state(`/beyond the bust price/.test(document.getElementById('guard-errors').textContent)`), 'beyond-bust error');
    // A price typed while the fields are read as distances is refused, not read as 100.05 bp.
    await setInput(scalp, 'guard-sl', '');
    await setInput(scalp, 'guard-tp', '100.05');
    await trustedClick(scalp, `document.getElementById('guard-arm')`);
    await until(() => state(`/looks like a price/.test(document.getElementById('guard-errors').textContent) && /Looks like a price/.test(document.getElementById('guard-tp-note').textContent)`), 'price typed as a distance is flagged');
    assert(await guardState(scalp) === 'idle' && await text(scalp, 'guard-tp-unit') === '(bp from entry)', 'a price-like distance armed the guard');
    await setSelect('guard-unit', 'price');
    assert(await text(scalp, 'guard-tp-unit') === '(price)', 'the field does not show its unit');
    await setInput(scalp, 'guard-sl', '');
    await setInput(scalp, 'guard-tp', '99.5');
    await trustedClick(scalp, `document.getElementById('guard-arm')`);
    await until(() => state(`/above the current price/.test(document.getElementById('guard-errors').textContent)`), 'wrong-side error');
    assert(await guardState(scalp) === 'idle', 'an invalid level armed the guard');
    await setSelect('guard-unit', 'bp');
    await setInput(scalp, 'guard-tp', '7');
    await trustedClick(scalp, `document.querySelector('.chips [data-clear="both"]')`);
    assert(await state(`document.getElementById('guard-tp').value === '' && document.getElementById('guard-sl').value === ''`), 'No TP/SL did not clear both fields');
    await trustedClick(scalp, `document.querySelector('.chips [data-sl="0.5"]')`);
    assert(await state(`document.getElementById('guard-sl').value`) === '4.90', 'half way to bust is not 4.90 bp at 1,000×');
    return { note: await text(scalp, 'guard-sl-note') };
  });

  await check('alert-only mode reports the level and presses nothing', async () => {
    await setInput(scalp, 'guard-sl', '');
    await setInput(scalp, 'guard-tp', '5');
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
    await setInput(scalp, 'guard-tp', '5');
    await setInput(scalp, 'guard-sl', '5');
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
    await until(() => state(`document.getElementById('guard-position').options.length === 1 && !document.getElementById('guard-arm').hidden && !document.getElementById('guard-arm').disabled`), 'position listed again');
    await setInput(scalp, 'guard-tp', '');
    await setInput(scalp, 'guard-sl', '5');
    await trustedClick(scalp, `document.getElementById('guard-arm')`);
    await until(async () => await guardState(scalp) === 'armed', 'armed');
    fixture.state.quotes = false;
    fixture.state.price = 99.9;
    await until(() => state(`document.getElementById('guard').hasAttribute('data-unprotected') && /NOT PROTECTED/.test(document.getElementById('guard-status').textContent)`), 'unprotected warning', 12_000);
    assert((await clicks()).close === 1, 'a stale price pressed Close');
    fixture.state.price = 100;
    fixture.state.quotes = true;
    await until(() => state(`!document.getElementById('guard').hasAttribute('data-unprotected')`), 'protection restored', 30_000);
    await trustedClick(scalp, `document.getElementById('guard-disarm')`);
    await until(async () => await guardState(scalp) === 'idle', 'disarmed');
    return { clicks: await clicks() };
  });

  await check('Long and Short stay locked until unlocked, and a first press only asks for confirmation', async () => {
    await ev(portal, `document.getElementById('rows').innerHTML = ''`);
    await until(() => state(`document.getElementById('guard-position').options.length === 0`), 'no position listed');
    await ev(scalp, `document.getElementById('entry-long').click()`);
    await sleep(300);
    assert((await clicks()).long === 0, 'a locked, scripted press reached the page');
    await trustedClick(scalp, `document.getElementById('entry-unlock')`);
    await until(() => state(`!document.getElementById('entry-long').disabled && !document.getElementById('entry-short').disabled`), 'entries unlocked');
    await ev(scalp, `document.getElementById('entry-long').click()`);
    await sleep(300);
    assert(await state(`document.getElementById('entry-status').dataset.state`) === 'idle', 'a scripted press started an entry');
    await trustedClick(scalp, `document.querySelector('input[name="entry-size"][value="0.75"]')`);
    await setInput(scalp, 'guard-tp', '5');
    await setInput(scalp, 'guard-sl', '5');
    await trustedClick(scalp, `document.getElementById('entry-long')`);
    await until(() => state(`document.getElementById('entry-long').textContent === 'Confirm long ¾'`), 'confirm prompt');
    await sleep(600);
    const counted = await clicks();
    assert(counted.long === 0 && counted.quick.length === 0, `the first press reached the page: ${JSON.stringify(counted)}`);
    await sleep(4200);
    assert(await state(`document.getElementById('entry-long').textContent`) === 'long', 'an unconfirmed press did not lapse');
    return counted;
  });

  await check('a confirmed Long sets three quarters from the page’s Max, presses Long once, and arms the levels from the real entry', async () => {
    await trustedClick(scalp, `document.getElementById('entry-long')`);
    await until(() => state(`document.getElementById('entry-long').hasAttribute('data-confirming')`), 'confirm prompt');
    // A second press straight away is the same gesture, not a confirmation.
    await trustedClick(scalp, `document.getElementById('entry-long')`);
    await sleep(400);
    assert((await clicks()).long === 0 && (await clicks()).quick.length === 0, 'a double-click confirmed the entry');
    await sleep(400);
    await trustedClick(scalp, `document.getElementById('entry-long')`);
    await until(async () => (await clicks()).long === 1, 'one Long press on the page');
    await until(async () => await guardState(scalp) === 'armed', 'levels armed from the new position', 20_000);
    const counted = await clicks();
    assert(JSON.stringify(counted.quick) === '["quick-max"]' && JSON.stringify(counted.amounts) === '["11.85264"]', `size not three quarters of Max: ${JSON.stringify(counted)}`);
    assert(counted.long === 1 && counted.short === 0, 'more than one side press');
    const seen = await state(`({ status: document.getElementById('entry-status').textContent, guard: document.getElementById('guard-status').textContent, option: document.getElementById('guard-position').selectedOptions[0]?.textContent, badge: document.getElementById('guard-badge').textContent })`);
    assert(/entry \$100\.0100/.test(seen.option) && /TP 100\.06\d* · SL 99\.95\d*/.test(seen.guard), `levels not taken from the real entry: ${JSON.stringify(seen)}`);
    assert(/will press Close/.test(seen.badge) && /Opened long\. Levels armed/.test(seen.status), JSON.stringify(seen));
    assert(await state(`document.getElementById('entry-long').disabled`), 'another entry is possible while a guard is live');
    fixture.state.price = 100.08;
    await until(async () => (await clicks()).close === 2, 'the take profit closed the new position', 20_000);
    await until(async () => await guardState(scalp) === 'closed', 'closed', 20_000);
    fixture.state.price = 100;
    return { counted, seen };
  });

  await check('with Confirm off and “No TP/SL”, Short opens in one press with nothing armed; other modes are refused', async () => {
    await until(() => state(`document.getElementById('guard-position').options.length === 0`), 'position gone', 10_000);
    await sleep(5200); // the bridge refuses a second entry within five seconds of the last
    await trustedClick(scalp, `document.querySelector('.chips [data-clear="both"]')`);
    await trustedClick(scalp, `document.getElementById('entry-confirm')`);
    await trustedClick(scalp, `document.querySelector('input[name="entry-size"][value="0.5"]')`);
    await trustedClick(scalp, `document.querySelector('input[name="entry-leverage"][value="500"]')`);
    await until(() => state(`!document.getElementById('entry-short').disabled`), 'short enabled');
    await trustedClick(scalp, `document.getElementById('entry-short')`);
    await until(async () => (await clicks()).short === 1, 'one Short press');
    await until(() => state(`/Opened short\. No take profit or stop loss is armed/.test(document.getElementById('entry-status').textContent)`), 'opened without levels', 20_000);
    const counted = await clicks();
    assert(counted.quick.at(-1) === 'quick-half' && counted.amounts.at(-1) === '7.90176' && counted.long === 1, `unexpected presses: ${JSON.stringify(counted)}`);
    assert(JSON.stringify(counted.leverage) === '["500×"]', `the 500× preset was not pressed exactly once: ${JSON.stringify(counted.leverage)}`);
    assert(/500× short/.test(await state(`document.getElementById('guard-position').selectedOptions[0]?.textContent ?? ''`)), 'the position opened at 500× was not adopted');
    assert(await guardState(scalp) === 'closed' || await guardState(scalp) === 'idle', 'a guard was armed with no levels');
    await ev(portal, `document.getElementById('mode').textContent = 'Blitz'`);
    await until(() => state(`document.getElementById('entry-long').disabled && /^Switch the Jupiter page to Classic mode/.test(document.getElementById('entry-long').title)`), 'refused outside Classic');
    await ev(portal, `document.getElementById('mode').textContent = 'Classic'`);
    return counted;
  });

  await check('the slope ladder shows a running accuracy gauge once calls settle', async () => {
    const cell = await until(() => state(`(() => { const td = document.querySelector('#slopes tbody tr td.hit'); return /[0-9]+% · [0-9]+/.test(td.textContent) ? { text: td.textContent, width: td.querySelector('.gauge i').style.width, title: td.title } : null; })()`), 'a settled 5s slope call', 60_000);
    assert(/matched the move over the next 30 seconds/.test(cell.title), 'the gauge does not explain itself');
    return cell;
  });

  await check('every tile shows its own running hit rate at each interval', async () => {
    const seen = await until(() => state(`(() => { const tiles = [...document.querySelectorAll('.tile')]; const cells = tiles.map(tile => [...tile.querySelectorAll('.hits i')].map(cell => cell.textContent));
      return cells.length === 16 && cells.every(row => row.length === 6) && /^[0-9]+$/.test(cells[0][0]) && /^[0-9]+$/.test(cells[0][2])
        ? { impulse: cells[0], title: tiles[0].querySelector('.hits i').title, late: cells[0][5] } : null; })()`), 'settled hit rates on the first tile', 60_000);
    assert(/Momentum 2s was right [0-9]+% of the time over the next 5s/.test(seen.title), `a hit-rate cell does not explain itself: ${seen.title}`);
    assert(seen.late === '·', 'the 5 minute interval showed a rate before five minutes had passed');
    return seen;
  });

  if (FULL) await check('after the warm-up the grid makes a call and draws the 30 second range', async () => {
    await until(() => ev(scalp, `document.getElementById('call').dataset.tier !== 'warming'`), 'call ready', 120_000);
    const state = await ev(scalp, `({ tier: document.getElementById('call').dataset.tier, direction: document.getElementById('call').dataset.direction, text: document.getElementById('call-text').textContent, detail: document.getElementById('call').title, meta: document.getElementById('call-meta').textContent, warm: document.querySelectorAll('.tile[data-vote=warming]').length, count: document.getElementById('tiles-count').textContent, title: document.title })`);
    assert(state.warm === 0 && ['strong', 'lean', 'mixed'].includes(state.tier), JSON.stringify(state));
    assert(/replayed without looking ahead/.test(state.detail) && /separate short live check/.test(state.detail) && /weighs each of the sixteen readings/.test(state.detail), 'the hover text does not state the measured hit rate, the untouched check and the weighting');
    assert(/weighted [+−]?[0-9]+% · recorded [0-9.]+% · live check [0-9.]+% ± [0-9.]+/.test(state.meta), `the line under the call lacks its numbers: ${state.meta}`);
    return state;
  });

  await check('the Experiments tab tests every setting at every interval, shows what each tile uses, and stays out of the order panel', async () => {
    await trustedClick(scalp, `document.getElementById('tab-experiments')`);
    const seen = await until(() => state(`(() => { const board = document.getElementById('exp-board'), rows = [...board.tBodies[0].rows];
      return !document.getElementById('panel-experiments').hidden && rows.length > 70 ? { hidden: document.getElementById('panel-live').hidden, rows: rows.length,
        columns: board.tHead.rows[0].cells.length, intervals: [...board.tHead.rows[0].cells].slice(1, -1).map(th => th.textContent),
        slots: document.querySelectorAll('#exp-slots tbody tr').length, inUse: document.querySelectorAll('#exp-board tr[data-in-use]').length,
        status: document.getElementById('exp-status').textContent, auto: document.getElementById('exp-auto').checked, cell: rows[0].cells[6].textContent, cellTitle: rows[0].cells[6].title,
        liveCells: document.querySelectorAll('#exp-board td[data-vote]:not(.rec):not([data-vote=warming])').length,
        says: [...document.querySelectorAll('#exp-slots tbody tr')].map(tr => tr.cells[2].textContent), rival: document.querySelector('#exp-slots tbody tr').cells[5].title,
        guard: getComputedStyle(document.getElementById('guard')).display, call: getComputedStyle(document.getElementById('call')).display } : null; })()`), 'the Experiments tab');
    assert(seen.hidden && seen.rows === 79 && seen.slots === 16 && seen.inUse === 16, `tab contents: ${JSON.stringify(seen)}`);
    assert(seen.columns === 14 && seen.intervals.join(' ') === '3s 5s 10s 15s 20s 30s 45s 1m 90s 2m 3m 5m', `intervals: ${seen.intervals}`);
    assert(/Testing 79 settings at 12 intervals/.test(seen.status) && seen.auto === true, seen.status);
    assert(/^[0-9]+$/.test(seen.cell) && /next 30s/.test(seen.cellTitle), `a cell does not explain itself: ${seen.cellTitle}`);
    assert(seen.liveCells > 0, 'no live result replaced a recorded figure');
    assert(/cautious estimate/.test(seen.rival), 'the switch rule is not explained');
    assert(seen.guard !== 'none' && seen.call !== 'none', 'the order panel or the call left the screen');
    if (FULL) assert(seen.says.every(text => /^[0-9]+%$/.test(text)) && Math.abs(seen.says.reduce((sum, text) => sum + Number.parseInt(text, 10), 0) - 100) <= 8, `says: ${seen.says}`);
    if (OUT) {
      const shot = await browser.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true }, scalp.sessionId);
      fs.writeFileSync(path.join(OUT, 'experiments.png'), Buffer.from(shot.data, 'base64'));
    }
    await trustedClick(scalp, `document.getElementById('tab-live')`);
    await until(() => state(`!document.getElementById('panel-live').hidden && document.getElementById('panel-experiments').hidden && document.querySelector('.tile .weight i') !== null`), 'back on the Live tab');
    return { rows: seen.rows, intervals: seen.intervals.length, liveCells: seen.liveCells, status: seen.status };
  });

  await check('the coin dropdown switches the watched coin and blocks entries while the Jupiter tab shows another', async () => {
    const options = await until(() => state(`(() => { const select = document.getElementById('coin'); return select.options.length === 3 ? [...select.options].map(option => option.value) : null; })()`), 'coin list');
    assert(options.join() === 'SOL,BTC,ZEC', `coins: ${options}`);
    await ev(scalp, `(() => { const select = document.getElementById('coin'); select.value = 'BTC'; select.dispatchEvent(new Event('change', { bubbles: true })); })()`);
    await until(() => state(`location.hash === '#market=BTC' && document.getElementById('coin')?.value === 'BTC' && document.getElementById('feed')?.dataset.state === 'live'`), 'window reloaded on BTC', 30_000);
    await until(() => state(`/The Jupiter tab is on SOL/.test(document.getElementById('guard-page').textContent)`), 'market mismatch shown');
    await trustedClick(scalp, `document.getElementById('entry-unlock')`);
    await sleep(600);
    const seen = await state(`({ unlock: document.getElementById('entry-unlock').checked, long: document.getElementById('entry-long').disabled, why: document.getElementById('entry-long').title.slice(0, 60), positions: document.getElementById('guard-position').options.length })`);
    assert(seen.unlock && seen.long && /The Jupiter tab is on SOL, not BTC/.test(seen.why), `entries were possible on the wrong market: ${JSON.stringify(seen)}`);
    assert(seen.positions === 0, 'a SOL position was offered in the BTC window');
    return { options, seen };
  });

  await check('from the Perps page the same window opens for read-outs only, with no order controls', async () => {
    const perpsUrl = scalpUrl.replace(/#market=.*$/, '#market=BTC&venue=perps');
    await browser.call('Page.navigate', { url: 'https://jup.ag/perps/long/JupUSD-BTC' }, portal.sessionId);
    const button = `document.querySelector('#smt-perps-panel')?.shadowRoot.querySelector('#smt-1000x-scalp')`;
    await until(() => ev(portal, `Boolean(${button}) && !${button}.hidden`), 'scalp button on the Perps overlay', 20_000);
    await trustedClick(portal, button);
    const view = await until(async () => { const target = (await browser.targets()).find(item => item.type === 'page' && item.url === perpsUrl); return target && targets.get(target.targetId); }, 'Perps scalp window');
    await ready.get(view.sessionId);
    await until(() => ev(view, `document.getElementById('feed')?.dataset.state === 'live' && document.getElementById('guard')?.dataset.venue === 'perps'`), 'Perps view live', 30_000);
    await sleep(1500);
    const seen = await ev(view, `(() => { const shown = id => { const node = document.getElementById(id); return Boolean(node && node.offsetParent !== null); };
      return { market: document.getElementById('market').textContent, note: shown('perps-note'), noteText: document.getElementById('perps-note').textContent,
        page: document.getElementById('guard-page').textContent, long: shown('entry-long'), short: shown('entry-short'), arm: shown('guard-arm'), unlock: shown('entry-unlock'),
        levels: shown('guard-tp'), size: shown('entry-size'), show: shown('guard-show'), tiles: document.querySelectorAll('.tile').length, tabs: shown('tab-experiments'),
        coin: document.getElementById('coin').value, title: document.getElementById('call').title }; })()`);
    assert(seen.market === '1s scalp · Perps view' && seen.note && /^Read-outs only/.test(seen.noteText) && /Opened from the Jupiter Perps page for BTC/.test(seen.page), JSON.stringify(seen));
    assert(!seen.long && !seen.short && !seen.arm && !seen.unlock && !seen.levels && !seen.size, `an order control is visible on the Perps view: ${JSON.stringify(seen)}`);
    assert(seen.show && seen.tiles === 16 && seen.tabs && seen.coin === 'BTC', JSON.stringify(seen));
    // BTC is a JLP market: the note points at the page's own Add TP / SL, and makes no such claim for the beta markets.
    assert(/On BTC the page’s positions list has its own Add TP \/ SL/.test(seen.noteText) && !/NOT offered/.test(seen.noteText), `Perps note: ${seen.noteText}`);
    assert((await browser.targets()).filter(target => target.url.startsWith(scalpUrl.replace(/#market=.*$/, ''))).length === 1, 'the 1000x window was left open beside the Perps one');
    if (OUT) {
      const shot = await browser.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true }, view.sessionId);
      fs.writeFileSync(path.join(OUT, 'perps.png'), Buffer.from(shot.data, 'base64'));
    }
    // The 1000x window was replaced; later steps look at the window that is open now.
    scalp = view;
    return seen;
  });

  await check('on a Perps beta market the window opens with the page’s own buttons, arms from the real entry, and closes with Quick close and its question', async () => {
    const betaUrl = scalpUrl.replace(/#market=.*$/, '#market=ZEC&venue=perps');
    await browser.call('Page.navigate', { url: 'https://jup.ag/perps/long/USDC-ZEC' }, portal.sessionId);
    const button = `document.querySelector('#smt-perps-panel')?.shadowRoot.querySelector('#smt-1000x-scalp')`;
    await until(() => ev(portal, `Boolean(${button}) && !${button}.hidden && Boolean(window.__perps)`), 'scalp button on the ZEC Perps overlay', 20_000);
    await trustedClick(portal, button);
    const beta = await until(async () => { const target = (await browser.targets()).find(item => item.type === 'page' && item.url === betaUrl); return target && targets.get(target.targetId); }, 'ZEC Perps scalp window');
    await ready.get(beta.sessionId);
    scalp = beta;
    await until(() => state(`document.getElementById('feed')?.dataset.state === 'live' && /Available 40 USDC/.test(document.getElementById('guard-page').textContent)`), 'order form read', 30_000);
    const panel = await state(`({ market: document.getElementById('market').textContent, page: document.getElementById('guard-page').textContent, note: document.getElementById('perps-note').textContent,
      sizes: [...document.querySelectorAll('input[name="entry-size"]')].map(input => [input.value, input.disabled, input.checked]),
      leverage: [...document.querySelectorAll('input[name="entry-leverage"]')].map(input => input.value), long: document.getElementById('entry-long').disabled,
      why: document.getElementById('entry-status').textContent, chips: [...document.querySelectorAll('.chips button[data-sl]')].map(chip => chip.textContent) })`);
    assert(panel.market === '1s scalp · Perps' && /Market/.test(panel.page) && /runs them itself/.test(panel.note) && /only while this window/.test(panel.note), JSON.stringify(panel));
    assert(JSON.stringify(panel.sizes) === JSON.stringify([['0.25', true, false], ['0.5', false, true], ['0.75', true, false], ['1', false, false]]), `sizes: ${JSON.stringify(panel.sizes)}`);
    assert(panel.leverage.join() === ',25,50' && panel.long && /Tick Unlock/.test(panel.why) && panel.chips.every(text => /liq\./.test(text)), JSON.stringify(panel));
    await trustedClick(scalp, `document.querySelector('input[name="entry-leverage"][value="25"]')`);
    await trustedClick(scalp, `document.querySelector('.chips [data-tp="50"]')`);
    await trustedClick(scalp, `document.querySelector('.chips [data-sl="0.5"]')`);
    await trustedClick(scalp, `document.querySelector('input[name="guard-mode"][value="close"]')`);
    // Half of the estimated liquidation distance at 25x on ZEC: (10000 / 25 - 100) / 2 = 150 bp.
    assert(await state(`document.getElementById('guard-sl').value`) === '150.00', 'the stop chip did not use the Perps liquidation estimate');
    await trustedClick(scalp, `document.getElementById('entry-unlock')`);
    await until(() => state(`!document.getElementById('entry-long').disabled`), 'Long enabled');
    await trustedClick(scalp, `document.getElementById('entry-long')`);
    await sleep(900);
    assert((await ev(portal, 'window.__perps.submit')) === 0, 'the first press already sent the order');
    await trustedClick(scalp, `document.getElementById('entry-long')`);
    try { await until(() => ev(portal, 'window.__perps.submit === 1'), 'one submit press', 15_000); }
    catch (error) { throw new Error(`${error.message}: ${await text(scalp, 'entry-status')} | ${await text(scalp, 'guard-errors')} | ${JSON.stringify(await ev(portal, 'window.__perps'))}`); }
    const sent = await ev(portal, 'window.__perps');
    assert(sent.side === 'Long' && sent.leverage === '25' && sent.amount === '20.0000' && sent.typed === 0, `order sent: ${JSON.stringify(sent)}`);
    await until(async () => await guardState(scalp) === 'armed', 'levels armed from the listed entry', 20_000);
    const armed = await text(scalp, 'guard-status');
    // The page's mark sits 2 bp from the oracle here; the window shows that distance beside the mark.
    assert(/oracle [+−]?[0-9.]+ bp from it/.test(await text(scalp, 'guard-position-detail')), 'the distance between oracle and mark is not shown');
    // With a position open, a second entry from the window is blocked: this venue keeps one net position per market.
    assert(await state(`document.getElementById('entry-long').disabled && document.getElementById('entry-short').disabled`), 'a second entry was possible on an open position');
    assert(/TP 100\.51/.test(armed) && /SL 98\.50/.test(armed) && /will press Close/.test(armed), `armed levels: ${armed}`);
    // Through the stop: one Quick close, one Confirm, and the row leaves.
    fixture.state.price = 98.3;
    await until(() => ev(portal, 'window.__perps.quick === 1 && window.__perps.confirm === 1'), 'quick close and its confirmation', 20_000);
    await until(async () => await guardState(scalp) === 'closed', 'closed', 20_000);
    await sleep(2500);
    const counted = await ev(portal, 'window.__perps');
    assert(counted.submit === 1 && counted.quick === 1 && counted.confirm === 1 && counted.dismiss === 0 && counted.all === 0 && counted.typed === 0, `unexpected presses: ${JSON.stringify(counted)}`);
    fixture.state.price = 100;
    if (OUT) {
      const shot = await browser.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true }, scalp.sessionId);
      fs.writeFileSync(path.join(OUT, 'perps-beta.png'), Buffer.from(shot.data, 'base64'));
    }
    return { panel: panel.page, sent, armed, counted };
  });

  await check('only public GET reads left the browser and no page error occurred', async () => {
    const sent = requests.filter(request => request.action !== 'blocked');
    assert(requests.every(request => request.method === 'GET'), 'a non-GET request was attempted');
    assert(sent.every(request => request.url === CATALOG || request.url.startsWith(HISTORY + '?') || request.url.startsWith('https://jup.ag/')), 'an unexpected host was read');
    assert(fixture.state.subscriptions.every(payload => payload.type === 'subscribe' && ['6', '1', '66'].includes(String(payload.priceFeedIds))), 'unexpected stream message');
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
