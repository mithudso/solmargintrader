import test from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { COMMANDS, runCommand, CommandError } from '../src/core/commands.js';
import { withStoreLock, enginePending } from '../src/core/engine.js';
import {
  soltuiCall, soltuiList, soltuiBuildHash, SoltuiTransportError, SOLTUI_ERROR, SOLTUI_TIMEOUT_MS, isEnvelope,
} from '../src/core/soltui.js';
import { createNativeTransport } from '../src/bg/soltui-transport.js';
import { createNodeSoltuiTransport, encodeFrame, decodeFrame, hostEnv } from '../tools/soltui-transport.js';
import { MemoryStore } from '../src/storage/memoryStore.js';
import { ConfigStore } from '../src/storage/store.js';
import { fakeHandle } from '../e2e/fixtures/fake-soltui-registry.js';

const HOST = join(dirname(fileURLToPath(import.meta.url)), '..', 'e2e', 'fixtures', 'fake-soltui-host.mjs');

/** A transport that answers from the fake registry and records what it was asked. */
function fakeTransport(overrides = {}) {
  const calls = [];
  return {
    calls,
    async request(request, opts) {
      calls.push({ request, timeoutMs: opts.timeoutMs });
      if (overrides.throw) throw overrides.throw;
      return overrides.respond ? overrides.respond(request) : fakeHandle(request);
    },
  };
}
const depsWith = (soltui) => ({ soltui, store: new MemoryStore(), configStore: new ConfigStore(null), clock: () => 1 });

/* ------------------------------------------------------------- envelope -- */

test('a soltui envelope passes through unchanged, with nothing added', async () => {
  const soltui = fakeTransport();
  const direct = fakeHandle({ op: 'call', command: 'demo.echo', params: { text: 'hi' } });
  const viaRegistry = await runCommand({ name: 'soltuiCall', args: { command: 'demo.echo', params: { text: 'hi' } }, deps: depsWith(soltui) });
  assert.deepEqual(viaRegistry, direct);
  assert.deepEqual(Object.keys(viaRegistry), ['ok', 'command', 'result', 'error']);
});

test('soltuiCommands returns soltui\'s own list envelope', async () => {
  const listed = await runCommand({ name: 'soltuiCommands', args: {}, deps: depsWith(fakeTransport()) });
  assert.deepEqual(listed, fakeHandle({ op: 'list' }));
  assert.ok(listed.result.every((c) => 'read_only' in c && 'long_running' in c && 'requires_confirm' in c));
});

test('a soltui-level refusal is a normal result, not a thrown error', async () => {
  const env = await runCommand({ name: 'soltuiCall', args: { command: 'demo.nope' }, deps: depsWith(fakeTransport()) });
  assert.equal(env.ok, false);
  assert.equal(env.error.code, 'unknown_command');
});

test('the confirm flag is forwarded untouched, and soltui decides', async () => {
  const soltui = fakeTransport();
  const deps = depsWith(soltui);
  const refused = await runCommand({ name: 'soltuiCall', args: { command: 'demo.resume' }, deps });
  assert.equal(refused.error.code, 'forbidden');
  const allowed = await runCommand({ name: 'soltuiCall', args: { command: 'demo.resume', params: { confirm: true } }, deps });
  assert.equal(allowed.ok, true);
  const sent = soltui.calls.filter((c) => c.request.op === 'call').map((c) => c.request.params);
  assert.deepEqual(sent, [{}, { confirm: true }]);
});

test('the extension adds no confirm of its own', async () => {
  const soltui = fakeTransport();
  await runCommand({ name: 'soltuiCall', args: { command: 'demo.echo' }, deps: depsWith(soltui) });
  assert.deepEqual(soltui.calls.at(-1).request.params, {});
});

/* --------------------------------------------------------------- errors -- */

