import test from 'node:test';
import assert from 'node:assert/strict';

import { MemoryStore } from '../src/storage/memoryStore.js';
import { withStoreLock } from '../src/core/engine.js';
import { SoltuiTransportError } from '../src/core/soltui.js';
import { fakeHandle } from '../e2e/fixtures/fake-soltui-registry.js';

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

const { handleInstalled, handleMessage, runBuildCheck } = await import('../src/bg/service-worker.js');

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

  const tickAlarms = alarms.created.filter((a) => a.name === 'solmargintrader-tick');
  assert.equal(tickAlarms.length, 1, 'the alarm must be re-created after an update');
  const buildAlarms = alarms.created.filter((a) => a.name === 'solmargintrader-soltui-build');
  assert.equal(buildAlarms.length, 1, 'the soltui build probe alarm must be re-created after an update');
  assert.equal(buildAlarms[0].info.periodInMinutes, 1);
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

// ------------------------------------------------------- soltui bridge -----

const H1 = '1'.repeat(64);
const H2 = '2'.repeat(64);
const hostReporting = (hash) => ({ request: async (request) => fakeHandle(request, { hash }) });

test('a soltuiCall message returns soltui\'s envelope as `result`, not spread over ok/error', async () => {
  reset();
  const soltui = hostReporting(H1);
  const res = await handleMessage({ type: 'soltuiCall', command: 'demo.echo', params: { text: 'x' } }, { openStore: async () => new MemoryStore(), soltui });
  assert.deepEqual(res, { ok: true, result: fakeHandle({ op: 'call', command: 'demo.echo', params: { text: 'x' } }) });
});

test('a soltui refusal inside the envelope does not turn the message response into an error', async () => {
  reset();
  const res = await handleMessage({ type: 'soltuiCall', command: 'demo.resume' }, { openStore: async () => new MemoryStore(), soltui: hostReporting(H1) });
  assert.equal(res.ok, true);
  assert.equal(res.result.ok, false);
  assert.equal(res.result.error.code, 'forbidden');
});

test('a message with the host missing gets a clean failed envelope', async () => {
  reset();
  const soltui = { request: async () => { throw new SoltuiTransportError('failed', 'soltui native host "com.mitchhudson.soltui" is not available; install it'); } };
  const res = await handleMessage({ type: 'soltuiCommands' }, { openStore: async () => new MemoryStore(), soltui });
  assert.equal(res.ok, true);
  assert.equal(res.result.ok, false);
  assert.equal(res.result.error.code, 'failed');
});

test('runBuildCheck: first observation stores the hash, a change on an idle engine reloads', async () => {
  reset();
  const store = new MemoryStore();
  const reloads = [];
  const common = { store, reload: () => reloads.push(1), hold: async () => {} };
  assert.equal(await runBuildCheck({ ...common, soltui: hostReporting(H1) }), 'first-observation');
  assert.equal(await runBuildCheck({ ...common, soltui: hostReporting(H1) }), 'unchanged');
  assert.equal(reloads.length, 0);
  assert.equal(await runBuildCheck({ ...common, soltui: hostReporting(H2) }), 'reloaded');
  assert.equal(reloads.length, 1);
  assert.equal(area.get('soltuiBuild').hash, H2);
  const events = await store.recentEvents(5);
  const reload = events.find((e) => e.type === 'auto-reload');
  assert.ok(reload, 'the reload is in the existing event log');
  assert.equal(reload.armed, false);
  assert.deepEqual(Object.keys(reload).sort(), ['armed', 'from', 'killSwitch', 'to', 'tsMs', 'type'].sort());
});

test('runBuildCheck: no reload while the real engine lock is busy, then reload once it is idle', async () => {
  reset();
  const store = new MemoryStore();
  const reloads = [];
  const common = { store, reload: () => reloads.push(1), hold: async () => {} };
  await runBuildCheck({ ...common, soltui: hostReporting(H1) });
  let finish;
  const tick = withStoreLock(store, () => new Promise((resolve) => { finish = resolve; }));
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(await runBuildCheck({ ...common, soltui: hostReporting(H2) }), 'deferred-busy');
  assert.equal(reloads.length, 0);
  finish();
  await tick;
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(await runBuildCheck({ ...common, soltui: hostReporting(H2) }), 'reloaded');
  assert.equal(reloads.length, 1);
});

