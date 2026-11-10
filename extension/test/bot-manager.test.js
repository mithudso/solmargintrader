import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { runCommand, COMMANDS } from '../src/core/commands.js';
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
  const before = await execution(d);
  await runCommand({ name: 'browserManagerPoll', args: {}, deps: d });
  assert.deepEqual(await execution(d), before);
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

// These exercise the real registry lock and engine queue, rather than mocking
// lifecycle helpers: a paper registration has no authority over a legacy owner.
import { engineStopGeneration, stopEngine } from '../src/core/engine.js';
import { OWNER_SOURCE_FILES, OWNER_SOURCE_SCHEMA } from '../src/core/owner-source.js';
import fs from 'node:fs';

function reply(controls = [], acknowledged = []) {
  return { ok: true, result: { schema_version: 1, controls, acknowledged,
    origin: `chrome-extension://${'a'.repeat(32)}`, transfer: { available: false } } };
}
const poll = d => runCommand({ name: 'browserManagerPoll', args: {}, deps: d });
const execution = async d => {
  const s = await d.configStore.get(MANAGER_KEY);
  return { running: s.running, generation: s.generation, runtime_id: s.runtime_id,
    last_sequence: s.last_sequence, stopGeneration: engineStopGeneration(d.store), runtime: await d.configStore.getRuntime() };
};

test('registry registration and refused controls preserve armed legacy execution gate', async () => {
  for (const mode of ['dry-run', 'semi-auto']) {
    const d = deps(); await d.configStore.setConfig({ mode });
    await d.configStore.setRuntime({ armed: true });
    await poll(d);
    const before = await execution(d);
    assert.equal(before.stopGeneration, 0);
    await poll(d);
    assert.deepEqual(await execution(d), before);
    const stop = await command(d, 'stop');
    d.soltui.request = async () => reply([stop]);
    await poll(d);
    assert.equal((await d.configStore.get(MANAGER_KEY)).requests[stop.request_id].receipt.outcome, 'failed');
    assert.deepEqual(await execution(d), before);
  }
});

test('registry pending, lost acknowledgment, replay and expired/stale stops preserve exact execution state', async () => {
  const d = deps(); await poll(d);
  stopEngine(d.store);
  const stopped = await execution(d);
  await poll(d); // No delivered control cannot resume a previously stopped queue.
  assert.deepEqual(await execution(d), stopped);
  const start = await command(d);
  d.soltui.request = async () => reply([start]);
  await poll(d);
  const running = await execution(d);
  assert.equal(running.running, true);
  await poll(d); // Lost native acknowledgment resends the identical start.
  assert.deepEqual(await execution(d), running);
  for (const kind of ['expired', 'stale']) {
    const stop = await command(d, 'stop', 2);
    if (kind === 'expired') stop.expires_at = Date.now() / 1000 - 1;
    else stop.expected_generation += 10;
    d.soltui.request = async () => reply([stop]);
    await poll(d);
    assert.equal((await d.configStore.get(MANAGER_KEY)).requests[stop.request_id].receipt.outcome, 'failed');
    assert.deepEqual(await execution(d), running);
  }
  const stop = await command(d, 'stop', 3);
  d.soltui.request = async () => reply([stop]);
  await poll(d);
  const final = await execution(d);
  assert.equal(final.running, false);
  assert.equal(final.stopGeneration, running.stopGeneration + 1);
  await poll(d);
  assert.deepEqual(await execution(d), final);
});

test('source identity covers canonical economics and every shipped JavaScript module', () => {
  assert.equal(OWNER_SOURCE_SCHEMA, 2);
  const extension = new URL('../', import.meta.url);
  const actual = fs.readdirSync(new URL('src/', extension), { recursive: true }).filter(p => p.endsWith('.js')).map(p => `src/${p}`);
  assert.deepEqual([...OWNER_SOURCE_FILES].sort(), ['manifest.json', ...actual].sort());
  for (const file of ['src/core/engine.js', 'src/core/grid.js', 'src/core/risk.js', 'src/core/pnl.js', 'src/storage/store.js']) {
    assert.ok(OWNER_SOURCE_FILES.includes(file), file);
  }
});

