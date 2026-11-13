import test from 'node:test';
import assert from 'node:assert/strict';
import { environment, seedUser, request, ORIGIN, at } from './helpers/d1.js';
import { authenticateAgent } from '../src/oauth.js';
import { handleMcp, MCP_PROTOCOL_VERSION } from '../src/mcp.js';

const hash = async value => Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))).toString('hex');
async function fixture(options = {}) {
  const env = options.env || environment(); const owner = await seedUser(env); const clientId = crypto.randomUUID(); const grantId = crypto.randomUUID();
  const scope = options.scope || 'status:read trade:prepare trade:submit'; const expiresAt = options.expiresAt ?? at() + 3600;
  const policy = scope.includes('trade:') ? { venues: ['coinbase', 'jupiter'], assets: ['SOL'], maxTradeUsd: 20, maxTotalUsd: 30, expiresAt } : null;
  const policyJson = policy ? JSON.stringify(policy) : null;
  env.sqlite.prepare('INSERT INTO agent_clients(id,name,redirect_uris,created_at) VALUES (?,?,?,?)').run(clientId, 'Customer agent', JSON.stringify(['https://agent.example/callback']), at());
  env.sqlite.prepare('INSERT INTO agent_grants(id,user_id,client_id,resource,scope,policy_json,policy_hash,created_at,expires_at) VALUES (?,?,?,?,?,?,?,?,?)').run(grantId, owner.id, clientId, options.resource || `${ORIGIN}/mcp`, scope, policyJson, policyJson ? await hash(policyJson) : null, at(), expiresAt);
  const token = Buffer.from(crypto.getRandomValues(new Uint8Array(32))).toString('base64url');
  env.sqlite.prepare('INSERT INTO agent_access_tokens(token_hash,grant_id,user_id,scope,created_at,expires_at) VALUES (?,?,?,?,?,?)').run(await hash(token), grantId, owner.id, options.tokenScope || scope, at(), options.tokenExpiresAt ?? at() + 900);
  env.sqlite.prepare("INSERT INTO subscriptions(user_id,stripe_subscription_id,status,period_end,updated_at,plan_id) VALUES (?,?,'active',?,?,'starter')").run(owner.id, `sub_test_${owner.id}`, at() + 3600, at());
  const services = { authenticateAgent, getStatus: async user => ({ wallet: user.wallet, bots: [{ id: `bot-${user.id}` }] }), requireEntitlement: async () => {} };
  const send = async (method, params = {}, options = {}) => {
    const response = await handleMcp(request('/mcp', { method: 'POST', body: { jsonrpc: '2.0', id: 1, method, params }, headers: { Authorization: `Bearer ${token}`, 'MCP-Protocol-Version': MCP_PROTOCOL_VERSION, ...options.headers }, ...options }), env, services);
    return { response, body: response.status === 202 ? null : await response.json() };
  };
  return { env, owner, grantId, token, services, send };
}
const trade = { idempotencyKey: 'my-trade', venue: 'jupiter', asset: 'SOL', side: 'buy', budgetUsd: 10 };

