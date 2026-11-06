/**
 * What the e2e harness may ask the extension to do.
 *
 * The harness drives the real service worker through `chrome.runtime.sendMessage`.
 * It must never arm the extension, change its mode, create a key or cancel an
 * order, so every message goes through this allowlist first. A name that is not
 * listed is refused before it leaves the harness, which makes "the e2e never
 * arms" a property of the code rather than of the current checks.
 */

export const ALLOWED_MESSAGES = Object.freeze([
  // read-only inspection
  'status',
  'getConfig',
  'getLimits',
  'levels',
  'capital',
  'price',
  'plan',
  'pnl',
  'data',
  'exportCsv',
  'venueInfo',
  // A tick on a disarmed extension returns `not-armed` and places nothing.
  'tick',
  // Stores a canary string so the secrets checks can prove it never leaks.
  'setApiKey',
]);

export const FORBIDDEN_MESSAGES = Object.freeze([
  'arm',
  'disarm',
  'kill',
  'clearKill',
  'setConfig',
  'setLimits',
  'createSessionKey',
  'cancelOrder',
  'resolveIntent',
  'reset',
]);

/** Throws unless `type` is an allowlisted message name. */
export function assertAllowedMessage(type) {
  if (!ALLOWED_MESSAGES.includes(type)) {
    throw new Error(`e2e harness refuses to send "${type}": not on the read-only allowlist`);
  }
  return type;
}

/** Throws if a page in the harness ever shows the extension armed. */
export function assertDisarmed(runtime, where) {
  if (runtime?.armed !== false) {
    throw new Error(`e2e invariant broken at ${where}: runtime.armed is ${JSON.stringify(runtime?.armed)}`);
  }
}
