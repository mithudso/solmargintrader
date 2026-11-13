import { TradeError, executionAvailable, getTradeStatus, listTradeIntents, requestTrade, submitTrade } from './trades.js';

export const MCP_PROTOCOL_VERSION = '2025-11-25';
const DIAGNOSTIC_EVENTS = Object.freeze({
  authDenied: ['warn', 'authenticate', 'denied', 'invalid_token'],
  authUnavailable: ['error', 'authenticate', 'failed', 'service_unavailable'],
  originDenied: ['warn', 'origin', 'denied', 'invalid_origin'],
  scopeDenied: ['warn', 'authorize_tool', 'denied', 'insufficient_scope'],
  toolRefused: ['warn', 'tool_call', 'refused', 'tool_error'],
  toolUnavailable: ['error', 'tool_call', 'failed', 'service_unavailable'],
});
function diagnostic(key) {
  const [level, operation, outcome, reason] = DIAGNOSTIC_EVENTS[key];
  // Only fixed vocabulary reaches diagnostics; a failed sink cannot change a response.
  try { console[level](JSON.stringify({ event: 'oraclebot.mcp', operation, outcome, reason })); }
  catch {}
}
const scopes = { oraclebot_get_status: 'status:read', oraclebot_request_trade: 'trade:prepare', oraclebot_get_trade_status: 'status:read', oraclebot_submit_trade: 'trade:submit' };
const emptySchema = { type: 'object', properties: {}, additionalProperties: false };
const intentSchema = { type: 'object', properties: { intentId: { type: 'string', minLength: 1, maxLength: 128, pattern: '^[A-Za-z0-9_.:-]+$' } }, required: ['intentId'], additionalProperties: false };
const tools = [
  { name: 'oraclebot_get_status', title: 'Oraclebot account status', description: 'Read your wallet, account, bot status, preauthorization and owned trade intents. Availability does not establish a live venue connection.', inputSchema: emptySchema, annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false } },
  { name: 'oraclebot_request_trade', title: 'Prepare a preauthorized trade', description: 'Prepare an expiring trade within your wallet-approved policy. budgetUsd is the maximum USD notional plus all fees. Preparation does not place an order. Refuses if a verified customer execution adapter is unavailable.',
    inputSchema: { type: 'object', properties: {
      idempotencyKey: { type: 'string', minLength: 1, maxLength: 128, pattern: '^[A-Za-z0-9_.:-]+$' },
      venue: { type: 'string', enum: ['coinbase', 'jupiter'] }, asset: { type: 'string', enum: ['SOL', 'BTC', 'ETH', 'ZEC'] },
      side: { type: 'string', enum: ['buy', 'sell', 'long', 'short'] }, budgetUsd: { type: 'number', exclusiveMinimum: 0, maximum: 1000000, multipleOf: 0.01 },
      product: { type: 'string', enum: ['spot', 'perpetual'], default: 'spot' }, leverage: { type: 'integer', minimum: 1, maximum: 5, default: 1 },
    }, required: ['idempotencyKey', 'venue', 'asset', 'side', 'budgetUsd'], additionalProperties: false },
    annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true } },
  { name: 'oraclebot_get_trade_status', title: 'Read an owned trade intent', description: 'Read one of your wallet-bound intents. Unknown submission outcomes require venue reconciliation and are never automatically resubmitted.', inputSchema: intentSchema, annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false } },
  { name: 'oraclebot_submit_trade', title: 'Submit a preauthorized trade', description: 'Submit an owned, prepared intent using its verified customer wallet delegation and current policy. The initial policy consent covers this call; there is no per-trade wallet approval. An unknown outcome must not be retried at the venue.', inputSchema: intentSchema, annotations: { readOnlyHint: false, destructiveHint: true, idempotentHint: true, openWorldHint: true } },
];
const plain = value => value !== null && typeof value === 'object' && !Array.isArray(value);
function response(value, status = 200, headers = {}) {
  return new Response(value === null ? null : JSON.stringify(value), { status, headers: { ...(value === null ? {} : { 'Content-Type': 'application/json' }), 'Cache-Control': 'no-store', 'MCP-Protocol-Version': MCP_PROTOCOL_VERSION, ...headers } });
}
function rpcError(id, code, message, status = 200, data) {
  return response({ jsonrpc: '2.0', id, error: { code, message, ...(data ? { data } : {}) } }, status);
}
function challenge(request, env, error, scope) {
  const origin = new URL(env.APP_ORIGIN || request.url).origin;
  const headers = { 'WWW-Authenticate': `Bearer resource_metadata="${origin}/.well-known/oauth-protected-resource/mcp"${error ? `, error="${error}"` : ''}${scope ? `, scope="${scope}"` : ''}` };
  return headers;
}
function validOrigin(request, env, principal) {
  const origin = request.headers.get('Origin');
  if (!origin) return true;
  const allowed = new Set([new URL(env.APP_ORIGIN || request.url).origin]);
  let redirects = principal.client?.redirect_uris;
  if (typeof redirects === 'string') { try { redirects = JSON.parse(redirects); } catch { return false; } }
  for (const uri of Array.isArray(redirects) ? redirects : []) { try { allowed.add(new URL(uri).origin); } catch { /* Invalid registrations confer no origin. */ } }
  return allowed.has(origin);
}
async function bodyJson(request) {
  const declared = request.headers.get('Content-Length');
  if (declared && (!/^\d+$/.test(declared) || Number(declared) > 65_536)) throw new RangeError('size');
  const reader = request.body?.getReader();
  if (!reader) throw new SyntaxError('body');
  const chunks = []; let total = 0;
  try {
    while (true) { const { done, value } = await reader.read(); if (done) break; total += value.byteLength; if (total > 65_536) throw new RangeError('size'); chunks.push(value); }
  } finally { await reader.cancel().catch(() => {}); }
  const bytes = new Uint8Array(total); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
}
function validate(schema, value) {
  if (schema.type === 'object') {
    if (!plain(value) || (schema.additionalProperties === false && Object.keys(value).some(key => !Object.hasOwn(schema.properties, key)))) return false;
    if ((schema.required || []).some(key => !Object.hasOwn(value, key))) return false;
    return Object.entries(value).every(([key, item]) => schema.properties[key] && validate(schema.properties[key], item));
  }
  if (schema.type === 'string' && (typeof value !== 'string' || value.length < (schema.minLength || 0) || value.length > (schema.maxLength || Infinity) || (schema.pattern && !new RegExp(schema.pattern).test(value)))) return false;
  if (['number', 'integer'].includes(schema.type)) {
    if (typeof value !== 'number' || !Number.isFinite(value) || (schema.type === 'integer' && !Number.isInteger(value)) ||
        (schema.exclusiveMinimum !== undefined && value <= schema.exclusiveMinimum) || (schema.minimum !== undefined && value < schema.minimum) ||
        (schema.maximum !== undefined && value > schema.maximum) || (schema.multipleOf === 0.01
          ? !/^\d+(?:\.\d{1,2})?$/.test(String(value))
          : schema.multipleOf && Math.abs(value / schema.multipleOf - Math.round(value / schema.multipleOf)) > 0.000001)) return false;
  }
  return !schema.enum || schema.enum.includes(value);
}
function toolResult(value, isError = false) {
  return { content: [{ type: 'text', text: JSON.stringify(value) }], structuredContent: value, isError };
}
async function accountStatus(env, principal, services) {
  const account = await services.getStatus(principal.user);
  let policy = null;
  try { policy = principal.grant.policy_json ? JSON.parse(principal.grant.policy_json) : null; } catch { /* Auth never makes a corrupt policy executable. */ }
  return {
    wallet: principal.user.wallet, account,
    authorization: { scopes: [...principal.scopes], expiresAt: principal.grant.expires_at, policy },
    execution: { adapterConfigured: executionAvailable(env), mode: 'preauthorized', requiresWalletApprovalPerTrade: false,
      readiness: executionAvailable(env) ? 'requires_verified_customer_connection_and_delegation' : 'execution_unavailable',
      message: 'Policy consent alone cannot sign a transaction. Every trade requires a verified customer connection, delegated authority and fresh quote.' },
    tradeIntents: await listTradeIntents(env, principal),
  };
}
export async function handleMcp(request, env, services) {
  if (new URL(request.url).pathname !== '/mcp') return null;
  if (request.method !== 'POST') return response({ error: 'method_not_allowed', message: 'Use authenticated JSON-RPC POST. This endpoint has no SSE or HTTP session.' }, 405, { Allow: 'POST' });
  let principal;
  try {
    if (!/^Bearer [A-Za-z0-9._~-]+$/i.test(request.headers.get('Authorization') || '')) throw { status: 401 };
    principal = await services.authenticateAgent(request, env);
  } catch (error) {
    if (![401, 403].includes(error?.status)) {
      diagnostic('authUnavailable');
      return response({ error: 'temporarily_unavailable', message: 'Agent authentication is temporarily unavailable.' }, 503);
    }
    diagnostic('authDenied');
    const status = error.status;
    return response({ error: status === 403 ? 'access_denied' : 'invalid_token', message: 'A current Oraclebot agent bearer token is required.' }, status, challenge(request, env, 'invalid_token'));
  }
  if (!validOrigin(request, env, principal)) {
    diagnostic('originDenied');
    return response({ error: 'invalid_origin', message: 'This origin is not registered for this agent.' }, 403);
  }
  const version = request.headers.get('MCP-Protocol-Version');
  if (version && version !== MCP_PROTOCOL_VERSION) return rpcError(null, -32600, 'Unsupported protocol version. This endpoint implements MCP 2025-11-25.', 400);
  if (!request.headers.get('Content-Type')?.toLowerCase().match(/^application\/json(?:\s*;|$)/)) return response({ error: 'unsupported_media_type', message: 'Use application/json.' }, 415);
  const accept = request.headers.get('Accept');
  if (accept && !accept.includes('application/json') && !accept.includes('*/*')) return response({ error: 'not_acceptable', message: 'Accept application/json responses.' }, 406);
  let message;
  try { message = await bodyJson(request); }
  catch (error) { return rpcError(null, error instanceof RangeError ? -32600 : -32700, error instanceof RangeError ? 'Request exceeds the size limit.' : 'Parse error.', error instanceof RangeError ? 413 : 400); }
  const hasId = plain(message) && Object.hasOwn(message, 'id');
  const id = hasId && (message.id === null || typeof message.id === 'string' || typeof message.id === 'number') ? message.id : null;
  if (!plain(message) || Object.keys(message).some(key => !['jsonrpc', 'id', 'method', 'params'].includes(key)) || message.jsonrpc !== '2.0' ||
      typeof message.method !== 'string' || message.method.length > 128 || (hasId && id === null && message.id !== null) ||
      (typeof id === 'string' && id.length > 128) || (typeof id === 'number' && !Number.isFinite(id))) return rpcError(null, -32600, 'Invalid Request.', 400);
  const rawParams = Object.hasOwn(message, 'params') ? message.params : {};
  if (!plain(rawParams) || (Object.hasOwn(rawParams, '_meta') && !plain(rawParams._meta))) return hasId ? rpcError(id, -32602, 'Invalid params.') : response(null, 202);
  // Request metadata is protocol metadata only. It never becomes trade input.
  const { _meta, ...params } = rawParams;
  if (message.method !== 'initialize' && !version) return rpcError(id, -32600, 'MCP-Protocol-Version: 2025-11-25 is required after initialization.', 400);
  if (!hasId) {
    if (message.method.startsWith('notifications/')) return response(null, 202);
    return rpcError(null, -32600, 'Requests require an ID.', 400);
  }
  if (message.method === 'initialize') {
    if (Object.keys(params).some(key => !['protocolVersion', 'capabilities', 'clientInfo'].includes(key)) ||
        typeof params.protocolVersion !== 'string' || !plain(params.capabilities) || !plain(params.clientInfo) ||
        typeof params.clientInfo.name !== 'string' || !params.clientInfo.name.length || params.clientInfo.name.length > 128 ||
        typeof params.clientInfo.version !== 'string' || params.clientInfo.version.length > 128) return rpcError(id, -32602, 'Invalid initialization params.');
    // Negotiation returns our supported version; clients must reject it if unsupported.
    return response({ jsonrpc: '2.0', id, result: { protocolVersion: MCP_PROTOCOL_VERSION, capabilities: { tools: { listChanged: false } }, serverInfo: { name: 'oraclebot', version: '1.0.0' }, instructions: 'Trades use your wallet-bound, limited preauthorization. Execution requires your verified customer venue connection and delegated signer; unavailable execution refuses safely.' } });
  }
  if (message.method === 'ping') {
    if (Object.keys(params).length) return rpcError(id, -32602, 'Invalid params.');
    return response({ jsonrpc: '2.0', id, result: {} });
  }
  if (message.method === 'tools/list') {
    if (Object.keys(params).some(key => key !== 'cursor') || params.cursor !== undefined) return rpcError(id, -32602, 'Pagination is not supported.');
    return response({ jsonrpc: '2.0', id, result: { tools: tools.filter(tool => principal.scopes.has(scopes[tool.name])) } });
  }
  if (message.method !== 'tools/call') return rpcError(id, -32601, 'Method not found.');
  if (Object.keys(params).some(key => !['name', 'arguments'].includes(key)) || typeof params.name !== 'string') return rpcError(id, -32602, 'Invalid tool params.');
  const tool = tools.find(item => item.name === params.name);
  if (!tool) return rpcError(id, -32602, 'Unknown tool.');
  const requiredScope = scopes[tool.name];
  if (!principal.scopes.has(requiredScope)) {
    diagnostic('scopeDenied');
    return response({ jsonrpc: '2.0', id, error: { code: -32001, message: 'Insufficient scope.', data: { scope: requiredScope } } }, 403, challenge(request, env, 'insufficient_scope', requiredScope));
  }
  const args = Object.hasOwn(params, 'arguments') ? params.arguments : {};
  if (!validate(tool.inputSchema, args)) return rpcError(id, -32602, 'Invalid tool arguments. Wallet, account, signer and endpoint overrides are not accepted.');
  try {
    let result;
    if (tool.name === 'oraclebot_get_status') result = await accountStatus(env, principal, services);
    else if (tool.name === 'oraclebot_request_trade') result = await requestTrade(env, principal, args, services);
    else if (tool.name === 'oraclebot_get_trade_status') result = await getTradeStatus(env, principal, args);
    else result = await submitTrade(env, principal, args, services);
    return response({ jsonrpc: '2.0', id, result: toolResult(result) });
  } catch (error) {
    const safe = error instanceof TradeError ? { code: error.code, message: error.message } :
      ['subscription_required', 'subscription_inactive', 'plan_required'].includes(error?.code) ? { code: 'subscription_required', message: 'A current subscription is required.' } :
        { code: 'service_unavailable', message: 'The requested account service is unavailable.' };
    diagnostic(safe.code === 'service_unavailable' || (error instanceof TradeError && error.status >= 500) ? 'toolUnavailable' : 'toolRefused');
    return response({ jsonrpc: '2.0', id, result: toolResult(safe, true) });
  }
}
