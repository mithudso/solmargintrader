import test from 'node:test';
import assert from 'node:assert/strict';
import { renderOverview } from '../src/ui/view-overview.js';

class FakeNode {
  constructor() { this.children = []; this.dataset = {}; this.style = {}; this.classList = { add() {}, remove() {} }; this.textContent = ''; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener() {}
  setAttribute() {}
}
const text = node => [node?.textContent, ...(node?.children ?? []).map(text)].join(' ');

test('overview does not turn missing evidence into zero, negative or clear alerts', async () => {
  const saved = { Node: globalThis.Node, document: globalThis.document, chrome: globalThis.chrome };
  const nodes = new Map(), bad = { chains: [{ chain: 'base', status: 'failed', holdings: [] }], complete: false, atMs: 0 };
  globalThis.Node = FakeNode;
  globalThis.document = { querySelector(s) { if (!nodes.has(s)) nodes.set(s, new FakeNode()); return nodes.get(s); }, createElement: () => new FakeNode() };
  globalThis.chrome = { runtime: { async sendMessage(m) {
    if (m.type === 'holdings') return { ok: true, result: bad };
    if (m.command === 'top5.list') return { ok: true, result: { ok: true, result: { configs: [{ rank: 1, label: 'fixture', home: {} }] } } };
    return { ok: false, error: 'fixture unavailable' };
  } } };
  try {
    const state = { holdings: bad, overview: { scan: { alerts: [{ acked: true }], liquidity: { bestScout: [{ expected_net_apr: null }] } } } };
    await renderOverview(state, { onAck() {} }); await new Promise(resolve => setImmediate(resolve));
    assert.equal(nodes.get('#kpiIdle').textContent, '—');
    assert.match(text(nodes.get('#overviewAlerts')), /No unacknowledged alerts/);
    assert.doesNotMatch(text(nodes.get('#overviewScout')), /models negative/);
    assert.match(text(nodes.get('#overviewStrategy')), /Positive paths unavailable/);
    bad.chains[0] = { chain: 'base', status: 'partial', holdings: [] };
    await renderOverview(state, { onAck() {} }); await new Promise(resolve => setImmediate(resolve));
    assert.match(nodes.get('#kpiIdle').textContent, /^at least /);
  } finally { globalThis.Node = saved.Node; globalThis.document = saved.document; globalThis.chrome = saved.chrome; }
});
