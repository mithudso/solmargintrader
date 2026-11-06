import test from 'node:test';
import assert from 'node:assert/strict';

import { MemoryStore } from '../src/storage/memoryStore.js';

/**
 * The service worker registers chrome listeners at import time and builds its
 * ConfigStore from chrome.storage.local, so a chrome stub must exist BEFORE the
 * module loads. One in-memory area is shared by the module's ConfigStore and
 * the assertions below; `reset()` wipes it between tests.
 */
const area = new Map();
const alarms = { created: [], cleared: [] };
const listeners = {};

globalThis.chrome = {
  storage: {
    local: {
      async get(key) {
        const keys = Array.isArray(key) ? key : [key];
        return Object.fromEntries(keys.filter((k) => area.has(k)).map((k) => [k, area.get(k)]));
      },
      async set(obj) {
        for (const [k, v] of Object.entries(obj)) area.set(k, v);
      },
    },
  },
  runtime: { onInstalled: { addListener: (fn) => (listeners.installed = fn) }, onStartup: { addListener() {} }, onMessage: { addListener() {} } },
  alarms: {
    onAlarm: { addListener() {} },
    async clear(name) {
      alarms.cleared.push(name);
    },
    async create(name, info) {
      alarms.created.push({ name, info });
    },
  },
  action: { async setBadgeText() {}, async setBadgeBackgroundColor() {} },
};

const { handleInstalled, handleMessage } = await import('../src/bg/service-worker.js');

const reset = () => {
  area.clear();
  alarms.created.length = 0;
  alarms.cleared.length = 0;
};

const runtimeOf = () => area.get('runtime') ?? {};
const configOf = () => area.get('config') ?? {};

// ------------------------------------------------------------ TASK-406 -----

test('a routine update does not clear a latched kill switch or the stored mode', async () => {
  reset();
  area.set('runtime', { armed: true, killSwitch: true });
  area.set('config', { mode: 'semi-auto' });
  const store = new MemoryStore();

  await handleInstalled({ reason: 'update', previousVersion: '0.0.9' }, { store });

  assert.equal(runtimeOf().killSwitch, true, 'an update must never release a hard stop');
  assert.equal(runtimeOf().armed, false, 'an update fails safe: the operator re-arms deliberately');
  assert.equal(configOf().mode, 'semi-auto', 'the operator’s configured mode is kept');
});

test('chrome_update behaves like update', async () => {
  reset();
  area.set('runtime', { armed: true, killSwitch: true });
  area.set('config', { mode: 'full-auto' });
  await handleInstalled({ reason: 'chrome_update' }, { store: new MemoryStore() });
  assert.equal(runtimeOf().killSwitch, true);
  assert.equal(runtimeOf().armed, false);
  assert.equal(configOf().mode, 'full-auto');
});

test('a fresh install applies the safe defaults', async () => {
  reset();
  area.set('runtime', { armed: true, killSwitch: true });
  area.set('config', { mode: 'full-auto' });
  await handleInstalled({ reason: 'install' }, { store: new MemoryStore() });
  assert.equal(runtimeOf().armed, false);
  assert.equal(runtimeOf().killSwitch, false);
  assert.equal(configOf().mode, 'dry-run');
});

test('an update still reschedules the alarm and records a lifecycle event', async () => {
  reset();
  area.set('runtime', { armed: true, killSwitch: true });
  const store = new MemoryStore();
  await handleInstalled({ reason: 'update', previousVersion: '0.0.9' }, { store });

  assert.equal(alarms.created.length, 1, 'the alarm must be re-created after an update');
  assert.equal(alarms.created[0].name, 'solmargintrader-tick');
  const [event] = await store.recentEvents(1);
  assert.equal(event.type, 'updated');
  assert.equal(event.previousVersion, '0.0.9');
  assert.equal(event.killSwitch, true);
  assert.equal(event.armed, false);
});

test('a failing event log cannot stop the disarm from landing', async () => {
  reset();
  area.set('runtime', { armed: true, killSwitch: false });
  const broken = {
    async logEvent() {
      throw new Error('indexeddb unavailable');
    },
  };
  const warn = console.warn;
  console.warn = () => {};
  try {
    await handleInstalled({ reason: 'update' }, { store: broken });
  } finally {
    console.warn = warn;
  }
  assert.equal(runtimeOf().armed, false);
});

test('the registered onInstalled listener passes the details through', () => {
  assert.equal(typeof listeners.installed, 'function');
  assert.ok(listeners.installed.length >= 1, 'the listener must accept the details argument');
});

// ------------------------------------------------------------ TASK-404 -----

test('createSessionKey sent as a message receives its passphrase and succeeds', async () => {
  reset();
  const passphrase = 'correct horse battery staple';
  const store = new MemoryStore();

  const res = await handleMessage({ type: 'createSessionKey', passphrase }, { openStore: async () => store });

  assert.equal(res.ok, true, `expected success, got ${JSON.stringify(res)}`);
  assert.ok(res.pubkeyBs58, 'the public key is returned');
  assert.ok(area.get('sessionKeyVault')?.vault, 'the sealed vault is stored in chrome.storage.local');
  assert.ok(
    !JSON.stringify(res).includes(passphrase),
    'the response body must never echo the passphrase',
  );
  assert.ok(
    !JSON.stringify([...area.entries()]).includes(passphrase),
    'the passphrase must not be persisted anywhere',
  );
});

test('a too-short passphrase is refused by the command, not swallowed', async () => {
  reset();
  const res = await handleMessage({ type: 'createSessionKey', passphrase: 'short' }, { openStore: async () => new MemoryStore() });
  assert.equal(res.ok, false);
  assert.match(res.error, /at least 12 characters/);
  assert.ok(!area.has('sessionKeyVault'));
});

test('a command that does not declare passphrase still receives no passphrase arg', async () => {
  reset();
  // `status` declares no params: forwarding a passphrase would make runCommand
  // reject it as an unknown argument.
  const res = await handleMessage({ type: 'status', passphrase: 'correct horse battery staple' }, { openStore: async () => new MemoryStore() });
  assert.equal(res.ok, true, `expected success, got ${JSON.stringify(res)}`);
});
