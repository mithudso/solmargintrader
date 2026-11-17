import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
import { mkdtemp, readFile, writeFile, readdir, rm, stat, symlink, link, unlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn } from 'node:child_process';
import { FileStore, createFileArea } from '../src/storage/fileStore.js';
import { withStoreLock, stopEngine, engineStopGeneration } from '../src/core/engine.js';

const emptyJournal = () => ({ intents: {}, fills: {}, carry: {}, events: [] });
const readJson = async path => JSON.parse(await readFile(path, 'utf8'));

async function fixture(t) {
  const directory = await mkdtemp(join(tmpdir(), 'smt-file-store-safety-'));
  const children = [];
  t.after(async () => {
    for (const child of children) {
      if (child.process.exitCode === null && child.process.signalCode === null) child.process.kill();
      await child.exit;
    }
    await rm(directory, { recursive: true, force: true });
  });
  return { directory, path: join(directory, 'journal.json'), children };
}

// Every venue operation is synthetic IPC. No real builder, signer or owner state is
// loaded; mode vectors and permission flags exist only in temporary fixtures.
const childSource = `
  import { FileStore, createFileArea } from ${JSON.stringify(new URL('../src/storage/fileStore.js', import.meta.url).href)};
  import { tick } from ${JSON.stringify(new URL('../src/core/engine.js', import.meta.url).href)};
  import { runCommand } from ${JSON.stringify(new URL('../src/core/commands.js', import.meta.url).href)};
  import { ConfigStore } from ${JSON.stringify(new URL('../src/storage/store.js', import.meta.url).href)};
  globalThis.fetch = async () => { throw new Error('Offline test forbids fetch'); };
  const [path, action] = process.argv.slice(1);
  let release;
  const released = new Promise(resolve => { release = resolve; });
  process.on('message', message => { if (message.type === 'release') release(); });
  let submissions = 0;
  try {
    const store = action === 'config-hold' ? new FileStore(path) : await FileStore.open(path);
    let result;
    if (action === 'hold' || action === 'mutation-hold' || action === 'config-hold') {
      const operation = async data => {
        process.send({ type: 'held' });
        await released;
        if (data) data.fills['synthetic-owner-fill'] = { id: 'synthetic-owner-fill' };
        else await store.putFill({ id: 'synthetic-owner-fill' });
      };
      result = action === 'mutation-hold' ? await store.mutate(operation) : await store.withExecutionLease(operation);
    } else if (action === 'fill') {
      await store.putFill({ id: 'synthetic-other-process-fill' });
    } else if (action === 'area') {
      await createFileArea(path).set({ syntheticConfig: true });
    } else {
      const configStore = ['tick-config-hold', 'tick-journal-hold', 'tick-permission-hold'].includes(action) ? new ConfigStore(createFileArea(path + '.config.json')) : new ConfigStore();
      await configStore.setConfig({ mode: action === 'tick-permission-hold' ? 'full-auto' : 'dry-run', gridId: 'synthetic-process-rung',
        lower: 90, upper: 110, rungs: ['tick-config-hold', 'tick-journal-hold', 'tick-permission-hold'].includes(action) ? 7 : 2, spacing: 'arith', notionalPerRungUsd: 12 });
      if (!['tick-config-hold', 'tick-journal-hold', 'tick-permission-hold'].includes(action)) await configStore.setRuntime({ armed: true, killSwitch: false });
      if (action === 'tick-journal-hold') {
        const writeIntent = store.putIntent.bind(store);
        store.putIntent = async intent => {
          await writeIntent(intent);
          process.send({ type: 'journal-persisted' });
          await released;
        };
      }
      if (action === 'tick-permission-hold') {
        let written = false, afterRuntime = false, paused = false;
        const putIntent = store.putIntent.bind(store);
        store.putIntent = async intent => { await putIntent(intent); written = true; };
        const getRuntime = configStore.getRuntime.bind(configStore);
        configStore.getRuntime = async () => { const value = await getRuntime(); if (written) afterRuntime = true; return value; };
        const getConfig = configStore.getConfig.bind(configStore);
        configStore.getConfig = async () => {
          const value = await getConfig();
          if (afterRuntime && !paused) { paused = true; process.send({ type: 'permission-read' }); await released; }
          return value;
        };
      }
      const venue = { kind: 'spot', getPrice: async () => 100,
        getOpenOrders: async () => [], getFills: async () => [],
        placeOrder: async ({ intent }) => {
          submissions++;
          process.send({ type: 'fake-submit', intentKey: intent.intentKey });
          if (action === 'tick-hold' || (action === 'tick-config-hold' && submissions === 1)) await released;
          return { venueOrderId: 'synthetic-order', simulated: true };
        } };
      result = action === 'tick-permission-hold'
        ? await runCommand({ name: 'tick', deps: { store, configStore, buildVenue: async () => venue } })
        : await tick({ venue, store, configStore });
    }
    process.send({ type: 'done', ok: true, submissions, result }, () => process.disconnect());
  } catch (error) {
    process.send({ type: 'done', ok: false, submissions, code: error.code,
      message: error.message }, () => process.disconnect());
  }
`;

