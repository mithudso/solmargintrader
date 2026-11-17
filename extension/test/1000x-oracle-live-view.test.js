import test from 'node:test';
import assert from 'node:assert/strict';
import { liveOracleView } from '../src/1000x/oracle-live-view.js';

class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.dataset = {}; this.style = {}; this.textContent = ''; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute(name, value) { this[name] = value; }
  remove() { this.removed = true; }
}
const find = (root, id) => root.id === id ? root : root.children.map(child => find(child, id)).find(Boolean);
const allText = root => [root.textContent, ...root.children.map(allText)].join(' ');
const row = (scores = { up: .81, down: .12, flat: .07 }) => ({ scores, samples: 2, issued: 4, resolved: 2, expired: 1, capacityDrops: 1, pending: 1, candidate: { hits: 1, brier: .8 }, uniform: { hits: 0, brier: 1.2 }, frequency: { hits: 1, brier: 1 } });
const horizons = r => Object.fromEntries([60, 300, 600, 900, 1200, 3600].map(h => [h, structuredClone(r)]));

test('fresh shared estimates show all strengths, observed windows and transition-only status', () => {
  const original = globalThis.document; globalThis.document = { createElement: tag => new Element(tag) };
  let now = 100000; const root = new Element('root'), ui = liveOracleView(root, { clock: () => now });
  try {
    const local = { market: 'SOL', source: 'feed', model: 'm', target: 't', asOfMs: now, status: 'learning', horizons: horizons(row()) };
    const shared = { source: 'feed', model: 'm', target: 't', as_of_ms: now, expires_at_ms: now + 2000, fresh: true, quote: { price: 123 }, horizons: horizons(row()) };
    shared.horizons[600].window = { direction: 'UP', start_ms: 80000, last_ms: 94000, peak: .87 };
    shared.horizons[600].history = [{ direction: 'DOWN', start_ms: 60000, end_ms: 70000, duration_ms: 10000, peak: .9, reason: 'side_flip' }];
    const view = { asset: 'SOL', selectedHorizon: 600, local, shared, localExpiresAtMs: 102000, status: 'ready' };
    ui.render(view);
    assert.match(find(root, 'live-oracle-primary').textContent, /↑ UP.*81\.0%.*learning n=2/);
    assert.equal(find(root, 'live-oracle-primary').dataset.direction, 'UP');
    assert.match(find(root, 'live-oracle-window').textContent, /14\.0s/);
    assert.doesNotMatch(find(root, 'live-oracle-window').textContent, /sustained/);
    assert.match(allText(find(root, 'live-oracle-evidence')), /reversed/);
    assert.match(allText(find(root, 'live-oracle-evidence')), /accuracy 50\.0%, Brier 0\.400/);
    assert.equal(find(root, 'live-oracle-horizons').children.length, 6);
    const announcement = find(root, 'live-oracle-announcement'); announcement.textContent = 'sentinel';
    shared.horizons[600].window.last_ms = 95000; now += 1000; ui.render(view);
    assert.match(find(root, 'live-oracle-window').textContent, /sustained 15s/);
    assert.equal(announcement.textContent, 'sentinel');
    now += 2000; ui.render(view);
    assert.match(find(root, 'live-oracle-status').textContent, /Historical/);
    assert.equal(find(root, 'live-oracle-primary').dataset.direction, 'FLAT');
    assert.match(find(root, 'live-oracle-window').textContent, /No current/);
    ui.close(); assert.equal(root.children[0].removed, true);
  } finally { globalThis.document = original; }
});

test('local fallback, neutral ties, warming, source change and malicious text remain honest', () => {
  const original = globalThis.document; globalThis.document = { createElement: tag => new Element(tag) };
  const root = new Element('root'), ui = liveOracleView(root, { clock: () => 100000 });
  try {
    const local = { market: 'SOL', source: 'feed', model: 'm', target: 't', asOfMs: 100000, status: 'learning', horizons: horizons(row({ up: .1, down: .6, flat: .3 })) };
    const base = { asset: 'SOL', selectedHorizon: 60, local, localExpiresAtMs: 102000, status: 'ready' };
    ui.render(base); assert.match(find(root, 'live-oracle-status').textContent, /This browser · sharing offline/);
    assert.equal(find(root, 'live-oracle-primary').dataset.direction, 'DOWN');
    local.horizons[60] = row({ up: .4, down: .4, flat: .2 }); ui.render(base);
    assert.match(find(root, 'live-oracle-primary').textContent, /NEUTRAL · tied/);
    assert.equal(find(root, 'live-oracle-primary').dataset.direction, 'FLAT');
    local.horizons[60].scores = null; local.status = 'warming'; ui.render(base);
    assert.match(find(root, 'live-oracle-primary').textContent, /no estimate yet/);
    ui.render({ ...base, asset: '<img onerror=attack>', status: 'source_changed' });
    assert.match(find(root, 'live-oracle-status').textContent, /Unavailable/);
    assert.doesNotMatch(find(root, 'live-oracle-primary').textContent, /40\.0%/);
    assert.equal(find(root, 'live-oracle-primary').dataset.direction, 'FLAT');
  } finally { globalThis.document = original; }
});


test('local quote expires at the source deadline without a controller update', () => {
  const original = globalThis.document; globalThis.document = { createElement: tag => new Element(tag) };
  let now = 101800; const root = new Element('root'), ui = liveOracleView(root, { clock: () => now });
  try {
    const local = { market: 'SOL', source: 'feed', model: 'm', target: 't', asOfMs: 101800, status: 'learning', horizons: horizons(row()) };
    const view = { asset: 'SOL', selectedHorizon: 60, local, localExpiresAtMs: 102000, status: 'ready' };
    ui.render(view);
    assert.equal(find(root, 'live-oracle-primary').dataset.direction, 'UP');
    now = 102000; ui.render(view);
    assert.equal(find(root, 'live-oracle-primary').dataset.direction, 'UP', 'deadline is inclusive');
    now = 102100; ui.render(view);
    assert.equal(find(root, 'live-oracle-primary').dataset.direction, 'FLAT');
    assert.match(find(root, 'live-oracle-primary').textContent, /Historical/);
    assert.match(find(root, 'live-oracle-status').textContent, /Historical/);
    assert.match(find(root, 'live-oracle-window').textContent, /No current/);
    delete view.localExpiresAtMs; now = 101800; ui.render(view);
    assert.equal(find(root, 'live-oracle-primary').dataset.direction, 'FLAT', 'missing deadline must fail closed');
  } finally { globalThis.document = original; }
});
