/** IndexedDB remains primary. Disk I/O happens after commit, never in a reducer. */
import { validateOracleState } from './oracle-model.js';
import { validateLiveState } from './oracle-live-model.js';
import { checkpointMeta, checkpointText, validLearningId } from './oracle-checkpoint.js';
import { soltui } from '../ui/ui-kit.js';

const PROFILE_DB = 'solmargintrader-oracle-backup-profile';
const MAX_BYTES = 2 * 1024 * 1024;
const encoder = new TextEncoder();
const validate = (kind, state, key) => (kind === 'minute' ? validateOracleState : validateLiveState)(state, key);
const digest = async text => [...new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(text)))].map(v => v.toString(16).padStart(2, '0')).join('');

/** This separate database survives clearing either learner database. Its single
 * transaction also gives simultaneous windows one profile identity. */
export async function learningProfile(indexedDb = globalThis.indexedDB) {
  return new Promise((resolve, reject) => {
    if (!indexedDb) { reject(new Error('oracle_profile_storage_unavailable')); return; }
    const request = indexedDb.open(PROFILE_DB, 1);
    request.onupgradeneeded = () => request.result.createObjectStore('profile');
    let openingFailed = false;
    request.onerror = request.onblocked = () => { openingFailed = true; reject(new Error('oracle_profile_storage_unavailable')); };
    request.onsuccess = () => {
      const db = request.result;
      if (openingFailed) { db.close(); return; }
      const tx = db.transaction('profile', 'readwrite'), store = tx.objectStore('profile');
      let value, failed = false;
      const read = store.get('namespace');
      read.onsuccess = () => {
        value = read.result;
        if (value === undefined) { value = crypto.randomUUID(); store.put(value, 'namespace'); }
        else if (!validLearningId(value)) { failed = true; tx.abort(); }
      };
      tx.oncomplete = () => { db.close(); resolve(value); };
      tx.onabort = tx.onerror = () => { db.close(); reject(new Error(failed ? 'oracle_profile_identity_invalid' : 'oracle_profile_storage_unavailable')); };
    };
  });
}

