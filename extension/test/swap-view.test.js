import test from 'node:test';
import assert from 'node:assert/strict';
import { mountSwap } from '../src/ui/view-trade.js';

class Element {
  constructor(value = '') { this.value = value; this.hidden = false; this.textContent = ''; this.listeners = new Map(); }
  addEventListener(name, handler) { this.listeners.set(name, handler); }
  emit(name) { return this.listeners.get(name)?.({ preventDefault() {} }); }
  replaceChildren(...children) { this.children = children; }
  append(...children) { (this.children ??= []).push(...children); }
  setAttribute() {}
}

const quote = value => ({ chain: 'base', venue: 'fixture', from: { symbol: 'ETH', amount: 1 },
  to: { symbol: 'USDC', amount: value }, minOut: value - 1, priceImpactPct: 0,
  feePct: 0.3, route: ['ETH', 'USDC'], caveats: [], handoffUrl: 'https://example.invalid/review' });

test('a delayed swap quote or failure cannot replace the result for the current form', async () => {
  const previous = { document: globalThis.document, Node: globalThis.Node, chrome: globalThis.chrome };
  const nodes = new Map();
  for (const id of ['swapForm', 'swapQuote', 'swapError', 'swapBalance', 'swapFlip', 'swapVenue', 'swapDetails', 'swapCaveats', 'swapHandoff']) nodes.set(`#${id}`, new Element());
  const form = nodes.get('#swapForm');
  form.elements = Object.fromEntries(Object.entries({ from: 'ETH', to: 'USDC', amount: '1', slippageBps: '50', out: '' }).map(([key, value]) => [key, new Element(value)]));
  form.querySelectorAll = () => [];
  const requests = [];
  globalThis.Node = Element;
  globalThis.document = { querySelector: id => nodes.get(id), createElement: () => new Element() };
  globalThis.chrome = { runtime: { sendMessage: request => new Promise((resolve, reject) => requests.push({ request, resolve, reject })) } };
  try {
    mountSwap({});
    const old = form.emit('submit');
    form.elements.amount.value = '2';
    form.elements.amount.emit('input');
    requests[0].resolve({ ok: true, result: quote(100) });
    await old;
    assert.equal(nodes.get('#swapQuote').hidden, true, 'changing the form must invalidate its pending quote and handoff');
    assert.equal(form.elements.out.value, '');

    const obsoleteFailure = form.emit('submit');
    form.elements.amount.value = '3';
    form.elements.amount.emit('input');
    const current = form.emit('submit');
    requests[2].resolve({ ok: true, result: quote(300) });
    await current;
    assert.equal(nodes.get('#swapQuote').hidden, false);
    assert.equal(form.elements.out.value, '300');
    requests[1].reject(new Error('obsolete fixture failure'));
    await obsoleteFailure;
    assert.equal(nodes.get('#swapQuote').hidden, false);
    assert.equal(form.elements.out.value, '300');
    assert.equal(nodes.get('#swapError').textContent, '');
  } finally {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete globalThis[key]; else globalThis[key] = value;
    }
  }
});
