/**
 * Take-profit / stop-loss guard for one Jupiter 1000x position.
 *
 * The 1000x page has no price-triggered exit. This guard watches the public
 * oracle quote and, when a level is crossed, asks the page bridge to press the
 * page's own Close button for that one position. It never opens a position,
 * never builds or signs a transaction and never retries a click it cannot
 * confirm: Jupiter builds the close, the wallet signs it.
 *
 * Pure state machine. Callers pass the clock, the quote and the bridge replies.
 */

export const GUARD_LIMITS = Object.freeze({
  // A level is only compared with a quote this fresh, on both clocks.
  quoteMaxAgeMs: 2000,
  // After a trigger, how long to keep trying while the page shows "Close in Ns".
  closeWaitMs: 30_000,
  // After the click, how long the position may stay listed before it is reported.
  confirmMs: 25_000,
  // The page's entry price must sit this close to the oracle price, or it was misread.
  entryTolerance: 0.2,
  // Complete reads in a row that must miss the position before it counts as gone.
  // One read can catch the table mid-render.
  goneReads: 3,
});

export const GUARD_STATES = Object.freeze(['idle', 'armed', 'triggered', 'clicked', 'closed', 'alerted', 'unconfirmed', 'failed']);

const positive = value => typeof value === 'number' && Number.isFinite(value) && value > 0;

/** A plain positive decimal, or null. Thousands separators and symbols are refused, not guessed. */
export function parseLevel(text) {
  if (typeof text !== 'string') return null;
  const trimmed = text.trim();
  if (!/^\d{1,12}(\.\d{1,12})?$/.test(trimmed)) return null;
  const value = Number(trimmed);
  return positive(value) ? value : null;
}

/** Identity of a listed position. The page exposes no id, so two identical rows are ambiguous. */
export function positionKey(position) {
  return [position.coin, position.side, position.leverage, position.entryText].join('|');
}

/**
 * Check a requested pair of levels against the position and the current price.
 * Returns { ok, errors, takeProfit, stopLoss }; a level left empty is null.
 */
export function validateLevels({ position, price, takeProfit = null, stopLoss = null, allowCrossed = false }) {
  const errors = [];
  if (!position || !['long', 'short'].includes(position.side)) return { ok: false, errors: ['No position selected.'] };
  if (!positive(price)) errors.push('No live price.');
  if (!positive(position.entry)) errors.push('The position’s entry price could not be read from the page.');
  if (takeProfit === null && stopLoss === null) errors.push('Set a take profit, a stop loss, or both.');
  for (const [label, value] of [['Take profit', takeProfit], ['Stop loss', stopLoss]]) {
    if (value !== null && !positive(value)) errors.push(`${label} must be a positive price.`);
  }
  if (errors.length) return { ok: false, errors };
  if (Math.abs(position.entry / price - 1) > GUARD_LIMITS.entryTolerance) {
    errors.push('The entry price on the page is far from the live price; it was probably misread.');
  }
  const long = position.side === 'long';
  // allowCrossed: the levels were fixed before the fill, and price may have passed one since.
  // The side checks are skipped so the guard can arm and act at once instead of leaving the position bare.
  if (!allowCrossed && takeProfit !== null && (long ? takeProfit <= price : takeProfit >= price)) {
    errors.push(`Take profit must be ${long ? 'above' : 'below'} the current price for a ${position.side}.`);
  }
  if (stopLoss !== null) {
    if (!allowCrossed && (long ? stopLoss >= price : stopLoss <= price)) {
      errors.push(`Stop loss must be ${long ? 'below' : 'above'} the current price for a ${position.side}.`);
    } else if (!positive(position.bust)) {
      // Without the bust price the stop cannot be shown to sit inside it.
      errors.push('The bust price could not be read from the page, so a stop loss cannot be checked.');
    } else if (long ? stopLoss <= position.bust : stopLoss >= position.bust) {
      errors.push('Stop loss is at or beyond the bust price; the position would be liquidated first.');
    }
  }
  return { ok: errors.length === 0, errors, takeProfit, stopLoss };
}

/** A distance in basis points: a plain positive decimal up to 10,000, or null. */
export function parseDistance(text) {
  const value = parseLevel(text);
  return value !== null && value <= 10_000 ? value : null;
}