test('MCP only handles its route and uses POST without SSE or server sessions', async () => {
  const { env, services } = await fixture();
  assert.equal(await handleMcp(request('/api/me'), env, services), null);
  for (const method of ['GET', 'DELETE', 'PUT', 'OPTIONS']) {
    const response = await handleMcp(request('/mcp', { method }), env, services);
    assert.equal(response.status, 405); assert.equal(response.headers.get('Allow'), 'POST'); assert.equal(response.headers.get('Mcp-Session-Id'), null);
  }
});
test('every POST needs its own bearer credential; browser cookies are not MCP authority', async () => {
  const { env, owner, services, token } = await fixture();
  for (const authorization of [undefined, 'Bearer bad', 'Basic ignored', `Bearer ${token} trailing`]) {
    const response = await handleMcp(request('/mcp', { method: 'POST', cookie: owner.cookie, body: { jsonrpc: '2.0', id: 1, method: 'ping' }, headers: authorization ? { Authorization: authorization } : {} }), env, services);
    assert.equal(response.status, 401); assert.match(response.headers.get('WWW-Authenticate'), /Bearer resource_metadata="https:\/\/oraclebot\.example\/\.well-known\/oauth-protected-resource\/mcp"/);
    assert.doesNotMatch(await response.text(), new RegExp(owner.wallet));
  }
});
test('real OAuth authentication rejects expired, revoked, wrong-resource and invalid-scope tokens', async () => {
  for (const options of [{ tokenExpiresAt: at() - 1 }, { expiresAt: at() - 1 }, { resource: 'https://other.example/mcp' }, { scope: 'status:read', tokenScope: 'status:read trade:submit' }, { revoke: true }]) {
    const f = await fixture(options);
    if (options.revoke) f.env.sqlite.prepare('UPDATE agent_grants SET revoked_at=? WHERE id=?').run(at(), f.grantId);
    assert.equal((await f.send('ping')).response.status, 401);
  }
});
test('initialization advertises only the explicit 2025 profile and stateless tools capability', async () => {
  const { send } = await fixture();
  const result = await send('initialize', { protocolVersion: '2025-11-25', capabilities: {}, clientInfo: { name: 'Test agent', version: '1' } });
  assert.equal(result.response.status, 200); assert.equal(result.body.result.protocolVersion, '2025-11-25');
  assert.deepEqual(result.body.result.capabilities, { tools: { listChanged: false } }); assert.equal(result.response.headers.get('Mcp-Session-Id'), null);
  assert.equal((await send('server/discover')).body.error.code, -32601);
});
test('unsupported protocol headers and omitted post-initialization version refuse clearly', async () => {
  const { send, env, token, services } = await fixture();
  const result = await send('ping', {}, { headers: { Authorization: `Bearer ${token}`, 'MCP-Protocol-Version': '2026-07-28' } });
  assert.equal(result.response.status, 400); assert.match(result.body.error.message, /2025-11-25/);
  const response = await handleMcp(request('/mcp', { method: 'POST', body: { jsonrpc: '2.0', id: 1, method: 'ping' }, headers: { Authorization: `Bearer ${token}` } }), env, services);
  assert.equal(response.status, 400);
  const init = await handleMcp(request('/mcp', { method: 'POST', body: { jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2025-11-25', capabilities: {}, clientInfo: { name: 'Agent', version: '1' } } }, headers: { Authorization: `Bearer ${token}` } }), env, services);
  assert.equal(init.status, 200);
});
test('Origin is restricted to server origin and this token client registered redirect origin', async () => {
  const { send } = await fixture();
  assert.equal((await send('ping', {}, { origin: 'https://agent.example' })).response.status, 200);
  assert.equal((await send('ping', {}, { origin: 'https://attacker.example' })).response.status, 403);
  assert.equal((await send('ping', {}, { origin: 'null' })).response.status, 403);
});
test('notifications return an empty 202 and never invoke a trade', async () => {
  const { env, services, token } = await fixture(); let calls = 0;
  env.LIVE_EXECUTION_ENABLED = 'true'; env.USER_TRADE_EXECUTOR = { fetch() { calls++; throw new Error(); } };
  const headers = { Authorization: `Bearer ${token}`, 'MCP-Protocol-Version': MCP_PROTOCOL_VERSION };
  const notification = await handleMcp(request('/mcp', { method: 'POST', headers, body: { jsonrpc: '2.0', method: 'notifications/initialized' } }), env, services);
  assert.equal(notification.status, 202); assert.equal(await notification.text(), '');
  const invalid = await handleMcp(request('/mcp', { method: 'POST', headers, body: { jsonrpc: '2.0', method: 'tools/call', params: { name: 'oraclebot_request_trade', arguments: trade } } }), env, services);
  assert.equal(invalid.status, 400); assert.equal(calls, 0);
});
test('tool listing respects granted scopes and insufficient scope includes the required permission', async () => {
  const { send } = await fixture({ scope: 'status:read' });
  const listed = (await send('tools/list')).body.result.tools;
  assert.deepEqual(listed.map(tool => tool.name), ['oraclebot_get_status', 'oraclebot_get_trade_status']);
  assert.ok(listed.every(tool => tool.inputSchema.additionalProperties === false));
  const refused = await send('tools/call', { name: 'oraclebot_request_trade', arguments: trade });
  assert.equal(refused.response.status, 403); assert.equal(refused.body.error.code, -32001);
  assert.match(refused.response.headers.get('WWW-Authenticate'), /error="insufficient_scope", scope="trade:prepare"/);
});
test('tool argument schemas reject principal, signer, URL and account overrides', async () => {
  const { send } = await fixture();
  for (const field of ['wallet', 'userId', 'account', 'signer', 'url', 'connectionId']) {
    const result = await send('tools/call', { name: 'oraclebot_request_trade', arguments: { ...trade, [field]: 'override' } });
    assert.equal(result.body.error.code, -32602);
    assert.equal((await send('tools/call', { name: 'oraclebot_get_status', arguments: { [field]: 'override' } })).body.error.code, -32602);
  }
  for (const args of [{ ...trade, budgetUsd: 1.001 }, { ...trade, budgetUsd: '10' }, { ...trade, leverage: 1.5 }]) assert.equal((await send('tools/call', { name: 'oraclebot_request_trade', arguments: args })).body.error.code, -32602);
});
test('status shows only the authenticated wallet and truthfully reports absent customer execution', async () => {
  const f = await fixture(); const other = await fixture({ env: f.env });
  const status = (await f.send('tools/call', { name: 'oraclebot_get_status', arguments: {} })).body.result;
  assert.equal(status.isError, false); assert.equal(status.structuredContent.wallet, f.owner.wallet);
  assert.equal(status.structuredContent.account.bots[0].id, `bot-${f.owner.id}`);
  assert.equal(status.structuredContent.execution.readiness, 'execution_unavailable');
  assert.equal(status.structuredContent.execution.requiresWalletApprovalPerTrade, false);
  assert.doesNotMatch(JSON.stringify(status), new RegExp(other.owner.wallet));
  const tradeResult = (await f.send('tools/call', { name: 'oraclebot_request_trade', arguments: trade })).body.result;
  assert.equal(tradeResult.isError, true); assert.equal(tradeResult.structuredContent.code, 'execution_unavailable');
  assert.equal(f.env.sqlite.prepare('SELECT COUNT(*) AS n FROM agent_trade_intents').get().n, 0);
});
test('trade intent read and submit cannot cross from a second bearer wallet', async () => {
  const f = await fixture(); const other = await fixture({ env: f.env }); const id = crypto.randomUUID();
  const grant = f.env.sqlite.prepare('SELECT * FROM agent_grants WHERE id=?').get(f.grantId);
  f.env.sqlite.prepare(`INSERT INTO agent_trade_intents(id,user_id,wallet,grant_id,resource,policy_hash,idempotency_key,payload_hash,payload_json,state,reservation_cents,expires_at,created_at,updated_at)
    VALUES (?,?,?,?,?,?,?,?,?,'unknown',1000,?,?,?)`).run(id, f.owner.id, f.owner.wallet, f.grantId, `${ORIGIN}/mcp`, grant.policy_hash, 'owned', await hash('payload'), JSON.stringify(trade), at() + 60, at(), at());
  const ownerStatus = (await f.send('tools/call', { name: 'oraclebot_get_trade_status', arguments: { intentId: id } })).body.result;
  assert.equal(ownerStatus.structuredContent.wallet, f.owner.wallet);
  for (const name of ['oraclebot_get_trade_status', 'oraclebot_submit_trade']) {
    const result = (await other.send('tools/call', { name, arguments: { intentId: id } })).body.result;
    assert.equal(result.isError, true); assert.equal(result.structuredContent.code, 'intent_not_found'); assert.doesNotMatch(JSON.stringify(result), new RegExp(f.owner.wallet));
  }
});
test('strict JSON-RPC rejects malformed, oversized, batches, unknown methods and invalid schemas', async () => {
  const { env, token, services, send } = await fixture();
  const headers = { Authorization: `Bearer ${token}`, 'MCP-Protocol-Version': MCP_PROTOCOL_VERSION, 'Content-Type': 'application/json' };
  for (const [raw, code, status] of [['{', -32700, 400], ['[]', -32600, 400], ['{"jsonrpc":"1.0","method":"ping","id":1}', -32600, 400], ['{"jsonrpc":"2.0","method":"ping","id":true}', -32600, 400], ['x'.repeat(65537), -32600, 413]]) {
    const response = await handleMcp(new Request(`${ORIGIN}/mcp`, { method: 'POST', headers, body: raw }), env, services);
    assert.equal(response.status, status); assert.equal((await response.json()).error.code, code);
  }
  assert.equal((await send('does/not/exist')).body.error.code, -32601);
  assert.equal((await send('ping', { unexpected: true })).body.error.code, -32602);
  assert.equal((await send('ping', null)).body.error.code, -32602);
  assert.equal((await send('tools/call', { name: 'oraclebot_get_status', arguments: null })).body.error.code, -32602);
  assert.equal((await send('tools/call', { name: 'unknown', arguments: {} })).body.error.code, -32602);
  assert.deepEqual((await send('ping', { _meta: { progressToken: 'protocol-only' } })).body.result, {});
  assert.equal((await send('ping', { _meta: 'invalid' })).body.error.code, -32602);
  assert.equal((await send('initialize', { protocolVersion: '2025-11-25' })).body.error.code, -32602);
  const media = await handleMcp(new Request(`${ORIGIN}/mcp`, { method: 'POST', headers: { ...headers, 'Content-Type': 'text/plain' }, body: '{}' }), env, services);
  assert.equal(media.status, 415);
});
test('unexpected backend errors produce fixed public errors without leaking private text', async () => {
  const f = await fixture(); f.services.getStatus = async () => { throw new Error('private backend credential text'); };
  const result = await f.send('tools/call', { name: 'oraclebot_get_status', arguments: {} });
  assert.equal(result.body.result.isError, true); assert.equal(result.body.result.structuredContent.code, 'service_unavailable'); assert.doesNotMatch(JSON.stringify(result.body), /private backend/);
});
