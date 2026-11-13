import { base58Decode } from '../../extension/src/wallet/solana.js';
import { validPolicyScope } from './policy-scope.js';

const SCOPES = ['status:read', 'trade:prepare', 'trade:submit'];
const MAX_BODY = 16384;
const ACCESS_TTL = 900;
const MAX_GRANT_TTL = 30 * 86400;
const now = () => Math.floor(Date.now() / 1000);
const query = (env, sql, ...args) => env.DB.prepare(sql).bind(...args);
const encoder = new TextEncoder();
const opaque = () => btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(32)))).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
const validToken = value => typeof value === 'string' && /^[A-Za-z0-9_-]{43}$/.test(value);
const validId = value => typeof value === 'string' && /^[a-f0-9-]{36}$/.test(value);
const trading = scopes => scopes.includes('trade:prepare') || scopes.includes('trade:submit');
const hash = async value => [...new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(value)))].map(byte => byte.toString(16).padStart(2, '0')).join('');
const challengeHash = async value => btoa(String.fromCharCode(...new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(value))))).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');

export class OAuthError extends Error {
  constructor(status, code, headers = {}) { super(code); this.name = 'OAuthError'; this.status = status; this.code = code; this.headers = headers; }
}
const fail = (status, code, headers) => { throw new OAuthError(status, code, headers); };
const response = (data, status = 200, headers = {}) => Response.json(data, { status, headers: { 'Cache-Control': 'no-store', Pragma: 'no-cache', ...headers } });
const cors = { 'Access-Control-Allow-Origin': '*' };

const SECURITY_EVENTS = Object.freeze({
  issued: ['info', 'grant_issued', 'succeeded', 'owner_consent'],
  denied: ['info', 'grant_denied', 'denied', 'owner_denied'],
  codeReplay: ['warn', 'code_replay', 'detected', 'already_used'],
  refreshReplay: ['warn', 'refresh_replay', 'detected', 'already_used'],
  codeConflict: ['warn', 'code_claim_conflict', 'denied', 'claim_unavailable'],
  refreshConflict: ['warn', 'refresh_claim_conflict', 'denied', 'claim_unavailable'],
  revokedCodeReplay: ['info', 'grant_revoked', 'succeeded', 'code_replay'],
  revokedRefreshReplay: ['info', 'grant_revoked', 'succeeded', 'refresh_replay'],
  revokedCodeConflict: ['info', 'grant_revoked', 'succeeded', 'code_claim_conflict'],
  revokedRefreshConflict: ['info', 'grant_revoked', 'succeeded', 'refresh_claim_conflict'],
  revokedOAuth: ['info', 'grant_revoked', 'succeeded', 'oauth_revocation'],
  revokedOwner: ['info', 'grant_revoked', 'succeeded', 'owner_revocation'],
});
function securityEvent(key) {
  const [level, operation, outcome, reason] = SECURITY_EVENTS[key];
  try { console[level](JSON.stringify({ event: 'oraclebot.agent_security', operation, outcome, reason })); }
  catch { /* An unavailable diagnostic sink must not interrupt authorization or revocation. */ }
}

function audience(request, env) {
  let configured;
  try { configured = new URL(env.APP_ORIGIN || new URL(request.url).origin); } catch { fail(503, 'server_error'); }
  if (configured.pathname !== '/' || configured.search || configured.hash || configured.username || configured.password ||
      !(configured.protocol === 'https:' || (configured.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(configured.hostname)))) fail(503, 'server_error');
  if (new URL(request.url).origin !== configured.origin) fail(403, 'invalid_origin');
  return { origin: configured.origin, resource: `${configured.origin}/mcp` };
}

function parseScope(value = 'status:read') {
  if (typeof value !== 'string' || value.length > 100 || !value.trim()) fail(400, 'invalid_scope');
  const values = value.split(' ');
  if (values.some(scope => !SCOPES.includes(scope)) || new Set(values).size !== values.length) fail(400, 'invalid_scope');
  return SCOPES.filter(scope => values.includes(scope));
}

function boundedText(value, maximum, required = true) {
  if ((!required && value == null) || (!required && value === '')) return null;
  if (typeof value !== 'string' || !value.length || value.length > maximum || /[\u0000-\u001f\u007f]/.test(value)) fail(400, 'invalid_request');
  return value;
}

function exactKeys(body, keys) {
  if (Object.keys(body).some(key => !keys.includes(key))) fail(400, 'invalid_request');
}

