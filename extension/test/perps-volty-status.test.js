import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { mountVoltyStatus } from '../src/perps/volty-status.js';

class Node {
  children = [];
  textContent = '';
  attributes = new Set();
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(key) { this.attributes.add(key); }
  toggleAttribute(key, on) { if (on) this.attributes.add(key); else this.attributes.delete(key); }
}

const at = 1800000000;
const markup = readFileSync(new URL('../src/perps/panel.html', import.meta.url), 'utf8');
const report = (values = {}) => ({
  schema: 1, mode: 'observe', state: 'watching', updated_at: at, orders: [], signal: null, ...values,
});
const performanceReport = (values = {}) => ({
  updated_at: at, gross_pnl_usdc: 0.012345, net_pnl_usdc: -0.000002,
  closed_trades: 3, profitable_trades: 2, ...values,
});
const reconciliation = (values = {}) => ({
  unresolved_fresh_ticks: 3, reset_threshold: 4, last_reset_at: at - 30, ...values,
});

async function mount(t, snapshot, now = at) {
  const nodes = new Map();
  for (const attribute of markup.matchAll(/\bdata-volty-[a-z-]+\b/g)) {
    nodes.set(`[${attribute[0]}]`, new Node());
  }
  const section = { hidden: true, querySelector: key => nodes.get(key) };
  const priorDocument = globalThis.document;
  const priorNode = globalThis.Node;
  globalThis.document = { createElement: () => new Node() };
  globalThis.Node = Node;
  const calls = [];
  const ui = mountVoltyStatus(section, { clock: () => now * 1000,
    call: async (name, params) => { calls.push({ name, params }); return snapshot; } });
  t.after(() => { ui.close(); globalThis.document = priorDocument; globalThis.Node = priorNode; });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(section.hidden, false);
  assert.deepEqual(calls, [{ name: 'zec.volty.status', params: undefined }]);
  return name => nodes.get(`[data-volty-${name}]`);
}

test('observe status says the owner will only watch for signals', async t => {
  const node = await mount(t, report());
  assert.equal(node('status').textContent, 'Observe · Watching for signals');
  assert.equal(node('orders-note').textContent, 'Observe mode submits no orders.');
  assert.equal(node('mark').textContent, '—');
  assert.match(node('market-note').textContent, /unavailable/);
  assert.equal(node('gross').textContent, '—');
  assert.equal(node('reconciliation').hidden, true);
});

test('live receipts distinguish an unverified open from a confirmed close', async t => {
  const template = { event_id: 'signal-1', client_order_id: '1234', side: 'sell', requested_quantity: '0.015', updated_at: at };
  const node = await mount(t, report({ mode: 'live', state: 'checking',
    signal: { event_id: 'signal-1', side: 'sell', at, mark: 550, upper: 600, lower: 551 },
    orders: [
      { ...template, leg: 'open', state: 'pending', order_id: null, filled_quantity: null, fills: [] },
      { ...template, leg: 'close', state: 'filled', order_id: '1234567890123456789', filled_quantity: '0.015',
        fills: [{ signature: '<txid>', size: '0.015', price: '550', fee: '0.01', timestamp: at }] },
    ] }));
  assert.match(node('signal').textContent, /Last signal Short/);
  const [open, close] = node('orders').children;
  assert.equal(open.children[0].textContent, 'Open short · Pending');
  assert.match(open.children[1].textContent, /filled size unverified/);
  assert.match(open.children[2].textContent, /client order 1234/);
  assert.equal(close.children[0].textContent, 'Close long · Confirmed fill');
  assert.match(close.children[1].textContent, /1234567890123456789/);
  const [tx] = close.children[3].children;
  assert.match(tx.textContent, /transaction <txid>/);
  assert.equal(tx.children.length, 0);
});

test('observe shows historical acknowledgements without treating them as filled', async t => {
  const node = await mount(t, report({ orders: [{ event_id: 'signal-2', client_order_id: '12345',
    side: 'buy', leg: 'open', state: 'acknowledged', order_id: null, requested_quantity: '0.015',
    filled_quantity: null, updated_at: at, fills: [] }] }));
  assert.match(node('orders-note').textContent, /Receipts below are from prior live runs/);
  assert.equal(node('orders').children[0].children[0].textContent, 'Open long · Acknowledged');
});

