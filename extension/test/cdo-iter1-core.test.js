import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { ConfigStore } from '../src/storage/store.js';
import { controlRoomTransitions, controlRoomSnapshot } from '../src/core/control-room.js';
import { intArray } from '../src/market/evm.js';
import { rpcBatch, rpcCall } from '../src/market/net.js';
import { normalisePool, rankPools, fetchPools } from '../src/market/pools.js';
import { isSolanaAddress } from '../src/market/tokens.js';
import { comparisonKey, runFromEnvelope } from '../src/ui/desk-model.js';
import { resultTables } from '../src/ui/workspace-model.js';
import { assertSoltuiCallAllowed } from '../e2e/lib/guard.mjs';
import { createLiveWindows } from '../src/bg/live-windows.js';

const response = value => new Response(JSON.stringify(value));

test('CDO-617f0c9a48 existing vault requires explicit typed replacement consent', async () => {
  let generated = 0;
  globalThis.__cdoKeyFactory = async () => { generated++; return { pubkeyBs58: 'new-public', vault: { synthetic: 'new' } }; };
  const url = new URL('../src/core/commands.js', import.meta.url);
  let source = await readFile(url, 'utf8');
  source = source.replace("import { createSessionKey } from '../wallet/signer.js';", 'const createSessionKey = (...args) => globalThis.__cdoKeyFactory(...args);');
  source = source.replace(/from '([^']+)'/g, (_, relative) => `from ${JSON.stringify(new URL(relative, url).href)}`);
  const { runCommand } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
  const configStore = new ConfigStore(null), store = new MemoryStore();
  const old = { pubkeyBs58: 'old-public', vault: { synthetic: 'old' } };
  await configStore.set('sessionKeyVault', old);
  const call = args => runCommand({ name: 'createSessionKey', deps: { store, configStore }, args: { passphrase: 'synthetic-passphrase', ...args } });
  try {
    await assert.rejects(call({}), /existing|replace/i);
    assert.deepEqual(await configStore.get('sessionKeyVault'), old);
    assert.equal(generated, 0);
    await assert.rejects(call({ replaceAcknowledged: 'true' }), /type/);
    await call({ replaceAcknowledged: true });
    assert.equal(generated, 1);
    assert.equal((await configStore.get('sessionKeyVault')).pubkeyBs58, 'new-public');
  } finally { delete globalThis.__cdoKeyFactory; }
});

test('CDO-9ffa4c6fac CDO-8dcafab778 persistent second outage notifies after cooldown', () => {
  let saved, result;
  for (const [state, now] of [['up', 0], ['down', 1000], ['up', 2000], ['down', 3000], ['down', 400000]]) {
    result = controlRoomTransitions({ helper: 'available', components: [{ name: 'manager', state }] }, saved, now);
    saved = result.state;
  }
  assert.equal(result.alerts.length, 1);
  assert.equal(controlRoomTransitions({ helper: 'available', components: [{ name: 'manager', state: 'down' }] }, saved, 400001).alerts.length, 0);
});

test('CDO-969a07cc66 CDO-ce14eb04b7 malformed helper components fail structurally', async () => {
  const value = await controlRoomSnapshot({ soltui: { request: async () => ({ ok: true, command: 'suite', error: null,
    result: { schema_version: 1, capability: 'control-room-v1', status: { state: 'up' }, health: { schema_version: 1, components: [null] } } }) } });
  assert.equal(value.state, 'unknown');
  assert.equal(value.helper, 'incompatible');
});

test('CDO-33f69ed540 ABI arrays reject unaligned and truncated payloads', () => {
  const word = n => BigInt(n).toString(16).padStart(64, '0');
  for (const values of [[1, 100], [32, 2, 100]]) assert.deepEqual(intArray('0x' + values.map(word).join('')), []);
  assert.deepEqual(intArray('0x' + [32, 1, 100].map(word).join('')), [100]);
});

