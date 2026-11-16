/** Separate from the money-moving journal. Each conditional learner transition
 * stays inside one native readwrite transaction, including across browser tabs. */
import { ORACLE } from './oracle-model.js';

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
  async update(key, reduce) {
    const db = await this.#open();
    if (this.#closed) throw new Error('oracle_store_closed');
    return new Promise((resolve, reject) => {
      const tx = db.transaction('partitions', 'readwrite'), store = tx.objectStore('partitions');
      this.#transactions.add(tx);
      let result, error;
      tx.oncomplete = () => { this.#transactions.delete(tx); resolve(structuredClone(result)); };
      tx.onabort = () => { this.#transactions.delete(tx); reject(error || new Error('oracle_storage_transaction_failed')); };
      tx.onerror = () => { error ||= new Error('oracle_storage_transaction_failed'); };
      const apply = state => {
        try {
          // The reducer MUST be synchronous. Awaiting here makes the transaction
          // inactive and splits model/counter/forecast writes across tabs.
          result = reduce(state);
          if (!result || typeof result.then === 'function') throw new Error('oracle_async_transaction');
          if (result.changed) store.put({ key, state: result.state });
        } catch (caught) { error = caught; tx.abort(); }
      };
      const read = store.get(key);
      read.onsuccess = () => {
        if (read.result) apply(read.result.state);
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
  cancelPending() {
    for (const tx of this.#transactions) {
      try { tx.abort(); } catch { /* An already finished transaction owns no lock. */ }
    }
  }
  close() { this.#closed = true; this.cancelPending(); this.#opening?.then(db => db.close()).catch(() => {}); }
}