test('a missing transport is a clean failed envelope', async () => {
  const env = await soltuiCall({}, { command: 'demo.echo' });
  assert.deepEqual(env, { ok: false, command: 'demo.echo', result: null, error: { code: 'failed', message: 'soltui transport is not configured on this surface' } });
});

test('a transport error keeps its code and message in the envelope', async () => {
  const soltui = fakeTransport({ throw: new SoltuiTransportError(SOLTUI_ERROR.TIMEOUT, 'soltui demo.echo timed out after 30s') });
  const env = await soltuiCall({ soltui }, { command: 'demo.echo', timeoutMs: 1 });
  assert.deepEqual(env.error, { code: 'timeout', message: 'soltui demo.echo timed out after 30s' });
  assert.equal(env.command, 'demo.echo');
  assert.equal(env.result, null);
});

test('an unexpected exception is reduced to a fixed sentence (no stack, no secret)', async () => {
  const soltui = fakeTransport({ throw: new Error('boom: token=abc123 at /Users/x') });
  const env = await soltuiCall({ soltui }, { command: 'demo.echo', timeoutMs: 1 });
  assert.equal(env.error.code, 'failed');
  assert.ok(!JSON.stringify(env).includes('abc123'));
});

test('a reply that is not an envelope is refused', async () => {
  const soltui = fakeTransport({ respond: () => ({ hello: 'world' }) });
  const env = await soltuiCall({ soltui }, { command: 'demo.echo', timeoutMs: 1 });
  assert.equal(env.ok, false);
  assert.equal(env.error.code, 'failed');
  assert.equal(isEnvelope({ ok: true, command: 'x', result: 1, error: null }), true);
});

test('a command that is not a registry name never reaches the host', async () => {
  for (const bad of ['', 'Demo.Echo', 'a b', 'rm -rf /', '../x', 'a..b', '.a', 'a;b']) {
    const soltui = fakeTransport();
    const env = await soltuiCall({ soltui }, { command: bad });
    assert.equal(env.error.code, 'bad_params', JSON.stringify(bad));
    assert.equal(soltui.calls.length, 0);
  }
});

test('the registry validates the argument types before the bridge runs', async () => {
  const deps = depsWith(fakeTransport());
  await assert.rejects(() => runCommand({ name: 'soltuiCall', args: {}, deps }), /requires --command/);
  await assert.rejects(() => runCommand({ name: 'soltuiCall', args: { command: 'demo.echo', params: 'x' }, deps }), CommandError);
  await assert.rejects(() => runCommand({ name: 'soltuiCall', args: { command: 'demo.echo', extra: 1 }, deps }), /unknown argument/);
});

/* -------------------------------------------------------------- timeouts -- */

test('a long_running command gets the long deadline, others the quick one', async () => {
  const soltui = fakeTransport();
  const deps = { soltui, clock: () => 1 };
  await soltuiCall(deps, { command: 'demo.sweep' });
  await soltuiCall(deps, { command: 'demo.echo' });
  const deadlines = soltui.calls.filter((c) => c.request.op === 'call').map((c) => c.timeoutMs);
  assert.deepEqual(deadlines, [SOLTUI_TIMEOUT_MS.long, SOLTUI_TIMEOUT_MS.quick]);
  assert.equal(soltui.calls.filter((c) => c.request.op === 'list').length, 1, 'the list is cached');
});

test('when the list cannot be read, the quick deadline applies and the call still goes out', async () => {
  const soltui = fakeTransport({ respond: (r) => (r.op === 'list' ? { ok: false, command: 'list', result: null, error: { code: 'failed', message: 'x' } } : fakeHandle(r)) });
  const env = await soltuiCall({ soltui, clock: () => 1 }, { command: 'demo.sweep' });
  assert.equal(env.ok, true);
  assert.equal(soltui.calls.find((c) => c.request.op === 'call').timeoutMs, SOLTUI_TIMEOUT_MS.quick);
});

