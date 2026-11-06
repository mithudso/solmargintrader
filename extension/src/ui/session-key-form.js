/**
 * Pure helpers for the dashboard's "Create session key" control.
 *
 * Kept free of DOM and chrome.* so the input rules and the message shape are
 * unit-testable. The command in src/core/commands.js stays the authority; this
 * only catches a typo before a passphrase is sealed into a vault that nothing
 * can reopen.
 */

// Mirrors the check in the createSessionKey command. Do not make it weaker.
export const MIN_PASSPHRASE_LENGTH = 12;

/**
 * Returns an error string, or null when the inputs may be submitted.
 * The messages never contain the passphrase.
 */
export function validateSessionKeyInputs({ passphrase, confirmPassphrase, acknowledged }) {
  if (typeof passphrase !== 'string' || passphrase.length < MIN_PASSPHRASE_LENGTH) {
    return `Passphrase must be at least ${MIN_PASSPHRASE_LENGTH} characters.`;
  }
  if (passphrase !== confirmPassphrase) {
    // A mistyped passphrase seals a key nobody can reopen, so make it a hard stop.
    return 'The two passphrases do not match.';
  }
  if (acknowledged !== true) {
    return 'Tick the box to confirm you understand this replaces any existing session key.';
  }
  return null;
}

/** The exact registered command message. */
export function buildCreateSessionKeyMessage(passphrase) {
  return { type: 'createSessionKey', passphrase };
}

/**
 * Turn a command response into non-secret display text. The response carries
 * the sealed vault; it is deliberately not rendered.
 */
export function describeCreateResult(res) {
  if (!res?.ok) return { ok: false, text: `Failed: ${res?.error ?? 'no response from the background worker'}` };
  return { ok: true, text: `Session key created. Public address: ${res.pubkeyBs58}` };
}
