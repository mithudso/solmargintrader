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
  assert.deepEqual(await recovered.control('status', panel), { attached: true, symbol: 'SOL', venue: '1000x' });
  assert.deepEqual(await recovered.control('positions', panel), { ok: true, recognized: true, positions: [{ coin: 'SOL' }] });
  assert.deepEqual(state.sent.at(-1), [2, { type: 'jupiter1000xPage', action: 'positions' }, { frameId: 0 }]);
  await recovered.control('closePosition', panel, { expect });
  assert.deepEqual(state.sent.at(-1), [2, { type: 'jupiter1000xPage', action: 'closePosition', expect }, { frameId: 0 }]);
  assert.deepEqual(await recovered.control('closePosition', panel, { expect: { ...expect, coin: 'BTC' } }), { ok: false, reason: 'position_market_mismatch' });
  assert.deepEqual(await recovered.control('closePosition', panel, {}), { ok: false, reason: 'position_market_mismatch' });
  // An entry is relayed with this window's market, so the page can refuse when it shows another one.
  await recovered.control('openPosition', panel, { side: 'long', fraction: 0.5 });
  assert.deepEqual(state.sent.at(-1), [2, { type: 'jupiter1000xPage', action: 'openPosition', request: { side: 'long', fraction: 0.5, leverage: null, coin: 'SOL' } }, { frameId: 0 }]);
  await recovered.control('openPosition', panel, { side: 'short', fraction: 1, leverage: 500 });
  assert.equal(state.sent.at(-1)[1].request.leverage, 500);
  await assert.rejects(recovered.control('openPosition', source, { side: 'long', fraction: 0.5 }), /Invalid scalp window action/);
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

test('the window can be re-bound to another coin, but not under a live guard', async () => {
  const { state, scalp } = harness();
  await scalp.control('open', source);
  const panel = panelOf(state);
  assert.deepEqual(await scalp.control('setMarket', panel, { market: 'BTC' }), { ok: true, symbol: 'BTC' });
  // The window reloads on its new address; the old one is no longer this window's.
  await assert.rejects(scalp.control('status', panel), /not attached/);
  const moved = { ...panel, url: 'chrome-extension://fixture/src/1000x/scalp.html#market=BTC' };
  assert.deepEqual(await scalp.control('status', moved), { attached: true, symbol: 'BTC', venue: '1000x' });
  await scalp.control('openPosition', moved, { side: 'long', fraction: 1 });
  assert.equal(state.sent.at(-1)[1].request.coin, 'BTC', 'entries go to the coin the window now watches');
  await scalp.control('guardState', moved, { live: true });
  assert.deepEqual(await scalp.control('setMarket', moved, { market: 'ETH' }), { ok: false, reason: 'guard_live' });
  for (const market of [undefined, '', 'eth', '1INCH', 'A'.repeat(13)]) assert.deepEqual(await scalp.control('setMarket', moved, { market }), { ok: false, reason: 'invalid_request' });
  await assert.rejects(scalp.control('setMarket', source, { market: 'BTC' }), /Invalid scalp window action/);
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
  await run({ action: 'openPosition', side: 'short', fraction: 0.75 });
  const none = { expect: undefined, live: undefined, side: undefined, fraction: undefined, leverage: undefined, market: undefined };
  await run({ action: 'openPosition', side: 'long', fraction: 1, leverage: 500 });
  await run({ action: 'setMarket', market: 'BTC' });
  assert.deepEqual(calls.pop().slice(0, 1).concat(calls.length), ['setMarket', 5]);
  assert.deepEqual(calls.map(call => [call[0], call[2]]), [['open', none], ['closePosition', { ...none, expect }],
    ['guardState', { ...none, live: true }], ['openPosition', { ...none, side: 'short', fraction: 0.75 }],
    ['openPosition', { ...none, side: 'long', fraction: 1, leverage: 500 }]]);
  for (const bad of [
    { action: 'closeAll' }, { action: 'closePosition' }, { action: 'closePosition', expect: { ...expect, leverage: 5000 } },
    { action: 'closePosition', expect: { ...expect, side: 'both' } }, { action: 'closePosition', expect: { ...expect, coin: 'sol' } },
    { action: 'closePosition', expect: { ...expect, entryText: '' } }, { action: 'closePosition', expect: { ...expect, extra: 1 } },
    { action: 'closePosition', expect: [] }, { action: 'positions', expect }, { action: 'guardState' }, { action: 'open', live: true },
    { action: 'openPosition' }, { action: 'openPosition', side: 'long' }, { action: 'openPosition', side: 'up', fraction: 0.5 },
    { action: 'openPosition', side: 'long', fraction: 0.6 }, { action: 'openPosition', side: 'long', fraction: 2 },
    { action: 'openPosition', side: 'long', fraction: 1, leverage: 750 }, { action: 'openPosition', side: 'long', fraction: 1, leverage: 2000 }, { action: 'positions', leverage: 500 },
    { action: 'setMarket' }, { action: 'setMarket', market: 'btc' }, { action: 'setMarket', market: 'BTC/USD' }, { action: 'open', market: 'BTC' },
    { action: 'positions', side: 'long', fraction: 0.5 }, { action: 'closePosition', expect, side: 'long', fraction: 1 },
  ]) await assert.rejects(run(bad), error => error instanceof CommandError && error.status === 400, JSON.stringify(bad));
  assert.equal(calls.length, 5);
  // Outside Chrome (CLI, HTTP API) there is no page to act on.
  await assert.rejects(runCommand({ name: 'jupiterScalpWindow', args: { action: 'open' }, deps: { store: {} } }),
    error => error instanceof CommandError && error.status === 501);
});

