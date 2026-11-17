/** Separate from the money-moving journal. Each conditional learner transition
 * stays inside one native readwrite transaction, including across browser tabs. */
import { ORACLE, validateOracleState } from './oracle-model.js';
import { checkpointMeta, nextCheckpoint, restoreCheckpoint } from './oracle-checkpoint.js';

export const ORACLE_DB = 'solmargintrader-streaming-oracle';
export class OracleStore {
  #indexedDb;
  #opening;
  #closed = false;
  #transactions = new Set();
  constructor(indexedDb = globalThis.indexedDB) { this.#indexedDb = indexedDb; }
  #open() {
    if (this.#closed) return Promise.reject(new Error('oracle_store_closed'));
    if (!this.#opening) this.#opening = new Promise((resolve, reject) => {
      if (!this.#indexedDb) { reject(new Error('oracle_storage_unavailable')); return; }
      const request = this.#indexedDb.open(ORACLE_DB, 1);
      let failed = false;
      request.onupgradeneeded = () => request.result.createObjectStore('partitions', { keyPath: 'key' });
      request.onerror = () => { failed = true; reject(new Error('oracle_storage_unavailable')); };
      request.onblocked = () => { failed = true; reject(new Error('oracle_storage_blocked')); };
      request.onsuccess = () => {
        const db = request.result;
        if (this.#closed || failed) { db.close(); reject(new Error('oracle_store_closed')); return; }
        db.onversionchange = () => { this.#closed = true; db.close(); };
        resolve(db);
      };
    }).catch(error => { this.#opening = null; throw error; });
    return this.#opening;
  }
  async #transaction(key, reduce, restore = null) {
    const db = await this.#open();
    if (this.#closed) throw new Error('oracle_store_closed');
    return new Promise((resolve, reject) => {
      const tx = db.transaction('partitions', reduce || restore ? 'readwrite' : 'readonly'), store = tx.objectStore('partitions');
      this.#transactions.add(tx);
      let result, error;
      tx.oncomplete = () => { this.#transactions.delete(tx); resolve(structuredClone(result)); };
      tx.onabort = () => { this.#transactions.delete(tx); reject(error || new Error('oracle_storage_transaction_failed')); };
      tx.onerror = () => { error ||= new Error('oracle_storage_transaction_failed'); };
      const apply = record => {
        try {
          if (!reduce) {
            if (record) { validateOracleState(record.state, key); result = { state: record.state, ...checkpointMeta(record) }; }
            else if (restore) { store.put(restore); result = { state: restore.state, ...checkpointMeta(restore) }; }
            else result = null;
            return;
          }
          // The reducer MUST be synchronous. Awaiting here makes the transaction
          // inactive and splits model/counter/forecast writes across tabs.
          result = reduce(record?.state || null);
          if (!result || typeof result.then === 'function') throw new Error('oracle_async_transaction');
          const metadata = result.changed || !record?.lineage ? nextCheckpoint(record) : checkpointMeta(record);
          if (result.changed || !record?.lineage) store.put({ key, state: result.state, ...metadata });
          result.checkpoint = metadata;
        } catch (caught) { error = caught; tx.abort(); }
      };
      const read = store.get(key);
      read.onsuccess = () => {
        if (read.result) apply(read.result);
        else if (!reduce && !restore) apply(null);
        else {
          const count = store.count();
          count.onsuccess = () => {
            if (count.result >= ORACLE.maxPartitions) { error = new Error('oracle_partition_capacity'); tx.abort(); }
            else apply(null);
          };
        }
      };
    });
  }
  update(key, reduce) { return this.#transaction(key, reduce); }
  loadCheckpoint(key) { return this.#transaction(key, null); }
  async load(key) { return (await this.loadCheckpoint(key))?.state ?? null; }
  restoreIfAbsent(key, checkpoint) { return this.#transaction(key, null, restoreCheckpoint(key, checkpoint, validateOracleState)); }
  cancelPending() {
    for (const tx of this.#transactions) {
      try { tx.abort(); } catch { /* An already finished transaction owns no lock. */ }
    }
  }
  close() { this.#closed = true; this.cancelPending(); this.#opening?.then(db => db.close()).catch(() => {}); }
}
