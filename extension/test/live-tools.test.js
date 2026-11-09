import test from 'node:test';
import assert from 'node:assert/strict';
import { createLiveWindows } from '../src/bg/live-windows.js';
import { runCommand, COMMANDS } from '../src/core/commands.js';
import { strategyChartData } from '../src/ui/charts.js';
import { explanationLines } from '../src/ui/vote-tools.js';
import { pnlLines, workflowText, workflowButtonText } from '../src/ui/live-panel.js';

function event() { const listeners = []; return { addListener(fn) { listeners.push(fn); }, fire(value) { for (const fn of listeners) fn(value); } }; }
function fixture(timeoutMs = 200) {
  const onConnect = event(), created = [];
  const getURL = path => `chrome-extension://own/${path}`;
  const broker = createLiveWindows({ runtime: { onConnect }, getURL, timeoutMs,
    windows: { async create(options) { created.push(options); return { id: 7 }; } } });
  function owner(url = getURL('src/ui/dashboard.html#soltui/signal')) {
    const messages = [], port = { name: 'signal-live-owner', sender: { url }, onMessage: event(), onDisconnect: event(), postMessage(m) { messages.push(m); } };
    onConnect.fire(port);
    return { port, messages };
  }
  return { broker, owner, created };
}

test('a trusted persistent owner receives the pin synchronously through the registry', async () => {
  const f = fixture(), a = f.owner();
  const task = runCommand({ name: 'openLiveWindow', args: { asset: 'ADA' }, deps: { store: {}, liveWindows: f.broker } });
  const pin = a.messages.at(-1);
  assert.equal(pin.kind, 'pin', 'must relay before any store/native await loses activation');
  assert.equal(pin.asset, 'ADA');
  assert.equal(COMMANDS.openLiveWindow.unlocked, true);
  assert.equal(COMMANDS.openLiveWindow.browserUi, true);
  a.port.onMessage.fire({ kind: 'result', id: pin.id, ok: true, result: { alwaysOnTop: true } });
  assert.deepEqual(await task, { alwaysOnTop: true });
  assert.equal(f.created.length, 0);
});

test('foreign pages cannot claim a live owner and cold opens are deduplicated ordinary windows', async () => {
  const f = fixture();
  f.owner('https://evil.test/src/ui/dashboard.html');
  f.owner('chrome-extension://other/src/ui/dashboard.html');
  const [a, b] = await Promise.all([f.broker.open('SOL'), f.broker.open('SOL')]);
  assert.equal(f.created.length, 1);
  assert.deepEqual(a, b);
  assert.equal(a.requiresPin, true);
  assert.equal(a.alwaysOnTop, undefined, 'ordinary popups are not pinned');
  assert.match(f.created[0].url, /live-window.html\?asset=SOL$/);
  assert.equal(f.created[0].alwaysOnTop, undefined);
});

test('a floating owner wins; another owner cannot spoof its response', async () => {
  const f = fixture(), a = f.owner(), b = f.owner();
  a.port.onMessage.fire({ kind: 'status', floating: true, visible: false });
  b.port.onMessage.fire({ kind: 'status', floating: false, visible: true });
  const task = f.broker.open('BTC'), pin = a.messages.at(-1);
  assert.equal(pin.kind, 'pin');
  let resolved = false; task.then(() => { resolved = true; });
  b.port.onMessage.fire({ kind: 'result', id: pin.id, ok: true, result: 'spoof' });
  await Promise.resolve(); assert.equal(resolved, false);
  a.port.onMessage.fire({ kind: 'result', id: pin.id, ok: true, result: 'real' });
  assert.equal(await task, 'real');
});

test('owner disconnection rejects pending pin and the next action opens a helper', async () => {
  const f = fixture(), a = f.owner();
  const task = f.broker.open('SOL');
  a.port.onDisconnect.fire();
  await assert.rejects(task, /workspace closed/);
  assert.equal((await f.broker.open('SOL')).requiresPin, true);
});

