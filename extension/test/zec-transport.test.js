import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { lstat, mkdtemp, readFile, rm } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';
import { ZEC_REMOTE_COMMANDS } from '../src/core/zec-advice.js';
import { installZecNativeHost } from '../tools/zec-native-install.js';
import {
  encodeZecFrame, MAX_ZEC_REPLY_BYTES, readZecFrames, requestZecChrome,
  ZEC_CHROME_UNAVAILABLE, ZEC_NATIVE_COMMANDS, ZEC_NATIVE_HOST,
} from '../tools/zec-transport.js';

const extensionId = 'p'.repeat(32);

async function setup(t) {
  const root = await mkdtemp('/tmp/smt-zec-test-');
  t.after(() => rm(root, { recursive: true, force: true }));
  const directory = path.join(root, "Chrome test's profile", 'NativeMessagingHosts');
  const endpoint = path.join(root, 'ipc', 'chrome.sock');
  const env = { SOLMARGIN_ZEC_SOCKET: endpoint };
  return { extensionId, root, directory, endpoint, env };
}

function spawnHost(t, config, origin = config.origin) {
  const host = spawn(config.wrapper, [origin], { stdio: ['pipe', 'pipe', 'pipe'] });
  t.after(() => { if (host.exitCode === null) host.kill(); });
  const messages = [];
  const exited = once(host, 'exit');
  const reader = readZecFrames(MAX_ZEC_REPLY_BYTES, (message) => messages.push(message));
  host.stdout.on('data', reader);

  return {
    host,
    exited,
    async nextFrame() {
      while (!messages.length) {
        await Promise.race([
          once(host.stdout, 'data'),
          exited.then(([code]) => { throw new Error(`Native host exited while waiting for a frame (${code}).`); }),
        ]);
      }
      return messages.shift();
    },
    async stop() {
      host.stdin.end();
      assert.equal((await exited)[0], 0);
    },
  };
}

test('Zec installer restricts origin and the executable survives installation from a temporary checkout', async (t) => {
  const opts = await setup(t);
  await assert.rejects(installZecNativeHost({ ...opts, extensionId: 'bad-id' }), /Extension ID/);
  const config = await installZecNativeHost(opts);
  assert.deepEqual(await installZecNativeHost(opts), config);
  const manifest = JSON.parse(await readFile(config.manifestPath, 'utf8'));
  assert.equal(manifest.name, ZEC_NATIVE_HOST);
  assert.equal(manifest.type, 'stdio');
  assert.equal(manifest.path, config.wrapper);
  assert.deepEqual(manifest.allowed_origins, [config.origin]);
  assert.equal((await lstat(config.wrapper)).mode & 0o777, 0o700);
  assert.equal((await lstat(path.dirname(config.wrapper))).mode & 0o777, 0o700);

  const denied = spawnHost(t, config, `chrome-extension://${'a'.repeat(32)}/`);
  assert.deepEqual(await denied.exited, [1, null]);
  await assert.rejects(lstat(config.endpoint), { code: 'ENOENT' });
});

test('Zec native host binds a private socket, allows known requests and returns only matching Chrome replies', { timeout: 8000 }, async (t) => {
  const opts = await setup(t);
  const config = await installZecNativeHost(opts);
  const ask = (name, params) => requestZecChrome(name, params, { env: opts.env });
  assert.deepEqual(await ask('zecSnapshot'), ZEC_CHROME_UNAVAILABLE);
  const browser = spawnHost(t, config);
  assert.deepEqual(await browser.nextFrame(), { ready: true });
  assert.equal((await lstat(opts.endpoint)).mode & 0o777, 0o600);
  assert.equal((await lstat(path.dirname(opts.endpoint))).mode & 0o777, 0o700);

  const competitor = spawnHost(t, config);
  assert.deepEqual(await competitor.exited, [1, null]);
  assert.equal((await lstat(opts.endpoint)).isSocket(), true);

  assert.equal((await ask('arm', {})).status, 400);
  assert.equal((await ask('zecSnapshot', 'invalid')).status, 400);
  assert.equal((await ask('zecAdvice', { text: 'x'.repeat(20_000) })).status, 400);
  const response = ask('zecSnapshot');
  const request = await browser.nextFrame();
  assert.deepEqual(request, { id: request.id, name: 'zecSnapshot', params: {} });
  assert.match(request.id, /^[0-9a-f-]{36}$/);

  const unknown = encodeZecFrame({ id: 'not-requested', result: { ok: true, result: 'wrong' } }, MAX_ZEC_REPLY_BYTES);
  const expected = { ok: true, result: { market: 'ZEC' } };
  const correct = encodeZecFrame({ id: request.id, result: expected }, MAX_ZEC_REPLY_BYTES);
  browser.host.stdin.write(Buffer.concat([unknown, correct.subarray(0, 3)]));
  browser.host.stdin.write(correct.subarray(3));
  assert.deepEqual(await response, expected);

  const conflicting = ask('zecAdvice', { snapshotId: 'expired' });
  const advisory = await browser.nextFrame();
  assert.equal(advisory.name, 'zecAdvice');
  assert.deepEqual(ZEC_NATIVE_COMMANDS, ZEC_REMOTE_COMMANDS);
  const rejected = { ok: false, error: 'Snapshot expired.', status: 409 };
  browser.host.stdin.write(encodeZecFrame({ id: advisory.id, result: rejected }, MAX_ZEC_REPLY_BYTES));
  assert.deepEqual(await conflicting, rejected);

  const interrupted = ask('zecAdvisories');
  assert.equal((await browser.nextFrame()).name, 'zecAdvisories');
  await browser.stop();
  assert.deepEqual(await interrupted, ZEC_CHROME_UNAVAILABLE);
  assert.deepEqual(await ask('zecSnapshot'), ZEC_CHROME_UNAVAILABLE);

  const restarted = spawnHost(t, config);
  assert.deepEqual(await restarted.nextFrame(), { ready: true });
  await restarted.stop();
});

test('a killed native process releases the endpoint claim on macOS', {
  skip: process.platform !== 'darwin',
  timeout: 8000,
}, async (t) => {
  const opts = await setup(t);
  const config = await installZecNativeHost(opts);
  const crashed = spawnHost(t, config);
  assert.deepEqual(await crashed.nextFrame(), { ready: true });
  crashed.host.kill('SIGKILL');
  assert.deepEqual(await crashed.exited, [null, 'SIGKILL']);
  assert.equal((await lstat(opts.endpoint)).isSocket(), true);
  assert.deepEqual(await requestZecChrome('zecSnapshot', {}, { env: opts.env }), ZEC_CHROME_UNAVAILABLE);
  const recovered = spawnHost(t, config);
  assert.deepEqual(await recovered.nextFrame(), { ready: true });
  await recovered.stop();
});
