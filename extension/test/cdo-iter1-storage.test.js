import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { FileStore } from '../src/storage/fileStore.js';
import { Store } from '../src/storage/store.js';
import { createNodeDeps } from '../tools/deps.js';
import { importSource, sourceText } from './helpers/import-source.js';

test('CDO-c808500bbb journal acknowledgment requires file and directory fsync', async () => {
  const source = await sourceText('src/storage/fileStore.js');
  const imported = source.match(/import \{[^\n]+\} from 'node:fs\/promises';/)[0];
  const calls = []; let failFileSync = false;
  globalThis.__durableFS = {
    realpath: async path => path, lstat: async () => ({ isFile: () => true, nlink: 1 }),
    mkdir: async () => {}, unlink: async () => {}, rename: async () => calls.push('rename'),
    writeFile: async () => calls.push('unsynced-write'),
    open: async (_path, mode) => mode === 'r' ? { sync: async () => calls.push('directory-sync'), close: async () => {} }
      : { writeFile: async () => calls.push('write'), sync: async () => { calls.push('file-sync'); if (failFileSync) throw new Error('synthetic fsync failure'); }, close: async () => calls.push('close') },
  };
  try {
    const { writeJsonAtomic } = await importSource('src/storage/fileStore.js', { replace: [[imported, `const ${imported.slice(7, imported.indexOf(' from'))} = globalThis.__durableFS;`]], append: 'export {writeJsonAtomic};' });
    await writeJsonAtomic('/owned-fixture/journal.json', {});
    assert.deepEqual(calls, ['write', 'file-sync', 'close', 'rename', 'directory-sync']);
    calls.length = 0; failFileSync = true;
    await assert.rejects(writeJsonAtomic('/owned-fixture/journal.json', {}), /fsync/);
    assert.ok(!calls.includes('rename'));
  } finally { delete globalThis.__durableFS; }
});

test('CDO-dee3bdfdc3 concurrent file writers preserve every acknowledged record or refuse busy', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'smt-owned-journal-'));
  try {
    const path = join(dir, 'journal.json'), a = await FileStore.open(path), b = await FileStore.open(path);
    const results = await Promise.allSettled([a.putIntent({ intentKey: 'a' }), b.putIntent({ intentKey: 'b' })]);
    const saved = await a.allIntents();
    for (let i = 0; i < results.length; i++) if (results[i].status === 'fulfilled') assert.ok(saved.some(x => x.intentKey === ['a', 'b'][i]));
    assert.ok(results.some(x => x.status === 'fulfilled'));
    for (const r of results.filter(x => x.status === 'rejected')) assert.match(r.reason.message, /busy|lock|owner/i);
  } finally { await rm(dir, { recursive: true, force: true }); }
});

test('CDO-7025aa9f47 Node paper orders survive dependency recreation without native calls', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'smt-owned-paper-'));
  try {
    const opts = { storePath: join(dir, 'journal.json'), configPath: join(dir, 'config.json'), quiet: true,
      soltui: { request() { throw new Error('Native transport forbidden'); } } };
    const a = await createNodeDeps(opts), first = await a.buildVenue();
    const placed = await first.placeOrder({ intent: { intentKey: 'paper', side: 'buy', level: 100, baseQty: 1 }, slippageBps: 0, ttlMs: 60000 });
    const b = await createNodeDeps(opts), second = await b.buildVenue();
    assert.deepEqual((await second.getOpenOrders()).map(o => o.venueOrderId), [placed.venueOrderId]);
    second.markPrice(99);
    assert.equal((await second.getFills()).length, 1);
    assert.equal(JSON.parse(await readFile(opts.configPath, 'utf8')).config?.mode ?? 'dry-run', 'dry-run');
  } finally { await rm(dir, { recursive: true, force: true }); }
});

test('CDO-5328e664b4 IndexedDB request success cannot acknowledge an uncommitted intent', async () => {
  let transaction;
  const store = new Store({ transaction() { transaction = { objectStore: () => ({ put: () => ({ result: 'request-success' }) }) }; return transaction; } });
  let settled = false;
  const pending = store.putIntent({ intentKey: 'submitting' });
  pending.finally(() => { settled = true; }).catch(() => {});
  await Promise.resolve();
  assert.equal(settled, false);
  transaction.onabort();
  await assert.rejects(pending, /abort/);
});

test('CDO-b78478b4c1 CDO-671273b356 event reads stop at the requested count', async () => {
  const values = Array.from({ length: 10000 }, (_, i) => ({ id: i }));
  let visits = 0, fullScans = 0;
  const store = new Store({ transaction() { return { objectStore() { return {
    getAll() { fullScans++; const request = {}; queueMicrotask(() => { request.result = values; request.onsuccess(); }); return request; },
    openCursor(_range, direction) {
      assert.equal(direction, 'prev');
      const request = {}; let index = values.length - 1;
      const advance = () => queueMicrotask(() => { visits++; request.result = index < 0 ? null : { value: values[index--], continue: advance }; request.onsuccess(); });
      advance(); return request;
    },
  }; } }; } });
  assert.deepEqual(await store.recentEvents(0), []);
  assert.equal(visits, 0); assert.equal(fullScans, 0);
  assert.deepEqual((await store.recentEvents(2)).map(x => x.id), [9999, 9998]);
  assert.equal(visits, 2); assert.equal(fullScans, 0);
});