function launch(f, action, path = f.path) {
  const child = spawn(process.execPath, ['--input-type=module', '-e', childSource, path, action],
    { stdio: ['ignore', 'pipe', 'pipe', 'ipc'] });
  const messages = [], waiters = [];
  let output = '';
  child.stdout.on('data', chunk => { output += chunk; });
  child.stderr.on('data', chunk => { output += chunk; });
  child.on('message', message => {
    messages.push(message);
    for (const waiter of waiters) if (waiter.type === message.type) waiter.resolve(message);
  });
  const exit = new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('exit', (code, signal) => {
      for (const waiter of waiters) {
        if (!messages.some(m => m.type === waiter.type)) waiter.reject(new Error(`Child exited before ${waiter.type}: ${output}`));
      }
      resolve({ code, signal, output });
    });
  });
  const launched = { process: child, messages, exit, waitFor(type) {
    const existing = messages.find(m => m.type === type);
    return existing ? Promise.resolve(existing) : new Promise((resolve, reject) => { waiters.push({ type, resolve, reject }); });
  } };
  f.children.push(launched);
  return launched;
}

test('malformed JSON refuses reads and writes without echoing stored bytes', async t => {
  const f = await fixture(t);
  const canary = 'CANARY123';
  await writeFile(f.path, canary);
  const safeError = error => !error.message.includes(canary) && /not valid JSON/.test(error.message);
  await assert.rejects(FileStore.open(f.path), safeError);
  await assert.rejects(createFileArea(f.path).get(null), safeError);
  await assert.rejects(createFileArea(f.path).set({ replacement: true }), safeError);
  assert.equal(await readFile(f.path, 'utf8'), canary);
});

test('syntactically valid malformed journal shapes fail before an update can disappear', async t => {
  const f = await fixture(t);
  for (const value of [null, [], {}, { ...emptyJournal(), fills: [] },
    { ...emptyJournal(), intents: null }, { ...emptyJournal(), carry: [] },
    { ...emptyJournal(), events: {} }, { ...emptyJournal(), fills: { bad: null } }]) {
    const before = JSON.stringify(value);
    await writeFile(f.path, before);
    await assert.rejects(FileStore.open(f.path), /invalid shape/);
    await assert.rejects(new FileStore(f.path).putFill({ id: 'synthetic-fill' }), /invalid shape/);
    assert.equal(await readFile(f.path, 'utf8'), before);
  }
  await writeFile(f.path, '[]');
  await assert.rejects(createFileArea(f.path).set({ replacement: true }), /invalid shape/);
  assert.equal(await readFile(f.path, 'utf8'), '[]');
});