test('buildHash and list use the same envelope path', async () => {
  const soltui = fakeTransport();
  assert.equal((await soltuiBuildHash({ soltui })).result.hash.length, 64);
  assert.equal((await soltuiList({ soltui })).ok, true);
});

/* ------------------------------------------------------- engine lock -- */

test('a running soltui command does not hold the engine lock', async () => {
  let release;
  const gate = new Promise((r) => { release = r; });
  const soltui = { async request(request) { if (request.op === 'call') await gate; return fakeHandle(request); } };
  const deps = depsWith(soltui);
  const running = runCommand({ name: 'soltuiCall', args: { command: 'demo.echo' }, deps });
  // A locked command (disarm) must complete while the soltui call is still pending.
  const disarmed = await runCommand({ name: 'disarm', args: {}, deps });
  assert.equal(disarmed.runtime.armed, false);
  assert.equal(enginePending(deps.store), 0);
  release();
  assert.equal((await running).ok, true);
});

test('soltuiCommands is read-only; soltuiCall is not, so the API serves it by POST only', () => {
  assert.equal(COMMANDS.soltuiCommands.readOnly, true);
  assert.notEqual(COMMANDS.soltuiCall.readOnly, true);
  assert.equal(COMMANDS.soltuiCall.destructive, undefined);
});

test('enginePending counts queued and running locked operations', async () => {
  const store = new MemoryStore();
  let release;
  const first = withStoreLock(store, () => new Promise((r) => { release = r; }));
  const second = withStoreLock(store, async () => {});
  assert.equal(enginePending(store), 2);
  await new Promise((r) => setImmediate(r));
  release();
  await Promise.all([first, second]);
  await new Promise((r) => setImmediate(r));
  assert.equal(enginePending(store), 0);
  await assert.rejects(withStoreLock(store, async () => { throw new Error('x'); }));
  await new Promise((r) => setImmediate(r));
  assert.equal(enginePending(store), 0, 'a failed operation still releases its slot');
});

/* ------------------------------------------- service-worker transport -- */

function fakePort() {
  const port = {
    sent: [], disconnected: false, msg: [], disc: [],
    onMessage: { addListener: (f) => port.msg.push(f) },
    onDisconnect: { addListener: (f) => port.disc.push(f) },
    postMessage: (m) => port.sent.push(m),
    disconnect: () => { port.disconnected = true; },
  };
  return port;
}

test('native transport: sends {id, op, ...}, resolves with the matching response, then disconnects', async () => {
  const port = fakePort();
  const transport = createNativeTransport({ connect: (name) => { assert.equal(name, 'com.mitchhudson.soltui'); return port; }, newId: () => 'id-1' });
  const pending = transport.request({ op: 'call', command: 'demo.echo', params: { text: 'a' } }, { timeoutMs: 1000 });
  assert.deepEqual(port.sent, [{ id: 'id-1', op: 'call', command: 'demo.echo', params: { text: 'a' } }]);
  port.msg[0]({ id: 'someone-else', response: { ok: true } });
  const envelope = fakeHandle({ op: 'call', command: 'demo.echo', params: { text: 'a' } });
  port.msg[0]({ id: 'id-1', response: envelope });
  assert.deepEqual(await pending, envelope);
  assert.equal(port.disconnected, true);
});

test('native transport: a missing host becomes a failed envelope that says how to install it', async () => {
  const port = fakePort();
  const transport = createNativeTransport({ connect: () => port, lastError: () => 'Specified native messaging host not found.' });
  const env = soltuiCall({ soltui: transport }, { command: 'demo.echo', timeoutMs: 1000 });
  port.disc[0]();
  const result = await env;
  assert.equal(result.ok, false);
  assert.equal(result.error.code, 'failed');
  assert.match(result.error.message, /not available \(Specified native messaging host not found\.\)/);
  assert.match(result.error.message, /native_host_install install/);
});

