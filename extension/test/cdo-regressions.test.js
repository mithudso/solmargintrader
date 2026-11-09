import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, cpSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { maxDrawdown, fillsToCsv } from '../src/core/pnl.js';
import { tick, withStoreLock, enginePending } from '../src/core/engine.js';
import { runCommand } from '../src/core/commands.js';
import { createNativeTransport } from '../src/bg/soltui-transport.js';
import { checkForUpdate, BUILD_STATE_KEY, OUTCOME } from '../src/core/autoreload.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { ConfigStore } from '../src/storage/store.js';

const extensionRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const deferred = () => {
  let resolve;
  const promise = new Promise((r) => { resolve = r; });
  return { promise, resolve };
};

function fakePort(onPost = () => {}) {
  const messages = [], disconnects = [], sent = [];
  return {
    messages, sent,
    onMessage: { addListener: (fn) => messages.push(fn) },
    onDisconnect: { addListener: (fn) => disconnects.push(fn) },
    postMessage(message) { sent.push(message); onPost(message, this); },
    disconnect() { for (const fn of disconnects) fn(); },
    reply(response) { messages[0](response); },
  };
}

test('dollar and percentage drawdown maxima can occur at different times', () => {
  const points = [0, 100, 50, 1000, 900].map((equityUsd) => ({ equityUsd }));
  assert.deepEqual(maxDrawdown(points), { drawdownUsd: 100, drawdownPct: 50 });
  assert.equal(maxDrawdown([{ equityUsd: 0 }, { equityUsd: -5 }]).drawdownPct, 0);
});

test('fill CSV quotes delimiters and line breaks without shifting monetary columns', () => {
  const csv = fillsToCsv([{ id: 'fill"one', gridId: 'grid,\n"one', tsMs: 0,
    side: 'buy', baseQty: 1, priceUsd: 100, feeUsd: 0.25 }]);
  assert.equal(csv, 'id,gridId,tsIso,side,baseQty,priceUsd,notionalUsd,feeUsd,level\n' +
    '"fill""one","grid,\n""one",1970-01-01T00:00:00.000Z,buy,1,100,100.000000,0.25,');
});

test('an alert acknowledgement waiting on a scan does not hold the engine lock', async () => {
  const started = deferred(), release = deferred();
  const store = new MemoryStore(), configStore = new ConfigStore(null);
  const deps = { store, configStore, clock: () => Date.now(),
    fetch: async () => ({ ok: false, status: 503, headers: { get: () => null }, text: async () => '' }),
    soltui: { async request(request) {
      if (request.command === 'liquidity.data') { started.resolve(); await release.promise; }
      return { ok: false, command: request.command ?? request.op, result: null,
        error: { code: 'failed', message: 'fixture unavailable' } };
    } },
  };
  const scan = runCommand({ name: 'scanAlerts', args: {}, deps });
  await started.promise;
  const ack = runCommand({ name: 'ackAlerts', args: { all: true }, deps });
  let advanced = false;
  const engine = withStoreLock(store, () => { advanced = true; });
  await new Promise((resolve) => setImmediate(resolve));
  const beforeNetworkCompleted = advanced;
  release.resolve();
  await Promise.all([scan, ack, engine]);
  assert.equal(beforeNetworkCompleted, true);
});

test('automatic reload defers while an unleased native call is unresolved', async () => {
  let sequence = 0, reloads = 0;
  const ports = [];
  const transport = createNativeTransport({ newId: () => `q${++sequence}`, connect: () => {
    const port = fakePort((message, current) => {
      if (message.op === 'buildHash') queueMicrotask(() => current.reply({ id: message.id,
        response: { ok: true, command: 'buildHash', result: { hash: 'b'.repeat(64) }, error: null } }));
    });
    ports.push(port); return port;
  } });
  const store = new MemoryStore(), state = new ConfigStore(null);
  await state.set(BUILD_STATE_KEY, { hash: 'a'.repeat(64), hostDown: false });
  const original = transport.request({ op: 'call', command: 'paper.step' }, { timeoutMs: 5000 });
  const wasBusy = transport.busy();
  const outcome = await checkForUpdate({ deps: { soltui: transport }, state,
    pending: () => enginePending(store) + (transport.busy() ? 1 : 0),
    withLock: (fn) => withStoreLock(store, fn), reload: () => { reloads++; },
    logEvent: (event) => store.logEvent(event), hold: async () => {} });
  ports[0].reply({ id: ports[0].sent[0].id, response: { ok: true } });
  await original;
  assert.equal(wasBusy, true);
  assert.equal(outcome, OUTCOME.DEFERRED);
  assert.equal(reloads, 0);
  assert.equal(ports[0].sent.length, 1, 'a native call is never replayed');
  assert.equal(transport.busy(), false);
});

test('one-shot activity clears on reply, disconnect, startup failure and timeout', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  for (const outcome of ['reply', 'disconnect', 'startup', 'timeout']) {
    const port = fakePort();
    const transport = createNativeTransport({ newId: () => 'one', lastError: () => '', connect: () => {
      if (outcome === 'startup') throw new Error('fixture missing host');
      return port;
    } });
    const call = transport.request({ op: 'ping' }, { timeoutMs: 500 });
    const during = transport.busy();
    const settled = outcome === 'reply' ? call : assert.rejects(call);
    if (outcome === 'reply') port.reply({ id: 'one', response: { ok: true } });
    if (outcome === 'disconnect') port.disconnect();
    if (outcome === 'timeout') t.mock.timers.tick(500);
    await settled;
    assert.equal(during, true, outcome);
    assert.equal(transport.busy(), false, outcome);
    assert.equal(port.sent.length, outcome === 'startup' ? 0 : 1, 'no retry');
  }
});

