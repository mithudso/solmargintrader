#!/usr/bin/env node
/**
 * Read-only 1000x overlay browser gate. No dependencies; uses real CfT and the
 * repository CDP transport. Default is a deterministic public-contract fixture.
 * --live separately visits the actual public portal; it never connects a wallet.
 * Fixture: real browser fetch + native WebSocket to an ephemeral loopback server.
 * Only the exact public stream URL is mapped; source modules are never replaced.
 * Exit: 0 pass, 1 failed assertion, 2 browser/required public surface unavailable.
 */
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { createHash } from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import { isDeepStrictEqual } from 'node:util';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const option = (name, fallback) => args.includes(name) ? args[args.indexOf(name) + 1] : fallback;
const EXT = path.resolve(option('--extension', process.env.EXTENSION_DIR || path.resolve(here, '..')));
const LIVE = args.includes('--live');
const ONLY_ORACLE = args.includes('--oracle-only');
const ONLY_NATIVE = args.includes('--oracle-native-only');
const OUT = path.resolve(option('--evidence', path.join(process.cwd(), 'artifacts', LIVE ? '1000x-live' : '1000x-fixture')));
fs.mkdirSync(OUT, { recursive: true });
const { launch, findChromeForTesting, sleep } = await import(pathToFileURL(path.join(EXT, 'e2e/lib/cdp.mjs')));
const CATALOG = 'https://yolo-api.jup.ag/markets';
const HISTORY = 'https://perps-api.jup.ag/v1/pyth/fixed_rate%40200ms/history';
const STREAM = 'wss://perps-api.jup.ag/v1/pyth/stream';
const PORTAL = 'https://jup.ag/1000x?market=SOL&mode=classic';
const SHA = data => createHash('sha256').update(data).digest('hex');
const reviewedFiles = ['manifest.json', 'src/1000x/autotrade-view.js', 'src/1000x/content.js', 'src/1000x/feed.js', 'src/1000x/timeframes.js', 'src/1000x/indicators.js', 'src/1000x/panel-model.js', 'src/1000x/reversal.js', 'src/1000x/oracle-model.js', 'src/1000x/oracle-store.js', 'src/1000x/oracle-controller.js', 'src/1000x/oracle-view.js', 'src/1000x/panel.js', 'src/1000x/panel.html', 'src/1000x/panel.css', 'src/bg/jupiter-indicator-window.js', 'src/jupiter/attribution.js', 'vendor/lightweight-charts/lightweight-charts.standalone.production.mjs'];
const source = Object.fromEntries(reviewedFiles.map(file => [file, SHA(fs.readFileSync(path.join(EXT, file)))]));
const manifest = JSON.parse(fs.readFileSync(path.join(EXT, 'manifest.json'), 'utf8'));
const { TIMEFRAMES } = await import(pathToFileURL(path.join(EXT, 'src/1000x/timeframes.js')));
const receipt = { runner: '1000x-browser-gate', schema_version: 1, status: 'partial', observed_at: new Date().toISOString(), mode: LIVE ? 'public-live' : 'native-browser-fixture', evidence: [], changes: [], remaining: [], checks: [], source, details: { surface: PORTAL, acceptance_condition: 'Version/source identity; seven causal indicator readouts/series; current indicator header; separate window and docking lifecycle; 10m DD/UU context; completed MTF shapes and closed1m momentum; settings; fresh completed-candle signals; lifecycle; responsive layout; public reads only; no trading state changes', source_revision: { git: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: EXT, encoding: 'utf8' }).trim(), file_sha256: source }, loaded_revision: null, process_or_origin: null, configuration_identity: null, observations: [], mismatches: [], unverified_checks: [] } };
const assert = (value, message) => { if (!value) throw new Error(message); };
const same = (actual, expected, message) => assert(isDeepStrictEqual(actual, expected), `${message}: ${JSON.stringify(actual)} != ${JSON.stringify(expected)}`);
async function check(name, fn) {
  if (ONLY_NATIVE && !/native legacy10m|native IndexedDB96|executed overlay|new extension|all seven|network guard|only local/.test(name)) return null;
  if (ONLY_ORACLE && !/streaming Oracle|two actual extension windows|native IndexedDB|executed overlay|new extension|all seven|network guard|only local/.test(name)) return null;
  try { const detail = await fn(); receipt.checks.push({ name, ok: true, detail }); console.log(`ok - ${name}`); return detail; }
  catch (error) { receipt.checks.push({ name, ok: false, error: error.message }); receipt.details.mismatches.push({ name, error: error.message }); console.log(`FAIL - ${name}: ${error.message}`); return null; }
}

