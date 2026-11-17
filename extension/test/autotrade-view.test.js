import test from 'node:test';
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { forecastPayload } from '../src/1000x/autotrade-view.js';

const now = 600_005_000;
const identity = { symbol: 'BTC', feedId: 1, marketAddress: 'source-address', stream: 'fixed_rate@200ms', kind: 'oracle-ohlc' };
const view = () => ({ inputReady: true, mode: 'active', horizon: 600, state: { pending: [{ id: 'composite', mode: 'active', modelSamples: 20,
  issuedAtMs: now - 1000, cutoff: 600000, target: 600600, reference: 100, servedP: 0.7 }] } });
test('maps only stored serving probability and actual source identity', async () => {
  const p = await forecastPayload(view(), identity, now, webcrypto.subtle);
  assert.equal(p.forecast_id.length, 64); assert.equal(p.source_basis, 'jupiter-pyth:1');
  assert.equal(p.market_address, identity.marketAddress); assert.equal(p.p_up, 0.7); assert.equal(p.mode, 'active');
  assert.deepEqual(p, await forecastPayload(view(), identity, now, webcrypto.subtle));
});
test('withholds stale, baseline, untrained, wrong source and unavailable predictions', async () => {
  for (const mutate of [v => { v.inputReady = false; }, v => { v.state.pending[0].mode = 'baseline-warmup'; },
    v => { v.state.pending[0].mode = 'baseline-performance'; }, v => { v.mode = 'baseline-performance'; }, v => { v.state.pending[0].modelSamples = 19; },
    v => { v.state.pending[0].issuedAtMs = now - 30001; }, v => { v.state.pending[0].target = now / 1000; }]) {
    const v = view(); mutate(v); assert.equal(await forecastPayload(v, identity, now, webcrypto.subtle), null);
  }
  assert.equal(await forecastPayload(view(), { ...identity, feedId: 66 }, now, webcrypto.subtle), null);
});

test('active status names the owner session, not editable next-session fields', async () => {
  const { autotradeView } = await import('../src/1000x/autotrade-view.js');
  class Node {
    constructor() { this.children = []; this.dataset = {}; this.value = ''; this.textContent = ''; }
    append(...nodes) { this.children.push(...nodes); }
    before(node) { this.sibling = node; }
    setAttribute() {}
    addEventListener() {}
  }
  const previous = globalThis.document; globalThis.document = { createElement: () => new Node() };
  const root = new Node();
  const call = async () => ({ state: 'running', mode: 'paper', policy: { asset: 'BTC', venue: 'jupiter-sdk-1000x' },
    position: { state: 'open', plan: { direction: 'long', leverage: 1000 } }, net_pnl_usd: 2.5 });
  const ui = autotradeView(root, { call });
  try {
    await new Promise(resolve => setImmediate(resolve));
    const section = root.sibling;
    section.children[2].children[1].children[0].children[0].value = 'ZEC';
    section.children[2].children[1].children[1].children[0].value = 'jupiter-cli-10x';
    const text = section.children[1].textContent;
    for (const item of ['BTC', '1000x', 'long', 'open', '2.5']) assert.ok(text.includes(item), text);
    assert.ok(!text.includes('ZEC'));
  } finally { ui.close(); globalThis.document = previous; }
});

test('blocked and unknown session reasons remain visible without HTML interpretation', async () => {
  const { autotradeView } = await import('../src/1000x/autotrade-view.js');
  class Node {
    constructor() { this.children = []; this.dataset = {}; this.value = ''; this.textContent = ''; }
    append(...nodes) { this.children.push(...nodes); }
    before(node) { this.sibling = node; }
    setAttribute() {}
    addEventListener() {}
  }
  const previous = globalThis.document; globalThis.document = { createElement: () => new Node() };
  const root = new Node();
  const reason = 'Owner restarted; continuity is unknown';
  const positionReason = 'Jupiter quote stream gap while position was at risk <script>not markup</script>';
  const ui = autotradeView(root, { call: async () => ({ state: 'blocked', mode: 'paper', reason,
    position: { state: 'unknown', reason: positionReason }, cleanup: { state: 'pending', reason: 'advice cleanup pending' } }) });
  try {
    await new Promise(resolve => setImmediate(resolve));
    const detail = root.sibling.children.flatMap(node => [node, ...node.children]).find(node => node.className === 'autotrade-detail');
    assert.ok(detail, 'the session-details disclosure contains the owner reasons');
    const text = detail.textContent;
    for (const value of [reason, positionReason, 'advice cleanup pending']) assert.ok(text.includes(value), text);
    assert.equal(detail.children.length, 0, 'reasons are text, not executable markup');
  } finally { ui.close(); globalThis.document = previous; }
});