test('native transport: connectNative throwing is also a clean envelope', async () => {
  const transport = createNativeTransport({ connect: () => { throw new Error('no api'); } });
  const env = await soltuiCall({ soltui: transport }, { command: 'demo.echo', timeoutMs: 1000 });
  assert.equal(env.error.code, 'failed');
  assert.match(env.error.message, /could not be started/);
});

test('native transport: a timeout disconnects so the host does not block the next request', async () => {
  const port = fakePort();
  const transport = createNativeTransport({ connect: () => port });
  const env = await soltuiCall({ soltui: transport }, { command: 'demo.echo', timeoutMs: 15 });
  assert.equal(env.error.code, 'timeout');
  assert.equal(port.disconnected, true);
});

/* ------------------------------------------------------- node transport -- */

const nodeTransport = (extra = {}) => createNodeSoltuiTransport({
  env: { ...process.env, SOLTUI_NATIVE_HOST: HOST, ...extra },
});

test('framing round-trips and refuses an oversized length', () => {
  const frame = encodeFrame({ id: 'x', n: 1 });
  assert.equal(frame.readUInt32LE(0), frame.length - 4);
  const half = decodeFrame(frame.subarray(0, frame.length - 1));
  assert.equal(half, null);
  const whole = decodeFrame(Buffer.concat([frame, Buffer.from([7])]));
  assert.deepEqual(whole.message, { id: 'x', n: 1 });
  assert.deepEqual([...whole.rest], [7]);
  const huge = Buffer.alloc(4); huge.writeUInt32LE(0xffffffff);
  assert.throws(() => decodeFrame(huge), SoltuiTransportError);
});

test('the host child receives HOME and PATH but not API tokens or passphrases', () => {
  const env = hostEnv({ HOME: '/h', PATH: '/p', SMT_API_TOKEN: 't', SMT_PASSPHRASE: 'p', SOLTUI_PYTHON: 'py', AWS_SECRET_ACCESS_KEY: 'k' });
  assert.deepEqual(env, { HOME: '/h', PATH: '/p', SOLTUI_PYTHON: 'py' });
});

test('node transport speaks the framed protocol to a real child process', async () => {
  const soltui = nodeTransport();
  const call = await soltuiCall({ soltui, clock: () => 1 }, { command: 'demo.echo', params: { text: 'over the pipe' } });
  assert.deepEqual(call, fakeHandle({ op: 'call', command: 'demo.echo', params: { text: 'over the pipe' } }));
  assert.deepEqual(await soltuiList({ soltui }), fakeHandle({ op: 'list' }));
  const hash = await soltuiBuildHash({ soltui: nodeTransport({ SOLTUI_FAKE_HASH: 'b'.repeat(64) }) });
  assert.equal(hash.result.hash, 'b'.repeat(64));
});

test('node transport: a missing host program is a clean failed envelope', async () => {
  const soltui = createNodeSoltuiTransport({ env: { ...process.env, SOLTUI_NATIVE_HOST: '/nonexistent/soltui-host' } });
  const env = await soltuiCall({ soltui }, { command: 'demo.echo', timeoutMs: 2000 });
  assert.equal(env.ok, false);
  assert.equal(env.error.code, 'failed');
  assert.match(env.error.message, /not available/);
});

test('node transport: a host that crashes, hangs or sends junk is a failed or timeout envelope', async () => {
  const crash = await soltuiCall({ soltui: nodeTransport({ SOLTUI_FAKE_MODE: 'crash' }) }, { command: 'demo.echo', timeoutMs: 3000 });
  assert.equal(crash.error.code, 'failed');
  const hang = await soltuiCall({ soltui: nodeTransport({ SOLTUI_FAKE_MODE: 'hang' }) }, { command: 'demo.echo', timeoutMs: 200 });
  assert.equal(hang.error.code, 'timeout');
  const junk = await soltuiCall({ soltui: nodeTransport({ SOLTUI_FAKE_MODE: 'garbage' }) }, { command: 'demo.echo', timeoutMs: 3000 });
  assert.equal(junk.ok, false);
});
