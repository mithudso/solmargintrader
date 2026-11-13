import test from 'node:test';
import assert from 'node:assert/strict';
import runtimeWorker, { RuntimeOwner, validateManifest } from './worker.js';

const token = 'fixture-engine-token-'.repeat(3);
const stateToken = 'fixture-state-token-'.repeat(3);
const digest = async raw => Buffer.from(await crypto.subtle.digest('SHA-256', raw)).toString('hex');
class Storage {
  constructor() { this.rows = new Map([['epoch', 1]]); this.serial = Promise.resolve(); }
  async get(key) { return Array.isArray(key) ? new Map(key.filter(k => this.rows.has(k)).map(k => [k, this.rows.get(k)])) : this.rows.get(key); }
  async put(key, value) { this.rows.set(key, structuredClone(value)); }
  async setAlarm(at) { this.alarm = at; }
  transaction(callback) {
    const next = this.serial.then(() => callback(this));
    this.serial = next.catch(() => {});
    return next;
  }
}
class Bucket {
  constructor() { this.rows = new Map(); }
  async put(key, bytes, options = {}) {
    if (options.onlyIf && this.rows.has(key)) return null;
    const raw = new Uint8Array(bytes);
    this.rows.set(key, raw.slice());
    if (this.onPut) await this.onPut(key);
    return { size: raw.length, etag: 'fixture' };
  }
  async get(key) {
    const bytes = this.rows.get(key);
    return bytes && { size: bytes.length, body: bytes.slice(), arrayBuffer: async () => bytes.slice().buffer };
  }
  async head(key) { return this.rows.has(key) ? { size: this.rows.get(key).length } : null; }
}
function fixture() {
  const storage = new Storage(), bucket = new Bucket(); let starts = 0;
  const calls = [];
  const container = {
    running: false, images: { base: 'registry.invalid/fixture@sha256:' + 'a'.repeat(64) },
    start(options) { starts++; this.running = true; this.startOptions = options; },
    async destroy() { this.running = false; },
    async setInactivityTimeout() {}, monitor() { return new Promise(() => {}); },
    getTcpPort(port) { assert.equal(port, 8790); return { fetch: async (request, init) => {
      const req = request instanceof Request ? request : new Request(request, init);
      calls.push({ path: new URL(req.url).pathname, authorization: req.headers.get('Authorization'), contentLength: req.headers.get('Content-Length'), body: req.body ? new Uint8Array(await req.arrayBuffer()) : null });
      return Response.json({ ready: true, status: 'ready' });
    } }; },
  };
  const ctx = { storage, container, blockConcurrencyWhile: callback => callback(), waitUntil() {} };
  const env = { ENGINE_TOKEN: token, RUNTIME_STATE_TOKEN: stateToken, RUNTIME_PUBLIC_ORIGIN: 'https://runtime.example', STATE: bucket };
  return { owner: new RuntimeOwner(ctx, env), env, ctx, bucket, storage, calls, starts: () => starts };
}
function stateRequest(path, method = 'GET', body = null, epoch = 1) {
  return new Request('https://runtime.example/internal/state/' + path, { method, headers: { Authorization: 'Bearer ' + stateToken, 'X-Runtime-Epoch': String(epoch) }, body });
}
async function stage(f, sequence = 1) {
  const raw = new TextEncoder().encode('explicit fixture public bytes'); const sha = await digest(raw);
  assert.equal((await f.owner.fetch(stateRequest('chunks/' + sha, 'PUT', raw))).status, 200);
  const manifest = { schemaVersion: 1, epoch: 1, sequence, files: { 'data/ZEC_1m.csv': { bytes: raw.length, sha256: sha, chunks: [sha] } } };
  return { raw, sha, manifest };
}

