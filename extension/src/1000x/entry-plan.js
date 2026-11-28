/**
 * Opening a Jupiter 1000x position from the 1s scalp window.
 *
 * The window never builds or signs anything. It asks the page bridge to press
 * the page's own size button and its own Long or Short button; Jupiter builds
 * the trade and the wallet signs it. This module holds the checks made before
 * that request and the bookkeeping after it: which request is out, and which
 * newly listed position is the one it opened. Pure; callers pass the clock.
 */

export const ENTRY_LIMITS = Object.freeze({
  // How long a first click stays armed waiting for the confirming click.
  confirmMs: 4000,
  // The confirming click must come at least this long after the first: a double-click is one decision, not two.
  confirmGapMs: 600,
  // How long to wait for the new position to be listed before saying it was not seen.
  appearMs: 60_000,
  // A wallet prompt can be answered late. A position listed within this time is still adopted and its levels armed.
  lateMs: 600_000,
});

// Replies that do not say whether the page pressed. The request may still have gone through.
const UNKNOWN_OUTCOME = new Set(['page_timeout', 'page_unreachable', 'page_no_reply', 'extension_unreachable', 'extension_error', 'page_read_failed', 'no_reply']);

/** Share of the page's own "Max" amount. The page has buttons for all but three quarters. */
export const SIZE_FRACTIONS = Object.freeze([0.25, 0.5, 0.75, 1]);

const positive = value => typeof value === 'number' && Number.isFinite(value) && value > 0;

/**
 * Check an entry before anything is sent. `levels` are distances in basis
 * points from the fill (null for none); they become prices only once the
 * position is listed with its real entry. `bustBps` is the adverse move that
 * liquidates at the page's current leverage.
 */
export function validateEntry({ side, fraction, takeProfitBps = null, stopLossBps = null, bustBps, form, guardLive, pending }) {
  const errors = [];
  if (side !== 'long' && side !== 'short') errors.push('Choose long or short.');
  if (!SIZE_FRACTIONS.includes(fraction)) errors.push('Choose a size: a quarter, half, three quarters or all.');
  if (pending) errors.push('An entry request is already out. Wait for it to finish.');
  if (guardLive) errors.push('A take profit or stop loss is live on another position. Disarm it first.');
  if (!form?.recognized) errors.push('The order form on the Jupiter tab could not be read.');
  else {
    if (!positive(form.leverage)) errors.push('The page’s leverage could not be read.');
    if (form.mode !== 'Classic') errors.push('Only Classic mode is supported. Switch the Jupiter page to Classic.');
    if (form.busy) errors.push('The Jupiter page is busy with another request.');
    if (side === 'long' && !form.longEnabled) errors.push('The page has its Long button disabled.');
    if (side === 'short' && !form.shortEnabled) errors.push('The page has its Short button disabled.');
  }
  for (const [label, value] of [['Take profit', takeProfitBps], ['Stop loss', stopLossBps]]) {
    if (value !== null && !positive(value)) errors.push(`${label} must be a positive distance in basis points.`);
  }
  if (stopLossBps !== null && positive(stopLossBps)) {
    if (!positive(bustBps)) errors.push('The page’s leverage could not be read, so the stop loss cannot be checked against the bust distance.');
    else if (stopLossBps >= bustBps) errors.push(`Stop loss is at or beyond the bust distance (${bustBps.toFixed(1)} bp); the position would be liquidated first.`);
  }
  return { ok: errors.length === 0, errors };
}

/**
 * The listed position this entry opened: the one row for that market and side
 * that was not there before, or null. Rows are counted, not just named, so a
 * new position with the same entry text as an old one is still found.
 */
export function newPosition({ before, positions, coin, side, leverage = null, keyOf }) {
  const seen = new Map();
  for (const key of before) seen.set(key, (seen.get(key) ?? 0) + 1);
  const fresh = [];
  for (const row of positions) {
    const key = keyOf(row), left = seen.get(key) ?? 0;
    if (left > 0) seen.set(key, left - 1);
    else if (row.coin === coin && row.side === side && (leverage === null || row.leverage === leverage)) fresh.push(row);
  }
  return fresh.length === 1 ? fresh[0] : null;
}

