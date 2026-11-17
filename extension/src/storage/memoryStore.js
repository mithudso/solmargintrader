/**
 * In-memory Store, API-compatible with the IndexedDB one.
 *
 * Exists so the tick can run headless — under `node --test` and in
 * tools/dryrun.js — without Chrome or a fake IndexedDB. The engine takes its
 * store as a dependency precisely so this substitution is possible.
 */

export class MemoryStore {
  constructor() {
    this.intents = new Map();
    this.fills = new Map();
    this.carry = new Map();
    this.events = [];
  }

  async putIntent(intent) {
    this.intents.set(intent.intentKey, structuredClone(intent));
  }

  async getIntent(key) {
    const v = this.intents.get(key);
    return v ? structuredClone(v) : undefined;
  }

  async allIntents() {
    return [...this.intents.values()].map((i) => structuredClone(i));
  }

  async intentsByStatus(status) {
    return (await this.allIntents()).filter((i) => i.status === status);
  }

  async updateIntent(key, patch) {
    const existing = this.intents.get(key);
    if (!existing) return null;
    const next = { ...existing, ...patch, updatedAtMs: Date.now() };
    this.intents.set(key, structuredClone(next));
    return structuredClone(next);
  }

  async putFill(fill) {
    this.fills.set(fill.id, structuredClone(fill));
  }

  async allFills() {
    return [...this.fills.values()].map((f) => structuredClone(f));
  }

  async putCarry(entry) {
    this.carry.set(entry.id, structuredClone(entry));
  }

  async allCarry() {
    return [...this.carry.values()].map((c) => structuredClone(c));
  }

  async logEvent(event) {
    this.events.push(structuredClone({ tsMs: Date.now(), ...event }));
  }

  async recentEvents(limit = 100) {
    if (!Number.isSafeInteger(limit) || limit < 0) throw new RangeError('event limit must be a nonnegative integer');
    return limit === 0 ? [] : structuredClone(this.events.slice(-limit).reverse());
  }

  async clearAll() {
    this.intents.clear();
    this.fills.clear();
    this.carry.clear();
    this.events = [];
  }
}
