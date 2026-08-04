/**
 * Price lookup.
 *
 * Two shapes have shipped across Price API versions (`{ <mint>: {...} }` in v3,
 * `{ data: { <mint>: {...} } }` in v2). The parser accepts either and throws a
 * named error on anything else, so a version bump surfaces as one clear failure
 * instead of `undefined` propagating into order sizing.
 */

import { request, headers } from './http.js';

export const PRICE_HOSTS = {
  // Keyed tier.
  keyed: 'https://api.jup.ag/price/v3',
  // Keyless tier, for dry-run and local verification.
  lite: 'https://lite-api.jup.ag/price/v3',
};

export class PriceShapeError extends Error {
  constructor(body) {
    super('unrecognised price response shape');
    this.name = 'PriceShapeError';
    this.sample = JSON.stringify(body)?.slice(0, 300);
  }
}

/** Pull a USD price out of either response shape. */
export function parsePrices(body, mints) {
  const table = body?.data && typeof body.data === 'object' ? body.data : body;
  if (!table || typeof table !== 'object') throw new PriceShapeError(body);

  const out = {};
  for (const mint of mints) {
    const entry = table[mint];
    if (!entry) continue;
    const raw = entry.usdPrice ?? entry.price ?? entry.usd_price;
    const price = typeof raw === 'string' ? Number(raw) : raw;
    if (Number.isFinite(price) && price > 0) out[mint] = price;
  }

  if (Object.keys(out).length === 0) throw new PriceShapeError(body);
  return out;
}

/**
 * Raw per-mint table from the price endpoint.
 *
 * Shared by price and decimals lookups so both go through the retry, timeout
 * and budget layer in http.js — a direct fetch here would bypass all three.
 */
export async function getPriceTable({ mints, apiKey, budget, fetchImpl, host }) {
  const base = host ?? (apiKey ? PRICE_HOSTS.keyed : PRICE_HOSTS.lite);
  const url = `${base}?ids=${mints.join(',')}`;
  const body = await request({
    url,
    init: { method: 'GET', headers: headers({ apiKey }) },
    budget,
    fetchImpl,
  });
  return body?.data && typeof body.data === 'object' ? body.data : body;
}

/**
 * @returns {Promise<Record<string, number>>} mint -> USD price
 */
export async function getPrices({ mints, apiKey, budget, fetchImpl, host }) {
  const table = await getPriceTable({ mints, apiKey, budget, fetchImpl, host });
  return parsePrices(table, mints);
}

/**
 * Token decimals as reported by the price endpoint.
 *
 * Read rather than hardcoded: order sizing multiplies by 10**decimals, so a
 * wrong constant is a wrong order size by orders of magnitude.
 */
export async function getDecimals({ mints, apiKey, budget, fetchImpl, host }) {
  const table = await getPriceTable({ mints, apiKey, budget, fetchImpl, host });
  const out = {};
  for (const mint of mints) {
    const d = table?.[mint]?.decimals;
    if (Number.isInteger(d) && d >= 0 && d <= 18) out[mint] = d;
  }
  return out;
}
