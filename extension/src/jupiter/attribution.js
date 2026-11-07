/**
 * Licence-required attribution, in one place.
 *
 * The Jupiter SDK & API License Agreement (read 2026-08-04) imposes two display
 * obligations that are easy for a private tool to miss, because nobody else sees
 * the UI:
 *
 *   §8.4  the product "shall prominently display to end users ... 'Powered by
 *         Jupiter'".
 *   §2.3  the product must "correctly and accurately display prominently /
 *         label / name / characterise the specific API used, which must be made
 *         visible to end users". Presenting output as merely "Jupiter" is called
 *         out there as misleading, and carries an indemnity.
 *
 * §2.3 is written around the two swap APIs — "Jupiter Ultra" and "Metis". Since
 * the 0.3.0 redesign the extension calls both, narrowly, and the label says
 * exactly how: the Metis Swap API for swap QUOTES (the owner signs the swap on
 * jup.ag; this extension builds no swap transaction), and the Ultra API's
 * holdings endpoint to read the wallet's token balances. Trigger V2 still places
 * the grid's orders and Price v3 still supplies marks. Naming a surface for
 * more than it does, or omitting one, is the mischaracterisation §2.3 forbids.
 *
 * Not legal advice. `SURFACES` is checked against the real base URLs by
 * `test/attribution.test.js`, so adding an API without updating the label fails
 * the build — the same anti-drift shape used for strategy cards.
 */

import { TRIGGER_BASE } from './trigger.js';
import { PRICE_HOSTS } from './price.js';
import { JUPITER_MARKET_BASES } from '../market/tokens.js';

/** The exact string §8.4 requires. Do not paraphrase it. */
export const POWERED_BY = 'Powered by Jupiter';

/**
 * Every Jupiter API this extension actually calls, with the base each one uses.
 * The `base` values are imported rather than retyped so they cannot drift.
 */
export const SURFACES = Object.freeze([
  Object.freeze({ name: 'Trigger V2', purpose: 'orders', bases: Object.freeze([TRIGGER_BASE]) }),
  Object.freeze({
    name: 'Price v3',
    purpose: 'marks',
    // Both, because which one is used depends on whether an API key is set.
    bases: Object.freeze([PRICE_HOSTS.keyed, PRICE_HOSTS.lite]),
  }),
  Object.freeze({
    name: 'Metis Swap API',
    purpose: 'swap quotes only; the swap is signed on jup.ag',
    bases: Object.freeze([JUPITER_MARKET_BASES.metis]),
  }),
  Object.freeze({
    name: 'Ultra API',
    purpose: 'Solana wallet holdings, read only',
    bases: Object.freeze([JUPITER_MARKET_BASES.ultraHoldings]),
  }),
]);

/** The swap API whose quotes are shown. It routes nothing from here: §2.3 is about naming it accurately. */
export const ROUTING_API = 'Metis';
export const ROUTING_NOTE = 'Metis for swap quotes only (swaps are signed on jup.ag), Ultra for holdings reads';

/** One line for a footer: satisfies §8.4 and §2.3 together. */
export function attributionLine() {
  const surfaces = SURFACES.filter((s) => !['Metis Swap API', 'Ultra API'].includes(s.name)).map((s) => s.name).join(' + ');
  return `${POWERED_BY} — ${surfaces} for the grid; ${ROUTING_NOTE}`;
}

/** Longer form for the dashboard, where there is room to be explicit. */
export function attributionDetail() {
  return SURFACES.map((s) => `${s.name} (${s.purpose}): ${s.bases.join(' or ')}`).join('\n');
}