test('CDO-8bfd1533c3 CDO-b484ce8a58 RPC evidence binds every expected response id', async () => {
  const seen = [], deps = { fetch: async url => { seen.push(url); return response(url.endsWith('bad') ? [] : [{ id: 0, result: '0x2105' }]); } };
  assert.deepEqual(await rpcBatch(deps, ['https://fixture/bad', 'https://fixture/good'], [['eth_chainId', []]]), ['0x2105']);
  assert.equal(seen.length, 2);
  await assert.rejects(rpcCall({ fetch: async () => response({ id: 999, result: 123 }) }, ['https://fixture'], 'getBalance', []));
});

test('CDO-be933deb06 CDO-970b24bace CDO-4ecb8aa49f pool measurements and feed shape remain explicit', async () => {
  for (const apy of [true, [], [1], {}]) assert.equal(normalisePool({ chain: 'Base', pool: 'bad', apy, tvlUsd: 1e6 }), null);
  assert.equal(normalisePool({ chain: 'Base', pool: 'valid', apy: '1', tvlUsd: 1e6 }).apy, 1);
  assert.equal(rankPools([{ id: 'spike', apy: 999, apyMean30d: null, tvlUsd: 1e6 }, { id: 'steady', apy: 20, apyMean30d: 20, tvlUsd: 1e6 }])[0].id, 'steady');
  await assert.rejects(fetchPools({ fetch: async () => response({ error: 'unavailable' }) }), /feed|response|data/i);
});

test('CDO-4a921da356 Solana address requires exactly 32 decoded bytes', () => {
  assert.equal(isSolanaAddress('1'.repeat(33)), false);
  assert.equal(isSolanaAddress('1'.repeat(32)), true);
});

test('CDO-d34afb85de store records are detached on every boundary', async () => {
  const s = new MemoryStore(), i = { intentKey: 'i', lots: [{ baseQty: .25 }] };
  await s.putIntent(i); i.lots[0].baseQty = 99;
  const got = await s.getIntent('i'); assert.equal(got.lots[0].baseQty, .25); got.lots[0].baseQty = 88;
  assert.equal((await s.getIntent('i')).lots[0].baseQty, .25);
  await s.logEvent({ type: 'original', summary: { count: 1 } });
  (await s.recentEvents())[0].summary.count = 99;
  assert.equal((await s.recentEvents())[0].summary.count, 1);
  assert.deepEqual(await s.recentEvents(0), []);
});

test('CDO-f443d75fca CDO-7bdf329412 incomplete provenance and malformed rows refuse', () => {
  assert.equal(comparisonKey({ data_sha256: 'data', strategy_revision: 'code', execution: {}, cpcv: {} }), null);
  for (const extra of [{ rows: [null] }, { rows: [], skipped: {} }, { rows: [], skipped: [null] }]) {
    assert.equal(runFromEnvelope({ ok: true, command: 'backtest.run', result: { context: { schema: 1, id: 'x' }, ...extra } }), null);
  }
});

test('CDO-299f0fa3b8 CDO-74f194abe7 nested tables preserve access and dictionary identity', () => {
  assert.equal(resultTables({ sections: Array.from({ length: 21 }, (_, i) => ({ source: String(i), rows: [{ timestamp: 1, price: i }] })) }).filter(t => t.path.endsWith('.rows')).length, 21);
  const row = resultTables({ accountA: { key: 'label', balance: 10 } })[0].rows[0];
  assert.ok(Object.values(row).includes('accountA'));
  assert.ok(Object.values(row).includes('label'));
});

test('CDO-584e87010c harness requires explicitly safe confirmation metadata', () => {
  for (const requires_confirm of [undefined, null, 'true', 0]) assert.throws(() => assertSoltuiCallAllowed('a.read', {}, [{ name: 'a.read', read_only: true, requires_confirm }]), /read-only/);
});

test('CDO-fd28606c1b conflicting cold window requests cannot acknowledge the wrong coin', async () => {
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  const broker = createLiveWindows({ runtime: { onConnect: { addListener() {} } }, windows: { create: () => gate }, getURL: path => path });
  const first = broker.open('SOL'), second = broker.open('BTC');
  release({ id: 1 });
  const results = await Promise.allSettled([first, second]);
  assert.equal(results[0].status, 'fulfilled');
  assert.equal(results[1].status, 'rejected');
});
