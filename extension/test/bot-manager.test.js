import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { runCommand } from '../src/core/commands.js';
import { ConfigStore } from '../src/storage/store.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { MANAGER_KEY, managerSnapshot, managerPoll, applyManagerControl, paperConfigStore } from '../src/core/bot-manager.js';

function deps() {
  return { store: new MemoryStore(), configStore: new ConfigStore(null), extensionVersion: '0.6.4',
    loadedSourceHash: 'a'.repeat(64), soltui: { request: async () => ({ ok: true, result: {
      schema_version: 1, controls: [], acknowledged: [], origin: `chrome-extension://${'a'.repeat(32)}`,
      transfer: { available: false, reason: 'owner_prepare_quiesce_snapshot_commit_unavailable' },
    } }) } };
}
async function command(d, operation='start', sequence=1) {
  const s = await managerSnapshot(d, { initialize: true });
  return { schema_version: 1, request_id: randomUUID(), installation_id: s.installation_id,
    native_id: 'grid', operation, expected_generation: s.generation, expected_config_hash: s.config_hash,
    expected_config_revision: s.config_revision, expected_runtime_id: s.runtime_id, sequence, expires_at: Date.now() / 1000 + 90 };
}

test('real storage wrapper persists a per-profile installation UUID without arming', async () => {
  const persisted = {};
  const area = { get: async key => ({ [key]: structuredClone(persisted[key]) }), set: async value => Object.assign(persisted, structuredClone(value)) };
  const a = deps(); a.configStore = new ConfigStore(area);
  const before = await managerSnapshot(a);
  assert.equal(before, null);
  await runCommand({ name: 'browserManagerPoll', args: {}, deps: a });
  const first = (await managerSnapshot(a)).installation_id;
  const restarted = { ...a, configStore: new ConfigStore(area) };
  assert.equal((await managerSnapshot(restarted)).installation_id, first);
  const b = deps(); await managerPoll(b);
  assert.notEqual((await managerSnapshot(b)).installation_id, first);
  assert.equal((await a.configStore.getRuntime()).armed, false);
  assert.equal(persisted[MANAGER_KEY].running, false);
});

test('owner control WAL replays receipt, preserves singleton and fences stale/transplanted controls', async () => {
  const d = deps(); const start = await command(d);
  const receipt = await applyManagerControl(d, start);
  assert.equal(receipt.outcome, 'acknowledged');
  assert.deepEqual(await applyManagerControl(d, start), receipt);
  assert.equal((await managerSnapshot(d)).running, true);
  assert.equal((await d.configStore.getRuntime()).armed, false);
  assert.equal((await paperConfigStore(d.configStore).getRuntime()).armed, true);
  const stale = { ...start, request_id: randomUUID(), sequence: 2 };
  assert.equal((await applyManagerControl(d, stale)).outcome, 'failed');
  await assert.rejects(applyManagerControl(d, { ...start, operation: 'stop' }), /binding conflict/);
  await assert.rejects(applyManagerControl(d, { ...start, secret: 'canary' }), /invalid owner control/);
  const stop = await command(d, 'stop', 3);
  assert.equal((await applyManagerControl(d, stop)).outcome, 'acknowledged');
  assert.equal((await managerSnapshot(d)).running, false);
  assert.equal((await paperConfigStore(d.configStore).getRuntime()).armed, false);
});

test('prepared control crash remains unknown and is never applied on restart', async () => {
  const d = deps(); const start = await command(d);
  const original = d.configStore.set.bind(d.configStore);
  let writes = 0;
  d.configStore.set = async (key, value) => {
    if (key === MANAGER_KEY && ++writes === 2) throw new Error('injected crash after prepare');
    return original(key, structuredClone(value));
  };
  await assert.rejects(applyManagerControl(d, start), /injected crash/);
  d.configStore.set = original;
  await managerPoll(d);
  assert.equal((await managerSnapshot(d)).running, false);
  assert.equal((await applyManagerControl(d, start)).outcome, 'unknown');
});

test('a paper grant cannot survive live config, kill, manual arm, or a later stop', async () => {
  const d = deps(); await applyManagerControl(d, await command(d));
  await d.configStore.setConfig({ mode: 'semi-auto' });
  assert.equal((await paperConfigStore(d.configStore).getRuntime()).armed, false);
  await managerSnapshot(d, { initialize: true });
  assert.equal((await managerSnapshot(d)).running, false);
  assert.equal((await d.configStore.getRuntime()).armed, false);
});

test('offline host never fabricates registration or receipts and secret storage never crosses protocol', async () => {
  const d = deps(); let message;
  await d.configStore.set('secrets', { apiKey: 'secret-canary-never-send' });
  d.soltui.request = async request => { message = request; throw new Error('offline'); };
  await assert.rejects(managerPoll(d), /offline/);
  assert.ok(!JSON.stringify(message).includes('secret-canary'));
  assert.equal((await managerSnapshot(d)).running, false);
});

test('a later stop revokes a fetched start and its replay cannot restart the slot', async () => {
  const d = deps();
  const start = await command(d, 'start', 1);
  const stop = { ...await command(d, 'stop', 2) };
  await applyManagerControl(d, start);
  assert.equal((await applyManagerControl(d, stop)).outcome, 'acknowledged');
  await applyManagerControl(d, start);
  assert.equal((await managerSnapshot(d)).running, false);
});

test('existing live owner and expired controls cannot masquerade as paper stopped', async () => {
  const d = deps();
  await d.configStore.setConfig({ mode: 'semi-auto' });
  const stop = await command(d, 'stop');
  assert.equal((await applyManagerControl(d, stop)).outcome, 'failed');
  const e = deps(); const expired = await command(e);
  expired.expires_at = Date.now() / 1000 - 1;
  assert.equal((await applyManagerControl(e, expired)).reason, 'browser_owner_expired');
});

test('changed loaded economic source revokes the old paper grant before another tick', async () => {
  const d = deps(); await applyManagerControl(d, await command(d));
  const before = await managerSnapshot(d);
  d.loadedSourceHash = 'b'.repeat(64);
  const after = await managerSnapshot(d, { initialize: true });
  assert.equal(after.running, false);
  assert.equal(after.generation, before.generation + 1);
  assert.equal(after.installation_id, before.installation_id);
  assert.equal((await d.configStore.getRuntime()).armed, false);
});
