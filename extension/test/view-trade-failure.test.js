import test from 'node:test';
import assert from 'node:assert/strict';
import { mountStrategies } from '../src/ui/view-trade.js';

class FakeNode {
  constructor() { this.handlers = {}; this.style = {}; this.children = []; this.dataset = {}; this.textContent = ''; }
  addEventListener(name, handler) { this.handlers[name] = handler; }
  replaceChildren(...children) { this.children = children; }
  append(...children) { this.children.push(...children); }
  setAttribute() {}
}

test('failed backtest and cancellation report failure without claiming completion', async () => {
  const saved = { Node: globalThis.Node, document: globalThis.document, chrome: globalThis.chrome };
  const nodes = new Map();
  globalThis.Node = FakeNode;
  globalThis.document = { querySelector(selector) { if (!nodes.has(selector)) nodes.set(selector, new FakeNode()); return nodes.get(selector); }, createElement: () => new FakeNode() };
  globalThis.chrome = { runtime: { async sendMessage(message) { return { ok: false, error: `${message.command} fixture failure` }; } } };
  try {
    mountStrategies({});
    await nodes.get('#backtestRun').handlers.click();
    assert.equal(nodes.get('#backtestBar').style.width, '0%');
    assert.match(nodes.get('#backtestStatus').textContent, /Backtest failed/);
    assert.match(nodes.get('#backtestResults').children[0].textContent, /fixture failure/);
    await nodes.get('#backtestCancel').handlers.click();
    assert.match(nodes.get('#backtestStatus').textContent, /Cancel request failed.*fixture failure/);
    await new Promise(resolve => setImmediate(resolve));
  } finally { globalThis.Node = saved.Node; globalThis.document = saved.document; globalThis.chrome = saved.chrome; }
});