async function readBody(request, type) {
  if (request.headers.get('Content-Type')?.split(';', 1)[0].trim().toLowerCase() !== type) fail(415, 'invalid_request');
  const length = request.headers.get('Content-Length');
  if (length && (!/^\d+$/.test(length) || Number(length) > MAX_BODY)) fail(413, 'invalid_request');
  const reader = request.body?.getReader();
  if (!reader) fail(400, 'invalid_request');
  let size = 0; const chunks = [];
  try {
    while (true) {
      const chunk = await reader.read(); if (chunk.done) break;
      size += chunk.value.length;
      if (size > MAX_BODY) { await reader.cancel(); fail(413, 'invalid_request'); }
      chunks.push(chunk.value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  let text;
  try { text = new TextDecoder('utf-8', { fatal: true }).decode(bytes); } catch { fail(400, 'invalid_request'); }
  if (type === 'application/json') {
    let result; try { result = JSON.parse(text); } catch { fail(400, 'invalid_request'); }
    if (!result || Array.isArray(result) || typeof result !== 'object') fail(400, 'invalid_request');
    return result;
  }
  const fields = new URLSearchParams(text);
  for (const key of fields.keys()) if (fields.getAll(key).length !== 1) fail(400, 'invalid_request');
  return Object.fromEntries(fields);
}

async function rateLimit(request, env, purpose, limit, seconds = 3600) {
  const at = now();
  const key = await hash(`${purpose}:${request.headers.get('CF-Connecting-IP') || 'local'}:${Math.floor(at / seconds)}`);
  const row = await query(env, `INSERT INTO agent_rate_limits(key_hash,count,expires_at) VALUES (?,1,?)
    ON CONFLICT(key_hash) DO UPDATE SET count=count+1 WHERE count<? RETURNING count`, key, at + seconds * 2, limit).first();
  if (!row) fail(429, 'rate_limited', { 'Retry-After': String(seconds) });
}

function redirectURI(value) {
  boundedText(value, 2048);
  let url; try { url = new URL(value); } catch { fail(400, 'invalid_redirect_uri'); }
  if (url.username || url.password || url.hash || !(url.protocol === 'https:' ||
    (url.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)))) fail(400, 'invalid_redirect_uri');
  // Preserve the exact supplied URI. Registered redirect matching is byte exact.
  return value;
}

function redirectResult(row, key, value) {
  const result = new URL(row.redirect_uri); result.searchParams.set(key, value);
  if (row.state !== null) result.searchParams.set('state', row.state);
  return { redirectTo: result.href };
}

async function client(env, id) {
  if (!validToken(id)) fail(400, 'invalid_client');
  const row = await query(env, 'SELECT * FROM agent_clients WHERE id=?', id).first();
  if (!row) fail(400, 'invalid_client');
  return row;
}

async function pending(env, id, user) {
  if (!validToken(id)) fail(404, 'authorization_not_found');
  const row = await query(env, `UPDATE agent_authorization_requests SET user_id=? WHERE id=?
    AND (user_id IS NULL OR user_id=?) AND consumed_at IS NULL AND expires_at>? RETURNING *`, user.id, id, user.id, now()).first();
  if (!row) fail(404, 'authorization_not_found');
  return row;
}

export function validateAgentPolicy(value, at = now()) {
  if (!validPolicyScope(value)) fail(400, 'invalid_policy');
  const collection = (items, allowed) => {
    if (!Array.isArray(items) || !items.length || items.length > allowed.length || items.some(item => !allowed.includes(item)) || new Set(items).size !== items.length) fail(400, 'invalid_policy');
    return [...items].sort();
  };
  const money = amount => {
    if (typeof amount !== 'number' || !Number.isFinite(amount) || amount <= 0 || amount > 1000000) fail(400, 'invalid_policy');
    const decimal = /^(\d+)(?:\.(\d{1,2}))?$/.exec(String(amount));
    if (!decimal) fail(400, 'invalid_policy');
    const cents = Number(decimal[1]) * 100 + Number((decimal[2] || '').padEnd(2, '0'));
    if (!Number.isSafeInteger(cents) || cents <= 0) fail(400, 'invalid_policy');
    return cents / 100;
  };
  const policy = { venues: collection(value.venues, ['coinbase', 'jupiter']), assets: collection(value.assets, ['BTC', 'ETH', 'SOL', 'ZEC']), maxTradeUsd: money(value.maxTradeUsd), maxTotalUsd: money(value.maxTotalUsd), expiresAt: value.expiresAt };
  if (policy.maxTradeUsd > policy.maxTotalUsd || !Number.isSafeInteger(policy.expiresAt) || policy.expiresAt <= at + 60 || policy.expiresAt > at + MAX_GRANT_TTL) fail(400, 'invalid_policy');
  if (value.version === 2) return { version: 2, venues: policy.venues, assets: policy.assets,
    products: collection(value.products, ['spot', 'perpetual']), maxLeverage: value.maxLeverage,
    maxTradeUsd: policy.maxTradeUsd, maxTotalUsd: policy.maxTotalUsd, expiresAt: policy.expiresAt };
  return policy;
}

function consentMessage(row, user, registered, policy, policyHash, nonce, issued, expires) {
  if (policy.version === 2) return [
    'Oraclebot agent trading preauthorization',
    'Policy version: 2',
    'Purpose: authorize this agent to trade within the limits below without asking for each trade.',
    'This is a trading authorization, separate from signing in to Oraclebot.',
    `Wallet: ${user.wallet}`, `Agent: ${registered.name}`, `Client ID: ${registered.id}`,
    `Agent redirect origin: ${new URL(row.redirect_uri).origin}`, `Resource: ${row.resource}`, `Scopes: ${row.scope}`,
    `Venues: ${policy.venues.join(', ')}`, `Assets: ${policy.assets.join(', ')}`,
    `Allowed products: ${policy.products.join(', ')}`, `Maximum leverage: ${policy.maxLeverage}x (spot trades remain 1x)`,
    'USD limits are fee-inclusive notional exposure (position notional plus quoted fees), not collateral limits.',
    `Maximum per trade (fee-inclusive notional): USD ${policy.maxTradeUsd.toFixed(2)}`,
    `Maximum total (fee-inclusive notional): USD ${policy.maxTotalUsd.toFixed(2)}`,
    `Trading authorization expires: ${new Date(policy.expiresAt * 1000).toISOString()}`,
    `Policy SHA-256: ${policyHash}`, `Nonce: ${nonce}`,
    `Issued: ${new Date(issued * 1000).toISOString()}`, `Sign before: ${new Date(expires * 1000).toISOString()}`,
    'Revoke this authorization at any time in Oraclebot Settings.',
  ].join('\n');
  return [
    'Oraclebot agent trading preauthorization',
    'Purpose: authorize this agent to trade within the limits below without asking for each trade.',
    'This is a trading authorization, separate from signing in to Oraclebot.',
    `Wallet: ${user.wallet}`, `Agent: ${registered.name}`, `Client ID: ${registered.id}`,
    `Agent redirect origin: ${new URL(row.redirect_uri).origin}`, `Resource: ${row.resource}`, `Scopes: ${row.scope}`,
    `Venues: ${policy.venues.join(', ')}`, `Assets: ${policy.assets.join(', ')}`,
    `Maximum per trade: USD ${policy.maxTradeUsd.toFixed(2)}`, `Maximum total: USD ${policy.maxTotalUsd.toFixed(2)}`,
    `Trading authorization expires: ${new Date(policy.expiresAt * 1000).toISOString()}`,
    `Policy SHA-256: ${policyHash}`, `Nonce: ${nonce}`,
    `Issued: ${new Date(issued * 1000).toISOString()}`, `Sign before: ${new Date(expires * 1000).toISOString()}`,
    'Revoke this authorization at any time in Oraclebot Settings.',
  ].join('\n');
}

async function revokeGrant(env, grantId, event) {
  const row = await query(env, 'UPDATE agent_grants SET revoked_at=COALESCE(revoked_at,?) WHERE id=? RETURNING id', now(), grantId).first();
  if (row) securityEvent(event);
}

async function activeGrant(env, grantId, resource) {
  return query(env, `SELECT g.*,u.wallet FROM agent_grants g JOIN users u ON u.id=g.user_id
    WHERE g.id=? AND g.resource=? AND g.revoked_at IS NULL AND g.expires_at>?`, grantId, resource, now()).first();
}

async function issueTokens(env, grant, scopes) {
  const at = now(); const access = opaque(); const refresh = opaque();
  const expires = Math.min(at + ACCESS_TTL, grant.expires_at); const scope = scopes.join(' ');
  const result = await env.DB.batch([
    query(env, `INSERT INTO agent_access_tokens(token_hash,grant_id,user_id,scope,created_at,expires_at)
      SELECT ?,id,user_id,?,?,? FROM agent_grants WHERE id=? AND revoked_at IS NULL AND expires_at>? RETURNING token_hash`, await hash(access), scope, at, expires, grant.id, at),
    query(env, `INSERT INTO agent_refresh_tokens(token_hash,grant_id,user_id,scope,created_at,expires_at)
      SELECT ?,id,user_id,?,?,expires_at FROM agent_grants WHERE id=? AND revoked_at IS NULL AND expires_at>? RETURNING token_hash`, await hash(refresh), scope, at, grant.id, at),
  ]);
  if (result.some(result => result.results?.length !== 1)) fail(400, 'invalid_grant');
  // Recheck after the atomic batch so a concurrently revoked grant never emits
  // credentials as if its authorization were still active.
  if (!await activeGrant(env, grant.id, grant.resource)) fail(400, 'invalid_grant');
  return response({ access_token: access, token_type: 'Bearer', expires_in: expires - at, refresh_token: refresh, scope }, 200, cors);
}

async function exchangeCode(body, env, resource) {
  exactKeys(body, ['grant_type', 'client_id', 'code', 'redirect_uri', 'code_verifier', 'resource']);
  await client(env, body.client_id);
  if (!validToken(body.code) || typeof body.code_verifier !== 'string' || !/^[A-Za-z0-9._~-]{43,128}$/.test(body.code_verifier)) fail(400, 'invalid_grant');
  const codeHash = await hash(body.code);
  const code = await query(env, 'SELECT * FROM agent_codes WHERE token_hash=?', codeHash).first();
  if (!code || code.client_id !== body.client_id || code.resource !== resource || body.resource !== resource || code.redirect_uri !== body.redirect_uri || code.code_challenge !== await challengeHash(body.code_verifier)) fail(400, 'invalid_grant');
  if (code.used_at !== null) { securityEvent('codeReplay'); await revokeGrant(env, code.grant_id, 'revokedCodeReplay'); fail(400, 'invalid_grant'); }
  if (code.expires_at <= now()) fail(400, 'invalid_grant');
  const grant = await activeGrant(env, code.grant_id, resource);
  if (!grant || grant.user_id !== code.user_id) fail(400, 'invalid_grant');
  const claimed = await query(env, 'UPDATE agent_codes SET used_at=? WHERE token_hash=? AND used_at IS NULL AND expires_at>? RETURNING grant_id', now(), codeHash, now()).first();
  if (!claimed) { securityEvent('codeConflict'); await revokeGrant(env, code.grant_id, 'revokedCodeConflict'); fail(400, 'invalid_grant'); }
  return issueTokens(env, grant, parseScope(grant.scope));
}

async function refreshTokens(body, env, resource) {
  exactKeys(body, ['grant_type', 'client_id', 'refresh_token', 'resource', 'scope']);
  await client(env, body.client_id);
  if (!validToken(body.refresh_token) || body.resource !== resource) fail(400, 'invalid_grant');
  const tokenHash = await hash(body.refresh_token);
  const token = await query(env, `SELECT t.*,g.client_id,g.resource FROM agent_refresh_tokens t
    JOIN agent_grants g ON g.id=t.grant_id WHERE t.token_hash=?`, tokenHash).first();
  if (!token || token.client_id !== body.client_id || token.resource !== resource) fail(400, 'invalid_grant');
  if (token.used_at !== null) { securityEvent('refreshReplay'); await revokeGrant(env, token.grant_id, 'revokedRefreshReplay'); fail(400, 'invalid_grant'); }
  if (token.expires_at <= now()) fail(400, 'invalid_grant');
  const grant = await activeGrant(env, token.grant_id, resource);
  if (!grant || grant.user_id !== token.user_id) fail(400, 'invalid_grant');
  const scopes = body.scope === undefined ? parseScope(token.scope) : parseScope(body.scope);
  if (scopes.some(scope => !parseScope(token.scope).includes(scope))) fail(400, 'invalid_scope');
  const claimed = await query(env, 'UPDATE agent_refresh_tokens SET used_at=? WHERE token_hash=? AND used_at IS NULL AND expires_at>? RETURNING grant_id', now(), tokenHash, now()).first();
  if (!claimed) { securityEvent('refreshConflict'); await revokeGrant(env, token.grant_id, 'revokedRefreshConflict'); fail(400, 'invalid_grant'); }
  return issueTokens(env, grant, scopes);
}

/** Bearer tokens bind the current database user, grant, client, and audience.
 * Browser cookies and caller-supplied wallet/user fields never identify an agent. */
export async function authenticateAgent(request, env) {
  const { origin, resource } = audience(request, env);
  const headers = { 'WWW-Authenticate': `Bearer resource_metadata="${origin}/.well-known/oauth-protected-resource/mcp"` };
  const authorization = request.headers.get('Authorization');
  if (!authorization || !/^Bearer [A-Za-z0-9_-]{43}$/i.test(authorization)) fail(401, 'invalid_token', headers);
  const row = await query(env, `SELECT t.scope AS token_scope,t.expires_at AS token_expiry,
    g.*,u.wallet,c.name AS client_name,c.redirect_uris FROM agent_access_tokens t
    JOIN agent_grants g ON g.id=t.grant_id JOIN users u ON u.id=g.user_id
    JOIN agent_clients c ON c.id=g.client_id WHERE t.token_hash=? AND t.user_id=g.user_id`, await hash(authorization.slice(7))).first();
  if (!row || row.resource !== resource || row.revoked_at !== null || row.expires_at <= now() || row.token_expiry <= now()) fail(401, 'invalid_token', headers);
  const granted = parseScope(row.scope); const scopes = new Set(parseScope(row.token_scope));
  if ([...scopes].some(scope => !granted.includes(scope))) fail(401, 'invalid_token', headers);
  if (trading([...scopes])) {
    try {
      if (!row.policy_json || await hash(row.policy_json) !== row.policy_hash) fail(401, 'invalid_token', headers);
      const policy = JSON.parse(row.policy_json);
      if (!validPolicyScope(policy) || !Number.isSafeInteger(policy.expiresAt) || policy.expiresAt !== row.expires_at || policy.expiresAt <= now()) fail(401, 'invalid_token', headers);
    } catch { fail(401, 'invalid_token', headers); }
  }
  const { id, user_id, client_id, scope, policy_json, policy_hash, created_at, expires_at, revoked_at } = row;
  return {
    user: { id: user_id, wallet: row.wallet },
    grant: { id, user_id, client_id, resource, scope, policy_json, policy_hash, created_at, expires_at, revoked_at },
    scopes,
    client: { id: client_id, name: row.client_name, redirect_uris: JSON.parse(row.redirect_uris) },
  };
}

async function routeOAuth(request, env, helpers) {
  const url = new URL(request.url); const path = url.pathname;
  const protocol = path.startsWith('/oauth/');
  const metadata = ['/.well-known/oauth-protected-resource', '/.well-known/oauth-protected-resource/mcp', '/.well-known/oauth-authorization-server'].includes(path);
  const cookieAPI = path === '/api/agent/authorization' || path === '/api/agent/authorization/challenge' || path === '/api/agent/grants' || /^\/api\/agent\/grants\/[^/]+\/revoke$/.test(path);
  if (!metadata && !protocol && !cookieAPI) return null;
  const { origin, resource } = audience(request, env);
  if (request.method === 'OPTIONS' && (metadata || protocol)) return new Response(null, { status: 204, headers: { ...cors, 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Max-Age': '600', 'Cache-Control': 'no-store' } });
  if (metadata) {
    if (request.method !== 'GET') fail(405, 'method_not_allowed', { Allow: 'GET, OPTIONS' });
    if (path !== '/.well-known/oauth-authorization-server') return response({ resource, resource_name: 'Oraclebot', authorization_servers: [origin], scopes_supported: SCOPES, bearer_methods_supported: ['header'] }, 200, cors);
    return response({ issuer: origin, authorization_endpoint: `${origin}/oauth/authorize`, token_endpoint: `${origin}/oauth/token`, registration_endpoint: `${origin}/oauth/register`, revocation_endpoint: `${origin}/oauth/revoke`, response_types_supported: ['code'], grant_types_supported: ['authorization_code', 'refresh_token'], token_endpoint_auth_methods_supported: ['none'], code_challenge_methods_supported: ['S256'], scopes_supported: SCOPES }, 200, cors);
  }
  if (!env.DB) fail(503, 'storage_unavailable');

  if (path === '/oauth/register') {
    if (request.method !== 'POST') fail(405, 'method_not_allowed', { Allow: 'POST, OPTIONS' });
    await rateLimit(request, env, 'register', 10);
    const body = await readBody(request, 'application/json');
    if (body.token_endpoint_auth_method !== undefined && body.token_endpoint_auth_method !== 'none') fail(400, 'invalid_client_metadata');
    if (body.grant_types !== undefined && (!Array.isArray(body.grant_types) || body.grant_types.some(type => !['authorization_code', 'refresh_token'].includes(type)))) fail(400, 'invalid_client_metadata');
    if (body.response_types !== undefined && (!Array.isArray(body.response_types) || body.response_types.some(type => type !== 'code'))) fail(400, 'invalid_client_metadata');
    if (!Array.isArray(body.redirect_uris) || body.redirect_uris.length < 1 || body.redirect_uris.length > 10 || new Set(body.redirect_uris).size !== body.redirect_uris.length) fail(400, 'invalid_redirect_uri');
    const redirects = body.redirect_uris.map(redirectURI); const name = boundedText(body.client_name || 'Unnamed agent', 80);
    const id = opaque();
    const registered = await query(env, `INSERT INTO agent_clients(id,name,redirect_uris,created_at)
      SELECT ?,?,?,? WHERE (SELECT COUNT(*) FROM agent_clients)<10000 RETURNING id`, id, name, JSON.stringify(redirects), now()).first();
    if (!registered) fail(503, 'registration_unavailable');
    return response({ client_id: id, client_name: name, redirect_uris: redirects, token_endpoint_auth_method: 'none', grant_types: ['authorization_code', 'refresh_token'], response_types: ['code'] }, 201, cors);
  }

  if (path === '/oauth/authorize') {
    if (request.method !== 'GET') fail(405, 'method_not_allowed', { Allow: 'GET' });
    if (url.search.length > 8192) fail(414, 'invalid_request');
    const params = url.searchParams;
    for (const key of params.keys()) if (params.getAll(key).length !== 1) fail(400, 'invalid_request');
    const body = Object.fromEntries(params);
    exactKeys(body, ['client_id', 'redirect_uri', 'response_type', 'resource', 'scope', 'state', 'code_challenge', 'code_challenge_method']);
    const registered = await client(env, body.client_id);
    if (!JSON.parse(registered.redirect_uris).includes(body.redirect_uri)) fail(400, 'invalid_redirect_uri');
    if (body.response_type !== 'code') fail(400, 'unsupported_response_type');
    if (body.resource !== resource) fail(400, 'invalid_target');
    if (body.code_challenge_method !== 'S256' || !validToken(body.code_challenge)) fail(400, 'invalid_request');
    const scopes = parseScope(body.scope); const state = body.state === '' ? '' : boundedText(body.state, 512, false);
    await rateLimit(request, env, 'authorize', 60, 300);
    const id = opaque(); const at = now();
    await query(env, `INSERT INTO agent_authorization_requests(id,client_id,redirect_uri,resource,scope,state,code_challenge,created_at,expires_at)
      VALUES (?,?,?,?,?,?,?,?,?)`, id, registered.id, body.redirect_uri, resource, scopes.join(' '), state, body.code_challenge, at, at + 600).run();
    return new Response(null, { status: 302, headers: { Location: `${origin}/?agent_request=${id}#settings`, 'Cache-Control': 'no-store' } });
  }

  if (path === '/oauth/token') {
    if (request.method !== 'POST') fail(405, 'method_not_allowed', { Allow: 'POST, OPTIONS' });
    await rateLimit(request, env, 'token', 120, 300);
    const body = await readBody(request, 'application/x-www-form-urlencoded');
    if (body.resource !== resource) fail(400, 'invalid_target');
    if (body.grant_type === 'authorization_code') return exchangeCode(body, env, resource);
    if (body.grant_type === 'refresh_token') return refreshTokens(body, env, resource);
    fail(400, 'unsupported_grant_type');
  }

  if (path === '/oauth/revoke') {
    if (request.method !== 'POST') fail(405, 'method_not_allowed', { Allow: 'POST, OPTIONS' });
    await rateLimit(request, env, 'revoke', 120, 300);
    const body = await readBody(request, 'application/x-www-form-urlencoded');
    exactKeys(body, ['client_id', 'token', 'token_type_hint']);
    if (validToken(body.token) && validToken(body.client_id)) {
      const tokenHash = await hash(body.token);
      const row = await query(env, `SELECT g.id FROM agent_grants g WHERE g.client_id=? AND g.id IN (
        SELECT grant_id FROM agent_access_tokens WHERE token_hash=? UNION SELECT grant_id FROM agent_refresh_tokens WHERE token_hash=?)`, body.client_id, tokenHash, tokenHash).first();
      if (row) await revokeGrant(env, row.id, 'revokedOAuth');
    }
    return response({}, 200, cors);
  }

  if (!cookieAPI) fail(404, 'not_found');
  const user = await helpers.account(request, env);
  if (!user?.id || !user?.wallet) fail(401, 'authentication_required');
  if (request.method !== 'GET') helpers.sameOrigin(request, env);

  if (path === '/api/agent/authorization' && request.method === 'GET') {
    const row = await pending(env, url.searchParams.get('request_id'), user);
    const registered = await client(env, row.client_id);
    return response({ requestId: row.id, client: { id: registered.id, name: registered.name, redirectOrigin: new URL(row.redirect_uri).origin, redirectUri: row.redirect_uri }, wallet: user.wallet, scopes: parseScope(row.scope), resource: row.resource, expiresAt: row.expires_at, requiresPolicyProof: trading(parseScope(row.scope)) });
  }

  if (path === '/api/agent/authorization/challenge' && request.method === 'POST') {
    await rateLimit(request, env, `consent:${user.id}`, 30, 300);
    const body = await readBody(request, 'application/json'); exactKeys(body, ['requestId', 'policy']);
    const row = await pending(env, body.requestId, user);
    if (!trading(parseScope(row.scope))) fail(400, 'policy_not_required');
    const policy = validateAgentPolicy(body.policy); const policyJSON = JSON.stringify(policy); const policyHash = await hash(policyJSON);
    const registered = await client(env, row.client_id); const id = crypto.randomUUID(); const at = now(); const expires = Math.min(at + 180, row.expires_at);
    const message = consentMessage(row, user, registered, policy, policyHash, id, at, expires);
    await query(env, `INSERT INTO agent_consent_challenges(id,request_id,user_id,wallet,policy_json,policy_hash,message,created_at,expires_at)
      VALUES (?,?,?,?,?,?,?,?,?)`, id, row.id, user.id, user.wallet, policyJSON, policyHash, message, at, expires).run();
    return response({ challengeId: id, message, expiresAt: expires, policy });
  }

  if (path === '/api/agent/authorization' && request.method === 'POST') {
    const body = await readBody(request, 'application/json'); exactKeys(body, ['requestId', 'approve', 'challengeId', 'signature']);
    if (typeof body.approve !== 'boolean') fail(400, 'invalid_request');
    const row = await pending(env, body.requestId, user); const scopes = parseScope(row.scope);
    if (!body.approve) {
      const denied = await query(env, 'UPDATE agent_authorization_requests SET consumed_at=? WHERE id=? AND user_id=? AND consumed_at IS NULL AND expires_at>? RETURNING id', now(), row.id, user.id, now()).first();
      if (!denied) fail(409, 'authorization_consumed');
      securityEvent('denied');
      return response(redirectResult(row, 'error', 'access_denied'));
    }
    let policyJSON = null; let policyHash = null; let grantExpiry = now() + 7 * 86400;
    if (trading(scopes)) {
      if (!validId(body.challengeId) || typeof body.signature !== 'string' || !/^[A-Za-z0-9+/]{86}==$/.test(body.signature)) fail(400, 'wallet_authorization_required');
      const proof = await query(env, `UPDATE agent_consent_challenges SET used_at=? WHERE id=? AND request_id=? AND user_id=?
        AND wallet=? AND used_at IS NULL AND expires_at>? RETURNING *`, now(), body.challengeId, row.id, user.id, user.wallet, now()).first();
      if (!proof) fail(400, 'wallet_authorization_required');
      let verified = false;
      try {
        const bytes = Uint8Array.from(atob(body.signature), character => character.charCodeAt(0));
        const publicKey = await crypto.subtle.importKey('raw', base58Decode(user.wallet), { name: 'Ed25519' }, false, ['verify']);
        verified = bytes.length === 64 && await crypto.subtle.verify('Ed25519', publicKey, bytes, encoder.encode(proof.message));
      } catch { /* Invalid public key or signature is an authorization failure. */ }
      if (!verified || await hash(proof.policy_json) !== proof.policy_hash) fail(400, 'invalid_wallet_authorization');
      const policy = validateAgentPolicy(JSON.parse(proof.policy_json));
      // Reconstruct the signed message from immutable request and policy fields.
      // A stored-field change cannot turn an earlier signature into new consent.
      const registered = await client(env, row.client_id);
      if (JSON.stringify(policy) !== proof.policy_json || consentMessage(row, user, registered, policy, proof.policy_hash, proof.id, proof.created_at, proof.expires_at) !== proof.message) fail(400, 'invalid_wallet_authorization');
      policyJSON = proof.policy_json; policyHash = proof.policy_hash; grantExpiry = policy.expiresAt;
    } else if (body.challengeId !== undefined || body.signature !== undefined) fail(400, 'invalid_request');
    const consumed = await query(env, `UPDATE agent_authorization_requests SET consumed_at=? WHERE id=? AND user_id=?
      AND consumed_at IS NULL AND expires_at>? RETURNING id`, now(), row.id, user.id, now()).first();
    if (!consumed) fail(409, 'authorization_consumed');
    const id = crypto.randomUUID(); const code = opaque(); const at = now();
    const issued = await env.DB.batch([
      query(env, `INSERT INTO agent_grants(id,user_id,client_id,resource,scope,policy_json,policy_hash,created_at,expires_at)
        SELECT ?,?,?,?,?,?,?,?,? WHERE (SELECT COUNT(*) FROM agent_grants WHERE user_id=? AND revoked_at IS NULL AND expires_at>?)<50 RETURNING id`, id, user.id, row.client_id, row.resource, row.scope, policyJSON, policyHash, at, grantExpiry, user.id, at),
      query(env, `INSERT INTO agent_codes(token_hash,grant_id,user_id,client_id,resource,redirect_uri,code_challenge,created_at,expires_at)
        SELECT ?,id,user_id,client_id,resource,?,?,?,? FROM agent_grants WHERE id=? RETURNING grant_id`, await hash(code), row.redirect_uri, row.code_challenge, at, Math.min(at + 120, grantExpiry), id),
    ]);
    if (issued.some(result => result.results?.length !== 1)) fail(429, 'grant_limit_reached');
    securityEvent('issued');
    return response(redirectResult(row, 'code', code));
  }

  if (path === '/api/agent/grants' && request.method === 'GET') {
    const rows = await query(env, `SELECT g.*,c.name AS client_name FROM agent_grants g JOIN agent_clients c ON c.id=g.client_id
      WHERE g.user_id=? ORDER BY CASE WHEN g.revoked_at IS NULL AND g.expires_at>? THEN 0 ELSE 1 END,g.created_at DESC,g.id LIMIT 100`, user.id, now()).all();
    return response({ grants: rows.results.map(row => ({ id: row.id, clientId: row.client_id, clientName: row.client_name, scopes: parseScope(row.scope), policy: row.policy_json ? JSON.parse(row.policy_json) : null, createdAt: row.created_at, expiresAt: row.expires_at, revokedAt: row.revoked_at })) });
  }
  if (/^\/api\/agent\/grants\/[^/]+\/revoke$/.test(path) && request.method === 'POST') {
    const id = path.split('/')[4]; if (!validId(id)) fail(404, 'grant_not_found');
    const row = await query(env, 'UPDATE agent_grants SET revoked_at=COALESCE(revoked_at,?) WHERE id=? AND user_id=? RETURNING id', now(), id, user.id).first();
    if (!row) fail(404, 'grant_not_found');
    securityEvent('revokedOwner');
    return response({ revoked: true });
  }
  fail(405, 'method_not_allowed', { Allow: path === '/api/agent/grants' ? 'GET' : path === '/api/agent/authorization' ? 'GET, POST' : 'POST' });
}

export async function handleOAuth(request, env, helpers) {
  try { return await routeOAuth(request, env, helpers); }
  catch (error) {
    const path = new URL(request.url).pathname;
    if (error instanceof OAuthError && (path.startsWith('/oauth/') || path.startsWith('/.well-known/oauth-'))) error.headers = { ...cors, ...error.headers };
    throw error;
  }
}

/** Retain consumed refresh hashes until their grant expires so replay detection
 * survives token rotation. Keep grant metadata for ninety days for user history. */
export async function cleanupAgentAccess(env) {
  const at = now();
  return env.DB.batch([
    query(env, 'DELETE FROM agent_authorization_requests WHERE expires_at<=?', at),
    query(env, 'DELETE FROM agent_codes WHERE expires_at<=? AND grant_id IN (SELECT id FROM agent_grants WHERE expires_at<=?)', at, at),
    query(env, 'DELETE FROM agent_access_tokens WHERE expires_at<=?', at),
    query(env, 'DELETE FROM agent_refresh_tokens WHERE expires_at<=?', at),
    query(env, 'DELETE FROM agent_grants WHERE expires_at<?', at - 90 * 86400),
    query(env, 'DELETE FROM agent_rate_limits WHERE expires_at<=?', at),
    query(env, `DELETE FROM agent_clients WHERE created_at<? AND id NOT IN (SELECT client_id FROM agent_grants)
      AND id NOT IN (SELECT client_id FROM agent_authorization_requests)`, at - 30 * 86400),
  ]);
}