test('a missing owner response expires instead of leaving a button pending forever', async () => {
  const f = fixture(10); f.owner();
  await assert.rejects(f.broker.open('SOL'), /did not answer/);
  assert.throws(() => f.broker.open('SOL<script>'), /Invalid/);
});

test('non-browser command surfaces refuse the UI action without trading dependencies', async () => {
  await assert.rejects(runCommand({ name: 'openLiveWindow', deps: { store: {} } }), /Chrome extension/);
});

test('strategy graphics reject missing numbers, conflicting candles and markers without an original bar', () => {
  const candle = { time: 100, open: 10, high: 12, low: 9, close: 11 };
  const a = { label: 'actual', chart: { candles: [candle, { ...candle, time: 200 }, { ...candle, time: 300, open: null }],
    series: [{ name: 'SMA', data: [{ time: 100, value: 10 }, { time: 200, value: 10 }, { time: 999, value: 9 }] }],
    markers: [{ time: 100, direction: 'UP', text: 'Saved UP' }, { time: 999, direction: 'DOWN', text: 'missing' }] } };
  const b = { label: 'other', chart: { candles: [{ ...candle, time: 200, close: 10 }], missing: ['State was not recorded'] } };
  const output = strategyChartData([a, b]);
  assert.deepEqual(output.candles, [candle]);
  assert.deepEqual(output.series[0].data, [{ time: 100, value: 10 }]);
  assert.equal(output.markers.length, 1);
  assert.match(output.markers[0].text, /actual.*Saved UP/);
  assert.match(output.missing.join(' '), /Conflicting/);
  assert.match(output.missing.join(' '), /State was not recorded/);
});

test('vote explanation uses the saved eligible rule and reports absent numeric state', () => {
  const lines = explanationLines({ available: true, calls: [{ eligible: true, horizon_minutes: 1, direction: 'DOWN', accuracy: 75, resolved: 24,
    issued_at: 100, expires_at: 160, rule: 'Saved RSI rule', recorded_signal_basis: { features_available: false, reason: 'Seed state was not saved.' } },
  { eligible: false, rule: 'Expired winning call must not explain current vote' }] });
  assert.match(lines.join(' '), /1m DOWN.*75%/);
  assert.ok(lines.includes('Saved RSI rule'));
  assert.ok(lines.includes('Seed state was not saved.'));
  assert.doesNotMatch(lines.join(' '), /Expired winning/);
});

test('paper P&L uses fractional returns and never invents missing realized profit', () => {
  const rows = pnlLines({ net_usd: 2.3691, net_pct: .0023691, equity: 1002.3691, hold_return: .015212, excess_return: -.012843 });
  assert.match(rows[0][1], /\+\$2\.37.*\+0\.2%/);
  assert.equal(rows.find(r => r[0] === 'Realized')[1], '—');
  assert.match(rows.find(r => r[0] === 'Buy & hold')[1], /1\.5%/);
  assert.match(rows.find(r => r[0] === 'Versus hold')[1], /−1\.3%/);
  assert.deepEqual(pnlLines(null), []);
});

test('workflow summary reports actual batch phase rather than claiming preparation finished tests', () => {
  assert.equal(workflowText({ state: 'ready', batch: { running: true, phase: 'backtesting', counts: { queued: 20, passed: 3 }, assets: ['SOL', 'ADA'] } }), 'backtesting · 20 queued · 3 passed · 2 coins');
  assert.match(workflowText({ running: true }), /Preparing/);
  assert.match(workflowText({ state: 'waiting', message: 'Grid Stop retained' }), /Stop retained/);
});

test('an independent running batch cannot label an unrequested coordinator running', () => {
  assert.equal(workflowButtonText({ state: 'stopped', running: false, batch: { running: true, phase: 'forward_partial' } }), 'Start / resume paper bots');
  assert.equal(workflowButtonText({ state: 'running', running: true }), 'Preparing paper workflow…');
  assert.equal(workflowButtonText({ state: 'ready', running: false }), 'Paper monitoring ready');
  assert.equal(workflowButtonText({ state: 'partial', running: false }), 'Start / resume paper bots');
});
