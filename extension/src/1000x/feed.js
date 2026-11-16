/** Observed public Jupiter oracle contracts, bound in docs/JUPITER-1000X-OVERLAY.md.
 * This module only reads markets/history and subscribes to public oracle prices.
 * Prices are oracle observations, not venue fills or trade-volume observations.
 */

import { MAX_INDICATOR_LENGTH } from './indicators.js';

export const TIMEFRAMES = Object.freeze([
  Object.freeze({ label: '1m', seconds: 60 }),
  Object.freeze({ label: '5m', seconds: 300 }),
  Object.freeze({ label: '10m', seconds: 600 }),
  Object.freeze({ label: '15m', seconds: 900 }),
  Object.freeze({ label: '20m', seconds: 1200 }),
  Object.freeze({ label: '1h', seconds: 3600 }),
]);

export const JUPITER_ENDPOINTS = Object.freeze({
  markets: 'https://yolo-api.jup.ag/markets',
  history: 'https://perps-api.jup.ag/v1/pyth/fixed_rate%40200ms/history',
  stream: 'wss://perps-api.jup.ag/v1/pyth/stream',
});

const SOURCE = 'Jupiter Pyth oracle USD';
const STALE_MS = 10_000;
const GAP_MS = 5_000;
const HISTORY_EVERY_MS = 30_000;
// Volty's previous-bar envelope needs length + 2 completed bars; keep one
// additional developing candle without evicting that full warmup segment.
const HISTORY_BARS = MAX_INDICATOR_LENGTH + 2;
const MAX_BARS = HISTORY_BARS + 1;
// 48 complete 20m windows plus at most 19 minutes in the open 20m bucket.
// This is bounded history on the existing feed, not another stream/recorder.
export const CONTEXT_HISTORY_BARS = 48 * 20 + 19;
const MAX_JSON_BYTES = 2_000_000;
const validPrice = (value) => typeof value === 'number' && Number.isFinite(value) && value > 0;
const validTime = (value) => Number.isSafeInteger(value) && value > 0;

function refusal(code) {
  return Object.assign(new Error(code), { code });
}

/** Strict column alignment prevents one malformed column from shifting an OHLC bar. */
export function decodeHistory(payload, { intervalSec, nowMs }) {
  if (payload?.s === 'no_data') return [];
  if (!payload || payload.s !== 'ok' || !validTime(intervalSec) || !validTime(nowMs)) {
    throw refusal('invalid_history');
  }
  const { t, o, h, l, c, v } = payload;
  if (![t, o, h, l, c].every(Array.isArray) || t.length > 10_000
      || [o, h, l, c].some((column) => column.length !== t.length)
      || (v !== undefined && (!Array.isArray(v) || v.length !== t.length))) {
    throw refusal('invalid_history');
  }
  const byTime = new Map();
  for (let i = 0; i < t.length; i += 1) {
    const time = t[i];
    if (!validTime(time) || time % intervalSec !== 0 || time * 1000 > nowMs
        || ![o[i], h[i], l[i], c[i]].every(validPrice)
        || h[i] < Math.max(o[i], l[i], c[i]) || l[i] > Math.min(o[i], c[i])
        || (v !== undefined && !(typeof v[i] === 'number' && Number.isFinite(v[i]) && v[i] >= 0))) {
      throw refusal('invalid_history');
    }
    const candle = {
      time, open: o[i], high: h[i], low: l[i], close: c[i],
      ...(v === undefined ? {} : { volume: v[i] }),
      closed: (time + intervalSec) * 1000 <= nowMs, partial: false,
    };
    const duplicate = byTime.get(time);
    if (duplicate && ['open', 'high', 'low', 'close', 'volume'].some((key) => duplicate[key] !== candle[key])) {
      throw refusal('conflicting_history_duplicate');
    }
    byTime.set(time, candle);
  }
  return continuity([...byTime.values()].sort((a, b) => a.time - b.time), intervalSec);
}