/**
 * Turn the order form's two fields into price levels for a position.
 * unit 'bp' reads each field as a distance from the position's entry, in the
 * winning direction for the take profit and the losing direction for the stop.
 * unit 'price' reads plain prices. An empty field is "no level". Returns
 * { takeProfit, stopLoss, errors }.
 */
export function resolveLevels({ unit, takeProfitText = '', stopLossText = '', position }) {
  const errors = [], out = { takeProfit: null, stopLoss: null, errors };
  if (unit !== 'bp' && unit !== 'price') { errors.push('Unknown level unit.'); return out; }
  const long = position?.side === 'long';
  for (const [key, label, text, direction] of [['takeProfit', 'Take profit', takeProfitText, 1], ['stopLoss', 'Stop loss', stopLossText, -1]]) {
    if (!String(text).trim()) continue;
    if (unit === 'price') {
      out[key] = parseLevel(text);
      if (out[key] === null) errors.push(`${label} is not a plain price.`);
      continue;
    }
    const distance = parseDistance(text);
    if (distance === null) { errors.push(`${label} is not a plain distance in basis points.`); continue; }
    if (!position || !positive(position.entry) || !['long', 'short'].includes(position.side)) {
      errors.push('The position’s entry price could not be read from the page.');
      continue;
    }
    out[key] = position.entry * (1 + (long ? 1 : -1) * direction * distance / 1e4);
  }
  return out;
}

/** Which level, if any, this price has reached. */
export function crossed({ side, price, takeProfit, stopLoss }) {
  if (!positive(price)) return null;
  const long = side === 'long';
  if (stopLoss !== null && (long ? price <= stopLoss : price >= stopLoss)) return 'stopLoss';
  if (takeProfit !== null && (long ? price >= takeProfit : price <= takeProfit)) return 'takeProfit';
  return null;
}

/** True when the quote is recent on the exchange clock and on the receipt clock. */
export function quoteFresh(quote, nowMs) {
  if (!quote || !positive(quote.price)) return false;
  const exchangeAge = nowMs - quote.exchangeMs, receiptAge = nowMs - quote.receivedMs;
  return [exchangeAge, receiptAge].every(age => Number.isFinite(age) && age >= -250 && age <= GUARD_LIMITS.quoteMaxAgeMs);
}

export class ExitGuard {
  #state = 'idle';
  #position = null;
  #levels = { takeProfit: null, stopLoss: null };
  #mode = 'alert';
  #trigger = null;
  #clickedAt = null;
  #note = '';
  #misses = 0;
  #attempts = 0;
  #journal = [];

  #log(event, detail, nowMs) {
    this.#journal.push({ at: nowMs, event, ...detail });
    if (this.#journal.length > 50) this.#journal.shift();
  }

