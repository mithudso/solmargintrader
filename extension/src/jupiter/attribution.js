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
 * §2.3 is written around the two swap routers — "Jupiter Ultra" and "Metis" —
 * and this extension uses **neither**. It talks to Trigger V2 for orders and
 * Price v3 for marks, and it does not route a swap at all. So the accurate label
 * names those surfaces and says the swap router is unused, rather than picking
 * whichever of the two names looks closest. Claiming "Metis" here would be the
 * precise mischaracterisation the clause exists to prevent.
 *
 * Not legal advice. `SURFACES` is checked against the real base URLs by
 * `test/attribution.test.js`, so adding an API without updating the label fails
 * the build — the same anti-drift shape used for strategy cards.
 */

import { TRIGGER_BASE } from './trigger.js';
import { PRICE_HOSTS } from './price.js';

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
]);

/** No swap router is used, which §2.3 is about. Stated rather than left implied. */
export const ROUTING_API = null;
export const ROUTING_NOTE = 'no swap router (neither Jupiter Ultra nor Metis)';

/** One line for a footer: satisfies §8.4 and §2.3 together. */
export function attributionLine() {
  const surfaces = SURFACES.map((s) => s.name).join(' + ');
  return `${POWERED_BY} — ${surfaces}, ${ROUTING_NOTE}`;
}

/** Longer form for the dashboard, where there is room to be explicit. */
export function attributionDetail() {
  return SURFACES.map((s) => `${s.name} (${s.purpose}): ${s.bases.join(' or ')}`).join('\n');
}
