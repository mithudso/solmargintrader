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