test('checkpoint publishes only verified immutable chunks and exact next sequence', async () => {
  const f = fixture(); const { raw, sha, manifest } = await stage(f);
  const body = JSON.stringify(manifest);
  const committed = await f.owner.fetch(stateRequest('manifest', 'PUT', body));
  assert.equal(committed.status, 200);
  assert.deepEqual(await committed.json(), { epoch: 1, sequence: 1, sha256: await digest(new TextEncoder().encode(body)) });
  const restored = await f.owner.fetch(stateRequest('manifest'));
  assert.deepEqual(await restored.json(), manifest);
  assert.deepEqual(new Uint8Array(await (await f.owner.fetch(stateRequest('chunks/' + sha))).arrayBuffer()), raw);
  assert.equal((await f.owner.fetch(stateRequest('manifest', 'PUT', body))).status, 409);
  assert.equal(f.starts(), 0, 'checkpoint callbacks cannot recursively start containers');
});
test('unverified chunks, bad lengths and path traversal never publish the head', async () => {
  const f = fixture(); const { manifest } = await stage(f);
  const missing = structuredClone(manifest); missing.files['data/ZEC_1m.csv'].chunks[0] = 'b'.repeat(64);
  assert.equal((await f.owner.fetch(stateRequest('manifest', 'PUT', JSON.stringify(missing)))).status, 409);
  const length = structuredClone(manifest); length.files['data/ZEC_1m.csv'].bytes++;
  assert.equal((await f.owner.fetch(stateRequest('manifest', 'PUT', JSON.stringify(length)))).status, 400);
  const escape = structuredClone(manifest); escape.files['../secret'] = escape.files['data/ZEC_1m.csv'];
  assert.equal(validateManifest(escape), false);
  assert.equal(await f.storage.get('head'), undefined);
});
test('stale epoch and epoch change during R2 upload fail closed', async () => {
  const f = fixture(); const bytes = new TextEncoder().encode('new bytes'), sha = await digest(bytes);
  f.bucket.onPut = async () => f.storage.put('epoch', 2);
  assert.equal((await f.owner.fetch(stateRequest('chunks/' + sha, 'PUT', bytes))).status, 409);
  assert.equal(await f.storage.get('chunk:' + sha), undefined);
  assert.equal((await f.owner.fetch(stateRequest('manifest'))).status, 409);
});
test('concurrent manifest publishers have one commit winner', async () => {
  const f = fixture(); const { manifest } = await stage(f);
  const statuses = await Promise.all([1, 2].map(async () => (await f.owner.fetch(stateRequest('manifest', 'PUT', JSON.stringify(manifest)))).status));
  assert.deepEqual(statuses.sort(), [200, 409]);
  assert.equal((await f.storage.get('head')).sequence, 1);
});
test('corrupt R2 head and wrong hash are withheld', async () => {
  const f = fixture(); const { manifest } = await stage(f);
  assert.equal((await f.owner.fetch(stateRequest('chunks/' + 'a'.repeat(64), 'PUT', 'wrong bytes'))).status, 400);
  await f.owner.fetch(stateRequest('manifest', 'PUT', JSON.stringify(manifest)));
  f.bucket.rows.set((await f.storage.get('head')).key, new TextEncoder().encode('corrupt'));
  assert.equal((await f.owner.fetch(stateRequest('manifest'))).status, 503);
});
test('analysis and state authorities are separate; browser and unconfigured requests fail closed', async () => {
  const f = fixture();
  const forged = stateRequest('manifest'); forged.headers.set('Authorization', 'Bearer ' + token);
  assert.equal((await f.owner.fetch(forged)).status, 401);
  assert.equal((await f.owner.fetch(new Request('https://runtime.example/health'))).status, 401);
  assert.equal((await f.owner.fetch(new Request('https://runtime.example/health', { headers: { Authorization: 'Bearer ' + token, Origin: 'https://oraclebot.io' } }))).status, 403);
});
test('concurrent application requests start exactly one owned image and expose its identity', async () => {
  const f = fixture();
  const request = () => new Request('https://runtime.example/health', { headers: { Authorization: 'Bearer ' + token } });
  const values = await Promise.all([f.owner.fetch(request()), f.owner.fetch(request())]);
  assert.equal(f.starts(), 1);
  assert.equal(f.ctx.container.startOptions.env.ENGINE_EPOCH, '2');
  assert.equal(f.ctx.container.startOptions.enableInternet, true);
  for (const value of values) assert.equal((await value.json()).deployment.image, f.ctx.container.images.base);
  assert.ok(f.calls.every(call => call.authorization === 'Bearer ' + token));
});
test('public gateway routes every caller to the fixed singleton name', async () => {
  const names = [];
  const env = { RUNTIME: { idFromName(name) { names.push(name); return 'fixed'; }, get(id) { assert.equal(id, 'fixed'); return { fetch: () => Response.json({ fixture: true }) }; } } };
  await runtimeWorker.fetch(new Request('https://runtime.example/health?instance=attacker'), env);
  assert.deepEqual(names, ['public-analysis-v1']);
});
test('warmup checkpoint callbacks reenter after the short ownership block', { timeout: 2000 }, async () => {
  const f = fixture(); let gate = null, callback = false;
  f.ctx.blockConcurrencyWhile = async operation => {
    let release; gate = new Promise(resolve => { release = resolve; });
    try { return await operation(); } finally { const finish = release; gate = null; finish(); }
  };
  f.ctx.container.getTcpPort = () => ({ fetch: async () => {
    if (!callback) {
      callback = true;
      if (gate) await gate;
      const result = await f.owner.fetch(stateRequest('manifest', 'GET', null, Number(f.ctx.container.startOptions.env.ENGINE_EPOCH)));
      assert.equal(result.status, 404);
    }
    return Response.json({ ready: true });
  } });
  const result = await f.owner.fetch(new Request('https://runtime.example/health', { headers: { Authorization: 'Bearer ' + token } }));
  assert.equal(result.status, 200);
  assert.equal(callback, true);
  assert.equal(f.starts(), 1);
});
test('bounded POST proxy supplies the exact content length required by Python', async () => {
  const f = fixture(); const body = JSON.stringify({ id: crypto.randomUUID(), request: { coin: 'SOL' } });
  const result = await f.owner.fetch(new Request('https://runtime.example/v1/jobs', { method: 'POST', headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }, body }));
  assert.equal(result.status, 200);
  const forwarded = f.calls.find(call => call.path === '/v1/jobs');
  assert.equal(forwarded.contentLength, String(Buffer.byteLength(body)));
  assert.equal(new TextDecoder().decode(forwarded.body), body);
  assert.equal((await f.owner.fetch(new Request('https://runtime.example/v1/jobs', { method: 'POST', headers: { Authorization: 'Bearer ' + token }, body: 'x'.repeat(4097) }))).status, 413);
});
test('trusted closed-bar signal requests use the same authenticated bounded container bridge', async () => {
  const f = fixture(); const body = JSON.stringify({ coin: 'SOL', strategy: 'rsi', interval: '1h' });
  const result = await f.owner.fetch(new Request('https://runtime.example/v1/signals', { method: 'POST', headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }, body }));
  assert.equal(result.status, 200);
  const forwarded = f.calls.find(call => call.path === '/v1/signals');
  assert.equal(forwarded.authorization, 'Bearer ' + token);
  assert.equal(forwarded.contentLength, String(Buffer.byteLength(body)));
  assert.equal(new TextDecoder().decode(forwarded.body), body);
  assert.equal((await f.owner.fetch(new Request('https://runtime.example/v1/signals', { method: 'POST', headers: { Authorization: 'Bearer ' + stateToken }, body }))).status, 401);
});
