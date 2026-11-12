/**
 * Read-only network access for the market modules (holdings, pools, quotes).
 *
 * Everything here goes through `request` in src/jupiter/http.js, so the
 * timeout, retry and JSON handling are the same ones the trading path uses.
 * The fetch implementation comes from `deps.fetch`: the service worker, the
 * CLI and the HTTP API inject the platform fetch, and tests inject a stub. A
 * surface without one gets a clean refusal instead of a silent global.
 *
 * Nothing in src/market signs, sends a transaction or calls a state-changing
 * method. JSON-RPC requests are POSTs, but only `eth_*` reads and Solana
 * `get*` reads are built here, and `assertReadMethod` refuses anything else.
 */

import { request } from '../jupiter/http.js';

export class MarketError extends Error {
  constructor(source, message) {
    super(`${source}: ${message}`);
    this.name = 'MarketError';
    this.source = source;
  }
}

/** The platform fetch from deps, or a named refusal. */
export function fetchOf(deps) {
  if (typeof deps?.fetch !== 'function') {
    throw new MarketError('network', 'this surface has no fetch configured for market reads');
  }
  return deps.fetch;
}

const READ_METHOD = /^(eth_(call|chainId|getBalance|blockNumber)|get[A-Z][A-Za-z]*)$/;

/** Market modules may only ever read. */
export function assertReadMethod(method) {
  if (!READ_METHOD.test(method)) throw new MarketError('rpc', `refusing non-read method ${method}`);
  return method;
}

export async function getJson(deps, url, { source, timeoutMs = 15_000, maxAttempts = 3, maxResponseBytes } = {}) {
  try {
    return await request({ url, init: { method: 'GET' }, fetchImpl: fetchOf(deps), timeoutMs, maxAttempts, maxResponseBytes, log: () => {} });
  } catch (err) {
    if (err instanceof MarketError) throw err;
    throw new MarketError(source ?? new URL(url).host, err?.message ?? 'request failed');
  }
}

async function postJson(deps, url, body, { timeoutMs = 15_000 } = {}) {
  return request({
    url,
    init: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) },
    fetchImpl: fetchOf(deps),
    timeoutMs,
    // request() replays only GETs; a JSON-RPC read is safe to repeat, so the
    // retry here is "try the next endpoint" in rpcBatch rather than a replay.
    maxAttempts: 1,
    log: () => {},
  });
}

/**
 * One JSON-RPC batch against the first endpoint that answers.
 *
 * Public Base and Solana endpoints are rate limited (docs.base.org: "Public
 * endpoints are rate-limited and are not suitable for production traffic"), so
 * a second endpoint is the difference between a slow read and no read. A
 * per-call error comes back as `null` in its slot: one bad token contract must
 * not sink the rest of the batch.
 *
 * @returns {Promise<Array<any|null>>} results in call order
 */
export async function rpcBatch(deps, endpoints, calls, { source = 'rpc' } = {}) {
  if (!calls.length) return [];
  for (const [method] of calls) assertReadMethod(method);
  const body = calls.map(([method, params], id) => ({ jsonrpc: '2.0', id, method, params }));
  let last = 'no endpoint configured';
  for (const url of endpoints) {
    try {
      const reply = await postJson(deps, url, body);
      if (!Array.isArray(reply)) { last = `${new URL(url).host} answered a batch with a non-list`; continue; }
      const byId = new Map(reply.filter((r) => r && typeof r === 'object').map((r) => [r.id, r]));
      return calls.map((_, i) => {
        const r = byId.get(i);
        return r && !r.error && 'result' in r ? r.result : null;
      });
    } catch (err) {
      last = `${safeHost(url)}: ${err?.message ?? 'request failed'}`;
    }
  }
  throw new MarketError(source, last);
}

/** A single JSON-RPC read; an RPC-level error is an exception, not a null. */
export async function rpcCall(deps, endpoints, method, params, { source = 'rpc' } = {}) {
  assertReadMethod(method);
  let last = 'no endpoint configured';
  for (const url of endpoints) {
    try {
      const reply = await postJson(deps, url, { jsonrpc: '2.0', id: 1, method, params });
      if (reply?.error) { last = `${safeHost(url)}: ${reply.error.message ?? 'rpc error'}`; continue; }
      if (!reply || !('result' in reply)) { last = `${safeHost(url)}: no result`; continue; }
      return reply.result;
    } catch (err) {
      last = `${safeHost(url)}: ${err?.message ?? 'request failed'}`;
    }
  }
  throw new MarketError(source, last);
}

function safeHost(url) {
  try { return new URL(url).host; } catch { return 'invalid endpoint'; }
}
