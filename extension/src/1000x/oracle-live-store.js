/** Separate database. Every synchronous reducer runs in one multi-store transaction.
 * Per-probe and per-score records avoid rewriting the full pending queue each second. */
import { validateLiveState } from './oracle-live-model.js';
import { checkpointMeta, nextCheckpoint, restoreCheckpoint } from './oracle-checkpoint.js';

export const LIVE_ORACLE_DB = 'solmargintrader-live-advisory-v1';
const STORES = ['partitions', 'metrics', 'pending', 'recent'];
const id = (...parts) => JSON.stringify(parts);
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
function join(key, core, metrics, pending, recent) {
  if (!core) {
    if (metrics.length || pending.length || recent.length) throw new Error('live_oracle_orphan_records');
    return null;
  }
  const state = structuredClone(core.state); state.metrics = {};
  for (const row of metrics) { if (state.metrics[row.horizon]) throw new Error('live_oracle_duplicate_metric');
    state.metrics[row.horizon] = { ...row.value, recent: [] }; }
  for (const row of recent) {
    if (!state.metrics[row.horizon]) throw new Error('live_oracle_orphan_score');
    state.metrics[row.horizon].recent.push(row.value);
  }
  for (const m of Object.values(state.metrics)) m.recent.sort((a, b) => a.ordinal - b.ordinal);
  state.pending = pending.map(row => row.value).sort((a, b) => a.issuedAtMs - b.issuedAtMs || a.horizon - b.horizon);
  if (state.key !== key) throw new Error('live_oracle_key_mismatch'); return state;
}
function records(key, state) {
  const { pending, metrics, ...core } = state, out = { partitions: [{ key, state: core }], metrics: [], pending: [], recent: [] };
  for (const [horizon, data] of Object.entries(metrics)) {
    const { recent, ...value } = data; out.metrics.push({ id: id(key, horizon), key, horizon, value });
    recent.forEach(v => out.recent.push({ id: id(key, horizon, v.id), key, horizon, value: v }));
  }
  pending.forEach(v => out.pending.push({ id: id(key, v.id), key, value: v }));
  return out;
}
export class LiveOracleStore {
  #indexedDb; #opening; #closed = false; #transactions = new Set();
  constructor(indexedDb = globalThis.indexedDB) { this.#indexedDb = indexedDb; }
  #open() {
    if (this.#closed) return Promise.reject(new Error('live_oracle_store_closed'));
    if (!this.#opening) this.#opening = new Promise((resolve, reject) => {
      if (!this.#indexedDb) { reject(new Error('live_oracle_storage_unavailable')); return; }
      const request = this.#indexedDb.open(LIVE_ORACLE_DB, 1); let failed = false;
      request.onupgradeneeded = () => {
        request.result.createObjectStore('partitions', { keyPath: 'key' });
        for (const name of STORES.slice(1)) request.result.createObjectStore(name, { keyPath: 'id' }).createIndex('key', 'key');
      };
      request.onerror = () => { failed = true; reject(new Error('live_oracle_storage_unavailable')); };
      request.onblocked = () => { failed = true; reject(new Error('live_oracle_storage_blocked')); };
      request.onsuccess = () => { const db = request.result; if (failed || this.#closed) { db.close(); reject(new Error('live_oracle_store_closed')); return; }
        db.onversionchange = () => { this.#closed = true; db.close(); }; resolve(db); };
    }).catch(e => { this.#opening = null; throw e; });
    return this.#opening;
  }
  async #transaction(key, reduce, restore = null) {
    const db = await this.#open(); if (this.#closed) throw new Error('live_oracle_store_closed');
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES, reduce || restore ? 'readwrite' : 'readonly'), found = {}, requests = [];
      this.#transactions.add(tx); let result, error, waiting = STORES.length;
      tx.oncomplete = () => { this.#transactions.delete(tx); resolve(structuredClone(result)); };
      tx.onabort = () => { this.#transactions.delete(tx); reject(error || new Error('live_oracle_storage_transaction_failed')); };
      tx.onerror = () => { error ||= new Error('live_oracle_storage_transaction_failed'); };
      const finish = () => { if (--waiting) return; try {
        const old = join(key, found.partitions, found.metrics, found.pending, found.recent);
        if (!reduce && (!restore || old)) { if (old) validateLiveState(old, key); result = old ? { state: old, ...checkpointMeta(found.partitions) } : null; return; }
        const apply = () => {
          const before = old ? records(key, structuredClone(old)) : { partitions: [], metrics: [], pending: [], recent: [] };
          result = restore ? { state: restore.state, changed: true } : reduce(old);
          if (!result || typeof result.then === 'function') throw new Error('live_oracle_async_transaction');
          const metadata = restore ? checkpointMeta(restore) : result.changed || !found.partitions?.lineage ? nextCheckpoint(found.partitions) : checkpointMeta(found.partitions);
          result.checkpoint = metadata;
          if (!result.changed) {
            if (!found.partitions?.lineage) tx.objectStore('partitions').put({ key, state: found.partitions.state, ...metadata });
            return;
          }
          if (result.state?.key !== key) throw new Error('live_oracle_key_mismatch');
          const after = records(key, result.state);
          for (const name of STORES) {
            const store = tx.objectStore(name), ident = row => name === 'partitions' ? row.key : row.id;
            const oldMap = new Map(before[name].map(row => [ident(row), row]));
            for (const row of after[name]) { if (name === 'partitions') Object.assign(row, metadata); const k = ident(row); if (!same(row, oldMap.get(k))) store.put(row); oldMap.delete(k); }
            for (const k of oldMap.keys()) store.delete(k);
          }
        };
        if (old) apply(); else { const count = tx.objectStore('partitions').count(); count.onsuccess = () => { try {
          if (count.result >= 16) throw new Error('live_oracle_partition_capacity'); apply();
        } catch (e) { error = e; tx.abort(); } }; }
      } catch (e) { error = e; tx.abort(); } };
      for (const name of STORES) {
        const store = tx.objectStore(name), request = name === 'partitions' ? store.get(key) : store.index('key').getAll(key);
        requests.push(request); request.onsuccess = () => { found[name] = request.result ?? (name === 'partitions' ? null : []); finish(); };
      }
    });
  }
  update(key, reduce) { if (typeof reduce !== 'function') return Promise.reject(new Error('live_oracle_reducer_required')); return this.#transaction(key, reduce); }
  loadCheckpoint(key) { return this.#transaction(key, null); }
  async load(key) { return (await this.loadCheckpoint(key))?.state ?? null; }
  async restoreIfAbsent(key, checkpoint) {
    const saved = restoreCheckpoint(key, checkpoint, validateLiveState);
    const result = await this.#transaction(key, null, saved);
    return { state: result.state, ...(result.checkpoint || checkpointMeta(result)) };
  }
  cancelPending() { for (const tx of this.#transactions) { try { tx.abort(); } catch { /* Already complete. */ } } }
  close() { this.#closed = true; this.cancelPending(); this.#opening?.then(db => db.close()).catch(() => {}); }
}
