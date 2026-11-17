import test from 'node:test';
import assert from 'node:assert/strict';
import { OracleController } from '../src/1000x/oracle-controller.js';
import { oracleInput, transitionOracle } from '../src/1000x/oracle-model.js';
import { oracleView } from '../src/1000x/oracle-view.js';
import { TIMEFRAMES } from '../src/1000x/feed.js';

class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.dataset = {}; this.textContent = ''; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute(name, value) { this[name] = value; }
  removeAttribute(name) { delete this[name]; }
}
const base = 1_800_000_000;
const rows = Array.from({ length: 1400 }, (_, i) => ({ time: base + i * 60, open: 100 + i / 100,
  high: 100.02 + i / 100, low: 99.99 + i / 100, close: 100.01 + i / 100, closed: true }));
const snapshot = now => ({ symbol: 'SOL', sourceIdentity: { symbol: 'SOL', feedId: 6,
  marketAddress: 'Ew8sRjpuBttpmhSUeaAn4dLAegWnz55AuafVcGuojCPS', stream: 'fixed_rate@200ms', kind: 'oracle-ohlc' },
  status: 'live', minuteStatus: 'ready', minuteCandles: rows, quote: { price: 110, exchangeMs: now, receivedMs: now } });
const settle = async () => { for (let i = 0; i < 80; i++) await Promise.resolve(); };

test('same-source stale input cannot be reactivated by any older committed completion; actual view retains honest historical metrics', async () => {
  const savedDocument = globalThis.document;
  globalThis.document = { createElement: tag => new Element(tag) };
  const root = new Element('root'), render = oracleView(root), views = [], states = new Map();
  const find = id => { const seek = x => x.id === id ? x : x.children.map(seek).find(Boolean); return seek(root); };
  let now;
  for (const t of TIMEFRAMES) {
    let state;
    for (let minute = 1000; minute <= 1080; minute++) {
      now = (base + minute * 60) * 1000 + 2000;
      state = transitionOracle(state, oracleInput(snapshot(now), now, t.seconds)).state;
    }
    states.set(state.key, state);
  }
  now += 60_000;
  const releases = [];
  const store = { update(key, reduce) {
    const result = reduce(structuredClone(states.get(key) || null));
    if (result.changed) states.set(key, structuredClone(result.state));
    return new Promise(resolve => releases.push(() => resolve(structuredClone(result))));
  }, close() {} };
  const c = new OracleController({ store, clock: () => now, onChange: view => { views.push(view); render(view); } });
  try {
    c.observe(snapshot(now)); await settle();
    assert.ok(releases.length); c.observe({ ...snapshot(now), status: 'stale', error: 'stream_disconnected' });
    releases.splice(0).forEach(release => release()); await settle();
    assert.equal(views.at(-1).inputReady, false, 'older live completion must consult latest same-source eligibility');
    assert.equal(root.dataset.state, 'waiting');
    assert.match(find('oracle-prediction').textContent, /Historical stored/);
    assert.doesNotMatch(find('oracle-status').textContent, /candidate active/);
    assert.match(find('oracle-counts').textContent, /^Historical/);
    assert.match(find('oracle-metrics').children.find(x => x.tag === 'caption').textContent, /^Historical/);
    assert.ok(Number(find('oracle-counts').dataset.trained) >= 20);
    assert.equal(find('oracle-metrics').children.find(x => x.tag === 'tbody').children.length, 6);
    for (const view of Object.values(views.at(-1).horizons || {})) assert.equal(view.inputReady, false);
    now += 1000; c.observe(snapshot(now)); await settle();
    releases.splice(0).forEach(release => release()); await settle();
    assert.equal(views.at(-1).inputReady, true);
    assert.doesNotMatch(find('oracle-counts').textContent, /^Historical/);
    assert.doesNotMatch(find('oracle-metrics').children.find(x => x.tag === 'caption').textContent, /^Historical/);
  } finally { c.stop(); globalThis.document = savedDocument; }
});
