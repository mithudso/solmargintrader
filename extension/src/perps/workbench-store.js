/** Local paper state, immutable fills and online learning share one IndexedDB commit. */
import { FEATURE_NAMES, ORACLE, learn, probability, score } from '../1000x/oracle-model.js';
import { advanceCandlePartition, finiteEpoch, prepareCandleModel, requirePaperMarket } from './candle-learning.js';

export { causalEntryFeatures, paperMarketKey } from './candle-learning.js';

export const WORKBENCH_DB = 'solmargintrader-perps-workbench';
const SCHEMA = 1;
const DB_VERSION = 2;
const STORES = ['accounts', 'journal', 'models'];
const CANDLE_STORE = 'candle-models';
const TARGET = 'positive-realized-net-pnl-v1';
const object = value => value && typeof value === 'object' && !Array.isArray(value);
const validFeatures = values => Array.isArray(values) && values.length === FEATURE_NAMES.length
  && values.every(value => Number.isFinite(value) && Math.abs(value) <= 1);

function normalizeTrade(input) {
  if (!object(input) || typeof input.id !== 'string' || !/^[A-Za-z0-9_.:-]{1,128}$/.test(input.id)
    || !finiteEpoch(input.time) || !finiteEpoch(input.openedAt) || input.time < input.openedAt
    || ![1, -1].includes(input.direction) || !Number.isFinite(input.pnl)) throw new Error('Invalid paper settlement.');
  const { id, time, openedAt, direction, pnl, strategy = 'manual', step = 60, features = null, reason } = input;
  if (!validPartitionScope(direction, strategy, step) || (features !== null && !validFeatures(features))
    || (reason !== undefined && (typeof reason !== 'string' || !/^[a-z][a-z0-9-]{0,63}$/.test(reason)))) {
    throw new Error('Invalid paper learning evidence.');
  }
  // Persist only known paper fields. Extra execution or wallet metadata is never journaled.
  const trade = { id, time, openedAt, direction, pnl, strategy, step, features };
  if (reason !== undefined) trade.reason = reason;
  for (const key of ['entry', 'price', 'units', 'size', 'deposit', 'carry', 'openCost', 'closeCost']) {
    if (input[key] === undefined) continue;
    if (!Number.isFinite(input[key]) || (key !== 'carry' && input[key] < 0)) throw new Error('Invalid paper settlement amount.');
    trade[key] = input[key];
  }
  return trade;
}

function validPartitionScope(direction, strategy, step) {
  return [1, -1].includes(direction) && typeof strategy === 'string' && /^[A-Za-z0-9_.:-]{1,96}$/.test(strategy)
    && Number.isSafeInteger(step) && step >= 60 && step % 60 === 0 && step <= 86400;
}

function modelId(key, { direction, strategy, step }) {
  return JSON.stringify([SCHEMA, key, direction, strategy, step, ORACLE.model, ORACLE.features, TARGET]);
}

function newModel(key, trade) {
  const { direction, strategy, step } = trade;
  return { id: modelId(key, trade), key, direction, strategy, step, model: { weights: FEATURE_NAMES.map(() => 0), bias: 0, n: 0 },
    hits: 0, brier: 0, logLoss: 0, untrained: 0, positive: 0 };
}

function train(model, trade) {
  if (!trade.features) {
    model.untrained++;
    return { status: 'missing-entry-features' };
  }
  const outcome = Number(trade.pnl > 0);
  const before = probability(model.model, trade.features);
  const totals = score(before, outcome);
  const samplesBefore = model.model.n;
  model.model = learn(model.model, trade.features, outcome);
  model.positive += outcome;
  model.hits += totals.hit;
  model.brier += totals.brier;
  model.logLoss += totals.logLoss;
  return { status: 'trained', outcome, probabilityBeforeUpdate: before, samplesBefore, ...totals };
}

function summarize({ key, direction, strategy, step, model, hits, brier, logLoss, untrained, positive }) {
  const samples = model.n;
  return { key, direction, strategy, step, samples, untrained, positive, minimumSamples: ORACLE.minTrained,
    status: samples >= ORACLE.minTrained ? 'ready' : 'warming-up',
    accuracy: samples ? hits / samples : null, brier: samples ? brier / samples : null,
    logLoss: samples ? logLoss / samples : null };
}

function transaction(db, names, mode, run) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(names, mode, mode === 'readwrite' ? { durability: 'strict' } : undefined);
    let result, failure;
    const finish = value => { result = value; };
    const guard = action => (...args) => {
      try { action(...args); }
      catch (error) { failure = error; tx.abort(); }
    };
    tx.oncomplete = () => resolve(result);
    tx.onabort = () => reject(failure ?? tx.error ?? new Error('Paper storage transaction failed.'));
    guard(run)(name => tx.objectStore(name), finish, guard);
  });
}

// Native requests keep an IndexedDB transaction active through each callback.
// A reducer cannot await, issue a network call, or rely on uncommitted local state.
function read(requests, receive) {
  let left = requests.length;
  if (!left) receive([]);
  for (const request of requests) {
    request.onsuccess = () => {
      if (--left === 0) receive(requests.map(item => item.result));
    };
  }
}

function flatten(record) {
  return { ...record.trade, key: record.key, learning: record.learning };
}