test('source validation failure refuses effective paper permission before a tick', async () => {
  const d = deps(); await applyManagerControl(d, await command(d));
  const guarded = paperConfigStore(d.configStore, async () => { throw new Error('extension reload required'); });
  await assert.rejects(guarded.getRuntime(), /reload required/);
  assert.equal((await d.configStore.getRuntime()).armed, false);
});


test('registry owner snapshot stays read-only and never initializes or revokes durable state', async () => {
  const d = deps();
  assert.equal(COMMANDS.browserManagerSnapshot.readOnly, true);
  assert.equal((await runCommand({ name: 'browserManagerSnapshot', deps: d })).snapshot, null);
  assert.equal(await d.configStore.get(MANAGER_KEY, null), null);
  await applyManagerControl(d, await command(d));
  const before = structuredClone(await d.configStore.get(MANAGER_KEY));
  d.loadedSourceHash = async options => {
    assert.equal(options.revoke, false);
    throw new Error('extension reload required');
  };
  await assert.rejects(runCommand({ name: 'browserManagerSnapshot', deps: d }), /reload required/);
  assert.deepEqual(await d.configStore.get(MANAGER_KEY), before);
});


test('valid stop-first revokes an earlier fetched start and replays after owner restart', async () => {
  const d = deps();
  const start = await command(d, 'start', 1);
  const stop = await command(d, 'stop', 2);
  const before = await execution(d);
  const receipt = await applyManagerControl(d, stop);
  assert.equal(receipt.outcome, 'skipped');
  assert.equal(receipt.reason, 'already_stopped');
  assert.deepEqual(await execution(d), { ...before, last_sequence: 2 });
  const restarted = { ...d, store: new MemoryStore() };
  assert.deepEqual(await applyManagerControl(restarted, stop), receipt);
  const late = await applyManagerControl(restarted, start);
  assert.equal(late.reason, 'revoked_by_later_stop');
  assert.deepEqual(await execution(restarted), { ...before, last_sequence: 2 });
  assert.deepEqual(await applyManagerControl(restarted, start), late);
});

test('registry stop-first fence survives lost acknowledgment, late start and owner restart', async () => {
  const d = deps(); await poll(d);
  const start = await command(d, 'start', 1);
  const stop = await command(d, 'stop', 2);
  const before = await execution(d);
  d.soltui.request = async () => reply([stop]);
  await poll(d);
  const stopped = await execution(d);
  assert.deepEqual(stopped, { ...before, last_sequence: 2 });
  const savedReceipt = (await d.configStore.get(MANAGER_KEY)).requests[stop.request_id].receipt;
  await poll(d); // Host did not acknowledge the receipt; same stop is replayed.
  assert.deepEqual(await execution(d), stopped);
  const restarted = { ...d, store: new MemoryStore() };
  let sent;
  restarted.soltui.request = async request => { sent = request; return reply([start, stop]); };
  await poll(restarted);
  assert.ok(sent.message.receipts.some(r => r.request_id === stop.request_id && r.reason === 'already_stopped'));
  const state = await restarted.configStore.get(MANAGER_KEY);
  assert.deepEqual(state.requests[stop.request_id].receipt, savedReceipt);
  assert.equal(state.requests[start.request_id].receipt.reason, 'revoked_by_later_stop');
  assert.deepEqual(await execution(restarted), stopped);
  restarted.soltui.request = async () => reply([start], [stop.request_id, start.request_id]);
  await poll(restarted);
  assert.deepEqual(await execution(restarted), stopped);
  assert.equal((await restarted.configStore.get(MANAGER_KEY)).requests[stop.request_id].delivered, true);
});

test('expired, stale and unbound stop-first requests cannot revoke a valid fetched start', async () => {
  for (const kind of ['expired', 'stale', 'unbound']) {
    const d = deps(); const start = await command(d, 'start', 1);
    const stop = await command(d, 'stop', 2);
    if (kind === 'expired') stop.expires_at = Date.now() / 1000 - 1;
    if (kind === 'stale') stop.expected_generation += 1;
    if (kind === 'unbound') stop.installation_id = randomUUID();
    const before = await execution(d);
    if (kind === 'unbound') await assert.rejects(applyManagerControl(d, stop), /invalid owner control/);
    else assert.equal((await applyManagerControl(d, stop)).outcome, 'failed');
    assert.deepEqual(await execution(d), before);
    assert.equal((await applyManagerControl(d, start)).outcome, 'acknowledged');
  }
});
