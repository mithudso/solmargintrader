/** Disposable browser DOM regressions. No native host, external request or owner environment. */
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { findChromeForTesting, launch } from '../lib/cdp.mjs';
import { isolateTargets } from '../lib/isolation.mjs';

const extension = process.env.CDO_FIXTURE_EXTENSION ?? fileURLToPath(new URL('../../', import.meta.url));
let isolation;
const blocked = [];
const browser = await launch({ chrome: process.env.CHROME || findChromeForTesting(), extension,
  environment: profile => ({ HOME: profile, TMPDIR: profile, PATH: '/usr/bin:/bin', LANG: 'en_US.UTF-8', TZ: 'UTC' }),
  beforeLoad: async api => { isolation = await isolateTargets(api, {
    preparePage: async session => api.call('Page.addScriptToEvaluateOnNewDocument', { source: 'window.setInterval = () => 0; window.clearInterval = () => {};' }, session),
    onEvent(message) {
      if (message.method === 'Runtime.consoleAPICalled') console.log('fixture console', ...message.params.args.map(arg => arg.value ?? arg.type));
      if (message.method !== 'Fetch.requestPaused') return;
      const { requestId, request } = message.params;
      console.log('fixture request', request.url, message.sessionId);
      const internal = ['chrome-extension:', 'data:', 'about:', 'blob:'].includes(new URL(request.url).protocol);
      if (!internal) blocked.push(request.url);
      api.call(internal ? 'Fetch.continueRequest' : 'Fetch.failRequest', internal ? { requestId } : { requestId, errorReason: 'BlockedByClient' }, message.sessionId).catch(error => console.log('fixture interception failure', error.message));
    },
  }); },
});
try {
  console.log('owned browser loaded');
  const { targetId } = await browser.call('Target.createTarget', { url: `chrome-extension://${browser.extensionId}/e2e/fixtures/cdo-ui.html` });
  const session = await browser.attach(targetId);
  await browser.waitFor(() => browser.evaluate(session, "document.readyState === 'complete'").catch(() => false));
  const html = await readFile(new URL('../../src/ui/dashboard.html', import.meta.url), 'utf8');
  await browser.evaluate(session, `window.__fixtureMarkup=${JSON.stringify(html.match(/<body[^>]*>([\s\S]*)<\/body>/i)[1])}`);
  const popup = await readFile(new URL('../../src/ui/popup.html', import.meta.url), 'utf8');
  await browser.evaluate(session, `window.__popupMarkup=${JSON.stringify(popup.match(/<body[^>]*>([\s\S]*)<\/body>/i)[1])}`);
  console.log('fixture document ready');
  const evaluated = await browser.call('Runtime.evaluate', { expression: `(${cases.toString()})()`, awaitPromise: true, returnByValue: true }, session, 90000);
  if (evaluated.exceptionDetails) throw new Error(evaluated.exceptionDetails.exception?.description ?? 'UI fixture failed');
  const result = evaluated.result.value;
  isolation.assertHealthy();
  for (const row of result) console.log(`${row.ok ? 'PASS' : 'FAIL'} ${row.name}${row.error ? ': ' + row.error : ''}`);
  console.log(JSON.stringify({ tests: result.length, failed: result.filter(r => !r.ok).length, blockedExternalRequests: blocked.length, environment: 'owned profile HOME/TMPDIR; fixed PATH/LANG/TZ only; no native manifest' }));
  process.exitCode = result.some(row => !row.ok) ? 1 : 0;
} finally { await browser.close(); }

