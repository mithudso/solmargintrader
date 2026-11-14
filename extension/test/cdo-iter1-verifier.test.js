import test from 'node:test';
import assert from 'node:assert/strict';
import { importSource } from './helpers/import-source.js';
import { DEFAULT_CONFIG } from '../src/storage/store.js';
const tool = suffix => importSource('tools/verify-endpoints.js', { replace: [['const apiKey = process.env.JUPITER_API_KEY;', 'const apiKey = null;']],
  tail: 'async function main()', append: `export { checkPrice, checkTriggerReachable }; export const failuresNow = () => failures; // ${suffix}` });
async function fixture(fn) {
  const saved = globalThis.fetch, log = console.log;
  console.log = () => {};
  try { return await fn(); } finally { globalThis.fetch = saved; console.log = log; }
}
test('CDO-46368a62b2 supported wrapped prices use the same decimals table', () => fixture(async () => {
  const t = await tool('wrapped');
  globalThis.fetch = async () => new Response(JSON.stringify({ data: { [DEFAULT_CONFIG.baseMint]: { usdPrice: 100, decimals: 9 }, [DEFAULT_CONFIG.quoteMint]: { usdPrice: 1, decimals: 6 } } }));
  await t.checkPrice('https://fixture', 'fixture', null);
  assert.equal(t.failuresNow(), 0);
}));
test('CDO-95350b27e7 verifier requires every requested price', () => fixture(async () => {
  const t = await tool('missing');
  globalThis.fetch = async () => new Response(JSON.stringify({ [DEFAULT_CONFIG.baseMint]: { usdPrice: 100, decimals: 9 } }));
  await t.checkPrice('https://fixture', 'fixture', null);
  assert.ok(t.failuresNow() > 0);
}));
test('CDO-f625ddd675 server failure is not route readiness', () => fixture(async () => {
  const t = await tool('status');
  globalThis.fetch = async () => new Response('', { status: 503 });
  await t.checkTriggerReachable();
  assert.ok(t.failuresNow() > 0);
}));
test('CDO-f58546c089 an uncooperative body cannot hang the verifier', () => fixture(async () => {
  const t = await tool('deadline'), timer = globalThis.setTimeout, clear = globalThis.clearTimeout;
  globalThis.fetch = async () => ({ ok: true, status: 200, json: () => new Promise(() => {}) });
  globalThis.setTimeout = callback => { queueMicrotask(callback); return 0; };
  globalThis.clearTimeout = () => {};
  try {
    const result = await Promise.race([t.checkPrice('https://fixture', 'fixture', null).then(() => 'done'), new Promise(r => timer(() => r('hung'), 25))]);
    assert.equal(result, 'done'); assert.ok(t.failuresNow() > 0);
  } finally { globalThis.setTimeout = timer; globalThis.clearTimeout = clear; }
}));
