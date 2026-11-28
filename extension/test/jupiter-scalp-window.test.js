import test from 'node:test';
import assert from 'node:assert/strict';
import { createJupiterScalpWindows } from '../src/bg/jupiter-scalp-window.js';
import { COMMANDS, runCommand, CommandError } from '../src/core/commands.js';

function harness({ reply = { ok: true, recognized: true, positions: [] }, tabUrl = 'https://jup.ag/1000x?market=SOL&mode=classic' } = {}) {
  const listeners = { windowRemoved: [], tabRemoved: [] };
  const state = { persisted: {}, opened: new Map(), sent: [], focused: [], activated: [], nextWindow: 4, tabUrl, reply };
  const options = {
    runtime: { getURL: path => `chrome-extension://fixture/${path}` },
    storage: {
      async get(key) { return { [key]: structuredClone(state.persisted[key]) }; },
      async set(values) { Object.assign(state.persisted, structuredClone(values)); },
    },
    tabs: {
      onRemoved: { addListener: fn => listeners.tabRemoved.push(fn) },
      async get(id) { if (id !== 2 || state.tabUrl === null) throw new Error('no tab'); return { id, windowId: 1, url: state.tabUrl }; },
      async update(id, change) {
        if (change.url) state.opened.get([...state.opened.keys()].at(-1)).tabs[0] = { id, url: change.url };
        if (change.active) state.activated.push(id);
      },
      async sendMessage(...args) { state.sent.push(args); if (state.reply instanceof Error) throw state.reply; return state.reply; },
    },
    windows: {
      onRemoved: { addListener: fn => listeners.windowRemoved.push(fn) },
      async create(options) {
        const id = state.nextWindow++;
        const popup = { id, tabs: [{ id: id + 5 }], options };
        state.opened.set(id, popup);
        return popup;
      },
      async get(id) { return state.opened.get(id); },
      async update(id, change) { if (change.focused) state.focused.push(id); },
      async remove(id) { if (!state.opened.delete(id)) throw new Error('gone'); },
    },
  };
  return { state, options, listeners, scalp: createJupiterScalpWindows(options) };
}
const source = { frameId: 0, documentId: 'source', tab: { id: 2, windowId: 1 }, url: 'https://jup.ag/1000x?market=SOL&mode=classic' };
const panelOf = state => {
  const [id, popup] = [...state.opened].at(-1);
  return { frameId: 0, documentId: 'panel', tab: { id: popup.tabs[0].id, windowId: id }, url: popup.tabs[0].url };
};
const expect = { coin: 'SOL', side: 'long', leverage: 1000, entryText: '$71.6802' };

test('the Jupiter tab opens one scalp window and reopening focuses it', async () => {
  const { state, scalp } = harness();
  assert.deepEqual(await scalp.control('status', source), { open: false });
  assert.deepEqual(await scalp.control('open', source), { open: true });
  assert.equal(state.opened.size, 1);
  assert.equal(panelOf(state).url, 'chrome-extension://fixture/src/1000x/scalp.html#market=SOL');
  assert.equal(state.opened.get(4).options.type, 'popup');
  assert.deepEqual(await scalp.control('open', source), { open: true });
  assert.deepEqual([state.opened.size, state.focused], [1, [4]]);
  assert.deepEqual(await scalp.control('status', source), { open: true });
  // Another market in the same tab replaces the window instead of leaving a stale one.
  await scalp.control('open', { ...source, url: 'https://jup.ag/1000x?market=BTC' });
  assert.deepEqual([state.opened.size, panelOf(state).url.endsWith('#market=BTC')], [1, true]);
  assert.deepEqual(await scalp.control('close', source), { open: false });
  assert.equal(state.opened.size, 0);
  await assert.rejects(scalp.control('open', { ...source, url: 'https://jup.ag/1000x' }), /Select a Jupiter 1000x market/);
  await assert.rejects(scalp.control('open', { ...source, frameId: 3 }), /owning browser tab/);
  await assert.rejects(scalp.control('positions', source), /Invalid scalp window action/);
});

test('only the window this worker opened may read positions or ask for a close', async () => {
  const { state, options, scalp } = harness({ reply: { ok: true, recognized: true, positions: [{ coin: 'SOL' }] } });
  await scalp.control('open', source);
  const panel = panelOf(state);
  // A rebuilt worker (MV3 eviction) still knows the window.
  const recovered = createJupiterScalpWindows(options);
  assert.deepEqual(await recovered.control('status', panel), { attached: true, symbol: 'SOL' });
  assert.deepEqual(await recovered.control('positions', panel), { ok: true, recognized: true, positions: [{ coin: 'SOL' }] });
  assert.deepEqual(state.sent.at(-1), [2, { type: 'jupiter1000xPage', action: 'positions' }, { frameId: 0 }]);
  await recovered.control('closePosition', panel, { expect });
  assert.deepEqual(state.sent.at(-1), [2, { type: 'jupiter1000xPage', action: 'closePosition', expect }, { frameId: 0 }]);
  assert.deepEqual(await recovered.control('closePosition', panel, { expect: { ...expect, coin: 'BTC' } }), { ok: false, reason: 'position_market_mismatch' });
  assert.deepEqual(await recovered.control('closePosition', panel, {}), { ok: false, reason: 'position_market_mismatch' });
  const before = state.sent.length;
  for (const stranger of [
    { ...panel, tab: { ...panel.tab, id: 99 } }, { ...panel, tab: { ...panel.tab, windowId: 99 } },
    { ...panel, url: 'chrome-extension://fixture/src/1000x/scalp.html#market=BTC' }, { ...panel, url: 'chrome-extension://fixture/src/ui/popup.html' },
    { ...panel, url: 'https://example.com/1000x?market=SOL' },
  ]) await assert.rejects(recovered.control('closePosition', stranger, { expect }), /not attached/);
  assert.equal(state.sent.length, before, 'a stranger reaches no page');
  assert.deepEqual(await recovered.control('showJupiter', panel), { ok: true });
  assert.deepEqual([state.activated, state.focused], [[2], [1]]);
  await assert.rejects(recovered.control('open', panel), /Invalid scalp window action/);
});