function update(db, key, reduce) {
  requirePaperMarket(key);
  if (typeof reduce !== 'function') throw new TypeError('A synchronous paper reducer is required.');
  return transaction(db, STORES, 'readwrite', (store, finish, guard) => {
    read([store('accounts').get(key)], guard(([older]) => {
      const current = older?.account ?? null;
      const proposed = reduce(structuredClone(current));
      if (proposed === null) { finish({ account: current, trades: [], changed: false }); return; }
      if (!object(proposed) || typeof proposed.then === 'function' || !object(proposed.account) || !Array.isArray(proposed.trades)) {
        throw new TypeError('A paper reducer must synchronously return an account and trades, or null.');
      }
      const account = proposed.account;
      const batch = proposed.trades.map(normalizeTrade);
      if (new Set(batch.map(trade => trade.id)).size !== batch.length) throw new Error('A paper settlement ID was reused.');
      const journal = store('journal');
      read(batch.map(trade => journal.get([key, trade.id])), guard(existing => {
        if (existing.some(Boolean)) {
          const replay = batch.every((trade, index) => JSON.stringify(trade) === JSON.stringify(existing[index]?.trade));
          if (!replay) throw new Error('Conflicting paper settlement ID.');
          // Even a correct retry must not apply the account settlement again.
          finish({ account: current, trades: [], changed: false });
          return;
        }
        const models = store('models');
        const partitions = new Map(batch.map(trade => [modelId(key, trade), trade]));
        read([...partitions.keys()].map(id => models.get(id)), guard(prior => {
          const next = new Map([...partitions].map(([id, trade], i) => [id, prior[i] ?? newModel(key, trade)]));
          const saved = batch.map(trade => {
            const learning = train(next.get(modelId(key, trade)), trade);
            const record = { key, id: trade.id, trade, learning };
            journal.add(record);
            return flatten(record);
          });
          for (const model of next.values()) models.put(model);
          store('accounts').put({ key, account });
          finish({ account, trades: saved, changed: true });
        }));
      }));
    }));
  });
}

function query(db, name, find) {
  return transaction(db, [name], 'readonly', (store, finish) => {
    read([find(store(name))], ([value]) => finish(value));
  });
}

function advanceCandleModel(db, key, rows, mark, nowMs) {
  const prepared = prepareCandleModel(key, rows, mark, nowMs);
  return transaction(db, [CANDLE_STORE], 'readwrite', (store, finish, guard) => {
    const candles = store(CANDLE_STORE);
    read(prepared.partitions.map(partition => candles.get(partition.key)), guard(saved => {
      const horizons = prepared.partitions.map((partition, i) => {
        const next = advanceCandlePartition(saved[i]?.state ?? null, prepared, partition);
        if (next.changed) candles.put({ key: partition.key, state: next.state });
        return next.summary;
      });
      finish({ eligible: prepared.eligible, status: prepared.status, horizons });
    }));
  });
}

export async function openWorkbenchStore(indexedDB = globalThis.indexedDB) {
  if (!indexedDB) throw new Error('Paper storage is unavailable.');
  const db = await new Promise((resolve, reject) => {
    const request = indexedDB.open(WORKBENCH_DB, DB_VERSION);
    let failed = false;
    request.onupgradeneeded = ({ oldVersion }) => {
      const opened = request.result;
      if (oldVersion < 1) {
        opened.createObjectStore('accounts', { keyPath: 'key' });
        opened.createObjectStore('journal', { keyPath: ['key', 'id'] });
        opened.createObjectStore('models', { keyPath: 'id' }).createIndex('key', 'key');
      }
      if (oldVersion < 2) opened.createObjectStore(CANDLE_STORE, { keyPath: 'key' });
    };
    request.onerror = () => reject(request.error ?? new Error('Paper storage is unavailable.'));
    request.onblocked = () => {
      failed = true;
      reject(new Error('Paper storage upgrade is blocked by an older tab.'));
    };
    request.onsuccess = () => {
      const opened = request.result;
      if (failed) { opened.close(); return; }
      opened.onversionchange = () => opened.close();
      resolve(opened);
    };
  });
  return {
    getAccounts: () => query(db, 'accounts', store => store.getAll()),
    getAccount: key => query(db, 'accounts', store => store.get(key)),
    update: async (key, reduce) => update(db, key, reduce),
    advanceCandleModel: async (key, rows, mark, nowMs) => advanceCandleModel(db, key, rows, mark, nowMs),
    async metrics(key) {
      requirePaperMarket(key);
      return (await query(db, 'models', store => store.index('key').getAll(key))).map(summarize);
    },
    async predict(key, { direction, strategy, step, features }) {
      requirePaperMarket(key);
      if (!validPartitionScope(direction, strategy, step) || !validFeatures(features)) {
        return { status: 'waiting-for-complete-history', samples: 0, minimumSamples: ORACLE.minTrained, probability: null };
      }
      const id = modelId(key, { direction, strategy, step });
      const saved = await query(db, 'models', store => store.get(id));
      const samples = saved?.model.n ?? 0;
      return { status: samples >= ORACLE.minTrained ? 'ready' : 'warming-up', samples,
        minimumSamples: ORACLE.minTrained,
        probability: samples >= ORACLE.minTrained ? probability(saved.model, features) : null };
    },
    async exportTrades() {
      const records = await query(db, 'journal', store => store.getAll());
      const trades = records.map(flatten).sort((a, b) => a.time - b.time || a.key.localeCompare(b.key) || a.id.localeCompare(b.id));
      return { schema: SCHEMA, mode: 'paper', model: ORACLE.model, featureSchema: ORACLE.features, target: TARGET, trades };
    },
    close: () => db.close(),
  };
}
