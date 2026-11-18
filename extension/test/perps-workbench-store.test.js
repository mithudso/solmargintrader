import test from 'node:test';
import assert from 'node:assert/strict';
import { FEATURE_NAMES } from '../src/1000x/oracle-model.js';
import { WORKBENCH_DB, causalEntryFeatures, openWorkbenchStore, paperMarketKey } from '../src/perps/workbench-store.js';

// Unit tests control the database commit or abort. Native locking and disk
// persistence are also exercised in Chrome using the same module.
function fakeIndexedDB() {
  const stores = new Map();
  let tail = Promise.resolve(), fail = false, version = 0;
  const keyString = key => JSON.stringify(key);
  const db = {
    createObjectStore(name, { keyPath }) {
      stores.set(name, { keyPath, records: new Map() });
      return { createIndex() {} };
    },
    close() {},
    transaction(_names, mode) {
      const pending = [], writes = [];
      let aborted = false;
      const tx = {
        abort() { aborted = true; },
        objectStore(name) {
          const { keyPath, records } = stores.get(name);
          const request = read => {
            const req = {};
            pending.push(() => { req.result = structuredClone(read()); req.onsuccess?.(); });
            return req;
          };
          const write = (row, add) => {
            const current = structuredClone(row);
            const id = keyString(Array.isArray(keyPath) ? keyPath.map(key => row[key]) : row[keyPath]);
            writes.push(() => {
              if (add && records.has(id)) throw new Error('duplicate key');
              records.set(id, current);
            });
          };
          return {
            get: key => request(() => records.get(keyString(key))),
            getAll: () => request(() => [...records.values()]),
            index: field => ({ getAll: key => request(() => [...records.values()].filter(row => row[field] === key)) }),
            put: row => write(row, false),
            add: row => write(row, true),
          };
        },
      };
      tail = tail.then(() => {
        while (pending.length && !aborted) pending.shift()();
        if (fail && mode === 'readwrite') { fail = false; aborted = true; }
        if (aborted) tx.onabort?.();
        else { for (const write of writes) write(); tx.oncomplete?.(); }
      });
      return tx;
    },
  };
  return {
    failNextWrite() { fail = true; },
    open(_name, requestedVersion) {
      const req = { result: db };
      queueMicrotask(() => {
        if (version < requestedVersion) {
          req.onupgradeneeded({ oldVersion: version });
          version = requestedVersion;
        }
        req.onsuccess();
      });
      return req;
    },
  };
}

const zec = paperMarketKey('GUM', 'ZEC');
const sol = paperMarketKey('JLP', 'SOL');
const features = Object.freeze(FEATURE_NAMES.map(() => 0.1));
const fill = (id, override = {}) => ({ id, time: 600, openedAt: 300, direction: 1, pnl: 2,
  strategy: 'volty', step: 300, features: [...features], ...override });
const settlement = trade => current => ({
  account: { equity: (current?.equity ?? 1000) + trade.pnl },
  trades: [trade],
});

test('serialized accounts share exactly one journal and model commit per market fill', async () => {
  const db = fakeIndexedDB();
  const [one, two] = await Promise.all([openWorkbenchStore(db), openWorkbenchStore(db)]);
  const trade = fill('abc-1');
  const changed = await Promise.all([one.update(zec, settlement(trade)), two.update(zec, settlement(trade))]);
  assert.deepEqual(changed.map(result => result.changed), [true, false]);
  assert.deepEqual(await two.getAccounts(), [{ key: zec, account: { equity: 1002 } }]);
  const trained = (await two.exportTrades()).trades;
  assert.equal(trained.length, 1);
  assert.equal(trained[0].learning.status, 'trained');
  assert.equal(trained[0].learning.probabilityBeforeUpdate, 0.5);
  assert.equal(trained[0].learning.samplesBefore, 0);
  assert.equal((await one.metrics(zec))[0].samples, 1);
  await assert.rejects(one.update(zec, settlement(fill('abc-1', { pnl: 100 }))), /Conflicting/);
  assert.equal((await one.getAccounts())[0].account.equity, 1002);
  one.close();
  two.close();
});

test('aborted disk settlement preserves position accounting, journal and model', async () => {
  const db = fakeIndexedDB();
  const store = await openWorkbenchStore(db);
  const start = { equity: 1000, position: { id: 'risk-1' } };
  await store.update(zec, () => ({ account: start, trades: [] }));
  db.failNextWrite();
  await assert.rejects(store.update(zec, settlement(fill('risk-1'))), /storage transaction failed/);
  assert.deepEqual(await store.getAccounts(), [{ key: zec, account: start }]);
  assert.deepEqual(await store.metrics(zec), []);
  assert.deepEqual((await store.exportTrades()).trades, []);
  await assert.rejects(store.update(zec, async () => ({ account: start, trades: [] })), /synchronously/);
  store.close();
});