export class OracleDiskBackup {
  #call; #profile; #clock; #change; #namespace; #queued = new Map(); #last = new Map(); #ack = new Map();
  #running = false; #closed = false; #timer = null; #calls = new Set(); #schedule; #cancel; #physicalSave = null;
  constructor({ call = soltui, profile = learningProfile, clock = Date.now, onChange = () => {},
    schedule = (fn, ms) => globalThis.setTimeout(fn, ms), cancel = timer => globalThis.clearTimeout(timer) } = {}) {
    this.#call = call; this.#profile = profile; this.#clock = clock; this.#change = onChange;
    this.#schedule = schedule; this.#cancel = cancel;
  }
  #id(kind, key) { return JSON.stringify([kind, key]); }
  #emit(kind, key, status, extra = {}) {
    if (!this.#closed) this.#change({ kind, key, status, ...extra });
  }
  activate() { /* Each event carries its exact partition identity. */ }
  markUnavailable(kind, key) { this.#emit(kind, key, 'unavailable'); }
  async #identity() {
    if (!this.#namespace) this.#namespace = this.#bounded(() => this.#profile()).catch(error => { this.#namespace = null; throw error; });
    return this.#namespace;
  }
  #request(command, params) {
    return this.#bounded(() => this.#call(command, params));
  }
  #bounded(invoke) {
    if (this.#closed) return Promise.reject(new Error('oracle_backup_closed'));
    return new Promise((resolve, reject) => {
      let done = false, timer;
      const finish = (fn, value) => { if (done) return; done = true; this.#cancel(timer); this.#calls.delete(cancel); fn(value); };
      const cancel = () => finish(reject, new Error('oracle_backup_closed'));
      this.#calls.add(cancel); timer = this.#schedule(() => finish(reject, new Error('oracle_backup_timeout')), 2000);
      try { Promise.resolve(invoke()).then(value => finish(resolve, value), error => finish(reject, error)); }
      catch (error) { finish(reject, error); }
    });
  }
  async restore(kind, key) {
    this.activate(kind, key);
    try {
      const namespace = await this.#identity();
      let offset = 0, text = '', first;
      for (let page = 0; page < 18; page++) {
        const response = await this.#request('oracle.learning.load', { namespace, kind, key, offset, ...(first ? { digest: first.digest } : {}) });
        if (!response || typeof response.found !== 'boolean') throw new Error('oracle_backup_invalid');
        if (!response?.found) { if (first) throw new Error('oracle_backup_incomplete'); this.#emit(kind, key, 'local-only'); return null; }
        if (!first) first = response;
        if (!Number.isSafeInteger(response.length) || response.length < 1 || response.length > MAX_BYTES
          || response.offset !== offset || typeof response.text !== 'string' || !response.text.length
          || response.text.length > 128 * 1024 || response.digest !== first.digest || response.lineage !== first.lineage || response.revision !== first.revision
          || response.length !== first.length || !/^[a-f0-9]{64}$/.test(response.digest)) throw new Error('oracle_backup_invalid');
        text += response.text; offset += response.text.length;
        if (offset > first.length || encoder.encode(text).length > MAX_BYTES) throw new Error('oracle_backup_invalid');
        if (offset === first.length) break;
      }
      if (text.length !== first?.length || await digest(text) !== first.digest) throw new Error('oracle_backup_digest_mismatch');
      let state, metadata;
      try { state = JSON.parse(text); validate(kind, state, key); metadata = checkpointMeta(first); }
      catch { throw new Error('oracle_backup_invalid_state'); }
      this.#emit(kind, key, 'verified', { revision: metadata.revision, savedAt: first.saved_at * 1000 });
      return { state, ...metadata };
    } catch (error) {
      this.#emit(kind, key, 'unavailable'); throw error;
    }
  }
  queue(kind, key, checkpoint, force = false) {
    if (this.#closed) return;
    this.activate(kind, key);
    const id = this.#id(kind, key), previous = this.#queued.get(id), saved = this.#ack.get(id);
    if (!force && saved?.lineage === checkpoint.lineage && saved.revision >= checkpoint.revision) return;
    if (!previous || checkpoint.revision >= previous.checkpoint.revision) this.#queued.set(id, { kind, key, checkpoint, force: force || previous?.force });
    // At most one latest complete snapshot per supported partition.
    if (this.#queued.size > 112) { this.#queued.delete(id); this.#emit(kind, key, 'unavailable'); return; }
    this.#emit(kind, key, 'pending', { revision: checkpoint.revision });
    if (!this.#running) void this.#drain();
  }
  async #drain() {
    if (this.#closed || this.#running) return;
    const now = this.#clock();
    const entry = [...this.#queued.entries()].find(([id, item]) => item.force || now - (this.#last.get(id) ?? -Infinity) >= 30000);
    if (!entry) {
      if (this.#queued.size && !this.#timer) this.#timer = this.#schedule(() => { this.#timer = null; void this.#drain(); }, 1000);
      return;
    }
    const [id, item] = entry; this.#queued.delete(id); this.#running = true;
    if (this.#timer) { this.#cancel(this.#timer); this.#timer = null; }
    this.#last.set(id, now);
    const { kind, key, checkpoint } = item;
    try {
      validate(kind, checkpoint.state, key); const metadata = checkpointMeta(checkpoint), text = checkpointText(checkpoint.state);
      if (encoder.encode(text).length > MAX_BYTES) throw new Error('oracle_backup_too_large');
      const namespace = await this.#identity();
      const flight = { settled: false, promise: Promise.resolve().then(() => this.#call('oracle.learning.save', { namespace, kind, key, checkpoint: { ...metadata, text } })) };
      this.#physicalSave = flight;
      flight.promise.then(() => { flight.settled = true; }, () => { flight.settled = true; });
      const reply = await this.#bounded(() => flight.promise);
      if (!Number.isSafeInteger(reply?.revision) || reply.revision < metadata.revision || !/^[a-f0-9]{64}$/.test(reply.digest)) throw new Error('oracle_backup_not_acknowledged');
      const newer = reply.status === 'disk_newer' && reply.revision > metadata.revision;
      if (!newer && (!reply.saved || reply.digest !== await digest(text))) throw new Error('oracle_backup_not_acknowledged');
      this.#ack.set(id, { lineage: metadata.lineage, revision: reply.revision });
      const queued = this.#queued.get(id);
      if (queued?.checkpoint.lineage === metadata.lineage && queued.checkpoint.revision <= reply.revision) this.#queued.delete(id);
      if (!this.#queued.has(id)) this.#emit(kind, key, newer ? 'disk-newer' : 'saved', { revision: reply.revision, savedAt: this.#clock() });
    } catch (error) {
      const conflict = /lineage_conflict|revision_conflict|count_regression/.test(error?.message || '');
      this.#emit(kind, key, conflict ? 'conflict' : 'unavailable');
      if (!conflict && !this.#closed && !this.#queued.has(id)) this.#queued.set(id, { ...item, force: false });
    } finally {
      const flight = this.#physicalSave;
      let retired = false;
      const retire = () => {
        if (retired) return; retired = true;
        if (this.#physicalSave === flight) this.#physicalSave = null;
        this.#running = false;
        if (!this.#closed && this.#queued.size) void this.#drain();
      };
      // A logical timeout does not cancel an already sent native write. Keep
      // the physical fence until the transport settles; local learning continues.
      if (flight && !flight.settled && !this.#closed) flight.promise.then(retire, retire);
      else retire();
    }
  }
  flush() { for (const item of this.#queued.values()) item.force = true; if (!this.#running) void this.#drain(); }
  close() {
    this.#closed = true; if (this.#timer) this.#cancel(this.#timer);
    this.#queued.clear(); for (const cancel of [...this.#calls]) cancel();
  }
}

/** Restore only a missing partition. A simultaneous tab always wins its own
 * native transaction; no disk reply can replace that tab's committed learning. */
export class MirroredOracleStore {
  #local; #disk; #kind; #clock; #ready = new Map(); #legacyRetryAt = new Map();
  constructor(local, disk, kind, { clock = Date.now } = {}) {
    this.#local = local; this.#disk = disk; this.#kind = kind; this.#clock = clock;
  }
  async #ensure(key) {
    this.#disk.activate(this.#kind, key);
    if (this.#clock() < (this.#legacyRetryAt.get(key) ?? 0)) return false;
    if (!this.#ready.has(key)) this.#ready.set(key, (async () => {
      const local = await this.#local.loadCheckpoint(key);
      if (local) {
        let saved = local;
        if (!saved.lineage) {
          try {
            // An old Live Oracle window can leave newer model state without
            // its backup metadata. Reuse the exact verified disk identity,
            // without replacing the browser model with the older disk copy.
            const backupBase = this.#kind === 'live' ? await this.#disk.restore(this.#kind, key) : null;
            const result = await this.#local.update(key, current => {
              validate(this.#kind, current, key); return { state: current, changed: false };
            }, { backupBase });
            saved = { state: result.state, ...result.checkpoint };
            this.#legacyRetryAt.delete(key);
          } catch {
            this.#ready.delete(key); this.#disk.markUnavailable(this.#kind, key);
            if (this.#kind === 'live') {
              // Leave the row unversioned until the helper can tell us whether
              // a prior lineage exists. Local learning does not need the helper.
              this.#legacyRetryAt.set(key, this.#clock() + 5000);
              return false;
            }
            return;
          }
        }
        this.#disk.queue(this.#kind, key, saved); return;
      }
      let saved;
      try { saved = await this.#disk.restore(this.#kind, key); }
      catch (error) {
        this.#ready.delete(key);
        if (/oracle_backup_(invalid|digest|incomplete)|learning_checkpoint_(corrupt|changed_during_read)/.test(error?.message || '')) throw error;
        return; // Local learning survives absent/failed native storage.
      }
      if (saved) await this.#local.restoreIfAbsent(key, saved);
    })().catch(error => { this.#ready.delete(key); throw error; }));
    return this.#ready.get(key);
  }
  async update(key, reduce) {
    const ready = await this.#ensure(key);
    const result = await this.#local.update(key, reduce, { deferLegacy: ready === false });
    if (result.checkpoint?.lineage) this.#disk.queue(this.#kind, key, { state: result.state, ...result.checkpoint });
    return result;
  }
  async load(key) { await this.#ensure(key); return this.#local.load(key); }
  cancelPending() { this.#local.cancelPending?.(); }
  close() { this.#local.close(); }
}
