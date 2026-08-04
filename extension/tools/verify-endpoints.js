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

const MINTS = [DEFAULT_CONFIG.baseMint, DEFAULT_CONFIG.quoteMint];
const apiKey = process.env.JUPITER_API_KEY;
let failures = 0;

function report(name, ok, detail) {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`);
  if (!ok) failures++;
}

async function checkPrice(host, label, key) {
  const url = `${host}?ids=${MINTS.join(',')}`;
  try {
    const res = await fetch(url, { headers: key ? { 'x-api-key': key } : {} });
    if (!res.ok) return report(label, false, `HTTP ${res.status}`);
    const body = await res.json();
    const prices = parsePrices(body, MINTS);
    const base = prices[DEFAULT_CONFIG.baseMint];
    const decimals = body?.[DEFAULT_CONFIG.baseMint]?.decimals;
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
    const res = await fetch(`${TRIGGER_BASE}/auth/challenge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(apiKey ? { 'x-api-key': apiKey } : {}) },
      body: JSON.stringify({ walletPubkey: DEFAULT_CONFIG.baseMint, type: 'message' }),
    });
    const routeExists = res.status !== 404;
    report(
      'trigger v2 auth/challenge route exists',
      routeExists,
      `HTTP ${res.status}${apiKey ? '' : ' (no API key: 401/403 expected)'}`,
    );
    if (apiKey && res.ok) {
      const body = await res.json();
      report('trigger v2 returns a challenge with a key', typeof body?.challenge === 'string');
    }
  } catch (err) {
    report('trigger v2 reachable', false, err.message);
  }
}

console.log(`checking Jupiter endpoints (${new Date().toISOString()})\n`);
await checkPrice(PRICE_HOSTS.lite, 'price v3 (keyless)', null);
if (apiKey) await checkPrice(PRICE_HOSTS.keyed, 'price v3 (keyed)', apiKey);
else console.log('SKIP  price v3 (keyed) — set JUPITER_API_KEY to check');
await checkTriggerReachable();

console.log(`\nvenue minimum order: $${TRIGGER_LIMITS.minOrderUsd}`);
console.log(failures === 0 ? '\nall checks passed' : `\n${failures} check(s) failed`);
process.exitCode = failures === 0 ? 0 : 1;