test('a Perps tab opens a read-outs-only window: nothing on that page is read or pressed', async () => {
  const perps = { ...source, url: 'https://jup.ag/perps/long/USDC-HYPE' };
  const { state, scalp } = harness({ tabUrl: perps.url });
  assert.deepEqual(await scalp.control('open', perps), { open: true });
  assert.equal(panelOf(state).url, 'chrome-extension://fixture/src/1000x/scalp.html#market=HYPE&venue=perps');
  const panel = panelOf(state);
  assert.deepEqual(await scalp.control('status', panel), { attached: true, symbol: 'HYPE', venue: 'perps' });
  // No relay to the page for any of the three page actions.
  for (const [action, args] of [['positions', {}], ['closePosition', { expect: { ...expect, coin: 'HYPE' } }], ['openPosition', { side: 'long', fraction: 0.25 }]]) {
    assert.deepEqual(await scalp.control(action, panel, args), { ok: false, reason: 'view_only' }, action);
  }
  assert.equal(state.sent.length, 0);
  // Bringing the Jupiter tab forward still works.
  assert.deepEqual(await scalp.control('showJupiter', panel), { ok: true });
  // The same window address without the venue is a stranger, and so is the 1000x form of it.
  await assert.rejects(scalp.control('status', { ...panel, url: 'chrome-extension://fixture/src/1000x/scalp.html#market=HYPE' }), /not attached/);
  // Switching the coin keeps the window read-outs only.
  assert.deepEqual(await scalp.control('setMarket', panel, { market: 'ZEC' }), { ok: true, symbol: 'ZEC' });
  const moved = { ...panel, url: 'chrome-extension://fixture/src/1000x/scalp.html#market=ZEC&venue=perps' };
  assert.deepEqual(await scalp.control('status', moved), { attached: true, symbol: 'ZEC', venue: 'perps' });
  assert.deepEqual(await scalp.control('positions', moved), { ok: false, reason: 'view_only' });
});

test('Perps routes: every listed market and both sides open, anything else is refused', async () => {
  for (const [path, symbol] of [['/perps/long/JupUSD-SOL', 'SOL'], ['/perps/short/JupUSD-BTC', 'BTC'], ['/perps/long/JupUSD-ETH', 'ETH'],
    ['/perps/short/USDC-ZEC', 'ZEC'], ['/perps/long/JupUSD-HYPE', 'HYPE'], ['/perps/long/USDC-HYPE/', 'HYPE']]) {
    const { state, scalp } = harness();
    await scalp.control('open', { ...source, url: `https://jup.ag${path}` });
    assert.equal(panelOf(state).url, `chrome-extension://fixture/src/1000x/scalp.html#market=${symbol}&venue=perps`, path);
  }
  for (const path of ['/perps', '/perps/long/USDC-SOL', '/perps/long/USDC-DOGE', '/perps/flat/USDC-HYPE', '/perps/long/USDC-HYPE/extra', '/swap/SOL-USDC']) {
    const { state, scalp } = harness();
    await assert.rejects(scalp.control('open', { ...source, url: `https://jup.ag${path}` }), /not attached|Invalid scalp window action|Select a Jupiter/, path);
    assert.equal(state.opened.size, 0, path);
  }
  await assert.rejects(harness().scalp.control('open', { ...source, url: 'https://evil.example/perps/long/USDC-HYPE' }), /not attached/);
});

test('moving a tab between 1000x and Perps replaces the window instead of reusing the wrong mode', async () => {
  const { state, scalp } = harness();
  await scalp.control('open', { ...source, url: 'https://jup.ag/1000x?market=HYPE' });
  assert.equal(panelOf(state).url.endsWith('#market=HYPE'), true);
  await scalp.control('open', { ...source, url: 'https://jup.ag/perps/long/USDC-HYPE' });
  assert.deepEqual([state.opened.size, panelOf(state).url.endsWith('#market=HYPE&venue=perps')], [1, true]);
  await scalp.control('open', { ...source, url: 'https://jup.ag/1000x?market=HYPE' });
  assert.deepEqual([state.opened.size, panelOf(state).url.endsWith('#market=HYPE')], [1, true]);
  // A 1000x window still relays; the Perps restriction did not leak into it.
  assert.equal((await scalp.control('positions', panelOf(state))).ok, true);
  assert.equal(state.sent.length, 1);
});