test('runBuildCheck: an unreachable host never reloads', async () => {
  reset();
  const reloads = [];
  const down = { request: async () => { throw new SoltuiTransportError('failed', 'down'); } };
  assert.equal(await runBuildCheck({ store: new MemoryStore(), reload: () => reloads.push(1), soltui: down }), 'host-unreachable');
  assert.equal(reloads.length, 0);
});

test('runBuildCheck preserves dashboard session state until its lease ends', async () => {
  reset();
  const reloads = [];
  const common = { store: new MemoryStore(), reload: () => reloads.push(1), hold: async () => {} };
  await runBuildCheck({ ...common, soltui: hostReporting(H1) });
  const host = { ...hostReporting(H2), busy: () => true };
  assert.equal(await runBuildCheck({ ...common, soltui: host }), 'deferred-busy');
  assert.equal(area.get('soltuiBuild').hash, H1, 'deferred update must not be forgotten');
  assert.equal(reloads.length, 0);
  host.busy = () => false;
  assert.equal(await runBuildCheck({ ...common, soltui: host }), 'reloaded');
  assert.equal(reloads.length, 1);
});


test('Chrome paper orders and fills survive dependency and worker recreation', async () => {
  reset();
  const { chromeDeps } = await import('../src/bg/service-worker.js');
  const first = await (await chromeDeps({openStore: async () => new MemoryStore()})).buildVenue();
  const receipt = await first.placeOrder({intent: {intentKey: 'paper-restart', side:'buy', level:100, baseQty:0.1}, slippageBps:50});
  const second = await (await chromeDeps({openStore: async () => new MemoryStore()})).buildVenue();
  assert.equal((await second.getOpenOrders())[0]?.venueOrderId, receipt.venueOrderId);
  second.markPrice(99);
  assert.equal((await second.getFills()).length, 1);
  const restarted = await import('../src/bg/service-worker.js?paper-restart');
  const third = await (await restarted.chromeDeps({openStore: async () => new MemoryStore()})).buildVenue();
  assert.equal((await third.getOpenOrders()).length, 0);
  assert.equal((await third.getFills())[0]?.venueOrderId, receipt.venueOrderId);
  area.set('config', {...configOf(), baseMint:'other-mint'});
  const other = await (await restarted.chromeDeps({openStore: async () => new MemoryStore()})).buildVenue();
  assert.deepEqual(await other.getFills(), []);
  assert.deepEqual(await other.getOpenOrders(), []);
});

test('startup resource baseline fences changed economic code until a worker reload', async () => {
  reset();
  const oldFetch = globalThis.fetch;
  const oldURL = chrome.runtime.getURL;
  const oldManifest = chrome.runtime.getManifest;
  let engineSource = 'engine-v1';
  chrome.runtime.getURL = path => `chrome-extension://${'a'.repeat(32)}/${path}`;
  chrome.runtime.getManifest = () => ({ version: '0.6.4' });
  globalThis.fetch = async url => ({ ok: true, text: async () => url.endsWith('/engine.js') ? engineSource : String(url) });
  try {
    const worker = await import('../src/bg/service-worker.js?source-fence-regression');
    const deps = await worker.chromeDeps({ openStore: async () => new MemoryStore() });
    const baseline = await deps.loadedSourceHash();
    assert.match(baseline, /^[a-f0-9]{64}$/);
    area.set('browserManager', { running: true, generation: 7 });
    engineSource = 'engine-v2';
    await assert.rejects(deps.loadedSourceHash(), /extension reload required/);
    assert.equal(area.get('browserManager').running, false);
    assert.equal(area.get('browserManager').generation, 8);
    engineSource = 'engine-v1';
    // A resource rollback cannot certify what this worker actually loaded.
    await assert.rejects(deps.loadedSourceHash(), /extension reload required/);
    assert.equal(area.get('browserManager').generation, 8);
  } finally {
    globalThis.fetch = oldFetch;
    chrome.runtime.getURL = oldURL;
    chrome.runtime.getManifest = oldManifest;
  }
});
