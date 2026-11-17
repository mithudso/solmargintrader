import { oracleIdentity } from './oracle-model.js';
import { LIVE_ORACLE, liveIdentity, liveSnapshot, transitionLive } from './oracle-live-model.js';
import { LiveOracleStore } from './oracle-live-store.js';
import { soltui } from '../ui/ui-kit.js';

const finite = value => typeof value === 'number' && Number.isFinite(value);
const supported = new Set(['BTC', 'ZEC']);

/** The live head needs identified, fresh observations, not complete minute bars. */
export function liveInput(snapshot, nowMs) {
  const identity = oracleIdentity(snapshot);
  const quote = snapshot.quote;
  const stream = snapshot.streamStatus ?? snapshot.status;
  const valid = stream === 'live' && finite(quote?.price) && quote.price > 0
    && [quote.exchangeMs, quote.receivedMs].every(finite)
    && quote.exchangeMs >= 0 && quote.receivedMs >= 0
    && quote.receivedMs <= nowMs && quote.exchangeMs <= quote.receivedMs + 250
    && nowMs - quote.receivedMs <= LIVE_ORACLE.graceMs && nowMs - quote.exchangeMs <= LIVE_ORACLE.graceMs;
  return { identity, key: liveIdentity(identity), valid,
    quote: valid ? { price: quote.price, exchangeMs: quote.exchangeMs, receivedMs: quote.receivedMs } : null,
    reason: stream !== 'live' ? 'feed_unavailable' : 'stale_oracle_quote' };
}

/** One committed producer, six live horizons, and a shared display-only relay. */
export class LiveOracleController {
  #store; #clock; #call; #change; #id;
  #latest = null; #identity = null; #key = null; #local = null; #shared = null;
  #running = false; #queued = false; #disposed = false; #eligible = false;
  #generation = 0; #nextAt = 0; #publisher; #sequence = 0; #selected = 600;
  #status = 'unavailable'; #error = null;
  #relayRunning = false; #relayQueued = null;
  #lastQueuedQuote = null;
  #restoreTicket = null; #restoreRetryAt = 0;
  #localExpiresAtMs = null; #timeoutMs; #schedule; #cancelTimer; #calls = new Set();

  constructor({ store = new LiveOracleStore(), clock = Date.now, call = soltui,
    onChange = () => {}, id = () => crypto.randomUUID(), relayTimeoutMs = 1500,
    schedule = (callback, delay) => globalThis.setTimeout(callback, delay),
    cancelTimer = timer => globalThis.clearTimeout(timer) } = {}) {
    if (!Number.isFinite(relayTimeoutMs) || relayTimeoutMs <= 0) throw new Error('invalid_signal_timeout');
    this.#store = store; this.#clock = clock; this.#call = call; this.#change = onChange; this.#id = id;
    this.#timeoutMs = relayTimeoutMs; this.#schedule = schedule; this.#cancelTimer = cancelTimer;
    this.#publisher = this.#id();
  }

  selectHorizon(horizon) {
    if (!LIVE_ORACLE.horizons.includes(horizon)) throw new Error('invalid_oracle_horizon');
    this.#selected = horizon; this.#emit();
  }

  #emit() {
    if (this.#disposed) return;
    const invalid = this.#status !== 'ready';
    this.#change({ selectedHorizon: this.#selected, asset: this.#identity?.market,
      local: this.#local, shared: invalid && this.#shared ? { ...this.#shared, fresh: false } : this.#shared,
      localExpiresAtMs: this.#localExpiresAtMs, status: this.#status, error: this.#error });
  }