test('concurrent FileStore instances preserve every fill and leave no temporary file or lease', async t => {
  const f = await fixture(t);
  const originalWrite = fs.promises.open;
  const tempPaths = [];
  fs.promises.open = async (path, ...args) => {
    if (String(path).endsWith('.tmp')) tempPaths.push(String(path));
    return originalWrite.call(fs.promises, path, ...args);
  };
  syncBuiltinESMExports();
  try {
    await Promise.all(Array.from({ length: 20 }, (_, index) =>
      new FileStore(f.path).putFill({ id: `synthetic-${index}` })));
  } finally { fs.promises.open = originalWrite; syncBuiltinESMExports(); }
  const durable = await readJson(f.path);
  assert.equal(Object.keys(durable.fills).length, 20);
  assert.equal(tempPaths.length, 20);
  assert.equal(new Set(tempPaths).size, 20);
  assert.equal((await stat(f.path)).mode & 0o777, 0o600);
  assert.deepEqual(await readdir(f.directory), ['journal.json']);
});

test('concurrent file-area instances preserve every independent configuration key', async t => {
  const f = await fixture(t);
  await Promise.all(Array.from({ length: 20 }, (_, index) =>
    createFileArea(f.path).set({ [`synthetic-${index}`]: index })));
  assert.equal(Object.keys(await readJson(f.path)).length, 20);
  assert.equal((await stat(f.path)).mode & 0o777, 0o600);
  assert.deepEqual(await readdir(f.directory), ['journal.json']);
});

test('nested engine journal writes serialize without deadlock, including aliases and config writes', { timeout: 10000 }, async t => {
  const f = await fixture(t);
  await new FileStore(f.path).putFill({ id: 'seed' });
  const alias = join(f.directory, 'journal-alias.json');
  await symlink(f.path, alias);
  const owner = new FileStore(f.path), other = new FileStore(alias);
  const configPath = join(f.directory, 'config.json');
  await withStoreLock(owner, async () => {
    await Promise.all([owner.putFill({ id: 'one' }), other.putFill({ id: 'two' }),
      createFileArea(configPath).set({ first: true }), createFileArea(configPath).set({ second: true })]);
  });
  assert.deepEqual(Object.keys((await readJson(f.path)).fills).sort(), ['one', 'seed', 'two']);
  assert.deepEqual(await readJson(configPath), { first: true, second: true });
});

test('same-runtime canonical aliases share one execution lease', { timeout: 10000 }, async t => {
  const f = await fixture(t);
  await new FileStore(f.path).putFill({ id: 'seed' });
  const alias = join(f.directory, 'journal-alias.json');
  await symlink(f.path, alias);
  const values = [];
  await Promise.all([new FileStore(f.path).withExecutionLease(async () => { values.push('A'); }),
    new FileStore(alias).withExecutionLease(async () => { values.push('B'); })]);
  assert.deepEqual(values.sort(), ['A', 'B']);
});

test('hard-linked storage refuses reads and writes because path leases cannot share its identity', async t => {
  const f = await fixture(t);
  const bytes = JSON.stringify(emptyJournal());
  await writeFile(f.path, bytes);
  const alias = join(f.directory, 'hard-linked-journal.json');
  await link(f.path, alias);
  for (const path of [f.path, alias]) {
    await assert.rejects(FileStore.open(path), error => error.code === 'FILE_STORE_UNSAFE_PATH');
    await assert.rejects(new FileStore(path).putFill({ id: 'must-not-appear' }), error => error.code === 'FILE_STORE_UNSAFE_PATH');
    await assert.rejects(createFileArea(path).set({ mustNotAppear: true }), error => error.code === 'FILE_STORE_UNSAFE_PATH');
    assert.equal(await readFile(path, 'utf8'), bytes);
  }
});

test('FileStore.open canonicalizes aliases so immediate engine stops share one queue', async t => {
  const f = await fixture(t);
  await writeFile(f.path, JSON.stringify(emptyJournal()));
  const alias = join(f.directory, 'journal-alias.json');
  await symlink(f.path, alias);
  const original = await FileStore.open(f.path), linked = await FileStore.open(alias);
  assert.equal(original.path, linked.path);
  assert.notEqual(original.requestedPath, linked.requestedPath);
  stopEngine(linked);
  assert.equal(engineStopGeneration(original), 1);
});