test('controls reuse request ID after a refusal and closing does not stop the owner', async () => {
  const { autotradeView } = await import('../src/1000x/autotrade-view.js');
  class Node {
    constructor(tag) { this.tag = tag; this.children = []; this.dataset = {}; this.value = ''; this.textContent = ''; }
    set value(v) { this._value = String(v); }
    get value() { return this._value; }
    append(...nodes) { this.children.push(...nodes); }
    before(node) { this.sibling = node; }
    setAttribute() {}
    addEventListener(name, fn) { this[name] = fn; }
  }
  const previous = globalThis.document, previousWindow = globalThis.window;
  globalThis.window = { confirm: () => true };
  globalThis.document = { createElement: tag => new Node(tag) };
  const root = new Node('root'), calls = [];
  const defaults = { asset: 'BTC', venue: 'jupiter-cli-10x', base_collateral_usd: 10, max_collateral_usd: 15, max_session_loss_usd: 50 };
  const call = async (name, params) => {
    calls.push([name, params]);
    if (name === 'autotrade.start_paper') throw new Error('fixture refusal');
    if (name === 'autotrade.start_live') return { state: 'blocked', mode: 'paper', position: { state: 'unknown' } };
    return { state: 'stopped', mode: 'paper', defaults, readiness: { live: 'blocked' } };
  };
  let ui;
  try {
    ui = autotradeView(root, { call, id: () => 'stable-id' });
    await new Promise(resolve => setImmediate(resolve));
    const section = root.sibling, buttons = section.children[3].children, status = section.children[1];
    assert.match(section.children[2].children[0].textContent, /BTC.*10× paper proxy.*base \$10.*max \$15.*loss cap \$50.*advice off/);
    section.children[2].children[1].children[1].children[0].value = 'jupiter-sdk-1000x';
    buttons[0].onclick(); await new Promise(resolve => setImmediate(resolve));
    assert.match(status.textContent, /fixture refusal/);
    buttons[0].onclick(); await new Promise(resolve => setImmediate(resolve));
    const starts = calls.filter(([name]) => name === 'autotrade.start_paper');
    assert.equal(starts.length, 2); assert.equal(starts[0][1].request_id, starts[1][1].request_id);
    assert.equal(starts[0][1].config.mode, 'paper');
    assert.equal(starts[0][1].config.venue, 'jupiter-sdk-1000x');
    assert.equal(starts[0][1].config.advice_enabled, false);
    buttons[1].onclick(); await new Promise(resolve => setImmediate(resolve));
    assert.match(status.textContent, /Enter each live/);
    assert.equal(calls.some(([name]) => name === 'autotrade.start_live'), false);
    for (const label of section.children[2].children[1].children.slice(2, 5)) label.children[0].input();
    buttons[1].onclick(); await new Promise(resolve => setImmediate(resolve));
    assert.equal(calls.find(([name]) => name === 'autotrade.start_live')[1].confirm, true);
    buttons[2].onclick(); await new Promise(resolve => setImmediate(resolve));
    assert.equal(calls.find(([name]) => name === 'autotrade.stop')[1].acknowledge_unknown, true);
    const fresh = view(); fresh.state.pending[0].issuedAtMs = Date.now() - 1000;
    fresh.state.pending[0].target = Math.floor(Date.now() / 1000) + 600;
    await ui.observe(fresh, identity); await ui.observe(fresh, identity);
    assert.equal(calls.filter(([name]) => name === 'autotrade.ingest_forecast').length, 1);
    const beforeClose = calls.length; ui.close();
    assert.equal(calls.length, beforeClose);
  } finally { ui?.close(); globalThis.document = previous; globalThis.window = previousWindow; }
});

test('connection failures keep the helper error visible and recover paper defaults', async t => {
  const { autotradeView } = await import('../src/1000x/autotrade-view.js');
  class Node {
    constructor() { this.children = []; this.dataset = {}; this.value = ''; this.textContent = ''; }
    set value(value) { this._value = String(value); }
    get value() { return this._value; }
    append(...nodes) { this.children.push(...nodes); }
    before(node) { this.sibling = node; }
    setAttribute() {}
    addEventListener() {}
  }
  const previous = globalThis.document;
  globalThis.document = { createElement: () => new Node() };
  let refresh, available = false;
  t.mock.method(globalThis, 'setInterval', callback => { refresh = callback; return 1; });
  t.mock.method(globalThis, 'clearInterval', () => {});
  const failure = 'Specified native messaging host not found; install the local helper';
  const calls = [], root = new Node();
  const ui = autotradeView(root, { call: async command => {
    calls.push(command);
    if (!available) throw new Error(failure);
    return { state: 'stopped', mode: 'paper', defaults: { asset: 'BTC', venue: 'jupiter-cli-10x',
      base_collateral_usd: 10, max_collateral_usd: 15, max_session_loss_usd: 50 } };
  } });
  try {
    await new Promise(resolve => setImmediate(resolve));
    const section = root.sibling, status = section.children[1];
    assert.ok(status.textContent.includes(failure), status.textContent);
    assert.equal(status.dataset.state, 'unavailable');
    available = true; await refresh();
    assert.match(status.textContent, /STOPPED/);
    assert.match(section.children[2].children[0].textContent, /base \$10.*max \$15.*loss cap \$50/);
    available = false; await refresh();
    assert.ok(status.textContent.includes(failure), status.textContent);
    assert.equal(status.dataset.state, 'unavailable');
    assert.deepEqual(calls, Array(3).fill('autotrade.status'));
  } finally { ui.close(); globalThis.document = previous; }
});

