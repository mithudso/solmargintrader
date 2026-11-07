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
  // The soltui bridge. soltuiCommands is a listing. soltuiCall can run ANY soltui
  // command, so it is allowed only through assertSoltuiCallAllowed below.
  'soltuiCommands',
  'soltuiCall',
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

/**
 * soltuiCall can reach every soltui command, including ones that change state on
 * a real-money system. The harness may only call a command that soltui itself
 * lists as read_only and not requires_confirm, and never passes a confirm.
 *
 * @param {string} command  the soltui registry name to call
 * @param {object} params   the params it would send
 * @param {Array<object>} listing  the `result` of the soltuiCommands envelope
 */
export function assertSoltuiCallAllowed(command, params, listing) {
  const entry = Array.isArray(listing) ? listing.find((c) => c?.name === command) : undefined;
  if (!entry) throw new Error(`e2e harness refuses soltuiCall "${command}": soltui does not list it`);
  if (entry.read_only !== true || entry.requires_confirm === true) {
    throw new Error(`e2e harness refuses soltuiCall "${command}": it is not a read-only command`);
  }
  if (params && Object.hasOwn(params, 'confirm')) {
    throw new Error(`e2e harness refuses soltuiCall "${command}": it never sends confirm`);
  }
  return entry;
}
