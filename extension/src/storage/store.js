/**
 * Persistence.
 *
 * Two surfaces, chosen by what the data is:
 *   chrome.storage.local — config and limits. Small, synchronously readable at
 *     worker start, and NEVER `.sync` (that would push settings, and anything
 *     near them, to Google's servers).
 *   IndexedDB — the intent journal and fill log. Unbounded, append-heavy, and
 *     queryable by time; chrome.storage would be the wrong shape and has quota
 *     limits a long-running fill log will hit.
 *
 * The intent journal is what makes the bot restart-safe: an intent is written
 * with status `submitting` BEFORE the network call, so a worker that dies
 * mid-submit leaves a record the reconciler can find.
 */

export const DB_NAME = 'solmargintrader';
export const DB_VERSION = 1;
export const STORES = { INTENTS: 'intents', FILLS: 'fills', CARRY: 'carry', EVENTS: 'events' };

export const INTENT_STATUS = {
  SUBMITTING: 'submitting', // written before the network call
  RESTING: 'resting', // confirmed live on the venue
  FILLED: 'filled',
  CANCELLED: 'cancelled',
  FAILED: 'failed', // submit threw; safe to retry
  UNKNOWN: 'unknown', // submitted but not found on the venue — needs human review
};

/* --------------------------------------------------------------- IndexedDB -- */