test('cross-process journal and file-area mutations refuse an active execution lease', { timeout: 10000 }, async t => {
  const f = await fixture(t);
  const owner = launch(f, 'hold');
  await owner.waitFor('held');
  assert.equal((await stat(`${f.path}.lock`)).mode & 0o777, 0o700);
  assert.equal((await stat(join(`${f.path}.lock`, 'owner.json'))).mode & 0o777, 0o600);
  for (const action of ['fill', 'area']) {
    const contender = launch(f, action);
    const result = await contender.waitFor('done');
    assert.equal(result.ok, false);
    assert.equal(result.code, 'FILE_STORE_BUSY');
    assert.equal((await contender.exit).code, 0);
  }
  owner.process.send({ type: 'release' });
  assert.equal((await owner.waitFor('done')).ok, true);
  assert.equal((await owner.exit).code, 0);
  assert.deepEqual(Object.keys((await readJson(f.path)).fills), ['synthetic-owner-fill']);
});

test('two child ticks cannot submit the same synthetic rung through one journal', { timeout: 10000 }, async t => {
  const f = await fixture(t);
  const first = launch(f, 'tick-hold');
  const firstSubmit = await first.waitFor('fake-submit');
  assert.equal(firstSubmit.intentKey, 'synthetic-process-rung:buy:90000000');
  const second = launch(f, 'tick');
  const refused = await second.waitFor('done');
  assert.equal(refused.ok, false);
  assert.equal(refused.code, 'FILE_STORE_BUSY');
  assert.equal(refused.submissions, 0);
  assert.equal((await second.exit).code, 0);
  first.process.send({ type: 'release' });
  const completed = await first.waitFor('done');
  assert.equal(completed.ok, true);
  assert.equal(completed.submissions, 1);
  assert.equal(completed.result.placed.length, 1);
  assert.deepEqual(completed.result.errors, []);
  assert.equal((await first.exit).code, 0);
  const durable = await readJson(f.path);
  assert.equal(Object.keys(durable.intents).length, 1);
  assert.equal(durable.events.length, 1);
});

test('an independent cross-process mutation cannot collide with an active journal mutation', { timeout: 10000 }, async t => {
  const f = await fixture(t);
  const first = launch(f, 'mutation-hold');
  await first.waitFor('held');
  const second = launch(f, 'fill');
  const refused = await second.waitFor('done');
  assert.equal(refused.ok, false);
  assert.equal(refused.code, 'FILE_STORE_BUSY');
  assert.equal((await second.exit).code, 0);
  first.process.send({ type: 'release' });
  assert.equal((await first.waitFor('done')).ok, true);
  assert.equal((await first.exit).code, 0);
  assert.deepEqual(Object.keys((await readJson(f.path)).fills), ['synthetic-owner-fill']);
});

test('a crashed process leaves its lease blocking; the next writer never steals it', { timeout: 10000 }, async t => {
  const f = await fixture(t);
  const owner = launch(f, 'hold');
  await owner.waitFor('held');
  const before = await readFile(join(`${f.path}.lock`, 'owner.json'), 'utf8');
  owner.process.kill('SIGKILL');
  assert.equal((await owner.exit).signal, 'SIGKILL');
  await assert.rejects(new FileStore(f.path).putFill({ id: 'must-not-appear' }), error => error.code === 'FILE_STORE_BUSY');
  assert.equal(await readFile(join(`${f.path}.lock`, 'owner.json'), 'utf8'), before);
});

test('a journal alias retargeted during a lease refuses subsequent journal access', { timeout: 10000 }, async t => {
  const f = await fixture(t);
  const targetB = join(f.directory, 'other-journal.json');
  await writeFile(f.path, JSON.stringify(emptyJournal()));
  await writeFile(targetB, JSON.stringify(emptyJournal()));
  const alias = join(f.directory, 'journal-alias.json');
  await symlink(f.path, alias);
  const store = await FileStore.open(alias);
  await store.withExecutionLease(async () => {
    await unlink(alias); await symlink(targetB, alias);
    await assert.rejects(store.putFill({ id: 'must-not-appear' }), error => error.code === 'FILE_STORE_PATH_CHANGED');
    await assert.rejects(store.allFills(), error => error.code === 'FILE_STORE_PATH_CHANGED');
  });
  assert.deepEqual((await readJson(f.path)).fills, {});
  assert.deepEqual((await readJson(targetB)).fills, {});
});