test('a window with a live guard is not closed or replaced under it', async () => {
  const { state, listeners, scalp } = harness();
  await scalp.control('open', source);
  const panel = panelOf(state);
  assert.deepEqual(await scalp.control('guardState', panel, { live: true }), { ok: true, live: true });
  await assert.rejects(scalp.control('open', { ...source, url: 'https://jup.ag/1000x?market=BTC' }), /Disarm it there first/);
  await assert.rejects(scalp.control('close', source), /Disarm it there first/);
  assert.equal(state.opened.size, 1);
  assert.deepEqual(await scalp.control('open', source), { open: true }, 'the same market still just focuses it');
  // Closing the Jupiter tab cannot be refused; the window stays to report that its page is gone.
  listeners.tabRemoved[0](2);
  await assert.rejects(scalp.control('status', panel), /not attached/);
  assert.equal(state.opened.size, 1);
  const calm = harness();
  await calm.scalp.control('open', source);
  const calmPanel = panelOf(calm.state);
  await calm.scalp.control('guardState', calmPanel, { live: true });
  assert.deepEqual(await calm.scalp.control('guardState', calmPanel, { live: false }), { ok: true, live: false });
  assert.deepEqual(await calm.scalp.control('close', source), { open: false });
  await assert.rejects(calm.scalp.control('guardState', source, { live: true }), /Invalid scalp window action/);
});

test('a lost page is an explicit failure, never a silent success', async () => {
  const gone = harness({ tabUrl: null });
  await gone.scalp.control('open', source);
  assert.deepEqual(await gone.scalp.control('positions', panelOf(gone.state)), { ok: false, reason: 'jupiter_tab_unavailable' });
  assert.equal(gone.state.sent.length, 0);
  const broken = harness({ reply: new Error('Receiving end does not exist') });
  await broken.scalp.control('open', source);
  assert.deepEqual(await broken.scalp.control('closePosition', panelOf(broken.state), { expect }), { ok: false, reason: 'page_unreachable' });
  const silent = harness({ reply: null });
  await silent.scalp.control('open', source);
  assert.deepEqual(await silent.scalp.control('positions', panelOf(silent.state)), { ok: false, reason: 'page_no_reply' });
  let fire;
  const slow = harness({ reply: new Promise(() => {}) });
  const timed = createJupiterScalpWindows({ ...slow.options, setTimeoutImpl: fn => { fire = fn; return 1; }, clearTimeoutImpl() {} });
  await timed.control('open', source);
  const pending = timed.control('positions', panelOf(slow.state));
  await new Promise(resolve => setImmediate(resolve));
  fire();
  assert.deepEqual(await pending, { ok: false, reason: 'page_timeout' });
});

test('the window closes with its Jupiter tab and forgets itself when closed', async () => {
  const { state, listeners, scalp } = harness();
  await scalp.control('open', source);
  const panel = panelOf(state);
  listeners.tabRemoved[0](7);
  await scalp.control('status', source);
  assert.equal(state.opened.size, 1, 'another tab closing changes nothing');
  listeners.tabRemoved[0](2);
  assert.deepEqual(await scalp.control('status', source), { open: false });
  assert.equal(state.opened.size, 0);
  await assert.rejects(scalp.control('status', panel), /not attached/);
  await scalp.control('open', source);
  const again = panelOf(state);
  state.opened.delete(again.tab.windowId);
  listeners.windowRemoved[0](again.tab.windowId);
  assert.deepEqual(await scalp.control('status', source), { open: false });
  await assert.rejects(scalp.control('positions', again), /not attached/);
});

test('the registry command validates before anything reaches a page', async () => {
  assert.deepEqual([COMMANDS.jupiterScalpWindow.browserUi, COMMANDS.jupiterScalpWindow.unlocked], [true, true]);
  const calls = [];
  const deps = { store: {}, sender: source, jupiterScalpWindows: { control: (...args) => { calls.push(args); return { ok: true }; } } };
  const run = args => runCommand({ name: 'jupiterScalpWindow', args, deps });
  await run({ action: 'open' });
  await run({ action: 'closePosition', expect });
  await run({ action: 'guardState', live: true });
  assert.deepEqual(calls.map(call => [call[0], call[2]]), [['open', { expect: undefined, live: undefined }],
    ['closePosition', { expect, live: undefined }], ['guardState', { expect: undefined, live: true }]]);
  for (const bad of [
    { action: 'closeAll' }, { action: 'closePosition' }, { action: 'closePosition', expect: { ...expect, leverage: 5000 } },
    { action: 'closePosition', expect: { ...expect, side: 'both' } }, { action: 'closePosition', expect: { ...expect, coin: 'sol' } },
    { action: 'closePosition', expect: { ...expect, entryText: '' } }, { action: 'closePosition', expect: { ...expect, extra: 1 } },
    { action: 'closePosition', expect: [] }, { action: 'positions', expect }, { action: 'guardState' }, { action: 'open', live: true },
  ]) await assert.rejects(run(bad), error => error instanceof CommandError && error.status === 400, JSON.stringify(bad));
  assert.equal(calls.length, 3);
  // Outside Chrome (CLI, HTTP API) there is no page to act on.
  await assert.rejects(runCommand({ name: 'jupiterScalpWindow', args: { action: 'open' }, deps: { store: {} } }),
    error => error instanceof CommandError && error.status === 501);
});
