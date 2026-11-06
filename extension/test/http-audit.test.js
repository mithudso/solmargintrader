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
