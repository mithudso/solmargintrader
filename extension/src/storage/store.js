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
  FAILED: 'failed', // a definitive rejection; ambiguous submissions stay unknown
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
const runtimeQueues = new WeakMap();
const validStopGeneration = value => Number.isSafeInteger(value) && value >= 0;
const runtimeDefaults = { armed: false, killSwitch: false, stopGeneration: 0,
  lastTickMs: null, lastTickDeltaMs: null, dayKey: null, realizedPnlUsdToday: 0 };

function runtimeValue(stored) {
  if (!stored || typeof stored !== 'object' || Array.isArray(stored)) return { ...runtimeDefaults, killSwitch: true };
  // Older records predate this counter. Explicit malformed counters cannot
  // become a fresh epoch or authorize an arm/clear after a stop.
  const generation = Object.hasOwn(stored, 'stopGeneration') ? stored.stopGeneration : 0;
  const valid = validStopGeneration(generation);
  return { ...runtimeDefaults, ...stored, stopGeneration: valid ? generation : null,
    armed: valid && stored.armed === true,
    killSwitch: !valid || (Object.hasOwn(stored, 'killSwitch') ? stored.killSwitch !== false : false) };
}

export class ConfigStore {
  constructor(area = globalThis.chrome?.storage?.local) {
    this.area = area;
    this.memory = new Map();
  }

  async get(key, fallback) {
    if (!this.area) return this.memory.has(key) ? this.memory.get(key) : fallback;
    const res = await this.area.get(key);
    return res && Object.hasOwn(res, key) && res[key] !== undefined ? res[key] : fallback;
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
    // Public configuration cannot expose legacy unknown fields such as apiKey.
    const values = stored && typeof stored === 'object' && !Array.isArray(stored) ? stored : {};
    return Object.fromEntries(Object.entries(DEFAULT_CONFIG).map(([key, fallback]) =>
      [key, Object.hasOwn(values, key) ? values[key] : fallback]));
  }

  async setConfig(patch) {
    const next = { ...(await this.getConfig()), ...patch };
    await this.set(CONFIG_KEY, next);
    return next;
  }

  async getRuntime() {
    return runtimeValue(await this.get(RUNTIME_KEY, {}));
  }

  async updateRuntime(update) {
    if (typeof this.area?.update === 'function') {
      return this.area.update(RUNTIME_KEY, stored => update(runtimeValue(stored === undefined ? {} : stored)));
    }
    const identity = this.area ?? this;
    const result = (runtimeQueues.get(identity) ?? Promise.resolve()).then(async () => {
      const next = update(await this.getRuntime());
      await this.set(RUNTIME_KEY, next);
      return next;
    });
    const tail = result.catch(() => {});
    runtimeQueues.set(identity, tail);
    tail.then(() => { if (runtimeQueues.get(identity) === tail) runtimeQueues.delete(identity); });
    return result;
  }

  async setRuntime(patch, options = {}) {
    return this.updateRuntime(current => {
      if (Object.hasOwn(options, 'expectedStopGeneration') && (!validStopGeneration(options.expectedStopGeneration)
          || current.stopGeneration !== options.expectedStopGeneration)) {
        throw Object.assign(new Error('A newer or unusable stop prevents this runtime change'), { code: 'RUNTIME_STOP_CHANGED' });
      }
      if (patch.armed === true && current.killSwitch) throw new Error('Kill switch is engaged');
      const next = { ...current, ...patch };
      // Initialization and metadata writers cannot clear an emergency latch.
      // Explicit clear and fresh-install reset supply a checked stop generation.
      if (current.killSwitch && patch.killSwitch === false && !Object.hasOwn(options, 'expectedStopGeneration')) next.killSwitch = true;
      return next;
    });
  }

  async killRuntime() {
    for (let attempt = 0; ; attempt++) {
      try {
        return await this.updateRuntime(current => ({ ...current, armed: false, killSwitch: true,
          stopGeneration: validStopGeneration(current.stopGeneration) && current.stopGeneration < Number.MAX_SAFE_INTEGER
            ? current.stopGeneration + 1 : null }));
      } catch (error) {
        // BUSY means the config lease was never acquired: no write occurred.
        // A stale/foreign config lease also blocks the active owner's reads.
        if (error.code !== 'FILE_STORE_BUSY' || attempt >= 20) throw error;
        await new Promise(resolve => setTimeout(resolve, 5));
      }
    }
  }

  async withExecutionPermission(invoke, permitted = () => true, options = {}) {
    let permission;
    // Serialize the last permission check and synchronous venue invocation with
    // emergency updates. Return a wrapped promise so the config lease releases
    // before waiting for the venue's response, which may be ambiguous or slow.
    await this.updateRuntime(current => {
      const epochMatches = !Object.hasOwn(options, 'expectedStopGeneration')
        || (validStopGeneration(options.expectedStopGeneration) && current.stopGeneration === options.expectedStopGeneration);
      if ((current.armed !== true && options.paperGrant !== true) || current.killSwitch !== false
          || !epochMatches || permitted() !== true) {
        permission = { allowed: false };
      } else {
        const pending = Promise.resolve(invoke());
        pending.catch(() => {}); // The caller awaits it after the lease releases.
        permission = { allowed: true, pending };
      }
      return current;
    });
    return permission;
  }
}
