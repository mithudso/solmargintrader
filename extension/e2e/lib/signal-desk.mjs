/** Independent Signal Desk acceptance in an actual MV3 page, with native writes isolated in memory. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const EXT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

export function saveScreenshot(data, scheme) {
  if (!['light', 'dark'].includes(scheme)) throw new Error('Unknown screenshot scheme');
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'signal-desk-acceptance-'));
  const file = path.join(directory, `${scheme}.png`);
  fs.writeFileSync(file, Buffer.from(data, 'base64'), { flag: 'wx', mode: 0o600 });
  return file;
}

// This bootstrap runs only in the separate acceptance target, before production modules.
// No synthetic payload or replacement transport is shipped into the production UI.
function fixtureBoot() {
  const originalSend = chrome.runtime.sendMessage.bind(chrome.runtime);
  const execution = { fee_schedule: 'jupiter-perps', fee_bps: 6, slippage_bps: 2,
    use_leverage: false, leverage: 3, allow_short: false, min_confidence: .8,
    borrow_long_bps_hour: .8, borrow_short_bps_hour: .15 };
  const context = (id, different = false) => ({ schema: 1, id, run_id: id, created_at: 1762550000,
    asset: 'SOL', interval: '1h', start: '2025-01-01', end: '2025-02-01', capital: 1000,
    fill_delay: 1, data_sha256: different ? 'other-dataset' : 'array-data-sha', strategy_revision: 'fixture-code',
    cpcv: { cpcv_groups: 8, cpcv_k: 2 }, execution, entries: [{ label: 'trend-precise', name: 'ma_crossover', params: { fast: 3, slow: 9 } }] });
  const run = (id, different = false) => ({ id, context: context(id, different), cancelled: false,
    skipped: [], message: 'Recorded fixture sweep', rows: [{ label: 'trend-precise', family: 'trend', median_sharpe: -.25,
      iqr: .5, frac_positive: .3, median_return: -.02, trades: 42, evaluable: true }] });
  const readonly = (name, params = []) => ({ name, describe: name, params, read_only: true, long_running: false, requires_confirm: false });
  const param = (name, type = 'string') => ({ name, type, describe: name, required: false });
  const commands = [
    ...['settings.get', 'roster.list', 'backtest.status', 'backtest.results', 'cumulative.summary', 'prices.status', 'forwardtest.state',
      'bots.overview', 'compound.autopilot_status', 'bots.schedule_status', 'docs.list', 'liquidity.status'].map((n) => readonly(n)),
    readonly('forwardtest.status', [param('coins', 'json')]),
    readonly('forwardtest.predictions', [param('asset')]),
    readonly('compound.unattended_status', [param('asset')]),
    { name: 'backtest.run', describe: 'Run historical sweep', params: [param('labels', 'json')], read_only: false, long_running: true },
    { name: 'forwardtest.start', describe: 'Prepare only', params: [param('snapshot', 'json'), param('source_label'), param('horizons', 'json'), param('optimize', 'bool'), param('coins', 'json')], read_only: false },
    ...['forwardtest.run', 'forwardtest.stop', 'forwardtest.restore', 'liquidity.resume', 'docs.search'].map((name) => ({ name, describe: name, params: [], read_only: false })),
  ];
  const state = window.__deskFixture = { calls: [], writes: [], commands, execution, currentRun: run('run-one'), failReads: [],
    storage: { 'signalDesk.v1': { runs: [run('run-one'), run('run-two'), run('run-other', true)], selected: [], draft: null, asset: 'SOL', page: 'signal', density: 'comfortable' } },
    prediction: 'UP', expired: false, prepared: false, streamFresh: true };
  // Legacy browser snapshots can omit fields added after their creation.
  delete state.storage['signalDesk.v1'].runs[1].skipped;
  const envelope = (command, result) => ({ ok: true, command, result, error: null });
  chrome.storage.local.get = async (key) => typeof key === 'string' ? { [key]: structuredClone(state.storage[key]) } : structuredClone(state.storage);
  chrome.storage.local.set = async (value) => Object.assign(state.storage, structuredClone(value));
  chrome.runtime.sendMessage = async (message) => {
    state.calls.push(structuredClone(message));
    if (message.type === 'soltuiSession') return { ok: true, result: { available: true, connected: true, generation: 1 } };
    if (message.type === 'soltuiCommands') return { ok: true, result: envelope('list', state.commands) };
    if (message.type !== 'soltuiCall') {
      if (['status', 'getConfig', 'getLimits', 'levels', 'capital', 'data', 'venueInfo', 'overview', 'getPrefs'].includes(message.type)) return originalSend(message);
      throw new Error('Acceptance fixture refuses extension mutation: ' + message.type);
    }
    const name = message.command, p = message.params ?? {};
    if (state.failReads.includes(name)) throw new Error('Fixture disconnected: ' + name);
    const now = Date.now() / 1000;
    const values = {
      'settings.get': { settings: { asset: 'SOL', interval: '1h', start: '2025-01-01', end: '2025-02-01', capital: 1000, ...execution } },
      'roster.list': { entries: state.currentRun.context.entries },
      'backtest.status': { running: false, phase: 'done', done: 1, total: 1, title: 'Historical fixture completed' },
      'backtest.results': { ...state.currentRun, execution },
      'cumulative.summary': { headline: 'Recorded fixture research summaries',
        totals: { files: 1, rows: 10, rankable: 7, below_floor: 3, positive: 4, made_money: 4 },
        files: [{ source: 'fixture-legacy-results.csv', rankable: 7, below_floor: 3, positive: 4, made_money: 4,
          median_sharpe: .42, path_range: '8–28', best: { label: 'legacy-trend', median_sharpe: .8, net_pct: .02 } }], casualties: [] },
      'prices.status': { running: true, live: state.streamFresh, snapshot_age_s: state.streamFresh ? 2 : 900,
        prices: { 'SOL-USD': { mid: 142.86, bid: 142.85, ask: 142.87, spread_bps: 1.4,
          quote_ts: now - (state.streamFresh ? 2 : 900), quote_age_s: state.streamFresh ? 2 : 900 } } },
      'forwardtest.predictions': { asset: p.asset ?? 'SOL', voting: { min_accuracy: 60, min_resolved: 20 },
        rows: [{ label: 'current-strategy', accuracy: 80, resolved: 50, pred_5m: state.prediction,
          acc_5m: 80, resolved_5m: 50, issued_5m: now - 60, expires_5m: state.expired ? now - 1 : now + 240 }] },
      'forwardtest.state': { running: false, prepared: state.prepared, busy: false, assets: ['SOL'], optimize: false, execution },
      'forwardtest.status': { asset: p.coins?.[0] ?? 'SOL', rows: [{ id: 'trial-one', label: 'trend-precise', minutes: 5, correct: 137,
        resolved: 216, pending: 1, net_pct: -.006, execution, last_issued: now - 60 }] },
      'bots.overview': { bots: [{ bot: 'grid', label: 'Ladder grid', about: 'Paper simulation', optimize: 'No adoption' }] },
      'compound.unattended_status': { running: true, last_line: 'Model output 18m old', asset: p.asset ?? 'SOL' },
      'compound.autopilot_status': { autopilot: false, running: [] },
      'bots.schedule_status': { enabled: false, running: false },
      'docs.list': { rows: [] }, 'liquidity.status': { archived: true },
    };
    if (Object.hasOwn(values, name)) return { ok: true, result: envelope(name, values[name]) };
    const command = state.commands.find((c) => c.name === name);
    if (!command) return { ok: true, result: { ok: false, command: name, error: { code: 'unknown_command', message: 'Unknown fixture command' } } };
    state.writes.push(structuredClone(message));
    if (name === 'forwardtest.start') { state.prepared = true; return { ok: true, result: envelope(name, { asset: 'SOL', trials: 1, execution, source: { backtest_context: p.snapshot.id }, message: 'Prepared only' }) }; }
    if (name === 'backtest.run') return { ok: true, result: envelope(name, { ...state.currentRun, execution }) };
    throw new Error('Unexpected fixture write: ' + name);
  };
}

export async function verifySignalDesk(_page, browser) {
  const { targetId } = await browser.call('Target.createTarget', { url: 'about:blank' });
  const sessionId = await browser.attach(targetId);
  const ev = (expression) => browser.evaluate(sessionId, expression);
  const loadedScripts = new Map(), loadedStyles = new Map(), pageRequests = [];
  const off = browser.on((m) => {
    if (m.sessionId !== sessionId) return;
    if (m.method === 'Debugger.scriptParsed' && m.params.url) loadedScripts.set(m.params.url, m.params.scriptId);
    if (m.method === 'CSS.styleSheetAdded') loadedStyles.set(m.params.header.sourceURL, m.params.header.styleSheetId);
    if (m.method === 'Network.requestWillBeSent') pageRequests.push(m.params.request.url);
  });
  const wait = async (expression, message = expression) => {
    const value = await browser.waitFor(() => ev(expression).catch(() => false), 15000);
    assert.ok(value, message); return value;
  };
  const click = (label, scope = 'document') => ev(`(()=>{const button=[...${scope}.querySelectorAll('button')].find(x=>x.textContent.trim()===${JSON.stringify(label)});if(!button)throw new Error('Button missing: '+${JSON.stringify(label)});button.focus();button.click()})()`);
  const route = async (id, title) => {
    await ev(`location.hash=${JSON.stringify('soltui/' + id)}`);
    await wait(`document.querySelector('#deskTitle').textContent===${JSON.stringify(title)}`);
    if (id !== 'signal') await wait(`document.querySelector('#deskReadStatus').textContent.startsWith('Read ')`);
  };
  try {
    await browser.call('Runtime.enable', {}, sessionId);
    await browser.call('Page.enable', {}, sessionId);
    await browser.call('Debugger.enable', {}, sessionId);
    await browser.call('DOM.enable', {}, sessionId);
    await browser.call('CSS.enable', {}, sessionId);
    await browser.call('Network.enable', {}, sessionId);
    await browser.call('Page.addScriptToEvaluateOnNewDocument', { source: `(${fixtureBoot.toString()})()` }, sessionId);
    await browser.call('Page.navigate', { url: `chrome-extension://${browser.extensionId}/src/ui/dashboard.html#soltui/signal` }, sessionId);
    await browser.call('Page.bringToFront', {}, sessionId);
    await wait(`document.querySelector('#soltuiStatus')?.textContent.includes('tools connected')`);
    await wait(`document.querySelector('#deskInterpretation').textContent.includes('Strong Buy')`);
    const identity = await ev(`(async()=>{const names=['src/ui/signal-desk.js','src/ui/desk-model.js','src/ui/signal-desk.css'];const result={version:chrome.runtime.getManifest().version,url:location.href};for(const name of names){const bytes=await(await fetch(chrome.runtime.getURL(name))).arrayBuffer();result[name]=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('')}return result})()`);
    for (const name of ['src/ui/signal-desk.js', 'src/ui/desk-model.js', 'src/ui/signal-desk.css']) {
      const expected = crypto.createHash('sha256').update(fs.readFileSync(path.join(EXT, name))).digest('hex');
      assert.equal(identity[name], expected, `loaded resource identity ${name}`);
      const url = `chrome-extension://${browser.extensionId}/${name}`;
      if (name.endsWith('.js')) {
        assert.ok(loadedScripts.has(url), `executed module was parsed: ${name}`);
        const { scriptSource } = await browser.call('Debugger.getScriptSource', { scriptId: loadedScripts.get(url) }, sessionId);
        assert.equal(crypto.createHash('sha256').update(scriptSource).digest('hex'), expected, `executed module source ${name}`);
      } else {
        assert.ok(loadedStyles.has(url), `applied stylesheet was loaded: ${name}`);
        const { text } = await browser.call('CSS.getStyleSheetText', { styleSheetId: loadedStyles.get(url) }, sessionId);
        assert.equal(crypto.createHash('sha256').update(text).digest('hex'), expected, `applied stylesheet source ${name}`);
      }
    }
    console.log('PASS Signal Desk actual extension resource hashes match reviewed source ' + JSON.stringify(identity));
    assert.equal(await ev(`__deskFixture.writes.length`), 0, 'opening Signal Desk starts no mutation');
    const nav = await ev(`[...document.querySelectorAll('.primary-nav')].map(x=>{const copy=x.cloneNode(true);copy.querySelectorAll('[aria-hidden=true]').forEach(n=>n.remove());return {label:copy.textContent.trim(),href:x.getAttribute('href')}})`);
    assert.deepEqual(nav.map((x) => x.label), ['Live signals', 'Backtesting', 'Forward testing', 'Bot monitor'], 'four primary accessible navigation labels');
    await browser.call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false }, sessionId);
    for (const [id, title] of [['signal', 'Live signals'], ['research', 'Backtesting'], ['forward', 'Forward testing'], ['bots', 'Bot monitor']]) {
      await route(id, title);
      assert.ok(await ev(`document.documentElement.scrollWidth<=innerWidth`), `desktop overflow ${id}`);
    }
    console.log('PASS four primary workspace routes and desktop containment');

    await route('research', 'Backtesting');
    assert.ok(await ev(`document.querySelector('#deskContent').textContent.includes('-2%')`), 'backtest fractions render as percentages');
    assert.ok(await ev(`document.querySelector('#deskContent').textContent.includes('Aggregate trades')`));
    assert.ok(await ev(`document.querySelector('#deskContent').textContent.includes('Drawdown, equity and itemized costs are unavailable')`));
    const archive = await ev(`(()=>{const card=[...document.querySelectorAll('#deskContent .card')].find(x=>x.querySelector('h2')?.textContent==='Existing research archives');return card?{text:card.textContent,cells:[...card.querySelectorAll('tbody tr:first-child td')].map(x=>x.textContent),comparisons:card.querySelectorAll('input[type=checkbox]').length,staging:[...card.querySelectorAll('button')].filter(x=>x.textContent==='Stage paper trial').length}:null})()`);
    assert.ok(archive, 'existing repository research archives are directly visible');
    assert.deepEqual(archive.cells, ['fixture-legacy-results.csv', '7', '3', '0.42', 'Inspect archive summary']);
    assert.match(archive.text, /Archives retain their original assumptions/);
    assert.equal(archive.comparisons, 0, 'archive summaries cannot join current-context comparisons');
    assert.equal(archive.staging, 0, 'archive summaries cannot stage an unpinned paper setup');
    assert.equal(await ev(`document.querySelectorAll('#deskContent input[aria-label^="Compare run "]').length`), 3, 'archive is not imported as an additional versioned run');
    await click('Inspect archive summary');
    await wait(`document.querySelector('#deskDetail').open`);
    assert.match(await ev(`document.querySelector('#deskDetail').textContent`), /Original research summary · not a current-engine rerun/);
    assert.match(await ev(`document.querySelector('#deskDetailBody').textContent`), /fixture-legacy-results\.csv/);
    await click('Close', 'document.querySelector("#deskDetail")');
    console.log('PASS existing research archive metrics and provenance remain visible apart from pinned runs');
    await ev(`(()=>{for(const id of ['run-one','run-two']){const x=document.querySelector('[aria-label="Compare run '+id+'"]');x.checked=true;x.dispatchEvent(new Event('change'))}})()`);
    await click('Compare selected runs');
    await wait(`document.querySelector('#deskDetail').open`);
    assert.match(await ev(`document.querySelector('#deskDetailBody').textContent`), /Matched dataset/);
    await click('Close', 'document.querySelector("#deskDetail")');
    await ev(`(()=>{const x=document.querySelector('[aria-label="Compare run run-other"]');x.checked=true;x.dispatchEvent(new Event('change'))})()`);
    await click('Compare selected runs');
    assert.match(await ev(`document.querySelector('#deskDetailBody').textContent`), /Incompatible evidence/);
    await click('Close', 'document.querySelector("#deskDetail")');
    assert.equal(await ev(`__deskFixture.writes.length`), 0, 'comparison is local');
    console.log('PASS compatible and incompatible saved evidence comparisons retain metric units');

    await click('Stage paper trial');
    await wait(`document.querySelector('#deskTitle').textContent==='Forward testing'`);
    assert.equal(await ev(`__deskFixture.writes.length`), 0, 'staging does not prepare or start');
    assert.ok(await ev(`document.querySelector('#deskDraft').textContent.includes('Nothing has started')`));
    await click('Review pinned paper setup');
    assert.equal(await ev(`document.querySelector('#soltuiCommand').value`), 'forwardtest.start');
    const staged = await ev(`({snapshot:JSON.parse(document.querySelector('[name=snapshot]').value),label:document.querySelector('[name=source_label]').value,horizons:JSON.parse(document.querySelector('[name=horizons]').value),optimize:document.querySelector('[name=optimize]').value})`);
    assert.equal(staged.snapshot.id, 'run-one');
    assert.equal(staged.snapshot.execution.fee_bps, 6);
    assert.equal(staged.snapshot.entries[0].params.fast, 3);
    assert.equal(staged.label, 'trend-precise');
    assert.deepEqual(staged.horizons, [5]); assert.equal(staged.optimize, 'false');
    await ev(`document.querySelector('#soltuiForm').requestSubmit()`);
    await wait(`__deskFixture.writes.some(x=>x.command==='forwardtest.start')`);
    assert.equal(await ev(`__deskFixture.writes.filter(x=>x.command==='forwardtest.run').length`), 0, 'preparing does not start checking');
    assert.deepEqual(await ev(`Object.keys(__deskFixture.writes.find(x=>x.command==='forwardtest.start').params).sort()`), ['horizons','optimize','snapshot','source_label']);
    await wait(`document.querySelector('#deskDetail').open`);
    await click('Close', 'document.querySelector("#deskDetail")');
    console.log('PASS exact data/strategy/cost snapshot stages and prepares without starting a worker');

    await route('forward', 'Forward testing');
    await wait(`document.querySelector('#deskContent').textContent.includes('137/216')`);
    assert.match(await ev(`document.querySelector('#deskContent').textContent`), /63\.43% \(137\/216\)/);
    assert.ok(await ev(`document.querySelector('#deskContent').textContent.includes('-0.6%')`));
    await route('bots', 'Bot monitor');
    assert.ok(await ev(`document.querySelector('#deskContent').textContent.includes('Native-session owned')`));
    assert.ok(await ev(`document.querySelector('#deskContent').textContent.includes('Detached; survives browser closure')`));
    assert.ok(await ev(`document.querySelector('#deskContent').textContent.includes('Model output 18m old')`));
    console.log('PASS forward accuracy, pending count, net units and process-lifetime distinctions');
    await browser.call('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: false }, sessionId);
    const tableScroll = await ev(`(()=>{const card=[...document.querySelectorAll('#deskContent .card')].find(x=>x.querySelector('h2')?.textContent==='Process responsibilities');const wrap=card.querySelector('.table-wrap');const hint=card.textContent.includes('Scroll horizontally to see all table columns and actions.');const before={width:wrap.clientWidth,content:wrap.scrollWidth,offset:wrap.scrollLeft};wrap.scrollLeft=wrap.scrollWidth;const last=wrap.querySelector('tbody tr button').getBoundingClientRect();const bounds=wrap.getBoundingClientRect();return {hint,before,offset:wrap.scrollLeft,buttonVisible:last.right<=bounds.right&&last.left>=bounds.left}})()`);
    assert.ok(tableScroll.hint, 'narrow process table explains the hidden controls');
    assert.ok(tableScroll.before.content > tableScroll.before.width && tableScroll.offset > 0, 'narrow process table scrolls horizontally');
    assert.ok(tableScroll.buttonVisible, 'scrolling reveals the Inspect action');
    await browser.call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false }, sessionId);
    console.log('PASS narrow process table scroll cue and Inspect action');


    await route('signal', 'Live signals');
    const priorTickAt = await ev(`Number(document.querySelector('#soltuiLiveChart [data-tick-time]:last-child').getAttribute('data-tick-time'))`);
    await wait(`Date.now()-2000>${priorTickAt + 1}`, 'fixture source time advances before observing unavailable agreement');
    await ev(`__deskFixture.expired=true;document.querySelector('#soltuiLiveRefresh').click()`);
    await wait(`document.querySelector('#deskInterpretation').textContent==='Agreement unavailable'`);
    assert.ok(await ev(`!document.querySelector('#deskLiveMetrics').textContent.includes('Strong Buy')`));
    assert.ok(await ev(`document.querySelector('#deskInterpretation').classList.contains('signal-score-gray')`));
    await wait(`(()=>{const tick=document.querySelector('#soltuiLiveChart [data-tick-time]:last-child');return Number(tick?.getAttribute('data-tick-time'))>${priorTickAt}&&tick.getAttribute('data-score')===''})()`, 'new source tick records an unavailable score');
    const unavailableTickTitle = await ev(`document.querySelector('#soltuiLiveChart [data-tick-time]:last-child title').textContent`);
    assert.match(unavailableTickTitle, / · Unavailable$/, 'missing-score tick tooltip names its unavailable rating');
    assert.doesNotMatch(unavailableTickTitle, /\bFlat\b/, 'missing-score tick must not imply a flat market reading');
    await ev(`__deskFixture.expired=false;document.querySelector('#soltuiLiveRefresh').click()`);
    await wait(`document.querySelector('#deskInterpretation').textContent.includes('Strong Buy')`);
    console.log('PASS expired evidence and its new chart tooltip stay unavailable; fresh recovery restores agreement');

    await ev(`(()=>{const f=document.querySelector('#soltuiLivePredictions [aria-label="Filter strategy evidence"]');f.value='no-match-exact';f.dispatchEvent(new Event('input'));f.focus();window.__oldFilter=f;document.querySelector('#soltuiLiveRefresh').click()})()`);
    await wait(`document.querySelector('#soltuiLivePredictions [aria-label="Filter strategy evidence"]')!==__oldFilter`);
    const filterState = await ev(`({value:document.querySelector('#soltuiLivePredictions input').value,focused:document.activeElement===document.querySelector('#soltuiLivePredictions input'),empty:document.querySelector('#soltuiLivePredictions').textContent.includes('No matching strategies')})`);
    assert.deepEqual(filterState, { value: 'no-match-exact', focused: true, empty: true }, `filter refresh state ${JSON.stringify(filterState)}`);
    await click('Clear filter', 'document.querySelector("#soltuiLivePredictions")');
    assert.equal(await ev(`document.querySelectorAll('#soltuiLivePredictions tbody tr').length`), 1);
    await route('forward', 'Forward testing');
    await ev(`__deskFixture.failReads=['forwardtest.status'];document.querySelector('#deskReadRefresh').click()`);
    await wait(`document.querySelector('#deskContent').textContent.includes('Fixture disconnected')`);
    const failedCount = await ev(`(()=>{const k=[...document.querySelectorAll('#deskContent .kpi')].find(x=>x.querySelector('.label').textContent==='Saved trial rows');return k.querySelector('.value').textContent})()`);
    assert.equal(failedCount, 'Unavailable', 'disconnection must not become an invented zero count');
    await ev(`__deskFixture.failReads=[];document.querySelector('#deskReadRefresh').click()`);
    await wait(`document.querySelector('#deskContent').textContent.includes('137/216')`);
    await route('signal', 'Live signals');
    console.log('PASS live filter focus/query survive refresh, empty-state clear recovers, and disconnected evidence stays unavailable until a read recovers');

    const writesBeforeSearch = await ev(`__deskFixture.writes.length`);
    await ev(`document.querySelector('#deskFind').focus();document.querySelector('#deskFind').click();document.querySelector('#deskSearchInput').value='backtest';document.querySelector('#deskSearchInput').dispatchEvent(new Event('input'))`);
    assert.ok(await ev(`document.querySelector('#deskSearchResults').textContent.includes('backtest.run')`));
    assert.equal(await ev(`__deskFixture.writes.length`), writesBeforeSearch);
    assert.equal(await ev(`document.querySelector('#deskSearchDialog').getAttribute('aria-labelledby')`), 'deskSearchTitle');
    await ev(`window.__escapeTrace=[];document.addEventListener('keydown',e=>__escapeTrace.push({key:e.key,code:e.code,prevented:e.defaultPrevented,trusted:e.isTrusted}))`);
    await browser.call('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 }, sessionId);
    await browser.call('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 }, sessionId);
    try { await wait(`!document.querySelector('#deskSearchDialog').open&&document.activeElement.id==='deskFind'`); }
    catch { throw new Error('Search Escape/focus state: '+JSON.stringify(await ev(`({open:document.querySelector('#deskSearchDialog').open,active:document.activeElement.id,focus:document.hasFocus(),trace:__escapeTrace,dialogs:[...document.querySelectorAll('dialog[open]')].map(x=>({id:x.id,closedBy:x.closedBy}))})`))); }
    await ev(`location.hash='soltui/all'`);
    await wait(`document.querySelector('#soltuiWorkspace').value==='all'`);
    const archived = await ev(`(()=>{const b=document.querySelector('#soltuiTools [data-command="liquidity.resume"]');return {exists:!!b,disabled:b?.disabled}})()`);
    assert.deepEqual(archived, { exists: true, disabled: true });
    await ev(`(()=>{const s=document.querySelector('#soltuiCommand');s.value='liquidity.resume';s.dispatchEvent(new Event('change'));document.querySelector('#soltuiForm').requestSubmit()})()`);
    assert.equal(await ev(`__deskFixture.writes.filter(x=>x.command==='liquidity.resume').length`), 0);
    console.log('PASS local search, named dialog Escape/focus, and archived mutators blocked even through expert form');

    await route('research', 'Backtesting');
    await click('Costs & provenance');
    await wait(`document.querySelector('#deskDetail').open`);
    assert.equal(await ev(`document.querySelector('#deskDetail').getAttribute('aria-labelledby')`), 'deskDetailTitle');
    await browser.call('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 }, sessionId);
    await browser.call('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 }, sessionId);
    await wait(`!document.querySelector('#deskDetail').open`);
    assert.ok(await ev(`document.activeElement.textContent==='Costs & provenance'||document.activeElement.id==='deskTitle'`), 'evidence dismissal restores a connected focus target');
    await ev(`location.hash='settings'`);
    await wait(`document.querySelector('#view-soltui').hidden`);
    await ev(`document.querySelector('#deskFind').focus();document.querySelector('#deskFind').click()`);
    await wait(`document.querySelector('#deskSearchDialog').open&&!document.querySelector('#view-soltui').hidden`);
    await ev(`document.querySelector('#deskSearchInput').value='backtest.run';document.querySelector('#deskSearchInput').dispatchEvent(new Event('input'));[...document.querySelectorAll('#deskSearchResults button')].find(x=>x.textContent==='backtest.run').click()`);
    await wait(`!document.querySelector('#deskSearchDialog').open&&document.querySelector('#soltuiCommand').value==='backtest.run'&&document.querySelector('#soltuiToolbox').open`);
    assert.equal(await ev(`__deskFixture.writes.filter(x=>x.command==='backtest.run').length`), 1, 'search action runs the selected default backtest directly');
    console.log('PASS evidence dialog Escape and global search recovery from a legacy settings view');

    for (const width of [390, 720]) {
      await browser.call('Emulation.setDeviceMetricsOverride', { width, height: 844, deviceScaleFactor: width === 720 ? 2 : 1, mobile: false }, sessionId);
      for (const [id, title] of [['signal', 'Live signals'], ['research', 'Backtesting'], ['forward', 'Forward testing'], ['bots', 'Bot monitor']]) {
        await route(id, title);
        assert.ok(await ev(`document.documentElement.scrollWidth<=innerWidth`), `narrow/zoom-equivalent overflow ${width} ${id}`);
      }
      assert.ok(await ev(`[...document.querySelectorAll('.sidebar a')].some(x=>x.textContent.trim()==='Settings'&&x.getBoundingClientRect().width>0)`));
    }
    console.log('PASS 390px and 200%-equivalent 720px CSS viewport containment with all primary routes and Settings');

    await browser.call('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: false }, sessionId);
    for (const [id, title, heading, actionLabel] of [
      ['signal', 'Live signals', null, 'Inspect'],
      ['research', 'Backtesting', 'Historical evidence', 'Stage paper trial'],
      ['research', 'Backtesting', 'Existing research archives', 'Inspect archive summary'],
      ['forward', 'Forward testing', 'SOL prospective evidence', 'Inspect trial'],
      ['bots', 'Bot monitor', 'Process responsibilities', 'Inspect'],
      ['bots', 'Bot monitor', 'Paper bot research', 'Inspect bot'],
    ]) {
      await route(id, title);
      const result = await ev(`(()=>{const heading=${JSON.stringify(heading)};const root=heading?[...document.querySelectorAll('#deskContent .card')].find(x=>x.querySelector('h2')?.textContent===heading):document.querySelector('#soltuiLivePredictions');const wrap=root?.querySelector('.table-wrap');const hint=root?.querySelector('.table-scroll-hint');const button=[...(wrap?.querySelectorAll('button')||[])].find(x=>x.textContent.trim()===${JSON.stringify(actionLabel)});if(!wrap||!button)return {missing:true};const before={client:wrap.clientWidth,scroll:wrap.scrollWidth};wrap.scrollLeft=wrap.scrollWidth;const b=button.getBoundingClientRect(),w=wrap.getBoundingClientRect();const context=root.querySelector('.desk-run .card-head label');const cr=context?.getBoundingClientRect(),cost=root.querySelector('.desk-run > .note')?.getBoundingClientRect(),rr=root.getBoundingClientRect();return {hint:hint?.textContent||'',before,offset:wrap.scrollLeft,visible:b.left>=w.left&&b.right<=w.right,contextVisible:!cr||(cr.left>=rr.left&&cr.right<=rr.right&&cost&&cost.left>=rr.left&&cost.right<=rr.right)}})()`);
      assert.match(result.hint ?? '', /Scroll horizontally to see all table columns and actions/ , `${id}: ${heading ?? 'strategy evidence'} scroll cue`);
      assert.ok(result.before.scroll > result.before.client && result.offset > 0, `${id}: ${heading ?? 'strategy evidence'} overflows and scrolls`);
      assert.ok(result.visible, `${id}: ${actionLabel} is visible after scrolling`);
      if (heading === 'Historical evidence') assert.ok(result.contextVisible, 'run identity stays visible while scrolling the results table');
    }
    console.log('PASS all six narrow evidence tables expose scroll cues and actions');

    await browser.call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false }, sessionId);
    await route('signal', 'Live signals');
    const shots = {};
    for (const scheme of ['light', 'dark']) {
      await browser.call('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: scheme }] }, sessionId);
      const contrast = await ev(`(()=>{const linear=v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4};const rgb=s=>(s.match(/[\\d.]+/g)||[]).slice(0,3).map(Number);const lum=s=>{const c=rgb(s).map(linear);return .2126*c[0]+.7152*c[1]+.0722*c[2]};const out=[];for(const selector of ['body','.view-head p','.kpi .sub','.kpi .label','.sidebar .nav-link','.primary-nav[aria-current=page]','.desk-interpretation .eyebrow']){const el=document.querySelector(selector);const style=getComputedStyle(el);let bg=style.backgroundColor,node=el;while(bg==='rgba(0, 0, 0, 0)'&&node.parentElement){node=node.parentElement;bg=getComputedStyle(node).backgroundColor}const a=lum(style.color),b=lum(bg);out.push({selector,foreground:style.color,background:bg,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)})}return out})()`);
      for (const item of contrast) assert.ok(item.ratio >= 4.5, `${scheme} text contrast ${item.selector}: ${item.ratio}`);
      const { data } = await browser.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false }, sessionId);
      shots[scheme] = saveScreenshot(data, scheme);
      console.log(`PASS ${scheme} sampled text contrast >=4.5:1 ${JSON.stringify(contrast)}`);
    }
    await ev(`document.querySelector('#deskDensity').value='compact';document.querySelector('#deskDensity').dispatchEvent(new Event('change'))`);
    assert.equal(await ev(`document.body.dataset.density`), 'compact');
    console.log('PASS compact density preference; screenshot artifacts ' + JSON.stringify(shots));
    assert.ok(pageRequests.every((url) => url.startsWith('chrome-extension://') || url.startsWith('data:') || url === 'https://www.tradingview-widget.com/embed-widget/advanced-chart/'), 'only the isolated TradingView chart may request an external frame: '+JSON.stringify(pageRequests));
    assert.ok(await ev(`[...document.scripts].every(s=>!s.src||s.src.startsWith(location.origin))`), 'all privileged extension scripts stay local');
    return { identity, screenshots: shots, pageRequests };
  } finally {
    off();
    await browser.call('Target.closeTarget', { targetId }).catch(() => {});
  }
}