  observe(snapshot) {
    if (this.#disposed) return;
    this.#latest = snapshot;
    let input;
    try { input = liveInput(snapshot, this.#clock()); }
    catch { this.suspend('source_changed', true); return; }
    if (input.key !== this.#key) {
      this.#revoke('source_changed'); this.#cancelCalls();
      this.#generation++; this.#store.cancelPending?.();
      this.#identity = input.identity; this.#key = input.key;
      this.#local = null; this.#shared = null; this.#localExpiresAtMs = null; this.#relayQueued = null; this.#nextAt = 0;
      this.#publisher = this.#id(); this.#sequence = 0;
      this.#lastQueuedQuote = null;
      this.#restoreRetryAt = 0;
    }
    if (!this.#local && typeof this.#store.load === 'function' && this.#clock() >= this.#restoreRetryAt
      && (this.#restoreTicket?.generation !== this.#generation || this.#restoreTicket?.key !== this.#key)) void this.#restore(this.#generation, this.#key);
    if (!input.valid) {
      if (this.#eligible) { this.#revoke(input.reason === 'feed_unavailable' ? 'feed_unavailable' : 'stale');
        this.#generation++; this.#store.cancelPending?.(); this.#cancelCalls(); }
      this.#eligible = false; this.#queued = false; this.#relayQueued = null;
      this.#status = 'stale'; this.#error = input.reason; this.#emit(); return;
    }
    this.#eligible = true; this.#queued = true;
    if (!this.#running && this.#clock() >= this.#nextAt) void this.#drain();
  }

  async #restore(generation, key) {
    const ticket = { generation, key }; this.#restoreTicket = ticket;
    try {
      const state = await this.#store.load(key);
      if (this.#disposed || generation !== this.#generation || key !== this.#key || this.#local || !state) return;
      this.#local = liveSnapshot(state, this.#clock());
      const quote = state.lastQuote;
      this.#localExpiresAtMs = quote ? Math.min(quote.exchangeMs, quote.receivedMs) + LIVE_ORACLE.graceMs : null;
      this.#emit();
    } catch {
      if (!this.#disposed && generation === this.#generation && key === this.#key && !this.#local) {
        this.#status = 'error'; this.#error = 'live_oracle_storage_unavailable'; this.#emit();
      }
    } finally {
      if (this.#restoreTicket === ticket) { this.#restoreTicket = null; this.#restoreRetryAt = this.#clock() + 5000; }
    }
  }

  async #drain() {
    this.#running = true; this.#queued = false;
    const generation = this.#generation, key = this.#key;
    this.#nextAt = this.#clock() + 1000;
    const current = () => !this.#disposed && generation === this.#generation && key === this.#key && this.#eligible;
    try {
      const result = await this.#store.update(key, state => {
        if (!current()) throw new Error('live_oracle_obsolete');
        const input = liveInput(this.#latest, this.#clock());
        if (!input.valid || input.key !== key) throw new Error('live_oracle_obsolete');
        return transitionLive(state, { identity: input.identity, quote: input.quote, nowMs: this.#clock() });
      });
      if (!current()) return;
      const nowMs = this.#clock();
      const snapshot = liveSnapshot(result.state, nowMs);
      const quote = result.state.lastQuote;
      this.#local = snapshot; this.#error = null;
      this.#localExpiresAtMs = quote ? Math.min(quote.exchangeMs, quote.receivedMs) + LIVE_ORACLE.graceMs : null;
      this.#status = snapshot.status === 'stale' ? 'stale' : 'ready'; this.#emit();
      if (this.#status !== 'ready' || !quote || !supported.has(this.#identity.market)) return;
      if (this.#lastQueuedQuote && (quote.exchangeMs <= this.#lastQueuedQuote.exchangeMs
        || quote.receivedMs <= this.#lastQueuedQuote.receivedMs)) return;
      this.#lastQueuedQuote = { exchangeMs: quote.exchangeMs, receivedMs: quote.receivedMs };
      const packet = { schema_version: 1, publisher_id: this.#publisher, sequence: ++this.#sequence,
        asset: this.#identity.market, quote: { ...quote }, snapshot };
      // A slow native client cannot delay observing, scoring or learning.
      this.#relayQueued = { packet, generation, key };
      if (!this.#relayRunning) void this.#relayDrain();
    } catch {
      if (current()) { this.#status = 'error'; this.#error = 'live_oracle_storage_unavailable'; this.#emit(); }
    } finally {
      this.#running = false;
      if (!this.#disposed && this.#queued && this.#clock() >= this.#nextAt) void this.#drain();
    }
  }

  async #relayDrain() {
    const entry = this.#relayQueued;
    this.#relayQueued = null;
    if (!entry || this.#disposed) return;
    const { packet, generation, key } = entry;
    const current = () => !this.#disposed && generation === this.#generation && key === this.#key && this.#eligible;
    if (!current() || this.#clock() - packet.quote.receivedMs > LIVE_ORACLE.graceMs) return;
    this.#relayRunning = true;
    try {
      const reply = await this.#boundedCall('oracle.signals.publish', { packet });
      if (current()) { this.#shared = reply.asset; this.#error = null; }
    } catch {
      if (current()) {
        this.#error = 'signal_sharing_unavailable';
        try {
          const reply = await this.#boundedCall('oracle.signals.status');
          if (current()) {
            const asset = reply.assets?.[packet.asset];
            this.#shared = asset?.source === packet.snapshot.source ? asset : null;
          }
        } catch { if (current()) this.#shared = null; }
      }
    } finally {
      if (current()) this.#emit();
      this.#relayRunning = false;
      if (!this.#disposed && this.#relayQueued) void this.#relayDrain();
    }
  }

  #boundedCall(command, params) {
    return new Promise((resolve, reject) => {
      let done = false, timer;
      const finish = (fn, value) => {
        if (done) return; done = true; this.#cancelTimer(timer); this.#calls.delete(cancel); fn(value);
      };
      const cancel = () => finish(reject, new Error('signal_request_obsolete'));
      timer = this.#schedule(() => finish(reject, new Error('signal_request_timeout')), this.#timeoutMs);
      this.#calls.add(cancel);
      try { Promise.resolve(this.#call(command, params)).then(value => finish(resolve, value), error => finish(reject, error)); }
      catch (error) { finish(reject, error); }
    });
  }

  #cancelCalls() { for (const cancel of [...this.#calls]) cancel(); }

  #revoke(reason) {
    if (!this.#identity || !this.#sequence || !supported.has(this.#identity.market)) return;
    const event = { asset: this.#identity.market, publisher_id: this.#publisher, sequence: ++this.#sequence, reason };
    // Best effort on page teardown; the relay's source expiry also bounds a lost revoke.
    try { Promise.resolve(this.#call('oracle.signals.invalidate', { event })).catch(() => {}); } catch { /* Transport unavailable. */ }
  }

  suspend(reason = 'unavailable', forget = false) {
    this.#revoke(reason === 'source_changed' ? 'source_changed' : 'feed_unavailable'); this.#cancelCalls();
    this.#generation++; this.#eligible = false; this.#queued = false; this.#nextAt = 0;
    this.#relayQueued = null;
    this.#store.cancelPending?.(); this.#status = reason; this.#error = reason;
    if (forget) { this.#key = null; this.#identity = null; this.#local = null; this.#shared = null; this.#localExpiresAtMs = null; }
    this.#emit();
  }

  stop() {
    this.#cancelCalls(); this.#revoke('page_closed');
    this.#disposed = true; this.#generation++; this.#queued = false;
    this.#relayQueued = null;
    this.#store.close();
  }
}