  /**
   * Arm for one position. mode 'alert' only notifies; 'close' presses the page's
   * Close button. Returns { ok, errors }.
   */
  arm({ position, price, takeProfit = null, stopLoss = null, mode = 'alert', allowCrossed = false, nowMs }) {
    if (!['idle', 'closed', 'alerted', 'unconfirmed', 'failed'].includes(this.#state)) {
      return { ok: false, errors: ['The guard is already armed.'] };
    }
    if (!['alert', 'close'].includes(mode)) return { ok: false, errors: ['Unknown guard mode.'] };
    const check = validateLevels({ position, price, takeProfit, stopLoss, allowCrossed });
    if (!check.ok) return { ok: false, errors: check.errors };
    this.#position = { ...position, key: positionKey(position) };
    this.#levels = { takeProfit, stopLoss };
    this.#mode = mode;
    this.#trigger = null;
    this.#clickedAt = null;
    this.#misses = 0;
    this.#attempts = 0;
    this.#state = 'armed';
    this.#note = '';
    this.#log('armed', { key: this.#position.key, takeProfit, stopLoss, mode, price }, nowMs);
    return { ok: true, errors: [] };
  }

  disarm(reason, nowMs) {
    // A close request that is out cannot be recalled; only its outcome may end these states.
    if (this.#state === 'clicked' || this.#state === 'triggered') return false;
    if (this.#state === 'idle') return true;
    this.#log('disarmed', { reason }, nowMs);
    this.#state = 'idle';
    this.#note = reason ?? '';
    this.#trigger = null;
    return true;
  }

  /**
   * Compare a quote with the armed levels. Returns the action to take, once:
   * { type: 'close' | 'alert', reason, price, expect }.
   */
  onQuote(quote, nowMs) {
    if (this.#state !== 'armed' || !quoteFresh(quote, nowMs)) return null;
    const reason = crossed({ side: this.#position.side, price: quote.price, ...this.#levels });
    if (!reason) return null;
    this.#trigger = { reason, price: quote.price, at: nowMs, level: this.#levels[reason] };
    this.#log('triggered', { reason, price: quote.price, level: this.#levels[reason], mode: this.#mode }, nowMs);
    if (this.#mode === 'alert') {
      this.#state = 'alerted';
      return { type: 'alert', reason, price: quote.price };
    }
    this.#state = 'triggered';
    return { type: 'close', reason, price: quote.price, expect: this.expect };
  }

  /** The identity the page bridge must match before it clicks. */
  get expect() {
    const p = this.#position;
    return p ? { coin: p.coin, side: p.side, leverage: p.leverage, entryText: p.entryText } : null;
  }

  /**
   * The bridge's reply to a close request. Returns true when the caller should
   * ask again (the page still shows the 15 second close lock).
   */
  onCloseResult(result, nowMs) {
    const pressed = result?.clicked === true || result?.already === true;
    // A reply can arrive after the wait ran out. A press that happened is still recorded.
    if (this.#state !== 'triggered' && !(pressed && this.#state === 'failed' && this.#trigger)) return false;
    const earlier = this.#attempts++;
    if (pressed) {
      this.#state = 'clicked';
      this.#clickedAt = nowMs;
      this.#misses = 0;
      // already: the page was closing this position before the guard pressed.
      this.#log(result.clicked === true ? 'clicked' : 'already-closing', { label: result.label ?? null }, nowMs);
      return false;
    }
    if (result?.reason === 'position_not_listed' && earlier > 0) {
      // An earlier request went out and its reply was lost; the row is gone now.
      this.#state = 'clicked';
      this.#clickedAt = nowMs;
      this.#misses = 0;
      this.#log('gone-after-request', {}, nowMs);
      return false;
    }
    if (result?.retry === true && nowMs - this.#trigger.at < GUARD_LIMITS.closeWaitMs) {
      this.#note = result.reason ?? 'waiting';
      return true;
    }
    this.#state = 'failed';
    this.#note = result?.reason ?? 'no_reply';
    this.#log('failed', { reason: this.#note }, nowMs);
    return false;
  }

  /**
   * Reconcile with the page's current position list. `positions` is null when
   * the list could not be read; `complete` is false when some row was still
   * opening or unreadable, so an absent position proves nothing. Returns a
   * change the UI should announce, or null.
   */
  onPositions(positions, nowMs, complete = true) {
    if (!this.#position) return null;
    const readable = Array.isArray(positions);
    const listed = readable && positions.some(row => positionKey(row) === this.#position.key);
    if (listed) this.#misses = 0;
    else if (readable && complete) this.#misses += 1;
    const gone = this.#misses >= GUARD_LIMITS.goneReads;
    if (this.#state === 'armed' && gone) {
      this.#state = 'idle';
      this.#note = 'position_gone';
      this.#log('position-gone', {}, nowMs);
      return 'position_gone';
    }
    if (this.#state === 'clicked') {
      if (gone) {
        this.#state = 'closed';
        this.#log('closed', {}, nowMs);
        return 'closed';
      }
      if (nowMs - this.#clickedAt >= GUARD_LIMITS.confirmMs) {
        this.#state = 'unconfirmed';
        // Still listed, or the page stopped answering: say which.
        this.#note = listed ? 'still_listed' : 'page_unreadable';
        this.#log('unconfirmed', { reason: this.#note }, nowMs);
        return 'unconfirmed';
      }
    }
    return null;
  }

  /** A trigger whose close attempts ran out of time without a reply. */
  onTimeout(nowMs) {
    if (this.#state === 'triggered' && nowMs - this.#trigger.at >= GUARD_LIMITS.closeWaitMs) {
      this.#state = 'failed';
      this.#note = 'close_window_elapsed';
      this.#log('failed', { reason: this.#note }, nowMs);
      return true;
    }
    return false;
  }

  snapshot() {
    return { state: this.#state, mode: this.#mode, position: this.#position ? { ...this.#position } : null,
      levels: { ...this.#levels }, trigger: this.#trigger ? { ...this.#trigger } : null,
      clickedAt: this.#clickedAt, note: this.#note, journal: this.#journal.map(entry => ({ ...entry })) };
  }
}
