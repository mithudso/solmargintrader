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
const OUT = path.resolve(option('--evidence', path.join(process.cwd(), 'artifacts', LIVE ? '1000x-live' : '1000x-fixture')));
fs.mkdirSync(OUT, { recursive: true });
const { launch, findChromeForTesting, sleep } = await import(pathToFileURL(path.join(EXT, 'e2e/lib/cdp.mjs')));
const CATALOG = 'https://yolo-api.jup.ag/markets';
const HISTORY = 'https://perps-api.jup.ag/v1/pyth/fixed_rate%40200ms/history';
const STREAM = 'wss://perps-api.jup.ag/v1/pyth/stream';
const PORTAL = 'https://jup.ag/1000x?market=SOL&mode=classic';
const SHA = data => createHash('sha256').update(data).digest('hex');
const reviewedFiles = ['manifest.json', 'src/1000x/content.js', 'src/1000x/feed.js', 'src/1000x/indicators.js', 'src/1000x/panel-model.js', 'src/1000x/reversal.js', 'src/1000x/panel.js', 'src/1000x/panel.html', 'src/1000x/panel.css', 'src/jupiter/attribution.js', 'vendor/lightweight-charts/lightweight-charts.standalone.production.mjs'];
const source = Object.fromEntries(reviewedFiles.map(file => [file, SHA(fs.readFileSync(path.join(EXT, file)))]));
const manifest = JSON.parse(fs.readFileSync(path.join(EXT, 'manifest.json'), 'utf8'));
const receipt = { runner: '1000x-browser-gate', schema_version: 1, status: 'partial', observed_at: new Date().toISOString(), mode: LIVE ? 'public-live' : 'native-browser-fixture', evidence: [], changes: [], remaining: [], checks: [], source, details: { surface: PORTAL, acceptance_condition: 'Version/source identity; seven causal indicator readouts/series; 10m DD/UU context; completed MTF shapes and closed1m momentum; settings; fresh completed-candle signals; lifecycle; responsive layout; public reads only; no trading state changes', source_revision: { git: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: EXT, encoding: 'utf8' }).trim(), file_sha256: source }, loaded_revision: null, process_or_origin: null, configuration_identity: null, observations: [], mismatches: [], unverified_checks: [] } };
const assert = (value, message) => { if (!value) throw new Error(message); };
const same = (actual, expected, message) => assert(isDeepStrictEqual(actual, expected), `${message}: ${JSON.stringify(actual)} != ${JSON.stringify(expected)}`);
async function check(name, fn) {
  try { const detail = await fn(); receipt.checks.push({ name, ok: true, detail }); console.log(`ok - ${name}`); return detail; }
  catch (error) { receipt.checks.push({ name, ok: false, error: error.message }); receipt.details.mismatches.push({ name, error: error.message }); console.log(`FAIL - ${name}: ${error.message}`); return null; }
}