test('saved coin memory follows settings without erasing history or requalifying risk', async t => {
  const { autotradeView } = await import('../src/1000x/autotrade-view.js');
  class Node {
    constructor() { this.children = []; this.dataset = {}; this.textContent = ''; this.events = {}; this.value = ''; }
    set value(value) { this._value = String(value); }
    get value() { return this._value; }
    append(...nodes) { this.children.push(...nodes); }
    before(node) { this.sibling = node; }
    setAttribute() {}
    addEventListener(name, fn) { (this.events[name] ||= []).push(fn); }
  }
  const previous = globalThis.document;
  globalThis.document = { createElement: () => new Node() };
  let refresh, unavailable = false;
  t.mock.method(globalThis, 'setInterval', callback => { refresh = callback; return 1; });
  t.mock.method(globalThis, 'clearInterval', () => {});
  const calls = [], root = new Node();
  const snapshot = { state: 'stopped', mode: 'paper', configuration: { asset: 'BTC', venue: 'jupiter-cli-10x' },
    learner: { samples: 0 }, learning_memory: { version: 1, storage: { durable: true, legacy_index_complete: true, unattributed_cohorts: 0 },
      coins: { BTC: { samples: 12, profiles: { 'jupiter-cli-10x': { samples: 9 } } },
        ZEC: { samples: 3, profiles: { 'jupiter-cli-10x': { samples: 3 } } } } } };
  const ui = autotradeView(root, { call: async command => {
    calls.push(command); if (unavailable) throw new Error('offline'); return snapshot;
  } });
  try {
    await new Promise(resolve => setImmediate(resolve));
    const section = root.sibling, memory = section.children.find(node => node.className === 'autotrade-memory');
    assert.match(memory.textContent, /Saved to local disk · BTC · 12 remembered results · 9 compatible model samples/);
    assert.match(memory.textContent, /Current-policy risk qualification stays separate/);
    const asset = section.children[2].children[1].children[0].children[0];
    asset.value = 'ZEC'; for (const fn of asset.events.change) fn();
    assert.match(memory.textContent, /ZEC · 3 remembered results · 3 compatible model samples/);
    asset.value = 'BTC'; for (const fn of asset.events.change) fn();
    assert.match(memory.textContent, /BTC · 12 remembered results/);
    unavailable = true; await refresh();
    assert.match(memory.textContent, /Last reported disk state · BTC · 12 remembered results/);
    asset.value = 'ZEC'; for (const fn of asset.events.change) fn();
    assert.match(memory.textContent, /Last reported disk state · ZEC · 3 remembered results/);
    unavailable = false; snapshot.state = 'unavailable'; await refresh();
    asset.value = 'BTC'; for (const fn of asset.events.change) fn();
    assert.match(memory.textContent, /Last reported disk state · BTC · 12 remembered results/);
    snapshot.state = 'stopped'; await refresh();
    assert.match(memory.textContent, /Saved to local disk · BTC · 12 remembered results/);
    assert.deepEqual(calls, Array(4).fill('autotrade.status'));
    assert.equal(snapshot.learner.samples, 0);
  } finally { ui.close(); globalThis.document = previous; }
});

test('older helpers and memory-only fixtures never claim durable disk persistence', async t => {
  const { autotradeView } = await import('../src/1000x/autotrade-view.js');
  class Node {
    constructor() { this.children = []; this.dataset = {}; this.textContent = ''; this.value = ''; }
    append(...nodes) { this.children.push(...nodes); }
    before(node) { this.sibling = node; }
    setAttribute() {}
    addEventListener() {}
  }
  const previous = globalThis.document;
  globalThis.document = { createElement: () => new Node() };
  let refresh;
  t.mock.method(globalThis, 'setInterval', callback => { refresh = callback; return 1; });
  t.mock.method(globalThis, 'clearInterval', () => {});
  let snapshot = { state: 'stopped', configuration: { asset: 'BTC', venue: 'jupiter-cli-10x' } };
  const root = new Node(), ui = autotradeView(root, { call: async () => snapshot });
  try {
    await new Promise(resolve => setImmediate(resolve));
    const memory = root.sibling.children.find(node => node.className === 'autotrade-memory');
    assert.match(memory.textContent, /unavailable from this helper/);
    assert.doesNotMatch(memory.textContent, /Saved to local disk/);
    snapshot = { ...snapshot, learning_memory: { version: 1, storage: { durable: false, legacy_index_complete: false, unattributed_cohorts: 2 }, coins: { BTC: { samples: 0, profiles: {} } } } };
    await refresh();
    assert.match(memory.textContent, /Disk persistence unavailable/);
    assert.match(memory.textContent, /2 older policy histories retained and being indexed/);
    assert.doesNotMatch(memory.textContent, /Saved to local disk/);
  } finally { ui.close(); globalThis.document = previous; }
});
