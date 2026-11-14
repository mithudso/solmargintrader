#!/usr/bin/env node
/**
 * Live endpoint check.
 *
 * Confirms the read-side assumptions this extension hardcodes still hold, so a
 * Jupiter API change surfaces here rather than mid-tick. Read-only: nothing is
 * signed, deposited, or ordered.
 *
 *   node tools/verify-endpoints.js
 *   JUPITER_API_KEY=... node tools/verify-endpoints.js   # also checks the keyed tier
 */

import { parsePrices, PRICE_HOSTS } from '../src/jupiter/price.js';
import { TRIGGER_BASE, TRIGGER_LIMITS } from '../src/jupiter/trigger.js';
import { DEFAULT_CONFIG } from '../src/storage/store.js';
import { toolArgs, toolFailure } from './args.js';
import { request } from '../src/jupiter/http.js';

const USAGE = 'Usage: node tools/verify-endpoints.js\nRead-only live endpoint checks; JUPITER_API_KEY optionally enables keyed checks.\nExample: node tools/verify-endpoints.js';

const MINTS = [DEFAULT_CONFIG.baseMint, DEFAULT_CONFIG.quoteMint];
const apiKey = process.env.JUPITER_API_KEY;
let failures = 0;

function report(name, ok, detail) {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`);
  if (!ok) failures++;
}

async function endpointRead(url, init = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  let timer;
  try {
    return await Promise.race([
      (async () => {
        const res = await fetch(url, { ...init, signal: controller.signal });
        return { ok: res.ok, status: res.status, body: res.ok ? await res.json() : null };
      })(),
      new Promise((_, reject) => { timer = setTimeout(() => { controller.abort(); reject(new Error('endpoint deadline exceeded')); }, timeoutMs); }),
    ]);
  } finally { clearTimeout(timer); }
}

async function checkPrice(host, label, key) {
  const url = `${host}?ids=${MINTS.join(',')}`;
  try {
    const res = await endpointRead(url, { headers: key ? { 'x-api-key': key } : {} });
    if (!res.ok) return report(label, false, `HTTP ${res.status}`);
    const body = res.body;
    const prices = parsePrices(body, MINTS);
    const base = prices[DEFAULT_CONFIG.baseMint];
    const table = body?.data ?? body;
    const decimals = table?.[DEFAULT_CONFIG.baseMint]?.decimals;
    for (const mint of MINTS) report(`${label}: requested price`, Number.isFinite(prices[mint]) && prices[mint] > 0);
    report(label, base > 0, `${DEFAULT_CONFIG.baseSymbol} $${base?.toFixed(4)}, decimals ${decimals}`);
    if (decimals !== 9) {
      report(`${label}: SOL decimals are 9`, false, `got ${decimals} — order sizing depends on this`);
    }
  } catch (err) {
    report(label, false, err.message);
  }
}

/**
 * The auth challenge endpoint is the cheapest proof that Trigger V2 is reachable
 * and that our route prefix is right. Without a key it should answer 401/403 —
 * which still tells us the route exists. A 404 means the path moved.
 */
async function checkTriggerReachable() {
  try {
    const res = await endpointRead(`${TRIGGER_BASE}/auth/challenge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(apiKey ? { 'x-api-key': apiKey } : {}) },
      body: JSON.stringify({ walletPubkey: DEFAULT_CONFIG.baseMint, type: 'message' }),
    });
    const routeExists = apiKey ? res.ok : [401, 403].includes(res.status);
    report(
      'trigger v2 auth/challenge route exists',
      routeExists,
      `HTTP ${res.status}${apiKey ? '' : ' (no API key: 401/403 expected)'}`,
    );
    if (apiKey && res.ok) {
      const body = res.body;
      report('trigger v2 returns a challenge with a key', typeof body?.challenge === 'string' && body.challenge.length > 0);
    }
  } catch (err) {
    if (!apiKey && [401, 403].includes(err.status)) {
      report('trigger v2 auth/challenge route exists', true, `HTTP ${err.status} (no API key)`);
      return;
    }
    report('trigger v2 reachable', false, err.message);
  }
}

async function main() {
const args = toolArgs(process.argv.slice(2), {}, { usage: USAGE });
if (args.help) { console.log(USAGE); return; }
console.log(`checking Jupiter endpoints (${new Date().toISOString()})\n`);
await checkPrice(PRICE_HOSTS.lite, 'price v3 (keyless)', null);
if (apiKey) await checkPrice(PRICE_HOSTS.keyed, 'price v3 (keyed)', apiKey);
else console.log('SKIP  price v3 (keyed) — set JUPITER_API_KEY to check');
await checkTriggerReachable();

console.log(`\nvenue minimum order: $${TRIGGER_LIMITS.minOrderUsd}`);
console.log(failures === 0 ? '\nall checks passed' : `\n${failures} check(s) failed`);
process.exitCode = failures === 0 ? 0 : 1;
}
await main().catch(toolFailure);
