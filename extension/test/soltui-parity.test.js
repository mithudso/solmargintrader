import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { MemoryStore } from '../src/storage/memoryStore.js';
import { ConfigStore } from '../src/storage/store.js';
import { createApiServer } from '../tools/api-server.js';
import { createNodeSoltuiTransport } from '../tools/soltui-transport.js';
import { fakeHandle } from '../e2e/fixtures/fake-soltui-registry.js';

// The service worker registers chrome listeners at import time.
const area = new Map();
globalThis.chrome = {
  storage: { local: { async get(key) { const keys = Array.isArray(key) ? key : [key]; return Object.fromEntries(keys.filter((k) => area.has(k)).map((k) => [k, area.get(k)])); }, async set(o) { for (const [k, v] of Object.entries(o)) area.set(k, v); } } },
  runtime: { onInstalled: { addListener() {} }, onStartup: { addListener() {} }, onMessage: { addListener() {} } },
  alarms: { onAlarm: { addListener() {} }, async clear() {}, async create() {} },
  action: { async setBadgeText() {}, async setBadgeBackgroundColor() {} },
};
const { handleMessage } = await import('../src/bg/service-worker.js');

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const HOST = join(ROOT, 'e2e', 'fixtures', 'fake-soltui-host.mjs');
const TOKEN = 'parity-token';
const hostEnv = { ...process.env, SOLTUI_NATIVE_HOST: HOST };
const transport = () => createNodeSoltuiTransport({ env: hostEnv });

const cli = (args) => new Promise((resolve) => {
  execFile(process.execPath, [join(ROOT, 'tools', 'cli.js'), ...args, '--json', '--ephemeral'], { cwd: ROOT, env: hostEnv, timeout: 20_000 },
    (err, stdout, stderr) => resolve({ code: err?.code ?? 0, stdout, stderr }));
});

async function withApi(fn) {
  const deps = { store: new MemoryStore(), configStore: new ConfigStore(null), soltui: transport(), log: () => {} };
  const server = createApiServer({ deps, token: TOKEN });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  try { return await fn(`http://127.0.0.1:${server.address().port}`); } finally { server.close(); await once(server, 'close'); }
}
const headers = { Authorization: `Bearer ${TOKEN}`, 'Content-Type': 'application/json' };

/** The same call, down all three extension-side paths plus the host itself. */
async function everySurface(command, params) {
  const direct = fakeHandle({ op: 'call', command, params });
  const message = await handleMessage({ type: 'soltuiCall', command, params }, { openStore: async () => new MemoryStore(), soltui: transport() });
  const viaCli = await cli(['soltuiCall', '--command', command, '--params', JSON.stringify(params)]);
  const viaApi = await withApi(async (base) => (await (await fetch(`${base}/v1/soltuiCall`, { method: 'POST', headers, body: JSON.stringify({ command, params }) })).json()));
  return { direct, message, viaCli, viaApi };
}

test('soltuiCall returns the identical envelope via the extension message, the CLI and the API', async () => {
  const { direct, message, viaCli, viaApi } = await everySurface('demo.echo', { text: 'parity' });
  assert.equal(message.ok, true);
  assert.deepEqual(message.result, direct);
  assert.equal(viaCli.code, 0, viaCli.stderr);
  assert.deepEqual(JSON.parse(viaCli.stdout), direct);
  assert.equal(viaApi.ok, true);
  assert.equal(viaApi.command, 'soltuiCall');
  assert.deepEqual(viaApi.result, direct);
});

test('a refusal (forbidden without confirm) is the identical envelope on every surface', async () => {
  const { direct, message, viaCli, viaApi } = await everySurface('demo.resume', {});
  assert.equal(direct.error.code, 'forbidden');
  assert.deepEqual(message.result, direct);
  assert.deepEqual(JSON.parse(viaCli.stdout), direct);
  assert.deepEqual(viaApi.result, direct);
});

test('with confirm:true the same call succeeds identically everywhere', async () => {
  const { direct, message, viaCli, viaApi } = await everySurface('demo.resume', { confirm: true });
  assert.equal(direct.ok, true);
  assert.deepEqual(message.result, direct);
  assert.deepEqual(JSON.parse(viaCli.stdout), direct);
  assert.deepEqual(viaApi.result, direct);
});

test('soltuiCommands is the identical list envelope on every surface', async () => {
  const direct = fakeHandle({ op: 'list' });
  const message = await handleMessage({ type: 'soltuiCommands' }, { openStore: async () => new MemoryStore(), soltui: transport() });
  const viaCli = await cli(['soltuiCommands']);
  const viaApi = await withApi(async (base) => (await fetch(`${base}/v1/soltuiCommands`, { headers: { Authorization: `Bearer ${TOKEN}` } })).json());
  assert.deepEqual(message.result, direct);
  assert.deepEqual(JSON.parse(viaCli.stdout), direct);
  assert.deepEqual(viaApi.result, direct);
});

test('an unknown soltui command is the same envelope on every surface', async () => {
  const { direct, message, viaCli, viaApi } = await everySurface('demo.nope', {});
  assert.equal(direct.error.code, 'unknown_command');
  assert.deepEqual(message.result, direct);
  assert.deepEqual(JSON.parse(viaCli.stdout), direct);
  assert.deepEqual(viaApi.result, direct);
});

test('with the host missing, every surface returns the same clean failed envelope', async () => {
  const missing = { ...process.env, SOLTUI_NATIVE_HOST: '/nonexistent/host' };
  const cliOut = await new Promise((resolve) => execFile(process.execPath, [join(ROOT, 'tools', 'cli.js'), 'soltuiCall', '--command', 'demo.echo', '--json', '--ephemeral'], { cwd: ROOT, env: missing }, (e, stdout) => resolve(stdout)));
  const viaCli = JSON.parse(cliOut);
  const message = await handleMessage({ type: 'soltuiCall', command: 'demo.echo' }, { openStore: async () => new MemoryStore(), soltui: createNodeSoltuiTransport({ env: missing }) });
  assert.equal(viaCli.ok, false);
  assert.equal(viaCli.error.code, 'failed');
  assert.deepEqual(message.result, viaCli);
});

test('the API refuses GET for soltuiCall (it can change state) and serves soltuiCommands by GET', async () => {
  await withApi(async (base) => {
    const auth = { Authorization: `Bearer ${TOKEN}` };
    assert.equal((await fetch(`${base}/v1/soltuiCall?command=demo.echo`, { headers: auth })).status, 405);
    assert.equal((await fetch(`${base}/v1/soltuiCommands`, { headers: auth })).status, 200);
    assert.equal((await fetch(`${base}/v1/soltuiCommands`, { headers: { ...auth, Origin: 'https://evil.example' } })).status, 403);
  });
});