async function cases() {
  const results = [];
  chrome.storage.local.get = async () => ({});
  chrome.storage.local.set = async () => {};
  const expect = (condition, message) => { if (!condition) throw new Error(message); };
  const flush = async () => { for (let i = 0; i < 32; i++) await Promise.resolve(); };
  const load = async name => { console.log('fixture loading', name); const value = await import(chrome.runtime.getURL(`src/ui/${name}.js`)); console.log('fixture loaded', name); return value; };
  const test = async (name, run) => {
    console.log('fixture case', name);
    document.body.innerHTML = window.__fixtureMarkup;
    chrome.runtime.sendMessage = async () => ({ ok: false, error: 'fixture unavailable' });
    try { await run(); results.push({ name, ok: true }); }
    catch (error) { results.push({ name, ok: false, error: error.message }); }
  };
  await test('CDO-146b3d564f dynamic control-room messages retain registry parity on every button', async () => {
    const { mountControlRoom } = await load('control-room');
    const { COMMANDS } = await import(chrome.runtime.getURL('src/core/commands.js'));
    const root = document.createElement('div'); document.body.append(root);
    const sent = [];
    mountControlRoom(root, { send: async message => {
      sent.push(message.type);
      expect(Object.hasOwn(COMMANDS, message.type), `Unregistered UI command ${message.type}`);
      return { ok: true, result: { helper: 'available', state: 'down', components: [], ready: false } };
    } });
    await flush();
    expect(JSON.stringify(sent) === JSON.stringify(['controlRoomStatus']), 'mount performed a start or open');
    root.querySelector('#controlRoomRefresh').click(); await flush();
    expect(JSON.stringify(sent) === JSON.stringify(['controlRoomStatus', 'controlRoomStatus']), 'refresh bypassed registry status');
    root.querySelector('#controlRoomStart').click(); await flush();
    root.querySelector('#controlRoomOpen').click(); await flush();
    expect(JSON.stringify(sent) === JSON.stringify(['controlRoomStatus', 'controlRoomStatus', 'controlRoomStart', 'controlRoomOpen']), 'dynamic UI command sequence drifted');
  });
  await test('CDO-506f442f64 initial Council status preserves typed settings', async () => {
    const { mountCouncil } = await load('council'); let release;
    const gate = new Promise(resolve => { release = resolve; });
    const c = mountCouncil({ supports: () => true, ask: async () => gate }); document.body.append(c.node);
    const read = c.refresh(); await flush();
    const field = c.node.querySelector('[name=asset]'); field.value = 'BTC'; field.dispatchEvent(new Event('input', { bubbles: true }));
    release({ ok: true, result: { config: { asset: 'SOL' } } }); await read;
    try { expect(field.value === 'BTC', 'first read overwrote the dirty draft'); } finally { c.dispose(); }
  });
  await test('CDO-bf9361f933 Council Stop is retained while status is pending', async () => {
    const { mountCouncil } = await load('council'); const calls = []; let release, held = false;
    const gate = new Promise(resolve => { release = resolve; });
    const c = mountCouncil({ supports: () => true, ask: async name => { calls.push(name); return name === 'council.status' && held ? gate : { ok: true, result: { running: name !== 'council.stop' } }; } });
    document.body.append(c.node); await c.refresh(); held = true;
    const reading = c.refresh(); await flush(); [...c.node.querySelectorAll('button')].find(b => b.textContent === 'Stop Council').click();
    release({ ok: true, result: { running: true } }); await reading; await flush();
    try { expect(calls.includes('council.stop'), 'explicit Stop was discarded'); } finally { c.dispose(); }
  });
  await test('CDO-ca22f26f00 disposed live workspace cannot dispatch workflow work', async () => {
    const { mountLiveWorkspace } = await load('live-workspace'); const calls = [];
    const read = async name => { calls.push(name); return name === 'live.rail_refresh' ? {} : new Promise(() => {}); };
    const mounted = mountLiveWorkspace(document, read); await flush(); mounted.dispose();
    document.getElementById('deskStartAll').click(); await flush();
    expect(!calls.includes('paper.workflow_ensure'), 'disposed click dispatched workflow ensure');
  });
  await test('CDO-d660eab351 saved live evidence survives warming failure', async () => {
    const { mountLivePanel } = await load('live-panel'); let rails = 0;
    const root = document.createElement('div'); document.body.append(root);
    const panel = mountLivePanel(root, { read: async name => { if (name === 'live.rail_refresh') throw new Error('synthetic warm failure'); rails++; return { stale: true, observed_at: 1, voting: {}, activity: {}, workflow: {} }; } });
    await flush();
    try { expect(rails > 0, 'saved rail was never read'); expect(/stale/i.test(root.textContent), 'saved snapshot lost its age label'); } finally { panel.dispose(); }
  });
  await test('CDO-0baa3b83ec formatted negative currency sorts numerically', async () => {
    const { sortableTable } = await load('ui-kit');
    const node = document.createElement('table'); node.innerHTML = '<thead><tr><th>Money</th></tr></thead><tbody><tr><td>−$2.00</td></tr><tr><td>−$10.00</td></tr></tbody>';
    document.body.append(node); sortableTable(node); node.querySelector('th button').click();
    expect(node.tBodies[0].rows[0].textContent === '−$10.00', 'negative money sorted as strings');
  });
  await test('CDO-e83665fec0 malformed restored desk evidence cannot crash routing', async () => {
    const { mountSignalDesk } = await load('signal-desk');
    const d = mountSignalDesk(document, { ask: async () => ({ ok: false }), openTool() {}, refreshLive() {},
      persist: { get: async () => ({ 'signalDesk.v1': { runs: [{ id: 'bad', context: { schema: 1, created_at: 1e100 }, rows: [] }], draft: { run: {}, row: {} } } }), set: async () => {} } });
    try { await d.restore; d.route('research'); } finally { d.dispose(); }
  });
  await test('CDO-37c54716c4 routing before restore never persists empty evidence', async () => {
    const { mountSignalDesk } = await load('signal-desk'); let release; const writes = [];
    const gate = new Promise(resolve => { release = resolve; });
    const saved = { id: 'saved', context: { schema: 1, id: 'saved', created_at: 1 }, rows: [], skipped: [] };
    const d = mountSignalDesk(document, { ask: async () => ({ ok: false }), openTool() {}, refreshLive() {},
      persist: { get: () => gate, set: async value => writes.push(structuredClone(value)) } });
    try {
      d.route('research'); await flush();
      const emptyWrite = writes.some(v => v['signalDesk.v1'].runs.length === 0);
      release({ 'signalDesk.v1': { runs: [saved] } }); await d.restore; await flush();
      expect(!emptyWrite, 'early route overwrote saved evidence before it was read');
      expect(writes.every(v => v['signalDesk.v1'].runs.some(r => r.id === 'saved')), 'restored run was lost');
    } finally { d.dispose(); }
  });
  await test('CDO-a7ed260776 late search retry cannot outlive desk disposal', async () => {
    const { mountSignalDesk } = await load('signal-desk'); const callbacks = [], oldTimeout = window.setTimeout, oldClear = window.clearTimeout;
    window.setTimeout = callback => { callbacks.push(callback); return callbacks.length; }; window.clearTimeout = () => {};
    const d = mountSignalDesk(document, { ask: async () => ({ ok: false }), openTool() {}, refreshLive() {}, persist: { get: async () => ({}), set: async () => {} } });
    try {
      await d.restore; document.getElementById('view-soltui').hidden = true; document.getElementById('deskFind').click();
      expect(callbacks.length === 1, 'search did not schedule its hidden-view retry');
      d.dispose(); callbacks[0](); expect(callbacks.length === 1, 'disposed search rescheduled itself');
    } finally { d.dispose(); window.setTimeout = oldTimeout; window.clearTimeout = oldClear; }
  });
  await test('CDO-a4e7093375 conflicting concurrent floating pin reports refusal', async () => {
    const { mountFloatingOwner } = await load('floating-owner'); let release;
    const gate = new Promise(resolve => { release = resolve; });
    const port = { onMessage: { addListener() {} }, onDisconnect: { addListener() {} }, postMessage() {}, disconnect() {} };
    const owner = { document: { hidden: false, addEventListener() {}, removeEventListener() {} }, setTimeout: () => 0, clearTimeout() {}, documentPictureInPicture: { requestWindow: () => gate } };
    const pip = { document: document.implementation.createHTMLDocument(), setInterval: () => 0, clearInterval() {}, addEventListener() {}, close() {}, focus() {} };
    const mounted = mountFloatingOwner({ owner, runtime: { connect: () => port, getURL: path => path }, read: () => new Promise(() => {}) });
    try {
      const first = mounted.pin('SOL'), second = mounted.pin('ADA'); release(pip);
      const result = await Promise.allSettled([first, second]);
      expect(result[0].status === 'fulfilled' && result[1].status === 'rejected', 'different coin silently joined the first pin');
    } finally { mounted.dispose(); }
  });
  const config = (await import(chrome.runtime.getURL('src/storage/store.js'))).DEFAULT_CONFIG;
  const limits = (await import(chrome.runtime.getURL('src/core/risk.js'))).DEFAULT_LIMITS;
  const status = { ok: true, config, limits, runtime: { armed: false, killSwitch: false }, lastTick: { price: 75 } };
  const journal = { ok: true, fills: [], intents: [], carry: [], events: [] };
  await test('CDO-3001958329 empty grid P&L clears every old KPI and ladder', async () => {
    const { refreshGrid } = await load('view-grid');
    const ids = ['net', 'realized', 'unrealized', 'fees', 'trips', 'winRate', 'drawdown', 'inventory', 'ladderChart'];
    ids.forEach(id => { document.getElementById(id).textContent = 'old-money'; });
    chrome.runtime.sendMessage = async m => m.type === 'status' ? status : journal;
    await refreshGrid();
    expect(ids.every(id => document.getElementById(id).textContent !== 'old-money'), 'old accounting remained beside empty journal');
  });
  await test('CDO-47c20f1e76 journal read failure remains unavailable rather than empty', async () => {
    const { refreshGrid } = await load('view-grid'); document.getElementById('events').textContent = 'known-journal';
    chrome.runtime.sendMessage = async m => m.type === 'status' ? status : { ok: false, error: 'database unavailable' };
    await refreshGrid();
    expect(document.getElementById('events').textContent === 'known-journal', 'failed read cleared previous journal');
    expect(/unavailable|failed/i.test(document.getElementById('banner').textContent), 'failure was not visible');
  });
  await test('CDO-7902529f21 refused risk save remains visible', async () => {
    const { mountGrid } = await load('view-grid'); mountGrid();
    chrome.runtime.sendMessage = async m => m.type === 'setLimits' ? { ok: false, error: 'synthetic rail refusal' } : m.type === 'status' ? status : journal;
    document.getElementById('limitsForm').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); await flush();
    expect(/refus/i.test(document.getElementById('banner').textContent), 'risk refusal disappeared');
  });
  await test('CDO-9509a56a75 unreadable grid accounting differs from zero activity', async () => {
    const { refreshPnl } = await load('view-markets');
    chrome.runtime.sendMessage = async m => m.type === 'pnl' ? { ok: false, error: 'ledger unavailable' } : { ok: true, result: { ok: true, result: { sections: [] } } };
    await refreshPnl(); expect(/grid.*unavailable|unavailable.*grid/i.test(document.getElementById('pnlSections').textContent), 'grid failure was silently omitted');
  });
  await test('CDO-4cd89bf3a8 newest P&L window owns notices and cards', async () => {
    const { refreshPnl } = await load('view-markets'); let release;
    const gate = new Promise(resolve => { release = resolve; });
    chrome.runtime.sendMessage = async m => {
      if (m.type === 'pnl') return { ok: true, result: { roundTripCount: 0 } };
      const value = m.params.window === 'old' ? await gate : { notice: 'new', sections: [] };
      return { ok: true, result: { ok: true, result: value } };
    };
    const window = document.getElementById('pnlWindow');
    window.append(new Option('old', 'old'), new Option('new', 'new')); window.value = 'old'; const old = refreshPnl();
    window.value = 'new'; await refreshPnl(); release({ notice: 'old', sections: [] }); await old;
    expect(document.getElementById('pnlNotice').textContent === 'new', 'old window replaced the selected window');
  });
  await test('CDO-1378f10a29 edited swap request cannot restore its old handoff', async () => {
    const { mountSwap } = await load('view-trade'); mountSwap({}); const form = document.getElementById('swapForm');
    form.elements.from.append(new Option('ETH', 'ETH')); form.elements.to.append(new Option('USDC', 'USDC'));
    form.elements.amount.value = '1'; form.elements.slippageBps.value = '50';
    let release; const gate = new Promise(resolve => { release = resolve; }); chrome.runtime.sendMessage = async () => gate;
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); await flush();
    form.elements.amount.value = '2'; form.elements.amount.dispatchEvent(new Event('input', { bubbles: true }));
    release({ ok: true, result: { chain: 'base', venue: 'fixture', from: { amount: 1, symbol: 'ETH' }, to: { amount: 100, symbol: 'USDC' }, route: [], caveats: [], handoffUrl: 'https://fixture.invalid/old' } }); await flush();
    expect(document.getElementById('swapQuote').hidden, 'old response restored the handoff after input changed');
  });
  const overviewState = () => ({ overview: { scan: { holdings: { totalUsd: 10, complete: false, atMs: Date.now(), chains: [{ chain: 'base', status: 'failed', errors: ['synthetic failure'], holdings: [] }] } } } });
  await test('CDO-e711f20308 failed Base read cannot certify zero idle capital', async () => {
    const { renderOverview } = await load('view-overview'); await renderOverview(overviewState(), { onAck() {} });
    expect(document.getElementById('kpiIdle').textContent === '—', 'failed Base read became known zero idle capital');
  });
  await test('CDO-8628bfad51 holdings refresh failure marks cached totals stale', async () => {
    const { renderOverview } = await load('view-overview'); await renderOverview(overviewState(), { onAck() {} });
    expect(/failed|unavailable|stale/i.test(document.getElementById('kpiTotalSub').textContent), 'fresh failure hidden behind cached read age');
  });
  await test('CDO-eca099e839 older overview cannot overwrite newest holdings', async () => {
    const { renderOverview } = await load('view-overview'); let release; const gate = new Promise(resolve => { release = resolve; }); let count = 0;
    chrome.runtime.sendMessage = async m => m.type === 'holdings' ? (++count === 1 ? gate : { ok: true, result: { totalUsd: 200, complete: true, chains: [], atMs: Date.now() } }) : { ok: false };
    const state = overviewState(), first = renderOverview(state, { onAck() {} }); await flush(); await renderOverview(state, { onAck() {} });
    release({ ok: true, result: { totalUsd: 1, complete: true, chains: [], atMs: Date.now() } }); await first;
    expect(state.holdings.totalUsd === 200 && /200/.test(document.getElementById('kpiTotal').textContent), 'old holdings replaced current result');
  });
  await test('CDO-587118619e older selected-vote request cannot replace refreshed graphics', async () => {
    const { mountVoteCharts } = await load('vote-tools'); let release; const gate = new Promise(resolve => { release = resolve; }); let calls = 0;
    const host = document.createElement('div'), controls = document.createElement('div'), reference = document.createElement('div'); document.body.append(host, controls, reference);
    const charts = mountVoteCharts({ host, controls, reference, follow: () => true, asset: () => 'SOL', read: async () => ++calls === 1 ? gate : { calls: [] } });
    const b = charts.button({ label: 'fixture' }, 'SOL'); document.body.append(b); b.click(); await flush(); charts.refresh(); await flush();
    release({ chart: { candles: [{ time: 1, open: 1, close: 1, high: 1, low: 1 }] } }); await flush(); await new Promise(resolve => setTimeout(resolve, 100));
    try { expect(!host.querySelector('canvas'), 'initial request overwrote refreshed chart graphics'); } finally { charts.dispose(); }
  });
  await test('CDO-a44214b986 selected-vote refresh refusal labels retained graphics stale', async () => {
    const { mountVoteCharts } = await load('vote-tools'); let fail = false;
    const host = document.createElement('div'), controls = document.createElement('div'), reference = document.createElement('div'); document.body.append(host, controls, reference);
    const charts = mountVoteCharts({ host, controls, reference, follow: () => true, asset: () => 'SOL', read: async () => { if (fail) throw new Error('synthetic refresh failed'); return { calls: [] }; } });
    const b = charts.button({ label: 'fixture' }, 'SOL'); document.body.append(b); b.click(); await flush(); fail = true; charts.refresh(); await flush();
    try { expect(/stale|failed/i.test(controls.textContent), 'refresh failure silently retained apparently fresh chart'); } finally { charts.dispose(); }
  });
  const mountedPanel = async (commands, read) => {
    const { mountSoltuiPanel } = await load('soltui-panel');
    const transport = async message => {
      if (message.type === 'soltuiSession') return { ok: true, result: { available: true, connected: true, generation: 1 } };
      if (message.type === 'soltuiCommands') return { ok: true, result: { ok: true, result: commands } };
      return { ok: true, result: await read(message.command, message.params) };
    };
    await mountSoltuiPanel(document, transport); return transport;
  };
  const command = (name, params = []) => ({ name, params, describe: 'Fixture only', read_only: true, requires_confirm: false, long_running: false });
  await test('CDO-3f0718ee37 automatic activation preserves explicit clear selections', async () => {
    const calls = [];
    await mountedPanel([command('demo.echo', [{name:'text', type:'string', required:false}]), command('docs.list')], async (name, params) => { calls.push({name, params}); return {ok:true, command:name, result:{}}; });
    const select = document.getElementById('soltuiCommand'), workspace = document.getElementById('soltuiWorkspace');
    select.value = 'demo.echo'; select.dispatchEvent(new Event('change'));
    document.querySelector('#soltuiForm [aria-label="Clear text"]').checked = true;
    select.value = 'docs.list'; select.dispatchEvent(new Event('change')); workspace.value = 'all'; workspace.dispatchEvent(new Event('change'));
    document.querySelector('#soltuiTools [data-command="demo.echo"]').click(); await flush();
    try { expect(calls.some(c => c.name === 'demo.echo' && Object.hasOwn(c.params, 'text') && c.params.text === ''), 'automatic activation omitted the retained explicit clear'); }
    finally { window.dispatchEvent(new Event('pagehide')); }
  });
  await test('CDO-9f21d3287d reopening the current document cannot enable a second save', async () => {
    let release, writes = 0; const gate = new Promise(resolve => { release = resolve; });
    await mountedPanel([command('docs.read', [{name:'path', type:'string', required:true}])], async (name, params) => {
      if (name === 'docs.write') { writes++; return gate; }
      return {ok:true, command:name, result:{path:params.path, text:'base', revision:'a'.repeat(64), editable:true}};
    });
    const form = document.getElementById('soltuiForm'); form.querySelector('[name=path]').value = 'fixture.md';
    form.dispatchEvent(new Event('submit', {cancelable:true})); await flush();
    document.getElementById('soltuiSave').click(); await flush(); expect(writes === 1, 'save did not reach inert write barrier');
    form.dispatchEvent(new Event('submit', {cancelable:true})); await flush();
    try { expect(document.getElementById('soltuiSave').disabled, 'reopening re-enabled Save during the first write'); }
    finally { release({ok:true,result:{revision:'b'.repeat(64)}}); await flush(); window.dispatchEvent(new Event('pagehide')); }
  });
  let popupCase = 0;
  const mountPopup = async send => {
    document.body.innerHTML = window.__popupMarkup; chrome.runtime.sendMessage = send;
    await import(chrome.runtime.getURL(`src/ui/popup.js?fixture=${++popupCase}`)); await flush();
  };
  const popupReply = message => message.type === 'status' ? status : message.type === 'overview' ? {ok:true, scan:{scannedAtMs:Date.now(), alerts:[]}} : {ok:false,error:'fixture unavailable'};
  await test('CDO-0de28cd30a popup action refusal survives status refresh', async () => {
    await mountPopup(async message => message.type === 'tickNow' ? {ok:false,error:'synthetic tick refusal'} : popupReply(message));
    document.getElementById('tickNow').click(); await flush();
    try { expect(!document.getElementById('err').classList.contains('hidden') && /refus/i.test(document.getElementById('err').textContent), 'status refresh erased action refusal'); }
    finally { window.dispatchEvent(new Event('pagehide')); }
  });
  await test('CDO-8548cf1ff4 rejected popup scan settles visibly without an unhandled rejection', async () => {
    await mountPopup(async message => { if (message.type === 'scanAlerts') throw new Error('synthetic transport'); return popupReply(message); });
    const errors = []; const onError = event => { errors.push(event.reason); event.preventDefault(); }; window.addEventListener('unhandledrejection', onError);
    document.getElementById('scanNow').click(); await flush(); await new Promise(resolve => setTimeout(resolve, 10));
    try { expect(/failed|unavailable/i.test(document.getElementById('scanAge').textContent), 'scan stayed permanently scanning'); expect(!errors.length, 'rejected scan escaped its UI handler'); }
    finally { window.removeEventListener('unhandledrejection', onError); window.dispatchEvent(new Event('pagehide')); }
  });
  await test('CDO-7bf5d8a764 unavailable popup glance clears old agreement and process state', async () => {
    document.body.innerHTML = window.__popupMarkup;
    document.getElementById('glanceScore').textContent = '90% UP'; document.getElementById('glanceScore').className = 'signal-score-green'; document.getElementById('glanceProcesses').textContent = 'running';
    chrome.runtime.sendMessage = async message => popupReply(message);
    await import(chrome.runtime.getURL(`src/ui/popup.js?fixture=${++popupCase}`)); await flush();
    try { expect(!/green/.test(document.getElementById('glanceScore').className), 'old green agreement remained current'); expect(!/^running$/.test(document.getElementById('glanceProcesses').textContent), 'old process status remained current'); }
    finally { window.dispatchEvent(new Event('pagehide')); }
  });
  return results;
}