test('markets, sides and strategy cadence stay separate. Reports expose training gaps.', async () => {
  const store = await openWorkbenchStore(fakeIndexedDB());
  await store.update(zec, settlement(fill('abc-1')));
  await store.update(zec, settlement(fill('abc-2', { direction: -1, pnl: -2 })));
  await store.update(zec, settlement(fill('abc-3', { step: 600, features: null })));
  await store.update(sol, settlement(fill('abc-1', { pnl: 0 })));
  const metrics = await store.metrics(zec);
  assert.deepEqual(metrics.map(row => [row.direction, row.step, row.samples, row.untrained, row.positive]),
    [[1, 300, 1, 0, 1], [-1, 300, 1, 0, 0], [1, 600, 0, 1, 0]]);
  const source = await store.exportTrades();
  assert.equal(source.mode, 'paper');
  assert.equal(source.trades.length, 4);
  assert.equal(source.trades.find(row => row.id === 'abc-3').learning.status, 'missing-entry-features');
  assert.equal((await store.metrics(sol))[0].positive, 0);
  assert.deepEqual(await store.predict(zec, { direction: 1, strategy: 'volty', step: 300, features }),
    { status: 'warming-up', samples: 1, minimumSamples: 20, probability: null });
  for (let i = 0; i < 19; i++) await store.update(zec, settlement(fill('proof-' + i)));
  const prediction = await store.predict(zec, { direction: 1, strategy: 'volty', step: 300, features });
  assert.equal(prediction.status, 'ready');
  assert.equal(prediction.samples, 20);
  assert.ok(prediction.probability > 0.5);
  store.close();
});

test('entry features use only complete, contiguous minutes through the entry time', () => {
  const rows = Array.from({ length: 100 }, (_, i) => {
    const price = 100 + i / 4 + Math.sin(i);
    return { time: 60 * i, open: price, high: price + 1, low: price - 1, close: price };
  });
  const at = 6000.5;
  const snapshot = causalEntryFeatures(rows, at);
  assert.equal(snapshot.length, FEATURE_NAMES.length);
  assert.deepEqual(causalEntryFeatures([...rows, { time: 6000, open: 999, high: 999, low: 999, close: 999 }], at), snapshot);
  assert.equal(causalEntryFeatures(rows.slice(0, -1), at), null);
  assert.equal(causalEntryFeatures(rows.map((row, i) => i === 82 ? { ...row, gapBefore: true } : row), at), null);
  assert.equal(causalEntryFeatures(rows.map((row, i) => i === 99 ? { ...row, closed: false } : row), at), null);
  assert.equal(causalEntryFeatures(rows.map((row, i) => i === 95 ? { ...row, high: NaN } : row), at), null);
});

const base = 1_800_000_000;
const history = Array.from({ length: 105 }, (_, i) => {
  const price = 100 + i / 2;
  return { time: base + 60 * i, open: price, high: price + 0.4, low: price - 0.2, close: price + 0.3 };
});
const clock = minute => (base + minute * 60 + 2) * 1000;
const markAt = minute => ({ time: clock(minute) / 1000, price: 101 });
const minute = view => view.horizons.find(horizon => horizon.seconds === 60);

test('prospective candle feedback uses only complete fresh labels and trains once across tabs', async () => {
  const db = fakeIndexedDB();
  const [one, two] = await Promise.all([openWorkbenchStore(db), openWorkbenchStore(db)]);
  const initial = await one.advanceCandleModel(zec, history, markAt(100), clock(100));
  assert.deepEqual(initial.horizons.map(horizon => horizon.seconds), [60, 300, 600, 900, 1200, 3600]);
  assert.ok(initial.horizons.every(horizon => horizon.samples === 0 && horizon.issue.probability === 0.5));
  assert.equal(minute(initial).issue.cutoff, base + 100 * 60);
  assert.equal(minute(initial).issue.reference, history[99].close);
  const stale = await two.advanceCandleModel(zec, history, markAt(100), clock(101));
  assert.equal(stale.eligible, false);
  assert.equal(minute(stale).issue, null);
  assert.equal(minute(stale).samples, 0);
  const [settled, duplicate] = await Promise.all([one, two].map(store =>
    store.advanceCandleModel(zec, history, markAt(101), clock(101))));
  for (const result of [settled, duplicate]) {
    assert.equal(minute(result).samples, 1);
    assert.equal(minute(result).brier, 0.25);
    assert.equal(result.horizons.find(horizon => horizon.seconds === 300).samples, 0);
  }
  const otherMarket = await two.advanceCandleModel(sol, history, markAt(101), clock(101));
  assert.ok(otherMarket.horizons.every(horizon => horizon.samples === 0));
  assert.deepEqual(await one.metrics(zec), []);
  assert.deepEqual((await one.exportTrades()).trades, []);
  one.close();
  two.close();
});

test('missing label minutes expire. Adding the candle store preserves prior version-one accounts.', async () => {
  const db = fakeIndexedDB();
  await new Promise(resolve => {
    const request = db.open(WORKBENCH_DB, 1);
    request.onupgradeneeded = () => {
      request.result.createObjectStore('accounts', { keyPath: 'key' });
      request.result.createObjectStore('journal', { keyPath: ['key', 'id'] });
      request.result.createObjectStore('models', { keyPath: 'id' }).createIndex('key', 'key');
    };
    request.onsuccess = () => {
      const tx = request.result.transaction(['accounts'], 'readwrite');
      tx.objectStore('accounts').put({ key: zec, account: { equity: 987 } });
      tx.oncomplete = resolve;
    };
  });
  const store = await openWorkbenchStore(db);
  await store.advanceCandleModel(zec, history, markAt(100), clock(100));
  const missing = history.filter(row => row.time !== base + 100 * 60);
  const unavailable = await store.advanceCandleModel(zec, missing, markAt(101), clock(101));
  assert.equal(unavailable.status, 'waiting-for-complete-history');
  assert.equal(minute(unavailable).samples, 0);
  const expired = await store.advanceCandleModel(zec, history, markAt(103), clock(103));
  assert.equal(minute(expired).expired, 1);
  assert.equal(minute(expired).samples, 0);
  assert.deepEqual(await store.getAccounts(), [{ key: zec, account: { equity: 987 } }]);
  store.close();
});
