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

import { readFile, writeFile, rename, mkdir, realpath, lstat, unlink, rmdir } from 'node:fs/promises';
import { constants } from 'node:fs';
import { dirname, basename, join, resolve } from 'node:path';
import { homedir } from 'node:os';
import { randomUUID } from 'node:crypto';
import { AsyncLocalStorage } from 'node:async_hooks';

export const DEFAULT_DATA_DIR = join(homedir(), '.solmargintrader');
export const DEFAULT_STORE_PATH = join(DEFAULT_DATA_DIR, 'journal.json');
export const DEFAULT_CONFIG_PATH = join(DEFAULT_DATA_DIR, 'config.json');

const pathQueues = new Map();
const leaseContext = new AsyncLocalStorage();
const isRecord = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const storageError = (code, message) => Object.assign(new Error(message), { code });
const pathChanged = () => storageError('FILE_STORE_PATH_CHANGED', 'File storage path changed during an operation');

function validateRecord(value) {
  if (!isRecord(value)) throw storageError('FILE_STORE_INVALID_SHAPE', 'Stored data has an invalid shape; refusing to overwrite it');
  return value;
}

function validateJournal(value) {
  validateRecord(value);
  for (const key of ['intents', 'fills', 'carry']) {
    if (!Object.hasOwn(value, key)) validateRecord(null);
    validateRecord(value[key]);
    for (const entry of Object.values(value[key])) validateRecord(entry);
  }
  if (!Array.isArray(value.events) || !value.events.every(isRecord)) validateRecord(null);
  return value;
}

async function canonicalPath(path, createParent = false) {
  const absolute = resolve(path);
  if (createParent) await mkdir(dirname(absolute), { recursive: true, mode: 0o700 });
  try {
    const canonical = await realpath(absolute);
    const identity = await lstat(canonical);
    // Hard links have different path leases, then diverge when rename replaces
    // either directory entry. Refuse them rather than claim shared ownership.
    if (!identity.isFile() || identity.nlink !== 1) {
      throw storageError('FILE_STORE_UNSAFE_PATH', 'File storage requires a regular file with one directory entry');
    }
    return canonical;
  }
  catch (error) {
    if (error.code !== 'ENOENT') throw error;
    // A dangling symlink must not turn into a new journal under another identity.
    try {
      if ((await lstat(absolute)).isSymbolicLink()) throw pathChanged();
    } catch (missing) { if (missing.code !== 'ENOENT') throw missing; }
    try { return join(await realpath(dirname(absolute)), basename(absolute)); }
    catch (missing) {
      if (missing.code !== 'ENOENT') throw missing;
      return absolute;
    }
  }
}

async function assertPath(path, expected) {
  if (await canonicalPath(path) !== expected || await canonicalPath(expected) !== expected) throw pathChanged();
}

async function readPath(path) {
  const context = leaseContext.getStore();
  const bound = context?.aliases.get(resolve(path));
  if (bound && context.leases.get(bound)?.active) { await assertPath(path, bound); return bound; }
  return canonicalPath(path);
}

async function checkedStorePath(store) {
  if (store.canonicalIdentity) await assertPath(store.requestedPath, store.canonicalIdentity);
  return store.requestedPath;
}

async function readJson(path, fallback, validate = validateRecord) {
  try {
    // The final component cannot become a symlink between canonicalisation and open.
    return validate(JSON.parse(await readFile(path, { encoding: 'utf8', flag: constants.O_RDONLY | constants.O_NOFOLLOW })));
  } catch (err) {
    if (err.code === 'ENOENT') return fallback;
    if (err instanceof SyntaxError) {
      // V8 may quote malformed input in SyntaxError.message, including a secret.
      throw storageError('FILE_STORE_INVALID_JSON', 'Stored data is not valid JSON; refusing to overwrite it');
    }
    throw err;
  }
}