test('an opened journal pins its canonical identity between separate engine operations', async t => {
  const f = await fixture(t);
  const targetB = join(f.directory, 'other-journal.json');
  await writeFile(f.path, JSON.stringify(emptyJournal()));
  await writeFile(targetB, JSON.stringify(emptyJournal()));
  const alias = join(f.directory, 'journal-alias.json');
  await symlink(f.path, alias);
  const store = await FileStore.open(alias);
  await store.withExecutionLease(async () => {});
  await unlink(alias); await symlink(targetB, alias);
  const changed = error => error.code === 'FILE_STORE_PATH_CHANGED';
  await assert.rejects(store.allFills(), changed);
  await assert.rejects(store.putFill({ id: 'must-not-appear' }), changed);
  let ran = false;
  await assert.rejects(store.withExecutionLease(async () => { ran = true; }), changed);
  assert.equal(ran, false);
  assert.deepEqual((await readJson(f.path)).fills, {});
  assert.deepEqual((await readJson(targetB)).fills, {});
});

test('lease releases after operation errors and dictionary keys cannot target object prototypes', async t => {
  const f = await fixture(t);
  const store = new FileStore(f.path);
  await assert.rejects(store.withExecutionLease(async () => { throw new Error('synthetic failure'); }), /synthetic failure/);
  await store.putFill({ id: '__proto__' });
  await store.putIntent({ intentKey: '__proto__', status: 'submitting' });
  assert.equal((await store.allFills()).length, 1);
  assert.equal((await store.getIntent('__proto__')).status, 'submitting');
  assert.equal(await store.getIntent('constructor'), undefined);
  assert.deepEqual(await readdir(f.directory), ['journal.json']);
});

test('nested mutations fail explicitly instead of deadlocking and later mutations still work', { timeout: 10000 }, async t => {
  const f = await fixture(t);
  const store = new FileStore(f.path);
  await assert.rejects(store.mutate(async () => store.putFill({ id: 'nested' })),
    error => error.code === 'FILE_STORE_NESTED_MUTATION');
  await store.putFill({ id: 'healthy' });
  assert.deepEqual(Object.keys((await readJson(f.path)).fills), ['healthy']);
});

test('detached async work claims a fresh lease after its originating mutation finishes', { timeout: 10000 }, async t => {
  const f = await fixture(t);
  const store = new FileStore(f.path);
  let release, later;
  const gate = new Promise(resolve => { release = resolve; });
  await store.mutate(data => {
    data.fills.first = { id: 'first' };
    later = gate.then(() => store.putFill({ id: 'later' }));
  });
  release(); await later;
  assert.deepEqual(Object.keys((await readJson(f.path)).fills).sort(), ['first', 'later']);
});


test('hard kill latches outside another process lease and prevents every later placement', { timeout: 10000 }, async t => {
  const f = await fixture(t);
  const { ConfigStore } = await import('../src/storage/store.js');
  const { runCommand } = await import('../src/core/commands.js');
  const configStore = new ConfigStore(createFileArea(f.path + '.config.json'));
  await configStore.setRuntime({ armed: true, killSwitch: false });
  const owner = launch(f, 'tick-config-hold');
  await owner.waitFor('fake-submit');
  const deps = { store: await FileStore.open(f.path), configStore };
  const stopped = await runCommand({ name: 'kill', deps });
  assert.equal(stopped.runtime.killSwitch, true);
  assert.equal(stopped.runtime.armed, false);
  assert.equal(stopped.executionOwnerBusy, true);
  owner.process.send({ type: 'release' });
  const completed = await owner.waitFor('done');
  assert.equal(completed.ok, true);
  assert.equal(completed.submissions, 1, 'the call already in flight may complete; no next call may begin');
  assert.ok(completed.result.skipped.some(row => row.reason === 'execution-stopped'));
  assert.equal((await owner.exit).code, 0);
  const cleared = await runCommand({ name: 'clearKill', deps });
  assert.equal(cleared.runtime.killSwitch, false);
  assert.equal(cleared.runtime.armed, false, 'clearing a kill never arms');
});