/** feedUpdateTimestamp is microseconds; candle time is always UTC seconds. */
export function decodeQuote(payload, { feedId, nowMs }) {
  if (payload?.type !== 'streamUpdated' || payload.subscriptionId !== 1
      || !Array.isArray(payload.parsed?.priceFeeds) || payload.parsed.priceFeeds.length > 16) return null;
  const matching = payload.parsed.priceFeeds.filter((feed) => feed?.priceFeedId === feedId);
  if (matching.length !== 1) return null;
  const feed = matching[0];
  if (typeof feed.price !== 'string' || !/^\d{1,16}$/.test(feed.price)
      || !Number.isSafeInteger(Number(feed.price)) || !Number.isInteger(feed.exponent)
      || feed.exponent < -12 || feed.exponent > 0 || !validTime(feed.feedUpdateTimestamp)
      || !validTime(nowMs)) return null;
  const price = Number(feed.price) * 10 ** feed.exponent;
  const exchangeMs = feed.feedUpdateTimestamp / 1000;
  // Do not silently calibrate a local clock against an untrusted upstream clock.
  if (!validPrice(price) || exchangeMs > nowMs || nowMs - exchangeMs >= STALE_MS) return null;
  return { price, exchangeMs, receivedMs: nowMs };
}

function continuity(candles, intervalSec) {
  return candles.map((candle, index) => ({
    ...candle,
    gapBefore: index > 0 && candle.time - candles[index - 1].time !== intervalSec,
  }));
}

/** The observed API supports5m, but rejects native10m/20m resolutions. Aggregate
 * complete5m buckets rather than changing clocks or accepting sparse candles.
 */
function resampleHistory(rows, sourceStep, targetStep, nowMs) {
  if (sourceStep === targetStep) return rows;
  const ratio = targetStep / sourceStep, buckets = new Map();
  for (const row of rows) {
    const time = Math.floor(row.time / targetStep) * targetStep;
    if (!buckets.has(time)) buckets.set(time, []);
    buckets.get(time).push(row);
  }
  return continuity([...buckets].map(([time, chunk]) => {
    const full = chunk.length === ratio && chunk.every((row, i) => row.time === time + i * sourceStep && row.closed && !row.partial);
    if ((time + targetStep) * 1000 <= nowMs && !full) return null;
    const expected = Math.min(ratio, Math.floor((nowMs / 1000 - time) / sourceStep) + 1);
    const partial = chunk.length !== expected || chunk.some((row, i) => row.time !== time + i * sourceStep || row.partial || (i && row.gapBefore));
    const result = { time, open: chunk[0].open, high: Math.max(...chunk.map(row => row.high)),
      low: Math.min(...chunk.map(row => row.low)), close: chunk.at(-1).close,
      closed: (time + targetStep) * 1000 <= nowMs && full,
      partial: partial || ((time + targetStep) * 1000 <= nowMs && !full) };
    if (chunk.every(row => Object.hasOwn(row, 'volume'))) {
      const volume = chunk.reduce((sum, row) => sum + row.volume, 0);
      if (!Number.isFinite(volume)) throw refusal('invalid_history');
      result.volume = volume;
    }
    return result;
  }).filter(Boolean), targetStep);
}

function mergeCandles(candles, history, liveTimes, lastGapMs, requestedAtMs, intervalSec, retention) {
  const merged = new Map(candles.map(candle => [candle.time, candle]));
  for (const candle of history) {
    const observed = merged.get(candle.time);
    if (!candle.closed && observed && liveTimes.has(candle.time)) {
      merged.set(candle.time, {
        ...candle, high: Math.max(candle.high, observed.high), low: Math.min(candle.low, observed.low),
        close: liveTimes.get(candle.time) > requestedAtMs ? observed.close : candle.close,
        partial: observed.partial || lastGapMs > requestedAtMs,
      });
    } else merged.set(candle.time, candle);
  }
  return continuity([...merged.values()].sort((a, b) => a.time - b.time).slice(-retention), intervalSec);
}

function applyQuote(candles, liveTimes, quote, previous, gap, intervalSec, retention) {
  const time = Math.floor(quote.exchangeMs / 1000 / intervalSec) * intervalSec;
  const byTime = new Map(candles.map(candle => [candle.time, { ...candle }]));
  if (gap) for (const candle of byTime.values()) {
    if (!candle.closed) Object.assign(candle, { partial: true, closed: false });
  }
  const found = byTime.get(time);
  if (found?.closed) return candles;
  const candle = found ?? {
    time, open: quote.price, high: quote.price, low: quote.price, close: quote.price,
    closed: false, partial: !previous || gap,
  };
  // History alone can certify the part of a candle before subscription.
  candle.high = Math.max(candle.high, quote.price);
  candle.low = Math.min(candle.low, quote.price);
  candle.close = quote.price;
  if (gap) candle.partial = true;
  byTime.set(time, candle);
  for (const row of byTime.values()) if (row.time < time && !row.partial) row.closed = true;
  const result = continuity([...byTime.values()].sort((a, b) => a.time - b.time).slice(-retention), intervalSec);
  liveTimes.set(time, quote.exchangeMs);
  const firstTime = result[0]?.time ?? time;
  for (const observedTime of liveTimes.keys()) if (observedTime < firstTime) liveTimes.delete(observedTime);
  return result;
}