/**
 * One entry at a time: idle -> confirming -> sent -> opened | unseen | failed.
 * A request that is out is never repeated. A reply that does not say whether
 * the page pressed leaves the entry out and watched, never marked as failed.
 */
export class EntryTracker {
  #state = 'idle';
  #request = null;
  #note = '';

  /** First click. With `confirm` off the request is ready to send at once. */
  begin({ side, fraction, takeProfitBps, stopLossBps, mode, before, confirm, nowMs }) {
    if (this.#state === 'sent') return { send: false, reason: 'pending' };
    const same = this.#state === 'confirming' && this.#request.side === side && this.#request.fraction === fraction
      && nowMs - this.#request.at <= ENTRY_LIMITS.confirmMs;
    // Too soon after the first press: the same gesture, not a confirmation.
    if (confirm && same && nowMs - this.#request.at < ENTRY_LIMITS.confirmGapMs) return { send: false, reason: 'confirm' };
    if (confirm && !same) {
      this.#state = 'confirming';
      this.#request = { side, fraction, takeProfitBps, stopLossBps, mode, before: [...before], at: nowMs };
      this.#note = '';
      return { send: false, reason: 'confirm' };
    }
    this.#state = 'sent';
    this.#request = { side, fraction, takeProfitBps, stopLossBps, mode, before: [...before], at: nowMs };
    this.#note = '';
    return { send: true };
  }

  /** The bridge's reply to the one request. */
  onReply(reply, nowMs) {
    if (this.#state !== 'sent') return;
    const reason = reply?.clicked === true ? null : reply?.reason ?? 'no_reply';
    if (reason === null || UNKNOWN_OUTCOME.has(reason)) {
      // uncertain: the page may have pressed; keep watching for the position rather than invite a second entry.
      this.#request = { ...this.#request, clickedAt: nowMs, uncertain: reason !== null, amountText: reply?.amountText ?? null, leverage: reply?.leverage ?? null };
      this.#note = reason ?? '';
      return;
    }
    this.#state = 'failed';
    this.#note = reason;
  }

  /**
   * Call on every poll: with the position list when it was read completely,
   * with null otherwise, so the wait still ends when the page cannot be read.
   * Returns the opened position once, or null.
   */
  onPositions({ positions, coin, keyOf, nowMs }) {
    this.onTick(nowMs);
    const watching = (this.#state === 'sent' || this.#state === 'unseen') && this.#request?.clickedAt;
    if (!watching) return null;
    const opened = Array.isArray(positions) ? newPosition({ before: this.#request.before, positions, coin, side: this.#request.side,
      leverage: this.#request.leverage, keyOf }) : null;
    if (opened) {
      this.#state = 'opened';
      return { position: opened, request: { ...this.#request } };
    }
    const waited = nowMs - this.#request.clickedAt;
    if (this.#state === 'sent' && waited >= ENTRY_LIMITS.appearMs) { this.#state = 'unseen'; this.#note = 'position_not_seen'; }
    // After the late window nothing listed can be tied to this request any more.
    if (this.#state === 'unseen' && waited >= ENTRY_LIMITS.lateMs) this.#request = { ...this.#request, clickedAt: null };
    return null;
  }

  /** A first click that was not confirmed in time is dropped. */
  onTick(nowMs) {
    if (this.#state === 'confirming' && nowMs - this.#request.at > ENTRY_LIMITS.confirmMs) { this.#state = 'idle'; this.#request = null; return true; }
    return false;
  }

  reset() {
    if (this.#state === 'sent') return false;
    this.#state = 'idle'; this.#request = null; this.#note = '';
    return true;
  }

  get pending() { return this.#state === 'sent'; }
  snapshot() { return { state: this.#state, request: this.#request ? { ...this.#request } : null, note: this.#note }; }
}