test('atomic runtime metadata updates cannot erase an emergency kill across file-area wrappers', async t => {
  const f = await fixture(t);
  const { ConfigStore } = await import('../src/storage/store.js');
  const first = new ConfigStore(createFileArea(f.path));
  const second = new ConfigStore(createFileArea(f.path));
  await first.setRuntime({ armed: true });
  await Promise.all([first.setRuntime({ lastTickMs: 123 }), second.killRuntime(), first.setRuntime({ realizedPnlUsdToday: 42 })]);
  const runtime = await second.getRuntime();
  assert.equal(runtime.killSwitch, true); assert.equal(runtime.armed, false);
  assert.equal(runtime.lastTickMs, 123); assert.equal(runtime.realizedPnlUsdToday, 42);
  assert.equal(runtime.stopGeneration, 1);
});

test('a foreign config lease refuses fresh runtime reads instead of returning stale permission', async t => {
  const f = await fixture(t);
  const { ConfigStore } = await import('../src/storage/store.js');
  await createFileArea(f.path).set({ runtime: { armed: true, killSwitch: false } });
  const owner = launch(f, 'config-hold');
  await owner.waitFor('held');
  await assert.rejects(new ConfigStore(createFileArea(f.path)).getRuntime(), error => error.code === 'FILE_STORE_BUSY');
  // The synthetic owner expects a journal, so terminate it without trying to
  // mutate this config fixture. Its stale lease remains and also refuses reads.
  owner.process.kill('SIGKILL'); await owner.exit;
  await assert.rejects(new ConfigStore(createFileArea(f.path)).getRuntime(), error => error.code === 'FILE_STORE_BUSY');
});


test('an acknowledged kill after write-ahead forbids the first venue invocation', { timeout: 10000 }, async t => {
  const f = await fixture(t);
  const { ConfigStore } = await import('../src/storage/store.js');
  const { runCommand } = await import('../src/core/commands.js');
  const configStore = new ConfigStore(createFileArea(f.path + '.config.json'));
  await configStore.setRuntime({ armed: true });
  const owner = launch(f, 'tick-journal-hold');
  await owner.waitFor('journal-persisted');
  const stopped = await runCommand({ name: 'kill', deps: { store: await FileStore.open(f.path), configStore } });
  assert.equal(stopped.runtime.killSwitch, true);
  owner.process.send({ type: 'release' });
  const result = await owner.waitFor('done');
  assert.equal(result.ok, true);
  assert.equal(result.submissions, 0, 'no venue invocation began before the kill acknowledgement');
  assert.ok(result.result.skipped.some(row => row.reason === 'execution-stopped'));
  assert.equal((await owner.exit).code, 0);
  const intents = await (await FileStore.open(f.path)).allIntents();
  assert.equal(intents.length, 1); assert.equal(intents[0].definitelyNotSubmitted, true);
});


test('the registry wrapper cannot reuse a pre-kill full-auto runtime snapshot', { timeout: 10000 }, async t => {
  const f = await fixture(t);
  const { ConfigStore } = await import('../src/storage/store.js');
  const { runCommand } = await import('../src/core/commands.js');
  const configStore = new ConfigStore(createFileArea(f.path + '.config.json'));
  await configStore.setRuntime({ armed: true });
  const owner = launch(f, 'tick-permission-hold');
  await owner.waitFor('permission-read');
  const stopped = await runCommand({ name: 'kill', deps: { store: await FileStore.open(f.path), configStore } });
  assert.equal(stopped.runtime.killSwitch, true);
  owner.process.send({ type: 'release' });
  const result = await owner.waitFor('done');
  assert.equal(result.ok, true);
  assert.equal(result.submissions, 0, 'wrapper awaits must not bypass the serialized permission gate');
  assert.ok(result.result.skipped.some(row => row.reason === 'execution-stopped'));
  assert.equal((await owner.exit).code, 0);
});
