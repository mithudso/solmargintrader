import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { createApiServer, createRequestHandler, tokenMatches } from '../tools/api-server.js';

test('API constructors refuse missing or empty bearer credentials', () => {
  for (const token of ['', ' ', undefined, null, false]) {
    assert.equal(tokenMatches(undefined, token), false);
    assert.throws(() => createRequestHandler({ deps: {}, token }), /token/i);
    assert.throws(() => createApiServer({ deps: {}, token }), /token/i);
  }
});

test('API errors and diagnostics never echo body or arbitrary upstream exception values', async () => {
  const secret = 'TEST_SENTINEL_PRIVATE_VALUE';
  const logs = [];
  const server = createApiServer({ token: 'unit-token', deps: {
    configStore: { getConfig: async () => { throw new Error(secret); } },
    log: (row) => logs.push(row),
  } });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    const malformed = await fetch(`${base}/v1/setApiKey`, {
      method: 'POST', headers: { Authorization: 'Bearer unit-token' }, body: `{"apiKey":"${secret}`,
    });
    assert.equal(malformed.status, 400);
    assert.ok(!(await malformed.text()).includes(secret));
    const upstream = await fetch(`${base}/v1/getConfig`, { headers: { Authorization: 'Bearer unit-token' } });
    assert.equal(upstream.status, 500);
    assert.ok(!(await upstream.text()).includes(secret));
    await fetch(`${base}/v1/getConfig`);
    assert.ok(logs.some((row) => row.level === 'error'));
    assert.ok(logs.some((row) => row.level === 'warn'));
    assert.ok(!JSON.stringify(logs).includes(secret));
  } finally {
    server.closeAllConnections();
    await new Promise((resolve) => server.close(resolve));
  }
});
