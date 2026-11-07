import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, access } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { toLineData, renderEquityChart, disposeChart } from '../src/ui/charts.js';

const VENDOR = fileURLToPath(new URL('../vendor/lightweight-charts/', import.meta.url));

test('toLineData converts ms to ascending integer seconds', () => {
  const out = toLineData([
    { tsMs: 3_000, equityUsd: 3 },
    { tsMs: 1_000, equityUsd: 1 },
    { tsMs: 2_500, equityUsd: 2 },
  ]);
  assert.deepEqual(out, [
    { time: 1, value: 1 },
    { time: 2, value: 2 },
    { time: 3, value: 3 },
  ]);
});

test('toLineData keeps the last equity reached within one second', () => {
  // The library rejects duplicate times; the curve's value at that second is the last close.
  const out = toLineData([
    { tsMs: 5_100, equityUsd: 10 },
    { tsMs: 5_900, equityUsd: 12 },
  ]);
  assert.deepEqual(out, [{ time: 5, value: 12 }]);
});

test('toLineData drops non-finite points instead of drawing them as zero', () => {
  const out = toLineData([
    { tsMs: 1_000, equityUsd: 1 },
    { tsMs: 2_000, equityUsd: NaN },
    { tsMs: Number.NaN, equityUsd: 5 },
    null,
    { tsMs: 3_000, equityUsd: -2 },
  ]);
  assert.deepEqual(out, [
    { time: 1, value: 1 },
    { time: 3, value: -2 },
  ]);
  assert.deepEqual(toLineData(undefined), []);
});

test('toLineData drops null and empty-string fields (Number(null) is 0)', () => {
  const out = toLineData([
    { tsMs: null, equityUsd: 5 },
    { tsMs: 1_000, equityUsd: null },
    { tsMs: '', equityUsd: 1 },
    { tsMs: 2_000, equityUsd: 7 },
    { tsMs: 3_000, equityUsd: 8 },
  ]);
  assert.deepEqual(out, [
    { time: 2, value: 7 },
    { time: 3, value: 8 },
  ]);
});

/* -------------------------------------------- render lifecycle (no browser) -- */

// Minimal DOM and library stand-ins: node has neither, and the real library is
// exercised in a real MV3 page by `npm run e2e`.
function fakeElement() {
  const attrs = {};
  return {
    innerHTML: '',
    children: [],
    style: {},
    append(...nodes) { this.children.push(...nodes); },
    setAttribute(k, v) { attrs[k] = v; },
    getAttribute(k) { return attrs[k] ?? null; },
  };
}
function fakeLib() {
  const calls = { createChart: 0, setData: 0, removed: 0 };
  return {
    calls,
    LineSeries: 'line',
    createChart() {
      calls.createChart += 1;
      return {
        addSeries: () => ({ applyOptions() {}, setData() { calls.setData += 1; } }),
        timeScale: () => ({ fitContent() {} }),
        remove() { calls.removed += 1; },
      };
    },
  };
}
const POINTS = [
  { tsMs: 1_000, equityUsd: 100 },
  { tsMs: 2_000, equityUsd: 101 },
];
globalThis.document ??= { createElement: () => fakeElement() };

test('renderEquityChart falls back below two points and never loads the library', async () => {
  const el = fakeElement();
  let loads = 0;
  const out = await renderEquityChart(el, POINTS.slice(0, 1), {
    label: 'x', fallbackHtml: () => '<p>svg</p>', loadLib: async () => { loads += 1; return fakeLib(); },
  });
  assert.equal(out, 'fallback');
  assert.equal(el.innerHTML, '<p>svg</p>');
  assert.equal(loads, 0);
});

test('renderEquityChart falls back to the SVG when the library fails to load', async () => {
  const el = fakeElement();
  const out = await renderEquityChart(el, POINTS, {
    label: 'x', fallbackHtml: () => '<p>svg</p>', loadLib: async () => { throw new Error('blocked'); },
  });
  assert.equal(out, 'fallback');
  assert.equal(el.innerHTML, '<p>svg</p>');
});

test('repeated renders reuse one chart, and dispose removes it', async () => {
  const el = fakeElement();
  const lib = fakeLib();
  const opts = { label: 'equity', fallbackHtml: () => 'svg', loadLib: async () => lib };
  assert.equal(await renderEquityChart(el, POINTS, opts), 'lightweight-charts');
  assert.equal(await renderEquityChart(el, POINTS, opts), 'lightweight-charts');
  assert.deepEqual([lib.calls.createChart, lib.calls.setData], [1, 2]);
  assert.equal(el.getAttribute('aria-label'), 'equity');
  disposeChart(el);
  assert.equal(lib.calls.removed, 1);
});

test('a draw superseded while the library loads does not overwrite the newer render', async () => {
  const el = fakeElement();
  const lib = fakeLib();
  let release;
  const slow = new Promise((r) => { release = r; });
  const pending = renderEquityChart(el, POINTS, { label: 'old', fallbackHtml: () => 'svg', loadLib: () => slow });
  // renderPnl's sync branch (no fills): dispose, then write its note.
  disposeChart(el);
  el.innerHTML = '<p>No fills yet.</p>';
  release(lib);
  assert.equal(await pending, 'stale');
  assert.equal(el.innerHTML, '<p>No fills yet.</p>');
  assert.equal(lib.calls.createChart, 0);
});

test('vendored Lightweight Charts is the pinned 5.2.1 build', async () => {
  // A changed byte means an unreviewed library update; MV3 runs this code with page privileges.
  const bytes = await readFile(`${VENDOR}lightweight-charts.standalone.production.mjs`);
  const sha = createHash('sha256').update(bytes).digest('hex');
  assert.equal(sha, '1bb1ee79f9d4dd17261b53d930f7a8995748276f80e7ba0e24412b5068062f5f');
});

test('vendored library ships its licence and attribution notice', async () => {
  await access(`${VENDOR}LICENSE`);
  const notice = await readFile(`${VENDOR}NOTICE`, 'utf8');
  assert.match(notice, /TradingView Lightweight Charts/);
  assert.match(notice, /https:\/\/www\.tradingview\.com\//);
});