export function openDb(indexedDbImpl = globalThis.indexedDB) {
  return new Promise((resolve, reject) => {
    const req = indexedDbImpl.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORES.INTENTS)) {
        const s = db.createObjectStore(STORES.INTENTS, { keyPath: 'intentKey' });
        s.createIndex('byStatus', 'status');
        s.createIndex('byGrid', 'gridId');
      }
      if (!db.objectStoreNames.contains(STORES.FILLS)) {
        const s = db.createObjectStore(STORES.FILLS, { keyPath: 'id' });
        s.createIndex('byTs', 'tsMs');
        s.createIndex('byGrid', 'gridId');
      }
      if (!db.objectStoreNames.contains(STORES.CARRY)) {
        db.createObjectStore(STORES.CARRY, { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains(STORES.EVENTS)) {
        const s = db.createObjectStore(STORES.EVENTS, { keyPath: 'id', autoIncrement: true });
        s.createIndex('byTs', 'tsMs');
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function tx(db, storeName, mode, fn) {
  return new Promise((resolve, reject) => {
    const t = db.transaction(storeName, mode);
    const store = t.objectStore(storeName);
    let result;
    try {
      result = fn(store);
    } catch (err) {
      reject(err);
      return;
    }
    t.oncomplete = () => resolve(result?.result ?? result);
    t.onerror = () => reject(t.error);
    t.onabort = () => reject(t.error ?? new Error('transaction aborted'));
  });
}

const asPromise = (req) =>
  new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });

export class Store {
  constructor(db) {
    this.db = db;
  }

  static async open(indexedDbImpl) {
    return new Store(await openDb(indexedDbImpl));
  }

  /* ------------------------------------------------------------- intents -- */

  /** Write-ahead: call this BEFORE submitting, so a crash leaves a trace. */
  async putIntent(intent) {
    return tx(this.db, STORES.INTENTS, 'readwrite', (s) => s.put(intent));
  }

  async getIntent(intentKey) {
    const t = this.db.transaction(STORES.INTENTS, 'readonly');
    return asPromise(t.objectStore(STORES.INTENTS).get(intentKey));
  }

  async allIntents() {
    const t = this.db.transaction(STORES.INTENTS, 'readonly');
    return asPromise(t.objectStore(STORES.INTENTS).getAll());
  }

  async intentsByStatus(status) {
    const all = await this.allIntents();
    return all.filter((i) => i.status === status);
  }

  async updateIntent(intentKey, patch) {
    const existing = await this.getIntent(intentKey);
    if (!existing) return null;
    const next = { ...existing, ...patch, updatedAtMs: Date.now() };
    await this.putIntent(next);
    return next;
  }

  /* --------------------------------------------------------------- fills -- */

  /** Idempotent by fill id, so re-reading venue history cannot double-count. */
  async putFill(fill) {
    return tx(this.db, STORES.FILLS, 'readwrite', (s) => s.put(fill));
  }

  async allFills() {
    const t = this.db.transaction(STORES.FILLS, 'readonly');
    return asPromise(t.objectStore(STORES.FILLS).getAll());
  }

  async putCarry(entry) {
    return tx(this.db, STORES.CARRY, 'readwrite', (s) => s.put(entry));
  }

  async allCarry() {
    const t = this.db.transaction(STORES.CARRY, 'readonly');
    return asPromise(t.objectStore(STORES.CARRY).getAll());
  }

  /* -------------------------------------------------------------- events -- */

  async logEvent(event) {
    return tx(this.db, STORES.EVENTS, 'readwrite', (s) =>
      s.add({ tsMs: Date.now(), ...event }),
    );
  }

  async recentEvents(limit = 100) {
    const t = this.db.transaction(STORES.EVENTS, 'readonly');
    const all = await asPromise(t.objectStore(STORES.EVENTS).getAll());
    return all.slice(-limit).reverse();
  }

  /** Erase every local record. Does not touch venue-side orders. */
  async clearAll() {
    const names = Object.values(STORES);
    return new Promise((resolve, reject) => {
      const t = this.db.transaction(names, 'readwrite');
      for (const name of names) t.objectStore(name).clear();
      t.oncomplete = () => resolve();
      t.onerror = () => reject(t.error);
      t.onabort = () => reject(t.error ?? new Error('clearAll aborted'));
    });
  }
}

/* ------------------------------------------------------------------ config -- */

export const CONFIG_KEY = 'config';
export const RUNTIME_KEY = 'runtime';

export const DEFAULT_CONFIG = Object.freeze({
  mode: 'dry-run', // never default to spending money
  venue: 'trigger',
  gridId: 'grid-1',
  // SOL / USDC. Mints cross-checked against the saved jup.ag pages.
  baseMint: 'So11111111111111111111111111111111111111112',
  quoteMint: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
  baseSymbol: 'SOL',
  quoteSymbol: 'USDC',
  userPubkey: null,
  lower: 60,
  upper: 90,
  rungs: 7,
  spacing: 'geom',
  notionalPerRungUsd: 12,
  direction: 'neutral',
  deadbandBps: 25,
  slippageBps: 100,
  ttlMs: 30 * 24 * 60 * 60 * 1000, // Trigger V2 requires an expiry on every order
  leverage: 1,
  marginSource: 'none',
  tickSeconds: 60,
  minOrderUsd: 10,
  // Auto re-centring is OFF by default: a fresh install must behave exactly as it
  // did before this feature existed. See recentreDecision() for why it can only
  // act when nothing would be stranded.
  autoRecentre: false,
  recentreSpanPct: 0.15, // 0.85x-1.15x, matching tools/dryrun.js
  recentreDriftBps: 0, // extra slack beyond the ladder before a move is worth it
});

/** chrome.storage.local wrapper that works headless (Node) for tests. */
export class ConfigStore {
  constructor(area = globalThis.chrome?.storage?.local) {
    this.area = area;
    this.memory = new Map();
  }

  async get(key, fallback) {
    if (!this.area) return this.memory.has(key) ? this.memory.get(key) : fallback;
    const res = await this.area.get(key);
    return res?.[key] ?? fallback;
  }

  async set(key, value) {
    if (!this.area) {
      this.memory.set(key, value);
      return;
    }
    await this.area.set({ [key]: value });
  }

  async getConfig() {
    const stored = await this.get(CONFIG_KEY, {});
    return { ...DEFAULT_CONFIG, ...stored };
  }

  async setConfig(patch) {
    const next = { ...(await this.getConfig()), ...patch };
    await this.set(CONFIG_KEY, next);
    return next;
  }

  async getRuntime() {
    return this.get(RUNTIME_KEY, {
      armed: false,
      killSwitch: false,
      lastTickMs: null,
      lastTickDeltaMs: null,
      dayKey: null,
      realizedPnlUsdToday: 0,
    });
  }

  async setRuntime(patch) {
    const next = { ...(await this.getRuntime()), ...patch };
    await this.set(RUNTIME_KEY, next);
    return next;
  }
}