/**
 * Timers and network constructors can be replaced for deterministic lifecycle tests.
 * stop() aborts reads and detaches socket callbacks before invalidating the snapshot.
 */
export class JupiterFeed {
  #fetch;
  #WebSocket;
  #clock;
  #onUpdate;
  #setTimer;
  #clearTimer;
  #timers = new Set();
  #controllers = new Set();
  #running = false;
  #terminal = false;
  #generation = 0;
  #socket = null;
  #socketAt = 0;
  #reconnectPending = false;
  #reconnectAttempts = 0;
  #market = null;
  #candles = [];
  #liveTimes = new Map();
  #lastGapMs = 0;
  #quote = null;
  #historyReady = false;
  #historyRequest = null;
  #historyGeneration = 0;
  #lastHistoryAttempt = 0;
  #lastHistoryMs = null;
  #status = 'connecting';
  #error = null;
  #withContext;
  #context = { candles: [], liveTimes: new Map(), ready: false, error: null };

  get #retention() { return this.#withContext && this.intervalSec === 60 ? CONTEXT_HISTORY_BARS + 1 : MAX_BARS; }
  get #historyInterval() { return [600, 1200].includes(this.intervalSec) ? 300 : this.intervalSec; }

  constructor({ symbol, intervalSec, onUpdate, fetchImpl = globalThis.fetch,
    WebSocketImpl = globalThis.WebSocket, clock = Date.now,
    setTimeoutImpl = globalThis.setTimeout, clearTimeoutImpl = globalThis.clearTimeout,
    withReversalContext = false } = {}) {
    if (typeof withReversalContext !== 'boolean') throw new TypeError('withReversalContext must be boolean');
    this.#withContext = withReversalContext;
    Object.defineProperties(this, {
      symbol: { value: typeof symbol === 'string' ? symbol.toUpperCase() : '', enumerable: true },
      intervalSec: { value: intervalSec, enumerable: true },
    });
    this.#onUpdate = typeof onUpdate === 'function' ? onUpdate : () => {};
    // Window fetch/timers validate their receiver. A private-field call would
    // otherwise invoke them with this JupiterFeed instance in a real browser.
    this.#fetch = typeof fetchImpl === 'function' ? fetchImpl.bind(globalThis) : fetchImpl;
    this.#WebSocket = WebSocketImpl;
    this.#clock = clock;
    this.#setTimer = setTimeoutImpl.bind(globalThis);
    this.#clearTimer = clearTimeoutImpl.bind(globalThis);
  }

  getSnapshot() {
    const minuteRows = this.intervalSec === 60 ? this.#candles : this.#context.candles;
    return Object.freeze({
      symbol: this.symbol, intervalSec: this.intervalSec, status: this.#status,
      candles: Object.freeze(this.#candles.map((candle) => Object.freeze({ ...candle }))),
      quote: this.#quote ? Object.freeze({ ...this.#quote }) : null,
      error: this.#error, source: SOURCE, lastHistoryMs: this.#lastHistoryMs,
      historyIntervalSec: this.#historyInterval,
      minuteCandles: this.#withContext ? Object.freeze(minuteRows.map(candle => Object.freeze({ ...candle }))) : null,
      minuteStatus: !this.#withContext ? 'disabled' : (this.intervalSec === 60 ? this.#historyReady : this.#context.ready) ? 'ready' : 'unavailable',
      minuteError: this.#context.error,
    });
  }

  #publish(status = this.#status, error = this.#error) {
    this.#status = status;
    this.#error = error;
    this.#onUpdate(this.getSnapshot());
  }