async function engineFixture() {
  const store = new MemoryStore(), configStore = new ConfigStore(null);
  await configStore.setConfig({ lower: 100, upper: 200, rungs: 5, spacing: 'arith' });
  const venue = { kind: 'spot', getPrice: async () => 150, getOpenOrders: async () => [],
    getFills: async () => [], placeOrder: async () => { throw new Error('must not submit'); } };
  return { store, configStore, venue, clock: () => Date.UTC(2026, 10, 8, 12) };
}

test('accounting holds remain in the event history after a later tick', async () => {
  const ctx = await engineFixture();
  await ctx.store.putFill({ id: 'unpriced', side: 'buy', baseQty: 0.1, priceUsd: 100,
    feeUsd: 0, feeUnknown: true, tsMs: ctx.clock() });
  await tick(ctx);
  const first = (await ctx.store.recentEvents())[0];
  assert.ok(first, 'a hold must leave a durable event');
  assert.ok(first.summary.holds.includes('accounting-evidence-needs-review'));
  await ctx.store.putFill({ id: 'unpriced', side: 'buy', baseQty: 0.1, priceUsd: 100,
    feeUsd: 0.1, feeUnknown: false, tsMs: ctx.clock() });
  await tick(ctx);
  assert.equal((await ctx.store.recentEvents()).length, 2);
});

test('venue preparation failure leaves a bounded secret-free durable diagnostic', async () => {
  const ctx = await engineFixture();
  await assert.rejects(tick({ ...ctx, buildVenue: async () => { throw new RangeError('private-canary'); } }), /private-canary/);
  const event = (await ctx.store.recentEvents())[0];
  assert.ok(event, 'preparation failure must survive the thrown call');
  assert.deepEqual(event.summary.errorDetails, [{ stage: 'prepare-venue', kind: 'RangeError' }]);
  assert.ok(!JSON.stringify(event).includes('private-canary'));
});

test('caught price failure persists its phase and type without upstream messages', async () => {
  const ctx = await engineFixture();
  ctx.venue.getPrice = async () => { throw new Error('private-canary'); };
  await tick(ctx);
  const event = (await ctx.store.recentEvents())[0];
  assert.deepEqual(event.summary.errorDetails, [{ stage: 'price', kind: 'Error' }]);
  assert.ok(!JSON.stringify(event).includes('private-canary'));
  ctx.venue.getPrice = async () => 150;
  await tick(ctx);
  assert.equal((await ctx.store.recentEvents())[1].summary.errorDetails[0].stage, 'price');
});

test('production API startup wires security diagnostics without credentials', () => {
  // A fresh child exercises main's real dependency wiring; only the OS listener
  // is replaced, so this fixture cannot bind a port or use owner storage.
  const path = join(extensionRoot, 'tools', 'api-server.js');
  const script = `import http from 'node:http'; import {syncBuiltinESMExports} from 'node:module';
    import {pathToFileURL} from 'node:url';
    http.createServer = handler => ({listen(_port,_host,ready) {
      const res={writeHead(){},end(){}};
      Promise.resolve(handler({url:'/v1/status',method:'GET',headers:{}},res)).then(ready);
    }, close(cb){cb?.();}}); syncBuiltinESMExports();
    process.argv=[process.execPath,${JSON.stringify(path)},'--ephemeral'];
    await import(pathToFileURL(process.argv[1]).href);`;
  const child = spawnSync(process.execPath, ['--input-type=module', '-e', script], {
    encoding: 'utf8', timeout: 5000, env: { ...process.env, SMT_API_TOKEN: 'private-canary' },
  });
  assert.equal(child.status, 0, child.stderr);
  assert.match(child.stderr, /API authentication refused/);
  assert.ok(!child.stderr.includes('private-canary'));
});

test('API direct startup works from paths containing spaces, hash and percent', () => {
  const directory = mkdtempSync(join(tmpdir(), 'smt API # % '));
  try {
    for (const entry of ['src', 'tools', 'package.json']) {
      cpSync(join(extensionRoot, entry), join(directory, entry), { recursive: true });
    }
    const child = spawnSync(process.execPath, [join(directory, 'tools', 'api-server.js')], {
      encoding: 'utf8', timeout: 5000, env: { ...process.env, SMT_API_TOKEN: '' },
    });
    assert.notEqual(child.status, 0, 'the direct entrypoint must validate startup instead of silently exiting');
    assert.match(child.stderr, /SMT_API_TOKEN must be set/);
  } finally { rmSync(directory, { recursive: true, force: true }); }
});


test('CSV external formula identities stay text while negative numeric amounts stay numeric', async () => {
  for (const id of ['=1+1', '+1+1', '-1+1', '@SUM(1)', ' \t=1+1', '\u0001=1+1']) {
    const store = new MemoryStore();
    await store.putFill({id, gridId:'grid',tsMs:0,side:'buy',baseQty:1,priceUsd:100,feeUsd:-0.25});
    const csv=fillsToCsv(await store.allFills());
    assert.ok(csv.split('\n')[1].startsWith("'"), JSON.stringify(id));
    assert.ok(csv.includes(',-0.25,'));
  }
});
