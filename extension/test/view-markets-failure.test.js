import test from 'node:test';
import assert from 'node:assert/strict';
import { renderHoldings, refreshPnl } from '../src/ui/view-markets.js';

class FakeNode {
  constructor(tag) { this.tag = tag; this.children = []; this.dataset = {}; this.style = {}; this.classList = { add() {}, remove() {} }; this.textContent = ''; this.value = ''; this.disabled = false; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(name, fn) { this[name] = fn; }
  setAttribute() {}
}
const walk = node => [node, ...(node.children ?? []).flatMap(walk)];
const text = node => walk(node).map(x => x.textContent).join(' ');

test('failed holdings remain incomplete and failed snapshot can be retried', async () => {
  const saved = { Node: globalThis.Node, document: globalThis.document, chrome: globalThis.chrome }, nodes = new Map();
  globalThis.Node = FakeNode;
  globalThis.document = { querySelector(s) { if (!nodes.has(s)) nodes.set(s, new FakeNode('query')); return nodes.get(s); }, createElement: tag => new FakeNode(tag) };
  globalThis.chrome = { runtime: { async sendMessage(m) {
    if (m.command === 'pnl.summary') return { ok: true, result: { ok: true, result: { sections: [{ source: 'wallet (live)', status: 'unavailable' }] } } };
    if (m.command === 'pnl.series') return { ok: true, result: { ok: true, result: { sections: [] } } };
    return { ok: false, error: 'fixture failure' };
  } } };
  try {
    renderHoldings({ holdings: { complete: false, chains: [{ chain: 'base', status: 'failed', holdings: [], errors: ['fixture failure'] }], addressSource: {} } });
    assert.match(text(nodes.get('#holdingsChains')), /read is incomplete/);
    assert.doesNotMatch(text(nodes.get('#holdingsChains')), /No balances above dust/);
    await refreshPnl();
    const button = walk(nodes.get('#pnlSections')).find(x => x.tag === 'button');
    await button.click();
    assert.equal(button.disabled, false);
    assert.match(button.textContent, /Not recorded.*Retry/);
  } finally { globalThis.Node = saved.Node; globalThis.document = saved.document; globalThis.chrome = saved.chrome; }
});