  #after(callback, ms) {
    const id = this.#setTimer(() => {
      this.#timers.delete(id);
      if (this.#running) callback();
    }, ms);
    this.#timers.add(id);
    return id;
  }

  #cancel(id) {
    this.#clearTimer(id);
    this.#timers.delete(id);
  }

  #active(generation) {
    return this.#running && !this.#terminal && generation === this.#generation;
  }

  async #json(url) {
    const controller = new AbortController();
    this.#controllers.add(controller);
    const timeout = this.#after(() => controller.abort(), 8000);
    try {
      if (typeof this.#fetch !== 'function') throw refusal('network_unavailable');
      const response = await this.#fetch(url, {
        method: 'GET', credentials: 'omit', redirect: 'error', cache: 'no-store', signal: controller.signal,
      });
      if (!response.ok) throw refusal('public_read_failed');
      let text = '';
      if (response.body?.getReader) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let bytes = 0;
        for (;;) {
          const next = await reader.read();
          if (next.done) break;
          bytes += next.value.byteLength;
          if (bytes > MAX_JSON_BYTES) {
            await reader.cancel();
            throw refusal('response_size_limit');
          }
          text += decoder.decode(next.value, { stream: true });
        }
        text += decoder.decode();
      } else {
        text = await response.text();
        if (new TextEncoder().encode(text).length > MAX_JSON_BYTES) throw refusal('response_size_limit');
      }
      return JSON.parse(text);
    } catch (error) {
      const safe = new Set(['network_unavailable', 'public_read_failed', 'response_size_limit']);
      throw refusal(safe.has(error?.code) ? error.code : 'public_read_failed');
    } finally {
      this.#cancel(timeout);
      this.#controllers.delete(controller);
    }
  }

  async start() {
    if (this.#running) return;
    this.#running = true;
    this.#terminal = false;
    this.#reconnectAttempts = 0;
    this.#reconnectPending = false;
    this.#quote = null;
    this.#candles = [];
    this.#liveTimes.clear();
    this.#context = { candles: [], liveTimes: new Map(), ready: false, error: null };
    this.#lastGapMs = 0;
    this.#market = null;
    this.#historyReady = false;
    this.#lastHistoryMs = null;
    const generation = ++this.#generation;
    this.#publish('connecting', null);
    if (!/^[A-Z][A-Z0-9]{0,11}$/.test(this.symbol)
        || !TIMEFRAMES.some((entry) => entry.seconds === this.intervalSec)) {
      this.#terminal = true;
      this.#publish('unsupported', 'unsupported_market_or_timeframe');
      return;
    }
    try {
      const catalog = await this.#json(JUPITER_ENDPOINTS.markets);
      if (!this.#active(generation)) return;
      const markets = catalog?.markets;
      if (!Array.isArray(markets) || markets.length > 1000) throw refusal('invalid_market_catalog');
      const matching = markets.filter((market) => market?.symbol === this.symbol);
      if (matching.length !== 1) {
        this.#terminal = true;
        this.#publish('unsupported', matching.length ? 'ambiguous_market' : 'market_unavailable');
        return;
      }
      const market = matching[0];
      if (!validTime(market.feedId) || typeof market.address !== 'string'
          || !/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(market.address)
          || typeof market.closed !== 'boolean') throw refusal('invalid_market_catalog');
      this.#market = { ...market };
      if (market.closed) {
        this.#terminal = true;
        this.#publish('unsupported', 'market_closed');
        return;
      }
      await this.#backfill(generation);
      if (!this.#active(generation)) return;
      this.#connect(generation);
      this.#maintenance(generation);
    } catch (error) {
      if (this.#active(generation)) this.#publish('error', error?.code === 'invalid_market_catalog'
        ? 'invalid_market_catalog' : 'public_read_failed');
    }
  }

  async #backfill(generation) {
    if (this.#historyRequest && this.#historyGeneration === generation) return this.#historyRequest;
    const operation = this.#loadHistory(generation);
    this.#historyRequest = operation;
    this.#historyGeneration = generation;
    try { return await operation; }
    finally { if (this.#historyRequest === operation) this.#historyRequest = null; }
  }

  async #loadHistory(generation) {
    if (!this.#active(generation)) return false;
    const requestedAtMs = this.#clock();
    this.#lastHistoryAttempt = requestedAtMs;
    this.#publish('backfilling', null);
    const seconds = Math.floor(this.#clock() / 1000);
    const currentStart = Math.floor(seconds / this.intervalSec) * this.intervalSec;
    const query = new URLSearchParams({
      symbol: `${this.symbol}USD`, resolution: String(this.#historyInterval / 60),
      from: String(Math.max(this.intervalSec, currentStart - (this.#retention - 1) * this.intervalSec)),
      to: String(seconds + 1),
    });
    try {
      const [payload] = await Promise.all([
        this.#json(`${JUPITER_ENDPOINTS.history}?${query}`),
        this.#withContext && this.intervalSec !== 60 ? this.#loadMinuteContext(generation, requestedAtMs) : null,
      ]);
      if (!this.#active(generation)) return false;
      // A response started before a boundary cannot certify that boundary's close,
      // even when its HTTP request finishes after the clock crosses the boundary.
      const nativeHistory = decodeHistory(payload, { intervalSec: this.#historyInterval, nowMs: requestedAtMs });
      const history = resampleHistory(nativeHistory, this.#historyInterval, this.intervalSec, requestedAtMs);
      this.#candles = mergeCandles(this.#candles, history, this.#liveTimes, this.#lastGapMs, requestedAtMs, this.intervalSec, this.#retention);
      // Only observations newer than this request may advance its close. Keep
      // older quote timestamps truthful rather than replaying them as new data.
      if (this.#quote?.exchangeMs > requestedAtMs) this.#applyQuote(this.#quote, false);
      this.#lastHistoryMs = this.#clock();
      const required = Math.floor(this.#clock() / 1000 / this.intervalSec) * this.intervalSec - this.intervalSec;
      this.#historyReady = history.some((candle) => candle.time === required && candle.closed);
      if (!this.#historyReady) {
        this.#publish('error', history.length ? 'history_lagging' : 'history_unavailable');
      } else if (this.#fresh()) {
        this.#publish('live', null);
      } else {
        this.#publish(this.#quote ? 'stale' : 'connecting', this.#quote ? 'stale_quote' : null);
      }
      return this.#historyReady;
    } catch (error) {
      if (!this.#active(generation)) return false;
      this.#historyReady = false;
      this.#publish('error', ['invalid_history', 'conflicting_history_duplicate'].includes(error?.code)
        ? error.code : 'history_unavailable');
      return false;
    }
  }

  async #loadMinuteContext(generation, requestedAtMs) {
    const current = Math.floor(requestedAtMs / 60_000) * 60;
    const query = new URLSearchParams({ symbol: `${this.symbol}USD`, resolution: '1',
      from: String(Math.max(60, current - CONTEXT_HISTORY_BARS * 60)), to: String(Math.floor(requestedAtMs / 1000) + 1) });
    try {
      const payload = await this.#json(`${JUPITER_ENDPOINTS.history}?${query}`);
      if (!this.#active(generation)) return;
      const history = decodeHistory(payload, { intervalSec: 60, nowMs: requestedAtMs });
      this.#context.candles = mergeCandles(this.#context.candles, history, this.#context.liveTimes,
        this.#lastGapMs, requestedAtMs, 60, CONTEXT_HISTORY_BARS + 1);
      if (this.#quote?.exchangeMs > requestedAtMs) this.#context.candles = applyQuote(this.#context.candles,
        this.#context.liveTimes, this.#quote, this.#quote, false, 60, CONTEXT_HISTORY_BARS + 1);
      const required = Math.floor(this.#clock() / 60_000) * 60 - 60;
      this.#context.ready = history.some(candle => candle.time === required && candle.closed);
      this.#context.error = this.#context.ready ? null : 'minute_history_lagging';
    } catch {
      if (!this.#active(generation)) return;
      this.#context.ready = false;
      this.#context.error = 'minute_history_unavailable';
    }
  }

  #fresh() {
    const now = this.#clock();
    return this.#quote && now >= this.#quote.exchangeMs && now >= this.#quote.receivedMs
      && now - this.#quote.exchangeMs < STALE_MS && now - this.#quote.receivedMs < STALE_MS;
  }

  #applyQuote(quote, gap) {
    this.#candles = applyQuote(this.#candles, this.#liveTimes, quote, this.#quote, gap, this.intervalSec, this.#retention);
    if (this.#withContext && this.intervalSec !== 60) this.#context.candles = applyQuote(this.#context.candles,
      this.#context.liveTimes, quote, this.#quote, gap, 60, CONTEXT_HISTORY_BARS + 1);
  }

  #connect(generation) {
    if (!this.#active(generation)) return;
    try {
      if (typeof this.#WebSocket !== 'function') throw refusal('stream_unavailable');
      const socket = new this.#WebSocket(JUPITER_ENDPOINTS.stream);
      this.#socket = socket;
      this.#socketAt = this.#clock();
      const current = () => this.#active(generation) && this.#socket === socket;
      socket.onopen = () => {
        if (!current()) return;
        try {
          socket.send(JSON.stringify({
            type: 'subscribe', subscriptionId: 1, channel: 'fixed_rate@200ms',
            priceFeedIds: [this.#market.feedId], properties: ['price', 'exponent', 'feedUpdateTimestamp'],
            formats: [], ignoreInvalidFeeds: false,
          }));
        } catch { this.#disconnect(generation); }
      };
      socket.onmessage = (event) => {
        if (!current() || typeof event.data !== 'string' || event.data.length > 64_000) return;
        let payload;
        try { payload = JSON.parse(event.data); } catch { return; }
        if (payload?.type === 'subscriptionError') {
          this.#terminal = true;
          this.#detach();
          this.#publish('error', 'subscription_refused');
          return;
        }
        const quote = decodeQuote(payload, { feedId: this.#market.feedId, nowMs: this.#clock() });
        if (!quote || (this.#quote && quote.exchangeMs <= this.#quote.exchangeMs)) return;
        const gap = this.#quote && (quote.exchangeMs - this.#quote.exchangeMs > GAP_MS
          || quote.receivedMs - this.#quote.receivedMs > GAP_MS);
        this.#applyQuote(quote, Boolean(gap));
        this.#quote = quote;
        this.#reconnectAttempts = 0;
        if (gap) {
          this.#lastGapMs = quote.receivedMs;
          this.#historyReady = false;
          this.#context.ready = false;
          void this.#backfill(generation);
        }
        this.#publish(this.#historyReady ? 'live' : 'backfilling', this.#historyReady ? null : 'awaiting_history');
      };
      socket.onclose = socket.onerror = () => { if (current()) this.#disconnect(generation); };
    } catch { this.#disconnect(generation); }
  }

  #detach() {
    const socket = this.#socket;
    this.#socket = null;
    if (socket) {
      socket.onopen = socket.onmessage = socket.onclose = socket.onerror = null;
      try { socket.close(); } catch { /* Detached callbacks cannot restart the feed. */ }
    }
  }

  #disconnect(generation) {
    if (!this.#active(generation) || this.#reconnectPending) return;
    this.#detach();
    // History can repair candles, but only this connection's next observation
    // can restore live status. The old receipt must not time out the new socket.
    this.#quote = null;
    this.#historyReady = false;
    this.#context.ready = false;
    this.#lastGapMs = this.#clock();
    this.#candles = this.#candles.map((candle) => candle.closed ? candle : { ...candle, partial: true });
    this.#context.candles = this.#context.candles.map(candle => candle.closed ? candle : { ...candle, partial: true });
    this.#reconnectAttempts += 1;
    if (this.#reconnectAttempts > 5) {
      this.#terminal = true;
      this.#publish('error', 'reconnect_exhausted');
      return;
    }
    this.#reconnectPending = true;
    this.#publish('stale', 'stream_disconnected');
    this.#after(async () => {
      this.#reconnectPending = false;
      if (!this.#active(generation)) return;
      await this.#backfill(generation);
      if (this.#active(generation)) this.#connect(generation);
    }, Math.min(10_000, 500 * 2 ** (this.#reconnectAttempts - 1)));
  }

  #maintenance(generation) {
    this.#after(() => {
      if (!this.#active(generation)) return;
      if (this.#quote && !this.#fresh()) this.#publish('stale', 'stale_quote');
      const last = this.#quote?.receivedMs ?? this.#socketAt;
      if (this.#socket && this.#clock() - last >= 20_000) this.#disconnect(generation);
      if (this.#clock() - this.#lastHistoryAttempt >= HISTORY_EVERY_MS) void this.#backfill(generation);
      this.#maintenance(generation);
    }, 1000);
  }

  stop() {
    if (!this.#running) return;
    this.#running = false;
    this.#generation += 1;
    this.#detach();
    for (const controller of this.#controllers) controller.abort();
    this.#controllers.clear();
    for (const timer of this.#timers) this.#clearTimer(timer);
    this.#timers.clear();
    this.#publish('stale', 'feed_stopped');
  }
}