async function writeJsonAtomic(path, value, requestedPath = path) {
  const tmp = `${path}.${process.pid}.${randomUUID()}.tmp`;
  try {
    await writeFile(tmp, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600, flag: 'wx' });
    await assertPath(requestedPath, path);
    await rename(tmp, path);
  } finally {
    try { await unlink(tmp); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
}

function queuePath(path, operation) {
  const result = (pathQueues.get(path) ?? Promise.resolve()).then(operation);
  const tail = result.catch(() => {});
  pathQueues.set(path, tail);
  tail.then(() => { if (pathQueues.get(path) === tail) pathQueues.delete(path); });
  return result;
}

async function acquireLease(path) {
  const directory = `${path}.lock`;
  try { await mkdir(directory, { mode: 0o700 }); }
  catch (error) {
    if (error.code === 'EEXIST') throw storageError('FILE_STORE_BUSY', 'File storage is locked by another owner; recovery requires owner review');
    throw error;
  }
  const identity = await lstat(directory);
  const token = randomUUID();
  const ownerPath = join(directory, 'owner.json');
  // A crash leaves this directory intact. PID liveness and elapsed time never
  // establish that a possibly submitted order is safe to repeat.
  await writeFile(ownerPath, `${JSON.stringify({ version: 1, pid: process.pid, token, createdAtMs: Date.now() })}\n`,
    { mode: 0o600, flag: 'wx' });
  return { directory, ownerPath, identity, token, active: true, mutationTail: Promise.resolve() };
}

async function releaseLease(lease) {
  lease.active = false;
  const lost = () => storageError('FILE_STORE_LEASE_LOST', 'File storage lease identity changed; owner review is required');
  let identity, owner;
  try {
    identity = await lstat(lease.directory);
    owner = await readJson(lease.ownerPath, null);
  } catch { throw lost(); }
  if (!identity.isDirectory() || identity.ino !== lease.identity.ino || identity.dev !== lease.identity.dev || owner?.token !== lease.token) throw lost();
  await unlink(lease.ownerPath);
  await rmdir(lease.directory);
}

async function withPathLease(path, operation) {
  const absolute = resolve(path);
  const inherited = leaseContext.getStore();
  const bound = inherited?.aliases.get(absolute);
  const canonical = bound && inherited.leases.get(bound)?.active ? bound : await canonicalPath(path, true);
  await assertPath(path, canonical);
  const existing = inherited?.leases.get(canonical);
  const contextFor = lease => {
    // Detached async work can retain a completed owner's context. It must claim
    // a fresh lease rather than inherit that owner's alias or mutation marker.
    const leases = new Map([...(inherited?.leases ?? [])].filter(([, owner]) => owner.active));
    const aliases = new Map([...(inherited?.aliases ?? [])].filter(([, key]) => leases.has(key)));
    const mutating = new Set([...(inherited?.mutating ?? [])].filter(key => leases.has(key)));
    leases.set(canonical, lease); aliases.set(absolute, canonical);
    return { leases, aliases, mutating };
  };
  if (existing?.active) return leaseContext.run(contextFor(existing), () => operation(existing, canonical));
  return queuePath(canonical, async () => {
    await assertPath(path, canonical);
    const lease = await acquireLease(canonical);
    try { return await leaseContext.run(contextFor(lease), () => operation(lease, canonical)); }
    finally {
      await lease.mutationTail;
      await releaseLease(lease);
    }
  });
}

function mutatePath(path, operation) {
  return withPathLease(path, (lease, canonical) => {
    const context = leaseContext.getStore();
    if (context.mutating.has(canonical)) throw storageError('FILE_STORE_NESTED_MUTATION', 'A file mutation cannot nest another mutation of the same journal');
    const result = lease.mutationTail.then(() => leaseContext.run({ ...context,
      mutating: new Set([...context.mutating, canonical]) }, async () => {
      await assertPath(path, canonical);
      return operation(canonical);
    }));
    lease.mutationTail = result.catch(() => {});
    return result;
  });
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
      const canonical = await readPath(path);
      if (!leaseContext.getStore()?.leases.get(canonical)?.active) {
        try {
          await lstat(`${canonical}.lock`);
          throw storageError('FILE_STORE_BUSY', 'Configuration is being updated; execution must wait for a fresh read');
        } catch (error) { if (error.code !== 'ENOENT') throw error; }
      }
      const all = await readJson(canonical, {});
      if (keys == null) return all;
      const list = Array.isArray(keys) ? keys : [keys];
      return Object.fromEntries(list.map((k) => [k, Object.hasOwn(all, k) ? all[k] : undefined]));
    },
    async set(obj) {
      validateRecord(obj);
      return mutatePath(path, async canonical => {
        const all = await readJson(canonical, {});
        await writeJsonAtomic(canonical, { ...all, ...obj }, path);
      });
    },
    async update(key, update) {
      return mutatePath(path, async canonical => {
        const all = await readJson(canonical, {});
        const next = update(Object.hasOwn(all, key) ? all[key] : undefined);
        await writeJsonAtomic(canonical, { ...all, [key]: next }, path);
        return next;
      });
    },
  };
}

/** Store API over a single JSON file. */
export class FileStore {
  /** Engine clients use open() to share the canonical path and immediate-stop queue. */
  constructor(path = DEFAULT_STORE_PATH) {
    this.path = resolve(path);
    this.requestedPath = this.path;
    this.canonicalIdentity = null;
  }

  static async open(path) {
    const store = new FileStore(path);
    await store.read(); // surface a corrupt journal now, not mid-tick
    store.path = await canonicalPath(store.requestedPath, true);
    store.canonicalIdentity = store.path;
    return store;
  }

  async read() {
    return readJson(await readPath(await checkedStorePath(this)), { intents: {}, fills: {}, carry: {}, events: [] }, validateJournal);
  }

  /** Hold one owner across reconcile, planning, write-ahead and submission.
   * Existing `.lock` directories are never stolen or cleared automatically.
   * Recovery requires stopping all owners and reviewing ambiguous submissions
   * before a human removes the exact stale directory. Never delete the journal.
   */
  async withExecutionLease(operation) {
    return withPathLease(await checkedStorePath(this), () => operation());
  }

  async mutate(fn) {
    return mutatePath(await checkedStorePath(this), async canonical => {
      const data = await readJson(canonical, { intents: {}, fills: {}, carry: {}, events: [] }, validateJournal);
      const result = await fn(data);
      validateJournal(data);
      await writeJsonAtomic(canonical, data, this.requestedPath);
      return result;
    });
  }

  async putIntent(intent) {
    return this.mutate((d) => {
      d.intents = { ...d.intents, [intent.intentKey]: { ...intent } };
    });
  }

  async getIntent(key) {
    const intents = (await this.read()).intents;
    return Object.hasOwn(intents, key) ? intents[key] : undefined;
  }

  async allIntents() {
    return Object.values((await this.read()).intents);
  }

  async intentsByStatus(status) {
    return (await this.allIntents()).filter((i) => i.status === status);
  }

  async updateIntent(key, patch) {
    return this.mutate((d) => {
      const existing = Object.hasOwn(d.intents, key) ? d.intents[key] : null;
      if (!existing) return null;
      d.intents[key] = { ...existing, ...patch, updatedAtMs: Date.now() };
      return d.intents[key];
    });
  }

  async putFill(fill) {
    return this.mutate((d) => {
      d.fills = { ...d.fills, [fill.id]: { ...fill } };
    });
  }

  async allFills() {
    return Object.values((await this.read()).fills);
  }

  async putCarry(entry) {
    return this.mutate((d) => {
      d.carry = { ...d.carry, [entry.id]: { ...entry } };
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
