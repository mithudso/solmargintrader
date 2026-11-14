import test from 'node:test';
import assert from 'node:assert/strict';
import { request } from '../src/jupiter/http.js';

test('ambiguous POST transport errors and server errors are never retried automatically', async () => {
  for (const fetchImpl of [
    async () => { throw new Error('TEST_PRIVATE_NETWORK_VALUE'); },
    async () => new Response('TEST_PRIVATE_RESPONSE_VALUE', { status: 503 }),
  ]) {
    let calls = 0;
    await assert.rejects(() => request({
      url: 'https://unit.invalid/create', init: { method: 'POST' }, maxAttempts: 4,
      sleepImpl: async () => {}, fetchImpl: async (...args) => { calls++; return fetchImpl(...args); },
    }), (err) => !JSON.stringify(err).includes('TEST_PRIVATE_'));
    assert.equal(calls, 1);
  }
});

test('HTTP timeout covers response body consumption after headers arrive', async () => {
  await assert.rejects(() => request({
    url: 'https://unit.invalid/read', timeoutMs: 10, maxAttempts: 1,
    fetchImpl: async (_url, { signal }) => ({
      ok: true, status: 200,
      text: () => new Promise((_resolve, reject) => signal.addEventListener('abort', () => {
        const error = new Error('aborted'); error.name = 'AbortError'; reject(error);
      }, { once: true })),
    }),
  }), /timed out/);
});

test('GET retains bounded retry after transient errors', async () => {
  let calls = 0;
  const result = await request({
    url: 'https://unit.invalid/read', sleepImpl: async () => {},
    fetchImpl: async () => ++calls === 1 ? new Response('', { status: 503 }) : new Response('{"ok":true}'),
  });
  assert.equal(calls, 2);
  assert.deepEqual(result, { ok: true });
});

test('transport diagnostics identify attempts and outcomes without headers, query or body', async () => {
  const logs = [];
  await assert.rejects(() => request({
    url: 'https://unit.invalid/order?api_key=TEST_PRIVATE_QUERY',
    init: { method: 'POST', headers: { Authorization: 'TEST_PRIVATE_HEADER' }, body: 'TEST_PRIVATE_BODY' },
    fetchImpl: async () => new Response('TEST_PRIVATE_RESPONSE', { status: 503 }),
    log: (event) => logs.push(event),
  }));
  assert.ok(logs.some((event) => event.msg === 'request started'));
  assert.ok(logs.some((event) => event.level === 'error' && event.status === 503));
  assert.ok(!JSON.stringify(logs).includes('TEST_PRIVATE_'));
});


test('response bodies stop at a byte cap and cancel the stream for success and error statuses', async () => {
  for (const status of [200, 503]) {
    let pulls = 0, cancelled = false, calls = 0;
    const body = new ReadableStream({
      pull(controller) {
        pulls++;
        controller.enqueue(new Uint8Array(1024).fill(32));
        if (pulls === 20) controller.close();
      },
      cancel() { cancelled = true; },
    });
    await assert.rejects(() => request({
      url: 'https://unit.invalid/read', maxResponseBytes: 1024, maxAttempts: 1, log: () => {},
      fetchImpl: async () => { calls++; return new Response(body, { status }); },
    }), /response exceeds size limit/);
    assert.equal(calls, 1);
    assert.ok(pulls < 20);
    assert.equal(cancelled, true);
  }
});

test('response byte cap preserves valid UTF-8 JSON and refuses oversized declared bodies', async () => {
  const encoded = new TextEncoder().encode('{"value":"😀"}');
  assert.deepEqual(await request({ url: 'https://unit.invalid/read', maxResponseBytes: encoded.length,
    fetchImpl: async () => new Response(new ReadableStream({ start(controller) {
      const cut = encoded.indexOf(0xf0) + 2;
      controller.enqueue(encoded.slice(0, cut)); controller.enqueue(encoded.slice(cut)); controller.close();
    } })), log: () => {} }), { value: '😀' });
  await assert.rejects(() => request({ url: 'https://unit.invalid/read', maxResponseBytes: encoded.length - 1,
    fetchImpl: async () => new Response(encoded), log: () => {} }), /response exceeds size limit/);
});


test('oversized Content-Length refuses before pulling any body bytes', async () => {
  let read = false, cancelled = false;
  await assert.rejects(() => request({ url: 'https://unit.invalid/read', maxResponseBytes: 100, log: () => {},
    fetchImpl: async () => ({ status: 200, ok: true, headers: { get: () => '101' },
      body: { cancel() { cancelled = true; return Promise.resolve(); } },
      text() { read = true; return Promise.resolve('{}'); } }),
  }), /response exceeds size limit/);
  assert.equal(read, false); assert.equal(cancelled, true);
});
