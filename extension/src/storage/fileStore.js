/**
 * Node-side persistence, API-compatible with the browser surfaces.
 *
 * The CLI and HTTP API need the same durability the extension gets from
 * IndexedDB + chrome.storage.local, so this provides:
 *
 *   FileStore       the Store API (intents, fills, carry, events) on a JSON file
 *   createFileArea  a chrome.storage.local-shaped {get,set} on a JSON file, so
 *                   ConfigStore works unchanged outside the browser
 *
 * Writes go through a temp file and a rename. A trading journal truncated by a
 * crash mid-write is worse than one that is slightly stale: rename is atomic on
 * POSIX, so a reader sees either the old file or the new one, never a partial.
 */

import { readFile, writeFile, rename, mkdir } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { homedir } from 'node:os';

export const DEFAULT_DATA_DIR = join(homedir(), '.solmargintrader');
export const DEFAULT_STORE_PATH = join(DEFAULT_DATA_DIR, 'journal.json');
export const DEFAULT_CONFIG_PATH = join(DEFAULT_DATA_DIR, 'config.json');

async function readJson(path, fallback) {
  try {
    return JSON.parse(await readFile(path, 'utf8'));
  } catch (err) {
    if (err.code === 'ENOENT') return fallback;
    if (err instanceof SyntaxError) {
      throw new Error(`${path} is not valid JSON — refusing to overwrite it: ${err.message}`);
    }
    throw err;
  }
}

async function writeJsonAtomic(path, value) {
  await mkdir(dirname(path), { recursive: true });
  const tmp = `${path}.${process.pid}.tmp`;
  await writeFile(tmp, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  await rename(tmp, path);
}

/**
 * chrome.storage.local-shaped area over a JSON file.
 *
 * Mode 0600: this file holds the Jupiter API key and the encrypted session-key
 * vault, so it must not be world-readable.
 */
export function createFileArea(path = DEFAULT_CONFIG_PATH) {
  return {
    path,
    async get(keys) {
      const all = await readJson(path, {});
      if (keys == null) return all;
      const list = Array.isArray(keys) ? keys : [keys];
      return Object.fromEntries(list.map((k) => [k, all[k]]));
    },
    async set(obj) {
      const all = await readJson(path, {});
      await writeJsonAtomic(path, { ...all, ...obj });
    },
  };
}

/** Store API over a single JSON file. */
export class FileStore {
  constructor(path = DEFAULT_STORE_PATH) {
    this.path = path;
  }

  static async open(path) {
    const store = new FileStore(path);
    await store.read(); // surface a corrupt journal now, not mid-tick
    return store;
  }

  async read() {
    return readJson(this.path, { intents: {}, fills: {}, carry: {}, events: [] });
  }

  async mutate(fn) {
    const data = await this.read();
    const result = fn(data);
    await writeJsonAtomic(this.path, data);
    return result;
  }

  async putIntent(intent) {
    return this.mutate((d) => {
      d.intents[intent.intentKey] = { ...intent };
    });
  }

  async getIntent(key) {
    return (await this.read()).intents[key];
  }

  async allIntents() {
    return Object.values((await this.read()).intents);
  }

  async intentsByStatus(status) {
    return (await this.allIntents()).filter((i) => i.status === status);
  }

  async updateIntent(key, patch) {
    return this.mutate((d) => {
      const existing = d.intents[key];
      if (!existing) return null;
      d.intents[key] = { ...existing, ...patch, updatedAtMs: Date.now() };
      return d.intents[key];
    });
  }

  async putFill(fill) {
    return this.mutate((d) => {
      d.fills[fill.id] = { ...fill };
    });
  }

  async allFills() {
    return Object.values((await this.read()).fills);
  }

  async putCarry(entry) {
    return this.mutate((d) => {
      d.carry[entry.id] = { ...entry };
    });
  }

  async allCarry() {
    return Object.values((await this.read()).carry);
  }

  async logEvent(event) {
    return this.mutate((d) => {
      d.events.push({ tsMs: Date.now(), ...event });
      // Bounded: this file is rewritten in full on every append, so an
      // unbounded event log would make each tick progressively slower.
      if (d.events.length > 500) d.events = d.events.slice(-500);
    });
  }

  async recentEvents(limit = 100) {
    return (await this.read()).events.slice(-limit).reverse();
  }

  async clearAll() {
    return this.mutate((d) => {
      d.intents = {};
      d.fills = {};
      d.carry = {};
      d.events = [];
    });
  }
}
