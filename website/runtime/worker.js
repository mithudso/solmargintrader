// A single named Durable Object owns the dedicated public-analysis container.
// R2 checkpoint publication, rather than ephemeral VM disk, commits its state.
const CHUNK_BYTES = 512 * 1024;
const MANIFEST_BYTES = 4 * 1024 * 1024;
const MAX_STATE_BYTES = 8 * 1024 * 1024 * 1024;
const DIGEST = /^[a-f0-9]{64}$/;
const STATE_PATH = /^(?:jobs\.sqlite3|oracle\/(?:SOL|BTC|ETH|ZEC)\/history\.sqlite3|data\/(?:SOL|BTC|ETH|ZEC)_(?:1m|5m|15m|1h|6h|1d)\.(?:csv|json)|inputs\/[a-f0-9]{64}\/(?:SOL|BTC|ETH|ZEC)_(?:1m|5m|15m|1h|6h|1d)\.(?:csv|json)|bootstrap\/(?:SOL|BTC|ETH|ZEC)\.json)$/;
const response = (status, value) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
const hash = async bytes => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), n => n.toString(16).padStart(2, '0')).join('');
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));

async function authorized(request, secret) {
  if (typeof secret !== 'string' || secret.length < 32) return false;
  const actual = new TextEncoder().encode(request.headers.get('Authorization') || '');
  const expected = new TextEncoder().encode(`Bearer ${secret}`);
  const [a, b] = await Promise.all([crypto.subtle.digest('SHA-256', actual), crypto.subtle.digest('SHA-256', expected)]);
  let mismatch = 0;
  const left = new Uint8Array(a), right = new Uint8Array(b);
  for (let i = 0; i < left.length; i++) mismatch |= left[i] ^ right[i];
  return mismatch === 0;
}

async function bounded(request, maximum) {
  const reader = request.body?.getReader();
  if (!reader) return new Uint8Array();
  const chunks = []; let bytes = 0;
  try {
    while (true) {
      const next = await reader.read();
      if (next.done) break;
      bytes += next.value.length;
      if (bytes > maximum) throw new Error('body_too_large');
      chunks.push(next.value);
    }
  } finally { await reader.cancel().catch(() => {}); }
  const output = new Uint8Array(bytes); let offset = 0;
  for (const item of chunks) { output.set(item, offset); offset += item.length; }
  return output;
}

export function validateManifest(value) {
  if (!exact(value, ['schemaVersion', 'epoch', 'sequence', 'files']) || value.schemaVersion !== 1 || !Number.isSafeInteger(value.epoch) || value.epoch < 1 || !Number.isSafeInteger(value.sequence) || value.sequence < 1 || !value.files || typeof value.files !== 'object' || Array.isArray(value.files)) return false;
  let total = 0;
  if (Object.keys(value.files).length > 20000) return false;
  for (const [path, file] of Object.entries(value.files)) {
    if (!STATE_PATH.test(path) || !exact(file, ['bytes', 'sha256', 'chunks']) || !Number.isSafeInteger(file.bytes) || file.bytes < 0 || typeof file.sha256 !== 'string' || !DIGEST.test(file.sha256) || !Array.isArray(file.chunks) || file.chunks.length !== Math.ceil(file.bytes / CHUNK_BYTES) || file.chunks.some(key => typeof key !== 'string' || !DIGEST.test(key))) return false;
    total += file.bytes;
    if (total > MAX_STATE_BYTES) return false;
  }
  return true;
}

export class RuntimeOwner {
  constructor(ctx, env) { this.ctx = ctx; this.env = env; this.starting = null; }