// Minimal RFC6455 fixture. Browser transport, frame parsing and lifecycle remain
// native; no fake WebSocket, fetch implementation or extension source is loaded.
async function websocketFixture() {
  const sockets = new Set(), subscriptions = [], historyRequests = [], state = { quotes: true, priceOverride: null, history: 'full', chartFailure: false, pattern: 'DD', clockOffsetMs: 0, frozenMs: null, oracleMode: false, hold: false, pending: [], sent: 0, upgrades: 0, closes: 0 };
  const frame = text => { const data = Buffer.from(text); if (data.length < 126) return Buffer.concat([Buffer.from([0x81, data.length]), data]); const head = Buffer.alloc(4); head[0] = 0x81; head[1] = 126; head.writeUInt16BE(data.length, 2); return Buffer.concat([head, data]); };
  const server = http.createServer((request, response) => { response.writeHead(404); response.end(); });
  server.on('upgrade', (request, socket) => {
    if (request.url !== '/oracle') { socket.destroy(); return; }
    const accept = createHash('sha1').update(request.headers['sec-websocket-key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
    socket.write(`HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ${accept}\r\n\r\n`);
    sockets.add(socket); state.upgrades++;
    let buffer = Buffer.alloc(0), feedId;
    const timer = setInterval(() => {
      if (!state.quotes || !feedId || socket.destroyed) return;
      const now = (state.frozenMs ?? Date.now() + state.clockOffsetMs) - 25;
      const payload = { type: 'streamUpdated', subscriptionId: 1, parsed: { timestampUs: String(now * 1000), priceFeeds: [{ priceFeedId: feedId, price: String(Math.round((state.priceOverride ?? (state.oracleMode ? 100 + (now / 1000 - 1700000000) / 6000 : 100 + Math.sin(now / 5000))) * 1e8)), exponent: -8, feedUpdateTimestamp: now * 1000 }] } };
      socket.write(frame(JSON.stringify(payload))); state.sent++;
    }, 200);
    socket.on('data', chunk => {
      buffer = Buffer.concat([buffer, chunk]);
      while (buffer.length >= 2) {
        const opcode = buffer[0] & 15, masked = !!(buffer[1] & 128);
        let length = buffer[1] & 127, offset = 2;
        if (length === 126) { if (buffer.length < 4) return; length = buffer.readUInt16BE(2); offset = 4; }
        if (length === 127 || !masked) { socket.destroy(); return; }
        if (buffer.length < offset + 4 + length) return;
        const mask = buffer.subarray(offset, offset + 4); offset += 4;
        const body = Buffer.from(buffer.subarray(offset, offset + length));
        for (let i = 0; i < length; i++) body[i] ^= mask[i % 4];
        buffer = buffer.subarray(offset + length);
        if (opcode === 8) { socket.end(Buffer.from([0x88, 0])); return; }
        if (opcode !== 1) continue;
        try { const payload = JSON.parse(body); subscriptions.push(payload); feedId = payload.priceFeedIds?.[0]; } catch { socket.destroy(); }
      }
    });
    socket.once('close', () => { clearInterval(timer); sockets.delete(socket); state.closes++; });
    socket.on('error', () => {});
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  function history(url) {
    historyRequests.push(url);
    if (state.chartFailure && new URL(url).searchParams.get('resolution') === '60') return { s: 'ok', t: [Date.now()], o: [], h: [], l: [], c: [] };
    if (state.history === 'invalid') return { s: 'ok', t: [Date.now()], o: [], h: [], l: [], c: [] };
    if (state.history === 'none') return { s: 'no_data' };
    const interval = Number(new URL(url).searchParams.get('resolution')) * 60;
    const current = Math.floor((state.frozenMs ?? Date.now() + state.clockOffsetMs) / 1000 / interval) * interval;
    const first = Number(new URL(url).searchParams.get('from'));
    const t = Array.from({ length: Math.floor((current - first) / interval) + 1 }, (_, i) => first + i * interval)
      .filter(time => state.history !== 'lagging' || time < current - interval)
      .filter(time => state.history !== 'gap' || time !== current - 2 * interval);
    // Finite valid OHLC can still overflow derived indicator arithmetic. Let
    // the real analytics model reject it, rather than the history decoder.
    if (state.history === 'overflow') return { s: 'ok', t, o: t.map(() => 1e308), h: t.map(() => 1.79e308), l: t.map(() => 1), c: t.map(() => 1.79e308) };
    const target = Math.floor((state.frozenMs ?? Date.now() + state.clockOffsetMs) / 600000) * 600;
    const inPair = time => time >= target - 1200 && time < target;
    const o = t.map((time, i) => state.oracleMode ? 100 + (time - 1700000000) / 6000 : inPair(time) ? 100 : 100 + Math.sin(i / 3) * 7);
    const c = o.map((v, i) => state.oracleMode ? v + interval / 6000 * 0.8 : inPair(t[i]) ? fixtureColor(t[i]) : v + Math.sin(i) * 2);
    function fixtureColor(time) { return state.pattern === 'UU' ? 101 : state.pattern === 'mixed' && time >= target - 600 ? 101 : 99; }
    return { s: 'ok', t, o, h: o.map((v, i) => Math.max(v, c[i]) + 2), l: o.map((v, i) => Math.min(v, c[i]) - 2), c };
  }
  const address = 'Ew8sRjpuBttpmhSUeaAn4dLAegWnz55AuafVcGuojCPS';
  return { state, subscriptions, historyRequests, sockets, url: `ws://127.0.0.1:${server.address().port}/oracle`, catalog: { markets: [{ symbol: 'SOL', address, feedId: 6, closed: false }, { symbol: 'BTC', address, feedId: 1, closed: false }] }, history, close: async () => { for (const socket of sockets) socket.destroy(); await new Promise(resolve => server.close(resolve)); } };
}

let browser, fixture, portal, panel;
const targets = new Map(), scripts = [], requests = [], responses = [], websocket = [], errors = [], instrumentationErrors = [], sessionReady = new Map();
const owned = new Set();
const shell = `<!doctype html><html><head><title>Public 1000x portal fixture</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;background:#080c14;color:white;font:16px system-ui}header{padding:20px}main{height:900px;padding:20px}#native-control{position:fixed;left:20px;top:80px}</style></head><body><header>Jupiter public-contract fixture</header><button id="native-control" onclick="this.dataset.clicks=String(Number(this.dataset.clicks||0)+1)">Native portal fixture control</button><main><canvas aria-label="Live market price chart" width="700" height="400"></canvas></main></body></html>`;
const forbidden = /(?:^|\/)(?:users?|requests?|accounts?|auth|login|wallets?|transactions?|tx|orders?|execute|submit|sign|send|positions?|deposit|withdraw)(?:\/|$)/i;
const writeMethods = new Set(['GET', 'HEAD', 'OPTIONS']);
function allowedPublic(url, method) { const u = new URL(url); return writeMethods.has(method) && !forbidden.test(u.pathname); }
function fixtureBootstrapCode() {
  // Auto-attach can evaluate the current document before the new-document hook
  // runs. Reapplying must not wrap Date.now twice and double the synthetic offset.
  return `(() => {globalThis.__smtFixtureClockOffsetMs=${JSON.stringify(fixture.state.clockOffsetMs)};globalThis.__smtFixtureFrozenMs=${JSON.stringify(fixture.state.frozenMs)};if(globalThis.__smtFixtureNativeTransport)return;const Native=globalThis.WebSocket;globalThis.WebSocket=class extends Native{constructor(url,...rest){super(String(url)===${JSON.stringify(STREAM)}?${JSON.stringify(fixture.url)}:url,...rest)}};const originalNow=Date.now.bind(Date);globalThis.__smtFixtureNativeNow=originalNow;Date.now=()=>globalThis.__smtFixtureFrozenMs??originalNow()+globalThis.__smtFixtureClockOffsetMs;globalThis.__smtFixtureNativeTransport=true;})()`;
}
async function setupTarget(sessionId, info) {
  targets.set(info.targetId, { ...info, sessionId }); owned.add(sessionId);
  const interceptRequests = () => browser.call('Fetch.enable', { patterns: [{ urlPattern: 'http*', requestStage: 'Request' }] }, sessionId);
  if (info.type === 'service_worker') {
    await interceptRequests();
    await browser.call('Runtime.runIfWaitingForDebugger', {}, sessionId);
    return;
  }
  await browser.call('Runtime.enable', {}, sessionId);
  await browser.call('Debugger.enable', {}, sessionId);
  await browser.call('Network.enable', {}, sessionId);
  await interceptRequests();
  if (info.type === 'page' || info.type === 'iframe') {
    await browser.call('Page.enable', {}, sessionId);
    if (fixture) {
      const code = fixtureBootstrapCode();
      await browser.call('Page.addScriptToEvaluateOnNewDocument', { source: code }, sessionId);
      await browser.evaluate(sessionId, code).catch(() => {});
    }
  }
  await browser.call('Target.setAutoAttach', { autoAttach: true, waitForDebuggerOnStart: true, flatten: true,
    filter: [{ type: 'service_worker', exclude: true }, {}] }, sessionId).catch(() => {});
  await browser.call('Runtime.runIfWaitingForDebugger', {}, sessionId);
}
async function intercept(m) {
  const { requestId, request } = m.params, url = new URL(request.url);
  const record = { at: new Date().toISOString(), method: request.method, url: request.url, target: m.sessionId, action: null };
  requests.push(record);
  const fulfill = async (body, type = 'application/json') => {
    record.action = 'fixture';
    await browser.call('Fetch.fulfillRequest', { requestId, responseCode: 200, responseHeaders: [{ name: 'content-type', value: type }, { name: 'access-control-allow-origin', value: '*' }], body: Buffer.from(typeof body === 'string' ? body : JSON.stringify(body)).toString('base64') }, m.sessionId);
  };
  if (!allowedPublic(request.url, request.method)) { record.action = 'blocked'; return browser.call('Fetch.failRequest', { requestId, errorReason: 'BlockedByClient' }, m.sessionId); }
  if (fixture) {
    if (url.origin === 'https://jup.ag' && m.params.resourceType === 'Document') return fulfill(shell, 'text/html');
    if (request.url === CATALOG) return fulfill(fixture.catalog);
    if (request.url.startsWith(HISTORY + '?')) {
      if (fixture.state.hold) { record.action = 'fixture-held'; fixture.state.pending.push(() => fulfill(fixture.history(request.url)).catch(() => {})); return; }
      return fulfill(fixture.history(request.url));
    }
    record.action = 'blocked'; return browser.call('Fetch.failRequest', { requestId, errorReason: 'BlockedByClient' }, m.sessionId);
  }
  record.action = 'public-read';
  return browser.call('Fetch.continueRequest', { requestId }, m.sessionId);
}
const ev = (page, expr) => browser.evaluate(page.sessionId, expr);
async function until(fn, what, ms = 10000) { let last; const result = await browser.waitFor(async () => { try { return await fn(); } catch (error) { last = error; return null; } }, ms, 100); assert(result, `timed out: ${what}${last ? ` (${last.message})` : ''}`); return result; }
async function findPanel(symbol = 'SOL', { detached = false } = {}) {
  const type = detached ? 'page' : 'iframe';
  const url = `chrome-extension://${browser.extensionId}/src/1000x/panel.html${detached ? '?detached=1' : ''}#market=${symbol}`;
  return until(async () => {
    const target = (await browser.targets()).find(item => item.type === type && item.url === url);
    const data = target && targets.get(target.targetId);
    if (!data) return null;
    await sessionReady.get(data.sessionId);
    return await ev(data, `document.querySelectorAll('#readouts tr').length === 7`).catch(() => false) ? data : null;
  }, `${symbol} extension ${type}`);
}
async function clickButton(page, selector) {
  const point = await ev(page, `(() => {
    const button = ${selector};
    const box = button?.getBoundingClientRect();
    return box?.width && box.height && { x: box.left + box.width / 2, y: box.top + box.height / 2 };
  })()`);
  assert(point, `missing visible button: ${selector}`);
  await browser.call('Input.dispatchMouseEvent', { type: 'mousePressed', ...point, button: 'left', clickCount: 1 }, page.sessionId);
  await browser.call('Input.dispatchMouseEvent', { type: 'mouseReleased', ...point, button: 'left', clickCount: 1 }, page.sessionId);
}
const immediateSnapshot = page => ev(page, `(() => {
  const section = document.querySelector('#immediate-indicators');
  const value = key => document.getElementById('immediate-' + key)?.textContent?.trim();
  return {
    state: section?.dataset.state,
    status: value('status'),
    zscore: value('zscore'),
    rsi: value('rsi'),
    bop: value('bop'),
    macd: value('macd'),
    direction: document.querySelector('#immediate-macd')?.dataset.direction,
    settingsBelow: Boolean(section?.compareDocumentPosition(document.querySelector('nav')) & Node.DOCUMENT_POSITION_FOLLOWING),
  };
})()`);
const indicatorNumber = value => value ? Number(value.replace('−', '-')) : NaN;
async function immediateReadings(page) {
  return until(async () => {
    const current = await immediateSnapshot(page);
    const numbers = [current.zscore, current.rsi, current.bop].map(indicatorNumber);
    return current.state === 'live' && numbers.every(Number.isFinite) ? current : null;
  }, 'three numeric current indicators');
}
const panelSnapshot = page => ev(page, `({url:location.href,market:document.querySelector('#market')?.textContent,status:document.querySelector('#status')?.textContent,state:document.querySelector('#status')?.dataset.state,timing:document.querySelector('#timing')?.textContent,note:document.querySelector('#candle-note')?.textContent,interval:document.querySelector('#timeframe')?.value,pattern:document.querySelector('#pattern')?.textContent,patternState:document.querySelector('#pattern')?.dataset.state,developing:document.querySelector('#developing-context')?.textContent,momentum:document.querySelector('#momentum-context')?.textContent,heuristic:document.querySelector('#heuristic')?.textContent,empirical:document.querySelector('#empirical')?.textContent,exit:document.querySelector('#exit-context')?.textContent,shapes:[...document.querySelectorAll('.shape-card')].map(card=>({minutes:card.dataset.minutes,text:card.textContent})),rows:[...document.querySelectorAll('#readouts tr')].map(row=>({key:row.dataset.indicator,value:row.querySelector('[data-value]').textContent,signal:row.querySelector('[data-signal]').textContent,enabled:row.querySelector('input').checked})),oracle:{horizon:Number(document.querySelector('#streaming-oracle')?.dataset.horizon),overview:[...document.querySelectorAll('#oracle-horizons tbody tr')].map(row=>({horizon:Number(row.dataset.horizon),state:row.dataset.state,trained:row.hasAttribute('data-trained')?Number(row.dataset.trained):null,resolved:row.hasAttribute('data-resolved')?Number(row.dataset.resolved):null,pending:row.hasAttribute('data-pending')?Number(row.dataset.pending):null,prediction:row.children[2]?.textContent,metrics:row.children[4]?.textContent})),state:document.querySelector('#streaming-oracle')?.dataset.state,status:document.querySelector('#oracle-status')?.textContent,prediction:document.querySelector('#oracle-prediction')?.textContent,counts:document.querySelector('#oracle-counts')?.textContent,trained:Number(document.querySelector('#oracle-counts')?.dataset.trained||0),resolved:Number(document.querySelector('#oracle-counts')?.dataset.resolved||0),feedback:document.querySelector('#oracle-feedback')?.textContent,metrics:document.querySelector('#oracle-metrics')?.textContent},canvas:document.querySelectorAll('canvas').length,width:innerWidth,scrollWidth:document.documentElement.scrollWidth})`);
async function screenshot(name, page = portal, clip) {
  if (page.type === 'iframe') {
    const origin = await ev(portal, `(()=>{const r=document.querySelector('#smt-1000x-indicators').shadowRoot.querySelector('iframe').getBoundingClientRect();return{x:r.x,y:r.y}})()`);
    if (clip) clip = { ...clip, x: clip.x + origin.x, y: clip.y + origin.y };
  }
  const result = await browser.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false, ...(clip ? { clip: { ...clip, scale: 1 } } : {}) }, page.type === 'iframe' ? portal.sessionId : page.sessionId);
  const file = path.join(OUT, `${name}.png`); fs.writeFileSync(file, Buffer.from(result.data, 'base64')); receipt.evidence.push({ source: file, observed_at: new Date().toISOString(), claim: name }); return SHA(Buffer.from(result.data, 'base64'));
}
async function refresh() { await ev(panel, `document.querySelector('#refresh').click()`); }
async function toggleDockedPanel() {
  await ev(portal, `document.querySelector('#smt-1000x-indicators').shadowRoot
    .querySelector('button[title="Collapse indicators"], button[title="Open indicators"]').click()`);
}
async function fresh() { return until(async () => { const s = await panelSnapshot(panel); return s.state === 'live' ? s : null; }, 'fresh completed-candle UI', LIVE ? 25000 : 10000); }
async function releaseHistory() { fixture.state.hold = false; for (const callback of fixture.state.pending.splice(0)) await callback(); }

let fatal;
try {
  if (!LIVE) fixture = await websocketFixture();
  const chrome = process.env.CHROME || findChromeForTesting();
  assert(chrome, 'no Chrome for Testing binary');
  browser = await launch({ chrome, extension: EXT, noSandbox: process.env.E2E_NO_SANDBOX === '1' });
  receipt.details.process_or_origin = { chrome, browser: browser.version, profile: browser.profile, extension: EXT, origin: `chrome-extension://${browser.extensionId}`, fixture_stream_mapping: fixture ? { from: STREAM, to: fixture.url, native_browser_transport: true } : null };
  browser.on(m => {
    if (m.method === 'Target.targetInfoChanged' && targets.has(m.params.targetInfo.targetId)) Object.assign(targets.get(m.params.targetInfo.targetId), m.params.targetInfo);
    if (m.method === 'Target.attachedToTarget') {
      const task = setupTarget(m.params.sessionId, m.params.targetInfo).catch(error => { instrumentationErrors.push({ target: m.params.targetInfo.url, error: error.message }); });
      sessionReady.set(m.params.sessionId, task);
    }
    if (m.method === 'Fetch.requestPaused') void intercept(m).catch(error => { if (!/session|target|closed|Invalid InterceptionId/i.test(error.message)) instrumentationErrors.push({ error: error.message }); });
    if (m.method === 'Debugger.scriptParsed') scripts.push({ sessionId: m.sessionId, scriptId: m.params.scriptId, url: m.params.url });
    if (m.method === 'Network.responseReceived') responses.push({ sessionId: m.sessionId, url: m.params.response.url, status: m.params.response.status });
    if (m.method.startsWith('Network.webSocket')) websocket.push({ method: m.method, sessionId: m.sessionId, ...m.params });
    if (m.method === 'Runtime.exceptionThrown') errors.push({ sessionId: m.sessionId, error: m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text });
  });
  await browser.call('Target.setAutoAttach', { autoAttach: true, waitForDebuggerOnStart: true, flatten: true });
  const { targetId } = await browser.call('Target.createTarget', { url: 'about:blank' });
  portal = await until(() => targets.get(targetId), 'portal target'); await sessionReady.get(portal.sessionId);
  await browser.call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false }, portal.sessionId);
  await browser.call('Page.navigate', { url: PORTAL }, portal.sessionId);
  panel = await findPanel();
  await check('new extension auto-mounts one isolated 1000x iframe with matching version', async () => {
    const mounted = await ev(portal, `({count:document.querySelectorAll('#smt-1000x-indicators').length,header:document.querySelector('#smt-1000x-indicators')?.shadowRoot.querySelector('strong').textContent,frames:document.querySelector('#smt-1000x-indicators')?.shadowRoot.querySelectorAll('iframe').length})`);
    same(mounted.count, 1, 'host count'); same(mounted.frames, 1, 'iframe count'); assert(mounted.header.includes(`v${manifest.version}`), 'header version does not match manifest');
    const actual = await ev(panel, 'chrome.runtime.getManifest()'); same(actual, manifest, 'loaded manifest'); receipt.details.configuration_identity = { version: actual.version, dry_run_default_unchanged: true }; return mounted;
  });
  await check('executed overlay modules and served assets match reviewed exact bytes', async () => {
    const loaded = {};
    for (const file of reviewedFiles) {
      if (file === 'manifest.json') continue;
      const loadedText = await ev(panel, `(async()=>{const r=await fetch(chrome.runtime.getURL(${JSON.stringify(file)}));if(!r.ok)throw new Error('asset '+r.status);return r.text()})()`);
      same(SHA(loadedText), source[file], `${file} served bytes`);
      if (file.endsWith('.js') && file.startsWith('src/1000x/')) {
        const script = scripts.find(s => s.url === `chrome-extension://${browser.extensionId}/${file}`); assert(script, `${file} execution was not observed`);
        const { scriptSource } = await browser.call('Debugger.getScriptSource', { scriptId: script.scriptId }, script.sessionId);
        same(SHA(scriptSource), source[file], `${file} executed bytes`); loaded[file] = SHA(scriptSource);
      }
    }
    receipt.details.loaded_revision = { version: manifest.version, executed_sha256: loaded, served_sha256: source }; return loaded;
  });
  if (fixture) await check('new extension panel moves with separate clicks or keyboard and stays reachable on resize', async () => {
    const shadow = `document.querySelector('#smt-1000x-indicators').shadowRoot`;
    const position = () => ev(portal, `(() => {
      const { left, top, right } = ${shadow}.host.getBoundingClientRect();
      return { left, top, right };
    })()`);
    const click = label => clickButton(portal, `[...${shadow}.querySelectorAll('button')].find(node =>
      (node.getAttribute('aria-label') || node.textContent) === ${JSON.stringify(label)})`);
    const press = async (key, keyCode, text) => {
      const params = { key, code: key, windowsVirtualKeyCode: keyCode };
      await browser.call('Input.dispatchKeyEvent', { type: 'keyDown', ...params, ...(text && { text, unmodifiedText: text }) }, portal.sessionId);
      await browser.call('Input.dispatchKeyEvent', { type: 'keyUp', ...params }, portal.sessionId);
    };
    const focus = () => ev(portal, `${shadow}.activeElement?.getAttribute('aria-label')`);
    const original = await position();
    await click('Move panel');
    same(await focus(), 'Move left', 'move menu starts focused');
    await click('Move left');
    const byClick = await position();
    assert(byClick.left < original.left, 'click did not move panel');
    await press('Enter', 13, '\r');
    const byKeyboard = await position();
    assert(byKeyboard.left < byClick.left, 'keyboard did not move panel');
    await browser.call('Emulation.setDeviceMetricsOverride', { width: 320, height: 844, deviceScaleFactor: 1, mobile: false }, portal.sessionId);
    assert(await browser.waitFor(() => ev(portal, `(() => {
      const overlay = ${shadow};
      return overlay.host.getBoundingClientRect().right <= innerWidth &&
        [...overlay.querySelectorAll('button')].filter(node => node.getBoundingClientRect().width).every(node => {
          const r = node.getBoundingClientRect();
          return r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight;
        });
    })()`)), 'moved panel controls left the narrow viewport');
    await screenshot('08-narrow-panel-move-controls');
    await press('Escape', 27);
    same(await focus(), 'Move panel', 'Escape restores focus');
    await browser.call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false }, portal.sessionId);
    same(await position(), original, 'Escape restores original placement');
    await click('Move panel');
    await click('Done');
    same(await focus(), 'Move panel', 'Done restores focus');
    assert(await ev(portal, `${shadow}.querySelector('iframe') !== null`), 'move mode removed the panel');
    return { original, byClick, byKeyboard, exitFocus: await focus() };
  });
  await check('all seven chart/readout series show fresh completed-candle values and source clocks', async () => {
    await fresh();
    const s = await until(async () => { const value = await panelSnapshot(panel); return ['active', 'baseline-warmup', 'baseline-performance'].includes(value.oracle.state) ? value : null; }, 'initialized Oracle with fresh source identity');
    same(s.rows.map(r => r.key), ['zigzag', 'rsi', 'bop', 'volty', 'psar', 'ema', 'macd'], 'indicator set');
    assert(s.rows.every(r => r.enabled && !/Warming up|NaN|Infinity/.test(r.value)), 'missing/invalid indicator values');
    assert(s.canvas >= 8, 'four chart panes did not render canvases'); assert(s.timing.includes('Exchange ') && s.timing.includes('received ') && /age [\d.]+s/.test(s.timing), 'clock distinction missing');
    assert(s.note.includes('contiguous completed candles') && s.note.includes('latest chart candle may be developing'), 'candle semantics missing');
    assert(await ev(panel, `document.body.textContent.includes('Jupiter Pyth oracle USD') && document.body.textContent.includes('TradingView') && document.body.textContent.includes('Powered by Jupiter')`), 'source/licence attribution missing');
    await screenshot('01-fresh-overlay'); receipt.details.observations.push(s); return s;
  });
  if (fixture) {
    await check('top indicator summary shows the current chart candle and all four readings', async () => {
      await fresh();
      const snapshot = await immediateReadings(panel);
      assert(snapshot.settingsBelow, 'the immediate indicators must precede the chart settings');
      assert(/10m developing candle/i.test(snapshot.status), 'current candle interval absent');
      assert(indicatorNumber(snapshot.rsi) >= 0 && indicatorNumber(snapshot.rsi) <= 100, 'RSI outside its range');
      assert(Math.abs(indicatorNumber(snapshot.bop)) <= 1, 'BOP outside its range');
      const macd = { up: '↑ Bullish', down: '↓ Bearish', neutral: '↔ Neutral' };
      same(snapshot.macd, macd[snapshot.direction], 'directional MACD text');
      assert(snapshot.macd, 'current MACD momentum must have a direction or neutral label');
      return snapshot;
    });
    await check('default 10m context shows DD then UU from closed bars and withholds unsupported probabilities', async () => {
      const first = await fresh(); same(first.interval, '600', 'new-install chart default');
      assert(/DD → watch UP/.test(first.pattern), `DD context absent: ${first.pattern}`);
      same(first.shapes.map(frame => frame.minutes), ['5', '10', '15', '20'], 'completed shape intervals');
      assert(first.shapes.every(frame => !/Warming up|Unavailable/.test(frame.text)), 'complete shape history did not warm all frames');
      assert(/Closed 1m momentum.*EMA9.*EMA21.*MACD.*BOP SMA3/.test(first.momentum), 'separate closed1m momentum absent');
      assert(/Heuristic alignment: [0-3]\/3/.test(first.heuristic) && /Not a probability/.test(first.heuristic), 'heuristic support label absent');
      assert(/probability \/ model score unavailable/.test(first.empirical), 'unsupported probability was not withheld');
      assert(/Position \/ ROE \/ exit context unavailable.*No typed position input/.test(first.exit), 'position was inferred');
      fixture.state.pattern = 'UU'; await refresh();
      const second = await until(async () => { const s = await fresh(); return /UU → watch DOWN/.test(s.pattern) ? s : null; }, 'UU short context');
      fixture.state.pattern = 'mixed'; await refresh();
      const mixed = await until(async () => { const s = await fresh(); return /No reversal setup/.test(s.pattern) ? s : null; }, 'mixed pair abstention');
      assert(/alignment unavailable/.test(mixed.heuristic), 'mixed pair retained directional alignment');
      fixture.state.pattern = 'DD'; await refresh(); await fresh();
      await screenshot('06-reversal-shape-momentum-context'); return { dd: first, uu: second, mixed };
    });
    await check('a developing target turns while its closed pair and supported context stay fixed', async () => {
      // Keep this observation away from a real minute close: the fixture uses
      // the real browser clock and a minute close legitimately changes context.
      await until(() => Date.now() % 60000 > 1500 && Date.now() % 60000 < 58000, 'stable minute observation');
      // Restart seeds the new minute if a first stream observation crossed that
      // boundary. A partial observed opening must stay unavailable in production.
      await refresh(); await fresh();
      try {
        fixture.state.priceOverride = 90;
        const down = await until(async () => { const s = await panelSnapshot(panel); return /Developing target.*DOWN/.test(s.developing) ? s : null; }, 'developing target down');
        fixture.state.priceOverride = 110;
        const up = await until(async () => { const s = await panelSnapshot(panel); return /Developing target.*UP/.test(s.developing) ? s : null; }, 'developing target up');
        for (const key of ['pattern', 'momentum', 'heuristic', 'shapes', 'empirical']) same(up[key], down[key], `developing bar changed ${key}`);
        return { down, up };
      } finally { fixture.state.priceOverride = null; await fresh(); }
    });
    await check('native browser WebSocket subscribes only to the selected public feed', async () => {
      assert(fixture.sockets.size === 1, 'expected one active native socket subscription');
      same(fixture.subscriptions[0], { type: 'subscribe', subscriptionId: 1, channel: 'fixed_rate@200ms', priceFeedIds: [6], properties: ['price', 'exponent', 'feedUpdateTimestamp'], formats: [], ignoreInvalidFeeds: false }, 'public subscription');
      assert(websocket.some(e => e.method === 'Network.webSocketFrameReceived'), 'native websocket frames absent'); return { subscriptions: fixture.subscriptions, sent_frames: fixture.state.sent };
    });
    await check('each indicator toggle changes chart pixels and persists only its local preference', async () => {
      fixture.state.quotes = false;
      await ev(panel, `document.querySelector('#chart').scrollIntoView({block:'start'})`);
      const box = await ev(panel, `(()=>{const r=document.querySelector('#chart').getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}})()`);
      const result = [];
      for (const key of ['zigzag', 'rsi', 'bop', 'volty', 'psar', 'ema', 'macd']) {
        const before = await screenshot(`toggle-${key}-on`, panel, box);
        await ev(panel, `document.querySelector('[data-indicator="${key}"] input').click()`);
        await until(async () => (await panelSnapshot(panel)).rows.find(r => r.key === key)?.signal === 'Hidden', `${key} hidden`);
        await sleep(100);
        const after = await screenshot(`toggle-${key}-off`, panel, box);
        assert(before !== after, `${key} toggle did not change chart pixels`);
        const settings = await ev(panel, `chrome.storage.local.get('jupiter1000xIndicatorView')`); same(settings.jupiter1000xIndicatorView.config[key].enabled, false, `${key} stored toggle`);
        await ev(panel, `document.querySelector('[data-indicator="${key}"] input').click()`); result.push({ key, before, after });
      }
      fixture.state.quotes = true; await fresh(); return result;
    });
    await check('parameter edits change readings; invalid values retain the last accepted settings', async () => {
      const before = await panelSnapshot(panel);
      await ev(panel, `(()=>{document.querySelector('#parameters').open=true;const f=document.querySelector('#config-form');f.elements.namedItem('rsi.length').value='3';f.elements.namedItem('bop.smoothing').value='4';f.elements.namedItem('volty.multiplier').value='1.5';f.requestSubmit()})()`);
      await until(async () => { const s = await ev(panel, `chrome.storage.local.get('jupiter1000xIndicatorView')`); return s.jupiter1000xIndicatorView?.config.rsi.length === 3; }, 'accepted RSI settings');
      await sleep(100); const accepted = await panelSnapshot(panel);
      assert(before.rows.find(r => r.key === 'rsi').value !== accepted.rows.find(r => r.key === 'rsi').value, 'RSI parameter did not affect readout');
      await ev(panel, `(()=>{document.querySelector('#parameters').open=true;const f=document.querySelector('#config-form');f.elements.namedItem('rsi.length').value='0';f.requestSubmit()})()`);
      const message = await until(() => ev(panel, `document.querySelector('#config-error').textContent`), 'invalid parameter feedback');
      const saved = await ev(panel, `chrome.storage.local.get('jupiter1000xIndicatorView')`); same(saved.jupiter1000xIndicatorView.config.rsi.length, 3, 'invalid config overwrote accepted value');
      await ev(panel, `document.querySelector('#config-form button[type=button]').click();document.querySelector('#parameters').open=false`); return { before, accepted, invalid_message: message };
    });
    await check('edited RSI thresholds render 20/80 price-line labels in the actual chart', async () => {
      await ev(panel, `(()=>{globalThis.__smtRenderedLabels=[];globalThis.__smtNativeFillText=CanvasRenderingContext2D.prototype.fillText;CanvasRenderingContext2D.prototype.fillText=function(...args){globalThis.__smtRenderedLabels.push(String(args[0]));return Reflect.apply(globalThis.__smtNativeFillText,this,args)};const f=document.querySelector('#config-form');f.elements.namedItem('rsi.oversold').value='20';f.elements.namedItem('rsi.overbought').value='80';f.requestSubmit()})()`);
      try {
        const labels = await until(() => ev(panel, `globalThis.__smtRenderedLabels.some(v=>/^20(?:\\.0+)?$/.test(v))&&globalThis.__smtRenderedLabels.some(v=>/^80(?:\\.0+)?$/.test(v)) ? [...new Set(globalThis.__smtRenderedLabels)] : null`), 'rendered 20/80 RSI labels');
        const stored = await ev(panel, `chrome.storage.local.get('jupiter1000xIndicatorView')`); same([stored.jupiter1000xIndicatorView.config.rsi.oversold,stored.jupiter1000xIndicatorView.config.rsi.overbought],[20,80],'saved RSI thresholds');
        return { labels, observation_method: 'native canvas fillText arguments recorded and forwarded without alteration' };
      } finally { await ev(panel, `CanvasRenderingContext2D.prototype.fillText=globalThis.__smtNativeFillText;delete globalThis.__smtNativeFillText;delete globalThis.__smtRenderedLabels;document.querySelector('#config-form button[type=button]').click()`); }
    });
    await check('1m/5m/10m/15m/20m/1h selection changes chart history while the same stream and learners survive', async () => {
      const intervals = [], upgrades = fixture.state.upgrades;
      for (const seconds of [300, 600, 900, 1200, 3600, 60]) {
        const before = fixture.historyRequests.length;
        await ev(panel, `(()=>{const s=document.querySelector('#timeframe');s.value=${JSON.stringify(String(seconds))};s.dispatchEvent(new Event('change'))})()`);
        const current = await fresh(); same(current.interval, String(seconds), 'selected interval'); const sourceSeconds = [600, 1200].includes(seconds) ? 300 : seconds;
        same(current.oracle.horizon, seconds, 'selected learner detail'); same(current.oracle.overview.length, 6, 'all horizon rows');
        const url = fixture.historyRequests.slice(before).map(url => new URL(url)).find(url => url.searchParams.get('resolution') === String(sourceSeconds / 60)); assert(url, 'selected history resolution absent'); await until(() => fixture.sockets.size === 1, 'one current stream'); intervals.push({ seconds, source_seconds: sourceSeconds, history_url: url.href, ui: current.interval });
      }
      same(fixture.state.upgrades, upgrades, 'chart selection replaced the shared stream');
      return intervals;
    });
    await check('intrabar reversal updates developing price while completed-candle readouts stay fixed', async () => {
      await ev(panel, `(()=>{const s=document.querySelector('#timeframe');s.value='3600';s.dispatchEvent(new Event('change'))})()`); await fresh();
      fixture.state.priceOverride = 106; await until(async () => (await panelSnapshot(panel)).market.includes('$106'), 'developing high');
      const high = await panelSnapshot(panel); fixture.state.priceOverride = 96; await until(async () => (await panelSnapshot(panel)).market.includes('$96'), 'developing reversal');
      const reversal = await panelSnapshot(panel); same(reversal.rows, high.rows, 'intrabar quote changed completed-candle explanations');
      fixture.state.priceOverride = null; await ev(panel, `(()=>{const s=document.querySelector('#timeframe');s.value='60';s.dispatchEvent(new Event('change'))})()`); await fresh(); return { high, reversal };
    });
    await check('immediate reconnect backfill cannot reuse an old fresh quote before the replacement stream sends', async () => {
      const before = await fresh(), beforeAt = Date.now();
      const oldAgeMs = Number(/age ([\d.]+)s/.exec(before.timing)?.[1]) * 1000;
      assert(Number.isFinite(oldAgeMs) && oldAgeMs < 1000, 'pre-disconnect quote was not recently received');
      const baseline = { upgrades: fixture.state.upgrades, subscriptions: fixture.subscriptions.length,
        history: fixture.historyRequests.length, frames: fixture.state.sent };
      fixture.state.quotes = false;
      let awaiting, recovered, oldQuoteAgeMs;
      try {
        for (const socket of fixture.sockets) socket.destroy();
        await until(() => fixture.state.upgrades > baseline.upgrades
          && fixture.subscriptions.length > baseline.subscriptions
          && fixture.historyRequests.length > baseline.history,
        'replacement native socket subscription after immediate history backfill', 2250);
        // The browser has completed backfill and opened/subscribed the replacement
        // native socket. Observe after rendering, while the prior quote is <3s old.
        await ev(panel, 'new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))');
        oldQuoteAgeMs = oldAgeMs + Date.now() - beforeAt;
        assert(oldQuoteAgeMs < 3000, `prior quote aged out before reconnect assertion (${oldQuoteAgeMs}ms)`);
        same(fixture.state.sent, baseline.frames, 'replacement stream sent a frame while suspended');
        awaiting = await panelSnapshot(panel);
        assert(awaiting.state !== 'live', 'immediate reconnect history revived live status from an old quote');
        assert(awaiting.rows.every(row => row.signal === 'Unavailable until feed is fresh'), 'old quote restored an explanatory signal before a replacement-stream frame');
        await screenshot('05-reconnect-awaiting-new-quote');
      } finally {
        fixture.state.quotes = true;
        recovered = await fresh();
      }
      assert(fixture.state.sent > baseline.frames, 'recovery did not receive a new native stream frame');
      return { before, awaiting, recovered, old_quote_age_ms_at_assertion: oldQuoteAgeMs,
        baseline, replacement_subscriptions: fixture.subscriptions.length,
        replacement_history_reads: fixture.historyRequests.length };
    });
    await check('stale data removes all explanatory signals before feed ten-second timeout', async () => {
      fixture.state.quotes = false;
      const stale = await until(async () => {
        const [snapshot, immediate] = await Promise.all([panelSnapshot(panel), immediateSnapshot(panel)]);
        return snapshot.state === 'stale' && immediate.state === 'stale' && snapshot.patternState === 'unavailable'
          && /alignment unavailable/.test(snapshot.heuristic)
          && snapshot.rows.every(row => row.signal === 'Unavailable until feed is fresh') ? { ...snapshot, immediate } : null;
      }, 'UI three-second freshness gate', 6500);
      await screenshot('02-stale-no-signals'); fixture.state.quotes = true;
      // A pause may straddle a minute and leave an observed opening partial.
      // Fresh ticks alone cannot certify that missing close; request real history.
      await refresh(); await fresh();
      const { zscore, rsi, bop, macd } = stale.immediate;
      same([zscore, rsi, bop, macd], ['—', '—', '—', '—'], 'stale current values must clear');
      return stale;
    });
    await check('lagging and malformed history fail closed; fresh ticks cannot revive stale readings', async () => {
      const observed = [];
      for (const mode of ['lagging', 'invalid']) {
        fixture.state.history = mode; await refresh();
        const s = await until(async () => { const s = await panelSnapshot(panel); return s.state !== 'live' && s.rows.every(r => /Unavailable|Waiting for live/.test(r.signal)) && /history|Feed/.test(s.status) ? s : null; }, `${mode} history refusal`); observed.push({ mode, snapshot: s });
      }
      fixture.state.history = 'full'; await refresh(); await fresh(); return observed;
    });
    await check('history gap trims old recursive state and does not retain pre-gap indicator values', async () => {
      fixture.state.history = 'gap'; await refresh();
      const s = await until(async () => { const s = await panelSnapshot(panel); return /earlier gap excluded/.test(s.note) ? s : null; }, 'gap reset');
      assert(s.rows.filter(r => ['rsi', 'volty', 'psar'].includes(r.key)).every(r => r.value === 'Warming up'), 'pre-gap recursive indicator values survived');
      fixture.state.history = 'full'; await refresh(); await fresh(); return s;
    });
    await check('narrow viewport keeps chart/settings/readout inside the panel', async () => {
      await browser.call('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: false }, portal.sessionId);
      await sleep(150);
      const geometry = await ev(panel, `({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,chartWidth:document.querySelector('#chart').getBoundingClientRect().width})`);
      assert(geometry.scrollWidth <= geometry.width + 1, `panel overflows ${geometry.scrollWidth}px inside ${geometry.width}px`);
      await ev(panel, `document.querySelector('#parameters').open=true`);
      const form = await ev(panel, `(()=>{const r=document.querySelector('#config-form').getBoundingClientRect();return {left:r.left,right:r.right,width:innerWidth}})()`);
      assert(form.left >= 0 && form.right <= form.width + 1, `parameter form clipped: ${JSON.stringify(form)}`);
      await ev(panel, `document.querySelector('#parameters').open=false`); await screenshot('03-narrow-overlay');
      await browser.call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false }, portal.sessionId); return { geometry, form };
    });
    await check('collapse removes iframe, closes native stream and preserves native portal controls', async () => {
      await toggleDockedPanel();
      await until(() => fixture.sockets.size === 0, 'stream closed on collapse');
      same(await ev(portal, `document.querySelector('#smt-1000x-indicators').shadowRoot.querySelectorAll('iframe').length`), 0, 'collapsed iframe count');
      const sent = fixture.state.sent, reads = fixture.historyRequests.length; await sleep(1100); same(fixture.state.sent, sent, 'frames after collapse'); same(fixture.historyRequests.length, reads, 'history after collapse');
      const native = await ev(portal, `(()=>{document.querySelector('#native-control').click();return document.querySelector('#native-control').dataset.clicks})()`); same(native, '1', 'native fixture control');
      await toggleDockedPanel(); panel = await findPanel(); await fresh(); same(fixture.sockets.size, 1, 'stream count after reopen'); return { native_control_clicks: native, stream_count: fixture.sockets.size };
    });
    await check('SPA market/route changes replace the old session and leave no duplicates', async () => {
      await ev(portal, `history.pushState({},'', '/1000x?market=BTC&mode=classic')`); panel = await findPanel('BTC'); await fresh();
      same(fixture.subscriptions.at(-1).priceFeedIds, [1], 'BTC public feed binding'); await until(() => fixture.sockets.size === 1, 'one BTC socket');
      same(await ev(portal, `document.querySelectorAll('#smt-1000x-indicators').length`), 1, 'host after market change');
      await ev(portal, `history.pushState({},'', '/swap')`); await until(() => ev(portal, `document.querySelectorAll('#smt-1000x-indicators').length===0`), 'route teardown'); await until(() => fixture.sockets.size === 0, 'route websocket teardown');
      await ev(portal, `history.pushState({},'', '/1000x?market=SOL&mode=classic')`); panel = await findPanel(); await fresh();
      same(await ev(portal, `document.querySelectorAll('#smt-1000x-indicators').length`), 1, 'host after return'); same(fixture.sockets.size, 1, 'socket after return'); return { selected_feed: fixture.subscriptions.at(-1).priceFeedIds, sockets: fixture.sockets.size };
    });
    await check('detached Chrome popup keeps one live feed and docks by button, close and navigation', async () => {
      const shadow = `document.querySelector('#smt-1000x-indicators')?.shadowRoot`;
      const sourceButton = action => `${shadow}?.querySelector('#smt-1000x-${action}')`;
      const popupTargets = async () => (await browser.targets()).filter(target =>
        target.type === 'page' && target.url.startsWith(`chrome-extension://${browser.extensionId}/src/1000x/panel.html?detached=1#`));
      const windowFor = page => browser.call('Browser.getWindowForTarget', { targetId: page.targetId });
      let detached, report, failure;
      let phase = 'synthetic click rejection';
      const detach = async (symbol = 'SOL') => {
        await browser.call('Target.activateTarget', { targetId: portal.targetId });
        await clickButton(portal, sourceButton('popout'));
        detached = await findPanel(symbol, { detached: true });
        await until(async () => (await panelSnapshot(detached)).state === 'live', 'detached live chart');
        await until(() => fixture.sockets.size === 1, 'only detached stream remains');
        same(await ev(portal, `${shadow}.querySelectorAll('iframe').length`), 0, 'docked frame must stop while detached');
        same((await popupTargets()).length, 1, 'single detached panel');
        return detached;
      };
      const restore = async (symbol = 'SOL') => {
        await until(async () => !(await popupTargets()).length, 'detached window closes');
        detached = null;
        panel = await findPanel(symbol);
        await fresh();
        await until(() => fixture.sockets.size === 1, 'one restored docked stream');
        same(await ev(portal, `${shadow}.querySelectorAll('iframe').length`), 1, 'one restored iframe');
      };
      try {
        const original = await fresh();
        await ev(portal, `${sourceButton('popout')}.click()`);
        await sleep(300);
        same((await popupTargets()).length, 0, 'synthetic page click must not open a window');
        same(await ev(portal, `${shadow}.querySelectorAll('iframe').length`), 1, 'synthetic click must keep the iframe');
        phase = 'real Chrome popup';
        await detach();
        const chromeWindow = await ev(detached, `(async()=>chrome.windows.get((await chrome.tabs.getCurrent()).windowId))()`);
        same(chromeWindow.type, 'popup', 'Chrome window type');
        const { windowId } = await windowFor(detached);
        assert(windowId !== (await windowFor(portal)).windowId, 'popup must occupy a separate browser window');
        same((await panelSnapshot(detached)).interval, original.interval, 'chart interval survives detaching');
        same(fixture.subscriptions.at(-1).priceFeedIds, [6], 'detached SOL public feed');

        phase = 'detached live indicators';
        const quoteAt = async price => {
          fixture.state.priceOverride = price;
          await until(async () => (await panelSnapshot(detached)).market.endsWith(`$${price}`), `detached quote $${price}`);
          return immediateReadings(detached);
        };
        const down = await quoteAt(80);
        const up = await quoteAt(120);
        assert(indicatorNumber(down.zscore) < 0 && indicatorNumber(up.zscore) > 0, 'detached Z-score must react to the current quote');
        assert(indicatorNumber(down.rsi) < indicatorNumber(up.rsi), 'detached RSI must react to the current quote');
        assert(indicatorNumber(down.bop) < indicatorNumber(up.bop), 'detached BOP must react to the current quote');
        same([down.direction, up.direction], ['down', 'up'], 'detached MACD momentum changes direction');
        await screenshot('09-detached-indicators', detached);
        fixture.state.priceOverride = null;

        phase = 'Dock button';
        await browser.call('Target.activateTarget', { targetId: detached.targetId });
        await clickButton(detached, `document.querySelector('#dock-window')`);
        await restore();

        phase = 'native window close';
        await detach();
        const closed = await browser.call('Target.closeTarget', { targetId: detached.targetId });
        assert(closed.success, 'closing the popup tab must close the window');
        await restore();

        phase = 'source SPA market change';
        await detach();
        await ev(portal, `history.pushState({}, '', '/1000x?market=BTC&mode=classic')`);
        await restore('BTC');
        same(fixture.subscriptions.at(-1).priceFeedIds, [1], 'BTC restores the current market instead of stale SOL');

        report = { separate_window: windowId, type: chromeWindow.type, down, up };
      } catch (error) {
        failure = new Error(`${phase}: ${error.message}`, { cause: error });
      } finally {
        try {
          fixture.state.priceOverride = null;
          for (const target of await popupTargets()) await browser.call('Target.closeTarget', { targetId: target.targetId }).catch(() => {});
          await ev(portal, `if (location.href !== ${JSON.stringify(PORTAL)}) history.pushState({}, '', ${JSON.stringify(PORTAL)})`);
          panel = await findPanel();
          await fresh();
        } catch (error) {
          if (failure) console.error('Detached fixture cleanup failed:', error.message);
          else failure = error;
        }
      }
      if (failure) throw failure;
      return report;
    });
  } else {
    await check('actual public catalog/history/stream supply SOL values from feed 6', async () => {
      const actualCatalog = await ev(panel, `(async()=>{const r=await fetch(${JSON.stringify(CATALOG)},{credentials:'omit'});return {status:r.status,body:await r.json()}})()`);
      same(actualCatalog.status, 200, 'catalog status'); const sol = actualCatalog.body.markets.filter(m => m.symbol === 'SOL'); assert(sol.length === 1 && sol[0].feedId === 6 && sol[0].closed === false, 'current SOL identity differs');
      const outgoing = websocket.filter(e => e.sessionId === panel.sessionId && e.method === 'Network.webSocketFrameSent').map(e => e.response?.payloadData).filter(Boolean).map(p => { try { return JSON.parse(p); } catch { return null; } });
      assert(outgoing.some(p => p?.type === 'subscribe' && p.priceFeedIds?.length === 1 && p.priceFeedIds[0] === 6), 'selected SOL native subscription absent');
      assert(responses.some(r => r.sessionId === panel.sessionId && r.url.startsWith(HISTORY) && r.status === 200), 'actual extension-origin history 200 not observed');
      assert(websocket.some(e => e.sessionId === panel.sessionId && e.method === 'Network.webSocketFrameReceived' && /streamUpdated/.test(e.response?.payloadData || '')), 'actual extension-origin stream frame absent'); return { markets: actualCatalog.body.markets.length, sol: sol[0], subscription: outgoing.filter(p => p?.type === 'subscribe'), snapshot: await panelSnapshot(panel) };
    });
    await check('public portal native chart/controls remain present and overlay can be collapsed', async () => {
      const before = await ev(portal, `(()=>{globalThis.__smtNativeControls=[...document.querySelectorAll('button')];return {title:document.title,buttons:globalThis.__smtNativeControls.map(e=>e.textContent?.trim()).filter(Boolean),nativeChart:!!document.querySelector('[aria-label="Live market price chart"]')}})()`);
      assert(before.nativeChart, 'actual native price canvas not found'); assert(before.buttons.length > 0, 'actual native portal controls absent');
      await toggleDockedPanel();
      same(await ev(portal, `document.querySelector('#smt-1000x-indicators').shadowRoot.querySelectorAll('iframe').length`), 0, 'collapsed public iframe');
      // Public market buttons contain live prices. Preserve their actual DOM
      // identity instead of demanding unchanged tick text across a native feed.
      const after = await ev(portal, `(()=>{const controls=[...document.querySelectorAll('button')];return {buttons:controls.map(e=>e.textContent?.trim()).filter(Boolean),controlsSame:controls.length===globalThis.__smtNativeControls.length&&controls.every((e,i)=>e===globalThis.__smtNativeControls[i]&&e.isConnected),nativeChart:!!document.querySelector('[aria-label="Live market price chart"]')}})()`);
      assert(after.controlsSame, 'native controls changed or disappeared during collapse'); assert(after.nativeChart, 'native canvas lost'); await screenshot('04-public-portal-collapsed'); return { before, after };
    });
  }
  if (fixture) {
    let twin;
    const oracleStates = page => ev(page, `(async()=>{const read=await new Promise((resolve,reject)=>{const r=indexedDB.open('solmargintrader-streaming-oracle',1);r.onsuccess=()=>{const db=r.result;const q=db.transaction('partitions').objectStore('partitions').getAll();q.onsuccess=()=>{db.close();resolve(q.result)};q.onerror=()=>{db.close();reject(new Error('oracle read'))}};r.onerror=()=>reject(new Error('oracle open'))});return read.filter(row=>row.state.market==='ORCL').map(row=>row.state)})()`);
    const oracleSnapshot = async (page, horizon = 600) => (await oracleStates(page)).find(state => JSON.parse(state.key)[4] === horizon) || null;
    const setClock = async (offset, pages) => {
      fixture.state.clockOffsetMs = offset;
      for (const page of pages.filter(Boolean)) { await ev(page, `globalThis.__smtFixtureClockOffsetMs=${offset}`); await browser.call('Page.addScriptToEvaluateOnNewDocument',{source:`globalThis.__smtFixtureClockOffsetMs=${offset}`},page.sessionId); }
    };
    await check('streaming Oracle cold start stores one prospective baseline/shadow forecast in native IndexedDB', async () => {
      fixture.state.oracleMode = true;
      fixture.catalog.markets.push({ ...fixture.catalog.markets[0], symbol: 'ORCL', feedId: 77 });
      const offset = Math.ceil(Date.now() / 60000) * 60000 + 2500 - Date.now();
      await setClock(offset, [portal]);
      await ev(portal, `history.pushState({},'', '/1000x?market=ORCL&mode=classic')`); panel = await findPanel('ORCL'); await fresh();
      await ev(panel, `(()=>{const s=document.querySelector('#timeframe');s.value='600';s.dispatchEvent(new Event('change'))})()`); await fresh();
      await until(() => ev(panel, `document.querySelector('#oracle-counts')?.dataset.trained==='0'`), 'cold native learner initialized');
      const state = await until(async () => { const s = await oracleSnapshot(panel); return s?.issued === 1 ? s : null; }, 'first prospective stored Oracle forecast');
      same(state.model.n, 0, 'cold start trained on historical labels');
      same(state.pending[0].p, 0.5, 'untrained candidate'); same(state.pending[0].servedP, 0.5, 'cold served baseline');
      same(state.pending[0].mode, 'baseline-warmup', 'cold mode');
      const all = await oracleStates(panel); same(all.length, 6, 'six initialized horizon partitions');
      for (const s of all) { same(s.model.n, 0, 'new horizon trained on historical labels'); same(s.issued, 1, 'new horizon first prospective forecast'); }
      const ui = await panelSnapshot(panel); assert(/rolling 10m/.test(await ev(panel, `document.querySelector('#oracle-selected').textContent`)), 'rolling target label absent');
      assert(/candidate|baseline/.test(ui.oracle.prediction) && /NON-UP/.test(ui.oracle.prediction), 'binary probability labels absent');
      receipt.details.observations.push({ oracle_fixture_clock: 'accelerated synthetic public-contract candles only; not public-market performance', first: state });
      return { issued: state.pending[0], ui: ui.oracle };
    });
    await check('two actual extension windows share immutable issued forecasts and native atomic learning', async () => {
      const { targetId } = await browser.call('Target.createTarget', { url: `chrome-extension://${browser.extensionId}/src/1000x/panel.html#market=ORCL` });
      twin = await until(() => targets.get(targetId), 'second extension window'); await sessionReady.get(twin.sessionId);
      await browser.call('Page.bringToFront', {}, twin.sessionId);
      await until(() => ev(twin, `document.visibilityState==='visible'`), 'owned second window foreground');
      await ev(twin, `globalThis.__smtBootstrapRefs={socket:WebSocket,now:Date.now}`);
      await ev(twin, fixtureBootstrapCode()); await ev(twin, fixtureBootstrapCode());
      assert(await ev(twin, `WebSocket===globalThis.__smtBootstrapRefs.socket&&Date.now===globalThis.__smtBootstrapRefs.now`), 'fixture initialization wrapped clock or transport twice');
      await ev(twin, `delete globalThis.__smtBootstrapRefs`);
      await until(async () => { const s = await panelSnapshot(twin); return s.state === 'live' && ['active', 'baseline-warmup', 'baseline-performance'].includes(s.oracle.state) ? s : null; }, 'second window fresh source before learning');
      await until(() => ev(twin, `document.querySelector('#oracle-counts')?.textContent.includes('pending 1')`), 'second window restored pending forecast');
      // Bounded, test-only observation forwards the original snapshot to the
      // actual method unchanged. Retain one sample for cross-platform failures.
      for (const page of [panel, twin]) await ev(page, `(async()=>{const {OracleController}=await import(chrome.runtime.getURL('src/1000x/oracle-controller.js'));const {OracleStore}=await import(chrome.runtime.getURL('src/1000x/oracle-store.js'));globalThis.__smtObserveOriginal=OracleController.prototype.observe;globalThis.__smtOraclePending=new Set();globalThis.__smtOraclePaused=false;const update=OracleStore.prototype.update;OracleStore.prototype.update=function(...args){const p=Reflect.apply(update,this,args);globalThis.__smtOraclePending.add(p);p.then(()=>globalThis.__smtOraclePending.delete(p),()=>globalThis.__smtOraclePending.delete(p));return p};OracleController.prototype.observe=function(snapshot){globalThis.__smtLastOracleInput={snapshot,seenAt:Date.now()};if(globalThis.__smtOraclePaused)return;return Reflect.apply(globalThis.__smtObserveOriginal,this,[snapshot])}})()`);
      try {
      const before = await oracleSnapshot(panel), restored = await oracleSnapshot(twin);
      same(restored.pending, before.pending, 'second window changed issued forecast'); same(restored.issued, 1, 'duplicate initial issuance');
      const fixedCutoff = before.pending[0].cutoff;
      for (let step = 1; step <= 81; step++) {
        const desired = (fixedCutoff + step * 60) * 1000 + 2500;
        await setClock(desired - Date.now(), [portal, panel, twin]);
        // Creating a target does not consistently activate it in Linux headless
        // Chrome. Production correctly pauses hidden pages; activate our owner.
        await browser.call('Page.bringToFront', {}, twin.sessionId);
        await until(async () => { const all = await oracleStates(panel); return all.length === 6 && all.every(s => s.lastIssuedCutoff === fixedCutoff + step * 60) ? all : null; }, `all six Oracle minute${step} issuance`).catch(async error => {
          const pages = [];
          for (const page of [panel, twin]) pages.push(await ev(page, `(async()=>{const trace=globalThis.__smtLastOracleInput;let input;try{const {oracleInput}=await import(chrome.runtime.getURL('src/1000x/oracle-model.js'));const i=oracleInput(trace?.snapshot,Date.now());input={eligible:i.eligible,reason:i.reason,cutoff:i.cutoff,rows:i.rows.length}}catch(error){input={error:error.message}}return{visibility:document.visibilityState,now:Date.now(),native_now:globalThis.__smtFixtureNativeNow?.(),clock_offset:globalThis.__smtFixtureClockOffsetMs,last_seen:trace?.seenAt,feed_status:trace?.snapshot.status,stream_status:trace?.snapshot.streamStatus,minute_status:trace?.snapshot.minuteStatus,quote:trace?.snapshot.quote,input,status:document.querySelector('#oracle-status')?.textContent}})()`));
          const diagnostic = { step, expected_cutoff: fixedCutoff + step * 60, pages, stored: (await oracleStates(panel)).map(s => ({ horizon: JSON.parse(s.key)[4], issued: s.issued, last_cutoff: s.lastIssuedCutoff, trained: s.model.n })), history_requests: fixture.historyRequests.slice(-6) };
          receipt.details.observations.push({ oracle_issuance_failure: diagnostic }); console.error('Oracle issuance diagnostic', JSON.stringify(diagnostic)); throw error;
        });
        if (step === 33) { const hour = await oracleSnapshot(panel, 3600); same(hour.pending.length, 34, '1h lost pending beyond32'); same(hour.model.n, 0, '1h learned before target'); }
      }
      const all = await until(async () => { const states = await oracleStates(panel); return states.length === 6 && states.every(s => s.model.n === 82 - JSON.parse(s.key)[4] / 60) ? states : null; }, 'all six genuine delayed outcome cohorts');
      const state = all.find(s => JSON.parse(s.key)[4] === 600);
      for (const s of all) {
        const horizon = JSON.parse(s.key)[4]; same(s.issued, 82, 'multiwindow duplicated forecast');
        same(s.totals.n, 82 - horizon / 60, 'multiwindow duplicated scoring'); same(s.pending.length, horizon / 60, 'own target window');
        assert(s.model.weights.some(w => w !== 0) || s.model.bias !== 0, 'deselected learner did not update');
      }
      const shadow = state.recent.find(f => f.p !== f.servedP && f.mode === 'baseline-warmup'); assert(shadow, 'actual served baseline was not preserved independently');
      assert(state.pending.at(-1).mode === 'active', 'model never left cold start');
      // Creating a second top-level page backgrounds the portal. Native Chrome
      // pauses its requestAnimationFrame callbacks; resume that UI before reading it.
      await browser.call('Page.bringToFront', {}, portal.sessionId);
      const ui = await until(async () => { const s = await panelSnapshot(panel); return s.oracle.trained === 72 && s.oracle.overview.every(row => row.trained === 82 - row.horizon / 60) ? s : null; }, 'rendered all-horizon native counts');
      assert(/candidate shadow|actually served|fixed 0.5/.test(ui.oracle.metrics), 'paired metrics labels absent');
      await ev(panel, `document.querySelector('#streaming-oracle details').open=true;window.scrollTo(0,0)`);
      await screenshot('07-streaming-oracle-learned-fixture');
      return { issued_per_horizon: state.issued, resolved_per_horizon: all.map(s => ({ horizon: JSON.parse(s.key)[4], n: s.model.n, pending: s.pending.length })), selected_model: state.model, shadow_served_example: shadow, ui: ui.oracle,
        interpretation: 'Synthetic accelerated fixture checks implementation and accounting, not future accuracy or profit', observation_method: 'One bounded snapshot observation forwards the unchanged input to the original controller; explicit owned-page activation preserves the real visibility policy' };
      } finally {
        for (const page of [panel, twin]) if (page) await ev(page, `(async()=>{const {OracleController}=await import(chrome.runtime.getURL('src/1000x/oracle-controller.js'));if(globalThis.__smtObserveOriginal)OracleController.prototype.observe=globalThis.__smtObserveOriginal;delete globalThis.__smtObserveOriginal;delete globalThis.__smtLastOracleInput})()`).catch(() => {});
      }
    });
    await check('streaming Oracle all six deselected models keep learning through selected-chart failure without a new socket', async () => {
      const before = await oracleStates(panel), upgrades = fixture.state.upgrades;
      try {
        fixture.state.chartFailure = true;
        await ev(panel, `(()=>{const s=document.querySelector('#timeframe');s.value='3600';s.dispatchEvent(new Event('change'))})()`);
        await until(async () => { const s = await panelSnapshot(panel); return s.state !== 'live' && s.rows.every(row => /Unavailable|Waiting for live/.test(row.signal)) ? s : null; }, 'selected chart history refusal');
        await setClock(fixture.state.clockOffsetMs + 60000, [portal, panel, twin]);
        const after = await until(async () => { const states = await oracleStates(panel); return states.length === 6 && states.every(s => s.model.n === before.find(old => old.key === s.key).model.n + 1) ? states : null; }, 'all models learned despite chart failure');
        const ui = await until(async () => { const s = await panelSnapshot(panel); return s.oracle.horizon === 3600 && s.oracle.overview.every(row => row.state === 'active') ? s : null; }, 'healthy all-horizon overview during chart error');
        assert(ui.state !== 'live' && ui.rows.every(row => /Unavailable|Waiting for live/.test(row.signal)), 'chart unexpectedly bypassed refusal'); same(fixture.state.upgrades, upgrades, 'chart error replaced shared socket');
        return { before: before.map(s => ({ horizon: JSON.parse(s.key)[4], n: s.model.n })), after: after.map(s => ({ horizon: JSON.parse(s.key)[4], n: s.model.n })), ui: ui.oracle };
      } finally {
        fixture.state.chartFailure = false;
        await ev(panel, `(()=>{const s=document.querySelector('#timeframe');s.value='600';s.dispatchEvent(new Event('change'))})()`); await fresh();
      }
    });
    await check('streaming Oracle native legacy10m persistence and actual-view delayed stale completion preserve honest history', async () => {
      const legacy = JSON.parse(fs.readFileSync(path.join(EXT, 'test/fixtures/oracle-0.9-10m-state.json'), 'utf8'));
      const reference = JSON.parse(fs.readFileSync(path.join(EXT, 'test/fixtures/oracle-model-0.9-provenance.json'), 'utf8'));
      same(SHA(fs.readFileSync(path.join(EXT, 'e2e/fixtures/oracle-model-0.9.mjs'))), reference.fixture_sha256, 'frozen0.9 reference source');
      receipt.details.observations.push({ legacy_browser_reference: reference });
      return ev(panel, `(async()=>{
        const {OracleStore}=await import(chrome.runtime.getURL('src/1000x/oracle-store.js'));
        const {OracleController}=await import(chrome.runtime.getURL('src/1000x/oracle-controller.js'));
        const {oracleView}=await import(chrome.runtime.getURL('src/1000x/oracle-view.js'));
        const old=await import(chrome.runtime.getURL('e2e/fixtures/oracle-model-0.9.mjs'));
        const current=await import(chrome.runtime.getURL('src/1000x/oracle-model.js'));
        const fixture=${JSON.stringify(legacy)};let original;
        const factory={open:(name,version)=>indexedDB.open(name+'-legacy-fixture',version)};
        const store=new OracleStore(factory), mount=document.createElement('section');document.body.append(mount);
        let clock, view, defer=false;const releases=[];
        const wait=async fn=>{for(let i=0;i<1000;i++){if(fn())return;await new Promise(r=>setTimeout(r,5))}throw new Error('legacy native wait '+JSON.stringify({error:view?.error,rows:Object.values(view?.horizons||{}).map(v=>({horizon:v.horizon,error:v.error,n:v.state?.model.n})),release_count:releases.length}))};
        const rows=Array.from({length:1400},(_,i)=>({time:fixture.base+i*60,open:100+i/100,high:100.02+i/100,low:99.99+i/100,close:100.01+i/100,closed:true}));
        const snapshot=()=>({symbol:'SOL',sourceIdentity:{symbol:'SOL',feedId:6,marketAddress:'Ew8sRjpuBttpmhSUeaAn4dLAegWnz55AuafVcGuojCPS',stream:'fixed_rate@200ms',kind:'oracle-ohlc'},status:'live',minuteStatus:'ready',minuteCandles:rows,quote:{price:110,exchangeMs:clock,receivedMs:clock}});
        // Run the frozen0.9 source in the actual browser. A Node-authored golden
        // JSON is not a browser checkpoint: engine libm can differ by one ULP.
        for(let minute=1000;minute<=1030;minute++){clock=(fixture.base+minute*60)*1000+2000;original=old.transitionOracle(original,old.oracleInput(snapshot(),clock)).state}
        if(original.key!==fixture.state.key||original.model.n!==21||original.issued!==31)throw new Error('browser0.9 reference identity/count mismatch');
        let crossEngineDifferences=0;
        for(const f of fixture.state.recent)for(const [name,p] of [['candidate',f.p],['served',f.servedP],['baseline',f.baselineP]]){
          const expected=current.score(p,f.y);for(const metric of ['hit','brier','logLoss'])if(f.scores[name][metric]!==expected[metric])crossEngineDifferences++;
        }
        const render=oracleView(mount), c=new OracleController({clock:()=>clock,onChange:v=>{view=v;render(v)},store:{
          update:async(key,reduce)=>{const result=await store.update(key,reduce);return defer?new Promise(resolve=>releases.push(()=>resolve(result))):result},
          cancelPending:()=>store.cancelPending(),close:()=>store.close()}});
        try{
          await store.update(original.key,()=>({state:original,changed:true}));c.observe(snapshot());
          await wait(()=>view?.state?.model.n===21&&Object.values(view.horizons).every(v=>v.state));
          const restored=(await store.update(original.key,state=>({state,changed:false}))).state;
          if(JSON.stringify(restored)!==JSON.stringify(original))throw new Error('legacy weights/pending/metrics changed');
          for(const v of Object.values(view.horizons))if(v.horizon!==600&&(v.state.model.n!==0||v.state.historicalTrainingSamples!==0))throw new Error('new horizon retrospective training');
          defer=true;clock+=60000;c.observe(snapshot());await wait(()=>releases.length===6);
          c.observe({...snapshot(),status:'stale'});
          const immediate={state:mount.dataset.state,trained:mount.querySelector('#oracle-counts').dataset.trained,prediction:mount.querySelector('#oracle-prediction').textContent};
          if(immediate.state!=='waiting'||immediate.trained!=='21'||!immediate.prediction.includes('Historical stored'))throw new Error('stale input cleared or activated known evidence');
          releases.splice(0).forEach(release=>release());await wait(()=>view?.state?.model.n===22);
          if(view.inputReady||mount.dataset.state!=='waiting'||![...mount.querySelectorAll('#oracle-horizons tbody tr')].every(r=>r.dataset.state==='waiting'))throw new Error('late completion reactivated a stale horizon');
          const result={legacy_key:original.key,legacy_trained:21,resumed_trained:22,immediate,late_input_ready:view.inputReady,all_six_historical:true,native_indexeddb:true,node_browser_score_differences:crossEngineDifferences,reference_source:'frozen0.9 executed inside the real browser; no validation or score was relaxed'};
          c.stop();const reopen=new OracleStore(factory);
          try{const saved=await reopen.update(original.key,state=>({state,changed:false}));if(saved.state.model.n!==22)throw new Error('native restart lost learned state')}finally{reopen.close()}
          return result;
        }finally{c.stop();mount.remove()}
      })()`);
    });
    await check('native IndexedDB96-partition capacity refuses new evidence without evicting or blocking existing updates', async () => {
      return ev(panel, `(async()=>{const {OracleStore}=await import(chrome.runtime.getURL('src/1000x/oracle-store.js'));const {ORACLE}=await import(chrome.runtime.getURL('src/1000x/oracle-model.js'));
        const store=new OracleStore({open:(name,version)=>indexedDB.open(name+'-capacity-fixture',version)});
        try{for(let i=0;i<ORACLE.maxPartitions;i++)await store.update('capacity-fixture-'+i,()=>({state:{count:1},changed:true}));
          let refusal;try{await store.update('capacity-fixture-extra',()=>({state:{count:1},changed:true}))}catch(error){refusal=error.message}
          if(refusal!=='oracle_partition_capacity')throw new Error('native capacity did not refuse');
          const existing=await store.update('capacity-fixture-0',state=>({state:{count:state.count+1},changed:true}));
          if(existing.state.count!==2)throw new Error('capacity blocked or reset existing evidence');return {capacity:ORACLE.maxPartitions,refusal,existing_count:existing.state.count,native_indexeddb:true};
        }finally{store.close()}})()`);
    });
    await check('streaming Oracle invalid analytics clears an active trained display and fresh history restores its evidence', async () => {
      const before = await oracleSnapshot(panel);
      assert(before.model.n >= 20, 'invalid-input case did not start from a trained learner');
      try {
        fixture.state.history = 'overflow';
        await setClock(fixture.state.clockOffsetMs + 60000, [portal, panel, twin]);
        const invalid = await until(async () => { const s = await panelSnapshot(panel); return s.state === 'error' && /Invalid candle or indicator/.test(s.status) ? s : null; }, 'actual invalid derived analytics');
        assert(invalid.oracle.state !== 'active', 'invalid chart retained an active Oracle prediction');
        assert(/Historical stored/.test(invalid.oracle.prediction), 'invalid shared analytics did not label retained evidence historical');
        assert(invalid.oracle.overview.every(row => row.state === 'error' || row.state === 'waiting'), 'invalid shared minutes kept a horizon live');
      } finally {
        fixture.state.history = 'full'; await refresh(); await fresh();
      }
      const recovered = await until(async () => { const s = await panelSnapshot(panel); return s.oracle.state === 'active' && s.oracle.trained >= before.model.n ? s : null; }, 'fresh analytics restores trained learner');
      const stored = await oracleSnapshot(panel);
      assert(stored.model.n >= before.model.n, 'analytics invalidation reset persisted learning');
      return { before_samples: before.model.n, recovered_samples: stored.model.n, ui: recovered.oracle };
    });
    await check('native IndexedDB abort/reload preserves counters and unknown outcomes stay outside learning', async () => {
      await browser.call('Page.bringToFront', {}, portal.sessionId);
      // Prevent the two fixture producers from committing a later minute between
      // the baseline and the aborted transaction. Drain their real pending store
      // promises, then serialize behind IndexedDB's existing readwrite queue.
      let before, beforeAll, clockFrozen = false;
      const pausedPages = [];
      const cleanupErrors = [];
      const pauseToken = crypto.randomUUID();
      try {
      for (const page of [panel, twin]) {
        pausedPages.push(page);
        await ev(page, `(async()=>{const {OracleController}=await import(chrome.runtime.getURL('src/1000x/oracle-controller.js'));const previous=OracleController.prototype.observe;const descriptor=Object.getOwnPropertyDescriptor(globalThis,'__smtAbortPause');if(descriptor)throw Error('abort pause already installed');const state={owner:${JSON.stringify(pauseToken)},previous,intercepted:0};globalThis.__smtAbortPause=state;OracleController.prototype.observe=function(...args){state.intercepted++;return undefined};OracleController.prototype.observe.call({},{});if(state.intercepted!==1)throw Error('abort pause failed')})()`);
      }
      for (const page of [panel, twin]) await ev(page, `(async()=>{const end=globalThis.__smtFixtureNativeNow()+10000;const bounded=async promise=>{const remaining=end-globalThis.__smtFixtureNativeNow();if(remaining<=0)throw Error('oracle fixture drain timeout');let timer;try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('oracle fixture drain timeout')),remaining)})])}finally{clearTimeout(timer)}};do{await bounded(Promise.allSettled([...globalThis.__smtOraclePending]));await bounded(new Promise((resolve,reject)=>{const r=indexedDB.open('solmargintrader-streaming-oracle',1);r.onerror=()=>reject(r.error);r.onsuccess=()=>{const db=r.result,tx=db.transaction('partitions','readwrite');tx.objectStore('partitions').get('__fixture_drain__');tx.oncomplete=()=>{db.close();resolve()};tx.onabort=()=>{db.close();reject(tx.error)}}}));await Promise.resolve()}while(globalThis.__smtOraclePending.size);return true})()`);
      console.log('Oracle recovery fixture: reading checkpoint');
      before = await oracleSnapshot(panel); beforeAll = await oracleStates(panel);
      console.log('Oracle recovery fixture: aborting a native transaction');
      const abort = await ev(panel, `(async()=>{const {OracleStore}=await import(chrome.runtime.getURL('src/1000x/oracle-store.js'));const store=new OracleStore();try{await store.update(${JSON.stringify('PLACEHOLDER')},()=>{throw new Error('fixture abort')});return false}catch(error){return error.message==='fixture abort'}finally{store.close()}})()` .replace(JSON.stringify('PLACEHOLDER'), JSON.stringify(before.key)));
      assert(abort, 'native transaction did not reject'); same(await oracleSnapshot(panel), before, 'aborted transition changed model');
      // Freeze the fixture server and each browser clock at the already-issued
      // cutoff. The new frame inherits the same frozen clock from bootstrap.
      if (fixture.state.frozenMs !== null) throw Error('fixture clock already frozen');
      fixture.state.frozenMs = before.lastIssuedCutoff * 1000 + 10000;
      clockFrozen = true;
      for (const page of [portal, panel, twin]) await ev(page, `globalThis.__smtFixtureFrozenMs=${fixture.state.frozenMs}`);
      console.log('Oracle recovery fixture: reopening the original window');
      await toggleDockedPanel();
      await until(() => fixture.sockets.size === 1, 'collapsed original stream with twin preserved');
      await toggleDockedPanel();
      panel = await findPanel('ORCL'); await fresh();
      assert(await ev(panel, `Date.now()===${fixture.state.frozenMs}`), 'reload did not inherit the frozen fixture clock');
      const restored = await until(async () => { const s = await oracleSnapshot(panel); return s?.model.n === before.model.n ? s : null; }, 'reloaded native learner');
      same(restored.pending, before.pending, 'reload changed pending features/probabilities'); same(restored.totals, before.totals, 'reload changed metrics');
      same(await oracleStates(panel), beforeAll, 'reopening changed a nonselected model ledger');
      assert(await ev(panel, `Date.now()===${fixture.state.frozenMs}`), 'fixture clock changed during ledger comparison');
      } finally {
        if (clockFrozen) {
          fixture.state.frozenMs = null;
          for (const page of [portal, panel, twin]) if (page) await ev(page, 'globalThis.__smtFixtureFrozenMs=null').catch(error => cleanupErrors.push(error.message));
        }
        for (const page of pausedPages) await ev(page, `(async()=>{const {OracleController}=await import(chrome.runtime.getURL('src/1000x/oracle-controller.js'));const state=globalThis.__smtAbortPause;if(state?.owner===${JSON.stringify(pauseToken)}){OracleController.prototype.observe=state.previous;delete globalThis.__smtAbortPause}})()`).catch(error => { if (page === twin || page === panel) cleanupErrors.push(error.message); });
        if (cleanupErrors.length) console.error('Oracle fixture cleanup failed:', cleanupErrors.join('; '));
      }
      if (cleanupErrors.length) throw Error(`Oracle fixture cleanup failed: ${cleanupErrors.join('; ')}`);
      console.log('Oracle recovery fixture: advancing past unknown outcomes');
      fixture.state.history = 'none';
      await setClock(fixture.state.clockOffsetMs + 15 * 60000, [portal, panel, twin]);
      await refresh();
      console.log('Oracle recovery fixture: checking expiry without labels');
      const expired = await until(async () => { const s = await oracleSnapshot(panel); return s?.expired > before.expired ? s : null; }, 'unknown labels expire').catch(async error => {
        console.error('Oracle expiry diagnostic', JSON.stringify({ ui: await panelSnapshot(panel), clock: await ev(panel, `({now:Date.now(),offset:globalThis.__smtFixtureClockOffsetMs,visibility:document.visibilityState})`) }));
        throw error;
      });
      same(expired.model.n, before.model.n, 'unknown outcomes trained'); same(expired.totals.n, before.totals.n, 'unknown outcomes scored');
      for (const s of await oracleStates(panel)) { const old = beforeAll.find(row => row.key === s.key); same(s.model.n, old.model.n, 'unknown nonselected outcome trained'); same(s.totals.n, old.totals.n, 'unknown nonselected outcome scored'); }
      await until(() => ev(panel, `document.querySelector('#oracle-prediction').textContent.includes('resolved UP')`), 'resolved forecast retains its known label after pending expiry');
      await browser.call('Target.closeTarget', { targetId: twin.targetId }); twin = null;
      fixture.state.history = 'full'; fixture.state.oracleMode = false; await setClock(0, [portal, panel]);
      await ev(portal, `history.pushState({},'', '/1000x?market=SOL&mode=classic')`); panel = await findPanel(); await fresh();
      return { before: { n: before.model.n, issued: before.issued }, after: { n: expired.model.n, expired: expired.expired }, native_abort: true };
    });
    if (twin) await browser.call('Target.closeTarget', { targetId: twin.targetId }).catch(() => {});
  } else {
    await check('public streaming Oracle shows honest initial prospective state without fabricated performance', async () => {
      // The earlier public UI snapshot was taken before collapse; a new profile
      // cannot have resolved a10m target during this bounded acceptance run.
      const observed = receipt.checks.find(c => c.name.startsWith('all seven'))?.detail;
      assert(observed?.oracle, 'public Oracle UI snapshot absent');
      same(observed.oracle.trained, 0, 'new public profile fabricated training samples');
      same(observed.oracle.resolved, 0, 'new public profile fabricated resolved accuracy');
      same(observed.oracle.overview.length, 6, 'actual public all-horizon overview');
      assert(observed.oracle.overview.every(row => row.trained === 0 && row.resolved === 0), 'new public horizon fabricated trained/resolved evidence');
      assert(/NON-UP|No issued forecast|unavailable/.test(observed.oracle.prediction), 'public target availability label missing');
      return observed.oracle;
    });
  }
  await check('only local view preferences persist; sync/secrets/arming stay untouched', async () => {
    const workerInfo = (await browser.targets()).find(t => t.url === `chrome-extension://${browser.extensionId}/${manifest.background.service_worker}`);
    assert(workerInfo, 'extension worker absent'); const worker = { sessionId: await browser.attach(workerInfo.targetId) }; await browser.call('Runtime.enable', {}, worker.sessionId);
    const result = await ev(worker, `(async()=>({local:await chrome.storage.local.get(null),sync:await chrome.storage.sync.get(null)}))()`);
    same(result.sync, {}, 'sync storage'); assert(!result.local.secrets, 'secret material was created');
    assert(result.local.runtime?.armed !== true && (result.local.config?.mode === undefined || result.local.config.mode === 'dry-run'), 'fresh-install trading mode changed or trading was armed');
    const unexpected = Object.keys(result.local).filter(k => !['config','runtime','limits','jupiter1000xIndicatorView','ownerSourceIdentity'].includes(k));
    assert(!unexpected.some(k => /wallet|secret|key|session/i.test(k)), `unexpected sensitive storage: ${unexpected}`);
    receipt.details.configuration_identity = { ...receipt.details.configuration_identity, storage_keys: Object.keys(result.local), sync_empty: true, armed: result.local.runtime?.armed ?? false, mode: result.local.config?.mode ?? 'fresh-install-default' }; return receipt.details.configuration_identity;
  });
  await check('network guard allowed public reads only and no operational endpoint was attempted by overlay', async () => {
    const panelSessions = new Set(scripts.filter(s => s.url === `chrome-extension://${browser.extensionId}/src/1000x/panel.js`).map(s => s.sessionId));
    const ownRequests = requests.filter(r => panelSessions.has(r.target));
    assert(ownRequests.some(r => r.url === CATALOG), 'overlay market read absent');
    same(ownRequests.filter(r => !writeMethods.has(r.method) || forbidden.test(new URL(r.url).pathname)), [], 'unsafe overlay request');
    assert(requests.filter(r => !allowedPublic(r.url, r.method)).every(r => r.action === 'blocked'), 'guard allowed a blocked operation');
    same(instrumentationErrors, [], 'CDP guard/instrumentation errors');
    const ownErrors = errors.filter(e => panelSessions.has(e.sessionId)); same(ownErrors, [], 'overlay uncaught browser errors'); return { public_overlay_reads: ownRequests.length, blocked_portal_requests: requests.filter(r => r.action === 'blocked').length, overlay_errors: ownErrors };
  });
} catch (error) { fatal = error; receipt.remaining.push(error.message); receipt.details.unverified_checks.push(error.message); console.error(error.stack); if (browser && portal) await screenshot('failure').catch(() => {}); }
finally {
  if (browser) await browser.close();
  if (fixture) await fixture.close();
  const failed = receipt.checks.filter(check => !check.ok);
  receipt.status = fatal ? 'blocked' : failed.length ? 'partial' : 'complete';
  receipt.details.unverified_checks.push(...failed.map(check => check.name));
  receipt.details.observations.push({ http_requests: requests, http_responses: responses, websocket_summary: websocket.filter(e => ['Network.webSocketCreated','Network.webSocketWillSendHandshakeRequest','Network.webSocketHandshakeResponseReceived','Network.webSocketClosed','Network.webSocketFrameError'].includes(e.method)).map(e => ({ method: e.method, sessionId: e.sessionId, requestId: e.requestId, url: e.url, timestamp: e.timestamp, status: e.response?.status, request_header_names: Object.keys(e.request?.headers || {}), response_header_names: Object.keys(e.response?.headers || {}), error: e.errorMessage })), uncaught_errors: errors, instrumentation_errors: instrumentationErrors });
  receipt.evidence.push({ source: path.join(OUT, 'receipt.json'), observed_at: new Date().toISOString(), claim: `${receipt.checks.filter(check => check.ok).length}/${receipt.checks.length} completed checks passed; fixture and public-live are separate scopes` });
  fs.writeFileSync(path.join(OUT, 'receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
  console.log(`${receipt.checks.filter(check => check.ok).length}/${receipt.checks.length} checks passed (${receipt.status}); ${path.join(OUT, 'receipt.json')}`);
}
process.exitCode = fatal ? 2 : receipt.checks.some(check => !check.ok) ? 1 : 0;