// Minimal RFC6455 fixture. Browser transport, frame parsing and lifecycle remain
// native; no fake WebSocket, fetch implementation or extension source is loaded.
async function websocketFixture() {
  const sockets = new Set(), subscriptions = [], historyRequests = [], state = { quotes: true, priceOverride: null, history: 'full', pattern: 'DD', hold: false, pending: [], sent: 0, upgrades: 0, closes: 0 };
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
      const now = Date.now() - 25;
      const payload = { type: 'streamUpdated', subscriptionId: 1, parsed: { timestampUs: String(now * 1000), priceFeeds: [{ priceFeedId: feedId, price: String(Math.round((state.priceOverride ?? (100 + Math.sin(now / 5000))) * 1e8)), exponent: -8, feedUpdateTimestamp: now * 1000 }] } };
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
    if (state.history === 'invalid') return { s: 'ok', t: [Date.now()], o: [], h: [], l: [], c: [] };
    if (state.history === 'none') return { s: 'no_data' };
    const interval = Number(new URL(url).searchParams.get('resolution')) * 60;
    const current = Math.floor(Date.now() / 1000 / interval) * interval;
    const first = Number(new URL(url).searchParams.get('from'));
    const t = Array.from({ length: Math.floor((current - first) / interval) + 1 }, (_, i) => first + i * interval)
      .filter(time => state.history !== 'lagging' || time < current - interval)
      .filter(time => state.history !== 'gap' || time !== current - 2 * interval);
    const target = Math.floor(Date.now() / 600000) * 600;
    const inPair = time => time >= target - 1200 && time < target;
    const o = t.map((time, i) => inPair(time) ? 100 : 100 + Math.sin(i / 3) * 7);
    const c = o.map((v, i) => inPair(t[i]) ? fixtureColor(t[i]) : v + Math.sin(i) * 2);
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
async function setupTarget(sessionId, info) {
  targets.set(info.targetId, { ...info, sessionId }); owned.add(sessionId);
  await browser.call('Runtime.enable', {}, sessionId);
  await browser.call('Debugger.enable', {}, sessionId);
  await browser.call('Network.enable', {}, sessionId);
  await browser.call('Fetch.enable', { patterns: [{ urlPattern: 'http*', requestStage: 'Request' }] }, sessionId);
  if (info.type === 'page' || info.type === 'iframe') {
    await browser.call('Page.enable', {}, sessionId);
    if (fixture) {
      const code = `(() => {const Native = globalThis.WebSocket; globalThis.WebSocket = class extends Native {constructor(url,...rest){super(String(url) === ${JSON.stringify(STREAM)} ? ${JSON.stringify(fixture.url)} : url,...rest)}}; globalThis.__smtFixtureNativeTransport = true;})()`;
      await browser.call('Page.addScriptToEvaluateOnNewDocument', { source: code }, sessionId);
      await browser.evaluate(sessionId, code).catch(() => {});
    }
  }
  await browser.call('Target.setAutoAttach', { autoAttach: true, waitForDebuggerOnStart: true, flatten: true }, sessionId).catch(() => {});
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
async function findPanel(symbol = 'SOL') { return until(async () => { const t = (await browser.targets()).find(t => t.url === `chrome-extension://${browser.extensionId}/src/1000x/panel.html#market=${symbol}`); if (!t) return null; const data = targets.get(t.targetId); if (!data) return null; await sessionReady.get(data.sessionId); if (!await ev(data, `document.querySelectorAll('#readouts tr').length === 7`).catch(() => false)) return null; return data; }, `${symbol} extension iframe`); }
const panelSnapshot = page => ev(page, `({url:location.href,market:document.querySelector('#market')?.textContent,status:document.querySelector('#status')?.textContent,state:document.querySelector('#status')?.dataset.state,timing:document.querySelector('#timing')?.textContent,note:document.querySelector('#candle-note')?.textContent,interval:document.querySelector('#timeframe')?.value,pattern:document.querySelector('#pattern')?.textContent,patternState:document.querySelector('#pattern')?.dataset.state,developing:document.querySelector('#developing-context')?.textContent,momentum:document.querySelector('#momentum-context')?.textContent,heuristic:document.querySelector('#heuristic')?.textContent,empirical:document.querySelector('#empirical')?.textContent,exit:document.querySelector('#exit-context')?.textContent,shapes:[...document.querySelectorAll('.shape-card')].map(card=>({minutes:card.dataset.minutes,text:card.textContent})),rows:[...document.querySelectorAll('#readouts tr')].map(row=>({key:row.dataset.indicator,value:row.querySelector('[data-value]').textContent,signal:row.querySelector('[data-signal]').textContent,enabled:row.querySelector('input').checked})),canvas:document.querySelectorAll('canvas').length,width:innerWidth,scrollWidth:document.documentElement.scrollWidth})`);
async function screenshot(name, page = portal, clip) {
  if (page !== portal) {
    const origin = await ev(portal, `(()=>{const r=document.querySelector('#smt-1000x-indicators').shadowRoot.querySelector('iframe').getBoundingClientRect();return{x:r.x,y:r.y}})()`);
    if (clip) clip = { ...clip, x: clip.x + origin.x, y: clip.y + origin.y };
  }
  const result = await browser.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false, ...(clip ? { clip: { ...clip, scale: 1 } } : {}) }, portal.sessionId);
  const file = path.join(OUT, `${name}.png`); fs.writeFileSync(file, Buffer.from(result.data, 'base64')); receipt.evidence.push({ source: file, observed_at: new Date().toISOString(), claim: name }); return SHA(Buffer.from(result.data, 'base64'));
}
async function refresh() { await ev(panel, `document.querySelector('#refresh').click()`); }
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
  await check('all seven chart/readout series show fresh completed-candle values and source clocks', async () => {
    const s = await fresh(); same(s.rows.map(r => r.key), ['zigzag', 'rsi', 'bop', 'volty', 'psar', 'ema', 'macd'], 'indicator set');
    assert(s.rows.every(r => r.enabled && !/Warming up|NaN|Infinity/.test(r.value)), 'missing/invalid indicator values');
    assert(s.canvas >= 8, 'four chart panes did not render canvases'); assert(s.timing.includes('Exchange ') && s.timing.includes('received ') && /age [\d.]+s/.test(s.timing), 'clock distinction missing');
    assert(s.note.includes('contiguous completed candles') && s.note.includes('latest chart candle may be developing'), 'candle semantics missing');
    assert(await ev(panel, `document.body.textContent.includes('Jupiter Pyth oracle USD') && document.body.textContent.includes('TradingView') && document.body.textContent.includes('Powered by Jupiter')`), 'source/licence attribution missing');
    await screenshot('01-fresh-overlay'); receipt.details.observations.push(s); return s;
  });
  if (fixture) {
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
    await check('1m/5m/10m/15m/20m/1h selection restarts history/stream with matching source interval', async () => {
      const intervals = [];
      for (const seconds of [300, 600, 900, 1200, 3600, 60]) {
        const before = fixture.historyRequests.length;
        await ev(panel, `(()=>{const s=document.querySelector('#timeframe');s.value=${JSON.stringify(String(seconds))};s.dispatchEvent(new Event('change'))})()`);
        const current = await fresh(); same(current.interval, String(seconds), 'selected interval'); const sourceSeconds = [600, 1200].includes(seconds) ? 300 : seconds;
        const url = fixture.historyRequests.slice(before).map(url => new URL(url)).find(url => url.searchParams.get('resolution') === String(sourceSeconds / 60)); assert(url, 'selected history resolution absent'); await until(() => fixture.sockets.size === 1, 'one current stream'); intervals.push({ seconds, source_seconds: sourceSeconds, history_url: url.href, ui: current.interval });
      }
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
      const stale = await until(async () => { const s = await panelSnapshot(panel); return s.state === 'stale' && s.patternState === 'unavailable' && /alignment unavailable/.test(s.heuristic) && s.rows.every(r => r.signal === 'Unavailable until feed is fresh') ? s : null; }, 'UI three-second freshness gate', 6500);
      await screenshot('02-stale-no-signals'); fixture.state.quotes = true; await fresh(); return stale;
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
      await ev(portal, `document.querySelector('#smt-1000x-indicators').shadowRoot.querySelector('button').click()`);
      await until(() => fixture.sockets.size === 0, 'stream closed on collapse');
      same(await ev(portal, `document.querySelector('#smt-1000x-indicators').shadowRoot.querySelectorAll('iframe').length`), 0, 'collapsed iframe count');
      const sent = fixture.state.sent, reads = fixture.historyRequests.length; await sleep(1100); same(fixture.state.sent, sent, 'frames after collapse'); same(fixture.historyRequests.length, reads, 'history after collapse');
      const native = await ev(portal, `(()=>{document.querySelector('#native-control').click();return document.querySelector('#native-control').dataset.clicks})()`); same(native, '1', 'native fixture control');
      await ev(portal, `document.querySelector('#smt-1000x-indicators').shadowRoot.querySelector('button').click()`); panel = await findPanel(); await fresh(); same(fixture.sockets.size, 1, 'stream count after reopen'); return { native_control_clicks: native, stream_count: fixture.sockets.size };
    });
    await check('SPA market/route changes replace the old session and leave no duplicates', async () => {
      await ev(portal, `history.pushState({},'', '/1000x?market=BTC&mode=classic')`); panel = await findPanel('BTC'); await fresh();
      same(fixture.subscriptions.at(-1).priceFeedIds, [1], 'BTC public feed binding'); await until(() => fixture.sockets.size === 1, 'one BTC socket');
      same(await ev(portal, `document.querySelectorAll('#smt-1000x-indicators').length`), 1, 'host after market change');
      await ev(portal, `history.pushState({},'', '/swap')`); await until(() => ev(portal, `document.querySelectorAll('#smt-1000x-indicators').length===0`), 'route teardown'); await until(() => fixture.sockets.size === 0, 'route websocket teardown');
      await ev(portal, `history.pushState({},'', '/1000x?market=SOL&mode=classic')`); panel = await findPanel(); await fresh();
      same(await ev(portal, `document.querySelectorAll('#smt-1000x-indicators').length`), 1, 'host after return'); same(fixture.sockets.size, 1, 'socket after return'); return { selected_feed: fixture.subscriptions.at(-1).priceFeedIds, sockets: fixture.sockets.size };
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
      const before = await ev(portal, `({title:document.title,buttons:[...document.querySelectorAll('button')].map(e=>e.textContent?.trim()).filter(Boolean),nativeChart:!!document.querySelector('[aria-label="Live market price chart"]')})`);
      assert(before.nativeChart, 'actual native price canvas not found'); assert(before.buttons.length > 0, 'actual native portal controls absent');
      await ev(portal, `document.querySelector('#smt-1000x-indicators').shadowRoot.querySelector('button').click()`);
      same(await ev(portal, `document.querySelector('#smt-1000x-indicators').shadowRoot.querySelectorAll('iframe').length`), 0, 'collapsed public iframe');
      const after = await ev(portal, `({buttons:[...document.querySelectorAll('button')].map(e=>e.textContent?.trim()).filter(Boolean),nativeChart:!!document.querySelector('[aria-label="Live market price chart"]')})`);
      same(after.buttons, before.buttons, 'native control texts'); assert(after.nativeChart, 'native canvas lost'); await screenshot('04-public-portal-collapsed'); return { before, after };
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