  async restart(request) {
    if (!await authorized(request, this.env.RUNTIME_STATE_TOKEN)) return response(401, { error: 'authentication_required' });
    if (request.method !== 'POST') return response(405, { error: 'method_not_allowed' });
    const rawEpoch = request.headers.get('X-Runtime-Epoch') || '';
    const epoch = Number(rawEpoch);
    if (!/^[1-9][0-9]*$/.test(rawEpoch) || !Number.isSafeInteger(epoch) || epoch >= Number.MAX_SAFE_INTEGER) return response(409, { error: 'owner_epoch_changed' });
    if (request.headers.get('Content-Type')?.split(';')[0].trim() !== 'application/json') return response(415, { error: 'json_required' });
    let body;
    try { body = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(await bounded(request, 128))); }
    catch (error) { if (error?.message === 'body_too_large') throw error; return response(400, { error: 'invalid_restart_request' }); }
    if (!exact(body, ['action']) || body.action !== 'restart') return response(400, { error: 'invalid_restart_request' });
    return this.ctx.blockConcurrencyWhile(async () => {
      if (epoch !== await this.ctx.storage.get('epoch')) return response(409, { error: 'owner_epoch_changed' });
      const head = await this.ctx.storage.get('head');
      if (!head || !this.env.STATE) return response(409, { error: 'committed_checkpoint_required' });
      const object = await this.env.STATE.get(head.key);
      if (!object || object.size > MANIFEST_BYTES) return response(503, { error: 'checkpoint_integrity' });
      const raw = await object.arrayBuffer();
      let manifest;
      try { manifest = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(raw)); }
      catch { return response(503, { error: 'checkpoint_integrity' }); }
      if (await hash(raw) !== head.sha256 || !validateManifest(manifest) || manifest.sequence !== head.sequence || manifest.epoch !== head.epoch) return response(503, { error: 'checkpoint_integrity' });
      if (!this.ctx.container?.running) return response(409, { error: 'runtime_not_running' });
      const fenced = await this.ctx.storage.transaction(async txn => {
        const current = await txn.get('head');
        if (await txn.get('epoch') !== epoch || current?.key !== head.key || current?.sha256 !== head.sha256) return false;
        await txn.put('epoch', epoch + 1);
        // A failed destroy must also force the normal start path to retry it.
        await txn.put('image', null);
        return true;
      });
      if (!fenced) return response(409, { error: 'owner_epoch_changed' });
      try { await this.ctx.container.destroy('operator_checkpointed_restart'); }
      finally { await this.ctx.storage.setAlarm(Date.now() + 1000); }
      return response(202, { status: 'restart_scheduled', previousEpoch: epoch, epoch: epoch + 1, checkpointSequence: head.sequence });
    });
  }

  async state(request, path) {
    if (!await authorized(request, this.env.RUNTIME_STATE_TOKEN)) return response(401, { error: 'authentication_required' });
    const rawEpoch = request.headers.get('X-Runtime-Epoch') || '';
    const epoch = Number(rawEpoch);
    if (!/^[1-9][0-9]*$/.test(rawEpoch) || !Number.isSafeInteger(epoch) || epoch !== await this.ctx.storage.get('epoch')) return response(409, { error: 'owner_epoch_changed' });
    if (!this.env.STATE) return response(503, { error: 'durable_state_unavailable' });
    if (path === '/internal/state/manifest' && request.method === 'GET') {
      const head = await this.ctx.storage.get('head');
      if (!head) return response(404, { error: 'no_checkpoint' });
      const object = await this.env.STATE.get(head.key);
      if (!object) return response(503, { error: 'checkpoint_missing' });
      const raw = await object.arrayBuffer();
      if (raw.byteLength > MANIFEST_BYTES || await hash(raw) !== head.sha256) return response(503, { error: 'checkpoint_integrity' });
      return new Response(raw, { headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } });
    }
    const chunk = /^\/internal\/state\/chunks\/([a-f0-9]{64})$/.exec(path)?.[1];
    if (chunk && request.method === 'GET') {
      const object = await this.env.STATE.get(`v1/chunks/${chunk}`);
      if (!object || object.size > CHUNK_BYTES) return response(503, { error: 'checkpoint_chunk_missing' });
      return new Response(object.body, { headers: { 'Content-Type': 'application/octet-stream', 'Cache-Control': 'no-store' } });
    }
    if (chunk && request.method === 'PUT') {
      const raw = await bounded(request, CHUNK_BYTES);
      if (!raw.length || await hash(raw) !== chunk) return response(400, { error: 'checkpoint_chunk_integrity' });
      const receipt = await this.ctx.storage.get(`chunk:${chunk}`);
      if (receipt === undefined) {
        const key = `v1/chunks/${chunk}`;
        const existing = await this.env.STATE.get(key);
        if (existing) {
          if (existing.size > CHUNK_BYTES || await hash(await existing.arrayBuffer()) !== chunk) return response(409, { error: 'immutable_chunk_conflict' });
        } else {
          const saved = await this.env.STATE.put(key, raw, { onlyIf: { etagDoesNotMatch: '*' }, customMetadata: { sha256: chunk } });
          if (!saved) return response(503, { error: 'chunk_store_unconfirmed' });
        }
        // Check the fence again after the external R2 operation.
        const accepted = await this.ctx.storage.transaction(async txn => {
          if (await txn.get('epoch') !== epoch) return false;
          await txn.put(`chunk:${chunk}`, raw.length);
          return true;
        });
        if (!accepted) return response(409, { error: 'owner_epoch_changed' });
      } else if (receipt !== raw.length) return response(409, { error: 'immutable_chunk_conflict' });
      return response(200, { sha256: chunk, bytes: raw.length });
    }
    if (path === '/internal/state/manifest' && request.method === 'PUT') {
      const raw = await bounded(request, MANIFEST_BYTES);
      let manifest;
      try { manifest = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(raw)); } catch { return response(400, { error: 'invalid_checkpoint_manifest' }); }
      if (!validateManifest(manifest) || manifest.epoch !== epoch) return response(400, { error: 'invalid_checkpoint_manifest' });
      const previous = await this.ctx.storage.get('head');
      if (manifest.sequence !== (previous?.sequence || 0) + 1) return response(409, { error: 'checkpoint_sequence_changed' });
      const keys = [...new Set(Object.values(manifest.files).flatMap(file => file.chunks))];
      const lengths = new Map();
      for (let offset = 0; offset < keys.length; offset += 128) {
        const entries = await this.ctx.storage.get(keys.slice(offset, offset + 128).map(key => `chunk:${key}`));
        for (const key of keys.slice(offset, offset + 128)) {
          const length = entries.get(`chunk:${key}`);
          if (!Number.isInteger(length)) return response(409, { error: 'checkpoint_chunk_unverified' });
          lengths.set(key, length);
        }
      }
      for (const file of Object.values(manifest.files)) {
        if (file.chunks.some((key, index) => lengths.get(key) !== Math.min(CHUNK_BYTES, file.bytes - index * CHUNK_BYTES))) return response(400, { error: 'invalid_checkpoint_lengths' });
      }
      const sha256 = await hash(raw);
      const key = `v1/manifests/${epoch}/${manifest.sequence}/${sha256}.json`;
      const object = await this.env.STATE.put(key, raw, { onlyIf: { etagDoesNotMatch: '*' }, httpMetadata: { contentType: 'application/json' }, customMetadata: { sha256 } });
      if (!object && !await this.env.STATE.head(key)) return response(503, { error: 'checkpoint_store_unconfirmed' });
      const published = await this.ctx.storage.transaction(async txn => {
        const head = await txn.get('head');
        if (await txn.get('epoch') !== epoch || (head?.sequence || 0) + 1 !== manifest.sequence) return false;
        await txn.put('head', { key, sha256, sequence: manifest.sequence, epoch });
        return true;
      });
      return published ? response(200, { sequence: manifest.sequence, sha256, epoch }) : response(409, { error: 'checkpoint_sequence_changed' });
    }
    return response(404, { error: 'not_found' });
  }

  async start() {
    await this.ctx.blockConcurrencyWhile(async () => {
      const container = this.ctx.container;
      if (!container || !container.images?.base) throw new Error('container_not_configured');
      const origin = new URL(this.env.RUNTIME_PUBLIC_ORIGIN);
      if (origin.protocol !== 'https:' || origin.username || origin.password || origin.pathname !== '/' || origin.search || origin.hash || typeof this.env.ENGINE_TOKEN !== 'string' || this.env.ENGINE_TOKEN.length < 32 || typeof this.env.RUNTIME_STATE_TOKEN !== 'string' || this.env.RUNTIME_STATE_TOKEN.length < 32) throw new Error('runtime_not_configured');
      const image = container.images.base;
      if (container.running && await this.ctx.storage.get('image') !== image) {
        // Published state is already in R2. A new epoch fences callbacks from
        // the old image before its explicitly owned container is replaced.
        await this.ctx.storage.put('epoch', (await this.ctx.storage.get('epoch') || 0) + 1);
        await container.destroy('analysis_image_upgrade');
      }
      if (!container.running) {
        const epoch = (await this.ctx.storage.get('epoch') || 0) + 1;
        await this.ctx.storage.put('epoch', epoch);
        container.start({ image, instance: 'standard-1', enableInternet: true, env: { ENGINE_EPOCH: String(epoch), ENGINE_STATE_URL: origin.origin, ENGINE_STATE_TOKEN: this.env.RUNTIME_STATE_TOKEN, ENGINE_TOKEN: this.env.ENGINE_TOKEN, ENGINE_DATA_ROOT: '/data' } });
        await this.ctx.storage.put('image', image);
        this.ctx.waitUntil(container.monitor().catch(() => {}).finally(() => this.ctx.storage.setAlarm(Date.now() + 1000)));
      }
      await container.setInactivityTimeout(30 * 60 * 1000);
      await this.ctx.storage.setAlarm(Date.now() + 30000);
    });
  }

  async ensure() {
    if (!this.starting) this.starting = this.start().finally(() => { this.starting = null; });
    await this.starting;
    // Never block incoming checkpoint callbacks while waiting for Python:
    // Python restores state through this same DO before it becomes ready.
    for (let attempt = 0; attempt < 8; attempt++) {
      try {
        const ready = await this.ctx.container.getTcpPort(8790).fetch('http://analysis.container/health', { headers: { Authorization: `Bearer ${this.env.ENGINE_TOKEN}` }, signal: AbortSignal.timeout(1500) });
        if (ready.ok) return;
      } catch { /* A running VM is not an application readiness receipt. */ }
      await new Promise(resolve => setTimeout(resolve, 250));
    }
    throw new Error('container_starting');
  }

  async fetch(request) {
    try {
      if (request.headers.has('Origin')) return response(403, { error: 'browser_origin_forbidden' });
      const url = new URL(request.url);
      if (url.pathname === '/internal/runtime/restart') return await this.restart(request);
      if (url.pathname.startsWith('/internal/state/')) return await this.state(request, url.pathname);
      if (!await authorized(request, this.env.ENGINE_TOKEN)) return response(401, { error: 'authentication_required' });
      if (!['/health', '/v1/strategies', '/v1/oracle', '/v1/backtests', '/v1/jobs', '/v1/signals'].includes(url.pathname) && !/^\/v1\/jobs\/[0-9a-f-]{36}$/.test(url.pathname)) return response(404, { error: 'not_found' });
      if (!['GET', 'POST'].includes(request.method)) return response(405, { error: 'method_not_allowed' });
      // BaseHTTPRequestHandler requires a declared length. Buffer only the
      // bounded JSON request, rather than forwarding an unknown-length stream.
      const body = request.method === 'POST' ? await bounded(request, 4096) : undefined;
      await this.ensure();
      const result = await this.ctx.container.getTcpPort(8790).fetch(new Request(`http://analysis.container${url.pathname}${url.search}`, { method: request.method, headers: { Authorization: `Bearer ${this.env.ENGINE_TOKEN}`, ...(request.headers.has('Content-Type') ? { 'Content-Type': request.headers.get('Content-Type') } : {}), ...(body ? { 'Content-Length': String(body.length) } : {}) }, body, signal: AbortSignal.timeout(60000), redirect: 'manual' }));
      if (url.pathname === '/health' && result.ok) {
        const value = await result.json();
        return response(200, { ...value, deployment: { image: this.ctx.container.images.base, epoch: await this.ctx.storage.get('epoch') } });
      }
      return result;
    } catch (error) { return error?.message === 'body_too_large' ? response(413, { error: 'invalid_body_size' }) : response(503, { error: 'runtime_unavailable' }); }
  }

  async alarm() {
    try { await this.ensure(); }
    finally { await this.ctx.storage.setAlarm(Date.now() + 30000); }
  }
}

export default {
  async fetch(request, env) {
    if (!env.RUNTIME || request.headers.has('Origin')) return response(503, { error: 'runtime_unavailable' });
    // User-controlled names never select containers or create extra instances.
    return env.RUNTIME.get(env.RUNTIME.idFromName('public-analysis-v1')).fetch(request);
  },
};