test('old live state never renders as currently armed even when an observation is present', async t => {
  const telemetry = { market: { window_start: at, mark_at: at, mark: 550, upper: 600, lower: 551 }, activity: [] };
  const node = await mount(t, report({ mode: 'live', state: 'armed', telemetry }), at + 61);
  assert.equal(node('status').textContent, 'Live · Status stale');
  assert.ok(node('status').attributes.has('data-stale'));
  assert.equal(node('mark').textContent, '—');
});

test('fresh live checks distinguish watchdog progress from the last signal reset', async t => {
  const telemetry = { reconciliation: reconciliation() };
  const node = await mount(t, report({ mode: 'live', state: 'checking', telemetry }));
  assert.equal(node('reconciliation').hidden, false);
  assert.match(node('reconciliation').textContent, /3 of 4 fresh ticks with an unresolved order/);
  assert.match(node('reconciliation').textContent, /Last signal reset .* UTC.*Order outcomes require separate venue confirmation/);
});

test('stale watchdog telemetry only shows when the signal last reset', async t => {
  const telemetry = { reconciliation: reconciliation() };
  const node = await mount(t, report({ mode: 'live', state: 'checking', telemetry }), at + 61);
  assert.equal(node('reconciliation').hidden, false);
  assert.match(node('reconciliation').textContent, /Historical signal reset .* UTC/);
  assert.doesNotMatch(node('reconciliation').textContent, /fresh ticks/);
});

test('armed status shows a reset without implying an unresolved order remains', async t => {
  const telemetry = { reconciliation: reconciliation() };
  const node = await mount(t, report({ mode: 'live', state: 'armed', telemetry }));
  assert.match(node('reconciliation').textContent, /Last signal reset .* UTC/);
  assert.doesNotMatch(node('reconciliation').textContent, /unresolved order/);
});

test('future snapshot is unavailable', async t => {
  const node = await mount(t, report({ mode: 'live', state: 'armed' }), at - 10);
  assert.equal(node('status').textContent, 'Local Volty status unavailable');
  assert.equal(node('orders').children.length, 0);
  assert.match(node('performance-note').textContent, /Local host unavailable/);
});

test('closed performance shows gross, net and win rate with its own freshness', async t => {
  const node = await mount(t, report({ mode: 'live', state: 'armed', performance: performanceReport() }), at + 61);
  assert.equal(node('status').textContent, 'Live · Status stale');
  assert.equal(node('gross').textContent, '+0.012345 USDC');
  assert.ok(node('gross').attributes.has('data-profit'));
  assert.equal(node('net').textContent, '-0.000002 USDC');
  assert.ok(node('net').attributes.has('data-loss'));
  assert.equal(node('profitable').textContent, '2 of 3 (66.7%)');
  assert.match(node('performance-note').textContent, /Closed trades as of .*Net includes fees and funding/);
  assert.ok(!node('performance-note').attributes.has('data-stale'));
});

test('zero confirmed closes have zero realized P&L and an undefined win rate', async t => {
  const performance = performanceReport({ gross_pnl_usdc: 0, net_pnl_usdc: 0, closed_trades: 0, profitable_trades: 0 });
  const node = await mount(t, report({ mode: 'live', state: 'armed', performance }));
  assert.equal(node('gross').textContent, '0.00 USDC');
  assert.equal(node('net').textContent, '0.00 USDC');
  assert.equal(node('profitable').textContent, '0 of 0 (—)');
});

test('malformed performance leaves the valid bot status and shows no amounts', async t => {
  const performance = performanceReport({ profitable_trades: 4 });
  const node = await mount(t, report({ mode: 'live', state: 'armed', performance }));
  assert.equal(node('status').textContent, 'Live · Armed');
  assert.equal(node('gross').textContent, '—');
  assert.equal(node('net').textContent, '—');
  assert.equal(node('profitable').textContent, '—');
  assert.equal(node('performance-note').textContent, 'Closed-trade performance unavailable.');
});
